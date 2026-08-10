"""
혼잡 시 대체 장소 추천 (Nudge Engine).

노션 문서 설계:
  - KNN으로 원래 가려던 곳(A)과 벡터가 가장 가까운 장소(B, C)를 탐색
  - '고요 지수'가 높은 곳을 최우선 필터링
  - 거리(L2)만 보지 않고 '이동 편의성' 가중치를 둬서 너무 먼 곳은 제외
  - 트리거 조건: Selected_POI.Quiet_Index < Threshold_Value 일 때만 알림
"""
from __future__ import annotations

import math

import numpy as np
from sklearn.neighbors import NearestNeighbors

from app.config import settings
from app.data.mock_data import POI

CATEGORY_CODES = {
    "사찰": 0, "해수욕장": 1, "미술관": 2, "골목": 3,
    "공원": 4, "카페": 5, "서원": 6,
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _poi_vector(poi: POI, quiet_index: float) -> list[float]:
    """
    문서에서 말한 '고요 지수, 테마, 편의시설 등' 벡터를 단순화한 버전.
    실서비스에서는 편의시설(주차/화장실 등) 피처를 추가로 확장 가능.
    """
    return [
        quiet_index,
        CATEGORY_CODES.get(poi.category, -1),
        poi.vegetation_score,
        poi.noise_sensitivity,
    ]


def should_trigger_nudge(quiet_index: float) -> bool:
    """문서의 If (Selected_POI.Quiet_Index < Threshold_Value) 트리거."""
    return quiet_index < settings.QUIET_INDEX_ALERT_THRESHOLD


def recommend_alternatives(
    target_poi: POI,
    target_quiet_index: float,
    candidates: list[tuple[POI, float]],  # (poi, quiet_index) 쌍의 리스트
    k: int = 3,
    max_distance_km: float = 15.0,
    distance_weight: float = 0.3,
) -> list[dict]:
    """
    target_poi 대비 유사하면서 더 한적한 대체 장소를 추천합니다.

    1) 이동 편의성 필터: max_distance_km보다 먼 곳은 후보에서 제외
    2) KNN으로 target과 벡터가 가까운 순으로 정렬
    3) 최종 스코어 = 벡터 유사도(가까울수록 좋음) + distance_weight * 정규화 거리
       (고요 지수가 낮은 곳, 즉 target보다 더 혼잡한 곳은 애초에 제외)
    """
    filtered = []
    for poi, qi in candidates:
        if poi.poi_id == target_poi.poi_id:
            continue
        if qi <= target_quiet_index:
            # 더 한적한 곳만 추천 (문서: '고요 지수'가 높은 곳을 최우선 필터링)
            continue
        dist_km = _haversine_km(target_poi.lat, target_poi.lng, poi.lat, poi.lng)
        if dist_km > max_distance_km:
            continue
        filtered.append((poi, qi, dist_km))

    if not filtered:
        return []

    target_vec = np.array([_poi_vector(target_poi, target_quiet_index)])
    candidate_vecs = np.array([_poi_vector(poi, qi) for poi, qi, _ in filtered])

    n_neighbors = min(k, len(filtered))
    nn = NearestNeighbors(n_neighbors=n_neighbors)
    nn.fit(candidate_vecs)
    distances, indices = nn.kneighbors(target_vec)

    max_vec_dist = float(distances.max()) or 1.0
    max_geo_dist = max(d for _, _, d in filtered) or 1.0

    results = []
    for vec_dist, idx in zip(distances[0], indices[0]):
        poi, qi, geo_dist = filtered[idx]
        vec_sim_score = 1 - (vec_dist / max_vec_dist)  # 가까울수록 1에 근접
        geo_penalty = (geo_dist / max_geo_dist) * distance_weight
        final_score = round(vec_sim_score - geo_penalty, 3)
        results.append({
            "poi_id": poi.poi_id,
            "name": poi.name,
            "quiet_index": qi,
            "distance_km": round(geo_dist, 2),
            "score": final_score,
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results

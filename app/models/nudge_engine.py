"""
혼잡 시 대체 장소 추천 (Nudge Engine).

노션 문서 설계:
  - KNN으로 원래 가려던 곳(A)과 벡터가 가장 가까운 장소(B, C)를 탐색
  - '고요 지수'가 높은 곳을 최우선 필터링
  - 거리(L2)만 보지 않고 '이동 편의성' 가중치를 둬서 너무 먼 곳은 제외
  - 트리거 조건: Selected_POI.Quiet_Index < Threshold_Value 일 때만 알림
  - 트리거 판단은 AI가 전담 (2026-09 확정, 백엔드는 API만 호출)
"""
from __future__ import annotations

from app.utils.geo import haversine_km

import numpy as np
from sklearn.neighbors import NearestNeighbors
from app.data.category_codes import CATEGORY_CODES
from app.config import settings
from app.data.mock_data import POI
from app.models.embedding_model import get_mode_fit_vector

MODE_LABELS = {
    "COZY": "아늑한", "NATURAL": "자연이 싱그러운", "URBAN": "도시적인",
    "VINTAGE": "빈티지한", "EXOTIC": "이국적인", "VIBRANT": "활기찬",
    "SENSORY": "감각적인", "TRANQUIL": "고요한",
}
MODE_ORDER = ["COZY", "NATURAL", "URBAN", "VINTAGE", "EXOTIC", "VIBRANT", "SENSORY", "TRANQUIL"]


def _poi_vector(poi: POI, quiet_index: float) -> list[float]:
    """
    대체지 유사도 판단에 쓰이는 벡터.
    [고요지수, 카테고리코드, 식생점수] +
    [COZY, NATURAL, URBAN, VINTAGE, EXOTIC, VIBRANT, SENSORY, TRANQUIL] 적합도(8개)

    모드 적합도를 추가한 이유: 카테고리만 보면 "자연공원류"로 비슷해 보여도
    실제 분위기(아늑함/활기참 등)는 다를 수 있어서
    (2026-09 팀 확정 — 여행감성 8종 최종 반영)
    """
    base = [
        quiet_index,
        CATEGORY_CODES.get(poi.category, -1),
        poi.vegetation_score,
    ]
    mode_fit = get_mode_fit_vector(poi.description)
    return base + mode_fit


def _generate_recommend_reason(
    target_poi: POI, target_qi: float, candidate: POI, candidate_qi: float, distance_km: float,
) -> str:
    """대체지 추천 이유를 자연어 한 문장으로 생성합니다."""
    target_modes = get_mode_fit_vector(target_poi.description)
    candidate_modes = get_mode_fit_vector(candidate.description)

    # 두 장소 모두에서 점수가 높은 무드(공통 분위기)를 찾음
    combined = [(MODE_ORDER[i], target_modes[i] * candidate_modes[i]) for i in range(len(MODE_ORDER))]
    top_mode_code, top_mode_score = max(combined, key=lambda x: x[1])
    mood_phrase = MODE_LABELS[top_mode_code] if top_mode_score > 0.1 else None

    qi_diff = candidate_qi - target_qi
    quiet_phrase = "훨씬 한적하고" if qi_diff >= 20 else "더 한적하고" if qi_diff >= 5 else None

    parts = []
    if quiet_phrase:
        parts.append(quiet_phrase)
    if mood_phrase:
        parts.append(f"비슷하게 {mood_phrase}")
    if distance_km <= 1.0:
        parts.append("걸어서 이동 가능한")

    if not parts:
        return f"{candidate.category} 대체 장소예요"

    return " ".join(parts) + f" {candidate.category}예요"


def should_trigger_nudge(quiet_index: float) -> bool:
    """문서의 If (Selected_POI.Quiet_Index < Threshold_Value) 트리거."""
    return quiet_index < settings.QUIET_INDEX_ALERT_THRESHOLD


def recommend_alternatives(
    target_poi: POI,
    target_quiet_index: float,
    candidates: list[tuple[POI, float]],  # (poi, quiet_index) 쌍의 리스트
    k: int = 3,
    max_distance_km: float = 3.0,
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
        dist_km = haversine_km(target_poi.lat, target_poi.lng, poi.lat, poi.lng)
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
        final_score = round(max(0.0, vec_sim_score - geo_penalty), 3)
        results.append({
            "poi_id": poi.poi_id,
            "name": poi.name,
            "quiet_index": qi,
            "distance_km": round(geo_dist, 2),
            "score": final_score,
            "recommend_reason": _generate_recommend_reason(
                target_poi, target_quiet_index, poi, qi, geo_dist
            ),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
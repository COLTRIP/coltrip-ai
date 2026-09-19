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


def _poi_vector(poi: POI) -> list[float]:
    """
    대체지 "분위기" 유사도 판단에 쓰이는 벡터.
    [카테고리코드, 식생점수] +
    [COZY, NATURAL, URBAN, VINTAGE, EXOTIC, VIBRANT, SENSORY, TRANQUIL] 적합도(8개)

    고요지수는 여기서 제외한다 — 방향성 없는 유클리드 거리에 넣으면
    "target과 고요지수가 다를수록 벌점"이 되어, 확실히 더 조용한 후보가
    오히려 낮은 점수를 받는 버그가 있었다. 고요지수 개선폭은
    recommend_alternatives에서 별도의 방향성 있는 보너스로 처리한다.
    (2026-09-15 수정)

    모드 적합도를 추가한 이유: 카테고리만 보면 "자연공원류"로 비슷해 보여도
    실제 분위기(아늑함/활기참 등)는 다를 수 있어서
    (2026-09 팀 확정 — 여행감성 8종 최종 반영)
    """
    base = [
        CATEGORY_CODES.get(poi.category, -1),
        poi.vegetation_score,
    ]
    mode_fit = get_mode_fit_vector(poi.description)
    return base + mode_fit


def _generate_recommend_reason(
    target_poi: POI, target_qi: float, candidate: POI, candidate_qi: float, distance_km: float,
) -> str:
    """
    대체지 추천 이유를 자연어 한 문장으로 생성합니다.

    2026-09-16 수정: 문구 조각을 공백으로 그냥 이어붙여서 형용사가
    나열되며 어색했던 문제를 접속어로 수정.

    2026-09-19 재작성: 위 방식도 매번 "훨씬 한적하고, 비슷하게 OO한 분위기의
    곳이에요"라는 똑같은 틀만 반복해 기계적으로 느껴졌음. LLM 호출은 매
    요청마다 지연시간·비용이 들어 즉시 응답이 중요한 이 기능엔 안 맞다고
    판단, 대신 각 조각(고요함 정도/무드/거리)마다 여러 자연스러운 표현을
    미리 준비해두고 무작위로 골라 조합하는 방식으로 다양성을 확보함.
    poi_id 조합을 시드로 써서, 같은 두 장소끼리는 항상 같은 문장이 나오게
    해 재현성은 유지함(새로고침할 때마다 문구가 바뀌면 오히려 어색함).
    """
    import random

    target_modes = get_mode_fit_vector(target_poi.description)
    candidate_modes = get_mode_fit_vector(candidate.description)

    combined = [(MODE_ORDER[i], target_modes[i] * candidate_modes[i]) for i in range(len(MODE_ORDER))]
    top_mode_code, top_mode_score = max(combined, key=lambda x: x[1])
    mood_phrase = MODE_LABELS[top_mode_code] if top_mode_score > 0.1 else None

    qi_diff = candidate_qi - target_qi

    # 같은 대체지 쌍(target, candidate)이면 항상 같은 문장이 나오도록 고정 시드 사용
    rng = random.Random(f"{target_poi.poi_id}-{candidate.poi_id}")

    QUIET_PHRASES_HIGH = [  # qi_diff >= 20
        "훨씬 한적하고", "사람이 확실히 적고", "붐비지 않고 여유롭고", "눈에 띄게 조용하고",
    ]
    QUIET_PHRASES_MID = [  # qi_diff >= 5
        "더 한적하고", "조금 더 여유롭고", "상대적으로 조용하고", "붐빔이 덜하고",
    ]
    MOOD_TEMPLATES = [
        "비슷하게 {mood} 분위기의", "{mood} 느낌이 닮아 있는", "{mood} 매력을 함께 지닌",
        "{mood} 분위기가 이어지는",
    ]
    WALK_ALONE_PHRASES = [
        "걸어서 갈 수 있는 가까운 거리예요", "도보로 이동 가능한 가까운 곳이에요",
        "멀지 않아 걸어서 갈 만해요",
    ]
    WALK_WITH_LEAD_PHRASES = [
        "곳이면서 걸어서도 갈 수 있는 거리예요", "곳이고 도보로도 충분히 갈 수 있어요",
        "곳인데 걸어서 이동하기도 좋아요",
    ]
    PLAIN_ENDING = ["곳이에요", "장소예요", "곳으로 추천드려요"]
    FALLBACK_PHRASES = [
        "{name}은 대체 장소로 추천할 만한 곳이에요",
        "{name}도 한번 가보시면 좋을 것 같아요",
        "{name}을 대안으로 고려해보세요",
    ]

    quiet_phrase = None
    if qi_diff >= 20:
        quiet_phrase = rng.choice(QUIET_PHRASES_HIGH)
    elif qi_diff >= 5:
        quiet_phrase = rng.choice(QUIET_PHRASES_MID)

    mood_clause = None
    if mood_phrase:
        mood_clause = rng.choice(MOOD_TEMPLATES).format(mood=mood_phrase)

    clauses = [c for c in [quiet_phrase, mood_clause] if c]
    walkable = distance_km <= 1.0

    if not clauses and not walkable:
        return rng.choice(FALLBACK_PHRASES).format(name=candidate.name)

    # lead = ", ".join(clauses) if clauses else ""

    if walkable:
        if lead:
            return f"{lead} {rng.choice(WALK_WITH_LEAD_PHRASES)}"
        return rng.choice(WALK_ALONE_PHRASES)

    return f"{lead} {rng.choice(PLAIN_ENDING)}"


def should_trigger_nudge(quiet_index: float, baseline_quiet_index: float | None = None) -> bool:
    """
    트리거 조건 (둘 중 하나만 충족해도 트리거):
      - 절대 기준: 현재 고요 지수 < Threshold_Value(기본 40)
      - 상대 기준: baseline_quiet_index가 주어졌고, 그 대비 15 이상 하락
    """
    if quiet_index < settings.QUIET_INDEX_ALERT_THRESHOLD:
        return True
    if baseline_quiet_index is not None and (baseline_quiet_index - quiet_index) >= 15:
        return True
    return False


def recommend_alternatives(
    target_poi: POI,
    target_quiet_index: float,
    candidates: list[tuple[POI, float]],
    k: int = 3,
    max_distance_km: float = 3.0,
    distance_weight: float = 0.3,
    quiet_weight: float = 0.3,
    exclude_poi_ids: set[str] | None = None,
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
        if exclude_poi_ids and poi.poi_id in exclude_poi_ids:
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

    target_vec = np.array([_poi_vector(target_poi)])
    candidate_vecs = np.array([_poi_vector(poi) for poi, qi, _ in filtered])

    # 스케일이 다른 피처(고요지수 0~100, 카테고리 코드 등)가 거리 계산을
    # 지배하지 않도록 타깃+후보 벡터를 함께 min-max 정규화한다.
    all_vecs = np.vstack([target_vec, candidate_vecs])
    vec_min = all_vecs.min(axis=0)
    vec_range = all_vecs.max(axis=0) - vec_min
    vec_range[vec_range == 0] = 1.0  # 상수 컬럼 나눗셈 방지
    all_vecs = (all_vecs - vec_min) / vec_range
    target_vec, candidate_vecs = all_vecs[:1], all_vecs[1:]

    n_neighbors = min(k, len(filtered))
    nn = NearestNeighbors(n_neighbors=n_neighbors)
    nn.fit(candidate_vecs)
    distances, indices = nn.kneighbors(target_vec)

    # vec_sim_score의 분모를 "이번에 뽑힌 k개 후보 중 최댓값"으로 쓰면,
    # k개 중 벡터상 가장 먼 하나는 절대적 차이와 무관하게 항상 vec_sim_score=0이
    # 되는 구조적 문제가 있었다(quiet_gain/geo_penalty에서 이미 고친 것과 동일한
    # 패턴). 벡터가 이미 [0,1]로 min-max 정규화돼 있으므로, D차원 정규화 공간에서
    # 이론상 가능한 최대 거리 sqrt(D)를 고정 분모로 쓴다. (2026-09-15)
    vec_dim = candidate_vecs.shape[1]
    max_possible_vec_dist = np.sqrt(vec_dim)

    # quiet_index는 로그밀도 기반 정규화 스케일이라 값 간격이 균일하지 않다.
    # 산술 차이(quiet_gain)를 그대로 쓰면 후보군 내 극단값 하나가 분모를 독점해
    # 나머지가 다 눌리므로, filtered 후보군 내에서의 순위(percentile rank,
    # 동점은 평균 순위 처리)로 바꾼다. (2026-09-15)
    qi_values = [qi for _, qi, _ in filtered]
    n_filtered = len(qi_values)
    if n_filtered > 1:
        quiet_percentiles = []
        for v in qi_values:
            less = sum(1 for x in qi_values if x < v)
            equal = sum(1 for x in qi_values if x == v)
            rank = less + (equal - 1) / 2  # 동점은 평균 순위
            quiet_percentiles.append(rank / (n_filtered - 1))
    else:
        quiet_percentiles = [1.0]

    results = []
    for vec_dist, idx in zip(distances[0], indices[0]):
        poi, qi, geo_dist = filtered[idx]
        vec_sim_score = 1 - (vec_dist / max_possible_vec_dist)  # 가까울수록 1에 근접, 고정 분모
        # 거리 페널티도 filtered 내 최대값이 아니라 고정 상한(max_distance_km)을
        # 분모로 써서, 후보 하나가 우연히 멀다고 나머지가 유리해지는 걸 막는다.
        geo_penalty = (geo_dist / max_distance_km) * distance_weight
        quiet_bonus = quiet_percentiles[idx] * quiet_weight
        final_score = round(min(1.0, max(0.0, vec_sim_score - geo_penalty + quiet_bonus)), 3)
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
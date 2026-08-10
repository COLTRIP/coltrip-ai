from __future__ import annotations

from app.models.embedding_model import matches_user_context, natural_sound_score
from app.services.quiet_index_service import get_all_quiet_indices


def recommend_by_context(
    mood: str,
    purpose: str,
    hour: int,
    is_weekend: bool,
    natural_sound_mode: bool = False,
    wind_speed_ms: float | None = None,
    min_match_score: float = 0.3,
) -> list[dict]:
    """
    시나리오 표 재현:
      입력: 사용자 선택("인문적 정적" + "사유/명상")
      연산: 1) context_tags 기반 매칭 점수 계산
            2) 그중 고요 지수가 가장 낮은(=가장 한적한 순) 순으로 정렬
            3) natural_sound_mode면 자연의 소리 점수도 함께 반영
      출력: 정렬된 추천 리스트
    """
    all_pois = get_all_quiet_indices(hour, is_weekend)

    scored = []
    for poi, _population, quiet_index in all_pois:
        match_score = matches_user_context(poi.description, mood, purpose)
        # NOTE(최지원): 코사인 유사도 기반이라 0.3이 정답은 아님.
        # 실제 모델로 여러 POI에 대해 점수 분포를 찍어보고 임계값을 조정할 것.
        if match_score < min_match_score:
            continue

        entry = {
            "poi_id": poi.poi_id,
            "name": poi.name,
            "quiet_index": quiet_index,
            "context_match_score": match_score,
            "natural_sound_score": None,
        }

        if natural_sound_mode and wind_speed_ms is not None:
            entry["natural_sound_score"] = natural_sound_score(wind_speed_ms, poi.vegetation_score)

        scored.append(entry)

    # 정렬 기준: context 매칭도 우선 → 동점이면 고요 지수 높은 순
    # natural_sound_mode인 경우 자연음 점수도 함께 고려
    def sort_key(e):
        natural = e["natural_sound_score"] or 0
        return (e["context_match_score"], natural, e["quiet_index"])

    scored.sort(key=sort_key, reverse=True)
    return scored

from app.data.mock_data import MOCK_POIS
from app.models.nudge_engine import recommend_alternatives, should_trigger_nudge


def test_trigger_threshold():
    assert should_trigger_nudge(20) is True
    assert should_trigger_nudge(80) is False


def test_recommend_alternatives_excludes_more_crowded():
    target = MOCK_POIS[0]
    target_qi = 20.0

    candidates = [(poi, 90.0) for poi in MOCK_POIS[1:]]
    # 하나는 target보다 더 혼잡하게 설정 -> 제외되어야 함
    candidates[0] = (candidates[0][0], 10.0)

    results = recommend_alternatives(target, target_qi, candidates, k=3)
    result_ids = {r["poi_id"] for r in results}
    assert candidates[0][0].poi_id not in result_ids


def test_recommend_alternatives_returns_sorted_by_score():
    target = MOCK_POIS[0]
    target_qi = 20.0
    candidates = [(poi, 70.0 + i) for i, poi in enumerate(MOCK_POIS[1:])]

    results = recommend_alternatives(target, target_qi, candidates, k=5)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

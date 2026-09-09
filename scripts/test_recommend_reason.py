"""recommendReason이 실제로 어떤 문장을 만드는지 확인."""
from app.data.mock_data import MOCK_POIS
from app.models.nudge_engine import recommend_alternatives

target = MOCK_POIS[0]
candidates = [(poi, 85.0) for poi in MOCK_POIS[1:]]

results = recommend_alternatives(target, target_quiet_index=25.0, candidates=candidates, k=3, max_distance_km=999)
for r in results:
    print(f"{r['name']}: \"{r['recommend_reason']}\" (점수: {r['score']})")
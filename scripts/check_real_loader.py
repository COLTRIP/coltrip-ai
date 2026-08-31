"""RealDataLoader.fetch_pois() 동작 확인용 임시 스크립트. 확인 끝나면 지울 것."""
from app.data.loader import RealDataLoader

loader = RealDataLoader()
pois = loader.fetch_pois()

print(f"총 {len(pois)}개 관광지 로드됨")
print()

# 카테고리별로 면적이 다르게 들어가는지 확인 (카페 vs 해수욕장)
for target_category in ["카페", "해수욕장", "종교성지"]:
    sample = next((p for p in pois if p.category == target_category), None)
    if sample:
        print(f"[{target_category}] {sample.name} | 면적: {sample.area_m2}㎡")
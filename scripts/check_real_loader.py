"""RealDataLoader.fetch_pois() 동작 확인용 임시 스크립트. 확인 끝나면 지울 것."""
from app.data.loader import RealDataLoader

loader = RealDataLoader()
pois = loader.fetch_pois()

print(f"총 {len(pois)}개 관광지 로드됨")
print()
for poi in pois[:5]:
    print(f"- {poi.name} | {poi.category} | ({poi.lat}, {poi.lng})")
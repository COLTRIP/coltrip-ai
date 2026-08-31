"""카테고리별 관광지 개수 분포 확인용."""
from collections import Counter
from app.data.loader import RealDataLoader

loader = RealDataLoader()
pois = loader.fetch_pois()

counts = Counter(poi.category for poi in pois)
print(f"총 {len(pois)}개 관광지\n")
for category, count in counts.most_common():
    print(f"{category}: {count}개")
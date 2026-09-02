"""
최종 POI(594개) 중 부산진구(230) 소속이 몇 개인지 확인.
원본 TourAPI 응답과 fetch_pois() 이후 필터링된 최종 목록, 둘 다 구별로 집계합니다.
"""
from collections import Counter

from app.data.loader import RealDataLoader, _fetch_area_based_list

# 1) 원본 기준 (카테고리 매핑 전, 필터링 전)
raw_items: list[dict] = []
for content_type_id in ("12", "14", "39"):
    raw_items.extend(_fetch_area_based_list(content_type_id))

raw_ids_by_sigungu: dict[str, set[str]] = {}
for item in raw_items:
    code = item.get("lDongSignguCd", "미상")
    raw_ids_by_sigungu.setdefault(code, set()).add(item.get("contentid"))

# 2) 최종 POI(594개) 기준 — poi_id로 역matching
loader = RealDataLoader()
final_pois = loader.fetch_pois()
final_ids = {poi.poi_id for poi in final_pois}

print(f"원본 poi_id 기준 총 {sum(len(v) for v in raw_ids_by_sigungu.values())}개(중복제거)")
print(f"최종 fetch_pois() 총 {len(final_pois)}개\n")

for code, ids in sorted(raw_ids_by_sigungu.items(), key=lambda x: -len(x[1])):
    final_count = len(ids & final_ids)
    marker = " ← 부산진구" if code == "230" else ""
    print(f"{code}: 원본 {len(ids)}개 → 최종 {final_count}개{marker}")
"""
부산진구 + 인접 5개 구(동구·남구·연제구·동래구·사상구)에 속한 POI 이름 목록을 뽑습니다.
"""
from app.data.loader import RealDataLoader, _fetch_area_based_list

ADJACENT_CODES = {
    "230": "부산진구",
    "170": "동구",
    "290": "남구",
    "470": "연제구",
    "260": "동래구",
    "530": "사상구",
}

raw_items: list[dict] = []
for content_type_id in ("12", "14", "39"):
    raw_items.extend(_fetch_area_based_list(content_type_id))

sigungu_map = {item["contentid"]: item.get("lDongSignguCd", "") for item in raw_items}

loader = RealDataLoader()
all_pois = loader.fetch_pois()

target_pois = [p for p in all_pois if sigungu_map.get(p.poi_id) in ADJACENT_CODES]

print(f"부산진구+인접구 소속 POI: {len(target_pois)}개\n")
for p in target_pois:
    gu = ADJACENT_CODES[sigungu_map[p.poi_id]]
    print(f"[{gu}] {p.name} ({p.category})")
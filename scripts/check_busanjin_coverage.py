"""
부산진구(230) 소속 POI 39개가, busanjin.go.kr 유동인구 격자 데이터에
실제로 얼마나 자주 잡히는지 여러 시간대에 걸쳐 확인합니다.
"""
import httpx
from datetime import datetime

from app.data.loader import RealDataLoader, _fetch_area_based_list
from app.utils.geo import haversine_km

# 1. 부산진구(230) 소속 POI만 골라내기 (원본 TourAPI 응답에서 시군구코드 확인)
raw_items: list[dict] = []
for content_type_id in ("12", "14", "39"):
    raw_items.extend(_fetch_area_based_list(content_type_id))

busanjin_ids = {
    item["contentid"] for item in raw_items
    if item.get("lDongSignguCd") == "230"
}

loader = RealDataLoader()
all_pois = loader.fetch_pois()
busanjin_pois = [p for p in all_pois if p.poi_id in busanjin_ids]
print(f"부산진구 소속 POI: {len(busanjin_pois)}개\n")

# 2. 확인할 시간대 목록 (오늘 날짜 기준, 이미 지난 시각들)
today = datetime.now().strftime("%Y-%m-%d")
check_times = ["09:00", "12:00", "14:00", "16:00"]

client = httpx.Client()
client.get("https://www.busanjin.go.kr/crowdflow/data.do")
headers = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.busanjin.go.kr/crowdflow/data.do",
}

RADIUS_KM = 0.2  # 격자 중심에서 200m 이내면 "매칭"으로 간주

# poi_id -> 몇 번 매칭됐는지 카운트
match_counts = {poi.poi_id: 0 for poi in busanjin_pois}

for t in check_times:
    resp = client.get(
        f"https://www.busanjin.go.kr/crowdflow/dataApiList?stdDate={today}&stdTime={t}",
        headers=headers,
    )
    grids = resp.json()
    print(f"[{t}] 격자 {len(grids)}개 수신")

    for poi in busanjin_pois:
        for grid in grids:
            grid_lat = (grid["lt_y"] + grid["rb_y"]) / 2
            grid_lng = (grid["lt_x"] + grid["rb_x"]) / 2
            dist = haversine_km(poi.lat, poi.lng, grid_lat, grid_lng)
            if dist <= RADIUS_KM:
                match_counts[poi.poi_id] += 1
                break  # 이 POI는 이 시간대에 매칭 완료, 다음 POI로

# 3. 결과 정리
print(f"\n=== 결과 (총 {len(check_times)}개 시간대 중 몇 번 매칭됐는지) ===\n")
for poi in busanjin_pois:
    count = match_counts[poi.poi_id]
    print(f"{poi.name}: {count}/{len(check_times)}회")
    
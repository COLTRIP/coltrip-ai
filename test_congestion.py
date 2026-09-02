"""매칭된 SK poiId 몇 개를 실제 혼잡도 API로 테스트."""
import httpx
import time

APP_KEY = "Q329dEHhFL7Uk2tHdmViL4gm9ozbSS6L3e0CPbEe"

# 카테고리 골고루 섞어서 테스트 (해수욕장, 사찰, 전시시설, 자연공원)
test_cases = [
    ("해운대해수욕장", "152054"),
    ("광안리해수욕장", "152111"),
    ("범어사", "31034"),
    ("해동용궁사", "382199"),
    ("부산박물관", "368107"),
    ("부산현대미술관", "7889439"),
    ("흰여울문화마을", "8332378"),
    ("감천문화마을", "2995132"),
    ("해운대수목원", "8652074"),
    ("을숙도공원", "1443584"),
]

for name, poi_id in test_cases:
    url = f"https://apis.openapi.sk.com/puzzle/place/congestion/rltm/pois/{poi_id}"
    resp = httpx.get(url, headers={"appKey": APP_KEY}, timeout=10)
    data = resp.json()
    has_data = "contents" in data and data["contents"].get("rltm")
    print(f"{name}: {'✅ 데이터 있음' if has_data else '❌ 데이터 없음'} | {resp.status_code}")
    time.sleep(1)  # 호출 제한 방지
"""
한국관광공사 관광지 집중률 API를, 부산 16개 구 각각 tAtsNm 없이 호출해서
부산 전체 관광지의 30일치 집중률 예측을 한 번에 받아옵니다.
"""
import json
import time

import httpx

SERVICE_KEY = "q0Xa310VVT2iKHZxmNmhr50pDHgSG75SWsyO0Uf3NXnzPU9bXbX0YhZ5UMj7h7l8Ep+GE7bPMUX6YWgOIvjFvw=="

BUSAN_SIGUNGU = {
    "26110": "중구", "26140": "서구", "26170": "동구", "26200": "영도구",
    "26230": "부산진구", "26260": "동래구", "26290": "남구", "26320": "북구",
    "26350": "해운대구", "26380": "사하구", "26410": "금정구", "26440": "강서구",
    "26470": "연제구", "26500": "수영구", "26530": "사상구", "26710": "기장군",
}

all_items = []
for signgu_cd, signgu_name in BUSAN_SIGUNGU.items():
    resp = httpx.get(
        "https://apis.data.go.kr/B551011/TatsCnctrRateService/tatsCnctrRatedList",
        params={
            "serviceKey": SERVICE_KEY,
            "numOfRows": 3000,
            "pageNo": 1,
            "MobileOS": "ETC",
            "MobileApp": "COLTRIP",
            "areaCd": "26",
            "signguCd": signgu_cd,
            "_type": "json",
        },
        timeout=15,
    )
    data = resp.json()
    if "response" not in data:
        print(f"⚠️ {signgu_name} 이상 응답: {data}")
        continue
    items = data["response"]["body"]["items"].get("item", [])
    if isinstance(items, dict):
        items = [items]
    all_items.extend(items)
    print(f"{signgu_name}: {len(items)}건 ({len(items)//30}개 관광지)")
    time.sleep(0.5)

with open("app/data/cnctr_rate_data.json", "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False)

print(f"\n총 {len(all_items)}건 저장 완료 (관광지 약 {len(all_items)//30}개)")
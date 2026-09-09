"""
SKT 장소 목록(place/meta/pois)의 나머지(offset 6000~34000)를 이어서 받습니다.
- 429(quota) 방지를 위해 호출 사이 3초 텀
- 빈 응답/이상 응답이 와도 멈추지 않고 재시도 후 계속 진행
"""
import httpx
import time
import json

APP_KEY = "qWAx6OQnON2fGeFPNqG2t9PO8jgDvfIZ1f4gHFnu"
OUTPUT_PATH = "all_pois_first6000.json"

all_items = []
offset = 0
LIMIT = 1000
MAX_RETRIES = 3

while offset < 6000:
    success = False
    for attempt in range(MAX_RETRIES):
        try:
            url = f"https://apis.openapi.sk.com/puzzle/place/meta/pois?offset={offset}&limit={LIMIT}"
            resp = httpx.get(url, headers={"appKey": APP_KEY}, timeout=15)

            if resp.status_code != 200:
                print(f"offset={offset} 시도{attempt+1}: 상태코드 {resp.status_code}, 응답: {resp.text[:200]}")
                time.sleep(5)
                continue

            if not resp.text.strip():
                print(f"offset={offset} 시도{attempt+1}: 빈 응답")
                time.sleep(5)
                continue

            data = resp.json()

            if "contents" not in data:
                print(f"offset={offset} 시도{attempt+1}: contents 없음, 응답: {data}")
                time.sleep(5)
                continue

            items = data["contents"]
            all_items.extend(items)
            print(f"offset={offset}: {len(items)}개 받음 (누적 {len(all_items)}개)")
            success = True
            break

        except Exception as e:
            print(f"offset={offset} 시도{attempt+1}: 예외 발생 - {e}")
            time.sleep(5)

    if not success:
        print(f"offset={offset}: {MAX_RETRIES}번 다 실패, 건너뜁니다.")

    offset += LIMIT
    time.sleep(3)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False)

print(f"\n완료: 총 {len(all_items)}개 저장 -> {OUTPUT_PATH}")
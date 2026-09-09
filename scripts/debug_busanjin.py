"""부산진구 API 원본 응답을 직접 확인 (에러 숨기지 않고 그대로 보기)."""
from datetime import datetime
import httpx

client = httpx.Client(timeout=10)
client.get("https://www.busanjin.go.kr/crowdflow/data.do")

now = datetime.now()
std_date = now.strftime("%Y-%m-%d")
std_time = now.strftime("%H:%M")
print(f"조회 시각: {std_date} {std_time}\n")

resp = client.get(
    "https://www.busanjin.go.kr/crowdflow/dataApiList",
    params={"stdDate": std_date, "stdTime": std_time},
    headers={
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.busanjin.go.kr/crowdflow/data.do",
    },
)
print(f"상태 코드: {resp.status_code}")
print(f"응답 앞부분: {resp.text[:300]}\n")

grids = resp.json()
print(f"격자 개수: {len(grids)}")

# 전포공구길 좌표가 이 중 어디라도 걸리는지 직접 확인
target_lat, target_lng = 35.1586890217, 129.0642539566
for g in grids:
    lat_min, lat_max = sorted([g["lt_y"], g["rb_y"]])
    lng_min, lng_max = sorted([g["lt_x"], g["rb_x"]])
    if lat_min <= target_lat <= lat_max and lng_min <= target_lng <= lng_max:
        print(f"매칭됨! {g}")
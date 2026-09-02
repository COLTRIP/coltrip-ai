"""부산진구 유동인구 API — 다른 시각을 넣었을 때 실제로 값이 달라지는지 확인."""
import httpx
from datetime import datetime, timedelta

client = httpx.Client()
client.get("https://www.busanjin.go.kr/crowdflow/data.do")

headers = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.busanjin.go.kr/crowdflow/data.do",
}

def fetch(dt):
    std_date = dt.strftime("%Y-%m-%d")
    std_time = dt.strftime("%H:%M")
    resp = client.get(
        f"https://www.busanjin.go.kr/crowdflow/dataApiList?stdDate={std_date}&stdTime={std_time}",
        headers=headers,
    )
    return resp.json()

now = datetime.now()
three_hours_ago = now - timedelta(hours=3)

data_now = fetch(now)
data_past = fetch(three_hours_ago)

# 같은 격자(id=4367)의 count가 시간에 따라 다른지 비교
now_val = next((d["count"] for d in data_now if d["id"] == 4367), None)
past_val = next((d["count"] for d in data_past if d["id"] == 4367), None)

print(f"격자 4367 — 지금({now.strftime('%H:%M')}): {now_val}명, 3시간 전({three_hours_ago.strftime('%H:%M')}): {past_val}명")
print(f"전체 격자 수 — 지금: {len(data_now)}개, 3시간 전: {len(data_past)}개")
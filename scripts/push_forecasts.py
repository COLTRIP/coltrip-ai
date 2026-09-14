
"""
관광지 집중률(30일 예측) 데이터를, 백엔드의 새 예측 API로 push합니다.

docs/forecast-api-spec.md 계약을 따릅니다:
  POST /api/internal/quiet-index/forecasts

전송 대상은 594개 전체가 아니라, 실제로 "날짜별로 다른 값"을 가진
관광지 집중률 데이터가 있는 267곳뿐입니다. 나머지 327곳은 진짜 미래
예측 수단이 없어서 보내지 않고, 백엔드 스펙대로 "예측 없음"으로 자연스럽게
추천 목록에서 빠지게 둡니다.

quietIndex = 100 - cnctrRate 로 환산합니다 (집중률이 낮을수록 한적하다는
직관을 그대로 반영한 가장 단순한 공식).

집중률 원본이 "하루 1개 값"이라, 같은 날짜의 24개 시간 슬롯 전부에 같은
값을 넣습니다 — 시간대별 변화를 실제로 아는 게 아니므로 지어내지 않습니다.

modelVersion을 "cnctr-relay-v1"로 정직하게 표기합니다 — AI가 직접 학습한
예측 모델이 아니라, 한국관광공사 집중률 데이터를 그대로 재가공해 전달하는
것이기 때문입니다.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.data.loader import RealDataLoader

BACKEND_URL = "https://api.coltrip.co.kr/api/internal/quiet-index/forecasts"
INTERNAL_API_KEY = "QWE98zD0CGzPdsBykuNru9Nd6fCQAVov8sGSmFjtT1c="  # spots push 때와 동일한 X-Internal-Api-Key 값

CNCTR_DATA_PATH = Path("app/data/cnctr_rate_data.json")
FORECAST_DAYS = 7  # 백엔드 현재 정책(7일). 나중에 30일로 늘어나면 이 값만 변경.
KST = timezone(timedelta(hours=9))


def build_name_to_cnctr() -> dict[str, dict[str, float]]:
    """tAtsNm(부분 매칭용) -> {YYYYMMDD: cnctrRate} 형태로 정리합니다."""
    with open(CNCTR_DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    by_name: dict[str, dict[str, float]] = {}
    for item in raw:
        name = item["tAtsNm"]
        try:
            rate = float(item["cnctrRate"])
        except (KeyError, ValueError):
            continue
        by_name.setdefault(name, {})[item["baseYmd"]] = rate
    return by_name


def find_cnctr_for_poi(poi_name: str, name_to_cnctr: dict) -> dict[str, float] | None:
    """POI 이름과 부분적으로라도 일치하는 tAtsNm의 날짜별 집중률을 찾습니다."""
    poi_norm = poi_name.replace(" ", "").replace("(", "").replace(")", "")
    for tats_nm, dates in name_to_cnctr.items():
        tats_norm = tats_nm.replace(" ", "").replace("(", "").replace(")", "")
        if poi_norm in tats_norm or tats_norm in poi_norm:
            return dates
    return None


def build_forecasts_for_poi(poi_id: str, dates: dict[str, float]) -> list[dict]:
    """이 POI의 향후 FORECAST_DAYS일치 시간별(24슬롯) 예측 레코드를 만듭니다."""
    now_kst = datetime.now(KST)
    start_hour = now_kst.replace(minute=0, second=0, microsecond=0)

    forecasts = []
    for h in range(FORECAST_DAYS * 24 + 1):
        target_at = start_hour + timedelta(hours=h)
        date_key = target_at.strftime("%Y%m%d")
        cnctr_rate = dates.get(date_key)
        if cnctr_rate is None:
            continue  # 이 날짜는 집중률 데이터 범위 밖 (30일 지남 등)

        quiet_index = round(max(0.0, min(100.0, 100 - cnctr_rate)), 2)
        valid_until = target_at + timedelta(hours=1)

        forecasts.append({
            "tourApiContentId": poi_id,
            "targetAt": target_at.isoformat(timespec="seconds"),
            "quietIndex": quiet_index,
            "validUntil": valid_until.isoformat(timespec="seconds"),
        })
    return forecasts


def main():
    name_to_cnctr = build_name_to_cnctr()
    loader = RealDataLoader()
    pois = loader.fetch_pois()

    all_forecasts = []
    matched_count = 0
    for poi in pois:
        dates = find_cnctr_for_poi(poi.name, name_to_cnctr)
        if dates is None:
            continue
        matched_count += 1
        all_forecasts.extend(build_forecasts_for_poi(poi.poi_id, dates))

    print(f"집중률 매칭된 관광지: {matched_count}개")
    print(f"전체 예측 레코드: {len(all_forecasts)}개\n")

    generated_at = datetime.now(KST).isoformat(timespec="seconds")
    client = httpx.Client(timeout=30)
    total_created = 0
    total_updated = 0
    failed_batches = []

    for i in range(0, len(all_forecasts), 1000):
        batch = all_forecasts[i:i + 1000]
        batch_num = i // 1000 + 1
        resp = client.post(
            BACKEND_URL,
            headers={"X-Internal-Api-Key": INTERNAL_API_KEY},
            json={
                "source": "coltrip-ai",
                "modelVersion": "cnctr-relay-v1",
                "generatedAt": generated_at,
                "forecasts": batch,
            },
        )
        if resp.status_code != 200:
            print(f"❌ 배치 {batch_num} 실패: {resp.status_code} - {resp.text[:300]}")
            failed_batches.append(batch_num)
            continue

        data = resp.json()
        created = data.get("created", 0)
        updated = data.get("updated", 0)
        total_created += created
        total_updated += updated
        print(f"배치 {batch_num}: created={created}, updated={updated}")

    print(f"\n=== 결과 ===")
    print(f"총 created: {total_created}, 총 updated: {total_updated}")
    if failed_batches:
        print(f"실패한 배치: {failed_batches} — 재전송 필요")


if __name__ == "__main__":
    main()
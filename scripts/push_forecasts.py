"""
관광지 집중률(30일 예측) 데이터를, 백엔드의 새 예측 API로 push합니다.

docs/forecast-api-spec.md 계약을 따릅니다:
  POST /api/internal/quiet-index/forecasts

전송 대상은 594개 전체가 아니라, 실제로 "날짜별로 다른 값"을 가진
관광지 집중률 데이터가 있는 223곳뿐입니다. 나머지 관광지는 진짜 미래
예측 수단이 없어서 보내지 않고, 백엔드 스펙대로 "예측 없음"으로 자연스럽게
추천 목록에서 빠지게 둡니다.

quietIndex 계산 (2026-09 수정):
  최초엔 quietIndex = 100 - cnctrRate로 단순 계산했으나, 실제 값이
  80점대에 몰려 분별이 안 되는 문제가 있었습니다. 원인은 한국관광공사
  집중률 원본 자체가 대부분 낮은 값에 쏠려있어, 100에서 빼면 자연히
  높은 쪽에 몰리기 때문입니다.

  1차 수정: 전체 기간(7일치)을 통째로 min-max 정규화 → 전체 범위는
  0~100으로 넓어졌지만, "하루만 떼어보면" 그날 안에서는 여전히 좁게
  몰려 보이는 문제가 남았습니다(그날의 실제 장소간 편차가 원래 작아서).

  2차 수정(현재): 날짜별로 따로 min-max 정규화합니다. "그날 하루 안에서
  223곳끼리 비교"가 항상 0~100 전체 폭을 쓰도록 날짜 단위로 정규화 범위를
  나눠 계산합니다. 사용자가 "오늘 어디가 더 한적한지" 비교하는 실제
  사용 맥락에 맞는 방식입니다.

집중률 원본이 "하루 1개 값"이라, 같은 날짜의 24개 시간 슬롯 전부에 같은
값을 넣습니다 — 시간대별 변화를 실제로 아는 게 아니므로 지어내지 않습니다.

modelVersion을 "cnctr-relay-v1"로 정직하게 표기합니다 — AI가 직접 학습한
예측 모델이 아니라, 한국관광공사 집중률 데이터를 그대로 재가공해 전달하는
것이기 때문입니다.
"""
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import httpx
from app.data.skt_congestion import SKT_VERIFIED_POIS, fetch_skt_population
from app.data.loader import RealDataLoader

BACKEND_URL = "https://api.coltrip.co.kr/api/internal/quiet-index/forecasts"
INTERNAL_API_KEY = "QWE98zD0CGzPdsBykuNru9Nd6fCQAVov8sGSmFjtT1c="  # spots push 때와 동일한 X-Internal-Api-Key 값

CNCTR_DATA_PATH = Path("app/data/cnctr_rate_data.json")
FORECAST_DAYS = 7  # 백엔드 현재 정책(7일). 나중에 30일로 늘어나면 이 값만 변경.
KST = timezone(timedelta(hours=9))


# app/models/quiet_index_model.py와 동일한 값 (일관성 유지)
_SKT_LOG_MIN = -6.8929 - (0.9813 - (-6.8929)) * 0.30
_SKT_LOG_MAX = 0.9813 + (0.9813 - (-6.8929)) * 0.30

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
    """
    이 POI의 향후 FORECAST_DAYS일치 시간별(24슬롯) 예측 레코드를 만듭니다.
    quietIndex는 아직 계산 안 하고, 원본 cnctrRate만 담아둡니다
    (날짜별로 모은 뒤 min-max 정규화로 나중에 한꺼번에 계산할 것이라).
    """
    now_kst = datetime.now(KST)
    start_hour = now_kst.replace(minute=0, second=0, microsecond=0)

    records = []
    for h in range(FORECAST_DAYS * 24 + 1):
        target_at = start_hour + timedelta(hours=h)
        date_key = target_at.strftime("%Y%m%d")
        cnctr_rate = dates.get(date_key)
        if cnctr_rate is None:
            continue

        valid_until = target_at + timedelta(hours=1)
        records.append({
            "tourApiContentId": poi_id,
            "targetAt": target_at.isoformat(timespec="seconds"),
            "validUntil": valid_until.isoformat(timespec="seconds"),
            "_cnctr_rate": cnctr_rate,  # 임시 필드, 정규화 후 제거
        })
    return records


def normalize_quiet_index_per_date(all_forecasts: list[dict]) -> None:
    """
    targetAt의 날짜 부분별로, 그날 223곳을 집중률 기준으로 순위 매겨서
    백분위(percentile)를 quietIndex로 씁니다(_cnctr_rate는 제거).

    min-max 대신 순위 기반으로 바꾼 이유: min-max는 "양 끝 두 값"에만
    맞춰서 늘리는 방식이라, 대부분의 값이 원래 좁은 구간에 몰려있으면
    정규화해도 여전히 좁게 나옵니다(실측: 최저 79점). 순위 기반은 분포
    모양과 무관하게 항상 0~100에 고르게 펼쳐지고, 꼴찌는 반드시 0점
    근처가 되도록 보장합니다 — 대체지 추천의 "40점 미만" 절대 기준이
    실제로 의미 있게 작동하려면 이 방식이 맞습니다.
    """
    by_date = defaultdict(list)
    for f in all_forecasts:
        date_key = f["targetAt"][:10]  # "2026-09-14T21:00:00+09:00" -> "2026-09-14"
        by_date[date_key].append(f)

    for date_key, records in sorted(by_date.items()):
        n = len(records)
        # 집중률 오름차순(한적한 순) 정렬 -> 순위가 곧 quietIndex 백분위
        records_sorted = sorted(records, key=lambda r: r["_cnctr_rate"])
        rates = [r["_cnctr_rate"] for r in records_sorted]
        print(f"{date_key}: 집중률 {rates[0]:.2f}~{rates[-1]:.2f} ({n}건)")

        for rank, r in enumerate(records_sorted):
            r.pop("_cnctr_rate")
            if n == 1:
                r["quietIndex"] = 50.0
            else:
                # rank=0(가장 한적함) -> 100점, rank=n-1(가장 붐빔) -> 0점
                percentile = (n - 1 - rank) / (n - 1) * 100
                r["quietIndex"] = round(percentile, 2)

def blend_today_with_skt(all_forecasts: list[dict], pois_by_id: dict) -> None:
    """
    SKT 실시간 대상(18곳)에 한해, '오늘' 날짜의 24개 시간 슬롯만
    TourAPI 집중률 기반 quietIndex와 SKT 실시간 기반 quietIndex를
    평균 내어 보정합니다. SKT 값은 저장하지 않고 이 계산에만 즉시
    사용하고 버립니다 (SK 약관 확인 결과 반영, 2026-09-16).
    """
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    blended_count = 0

    for f in all_forecasts:
        if not f["targetAt"].startswith(today_str):
            continue
        poi_id = f["tourApiContentId"]
        if poi_id not in SKT_VERIFIED_POIS:
            continue

        poi = pois_by_id.get(poi_id)
        if poi is None:
            continue

        skt_population = fetch_skt_population(poi_id, poi.area_m2)
        if skt_population is None:
            continue  # 야간이거나 SKT 호출 실패 시 원래 값 그대로 둠

        # SKT population -> 같은 로그밀도 스케일로 변환해서 quietIndex 계산
        # (app/models/quiet_index_model.py와 동일한 상수 사용)
        density = skt_population / poi.area_m2 if poi.area_m2 > 0 else 0
        log_density = math.log(density + 0.0001)
        span = _SKT_LOG_MAX - _SKT_LOG_MIN
        congestion = max(0.0, min(100.0, (log_density - _SKT_LOG_MIN) / span * 100)) if span > 0 else 50.0
        skt_quiet_index = round(100 - congestion, 2)

        f["quietIndex"] = round((f["quietIndex"] + skt_quiet_index) / 2, 2)
        blended_count += 1

    print(f"SKT 실시간 값과 오늘자 예측 결합: {blended_count}건\n")

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

    normalize_quiet_index_per_date(all_forecasts)
    print()

    pois_by_id = {p.poi_id: p for p in pois}
    blend_today_with_skt(all_forecasts, pois_by_id)

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
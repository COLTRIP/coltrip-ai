"""
한국관광공사 관광지 집중률 방문자 추이 예측 정보 연동 (일 단위, 향후 30일).

부산 16개 구 전체를 tAtsNm 없이 조회해서 미리 받아둔 267개 관광지의 30일치
예측 데이터(cnctr_rate_data.json)를 사용합니다. 저희 POI 이름과 API의 tAtsNm이
완전히 같지 않은 경우가 있어(예: "가야공원" vs "가야공원 / 가야산책공원"),
부분 포함 매칭으로 처리합니다.

집중률(cnctrRate, 0~100)은 "인구수"가 아니라 상대적 비율이므로, 다른 폴백
단계들과 스케일을 맞추기 위해 임시로 area_m2에 곱해 population 근사치를
만듭니다(완벽한 환산은 아니며, 최후 폴백 단계로서의 방향성 신호로 사용).

hour 파라미터는 이 소스에서는 사용하지 않습니다(일 단위 데이터라 시간대
구분이 없음). is_weekend도 사용하지 않고, 그날 날짜 자체의 예측치를 그대로 씁니다.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "cnctr_rate_data.json"

_cnctr_data: list[dict] | None = None
_name_index: dict[str, list[dict]] | None = None


def _load_data() -> list[dict]:
    global _cnctr_data
    if _cnctr_data is None:
        with open(_DATA_PATH, encoding="utf-8") as f:
            _cnctr_data = json.load(f)
    return _cnctr_data


def _build_name_index() -> dict[str, list[dict]]:
    """tAtsNm별로 30일치 레코드를 묶어서 미리 인덱싱합니다."""
    global _name_index
    if _name_index is None:
        _name_index = {}
        for item in _load_data():
            name = item["tAtsNm"]
            _name_index.setdefault(name, []).append(item)
    return _name_index


def _find_matching_records(poi_name: str) -> list[dict] | None:
    """POI 이름과 부분적으로라도 일치하는 tAtsNm의 레코드들을 찾습니다."""
    index = _build_name_index()
    poi_name_norm = poi_name.replace(" ", "").replace("(", "").replace(")", "")

    for tats_nm, records in index.items():
        tats_nm_norm = tats_nm.replace(" ", "").replace("(", "").replace(")", "")
        if poi_name_norm in tats_nm_norm or tats_nm_norm in poi_name_norm:
            return records
    return None


def fetch_cnctr_rate_population(poi_name: str, area_m2: float) -> int | None:
    """
    오늘 날짜 기준 이 POI의 집중률을 찾아 population 근사치로 환산합니다.
    매칭되는 관광지가 없거나 오늘 날짜 데이터가 없으면 None.
    """
    records = _find_matching_records(poi_name)
    if not records:
        return None

    today_str = datetime.now().strftime("%Y%m%d")
    today_record = next((r for r in records if r["baseYmd"] == today_str), None)
    if today_record is None:
        return None

    try:
        cnctr_rate = float(today_record["cnctrRate"])
    except (KeyError, ValueError):
        return None

    # 집중률(0~100)을 면적 대비 임시 인구수로 환산 (TODO: 추후 실측 데이터로 보정)
    return round((cnctr_rate / 100) * area_m2 * 0.1)
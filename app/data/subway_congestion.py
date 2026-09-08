"""
지하철 시간대별 승하차 패턴 기반 유동인구 폴백.

부산교통공사 시간대별 승하차인원(6개월치, 2026-01~06)을 역별+평일/주말+시간대별
평균으로 미리 압축해둔 표(subway_hourly_pattern.csv)와, 전국도시철도역사정보
표준데이터에서 추출한 부산 114개 역 좌표(subway_station_coords.csv)를 사용합니다.

POI 좌표에서 가장 가까운 역이 일정 반경(기본 500m) 이내에 있으면, 그 역의
같은 요일유형·시간대 평균 승하차 인원(승차+하차 평균 합산)을 population으로
사용합니다. 범위 밖이면 None을 반환해 다음 폴백 단계로 넘어가야 합니다.

실시간이 아니라 "과거 6개월 평균 패턴"이라는 점에 유의하세요 — SKT·부산진구처럼
지금 이 순간의 값이 아니라, hour/is_weekend 파라미터로 지정한 시점의 통상적인
패턴을 추정합니다.
"""
from __future__ import annotations

import csv
from pathlib import Path

from app.utils.geo import haversine_km

_STATIONS_PATH = Path(__file__).parent / "subway_station_coords.csv"
_PATTERN_PATH = Path(__file__).parent / "subway_hourly_pattern.csv"

MATCH_RADIUS_KM = 0.5  # 역 반경 500m 이내만 "지하철역 인근"으로 간주

_stations: list[dict] | None = None
_pattern: dict[tuple[str, bool, int], float] | None = None


def _load_stations() -> list[dict]:
    global _stations
    if _stations is None:
        with open(_STATIONS_PATH, encoding="utf-8-sig") as f:
            _stations = [
                {"name": row["station_name"], "lat": float(row["lat"]), "lng": float(row["lng"])}
                for row in csv.DictReader(f)
            ]
    return _stations


def _load_pattern() -> dict[tuple[str, bool, int], float]:
    global _pattern
    if _pattern is None:
        _pattern = {}
        with open(_PATTERN_PATH, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                key = (row["station_name"], row["is_weekend"] == "True", int(row["hour"]))
                _pattern[key] = float(row["avg_count"])
    return _pattern


def _find_nearest_station(lat: float, lng: float) -> tuple[str, float] | None:
    """가장 가까운 역과 그 거리(km)를 반환합니다. 후보가 없으면 None."""
    stations = _load_stations()
    nearest = min(
        stations, key=lambda s: haversine_km(lat, lng, s["lat"], s["lng"])
    )
    dist = haversine_km(lat, lng, nearest["lat"], nearest["lng"])
    return nearest["name"], dist


def fetch_subway_population(lat: float, lng: float, hour: int, is_weekend: bool) -> int | None:
    """
    POI 좌표 기준 반경 500m 이내에 지하철역이 있으면, 그 역의 같은 요일유형·
    시간대 평균 승하차 인원을 population으로 반환합니다. 없으면 None.
    """
    result = _find_nearest_station(lat, lng)
    if result is None:
        return None

    station_name, dist_km = result
    if dist_km > MATCH_RADIUS_KM:
        return None

    pattern = _load_pattern()
    avg_count = pattern.get((station_name, is_weekend, hour))
    if avg_count is None:
        return None

    return round(avg_count)
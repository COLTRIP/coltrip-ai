"""
부산진구청 자체 유동인구 API 연동 (공공와이파이 기반, 1분 단위).

배경 (2026-09 조사):
  - busanjin.go.kr/crowdflow가 공식 Open API로 문서화된 건 아니지만, 브라우저
    개발자도구로 실제 호출 구조를 확인했습니다. 로그인/세션 없이 호출 가능합니다.
  - "부산진구 내 밀집 지역"만 격자 단위로 보여주는 방식이라, 부산진구 소속
    POI라고 해서 항상 격자가 잡히는 건 아닙니다. 실측 결과 전포공구길·서면
    번화가급 POI는 항상 잡히고, 공원·사찰 등 상대적으로 한적한 곳은 거의
    안 잡힙니다(39개 중 9개 정도만 재현성 있게 매칭 확인, 2026-09).
  - 격자에 안 잡히는 POI는 "이 시점에 딱히 안 붐빈다"로 해석하기보다,
    "이 소스로는 측정 불가"로 보고 다음 폴백 단계로 넘기는 것이 안전합니다
    (와이파이 커버리지 자체가 없는 곳일 수 있어 혼동 위험).

캐싱 (2026-09 추가):
  - 이 API는 "현재 순간 밀집 격자 전체 목록"을 한 번에 반환하는 방식이라,
    POI마다 매번 새로 호출할 필요가 없습니다. 처음엔 이걸 놓치고 POI마다
    매번 재호출하도록 짜서, /quiet-index/map(약 595개 POI 순회) 호출 시
    부산진구 서버에 577번 연속 요청이 나가 504 타임아웃이 발생했습니다.
    이제 짧은 TTL(60초)로 격자 목록 자체를 캐싱해서, 같은 호출 흐름 안에서는
    실제로 딱 1번만 외부 API를 부르고 나머지는 로컬 대조만 합니다.

fetch_population()의 hour/is_weekend 파라미터는 이 소스에서는 사용하지 않습니다
(SKT와 마찬가지로 "현재 시각" 기준 실시간 데이터만 제공하기 때문).
"""
from __future__ import annotations

import time
from datetime import datetime

import httpx

BUSANJIN_BASE_URL = "https://www.busanjin.go.kr/crowdflow"
GRID_CACHE_TTL_SECONDS = 60  # 원본이 1분 단위 갱신이라 이 주기에 맞춤

_client: httpx.Client | None = None
_grid_cache: tuple[float, list[dict]] | None = None  # (캐시된 시각, 격자 목록)


def _get_client() -> httpx.Client:
    """세션 쿠키를 재사용하기 위해 클라이언트를 모듈 전역에서 하나만 유지합니다."""
    global _client
    if _client is None:
        _client = httpx.Client(timeout=10)
        _client.get(f"{BUSANJIN_BASE_URL}/data.do")  # 세션 쿠키 발급
    return _client


def _fetch_current_grids() -> list[dict]:
    """
    현재 시각 기준 밀집 격자 전체 목록을 가져옵니다. 60초 이내 재호출 시
    캐시된 목록을 그대로 반환해, 여러 POI를 순회할 때 외부 API를
    반복 호출하지 않도록 합니다.
    """
    global _grid_cache
    now = time.time()
    if _grid_cache is not None and (now - _grid_cache[0]) < GRID_CACHE_TTL_SECONDS:
        return _grid_cache[1]

    now_dt = datetime.now()
    std_date = now_dt.strftime("%Y-%m-%d")
    std_time = now_dt.strftime("%H:%M")

    try:
        client = _get_client()
        resp = client.get(
            f"{BUSANJIN_BASE_URL}/dataApiList",
            params={"stdDate": std_date, "stdTime": std_time},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BUSANJIN_BASE_URL}/data.do",
            },
        )
        resp.raise_for_status()
        grids = resp.json()
    except (httpx.HTTPError, ValueError):
        grids = []

    _grid_cache = (now, grids)
    return grids


def _point_in_grid(lat: float, lng: float, grid: dict) -> bool:
    """POI 좌표가 이 격자(사각형) 범위 안에 있는지 확인합니다."""
    lat_min, lat_max = sorted([grid["lt_y"], grid["rb_y"]])
    lng_min, lng_max = sorted([grid["lt_x"], grid["rb_x"]])
    return lat_min <= lat <= lat_max and lng_min <= lng <= lng_max


def fetch_busanjin_population(lat: float, lng: float) -> int | None:
    """
    부산진구 유동인구 격자 중, 이 좌표를 포함하는 격자가 있으면 그 인구수를 반환합니다.
    격자가 안 잡히면(측정 불가 또는 현재 비혼잡) None을 반환하고,
    호출부에서 다음 폴백 단계로 넘어가야 합니다.
    """
    grids = _fetch_current_grids()

    for grid in grids:
        if _point_in_grid(lat, lng, grid):
            return grid.get("count")

    return None
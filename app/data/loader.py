"""
데이터 로더 추상화 계층.

서비스 코드(app/services/*)는 이 모듈이 제공하는 인터페이스만 바라보고,
실제 데이터가 mock인지 TourAPI 등 실제 API인지는 신경 쓰지 않습니다.

지금 당장은 MockDataLoader만 동작하며, RealDataLoader는 뼈대만
잡아두었습니다. 데이터가 준비되면 아래 두 메서드만 채우면 됩니다.
  - fetch_pois()
  - fetch_population(poi_id, hour, is_weekend)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx
import requests
import time

from app.config import settings
from app.data.category_mapping import map_tourapi_category
from app.data.category_defaults import get_category_defaults
from app.data.mock_data import MOCK_POIS, POI, mock_realtime_population


class BaseDataLoader(ABC):
    @abstractmethod
    def fetch_pois(self) -> list[POI]:
        """전체 관광지(POI) 목록을 반환합니다."""

    @abstractmethod
    def fetch_population(self, poi_id: str, hour: int, is_weekend: bool) -> int:
        """특정 POI의 특정 시점 실시간 인구수를 반환합니다."""


class MockDataLoader(BaseDataLoader):
    def fetch_pois(self) -> list[POI]:
        return MOCK_POIS

    def fetch_population(self, poi_id: str, hour: int, is_weekend: bool) -> int:
        return mock_realtime_population(poi_id, hour, is_weekend)


TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"


def _fetch_area_based_list(content_type_id: str, lcls_systm2: str | None = None) -> list[dict]:
    """
    TourAPI areaBasedList2를 호출해서 부산(lDongRegnCd=26) 관광지 원본 목록을 가져옵니다.
    결과가 많으면 여러 페이지로 나눠져 있어서, 전부 받을 때까지 반복 호출합니다.

    이 서버가 간헐적으로 TLS handshake에서 멈추는 경우가 있어(공공데이터포털
    자체의 알려진 불안정성), 페이지마다 최대 3번까지 재시도합니다.
    """
    items: list[dict] = []
    page_no = 1
    num_of_rows = 100

    while True:
        params = {
            "serviceKey": settings.TOUR_API_KEY,
            "MobileOS": "ETC",
            "MobileApp": "COLTRIP",
            "_type": "json",
            "arrange": "C",
            "numOfRows": num_of_rows,
            "pageNo": page_no,
            "contentTypeId": content_type_id,
            "lDongRegnCd": "26",
        }
        if lcls_systm2:
            params["lclsSystm2"] = lcls_systm2

        resp = None
        for attempt in range(3):
            try:
                resp = requests.get(
                    f"{TOUR_API_BASE_URL}/areaBasedList2", params=params, timeout=15
                )
                resp.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                print(f"  (재시도 {attempt + 1}/3) page {page_no}: {e}")
                time.sleep(2)

        if resp is None:
            raise RuntimeError(f"page {page_no} 3번 재시도 후에도 실패")

        body = resp.json()["response"]["body"]

        raw_items = body["items"]
        page_items = raw_items["item"] if raw_items else []
        if isinstance(page_items, dict):
            page_items = [page_items]

        items.extend(page_items)

        total_count = body["totalCount"]
        if page_no * num_of_rows >= total_count:
            break
        page_no += 1

    return items


class RealDataLoader(BaseDataLoader):
    """
    한국관광공사 TourAPI 기반 실제 데이터 로더.

    fetch_pois()는 areaBasedList2를 호출해서 poi_id/name/category/lat/lng를
    실제 값으로 채웁니다. area_m2, description 등은 아직 데이터 소스가 없어
    임시 기본값으로 채워둔 상태입니다 (코드 내 TODO 참고).

    fetch_population()은 SKT 실시간(18곳) → 부산진구 자체 유동인구 →
    지하철 시간대별 패턴 → 관광지 집중률(일단위) → mock 순서로 폴백합니다.
    """

    _cached_pois: list[POI] | None = None
    _cache_time: float = 0.0
    _CACHE_TTL_SECONDS = 3600  # 1시간 — QuietIndex 배치 주기랑 맞춤

    def fetch_pois(self) -> list[POI]:
        import time
        now = time.time()
        if self._cached_pois is not None and (now - self._cache_time) < self._CACHE_TTL_SECONDS:
            return self._cached_pois

        raw_items: list[dict] = []
        for content_type_id in ("12", "14", "39"):  # 관광지, 문화시설, 음식점(카페)
            raw_items.extend(_fetch_area_based_list(content_type_id))

        pois: list[POI] = []
        seen_ids: set[str] = set()

        for item in raw_items:
            poi_id = item.get("contentid")
            if not poi_id or poi_id in seen_ids:
                continue

            category = map_tourapi_category(
                lcls_systm3=item.get("lclsSystm3", ""),
                lcls_systm2=item.get("lclsSystm2", ""),
            )
            if category is None:
                continue

            try:
                lat = float(item.get("mapy", 0))
                lng = float(item.get("mapx", 0))
            except (TypeError, ValueError):
                continue

            defaults = get_category_defaults(category)
            pois.append(POI(
                poi_id=poi_id,
                name=item.get("title", ""),
                category=category,
                area_m2=defaults["area_m2"],
                lat=lat,
                lng=lng,
                context_tags=[],
                description="",
                has_indoor=defaults["has_indoor"],
                vegetation_score=defaults["vegetation_score"],
            ))
            seen_ids.add(poi_id)

        self.__class__._cached_pois = pois
        self.__class__._cache_time = time.time()
        return pois

    def fetch_population(self, poi_id: str, hour: int, is_weekend: bool) -> int:
        from app.data.skt_congestion import fetch_skt_population
        from app.data.busanjin_congestion import fetch_busanjin_population
        from app.data.subway_congestion import fetch_subway_population
        from app.data.cnctr_rate_congestion import fetch_cnctr_rate_population
        from app.data.mock_data import mock_realtime_population
        from app.data.congestion_logger import log_observation

        pois = self.fetch_pois()
        poi = next((p for p in pois if p.poi_id == poi_id), None)
        if poi is None:
            raise ValueError(f"존재하지 않는 poi_id: {poi_id}")

        skt_result = fetch_skt_population(poi_id, poi.area_m2)
        if skt_result is not None:
            log_observation(poi_id, "skt", skt_result)
            return skt_result

        busanjin_result = fetch_busanjin_population(poi.lat, poi.lng)
        if busanjin_result is not None:
            log_observation(poi_id, "busanjin", busanjin_result)
            return busanjin_result

        subway_result = fetch_subway_population(poi.lat, poi.lng, hour, is_weekend)
        if subway_result is not None:
            return subway_result

        cnctr_result = fetch_cnctr_rate_population(poi.name, poi.area_m2)
        if cnctr_result is not None:
            return cnctr_result

        return mock_realtime_population(poi_id, hour, is_weekend)
    
def get_data_loader() -> BaseDataLoader:
    if settings.DATA_SOURCE == "real":
        return RealDataLoader()
    return MockDataLoader()
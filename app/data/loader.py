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

from app.config import settings
from app.data.category_mapping import map_tourapi_category
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

        resp = httpx.get(f"{TOUR_API_BASE_URL}/areaBasedList2", params=params, timeout=10)
        resp.raise_for_status()
        body = resp.json()["response"]["body"]

        raw_items = body["items"]
        page_items = raw_items["item"] if raw_items else []
        if isinstance(page_items, dict):
            # 결과가 1건일 때 TourAPI가 리스트가 아니라 딕셔너리 하나로 줄 때가 있어서 보정
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
    실제 값으로 채웁니다. area_m2, noise_sensitivity, description 등은
    아직 데이터 소스가 없어 임시 기본값으로 채워둔 상태입니다 (코드 내 TODO 참고).

    fetch_population()은 아직 미구현 — 유동인구 데이터 소스 확정 후 구현 예정
    (지하철 시간대별 승하차, 도로 소통정보 등 조합 검토 중).
    """

    def fetch_pois(self) -> list[POI]:
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
                continue  # 매핑 안 되는 카테고리는 일단 제외

            try:
                lat = float(item.get("mapy", 0))
                lng = float(item.get("mapx", 0))
            except (TypeError, ValueError):
                continue

            pois.append(POI(
                poi_id=poi_id,
                name=item.get("title", ""),
                category=category,
                area_m2=10000.0,  # TODO: 상가업소정보 API 연동 전까지 임시 기본값
                noise_sensitivity=1.0,  # TODO: 카테고리별 기본값 표 필요
                lat=lat,
                lng=lng,
                context_tags=[],
                description="",  # TODO: detailCommon2로 별도 스크립트에서 채울 예정
                has_indoor=False,  # TODO
                vegetation_score=0.3,  # TODO
            ))
            seen_ids.add(poi_id)

        return pois

    def fetch_population(self, poi_id: str, hour: int, is_weekend: bool) -> int:
        raise NotImplementedError("실제 TourAPI 연동 후 구현 예정")


def get_data_loader() -> BaseDataLoader:
    if settings.DATA_SOURCE == "real":
        return RealDataLoader()
    return MockDataLoader()
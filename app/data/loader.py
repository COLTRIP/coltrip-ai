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

from app.config import settings
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


class RealDataLoader(BaseDataLoader):
    """
    TODO(반기태/최지원): 실제 데이터 연동 시 구현.

    - fetch_pois(): 한국관광공사 TourAPI(관광지 기본정보) +
      공공데이터포털 상가업소정보(면적) 조인 결과를 POI 리스트로 변환
    - fetch_population(): TourAPI 혼잡도(5단계) 또는
      부산시 시간대·행정동별 유동인구 데이터를 조회해 인구수로 환산

    주의: POI dataclass의 필드(특히 noise_sensitivity, context_tags,
    vegetation_score)는 공공데이터에 없는 값이라 별도 기준표를 만들어
    카테고리별로 매핑해줘야 합니다. (문서의 "사찰 1.5 / 해수욕장 0.8" 예시 참고)
    """

    def fetch_pois(self) -> list[POI]:
        raise NotImplementedError("실제 TourAPI 연동 후 구현 예정")

    def fetch_population(self, poi_id: str, hour: int, is_weekend: bool) -> int:
        raise NotImplementedError("실제 TourAPI 연동 후 구현 예정")


def get_data_loader() -> BaseDataLoader:
    if settings.DATA_SOURCE == "real":
        return RealDataLoader()
    return MockDataLoader()

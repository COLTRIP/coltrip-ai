from __future__ import annotations

from app.data.loader import get_data_loader
from app.data.mock_data import POI
from app.models.quiet_index_model import QuietIndexModel

_loader = get_data_loader()

# 앱 전역에서 하나의 모델 인스턴스를 재사용 (요청마다 재학습하지 않도록)
_quiet_index_model = QuietIndexModel()
_quiet_index_model.fit_synthetic()


def _get_poi_or_raise(poi_id: str) -> POI:
    for poi in _loader.fetch_pois():
        if poi.poi_id == poi_id:
            return poi
    raise ValueError(f"존재하지 않는 poi_id: {poi_id}")


def get_quiet_index(poi_id: str, hour: int, is_weekend: bool) -> tuple[POI, int, float]:
    """단일 POI의 고요 지수를 계산합니다. (poi, population, quiet_index) 반환."""
    poi = _get_poi_or_raise(poi_id)
    population = _loader.fetch_population(poi_id, hour, is_weekend)
    quiet_index = _quiet_index_model.predict_quiet_index(
        population=population,
        area_m2=poi.area_m2,
        category=poi.category,
        hour=hour,
        is_weekend=is_weekend,
        noise_sensitivity=poi.noise_sensitivity,
    )
    return poi, population, quiet_index


def get_all_quiet_indices(hour: int, is_weekend: bool) -> list[tuple[POI, int, float]]:
    """전체 POI에 대해 고요 지수를 일괄 계산합니다. (지도 매핑, 추천 등에서 재사용)"""
    results = []
    for poi in _loader.fetch_pois():
        population = _loader.fetch_population(poi.poi_id, hour, is_weekend)
        quiet_index = _quiet_index_model.predict_quiet_index(
            population=population,
            area_m2=poi.area_m2,
            category=poi.category,
            hour=hour,
            is_weekend=is_weekend,
            noise_sensitivity=poi.noise_sensitivity,
        )
        results.append((poi, population, quiet_index))
    return results

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.schemas import QuietIndexMapItem, QuietIndexRequest, QuietIndexResponse
from app.services.quiet_index_service import get_all_quiet_indices, get_quiet_index

router = APIRouter(prefix="/quiet-index", tags=["quiet-index"])


@router.post("", response_model=QuietIndexResponse)
def read_quiet_index(payload: QuietIndexRequest):
    try:
        poi, population, quiet_index = get_quiet_index(
            payload.poi_id, payload.hour, payload.is_weekend
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return QuietIndexResponse(
        poi_id=poi.poi_id, name=poi.name, population=population, quiet_index=quiet_index
    )


@router.get("/map", response_model=list[QuietIndexMapItem])
def read_all_quiet_indices(hour: int = 12, is_weekend: bool = False):
    """지도 매핑용: 전체 POI의 고요 지수를 한 번에 반환 (1단계 기능)."""
    results = get_all_quiet_indices(hour, is_weekend)
    return [
        QuietIndexMapItem(
            poi_id=poi.poi_id, name=poi.name, lat=poi.lat, lng=poi.lng, quiet_index=quiet_index
        )
        for poi, _population, quiet_index in results
    ]
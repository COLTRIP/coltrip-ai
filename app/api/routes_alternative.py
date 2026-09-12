from __future__ import annotations

from fastapi import APIRouter

from app.schemas.schemas import AlternativeRequest, AlternativeResponse
from app.services.nudge_service import get_alternatives_if_needed

router = APIRouter(prefix="/alternative", tags=["alternative"])


@router.post("", response_model=AlternativeResponse)
def get_alternative(payload: AlternativeRequest):
    """혼잡 시 대체 장소 추천 (3단계 기능, Nudge Engine)."""
    result = get_alternatives_if_needed(
        payload.poi_id, payload.hour, payload.is_weekend, payload.baseline_quiet_index)
    return AlternativeResponse(**result)

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.schemas import RecommendRequest, RecommendResponse
from app.services.context_service import recommend_by_context

router = APIRouter(prefix="/recommend", tags=["recommend"])


@router.post("", response_model=RecommendResponse)
def recommend(payload: RecommendRequest):
    """감성 맥락 기반 정적 장소 추천 (2단계 기능)."""
    results = recommend_by_context(
        mood=payload.mood,
        purpose=payload.purpose,
        hour=payload.hour,
        is_weekend=payload.is_weekend,
    )
    return RecommendResponse(results=results)

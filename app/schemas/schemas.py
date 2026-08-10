from __future__ import annotations

from pydantic import BaseModel, Field


class QuietIndexRequest(BaseModel):
    poi_id: str = Field(..., examples=["POI001"])
    hour: int = Field(..., ge=0, le=23)
    is_weekend: bool = False


class QuietIndexResponse(BaseModel):
    poi_id: str
    name: str
    population: int
    quiet_index: float


class RecommendRequest(BaseModel):
    mood: str = Field(..., description="인문적 | 자연적")
    purpose: str = Field(..., description="예: 사유, 명상, 산책, 독서")
    hour: int = Field(12, ge=0, le=23)
    is_weekend: bool = False
    natural_sound_mode: bool = False
    wind_speed_ms: float | None = None


class RecommendedPlace(BaseModel):
    poi_id: str
    name: str
    quiet_index: float
    context_match_score: float
    natural_sound_score: float | None = None


class RecommendResponse(BaseModel):
    results: list[RecommendedPlace]


class AlternativeRequest(BaseModel):
    poi_id: str
    hour: int = Field(12, ge=0, le=23)
    is_weekend: bool = False


class AlternativePlace(BaseModel):
    poi_id: str
    name: str
    quiet_index: float
    distance_km: float
    score: float


class AlternativeResponse(BaseModel):
    triggered: bool
    target_quiet_index: float
    alternatives: list[AlternativePlace]

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """
    Python 코드에서는 snake_case를 그대로 쓰되, 실제 JSON 요청/응답은
    camelCase로 주고받기 위한 공통 베이스 클래스.
    백엔드(Spring/Kotlin)가 관례적으로 camelCase를 쓰기 때문에 맞춤 (2026-09).
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # camelCase, snake_case 둘 다 요청으로 받아줌 (호환성)
    )


class QuietIndexRequest(CamelModel):
    poi_id: str = Field(..., examples=["POI001"])
    hour: int = Field(..., ge=0, le=23)
    is_weekend: bool = False


class QuietIndexResponse(CamelModel):
    poi_id: str
    name: str
    population: int
    quiet_index: float


class RecommendRequest(CamelModel):
    mood: str = Field(..., description="COZY | NATURAL | URBAN | VINTAGE | EXOTIC | VIBRANT | SENSORY | TRANQUIL")
    purpose: str = Field(..., description="예: 사유, 명상, 산책, 독서")
    hour: int = Field(12, ge=0, le=23)
    is_weekend: bool = False
    


class RecommendedPlace(CamelModel):
    poi_id: str
    name: str
    quiet_index: float
    context_match_score: float



class RecommendResponse(CamelModel):
    results: list[RecommendedPlace]


class AlternativeRequest(CamelModel):
    poi_id: str
    hour: int = Field(12, ge=0, le=23)
    is_weekend: bool = False
    baseline_quiet_index: float | None = Field(
        None, description="방문 시작 시점의 고요 지수. 있으면 상대 기준(15 이상 하락) 트리거도 함께 검사"
    )


class AlternativePlace(CamelModel):
    poi_id: str
    name: str
    quiet_index: float
    distance_km: float
    score: float
    recommend_reason: str


class AlternativeResponse(CamelModel):
    triggered: bool
    target_quiet_index: float
    alternatives: list[AlternativePlace]
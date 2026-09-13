from __future__ import annotations

from fastapi import Depends, FastAPI

from app.api import routes_alternative, routes_quiet_index, routes_recommend
from app.auth import verify_api_key

app = FastAPI(
    title="COLTRIP AI Engine",
    description="콜트립 AI 파트: 고요 지수 / 감성 맥락 추천 / 대체 장소 추천(Nudge Engine)",
    version="0.1.0",
)

@app.on_event("startup")
def warmup_embeddings():
    """
    서버 시작 시 모든 POI 설명 문장을 미리 임베딩해서 캐시를 채워둡니다.
    안 하면 첫 /recommend·/alternative 요청이 594개를 그 자리에서 전부 계산하느라
    504 타임아웃이 날 수 있습니다 (SKT·부산진구 등 외부 API는 안 건드리므로
    quota 걱정 없이 안전합니다).
    """
    from app.data.loader import get_data_loader
    from app.models.embedding_model import embed_text

    loader = get_data_loader()
    for poi in loader.fetch_pois():
        if poi.description:
            embed_text(poi.description)

app.include_router(routes_quiet_index.router, dependencies=[Depends(verify_api_key)])
app.include_router(routes_recommend.router, dependencies=[Depends(verify_api_key)])
app.include_router(routes_alternative.router, dependencies=[Depends(verify_api_key)])


@app.get("/health")
def health_check():
    return {"status": "ok"}
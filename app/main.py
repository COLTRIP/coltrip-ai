from __future__ import annotations

from fastapi import Depends, FastAPI

from app.api import routes_alternative, routes_quiet_index, routes_recommend
from app.auth import verify_api_key

app = FastAPI(
    title="COLTRIP AI Engine",
    description="콜트립 AI 파트: 고요 지수 / 감성 맥락 추천 / 대체 장소 추천(Nudge Engine)",
    version="0.1.0",
)

app.include_router(routes_quiet_index.router, dependencies=[Depends(verify_api_key)])
app.include_router(routes_recommend.router, dependencies=[Depends(verify_api_key)])
app.include_router(routes_alternative.router, dependencies=[Depends(verify_api_key)])


@app.get("/health")
def health_check():
    return {"status": "ok"}
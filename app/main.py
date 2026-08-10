from __future__ import annotations

from fastapi import FastAPI

from app.api import routes_alternative, routes_quiet_index, routes_recommend

app = FastAPI(
    title="COLTRIP AI Engine",
    description="콜트립 AI 파트: 고요 지수 / 감성 맥락 추천 / 대체 장소 추천(Nudge Engine)",
    version="0.1.0",
)

app.include_router(routes_quiet_index.router)
app.include_router(routes_recommend.router)
app.include_router(routes_alternative.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

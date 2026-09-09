"""
전역 설정.

DATA_SOURCE 값 하나로 mock ↔ 실제 API 데이터 소스를 전환합니다.
반기태(데이터/AI 연동 백엔드) 파트에서 TourAPI 연동을 붙일 때는
"mock"을 "real"로 바꾸고 app/data/loader.py의 RealDataLoader만
구현하면 나머지 서비스/모델 코드는 그대로 재사용됩니다.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # "mock" | "real"
    DATA_SOURCE: str = os.getenv("DATA_SOURCE", "mock")

    # 추후 실제 연동 시 사용할 키 (지금은 비어 있어도 mock 모드 동작에 문제 없음)
    TOUR_API_KEY: str = os.getenv("TOUR_API_KEY", "")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    # 지도/좌표 정제(Kakao Local API)는 팀 결정에 따라 사용하지 않음.
    # 좌표 정제는 백엔드가 네이버 클라우드 플랫폼(NCP) Geocoding으로 전담 처리.

    # 감성 맥락 매칭(2번 기능)은 로컬 오픈소스 임베딩 모델(jhgan/ko-sroberta-multitask)을
    # 사용하므로 별도 API 키가 필요 없음. (app/models/embedding_model.py 참고)

    # 고요 지수 임계값 (Nudge Engine 트리거 기준, 문서의 Threshold_Value)
    QUIET_INDEX_ALERT_THRESHOLD: float = float(
        os.getenv("QUIET_INDEX_ALERT_THRESHOLD", "40")
    )

    MODEL_DIR: str = os.getenv("MODEL_DIR", "app/models/artifacts")

    SKT_APP_KEY: str = os.getenv("SKT_APP_KEY", "")


settings = Settings()

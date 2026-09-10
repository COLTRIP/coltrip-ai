"""
AI 서버 API 인증.

백엔드가 이 AI 서버를 호출할 때, 요청 헤더에 X-API-Key로 사전에 공유된
비밀 키를 담아 보내야 합니다. 이 키는 .env의 AI_SERVER_API_KEY와
비교되며, 일치하지 않으면 401을 반환합니다.
"""
from fastapi import Header, HTTPException, status

from app.config import settings


def verify_api_key(x_api_key: str = Header(...)) -> None:
    if not settings.AI_SERVER_API_KEY:
        # 키 자체가 설정 안 된 로컬 개발 환경에서는 인증을 건너뜁니다.
        return
    if x_api_key != settings.AI_SERVER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API 키입니다.",
        )
"""
정적의 세분화 (Contextual Silence) - 로컬 임베딩 기반 감성 맥락 매칭.

팀 결정: 키워드 매칭 대신, 로컬에서 동작하는 오픈소스 한국어 문장 임베딩
모델(jhgan/ko-sroberta-multitask, sentence-transformers)을 사용합니다.

이 방식을 선택한 이유:
  - API 키/비용이 전혀 들지 않고, 호출 횟수 제한이 없음
  - 외부 API 장애와 무관하게 동작 (완전 로컬 추론)
  - "조용한/고즈넉한/정숙한"처럼 표현이 달라도 의미가 비슷하면 매칭됨
    (키워드 정확히 일치해야만 하는 기존 방식의 한계를 해결)

주의:
  - 최초 실행 시 HuggingFace Hub에서 모델(~440MB)을 자동 다운로드합니다.
    인터넷이 차단된 환경(사내망, 일부 CI/샌드박스 등)에서는 다운로드가
    실패할 수 있으니, 배포 서버에 인터넷 접근이 되는지 미리 확인하세요.
  - 처음 모델을 로드할 때 몇 초 정도 걸립니다 (이후 요청은 캐시된 모델 재사용).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

_MODEL_NAME = "jhgan/ko-sroberta-multitask"
_model = None


def _get_model():
    """모델을 최초 1회만 로드하는 lazy singleton."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_MODEL_NAME)
    return _model


@lru_cache(maxsize=512)
def embed_text(text: str) -> tuple:
    """
    문장을 임베딩 벡터로 변환.
    lru_cache로 같은 문장은 재계산하지 않고 캐시된 벡터를 재사용합니다.
    (POI 설명은 고정 문장이라 캐시 효율이 특히 좋음)
    """
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return tuple(float(x) for x in vector)


def cosine_similarity(vec_a, vec_b) -> float:
    a = np.asarray(vec_a)
    b = np.asarray(vec_b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


# 사용자가 고르는 고정 옵션(드롭다운)을 자연어 쿼리 문장으로 변환하기 위한 매핑.
# 자유 텍스트 입력이 아니라 정해진 선택지이므로, 이 정도 하드코딩으로 충분함.
_MOOD_PHRASES = {
    "인문적": "고즈넉하고 사유적인 인문학적 분위기",
    "자연적": "자연 속에서 탁 트인 개방감 있는 분위기",
}


def build_query_sentence(mood: str, purpose: str) -> str:
    mood_phrase = _MOOD_PHRASES.get(mood, mood)
    return f"{mood_phrase}에서 {purpose} 하기 좋은 장소"


def matches_user_context(poi_description: str, mood: str, purpose: str) -> float:
    """
    사용자가 선택한 분위기(mood) + 목적(purpose) 조합과 POI 설명 문장의
    의미적 유사도를 0~1 사이 점수로 반환합니다.
    """
    if not poi_description:
        return 0.0
    query_vec = embed_text(build_query_sentence(mood, purpose))
    poi_vec = embed_text(poi_description)
    sim = cosine_similarity(query_vec, poi_vec)
    return round(max(0.0, min(1.0, sim)), 3)


def natural_sound_score(wind_speed_ms: float, vegetation_score: float) -> float:
    """
    '자연의 소리' 모드용 환경 동기화 로직 (임베딩과 무관, 기존 규칙 유지).
    문서 조건: "풍속 3~5m/s + 식생 데이터(숲) = 잎소리 ASMR 최상"
    """
    if 3.0 <= wind_speed_ms <= 5.0:
        wind_score = 1.0
    else:
        distance = min(abs(wind_speed_ms - 3.0), abs(wind_speed_ms - 5.0))
        wind_score = max(0.0, 1.0 - distance / 5.0)

    return round(wind_score * 0.6 + vegetation_score * 0.4, 2)

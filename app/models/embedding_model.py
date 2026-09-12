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
# 여행감성 8종 최종 확정안 반영 (2026-09).
_MOOD_PHRASES = {
    "COZY": "아늑하고 편안하게 머물 수 있는",
    "NATURAL": "자연 속 싱그러운 풍경이 느껴지는",
    "URBAN": "세련되고 도시적인 분위기의",
    "VINTAGE": "낡고 오래된 정취가 느껴지는 빈티지한",
    "EXOTIC": "낯설고 이색적인 이국적 분위기의",
    "VIBRANT": "생동감 있고 활기찬 분위기의",
    "SENSORY": "오감을 자극하는 감각적인",
    "TRANQUIL": "조용하고 잔잔하게 마음이 가라앉는 고요한",
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


# 여행감성 8종 각각을 대표하는 쿼리 문장. get_mode_fit_vector()에서
# POI 설명과의 유사도를 재는 기준으로 사용됩니다.
# 반환 순서(딕셔너리 삽입 순서)가 get_mode_fit_vector()의 반환 벡터 순서를 결정합니다.
MODE_QUERIES = {
    "COZY": "아늑하고 편안하게 머물 수 있는 장소",
    "NATURAL": "자연 속 싱그러운 풍경이 느껴지는 장소",
    "URBAN": "세련되고 도시적인 분위기의 장소",
    "VINTAGE": "낡고 오래된 정취가 느껴지는 빈티지한 장소",
    "EXOTIC": "낯설고 이색적인 이국적 분위기의 장소",
    "VIBRANT": "생동감 있고 활기찬 분위기의 장소",
    "SENSORY": "오감을 자극하는 감각적인 장소",
    "TRANQUIL": "조용하고 잔잔하게 마음이 가라앉는 고요한 장소",
}


def get_mode_fit_vector(poi_description: str) -> list[float]:
    """
    POI 설명 문장이 8개 여행감성 각각과 얼마나 어울리는지 계산합니다.
    반환 순서: [COZY, NATURAL, URBAN, VINTAGE, EXOTIC, VIBRANT, SENSORY, TRANQUIL]

    대체지 추천(nudge_engine.py)에서 "카테고리는 비슷한데 활동 궁합은 안 맞는"
    후보를 걸러내기 위해 사용합니다.
    """
    if not poi_description:
        return [0.0] * 8

    poi_vec = embed_text(poi_description)
    scores = []
    for query in MODE_QUERIES.values():
        query_vec = embed_text(query)
        sim = cosine_similarity(poi_vec, query_vec)
        scores.append(round(max(0.0, min(1.0, sim)), 3))
    return scores
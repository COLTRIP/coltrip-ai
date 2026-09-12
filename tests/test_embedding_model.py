import pytest

from app.models.embedding_model import (
    build_query_sentence,
    cosine_similarity,
)


def test_cosine_similarity_identical_vectors():
    v = (1.0, 0.0, 0.0)
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    a = (1.0, 0.0)
    b = (0.0, 1.0)
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    assert cosine_similarity((0, 0, 0), (1, 2, 3)) == 0.0


def test_build_query_sentence_contains_purpose():
    sentence = build_query_sentence("TRANQUIL", "사유")
    assert "사유" in sentence


@pytest.mark.skipif(
    True,  # 네트워크 차단 환경(예: 이 프로젝트의 개발 샌드박스)에서는 항상 skip
    reason="HuggingFace Hub 접근이 필요한 통합 테스트. 인터넷이 되는 환경에서 skipif 조건을 지우고 실행하세요.",
)
def test_matches_user_context_real_model():
    """
    실제 임베딩 모델을 다운로드해 의미적 유사도가 그럴듯한지 확인하는 통합 테스트.
    로컬(인터넷 되는) 환경에서 위 skipif의 True를 False로 바꾸고 실행해보세요.
    """
    from app.models.embedding_model import matches_user_context

    temple_desc = "울창한 숲 속에 자리한 고즈넉한 산사로, 걸으며 마음을 가라앉히고 조용히 사유하기 좋은 공간이다."
    beach_desc = "부산을 대표하는 번화한 해수욕장으로, 넓은 백사장에서 파도 소리를 들으며 개방감을 느낄 수 있다."

    temple_score = matches_user_context(temple_desc, "TRANQUIL", "사유")
    beach_score = matches_user_context(beach_desc, "TRANQUIL", "사유")

    # "고요함 + 사유" 쿼리는 사찰 설명과 더 가까워야 함
    assert temple_score > beach_score
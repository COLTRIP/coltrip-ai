from __future__ import annotations

# TourAPI의 lclsSystm3(가장 세부 분류) 코드 -> 우리 AI 카테고리
LCLS_SYSTM3_TO_CATEGORY = {
    "HS030100": "사찰",       # 불교
    "NA020900": "해수욕장",    # 해변, 해수욕장
    "VE070600": "미술관",     # 미술관/화랑
    "VE040100": "골목",       # 골목길, 문화거리
    "FD050100": "카페",       # 카페
    "HS010400": "역사문화공간",  # 고택
    "HS010700": "역사문화공간",  # 사적지
    "HS010600": "역사문화공간",  # 민속마을
}

# lclsSystm3에 없으면, lclsSystm2 앞 4글자만 보고 폭넓게 판단
LCLS_SYSTM2_PREFIX_TO_CATEGORY = {
    "NA04": "공원",  # 자연공원류
    "VE03": "공원",  # 도시공원류
}

def map_tourapi_category(
    lcls_systm3: str = "", lcls_systm2: str = "", content_type_id: str = ""
) -> str | None:
    """
    TourAPI 분류 코드를 AI의 7개 카테고리 중 하나로 매핑합니다.
    매핑 실패 시 None을 반환합니다.
    """
    if lcls_systm3 in LCLS_SYSTM3_TO_CATEGORY:
        return LCLS_SYSTM3_TO_CATEGORY[lcls_systm3]

    prefix = lcls_systm2[:4] if lcls_systm2 else ""
    if prefix in LCLS_SYSTM2_PREFIX_TO_CATEGORY:
        return LCLS_SYSTM2_PREFIX_TO_CATEGORY[prefix]

    return None
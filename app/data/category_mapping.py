from __future__ import annotations

# 소분류(lclsSystm3) 특별 처리 — 해수욕장만 NA02 그룹에서 분리
LCLS_SYSTM3_TO_CATEGORY: dict[str, str] = {
    "NA020900": "해수욕장",
    "VE090300": "도서관",
    "VE120100": "서점",
}

# 중분류(lclsSystm2) -> 카테고리. TourAPI 중분류명을 그대로 사용.
LCLS_SYSTM2_TO_CATEGORY: dict[str, str] = {
    "EX01": "전통체험",
    "EX02": "공예체험",
    "EX03": "농산어촌체험",
    "EX04": "산사체험",
    "EX05": "웰니스관광",
    "EX06": "산업관광",
    "EX07": "기타체험",
    "HS01": "역사유적지",
    "HS02": "역사유물",
    "HS03": "종교성지",
    "HS04": "안보관광지",
    "NA01": "자연경관(산)",
    "NA02": "자연경관(하천‧해양)",  # NA020900(해수욕장)만 위에서 먼저 걸러짐
    "NA03": "자연생태",
    "NA04": "자연공원",
    "NA05": "기타자연관광",
    "VE01": "랜드마크관광",
    "VE02": "테마공원",
    "VE03": "도시공원",
    "VE04": "도시지역문화관광",
    "VE05": "복합관광시설",
    "VE06": "공연시설",
    "VE07": "전시시설",
    "VE08": "행사시설",
    "VE09": "교육시설",
    "VE12": "기타문화관광지",
    "FD05": "카페",
}


def map_tourapi_category(lcls_systm3: str = "", lcls_systm2: str = "") -> str | None:
    """
    TourAPI 분류 코드를 AI 카테고리로 매핑합니다.
    lclsSystm3(소분류)에서 먼저 특별 처리(해수욕장)를 확인하고,
    없으면 lclsSystm2(중분류)로 폭넓게 판단합니다.
    """
    if lcls_systm3 in LCLS_SYSTM3_TO_CATEGORY:
        return LCLS_SYSTM3_TO_CATEGORY[lcls_systm3]
    return LCLS_SYSTM2_TO_CATEGORY.get(lcls_systm2)

def test_library_and_bookstore_special_case():
    assert map_tourapi_category(lcls_systm3="VE090300", lcls_systm2="VE09") == "도서관"
    assert map_tourapi_category(lcls_systm3="VE120100", lcls_systm2="VE12") == "서점"


def test_ve09_sibling_not_library():
    # 같은 VE09 그룹이어도 도서관이 아니면 "교육시설"로
    assert map_tourapi_category(lcls_systm3="VE090600", lcls_systm2="VE09") == "교육시설"
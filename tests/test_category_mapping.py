from app.data.category_mapping import map_tourapi_category


def test_beach_special_case():
    # 해수욕장은 NA02 그룹에서 분리된 특별 케이스
    assert map_tourapi_category(lcls_systm3="NA020900", lcls_systm2="NA02") == "해수욕장"


def test_na02_sibling_not_beach():
    # 같은 NA02 그룹이어도 해변이 아니면 "자연경관(하천‧해양)"으로
    assert map_tourapi_category(lcls_systm3="NA020800", lcls_systm2="NA02") == "자연경관(하천‧해양)"


def test_lcls_systm2_direct_mappings():
    assert map_tourapi_category(lcls_systm3="HS030100", lcls_systm2="HS03") == "종교성지"
    assert map_tourapi_category(lcls_systm3="HS010400", lcls_systm2="HS01") == "역사유적지"
    assert map_tourapi_category(lcls_systm3="NA040600", lcls_systm2="NA04") == "자연공원"
    assert map_tourapi_category(lcls_systm3="VE040100", lcls_systm2="VE04") == "도시지역문화관광"
    assert map_tourapi_category(lcls_systm3="FD050100", lcls_systm2="FD05") == "카페"


def test_unknown_returns_none():
    assert map_tourapi_category(lcls_systm3="ZZ999999", lcls_systm2="ZZ99") is None
    assert map_tourapi_category() is None
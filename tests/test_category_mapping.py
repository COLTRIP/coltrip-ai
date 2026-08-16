from app.data.category_mapping import map_tourapi_category


def test_direct_lcls_systm3_match():
    assert map_tourapi_category(lcls_systm3="HS030100") == "사찰"


def test_history_culture_space_mapping():
    assert map_tourapi_category(lcls_systm3="HS010400") == "역사문화공간"
    assert map_tourapi_category(lcls_systm3="HS010700") == "역사문화공간"
    assert map_tourapi_category(lcls_systm3="HS010600") == "역사문화공간"


def test_park_prefix_fallback():
    assert map_tourapi_category(lcls_systm3="NA040600", lcls_systm2="NA04") == "공원"
    assert map_tourapi_category(lcls_systm3="VE030100", lcls_systm2="VE03") == "공원"


def test_unknown_returns_none():
    assert map_tourapi_category(lcls_systm3="ZZ999999", lcls_systm2="ZZ99") is None
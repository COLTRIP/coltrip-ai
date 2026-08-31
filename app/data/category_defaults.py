"""
카테고리별 면적·실내여부·식생점수 기본값.

RealDataLoader가 TourAPI에서 못 가져오는 필드를 채울 때 사용하는
임시 기본값 표입니다. category_codes.py의 30개 카테고리와
정확히 이름이 일치해야 합니다.

값의 근거: 해당 카테고리의 일반적인 특성을 참고해 임의로 추정한 값입니다
(실측치 아님). 실제 데이터 소스 연동 전까지의 잠정치입니다.

- area_m2: 일반적인 규모 추정치 (㎡)
- has_indoor: 실내 위주 장소인지 (날씨 연동 로직에 사용 예정)
- vegetation_score: 0~1, 식생(숲) 밀도 — 자연의 소리 모드 조건용
"""
from __future__ import annotations

CATEGORY_DEFAULTS: dict[str, dict[str, float | bool]] = {
    # 자연 계열 — 실외, 식생 높음
    "해수욕장": {"area_m2": 150000, "has_indoor": False, "vegetation_score": 0.1},
    "자연경관(산)": {"area_m2": 100000, "has_indoor": False, "vegetation_score": 0.8},
    "자연경관(하천‧해양)": {"area_m2": 80000, "has_indoor": False, "vegetation_score": 0.3},
    "자연생태": {"area_m2": 50000, "has_indoor": False, "vegetation_score": 0.9},
    "자연공원": {"area_m2": 100000, "has_indoor": False, "vegetation_score": 0.7},
    "기타자연관광": {"area_m2": 50000, "has_indoor": False, "vegetation_score": 0.6},

    # 역사·종교 계열 — 대체로 실외, 식생 중간
    "역사유적지": {"area_m2": 15000, "has_indoor": False, "vegetation_score": 0.3},
    "역사유물": {"area_m2": 3000, "has_indoor": True, "vegetation_score": 0.0},
    "종교성지": {"area_m2": 30000, "has_indoor": False, "vegetation_score": 0.5},
    "안보관광지": {"area_m2": 10000, "has_indoor": False, "vegetation_score": 0.2},

    # 문화·도시 계열 — 대체로 실내, 식생 거의 없음
    "랜드마크관광": {"area_m2": 5000, "has_indoor": False, "vegetation_score": 0.1},
    "테마공원": {"area_m2": 200000, "has_indoor": False, "vegetation_score": 0.2},
    "도시공원": {"area_m2": 20000, "has_indoor": False, "vegetation_score": 0.6},
    "도시지역문화관광": {"area_m2": 3000, "has_indoor": False, "vegetation_score": 0.1},
    "복합관광시설": {"area_m2": 30000, "has_indoor": True, "vegetation_score": 0.1},
    "공연시설": {"area_m2": 5000, "has_indoor": True, "vegetation_score": 0.0},
    "전시시설": {"area_m2": 8000, "has_indoor": True, "vegetation_score": 0.0},
    "행사시설": {"area_m2": 15000, "has_indoor": True, "vegetation_score": 0.0},
    "교육시설": {"area_m2": 5000, "has_indoor": True, "vegetation_score": 0.1},
    "기타문화관광지": {"area_m2": 3000, "has_indoor": True, "vegetation_score": 0.0},

    # 체험 계열
    "전통체험": {"area_m2": 5000, "has_indoor": True, "vegetation_score": 0.1},
    "공예체험": {"area_m2": 1000, "has_indoor": True, "vegetation_score": 0.0},
    "농산어촌체험": {"area_m2": 20000, "has_indoor": False, "vegetation_score": 0.7},
    "산사체험": {"area_m2": 20000, "has_indoor": False, "vegetation_score": 0.8},
    "웰니스관광": {"area_m2": 3000, "has_indoor": True, "vegetation_score": 0.2},
    "산업관광": {"area_m2": 10000, "has_indoor": True, "vegetation_score": 0.0},
    "기타체험": {"area_m2": 5000, "has_indoor": False, "vegetation_score": 0.2},

    # 새로 분리된 것 + 카페 — 실내, 식생 없음
    "도서관": {"area_m2": 2000, "has_indoor": True, "vegetation_score": 0.0},
    "서점": {"area_m2": 800, "has_indoor": True, "vegetation_score": 0.0},
    "카페": {"area_m2": 900, "has_indoor": True, "vegetation_score": 0.0},
}

# 혹시 매핑에 없는 카테고리가 들어올 경우의 안전장치
_FALLBACK: dict[str, float | bool] = {
    "area_m2": 5000.0,
    "has_indoor": False,
    "vegetation_score": 0.2,
}


def get_category_defaults(category: str) -> dict[str, float | bool]:
    """카테고리명으로 면적·실내여부·식생점수 기본값을 반환합니다. 없으면 무난한 기본값(FALLBACK)."""
    return CATEGORY_DEFAULTS.get(category, _FALLBACK)
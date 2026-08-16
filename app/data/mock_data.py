"""
Mock 부산 관광지(POI) 데이터셋.

실제 데이터 연동 전까지 개발/테스트를 진행하기 위한 더미 데이터입니다.
나중에 TourAPI + 공공데이터포털(상가업소정보) 연동이 완료되면,
이 파일 대신 `app/data/loader.py`의 `RealDataLoader`를 사용하도록
`app/config.py`의 `DATA_SOURCE` 값만 바꾸면 됩니다.

각 필드는 노션 "AI 기능 구현" 문서의 피처 스펙을 그대로 반영했습니다:
- population: 실시간 인구수 (TourAPI 혼잡도 데이터 대응)
- area_m2: 장소 면적(㎡) (공공데이터포털 상가업소정보 대응)
- category: 장소 카테고리 코드
- noise_sensitivity: 소음 민감도 가중치 (문서 예시: 사찰 1.5, 해수욕장 0.8)
- context_tags: 감성 맥락 키워드 (NLP 임베딩 이전 단계의 임시 라벨)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class POI:
    poi_id: str
    name: str
    category: str  
    area_m2: float
    noise_sensitivity: float  # 문서 예시: 사찰 1.5, 해수욕장 0.8
    lat: float
    lng: float
    context_tags: list[str] = field(default_factory=list)  # 참고용 라벨 (임베딩 이후에도 필터/분석용으로 남겨둠)
    description: str = ""  # 임베딩 입력으로 쓰이는 자연어 설명 문장 (감성 맥락 매칭의 핵심 필드)
    has_indoor: bool = False  # 실내 여부 (날씨 연동 로직에 사용)
    vegetation_score: float = 0.0  # 0~1, 식생(숲) 밀도 — 잎소리 ASMR 조건용


# 실제로는 TourAPI(관광지 기본정보) + 공공데이터포털(상가업소 면적) 조인으로 채워질 테이블.
# 지금은 부산의 대표 유형별로 하나씩 샘플을 만들어 파이프라인을 검증합니다.
MOCK_POIS: list[POI] = [
    POI(
        poi_id="POI001",
        name="범어사",
        category="종교성지",
        area_m2=45000,
        noise_sensitivity=1.5,
        lat=35.2695,
        lng=129.0808,
        context_tags=["고즈넉한", "사유", "명상", "산사"],
        description="울창한 숲 속에 자리한 고즈넉한 산사로, 걸으며 마음을 가라앉히고 조용히 사유하기 좋은 공간이다.",
        has_indoor=False,
        vegetation_score=0.9,
    ),
    POI(
        poi_id="POI002",
        name="송정해수욕장",
        category="해수욕장",
        area_m2=180000,
        noise_sensitivity=0.8,
        lat=35.1785,
        lng=129.1996,
        context_tags=["파도 소리", "개방감", "산책"],
        description="탁 트인 백사장과 파도 소리가 인상적인 해변으로, 자연의 리듬을 느끼며 걷기 좋은 개방적인 공간이다.",
        has_indoor=False,
        vegetation_score=0.1,
    ),
    POI(
        poi_id="POI003",
        name="F1963 미술관",
        category="전시시설",
        area_m2=12000,
        noise_sensitivity=1.3,
        lat=35.1823,
        lng=129.0991,
        context_tags=["사유", "전시 관람", "정적인"],
        description="옛 고무공장을 개조한 복합문화공간으로, 전시를 천천히 관람하며 사유하기 좋은 정적인 실내 공간이다.",
        has_indoor=True,
        vegetation_score=0.2,
    ),
    POI(
        poi_id="POI004",
        name="흰여울문화마을",
        category="도시지역문화관광",
        area_m2=8000,
        noise_sensitivity=1.2,
        lat=35.0764,
        lng=129.0431,
        context_tags=["고즈넉한", "바다 조망", "산책"],
        description="바다가 내려다보이는 계단식 골목 마을로, 고즈넉한 풍경을 바라보며 천천히 산책하기 좋다.",
        has_indoor=False,
        vegetation_score=0.05,
    ),
    POI(
        poi_id="POI005",
        name="보수동 책방골목",
        category="도시지역문화관광",
        area_m2=6000,
        noise_sensitivity=1.1,
        lat=35.1023,
        lng=129.0261,
        context_tags=["고즈넉한", "독서", "레트로"],
        description="오래된 헌책방들이 늘어선 레트로 골목으로, 책을 뒤적이며 조용히 독서하기 좋은 고즈넉한 분위기다.",
        has_indoor=False,
        vegetation_score=0.05,
    ),
    POI(
        poi_id="POI006",
        name="동백섬 산책로",
        category="자연공원",
        area_m2=90000,
        noise_sensitivity=0.9,
        lat=35.1571,
        lng=129.1522,
        context_tags=["숲", "산책", "잎소리"],
        description="소나무 숲이 우거진 해안 산책로로, 바람에 스치는 잎소리를 들으며 자연 속을 걷기 좋다.",
        has_indoor=False,
        vegetation_score=0.8,
    ),
    POI(
        poi_id="POI007",
        name="독립카페 브라운핸즈",
        category="카페",
        area_m2=900,
        noise_sensitivity=1.0,
        lat=35.1015,
        lng=129.0303,
        context_tags=["조용한", "독서", "커피 향"],
        description="원도심 골목에 자리한 조용한 독립카페로, 커피 향 속에서 책을 읽으며 시간을 보내기 좋다.",
        has_indoor=True,
        vegetation_score=0.0,
    ),
    POI(
        poi_id="POI008",
        name="해운대해수욕장",
        category="해수욕장",
        area_m2=220000,
        noise_sensitivity=0.8,
        lat=35.1587,
        lng=129.1604,
        context_tags=["파도 소리", "개방감"],
        description="부산을 대표하는 번화한 해수욕장으로, 넓은 백사장에서 파도 소리를 들으며 개방감을 느낄 수 있다.",
        has_indoor=False,
        vegetation_score=0.05,
    ),
]


def mock_realtime_population(poi_id: str, hour: int, is_weekend: bool) -> int:
    """
    실시간 유동인구 mock 값을 생성합니다.
    실제로는 TourAPI 혼잡도(5단계) 또는 부산시 유동인구 데이터로 대체됩니다.
    시간대/주말 여부에 따라 대략적인 패턴만 흉내 냅니다.
    """
    import random

    base = {
        "POI001": 300, "POI002": 2500, "POI003": 400, "POI004": 900,
        "POI005": 600, "POI006": 1200, "POI007": 80, "POI008": 4000,
    }.get(poi_id, 500)

    peak_hours = {11, 12, 13, 14, 15, 16, 17}
    multiplier = 1.6 if hour in peak_hours else 0.7
    if is_weekend:
        multiplier *= 1.5

    noise = random.uniform(0.85, 1.15)
    return max(0, int(base * multiplier * noise))

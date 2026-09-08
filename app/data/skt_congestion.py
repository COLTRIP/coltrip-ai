"""
SKT 지오비전 퍼즐 API 연동 (실시간 장소 혼잡도).

배경 (2026-09 조사):
  - 부산 관광지 594개 중, 이름이 SKT 장소 목록(전국 33,914개)과 일치하는 후보는
    약 195개였으나, 실제로 혼잡도 데이터가 존재하는지 전수 테스트한 결과
    18개(약 9%)만 성공했습니다. SKT는 전국 기준 상위 인기 상업·여가 시설
    위주로만 혼잡도를 제공하며, 나머지는 이름이 등록되어 있어도 실제 데이터가
    없습니다(404 NOT_FOUND_POI).
  - 따라서 "SKT 커버 지역에 관광지를 몰아서 배치"하는 전략 대신, 확정된 18곳만
    실시간으로 쓰고 나머지는 자동으로 기존 폴백 단계로 넘어가는 구조로 설계했습니다.

요금: 해커톤 요금제(11원/건, 월 3,000건 한도). 18곳을 하루 3회(09/15/21시)
갱신하면 월 18*3*30 = 1,620건으로 한도 내에서 여유 있게 운영 가능합니다.
"""
from __future__ import annotations

import httpx

from app.config import settings

SKT_BASE_URL = "https://apis.openapi.sk.com/puzzle/place/congestion/rltm/pois"

# poi_id(TourAPI contentid, 우리 쪽 식별자) -> SK poiId 매핑.
# 195개 후보 전수 테스트(2026-09) 결과 실제 혼잡도 데이터가 확인된 18곳만 포함.
SKT_VERIFIED_POIS: dict[str, str] = {
    "126119": "529636",     # 부산 어린이대공원
    "126078": "152111",     # 광안리해수욕장
    "126081": "152054",     # 해운대해수욕장
    "126848": "382199",     # 해동용궁사
    "2815627": "10323070",  # 롯데월드 어드벤처 부산
    "126098": "152114",     # 일광해수욕장
    "3060966": "1442822",   # 백운포체육공원
    "126121": "152117",     # 용두산공원
    "126658": "152115",     # 태종대
    "2661446": "8830667",   # 아미르공원
    "126080": "152112",     # 송정해수욕장
    "2729918": "1528664",   # 용소웰빙공원
    "252561": "2986231",    # 절영해안산책로
    "2756696": "2634342",   # 화명수목원
    "128108": "559264",     # 스포원파크
    "2456224": "566637",    # 렛츠런파크 부산경남
    "2385666": "6504442",   # 국립부산과학관
    "130145": "382675",     # 복천박물관
}


def is_skt_covered(poi_id: str) -> bool:
    """이 POI가 SKT 실시간 혼잡도 대상인지 확인합니다."""
    return poi_id in SKT_VERIFIED_POIS


def fetch_skt_population(poi_id: str, area_m2: float) -> int | None:
    """
    SKT 실시간 혼잡도를 조회해 population(추정 인구수)으로 환산합니다.

    SKT의 congestion 값은 "1㎡당 추정 방문자 수"(공식 문서 명시)이므로,
    population = congestion * area_m2 로 역산합니다. 이러면 기존
    QuietIndexModel의 밀도 계산(population / area_m2)과 자연스럽게 맞물립니다.

    실패하거나 데이터가 없으면 None을 반환하고, 호출부에서 다음 폴백 단계로
    넘어가야 합니다.
    """
    sk_poi_id = SKT_VERIFIED_POIS.get(poi_id)
    if not sk_poi_id:
        return None

    try:
        resp = httpx.get(
            f"{SKT_BASE_URL}/{sk_poi_id}",
            headers={"appKey": settings.SKT_APP_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        rltm = data.get("contents", {}).get("rltm")
        if not rltm:
            return None
        congestion = rltm[0].get("congestion")
        if congestion is None:
            return None
        return round(congestion * area_m2)
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        # 네트워크 오류, quota 초과, 예상 밖 응답 구조 등 — 폴백으로 넘어가기 위해
        # 여기서 예외를 흡수합니다. 상세 원인은 필요 시 로깅 추가.
        return None



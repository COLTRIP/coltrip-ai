"""
최종 확정된 30곳의 SK poiId로 실제 혼잡도 데이터가 나오는지 검증합니다.
해커톤 키(월 3,000건) 사용 — 이 검증에 딱 30건만 씁니다.
"""
import time

import httpx

APP_KEY = "qWAx6OQnON2fGeFPNqG2t9PO8jgDvfIZ1f4gHFnu"

FINAL_30 = [
    ("부산시민공원", "2788539"), ("송상현광장", "5742567"), ("KT&G 상상마당 부산", "10051831"),
    ("삼광사", "135187"), ("황령산레포츠공원", "461469"), ("호천문화플랫폼", "8601911"),
    ("황령산 전망대", "6473107"), ("황령산", "82715"), ("성지곡수원지", "1933853"),
    ("이중섭전망대", "7703524"), ("부산 어린이대공원", "529636"), ("한국신발관", "8672312"),
    ("증산공원", "1194970"), ("가야공원", "525829"), ("부산진성공원", "4100609"),
    ("조선통신사역사관", "2579810"), ("우암동 도시숲", "8590110"), ("온천천시민공원", "1136627"),
    ("한국기독교선교박물관", "7862833"), ("백양산 웰빙숲", "10288358"),
    ("동래읍성 임진왜란 역사관", "8525296"), ("비콘그라운드", "10089941"),
    ("부산과학체험관", "6807262"), ("도모헌", "7955865"), ("부산박물관", "368107"),
    ("수영민속예술관", "1143282"), ("동래향교", "697534"), ("F1963", "7769603"),
    ("광안리해수욕장", "152111"), ("해운대해수욕장", "152054"),
]

success, empty, failed = [], [], []

for name, poi_id in FINAL_30:
    try:
        resp = httpx.get(
            f"https://apis.openapi.sk.com/puzzle/place/congestion/rltm/pois/{poi_id}",
            headers={"appKey": APP_KEY}, timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("contents", {}).get("rltm"):
            level = data["contents"]["rltm"][0].get("congestionLevel", "?")
            success.append(name)
            print(f"✅ {name}: 정상 (혼잡도 레벨 {level})")
        else:
            empty.append(name)
            print(f"⚠️  {name}: 데이터 없음 - {data}")
    except Exception as e:
        failed.append(name)
        print(f"❌ {name}: 호출 실패 - {e}")
    time.sleep(1.5)  # 호출 간격 (429 방지)

print(f"\n=== 결과 요약 ===")
print(f"정상: {len(success)}개")
print(f"데이터 없음: {len(empty)}개 -> {empty}")
print(f"호출 실패: {len(failed)}개 -> {failed}")
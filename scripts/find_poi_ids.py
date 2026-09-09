"""FINAL_30 각 장소의 SK poiId를 all_pois.json(첫 6000개)에서 찾습니다."""
import json

with open("all_pois.json", encoding="utf-8") as f:
    sk_pois_old = json.load(f)

FINAL_30_REMAINING = [
    "동백","희와제과","먼스커피바","퍼프베이커리",
    "부산시민공원","송상현광장","부산정중앙공원","황령산레포츠공원","황령산","성지곡수원지",
    "KT&G 상상마당 부산","부산자유회관(부산통일관)","커넥트현대",
    "황령산 전망대","범일 이중섭거리",
    "보광사(부산)","선암사(부산)","혜원정사(부산)",
    "부산과학체험관","F1963",
    "부산광역시립 부전도서관","부산광역시립 연산도서관",
    "광안리해수욕장","해운대해수욕장",
]

def norm(s):
    return s.replace(" ", "").replace("(", "").replace(")", "")

for name in FINAL_30_REMAINING:
    n = norm(name)
    match = next((sk for sk in sk_pois_old if norm(sk["poiName"]) == n), None)
    if match:
        print(f"✅ {name} -> poiId {match['poiId']}")
    else:
        print(f"❌ {name} -> 첫 6000개에도 없음")
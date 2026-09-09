"""
SKT 매칭 확인된 후보들 중, 부산진구 중심에서 가까운 순 + 카테고리 다양성을 고려해
최종 30~33곳을 추립니다.
"""
from app.data.loader import RealDataLoader
from app.utils.geo import haversine_km

# SKT에서 매칭 확인된 후보 이름 목록 (166개 중 확인된 것들)
CONFIRMED_NAMES = [
    "오륙도해맞이공원","이기대","허심청","금강공원","부산시민공원","KT&G 상상마당 부산",
    "황령산레포츠공원","부산과학체험관","백운포체육공원","부산정중앙공원","부산북항 친수공원",
    "충렬사(부산)","부산 어린이대공원","오륙도 등대","오륙도 (부산 국가지질공원)","삼락생태공원",
    "가야공원","온천천시민공원","성지곡수원지","송상현광장","혜원정사(부산)","신선대(부산)",
    "삼광사","오륙도 스카이워크","당산","우암동 도시숲","소림사(부산)","운수사(부산)",
    "선암사(부산)","보광사(부산)","범일 이중섭거리","황령산 전망대","부산동명불원","법륜사(부산)",
    "황령산","사상근린공원","커넥트현대","부산해양자연사박물관","부산예술회관","우장춘기념관",
    "복천박물관","부산박물관","부산광역시립 명장도서관","168계단","이기대공원 동생말전망대",
    "증산공원","이중섭전망대","문화공감 수정(부산 수정동 일본식 가옥)","부산진성공원",
    "초량 이바구길","유치환 우체통 전망대","동래읍성지","부산 연산동 고분군","백양산 웰빙숲",
    "용호별빛공원","부산 복천동 고분군","대연수목전시원","동래향교","친환경 스카이웨이 전망대(이바구길)",
    "UN조각공원","국립일제강제동원역사관","부산자유회관(부산통일관)","한국신발관",
    "사상생활사박물관","망양로 산복도로전시관","감만창의 문화촌","호천문화플랫폼","동구 문화플랫폼",
    "유엔평화기념관","조선통신사역사관","해성아트베이","동래읍성 임진왜란 역사관",
    "한국기독교선교박물관","백양산 (부산 국가지질공원)","선암사(부산)",
]

loader = RealDataLoader()
all_pois = loader.fetch_pois()
by_name = {p.name: p for p in all_pois}

candidates = [by_name[n] for n in CONFIRMED_NAMES if n in by_name]
print(f"실제 좌표 확인된 후보: {len(candidates)}개 (목록에서 이름 불일치로 빠진 것도 있을 수 있음)\n")

# 부산진구 중심점 계산 (부산진구 POI들의 평균 좌표)
busanjin_names = ["전포공구길", "부산시민공원", "서면먹자골목", "삼광사", "선암사(부산)"]
anchors = [by_name[n] for n in busanjin_names if n in by_name]
center_lat = sum(p.lat for p in anchors) / len(anchors)
center_lng = sum(p.lng for p in anchors) / len(anchors)
print(f"부산진구 중심점: ({center_lat:.4f}, {center_lng:.4f})\n")

# 중심점으로부터 거리 계산 후 정렬
ranked = sorted(candidates, key=lambda p: haversine_km(center_lat, center_lng, p.lat, p.lng))

print(f"{'순위':<4}{'이름':<25}{'카테고리':<15}{'중심거리(km)'}")
for i, p in enumerate(ranked, 1):
    dist = haversine_km(center_lat, center_lng, p.lat, p.lng)
    marker = " ← 30위 컷" if i == 30 else ""
    print(f"{i:<4}{p.name:<25}{p.category:<15}{dist:.2f}{marker}")
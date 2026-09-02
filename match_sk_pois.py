"""SKT 장소 목록(all_pois.json)이랑 실제 저희 POI(594개)를 이름으로 대조."""
import re
from app.data.loader import RealDataLoader

with open('all_pois.json', encoding='utf-8') as f:
    content = f.read()

# poiId, poiName 쌍으로 추출
sk_pois = re.findall(r'"poiId":"(\d+)","poiName":"([^"]+)"', content)
sk_names = {name: poi_id for poi_id, name in sk_pois}

loader = RealDataLoader()
our_pois = loader.fetch_pois()

matched = []
for poi in our_pois:
    # 완전 일치 또는 부분 포함으로 느슨하게 매칭
    for sk_name, sk_id in sk_names.items():
        if poi.name.replace(" ", "") in sk_name.replace(" ", "") or sk_name.replace(" ", "") in poi.name.replace(" ", ""):
            matched.append((poi.poi_id, poi.name, sk_id, sk_name))
            break

print(f"저희 POI {len(our_pois)}개 중 SKT 목록과 매칭: {len(matched)}개\n")
for our_id, our_name, sk_id, sk_name in matched:
    print(f"{our_name} (우리ID:{our_id}) ↔ {sk_name} (SK poiId:{sk_id})")
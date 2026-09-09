"""fetch_population() 폴백 동작 테스트. SKT 18곳이 아닌 POI로만 테스트해서 quota를 안 씁니다."""
from app.data.loader import RealDataLoader
from app.data.busanjin_congestion import fetch_busanjin_population

loader = RealDataLoader()
pois = loader.fetch_pois()

target = next(p for p in pois if p.name == "가야공원")

print(f"테스트 대상: {target.name} (poi_id: {target.poi_id})")
print(f"좌표: ({target.lat}, {target.lng})\n")

# 먼저 부산진구 API만 단독으로 확인 (에러 나도 아래 코드 실행에 영향 없게)
print("--- 부산진구 API 직접 확인 ---")
result = fetch_busanjin_population(target.lat, target.lng)
print(f"부산진구 결과: {result}\n")

# 그다음 전체 fetch_population() 호출 (여기서 에러 나도 위 결과는 이미 봤으니 괜찮음)
print("--- fetch_population() 전체 흐름 ---")
population = loader.fetch_population(target.poi_id, hour=14, is_weekend=False)
print(f"최종 결과: {population}명")
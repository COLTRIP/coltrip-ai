# 콜트립(COLTRIP) AI Engine

AI 기반 실시간 혼잡도 분석 서비스의 AI 파트. FastAPI로 서빙하여
Spring 백엔드(반기태·선민제)가 REST로 호출하는 구조를 가정합니다.

## 구현된 3가지 기능

| 기능 | 파일 | 상태 |
|---|---|---|
| ① 실시간 고요 지수(Quiet Index) | `app/models/quiet_index_model.py` | RandomForest, 합성 데이터로 동작 확인 완료 |
| ② 감성 맥락 기반 추천 | `app/models/embedding_model.py` | 로컬 한국어 임베딩(ko-sroberta-multitask), **최초 실행 시 인터넷 필요** |
| ③ 혼잡 시 대체 장소 추천(Nudge Engine) | `app/models/nudge_engine.py` | KNN, 트리거 로직 포함 |

### ⚠️ ② 기능 실행 전 꼭 확인하세요

`/recommend` 엔드포인트는 최초 호출 시 HuggingFace Hub에서 임베딩 모델(~440MB)을
자동 다운로드합니다. 인터넷이 되는 일반 개발 환경에서는 문제없이 동작하지만,
사내망/폐쇄망/일부 CI 환경에서는 다운로드가 실패할 수 있습니다.
(이 프로젝트를 만든 개발 샌드박스는 보안상 huggingface.co 접근이 막혀 있어
② 기능은 실제로 다운로드해서 돌려보지 못했습니다 — **본인 컴퓨터에서 한 번
직접 실행해서 정상 동작하는지 꼭 확인해주세요.** 나머지 ①③ 기능은 정상 동작
확인 완료.)

모두 **Mock 데이터로 지금 바로 실행 가능**합니다. 실제 API가 준비되면
`app/data/loader.py`의 `RealDataLoader`만 채우면 나머지 코드는 그대로 재사용됩니다.

## 실행 방법

```bash
python3 -m venv venv
source venv/bin/activate          # Windows는 venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # 지금은 그대로 둬도 mock 모드로 동작함

# 테스트
pytest tests/ -v

# 서버 실행
uvicorn app.main:app --reload
# http://127.0.0.1:8000/docs 에서 Swagger UI로 바로 테스트 가능
```

## API 요약

- `POST /quiet-index` — 특정 POI의 고요 지수 조회
- `GET /quiet-index/map?hour=14&is_weekend=true` — 전체 POI 고요 지수 (지도 매핑용)
- `POST /recommend` — 감성 맥락 기반 정적 장소 추천
- `POST /alternative` — 혼잡 시 대체 장소 추천 (고요 지수가 임계값보다 낮을 때만 `triggered: true`)

## 프로젝트 구조

```
app/
  config.py          # 환경변수, mock/real 데이터 소스 스위치
  main.py             # FastAPI 엔트리포인트
  api/                 # 라우트 (요청/응답만 다룸)
  services/            # 비즈니스 로직 (모델 + 데이터 로더 조합)
  models/              # 순수 알고리즘 (Quiet Index, 임베딩, KNN)
  schemas/             # Pydantic 요청/응답 스키마
  data/
    mock_data.py       # 더미 POI 8개 + 실시간 인구 mock 생성기
    loader.py           # MockDataLoader / RealDataLoader 추상화
tests/                 # pytest (현재 7개, 전부 통과 확인함)
```

## 다음 단계 (팀 로드맵 3~7주차 기준)

1. **로컬에서 `/recommend` 엔드포인트 직접 실행 확인** (최우선): 임베딩 모델
   다운로드가 정상적으로 되는지, 사찰 설명이 "인문적+사유" 쿼리와 실제로
   더 유사하게 나오는지 눈으로 확인. `tests/test_embedding_model.py`의
   `test_matches_user_context_real_model` 테스트도 `skipif` 조건을 지우고 실행해보기.
2. **TourAPI 연동** (반기태 파트와 협업): `app/data/loader.py`의
   `RealDataLoader.fetch_pois()` / `fetch_population()` 구현
3. **`QuietIndexModel.fit_synthetic()` → `fit()` 전환**: 실제 방문객 데이터나
   설문 기반 라벨이 쌓이면 합성 데이터 학습을 실 데이터 학습으로 교체
4. **`recommend_by_context()`의 `min_match_score` 임계값 튜닝**: 실제 임베딩
   유사도 분포를 몇 개 POI로 찍어보고 0.3이 적절한지 조정 (지금은 임의값)
5. **기상청 API 연동**: `natural_sound_score()`에 실제 풍속 데이터 연결
6. **`/alternative` 트리거 튜닝**: 지금 mock 인구 기준으로는 임계값(40)을
   거의 넘지 않으므로, 실 데이터 붙이면서 `QUIET_INDEX_ALERT_THRESHOLD` 재조정 필요
7. **배포 서버 스펙 확인**: 임베딩 모델 로드에 최소 1GB 이상 RAM 권장.
   저사양 무료 티어로 배포 시 메모리 부족 가능성 있으니 클라우드 스펙 정할 때 고려

## 설계 메모

- Random Forest 피처는 노션 문서 스펙 그대로: `[인구수, 면적, 카테고리, 시간대,
  주말여부, 보정밀도]`. 보정밀도 = (인구/면적) × 소음민감도 가중치.
- KNN은 `[고요지수, 카테고리코드, 식생점수, 소음민감도]` 벡터 기준이며,
  이동거리는 별도 haversine 계산 후 가중치로 페널티를 줌 (문서: "이동 편의성 가중치").
- 감성 맥락 매칭은 키워드 매칭 대신 로컬 임베딩(ko-sroberta-multitask) 채택.
  API 키·비용 없이 동작하고, "조용한/고즈넉한/정숙한"처럼 표현이 달라도 의미가
  비슷하면 매칭되는 게 장점. POI의 `description`(자연어 문장)을 입력으로 쓰며,
  `context_tags`는 필터/분석용으로만 남겨둠.
- Kakao Local API는 사용하지 않음 (팀 결정: 좌표 정제는 백엔드가 네이버
  클라우드 플랫폼(NCP) Geocoding으로 전담).

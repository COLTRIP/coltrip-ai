"""
실시간 고요 지수(Quiet Index) 모델.

노션 문서의 설계를 기반으로 구현:
  1) 기본 밀도 D = 실시간 인구수(P) / 면적(A)
  2) D를 로그 스케일로 압축한 뒤, 실제 부산 594개 관광지에서 관측된
     로그밀도 범위(min~max)를 0~100으로 늘려서 "체감 혼잡도"를 계산
  3) Quiet Index = 100 - 체감 혼잡도  (점수가 높을수록 더 고요함)

2026-09 재작성 배경:
  기존엔 RandomForestRegressor를 mock 합성 학습 데이터(평균 밀도 0.02 근처로
  생성)로 학습시켜 사용했습니다. 실제 데이터를 넣어보니 밀도가 0.0009~2.67
  (약 3,000배 차)로, 학습 범위와 완전히 달라서 모델이 "낯선 입력"을
  제대로 구분 못 하고 80~86점 사이로만 뭉뚱그려 예측하는 문제가 있었습니다.

  또한 실제 밀도 분포 자체가 심하게 치우쳐 있어(중간값이 최댓값의
  1/27 수준), 단순 min-max로 늘리기만 하면 극단값 하나 때문에 나머지
  대부분이 다시 좁은 구간에 몰립니다. 그래서 로그 변환으로 먼저 분포를
  고르게 압축한 뒤 0~100으로 펼칩니다.

  로그밀도 범위(-6.8929 ~ 0.9813)는 2026-09-14 기준 594개 관광지 전체의
  실측값으로 캘리브레이션한 상수입니다. 나중에 관광지 수·유형 구성이
  크게 달라지면(신규 대량 추가 등) 재계산을 권장합니다.

  머신러닝 모델을 걷어낸 이유: (1) 장소 하나만 조회해도 즉시 계산
  가능해져 594개 전체를 매번 순회할 필요가 없고, (2) 계산식이 투명해서
  왜 이런 점수가 나왔는지 팀 누구나 바로 확인·조정할 수 있습니다.
"""
from __future__ import annotations

import math


# 2026-09-14 기준 594개 관광지 실측 로그밀도 범위에, 양쪽으로 15% 여유를 둔 값.
# (실측값을 그대로 쓰면 "오늘 제일 붐빈 곳=무조건 0점, 제일 한적한 곳=무조건 100점"이
#  강제로 맞춰지는 셈이라 다소 인위적으로 느껴짐 — 여유를 둬서 대부분은 10~90 사이에
#  자연스럽게 분포하고, 진짜 극단적인 값이 나올 때만 0/100에 가까워지도록 함)
_OBSERVED_LOG_MIN = -6.8929
_OBSERVED_LOG_MAX = 0.9813
_PADDING_RATIO = 0.10
_SCORE_OFFSET = 20.0
_span = _OBSERVED_LOG_MAX - _OBSERVED_LOG_MIN
_LOG_DENSITY_MIN = _OBSERVED_LOG_MIN - _span * _PADDING_RATIO
_LOG_DENSITY_MAX = _OBSERVED_LOG_MAX + _span * _PADDING_RATIO


def compute_density(population: int, area_m2: float) -> float:
    """기본 밀도(D = P/A)."""
    if area_m2 <= 0:
        return 0.0
    return population / area_m2


class QuietIndexModel:
    """
    이름은 기존 인터페이스(quiet_index_service.py 등)와의 호환을 위해
    유지하지만, 내부적으로는 머신러닝 모델이 아니라 위에서 설명한
    로그 스케일 캘리브레이션 공식을 사용합니다.
    """

    def fit_synthetic(self, *args, **kwargs) -> None:
        """
        더 이상 학습이 필요 없는 구조라 아무 일도 하지 않습니다.
        기존 호출부(quiet_index_service.py의 초기화 코드)를 안 고쳐도
        되도록 시그니처만 남겨둡니다.
        """
        pass

    def fit(self, *args, **kwargs) -> None:
        """위와 동일한 이유로 아무 일도 하지 않습니다."""
        pass

    def predict_quiet_index(
        self,
        population: int,
        area_m2: float,
        category: str,
        hour: int,
        is_weekend: bool,
    ) -> float:
        density = compute_density(population, area_m2)
        log_density = math.log(density + 0.0001)

        # 실측 로그밀도 범위를 0~100 혼잡도로 늘림
        span = _LOG_DENSITY_MAX - _LOG_DENSITY_MIN
        if span <= 0:
            congestion = 50.0
        else:
            congestion = (log_density - _LOG_DENSITY_MIN) / span * 100
            congestion = max(0.0, min(100.0, congestion))

        quiet_index = 100 - congestion
        # 전반적으로 점수가 너무 낮게 느껴진다는 피드백 반영, 전체를 위로
        # 밀어올리는 보정값 추가 (2026-09-16). 값 자체의 "정확도"보다는
        # 사용자가 체감하는 절대적인 느낌(숫자가 너무 낮아 보이지 않게)을
        # 맞추기 위한 주관적 보정.
        quiet_index = min(100.0, quiet_index + _SCORE_OFFSET)
        return round(quiet_index, 1)
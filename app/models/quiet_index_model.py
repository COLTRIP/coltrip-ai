"""
실시간 고요 지수(Quiet Index) 모델.

노션 문서의 설계를 그대로 구현:
  1) 기본 밀도 D = 실시간 인구수(P) / 면적(A)
  2) 장소별 '소음 민감도' 가중치를 곱해 체감 밀도를 보정
     예: 사찰 1.5(사람 늘면 고요 점수 급락), 해수욕장 0.8(개방감 반영)
  3) [실시간 인구수, 면적, 카테고리, 시간대, 주말여부, 보정밀도]를
     피처로 하는 RandomForestRegressor로 최종 "체감 혼잡도(0~100)"를 추정
  4) Quiet Index = 100 - 체감 혼잡도  (점수가 높을수록 더 고요함)

지금은 학습 데이터가 없으므로, 물리적으로 타당한 규칙(밀도가 높을수록
혼잡도가 높다)을 반영한 합성(synthetic) 학습 데이터로 모델을 학습합니다.
실제 방문객 만족도/혼잡 신고 데이터가 쌓이면 `train_on_real_data()`로
교체하면 됩니다.
"""
from __future__ import annotations
from app.data.category_codes import CATEGORY_CODES
import numpy as np
from sklearn.ensemble import RandomForestRegressor

def compute_weighted_density(population: int, area_m2: float, noise_sensitivity: float) -> float:
    """기본 밀도(D = P/A)에 소음 민감도 가중치를 곱한 보정 밀도."""
    if area_m2 <= 0:
        return 0.0
    base_density = population / area_m2
    return base_density * noise_sensitivity


def _category_code(category: str) -> int:
    return CATEGORY_CODES.get(category, -1)


class QuietIndexModel:
    def __init__(self, n_estimators: int = 200, random_state: int = 42):
        self.model = RandomForestRegressor(
            n_estimators=n_estimators, random_state=random_state, max_depth=8
        )
        self._is_fitted = False

    def _build_features(
        self,
        population: int,
        area_m2: float,
        category: str,
        hour: int,
        is_weekend: bool,
        noise_sensitivity: float,
    ) -> np.ndarray:
        weighted_density = compute_weighted_density(population, area_m2, noise_sensitivity)
        return np.array([[
            population,
            area_m2,
            _category_code(category),
            hour,
            int(is_weekend),
            weighted_density,
        ]])

    def fit_synthetic(self, n_samples: int = 4000, seed: int = 42) -> None:
        """
        합성 데이터로 초기 모델을 학습합니다.
        규칙: 혼잡도 = f(보정밀도) + 약간의 잡음, 카테고리/시간대 영향 소폭 반영.
        실제 데이터가 쌓이면 이 메서드 대신 fit()을 실 데이터로 호출하세요.
        """
        rng = np.random.default_rng(seed)
        categories = list(CATEGORY_CODES.keys())

        rows = []
        targets = []
        for _ in range(n_samples):
            category = rng.choice(categories)
            area = rng.uniform(500, 200000)
            noise_sensitivity = rng.uniform(0.7, 1.6)
            hour = int(rng.integers(6, 23))
            is_weekend = bool(rng.integers(0, 2))

            # 인구는 면적에 어느 정도 비례하되 랜덤성을 부여
            population = max(0, int(rng.normal(area * 0.02, area * 0.01)))

            weighted_density = compute_weighted_density(population, area, noise_sensitivity)

            # 혼잡도 라벨(0~100): 보정 밀도가 높을수록, 피크 시간대일수록, 주말일수록 상승
            peak_bonus = 15 if hour in (11, 12, 13, 14, 15, 16, 17) else 0
            weekend_bonus = 10 if is_weekend else 0
            raw_score = weighted_density * 40 + peak_bonus + weekend_bonus
            noise = rng.normal(0, 5)
            congestion = float(np.clip(raw_score + noise, 0, 100))

            rows.append([
                population, area, CATEGORY_CODES[category], hour, int(is_weekend), weighted_density
            ])
            targets.append(congestion)

        X = np.array(rows)
        y = np.array(targets)
        self.model.fit(X, y)
        self._is_fitted = True

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """실 데이터로 학습할 때 사용 (X: 피처 행렬, y: 실측 혼잡도/설문 기반 라벨)."""
        self.model.fit(X, y)
        self._is_fitted = True

    def predict_quiet_index(
        self,
        population: int,
        area_m2: float,
        category: str,
        hour: int,
        is_weekend: bool,
        noise_sensitivity: float,
    ) -> float:
        if not self._is_fitted:
            self.fit_synthetic()
        X = self._build_features(population, area_m2, category, hour, is_weekend, noise_sensitivity)
        congestion = float(self.model.predict(X)[0])
        congestion = float(np.clip(congestion, 0, 100))
        quiet_index = 100 - congestion
        return round(quiet_index, 1)

from app.models.quiet_index_model import QuietIndexModel, compute_weighted_density


def test_weighted_density_basic():
    d = compute_weighted_density(population=100, area_m2=200, noise_sensitivity=1.5)
    assert d == 0.75  # (100/200) * 1.5


def test_weighted_density_zero_area():
    assert compute_weighted_density(100, 0, 1.5) == 0.0


def test_quiet_index_range():
    model = QuietIndexModel()
    model.fit_synthetic(n_samples=500)
    qi = model.predict_quiet_index(
        population=1000, area_m2=5000, category="사찰", hour=14, is_weekend=True,
        noise_sensitivity=1.5,
    )
    assert 0 <= qi <= 100


def test_quiet_index_more_crowded_is_less_quiet():
    model = QuietIndexModel()
    model.fit_synthetic(n_samples=1500)
    low_pop = model.predict_quiet_index(
        population=50, area_m2=5000, category="카페", hour=14, is_weekend=False,
        noise_sensitivity=1.0,
    )
    high_pop = model.predict_quiet_index(
        population=3000, area_m2=5000, category="카페", hour=14, is_weekend=False,
        noise_sensitivity=1.0,
    )
    assert low_pop > high_pop

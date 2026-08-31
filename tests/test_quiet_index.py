from app.models.quiet_index_model import QuietIndexModel, compute_density


def test_density_basic():
    d = compute_density(population=100, area_m2=200)
    assert d == 0.5  # 100/200


def test_density_zero_area():
    assert compute_density(100, 0) == 0.0


def test_quiet_index_range():
    model = QuietIndexModel()
    model.fit_synthetic(n_samples=500)
    qi = model.predict_quiet_index(
        population=1000, area_m2=5000, category="종교성지", hour=14, is_weekend=True,
    )
    assert 0 <= qi <= 100


def test_quiet_index_more_crowded_is_less_quiet():
    model = QuietIndexModel()
    model.fit_synthetic(n_samples=1500)
    low_pop = model.predict_quiet_index(
        population=50, area_m2=5000, category="카페", hour=14, is_weekend=False,
    )
    high_pop = model.predict_quiet_index(
        population=3000, area_m2=5000, category="카페", hour=14, is_weekend=False,
    )
    assert low_pop > high_pop
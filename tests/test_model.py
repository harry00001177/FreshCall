"""Quantile models can cross (P50 predicted below P10, etc.) because they're
three independent regressors, not one joint model — enforce_non_crossing is
the safety net. Fitting itself is tested end-to-end on synthetic data so the
test doesn't depend on real Favorita data being present."""

import numpy as np
import pandas as pd

from freshcall.model import enforce_non_crossing, fit_quantile_models, predict_quantiles


class TestEnforceNonCrossing:
    def test_sorts_out_of_order_predictions(self):
        # p50 came back below p10 -- physically impossible, must be fixed by sorting
        p10, p50, p90 = enforce_non_crossing(p10=50, p50=40, p90=90)
        assert p10 <= p50 <= p90
        assert {p10, p50, p90} == {40, 50, 90}

    def test_leaves_already_ordered_predictions_unchanged(self):
        assert enforce_non_crossing(p10=10, p50=20, p90=30) == (10, 20, 30)


class TestFitPredict:
    def test_fits_and_predicts_three_ordered_quantiles(self):
        rng = np.random.default_rng(42)
        n = 60
        X = pd.DataFrame({"x": rng.normal(size=n)})
        y = X["x"] * 2 + rng.normal(scale=0.1, size=n) + 10

        models = fit_quantile_models(X, y, quantiles=[0.1, 0.5, 0.9], random_state=42)
        assert set(models.keys()) == {0.1, 0.5, 0.9}

        p10, p50, p90 = predict_quantiles(models, X.iloc[[0]])
        assert p10 <= p50 <= p90

    def test_works_with_non_default_quantiles(self):
        # config.yaml's model.quantiles is editable -- predict_quantiles must
        # not assume the keys are exactly 0.1/0.5/0.9
        rng = np.random.default_rng(42)
        n = 60
        X = pd.DataFrame({"x": rng.normal(size=n)})
        y = X["x"] * 2 + rng.normal(scale=0.1, size=n) + 10

        models = fit_quantile_models(X, y, quantiles=[0.05, 0.5, 0.95], random_state=42)
        p10, p50, p90 = predict_quantiles(models, X.iloc[[0]])
        assert p10 <= p50 <= p90

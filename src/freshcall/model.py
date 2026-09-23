"""Three independent quantile GradientBoostingRegressors (alpha 0.1/0.5/0.9).
Chosen over a single model because no vendor sells an inspectable, re-
thresholdable interval, and an LLM gives no calibrated interval at all (see
Problem Statement §4). Being three independent models means they can predict
out of order (P50 below P10) — `enforce_non_crossing` is the required
safety net, not an edge case."""

from sklearn.ensemble import GradientBoostingRegressor


def fit_quantile_models(X, y, quantiles=(0.1, 0.5, 0.9), **hyperparams):
    models = {}
    for q in quantiles:
        model = GradientBoostingRegressor(loss="quantile", alpha=q, **hyperparams)
        model.fit(X, y)
        models[q] = model
    return models


def predict_quantiles(models: dict, X) -> tuple[float, float, float]:
    """Derives low/mid/high from whatever quantile keys `models` actually
    has (sorted), rather than hardcoding 0.1/0.5/0.9 — so this stays correct
    if config.yaml's `model.quantiles` is ever changed."""
    low_q, mid_q, high_q = sorted(models.keys())
    p10 = models[low_q].predict(X)[0]
    p50 = models[mid_q].predict(X)[0]
    p90 = models[high_q].predict(X)[0]
    return enforce_non_crossing(p10, p50, p90)


def enforce_non_crossing(p10: float, p50: float, p90: float) -> tuple[float, float, float]:
    """Sort the three predictions so P10 <= P50 <= P90 always holds, even
    though each came from an independently-trained model."""
    lo, mid, hi = sorted([p10, p50, p90])
    return lo, mid, hi

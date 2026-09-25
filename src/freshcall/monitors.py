"""Two monitors from the Problem Statement's risk table (pre-registered,
DECISIONS.md 2026-09-25). Unlike the gate, they watch many SKU-days after
the fact: a *bias* monitor for systematic over/under-ordering (in cases,
the decision unit) and a *coverage* monitor for intervals that keep
missing. Alert bands are fitted on a calibration period, then applied to
later data."""

import pandas as pd

from freshcall.order import recommended_cases


def daily_monitor_series(rows: pd.DataFrame, case_pack: int, safety: float, on_hand: float, window: int = 7) -> pd.DataFrame:
    df = rows.copy()
    df["model_cases"] = [recommended_cases(p, safety, on_hand, case_pack) for p in df["p50"]]
    df["signed_case_error"] = df["model_cases"] - df["hindsight"]
    df["covered"] = (df["p10"] <= df["actual"]) & (df["actual"] <= df["p90"])
    daily = df.groupby("date").agg(
        fold=("fold", "first"), bias=("signed_case_error", "mean"), coverage=("covered", "mean")
    ).sort_index()
    daily["bias_rolling"] = daily["bias"].rolling(window).mean()
    daily["coverage_rolling"] = daily["coverage"].rolling(window).mean()
    return daily


def fit_band(values: pd.Series, k: float = 3.0) -> tuple[float, float]:
    v = values.dropna()
    return v.mean() - k * v.std(), v.mean() + k * v.std()


def alerts(series: pd.Series, lower: float | None, upper: float | None) -> list:
    s = series.dropna()
    out = pd.Series(False, index=s.index)
    if lower is not None:
        out |= s < lower
    if upper is not None:
        out |= s > upper
    return list(s.index[out])

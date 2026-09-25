"""Phase 2 multi-SKU backtest: 3 rolling-origin folds (instructor feedback,
DECISIONS.md 2026-09-23), fitting one model per (SKU, fold) on data up to
the fold's train cutoff, then walking forward through the 31-day test
window using real historical lag features (not leakage — lag_1 for day T
is day T-1's actual sale, known before day T in real deployment)."""

import pandas as pd

from freshcall.features import add_features, build_daily_grid
from freshcall.gate import should_abstain
from freshcall.model import fit_quantile_models, predict_quantiles
from freshcall.order import hindsight_demand_order, naive_seasonal_order, recommended_cases

FOLDS = [
    {"name": "fold1_may_jun", "train_end": "2017-05-15", "test_start": "2017-05-16", "test_end": "2017-06-15"},
    {"name": "fold2_jun_jul", "train_end": "2017-06-15", "test_start": "2017-06-16", "test_end": "2017-07-15"},
    {"name": "fold3_jul_aug", "train_end": "2017-07-15", "test_start": "2017-07-16", "test_end": "2017-08-15"},
]

FEATURE_COLS_STATIC = ["lag_1", "lag_7", "rolling_7_mean"]


def evaluate_sku_fold(raw_df: pd.DataFrame, store_nbr: int, item_nbr: int, fold: dict, cfg: dict,
                      features_fn=add_features) -> list[dict]:
    """Fit once on data up to fold['train_end'], predict every day in
    [test_start, test_end]. Returns one dict per test day, or [] if there
    isn't enough training history for this SKU to reach this fold."""
    sku = raw_df[(raw_df["store_nbr"] == store_nbr) & (raw_df["item_nbr"] == item_nbr)][["date", "unit_sales"]]
    sku = sku.sort_values("date")
    if sku.empty:
        return []

    grid = build_daily_grid(sku, start=sku["date"].min(), end=fold["test_end"])
    feats = features_fn(grid)
    dow_cols = [c for c in feats.columns if c.startswith("dow_")]
    feature_cols = dow_cols + FEATURE_COLS_STATIC

    train = feats[feats["date"] <= fold["train_end"]].dropna(subset=feature_cols)
    test = feats[(feats["date"] >= fold["test_start"]) & (feats["date"] <= fold["test_end"])]
    test = test.dropna(subset=feature_cols)

    if len(train) < 30 or test.empty:
        return []  # not enough history for this SKU to evaluate this fold

    models = fit_quantile_models(
        train[feature_cols], train["unit_sales"],
        quantiles=cfg["model"]["quantiles"],
        n_estimators=cfg["model"]["n_estimators"],
        max_depth=cfg["model"]["max_depth"],
        learning_rate=cfg["model"]["learning_rate"],
        random_state=cfg["model"]["random_state"],
    )

    case_pack, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]
    threshold = cfg["gate"]["rel_width_threshold"]

    results = []
    for _, row in test.iterrows():
        p10, p50, p90 = predict_quantiles(models, row[feature_cols].to_frame().T)
        abstain = should_abstain(p10, p50, p90, threshold)
        actual = float(row["unit_sales"])
        hindsight = hindsight_demand_order(actual, case_pack)
        naive = naive_seasonal_order(row["lag_7"], case_pack)
        cases = None if abstain else recommended_cases(p50, safety, on_hand, case_pack)
        results.append({
            "item_nbr": item_nbr, "fold": fold["name"], "date": row["date"],
            "abstain": abstain, "cases": cases, "hindsight": hindsight, "naive": naive,
            "p10": p10, "p50": p50, "p90": p90, "actual": actual,
        })
    return results


def summarize_fold(rows: list[dict]) -> dict:
    """model_cmr and naive_cmr are BOTH computed on the auto-answered
    subset only (the fix from instructor feedback, DECISIONS.md
    2026-09-23) — comparing the model's accuracy on its self-selected easy
    subset against the baseline's accuracy on the full set would be
    selection bias, not a measured improvement. Coverage uses every row,
    abstained or not, since it's a property of the interval itself."""
    n = len(rows)
    if n == 0:
        return {"n": 0, "n_answered": 0, "abstain_rate": 0.0, "model_cmr": None, "naive_cmr": None, "coverage": 0.0}

    answered = [r for r in rows if not r["abstain"]]
    abstain_rate = 1 - (len(answered) / n)

    if answered:
        model_cmr = sum(r["cases"] == r["hindsight"] for r in answered) / len(answered)
        naive_cmr = sum(r["naive"] == r["hindsight"] for r in answered) / len(answered)
    else:
        model_cmr = None
        naive_cmr = None

    coverage = sum(r["p10"] <= r["actual"] <= r["p90"] for r in rows) / n

    return {
        "n": n, "n_answered": len(answered), "abstain_rate": abstain_rate,
        "model_cmr": model_cmr, "naive_cmr": naive_cmr, "coverage": coverage,
    }


def recompute_abstain(rows: list[dict], threshold: float) -> list[dict]:
    """Re-derive the abstain flag at a different rel_width threshold from
    the same stored p10/p50/p90 — lets the Section 7 gate sweep reuse one
    backtest run instead of refitting models per threshold. Returns new
    dicts; never mutates the input."""
    return [{**r, "abstain": should_abstain(r["p10"], r["p50"], r["p90"], threshold)} for r in rows]


def abstention_precision(rows: list[dict], case_pack: int, safety: float, on_hand: float) -> float | None:
    """Of the SKU-days the gate abstained on, what share would the model's
    own P50 have gotten wrong (>=1 case off hindsight_demand_order) had it
    answered anyway? This is the metric that actually validates the gate —
    a high rel_width that never corresponds to a real error would mean the
    gate is just cautious, not accurate. Backtest-only: in production the
    counterfactual answer for an abstained day is never observed."""
    abstained = [r for r in rows if r["abstain"]]
    if not abstained:
        return None
    wrong = sum(
        recommended_cases(r["p50"], safety, on_hand, case_pack) != r["hindsight"]
        for r in abstained
    )
    return wrong / len(abstained)


def error_base_rate(rows: list[dict], case_pack: int, safety: float, on_hand: float) -> float | None:
    """Share of ALL SKU-days (abstained or not) whose P50-implied
    recommendation would miss hindsight_demand_order — the error rate a
    gate abstaining on a random subset would 'catch' by chance alone.
    abstention_precision only means something if it clears this bar (the
    Section 7 abandon condition)."""
    if not rows:
        return None
    wrong = sum(
        recommended_cases(r["p50"], safety, on_hand, case_pack) != r["hindsight"]
        for r in rows
    )
    return wrong / len(rows)

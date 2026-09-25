"""The Problem Statement §8 minimal end-to-end version: one SKU, 90 rows,
predict -> gate -> arithmetic -> explain. This script's job is to prove the
pipeline has no structural bug, not to produce a defensible accuracy number
(see docs/PROJECT_OVERVIEW.md phase 1 vs phase 2)."""

import time
from functools import lru_cache

import pandas as pd
import yaml
from dotenv import load_dotenv

load_dotenv()

from freshcall.containment import check_numeral_containment
from freshcall.explain import build_fact_block, generate_explanation
from freshcall.features import add_features, build_daily_grid
from freshcall.gate import rel_width, should_abstain
from freshcall.model import fit_quantile_models, predict_quantiles
from freshcall.order import hindsight_demand_order, recommended_cases

FEATURE_COLS_STATIC = ["lag_1", "lag_7", "rolling_7_mean"]


@lru_cache(maxsize=1)
def _load_raw_sales(parquet_path: str) -> pd.DataFrame:
    """Cached so Phase 2 (looping over 500+ SKUs) reads the 31M-row parquet
    from disk once, not once per SKU (measured at 1.26s/read)."""
    return pd.read_parquet(parquet_path)


def load_sku_slice(parquet_path: str, store_nbr: int, item_nbr: int, n_rows: int) -> pd.DataFrame:
    df = _load_raw_sales(parquet_path)
    sku = df[(df["store_nbr"] == store_nbr) & (df["item_nbr"] == item_nbr)][["date", "unit_sales"]]
    sku = sku.sort_values("date")
    start = sku["date"].min()
    end = start + pd.Timedelta(days=n_rows - 1)
    return build_daily_grid(sku, start=start, end=end)


def run(config_path: str = "config.yaml", n_rows: int = 90, train_rows: int = 83) -> dict:
    t0 = time.time()
    cfg = yaml.safe_load(open(config_path))

    grid = load_sku_slice(
        "data/derived_perishable_train.parquet",
        cfg["slice"]["store_nbr"],
        cfg["slice"]["first_test_item_nbr"],
        n_rows=n_rows,
    )
    feats = add_features(grid)
    dow_cols = [c for c in feats.columns if c.startswith("dow_")]
    feature_cols = dow_cols + FEATURE_COLS_STATIC

    train = feats.iloc[:train_rows].dropna(subset=feature_cols)
    predict_row = feats.iloc[[train_rows]]

    models = fit_quantile_models(
        train[feature_cols],
        train["unit_sales"],
        quantiles=cfg["model"]["quantiles"],
        n_estimators=cfg["model"]["n_estimators"],
        max_depth=cfg["model"]["max_depth"],
        learning_rate=cfg["model"]["learning_rate"],
        random_state=cfg["model"]["random_state"],
    )
    p10, p50, p90 = predict_quantiles(models, predict_row[feature_cols])

    threshold = cfg["gate"]["rel_width_threshold"]
    abstain = should_abstain(p10, p50, p90, threshold)

    actual = float(predict_row["unit_sales"].iloc[0])
    recent_avg = round(float(train["unit_sales"].tail(7).mean()), 1)
    last_same_weekday = round(float(predict_row["lag_7"].iloc[0]), 1)

    case_pack, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]
    cases = None if abstain else recommended_cases(p50, safety, on_hand, case_pack)
    units = None if abstain else cases * case_pack
    hindsight = hindsight_demand_order(actual, case_pack)

    fact_block = build_fact_block(
        sku_name=f"item {cfg['slice']['first_test_item_nbr']}",
        abstain=abstain,
        recommend_cases=cases,
        recent_avg=recent_avg,
        last_same_weekday=last_same_weekday,
    )
    text = generate_explanation(fact_block)
    elapsed = time.time() - t0

    result = {
        "p10": p10, "p50": p50, "p90": p90,
        "rel_width": rel_width(p10, p50, p90),
        "abstain": abstain, "actual": actual,
        "hindsight_demand_order": hindsight,
        "cases": cases, "units": units, "case_pack": case_pack,
        "text": text, "elapsed": elapsed,
        "fact_block": fact_block,
    }
    return result


def print_report(result: dict) -> None:
    print("--- FreshCall Section 8 minimal pipeline run ---")
    print(f"P10={result['p10']:.1f}  P50={result['p50']:.1f}  P90={result['p90']:.1f}  "
          f"rel_width={result['rel_width']:.3f}")
    print(f"Abstain: {result['abstain']}")
    print(f"Actual next-day sales: {result['actual']}")
    print(f"hindsight_demand_order: {result['hindsight_demand_order']} cases (eval-only, not shown to manager)")
    if not result["abstain"]:
        print(f"Recommended: {result['cases']} cases ({result['units']} units)")
    print(f"Output sentence: {result['text']}")
    print(f"Elapsed: {result['elapsed']:.2f}s")


def check_pass_fail(result: dict) -> None:
    assert result["elapsed"] < 60, "FAIL: must run end-to-end in under 60 seconds"

    if not result["abstain"]:
        assert result["units"] % result["case_pack"] == 0, (
            "FAIL: units must be a whole multiple of case_pack"
        )

    assert check_numeral_containment(result["text"], result["fact_block"]), (
        "FAIL: every numeral in the output must be a member of the fact block"
    )

    if result["abstain"]:
        # the only number allowed is the reference anchor, already covered by
        # the containment check above; no recommended quantity may appear
        assert result["text"].startswith("ASK ME") and result["cases"] is None, (
            "FAIL: an abstain message must hand back without a recommended quantity"
        )

    print("\nAll Section 8 pass/fail checks: PASSED")


if __name__ == "__main__":
    result = run()
    print_report(result)
    check_pass_fail(result)

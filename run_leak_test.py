"""Leak test, pre-registered (DECISIONS.md 2026-09-25): re-run the store-44
backtest with ONE deliberate bug — a 7-day mean that includes the day
being predicted (a forgotten shift(1)) — and compare with the clean run.
The leaky feature lives only in this script, never in the library."""

import sys

import pandas as pd
import yaml

from freshcall.backtest import FOLDS, evaluate_sku_fold, recompute_abstain
from freshcall.features import add_features
from run_case_gate_experiment import apply_case_gate, metrics

CLEAN = "data/backtest_results.parquet"
LEAKY = "data/backtest_results_leaky.parquet"


def add_features_leaky(grid: pd.DataFrame) -> pd.DataFrame:
    df = add_features(grid)
    df["rolling_7_mean"] = df["unit_sales"].rolling(window=7).mean()  # BUG on purpose: includes today
    return df


def existing_test_catches_it() -> bool:
    """Re-run the logic of tests/test_features.py::test_rolling_7_mean_excludes_todays_value
    against the leaky function: day 8 of 1..10 must have rolling mean 4.0."""
    grid = pd.DataFrame({"date": pd.date_range("2013-01-01", periods=10, freq="D"), "unit_sales": range(1, 11)})
    value = add_features_leaky(grid).loc[lambda d: d["unit_sales"] == 8, "rolling_7_mean"].iloc[0]
    return value != 4.0


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    skus = pd.read_parquet("data/full_426_skus.parquet")["item_nbr"].tolist()
    raw = pd.read_parquet("data/derived_perishable_train.parquet")

    rows = []
    for i, item in enumerate(skus):
        for fold in FOLDS:
            rows.extend(evaluate_sku_fold(raw, 44, item, fold, cfg, features_fn=add_features_leaky))
        if (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{len(skus)} SKUs", file=sys.stderr)
    pd.DataFrame(rows).to_parquet(LEAKY, index=False)

    print(f"Would the existing unit test catch this bug? {'YES' if existing_test_catches_it() else 'NO'}\n")
    print(f"{'run':<7}{'gate':<16}{'abstain':>9}{'modelCMR':>10}{'naiveCMR':>10}{'relImpr':>9}{'coverage':>10}{'lift':>7}")
    for name, path in [("clean", CLEAN), ("leaky", LEAKY)]:
        res = pd.read_parquet(path).to_dict("records")
        coverage = sum(r["p10"] <= r["actual"] <= r["p90"] for r in res) / len(res)
        for gate_name, gated in [("rel_width 0.60", recompute_abstain(res, 0.60)),
                                 ("rel_width 1.00", recompute_abstain(res, 1.00)),
                                 ("case-straddle", apply_case_gate(res, cfg))]:
            m = metrics(gated, cfg)
            print(f"{name:<7}{gate_name:<16}{m['abstain']:>9.3f}{m['model_cmr']:>10.3f}{m['naive_cmr']:>10.3f}"
                  f"{m['rel_impr'] * 100:>+8.1f}%{coverage:>10.3f}{m['lift']:>7.2f}")


if __name__ == "__main__":
    main()

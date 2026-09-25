"""Bias and coverage monitors on both stores' stored predictions, plus a
positive control, exactly as pre-registered (DECISIONS.md 2026-09-25):
bands fitted on fold 1 (mean ± 3 std of the 7-day rolling values),
applied to folds 2-3. Positive control: store 44 with actual sales x1.5
from 2017-08-01 — the bias monitor should fire within 7 days."""

import pandas as pd
import yaml

from freshcall.backtest import FOLDS
from freshcall.monitors import alerts, daily_monitor_series, fit_band
from freshcall.order import hindsight_demand_order

STORES = {44: "data/backtest_results.parquet", 49: "data/backtest_results_store49.parquet"}
SHOCK_START, SHOCK_FACTOR = pd.Timestamp("2017-08-01"), 1.5


def bands(daily: pd.DataFrame) -> dict:
    calib = daily[daily["fold"] == FOLDS[0]["name"]]
    bias_lo, bias_hi = fit_band(calib["bias_rolling"])
    cov_lo, _ = fit_band(calib["coverage_rolling"])
    return {"bias": (bias_lo, bias_hi), "coverage": (cov_lo, None)}


def monitored(daily: pd.DataFrame, b: dict) -> dict:
    later = daily[daily["fold"] != FOLDS[0]["name"]]
    return {name: alerts(later[f"{name}_rolling"], *b[name]) for name in ("bias", "coverage")}


def fmt_dates(ds: list) -> str:
    return "none" if not ds else f"{len(ds)} days, first {ds[0].date()}, last {ds[-1].date()}"


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    cp, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]

    store44_bands = None
    for store, path in STORES.items():
        rows = pd.read_parquet(path)
        daily = daily_monitor_series(rows, cp, safety, on_hand)
        b = bands(daily)
        if store == 44:
            store44_bands = b
        found = monitored(daily, b)
        print(f"== Store {store} ==")
        print(f"  bias band (cases/SKU-day, from fold 1): [{b['bias'][0]:+.3f}, {b['bias'][1]:+.3f}]  "
              f"| folds 2-3 rolling range [{daily['bias_rolling'][daily['fold'] != FOLDS[0]['name']].min():+.3f}, "
              f"{daily['bias_rolling'][daily['fold'] != FOLDS[0]['name']].max():+.3f}]")
        print(f"  coverage lower bound (from fold 1): {b['coverage'][0]:.3f}  "
              f"| folds 2-3 rolling min {daily['coverage_rolling'][daily['fold'] != FOLDS[0]['name']].min():.3f}")
        print(f"  bias alerts in folds 2-3:     {fmt_dates(found['bias'])}")
        print(f"  coverage alerts in folds 2-3: {fmt_dates(found['coverage'])}\n")

    shocked = pd.read_parquet(STORES[44])
    hit = shocked["date"] >= SHOCK_START
    shocked.loc[hit, "actual"] = shocked.loc[hit, "actual"] * SHOCK_FACTOR
    shocked.loc[hit, "hindsight"] = [hindsight_demand_order(a, cp) for a in shocked.loc[hit, "actual"]]
    found = monitored(daily_monitor_series(shocked, cp, safety, on_hand), store44_bands)
    after = [d for d in found["bias"] if d >= SHOCK_START]
    print(f"== Positive control: store 44, actual sales x{SHOCK_FACTOR} from {SHOCK_START.date()} ==")
    if after:
        print(f"  bias monitor first alert: {after[0].date()} ({(after[0] - SHOCK_START).days} days after the shock)")
    else:
        print("  bias monitor: NO alert after the shock")
    print(f"  bias alerts before the shock: {len([d for d in found['bias'] if d < SHOCK_START])}")
    print(f"  coverage alerts after the shock: {fmt_dates([d for d in found['coverage'] if d >= SHOCK_START])}")


if __name__ == "__main__":
    main()

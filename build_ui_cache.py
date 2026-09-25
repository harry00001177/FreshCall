"""Pre-computes everything the UI shows (DECISIONS.md 2026-09-25): store 44,
40 SKUs (fixed seed, still-selling only), one date every 14 days of the
test period. Forecasts come from the stored post-fix backtest (no refit).
Stores what the redesign needs (case range, routine flag, both standing-
order policies, the v3 sentence's facts) and, for the UI's history view,
the v1 / v2 gates' ASK ME decisions. No LLM call: the order sentence is a
deterministic template rendered by the app. Output: data/ui_cache.parquet."""

import pandas as pd
import yaml

from freshcall.case_gate import straddles_case_boundary
from freshcall.features import build_daily_grid, same_weekday_avg
from freshcall.gate import should_abstain
from freshcall.order import naive_seasonal_order
from freshcall.redesign import case_range, is_routine, past_max
from freshcall.ui_logic import select_ui_skus, ui_dates

STORE = 44
RESULTS = "data/backtest_results.parquet"
OUT = "data/ui_cache.parquet"
FIRST_TEST_DAY, LAST_TEST_DAY = "2017-05-16", "2017-08-15"


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    cp, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]
    sales = pd.read_parquet("data/derived_perishable_train.parquet")
    sales = sales[sales["store_nbr"] == STORE]
    last_sale = sales.groupby("item_nbr")["date"].max()
    inactive = set(last_sale[last_sale < FIRST_TEST_DAY].index)

    candidates = pd.read_parquet("data/full_426_skus.parquet")["item_nbr"].tolist()
    skus = select_ui_skus(candidates, inactive, n=40, seed=42)
    dates = ui_dates(FIRST_TEST_DAY, LAST_TEST_DAY, step_days=14)
    families = pd.read_csv("data/items.csv").set_index("item_nbr")["family"]

    results = pd.read_parquet(RESULTS)
    results = results[results["item_nbr"].isin(skus) & results["date"].isin(dates)]

    daily = {}
    for item in skus:
        sku = sales[sales["item_nbr"] == item][["date", "unit_sales"]]
        daily[item] = build_daily_grid(sku, start=sku["date"].min(), end=LAST_TEST_DAY).set_index("date")["unit_sales"]

    rows = []
    for r in results.itertuples():
        s = daily[r.item_nbr]
        lo, order, hi = case_range(r.p10, r.p50, r.p90, safety, on_hand, cp)
        last_week_units = round(float(s.shift(7).loc[r.date]), 1)
        rows.append({
            "date": r.date, "item_nbr": r.item_nbr, "family": families.get(r.item_nbr, ""),
            "p10": r.p10, "p50": r.p50, "p90": r.p90, "lo": lo, "order": order, "hi": hi,
            "routine": is_routine(past_max(s).loc[r.date], cp),
            "last_week_units": last_week_units, "last_week_cases": naive_seasonal_order(last_week_units, cp),
            "weekday": r.date.day_name(), "weekday_avg": round(float(same_weekday_avg(s).loc[r.date]), 1),
            "abstain_case_straddle": straddles_case_boundary(r.p10, r.p50, r.p90, safety, on_hand, cp),
            "abstain_rel_width": should_abstain(r.p10, r.p50, r.p90, cfg["gate"]["rel_width_threshold"]),
            "actual": r.actual, "hindsight": r.hindsight,
        })

    df = pd.DataFrame(rows).sort_values(["date", "item_nbr"])
    df.to_parquet(OUT, index=False)
    print(f"{len(df)} rows ({df['item_nbr'].nunique()} SKUs x {df['date'].nunique()} dates) -> {OUT}")
    print(f"routine share {df['routine'].mean():.1%}; range width 0/1/2+ (non-routine): "
          + " / ".join(f"{x:.0%}" for x in [((df.hi - df.lo)[~df.routine] == k).mean() for k in (0, 1)]
                       + [((df.hi - df.lo)[~df.routine] >= 2).mean()]))


if __name__ == "__main__":
    main()

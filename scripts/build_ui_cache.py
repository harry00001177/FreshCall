"""Pre-computes everything the UI shows (DECISIONS.md 2026-09-25, 2026-10-01):
for stores 44 (development), 8 and 45 (confirmation stores), 40 SKUs each
(fixed seed, still-selling only), one date every 14 days of the test period.
Forecasts come from the stored 9-quantile backtests (no refit): q0.1 / q0.5 /
q0.9 give the range and the history view's gates; all 9 give the newsvendor
order, recomputed live in the app for any cost ratio. Also writes the Data
page's summary (filter funnel, a few raw rows). No LLM call: the order
sentence is a deterministic template rendered by the app.
Output: data/ui_cache.parquet, data/ui_data_summary.json."""

import json

import pandas as pd
import yaml

from freshcall.case_gate import straddles_case_boundary
from freshcall.features import build_daily_grid, same_weekday_avg
from freshcall.gate import should_abstain
from freshcall.newsvendor import QUANTILES, floor_applies
from freshcall.order import naive_seasonal_order
from freshcall.redesign import case_range, is_routine, past_max
from freshcall.ui_logic import select_ui_skus, ui_dates
from prepare_data import DENSITY_THRESHOLD, FIRST_SALE_CUTOFF, density_table, whole_unit_items

STORES = {44: "data/full_426_skus.parquet", 8: "data/store8_candidates.parquet",
          45: "data/store45_candidates.parquet"}
OUT, SUMMARY = "data/ui_cache.parquet", "data/ui_data_summary.json"
FIRST_TEST_DAY, LAST_TEST_DAY = "2017-05-16", "2017-08-15"
QCOLS = [f"q{round(q * 100)}" for q in QUANTILES]  # q10 ... q90 (itertuples needs identifiers)


def store_rows(store: int, cfg: dict, all_sales: pd.DataFrame, families: pd.Series) -> list[dict]:
    cp, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]
    sales = all_sales[all_sales["store_nbr"] == store]
    last_sale = sales.groupby("item_nbr")["date"].max()
    inactive = set(last_sale[last_sale < FIRST_TEST_DAY].index)
    skus = select_ui_skus(pd.read_parquet(STORES[store])["item_nbr"].tolist(), inactive, n=40, seed=42)
    dates = ui_dates(FIRST_TEST_DAY, LAST_TEST_DAY, step_days=14)

    q = pd.read_parquet(f"data/newsvendor_store{store}.parquet")
    q = q[q["item_nbr"].isin(skus) & q["date"].isin(dates)]
    q = q.rename(columns={f"q{x}": c for x, c in zip(QUANTILES, QCOLS)})

    rows = []
    for item, g in q.groupby("item_nbr"):
        sku = sales[sales["item_nbr"] == item][["date", "unit_sales"]]
        s = build_daily_grid(sku, start=sku["date"].min(), end=LAST_TEST_DAY).set_index("date")["unit_sales"]
        for r in g.itertuples():
            p10, p50, p90 = r.q10, r.q50, r.q90
            lo, order, hi = case_range(p10, p50, p90, safety, on_hand, cp)
            last_week_units = round(float(s.shift(7).loc[r.date]), 1)
            rows.append({
                "store": store, "date": r.date, "item_nbr": item, "family": families.get(item, ""),
                "p10": p10, "p50": p50, "p90": p90, "lo": lo, "order": order, "hi": hi,
                "routine": is_routine(past_max(s).loc[r.date], cp),
                "floor": bool(floor_applies(s.shift(1).loc[:r.date].tail(7))),
                **{c: getattr(r, c) for c in QCOLS},
                "last_week_units": last_week_units, "last_week_cases": naive_seasonal_order(last_week_units, cp),
                "weekday": r.date.day_name(), "weekday_avg": round(float(same_weekday_avg(s).loc[r.date]), 1),
                "abstain_case_straddle": straddles_case_boundary(p10, p50, p90, safety, on_hand, cp),
                "abstain_rel_width": should_abstain(p10, p50, p90, cfg["gate"]["rel_width_threshold"]),
                "actual": r.actual, "hindsight": r.hindsight,
            })
    return rows


def data_summary(sales: pd.DataFrame, items: pd.DataFrame) -> dict:
    """The Data page's filter funnel (prepare_data.py's rules) and a few raw rows."""
    whole = whole_unit_items(sales)
    d = density_table(sales[sales["item_nbr"].isin(whole)])
    dense = d[d["density"] >= DENSITY_THRESHOLD]
    kept = dense[dense["min"] <= FIRST_SALE_CUTOFF]
    sample = sales[sales["store_nbr"] == 44].head(6).merge(items[["item_nbr", "family"]], on="item_nbr")
    return {
        "funnel": [
            ["All items in the catalogue", f"{len(items):,} items", "items.csv"],
            ["Perishable", f"{int(items['perishable'].sum()):,} items · {len(sales):,} sales rows",
             "fresh food is what gets thrown away"],
            ["Sold in whole units in every store", f"{len(whole):,} items",
             "items sold by weight can't be ordered in cases"],
            [f"Sold on at least {DENSITY_THRESHOLD:.0%} of days", f"{len(dense):,} store-item pairs",
             "items that rarely sell make every forecast a guess"],
            [f"First sale on or before {FIRST_SALE_CUTOFF}", f"{len(kept):,} store-item pairs",
             "enough history to train before all three test months"],
        ],
        "per_store": {str(s): int((kept["store_nbr"] == s).sum()) for s in (44, 49, 8, 45)},
        "sample": sample[["date", "store_nbr", "item_nbr", "family", "unit_sales"]]
        .assign(date=lambda x: x["date"].dt.date.astype(str)).to_dict("records"),
    }


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    sales = pd.read_parquet("data/derived_perishable_train.parquet")
    items = pd.read_csv("data/items.csv")
    families = items.set_index("item_nbr")["family"]
    rows = [r for store in STORES for r in store_rows(store, cfg, sales, families)]
    df = pd.DataFrame(rows).sort_values(["store", "date", "item_nbr"])
    df.to_parquet(OUT, index=False)
    json.dump(data_summary(sales, items), open(SUMMARY, "w"), indent=1)
    for store, g in df.groupby("store"):
        print(f"store {store}: {len(g)} rows ({g['item_nbr'].nunique()} SKUs x {g['date'].nunique()} dates), "
              f"routine {g['routine'].mean():.1%}")
    print(f"-> {OUT}, {SUMMARY}")


if __name__ == "__main__":
    main()

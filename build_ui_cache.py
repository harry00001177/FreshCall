"""Pre-generates everything the UI shows (DECISIONS.md 2026-09-25): store
44, 40 SKUs (fixed seed, still-selling only), one date every 14 days of the
test period. Forecasts come from the stored post-fix backtest (no refit);
both gates' decisions are stored so the UI can compare them; explanation
sentences are generated once here, through numeral containment with the
template fallback, never live in the UI. Output: data/ui_cache.parquet."""

import pandas as pd
import yaml
from dotenv import load_dotenv

load_dotenv()

from freshcall.case_gate import straddles_case_boundary
from freshcall.containment import check_numeral_containment
from freshcall.explain import _default_call_llm, build_fact_block, render_template_fallback
from freshcall.features import add_features, build_daily_grid
from freshcall.gate import should_abstain
from freshcall.order import recommended_cases
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

    feats = {}
    for item in skus:
        sku = sales[sales["item_nbr"] == item][["date", "unit_sales"]]
        feats[item] = add_features(build_daily_grid(sku, start=sku["date"].min(), end=LAST_TEST_DAY)).set_index("date")

    rows, llm_calls, fallbacks = [], 0, 0
    for r in results.itertuples():
        f = feats[r.item_nbr].loc[r.date]
        recent_avg, last_same = round(float(f["rolling_7_mean"]), 1), round(float(f["lag_7"]), 1)
        abstain_case = straddles_case_boundary(r.p10, r.p50, r.p90, safety, on_hand, cp)
        abstain_relw = should_abstain(r.p10, r.p50, r.p90, cfg["gate"]["rel_width_threshold"])
        cases = recommended_cases(r.p50, safety, on_hand, cp)
        name = f"item {r.item_nbr}"

        order_text = None
        if not (abstain_case and abstain_relw):
            fb = build_fact_block(name, False, cases, recent_avg, last_same)
            try:
                raw = _default_call_llm(fb)
                llm_calls += 1
            except Exception:
                raw = ""
            if raw and check_numeral_containment(raw, fb):
                order_text = raw
            else:
                order_text = render_template_fallback(fb)
                fallbacks += 1

        rows.append({
            "date": r.date, "item_nbr": r.item_nbr, "family": families.get(r.item_nbr, ""),
            "cases": cases, "order_text": order_text,
            "recent_avg": recent_avg, "last_same_weekday": last_same,
            "abstain_case_straddle": abstain_case, "abstain_rel_width": abstain_relw,
            "actual": r.actual, "hindsight": r.hindsight,
        })

    df = pd.DataFrame(rows).sort_values(["date", "item_nbr"])
    df.to_parquet(OUT, index=False)
    print(f"{len(df)} rows ({df['item_nbr'].nunique()} SKUs x {df['date'].nunique()} dates) -> {OUT}")
    print(f"LLM calls: {llm_calls}, template fallbacks: {fallbacks}")
    for gate in ("case_straddle", "rel_width"):
        print(f"ASK ME share, {gate}: {df[f'abstain_{gate}'].mean():.1%}")


if __name__ == "__main__":
    main()

"""L1/L2 explanation harness, step 1 of 2 (pre-registered, DECISIONS.md
2026-09-24): select the 10 cases, build each fact block, get the raw LLM
sentence, run L1 on the raw output, and write a sheet for Harry to label.
The L2 judge is a separate, later step, run only after Harry's labels."""

import json
import os

import pandas as pd
import yaml
from dotenv import load_dotenv

load_dotenv()

from freshcall.containment import check_numeral_containment
from freshcall.explain import _default_call_llm, build_fact_block, render_template_fallback
from freshcall.features import add_features, build_daily_grid
from freshcall.gate import should_abstain
from freshcall.harness import select_cases
from freshcall.order import recommended_cases

RESULTS = "data/backtest_results.parquet"
OUT_DIR = "data/l1l2"


def fact_inputs(sales: pd.DataFrame, item_nbr: int, date: pd.Timestamp) -> tuple[float, float]:
    sku = sales[sales["item_nbr"] == item_nbr][["date", "unit_sales"]]
    feats = add_features(build_daily_grid(sku, start=sku["date"].min(), end=date))
    row = feats[feats["date"] == date].iloc[0]
    return round(float(row["rolling_7_mean"]), 1), round(float(row["lag_7"]), 1)


def select_batch(batch: int, threshold: float) -> tuple[pd.DataFrame, str, int]:
    """Batch 1: the original pre-registered draw. Batch 2 (supplementary,
    pre-registered after batch 1 was 6/7 all-zero inputs): P50 >= 1 only,
    batch 1's rows excluded, answered strata only."""
    results = pd.read_parquet(RESULTS)
    if batch == 1:
        return select_cases(results, threshold=threshold, seed=42), f"{OUT_DIR}/cases.csv", 1
    batch1 = pd.read_csv(f"{OUT_DIR}/cases.csv", parse_dates=["date"])
    seen = set(zip(batch1["item_nbr"], batch1["date"]))
    pool = results[(results["p50"] >= 1) & ~pd.Series(list(zip(results["item_nbr"], results["date"]))).isin(seen).values]
    return select_cases(pool, threshold=threshold, seed=42, counts=(4, 3, 0)), f"{OUT_DIR}/cases_batch2.csv", len(batch1) + 1


def main(batch: int = 1):
    cfg = yaml.safe_load(open("config.yaml"))
    threshold = cfg["gate"]["rel_width_threshold"]
    cases, out_path, first_case = select_batch(batch, threshold)

    raw_sales = pd.read_parquet("data/derived_perishable_train.parquet")
    sales = raw_sales[raw_sales["store_nbr"] == cfg["slice"]["store_nbr"]]

    records = []
    for i, c in enumerate(cases.itertuples(), start=first_case):
        recent_avg, last_same_weekday = fact_inputs(sales, c.item_nbr, c.date)
        abstain = should_abstain(c.p10, c.p50, c.p90, threshold)
        cases_n = None if abstain else recommended_cases(c.p50, cfg["safety"], cfg["on_hand"], cfg["case_pack"])
        fb = build_fact_block(f"item {c.item_nbr}", abstain, cases_n, recent_avg, last_same_weekday)

        if abstain:
            raw, shown = None, render_template_fallback(fb)
            l1 = check_numeral_containment(shown, fb)
            source = "template (abstain)"
        else:
            try:
                raw = _default_call_llm(fb)
            except Exception as e:
                raw = f"<LLM call failed: {type(e).__name__}>"
            l1 = check_numeral_containment(raw, fb)
            shown = raw if l1 else render_template_fallback(fb)
            source = "LLM" if l1 else "template (L1 failed)"

        records.append({
            "case": i, "stratum": c.stratum, "item_nbr": c.item_nbr, "date": c.date.date().isoformat(),
            "rel_width": round(c.rel_width, 3), "fact_block": json.dumps(fb), "raw_llm_output": raw,
            "l1_pass": l1, "shown_text": shown, "shown_source": source,
            "harry_faithful": "", "harry_usable": "", "harry_note": "",
        })

    os.makedirs(OUT_DIR, exist_ok=True)
    pd.DataFrame(records).to_csv(out_path, index=False)

    llm_rows = [r for r in records if r["stratum"] != "abstain"]
    abstain_rows = [r for r in records if r["stratum"] == "abstain"]
    print(f"L1 on raw LLM output: {sum(r['l1_pass'] for r in llm_rows)}/{len(llm_rows)} pass")
    if abstain_rows:
        print(f"Abstain texts passing containment: {sum(r['l1_pass'] for r in abstain_rows)}/{len(abstain_rows)}")
    print()
    for r in records:
        print(f"[{r['case']}] {r['stratum']:<10} rel_width={r['rel_width']:<6} {r['fact_block']}")
        print(f"     shown ({r['shown_source']}): {r['shown_text']}")
        if r["raw_llm_output"] and r["shown_source"] != "LLM":
            print(f"     raw LLM output: {r['raw_llm_output']}")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)

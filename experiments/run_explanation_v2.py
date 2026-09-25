"""Explanation fix, batch 3, exactly as pre-registered (DECISIONS.md
2026-09-25, commit eae5369). Fact block v2: the same weekday's 4-week
average instead of a 7-day mean. Cases: (a) the 7 batch-2 SKU-days
(incl. case 16) for a before/after on the same inputs; (b) 7 unused
non-routine SKU-days with P50 >= 1, seed 43.

  step 1:  python experiments/run_explanation_v2.py generate
           -> data/l1l2/cases_v3.csv (Harry labels q1-q3, blind)
  step 2:  python experiments/run_explanation_v2.py judge
           -> data/l1l2/judged_v3.csv (only after all labels exist)"""

import json
import sys

import pandas as pd
import yaml
from dotenv import load_dotenv

load_dotenv()

from freshcall.containment import check_numeral_containment
from freshcall.explain import _default_call_llm, build_fact_block_v2, render_template_fallback
from freshcall.features import build_daily_grid, same_weekday_avg
from freshcall.judge import JUDGE_MODEL, call_judge
from freshcall.order import recommended_cases
from freshcall.redesign import is_routine, past_max

RESULTS = "data/backtest_results.parquet"
BATCH1, BATCH2 = "data/l1l2/cases.csv", "data/l1l2/cases_batch2.csv"
LATEST_BATCH2_SENTENCES = "data/l1l2/cases_batch2_v2.csv"  # after the comparison-word fix
OUT, JUDGED = "data/l1l2/cases_v3.csv", "data/l1l2/judged_v3.csv"
QUESTIONS = ("faithful", "usable", "direction")


def daily_series(sales: pd.DataFrame, item: int) -> pd.Series:
    sku = sales[sales["item_nbr"] == item][["date", "unit_sales"]]
    return build_daily_grid(sku, start=sku["date"].min(), end="2017-08-15").set_index("date")["unit_sales"]


def pick_cases(results: pd.DataFrame, sales: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    b2 = pd.read_csv(BATCH2, parse_dates=["date"])
    part_a = results.merge(b2[["case", "item_nbr", "date"]], on=["item_nbr", "date"]).assign(group="a")
    used = set(zip(pd.read_csv(BATCH1, parse_dates=["date"])["item_nbr"], pd.read_csv(BATCH1, parse_dates=["date"])["date"]))
    used |= set(zip(b2["item_nbr"], b2["date"]))
    pool = results[results["p50"] >= 1].sample(frac=1.0, random_state=43)
    picked, series = [], {}
    for r in pool.itertuples():
        if (r.item_nbr, r.date) in used:
            continue
        s = series.setdefault(r.item_nbr, daily_series(sales, r.item_nbr))
        if not is_routine(past_max(s).get(r.date), cfg["case_pack"]):
            picked.append(r.Index)
        if len(picked) == 7:
            break
    part_b = results.loc[picked].assign(group="b", case=range(101, 108))
    return pd.concat([part_a, part_b], ignore_index=True)


def generate():
    cfg = yaml.safe_load(open("config.yaml"))
    sales = pd.read_parquet("data/derived_perishable_train.parquet")
    sales = sales[sales["store_nbr"] == cfg["slice"]["store_nbr"]]
    cases = pick_cases(pd.read_parquet(RESULTS), sales, cfg)
    old = pd.read_csv(LATEST_BATCH2_SENTENCES).set_index("case")["new_sentence"]

    rows = []
    for c in cases.itertuples():
        s = daily_series(sales, c.item_nbr)
        fb = build_fact_block_v2(
            f"item {c.item_nbr}", recommended_cases(c.p50, cfg["safety"], cfg["on_hand"], cfg["case_pack"]),
            c.date.day_name(), round(float(same_weekday_avg(s).loc[c.date]), 1), round(float(s.shift(7).loc[c.date]), 1),
        )
        raw = _default_call_llm(fb)
        l1 = check_numeral_containment(raw, fb)
        rows.append({"case": c.case, "group": c.group, "item_nbr": c.item_nbr, "date": c.date.date().isoformat(),
                     "fact_block": json.dumps(fb), "old_sentence": old.get(c.case, ""), "raw_llm_output": raw,
                     "l1_pass": l1, "shown_text": raw if l1 else render_template_fallback(fb),
                     "harry_faithful": "", "harry_usable": "", "harry_direction": ""})
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"L1 on raw output: {df['l1_pass'].sum()}/{len(df)}\n")
    for r in df.itertuples():
        fb = json.loads(r.fact_block)
        print(f"[{r.case}] {fb['weekday']}: order {fb['recommend_cases']}, {fb['weekday']}s avg {fb['weekday_avg']}, "
              f"last {fb['weekday']} {fb['last_same_weekday']}")
        if r.old_sentence:
            print(f"     old: {r.old_sentence}")
        print(f"     new: {r.shown_text}")
    print(f"\nWrote {OUT}")


def judge():
    df = pd.read_csv(OUT)
    assert all(df[f"harry_{q}"].isin(["yes", "no"]).all() for q in QUESTIONS), "Harry's labels must exist first"
    verdicts = [call_judge(r.fact_block, r.shown_text, three_questions=True) for r in df.itertuples()]
    for q in QUESTIONS:
        df[f"judge_{q}"] = [v[q] for v in verdicts]
    df["judge_reason"] = [v["reason"] for v in verdicts]
    df.to_csv(JUDGED, index=False)
    print(f"Judge: {JUDGE_MODEL}")
    for q in QUESTIONS:
        h, j = df[f"harry_{q}"], df[f"judge_{q}"]
        print(f"{q:<10} Harry yes {(h == 'yes').sum()}/{len(df)} | judge yes {(j == 'yes').sum()}/{len(df)} | "
              f"disagreements {(h != j).sum()}")
    for r in df.itertuples():
        if any(getattr(r, f"harry_{q}") != getattr(r, f"judge_{q}") for q in QUESTIONS):
            print(f"  [{r.case}] {r.shown_text}\n       judge: {[getattr(r, f'judge_{q}') for q in QUESTIONS]} -- {r.judge_reason}")


if __name__ == "__main__":
    {"generate": generate, "judge": judge}[sys.argv[1]]()

"""Template sentence test, exactly as pre-registered (DECISIONS.md
2026-09-25, commit 6824573): the same 14 batch-3 SKU-days, written by the
deterministic v3 template instead of the LLM.

  step 1:  python experiments/run_explanation_v3.py generate -> data/l1l2/cases_v3_template.csv
  step 2:  python experiments/run_explanation_v3.py judge    (after Harry's labels)"""

import json
import re
import sys

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from freshcall.containment import check_numeral_containment
from freshcall.explain import build_fact_block_v3, comparison_word, order_sentence_from
from freshcall.judge import JUDGE_MODEL, call_judge

BATCH3 = "data/l1l2/cases_v3.csv"
OUT, JUDGED = "data/l1l2/cases_v3_template.csv", "data/l1l2/judged_v3_template.csv"
QUESTIONS = ("faithful", "usable", "direction")


def units_labelled(sentence: str) -> bool:
    """The order states cases and units; every number in the reason is followed by unit(s),
    except last week's figure, which reads as the same unit ("last Sunday's 51")."""
    order_part, _, reason = sentence.partition(". ")
    order_ok = re.fullmatch(r"ORDER \d+ cases? \(\d+ units?\)", order_part) is not None
    avg_ok = re.search(r"averaged \d+(\.\d+)? units?,", reason) is not None
    return order_ok and avg_ok


def generate():
    b3 = pd.read_csv(BATCH3)
    rows = []
    for r in b3.itertuples():
        old = json.loads(r.fact_block)
        fb = build_fact_block_v3(old["sku_name"], old["recommend_cases"], 12, old["weekday"],
                                 old["weekday_avg"], old["last_same_weekday"])
        text = order_sentence_from(fb)
        word = comparison_word(fb["weekday_avg"], fb["last_same_weekday"])
        rows.append({"case": r.case, "fact_block": json.dumps(fb), "llm_sentence": r.shown_text, "template_sentence": text,
                     "l1_pass": check_numeral_containment(text, fb), "word_correct": word in text,
                     "units_labelled": units_labelled(text),
                     "harry_faithful": "", "harry_usable": "", "harry_direction": ""})
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    for c in ("l1_pass", "word_correct", "units_labelled"):
        print(f"{c}: {df[c].sum()}/{len(df)}")
    print()
    for r in df.itertuples():
        print(f"[{r.case}] LLM (v2):  {r.llm_sentence}\n      template: {r.template_sentence}")
    print(f"\nWrote {OUT}")


def judge():
    df = pd.read_csv(OUT)
    assert all(df[f"harry_{q}"].isin(["yes", "no"]).all() for q in QUESTIONS), "Harry's labels must exist first"
    verdicts = [call_judge(r.fact_block, r.template_sentence, three_questions=True) for r in df.itertuples()]
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
            print(f"  [{r.case}] {r.template_sentence}\n       judge: {[getattr(r, f'judge_{q}') for q in QUESTIONS]} -- {r.judge_reason}")


if __name__ == "__main__":
    {"generate": generate, "judge": judge}[sys.argv[1]]()

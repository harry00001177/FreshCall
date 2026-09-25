"""Negative-control test of the L2 judge, exactly as pre-registered
(DECISIONS.md 2026-09-25, commit 265da47): six sentences with one
deliberate flaw each plus two clean controls, on real harness fact blocks.
Measures whether the judge catches bad sentences, and which flaws the L1
numeral check already catches on its own."""

import json

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from freshcall.containment import check_numeral_containment
from freshcall.judge import JUDGE_MODEL, call_judge

SHEETS = ["data/l1l2/cases.csv", "data/l1l2/cases_batch2.csv"]
OUT = "data/l1l2/negative_control.csv"

PROBES = [
    ("NC1", 5, "invented number", "faithful",
     "ORDER 4 cases. Recent average 36.9, close to last week's 39.0, so expect about 45 units tomorrow."),
    ("NC2", 13, "wrong direction", "faithful",
     "ORDER 1 case. Recent average 11.4, lower than last week's 7.0."),
    ("NC3", 12, "confidence talk", "usable",
     "ORDER 4 cases, though I am not very confident about this one. Recent average 25.4, lower than last week's 51.0."),
    ("NC4", 15, "order buried, too long", "usable",
     "Looking at recent sales, this item has averaged 19.0 units over the past week, which is lower than the 34.0 "
     "units sold on the same day last week, so after weighing both figures the suggested order for tomorrow is 3 cases."),
    ("NC5", 9, "hand-back that still gives a quantity", "faithful",
     "ASK ME - this one is harder to call than usual, but 1 case should probably be enough."),
    ("NC6", 5, "overstated comparison", "faithful",
     "ORDER 4 cases. Recent average 36.9, significantly lower than last week's 39.0."),
    ("PC1", 14, "none (control)", None,
     "ORDER 1 case. Recent average 10.0, higher than last week's 6.0."),
    ("PC2", 11, "none (control)", None,
     "ORDER 1 case. Recent average 3.4, lower than last week's 9.0."),
]


def main():
    cases = pd.concat([pd.read_csv(s) for s in SHEETS]).set_index("case")
    rows = []
    for pid, case, flaw, target, sentence in PROBES:
        fact_json = cases.loc[case, "fact_block"]
        l1 = check_numeral_containment(sentence, json.loads(fact_json))
        v = call_judge(fact_json, sentence)
        if target:
            outcome = "caught" if v[target] == "no" else "MISSED"
        else:
            outcome = "false alarm" if "no" in (v["faithful"], v["usable"]) else "ok"
        rows.append({"id": pid, "case": case, "flaw": flaw, "target": target, "sentence": sentence,
                     "l1_pass": l1, "judge_faithful": v["faithful"], "judge_usable": v["usable"],
                     "judge_reason": v["reason"], "outcome": outcome})

    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"Judge: {JUDGE_MODEL}\n")
    for r in df.itertuples():
        print(f"[{r.id}] {r.flaw:<38} L1={'pass' if r.l1_pass else 'FAIL':<5} "
              f"judge faithful={r.judge_faithful:<4} usable={r.judge_usable:<4} -> {r.outcome}")
        print(f"       judge reason: {r.judge_reason}")

    flawed = df[df["target"].notna()]
    by_l1 = ~flawed["l1_pass"]
    by_judge = flawed["outcome"] == "caught"
    print(f"\nFlaws caught by L1 alone:  {by_l1.sum()}/{len(flawed)}")
    print(f"Flaws caught by the judge: {by_judge.sum()}/{len(flawed)}")
    print(f"Flaws caught by either:    {(by_l1 | by_judge).sum()}/{len(flawed)}")
    print(f"False alarms on controls:  {(df['outcome'] == 'false alarm').sum()}/{df['target'].isna().sum()}")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()

"""L1/L2 harness, step 2 of 2: run the L2 judge on all labelled sentences
(batch 1 + supplementary batch 2), only after Harry's labels are saved,
and report judge-vs-Harry disagreement per question."""

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from freshcall.judge import JUDGE_MODEL, call_judge

SHEETS = ["data/l1l2/cases.csv", "data/l1l2/cases_batch2.csv"]
OUT = "data/l1l2/judged.csv"


def main():
    df = pd.concat([pd.read_csv(s).assign(batch=i + 1) for i, s in enumerate(SHEETS)], ignore_index=True)
    assert (df["harry_faithful"].isin(["yes", "no"]) & df["harry_usable"].isin(["yes", "no"])).all(), \
        "every sentence must be labelled by Harry before the judge runs"

    verdicts = [call_judge(r.fact_block, r.shown_text) for r in df.itertuples()]
    df["judge_faithful"] = [v["faithful"] for v in verdicts]
    df["judge_usable"] = [v["usable"] for v in verdicts]
    df["judge_reason"] = [v["reason"] for v in verdicts]
    df.to_csv(OUT, index=False)

    print(f"Judge: {JUDGE_MODEL}, {len(df)} sentences (batch 1: {(df.batch == 1).sum()}, batch 2: {(df.batch == 2).sum()})\n")
    llm = df[df["shown_source"] == "LLM"]
    print(f"L1 on raw LLM output: {llm['l1_pass'].sum()}/{len(llm)} pass")
    for q in ("faithful", "usable"):
        h, j = df[f"harry_{q}"], df[f"judge_{q}"]
        print(f"{q:<9} Harry yes {(h == 'yes').sum()}/{len(df)} | judge yes {(j == 'yes').sum()}/{len(df)} | "
              f"unparseable {(j == 'unparseable').sum()} | disagreements {(h != j).sum()}")
    dis = df[(df["harry_faithful"] != df["judge_faithful"]) | (df["harry_usable"] != df["judge_usable"])]
    print(f"\nDisagreements ({len(dis)}):")
    for r in dis.itertuples():
        print(f"  [{r.case}] {r.shown_text}\n       judge: faithful={r.judge_faithful} usable={r.judge_usable} -- {r.judge_reason}")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()

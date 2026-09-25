"""Regenerates the 7 batch-2 sentences with the restricted-comparison
prompt and checks them deterministically, exactly as pre-registered
(DECISIONS.md 2026-09-25). Old sentences are kept untouched."""

import json
import re

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from freshcall.containment import check_numeral_containment
from freshcall.explain import _default_call_llm

OLD = "data/l1l2/cases_batch2.csv"
NEW = "data/l1l2/cases_batch2_v2.csv"
INTENSITY = ["significantly", "sharply", "slightly", "much", "far", "considerably", "substantially",
             "dramatically", "notably", "markedly", "greatly", "strongly", "marginally", "somewhat",
             "a lot", "a bit"]
PHRASES = {"higher than": "higher", "lower than": "lower", "about the same as": "same"}


def check(sentence: str, fb: dict) -> dict:
    s = sentence.lower()
    intensity = [w for w in INTENSITY if re.search(rf"\b{re.escape(w)}\b", s)]
    found = [v for p, v in PHRASES.items() if p in s]
    a, b = fb["recent_avg"], fb["last_same_weekday"]
    if len(found) != 1:
        direction_ok = False
    elif found[0] == "higher":
        direction_ok = a > b
    elif found[0] == "lower":
        direction_ok = a < b
    else:
        direction_ok = abs(a - b) / max(a, b) <= 0.10
    return {
        "l1_pass": check_numeral_containment(sentence, fb),
        "intensity_words": ",".join(intensity),
        "comparison": ",".join(found) or "none",
        "direction_ok": direction_ok,
        "opens_with_order": sentence.strip().startswith("ORDER"),
    }


def main():
    old = pd.read_csv(OLD)
    rows = []
    for r in old.itertuples():
        fb = json.loads(r.fact_block)
        new_sentence = _default_call_llm(fb)
        rows.append({"case": r.case, "fact_block": r.fact_block, "old_sentence": r.shown_text,
                     "new_sentence": new_sentence, **check(new_sentence, fb),
                     **{f"old_{k}": v for k, v in check(r.shown_text, fb).items()}})
    df = pd.DataFrame(rows)
    df.to_csv(NEW, index=False)

    for r in df.itertuples():
        print(f"[{r.case}] old: {r.old_sentence}")
        print(f"     new: {r.new_sentence}")
        print(f"     L1={r.l1_pass} intensity=[{r.intensity_words}] comparison={r.comparison} "
              f"direction_ok={r.direction_ok} opens_with_order={r.opens_with_order}")
    new_ok = df[["l1_pass", "direction_ok", "opens_with_order"]].all(axis=1) & (df["intensity_words"] == "")
    old_ok = df[["old_l1_pass", "old_direction_ok", "old_opens_with_order"]].all(axis=1) & (df["old_intensity_words"] == "")
    print(f"\nOld prompt: {old_ok.sum()}/{len(df)} pass all four checks "
          f"({(df['old_intensity_words'] != '').sum()} with intensity words)")
    print(f"New prompt: {new_ok.sum()}/{len(df)} pass all four checks "
          f"({(df['intensity_words'] != '').sum()} with intensity words)")
    print(f"Pre-registered criterion (7/7 pass): {'SUCCESS' if new_ok.all() else 'FAIL'}")
    print(f"\nWrote {NEW}")


if __name__ == "__main__":
    main()

"""Manager-time sensitivity (DECISIONS.md 2026-09-25): every timing in the
Problem Statement is an unmeasured guess, so show minutes per 40-SKU night
across a grid of guesses instead of one number. Routine share comes from
the stored backtests (stores 44 and 8); routine SKUs are assumed to take
1 s (collapsed standing orders).

Second table (DECISIONS.md 2026-10-01): minutes for the v2 case-straddle
gate when a handed-back SKU takes 20 / 30 / 45 / 90 s. The 2026-09-25
real-value table used 90 s, which contradicts its own proxy: a handed-back
SKU is ordered the way managers do today (last week's number), and today
was costed at 30 s per SKU."""

import pandas as pd
import yaml

from freshcall.case_gate import straddles_case_boundary

from run_redesign import prepare

STORES = {44: "data/backtest_results.parquet", 8: "data/backtest_results_store8.parquet"}
TODAY_SECONDS = (20, 30, 45)
REDESIGN_SECONDS = (5, 10, 15)
ROUTINE_SECONDS = 1
HANDED_BACK_SECONDS = (20, 30, 45, 90)
ANSWERED_SECONDS = 5  # a system answer: glance and confirm


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    sales = pd.read_parquet("data/derived_perishable_train.parquet")
    for store, path in STORES.items():
        routine = prepare(store, path, cfg, sales)["routine"].mean()
        print(f"\nStore {store} (routine share {routine:.1%}) — minutes per 40-SKU night")
        print(f"{'':<28}" + "".join(f"{'today ' + str(t) + ' s':>13}" for t in TODAY_SECONDS))
        for r in REDESIGN_SECONDS:
            redesign_min = 40 * (routine * ROUTINE_SECONDS + (1 - routine) * r) / 60
            cells = "".join(f"{f'{redesign_min:.1f} vs {40 * t / 60:.0f}':>13}" for t in TODAY_SECONDS)
            print(f"{'redesign ' + str(r) + ' s/non-routine':<28}{cells}")

    cp, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]
    df = pd.read_parquet(STORES[44])
    share = sum(straddles_case_boundary(a, b, c, safety, on_hand, cp)
                for a, b, c in zip(df["p10"], df["p50"], df["p90"])) / len(df)
    print(f"\nStore 44, v2 case-straddle gate (hands back {share:.1%}) — minutes per 40-SKU night")
    for h in HANDED_BACK_SECONDS:
        minutes = 40 * (share * h + (1 - share) * ANSWERED_SECONDS) / 60
        print(f"  handed-back SKU {h:>2} s: {minutes:5.1f}   (today 30 s/SKU: {40 * 30 / 60:.1f}; "
              f"no hand-back {ANSWERED_SECONDS} s/SKU: {40 * ANSWERED_SECONDS / 60:.1f})")


if __name__ == "__main__":
    main()

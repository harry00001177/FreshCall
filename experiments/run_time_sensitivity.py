"""Manager-time sensitivity (DECISIONS.md 2026-09-25): every timing in the
Problem Statement is an unmeasured guess, so show minutes per 40-SKU night
across a grid of guesses instead of one number. Routine share comes from
the stored backtests (stores 44 and 8); routine SKUs are assumed to take
1 s (collapsed standing orders)."""

import pandas as pd
import yaml

from run_redesign import prepare

STORES = {44: "data/backtest_results.parquet", 8: "data/backtest_results_store8.parquet"}
TODAY_SECONDS = (20, 30, 45)
REDESIGN_SECONDS = (5, 10, 15)
ROUTINE_SECONDS = 1


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


if __name__ == "__main__":
    main()

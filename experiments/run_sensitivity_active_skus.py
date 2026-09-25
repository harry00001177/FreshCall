"""Sensitivity check (pre-registered, DECISIONS.md 2026-09-24): recompute
the gate results from stored predictions, excluding SKUs whose last sale
in that store was before the first test window. The original,
pre-registered numbers remain the primary results; this is reported
alongside them. No refit, no other exclusion."""

import pandas as pd
import yaml

from freshcall.backtest import FOLDS, recompute_abstain
from run_case_gate_experiment import apply_case_gate, print_block

STORES = {44: "data/backtest_results.parquet", 49: "data/backtest_results_store49.parquet"}
FIRST_TEST_DAY = FOLDS[0]["test_start"]


def inactive_skus(sales: pd.DataFrame, store_nbr: int) -> set:
    last_sale = sales[sales["store_nbr"] == store_nbr].groupby("item_nbr")["date"].max()
    return set(last_sale[last_sale < FIRST_TEST_DAY].index)


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    sales = pd.read_parquet("data/derived_perishable_train.parquet", columns=["date", "store_nbr", "item_nbr"])

    for store_nbr, path in STORES.items():
        results = pd.read_parquet(path)
        dead = inactive_skus(sales, store_nbr)
        active = results[~results["item_nbr"].isin(dead)]
        dropped = results["item_nbr"].isin(dead).sum()
        print(f"\n######## Store {store_nbr}: excluded {results['item_nbr'][results['item_nbr'].isin(dead)].nunique()} "
              f"inactive SKUs ({dropped} SKU-days); {len(active)} SKU-days remain ########")
        rows = active.to_dict("records")
        print_block(f"store {store_nbr} ACTIVE SKUs, case-straddle gate", apply_case_gate(rows, cfg), cfg)
        for th in (0.60, 1.00):
            print_block(f"store {store_nbr} ACTIVE SKUs, rel_width gate at {th}", recompute_abstain(rows, th), cfg)


if __name__ == "__main__":
    main()

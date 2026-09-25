"""Look-ahead sensitivity (pre-registered, DECISIONS.md 2026-09-25): SKU
selection computed density over each SKU's full history, test windows
included. Drop the SKUs that only qualify because of test-period sales
(in the current list, not in a list built from data up to 2017-05-15)
and recompute from stored predictions. Originals remain primary."""

import pandas as pd
import yaml

from freshcall.backtest import recompute_abstain
from prepare_data import density_table, store_candidates, whole_unit_items
from run_case_gate_experiment import apply_case_gate, print_block

STORES = {44: "data/backtest_results.parquet", 49: "data/backtest_results_store49.parquet"}
LAST_PRE_TEST_DAY = "2017-05-15"


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    sales = pd.read_parquet("data/derived_perishable_train.parquet")
    sales = sales[sales["item_nbr"].isin(whole_unit_items(sales))]
    full_density = density_table(sales)
    past_density = density_table(sales[sales["date"] <= LAST_PRE_TEST_DAY])

    for store, path in STORES.items():
        current = set(store_candidates(full_density, store)["item_nbr"])
        past_only = set(store_candidates(past_density, store)["item_nbr"])
        lookahead = current - past_only
        results = pd.read_parquet(path)
        kept = results[~results["item_nbr"].isin(lookahead)]
        print(f"\n######## Store {store}: {len(lookahead)} look-ahead SKUs {sorted(lookahead)} dropped "
              f"({len(results) - len(kept)} SKU-days); {len(kept)} remain ########")
        rows = kept.to_dict("records")
        print_block(f"store {store} no look-ahead SKUs, case-straddle", apply_case_gate(rows, cfg), cfg)
        for th in (0.60, 1.00):
            print_block(f"store {store} no look-ahead SKUs, rel_width {th}", recompute_abstain(rows, th), cfg)


if __name__ == "__main__":
    main()

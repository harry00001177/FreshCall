"""Phase 2: run the 3-fold rolling-origin backtest across a set of SKUs at
store 44, and report Case Match Rate, naive-baseline CMR (on the same
auto-answered subset -- the instructor's fix), abstain rate, and interval
coverage, per fold."""

import sys
import time

import pandas as pd
import yaml

from freshcall.backtest import FOLDS, evaluate_sku_fold, summarize_fold


def run_backtest(sku_list: list[int], store_nbr: int, cfg: dict, raw_df: pd.DataFrame) -> pd.DataFrame:
    all_rows = []
    for i, item_nbr in enumerate(sku_list):
        for fold in FOLDS:
            rows = evaluate_sku_fold(raw_df, store_nbr, item_nbr, fold, cfg)
            all_rows.extend(rows)
        if (i + 1) % 10 == 0:
            print(f"  ...{i + 1}/{len(sku_list)} SKUs done", file=sys.stderr)
    return pd.DataFrame(all_rows)


def main(sku_parquet: str, n_skus: int | None = None):
    t0 = time.time()
    cfg = yaml.safe_load(open("config.yaml"))
    store_nbr = cfg["slice"]["store_nbr"]

    sku_df = pd.read_parquet(sku_parquet)
    sku_list = sku_df["item_nbr"].tolist()
    if n_skus:
        sku_list = sku_list[:n_skus]

    print(f"Loading raw sales data...")
    raw_df = pd.read_parquet("data/derived_perishable_train.parquet")

    print(f"Running backtest on {len(sku_list)} SKUs x {len(FOLDS)} folds...")
    all_rows_df = run_backtest(sku_list, store_nbr, cfg, raw_df)
    elapsed = time.time() - t0

    print(f"\nDone in {elapsed:.0f}s. Total SKU-day predictions: {len(all_rows_df)}\n")

    if all_rows_df.empty:
        print("No results -- every SKU had insufficient history for every fold.")
        return all_rows_df

    print(f"{'Fold':<16} {'N':>6} {'N_ans':>7} {'AbstainRate':>12} {'ModelCMR':>10} {'NaiveCMR':>10} {'Coverage':>10}")
    for fold in FOLDS:
        fold_rows = all_rows_df[all_rows_df["fold"] == fold["name"]].to_dict("records")
        s = summarize_fold(fold_rows)
        model_cmr_str = f"{s['model_cmr']:.3f}" if s["model_cmr"] is not None else "N/A"
        naive_cmr_str = f"{s['naive_cmr']:.3f}" if s["naive_cmr"] is not None else "N/A"
        print(f"{fold['name']:<16} {s['n']:>6} {s['n_answered']:>7} {s['abstain_rate']:>12.3f} "
              f"{model_cmr_str:>10} {naive_cmr_str:>10} {s['coverage']:>10.3f}")

    all_rows_df.to_parquet("data/backtest_results.parquet", index=False)
    print("\nSaved raw results to data/backtest_results.parquet")
    return all_rows_df


if __name__ == "__main__":
    sku_parquet = sys.argv[1] if len(sys.argv) > 1 else "data/pilot_30_skus.parquet"
    n_skus = int(sys.argv[2]) if len(sys.argv) > 2 else None
    main(sku_parquet, n_skus)

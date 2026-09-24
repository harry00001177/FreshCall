"""Builds every derived data file the pipeline reads, from the raw Kaggle
CSVs in data/. Filter chain (Problem Statement §3.2, DECISIONS.md
2026-09-22): perishable -> sold only in whole units everywhere -> sales
density >= 0.7 within each SKU's own active span -> first sale on or
before 2015-06-01 (enough history for all 3 rolling-origin folds).

Usage: python prepare_data.py [out_dir]   (default: data)"""

import os
import sys

import numpy as np
import pandas as pd

DENSITY_THRESHOLD = 0.7
FIRST_SALE_CUTOFF = "2015-06-01"
DEV_STORE, CONFIRM_STORE, PILOT_SIZE = 44, 49, 30


def load_perishable_sales(data_dir: str) -> pd.DataFrame:
    items = pd.read_csv(f"{data_dir}/items.csv")
    perishable = set(items.loc[items["perishable"] == 1, "item_nbr"])
    chunks = pd.read_csv(
        f"{data_dir}/train.csv",
        usecols=["date", "store_nbr", "item_nbr", "unit_sales"],
        dtype={"store_nbr": "int16", "item_nbr": "int32", "unit_sales": "float32"},
        parse_dates=["date"],
        chunksize=3_000_000,
    )
    return pd.concat((c[c["item_nbr"].isin(perishable)] for c in chunks), ignore_index=True)


def whole_unit_items(sales: pd.DataFrame) -> set:
    """Items whose unit_sales is an integer on every row in every store —
    sold by count, so a case pack makes sense (weight-sold items don't)."""
    is_int = np.isclose(sales["unit_sales"], np.round(sales["unit_sales"]), atol=1e-6)
    frac = pd.Series(is_int).groupby(sales["item_nbr"].values).mean()
    return set(frac[frac == 1.0].index)


def density_table(sales: pd.DataFrame) -> pd.DataFrame:
    g = sales.groupby(["store_nbr", "item_nbr"])["date"].agg(["count", "min", "max"])
    g["span_days"] = (g["max"] - g["min"]).dt.days + 1
    g["density"] = g["count"] / g["span_days"]
    return g.reset_index()


def store_candidates(density: pd.DataFrame, store_nbr: int) -> pd.DataFrame:
    d = density[
        (density["store_nbr"] == store_nbr)
        & (density["density"] >= DENSITY_THRESHOLD)
        & (density["min"] <= FIRST_SALE_CUTOFF)
    ]
    return d[["item_nbr", "min", "max", "density"]].sort_values("density", ascending=False)


def main(out_dir: str = "data", data_dir: str = "data"):
    os.makedirs(out_dir, exist_ok=True)
    print("Filtering train.csv to perishable items (a few minutes)...")
    sales = load_perishable_sales(data_dir)
    sales.to_parquet(f"{out_dir}/derived_perishable_train.parquet", index=False)

    integer_sales = sales[sales["item_nbr"].isin(whole_unit_items(sales))]
    density = density_table(integer_sales)

    dev = store_candidates(density, DEV_STORE)
    dev.to_parquet(f"{out_dir}/full_426_skus.parquet", index=False)
    dev.head(PILOT_SIZE).to_parquet(f"{out_dir}/pilot_30_skus.parquet", index=False)
    store_candidates(density, CONFIRM_STORE).to_parquet(f"{out_dir}/store{CONFIRM_STORE}_candidates.parquet", index=False)
    print(f"Store {DEV_STORE}: {len(dev)} candidate SKUs; store {CONFIRM_STORE} candidates written.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")

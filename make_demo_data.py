"""Generates demo/demo_sales.csv: a synthetic 90-day sales series (store 0,
item 0) so `run_slice.py --demo` works without the Kaggle data, which may
not be redistributed. Synthetic on purpose; never used for any reported
result. Shape only loosely mimics a perishable SKU: a weekly pattern
(busier Fri-Sun), noise, whole units, and a few zero days."""

import os

import numpy as np
import pandas as pd

WEEKLY = {0: 0.9, 1: 0.85, 2: 0.9, 3: 1.0, 4: 1.25, 5: 1.4, 6: 1.2}  # Mon..Sun multipliers


def make_series(days: int = 90, base: float = 40.0, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2017-01-02", periods=days, freq="D")
    mean = np.array([base * WEEKLY[d.dayofweek] for d in dates])
    sales = np.maximum(0, np.round(rng.normal(mean, 0.2 * mean))).astype(int)
    sales[rng.choice(days, size=3, replace=False)] = 0  # a few no-sale days, as in real data
    return pd.DataFrame({"date": dates.date, "store_nbr": 0, "item_nbr": 0, "unit_sales": sales})


if __name__ == "__main__":
    os.makedirs("demo", exist_ok=True)
    make_series().to_csv("demo/demo_sales.csv", index=False)
    print("Wrote demo/demo_sales.csv")

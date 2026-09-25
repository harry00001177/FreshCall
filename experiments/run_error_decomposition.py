"""Error decomposition on both stores' saved backtest results (read-only).
Descriptive, not a hypothesis test: reports how the model's would-be
errors split into catchable vs uncaught (over- or under-ordered), and
whether uncaught errors concentrate on observed holidays."""

import pandas as pd
import yaml

from freshcall.decomposition import error_bucket, observed_holidays

RESULTS = {44: "data/backtest_results.parquet", 49: "data/backtest_results_store49.parquet"}


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    stores = pd.read_csv("data/stores.csv").set_index("store_nbr")
    holidays = pd.read_csv("data/holidays_events.csv", parse_dates=["date"])

    for store_nbr, path in RESULTS.items():
        df = pd.read_parquet(path)
        city, state = stores.loc[store_nbr, "city"], stores.loc[store_nbr, "state"]
        hol = observed_holidays(holidays, city, state)

        df["bucket"] = [
            error_bucket(r.p10, r.p50, r.p90, r.hindsight, cfg["safety"], cfg["on_hand"], cfg["case_pack"])
            for r in df.itertuples()
        ]
        df["holiday"] = df["date"].isin(hol)
        errors = df[df["bucket"].notna()]
        uncaught = errors[errors["bucket"] != "catchable"]

        print(f"\n== Store {store_nbr} ({city}) ==")
        print(f"SKU-days: {len(df)}   would-be errors: {len(errors)} ({len(errors) / len(df):.1%} of SKU-days)")
        for b in ["catchable", "uncaught_over", "uncaught_under"]:
            n = (errors["bucket"] == b).sum()
            print(f"  {b:<16}{n:>7}  {n / len(errors):>6.1%} of errors")

        hol_days = sorted(d.date() for d in hol if df["date"].min() <= d <= df["date"].max())
        print(f"Observed holidays in test windows: {len(hol_days)} days {hol_days}")
        if hol_days:
            print(f"  share of SKU-days on holidays:        {df['holiday'].mean():.1%}")
            print(f"  share of uncaught errors on holidays: {uncaught['holiday'].mean():.1%}")
            print(f"  error rate on holiday SKU-days:       {df.loc[df['holiday'], 'bucket'].notna().mean():.1%}")
            print(f"  error rate on other SKU-days:         {df.loc[~df['holiday'], 'bucket'].notna().mean():.1%}")


if __name__ == "__main__":
    main()

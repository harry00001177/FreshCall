"""Newsvendor test, exactly as pre-registered and then amended before store
45 was touched (DECISIONS.md 2026-09-28, commits 50d3d51 and 703de07):
order the whole case count with the lowest expected cost over the 9
quantile forecasts, and compare its cost (r x units short + units over,
per 40-SKU night) with the P50 order and with last week's same day. Store 44 (and 8) = development;
store 45 = confirmation (success judged there only, run once).

  python experiments/run_newsvendor.py backtest 45   # fit + save, prints no metrics
  python experiments/run_newsvendor.py evaluate 44 8 # score saved predictions"""

import os
import sys
from functools import partial
from multiprocessing import Pool

import pandas as pd
import yaml

from freshcall.backtest import FOLDS, evaluate_sku_fold_quantiles
from freshcall.features import build_daily_grid
from freshcall.newsvendor import QUANTILES, floor_applies, newsvendor_cases, order_cost
from freshcall.order import recommended_cases
from freshcall.redesign import is_routine, past_max, unit_errors
from prepare_data import store_candidates, density_table, whole_unit_items

RATIOS = [0.25, 0.5, 1, 2, 4, 9]
CONFIRM_STORE = 45
SKU_FILES = {44: "data/full_426_skus.parquet", 8: "data/store8_candidates.parquet",
             45: "data/store45_candidates.parquet"}


def result_path(store: int) -> str:
    return f"data/newsvendor_store{store}.parquet"


def sku_list(store: int, sales: pd.DataFrame) -> list[int]:
    path = SKU_FILES[store]
    if not os.path.exists(path):  # same rule as every other store (prepare_data.py)
        integer_sales = sales[sales["item_nbr"].isin(whole_unit_items(sales))]
        store_candidates(density_table(integer_sales), store).to_parquet(path, index=False)
    return pd.read_parquet(path)["item_nbr"].tolist()


def _one_sku(item: int, store: int, cfg: dict, raw: pd.DataFrame) -> list[dict]:
    return [r for fold in FOLDS for r in evaluate_sku_fold_quantiles(raw, store, item, fold, cfg, QUANTILES)]


def backtest(store: int, cfg: dict, sales: pd.DataFrame) -> None:
    skus = sku_list(store, sales)
    raw = sales[sales["store_nbr"] == store]
    print(f"Store {store}: {len(skus)} SKUs x {len(FOLDS)} folds x {len(QUANTILES)} quantiles ...")
    with Pool() as pool:
        parts = pool.map(partial(_one_sku, store=store, cfg=cfg, raw=raw), skus)
    df = pd.DataFrame([r for p in parts for r in p])
    df.to_parquet(result_path(store), index=False)
    print(f"Saved {len(df)} SKU-days to {result_path(store)} (no metrics printed).")


def add_orders(df: pd.DataFrame, store: int, cfg: dict, sales: pd.DataFrame) -> pd.DataFrame:
    cp, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]
    s = sales[sales["store_nbr"] == store]
    routine, floor = [], []
    for item, g in df.groupby("item_nbr"):
        sku = s[s["item_nbr"] == item][["date", "unit_sales"]]
        grid = build_daily_grid(sku, start=sku["date"].min(), end="2017-08-15").set_index("date")["unit_sales"]
        routine.append(pd.Series(past_max(grid).reindex(g["date"]).values, index=g.index))
        sold_7 = grid.shift(1).rolling(7).apply(floor_applies, raw=True)  # days before the order date only
        floor.append(pd.Series(sold_7.reindex(g["date"]).values == 1, index=g.index))
    df["routine"] = [is_routine(v, cp) for v in pd.concat(routine)]
    df["floor"] = pd.concat(floor)

    scenarios = df[[f"q{q}" for q in QUANTILES]].to_numpy()
    df["order_last_week"] = df["naive"]
    df["order_p50"] = [recommended_cases(v, safety, on_hand, cp) for v in df["q0.5"]]
    for r in RATIOS:
        df[f"order_nv{r}"] = [newsvendor_cases(sc, r, cp) for sc in scenarios]
        df[f"order_floor{r}"] = df[f"order_nv{r}"].where(~df["floor"], df[f"order_nv{r}"].clip(lower=1))
    for col in [c for c in df.columns if c.startswith("order_")]:
        over_short = [unit_errors(o, a, cp) for o, a in zip(df[col], df["actual"])]
        df[f"over_{col[6:]}"], df[f"short_{col[6:]}"] = zip(*over_short)
    return df


def cost_per_night(part: pd.DataFrame, policy: str, ratio: float) -> float:
    return order_cost(part[f"over_{policy}"], part[f"short_{policy}"], ratio).mean() * 40


def report(store: int, label: str, df: pd.DataFrame) -> dict:
    print(f"\n######## Store {store} ({label}): {len(df)} SKU-days, routine {df['routine'].mean():.1%}, "
          f"floor applies {df['floor'].mean():.1%} ########")
    print("\nCalibration: share of SKU-days with actual <= the quantile's prediction")
    print("  " + "  ".join(f"q{q}: {(df['actual'] <= df[f'q{q}']).mean():.1%}" for q in QUANTILES))

    verdicts = {}
    for ratio in RATIOS:
        nv, fl = f"nv{ratio}", f"floor{ratio}"
        print(f"\nratio {ratio:g} (one unit short costs {ratio:g}x one unit wasted)")
        print(f"  {'subset':<13}{'policy':<12}{'cost/40':>9}{'over/40':>9}{'short/40':>10}{'0-case days':>13}")
        for name, part in (("all", df), ("non-routine", df[~df["routine"]]), ("routine", df[df["routine"]])):
            for pol, tag in (("last_week", "last week"), ("p50", "P50 (today)"), (nv, "newsvendor"),
                             (fl, "nv + floor")):
                print(f"  {name:<13}{tag:<12}{cost_per_night(part, pol, ratio):>9.1f}"
                      f"{part[f'over_{pol}'].mean() * 40:>9.1f}{part[f'short_{pol}'].mean() * 40:>10.1f}"
                      f"{(part[f'order_{pol}'] == 0).mean():>13.1%}")
        changed = (df[f"order_{fl}"] != df[f"order_{nv}"]).mean()
        print(f"  floor changes {changed:.1%} of SKU-days")
        wins = {}
        for scope in ["pooled"] + [f["name"] for f in FOLDS]:
            part = df if scope == "pooled" else df[df["fold"] == scope]
            wins[scope] = cost_per_night(part, nv, ratio) < cost_per_night(part, "p50", ratio)
        folds_won = sum(wins[f["name"]] for f in FOLDS)
        verdicts[ratio] = wins["pooled"] and folds_won >= 2
        print(f"  newsvendor < P50 (all SKUs): pooled [{'yes' if wins['pooled'] else 'no'}], "
              f"folds {folds_won}/3 -> {'pass' if verdicts[ratio] else 'FAIL'}")
    return verdicts


def main():
    mode, stores = sys.argv[1], [int(s) for s in sys.argv[2:]]
    cfg = yaml.safe_load(open("config.yaml"))
    sales = pd.read_parquet("data/derived_perishable_train.parquet")
    for store in stores:
        if mode == "backtest":
            if os.path.exists(result_path(store)):
                sys.exit(f"{result_path(store)} exists -- pre-registered: no second run.")
            backtest(store, cfg, sales)
            continue
        label = "CONFIRMATION" if store == CONFIRM_STORE else "development"
        verdicts = report(store, label, add_orders(pd.read_parquet(result_path(store)), store, cfg, sales))
        if label == "CONFIRMATION":
            passed = [r for r, ok in verdicts.items() if ok]
            outcome = "SUCCESS" if len(passed) == len(verdicts) else ("PARTIAL" if passed else "FAIL")
            print(f"\nPre-registered criterion (store {store}): newsvendor beats P50 on cost, pooled and >= 2/3 "
                  f"folds, at every ratio (1 included). Passed at {passed or 'none'} -> {outcome}")


if __name__ == "__main__":
    main()

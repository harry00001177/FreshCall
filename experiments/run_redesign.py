"""Redesign test, exactly as pre-registered (DECISIONS.md 2026-09-25,
commit 62f2d1d): "an order for every SKU + its likely range", routine SKUs
as standing orders, compared with today's practice (last week's same day)
per 40-SKU night. Store 44 = development; store 8 = confirmation (success
judged there only). Reads stored backtest predictions; writes nothing.

"Widest-range quarter": non-routine SKU-days sorted by range width in cases
(descending), ties broken by P90 - P10 in units (descending); the first 25%."""

import pandas as pd
import yaml

from freshcall.backtest import FOLDS
from freshcall.features import build_daily_grid
from freshcall.redesign import case_range, is_routine, past_max, unit_errors

STORES = {44: ("development", "data/backtest_results.parquet"),
          8: ("CONFIRMATION", "data/backtest_results_store8.parquet")}
SECONDS = {"today": 30, "non_routine": 5, "routine": 1}  # ASSUMPTIONS, never measured


def prepare(store: int, path: str, cfg: dict, sales: pd.DataFrame) -> pd.DataFrame:
    cp, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]
    df = pd.read_parquet(path)
    s = sales[sales["store_nbr"] == store]
    parts = []
    for item, g in df.groupby("item_nbr"):
        sku = s[s["item_nbr"] == item][["date", "unit_sales"]]
        grid = build_daily_grid(sku, start=sku["date"].min(), end="2017-08-15").set_index("date")["unit_sales"]
        parts.append(pd.Series(past_max(grid).reindex(g["date"]).values, index=g.index))
    df["past28_max"] = pd.concat(parts)
    df["routine"] = [is_routine(v, cp) for v in df["past28_max"]]
    lo_mid_hi = [case_range(a, b, c, safety, on_hand, cp) for a, b, c in zip(df["p10"], df["p50"], df["p90"])]
    df["lo"], df["order"], df["hi"] = zip(*lo_mid_hi)
    for who, col in (("today", "naive"), ("redesign", "order")):
        ue = [unit_errors(o, a, cp) for o, a in zip(df[col], df["actual"])]
        df[f"{who}_over"], df[f"{who}_short"] = zip(*ue)
        df[f"{who}_wrong"] = df[col] != df["hindsight"]
    return df


def per_night(part: pd.DataFrame, who: str) -> dict:
    return {"wrong": part[f"{who}_wrong"].mean() * 40, "over": part[f"{who}_over"].mean() * 40,
            "short": part[f"{who}_short"].mean() * 40}


def minutes(part: pd.DataFrame, who: str) -> float:
    if who == "today":
        return 40 * SECONDS["today"] / 60
    r = part["routine"].mean()
    return 40 * (r * SECONDS["routine"] + (1 - r) * SECONDS["non_routine"]) / 60


def report(store: int, label: str, df: pd.DataFrame) -> dict:
    print(f"\n######## Store {store} ({label}): {len(df)} SKU-days, routine {df['routine'].mean():.1%} ########")
    print(f"{'subset':<13}{'policy':<10}{'wrong/40':>10}{'units over/40':>15}{'units short/40':>16}{'minutes/40':>12}")
    for name, part in (("non-routine", df[~df["routine"]]), ("routine", df[df["routine"]]), ("all", df)):
        for who in ("today", "redesign"):
            m = per_night(part, who)
            print(f"{name:<13}{who:<10}{m['wrong']:>10.1f}{m['over']:>15.1f}{m['short']:>16.1f}{minutes(part, who):>12.1f}")

    nr = df[~df["routine"]].copy()
    width = nr["hi"] - nr["lo"]
    inside = ((nr["lo"] <= nr["hindsight"]) & (nr["hindsight"] <= nr["hi"])).mean()
    print(f"\nrange (non-routine): needed cases inside it {inside:.1%}; width 0 / 1 / 2+ cases: "
          f"{(width == 0).mean():.1%} / {(width == 1).mean():.1%} / {(width >= 2).mean():.1%}")
    nr["width"], nr["unit_width"] = width, nr["p90"] - nr["p10"]
    ranked = nr.sort_values(["width", "unit_width"], ascending=False)
    top = ranked.head(len(ranked) // 4)
    share = top["redesign_wrong"].sum() / nr["redesign_wrong"].sum()
    print(f"share of redesign's case errors in the widest-range quarter: {share:.1%} (25% if width told us nothing)")

    print(f"\nnon-routine, per fold:   {'today wrong':>12}{'redesign wrong':>15}{'today |unit err|':>18}{'redesign |unit err|':>21}")
    verdicts = {}
    for scope in ["pooled"] + [f["name"] for f in FOLDS]:
        part = nr if scope == "pooled" else nr[nr["fold"] == scope]
        t, r = per_night(part, "today"), per_night(part, "redesign")
        tu, ru = t["over"] + t["short"], r["over"] + r["short"]
        verdicts[scope] = r["wrong"] < t["wrong"] and ru < tu
        print(f"  {scope:<22}{t['wrong']:>12.1f}{r['wrong']:>15.1f}{tu:>18.1f}{ru:>21.1f}   "
              f"{'beats today on both' if verdicts[scope] else 'does NOT beat today on both'}")
    return verdicts


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    sales = pd.read_parquet("data/derived_perishable_train.parquet")
    print("Timings are ASSUMPTIONS (today 30 s/SKU; redesign 5 s non-routine, 1 s routine).")
    print("Redesign = manager accepts every suggestion (a floor: real manager input can't be measured here).")
    for store, (label, path) in STORES.items():
        verdicts = report(store, label, prepare(store, path, cfg, sales))
        if label == "CONFIRMATION":
            folds_ok = sum(verdicts[f["name"]] for f in FOLDS)
            ok = verdicts["pooled"] and folds_ok >= 2
            print(f"\nPre-registered criterion (store {store}, non-routine): beats today on case errors AND "
                  f"total unit error, pooled [{'yes' if verdicts['pooled'] else 'no'}] and >= 2 of 3 folds "
                  f"[{folds_ok}/3] -> {'SUCCESS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()

"""Case-straddle gate experiment, exactly as pre-registered in DECISIONS.md
(2026-09-24, commit a708b61). Store 44 = development (reads the existing
results file, never writes it). Store 49 = confirmation (backtest run
once, saved to its own file). Success is judged on store 49 only."""

import os

import pandas as pd
import yaml

from freshcall.backtest import FOLDS, abstention_precision, error_base_rate, recompute_abstain
from freshcall.case_gate import straddles_case_boundary
from report_backtest import with_cases
from run_backtest import run_backtest

DEV_RESULTS = "data/backtest_results.parquet"
CONFIRM_STORE = 49
CONFIRM_SKUS = "data/store49_candidates.parquet"
CONFIRM_RESULTS = "data/backtest_results_store49.parquet"


def apply_case_gate(rows: list[dict], cfg: dict) -> list[dict]:
    return [
        {**r, "abstain": straddles_case_boundary(r["p10"], r["p50"], r["p90"], cfg["safety"], cfg["on_hand"], cfg["case_pack"])}
        for r in rows
    ]


def metrics(rows: list[dict], cfg: dict) -> dict:
    rows = with_cases(rows, cfg)
    answered = [r for r in rows if not r["abstain"]]
    model = sum(r["cases"] == r["hindsight"] for r in answered) / len(answered) if answered else None
    naive = sum(r["naive"] == r["hindsight"] for r in answered) / len(answered) if answered else None
    prec = abstention_precision(rows, cfg["case_pack"], cfg["safety"], cfg["on_hand"])
    base = error_base_rate(rows, cfg["case_pack"], cfg["safety"], cfg["on_hand"])
    return {
        "n": len(rows),
        "abstain": 1 - len(answered) / len(rows),
        "model_cmr": model, "naive_cmr": naive,
        "rel_impr": (model / naive - 1) if model is not None and naive else None,
        "prec": prec, "base": base,
        "lift": prec / base if prec is not None and base else None,
    }


def f(x, pct=False):
    if x is None:
        return "N/A"
    return f"{x * 100:+.1f}%" if pct else f"{x:.3f}"


def print_block(title: str, rows: list[dict], cfg: dict) -> dict:
    print(f"\n== {title} ==")
    print(f"{'scope':<16}{'N':>7}{'abstain':>9}{'modelCMR':>10}{'naiveCMR':>10}{'relImpr':>9}"
          f"{'abstPrec':>10}{'errBase':>9}{'lift':>7}")
    per_fold = {}
    for scope in ["pooled"] + [fo["name"] for fo in FOLDS]:
        subset = rows if scope == "pooled" else [r for r in rows if r["fold"] == scope]
        m = metrics(subset, cfg)
        per_fold[scope] = m
        print(f"{scope:<16}{m['n']:>7}{m['abstain']:>9.3f}{f(m['model_cmr']):>10}{f(m['naive_cmr']):>10}"
              f"{f(m['rel_impr'], pct=True):>9}{f(m['prec']):>10}{f(m['base']):>9}{f(m['lift']):>7}")
    return per_fold


def main():
    cfg = yaml.safe_load(open("config.yaml"))

    dev_rows = pd.read_parquet(DEV_RESULTS).to_dict("records")
    print_block("DEVELOPMENT: store 44, case-straddle gate", apply_case_gate(dev_rows, cfg), cfg)

    if not os.path.exists(CONFIRM_RESULTS):
        skus = pd.read_parquet(CONFIRM_SKUS)["item_nbr"].tolist()
        raw = pd.read_parquet("data/derived_perishable_train.parquet")
        print(f"\nRunning confirmation backtest: store {CONFIRM_STORE}, {len(skus)} SKUs x {len(FOLDS)} folds...")
        run_backtest(skus, CONFIRM_STORE, cfg, raw).to_parquet(CONFIRM_RESULTS, index=False)
    conf_rows = pd.read_parquet(CONFIRM_RESULTS).to_dict("records")

    result = print_block(f"CONFIRMATION: store {CONFIRM_STORE}, case-straddle gate", apply_case_gate(conf_rows, cfg), cfg)
    for th in (0.60, 1.00):
        print_block(f"Replication: store {CONFIRM_STORE}, rel_width gate at {th}", recompute_abstain(conf_rows, th), cfg)

    pooled_ok = result["pooled"]["lift"] is not None and result["pooled"]["lift"] > 1.0
    folds_ok = sum(1 for fo in FOLDS if (result[fo["name"]]["lift"] or 0) > 1.0)
    verdict = "SUCCESS" if pooled_ok and folds_ok >= 2 else "FAIL"
    print(f"\nPre-registered criterion (store {CONFIRM_STORE}): pooled lift > 1.0 "
          f"[{'yes' if pooled_ok else 'no'}] AND >= 2 of 3 folds lift > 1.0 [{folds_ok}/3] -> {verdict}")


if __name__ == "__main__":
    main()

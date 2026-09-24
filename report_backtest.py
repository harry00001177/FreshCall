"""Prints exactly the tables pre-registered in DECISIONS.md (2026-09-24),
from a saved backtest results file. Everything is recomputed from the
stored P10/P50/P90 so any threshold can be reported from one run."""

import sys

import pandas as pd
import yaml

from freshcall.backtest import (
    FOLDS, abstention_precision, error_base_rate, recompute_abstain, summarize_fold,
)
from freshcall.order import recommended_cases

SPLIT_THRESHOLDS = [0.60, 1.00]


def with_cases(rows: list[dict], cfg: dict) -> list[dict]:
    return [
        {**r, "cases": None if r["abstain"] else recommended_cases(r["p50"], cfg["safety"], cfg["on_hand"], cfg["case_pack"])}
        for r in rows
    ]


def fmt(x):
    return "N/A" if x is None else f"{x:.3f}"


def cmr_pair(rows: list[dict]) -> tuple[int, str, str]:
    answered = [r for r in rows if not r["abstain"]]
    if not answered:
        return 0, "N/A", "N/A"
    model = sum(r["cases"] == r["hindsight"] for r in answered) / len(answered)
    naive = sum(r["naive"] == r["hindsight"] for r in answered) / len(answered)
    return len(answered), fmt(model), fmt(naive)


def main(results_path: str):
    cfg = yaml.safe_load(open("config.yaml"))
    cp, safety, on_hand = cfg["case_pack"], cfg["safety"], cfg["on_hand"]
    base_rows = pd.read_parquet(results_path).to_dict("records")
    print(f"{results_path}: {len(base_rows)} SKU-day predictions\n")

    t = cfg["gate"]["rel_width_threshold"]
    rows = with_cases(recompute_abstain(base_rows, t), cfg)
    print(f"== Per fold at configured threshold {t} ==")
    print(f"{'fold':<16}{'N':>7}{'N_ans':>7}{'abstain':>9}{'modelCMR':>10}{'naiveCMR':>10}{'coverage':>10}")
    for fold in FOLDS:
        s = summarize_fold([r for r in rows if r["fold"] == fold["name"]])
        print(f"{fold['name']:<16}{s['n']:>7}{s['n_answered']:>7}{s['abstain_rate']:>9.3f}"
              f"{fmt(s['model_cmr']):>10}{fmt(s['naive_cmr']):>10}{s['coverage']:>10.3f}")

    print("\n== Threshold sweep (all folds pooled) ==")
    print(f"{'thresh':>7}{'abstain':>9}{'N_ans':>7}{'modelCMR':>10}{'naiveCMR':>10}{'coverage':>10}"
          f"{'abstPrec':>10}{'errBase':>9}{'lift':>7}")
    for th in cfg["gate"]["sweep_thresholds"]:
        rows = with_cases(recompute_abstain(base_rows, th), cfg)
        s = summarize_fold(rows)
        prec = abstention_precision(rows, cp, safety, on_hand)
        base = error_base_rate(rows, cp, safety, on_hand)
        lift = f"{prec / base:.2f}x" if prec is not None and base else "N/A"
        print(f"{th:>7.2f}{s['abstain_rate']:>9.3f}{s['n_answered']:>7}{fmt(s['model_cmr']):>10}"
              f"{fmt(s['naive_cmr']):>10}{s['coverage']:>10.3f}{fmt(prec):>10}{fmt(base):>9}{lift:>7}")

    for th in SPLIT_THRESHOLDS:
        rows = with_cases(recompute_abstain(base_rows, th), cfg)
        print(f"\n== Splits at threshold {th} (answered rows; N, modelCMR, naiveCMR) ==")
        splits = [
            ("P50 < 1", lambda r: r["p50"] < 1),
            ("P50 >= 1", lambda r: r["p50"] >= 1),
            ("hindsight 0", lambda r: r["hindsight"] == 0),
            ("hindsight 1-2", lambda r: 1 <= r["hindsight"] <= 2),
            ("hindsight 3+", lambda r: r["hindsight"] >= 3),
        ]
        for label, pred in splits:
            n, m, nv = cmr_pair([r for r in rows if pred(r)])
            print(f"  {label:<14}{n:>7}{m:>10}{nv:>10}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/backtest_results.parquet")

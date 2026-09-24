"""Case selection for the L1/L2 explanation harness (pre-registered,
DECISIONS.md 2026-09-24): 4 confident / 3 borderline-but-answered / 3
abstained, by rel_width against the gate threshold, fixed seed."""

import pandas as pd

CONFIDENT_BELOW = 0.30


def select_cases(results: pd.DataFrame, threshold: float, seed: int = 42) -> pd.DataFrame:
    df = results.copy()
    df["rel_width"] = (df["p90"] - df["p10"]) / df["p50"].clip(lower=1)
    strata = [
        ("confident", df["rel_width"] < CONFIDENT_BELOW, 4),
        ("borderline", (df["rel_width"] >= CONFIDENT_BELOW) & (df["rel_width"] <= threshold), 3),
        ("abstain", df["rel_width"] > threshold, 3),
    ]
    picked = [df[mask].sample(n=k, random_state=seed).assign(stratum=name) for name, mask, k in strata]
    return pd.concat(picked, ignore_index=True)

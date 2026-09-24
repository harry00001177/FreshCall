"""Case selection for the L1/L2 explanation harness (pre-registered,
DECISIONS.md 2026-09-24): 4 confident / 3 borderline-but-answered / 3
abstained, by rel_width against the gate threshold, fixed seed."""

import pandas as pd

CONFIDENT_BELOW = 0.30


def select_cases(results: pd.DataFrame, threshold: float, seed: int = 42, counts=(4, 3, 3)) -> pd.DataFrame:
    """`counts` = cases drawn from (confident, borderline, abstain)."""
    df = results.copy()
    df["rel_width"] = (df["p90"] - df["p10"]) / df["p50"].clip(lower=1)
    masks = [
        ("confident", df["rel_width"] < CONFIDENT_BELOW),
        ("borderline", (df["rel_width"] >= CONFIDENT_BELOW) & (df["rel_width"] <= threshold)),
        ("abstain", df["rel_width"] > threshold),
    ]
    picked = [
        df[mask].sample(n=k, random_state=seed).assign(stratum=name)
        for (name, mask), k in zip(masks, counts) if k > 0
    ]
    return pd.concat(picked, ignore_index=True)

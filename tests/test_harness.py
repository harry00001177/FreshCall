"""Explanation-harness case selection: stratified by rel_width against the
configured gate threshold, fixed seed, so the 10 cases are chosen by a
rule, not by eye (DECISIONS.md 2026-09-24 pre-registration)."""

import numpy as np
import pandas as pd

from freshcall.harness import select_cases


def _results(n=300, seed=0):
    rng = np.random.default_rng(seed)
    p50 = rng.uniform(5, 100, n)
    width = p50 * rng.uniform(0.05, 1.5, n)
    return pd.DataFrame({
        "item_nbr": rng.integers(1, 50, n),
        "date": pd.Timestamp("2017-06-01") + pd.to_timedelta(rng.integers(0, 60, n), unit="D"),
        "p10": p50 - width / 2, "p50": p50, "p90": p50 + width / 2,
    })


class TestSelectCases:
    def test_picks_4_3_3_across_the_three_strata(self):
        cases = select_cases(_results(), threshold=0.60, seed=42)
        assert cases["stratum"].value_counts().to_dict() == {"confident": 4, "borderline": 3, "abstain": 3}

    def test_strata_respect_the_gate_boundary(self):
        cases = select_cases(_results(), threshold=0.60, seed=42)
        assert (cases.loc[cases["stratum"] == "confident", "rel_width"] < 0.30).all()
        border = cases.loc[cases["stratum"] == "borderline", "rel_width"]
        assert ((border >= 0.30) & (border <= 0.60)).all()
        assert (cases.loc[cases["stratum"] == "abstain", "rel_width"] > 0.60).all()

    def test_counts_can_skip_a_stratum(self):
        cases = select_cases(_results(), threshold=0.60, seed=42, counts=(4, 3, 0))
        assert cases["stratum"].value_counts().to_dict() == {"confident": 4, "borderline": 3}

    def test_same_seed_gives_the_same_cases(self):
        a = select_cases(_results(), threshold=0.60, seed=42)
        b = select_cases(_results(), threshold=0.60, seed=42)
        assert a[["item_nbr", "date"]].equals(b[["item_nbr", "date"]])

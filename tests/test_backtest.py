"""Aggregation math for the multi-SKU backtest. The single most important
property tested here is the instructor-flagged fix (DECISIONS.md
2026-09-23): naive_seasonal's accuracy must be computed on the exact same
auto-answered subset as the model's, never on the full set of SKU-days."""

import pytest

from freshcall.backtest import FOLDS, abstention_precision, error_base_rate, recompute_abstain, summarize_fold


class TestSummarizeFold:
    def _row(self, abstain, cases, hindsight, naive, p10, p50, p90, actual):
        return {
            "abstain": abstain, "cases": cases, "hindsight": hindsight,
            "naive": naive, "p10": p10, "p50": p50, "p90": p90, "actual": actual,
        }

    def test_naive_cmr_is_computed_on_the_same_subset_as_model_cmr(self):
        rows = [
            # answered, model matches hindsight, naive does NOT
            self._row(False, cases=3, hindsight=3, naive=5, p10=1, p50=3, p90=5, actual=3),
            self._row(False, cases=4, hindsight=4, naive=6, p10=2, p50=4, p90=6, actual=4),
            # abstained -- naive matches hindsight here, but this row must be
            # EXCLUDED from naive_cmr, or naive_cmr would look artificially
            # inflated by an "easy" case the model itself routed away
            self._row(True, cases=None, hindsight=7, naive=7, p10=1, p50=7, p90=20, actual=7),
        ]
        summary = summarize_fold(rows)
        # on the 2 answered rows: model got both right (2/2=1.0), naive got 0/2=0.0
        assert summary["model_cmr"] == 1.0
        assert summary["naive_cmr"] == 0.0
        assert summary["n_answered"] == 2
        assert summary["abstain_rate"] == pytest.approx(1 / 3)

    def test_no_answered_rows_gives_none_not_a_crash(self):
        rows = [self._row(True, None, 5, 5, 1, 5, 10, 5)]
        summary = summarize_fold(rows)
        assert summary["model_cmr"] is None
        assert summary["naive_cmr"] is None
        assert summary["abstain_rate"] == 1.0

    def test_coverage_uses_all_rows_including_abstained(self):
        # coverage (P10-P90 containing actual) is a property of the interval
        # itself, independent of whether the gate fired -- must be measured
        # on every row, not just the answered subset
        rows = [
            self._row(False, 3, 3, 3, p10=1, p50=3, p90=5, actual=3),  # inside
            self._row(True, None, 3, 3, p10=1, p50=3, p90=5, actual=10),  # outside
        ]
        summary = summarize_fold(rows)
        assert summary["coverage"] == 0.5

    def test_empty_rows_does_not_crash(self):
        summary = summarize_fold([])
        assert summary["n"] == 0
        assert summary["abstain_rate"] == 0.0
        assert summary["coverage"] == 0.0


class TestAbstentionPrecision:
    """Abstention precision: of the SKU-days the gate abstained on, what
    share would the model's own P50 have gotten wrong (>=1 case off from
    hindsight_demand_order) if it had answered anyway? High precision means
    the gate is abstaining on genuinely hard days, not being cautious for
    no reason. See Problem Statement Section 7 and the abandon condition."""

    def _row(self, abstain, p50, hindsight):
        return {"abstain": abstain, "p50": p50, "hindsight": hindsight}

    def test_precision_counts_only_abstained_rows_that_would_have_erred(self):
        rows = [
            # abstained, P50=37 -> ceil(37/12)=4 cases, hindsight=4 -> would have been RIGHT
            self._row(True, p50=37, hindsight=4),
            # abstained, P50=10 -> ceil(10/12)=1 case, hindsight=4 -> would have been WRONG
            self._row(True, p50=10, hindsight=4),
            # not abstained -- excluded entirely from this metric
            self._row(False, p50=37, hindsight=4),
        ]
        precision = abstention_precision(rows, case_pack=12, safety=0, on_hand=0)
        assert precision == 0.5  # 1 of 2 abstained rows would have erred

    def test_none_when_nothing_was_abstained(self):
        rows = [self._row(False, p50=37, hindsight=4)]
        assert abstention_precision(rows, case_pack=12, safety=0, on_hand=0) is None


class TestErrorBaseRate:
    def test_measures_error_rate_across_every_row_regardless_of_abstain(self):
        rows = [
            {"abstain": True, "p50": 10, "hindsight": 4},   # would err
            {"abstain": False, "p50": 37, "hindsight": 4},  # would not err
        ]
        rate = error_base_rate(rows, case_pack=12, safety=0, on_hand=0)
        assert rate == 0.5

    def test_none_for_empty_rows(self):
        assert error_base_rate([], case_pack=12, safety=0, on_hand=0) is None


class TestRecomputeAbstain:
    def test_reapplies_a_different_threshold_from_stored_p10_p50_p90(self):
        rows = [{"p10": 50, "p50": 100, "p90": 150, "abstain": True}]  # rel_width=1.0, was abstain at 0.60
        recomputed = recompute_abstain(rows, threshold=1.2)
        assert recomputed[0]["abstain"] is False  # 1.0 no longer exceeds 1.2

    def test_does_not_mutate_the_original_rows(self):
        rows = [{"p10": 50, "p50": 100, "p90": 150, "abstain": True}]
        recompute_abstain(rows, threshold=1.2)
        assert rows[0]["abstain"] is True


class TestFolds:
    def test_three_folds_are_defined_and_chronologically_ordered(self):
        assert len(FOLDS) == 3
        ends = [f["test_end"] for f in FOLDS]
        assert ends == sorted(ends)

    def test_folds_do_not_overlap(self):
        for a, b in zip(FOLDS, FOLDS[1:]):
            assert a["test_end"] < b["test_start"]

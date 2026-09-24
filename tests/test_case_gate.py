"""Case-straddle gate: abstain when P10/P50/P90 don't all imply the same
case count. Uncertainty measured in the manager's decision units (cases),
not in demand units. Pre-registered in DECISIONS.md 2026-09-24."""

from freshcall.case_gate import straddles_case_boundary


class TestStraddlesCaseBoundary:
    def test_wide_interval_inside_one_case_is_not_abstained(self):
        # 25..35 units all round to 3 cases (case_pack=12): the decision is safe
        assert straddles_case_boundary(p10=25, p50=30, p90=35, safety=0, on_hand=0, case_pack=12) is False

    def test_narrow_interval_across_a_boundary_is_abstained(self):
        # 35.6 -> 36 units -> 3 cases; 37 -> 4 cases: tiny interval, different decision
        assert straddles_case_boundary(p10=35.6, p50=36.4, p90=37.0, safety=0, on_hand=0, case_pack=12) is True

    def test_only_p90_crossing_is_enough_to_abstain(self):
        assert straddles_case_boundary(p10=26, p50=30, p90=40, safety=0, on_hand=0, case_pack=12) is True

    def test_all_zero_forecast_is_not_abstained(self):
        assert straddles_case_boundary(p10=0, p50=0, p90=0.3, safety=0, on_hand=0, case_pack=12) is False

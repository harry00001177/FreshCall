"""The abstain gate is the only thing standing between a confident-looking
wrong number and a manager who trusts it — every branch gets a test."""

from freshcall.gate import decide_abstain, rel_width, should_abstain


def _cfg(gate_type):
    return {"case_pack": 12, "safety": 0, "on_hand": 0,
            "gate": {"type": gate_type, "rel_width_threshold": 0.60}}


class TestDecideAbstain:
    def test_case_straddle_config_uses_case_counts(self):
        # wide interval (rel_width ~0.33) inside one case: case-straddle answers
        assert decide_abstain(25, 30, 35, _cfg("case_straddle")) is False
        # narrow interval across 36/37 units: case-straddle abstains
        assert decide_abstain(35.6, 36.4, 37.0, _cfg("case_straddle")) is True

    def test_rel_width_config_uses_the_threshold(self):
        assert decide_abstain(50, 86, 140, _cfg("rel_width")) is True
        assert decide_abstain(35.6, 36.4, 37.0, _cfg("rel_width")) is False

    def test_unknown_gate_type_is_an_error_not_a_silent_default(self):
        import pytest
        with pytest.raises(ValueError):
            decide_abstain(1, 2, 3, _cfg("typo"))


class TestRelWidth:
    def test_narrow_interval_gives_small_rel_width(self):
        # p10=80, p50=86, p90=92 -> tight interval around the median
        assert rel_width(p10=80, p50=86, p90=92) == (92 - 80) / 86

    def test_uses_at_least_1_as_denominator_to_avoid_division_by_zero(self):
        # p50=0 must not raise ZeroDivisionError or blow up to infinity
        assert rel_width(p10=0, p50=0, p90=2) == 2.0  # (2-0)/max(0,1) == 2


class TestShouldAbstain:
    def test_abstains_when_rel_width_exceeds_threshold(self):
        assert should_abstain(p10=50, p50=86, p90=140, threshold=0.60) is True

    def test_does_not_abstain_when_rel_width_is_within_threshold(self):
        assert should_abstain(p10=80, p50=86, p90=92, threshold=0.60) is False

    def test_exactly_at_threshold_does_not_abstain(self):
        # rel_width == threshold is the boundary; gate fires only when it's exceeded
        p50 = 100
        p10, p90 = 70, 130  # rel_width = 0.60 exactly
        assert should_abstain(p10=p10, p50=p50, p90=p90, threshold=0.60) is False

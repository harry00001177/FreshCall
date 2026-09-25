"""The redesign (DECISIONS.md 2026-09-25, pre-registered): an order for
every SKU plus its likely range; routine SKUs as standing orders; value
measured in wrong orders and units wasted / short, not just case matches."""

import pandas as pd

from freshcall.redesign import case_range, is_routine, past_max, standing_order, unit_errors


class TestStandingOrder:
    def test_model_policy_uses_the_forecast(self):
        assert standing_order("model", model_cases=1, last_week_units=0, case_pack=12) == 1

    def test_last_week_policy_uses_last_weeks_sales(self):
        assert standing_order("last_week", model_cases=1, last_week_units=0, case_pack=12) == 0
        assert standing_order("last_week", model_cases=0, last_week_units=5, case_pack=12) == 1

    def test_unknown_policy_is_an_error(self):
        import pytest
        with pytest.raises(ValueError):
            standing_order("typo", model_cases=1, last_week_units=0, case_pack=12)


class TestIsRoutine:
    def test_routine_when_every_recent_day_fit_in_one_case(self):
        assert is_routine(12, case_pack=12) is True
        assert is_routine(13, case_pack=12) is False

    def test_missing_history_is_not_routine(self):
        assert is_routine(float("nan"), case_pack=12) is False


class TestPastMax:
    def test_uses_only_days_before_the_order_date(self):
        grid = pd.Series([1, 2, 30, 4], index=pd.date_range("2017-06-01", periods=4))
        # for 2017-06-04 with window 2: days 06-02 and 06-03 -> max 30; the day itself (4) excluded
        assert past_max(grid, window=2).loc["2017-06-04"] == 30
        # for 2017-06-03: days 06-01, 06-02 -> 2 (the 30 on 06-03 itself is not seen)
        assert past_max(grid, window=2).loc["2017-06-03"] == 2


class TestCaseRange:
    def test_range_brackets_the_order(self):
        assert case_range(p10=20, p50=30, p90=40, safety=0, on_hand=0, case_pack=12) == (2, 3, 4)

    def test_single_value_range(self):
        assert case_range(p10=25, p50=30, p90=35, safety=0, on_hand=0, case_pack=12) == (3, 3, 3)


class TestUnitErrors:
    def test_over_order_counts_wasted_units_even_when_cases_match(self):
        # sold 3, ordered 1 case: the case count is "right" but 9 units are wasted
        assert unit_errors(order_cases=1, actual=3, case_pack=12) == (9, 0)

    def test_short_order_counts_missing_units(self):
        assert unit_errors(order_cases=1, actual=20, case_pack=12) == (0, 8)

    def test_negative_actual_counts_as_zero_demand(self):
        assert unit_errors(order_cases=0, actual=-2, case_pack=12) == (0, 0)

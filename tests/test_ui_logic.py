"""Logic behind the one-page UI, kept out of Streamlit so it can be tested:
which SKUs and dates are shown, what counts as a valid order, and what
gets logged when the manager confirms or overrides."""

import pandas as pd

from freshcall.ui_logic import log_records, range_text, select_ui_skus, ui_dates, validate_order, widest_first


class TestSelectUiSkus:
    def test_draws_n_active_skus_with_a_fixed_seed(self):
        candidates = list(range(100))
        inactive = {0, 1, 2}
        a = select_ui_skus(candidates, inactive, n=40, seed=42)
        b = select_ui_skus(candidates, inactive, n=40, seed=42)
        assert a == b and len(a) == 40
        assert not set(a) & inactive


class TestUiDates:
    def test_every_14_days_inside_the_test_period(self):
        dates = ui_dates("2017-05-16", "2017-08-15", step_days=14)
        assert dates[0] == pd.Timestamp("2017-05-16")
        assert all((b - a).days == 14 for a, b in zip(dates, dates[1:]))
        assert dates[-1] <= pd.Timestamp("2017-08-15")


class TestValidateOrder:
    def test_ask_me_rows_need_the_managers_number(self):
        rows = [{"item_nbr": 1, "system_cases": None, "manager_cases": None}]
        assert validate_order(rows) == ["item 1: ASK ME — please enter a number of cases"]

    def test_negative_numbers_are_rejected(self):
        rows = [{"item_nbr": 2, "system_cases": 3, "manager_cases": -1}]
        assert validate_order(rows) == ["item 2: cases can't be negative"]

    def test_a_complete_order_has_no_errors(self):
        rows = [{"item_nbr": 1, "system_cases": None, "manager_cases": 2},
                {"item_nbr": 2, "system_cases": 3, "manager_cases": 3}]
        assert validate_order(rows) == []


class TestLogRecords:
    def test_marks_overrides_and_manager_calls(self):
        rows = [{"item_nbr": 1, "system_cases": None, "manager_cases": 2},
                {"item_nbr": 2, "system_cases": 3, "manager_cases": 3},
                {"item_nbr": 3, "system_cases": 3, "manager_cases": 5}]
        recs = log_records("2017-06-13", "case_straddle", rows, submitted_at="2026-09-25T20:00")
        assert [r["outcome"] for r in recs] == ["manager_call", "confirmed", "overridden"]
        assert recs[0]["order_date"] == "2017-06-13" and recs[0]["gate"] == "case_straddle"


class TestRangeText:
    def test_single_value_range_shows_nothing(self):
        assert range_text(3, 3) == ""

    def test_range_uses_an_en_dash(self):
        assert range_text(2, 4) == "likely 2–4"


class TestWidestFirst:
    def test_sorts_by_case_width_then_unit_width(self):
        df = pd.DataFrame({"item_nbr": [1, 2, 3], "lo": [1, 1, 2], "hi": [2, 3, 2],
                           "p10": [5.0, 5.0, 20.0], "p90": [15.0, 30.0, 22.0]})
        assert widest_first(df)["item_nbr"].tolist() == [2, 1, 3]

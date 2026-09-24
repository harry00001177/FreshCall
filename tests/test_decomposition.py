"""Error decomposition: of the SKU-days the model would get wrong if it
answered everything, which ones could any interval-based gate catch
(the P10-P90 interval spans a case boundary) and which not (the whole
interval sits in one case count, and actual sales land outside it)."""

import pandas as pd

from freshcall.decomposition import error_bucket, observed_holidays


class TestErrorBucket:
    def test_correct_order_has_no_bucket(self):
        # 25..35 units -> 3 cases everywhere; actual 30 -> 3 cases
        assert error_bucket(p10=25, p50=30, p90=35, hindsight=3, safety=0, on_hand=0, case_pack=12) is None

    def test_wrong_order_with_straddling_interval_is_catchable(self):
        # P50 30 -> 3 cases, P90 40 -> 4 cases: interval spans a boundary; actual needed 4
        assert error_bucket(p10=26, p50=30, p90=40, hindsight=4, safety=0, on_hand=0, case_pack=12) == "catchable"

    def test_wrong_order_inside_one_case_with_actual_above_is_uncaught_under(self):
        # whole interval says 3 cases, actual needed 5 -> under-ordered (stockout), nothing flagged it
        assert error_bucket(p10=25, p50=30, p90=35, hindsight=5, safety=0, on_hand=0, case_pack=12) == "uncaught_under"

    def test_wrong_order_inside_one_case_with_actual_below_is_uncaught_over(self):
        # whole interval says 3 cases, actual needed 1 -> over-ordered (waste), nothing flagged it
        assert error_bucket(p10=25, p50=30, p90=35, hindsight=1, safety=0, on_hand=0, case_pack=12) == "uncaught_over"


class TestObservedHolidays:
    def test_transferred_holiday_is_not_observed_but_its_transfer_day_is(self):
        h = pd.DataFrame({
            "date": pd.to_datetime(["2017-05-24", "2017-05-26"]),
            "type": ["Holiday", "Transfer"],
            "locale": ["National", "National"],
            "locale_name": ["Ecuador", "Ecuador"],
            "transferred": [True, False],
        })
        assert observed_holidays(h, city="Quito", state="Pichincha") == {pd.Timestamp("2017-05-26")}

    def test_other_cities_local_holidays_are_ignored(self):
        h = pd.DataFrame({
            "date": pd.to_datetime(["2017-07-25", "2017-12-06"]),
            "type": ["Holiday", "Holiday"],
            "locale": ["Local", "Local"],
            "locale_name": ["Guayaquil", "Quito"],
            "transferred": [False, False],
        })
        assert observed_holidays(h, city="Quito", state="Pichincha") == {pd.Timestamp("2017-12-06")}

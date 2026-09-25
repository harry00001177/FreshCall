"""Feature building: zero-fill the sales grid (Favorita omits zero-sales
days entirely), then build lag/rolling features that only ever look
backward — every feature here uses shift(1) so day N's row never contains
information from day N or later."""

import pandas as pd

from freshcall.features import add_features, build_daily_grid, same_weekday_avg


class TestSameWeekdayAvg:
    def test_averages_the_same_weekday_over_the_previous_four_weeks(self):
        s = pd.Series(range(1, 36), index=pd.date_range("2017-06-01", periods=35), dtype=float)
        # day 35 (value 35): same weekday 7/14/21/28 days earlier = values 28, 21, 14, 7
        assert same_weekday_avg(s).iloc[-1] == (28 + 21 + 14 + 7) / 4

    def test_never_uses_the_day_itself_or_other_weekdays(self):
        s = pd.Series([0.0] * 34 + [1000.0], index=pd.date_range("2017-06-01", periods=35))
        assert same_weekday_avg(s).iloc[-1] == 0.0

    def test_needs_four_full_weeks_of_history(self):
        s = pd.Series(range(20), index=pd.date_range("2017-06-01", periods=20), dtype=float)
        assert pd.isna(same_weekday_avg(s).iloc[-1])


class TestBuildDailyGrid:
    def test_fills_missing_dates_with_zero_sales(self):
        sparse = pd.DataFrame(
            {"date": pd.to_datetime(["2013-01-01", "2013-01-03"]), "unit_sales": [10.0, 20.0]}
        )
        grid = build_daily_grid(sparse, start="2013-01-01", end="2013-01-03")
        assert len(grid) == 3
        assert grid.set_index("date").loc["2013-01-02", "unit_sales"] == 0.0

    def test_keeps_existing_values_unchanged(self):
        sparse = pd.DataFrame({"date": pd.to_datetime(["2013-01-01"]), "unit_sales": [10.0]})
        grid = build_daily_grid(sparse, start="2013-01-01", end="2013-01-01")
        assert grid["unit_sales"].iloc[0] == 10.0


class TestAddFeatures:
    def _make_grid(self, n=10):
        dates = pd.date_range("2013-01-01", periods=n, freq="D")
        # unit_sales = 1, 2, 3, ... n -- easy to hand-verify lag/rolling values
        return pd.DataFrame({"date": dates, "unit_sales": range(1, n + 1)})

    def test_lag_1_is_yesterdays_value(self):
        df = add_features(self._make_grid())
        # row for day 5 (unit_sales=5) should have lag_1 == day 4's value == 4
        row = df[df["unit_sales"] == 5].iloc[0]
        assert row["lag_1"] == 4

    def test_lag_7_is_a_week_ago(self):
        df = add_features(self._make_grid(n=10))
        row = df[df["unit_sales"] == 8].iloc[0]  # day 8
        assert row["lag_7"] == 1  # day 1's value

    def test_rolling_7_mean_excludes_todays_value(self):
        df = add_features(self._make_grid(n=10))
        # day 8: rolling mean of days 1-7 (shifted by 1) = mean(1..7) = 4.0
        row = df[df["unit_sales"] == 8].iloc[0]
        assert row["rolling_7_mean"] == 4.0

    def test_weekday_dummies_are_present(self):
        df = add_features(self._make_grid())
        assert any(col.startswith("dow_") for col in df.columns)

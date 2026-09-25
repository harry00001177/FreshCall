"""Monitors watch many SKU-days after the fact (see CONTEXT.md: gate vs
monitor). Thresholds come from a calibration period, never chosen by eye
(pre-registered, DECISIONS.md 2026-09-25)."""

import pandas as pd

from freshcall.monitors import alerts, daily_monitor_series, fit_band


def _rows():
    # two days, two SKUs each; case_pack 12
    return pd.DataFrame({
        "date": pd.to_datetime(["2017-06-01", "2017-06-01", "2017-06-02", "2017-06-02"]),
        "fold": ["f1"] * 4,
        "p10": [20, 20, 20, 20], "p50": [30, 30, 30, 30], "p90": [40, 40, 40, 40],
        "actual": [30, 50, 30, 30],
        "hindsight": [3, 5, 3, 3],
    })


class TestDailyMonitorSeries:
    def test_signed_case_error_is_model_cases_minus_hindsight(self):
        daily = daily_monitor_series(_rows(), case_pack=12, safety=0, on_hand=0, window=1)
        # P50 30 -> 3 cases. Day 1: errors 0 and -2 -> mean -1. Day 2: 0 and 0.
        assert daily["bias"].tolist() == [-1.0, 0.0]

    def test_coverage_is_share_of_actuals_inside_the_interval(self):
        daily = daily_monitor_series(_rows(), case_pack=12, safety=0, on_hand=0, window=1)
        assert daily["coverage"].tolist() == [0.5, 1.0]

    def test_rolling_window_averages_the_daily_values(self):
        daily = daily_monitor_series(_rows(), case_pack=12, safety=0, on_hand=0, window=2)
        assert pd.isna(daily["bias_rolling"].iloc[0])
        assert daily["bias_rolling"].iloc[1] == -0.5


class TestFitBandAndAlerts:
    def test_band_is_mean_plus_minus_three_std(self):
        lower, upper = fit_band(pd.Series([1.0, 2.0, 3.0]))
        assert (lower, upper) == (2.0 - 3.0, 2.0 + 3.0)  # std of [1,2,3] is 1.0

    def test_alerts_only_outside_the_band(self):
        s = pd.Series([0.0, 5.0, -5.0, 1.0], index=pd.date_range("2017-06-01", periods=4))
        assert alerts(s, lower=-2.0, upper=2.0) == [pd.Timestamp("2017-06-02"), pd.Timestamp("2017-06-03")]

    def test_one_sided_alert_ignores_the_missing_side(self):
        s = pd.Series([0.95, 0.40], index=pd.date_range("2017-06-01", periods=2))
        assert alerts(s, lower=0.6, upper=None) == [pd.Timestamp("2017-06-02")]

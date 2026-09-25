"""Grid reconstruction + feature building. Favorita omits zero-sales days
entirely, so a missing date is not a missing row to drop — it's a real
"sold zero" day that must be filled in before lag/rolling features are
computed. Every feature uses `.shift(1)`: day N's row must never see day
N's own sale, or any day after it (leakage)."""

import pandas as pd


def build_daily_grid(sales: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Reindex sparse sales onto a continuous daily calendar, filling
    missing days with 0 (a day with no recorded row is a day nothing sold,
    not a day that didn't happen)."""
    full_dates = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    grid = full_dates.merge(sales, on="date", how="left")
    grid["unit_sales"] = grid["unit_sales"].fillna(0.0)
    return grid


def same_weekday_avg(daily_sales: pd.Series, weeks: int = 4) -> pd.Series:
    """Average of the same weekday over the previous `weeks` weeks (days -7,
    -14, ...). Used in the explanation's fact block instead of a 7-day mean,
    which weekend spikes distort (DECISIONS.md 2026-09-25, case 16)."""
    return sum(daily_sales.shift(7 * k) for k in range(1, weeks + 1)) / weeks


def add_features(grid: pd.DataFrame) -> pd.DataFrame:
    """Add weekday dummies (same-day, not leakage — the calendar is known in
    advance) and lag/rolling demand features (all shifted by 1 day, since
    tomorrow's forecast can only use sales through today)."""
    df = grid.copy()
    df["dow"] = df["date"].dt.dayofweek
    df = pd.get_dummies(df, columns=["dow"], prefix="dow")

    df["lag_1"] = df["unit_sales"].shift(1)
    df["lag_7"] = df["unit_sales"].shift(7)
    df["rolling_7_mean"] = df["unit_sales"].shift(1).rolling(window=7).mean()

    return df

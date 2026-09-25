"""The redesign (pre-registered, DECISIONS.md 2026-09-25): instead of
handing uncertain SKUs back (ASK ME), give every SKU an order plus its
likely range in cases; treat routine SKUs (every recent day fit in one
case) as standing orders; and judge value in wrong orders and units
wasted / short — a case can be "right" and still waste units."""

import math

import pandas as pd

from freshcall.order import naive_seasonal_order, recommended_cases


def standing_order(policy: str, model_cases: int, last_week_units: float, case_pack: int) -> int:
    """Order for a routine SKU under the store's `routine_policy`: `model`
    (fewer stockouts, more waste) or `last_week` (the reverse) — a trade-off
    only the store can price (DECISIONS.md 2026-09-25)."""
    if policy == "model":
        return model_cases
    if policy == "last_week":
        return naive_seasonal_order(last_week_units, case_pack)
    raise ValueError(f"unknown routine_policy: {policy!r}")


def past_max(daily_sales: pd.Series, window: int = 28) -> pd.Series:
    """Max daily sales over the `window` days *before* each date (shift(1):
    the order date's own sales are never seen)."""
    return daily_sales.shift(1).rolling(window).max()


def is_routine(past_max_value: float, case_pack: int) -> bool:
    if past_max_value is None or (isinstance(past_max_value, float) and math.isnan(past_max_value)):
        return False
    return bool(past_max_value <= case_pack)


def case_range(p10: float, p50: float, p90: float, safety: float, on_hand: float, case_pack: int) -> tuple[int, int, int]:
    """(low, order, high) in cases, from P10 / P50 / P90."""
    return tuple(recommended_cases(q, safety, on_hand, case_pack) for q in (p10, p50, p90))


def unit_errors(order_cases: int, actual: float, case_pack: int) -> tuple[float, float]:
    """(units over-ordered, units short). Negative net sales (returns) count
    as zero demand."""
    demand = max(0.0, actual)
    supplied = order_cases * case_pack
    return max(0.0, supplied - demand), max(0.0, demand - supplied)

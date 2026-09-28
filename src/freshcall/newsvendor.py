"""Newsvendor ordering (PRE-REGISTRATION, DECISIONS.md 2026-09-28). P50 is
only the cheapest order when a unit short costs the same as a unit wasted.
With the store's cost ratio r = (cost of one unit short) / (cost of one
unit wasted), the cheapest single-day order sits at quantile r / (1 + r).
The prototype's on_hand = 0 (leftovers never carry over) is exactly the
newsvendor's single-period setting."""

import math


def critical_quantile(ratio: float) -> float:
    if ratio <= 0:
        raise ValueError(f"cost ratio must be positive, got {ratio!r}")
    return ratio / (1 + ratio)


def nearest_quantile(q: float, trained: list[float]) -> float:
    """Only a fixed grid of quantile models is trained, so the order uses
    the trained quantile closest to q."""
    return min(trained, key=lambda t: abs(t - q))


def order_cost(over: float, short: float, ratio: float) -> float:
    """Cost of one order in units of 'one unit wasted'."""
    return over + ratio * short


def newsvendor_cases(scenarios, ratio: float, case_pack: int) -> int:
    """AMENDED PRE-REGISTRATION (DECISIONS.md 2026-09-28): with 12-unit
    cases, "order at quantile q*" and then round up over-orders — the
    rounding alone already lifts a P50 order to ~85-90% coverage. Instead,
    treat the quantile forecasts as equally likely demands and pick the
    whole case count with the lowest average cost (ties -> fewer cases)."""
    scenarios = [max(0.0, float(d)) for d in scenarios]
    top = math.ceil(max(scenarios) / case_pack) + 1
    costs = [
        sum(order_cost(max(0.0, n * case_pack - d), max(0.0, d - n * case_pack), ratio) for d in scenarios)
        for n in range(top + 1)
    ]
    return costs.index(min(costs))


def floor_applies(last_7_days_sales) -> bool:
    """Business-rule variant (reported, not judged): a SKU that sold on
    each of the 7 days before the order date always gets at least 1 case."""
    days = list(last_7_days_sales)
    return len(days) == 7 and all(d >= 1 for d in days)

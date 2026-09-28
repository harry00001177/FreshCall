"""Newsvendor ordering (PRE-REGISTRATION, DECISIONS.md 2026-09-28). P50 is
only the cheapest order when a unit short costs the same as a unit wasted.
With the store's cost ratio r = (cost of one unit short) / (cost of one
unit wasted), the cheapest single-day order sits at quantile r / (1 + r).
The prototype's on_hand = 0 (leftovers never carry over) is exactly the
newsvendor's single-period setting."""


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

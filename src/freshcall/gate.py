"""The abstain gate: a deterministic threshold on interval width. See
CONTEXT.md — `rel_width` is the only uncertainty signal in this codebase,
and `confidence` is a banned word."""


def rel_width(p10: float, p50: float, p90: float) -> float:
    """Relative width of the predicted demand interval. `max(p50, 1)` avoids
    dividing by zero on a near-zero-demand SKU-day."""
    return (p90 - p10) / max(p50, 1)


def should_abstain(p10: float, p50: float, p90: float, threshold: float) -> bool:
    """Abstain only when rel_width strictly exceeds the threshold — a SKU-day
    exactly at the threshold still gets an answer."""
    return rel_width(p10, p50, p90) > threshold

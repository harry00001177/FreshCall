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


def decide_abstain(p10: float, p50: float, p90: float, cfg: dict) -> bool:
    """The system's gate, chosen in config.yaml (gate.type). An unknown type
    raises rather than silently falling back to a gate nobody chose."""
    from freshcall.case_gate import straddles_case_boundary

    gate_type = cfg["gate"]["type"]
    if gate_type == "case_straddle":
        return straddles_case_boundary(p10, p50, p90, cfg["safety"], cfg["on_hand"], cfg["case_pack"])
    if gate_type == "rel_width":
        return should_abstain(p10, p50, p90, cfg["gate"]["rel_width_threshold"])
    raise ValueError(f"unknown gate type in config: {gate_type!r}")

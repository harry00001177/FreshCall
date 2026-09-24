"""Case-straddle gate (experiment, pre-registered DECISIONS.md 2026-09-24).
Measures uncertainty in the manager's decision units: abstain only if the
P10/P50/P90 forecasts would lead to different case orders. No threshold.
Separate from gate.py so the original rel_width gate is untouched."""

from freshcall.order import recommended_cases


def straddles_case_boundary(p10: float, p50: float, p90: float, safety: float, on_hand: float, case_pack: int) -> bool:
    return len({recommended_cases(q, safety, on_hand, case_pack) for q in (p10, p50, p90)}) > 1

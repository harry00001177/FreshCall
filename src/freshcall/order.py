"""Deterministic order arithmetic. No model, no LLM — every number here must
be exactly reproducible and unit-tested, because an error here is a direct
cash error, not a wording error."""

import math


def recommended_cases(demand: float, safety: float, on_hand: float, case_pack: int) -> int:
    """Cases to order = ceil((demand + safety - on_hand) / case_pack), floored at 0."""
    needed_units = demand + safety - on_hand
    if needed_units <= 0:
        return 0
    return math.ceil(needed_units / case_pack)


def hindsight_demand_order(actual_units: float, case_pack: int) -> int:
    """What the case order would have been if tomorrow's actual sales were
    known in advance. A Layer A demand benchmark, not a claim of ordering
    optimality — see CONTEXT.md."""
    if actual_units <= 0:
        return 0
    return math.ceil(actual_units / case_pack)


def naive_seasonal_order(same_weekday_last_week_units: float, case_pack: int) -> int:
    """The non-AI baseline: same weekday last week, rounded up to a case."""
    return hindsight_demand_order(same_weekday_last_week_units, case_pack)

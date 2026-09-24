"""Error decomposition (Problem Statement Section 7 / handoff "three-bucket"
analysis, simplified because the novelty check was never built). An error
is a SKU-day where the P50-implied order differs from
hindsight_demand_order. "catchable" = the P10-P90 interval spans a case
boundary, so an interval-based gate could flag it. "uncaught_*" = the
whole interval implies one case count and actual sales landed outside
it: no interval-based gate can flag these, so their share bounds what
abstention can ever achieve."""

import pandas as pd

from freshcall.case_gate import straddles_case_boundary
from freshcall.order import recommended_cases

_OBSERVED_TYPES = {"Holiday", "Transfer", "Additional", "Bridge"}


def error_bucket(p10, p50, p90, hindsight, safety, on_hand, case_pack) -> str | None:
    cases = recommended_cases(p50, safety, on_hand, case_pack)
    if cases == hindsight:
        return None
    if straddles_case_boundary(p10, p50, p90, safety, on_hand, case_pack):
        return "catchable"
    return "uncaught_under" if hindsight > cases else "uncaught_over"


def observed_holidays(holidays: pd.DataFrame, city: str, state: str) -> set:
    """Days a store in `city` actually had off: national, its region, or
    its city. A holiday with transferred=True was moved, so its original
    date is not observed (its 'Transfer' row carries the real day)."""
    h = holidays[holidays["type"].isin(_OBSERVED_TYPES) & ~holidays["transferred"]]
    relevant = (
        (h["locale"] == "National")
        | ((h["locale"] == "Regional") & (h["locale_name"] == state))
        | ((h["locale"] == "Local") & (h["locale_name"] == city))
    )
    return set(pd.to_datetime(h.loc[relevant, "date"]))

"""UI logic, separate from Streamlit so it's testable (DECISIONS.md
2026-09-25 UI decisions): which SKUs/dates are shown, what a valid order
is, and what the confirm/override log records."""

import random

import pandas as pd


def select_ui_skus(candidates: list[int], inactive: set, n: int = 40, seed: int = 42) -> list[int]:
    """n SKUs drawn with a fixed seed from those still selling — a manager's
    nightly list, not the best-looking 40."""
    pool = sorted(c for c in candidates if c not in inactive)
    return sorted(random.Random(seed).sample(pool, n))


def ui_dates(first: str, last: str, step_days: int = 14) -> list[pd.Timestamp]:
    return list(pd.date_range(first, last, freq=f"{step_days}D"))


def validate_order(rows: list[dict]) -> list[str]:
    errors = []
    for r in rows:
        if r["manager_cases"] is None:
            if r["system_cases"] is None:
                errors.append(f"item {r['item_nbr']}: ASK ME — please enter a number of cases")
        elif r["manager_cases"] < 0:
            errors.append(f"item {r['item_nbr']}: cases can't be negative")
    return errors


def log_records(order_date: str, gate: str, rows: list[dict], submitted_at: str) -> list[dict]:
    """One record per SKU. 'manager_call' = the system abstained; 'overridden'
    = the manager changed the suggestion (not a system failure — a signal of
    where the model isn't trusted)."""
    records = []
    for r in rows:
        if r["system_cases"] is None:
            outcome = "manager_call"
        elif r["manager_cases"] == r["system_cases"]:
            outcome = "confirmed"
        else:
            outcome = "overridden"
        records.append({
            "submitted_at": submitted_at, "order_date": order_date, "gate": gate,
            "item_nbr": r["item_nbr"], "system_cases": r["system_cases"],
            "manager_cases": r["manager_cases"], "outcome": outcome,
        })
    return records


def range_text(lo: int, hi: int) -> str:
    """"likely 2–4" beside an order; nothing when P10 and P90 imply the same
    case count (DECISIONS.md 2026-09-25: a range is information, not an alarm)."""
    return "" if lo == hi else f"likely {lo}–{hi}"


def widest_first(rows: pd.DataFrame) -> pd.DataFrame:
    """Widest case range first (ties: widest P10–P90 in units) — on stores 44/8
    the widest quarter held ~45% of wrong orders, so the top of the list is
    where a manager's glance pays off most."""
    ranked = rows.assign(_w=rows["hi"] - rows["lo"], _u=rows["p90"] - rows["p10"])
    return ranked.sort_values(["_w", "_u"], ascending=False).drop(columns=["_w", "_u"])

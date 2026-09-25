"""FreshCall — one-page UI for the store manager (DECISIONS.md 2026-09-25).
The redesign: every SKU gets tomorrow's order in cases (with units), plus
its likely range when P10 and P90 disagree; lines are listed widest range
first; routine SKUs are collapsed standing orders. Every line is editable
and "Place order" logs confirmed / changed. No confidence figure appears.
The sidebar's history view shows the earlier designs (v1 / v2, which
handed uncertain SKUs back as ASK ME) for comparison. Reads
data/ui_cache.parquet (build_ui_cache.py); calls no model and no LLM.
Run: streamlit run app.py"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))  # `streamlit run` doesn't take PYTHONPATH from the project

from freshcall.explain import build_fact_block, order_sentence, render_template_fallback  # noqa: E402
from freshcall.redesign import standing_order  # noqa: E402
from freshcall.ui_logic import log_records, range_text, validate_order, widest_first  # noqa: E402

CACHE = ROOT / "data/ui_cache.parquet"
LOG = ROOT / "data/ui_orders_log.csv"
DESIGNS = {
    "redesign": "Order + likely range (system)",
    "case_straddle": "History v2: case-straddle + ASK ME",
    "rel_width": "History v1: rel_width 0.60 + ASK ME",
}

st.set_page_config(page_title="FreshCall", layout="centered")

if not CACHE.exists():
    st.error("No UI data yet. Run `PYTHONPATH=src python build_ui_cache.py` first.")
    st.stop()

cfg = yaml.safe_load(open(ROOT / "config.yaml"))
cp = cfg["case_pack"]
cache = pd.read_parquet(CACHE)
dates = sorted(cache["date"].unique())

with st.sidebar:
    date = st.selectbox("Order for", dates, format_func=lambda d: pd.Timestamp(d).strftime("%a %d %b %Y"))
    st.divider()
    st.caption("Evaluation view — for the demo, not part of the manager's screen")
    design = st.radio("Design", list(DESIGNS), format_func=DESIGNS.get)
    show_outcome = st.checkbox("Show what actually sold (backtest)")

day = cache[cache["date"] == date].copy()
day["name"] = day["family"].str.title() + " · item " + day["item_nbr"].astype(str)
day["shown"] = [
    standing_order(cfg["routine_policy"], r.order, r.last_week_units, cp) if r.routine else r.order
    for r in day.itertuples()
]


def plural(n, word: str) -> str:
    return f"{n:g} {word}{'' if n == 1 else 's'}"


def outcome_note(row, cases=None) -> str:
    note = f"Actually sold {plural(row.actual, 'unit')} → needed {plural(row.hindsight, 'case')}."
    if cases is not None:
        note += " Suggestion matches." if cases == row.hindsight else f" Suggestion off by {abs(cases - row.hindsight)}."
    return note


def order_lines(row, cases: int, with_range: bool) -> tuple[str, str]:
    sentence = order_sentence(cases, cp, row.weekday, row.weekday_avg, row.last_week_units)
    head, _, reason = sentence.partition(". ")
    rng = range_text(row.lo, row.hi) if with_range else ""
    return f"**{head}**" + (f" · {rng}" if rng else ""), reason


def order_card(row, cases: int, with_range: bool, key: str) -> dict:
    with st.container(border=True):
        left, right = st.columns([3, 1])
        left.markdown(f"**{row.name}**")
        head, reason = order_lines(row, cases, with_range)
        left.markdown(head)
        left.caption(reason)
        if show_outcome:
            left.caption(outcome_note(row, cases))
        value = right.number_input("Cases", min_value=0, step=1, value=int(cases), key=key)
    return {"item_nbr": row.item_nbr, "system_cases": int(cases), "manager_cases": value}


st.title("FreshCall")
st.caption(f"Tomorrow's fresh order · Store 44 · {pd.Timestamp(date).strftime('%A %d %B %Y')}")

entries = []
with st.form("order"):
    if design == "redesign":
        look, routine = widest_first(day[~day["routine"]]), day[day["routine"]].sort_values("name")
        c1, c2 = st.columns(2)
        c1.metric("Worth a look", f"{len(look)} of {len(day)}")
        c2.metric("Standing orders", f"{len(routine)} of {len(day)}")
        st.caption("Widest likely range first — the lines where what you know about tomorrow matters most.")
        for row in look.itertuples():
            entries.append(order_card(row, row.shown, True, f"{date}-{design}-{row.item_nbr}"))
        with st.expander(f"Standing orders ({len(routine)}) — every day of the last 4 weeks fit in one case"):
            for row in routine.itertuples():
                entries.append(order_card(row, row.shown, False, f"{date}-{design}-{row.item_nbr}"))
    else:
        day["abstain"] = day[f"abstain_{design}"]
        ask, ready = day[day["abstain"]].sort_values("name"), day[~day["abstain"]].sort_values("name")
        st.info("History view: an earlier design that handed uncertain SKUs back as ASK ME.")
        c1, c2 = st.columns(2)
        c1.metric("Need your call", f"{len(ask)} of {len(day)}")
        c2.metric("Ready to confirm", f"{len(ready)} of {len(day)}")
        for row in ask.itertuples():
            with st.container(border=True):
                left, right = st.columns([3, 1])
                left.markdown(f"**{row.name}**")
                ask_text = render_template_fallback(build_fact_block(
                    f"item {row.item_nbr}", True, None, None, row.last_week_units))
                head, _, rest = ask_text.partition(". ")
                left.markdown(f"**{head}.** {rest}")
                if show_outcome:
                    left.caption(outcome_note(row))
                value = right.number_input("Cases", min_value=0, step=1, value=None,
                                           key=f"{date}-{design}-{row.item_nbr}")
            entries.append({"item_nbr": row.item_nbr, "system_cases": None, "manager_cases": value})
        for row in ready.itertuples():
            entries.append(order_card(row, row.order, False, f"{date}-{design}-{row.item_nbr}"))

    submitted = st.form_submit_button("Place order", type="primary", use_container_width=True)

if submitted:
    errors = validate_order(entries)
    if errors:
        st.error("Not placed yet:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        records = log_records(pd.Timestamp(date).date().isoformat(), design, entries,
                              submitted_at=datetime.now().isoformat(timespec="seconds"))
        pd.DataFrame(records).to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
        counts = pd.Series([r["outcome"] for r in records]).value_counts()
        st.success(f"Order placed: {counts.get('confirmed', 0)} confirmed, "
                   f"{counts.get('overridden', 0)} changed, {counts.get('manager_call', 0)} set by you.")

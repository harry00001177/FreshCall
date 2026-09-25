"""FreshCall — one-page UI for the store manager (Problem Statement §3, §5, §8;
DECISIONS.md 2026-09-25). Shows tomorrow's order in cases, hands hard SKUs
back as ASK ME with a reference anchor, lets the manager confirm or change
every line, and logs the result. Never shows a confidence figure.
Reads data/ui_cache.parquet (built by build_ui_cache.py); no model or LLM
calls happen here. Run: streamlit run app.py"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))  # `streamlit run` doesn't take PYTHONPATH from the project

from freshcall.explain import build_fact_block, render_template_fallback  # noqa: E402
from freshcall.ui_logic import log_records, validate_order  # noqa: E402

CACHE = ROOT / "data/ui_cache.parquet"
LOG = ROOT / "data/ui_orders_log.csv"
GATES = {"case_straddle": "Case-straddle (system gate)", "rel_width": "Original design: rel_width 0.60"}

st.set_page_config(page_title="FreshCall", layout="centered")

if not CACHE.exists():
    st.error("No UI data yet. Run `PYTHONPATH=src python build_ui_cache.py` first.")
    st.stop()

cfg = yaml.safe_load(open(ROOT / "config.yaml"))
cache = pd.read_parquet(CACHE)
dates = sorted(cache["date"].unique())

with st.sidebar:
    date = st.selectbox("Order for", dates, format_func=lambda d: pd.Timestamp(d).strftime("%a %d %b %Y"))
    st.divider()
    st.caption("Evaluation view — for the demo, not part of the manager's screen")
    gate = st.radio("Gate", list(GATES), format_func=GATES.get, index=list(GATES).index(cfg["gate"]["type"]))
    show_outcome = st.checkbox("Show what actually sold (backtest)")

day = cache[cache["date"] == date].copy()
day["abstain"] = day[f"abstain_{gate}"]
day["name"] = day["family"].str.title() + " · item " + day["item_nbr"].astype(str)
day = day.sort_values(["name"])
ask, ready = day[day["abstain"]], day[~day["abstain"]]

st.title("FreshCall")
st.caption(f"Tomorrow's fresh order · Store 44 · {pd.Timestamp(date).strftime('%A %d %B %Y')}")
c1, c2 = st.columns(2)
c1.metric("Need your call", f"{len(ask)} of {len(day)}")
c2.metric("Ready to confirm", f"{len(ready)} of {len(day)}")


def bold_head(text: str) -> str:
    head, sep, rest = text.partition(". ")
    return f"**{head}.** {rest}" if sep else f"**{text}**"


def plural(n, word: str) -> str:
    return f"{n:g} {word}{'' if n == 1 else 's'}"


def outcome_note(row) -> str:
    return f"Actually sold {plural(row.actual, 'unit')} → needed {plural(row.hindsight, 'case')}."


with st.form("order"):
    entries = []
    st.subheader(f"Needs your call ({len(ask)})")
    for row in ask.itertuples():
        with st.container(border=True):
            left, right = st.columns([3, 1])
            left.markdown(f"**{row.name}**")
            ask_text = render_template_fallback(build_fact_block(
                f"item {row.item_nbr}", True, None, row.recent_avg, row.last_same_weekday))
            left.markdown(bold_head(ask_text))
            if show_outcome:
                left.caption(outcome_note(row))
            value = right.number_input("Cases", min_value=0, step=1, value=None,
                                       key=f"{date}-{gate}-{row.item_nbr}")
        entries.append({"item_nbr": row.item_nbr, "system_cases": None, "manager_cases": value})

    st.subheader(f"Ready to confirm ({len(ready)})")
    for row in ready.itertuples():
        with st.container(border=True):
            left, right = st.columns([3, 1])
            left.markdown(f"**{row.name}**")
            left.markdown(bold_head(row.order_text))
            if show_outcome:
                verdict = "matches" if row.cases == row.hindsight else f"off by {abs(row.cases - row.hindsight)}"
                left.caption(f"{outcome_note(row)} Suggestion {verdict}.")
            value = right.number_input("Cases", min_value=0, step=1, value=int(row.cases),
                                       key=f"{date}-{gate}-{row.item_nbr}")
        entries.append({"item_nbr": row.item_nbr, "system_cases": int(row.cases), "manager_cases": value})

    submitted = st.form_submit_button("Place order", type="primary", use_container_width=True)

if submitted:
    errors = validate_order(entries)
    if errors:
        st.error("Not placed yet:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        records = log_records(pd.Timestamp(date).date().isoformat(), gate, entries,
                              submitted_at=datetime.now().isoformat(timespec="seconds"))
        pd.DataFrame(records).to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
        counts = pd.Series([r["outcome"] for r in records]).value_counts()
        st.success(f"Order placed: {counts.get('confirmed', 0)} confirmed, "
                   f"{counts.get('overridden', 0)} changed, {counts.get('manager_call', 0)} set by you.")

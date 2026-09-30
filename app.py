"""FreshCall — one-page UI for the store manager (DECISIONS.md 2026-09-25,
2026-09-28). Every SKU gets tomorrow's order in cases (with units): the
newsvendor order — the whole case count with the lowest expected cost at
the store's cost ratio — plus its likely range; lines are listed widest
range first; routine SKUs are collapsed standing orders. Every line is editable
and "Place order" logs confirmed / changed. No confidence figure appears.
The sidebar's history view shows the earlier designs (v1 / v2, which
handed uncertain SKUs back as ASK ME) for comparison. Reads
data/ui_cache.parquet (scripts/build_ui_cache.py); calls no model and no LLM.
Run: streamlit run app.py"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))  # `streamlit run` doesn't take PYTHONPATH from the project

from freshcall.explain import build_fact_block, order_sentence, render_template_fallback  # noqa: E402
from freshcall.newsvendor import QUANTILES, system_order  # noqa: E402
from freshcall.ui_logic import log_records, range_bar, range_text, shown_range, validate_order, widest_first  # noqa: E402

CACHE = ROOT / "data/ui_cache.parquet"
LOG = ROOT / "data/ui_orders_log.csv"
DESIGNS = {
    "redesign": "v3 (current): order + likely range",
    "case_straddle": "v2: case-straddle + ASK ME",
    "rel_width": "v1: rel_width + ASK ME",
}

st.set_page_config(page_title="FreshCall", layout="centered")

if not CACHE.exists():
    st.error("No UI data yet. Run `PYTHONPATH=src python scripts/build_ui_cache.py` first.")
    st.stop()

cfg = yaml.safe_load(open(ROOT / "config.yaml"))
cp = cfg["case_pack"]
cache = pd.read_parquet(CACHE)
SUMMARY = ROOT / "data/ui_data_summary.json"
STORE_ROLES = {45: "confirmation store — newsvendor (cost-ratio) order",
               8: "confirmation store — v3 order + likely range",
               44: "development store — every design was tuned here"}
RATIOS = [0.25, 0.5, 1, 2, 4, 9]  # the cost ratios tested on stores 44 / 8 / 45
QCOLS = [f"q{round(q * 100)}" for q in QUANTILES]  # as scripts/build_ui_cache.py names them

with st.sidebar:
    store = st.selectbox("Store", list(STORE_ROLES), format_func=lambda s: f"Store {s}")
    st.caption(STORE_ROLES[store].capitalize())
    dates = sorted(cache.loc[cache["store"] == store, "date"].unique())
    date = st.selectbox("Order for", dates, format_func=lambda d: pd.Timestamp(d).strftime("%a %d %b %Y"))
    st.divider()
    st.caption("Evaluation view — for the demo, not part of the manager's screen")
    design = st.radio("Design", list(DESIGNS), format_func=DESIGNS.get)
    show_outcome = st.checkbox("Show what actually sold (backtest)")
    ratio = st.select_slider("Cost ratio", RATIOS, value=cfg["cost_ratio"],
                             help="A store setting (config.yaml), shown here for the demo only.")
    st.caption("How much worse running out is than wasting. Slide right to order more, left to order less.")
    use_floor = st.checkbox("Sold every day last week → at least 1 case", value=cfg["min_one_case_floor"])

day = cache[(cache["store"] == store) & (cache["date"] == date)].copy()
day["name"] = day["family"].str.title() + " · item " + day["item_nbr"].astype(str)
day["shown"] = [system_order([getattr(r, c) for c in QCOLS], ratio, cp, use_floor and r.floor)
                for r in day.itertuples()]
day["lo"], day["hi"] = zip(*[shown_range(r.lo, r.shown, r.hi) for r in day.itertuples()])


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
    rng = range_text(row.lo, row.hi, cfg["range_display_max_width"]) if with_range else ""
    return f"**{head}**" + (f" · {rng}" if rng else ""), reason


FAMILY_HUE = {"PRODUCE": "99,153,34", "DAIRY": "55,138,221", "BREAD/BAKERY": "186,117,23",
              "EGGS": "186,117,23", "DELI": "212,83,126", "MEATS": "216,90,48", "POULTRY": "216,90,48",
              "PREPARED FOODS": "127,119,221", "SEAFOOD": "29,158,117"}
ROW_CSS = """<style>
div[data-testid="stForm"] div[data-testid="stVerticalBlock"] {gap: 0.15rem;}
.fc-head {display:flex; gap:1rem; font-size:12px; opacity:.6; padding:0 2px 4px; margin-bottom:6px; border-bottom:1px solid rgba(128,128,128,.35);}
.fc-item {font-size:14px; line-height:2.4rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.fc-chip {font-size:11px; padding:2px 7px; border-radius:6px; margin-right:8px;}
.fc-bar {position:relative; height:6px; border-radius:3px; background:rgba(128,128,128,.18); margin-top:.9rem;}
.fc-band {position:absolute; top:0; height:6px; border-radius:3px; background:rgba(128,128,128,.55);}
.fc-dot {position:absolute; top:-3px; width:12px; height:12px; border-radius:50%; background:currentColor;}
.fc-lbl {font-size:11px; opacity:.6; margin-top:2px;}
.fc-wide {font-size:12px; color:#BA7517; line-height:2.4rem;}
div[data-testid="stForm"] details {border:none; margin-top:-0.4rem;}
div[data-testid="stForm"] details summary {padding:0 2px; font-size:12px; opacity:.7; min-height:1.2rem;}
div[data-testid="stForm"] details summary p {font-size:12px;}
div[data-testid="stForm"] details:has(.fc-standing) {border:1px solid rgba(128,128,128,.35); margin-top:.6rem;}
div[data-testid="stForm"] details:has(.fc-standing) > summary {font-size:14px; opacity:1; padding:.5rem .75rem;}
div[data-testid="stForm"] details:has(.fc-standing) > summary p {font-size:14px;}
@media (max-width: 640px) {.fc-head {display:none;}}
</style>"""


def chip(family: str) -> str:
    rgb = FAMILY_HUE.get(family, "128,128,128")
    return (f'<span class="fc-chip" style="background:rgba({rgb},.16);color:rgb({rgb})">'
            f'{family.title()}</span>')


def bar_html(row) -> str:
    bar = range_bar(row.lo, row.shown, row.hi, cfg["range_display_max_width"])
    if bar is None:
        return '<div class="fc-wide">Wide range — take a look</div>'
    band = f'left:{bar["lo_pct"]:.1f}%;width:{bar["hi_pct"] - bar["lo_pct"]:.1f}%'
    return (f'<div class="fc-bar"><div class="fc-band" style="{band}"></div>'
            f'<div class="fc-dot" style="left:calc({bar["order_pct"]:.1f}% - 6px)"></div></div>'
            f'<div class="fc-lbl">{bar["label"] and "likely " + bar["label"]}</div>')


def compact_row(row, cases: int, key: str, with_range: bool = True) -> dict:
    """One slim line per SKU (item · likely range · order); details fold out below."""
    item, rng, qty = st.columns([5, 4, 3], vertical_alignment="center")
    item.markdown(f'<div class="fc-item">{chip(row.family)}item {row.item_nbr}</div>', unsafe_allow_html=True)
    if with_range:
        rng.markdown(bar_html(row), unsafe_allow_html=True)
    value = qty.number_input("Cases", min_value=0, step=1, value=int(cases), key=key, label_visibility="collapsed")
    if not with_range:  # standing orders sit inside an expander, and expanders can't nest
        rng.caption(f"last {row.weekday} {row.last_week_units:g} · 4-week avg {row.weekday_avg:g} units")
        return {"item_nbr": row.item_nbr, "system_cases": int(cases), "manager_cases": value}
    with st.expander("Details"):
        head, reason = order_lines(row, cases, with_range)
        st.markdown(head)
        st.caption(reason)
        a, b, c = st.columns(3)
        a.caption(f"{row.weekday}s, 4-week avg  \n**{row.weekday_avg:g} units**")
        b.caption(f"Last {row.weekday}  \n**{row.last_week_units:g} units**")
        c.caption(f"Units per case  \n**{cp}**")
        if show_outcome:
            before = "" if cases == row.order else f" (P50 order before the newsvendor change: {plural(row.order, 'case')})"
            st.caption(outcome_note(row, cases) + before)
    return {"item_nbr": row.item_nbr, "system_cases": int(cases), "manager_cases": value}


def order_card(row, cases: int, with_range: bool, key: str) -> dict:
    with st.container(border=True):
        left, right = st.columns([3, 1])
        left.markdown(f"**{row.name}**")
        head, reason = order_lines(row, cases, with_range)
        left.markdown(head)
        left.caption(reason)
        if show_outcome:
            before = "" if cases == row.order else f" (P50 order before the newsvendor change: {plural(row.order, 'case')})"
            left.caption(outcome_note(row, cases) + before)
        value = right.number_input("Cases", min_value=0, step=1, value=int(cases), key=key)
    return {"item_nbr": row.item_nbr, "system_cases": int(cases), "manager_cases": value}


st.title("FreshCall")
st.caption(f"Tomorrow's fresh order · Store {store} · {pd.Timestamp(date).strftime('%A %d %B %Y')} · "
           f"ordered for a store where running out costs {ratio:g}× wasting")

tab_order, tab_data = st.tabs(["Tomorrow's order", "Data"])
entries = []
with tab_order, st.form("order"):
    if design == "redesign":
        look, routine = widest_first(day[~day["routine"]]), day[day["routine"]].sort_values("name")
        st.markdown(ROW_CSS, unsafe_allow_html=True)
        st.caption(f"{len(day)} orders ready · {len(look)} worth a glance, widest likely range first — "
                   f"where what you know about tomorrow matters most · {len(routine)} standing orders")
        st.markdown('<div class="fc-head"><span style="flex:5">Item</span><span style="flex:4">Likely range '
                    '(cases) · dot = order</span><span style="flex:3">Order (cases)</span></div>',
                    unsafe_allow_html=True)
        for row in look.itertuples():
            entries.append(compact_row(row, row.shown, f"{store}-{date}-{design}-{ratio}-{use_floor}-{row.item_nbr}"))
        with st.expander(f"Standing orders · {len(routine)} items — every day of the last 4 weeks fit in one case"):
            st.markdown('<span class="fc-standing"></span>', unsafe_allow_html=True)
            for row in routine.itertuples():
                entries.append(compact_row(row, row.shown, f"{store}-{date}-{design}-{ratio}-{use_floor}-{row.item_nbr}",
                                           with_range=False))
    else:
        day["abstain"] = day[f"abstain_{design}"]
        ask, ready = day[day["abstain"]].sort_values("name"), day[~day["abstain"]].sort_values("name")
        st.info(f"{DESIGNS[design].split(':')[0]} (earlier design): uncertain SKUs were handed back as ASK ME.")
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
                                           key=f"{store}-{date}-{design}-{row.item_nbr}")
            entries.append({"item_nbr": row.item_nbr, "system_cases": None, "manager_cases": value})
        for row in ready.itertuples():
            entries.append(order_card(row, row.order, False, f"{store}-{date}-{design}-{row.item_nbr}"))

    submitted = st.form_submit_button("Place order", type="primary", use_container_width=True)

if submitted:
    errors = validate_order(entries)
    if errors:
        tab_order.error("Not placed yet:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        records = [{**r, "store": store} for r in log_records(
            pd.Timestamp(date).date().isoformat(), design, entries,
            submitted_at=datetime.now().isoformat(timespec="seconds"))]
        if LOG.exists() and "store" not in LOG.open().readline():
            LOG.rename(LOG.with_name("ui_orders_log_before_stores.csv"))  # older log had no store column
        pd.DataFrame(records).to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
        counts = pd.Series([r["outcome"] for r in records]).value_counts()
        tab_order.success(f"Order placed: {counts.get('confirmed', 0)} confirmed, "
                          f"{counts.get('overridden', 0)} changed, {counts.get('manager_call', 0)} set by you.")

with tab_data:
    summary = json.load(open(SUMMARY))
    st.markdown("**Source:** Corporación Favorita Grocery Sales Forecasting (Kaggle) — a supermarket chain in "
                "Ecuador, 2013–2017, 125,497,040 daily sales rows. Raw files aren't redistributed "
                "(competition rules); `scripts/prepare_data.py` rebuilds everything below from them.")
    st.markdown("**How the items were chosen** (`scripts/prepare_data.py`) — each step keeps what can be ordered and "
                "forecast honestly:")
    st.dataframe(pd.DataFrame(summary["funnel"], columns=["Step", "What's left", "Why"]),
                 hide_index=True, use_container_width=True)
    st.markdown("**Stores and their roles.** Every design was developed on one store, then checked once on a "
                "store never looked at before (pre-registered in `DECISIONS.md`).")
    roles = [(44, "Development", "every design (v1, v2, v3, newsvendor) was built and tuned here"),
             (49, "Confirmation", "v1 / v2 ASK ME gates (not shown in this app)"),
             (8, "Confirmation", "v3: an order + likely range for every item"),
             (45, "Confirmation", "newsvendor order at the store's cost ratio")]
    st.dataframe(pd.DataFrame([(f"Store {s}", summary["per_store"][str(s)], r, u) for s, r, u in roles],
                              columns=["Store", "Items kept", "Role", "Used for"]),
                 hide_index=True, use_container_width=True)
    st.markdown("**What the raw data looks like** (first rows for store 44 — one row per item per day with a sale):")
    st.dataframe(pd.DataFrame(summary["sample"]), hide_index=True, use_container_width=True)
    st.caption("Every result is recomputed by a script in `experiments/` (e.g. `run_redesign.py`, "
               "`run_newsvendor.py`) and logged with its numbers in `DECISIONS.md`. This page shows 40 items "
               "per store on 7 dates; the results use every item on every test day.")

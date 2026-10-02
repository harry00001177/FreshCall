# FreshCall

Next-day fresh-food ordering copilot for the manager who places
tomorrow's fresh order, at a supermarket's fresh section or a fast-food
(QSR) restaurant. Validated on supermarket data. For every
SKU it gives tomorrow's order in whole cases (and units) — sized for the
store's own **cost ratio** (how much worse running out is than wasting) —
the **likely range** when the forecast is uncertain, and a one-line reason — with the
uncertain lines listed first, so the manager's attention goes where their
own knowledge (a promotion, a local event, a delivery problem) matters
most. Routine SKUs are collapsed as standing orders. Forecasts come from
quantile regression; every number and word on the manager's screen is
produced by deterministic Python. An LLM is used where it earned a place:
as a judge inside the evaluation.

NTU MSc Enterprise AI, PE6201 (Emerging AI Technologies), end-of-course
project.

**How this was built:** the code was written with AI assistance
(Claude Code). Every design decision was made by me, the human labels in
the evaluation were done by me, and every number reported was actually
run and can be reproduced from this repository.

**Demo video** (7:58, English captions burned in; `.srt` alongside):
[`video/FreshCall_demo.mp4`](./video/FreshCall_demo.mp4).

**For the marker, quickest path** (tested on Python 3.13; no Kaggle download, no
API key):

```bash
pip install -r requirements.txt
python -m pytest                                            # 156 tests
streamlit run app.py                                        # the manager's screen
PYTHONPATH=src:scripts:experiments python experiments/run_newsvendor.py evaluate 45   # re-score store 45
```

**Documentation:**

- [`docs/REPORT.md`](./docs/REPORT.md) (PDF: [`docs/FreshCall_Report.pdf`](./docs/FreshCall_Report.pdf)):
  the trade-off analysis report.
- [`docs/PRODUCT.md`](./docs/PRODUCT.md): persona, input, output,
  architecture diagram, metrics targeted vs reached.
- [`docs/DATA.md`](./docs/DATA.md): the data used, where it came from,
  every file in `data/`.
- [`docs/EVALS.md`](./docs/EVALS.md): every evaluation written, how to
  re-run it, what came out (including the failures).
- [`CONTEXT.md`](./CONTEXT.md): glossary.
- [`DECISIONS.md`](./DECISIONS.md): every decision, result and
  correction, with the real numbers.

## How the design got here

The project started as "size tomorrow's order, **or abstain**" (hand
uncertain SKUs back to the manager as ASK ME). Evaluated on Kaggle
Favorita data (a supermarket stand-in for QSR data; 4 stores × 400+ SKUs ×
3 rolling-origin folds, each design pre-registered before its test):

1. **v1 — abstain when the interval is wide (`rel_width`): failed.**
   Abstention precision at or below random; replicated on an unseen store.
2. **v2 — abstain when P10/P50/P90 imply different case counts: a real
   signal, unusable.** 1.26x better than random on an unseen store, but it
   hands back ~74–78% of SKUs.
3. **The real-value check changed the question.** Measured as wrong orders
   and minutes per 40-SKU night, the forecaster alone beats today's
   practice ("order what sold on the same day last week"), and every
   abstain gate gives that back — even on the SKUs it hands back, the
   model is wrong less often than "last week" (39.6% vs 46.5%). Handing a
   SKU to someone who has no extra information makes it worse.
4. **Redesign — every SKU gets an order plus its likely range: confirmed**
   on a third unseen store (store 8, pre-registered, all 3 folds). On the
   SKUs that need judgement, per 40-SKU night: wrong orders 13.3 → 10.3,
   units wasted −11%, units short −26%, and far less of the manager's time
   (faster under all 9 timing assumptions tested). The needed cases fall
   inside the shown range ~95% of the time; the widest-range quarter holds
   ~45% of the wrong orders. Trade-off stated, not hidden: on routine,
   low-volume SKUs the P50 order wasted more units than "last week" while
   cutting stockouts — which raised the next question.
5. **Newsvendor ordering — order for the store's costs: confirmed** on a
   fourth unseen store (store 45, pre-registered, all 6 cost ratios, 3/3
   folds each). Rounding a P50 forecast up to whole cases already covers
   demand on ~85–91% of days, so "P50" was really a high-service order
   whatever the store's costs. The new order picks the whole case count
   with the lowest expected cost over 9 quantile forecasts. Cost vs today's
   order, per 40-SKU night: −23% when a unit short and a unit wasted cost
   the same, −6% / −4% / −18% when running out costs 2× / 4× / 9× more
   (−21% to −35% vs "last week"). The first pre-registered version (order
   at quantile r/(1+r), then round up) lost at ratios 2 and 4 on the
   development stores; the amended rule was committed before store 45 was
   touched. Caveat: at low ratios much of the saving is ordering *nothing*
   (up to 64% of days), partly an artifact of no leftover carrying over —
   the ratio ≥ 2 results are the ones that survive it. The UI defaults to
   ratio 4 plus a "sold every day last week → at least 1 case" floor.

Also in `DECISIONS.md`: a deliberate-leak test (one missing `shift(1)`
would have faked a pass of the 15% target, +11.8% → +20.7%; the unit tests
catch it), bias/coverage monitors with a positive control, an explanation
harness (human labels + LLM judge + negative controls) that led from an
LLM-written sentence to a deterministic one, and every correction of a
wrong turn along the way.

Evaluation sheets for the explanation layer are in `data/l1l2/`, with
copies of the main tables in
[`results/explanation_harness/`](./results/explanation_harness/).

**Scope limits:** no inventory field, so this validates demand
estimation, uncertainty and the ordering display (Layer A), not
inventory-aware ordering (Layer B) — which also means waste is overstated
for both policies on low-volume SKUs. `case_pack=12` and all manager
timings are assumptions (`config.yaml`). What a manager knows that the
model doesn't is unmeasurable in this data.

## Layout

```text
src/freshcall/   the system: order, gate, case_gate, features, model,
                 explain, containment, monitors, backtest, decomposition,
                 harness, judge, redesign, newsvendor, ui_logic
tests/           pytest suite for every module above
scripts/         pipeline entry points:
  prepare_data.py    raw Kaggle CSVs -> derived files the pipeline reads
  make_demo_data.py  synthetic demo series (demo/), no Kaggle data needed
  run_slice.py       one SKU, end to end (Problem Statement Section 8)
  build_ui_cache.py  pre-generates what the UI shows
  run_backtest.py    multi-SKU, 3-fold rolling-origin backtest
app.py           the manager's one-page UI (Streamlit)
experiments/     every evaluation in DECISIONS.md, one script each:
  report_backtest.py              pre-registered tables from a backtest
  run_case_gate_experiment.py     case-straddle gate, store 49 confirmation
  run_error_decomposition.py      catchable vs uncaught errors
  run_sensitivity_active_skus.py  without discontinued SKUs
  run_sensitivity_lookahead.py    without look-ahead-selected SKUs
  run_leak_test.py                deliberate leak: before and after
  run_monitors.py                 bias / coverage monitors + positive control
  run_explanation_harness.py      L1 check + sheet for human labels
  run_judge.py                    L2 judge vs human labels
  run_judge_negative_control.py   does the judge catch flawed sentences?
  run_comparison_word_check.py    generator prompt change, before vs after
  run_redesign.py                 the redesign vs today (store 8 confirmation)
  run_time_sensitivity.py         manager minutes under 9 timing assumptions
  run_newsvendor.py               cost-ratio ordering (store 45 confirmation)
  run_explanation_v2.py           same-weekday fact block, 3-question labels
  run_explanation_v3.py           deterministic sentence vs the LLM one
config.yaml      all assumptions (case_pack, safety, gate threshold...)
data/            the data and stored predictions behind every result
                 (docs/DATA.md); the 5 GB raw train.csv is not included
results/         evaluation tables committed for review
video/           the recorded demo (mp4 + captions)
docs/            REPORT.md (+ PDF), PRODUCT.md, DATA.md, EVALS.md; problem statement
                 (v2 as submitted, v3 current)
```

## Quick demo (no Kaggle data needed)

```bash
pip install -r requirements.txt
python scripts/make_demo_data.py
PYTHONPATH=src python scripts/run_slice.py --demo
```

Runs the full predict → gate → order → explain path on a small synthetic
series (`demo/demo_sales.csv`). Demo data is never used for any reported
result.

## Manager UI

```bash
streamlit run app.py
```

The app reads `data/ui_cache.parquet`, which is checked in. To rebuild it
from the stored predictions (about a minute):

```bash
PYTHONPATH=src:scripts:experiments python scripts/build_ui_cache.py
```

One page: tomorrow's order for 40 SKUs at a chosen store — 45 or 8 (confirmation stores) or 44 (development) — as slim table-like
rows — item (with a colour-coded category tag), a likely-range bar with a
dot at the order, and an editable case count. Each row folds out to its
details: "ORDER 3 cases (36 units) · likely 1–5", the one-line reason
("Tuesdays have averaged 19.8 units, lower than last Tuesday's 45"), and
the numbers behind it. Ranges wider than 4 cases are shown in words
instead. Rows are listed widest range first; routine SKUs sit in a
collapsed "standing orders" block. **Place order** logs what was confirmed
or changed (`data/ui_orders_log.csv`). No confidence figure appears
anywhere, and the page calls no model and no LLM. The sidebar's
*evaluation view* (for demos, not managers) has a cost-ratio slider,
switches between the designs — v3 (current) and the earlier ASK ME designs v1 and v2 — and can
show what actually sold. A **Data** tab shows where the data comes from, how items were chosen (the filter funnel, with why each step exists), which store played which role, and a few raw rows. A **Results** tab charts the three claims behind the design — handing items back (store 44), v3 on an unseen store (8), and ordering for the store's costs (45) — computed by the experiment scripts' own functions from every test day, with a table view. Favorita has no item names (only number,
category and class), so items are shown by category and number.

## Setup

```bash
pip install -r requirements.txt
```

The manager-facing path needs no API key. The evaluation scripts that use
an LLM (the judge, and the earlier LLM-written sentences they compare
against) call OpenRouter; put the key in a `.env` file (gitignored):

```text
OPENROUTER_API_KEY=sk-or-...
```

## Data

Source: [Corporación Favorita Grocery Sales Forecasting](https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting/data)
(Kaggle; 125,497,040 training rows, 54 stores, 4,100 items).

The data every result was computed from is checked in under `data/`: the
perishable-item sales (86 MB), the item lists, the stored predictions of
every backtest and the evaluation sheets. Only the 5 GB raw `train.csv` is
left out (too large for GitHub). So a fresh clone can open the app,
re-score and re-run everything without a Kaggle download. What each file
is, how it was made, and how to rebuild it from the original download:
[`docs/DATA.md`](./docs/DATA.md).

## Run

From the repository root:

```bash
python -m pytest
PYTHONPATH=src python scripts/run_slice.py
PYTHONPATH=src python scripts/run_backtest.py data/full_426_skus.parquet
```

Experiments (they import each other, hence the longer path). The three
confirmation results first, then the rest:

```bash
export PYTHONPATH=src:scripts:experiments
python experiments/run_newsvendor.py evaluate 45   # newsvendor order, store 45
python experiments/run_redesign.py                 # v3 redesign, store 8
python experiments/run_time_sensitivity.py         # manager minutes
python experiments/report_backtest.py data/backtest_results.parquet
python experiments/run_case_gate_experiment.py
python experiments/run_error_decomposition.py
python experiments/run_sensitivity_active_skus.py
python experiments/run_sensitivity_lookahead.py
python experiments/run_leak_test.py
python experiments/run_monitors.py
python experiments/run_explanation_harness.py 1   # then label, then:
python experiments/run_judge.py
```

Re-scoring from stored predictions takes seconds to a minute. The full
backtest (and the leak test) take about 6 minutes per store. The
confirmation scripts do not re-fit when their predictions file exists
(pre-registered: one run); rename the file first to re-fit. All scripts and their
results: [`docs/EVALS.md`](./docs/EVALS.md).
The explanation and judge scripts call paid APIs and overwrite their
sheets under `data/l1l2/`.

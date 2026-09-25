# FreshCall

Next-day fresh-food ordering copilot for QSR store managers: forecast
tomorrow's demand with an interval, turn it into a whole-case order with
deterministic Python, and **abstain** (hand the SKU back to the manager)
when the forecast shouldn't be trusted. An LLM only writes the one-line
explanation, and every number it writes is checked against the facts it
was given.

NTU MSc Enterprise AI, PE6201 (Emerging AI Technologies), end-of-course
project. Glossary: [`CONTEXT.md`](./CONTEXT.md). Every decision, result and
correction, with the real numbers: [`DECISIONS.md`](./DECISIONS.md).

## Status and findings

The full pipeline runs end to end and has been backtested on 2 stores ×
400+ SKUs × 3 rolling-origin folds (Kaggle Favorita data, a supermarket
stand-in for QSR data). Headline results, all detailed in `DECISIONS.md`:

- **Forecasting layer:** beats a "same day last week" baseline on the same
  answered SKU-days at every threshold and fold. Relative improvement is
  +4% to +12% on store 44 in the primary run; excluding 21 SKUs that had
  stopped selling before the test period, +14.6% (store 44) and +20.0%
  (store 49) at threshold 1.00 — around the 15% target, store-dependent.
- **Original abstain gate (interval width, `rel_width`): failed.**
  Abstention precision is at or below random; replicated on a second,
  unseen store and with the discontinued SKUs removed.
- **Pre-registered replacement (abstain when P10/P50/P90 imply different
  case counts): a real signal** — 1.26x better than random on the unseen
  confirmation store, all folds (1.24x without discontinued SKUs) — **but
  not usable as-is**: it abstains on ~74–78% of SKU-days, far past the
  manager-attention break-even.
- **Error decomposition:** ~94% of would-be errors are detectable from the
  interval; the limit is the attention cost of acting on that, not
  detection.
- **Explanation layer:** numeral containment passed 14/14 raw LLM
  sentences; Harry and an independent judge model (Claude Haiku 4.5)
  agreed on all 17 labelled sentences. A negative-control test showed the
  judge catches 5 of 6 deliberately flawed sentences but misses overstated
  comparisons ("significantly" on a tiny gap) — fixed at the source by
  restricting the generator's comparison words (intensity words 4/7 → 0/7).
  One real sentence was true in every word yet argued for ordering *more*
  than the (correct) recommendation — the "true but misleading" risk the
  Problem Statement predicted, which no check here catches.
- **Leakage check:** injecting one realistic bug (a 7-day mean that
  includes the day being predicted) inflates the forecaster's improvement
  from +11.8% to +20.7% — a fake pass of the 15% target — while interval
  coverage barely moves; the existing unit test catches it. Hunting for
  leakage also found SKU selection had used test-period sales for 5 of 426
  SKUs; dropping them changes nothing material.
- **Monitors:** bias and coverage monitors (bands fitted on the first
  fold) stay quiet on the real test windows apart from one day; on a
  simulated +50% demand shift the bias monitor alerts the next day.
  Built guardrails: numeral containment with template fallback, the
  abstain gate, the two monitors. Not built: holiday rule, novelty check,
  per-order confirmation UI.

Evaluation tables for the explanation layer are in
[`results/explanation_harness/`](./results/explanation_harness/) (7–17
rows each, with a few derived numbers from the Kaggle data per row).

Scope limit: the dataset has no inventory field, so this validates demand
estimation, uncertainty and abstention (Layer A), not inventory-aware
ordering (Layer B). `case_pack=12` is an assumption; see `config.yaml`.

## Layout

```text
src/freshcall/      order, gate, case_gate, features, model, explain,
                    containment, backtest, decomposition, harness, judge,
                    monitors
tests/              pytest suite for every module above
prepare_data.py     raw Kaggle CSVs -> derived files the pipeline reads
run_slice.py        one SKU, end to end (Problem Statement Section 8)
run_backtest.py     multi-SKU, 3-fold rolling-origin backtest
report_backtest.py  pre-registered tables from a saved backtest
run_case_gate_experiment.py    pre-registered case-straddle experiment
run_error_decomposition.py     catchable vs uncaught error breakdown
run_sensitivity_active_skus.py same results without discontinued SKUs
run_explanation_harness.py     L1 check + sheet for human labels
run_judge.py                   L2 judge vs human labels
run_judge_negative_control.py  does the judge catch flawed sentences?
run_comparison_word_check.py   generator prompt change, before vs after
run_leak_test.py               deliberate leak: before-and-after
run_sensitivity_lookahead.py   results without look-ahead-selected SKUs
run_monitors.py                bias / coverage monitors + positive control
make_demo_data.py              synthetic demo series (demo/)
config.yaml         all assumptions (case_pack, safety, gate threshold...)
results/            evaluation tables committed for review
docs/               problem statement (v2 as submitted, v3 current),
                    project overview, original handoff
```

## Quick demo (no Kaggle data needed)

```bash
pip install -r requirements.txt
python make_demo_data.py
PYTHONPATH=src python run_slice.py --demo
```

Runs the full predict → gate → order → explain path on a small synthetic
series (`demo/demo_sales.csv`). Demo data is never used for any reported
result.

## Setup

```bash
pip install -r requirements.txt
```

The explanation step calls `openai/gpt-4o-mini` via OpenRouter. Put the key
in a `.env` file (gitignored):

```text
OPENROUTER_API_KEY=sk-or-...
```

Without a key the pipeline still runs: the explanation falls back to a
deterministic template.

## Data

Raw Kaggle data is never committed (competition rules prohibit
redistribution). You need a Kaggle account, the competition rules accepted
on the competition page, and an API token (Kaggle CLI 2.x reads
`~/.kaggle/access_token`).

```bash
kaggle competitions download -c favorita-grocery-sales-forecasting -p data
cd data && unzip favorita-grocery-sales-forecasting.zip && for f in *.7z; do 7z x -y "$f"; done && cd ..
python prepare_data.py
```

`7z` comes from `brew install p7zip`. `prepare_data.py` takes a few
minutes (it scans the ~5 GB `train.csv`).

## Run

```bash
python -m pytest
PYTHONPATH=src python run_slice.py
PYTHONPATH=src python run_backtest.py data/full_426_skus.parquet
PYTHONPATH=src python report_backtest.py data/backtest_results.parquet
PYTHONPATH=src:. python run_case_gate_experiment.py
PYTHONPATH=src python run_error_decomposition.py
PYTHONPATH=src:. python run_sensitivity_active_skus.py
PYTHONPATH=src python run_explanation_harness.py 1   # then label, then:
PYTHONPATH=src python run_judge.py
PYTHONPATH=src:. python run_leak_test.py
PYTHONPATH=src python run_monitors.py
```

The full backtest takes about 6 minutes per store.

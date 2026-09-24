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
  answered SKU-days at every threshold and fold, by +4% to +12% relative
  on store 44 — below the Problem Statement's 15% target.
- **Original abstain gate (interval width, `rel_width`): failed.**
  Abstention precision is at or below random; replicated on a second,
  unseen store.
- **Pre-registered replacement (abstain when P10/P50/P90 imply different
  case counts): a real signal** — 1.26x better than random on the unseen
  confirmation store, all folds — **but not usable as-is**: it abstains on
  ~74–78% of SKU-days, far past the manager-attention break-even.
- **Error decomposition:** ~94% of would-be errors are detectable from the
  interval; the limit is the attention cost of acting on that, not
  detection.

Scope limit: the dataset has no inventory field, so this validates demand
estimation, uncertainty and abstention (Layer A), not inventory-aware
ordering (Layer B). `case_pack=12` is an assumption; see `config.yaml`.

## Layout

```text
src/freshcall/      order, gate, case_gate, features, model, explain,
                    containment, backtest, decomposition
tests/              pytest suite for every module above
prepare_data.py     raw Kaggle CSVs -> derived files the pipeline reads
run_slice.py        one SKU, end to end (Problem Statement Section 8)
run_backtest.py     multi-SKU, 3-fold rolling-origin backtest
report_backtest.py  pre-registered tables from a saved backtest
run_case_gate_experiment.py  pre-registered case-straddle experiment
run_error_decomposition.py   catchable vs uncaught error breakdown
config.yaml         all assumptions (case_pack, safety, gate threshold...)
docs/               problem statement, project overview, original handoff
```

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
```

The full backtest takes about 6 minutes per store.

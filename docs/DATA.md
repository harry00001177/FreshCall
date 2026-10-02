# Data: what was used, where it came from, and what each file is

Everything FreshCall's results were computed from is checked in under
`data/`, except the 5 GB raw sales file, which is too large for GitHub. A
fresh clone can open the app, re-score every result, and re-run every
backtest without downloading anything. Only rebuilding the derived sales
file from scratch needs the original download.

How each evaluation uses these files: [`EVALS.md`](./EVALS.md).

## Source

**Corporación Favorita Grocery Sales Forecasting** (Kaggle competition,
2017): daily unit sales of a supermarket chain in Ecuador.
<https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting/data>

- 125,497,040 sales rows, 54 stores, 4,100 items, 2013-01-01 to 2017-08-15.
- No personal data. No item names (only number, category and class), so
  the app shows items by category and number.
- **No inventory or on-hand field.** A day with no sales cannot be told
  apart from a stockout, and an order that depends on stock carried over
  cannot be validated. This is the main limit of every result.
- Why a supermarket for a fresh-food ordering tool: I found no public QSR
  dataset with daily item-level sales. The ordering problem has the same
  shape.

**Terms.** Use here is non-commercial, for a university course project.
The data belongs to Corporación Favorita and is provided under Kaggle's
competition rules; check them on the competition page before any other
use. The checked-in files are included only so the course staff can
reproduce the results.

## From raw data to the files in this repo

```text
train.csv (125.5M rows, 5 GB; not in the repo)
  │  scripts/prepare_data.py
  │  keep perishable items (items.csv perishable = 1)
  ▼
derived_perishable_train.parquet   986 items, 31,702,536 rows, all 54 stores
  │  keep items sold in whole units in every store       → 707 items
  │  keep store-item pairs sold on ≥ 70% of days          → 18,586 pairs
  │  keep pairs first sold on or before 2015-06-01         → 13,218 pairs
  ▼
item lists per store: 44 (426 items), 49 (436), 8 (433), 45 (428)
  │  scripts/run_backtest.py, experiments/*  (3 rolling-origin folds)
  ▼
stored predictions (backtest_results*, newsvendor_store*)
  │  experiments/*  re-score;  scripts/build_ui_cache.py
  ▼
app data (ui_cache.parquet, ui_data_summary.json, ui_results.json)
```

Why each filter exists:

| Filter | Why |
|---|---|
| Perishable | fresh food is what gets thrown away |
| Whole units in every store | items sold by weight cannot be ordered in cases |
| Sold on ≥ 70% of days | items that rarely sell make every forecast a guess |
| First sale by 2015-06-01 | enough history to train before all three test months |

`train.csv` leaves out days with zero sales, so the code rebuilds the full
daily grid (missing day = 0 units) before computing any feature.

**Store roles.** Store 44 is the development store (the most qualifying
items at every density threshold tried). Stores 49, 8 and 45 were each
picked by the same rule and used once to confirm a design: 49 for the v1
and v2 gates, 8 for the v3 redesign, 45 for the newsvendor order.

## Files in `data/`

### Sales and reference data (from Kaggle)

| File | Size | Contents | Read by |
|---|---|---|---|
| `derived_perishable_train.parquet` | 86 MB | `date`, `store_nbr`, `item_nbr`, `unit_sales` (net, returns kept as negatives), `is_int` (unused leftover from an earlier version of `prepare_data.py`). Perishable items only | every backtest, `run_slice.py`, most experiments |
| `items.csv` | 0.1 MB | item number, family (category), class, perishable flag | `prepare_data.py`, `build_ui_cache.py` |
| `stores.csv` | 1 KB | store number, city, state, type, cluster | `run_error_decomposition.py` |
| `holidays_events.csv` | 22 KB | Ecuador holidays and events | `run_error_decomposition.py` |

### Item lists (output of the filters above)

| File | Rows | Contents |
|---|---|---|
| `full_426_skus.parquet` | 426 | store 44's items: `item_nbr`, first and last sale date, `density` |
| `pilot_30_skus.parquet` | 30 | first 30 of the above (the pilot run) |
| `store49_candidates.parquet` | 436 | store 49's items |
| `store8_candidates.parquet` | 433 | store 8's items |
| `store45_candidates.parquet` | 428 | store 45's items |

### Stored predictions (one row per item per test day)

| File | Rows | From | Contents |
|---|---|---|---|
| `backtest_results.parquet` | 39,192 | store 44, 3 quantiles | P10 / P50 / P90, actual units, last week's order, hindsight order, gate decision |
| `backtest_results_prefix.parquet` | 39,192 | store 44, before the E2 fix | same columns; kept so the "before" numbers can be checked |
| `backtest_results_leaky.parquet` | 39,192 | store 44, deliberate leak (E8) | same columns |
| `backtest_results_store49.parquet` | 40,112 | store 49 (confirmation, E3) | same columns |
| `backtest_results_store8.parquet` | 39,836 | store 8 (confirmation, E15) | same columns |
| `newsvendor_store44.parquet` | 39,192 | store 44, 9 quantiles | `q0.1` … `q0.9`, actual, last week's units and order, hindsight order |
| `newsvendor_store8.parquet` | 39,836 | store 8, 9 quantiles | same columns |
| `newsvendor_store45.parquet` | 39,376 | store 45 (confirmation, E17) | same columns |

### App data (built by `scripts/build_ui_cache.py`)

| File | Contents |
|---|---|
| `ui_cache.parquet` | 840 rows: 40 items × 7 test days × 3 stores (45, 8, 44), with forecasts, orders, ranges and what actually sold |
| `ui_data_summary.json` | the Data tab: filter funnel, items per store, sample raw rows |
| `ui_results.json` | the Results tab: the three charts' numbers |

### Evaluation sheets

`data/l1l2/`: the explanation-harness sheets (LLM and template sentences,
Harry's labels, judge verdicts). Listed file by file in
[`EVALS.md`](./EVALS.md#e9-to-e13-the-reason-sentence-from-llm-to-template).

### Not in the repo

| File | Why |
|---|---|
| `train.csv` (5 GB), `*.7z` archives | too large for GitHub; download from Kaggle (below) |
| `oil.csv`, `transactions.csv`, `test.csv` | never used |
| `ui_orders_log.csv` | written by the app when you press Place order |

## Rebuilding from the original download (optional)

Only needed to regenerate `derived_perishable_train.parquet` and the item
lists yourself. Needs a Kaggle account, the competition rules accepted on
the competition page, and an API token (Kaggle CLI 2.x reads
`~/.kaggle/access_token`). `7z` comes from `brew install p7zip`.

```bash
kaggle competitions download -c favorita-grocery-sales-forecasting -p data
cd data && unzip favorita-grocery-sales-forecasting.zip && for f in *.7z; do 7z x -y "$f"; done && cd ..
python scripts/prepare_data.py
```

`prepare_data.py` scans the 5 GB `train.csv` and takes a few minutes. It
writes the derived sales file and the store 44 / 49 item lists; the
store 8 and 45 lists are written by `experiments/run_newsvendor.py` with
the same rule when missing.

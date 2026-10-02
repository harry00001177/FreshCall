# Evaluations: what was tested, how, and what came out

Every evaluation written while building FreshCall, including the ones
that failed. Each one has a script in `experiments/` (or `scripts/`), its
inputs and outputs in `data/` or `results/`, and a dated entry in
[`DECISIONS.md`](../DECISIONS.md) with the full tables. The data files
themselves are explained in [`DATA.md`](./DATA.md).

## The rules every evaluation followed

1. **Pre-registration.** The pass/fail criterion was committed to git
   before the result existed. The commit hash is in the decision log, so
   anyone can check the criterion was not moved after the fact. When a
   rule had to change (E17), the amended criterion was committed before
   the confirmation store was touched, and the first version's failure is
   reported.
2. **Develop on one store, confirm on an unseen one.** Store 44 is the
   development store. Each new design was confirmed once, on a store not
   looked at before: 49 (v1/v2 gates), 8 (v3 redesign), 45 (newsvendor
   order). A confirmation backtest saves its predictions without printing
   any metric, then is scored once.
3. **Rolling-origin time folds.** Three folds, each trained on everything
   before its 31-day test window: 2017-05-16 to 06-15, 06-16 to 07-15,
   07-16 to 08-15. Folds are reported separately, so one holiday weekend
   cannot carry a result.
4. **The baseline is what managers do today:** same weekday last week,
   rounded up to whole cases. Scored on exactly the same item-days as the
   system.
5. **Metrics a manager feels:** wrong orders (wrong number of cases),
   units wasted, units short, cost at the store's cost ratio, minutes.
   "Per night" means per 40-item ordering night.

## How to re-run

```bash
pip install -r requirements.txt
export PYTHONPATH=src:scripts:experiments
python -m pytest                                   # 156 unit tests
python experiments/run_newsvendor.py evaluate 45   # re-score store 45 (E17)
python experiments/run_redesign.py                 # v3 on store 8 (E15)
```

Scripts marked "reads stored predictions" re-score in seconds from the
committed files. Scripts marked "refits" retrain models (about 3.5 to 6
minutes per store). Scripts marked "LLM" call OpenRouter, cost money and
need `OPENROUTER_API_KEY` in `.env`; they overwrite their sheets in
`data/l1l2/`, so the committed sheets are the record of the runs reported.

Confirmation scripts do not re-fit when their predictions file already
exists (the pre-registration allows one run): `run_newsvendor.py
backtest` refuses, `run_case_gate_experiment.py` re-scores the saved
file. To re-fit, rename the predictions file first.

## Index

| # | Question | Script | Kind | Result | Log entry |
|---|---|---|---|---|---|
| E0 | Do the core invariants hold? | `python -m pytest` | unit tests | 156 pass | throughout |
| E1 | Does the minimal slice run end to end? | `scripts/run_slice.py` | refits one item | all checks pass | 2026-09-23 |
| E2 | Is the forecaster better than last week? Does the v1 gate abstain where the model is wrong? Are the intervals calibrated? | `scripts/run_backtest.py`, `experiments/report_backtest.py` | refits / reads | +4% to +12% (target 15%); gate at or below random; coverage 77.6% vs 80% | 2026-09-24 (×5) |
| E3 | Does the v2 case-straddle gate work on an unseen store? | `run_case_gate_experiment.py` | refits store 49 | lift 1.26x, but hands back 74% | 2026-09-24 |
| E4 | Are errors catchable at all? | `run_error_decomposition.py` | reads | ~94% catchable; the price is attention | 2026-09-24 |
| E5 | Do results survive dropping discontinued items? | `run_sensitivity_active_skus.py` | reads | yes; forecaster +14.6% / +20.0% | 2026-09-24 |
| E6 | Do results survive dropping items picked with look-ahead? | `run_sensitivity_lookahead.py` | reads | no material change | 2026-09-25 |
| E7 | Would monitors notice a demand shift? | `run_monitors.py` | reads | quiet on real data; fire 1 day after a planted shock | 2026-09-25 |
| E8 | Would a feature leak fool the evaluation? | `run_leak_test.py` | refits store 44 | +11.8% → +20.7% (fake pass); unit tests catch it | 2026-09-25 |
| E9 | Are LLM-written reasons faithful? Does an LLM judge agree with a human? | `run_explanation_harness.py`, `run_judge.py` | LLM | L1 14/14; judge 0 disagreements on 17, but a "true but misleading" sentence found | 2026-09-24 |
| E10 | Does the judge catch deliberately broken sentences? | `run_judge_negative_control.py` | LLM | 5 of 6, 0 false alarms; misses overstatement | 2026-09-25 |
| E11 | Does restricting comparison words fix overstatement? | `run_comparison_word_check.py` | LLM | 7/7 pass (was 3/7) | 2026-09-25 |
| E12 | Does a same-weekday fact block fix the misleading sentence? | `run_explanation_v2.py` | LLM | met; but LLM breaks the 10% rule in 2/14 | 2026-09-25 |
| E13 | Does a fixed template beat the LLM sentence? | `run_explanation_v3.py` | template + LLM judge | 14/14 on every check; judge "direction" 7/14 | 2026-09-25 |
| E14 | What does a manager actually experience (wrong orders, minutes)? | `scripts/build_ui_cache.py` (Results tab), `run_time_sensitivity.py` | reads | last week 15.5; v2 15.2 / ~16 min; model answers all 13.1 / 3.3 min | 2026-09-25, corrected 2026-10-01 |
| E15 | Does v3 (order + range for every item) beat last week on an unseen store? | `run_redesign.py` | reads | store 8: 13.3 → 10.3 wrong orders, 3/3 folds | 2026-09-25 |
| E16 | Does the time saving depend on the timing guesses? | `run_time_sensitivity.py` | reads | holds in all 9 combinations | 2026-09-25 |
| E17 | Does ordering for the store's costs beat the old order? | `run_newsvendor.py` | refits / reads | store 45: cheaper at all 6 ratios, 3/3 folds | 2026-09-28 (×4) |

## Details

### E0. Unit tests: the invariants

156 tests in `tests/`, one file per module. They pin the rules a wrong
number would break: orders are always a whole number of cases; every
numeral in a sentence must exist in the fact block; lag and rolling
features never include the day being predicted (the test that catches
the E8 leak); the newsvendor order is the lowest-cost case count; the
abstain message gives no quantity and no confidence figure.

### E1. Minimal slice (Problem Statement section 8)

One real item (store 44, item 502331), predict → order → explain.
Criteria: units are a multiple of the case pack (asserted in code); every
numeral in the sentence is in the fact block; a wide interval gives an
abstain message with no quantity. **All pass**, on real data and on the
synthetic demo series (`run_slice.py --demo`).

### E2. Forecaster, v1 gate, calibration (store 44, development)

426 items × 3 folds (39,192 item-days). Criteria from the Problem
Statement: forecaster ≥ 15% better than last week in Case Match Rate on
the answered items; abstention precision better than random at about 15%
abstain; P10–P90 coverage near 80%.

- Forecaster: **+4% to +12%**, ahead of last week in every fold and
  threshold, but **below the 15% target**.
- v1 gate (`rel_width`): precision **0.87x to 1.01x random**, and it never
  got near 15% abstain (58% at the loosest threshold). This met the
  Problem Statement's own abandon condition. Replicated on store 49 (E3).
- Coverage 77.6% against 80% nominal.
- A first full run looked much worse (model CMR 25.8%). The cause was
  first misdiagnosed and then corrected in the log; the fix was
  pre-registered before re-running. Raw pre-fix predictions are kept in
  `data/backtest_results_prefix.parquet`.

### E3. v2 case-straddle gate (store 49, confirmation)

Abstain when P10, P50 and P90 imply different case counts. Criterion:
lift over random > 1.0 pooled and in ≥ 2 of 3 folds. **Passed: 1.26x,
3/3 folds**, but it hands back **74%** of items. A real signal, unusable
as a product.

### E4. Error decomposition (stores 44, 49)

Descriptive. About 94% of the model's wrong orders have an interval that
spans a case boundary, so they are "catchable"; only 5–6% are confident
and wrong. Detection is not the bottleneck; the attention it costs is.

### E5, E6. Sensitivity checks

E5 drops 21 items per store that had stopped selling: the gate result
holds (1.19x / 1.24x) and the forecaster improves to +14.6% / +20.0%, so
"below target" is not robust either way. E6 drops 5 items per store whose
selection used future data: no material change to any number.

### E7. Monitors with a positive control

Bias and coverage monitors, bands fitted on fold 1. On real data: one
alert day (store 44, 2017-08-13). With a planted +50% shock from
2017-08-01, the bias monitor fired on 2017-08-02. Store-level only.

### E8. Deliberate leak test

The 7-day mean was made to include the day being predicted. The
forecaster's improvement jumped **+11.8% → +20.7%**, a false pass of the
15% target. Coverage barely moved (77.6% → 78.3%), so calibration would
not have caught it; the unit test does. Output:
`data/backtest_results_leaky.parquet`.

### E9 to E13. The reason sentence: from LLM to template

Two layers checked each sentence. **L1** (deterministic): every numeral
must be in the fact block. **L2**: an LLM judge (Claude Haiku 4.5 via
OpenRouter, a different vendor from the gpt-4o-mini generator), checked
against Harry's blind human labels, which are the reference.

| Step | What was tested | Result |
|---|---|---|
| E9 | 17 LLM sentences, human labels, judge | L1 14/14; judge agreed with Harry on all 17. Found case 16: every number true, but the reason argued for ordering more while the order was small |
| E10 | 6 deliberately broken sentences + 2 clean | judge caught 5/6 (recall 5/6), 0 false alarms (precision 5/5); missed "significantly" for 36.9 vs 39.0. Only 8 items, so a probe, not a rate |
| E11 | generator limited to higher / lower / about the same | 7/7 pass (was 3/7) |
| E12 | fact block uses the same weekday's 4-week average | case 16 fixed; but the LLM broke the "about the same within 10%" rule in 2 of 14, and mixed cases with unlabelled units |
| E13 | fixed template instead of the LLM | 14/14 on every check, Harry yes on all 14; judge said "direction" was wrong in 7/14, all checked and all wrong (it compared cases with units) |

**Outcome:** the manager's screen uses the template and makes no LLM
call. The judge stays a first screen in the evaluation, not an authority.
Sheets: `data/l1l2/` (copies of the two judge tables and the
before/after comparison also in `results/explanation_harness/`).

| File | What it holds |
|---|---|
| `cases.csv`, `cases_batch2.csv` | batch 1 (10) and batch 2 (7): fact block, LLM sentence, L1 result, Harry's labels |
| `judged.csv` | E9: judge verdicts and reasons next to Harry's labels |
| `negative_control.csv` | E10: the 8 control sentences and the judge's verdicts |
| `cases_batch2_v2.csv` | E11: batch 2 regenerated with the restricted words |
| `cases_v3.csv`, `judged_v3.csv` | E12: 14 sentences from the same-weekday fact block, Harry's 3 labels, judge |
| `cases_v3_template.csv`, `judged_v3_template.csv` | E13: the template sentences, labels, judge |

### E14. What a manager experiences (store 44, development)

Per night. The minutes are assumptions (30 s per item today, 5 s to scan
a suggestion, 30 s for a handed-back item). A handed-back item is assumed
to be ordered the way managers do today.

| Policy | Wrong orders | Minutes |
|---|---|---|
| Copy last week (today) | 15.5 | 20.0 |
| v2: hand back uncertain items | 15.2 | ~16 |
| Model answers every item | 13.1 | 3.3 |

This is why the abstain design was dropped. **Correction on record:** the
first version priced a handed-back item at 90 s (47.5 minutes), which
contradicted the table's own proxy. Found on review, recomputed, and both
versions kept in the log (2026-10-01).

### E15. v3 redesign (store 8, confirmation)

Every item gets an order and its likely range. Criterion: on items that
need judgement, beat last week on both wrong orders and unit error in
≥ 2 of 3 folds. **Met, 3/3 folds.** Wrong orders 13.3 → 10.3, units
wasted −11%, units short −26%. The needed cases fall inside the shown
range 94.8% of the time. Trade-off reported: on slow routine items the
model wastes more than last week (243.5 → 281.0 units) to avoid running
out (9.4 → 1.3).

The store 8 predictions were fitted with the same backtest function as
store 44, run once from the command line rather than from a saved script.
To re-fit them (about 6 minutes):

```bash
PYTHONPATH=src:scripts python -c "import pandas as pd, yaml; from run_backtest import run_backtest; \
cfg = yaml.safe_load(open('config.yaml')); raw = pd.read_parquet('data/derived_perishable_train.parquet'); \
items = pd.read_parquet('data/store8_candidates.parquet')['item_nbr'].tolist(); \
run_backtest(items, 8, cfg, raw).to_parquet('data/backtest_results_store8_refit.parquet', index=False)"
```

Checked on 2026-10-02 for two items: the re-fit predictions match the
stored ones exactly.

### E16. Time sensitivity

v3 minutes vs today over a grid of 3 × 3 timing guesses: v3 is faster in
all 9. No timing was ever measured with a real manager.

### E17. Newsvendor ordering (store 45, confirmation)

Order the whole case count with the lowest expected cost, where one unit
short costs `ratio` times one unit wasted. Criterion: cheaper than the
old P50 order, pooled and in ≥ 2 of 3 folds, at every ratio tested.

- **First version failed on the development stores** (order at quantile
  r/(1+r), then round up: it over-ordered at ratios 2 and 4). Cause found,
  rule amended, amended criterion committed before store 45 was touched.
- **Store 45: met at all 6 ratios, 3/3 folds each.** Cost vs the old order:
  −62 / −45 / −23 / −6 / −4 / −18% at ratios 0.25 / 0.5 / 1 / 2 / 4 / 9;
  −21% to −35% vs last week at ratios ≥ 2.
- **Caveat:** at ratios below 2 most of the saving is ordering nothing
  (up to 64% of days), partly because the data has no stock carried over.
  Only ratios ≥ 2 are quoted.

## Critique of the evaluation itself

- **The manager is simulated.** Every value result assumes the manager
  accepts every suggestion, or orders like last week when handed an item.
  What a real manager knows that the model does not is not in the data.
- **Timings are guesses.** Minutes are shown as a sensitivity grid
  because none was measured.
- **Waste is overstated** for every policy on slow items (no inventory:
  each day starts from zero). Compare policies with each other, not the
  absolute units with a real store.
- **Small samples in the language checks:** 6 to 17 sentences per batch,
  one human labeller. They show the failure modes exist; they are not
  rate estimates.
- **Same city:** stores 44 and 8 are both in Quito.
- **The LLM judge is unreliable on direction and on overstatement.** It
  is kept as a screen, never as the reference.

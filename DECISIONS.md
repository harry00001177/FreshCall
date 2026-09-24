# FreshCall — Decision Log

Format: date / decision / why + what was rejected / real numbers (or "not
run yet"). This is raw material for resume bullets and interview stories —
log every substantive step, including failed attempts.

---

## 2026-09-22 — Repo initialized, terminology locked, plan grilled

**What:** Set up `~/Documents/FreshCall` as a git repo (pushed to GitHub).
Ran a design grill over the Problem Statement / handoff doc before writing
any code.

**Decisions made:**
- Rename "PH order" → `hindsight_demand_order`, and "CPOA" → `Case Match
  Rate (CMR)`. Why: both old names implied the prototype validates
  inventory-aware ordering optimality (Layer B), which the Favorita dataset
  cannot support (no inventory field). Rejected alternative: keep the names
  and add a disclaimer paragraph — rejected because a name is read before a
  disclaimer, and "Order Accuracy" is the kind of phrase a grader or
  interviewer will quote back at face value.
- Keep quantile GBR (three separate `GradientBoostingRegressor` models,
  non-crossing sort) instead of switching to split conformal prediction.
  Why: conformal prediction would give a coverage *guarantee* instead of
  hoping calibration works out, but swapping architecture pre-code adds a
  new concept to learn under budget/time pressure. Decision: ship quantile
  GBR for the minimal version, run the interval-calibration check as
  planned, and only reach for conformal prediction later if calibration
  actually comes back bad — let the empirical result drive the next
  architecture decision, not a resume-keyword.
- Returns (negative `unit_sales`) will be kept as raw net values, not
  clipped to 0. Why: clipping would artificially smooth demand and make the
  calibration check look better than the real world is — retaining the
  noise is the honest test of the interval.
- `safety` stays 0 in the prototype (not a real-store recommendation) so
  recommended cases are directly comparable to `hindsight_demand_order`.
- Novelty check (IsolationForest) deferred until the single-gate (`rel_width`)
  pipeline is working end-to-end and calibration passes. Why: debugging two
  interacting gates from zero is harder than debugging one, and it isn't
  part of the §8 minimal-version pass/fail criteria.
- `confidence` banned as a word anywhere in the codebase — see CONTEXT.md.

**Numbers:** none yet — no code has run. Python 3.13.5, scikit-learn 1.6.1,
pandas 2.2.3, numpy 2.1.3 confirmed installed locally. Kaggle CLI not yet
configured (`~/.kaggle/kaggle.json` missing) — action item for Harry:
accept competition rules on Kaggle and generate an API token.

**Deadline:** end-of-course project final submission confirmed as 2026-10-04
23:59 SGT (the earlier 2026-09-20 date in the official timeline PDF was
superseded by a later course announcement — verify this stays correct).

---

## 2026-09-22 — Kaggle set up, real data explored, D3/D4/D7-adjacent decisions closed

**What:** Registered a Kaggle account, accepted the competition rules, generated
an API token, downloaded and extracted the full Favorita dataset (~5GB
uncompressed) into `data/` (gitignored). Ran real analysis to close the open
D3/D4 decisions instead of guessing.

**Numbers (all run, not estimated):**
- 54 stores, 4,100 items in `items.csv`, 986 flagged `perishable=1`. Matches
  the handoff's prior desk-research facts exactly.
- Returns (negative `unit_sales`) among perishable items: 1,345 rows out of
  31,702,536 (0.004%) — confirms the earlier "keep raw, don't clip" call
  (2026-09-22 entry above) was low-risk.
- Of 986 perishable items, 707 (72%) are sold in whole-unit (integer)
  quantities everywhere; 279 are sold by weight (float `unit_sales`, no
  case-pack concept) and are excluded by the existing filter chain.
- Density (share of days with a sales record, within each SKU's own active
  date range) at threshold ≥0.7: 18,586 qualifying (store, item) pairs
  system-wide. Store 44 is the top store at every threshold tested
  (0.5/0.6/0.7/0.8/0.9), with 541 qualifying SKUs at 0.7 — comfortably above
  the ~40 needed.

**Decisions made:**
- **D3 = store 44** (Quito, type A, cluster 5), **D4 = density threshold
  0.7**. Why: store 44 topped the qualifying-SKU count at every threshold
  tried, so it isn't a threshold-dependent artifact; 0.7 leaves 537 usable
  SKUs at that one store, far more headroom than the ~40-SKU target needs.
- **First single-SKU pipeline test = item 502331** (BREAD/BAKERY, class
  2702) at store 44: 1,679 of 1,687 possible days recorded (density 0.995),
  daily sales mean 86 / std 34 / range 26–222. Why this one specifically:
  it's the cleanest (least missing data) of the 537 candidates, so a bug in
  the §8 minimal pipeline can't be blamed on data gaps — isolates pipeline
  bugs from data-quality issues on the very first run.
- **`case_pack` stays one global assumption (12)**, not varied per SKU.
  Why: Favorita has no real case-pack field at all, so a per-SKU value
  would not be more accurate — only harder to defend, since it turns one
  clearly-labelled assumption into several assumptions that look more
  precise than they are.
- **L1/L2 explanation-harness test-case selection is stratified by
  `rel_width`, with the split rule written into `backtest.py` before any
  backtest results exist.** Why: picking 10 cases after seeing results
  (even "fairly") is unfalsifiable to a reviewer; a rule fixed in code
  beforehand, with a fixed random seed, proves the selection wasn't tuned
  to look good after the fact. Rejected: pure random sampling (could by
  chance miss the abstain case entirely, so the harness never actually
  tests the abstain string) and post-hoc "fair" manual picking (no reviewer
  can distinguish that from cherry-picking).
- **Streamlit UI deferred until the prediction→gate→arithmetic→explain
  pipeline works end-to-end.** Why: the §8 minimal-version pass/fail
  criteria are all CLI-level (a printed sentence, an assertion on units,
  a numeral-containment check) — none require a rendered page. A terminal
  output plus narration is enough for the video demo; building UI before
  the core logic is proven would be effort spent on the wrong risk.
- **When the gate abstains, the UI shows one reference anchor alongside
  "ASK ME": last same-weekday actual sales.** This is a historical fact,
  not a model output, so it doesn't violate the "never show a confidence
  number" persona constraint — it answers "where do I even start" without
  smuggling a confidence signal back in. This adds a "last same-weekday
  actual" field to the `explain.py` fact block, computed regardless of
  whether the gate fires.

**Environment note:** the installed `kaggle` CLI (2.2.4) uses a newer auth
scheme than the handoff assumed — a plaintext token at `~/.kaggle/access_token`
rather than the legacy `~/.kaggle/kaggle.json` (username+key). Both files were
written; the legacy one is harmless but unused by this CLI version.

---

## 2026-09-23 — Two eval-methodology fixes from instructor feedback on Milestone 1

**What:** Course instructor (Ajay Vikram Singh) sent formative feedback on the
submitted Problem Statement. Two of the points identified a real gap in the
eval design that we hadn't caught in our own grill — adopted both before
writing `backtest.py`, since fixing them after the fact would mean rerunning
everything anyway.

**Decisions made:**
- **Switch from a single 31-day holdout to 3-fold rolling-origin backtesting**
  (e.g. test windows 2017-06-16→07-15, 2017-07-16→08-15, and one earlier
  window such as 2017-05-16→06-15, each preceded by its own training
  cutoff). Why: a single 31-day window can
  be dominated by one coincidental event (a holiday weekend) inside it, so a
  good or bad result proves nothing about the method — it might just prove
  something about that specific month. Three folds reported separately (not
  averaged into one number) show whether the result is stable across time or
  whether one fold is an outlier worth investigating on its own. Cost: near
  zero — same code, run three times over three windows.
- **Naive_seasonal baseline must be measured on the exact same auto-answered
  SKU-days as the model, not on the full dataset.** Why: Case Match Rate is
  reported only on SKU-days where the gate didn't abstain (the "easy" days
  by construction — the model routed the hard days to a human). If the
  baseline's accuracy is measured on *all* days while the model's is measured
  only on the *easy* subset it chose to answer, the comparison is invalid —
  any improvement could be entirely selection bias (the model looks better
  because it only competed on cases it found easy), not a genuine skill
  difference. Fixing this means `backtest.py` must compute
  `naive_seasonal` accuracy conditional on the same abstain mask the model
  produced, every time CMR is reported.

**Numbers:** none yet — this changes `backtest.py`'s design, not anything
already run. Both fixes are folded into the Phase 2 (multi-SKU backtest)
implementation plan in `docs/PROJECT_OVERVIEW.md` §6.

---

## 2026-09-23 — Phase 1 (Section 8 minimal pipeline) implemented and run for real

**What:** Built the full predict → gate → order → explain pipeline
(`order.py`, `gate.py`, `containment.py`, `features.py`, `model.py`,
`explain.py`, `run_slice.py`) test-first, starting with the deterministic
seams (order arithmetic, gate threshold, numeral containment) since those
don't need a model or an API key to test. 40 unit tests, all passing.

**Numbers (real run, store 44 / item 502331, no synthetic data):**
- Predicting day 84 from days 1–83: P10=55.5, P50=81.3, P90=107.2,
  `rel_width`=0.636 → **abstained** (threshold 0.60). Actual next-day sales
  turned out to be 42 — well outside even the P10 estimate — so on this one
  sample, abstaining was the right call. (One sample proves nothing on its
  own; noted here because it's a concrete, real illustration of why the gate
  exists, not a claimed result.)
- Tried 6 other split points (train_rows 40/50/60/70/75/80): all gave
  `rel_width` between 0.20 and 0.56, all below threshold, all produced a
  normal case recommendation (6–13 cases depending on split) — confirms
  both the abstain and non-abstain branches work on real data, not just in
  unit tests with synthetic numbers.
- No `OPENROUTER_API_KEY` configured yet, so every run so far has exercised
  the deterministic template fallback in `explain.py`, not a real LLM call.
  That fallback path is fully verified; the actual gpt-4o-mini call is
  still unexercised end-to-end.

**Code review (medium effort) before commit caught 4 issues, all fixed:**
- `containment.py` only added `int`/`float` fact-block values to the
  allowed-numbers set, so a numeral embedded in a *string* field (like
  `sku_name`) was never allowed. Concretely confirmed: this SKU's name is
  literally "item 502331" (Favorita has no product names, only item
  numbers), so almost any real LLM sentence mentioning the SKU by name
  would have been wrongly flagged as inventing a number and silently
  replaced by the template — indistinguishable from the L1 check actually
  catching a hallucination. Fixed by also extracting numerals from string
  values into the allowed set.
- `run_slice.py`'s pass/fail check asserted `units % 12 == 0` with a
  hardcoded literal instead of reading `case_pack` from config — would have
  silently stopped validating anything the moment `case_pack` was changed
  from its current value. Fixed to check against the configured value.
- `model.py`'s `predict_quantiles` hardcoded dict keys `0.1`/`0.5`/`0.9`
  instead of deriving low/mid/high from whatever quantiles were actually
  fit — editing `config.yaml`'s `model.quantiles` would have raised a
  confusing `KeyError` far from the actual change. Fixed to sort the
  models dict's own keys.
- `load_sku_slice` re-read the full 31.7M-row parquet file from disk on
  every call (measured: 1.26s/call) instead of caching it — harmless for
  one SKU, but Phase 2's planned loop over 537 SKUs (times 3 rolling-origin
  folds) would have cost roughly 11 minutes of pure redundant I/O before
  any model fitting even started. Fixed with an `lru_cache` on the raw
  parquet load.

**Rejected nothing this round** — all 4 findings were clear-cut bugs with a
cheap, obvious fix, not judgment calls with a real alternative to weigh.

---

## 2026-09-23 — Real gpt-4o-mini call verified end-to-end (not just the fallback)

**What:** Configured `OPENROUTER_API_KEY` in a local `.env` (gitignored, never
committed) and ran `explain.py`'s real LLM path for the first time — every
run before this had silently used the deterministic template fallback
because no key was configured.

**Numbers (real API call, not the template):**
- item 502331, order case: LLM returned `"The recent average for item 502331
  is 99.9, with 13 recommended cases and a last same weekday sales of
  161.0."` — passed numeral containment (7 pass verified this specific
  string), confirming the fix to `containment.py` (string-embedded numerals
  allowed) actually works against a real, non-mocked model response, not
  just the unit test's hand-written example.

**Observation to revisit, not a bug:** the wording is grammatically correct
but doesn't match the target style from the Problem Statement's example
output ("ORDER 7 cases. Recent average 82, similar to last Tuesday's 79.") —
it reads more like a data summary than an instruction a manager scans in 2
seconds. This is a prompt-engineering quality issue, not a correctness
issue (L1 containment is the hard requirement and it passed) — worth
tightening the system prompt in `explain.py` before the L1/L2 explanation
harness (Section 7 eval check 4) is run, since a technically-correct but
badly-phrased sentence is exactly the kind of thing the L2 judge step
exists to catch.

**Fixed same day:** rewrote the system prompt to require the literal opening
"ORDER {cases} cases." followed by one short reason clause, with one
good/bad worked example inline (few-shot). Why a worked example instead of
just a stronger instruction: the first prompt already said "single, plain
sentence" and still produced a report-style sentence — telling the model
what "good" looks like concretely worked where describing it abstractly
didn't. Re-ran against the real API (not mocked): output changed from
`"The recent average for item 502331 is 99.9, with 13 recommended cases
and a last same weekday sales of 161.0."` to `"ORDER 13 cases. Recent
average 99.9, lower than last week's 161.0."` — matches the target style,
still passes containment, all 40 tests still green.

---

## 2026-09-24 — Phase 2 pilot backtest (30 SKUs, 3 folds): two real findings, one good, one an open problem

**What:** Ran the full `backtest.py` pipeline (fit once per SKU per fold on
data up to that fold's train cutoff, walk forward through the 31-day test
window) on a 30-SKU pilot from the 426 store-44 candidates with long enough
history for all 3 folds. 2,760 real SKU-day predictions, saved to
`data/backtest_results.parquet`.

**Finding 1 — the Section 7 sweep range (0.40/0.50/0.60/0.70) was wrong,
not the model:** Measured `rel_width` on real data has median 0.77, so even
the "boldest" planned threshold (0.70) still abstains on 60.4% of SKU-days —
nowhere near the 15% design target. Swept further out and found the
threshold that actually produces ~15% abstain rate is **~1.00**, not 0.60.
At that threshold: abstain rate 16.2%, Case Match Rate (on the auto-answered
subset, computed fairly per the 2026-09-23 instructor fix) = 58.3% vs
Naive_seasonal's 50.0% on the *same* subset — a **16.6% relative
improvement**, clearing the Problem Statement's ≥15% target. Coverage at
that threshold: 78.4% vs nominal 80%, reasonably close.

**Finding 2 — abstention precision does NOT beat random selection, at any
threshold tested. This trips the Problem Statement's own abandon
condition:**

| threshold | abstain rate | abstention precision | error_base_rate (random) | lift |
|---|---|---|---|---|
| 0.60 | 74.5% | 40.8% | 40.3% | 1.01x |
| 0.70 | 60.4% | 39.4% | 40.3% | 0.98x |
| 0.85 | 34.3% | 38.1% | 40.3% | 0.95x |
| 1.00 | 16.2% | 32.6% | 40.3% | 0.81x |
| 1.20 | 5.8% | 27.5% | 40.3% | 0.68x |

At the ~15%-abstain operating point (threshold 1.00), the gate's chosen
abstain set is *less* likely to contain a real case-rounding error than a
same-sized random sample would be. This gets worse, not better, as the
threshold rises (i.e. as the gate gets more "selective").

**Working hypothesis, not yet confirmed:** `rel_width` measures how volatile
a SKU-day's demand is (aleatoric uncertainty), which is not the same thing
as how close its P50 sits to a case-pack rounding boundary. A high-volatility
SKU-day can still land its P50 safely mid-bucket (right answer despite a
wide interval); a low-volatility SKU-day can still sit right on a case
boundary and round the wrong way (wrong answer despite a narrow interval).
If true, `rel_width` alone is the wrong signal for *this specific* gate
purpose, even though it's a perfectly fine signal for the calibration
check (which it passes).

**Not treating this as project failure — treating it as the honest result
the Section 7 abandon condition exists to surface.** Two things left
unresolved, to check before drawing a final conclusion: (1) is this a real
pattern or a 30-SKU pilot artifact — scaling to the full 426-SKU candidate
set is the immediate next step; (2) if it holds at scale, worth testing
whether a boundary-distance signal (how close P50 sits to the nearest
case-pack multiple) predicts case-rounding errors better than `rel_width`
does — a genuinely different idea from "widen or narrow the same
threshold," not yet implemented.

---

## 2026-09-24 — Full 426-SKU backtest: the 30-SKU pilot's good news does not replicate at scale

**What:** Ran the same `backtest.py` pipeline across all 426 store-44
candidates (not just the 30-SKU pilot), 3 folds each — 39,192 real
SKU-day predictions, ~13x the pilot's sample size. This was the planned
"check whether Finding 1/2 hold at scale" step from the 2026-09-24 pilot
entry above. They mostly don't, and the investigation into *why* surfaced
a real, previously-unconsidered gap in the SKU selection criteria.

**Numbers (real run, not estimated):**

| metric | 30-SKU pilot (threshold 0.60) | 426-SKU full (threshold 0.60) | 426-SKU full (threshold 1.00) |
|---|---|---|---|
| abstain rate | 74.5% | **94.0%** | 73.4% (not ~15% — the pilot's threshold-1.00 finding does not transfer) |
| model CMR (answered subset) | 61.3% | **25.8%** | 47.4% |
| naive CMR (same subset) | 55.2% | **69.1%** | 53.0% |
| abstention precision vs random | 1.01x | 0.94x | 0.87x |

At full scale, **Naive_seasonal beats the model on the fair (same-subset)
comparison at every threshold tested** — the reverse of the pilot's
headline finding. Abstention precision confirms the pilot's Finding 2
(worse than random), now on a sample large enough (39,192 vs 2,760) that
it's not plausibly noise.

**Root cause, verified by splitting the answered rows by order size:**

| hindsight bucket | share of answered rows | model CMR | naive CMR |
|---|---|---|---|
| 0–2 cases (small orders) | 68% | 51.4% | **63.1%** — naive wins by 12pp |
| 3+ cases (larger orders) | 32% | **38.7%** — model wins by 7pp | 31.4% |

Two-thirds of all SKU-days in the real candidate pool are small orders
(1 case is the single most common `hindsight_demand_order` value, ~51% of
all 39,192 rows). In that regime, `recommended_cases` ceilings *any*
positive P50 up to at least 1 case (correct arithmetic — Problem Statement
§4 specifies always-round-up, never down, since under-ordering is the
costlier failure) — but a continuous GBR prediction almost never lands on
exactly 0, while Naive_seasonal copies a real integer from last week that
*can* be exactly 0. On days where actual demand truly is 0 (common for
these lower-volume SKUs, especially after zero-filling Favorita's omitted
days), Naive_seasonal gets it right essentially for free; the model
structurally can't.

**Why the pilot looked good and this doesn't:** the pilot's 30 SKUs were
selected by density alone (data completeness), and just happened to skew
toward the minority "larger order" regime where the model has a real edge
(mean daily sales 26.6 vs the full pool's 18.3, and the single-SKU Phase 1
demo item, 502331, averages ~86/day — nowhere near typical). Density says
nothing about order-size regime; a small, non-representative pilot masked
a real, majority-case weakness that only appeared once volume-diverse SKUs
were included at scale.

**Conclusion — not a coding bug, not project failure, a real scope gap in
the SKU selection criteria:** density (§3.2's filter chain: perishable →
integer-sold → density) never checked whether a SKU's typical order size
is even large enough for case-level rounding to be a meaningful decision
in the first place. For SKUs that almost always round to 0 or 1 case, the
whole "quantile regression + case rounding" apparatus is arguably the
wrong tool — a much simpler rule might do as well or better, which is
itself worth stating plainly rather than hidden.

**Open decision for the next step (not yet made — ask Harry):** (a) add an
order-size filter to the SKU selection (e.g. require median actual units
meaningfully above one case_pack) and re-run only on that higher-volume
subset, closer to what the Problem Statement's "Tomato slices / Lettuce"
persona examples implied; or (b) keep the full, unfiltered candidate pool
and report the split honestly — "this approach helps on higher-volume
SKUs, actively hurts on low-volume ones" — which is itself a defensible,
mature finding for the final report, arguably more interesting than a
single clean headline number.

---

## 2026-09-24 — CORRECTION to the entry above: the root cause was misdiagnosed

**The "small orders (0–2 cases)" explanation above is wrong.** Re-audit
split the answered rows by forecast size instead of by hindsight bucket
(real run, same `backtest_results.parquet`):

| threshold | rows with P50 < 1 unit | rows with P50 ≥ 1 unit |
|---|---|---|
| 0.60 | 54% of answered: model right 15%, **naive right 100%**, actual = 0 in 100% | model **39%** vs naive 32% |
| 1.00 | 13% of answered: model right 13%, **naive right 100%**, actual = 0 in 100% | model **53%** vs naive 46% |

On every SKU-day with a real (≥1 unit) forecast, the model beats
Naive_seasonal by ~7pp on the same subset, at both thresholds. The entire
"naive wins" reversal comes from near-zero forecasts on days where actual
sales were exactly 0. Two mechanisms compound:

1. **Rounding:** `ceil(0.001 / 12) = 1` — a forecast of a thousandth of a
   unit becomes a full case. Naive copies last week's real integer (0) and
   is right for free.
2. **Gate floor:** `rel_width = (P90−P10) / max(P50, 1)` — when P50 < 1 the
   denominator is pinned to 1, so near-zero forecasts with near-zero
   absolute width read as maximally confident and are *always answered*.
   The gate systematically routes exactly the rows the rounding rule gets
   wrong into the answered set.

The earlier split by hindsight 0–2 vs 3+ lumped "actual = 0" in with
"actual = 1–2 cases", which hid this. The proposed volume filter was aimed
at the wrong cause and is dropped (see pre-registration below).

---

## 2026-09-24 — PRE-REGISTRATION of the fix, committed before any code changes

Written and committed *before* touching code or re-running, so the git
history shows the criteria weren't chosen after seeing the new numbers.
This fix was discovered post-hoc (after seeing bad results), which is
exactly why it's pinned down here first.

**The fix (and nothing else):**
1. `recommended_cases` rounds the demand forecast to the nearest whole unit
   (half-up) before the case ceiling. Justification is definitional, not
   result-driven: §3.2's filter chain already restricted the SKU pool to
   items sold only in whole units, so a forecast of 0.4 units *means* 0
   units in this domain; ceiling a fractional forecast was inconsistent
   with our own data definition.
2. Quantile predictions are clipped at 0 (1.3% of P10s were negative;
   demand cannot be).

**Explicitly NOT changed:** the gate formula (including the `max(P50, 1)`
floor), the SKU pool (all 426, no volume filter), the model, its
hyperparameters, the folds, `case_pack`, `hindsight_demand_order`,
`naive_seasonal_order`.

**What will be reported after the re-run, whatever it shows:**
- Before-fix numbers (preserved in `data/backtest_results_prefix.parquet`)
  side by side with after-fix numbers — the before-fix run stays in the
  record, not replaced.
- Per-fold table at the configured threshold (0.60).
- Sweep at thresholds 0.60 / 0.70 / 0.85 / 1.00 / 1.20: abstain rate,
  model CMR and naive CMR on the same answered subset, coverage,
  abstention precision, error_base_rate, lift.
- The same P50 < 1 vs ≥ 1 split as above, and a hindsight split of
  0 / 1–2 / 3+ cases.

**Decision rule for the volume-filter idea (from the 2026-09-24 grill):**
only added as a clearly labelled post-hoc analysis if, after the fix,
naive still beats the model in a hindsight bucket other than 0. Otherwise
it's not done.

**No further tuning after this re-run.** If abstention precision is still
below random after the fix, that stands as the reported result for the
final submission.

---

## 2026-09-24 — Post-fix full re-run: results, reported exactly as pre-registered

**What:** Re-ran all 426 SKUs × 3 folds (39,192 SKU-day predictions) with
the pre-registered fix only (code commit `4912d93`, pre-registration
commit `2a1d668`, both pushed before the re-run finished). Tables below
come from `report_backtest.py`; before-fix numbers are the ones already
logged above (raw file kept as `data/backtest_results_prefix.parquet`).

**Per fold at the configured threshold (0.60):**

| fold | N | answered | abstain | model CMR | naive CMR | coverage |
|---|---|---|---|---|---|---|
| May–Jun | 13,206 | 667 | 94.9% | 66.9% | 63.3% | 77.1% |
| Jun–Jul | 12,780 | 809 | 93.7% | 70.8% | 69.0% | 76.7% |
| Jul–Aug | 13,206 | 857 | 93.5% | 77.5% | 73.7% | 79.0% |

Model ahead of naive in all three folds, so the direction isn't one
window's coincidence (the reason for rolling-origin in the first place).

**Sweep, before vs after the fix (all folds pooled):**

| threshold | abstain | model CMR before → after | naive CMR (unchanged) | relative improvement after | abstention precision | random base | lift before → after |
|---|---|---|---|---|---|---|---|
| 0.60 | 94.0% | 25.8% → **72.1%** | 69.1% | +4.3% | 32.9% | 32.6% | 0.94x → 1.01x |
| 0.70 | 90.9% | — → 64.6% | 59.4% | +8.8% | 32.4% | 32.6% | — → 0.99x |
| 0.85 | 83.0% | — → 60.3% | 54.5% | +10.6% | 31.2% | 32.6% | — → 0.96x |
| 1.00 | 73.3% | 47.4% → **59.3%** | 53.0% | +11.9% | 29.7% | 32.6% | 0.87x → 0.91x |
| 1.20 | 58.5% | — → 61.4% | 55.1% | +11.4% | 28.4% | 32.6% | — → 0.87x |

Coverage (P10–P90 contains actual) is 77.6% at every threshold (it's a
property of the interval, not the gate), vs 80% nominal. Naive CMR is
identical before and after, as expected (naive wasn't touched) — a sanity
check that the fix changed only what it was meant to change.

**Splits (answered rows, model CMR vs naive CMR):**

| split | threshold 0.60 | threshold 1.00 |
|---|---|---|
| P50 < 1 | 99.7% vs 99.8% (n=1,271) | 99.7% vs 99.7% (n=1,397) |
| P50 ≥ 1 | 39.2% vs 32.4% (n=1,062) | 53.1% vs 45.8% (n=9,050) |
| hindsight 0 | 99.6% vs 99.8% | 96.3% vs 96.7% |
| hindsight 1–2 | 51.1% vs 41.1% | 62.7% vs 54.5% |
| hindsight 3+ | 36.1% vs 29.9% | 37.4% vs 31.4% |

**Reading, against the pre-registered criteria:**
1. **The fix did what it was meant to and nothing more.** Near-zero
   forecasts now tie with naive (~99.7% both) instead of losing 15% vs
   100%. The artifact is gone.
2. **The forecasting layer adds real but modest value.** Model beats naive
   on the fair same-subset comparison at every threshold, in every fold,
   and in every non-zero hindsight bucket. Pooled relative improvement is
   +4% to +12% — **below the Problem Statement's ≥15% target**, which was
   defined on the pooled auto-answered slice. (The P50 ≥ 1 subset alone
   shows +16% to +21%, but choosing that subset as the headline *because*
   it crosses 15% would be exactly the selective reporting the
   pre-registration exists to prevent. Reported as a split, not a
   headline.)
3. **The abstain gate does not work as designed.** Abstention precision is
   at or below random at every threshold (1.01x down to 0.87x) and falls
   as the gate gets more selective. The Section 7 abandon condition is
   met; per the pre-registration, this stands as the reported result.
   `rel_width` is a roughly calibrated measure of demand volatility, but
   not a useful predictor of which case-level decisions will be wrong.
4. **The ~15% abstain design point is not reached** anywhere in the
   pre-registered sweep (lowest is 58.5% at 1.20). Not extended further:
   the pre-registration said no further tuning, and the lift trend
   *declines* as the threshold rises, so finding the 15% threshold would
   not rescue the gate's usefulness — though that's an inference from the
   trend, not a measured result.
5. **Volume filter: not done.** Pre-registered rule: only if naive still
   beats the model in a hindsight bucket other than 0. It doesn't — the
   model wins both 1–2 and 3+ at both thresholds.

**What this means for the project's story:** the honest conclusion is
"a quantile forecaster beats last-week's-order by a modest, consistent
margin, and its intervals are roughly calibrated — but interval width,
the signal the whole abstention design rests on, does not identify which
orders will be wrong." That is a negative result on the project's core
hypothesis, arrived at by a method (fair comparison, rolling folds,
pre-registration, correcting our own misdiagnosis) that is itself the
strongest thing to show.

---

## 2026-09-24 — PRE-REGISTRATION: a new gate signal ("case-straddle"), tested on a fresh store

Committed before any code for this experiment exists and before any
case-straddle number has been computed on any store.

**Why a new signal, and why it isn't "more tuning":** the `rel_width` gate
failed (entry above) and stays reported as failed. This is a *different
hypothesis*, motivated by *why* it failed: `rel_width` measures
uncertainty in units of demand, but the manager's decision is in cases.
A wide interval whose P10/P50/P90 all round to the same case count is a
safe decision; a narrow one sitting on a case boundary is not.

**Hypothesis:** abstaining when the interval implies more than one case
count gives abstention precision above random.

**Signal, exactly:** abstain iff `recommended_cases(q, safety, on_hand,
case_pack)` is not the same for all three of q = P10, P50, P90. Same
`safety=0`, `on_hand=0`, `case_pack=12`. No threshold, so no sweep and no
knob to tune after seeing results.

**Data:**
- *Development:* store 44, reusing the stored post-fix predictions in
  `data/backtest_results.parquet` (read-only; no re-run, no overwrite).
- *Confirmation:* store 49, chosen by a rule stated before looking at any
  of its predictions — highest count of density ≥ 0.7 SKUs, excluding
  store 44 (store 49: 541). Same SKU rule as store 44: perishable,
  integer-sold, density ≥ 0.7, first sale on or before 2015-06-01 → 436
  SKUs. Same model, hyperparameters, 3 folds. Run once. Output to its own
  file (`data/backtest_results_store49.parquet`).
- *Limitation, stated up front:* 410 of store 49's 436 items also appear in
  store 44's list. Store 49 is unseen sales data, not unseen products — it
  tests "does this hold in another store", not "for other products".

**Reported for both stores, whatever it shows:** abstain rate; model CMR
and naive CMR on the same answered subset, and relative improvement;
abstention precision, error_base_rate, lift — pooled and per fold. For
store 49 also the `rel_width` gate at 0.60 and 1.00, as a replication
check of the original negative result.

**Success criterion (judged on store 49 only):** pooled lift > 1.0 AND
lift > 1.0 in at least 2 of the 3 folds. Store 44 numbers are development
and do not count toward success or failure.

**Not changed:** every existing module, script, config value and result
file. The new gate lives in a new module; the experiment in a new script.

**No second try.** If store 49 fails the criterion, that is the result;
the signal is not modified and re-run.

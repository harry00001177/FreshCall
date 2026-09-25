# FreshCall — Decision Log

Format: date / decision / why + what was rejected / real numbers (or "not
run yet"). This is raw material for resume bullets and interview stories —
log every substantive step, including failed attempts.

## Index

1. 2026-09-22 — Repo initialized, terminology locked, plan grilled
2. 2026-09-22 — Kaggle set up, real data explored, D3/D4/D7-adjacent decisions closed
3. 2026-09-23 — Two eval-methodology fixes from instructor feedback on Milestone 1
4. 2026-09-23 — Phase 1 (Section 8 minimal pipeline) implemented and run for real
5. 2026-09-23 — Real gpt-4o-mini call verified end-to-end (not just the fallback)
6. 2026-09-24 — Phase 2 pilot backtest (30 SKUs, 3 folds): two real findings, one good, one an open problem
7. 2026-09-24 — Full 426-SKU backtest: the 30-SKU pilot's good news does not replicate at scale
8. 2026-09-24 — CORRECTION to the entry above: the root cause was misdiagnosed
9. 2026-09-24 — PRE-REGISTRATION of the fix, committed before any code changes
10. 2026-09-24 — Post-fix full re-run: results, reported exactly as pre-registered
11. 2026-09-24 — PRE-REGISTRATION: a new gate signal ("case-straddle"), tested on a fresh store
12. 2026-09-24 — Case-straddle experiment results: passes the pre-registered test, but abstains far too often to use
13. 2026-09-24 — Error decomposition: the ceiling isn't the problem, the price is
14. 2026-09-24 — PRE-REGISTRATION: L1/L2 explanation harness (Section 7 eval check 4)
15. 2026-09-24 — Harness batch 1 generated; it exposed a candidate-selection flaw
16. 2026-09-24 — Harry's batch 1 labels; PRE-REGISTRATION of batch 2 and a sensitivity check
17. 2026-09-24 — Sensitivity check results (active SKUs only) and harness batch 2 generated
18. 2026-09-24 — L2 judge results, and a "true but misleading" sentence nobody flagged
19. 2026-09-25 — PRE-REGISTRATION: negative-control test of the L2 judge
20. 2026-09-25 — Negative-control results: the judge catches 5 of 6 flaws, misses overstatement, and its reasons aren't reliable
21. 2026-09-25 — PRE-REGISTRATION: restrict the generator's comparison words
22. 2026-09-25 — Comparison-word restriction: pre-registered criterion met (7/7)
23. 2026-09-25 — Problem Statement v3: method changes written in, plan left as the plan
24. 2026-09-25 — Wrap-up: reference anchor added, harness tables committed, docs refreshed
25. 2026-09-25 — Watch-outs audit: decisions, and PRE-REGISTRATION of three checks
26. 2026-09-25 — Monitor and look-ahead results; demo data added
27. 2026-09-25 — Leak test result: one missing shift(1) would have faked a "target met"
28. 2026-09-25 — Repo tidy: experiments/ folder, index, local cleanup

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

---

## 2026-09-24 — Case-straddle experiment results: passes the pre-registered test, but abstains far too often to use

**What:** Ran `run_case_gate_experiment.py` once, as pre-registered
(code commit `eaba9ff`, committed before the run). Store 49 backtest saved
to `data/backtest_results_store49.parquet`; store 44 results file read
only. No existing file or result changed.

**Case-straddle gate:**

| store | scope | abstain | model CMR | naive CMR | rel. impr. | abst. precision | random base | lift |
|---|---|---|---|---|---|---|---|---|
| 44 (dev) | pooled | 77.9% | 92.1% | 88.8% | +3.7% | 39.6% | 32.6% | **1.21x** |
| 44 (dev) | folds | 77.3–78.5% | | | +3.4 to +4.0% | | | 1.20 / 1.22 / 1.23 |
| **49 (confirm)** | pooled | 74.2% | 93.1% | 89.1% | +4.4% | 36.4% | 28.8% | **1.26x** |
| **49 (confirm)** | folds | 73.7–74.9% | | | +4.2 to +4.8% | | | 1.26 / 1.27 / 1.27 |

**Pre-registered verdict (store 49): SUCCESS** — pooled lift 1.26 > 1.0,
and 3 of 3 folds > 1.0. Consistent across both stores and all six folds.

**Replication of the original `rel_width` gate on store 49:** lift 1.01x
at 0.60 (≈ random) and 0.89x at 1.00 (worse than random) — the original
negative result replicates on unseen data. (Side note, reported for
completeness, not as a headline: on store 49 the model's CMR improvement
at `rel_width` 1.00 is +15.4% vs +11.9% on store 44, so whether the
forecaster clears the ≥15% target is store-dependent.)

**What "success" does and doesn't mean here:**
- *Does:* measuring uncertainty in case counts rather than demand units is
  a real signal. The abstained set is ~1.2–1.3x more likely to contain a
  wrong order than a random set of the same size, on a store the idea was
  never developed on.
- *Doesn't:* make it usable. It abstains on ~74–78% of SKU-days. Using the
  Problem Statement's own coupling formula, recall = abstain rate ×
  precision ÷ base rate ≈ 0.742 × 0.364 ÷ 0.288 ≈ 94% on store 49: it
  catches almost every error, but only by handing back three quarters of
  all decisions. The Problem Statement's attention model put break-even
  at ~29% abstain; this is far past it. The pre-registered criterion
  (lift > 1) was deliberately a low bar for "is there a signal at all",
  and it passed that bar — not the higher bar of "is it deployable".
- *Why so many abstentions (the risk flagged before running):* median
  daily sales in this SKU pool is ~12 units — about one case — so an 80%
  interval very often spans a case boundary. The result also depends
  entirely on the assumed `case_pack=12`, which Favorita doesn't contain.

**Status:** no follow-up run. A version with a tunable knob (e.g. abstain
only when P50 is within some distance of a boundary) could trade recall
for a lower abstain rate, but that is a new experiment with a threshold to
choose, would need its own pre-registration, and is noted as future work,
not done.

---

## 2026-09-24 — Error decomposition: the ceiling isn't the problem, the price is

**What:** Descriptive analysis (`run_error_decomposition.py`, new files
only, results files read-only) of the model's would-be errors — SKU-days
where the P50-implied order ≠ `hindsight_demand_order` — split into
*catchable* (P10–P90 spans a case boundary, so an interval-based gate can
flag it) vs *uncaught* (whole interval implies one case count, actual
landed outside it; no interval-based gate can flag it), and uncaught by
direction. Simplified from the handoff's three buckets: the "novel
feature vector" bucket needs the novelty check, which was never built;
observed holidays are used as a rough stand-in.

**Numbers (real run):**

| | store 44 | store 49 |
|---|---|---|
| would-be errors | 12,792 (32.6% of SKU-days) | 11,546 (28.8%) |
| catchable | 94.6% | 93.8% |
| uncaught, over-ordered (waste) | 3.1% | 3.0% |
| uncaught, under-ordered (stockout) | 2.2% | 3.2% |
| observed holidays in test windows | 2 days (2017-05-26, 2017-08-11) | same |
| share of SKU-days on holidays | 2.2% | 2.2% |
| share of uncaught errors on holidays | 5.1% | 2.6% |
| error rate: holiday vs other days | 37.1% vs 32.5% | 30.6% vs 28.7% |

Note: "catchable share" equals the case-straddle gate's recall by
construction (it abstains on exactly these rows), so this is not an
independent confirmation of the 94% recall figure — it's the same fact
viewed as a ceiling.

**Reading:**
- **Detection is not the bottleneck.** Only ~5–6% of errors are "confident
  and wrong" — the interval-based ceiling on abstention is high (~94%).
  So the `rel_width` gate failed by using the wrong unit, not because
  errors are fundamentally undetectable.
- **The price is the bottleneck.** Catching those errors requires flagging
  every boundary-straddling interval, and most of those do *not* end in an
  error (precision ~36–40%). At ~12 units/day median against a 12-unit
  case, most decisions sit near a boundary — hence the 74–78% abstain rate.
  The problem is attention cost, not detection.
- **Uncaught errors split roughly evenly** between over-ordering (waste)
  and under-ordering (stockout): no systematic bias.
- **Holidays: suggestive at most.** Store 44 shows uncaught errors ~2.3x
  over-represented on holidays; store 49 barely (1.2x). Two holiday days
  per store is far too thin to support a calendar-rule claim either way.

---

## 2026-09-24 — PRE-REGISTRATION: L1/L2 explanation harness (Section 7 eval check 4)

Committed before any harness code exists and before any explanation
sentence for these cases has been generated.

**Deviation from the 2026-09-22 plan, stated plainly:** that entry said
the case-selection rule would be written *before any backtest results
existed*. That didn't happen — backtests have run. What the rule must
protect against is picking cases after seeing how good the *sentences*
are, and no sentence has been generated yet, so fixing the rule now still
meets that purpose. The rule also lives in a new module rather than
`backtest.py`, to leave existing files untouched.

**Selection (fixed seed 42), from store 44's post-fix backtest results,
stratified by `rel_width` against the configured threshold 0.60:**
- confident: `rel_width` < 0.30 → 4 cases
- borderline, still answered: 0.30 ≤ `rel_width` ≤ 0.60 → 3 cases
- abstained: `rel_width` > 0.60 → 3 cases (template path, no LLM call)

**Fact block per case:** `sku_name` "item N", `abstain`, `recommend_cases`
(from P50, post-fix rounding), `recent_avg` (mean of the 7 days before the
date, rounded to 1dp), `last_same_weekday` (units 7 days earlier) — same
fields and rounding as `run_slice.py`.

**L1 (automated):** numeral containment on the LLM's *raw* output, before
any fallback — the shown sentence always passes by construction (the
system swaps a failing sentence for the template), so checking it would
measure nothing. Abstain cases: check the shown text has no digits.

**L2 human labels (Harry, all 10, before seeing any judge output):** two
yes/no questions per shown sentence —
1. *Faithful:* says nothing the fact block doesn't support (incl.
   direction words like "higher"/"lower").
2. *Usable:* opens with the order (or a clear hand-back), readable in ~5
   seconds, no talk of confidence/probability.

**L2 judge:** run only after Harry's labels are saved; same two questions;
model choice left to Harry (it spends API budget) — recommendation is a
different, stronger model than the generator, to avoid a model grading
its own writing. Reported: L1 pass rate on raw output; Harry's pass rates;
judge's pass rates; judge–human disagreement count per question.

**Data handling:** the 10-case sheet contains a few derived numbers from
Kaggle data per row, so it's written under `data/` (gitignored) until
Harry decides whether a 10-row derived sample may be committed.

---

## 2026-09-24 — Harness batch 1 generated; it exposed a candidate-selection flaw

**Harness batch 1 (real run, 7 real gpt-4o-mini calls):** L1 on raw LLM
output 7/7 pass; abstain texts 3/3 digit-free. But 6 of the 7 LLM cases
are the same trivial input — recent average 0, last week 0, order 0 cases
— so the LLM was really only tested on one non-trivial sentence (case 5:
"ORDER 4 cases. Recent average 36.9, close to last week's 39.0."). Cause:
at threshold 0.60 most answered SKU-days are near-zero forecasts (see the
2026-09-24 correction), and those have tiny `rel_width`, so the
"confident" and "borderline" strata are dominated by them. Reported as
is; not re-sampled. Harry's L2 labels still pending.

**Flaw found while inspecting batch 1:** case 3 is item 958015, which sold
on exactly one day in its whole history. The candidate filter computes
density over each SKU's *own* active span and requires the first sale to
be early enough, but never requires the SKU to still be selling during
the test windows. SKUs discontinued before the test period then get
zero-filled through it — a run of trivially predictable zero days.

| | store 44 | store 49 |
|---|---|---|
| candidates whose last sale was before 2017-05-16 | 21 of 426 | 21 of 436 |
| their last-sale dates (min / median / max) | 2013-08-14 / 2017-04-02 / 2017-05-13 | 2014-07-25 / 2017-04-02 / 2017-05-15 |
| share of backtest SKU-days from them | 4.9% | 4.8% |
| actual = 0 within them / overall | 100% / 10.2% | 100% / 10.3% |

**Why it matters:** these rows are free points for both model and naive,
so the model-vs-naive *difference* is barely affected — but they inflate
the random base rate's denominator with non-errors that any gate answering
zeros "gets right", which can inflate a gate's lift. Pre-registered
results stand as reported; whether a sensitivity check excluding these
SKUs should be added is an open decision for Harry.

---

## 2026-09-24 — Harry's batch 1 labels; PRE-REGISTRATION of batch 2 and a sensitivity check

**Batch 1 L2 human labels (Harry, blind — no judge output exists yet):**
faithful 10/10, usable 10/10. Qualitative note on all 7 LLM sentences: "a
bit long; only restates the facts, no reason given." That is a real design
tension, not a bug: the Problem Statement's target output ("…steady")
includes a little interpretation, but every word of interpretation is a
chance to say something the fact block doesn't support. Prompt not changed
mid-evaluation; noted for the final report.

**Gap found while labelling:** the 2026-09-22 decision to show a reference
anchor (last same-weekday actual) next to "ASK ME" is not implemented. The
number sits in the fact block but nothing surfaces it — it was meant for
the UI, which was deferred. Open for Harry.

**Pre-registered, before any code or number for either:**

*Harness batch 2 (Harry approved; supplementary):* added *because* batch 1
tested the LLM on 6 identical all-zero inputs — labelled as supplementary
in any report, batch 1 reported unchanged. Same store-44 results, same
`rel_width` strata, same seed 42, restricted to SKU-days with P50 ≥ 1
(an input-side filter on the model's own forecast, not on actual sales),
excluding batch 1's rows: 4 confident + 3 borderline, no abstain stratum
(the abstain path doesn't call the LLM). Same fact block, same L1 on raw
output, same two labels by Harry before any judge runs.

*Sensitivity check (Harry approved):* recompute from the stored
predictions — no refit — excluding SKUs whose last sale in that store
was before 2017-05-16 (the first test window's start): 21 SKUs per store.
Reported next to the original numbers, which stay the primary,
pre-registered results:
- case-straddle gate, both stores: pooled + per-fold abstain rate,
  abstention precision, error_base_rate, lift;
- `rel_width` gate at 0.60 and 1.00, both stores: same metrics;
- model vs naive CMR on the answered subset for each of the above.

No other exclusion is tried afterwards.

---

## 2026-09-24 — Sensitivity check results (active SKUs only) and harness batch 2 generated

**Sensitivity check** (`run_sensitivity_active_skus.py`, code commit
`e419d5e` before the run): 21 inactive SKUs excluded per store (1,932
SKU-days each). Original pre-registered numbers remain primary.

| | original | active SKUs only |
|---|---|---|
| **case-straddle lift**, store 44 (dev) | 1.21x | **1.19x** (folds 1.18 / 1.20 / 1.20) |
| **case-straddle lift**, store 49 (confirm) | 1.26x | **1.24x** (folds 1.24 / 1.24 / 1.24) |
| case-straddle abstain rate, 44 / 49 | 77.9% / 74.2% | 79.3% / 75.6% |
| `rel_width` lift at 0.60, 44 / 49 | 1.01x / 1.01x | 0.98x / 0.99x |
| `rel_width` lift at 1.00, 44 / 49 | 0.91x / 0.89x | 0.89x / 0.87x |
| forecaster rel. improvement at `rel_width` 1.00, 44 / 49 | +11.9% / +15.4% | +14.6% / +20.0% |

**Reading:**
- The case-straddle result survives: lift drops slightly (the dead-SKU
  rows were inflating it, as suspected) but stays above 1.0 in every fold
  of both stores. Before the run I'd estimated ~1.20x for store 49 from
  simple arithmetic; the real figure is 1.24x.
- The `rel_width` gate looks *worse* without the dead SKUs — its
  "≈ random" at 0.60 becomes slightly below random in both stores.
- The forecaster's improvement over naive *grows* once trivial zero days
  are removed, landing around the 15% target (14.6% store 44, 20.0% store
  49 at threshold 1.00) — so "below target" from the primary results is
  not robust either way; the honest statement is "around the target,
  store-dependent". Per-fold figures at threshold 0.60 swing widely (e.g.
  store 49: +28.1% / +9.2% / +0.0%) because only ~2–3% of SKU-days are
  answered there — small samples, not a finding.

**Harness batch 2** (7 real gpt-4o-mini calls): L1 on raw output 7/7 pass,
all seven non-trivial (order 1–4 cases, real averages). Harry's labels
pending — sentences deliberately not commented on here to keep his
labelling blind.

---

## 2026-09-24 — L2 judge results, and a "true but misleading" sentence nobody flagged

**Harry's batch 2 labels (blind):** faithful 7/7, usable 7/7.

**L2 judge** (`anthropic/claude-haiku-4.5` via OpenRouter, Harry's choice —
different vendor from the gpt-4o-mini generator; code commit `1008d65`
before the run; listed price $1 / $5 per million input / output tokens):
over all 17 sentences, faithful 17/17, usable 17/17, 0 unparseable, **0
disagreements with Harry** on either question. L1 on raw LLM output over
both batches: 14/14.

**What 0 disagreements does and doesn't show:** every sentence was
labelled "yes" by both, so the judge raised no false alarms here — but
with no bad sentence in the set, this says nothing about whether it
*would catch* one. Its detection ability is unmeasured.

**Finding — case 16, a faithful sentence that points the wrong way:**
"ORDER 1 case. Recent average 61.6, significantly higher than last week's
21.0." Every number is correct and every comparison is true, so it
rightly passes L1, Harry and the judge. But the stated reason argues for
ordering *more*, while the order is small. Underlying data (item 1149069,
store 44, 2017-06-20): a weekend spike (95 / 169 / 90 units Fri–Sun)
pulled the 7-day average to 61.6; Monday sold 8; the model forecast
P50 = 12 → 1 case; actual was 2 → 1 case. **The model was right** (naive,
2 cases, was wrong) — but a manager reading that sentence would likely
override upward and over-order: the exact waste the product exists to
prevent. This is the "true-but-irrelevant explanation" silent failure
flagged in the Problem Statement's risks section, now observed for real.

**Why no check caught it:** L1 checks numbers, and both L2 questions ask
whether the sentence is *supported* and *readable* — none asks whether the
stated reason *supports the order*. And the cause isn't the LLM: it
faithfully paraphrased a fact block whose "recent average" is distorted by
weekly seasonality. The fact-block design decides whether an explanation
helps.

**Not changed now** (mid-evaluation). Candidate follow-ups for Harry: a
third rubric question ("does the stated reason point the same way as the
order?"); a negative-control test for the judge (deliberately flawed
sentences, including one like case 16) to measure whether it catches bad
sentences at all; a fact block without the seasonally-distorted 7-day
mean.

---

## 2026-09-25 — PRE-REGISTRATION: negative-control test of the L2 judge

Harry chose follow-up 1. Committed before any code exists and before the
judge sees any of these sentences.

**Purpose:** the judge agreed with Harry 17/17, but on an all-"yes" set, so
its ability to *catch* a bad sentence is unmeasured. Hand-written flawed
sentences, each built on a real harness fact block with one deliberate
flaw aimed at one rubric question, so the right answer is fixed by
construction. Two clean sentences as controls for false alarms.

| id | fact block from | flaw | sentence | should be "no" on |
|---|---|---|---|---|
| NC1 | case 5 | invented number | ORDER 4 cases. Recent average 36.9, close to last week's 39.0, so expect about 45 units tomorrow. | faithful |
| NC2 | case 13 | wrong direction | ORDER 1 case. Recent average 11.4, lower than last week's 7.0. | faithful |
| NC3 | case 12 | confidence talk | ORDER 4 cases, though I am not very confident about this one. Recent average 25.4, lower than last week's 51.0. | usable |
| NC4 | case 15 | order buried, too long | Looking at recent sales, this item has averaged 19.0 units over the past week, which is lower than the 34.0 units sold on the same day last week, so after weighing both figures the suggested order for tomorrow is 3 cases. | usable |
| NC5 | case 9 (abstain) | hand-back that still gives a quantity | ASK ME - this one is harder to call than usual, but 1 case should probably be enough. | faithful |
| NC6 | case 5 | overstated comparison (36.9 vs 39.0) | ORDER 4 cases. Recent average 36.9, significantly lower than last week's 39.0. | faithful |
| PC1 | case 14 | none (control) | ORDER 1 case. Recent average 10.0, higher than last week's 6.0. | neither |
| PC2 | case 11 | none (control) | ORDER 1 case. Recent average 3.4, lower than last week's 9.0. | neither |

**Scoring:** a flawed sentence is *caught* if the judge answers "no" on its
target question (an extra "no" on the other question is reported, not
penalised). A control is a *false alarm* if the judge answers "no" on
either question. L1 (numeral containment) is also run on every sentence,
to show which flaws the cheap automated check already catches — expected
by construction: only NC1 (45) and NC5 (1) fail L1; NC2, NC3, NC4, NC6
contain only fact-block numbers, so only the judge can catch them.

**Reported:** per sentence — L1 result, judge verdicts and reason; totals —
flaws caught by L1, by the judge, by either; false alarms. No pass/fail
threshold: with 6 items this is a probe, and any miss is logged as a
known blind spot. Same judge model and prompt as the 17-sentence run
(commit `1008d65`), temperature 0, run once. The case-16 kind of flaw
(reason points the opposite way to the order) is deliberately not in
this set: the current rubric doesn't ask about it, so a "yes" there
wouldn't be a judge error — that's follow-up 2.

---

## 2026-09-25 — Negative-control results: the judge catches 5 of 6 flaws, misses overstatement, and its reasons aren't reliable

Ran `run_judge_negative_control.py` once (code commit `a9939b4` before the
run; 8 real judge calls). Output in `data/l1l2/negative_control.csv`.

| id | flaw | L1 | judge faithful / usable | outcome |
|---|---|---|---|---|
| NC1 | invented number | FAIL | no / no | caught |
| NC2 | wrong direction | pass | no / no | caught |
| NC3 | confidence talk | pass | no / no | caught |
| NC4 | order buried, too long | pass | yes / no | caught |
| NC5 | hand-back that gives a quantity | FAIL | no / no | caught |
| NC6 | overstated ("significantly", 36.9 vs 39.0) | pass | yes / yes | **MISSED** |
| PC1, PC2 | clean controls | pass | yes / yes | ok (0 false alarms) |

**Totals:** L1 alone 2/6 (exactly the two predicted by construction);
judge 5/6; either 5/6; false alarms 0/2.

**Reading (6 items — a probe, not a rate estimate):**
- **The layers do different jobs.** L1 reliably catches invented numbers
  and nothing else; 3 of the 5 judge catches (wrong direction, confidence
  talk, buried order) are flaws L1 cannot see. Neither layer alone would
  have caught what both together did.
- **Blind spot: overstated magnitude.** NC6 says "significantly lower"
  for 36.9 vs 39.0 and passed the judge, even though the judge prompt
  names "significantly" as a word to check. This matters beyond the probe:
  the real generator used "significantly" in 4 of the 7 batch-2 sentences
  (cases 12, 15, 16, 17). Those gaps were large, but nothing in the
  pipeline would stop it using the word on a small one.
- **Right verdicts, unreliable reasons.** NC3's reason includes a false
  objection ("'last week's 51.0' … different time period" — it isn't).
  NC5's reason calls "harder to call than usual" confidence talk, yet
  that phrase is the standard abstain template, which the judge passed as
  usable 3/3 in the 17-sentence run. And once it finds one flaw it tends
  to answer "no" on both questions (NC1, NC2, NC5), so its per-question
  verdicts aren't independent. Use it as a screen, not an authority — as
  the Problem Statement said, "the judge is a component, not ground
  truth."

**Candidate follow-ups (not done):** fix the blind spot at the source by
telling the generator to use only "higher / lower / about the same", no
intensity words — cheaper and more reliable than hoping the judge
notices; the third rubric question from the case-16 finding.

---

## 2026-09-25 — PRE-REGISTRATION: restrict the generator's comparison words

Harry chose to fix the overstatement blind spot at the source. Committed
before the prompt is edited and before any new sentence is generated.

**The change (and nothing else):** the system prompt in `explain.py` tells
the generator to compare `recent_avg` with `last_same_weekday` using
exactly one of "higher than", "lower than", "about the same as" — the
last only when the two are within 10% of each other — and never to add
intensity words ("significantly", "sharply", "slightly", "much", …). The
in-prompt good example changes from "similar to" to "about the same as"
so the example obeys the new rule. Model, temperature, token limit, fact
block, containment check, fallback: unchanged.

**Considered, not chosen:** computing the comparison word in Python and
putting it in the fact block, so the LLM never judges the numbers at all.
More in line with "the LLM never touches numbers", but a bigger change;
kept as a follow-up.

**Test:** regenerate the 7 batch-2 sentences (cases 11–17, same fact
blocks) once. Old sentences stay in `cases_batch2.csv`; new ones go to
`cases_batch2_v2.csv`. Checked deterministically, no judge and no
relabelling (the property under test is mechanically checkable):
1. L1 on raw output;
2. no intensity word from a fixed list (significantly, sharply, slightly,
   much, far, considerably, substantially, dramatically, notably,
   markedly, greatly, strongly, marginally, somewhat, a lot, a bit);
3. exactly one allowed comparison phrase, and it is correct: "higher" iff
   recent_avg > last_same_weekday, "lower" iff <, "about the same" only if
   within 10% (|a − b| / max(a, b) ≤ 0.10);
4. opens with "ORDER".

**Success:** all four hold for 7/7. **If not:** reported as is — the prompt
isn't iterated again on these same 7 cases (that would be tuning to the
test).

---

## 2026-09-25 — Comparison-word restriction: pre-registered criterion met (7/7)

Ran `run_comparison_word_check.py` once (prompt change + script committed
in `93e9fd2` before the run; 7 real gpt-4o-mini calls).

| | old prompt | new prompt |
|---|---|---|
| pass all four checks | 3/7 | **7/7** |
| sentences with intensity words | 4/7 (all "significantly") | **0/7** |
| L1 on raw output | 7/7 | 7/7 |
| comparison direction correct | 7/7 | 7/7 |

The only change in the sentences: "significantly" disappeared from cases
12, 15, 16, 17; cases 11 and 13 came out word-for-word the same; case 14
now writes "10.0 / 6.0" instead of "10 / 6". End-to-end check afterwards:
`run_slice.py` (item 502331, split 60) → "ORDER 13 cases. Recent average
99.9, lower than last week's 161.0." — all Section 8 checks pass.

**Limits, stated plainly:**
- "about the same as" was never exercised: all 7 cases differ by more
  than 10%, so whether the model applies that rule correctly is untested.
- 7 sentences, one run. This shows the instruction is followed on these
  inputs, not that it always will be. Nothing *enforces* it — a
  deterministic guard (fallback to the template if an intensity word
  appears, like the numeral-containment guard) would; not built.
- It does nothing for the case-16 problem: "ORDER 1 case. Recent average
  61.6, higher than last week's 21.0." is now calmer but still argues for
  ordering more. That needs a different fix (fact-block design or the
  third rubric question).

---

## 2026-09-25 — Problem Statement v3: method changes written in, plan left as the plan

**What:** `docs/Problem_Statement_FreshCall_v3.docx` (v2 kept untouched).
Principle agreed with Harry: the Problem Statement is the plan submitted
to Ajay in September, not a results report. Anything that was a *plan*
stays as written even where results later disagreed (0.60 opening
threshold, 15% abstain design target, ≥15% improvement target, abandon
condition) — the report discusses whether they held. Only places where
the *method actually used* changed were updated, each with its reason:

1. Metric renamed CPOA → Case Match Rate (CMR); "perfect-hindsight order"
   → "hindsight demand order", with one sentence on why.
2. Naive_seasonal scored on the same auto-answered SKU-days as the model
   (promised to Ajay).
3. Single 31-day holdout → three rolling-origin folds, reported separately
   (promised to Ajay).
4. Sweep: original 0.40–0.70 kept, with a note that it was extended to
   0.60–1.20 after the first run measured median rel_width ≈ 0.77.
5. Slice: store 44 / 426 SKUs via the actual filter chain, store 49 as
   confirmation store, and the discontinued-SKU gap stated.
6. Order arithmetic: P50 rounded to whole units before the case ceiling;
   negative quantiles clipped to 0.

Validated against v2 (structure unchanged); a word-level diff confirms
nothing else changed. Template header ("Milestone 1 / formative") left
as is.

---

## 2026-09-25 — Wrap-up: reference anchor added, harness tables committed, docs refreshed

- **Reference anchor on abstain (the 2026-09-22 decision, previously
  unimplemented):** the abstain message now ends with "Same day last week:
  N units." The abstain contract changes from "no digits at all" to "only
  the anchor, which must be in the fact block" — enforced by the same
  numeral-containment check as order sentences; no recommended quantity or
  confidence figure can appear. Tests, `run_slice.py`'s pass/fail check and
  the harness's abstain check updated to match. Harness results logged
  above used the old, number-free template (cases 8–10). 77/77 tests;
  `run_slice.py` abstain path → "… Please set it manually. Same day last
  week: 90 units."
- **Harness tables committed** (Harry's decision — a few derived numbers
  from Kaggle data per row, 7–17 rows per table, no raw data) to
  `results/explanation_harness/`: `judged.csv` (all 17 sentences, Harry's
  and the judge's labels), `negative_control.csv`,
  `comparison_words_before_after.csv`.
- **README and PROJECT_OVERVIEW** updated with the sensitivity check,
  explanation-layer results and the case-16 finding.
- **Remaining:** ≤1200-word trade-off analysis and video, once the
  instructor publishes requirements (due 2026-10-04).

---

## 2026-09-25 — Watch-outs audit: decisions, and PRE-REGISTRATION of three checks

**Audit:** checked the project against the instructor's Watch-outs doc
line by line. Gaps found: no leakage before/after comparison; the Problem
Statement's §8 table is headed "Mitigation (built, not described)" but
only numeral containment + fallback and the abstain gate were built;
the repo can't run without the Kaggle data. Also found while hunting for
leakage: SKU selection computed density over each SKU's *full* history,
including the test windows — using only data up to 2017-05-15, store 44's
list would be 421 SKUs, not 426; **5 SKUs got in only because of
test-period sales** (a look-ahead in selection, found by us).

**Decisions (Harry, 2026-09-25):**
- Leak test: inject the realistic bug — a 7-day mean that includes the
  day being predicted (a forgotten `.shift(1)`) — not same-day sales.
- Look-ahead SKUs: sensitivity check excluding them; originals stay primary.
- Build two monitors (bias, coverage); list the rest honestly as not built.
  Problem Statement v3 not edited again (it's the plan).
- Ship synthetic demo data + its generator, not a real-data sample.
- Low-code: never tried. Report states why code was chosen directly
  (gate threshold and case arithmetic must be unit-testable and diffable
  in git; GUI-configured logic can't be asserted in pytest).

**Pre-registered, before any code for these exists:**

*1. Leak test.* Re-run the store-44 backtest (426 SKUs × 3 folds, same
model and folds) with one change: `rolling_7_mean` computed *without*
`shift(1)`, so it includes the day being predicted. Saved to its own file.
Report, next to the clean run: pooled model CMR vs naive CMR at 0.60 and
1.00, coverage, and case-straddle lift. Also report whether the existing
unit test `test_rolling_7_mean_excludes_todays_value` fails against the
leaky feature (i.e. whether our tests would have caught this bug).

*2. Look-ahead sensitivity.* For each store, drop the SKUs that are in the
current list but not in the list built from data up to 2017-05-15; recompute
from stored predictions (no refit). Report case-straddle lift, `rel_width`
lift at 0.60 / 1.00, and forecaster relative improvement.

*3. Monitors*, on each store's stored predictions, all folds:
- *Bias monitor:* per day, mean signed case error across SKUs
  (P50-implied cases − hindsight cases, whether or not the gate
  abstained); 7-day rolling mean.
- *Coverage monitor:* per day, share of SKUs whose actual falls inside
  [P10, P90]; 7-day rolling mean.
- *Thresholds from data, not chosen by eye:* fitted on fold 1 only
  (mean ± 3 standard deviations of the rolling values; coverage alerts on
  the lower side only), then applied to folds 2–3.
- *Positive control* (does a monitor fire when it should?): copy store 44's
  rows, multiply actual sales by 1.5 from 2017-08-01 onward (recomputing
  hindsight), run the bias monitor with the same fold-1 thresholds. It
  should alert within 7 days of 2017-08-01; report the first alert date.
- Report alert counts and dates. No alerts on the real data is a
  legitimate result (there's no known regime break in the test windows),
  which is exactly why the positive control exists.

No thresholds, windows or scaling factors are changed after seeing results.

---

## 2026-09-25 — Monitor and look-ahead results; demo data added

**Monitors** (`run_monitors.py`, code commit `4d6564d` before the run; no
refit, stored predictions). Bands fitted on fold 1, applied to folds 2–3:

| | store 44 | store 49 |
|---|---|---|
| bias band (mean signed case error / SKU-day, 7-day rolling) | [−0.113, +0.133] | [−0.167, +0.096] |
| folds 2–3 rolling range | [−0.096, +0.140] | [−0.120, +0.043] |
| bias alerts, folds 2–3 | **1 day: 2017-08-13** | none |
| coverage lower bound / folds 2–3 min | 0.733 / 0.738 | 0.710 / 0.749 |
| coverage alerts, folds 2–3 | none | none |

**Positive control** (store 44, actual sales ×1.5 from 2017-08-01, same
fold-1 bands): bias monitor fired on **2017-08-02, one day after the
shock**, with 0 alerts before it; coverage monitor also alerted on all 14
days after it. The monitors do fire when demand really shifts.

Reading: on the real data, the monitors stayed quiet except one store-44
day (2017-08-13, rolling bias +0.140 vs upper bound +0.133 — the model
over-ordering slightly). That 7-day window contains the 2017-08-11
national holiday, which is a plausible cause, but with a single day and a
single holiday this is not established. The quiet result is consistent
with there being no known regime break in the test windows, which is why
the positive control matters. Limits: store-level averages only (a bias
in a handful of SKUs could hide inside a store average); the ±3 std band
comes from one 31-day calibration fold.

**Look-ahead sensitivity** (`run_sensitivity_lookahead.py`, same commit):
5 look-ahead SKUs per store dropped (460 SKU-days each; item 1726956 is on
both lists).

| | original | without look-ahead SKUs |
|---|---|---|
| case-straddle lift, 44 / 49 | 1.21x / 1.26x | 1.22x / 1.27x |
| `rel_width` lift at 0.60, 44 / 49 | 1.01x / 1.01x | 1.01x / 1.01x |
| `rel_width` lift at 1.00, 44 / 49 | 0.91x / 0.89x | 0.91x / 0.89x |
| forecaster rel. improvement at 1.00, 44 / 49 | +11.9% / +15.4% | +11.9% / +15.6% |

The selection look-ahead is real but has no material effect on any
reported number.

**Demo data** (commit `ecf14c1`): `make_demo_data.py` writes a synthetic
90-day series (`demo/demo_sales.csv`, store 0 / item 0, fixed seed);
`run_slice.py --demo` runs end to end without the Kaggle data. Never used
for any reported result.

---

## 2026-09-25 — Leak test result: one missing shift(1) would have faked a "target met"

`run_leak_test.py` (code commit `29cd392` before the run): store 44, 426
SKUs × 3 folds, refit with `rolling_7_mean` including the day being
predicted. Output `data/backtest_results_leaky.parquet`.

| gate | run | abstain | model CMR | naive CMR | rel. improvement | coverage | lift |
|---|---|---|---|---|---|---|---|
| `rel_width` 0.60 | clean | 94.0% | 72.1% | 69.1% | +4.4% | 77.6% | 1.01x |
| | **leaky** | 91.6% | 70.9% | 63.8% | **+11.2%** | 78.3% | 1.00x |
| `rel_width` 1.00 | clean | 73.3% | 59.3% | 53.0% | +11.8% | 77.6% | 0.91x |
| | **leaky** | 65.9% | 65.7% | 54.4% | **+20.7%** | 78.3% | 0.91x |
| case-straddle | clean | 77.9% | 92.1% | 88.8% | +3.7% | 77.6% | 1.21x |
| | **leaky** | 73.7% | 93.5% | 88.2% | +6.0% | 78.3% | **1.28x** |

(Clean relative improvements are computed here from unrounded CMRs, so
+4.4% / +11.8% vs the +4.3% / +11.9% logged earlier from rounded ones.)

**Reading:**
- The leak inflates every headline in the direction I'd have wanted: the
  forecaster's improvement at threshold 1.00 nearly doubles, from +11.8%
  to +20.7% — **crossing the Problem Statement's ≥15% target** — the model
  looks more confident (abstain rate 73% → 66%), and the case-straddle
  gate's lift rises from 1.21x to 1.28x. A single forgotten `.shift(1)`
  would have turned "around the target" into a clean, false success.
- Coverage barely moves (77.6% → 78.3%): the calibration check would *not*
  have exposed this leak. What does: the existing unit test
  `test_rolling_7_mean_excludes_todays_value` fails against the leaky
  feature — confirmed programmatically in the same run.
- This is the "before-and-after" the Watch-outs ask for; the clean
  numbers remain the reported results.

---

## 2026-09-25 — Repo tidy: experiments/ folder, index, local cleanup

- The 11 evaluation scripts moved into `experiments/` with `git mv`
  (history kept); the core pipeline (`prepare_data.py`,
  `make_demo_data.py`, `run_slice.py`, `run_backtest.py`) stays at the
  root. No code changed. Entries above refer to scripts by their old root
  paths. Verified after the move: all 11 import; 83/83 tests; the
  read-only ones (`report_backtest`, case-gate experiment, decomposition,
  monitors) reproduce the logged numbers exactly.
- README: new layout and run commands; dataset link added.
- This log: an index of entries added at the top.
- Local only (gitignored, nothing tracked): deleted four intermediate data
  files from the early ad-hoc exploration that no code uses any more
  (`store44_qualifying_skus`, `store44_backtest_candidates`,
  `derived_density`, `fully_integer_items`), and my own temp download and
  unpack folders outside the repo. Raw Kaggle files, all backtest results
  (including the pre-fix run) and the harness sheets are kept.

---

## 2026-09-25 — UI decisions; system gate switched to case-straddle

**Correction first:** I had described the UI as optional ("the video doesn't
need a UI"). It isn't: the Problem Statement §5 lists "Interface: Own —
Streamlit, one page" and §8 lists an explicit confirmation tap as a
mitigation. The 2026-09-22 decision only *deferred* it until the pipeline
worked, which it now does.

**Decisions (Harry, grilled 2026-09-25):**
- **System gate = case-straddle** (`config.yaml` `gate.type`). It is the
  only gate that beat random on an unseen store under pre-registration;
  the `rel_width` 0.60 default was an untested opening value, now shown to
  be ≈ random. The UI gets a sidebar "evaluation view" that can switch to
  the original `rel_width` gate for the demo, clearly labelled.
  Implemented as `decide_abstain(p10, p50, p90, cfg)` (unknown gate type
  raises). The backtest and all experiments are deliberately unchanged, so
  every logged result still reproduces (checked: `report_backtest.py`
  identical). `run_slice.py` now uses the system gate.
- **Shown data:** store 44, test-period dates, 40 SKUs (the persona's
  nightly order size) drawn with a fixed seed from the candidates that were
  still selling at the start of the test period — not top-by-volume, which
  would favour large orders and flatter the screen.
- **Confirm / override:** every row has an editable case count; ASK ME rows
  require the manager's own number; one "place order" action writes a local
  log (date, SKU, system suggestion, manager's number, overridden?) —
  implements §8's confirmation mitigation; overrides show where the model
  isn't trusted. Log stays local (gitignored).
- **Sentences pre-generated** once per shown date into a cache (still
  through numeral containment + template fallback), not called live: fast,
  reproducible, cheap, and consistent with "the LLM only words things".
- **Polish level:** faithful and solid (cases only, no confidence figures,
  ASK ME with anchor, overrides, phone-width), tested logic, a README
  screenshot. No deployment for now; revisit after the report and video.

---

## 2026-09-25 — Manager UI built and tested in the browser

`app.py` (Streamlit, one page) + `build_ui_cache.py` + tested logic in
`src/freshcall/ui_logic.py`, per the UI decisions above.

**Cache (real run):** store 44, 40 SKUs (fixed seed 42, still-selling
only), 7 dates (every 14 days from 2017-05-16), 280 rows. 81 real
gpt-4o-mini calls for rows some gate would answer, 0 template fallbacks.
ASK ME share on these rows: case-straddle 71.1%, `rel_width` 0.60 98.6%.

**Tested by using it in the browser (not just unit tests):**
- Placing an order with ASK ME lines empty is refused and lists them.
- Filled all 28 ASK ME lines, changed one suggestion (1 → 9 cases), placed:
  "11 confirmed, 1 changed, 28 set by you"; the log file had exactly those
  40 rows and outcomes (and is gitignored).
- Evaluation view: switching to the original `rel_width` gate turns 16 May
  into 40 of 40 ASK ME; "show what actually sold" adds the backtest outcome
  and "matches / off by N" per suggestion.
- Changing the date reloads that day (13 June: 30 of 40 need a call) and
  resets the inputs.
- Phone width (375 px): single column, full-width inputs, evaluation
  sidebar collapsed.
- Found and fixed while testing: "1 units" in both the outcome note and the
  ASK ME anchor (now "1 unit"; ASK ME text is rendered from stored numbers
  by the deterministic template, so the cache can't hold stale wording);
  paths made relative to `app.py` so it runs from any directory; Streamlit's
  "Deploy" toolbar hidden (`.streamlit/config.toml`).

**Not done:** no README screenshot (the browser pane can't save one to a
file; Harry to capture one while recording the video). The UI needs the
Kaggle-derived cache, so it can't run from a clean clone without the data
— the synthetic `--demo` path covers only `run_slice.py`. No deployment.

---

## 2026-09-25 — Re-examining "real-world value": the gate, as designed, removes the value the model creates

Harry asked the question that matters most: does this have real value for
a manager? Measured it the way a manager experiences it — wrong orders and
minutes per night — on store 44 (development data; not yet confirmed on
another store). Descriptive, computed from stored predictions.

**Assumptions, stated:** timings are the Problem Statement §5 guesses,
never measured (today 30 s per SKU; a system answer 5 s to scan; a
handed-back SKU 90 s). A handed-back SKU is assumed to be ordered the way
managers do today — "same weekday last week" (the naive baseline) — the
only proxy for human judgement this data allows.

| policy (per 40-SKU night) | handed back | wrong orders | over (waste) | under (stockout) | minutes |
|---|---|---|---|---|---|
| today: manager orders last week's number | 100% | 15.5 | 7.9 | 7.6 | 20.0 |
| **system answers everything, no gate** | 0% | **13.1** | 7.0 | 6.1 | **3.3** |
| `rel_width` 0.60 gate | 94% | 15.4 | 7.9 | 7.5 | 56.6 |
| `rel_width` 1.00 gate | 73% | 14.8 | 7.7 | 7.1 | 44.9 |
| case-straddle gate | 78% | 15.2 | 7.9 | 7.3 | 47.5 |

**Why the gates lose:** even on the SKU-days case-straddle hands back (the
hard ones), the model is wrong less often than "last week" (39.6% vs
46.5%; on the answered ones 7.9% vs 11.2%). Handing a SKU to someone who
does worse than the model there adds errors and time.

**Reading:**
- Under this proxy the *forecaster alone* has real value: ~15% fewer wrong
  orders than today (13.1 vs 15.5 per night), fewer over-orders (7.0 vs
  7.9) and fewer stockouts (6.1 vs 7.6) — and far less time.
- Every gate we built gives most of that away: errors back near today's
  level, and more minutes than today.
- The evaluation so far asked "is the gate more likely to abstain where
  the *model* is wrong?" (abstention precision vs random). The question
  that decides real value is different: "is the *manager* likely to do
  better than the model on the SKUs handed back?" A person guessing with
  no extra information is not. A person who knows something the model
  can't see — a local event, a promotion, a delivery problem — might be.
  This data has no record of what managers know, so that part cannot be
  measured here; it is the central open question for any real deployment.
- Caveats: store 44 only; the manager proxy is pessimistic (a real manager
  thinking for 90 s may beat "last week"); minutes rest on unmeasured
  timings (the error comparison does not).

Redesign direction to be decided with Harry before any new code.

---

## 2026-09-25 — Redesign decisions, and PRE-REGISTRATION of the redesign test

**Decisions (Harry, grilled 2026-09-25):**
- **Q1 — the hand-back's job:** hand a SKU to the manager only where the
  *manager* can beat the model (information the model can't see), not
  merely where the model is uncertain — the real-value check showed a
  person without extra information does worse than the model even on the
  hard SKUs.
- **Q2 — product shape: "an order for every SKU, plus its likely range".**
  No more ASK ME. The manager changes a line when they know something.
  Manager-flagged events (promotions, local events) noted as the future
  direction; this data has no record of what managers know.
- **Q3 — headline measure:** wrong orders and minutes per 40-SKU night,
  compared with today's practice. Abstention precision becomes a diagnostic.
- **Q4 — validation:** develop on store 44; confirm once on a store never
  looked at.
- **Harry's point on trivial SKUs** (they always need 1 case; no model
  needed): checked on store 44 — 17.3% of SKU-days are *routine* (every day
  of the past 28 sold ≤ 1 case); today's practice is wrong on 11.4% of
  them, the model on 9.7%; **95% of the errors the model avoids come from
  the other 83%**, where today's practice is wrong 44.4% of the time vs the
  model's 37.4%. Also: a case can be "right" and still waste units (5.4
  units per routine order) — the case metric can't see that.
- **Q5 — routine SKUs:** shown as collapsed *standing orders* at the
  model's number (almost always 1 case; 0 for a SKU that has stopped
  selling — a small change from "always 1 case", to avoid ordering for
  nothing). Real stores would order these less often than daily, carrying
  stock; this data has no inventory, so daily ordering is assumed.
- **Q6 — metrics:** headline on non-routine SKU-days, routine reported
  separately; add units over-ordered (waste) and units short (stockout),
  not just case errors.
- **Q7 — range display:** every non-routine SKU shows "ORDER n cases ·
  likely lo–hi" (cases implied by P10 and P90), listed widest range first.
  A range is information, not an alarm.

**PRE-REGISTERED — committed before any redesign code exists and before
store 8 has been backtested:**

*Definitions (all known at order time):*
- routine: the SKU's maximum daily sales over the 28 days before the order
  date ≤ `case_pack` (12). Everything else is non-routine.
- order = `recommended_cases(P50)` (current rounding); range =
  [`recommended_cases(P10)`, `recommended_cases(P90)`].
- units over = max(0, order × 12 − actual); units short =
  max(0, actual − order × 12).

*Compared, per 40-SKU night, routine and non-routine separately and
together:* **today** (order = last week's same day, "naive") vs **redesign
with the manager accepting every suggestion** — a floor for the redesign,
since any real manager input is unmeasurable here. Reported: case errors,
units over, units short, and minutes under stated assumptions (today 30 s
per SKU; redesign 5 s per non-routine SKU, 1 s per routine SKU — never
measured). For the range: share of non-routine SKU-days whose needed cases
fall inside it; share with width 0 / 1 / 2+ cases; and the share of case
errors that sit in the widest-range quarter (does "widest first" point
the manager at the right lines?).

*Data:* development = store 44 (existing post-fix backtest). Confirmation
= **store 8** (Quito, type D), chosen by rule before any of its results
exist: the store with most density ≥ 0.7 SKUs, excluding 44 and 49 (539);
same SKU rule → 433 SKUs; same model, hyperparameters and 3 folds; run
once, its own output file.

*Success (store 8, non-routine SKU-days):* the redesign beats today on
**case errors** AND on **total unit error (over + short)**, pooled AND in
at least 2 of 3 folds. Store 44 numbers are development only.

*No second try:* store 8 is not re-run with any definition, rounding or
threshold changed. Whatever it shows is reported.

---

## 2026-09-25 — Redesign results: confirmed on store 8 (pre-registered SUCCESS)

`experiments/run_redesign.py` (commit `0c9176d`, before any store-8 result
existed; store-8 backtest saved without printing metrics, then evaluated
once). Per 40-SKU night; redesign = manager accepts every suggestion (a
floor); timings are assumptions.

**Non-routine SKU-days (the headline):**

| | store 44 today | store 44 redesign | **store 8 today** | **store 8 redesign** |
|---|---|---|---|---|
| wrong orders | 17.8 | 15.0 | 13.3 | **10.3** (−23%) |
| units over (waste) | 317.9 | 285.2 | 282.3 | **250.1** (−11%) |
| units short (stockout) | 83.4 | 59.5 | 41.7 | **31.0** (−26%) |
| minutes (assumed) | 20.0 | 3.3 | 20.0 | 3.3 |

Store 8, non-routine, per fold — beats today on both case errors and total
unit error in **3 of 3 folds** (wrong 13.2→10.9, 13.7→10.3, 12.9→9.7;
|unit error| 326→282, 327→275, 319→286). **Pre-registered criterion met.**

**Range:** the needed cases fall inside the shown range 94.1% (store 44) /
94.8% (store 8). Width 0 / 1 / 2+ cases: 15/44/41% (44), 28/49/23% (8).
The widest-range quarter holds 42.1% / 45.2% of the redesign's case errors
(vs 25% if width meant nothing) — "widest first" does point the manager at
the lines most likely to be wrong, about 1.7–1.8× more than chance.

**Routine SKU-days** (17.3% of store 44, 38.7% of store 8): fewer wrong
orders (store 8 6.1 → 4.4) and far fewer units short (9.4 → 1.3), **but
more units wasted** (243.5 → 281.0; store 44 182.8 → 214.1). The model
orders a case where "last week" would have ordered none, trading
stockouts for waste on low-volume SKUs. Reported, not hidden: on routine
SKUs the redesign is not better on waste.

**Overall (all SKUs), store 8:** wrong 10.5 → 8.0, units over 267.3 →
262.1, units short 29.2 → 19.5, minutes 20 → 2.3.

**Caveats:** absolute waste is inflated for *both* policies by the
no-inventory assumption (every day's order starts from zero stock, so a
case bought for 3 units wastes 9 every day) — compare the two policies,
don't read the absolute units as a real store's waste. Manager judgement
is not measured (floor only). Timings unmeasured. Stores 44 and 8 are both
in Quito.

**What this means:** the value the project set out to deliver — fewer bad
orders for less of the manager's time — holds up on an unseen store once
the product stops handing uncertain SKUs back and instead shows every
order with its likely range. The original abstention idea failed; the
redesign built from understanding *why* it failed passes.

---

## 2026-09-25 — Decisions after the redesign result; PRE-REGISTRATION of the explanation fix

**Decisions (Harry, grilled 2026-09-25):**
- **Routine SKUs:** a store-level business setting `routine_policy`
  (`model` | `last_week`), default `model`. On stores 44 / 8, `last_week`
  trades about 4.6–4.7 units less waste for each extra unit short (and
  more wrong cases), so it pays only if a unit short costs less than ~4.6
  units wasted — a cost only the store knows. Default `model` because a
  missing QSR ingredient often blocks several menu items and because this
  data overstates waste on exactly these SKUs (no carry-over stock). Both
  policies' numbers are already measured; no new experiment.
- **System default = the redesign** (every SKU gets an order + range; no
  ASK ME). `gate.type` gains `none`. The UI's evaluation view keeps a
  "design version" switch — redesign (system) / v2 case-straddle + ASK ME /
  v1 `rel_width` + ASK ME — labelled as history, for comparison.
- **Range wording:** "ORDER 3 cases · likely 2–4"; a one-value range shows
  just "ORDER 3 cases". The range is rendered by deterministic UI code,
  never written by the LLM.
- **Timing:** replace single assumed timings with a sensitivity table
  (redesign 5 / 10 / 15 s per non-routine SKU × today 20 / 30 / 45 s).

**PRE-REGISTERED — the explanation fix (case 16), before any code:**

*Change:* the fact block's "recent average" (last 7 days, distorted by
weekend spikes — the cause of case 16) is replaced by the **average of the
same weekday over the previous 4 weeks** (days −7, −14, −21, −28), plus the
weekday's name. The prompt compares that average with last week's same
day using the existing restricted words (higher / lower / about the same).
Old fact block, prompt and experiment scripts are kept untouched so every
earlier result still reproduces.

*New rubric question 3 (Harry and the judge):* "Does the reason point the
same way as the order?" — i.e. would a manager reading the reason be pushed
towards ordering more when the order is low, or less when it is high?

*Batch 3 (store 44 post-fix predictions, non-routine SKU-days only):*
(a) the 7 batch-2 SKU-days (cases 11–17, including case 16) — before/after
on the same inputs; (b) 7 SKU-days not used before, drawn with seed 43 from
non-routine SKU-days with P50 ≥ 1 — so the fix isn't judged only on the
case it was designed for.

*Reported:* L1 on raw output; Harry's labels on all 3 questions (given
before any judge output, and without my comments); judge (Claude Haiku
4.5) on the same 3 questions; judge–Harry disagreements; for (a), old vs
new sentence side by side.

*Success:* Harry answers "yes" to question 3 for case 16's new sentence,
L1 passes 14/14, and no sentence gets a "no" from Harry on questions 1–2.
If not, reported as is; the fact block isn't iterated on these cases.

---

## 2026-09-25 — Manager-time sensitivity table

`experiments/run_time_sensitivity.py`. Minutes per 40-SKU night, redesign
(routine SKUs 1 s) vs today, over a grid of unmeasured timings:

| redesign s / non-routine SKU | store 44 vs today 20 / 30 / 45 s | store 8 vs today 20 / 30 / 45 s |
|---|---|---|
| 5 | 2.9 vs 13 / 20 / 30 | 2.3 vs 13 / 20 / 30 |
| 10 | 5.6 vs 13 / 20 / 30 | 4.3 vs 13 / 20 / 30 |
| 15 | 8.4 vs 13 / 20 / 30 | 6.4 vs 13 / 20 / 30 |

"The redesign takes less of the manager's time" holds in all 9
combinations, including the least favourable (15 s per line vs 20 s
today). Still assumptions — no timing has been measured with a real
manager — but the conclusion doesn't hinge on any particular guess.
(It excludes time spent overriding lines, which depends on how often a
manager knows something the model doesn't — unmeasurable here.)

---

## 2026-09-25 — Explanation fix, batch 3 results: pre-registered SUCCESS; two new problems found

**Harry's labels (blind):** faithful / usable / direction — yes on all 14.
Note: "the order is in cases but the reason is in units, with no unit
named — could confuse the manager."

**Pre-registered criterion:** case 16's new sentence ("ORDER 1 case.
Tuesdays have averaged 11, lower than last Tuesday's 21.") gets "yes" on
direction from Harry; L1 14/14; no "no" from Harry on questions 1–2 —
**met.** Case 16 now points the same way as its order.

**Judge (Claude Haiku 4.5, 3 questions):** faithful 12/14, usable 14/14,
direction 11/14 → 5 disagreements with Harry. Checked each against the
data deterministically (comparison word vs the numbers; order vs the case
count last week's sales imply):
- Direction: every sentence whose order is *below* last week's case count
  says "lower" (cases 12, 16, 101, 105); the one *above* says "higher"
  (106); the rest are equal. The judge's three direction "no"s (12, 13,
  105) are wrong — its reasons treat a correct "lower" as contradicting a
  lower order. Harry was right.
- Faithful: the judge's "no" on 14 ("higher" called unsupported for 7.2 vs
  6.0) is wrong. Its "no" on 13 lands on a real problem but gives a false
  reason ("the sentence reverses this").
- Consistent with the negative-control finding: the judge's verdicts can
  be useful as a screen, its reasons can't be trusted.

**New problem 1 — the "about the same" rule is not reliably followed.**
The prompt says "about the same" when within 10%. Two of 14 break it:
case 13 (6.5 vs 7.0, 7% apart) says "lower"; case 17 (39.5 vs 37.0, 6%
apart) says "higher". Both true, both against the rule — the first time
the "about the same" branch was exercised (it was untested in the
comparison-word check). An LLM applying a numeric threshold is exactly
what "the LLM never touches numbers" was meant to avoid.

**New problem 2 (Harry) — mixed units.** "ORDER 1 case. Tuesdays have
averaged 11 …" — 11 what? The order is in cases, the reason in unlabelled
units; a manager could read 11 as cases. (Suggestively, the judge's wrong
direction calls come from the same mix — it compared a case count with
unit averages.) The Problem Statement's own target output already showed
both: "ORDER 3 cases (36 units)."

Next: decide how to fix both before the UI is rebuilt.

---

## 2026-09-25 — Decision: the order line becomes a deterministic template; PRE-REGISTRATION

**Decision (Harry):** the manager-facing sentence is written by a fixed
template, not the LLM. Why: for a fixed-format line, the measured record
is that the LLM added no information and every risk we found — invented
numbers (caught by containment), overstatement (fixed by restricting
words), and now breaking the 10% "about the same" rule in 2/14 — while
costing latency and money and needing a fallback. The one thing it did
(natural phrasing) a template does as well here. The LLM keeps a real job
where it earned one: the **judge** inside the evaluation. Old v1/v2 LLM
paths stay in the code, unchanged, so every earlier result reproduces.
This reverses part of the Problem Statement's architecture (§4: "rented
gpt-4o-mini for language"), based on evidence — to be stated as such.

**PRE-REGISTERED, before any code:**

*Template (v3):* `ORDER {n} case(s) ({n×12} units). {Weekday}s have averaged
{avg} units, {word} last {Weekday}'s {last}.` — `{word}` computed in Python:
"about the same as" if |avg − last| ≤ 10% of the larger, else "higher than"
/ "lower than"; both zero → "about the same as". Unit and case words
singular/plural as needed.

*Test:* regenerate the same 14 batch-3 SKU-days with the template. Checks:
(1) L1 containment 14/14; (2) comparison word correct under the 10% rule
14/14 (deterministic); (3) every number in the reason is followed by
"units" / "unit", and the order states both cases and units; (4) Harry
labels the 14 on the same 3 questions, blind; (5) the judge (Haiku, 3
questions) runs after, and its disagreements are reported.

*Success:* checks 1–3 all 14/14 AND Harry "yes" on all 3 questions for all
14. If not, reported as is.

---

## 2026-09-25 — Template sentence results: pre-registered SUCCESS; the judge is unreliable on "direction"

`experiments/run_explanation_v3.py` (commit `3fc1ca9` before generating).
Same 14 SKU-days as batch 3.

- **Deterministic checks:** L1 14/14; comparison word correct under the 10%
  rule 14/14 (cases 13 and 17 now say "about the same", which the LLM got
  wrong); units stated for the order and the average 14/14.
- **Harry (blind):** yes on faithful / usable / direction for all 14.
- **Pre-registered criterion: met.** Example — case 16: "ORDER 1 case (12
  units). Tuesdays have averaged 11 units, lower than last Tuesday's 21."
- **Judge (Haiku, 3 questions):** faithful 12/14, usable 14/14, direction
  **7/14** — more disagreement than on the LLM sentences (3). Its direction
  reasons share one misreading: it treats "lower than last week" as
  contradicting *any* non-zero order, never comparing the order with the
  case count last week implies (the deterministic check shows every
  direction is consistent), and once calls 36 units "exceeding" 38. Its
  two faithful "no"s are wording disagreements, not errors: it thinks 39.5
  vs 37 (6% apart) shouldn't be "about the same" (our 10% rule), and that
  "higher than last Tuesday's 0" lacks context — fair: a zero last week may
  have been a stockout, which the sentence can't know.
- **Judge overall, across batches 1–3 and the negative control:** screens
  invented numbers and blatant wording flaws; misses overstatement; its
  direction verdicts and its reasons are not reliable. Useful as a first
  screen only — human labels stay the reference.

**Adopted:** the v3 template is the system's order sentence (UI and
`run_slice.py`). The manager-facing path now makes no LLM call.

---

## 2026-09-25 — UI rebuilt for the redesign; very wide ranges found

**Built** (`app.py`, `build_ui_cache.py`, `ui_logic.range_text` /
`widest_first`, `run_slice.py`): every SKU shows "ORDER n cases (n×12
units)" plus "likely lo–hi" when P10 and P90 imply different case counts;
non-routine lines listed widest range first; routine SKUs collapsed as
standing orders under `routine_policy`; the order sentence is the v3
template (no LLM anywhere on the manager's path; the cache build no longer
calls the LLM either). History view keeps v2 / v1 (ASK ME) for comparison.

**Tested in the browser:** store 44, 16 May: 31 lines "worth a look", 9
standing orders (expander holds 9 inputs; 40 in total); "Place order" with
no changes → "40 confirmed, 0 changed, 0 set by you"; history v2 shows
28 of 40 ASK ME as before; no console errors.

**Problem found while testing:** the top line read "ORDER 14 cases (168
units) · likely 1–21" (item 1584575: P10 11.6, P50 165.2, P90 243.4 units;
actual 253). A 1–21-case range is useless to a manager and invites
distrust — and "widest first" puts it at the very top. How common, over
SKU-days with an order of ≥ 1 case: width ≥ 5 cases on 5.6% (store 44) /
1.4% (store 8); in those, the low end is typically 0 cases (P10 near zero),
yet the needed cases still fall inside 91% / 94% of the time. Likely cause:
zero-sales days in the history (stockouts or days not stocked — this data
can't tell them apart) teach the P10 model that "almost nothing" is
possible. Honest but unhelpful. Display fix to be decided with Harry.

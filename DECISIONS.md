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

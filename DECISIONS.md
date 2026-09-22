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

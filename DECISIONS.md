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

# FreshCall — Project Handoff for Claude Code

> **Read this first.** This file is the single source of truth carried out of a long planning chat for Harry's (CHAN HIO WENG) NTU MSc Enterprise AI course **PE6201 Emerging AI Technologies**, End-of-Course Project. It records decisions, verified facts, formulas, open issues and working rules. State reflects the chat up to Milestone 1 (Problem Statement, submitted Aug 2026). Later decisions may exist elsewhere — if anything here conflicts with newer instructions from Harry, **Harry wins**.

---

## 0. Working rules (non-negotiable)

1. **Never state an unverified fact as fact.** If something is an assumption, label it `ASSUMPTION` in code comments, config and docs. Harry's explicit rule: *没确认的东西不要提及/不要生成.*
2. **Be concise.** Harry dislikes padding, preamble and over-long answers. Answer the question asked.
3. **Language:** Harry reads mixed Chinese + English. Code, comments, docstrings and README in English.
4. **The LLM never touches numbers.** All arithmetic and decisions are deterministic Python. The LLM only writes wording, from a fact block, and may not emit any number not in that block.
5. **Do not redistribute Kaggle data.** Keep raw data out of git (`data/` in `.gitignore`). Ship a README download step, a small derived sample only if Harry confirms it is allowed.
6. **Deadlines / assessment requirements:** do not assert any. Check `PE6201_Assessment_Timeline.pdf` / course docs, or ask Harry.

---

## 1. What the project is

**Working title:** FreshCall — sizes tomorrow's fresh order, or abstains

**One-line:** A next-day ordering copilot for short-shelf-life QSR SKUs that returns a quantity (in cases) with a one-line reason when it is confident, and hands the SKU back to the manager when it is not.

**What the manager sees (one line per SKU):**
```
Tomato slices    ORDER 3 cases. Last 7 days averaged 30, steady.
Lettuce          ASK ME — harder to call than usual today.
```

**Problem.** QSR managers size next-day fresh orders from last week's number plus a margin; over-ordering is discarded. ~40 short-shelf-life SKUs/store/day ≈ 14,600 decisions/store/year (ASSUMPTION on SKU count).

**Gap vs existing tools** (Crunchtime = category leader, already handles weather/holidays, 15-min forecasts; ClearCOGS = lightweight, waste-focused): not that they forecast badly, and not that FreshCall can predict structural breaks (nobody can — a break is outside the training distribution by definition). The gap: they return a number with **no statement of whether to trust it**. FreshCall communicates that difference.

**Out of scope:** predicting demand shocks whose driver is outside the feature set; labour scheduling; ambient/frozen SKUs; multi-store allocation; automatic order submission; food-safety hold/discard times.

**Primary user:** the restaurant manager placing tomorrow's fresh order on a phone at the end of the evening shift; has never seen a prediction interval; will not open a second screen.

**Design constraints from the persona:**
- One screen; quantities in **cases**, not units.
- **Never show a confidence number** on screen; abstention reads as a request for judgement.
- Every recommendation is overridable; an override is not a system failure.

**Domain-knowledge note:** Harry worked in McDonald's China procurement (Dec 2025 – Mar 2026), not store ops. The persona is a **design hypothesis**, not an observation. Do not write copy implying store-level first-hand knowledge.

---

## 2. Architecture (decided)

Hybrid. Each layer chosen for a reason:

| Component | Choice | Why not the alternative |
|---|---|---|
| Next-day demand | Narrow ML — scikit-learn `GradientBoostingRegressor(loss="quantile")`, α = 0.1 / 0.5 / 0.9 | LLM gives no calibrated interval over a number; the interval *is* the product. LLM is also non-deterministic. |
| Order arithmetic | Deterministic Python | Unit-testable, replayable; errors here are cash errors |
| Abstention gate | Deterministic threshold on the interval (+ interval-independent gates, §6) | Self-reported LLM confidence is unvalidated; the threshold must be movable and re-measurable |
| Explanation + abstention wording | Rented `openai/gpt-4o-mini` via OpenRouter | Generation over a fixed fact block; no number originates here |

**Rejected:** RAG (no document corpus; structured numerics → no information gain). Agent (single-shot pipeline: history → predict → gate → arithmetic → one sentence).

**Non-AI baseline:** `naive_seasonal` = same weekday last week, ÷ case pack, rounded up. If it wins on a SKU, that SKU should not use the model.

**Own / Rent:**

| Layer | Own/Rent | Thing |
|---|---|---|
| Interface | Own | Streamlit, one page |
| Serving | Rent | Fly.io shared-cpu-1x (~USD 5/mo) — demo only |
| Orchestration | Own | Plain Python, **no LangChain** |
| Model — numeric | Own | scikit-learn quantile GBR |
| Model — language | Rent | gpt-4o-mini via OpenRouter |
| Data | Own (prod) / Kaggle (prototype) | Daily net units per SKU |
| Vector store | Neither | No retrieval |
| Eval / observability | Own | pytest + backtest script |

**Low-code:** not used. Stated reason (to be written into the doc): the gate threshold and case-pack arithmetic must be unit-testable and diffable in git; a GUI-configured gate cannot be asserted in pytest. Planned check: a bounded 45-min n8n build (one SKU, one gate branch) to test that reasoning; report if low-code wins.

---

## 3. Data — Corporación Favorita Grocery Sales Forecasting (Kaggle)

URL: `kaggle.com/competitions/favorita-grocery-sales-forecasting`

### 3.1 Verified facts (primary data description or direct file inspection)

| Fact | Value |
|---|---|
| Stores | 54 (`stores.csv`) |
| Items | **4,100 rows in `items.csv`**; ~4,036 distinct items appear in train (use "4,100", not "~4,000" or "4,400") |
| Train dates | 2013-01-01 → 2017-08-15 |
| Test dates | 2017-08-16 → 2017-08-31 |
| Train rows | 125,497,040 |
| Files | `train.csv, test.csv, sample_submission.csv, stores.csv, items.csv, transactions.csv, oil.csv, holidays_events.csv` |
| Promotions | `onpromotion` **column** in train/test (not a separate file); ~16% NaN in train, mostly 2013–2014 |
| Holidays | `holidays_events.csv` with a `transferred` column (also types Transfer / Bridge / Work Day) |
| Perishable | `items.csv` has `perishable` (0/1); metric NWRMSLE weights perishable 1.25 vs 1.00 |
| **Zero-sales rows** | **Omitted from train.csv.** Must expand the store×item×date grid and fill zeros |
| unit_sales | Can be **float** (sold by weight); **negative = returns** |
| Christmas | Dec 25 missing for 2013–2016 (stores closed) |
| Inventory | **No stock/inventory field** — zero day cannot be told apart from stockout or not-carried |
| Known shocks | Public-sector pay days (15th and last day of month); **M7.8 earthquake 2016-04-16**, affected sales for several weeks |
| Access | Kaggle account + **accept competition rules** before download; CLI: `kaggle competitions download -c favorita-grocery-sales-forecasting` |
| Licence | Rules permit academic/non-commercial use; **prohibit redistribution** (from search-indexed rules text — Harry should confirm on the Rules tab while logged in) |

**Do not confuse** with "Store Sales – Time Series Forecasting" (family-level aggregation, **no `items.csv`, no perishable flag**). FreshCall needs the item-level competition.

### 3.2 Slice design

- One store × 40 perishable SKUs (40 is a target; final count depends on filters).
- Full grid ≈ 40 × ~1,688 days ≈ 67,500 rows **after** expansion; raw filtered rows will be fewer.
- **Filters (in order):**
  1. `perishable == 1`
  2. **integer unit_sales across full history** (drop sold-by-weight items — no case pack)
  3. **sales density** filter (threshold set from the data; purpose: avoid intermittent series that make every interval wide)
- Handle negatives (returns) explicitly — do not silently clip; decide and document.
- Handle missing Christmas dates explicitly when building the continuous series.

### 3.3 What the dataset cannot tell us

- No discard field → the money value (§5) is a **modelled inference**, not observed.
- It was built to score forecast accuracy, not ordering decisions.
- Supermarket demand ≠ QSR demand (QSR consumes SKUs through a menu bill of materials).
- Ecuadorian calendar, not Chinese.
- No inventory → `on_hand` unavailable; censored-demand correction not implementable on this data.

**Framing consequence (important):** the prototype validates **Layer A — demand estimation + uncertainty + abstention + translation pipeline**. It does **not** validate **Layer B — inventory-aware order optimisation**, which needs real POS data with on-hand.

### 3.4 Leakage controls

- All lag/rolling features use strict `.shift(1)`.
- Chronological split only, never random.
- Deliberate-leak control: add same-day sales as a feature, report metric with vs without; the gap measures pipeline cheating.

---

## 4. Core formulas

```text
# Quantiles
P10, P50, P90 = three quantile GBRs (alpha 0.1 / 0.5 / 0.9)
# Enforce non-crossing: sort the three predictions per row before use.

# Gate
rel_width = (P90 - P10) / max(P50, 1)
abstain if rel_width > THRESHOLD         # THRESHOLD starts at 0.60 (opening position, not derived)

# Order arithmetic (deterministic Python)
cases = ceil((P50 + safety - on_hand) / case_pack)
units = cases * case_pack

# Prototype assumptions (all ASSUMPTION, in config.yaml)
case_pack = 12
safety    = fixed constant (default 0 — see open decision D2)
on_hand   = 0          # Favorita has no inventory field
```

**Baseline order:** `ceil(sales[same weekday last week] / case_pack)`.

**Perfect-hindsight (PH) order — OPEN DECISION D1, must be written down before any metric is computed.** Recommended for the prototype:
```text
PH_cases = ceil(actual_units / case_pack)
```
Consequence to state honestly: with `on_hand = 0`, CPOA becomes a discretised demand-accuracy metric (Layer A), not an inventory-aware ordering metric.

---

## 5. Metrics & evaluation

### 5.1 Metrics

| Metric | Definition | Baseline | Target |
|---|---|---|---|
| **Case-Pack Order Accuracy (CPOA)** — headline | Share of SKU-days where recommended cases == PH cases | To measure (naive_seasonal) | ≥ 15% relative improvement on the auto-answered slice |
| Abstain Rate | Abstained SKU-days ÷ all SKU-days | — | 15% (design choice under the attention ceiling; final point chosen from the sweep) |
| Abstention Precision | Share of abstained SKU-days where the model's cases would have ≠ PH cases (≥1-case error) | — | As high as the sweep allows at that rate |

Why CPOA: the decision is discrete (3 cases or 4). An 8% forecast error matters only if it crosses a case boundary; store-level MAPE hides this and lets opposite-sign SKU errors cancel.

Coupling (report as a curve, never one point):
```text
recall = (abstain_rate * precision) / error_base_rate
```
`error_base_rate` is unmeasured → **no recall target**. Abstention precision is **backtest-only** (in production the counterfactual is never observed).

### 5.2 Eval plan (four checks)

1. **Temporal holdout** — train ≤ 2017-07-15; test 2017-07-16 → 2017-08-15 (last 31 days of Favorita train). 31 days × selected SKUs, fixed before fitting. Do **not** claim statistical sufficiency (31 correlated days is a small effective sample).
2. **Gate sweep** — thresholds 0.40 / 0.50 / 0.60 / 0.70; plot abstention precision vs abstain rate.
3. **Explanation harness** — 10-case L1/L2 (from Class 3). L1: every numeral in output ∈ fact block. L2: LLM judge on faithfulness/tone; Harry hand-labels all 10 and reports judge–human disagreement.
4. **Interval calibration** — empirical coverage of P10–P90 vs nominal 80%. **Run first**: if far below nominal, all abstention numbers are meaningless.

**Earthquake probe (separate from the holdout):** check behaviour around 2016-04-16 — did the interval widen, did the novelty check fire, or was the model confidently wrong?

**Three-bucket error decomposition** (backtest, high-error days): (a) wide interval — gate catches; (b) novel feature vector — novelty check catches; (c) narrow interval + ordinary features — nothing catches. **The size of (c) bounds what abstention can achieve**; report it whatever it is.

**Abandon condition:** if abstention precision at ~15% is no better than random SKU selection, conclude the problem needs faster post-hoc detection, not abstention — and report it.

---

## 6. Risks & mitigations

**Silent failure:** a regime break the features can't see (local promo, school holiday, competitor closure). Interval stays narrow (estimated from normal-condition residuals) → gate doesn't fire → LLM writes a true, grounded, irrelevant sentence ("last 7 days averaged 30, no trend") → manager accepts → waste surfaces weeks later in an aggregate variance report.

**Compounding version:** stockout censors recorded demand → enters training → model learns lower demand → orders less → stocks out again. MAPE stays flat (persistent bias, not larger magnitude).

| Risk | Mitigation |
|---|---|
| Narrow interval on a regime break | Two interval-independent gates: calendar-flag rule (force abstain around rare events) + novelty check (e.g. IsolationForest distance from training features). Thresholds set from data. |
| Persistent bias invisible to MAPE | Rolling **signed** mean error monitor; alert threshold from backtest residual distribution |
| Censored-demand loop | Real POS: exclude SKU-days ending at zero on-hand. **Not implementable on Favorita** — state as limitation, do not simulate |
| Miscalibrated intervals | Rolling coverage monitor; sustained under-coverage → global forced abstention until retrained |
| LLM invents a figure | Numeric-containment assertion on every call; failure → deterministic template string |
| Over-trust | Never auto-submit; explicit confirmation tap per recommendation |

**Intended use:** advisory next-day quantities for short-shelf-life SKUs, always human-confirmed.
**Non-use:** never food-safety decisions (shelf life / hold / discard are HACCP-governed); not labour scheduling; not SKUs where stockout has safety/allergen consequence; never auto-submits.
**Affected:** manager (accountable for a variance she didn't cause), crew (absorb stockouts), franchisee P&L.
**Frameworks (wording, no entry numbers — numbering not verified):** IMDA Model AI Governance Framework — Harry's judgement: low-severity, high-frequency → human-in-the-loop. OWASP Top 10 for LLM Applications (2025) — the misinformation entry.

---

## 7. Economics

**Token cost (estimate — measure real counts with the Class 3 notebook before relying on it):**
```text
per call  = 580 in × 0.15/1M + 60 out × 0.60/1M = USD 0.000123   (gpt-4o-mini)
per store = 10 calls/day × 30 = USD ≈0.037/month
Claude Haiku 4.5 (1.00/5.00 per 1M) ≈ 7× → still negligible
```

**Avoided waste (illustrative, all ASSUMPTION):**
```text
USD 19k weekly revenue × 30% food cost × 22% short-shelf-life × 4.5% waste
  × 60% attributable to over-ordering × 25% reduction ≈ USD 8.5/week ≈ USD 35–37/store/month
```
Claim only the direction: tokens are ~three orders of magnitude smaller than value at stake. Don't quote precise ratios.

**Binding constraint = manager attention:**
```text
today:    40 SKUs × 30 s = 1,200 s
copilot:  40 × [a×90 + (1−a)×5] = 3,400a + 200 s
break-even a ≈ 29.4%   → design target 15% sits inside the ceiling
```
All three timings (30 / 90 / 5 s) are unmeasured assumptions. Better in the final: a small sensitivity table (e.g. abstain 60/90/120 s, scan 3/5/8 s).

---

## 8. Smallest first version (build this first)

One SKU exported from the Favorita slice as a 90-row daily CSV (≈12 weekday cycles).

1. Features: weekday dummies, lag-1, lag-7, rolling-7 mean — all `.shift(1)`.
2. Fit 3 quantile GBRs on rows 1–83; predict next day.
3. Gate: `rel_width > 0.60` → abstain.
4. Else `cases`, `units` via deterministic Python (`on_hand = 0`, `safety` from YAML — both ASSUMPTION). Write both into the fact block.
5. One gpt-4o-mini call with the fact block, forbidden from emitting numbers not in it → single output line.

This is a **pipeline test**, not a test of the ordering/safety-stock policy.

**Pass / fail (all automated):**
1. Runs end-to-end on a clean venv in < 60 s.
2. `units % case_pack == 0` asserted in code.
3. Every numeral in the output ∈ fact block — one unauthorised number = FAIL.
4. High-variance input → abstain string with **no quantity and no confidence figure** (assert: no digits in output).

**Target outputs:**
```text
ORDER 3 cases (36 units). Forecast 31, recent daily average 30.
ABSTAIN - this one is harder to call than usual. Please set it manually.
```

---

## 9. Suggested repo layout

```text
freshcall/
├── README.md               # download step (kaggle CLI + accept rules), how to run
├── config.yaml             # case_pack, safety, on_hand, gate threshold, sweep list — all marked ASSUMPTION
├── .gitignore              # data/, .env
├── data/                   # raw Kaggle files (never committed)
├── src/freshcall/
│   ├── load.py             # read train.csv efficiently (filter by store; typed dtypes/chunks)
│   ├── slice.py            # perishable → integer-only → density filters; grid expansion; zero fill; Christmas; returns
│   ├── features.py         # weekday dummies, lag-1, lag-7, rolling-7, all shift(1)
│   ├── model.py            # 3 quantile GBRs, non-crossing sort
│   ├── gate.py             # rel_width gate (+ calendar flag, novelty check later)
│   ├── order.py            # deterministic case arithmetic, baseline, PH order
│   ├── explain.py          # fact block → OpenRouter gpt-4o-mini; template fallback
│   ├── containment.py      # numeral ⊆ fact block check
│   └── backtest.py         # holdout, CPOA, abstention precision, sweep, coverage, 3-bucket decomposition
├── run_slice.py            # the smallest first version
└── tests/
    ├── test_order.py       # units % case_pack == 0, baseline, PH
    ├── test_containment.py # zero-tolerance numeral check
    └── test_gate.py        # high-variance → number-free abstain string
```

Env: `OPENROUTER_API_KEY` from `.env`. Model string: `openai/gpt-4o-mini`.

---

## 10. Open decisions (ask Harry before assuming)

| ID | Decision | Recommendation |
|---|---|---|
| D1 | PH order definition | `ceil(actual_units / case_pack)`; state it makes CPOA a Layer-A metric |
| D2 | `safety` value | 0 in prototype, so recommended vs PH are comparable; if >0, recommended cases are systematically above PH and CPOA is biased |
| D3 | Which store | Pick after density filter shows which store yields enough integer-sale perishables |
| D4 | Density threshold | Set from the data distribution; document the chosen value |
| D5 | Returns handling | Decide (e.g. keep net units, or clip at 0) and document |
| D6 | Novelty check method | IsolationForest suggested; confirm |
| D7 | 15% target vs sweep-chosen point | Treat 15% as a comparison/design point, final operating point from the curve |

---

## 11. Milestone 1 document — outstanding fixes (as of last review)

Last reviewed version scored ~80/100 in Claude's simulated review (a separate AI gave 88). Remaining gaps:

**Must fix**
- §7 holdout: insert dates (train ≤ 2017-07-15; test 2017-07-16 → 2017-08-15; last 31 days before train file ends).
- §2: restore the **Out of scope** paragraph (deleted in last revision).
- §5: unify currency — chain in USD (19k weekly revenue → ≈USD 35/month).
- Fix broken sentences: §2 "ordered daily about 14,600"; §4 "rather than a multi-step loop adds failure modes"; §5 "25% reduction, tokens are smaller…" (split into two sentences).
- **Unify pronouns** (§3 "his", §5 "her"/"his" in one sentence, §8 "she").

**Should fix**
- §7: define PH order (D1).
- §5: add low-code paragraph (question explicitly asks "low-code and/or code").
- §6: add leakage sentences.
- §6: "~4,000 items" → "4,100 items in items.csv"; rows = "≈67,500 after grid expansion; raw filtered rows fewer because zero-sales days are omitted".
- §6: licence wording — "no personal data, so no PDPA/residency issue; Kaggle rules require acceptance before download and prohibit redistribution, so raw data is not re-hosted." Don't claim "no constraint".
- §9: label `case_pack = 12` as an assumption.

**Nice to have**
- §1: add the two-line output example (biggest readability gain — reader currently sees what the system outputs only on page 4).
- §5: restore the domain-specific / portability paragraph (qualitative only — no "70%" claim).
- §3: restore the domain-knowledge declaration.
- §8: add Frameworks line.
- Grammar: "de-identified at store-item level, which means no PDPA…".

---

## 12. Key concepts Harry asked about (so they aren't re-explained from scratch)

- **Case boundary:** with case pack 12, demand 35 vs forecast 37 flips 3→4 cases (bad) while 31 vs 33 stays 3 (fine) — smaller % error can be a worse decision.
- **Aggregation hides errors:** over-ordering tomato and under-ordering lettuce cancel at store level but both happen in the store.
- **Compounding / censored demand:** sales ≠ demand when stocked out; training on censored sales creates a self-reinforcing under-order loop; model scores "perfect" against its own censored record.
- **Aleatoric vs epistemic uncertainty:** quantile intervals capture inherent volatility (aleatoric) but not "never seen this" (epistemic) → need novelty/calendar gates.
- **Silent failure via true-but-irrelevant explanation:** passes numeric checks, misleads anyway — why OWASP's misinformation entry, not "hallucination", is the right frame.

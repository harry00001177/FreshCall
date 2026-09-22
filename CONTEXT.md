# FreshCall — Glossary

Terms only. No implementation details here — see `src/` and `config.yaml`.

- **abstain** — the system's decision to withhold a quantity recommendation
  because its uncertainty is too high, handing the SKU back to a human. This
  is the only term used for this concept in code, logs, and comments.
- **ASK ME** — the *only* UI-facing rendering of `abstain`. Never write
  "uncertain", "low confidence", "needs review", or any other synonym in
  code or copy — they all mean `abstain` and must say so.
- `confidence` — **banned word**, everywhere in this codebase (code, comments,
  logs, variable names). The persona design constraint is that a manager must
  never see a confidence number. To keep that true by construction, the
  underlying uncertainty proxy is only ever called `rel_width` (relative
  interval width), never "confidence" of any kind — so a name search for the
  banned word is a genuine check that the constraint hasn't leaked.
- **hindsight_demand_order** — `ceil(actual_units / case_pack)`, i.e. what a
  case-based order would have been if the actual next-day sales were known in
  advance. This is a Layer A (demand-only) benchmark, not a claim about the
  optimal order under any real ordering policy — that would require real
  on-hand/inventory data, which this dataset doesn't have. (Previously called
  "PH order" / "perfect-hindsight order" — renamed because "perfect" implied
  an optimality this number doesn't have.)
- **Case Match Rate (CMR)** — share of SKU-days where the recommended case
  quantity equals `hindsight_demand_order`. This is the project's headline
  metric. (Previously "CPOA" / "Case-Pack Order Accuracy" — renamed to drop
  "Order Accuracy," which implied validation of inventory-aware ordering
  (Layer B) that this dataset cannot support.)
- **Layer A** — the part of the system this prototype actually validates:
  demand estimation + uncertainty + abstention + wording.
- **Layer B** — inventory-aware order optimization (using real on-hand stock).
  Not implementable on the Favorita dataset (no inventory field); not
  validated by this prototype.
- **case_pack** — units per case. A single global assumption (12) applied to
  every SKU in `config.yaml` — Favorita has no real case-pack field, so a
  per-SKU value would be no more accurate, just harder to defend (one
  labelled assumption beats five unlabelled-looking ones). Orders are always
  in whole cases.
- **reference anchor** — the one number shown alongside an `abstain` ("ASK
  ME") message: last same-weekday actual sales (a historical fact, not a
  model output). Allowed precisely because it isn't a confidence signal —
  see the `confidence` ban above.
- **on_hand** — units already in the store before tomorrow's delivery.
  Hardcoded to 0 in the prototype (Favorita has no inventory field) — this is
  a data limitation, not a modeling choice.
- **safety** — a fixed constant added to the demand forecast before rounding
  to cases. Set to 0 in the prototype so recommended cases are directly
  comparable to `hindsight_demand_order` (any positive value would bias the
  comparison). Not a claim that real stores should run with zero safety
  stock — a Layer A simplification.
- **rel_width** — `(P90 - P10) / max(P50, 1)`, the relative width of the
  predicted demand interval. The sole uncertainty signal driving the abstain
  gate.

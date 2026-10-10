# Track B remainder: age-anchored smile, age clocks, JSON interchange (2026-10-09)

Fork-only planning note. **Supersedes the first draft of this file**, which was written before
this branch's Phase 2b and essential-lines work. Discussion: upstream #177 / #175. We are waiting
on mdlacasse's reply to three questions (bequest as a tier, "ladders", age-anchored smile). This
plan assumes our proposed answers:

1. **Bequest stays the objective** in v1. A minimum-bequest floor is a later constraint, not a tier.
2. **"Ladders" = budget variants** (lean/base/comfortable, rent vs buy, move years) swept in Owl.
3. **Age-anchored smile is worth doing on its own**, independent of Owl-budget.

## What is already shipped (do not rebuild)

Phase 2b and the cost-function work are on `claude/phase2-housing` (PROGRESS.md, CHANGELOG
Unreleased). This plan only adds what they left open.

| Shipped | Where |
|---|---|
| HFP `Budget` sheet → spending profile (`spending_profile = "budget"`) | `budget.py`, `Plan._evaluateBudget` (`plan.py:1465`) |
| Spec, not array: re-evaluated at the current `N_n` / `n_d` | `budget.evaluate()`; clone goes through `plan_to_config` and re-applies house tables |
| Per-line `survivor` % (household types default 100) | `budget._survivor_share` |
| Essential lines as a floor, discretionary scaled (`g_n = E_n + k D_n`) | `Plan._add_essential_profile` (`plan.py:3827`); one LP, no new binaries |
| `netSpending` default = budget first year under `maxBequest` | `plan.py`, tested |
| NJ property tax deduction from the budget's rent / property-tax lines | `st_pt`, bound follows `g_n` |
| Reporting by line (Budget sheet in the results workbook) | `export.py` |
| Old `Housing` sheets read as budget lines | `hfp_io.py` |

The LP, `spendingSlack` and the two objectives are unchanged except for the affine profile rows
when essentials are present.

## What is left (this plan)

Three gaps, in the order that matters for longevity and for Owl-budget.

### 1. Age-anchored smile (independent; answers Q3)

Today (`spending.py:57-70`) the cosine is stretched over `span = N_n - 1 - delay`, so a longer
life moves the dip later. The discussion's point: a line (and the smile) should follow the clock
that causes it — age, not plan length.

- Draw the shape as a **function of age**, then sample it onto plan years.
- Age index: the younger spouse's age (or the individual's), `age_n[n] = yobs_min + n`.
  Document it; the budget-line age clock below reuses the same index.
- `dip`, `increase` stay percent. Keep `delay` as **years after plan start** (the retirement
  transition), so existing cases and fixtures do not move when `N_n` is unchanged.
- On a fixed horizon this must reproduce today's curve for the shipped defaults
  (`dip=15`, `increase=12`, `delay=0`). On a longer horizon the early years are **unchanged**
  and the extra years take the late part of the curve.
- Only `profile == "smile"` changes. Flat and `"budget"` are unaffected.

If the maintainer wants this without the rest, it is a self-contained upstream issue.

### 2. Age clock on budget lines

`budget.evaluate()` (`budget.py:160-171`) only knows calendar `year` / `end`. A travel line
("while we are able") and a care line ("from 80") should follow age, so a longer life appends
years in which they still apply — the same reason the profile must be a spec.

Minimal addition to the `Budget` sheet (and to the JSON form below):

| Column | Meaning |
|---|---|
| `clock` | optional; `"calendar"` (default) or `"age"` |
| `start_age`, `end_age` | used when `clock = "age"`; inclusive ages |
| `index` | optional; `"younger"` (default), `"older"`, or a name in `basic_info.names` |

- When `clock = "age"`, `year` / `end` are ignored (or reused as the age fields — prefer explicit
  `start_age` / `end_age` so the two clocks cannot be mixed up).
- Evaluation: `age_n[n]` from the Plan's `yobs` / `mobs`, same index rule as the smile.
- Survivor share, `amount`, `rate`, `essential` unchanged.
- A line timed from the *death* ("downsize two years after") stays out of scope (already said so
  on #175).

### 3. JSON interchange for Owl-budget (no second evaluator)

The contract we proposed on #175 is a JSON profile file Owl evaluates. The fork already has the
evaluator (`budget.py`); what is missing is a **file format** that is not the HFP workbook, so
Owl-budget (and MCP) can hand lines over without writing Excel.

- `spending_profile = "budget"` can take lines from either:
  - the HFP `Budget` sheet (today), or
  - `optimization_parameters.budget_file = "profile.json"` (new), used when the sheet is absent
    or empty.
- JSON is the **same line model** as the sheet, plus `schema_version` and free-text `kind` /
  category for reporting:

```json
{
  "schema_version": 1,
  "lines": [
    {"name": "core living", "kind": "core", "year": 2026, "end": 0,
     "amount": 62.0, "rate": 0.0, "survivor": 60, "essential": true},
    {"name": "travel", "kind": "travel", "clock": "age",
     "start_age": 62, "end_age": 74, "index": "younger",
     "amount": 12.0, "rate": -1.0, "survivor": 30, "essential": false}
  ]
}
```

- Amounts in **today's dollars, $k** (Owl units). Document loudly; a dollars file is 1000× off.
- Unknown fields and unknown `schema_version` are refusals, not silent drops (as we said for
  #173's property links).
- One evaluator: a small loader turns the JSON into the same DataFrame/rows `budget.evaluate()`
  already takes. Do not fork the math.
- Round trip: a case saved from Owl keeps the file path; Owl does not need to rewrite the JSON
  (Owl-budget owns the file). HFP write-back of the sheet stays as it is.

Three-column pre-built series (both-alive / A-survivor / B-survivor) stay an **optional later
encoding** of the same spec for Excel/MCP. Not needed while lines carry survivor share.

## Out of scope (still)

- Priority tiers beyond essential/discretionary (already two-tier in the LP; more tiers = a
  sequence of LPs, later).
- Per-tier stochastic risk (core at a high success rate, discretionary risk-neutral). Evidence is
  in the #175 thread (9/200 survivor draws). Needs `stresstests._stochastic_lp` to split the
  commitment; a later design note.
- Non-scalable lines as a separate LP family (the essential flag already gives a floor; rent as a
  true fixed outflow is the old Housing ledger).
- Bequest as a tier.
- Owl-budget itself (Track C; `owl-budget-requirements.md`).
- Payroll tax for pre-retirement budgets.

## Steps (each a commit)

| # | Piece | Tests |
|---|---|---|
| 0 | Age-anchored smile in `spending.py` | Fixed horizon ≡ old smile (tight tolerance); longer horizon leaves early years unchanged and keeps the dip at the same age |
| 1 | Age clock on `Budget` lines (`clock`, `start_age`, `end_age`, `index`) | Growth/bounds/survivor already covered; add age-clock cases, `index`, longer clone horizon |
| 2 | JSON loader (`budget_file`) → `budget.evaluate()` | Schema version, unknown field refused, $k units, sheet preferred when both present, clone round trip |
| 3 | Docs (`info/PARAMETERS.md`, `ui/Documentation.py`, `phase0-scenarios.md`) + optional UI read-only path | |

Order 0 → 1 → 2 is strict; 3 can ride along. Suite green and flake8 after each.

## Upstream delivery

- Implement in the fork first (the household needs age clocks for travel/care lines).
- **Step 0 alone** is a clean upstream issue if he answers Q3 with yes before the rest is ready.
- Steps 1–2 are the #175 contract made concrete: one design issue or a reply on #175, pointing at
  the branch, with the equivalence tests (one core line ≡ flat/smile; essentials ≡ the old plan
  when the flag is off) as evidence. Cut a stock-`dev` patch without fork-only NJ/budget-tax code
  if he wants code rather than a description (the #158 pattern).
- NJ and other state rules stay in the fork.

## Track A reminder (unchanged)

Fill `otherFiles/Case_us.toml` and the HFP workbooks; run Scenario 5 (rent vs buy) and Scenario 3
(residency) with local search + exact LP. Already supported by the shipped Budget profile and the
NJ deduction. This remainder improves longevity behavior and the Owl-budget handoff; it is not a
prerequisite for the first rent-vs-buy table.

## Note on the 2026-10-09 upstream merge

Merged `upstream/dev` at `d6970b2e` (`withSeniorBonus = "optimize"`). Keep both binary families:
fork `zx` (NJ exclusion tiers, in `localsearch.FAMILIES`) and upstream `zsb` (senior bonus, in
`ALWAYS_FREE`). A state that follows the federal deduction still takes the bonus from the previous
iteration; our NJ path does not use it.

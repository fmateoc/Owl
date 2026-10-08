# Phase 2b plan: housing as part of a budget-built spending profile (2026-10-08)

**Status (2026-10-08): the user agreed to all three decisions as recommended and posted
`issue-175-reply.md`; implemented on `claude/phase2-housing` (see PROGRESS.md). One change from the
design below: the NJ deduction's bound follows spending exactly, as an LP row `st_pt_n <=
s_n * g_n` (s_n = the deductible lines' share of the budget's year), instead of using the lines'
unscaled amounts. Under `maxBequest` the two are the same; under `maxSpending` the row is right
and the unscaled bound was not.**

Fork-only planning note, after the maintainer's answer on #175 (housing ledger + NJ property tax
deduction). Goal: keep what the household needs (rent / buy with cash / buy with a mortgage,
recurring housing costs, NJ's property tax deduction) while moving the generic part to the shape
the maintainer described, so that it can go upstream.

## What the maintainer said (#175, relayed 2026-10-08)

1. No more state-tax plumbing upstream (4,000+ jurisdictions, diminishing returns, false sense of
   certainty). So the NJ property tax deduction stays in the fork, like the NJ exclusion (#160).
2. Budgeting is a different problem from optimizing. It belongs outside the optimizer: "a separate
   module ... to create the spending profile, based on specific budget activities. The output would
   then feed to the spending profile, either as a constraint or as shape ... The optimizer would then
   consume the envelope as an external spending profile."

## The check that decides it (run 2026-10-08)

`fork-notes/model-review/envelope_vs_ledger.py`: couple born 1964, NY, $1.5M tax-deferred, exact LP, $80k/yr core
spending (flat, 60% survivor), $30k/yr rent. Version A: Phase 2's Housing ledger (rent outside
`g_n`). Version B: no ledger; a custom `xi_n` = (80 x flat-with-survivor + 30) / its first year,
with `netSpending` = 110.

| Objective | A: ledger | B: rent inside the profile |
|---|---|---|
| `maxBequest`, fixed spending | bequest 1,209,697; outlays 110,000 then 78,000 | bequest 1,209,697; outlays identical every year (max difference $0) |
| `maxSpending`, bequest 0 | core 107,213 + rent 30,000 = 137,213 in year 0 | 137,004 = 1.2455 x the whole budget; survivor years up to $2,821/yr apart |

So with the reading we chose for rent vs buy (`maxBequest` at fixed spending, decision 2 of
`phase2-plan.md`), the envelope design gives the same plan as the ledger. It differs only under
`maxSpending`, where it scales the whole budget, rent included: "how large a version of this budget
can we afford", instead of "how much on top of fixed housing". That is the maintainer's model.

## Design

### Upstream-shaped part (proposal for #175)

**A. Owl consumes an external spending profile.** `setSpendingProfile("budget", ...)` (name to
agree) takes a profile in today's dollars per plan year instead of a flat/smile shape. Owl
normalizes it to `xi_n` (first year = 1, so the existing `g_n = g_0 xiBar_n / xiBar_0` rows and
`spendingSlack` are unchanged) and, under `maxBequest`, takes `netSpending` from the profile's first
year unless given. No LP change.

It must be a *specification* evaluated by Owl, not a stored array: the survivor step sits at the
first death (`n_d`), and `clone(expectancy=...)` and lifespan sampling rebuild the plan with a new
`n_d` and horizon. Checked: `clone` with a new expectancy rebuilds from the case configuration
(`plan_bridge.clone`), and the profile is regenerated only through `setSpendingProfile`.

**B. A budget module builds that specification** (`budget.py`, outside the optimizer). Lines from an
HFP sheet (generalizing Phase 2's `Housing` sheet):

| Column | Meaning |
|---|---|
| `active`, `name` | as in the other household sheets |
| `type` | `core`, `rent`, `property tax`, `insurance`, `maintenance`, `car`, `travel`, `care`, `other` (open list; only the tax rules read specific types) |
| `year`, `end` | first and last calendar year (as the Housing sheet: `end` 0 = last plan year, negative counts back) |
| `amount` | annual amount in `year` dollars (today's dollars for a past or current year) |
| `rate` | real growth above inflation, % |
| `survivor` | % kept after the first death (household costs such as rent: 100; personal spending: the case's survivor %) |

A `core` line can carry the flat/smile shape and the case's survivor percentage, so today's cases
are the special case "one core line". Output: the per-year real amounts (for A) and the breakdown
by line (for reporting: under `maxBequest` the amounts are exact; under `maxSpending` they scale
with the basis).

One-off items stay where upstream has them: purchase price or down payment as big-ticket items,
the home in Fixed Assets, the mortgage in Debts with its `property` link (#173).

### Fork-only part

- NJ property tax deduction (line 41): unchanged rule (`st_pt`, bounded LP variable, data in
  `taxes_state.toml`), with its bound computed from the budget's `property tax` and `rent` lines
  instead of the Housing ledger: at most the cap, and at most those lines' share of the year's
  net spending (an LP row, so it follows `g_n` under `maxSpending`; as implemented).
- The Phase 2 cash-flow term (`housing_costs_n` subtracted next to debt payments) goes away; the
  costs are inside `g_n`.

### What changes for the household

- Rent / buy with cash / buy with a mortgage: one budget per variant (rent line vs owner lines),
  same one-off entries as now. Reading unchanged: `maxBequest` at fixed spending, `final_bequest_today`.
- `netSpending` becomes the whole first-year budget (non-housing + housing), or is taken from it.
- Reports: total spending now includes housing; the budget breakdown shows the parts.

## Decisions for the user

1. **`maxSpending` semantics.** Recommended: accept the maintainer's (the whole budget scales).
   Our decision runs use `maxBequest`, where the two are identical (table above). The alternative,
   fixed lines that never scale, needs an LP change (a fixed outflow next to `g_n`), which is the
   Phase 2 ledger he is steering away from.
2. **Order.** Recommended: post the reply (`issue-175-reply.md`) and build in the fork now, shaped as
   the proposal; we need the feature either way, and nothing in it waits on him. If he wants part A
   only, B stays in the fork as a pre-processor.
3. **The Phase 2 code.** Recommended: replace the Housing ledger and its cash-flow term by A + B in
   the fork, keeping the NJ rule; keep reading old `Housing` sheets as budget lines (no data loss).

## Steps (after the decisions)

1. `budget.py`: lines -> per-year real amounts and breakdown; `core` line with flat/smile and
   survivor %; unit tests (growth, bounds, survivor step, a single core line = today's flat/smile).
2. `setSpendingProfile("budget", ...)`; `netSpending` from the profile under `maxBequest`; clone and
   lifespan sampling re-evaluate it; TOML (`spending_profile = "budget"`), HFP sheet read/write, UI
   keeps the sheet.
3. Remove the Housing cash-flow term; the NJ deduction bound from the budget lines; Housing sheet
   read as budget lines.
4. Tests: equivalence with Phase 2's ledger under `maxBequest` (the table above, to the dollar);
   a one-core-line budget equals the flat and smile profiles; NJ deduction tests carried over.
5. Re-run the housing stakes and Scenario 5; update `phase0-scenarios.md`.
6. Stock-`dev` patch for A + B (without the NJ rule) if the maintainer wants code.

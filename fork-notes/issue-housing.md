# Draft upstream issue (mdlacasse/Owl): Housing sheet and the NJ property tax deduction

**Title:** Proposal: a Housing ledger for recurring housing costs, and New Jersey's property tax deduction (line 41) as its first state rule

Status: filed by the user (issue number not recorded here; no maintainer response relayed as of 2026-10-08). Since then, the loan payoff it points to landed upstream as a `property` link on Debts (#173). Reference implementation: fork `fmateoc/Owl`, branch `claude/phase2-housing` (2026-10-07; review fixes in `a9093f8`). A minimal stock-`dev` patch can be prepared on request; the design below is what we would want reviewed first.

---

Two gaps, one shape. Recurring housing costs (rent, property tax, insurance, maintenance, HOA) run for decades and grow; today they can only be typed as one negative `big-ticket items` cell per year. And upstream assumes the federal standard deduction and has no state property-tax rule (`info/modeling-capabilities.md`; `ui/Documentation.py`), so a NJ homeowner or tenant gets no deduction. We propose an exogenous `Housing` sheet, and NJ-1040 line 41 as the first state rule that reads it. Housing itself is not optimized (your note on Debts: "Should I pay my mortgage or leave my money invested?" depends on risk tolerance); these are scenarios, not decisions inside the LP.

## 1. `Housing` sheet (generic)

An optional HFP sheet, shaped like `Debts`, one row per recurring cost:

| Column | Meaning |
|---|---|
| `active` | as in `Debts` / `Fixed Assets` |
| `name` | free text |
| `type` | `rent`, `property tax`, `insurance`, `maintenance`, `other` |
| `year` | first year paid |
| `end` | last calendar year paid, inclusive; 0 = through the last plan year, negative counts back from it (-1 = the year before the last). A positive `end` before `year` or the plan start leaves the row out, with a warning |
| `amount` | annual amount in `year` dollars |
| `rate` | real growth above inflation, %; 0 = tracks inflation (as `residence` in `Fixed Assets`) |

A new `housing.py`, modeled on `debts.py`, returns nominal per-year arrays `total_n`, `property_tax_n`, `rent_n`. The Plan stores them and subtracts `total_n` in `_add_net_cash_flow`, next to the debt payments. Net spending `g_n` then means non-housing spending, as it already excludes debt payments, so `maxSpending` results are comparable between rent and buy.

Conventions: amounts are household-level and are not scaled at the first death (as for debts). A workbook without the sheet loads as before. With a move, split the rows at the move year. For a residence sold in `yod` = Y, the owner's rows end in Y - 1 and the next home's (or rent) start in Y; with negative values, the same number in `end` and `yod` does that (`yod` = -3 is a sale in the third year from the end, `end` = -3 a last payment the year before).

**Evidence: the equivalence test.** A plan with a `Housing` sheet gives the same objective, to solver tolerance, as the same plan with those amounts entered as negative `big-ticket items` (the big-ticket series is inflated to match the housing ledger's growth). That is the claim that matters: the ledger is only a cleaner way to enter what `big-ticket items` can already express, plus the type split that a state rule needs.

Reporting: the Cash Flow sheet, one Summary line (total housing costs, today's and nominal $), `"housing"` next to `"debt pmts"` in the plot sources, `housing_costs_today`/`housing_costs_nominal` in `plan_metrics()` (so `owlcli run/compare` report them), and `property_tax_deduction` in the explanation's state-tax entries.

## 2. NJ property tax deduction (NJ-1040 line 41)

**Rule** (2025 NJ-1040 instructions, pages 25-31; the same $15,000, 18% and $50 are printed in the 2020 instructions, so the amounts are nominal):

- Line 40a: homeowners enter property taxes due and paid on the main home; tenants enter **18% of rent**.
- Line 41: **Property Tax Deduction up to $15,000**, subtracted from line 39 (taxable income) to give line 42.
- It comes **after** the retirement exclusion (lines 28a-28c) and the exemptions, so it does not change the income that sets the exclusion tiers.
- Line 56: the alternative is a refundable **$50 Property Tax Credit** (Worksheet H takes the credit only when the deduction saves less than $50). We leave the credit out; see below.

**Data** (`taxes_state.toml`, both `NJ_MFJ` and `NJ_Single`; omit for every other state):

```toml
property_tax_deduction = { cap = 15000, rent_share = 18, indexed = false }
```

**LP** (pure LP, no binaries, no new loop parameter — consistent with your choice to keep state taxes a pure LP on #160):

- Per year, before the solve: `st_ptd_n = min(cap, housing_property_tax_n + rent_share% * housing_rent_n)`.
- A continuous variable `st_pt` in `[0, st_ptd_n]`, only in years where `st_ptd_n > 0`, with coefficient +1 in the `state_taxable_income` row (the same position as the state standard deduction `st_e`).
- It is **also** added to the exclusion's total income `L` in `_add_state_tiered_exclusion`, so `L` stays at line 27. (Line 41 is after line 39: the deduction must not move the NJ exclusion tier.) Without that, a $15,000 deduction would push a year from $110,000 to $95,000 and flip it into the 100% tier.
- `localsearch.FAMILIES` does not change: there are no new binaries.
- The deduction's parameters are per-year arrays set in `solve()`; the Plan initializes them to zero so that `processDebtsAndFixedAssets()` still works before a first solve (the UI calls it for the Goals page).

Every new quantity is a per-year array computed before the solve, so the same variables appear in every state and nothing looks up another year (the constraints you set on #159).

**Not modeled, documented:** the $50 credit (worth at most $50 in a year where the deduction is worth less), the main-home and multi-unit rules (rows are assumed to be the main home), part-year amounts. NJ ANCHOR, Senior Freeze and Stay NJ are separate relief programs; enter an expected benefit as a positive big-ticket item.

## Illustration

Synthetic couple born 1964-03-15 and 1964-09-15, life expectancies 89 and 92, SS $3,000 and $2,400/month at 70, $150k taxable each, $75k Roth each, $1.5M tax-deferred, conservative rates, 60/40, `maxBequest` at `netSpending` $80k/yr. No Roth conversions (`maxRothConversion=0`) and Medicare off (`withMedicare="None"`) in every run. Lifetime state tax in today's dollars. "Exact LP" adds `withSSTaxability=0.85`. "Local search" adds `breakpointMethod="local-search"` (taxable SS by the IRS formula). Script: `fork-notes/model-review/housing_stakes.py`.

| Case | Final bequest, exact LP | Final bequest, local search | State tax (exact / LS) | Lifetime `st_pt` (exact / LS) |
|---|---:|---:|---:|---:|
| NJ, $20k property tax as big-ticket items (no deduction) | 1,047,594 | 1,096,194 | 11,047 / 12,981 | 0 / 0 |
| NJ, $20k property tax as Housing (deduction) | 1,056,287 | 1,109,414 | 5,693 / 11,890 | 260,356 / 255,451 |
| NJ, $30k rent as Housing (18% = $5,400) | 635,003 | 693,072 | 4,042 / 12,316 | 102,600 / 118,800 |
| NY, $20k property tax as Housing (no rule) | 993,457 | 1,062,711 | 48,926 / 50,495 | 0 / 0 |

Final bequest is the objective: savings after heirs' tax (`final_bequest_today`), today's dollars. Rerun 2026-10-07; the state-tax and `st_pt` columns are identical to the first run.

Reading: the NJ deduction raises the final bequest by $8,693 on the exact LP and $13,220 under local search, against the same cost entered as big-ticket items; the lifetime state tax it saves is smaller ($5,354 / $1,091), so most of the gain is not in the state-tax line: the saved tax compounds, and the plans differ on the federal side (not decomposed). The two methods differ by $49k-69k in level because they are different models (the exact LP pins taxable SS at 85%; both runs have Medicare off); compare differences within a method. The lifetime `st_pt` column is not a measure of value: in a year where NJ taxable income is zero anyway, any deduction up to the allowed amount gives the same plan, and the solver's pick there is arbitrary. NY pays far more state tax than NJ here because NJ's retirement exclusion is in the fork and NY's is smaller. Under the default self-consistent loop, differences under about 1% can come from the loop settling on different fixed points (see also our #171 findings); the table uses the two sturdier methods.

Size, by arithmetic on the NJ MFJ brackets: a full $15,000 deduction saves $525 at 3.5%, $829 at 5.525%, $956 at 6.37% a year. That is the same size as a NY/NJ residency spread, so it belongs in any rent-vs-buy or move comparison. A tenant paying $36,000 rent deducts $6,480.

## Choices that are yours

1. **The $50 credit.** We leave it out (at most $50 in a year where the deduction is worth less). A loop rule that picks credit or deduction would need another breakpoint. Happy to add it behind a data field if you prefer completeness.
2. **Where the rows live.** A new `Housing` sheet (what we did) rather than more `big-ticket items` cells or a property-tax column on `Fixed Assets` (which would change an upstream sheet and leave rent nowhere). The equivalence test is the safety net either way.
3. **Housing is not optimized.** The ledger is exogenous; rent vs buy is read as `maxBequest` at a fixed `netSpending`, comparing `final_bequest_today` (which already counts fixed assets net of remaining debt). A second view is `maxSpending` with the residence sold in a chosen year.
4. **Patch or design.** If you would rather implement from this description (as with #159), we will drop the fork copy when yours lands. If you want a minimal stock-`dev` patch first, we will cut one without our typed `StateTaxParams`, local tax or recapture, the way we rebuilt #158.

## Tests in the fork

- `housing.py`: growth (real rate with `gamma_n`), `year`/`end` bounds, `end <= 0`, `active`, type split.
- The equivalence test (Housing sheet = negative big-ticket items).
- NJ deduction: owner with $20,000 property tax (deduction $15,000), tenant with $30,000 rent ($5,400); NY unchanged (rule off); NY to NJ move (deduction only in NJ years); a year at $109k of line 27 claims the statutory 50% tier with the deduction (without the `L` term it claimed $92,035 instead of $54,518; checked by removing the term).
- `processDebtsAndFixedAssets()` before any solve; rows left out are named in a warning; `plan_metrics()` and the explanation report housing and the deduction (schema-validated).
- HFP write-read round trip with a `Housing` sheet; UI sync keeps it.
- The constraint-replay guard extended with a housing row in NJ.
- One NJ + housing case under `breakpointMethod="local-search"`.
- Full fork suite after the change: 2856 passed, 1 skipped (2818 before Phase 2).

Related, filed separately as #173: a mortgage outlived the sale of its home. Fixed upstream (`431aee0`) by linking a loan to the property it finances; rent vs buy with a planned sale uses that link.

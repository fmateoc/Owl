# Fork changelog (`fmateoc/Owl`; not part of upstream)

Moved here from the top of `CHANGELOG.md` on 2026-10-25, so that `CHANGELOG.md` stays upstream's
and stops conflicting at every sync (upstream edits its top on nearly every commit). New fork
entries go here. Not complete: Phase 5 (the payroll tax, the earnings test, which upstream now
has) is logged in `PROGRESS.md` only.

## Unreleased

### Upstream: docs pass and DCC-GARCH fix (`dev` `226ff54`, merged 2026-10-29)

Taken, with the doc conflicts resolved toward upstream's text (`papers/owl.tex` keeps only the
fork's state-tax paragraph). Fork follow-up: the city-tax identity `local_taxable_income` and the
STAR big-M link `star_enhanced_income` registered in the explainer's `CONSTRAINT_FAMILIES`, which
upstream's new registry test requires.

### Upstream: #235 (`dev` `b6a3ba7`, merged 2026-10-28)

Taken as is, no conflicts. The earnings test reads the five years before the plan for someone
already claiming (grace year, months withheld before the plan, the December check before the
plan). Version 2026.10.28 and dependency bumps. Fork follow-up: `check235_after.py` (the
law-side figures of the 2026-10-26 check reproduced).

### Upstream: #233, #234, #236, #238, #239 (`dev` `1bdc3b2`, merged 2026-10-28)

Taken as is, no conflicts. #233 (ours): a sticky-binaries tie no longer takes a plan outside the
requested gap (our patch). #234: the worksheet nets only a surplus round trip that realizes no
gain. #236: `spousal_surplus_deposit_fraction = "optimize"`. #238: the survivor's inherited
taxable account is stepped up at the first death; an initially empty taxable account is tracked
from a $0 basis. #239: a warning when the LTCG loop does not settle. Fork follow-up: the
`work_sweep.py` docstring.

### Upstream: #229-#232 fixed (`dev` `07b9a77`, merged 2026-10-27)

Taken as is. A 401k deferral counts as earnings with or without wages, and the employer's
contributions have their own HFP column, `employer ctrb` (never earnings). Exempt amounts and the
payroll wage base are nominal tables by year, 2027 included. After the spouse's FRA, the worker's
excess is charged on the ARF-adjusted add-on. Fork follow-ups: the strict xfails in
`tests/ss/test_earnings_test_properties.py` removed, the #229 case entering the deferral as
`kappa401k_in`, a case for the IRA rule, and `employer ctrb` in the household HFP generator
(`fork-notes/phase0/gen_hfp_us.py`).

### Upstream: the payroll tax is upstream's (#227, PR #228)

PR #228 landed upstream as `3a2dfc33` (2026-10-25), tree identical to the PR head, followed by
upstream's own changes: MOSEK records for the five re-pinned cases, the payroll tax as its own line
in the taxes plot ("Taxes and Premiums") and as its own *Payroll tax* slice and band in the
lifetime allocation and cash-flow mix (the fork had it inside *Taxes*), and a Summary with the same
rows for every plan. Merged here the same day; the fork's payroll code, tests and fixture are
upstream's. The entry below is the history before the landing.

### Changed: the payroll tax takes the shape of the upstream PR for #227

The fork's payroll-tax code is now the PR's (`payroll-tax-pr`, built on upstream `dev` `22ce72b`
at the maintainer's request): `Plan.payroll_n` (was `payroll_tax_n`), one yearly total from
`tax_federal.payrollTax(N_i, earnings_in, gamma_n, n_d, N_n)`, the wage base a single constant in
today's dollars. *Total payroll tax paid* is now in the Summary of every case (\$0 without
earnings), the fork's *Additional Medicare tax* line under it is gone, and the Cash Flow and CSV
*payroll tax* column sits after *NIIT*. Rules and amounts unchanged: every pinned case gives the
PR's values. With the PR's review fixes: a *payroll tax* column in the Taxes worksheet, and
`tax_federal.filingStatusIndex_n` in place of the fork's `tax_state.filing_status_by_year` (same rule),
then of the other copies, upstream's and the fork's (the itemizing warning, the non-itemizer
charity cap), except upstream's `taxParams` and `seniorBonusSchedule`, which keep theirs as in the
PR.

### Removed: the fork's age-anchored smile (back to upstream's smile)

The smile is upstream's again: one cosine period over the plan's length, starting `smile_delay`
years after the first plan year. Gone: the fixed 30-year period, `smile_start_age` (a case that
still carries it has it ignored), the survivor's age after the first death, the old-case warning
and the UI's start-age field. The six example cases no longer carry `smile_start_age`, and the
pinned results of the smile cases are upstream's again where no other fork feature moves them
(jack+jill's spending basis 102,621 in `test_toml_cases`; the AMO records of jordan+taylor and
morgan, MOSEK entries included). For the household's horizon (ages 62-92, 31 years) both curves
were identical.

### Removed: the fork's New Jersey rules (back to upstream's New Jersey)

The household dropped New Jersey as a place to live (2026-10-17), and the fork's three NJ-only
rules were used by no other state: the income-tiered retirement exclusion (NJ-1040 lines 28a-28c, a
MILP with tier binaries, its node cap and the tiers kept after a capped solve), the property tax
deduction (line 41) and the medical deduction (line 31). An NJ case now runs on upstream's NJ:
brackets and the \$1,000 personal and 65+ exemptions, with no retirement exclusion, so it overstates
NJ tax for retirees aged 62+ with NJ income up to \$150,000. With the exclusion's node cap gone,
HiGHS uses upstream's node limit and the Summary's *MIP node limit* row is upstream's; the fork's
log warnings for a MILP stopped at its time or node limit went with it. Plans in other states are
unchanged.

### New: NY STAR credit (`withSTAR`, `school_district`) (fork)

The School Tax Relief credit (Tax Law sec. 606(eee)) for a NY owner: `basic_info.school_district`
(and a move's `school_district`) names the home's municipality and school district, and the credit
applies in the years the budget has a `property tax` line. Basic while the income two years
earlier (federal AGI less IRA distributions) is at most \$500,000; Enhanced from the year an owner
turns 65 while that income is at most the Enhanced standard (\$110,750 for 2026, \$113,550 for
2027, then indexed), kept by a surviving spouse who was 62 at the death. District amounts are the
2025 final credits from tax.ny.gov (Westchester and New York City in
`data/property_tax_relief.toml`), growing 2% a year, the statutory cap. The credit is charged
against the state income tax, as it is in law: the cash flow and the SALT deduction follow, and
NY's itemized deduction subtracts it from real estate taxes (IT-196 line 6). `withSTAR = "loop"`
(default), `"optimize"` (one binary per year for the Enhanced credit; set by `breakpointMethod`)
or `"none"`; `previousSTARIncomes` gives the two years before the plan. The Taxes sheet has a
*STAR credit* column and the Summary a total.

### New: itemized deductions, federal and state (`withItemized`)

Each year deducts the larger of the standard deduction and the itemized total, built from the
expenses the plan already knows. Federally (Schedule A, P.L. 119-21): SALT, which is the budget's
`property tax` lines plus the state and local income tax the plan pays (cash basis, the same terms
the cash flow charges), capped at \$40,400 in 2026, +1%/yr through 2029 and \$10,000 from 2030, the
cap reduced by 30% of MAGI over \$505,000 (2026) before 2030; home mortgage interest from `Debts`
rows of type `mortgage` (Pub. 936 Table 1: \$750,000 of acquisition debt, \$1M for loans taken out
before 2018; a loan linked to `real estate` is a rental's and is left out); `charity` lines above
0.5% of AGI; and `medical` lines (or, in a plan without one, the `other_medical_expenses` amount
of `setMedicalExpenses`) plus Owl's Medicare Part B/D (IRMAA included) and ACA net premiums, less
the year's HSA distributions (Pub. 502), above 7.5% of AGI. Itemizers keep the
OBBBA \$6,000 senior bonus and lose the 65+ additions; non-itemizers also deduct up to \$1,000
(\$2,000 MFJ) of cash charity. After a pre-TCJA reversion (`obbba_expiration_year`) SALT is
uncapped, the mortgage limit is \$1M and the OBBBA charity rules end.

New York's own itemized deduction (IT-196, 2025): property tax without a cap, charity, medical
above 10% of federal AGI, mortgage interest under the \$1M limit, state and local income taxes left
out, and the line 46 cut (up to 25% of the deduction between NYAGI \$200,000 and \$250,000 MFJ;
\$100,000-\$150,000 single). New York lets a filer itemize whether or not the federal return
itemizes. Data: `itemized` entries in `taxes_state.toml`.

`withItemized = "loop"` (default) or `"none"` (the standard deduction everywhere, federal and
state, as before). The branch (itemize or not) and which side of each floor an amount is on come
from the previous iteration of the self-consistent loop, as do the floors, the SALT phase-down and
the NY cut: itemizing adds rows on existing columns, never a column or a binary, and a year that
never itemizes leaves the plan exactly as `"none"` builds it. The loop's lag shows in the plan:
a warning when a year takes the smaller deduction, and the *itemized*, *state itemized* and
*state medical* entries of `fixedPointResidual`. Not modeled, reported as warnings: the 2/37
limit in the 37% bracket and Pease after a reversion. Not modeled: AMT, other Schedule A items,
NY's rules above \$525,000. Results: Taxes sheet columns and Summary lines when nonzero;
`plan_metrics` keys `itemized_deductions_today` and `state_itemized_today`.

### New: `medical` and `charity` budget types

Two Budget line types for the deductions above. `care` stays non-deductible (assisted-living room
and board is not a medical expense unless care is the main reason): use `medical` for deductible
care. `Budget.by_type(..., essential=)` filters by tier.

### New: budget lines can follow an age clock; a JSON budget file

A Budget line's `clock` is `calendar` (default; `year` / `end`) or `age`: `start_age` / `end_age`
against `index`. Age-tied lines — travel "while we are able", care "from 80" — stay with the age
that causes them, so a longer life still includes them. Growth counts from the first year the line
pays. `index` `younger` (default) or `older` is a household line: that spouse's age while both are
alive, the survivor's after the first death (an `older` line can resume when the survivor reaches
its range). A person's name makes a personal line, which ends at that person's death.

`optimization_parameters.budget_file` points at a JSON budget profile (`schema_version` 1, the
same lines as the sheet, amounts in today's dollars like the sheet). It feeds the Budget sheet's
DataFrame, so one evaluator serves both; the workbook sheet wins when both are present. Refused
rather than read loosely: unknown fields, an unknown schema_version, a `type` outside the sheet's
list, numbers given as text, flags other than true/false, fractional years. `kind` is free text
kept with the line (also an optional sheet column). Lines read from the file are not written to the
HFP by `saveHFP` (or the MCP export), so the file stays their only source; reading a workbook makes
its Budget sheet the source again. The web interface does not read the file: it keeps its name when
saving the case, and a plan whose only lines are in an unread file says so when it is solved.
Owl-budget and MCP can hand lines over without writing Excel.

### Changed: the smile starts at an age of the younger spouse

`optimization_parameters.smile_start_age` (UI: *Smile starts at age (younger spouse)*) is the
younger spouse's age (calendar year minus birth year) when the smile starts; it replaces
`smile_delay`, which counted years from the current year and so moved the curve one year later,
relative to the household's ages, each year the same case was run again. A case with only
`smile_delay` is read with the delay turned into an age once (today's age plus the delay), so no plan
changes on the day of the upgrade; saved again, it carries the age. Owl also writes the equivalent
`smile_delay` (never negative) for readers that only know the delay. Reading a smile case without
`smile_start_age` warns, naming the age to add. The curve follows the younger spouse's age and, after
the first death, the survivor's: if the younger spouse dies first, it jumps ahead by the age gap
(of the example cases, only `Case_avery+quinn`, three years apart). An age earlier than today's
starts the plan partway through the smile (`gen_spending_profile` takes a negative `delay`). MCP
tools keep their `smile_delay` argument, read as years from the day of the call.

### Changed: the smile's period no longer follows the plan's length

The smile's cosine used to stretch one period over the plan's length (`span = N_n - 1 - delay`), so
a longer life widened the go-go years and moved the slow-go dip later. It now covers a fixed
`SMILE_SPAN` of 30 years from the start of the smile (plan start plus `smile_delay`); extra years
take the late-life rise instead of stretching the curve. At `N_n = 31` and `smile_delay = 0` the
curve is exactly the old one (`span` overrides the span and recovers the old curve when it equals
`N_n - 1`). The dip sits at `SMILE_SPAN/2` years after the smile starts on any horizon. Flat and
`"budget"` profiles are unchanged. `Case_jack+jill`'s expected basis moved with the shape (33-year
horizon); `Case_joe` (31 years) did not. The AMO references of the three smile cases that moved
(jack+jill +0.9%, jordan+taylor -2.0%, morgan +3.3% basis) were re-recorded with HiGHS; their MOSEK
entries were removed rather than left stale.

### New: essential budget lines (a spending floor)

A *Budget* line can be marked `essential` (optional column; blank means no). Essential lines are paid
at their amounts whatever the spending level, and only the other, discretionary lines scale: net
spending each year is the essential lines plus k times the discretionary ones. `maxSpending` maximizes
k, shown in the summary as *Discretionary spending (share of budget)* and in `plan_metrics()` as
`discretionary_scale`; a plan that cannot pay the essential lines is infeasible, which stochastic
spending and lifespan sampling count as a full shortfall. Under `maxBequest`, `netSpending` must cover
the essential lines; at exactly that amount nothing discretionary is spent, and the bequest is what
remains above the core. In the LP the profile rows become affine, with `spendingSlack` on the
discretionary part only; no binaries, and a budget without essential lines gives the plan it gave
before. Upstream's cost-function point on #175 (core versus discretionary spending).

### New: a budget spending profile

`spending_profile = "budget"` builds the spending profile from the lines of an optional *Budget*
sheet in the HFP workbook: core spending, rent, property tax, insurance, maintenance, a car, travel,
care, ..., each with a first and last year, an annual amount in today's dollars, a real growth rate
and the share a survivor keeps (by default the case's survivor percentage, and all of it for housing
costs). The profile is the lines' sum divided by its first year, so the optimizer and the LP are
unchanged: budgeting stays outside the optimizer, as upstream suggested on #175. With `maxBequest`,
net spending unset or 0 means the budget's first-year total (another amount scales the budget); with
`maxSpending`, the whole budget scales.
Renting and buying are compared with one budget per variant at a fixed spending level. The results
workbook has a *Budget* sheet that splits net spending along the lines. A *Housing* sheet (this
fork's first, ledger form, whose costs were paid outside net spending) is read as budget lines; at a
fixed spending level the two give the same plan.

### New: New York benefit recapture

Above \$107,650 of New York AGI, New York takes back the benefit of the lower brackets: the tax is the
bracket tax plus a supplemental amount that phases in over \$50,000 of AGI, tier by tier, until the
whole taxable income is taxed at the rate of its top bracket. For a married couple that is
about 0.7% more at the margin from \$107,650 to \$157,650 of AGI and 1.6% more from \$161,550 to \$211,550, and it was missing. It is
data (`recapture_agi_start`, `recapture_width`, `recapture_until` in `taxes_state.toml`) with the rule
in `tax_state.state_recapture`, whose tier amounts reproduce every constant on the 2025 IT-201-I
tax computation worksheets. The amounts follow from the brackets, so they use the 2026 rates without
another edit; the 2026 worksheets are not published yet.

The recapture enters as a self-consistent-loop quantity, like the NIIT: the LP is charged its amount
but does not see its marginal effect, so a Roth-conversion schedule is not steered away from the
phase-in range. `Plan.st_recap_n` gives it by year; it is included in `st_T_n`, and a Yonkers
surcharge applies to it. The fixed-point residual reports a `state recapture` family. The tax also
jumps when taxable income crosses a tier threshold while AGI is inside that tier's phase-in, exactly
as the worksheets compute it. The flat 10.9% above \$25M of AGI is not modeled.

### New: local income tax (`basic_info.locality`)

`locality = "NYC"` or `"Yonkers"` adds New York City's resident income tax (four brackets on New York
taxable income) or the Yonkers surcharge (16.75% of net New York tax). The tax appears inside the
state-tax figures, and `Plan.lt_T_n` gives the local part. Localities are data in
`data/taxes_local.toml`, whose header explains how to add one; a flat rate above a threshold is just
two brackets. Wage-only local taxes do not belong there. The NYC rates and thresholds and the Yonkers
rate were checked against the 2025 IT-201-I (2026 not yet published; the Yonkers rate is unchanged in
the 2026 withholding tables).

### Changed: several moves and a locality on top of upstream's change of state (#159)

Upstream 2026.10.6 models one change of state (`basic_info.moves`, `Plan.setStateTax(state, moves)`,
per-year state parameters). The fork keeps its own extension of the same model: any number of moves,
each optionally naming a `locality` (`moves = [{year = 2032, state = "NJ"}]`, or
`{year = 2030, state = "NY", locality = "Yonkers"}` for a move within the state), and a move may
stay in the state if it changes the locality. The residence in force on December 31 governs the
whole year. Plan attributes, the per-year flags (`st_conv_n`, `st_tax_ss_n`, `st_fed_sd_n`,
`st_senior_bonus_n`, `st_pension_eligible_n`) and `_states_n()` follow upstream's names. The web UI
uses upstream's move toggle for the first move, with a city selector, and keeps any further moves
from the case file as they are. The explanation reports the first move as upstream's `move` and,
when there are more, all of them in `moves`.

### Changed: state indexing and exemptions now come from upstream (#157)

The fork's single `indexed` flag and its New Jersey exemption data are replaced by upstream's
2026.10.3 fields (`brackets_indexed`, `deduction_indexed`, `exemptions_indexed`, and the per-filer
exemptions and credits below). Fork-only amounts follow the matching flag: New York's recapture
thresholds index with the brackets.
A personal credit offsets the state tax including recapture, and a local surcharge applies to the
tax after the credit. The `StateTaxParams` dataclass carries the credits as `credit_n`, so a move
takes the new state's credits from its year.

### Changed: `st_taxParams` and `st_schedule` return a `StateTaxParams` dataclass

Upstream's nine-element tuple (`st_taxParams`) and dict (`st_schedule`) are replaced by a frozen
dataclass with named fields, which also carries the fork's recapture and itemized-deduction arrays. Its flag
fields carry upstream's dict keys (`conv_n`, `tax_ss_n`, ...); `conv_n` holds upstream's three-valued
conversion treatment (`"exemption"`, `"taxed"`, `"excluded"`, #203) per year.

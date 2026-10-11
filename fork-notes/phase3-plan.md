# Phase 3 plan: where we are, what we learned, and deductions redefined (2026-10-10)

Fork-only planning note. Written on `claude/eager-cray-s0fvks` (= `main` = `claude/phase2-housing`
`066b8d6`; upstream `dev` `d6970b2` fully merged, nothing newer on `upstream/dev` or `main` as of
this session's fetch).

Sources used for this note, and what each claim rests on:

- **Verified this session** against primary text: P.L. 119-21 (govinfo.gov) sections 70108, 70111,
  70120, 70424, 70425; 2025 Form 1040 instructions (line 13b, Schedule 1-A) and 2025 Schedule A
  instructions (irs.gov); Pub. 936 (2025); Rev. Proc. 2025-32 sec. 3.14; IT-196-I (2025,
  tax.ny.gov); NJ-1040 instructions (current, nj.gov) line 31; nj.gov Stay NJ and ANCHOR pages
  and tax.ny.gov STAR eligibility page (fetched 2026-10-10). uscode.house.gov is blocked (403).
- **Measured this session**: `fork-notes/model-review/itemized_probe.py` (output
  `itemized_probe_2026-10-10.txt`) and a check of the NJ deduction under essential lines (§3.3).
- **Read in code**: everything cited by file and function.
- **Recalled, not verified** where marked.
- The original roadmap (`myfiles/requirements.md`, not in the repo) as pasted by the user on
  2026-10-10.

---

## 1. Where we are against the original roadmap

| Phase | Original intent | What happened | State |
|---|---|---|---|
| 0 Baseline case | Real `Case_us.toml` + HFP; scenarios via `owlcli compare` | Templates, HFP generator and scenario commands in `fork-notes/phase0/`, checked with placeholders | **Real case never filled or run.** Every stake measured so far is on synthetic couples |
| 1 State/local tax | AGI base, non-indexed NY, recapture, local layer, typed params, SC registry | All done; AGI base and non-indexing taken upstream (#157); recapture optimize dropped after measuring zero regret | Done |
| 2 Housing | `Recurring Expenses` sheet with `tax_tag`; property tax as a rate on assessed value per locality; transfer taxes; senior relief (STAR, SCHE, Stay NJ, ANCHOR, Senior Freeze) as income-gated credits | Ledger built, then replaced after #175 by a budget spending profile (Phase 2b) and Track B (age clocks, JSON, age-anchored smile). Property tax is an amount the user enters; transfer taxes are big-ticket items; **senior relief not modeled** ("enter the net amount") | Done as redefined; relief dropped without measurement (§3.4) |
| 3 Itemized deductions | max(standard, itemized); SALT, mortgage interest, medical; loop default + binary optimize; NY itemized; senior bonus kept | Not started | This plan |
| 4 Healthcare cost | OOP line with medical inflation and age curve; Medigap vs Advantage; NY community rating; LTC shocks | Partly covered by Budget lines (`care` type, age clocks, own `rate`); no NY ACA rating, no Medigap choice | Not started |
| 5 Part-time / earnings test | Earnings test in `socialsecurity.py`; TOML work plan | Not started; scenario 4b works around it | Not started |
| 6 Sweep and report | `owlcli sweep`, robustness, `maxMAGI`, dashboard | `owlcli compare` only; maintainer's "ladders" / MCP sweeps on the Owl-budget side | Not started |
| 7 NJ specifics | Exclusion, exemptions, property tax deduction | Exclusion (MILP), exemptions (upstream), line 41 deduction done | Done |

Two things this table makes plain:

1. **The decision engine has never run on the decision.** Phases 1, 2 and 7 were each justified by
   stakes on a synthetic couple. The household's own numbers (property tax of the homes they would
   consider, whether a mortgage is on the table, expected income in retirement) decide which of the
   remaining pieces matter. The probe below shows how strongly Phase 3's value depends on them.
2. **Phase 2's redefinition dropped a piece that may be larger than Phase 3** (NJ senior relief,
   §3.4).

## 2. Lessons from the interactions with the maintainer

Each with the evidence it rests on (PROGRESS.md "Upstream" table unless noted).

1. **He implements from issues; he does not merge our PRs.** #149, #155, #157, #161-169, #173,
   #174, #176 were all implemented by him, with credit. A patch is evidence, not a delivery.
2. **He often solves the problem with another design than ours, usually broader.** #173 (a
   `property` link instead of our `payoff` year: "a typed year drifts"), #174 (all six mode options
   normalized, not our one validator), #176 (percent-formatted cells only), #159 (one move, no local
   tax), #161 (crossing found on the sliding scale). Consequence: send the problem and the evidence
   first, keep our code shaped so it can be dropped for his (the fork has done this at every merge).
3. **Scope boundary on states.** #160: state taxes stay a pure LP upstream. #175: no more state-tax
   plumbing. #159: he wants "equivalence of all variables between states and no lookup between
   years" before folding more in. So **every state rule in Phase 3 is fork-only**; only federal rules
   are candidates upstream.
4. **Federal rules with phase-outs are in scope, as an opt-in optimize mode.** The closest precedent
   is his own `withSeniorBonus = "loop" | "optimize"` (`d6970b2`, 2026-10-09): a federal deduction,
   loop by default, a binary per year in optimize mode, binaries in `localsearch.ALWAYS_FREE`.
   Federal itemizing should copy that shape.
5. **One model.** #170/#171 (envelope model, pinned loop) were declined as a second model; his
   answer to loop sub-optimality is local search. New machinery must be rows in the one LP, and
   every new binary block must be known to local search.
6. **Inputs: link existing tables, avoid free-floating years.** #173's `property` column. So:
   mortgage interest comes from the `Debts` rows he already has, not from a new input; deductible
   amounts come from Budget line types, not a new sheet.
7. **Budgeting lives outside the optimizer, in Owl-budget, which he owns for now** (#175, third
   answer). Which budget lines are deductible is part of that contract. Adding line types in the
   fork is fine; proposing them upstream is a contract question for the #175 Discussion, not an
   issue with a patch.
8. **Discussions start at the concept level.** The measured #175 third reply was superseded by a
   conceptual one at his pace. Measurements support a proposal; they do not open one.
9. **He adopts well-evidenced findings quickly** (local search reply: all three points adopted in
   `785217c`), and some issues get no reply (#158 since 2026-10-06). Don't stack requests on an
   open one.

## 3. New evidence gathered for this plan

### 3.1 Rules (verified unless marked)

Federal (P.L. 119-21; IRS instructions):

- SALT cap (sec. 70120, IRC 164(b)(7)): $40,000 in 2025, **$40,400 in 2026**, then +1%/yr through
  2029, **$10,000 from 2030**. Before 2030 reduced by 30% of MAGI over $500,000 (2025), $505,000
  (2026), +1%/yr after, never below $10,000. MAGI = AGI + foreign exclusions (= AGI here).
  Schedule A 2025 worksheet confirms the mechanics.
- Mortgage interest: the $750,000 acquisition-debt limit is made permanent (sec. 70108); Pub. 936
  (2025): $750,000 ($375,000 MFS), $1M for debt before 16 Dec 2017; mortgage insurance premiums count
  as interest from 2026 (sec. 70108(a)(1)(D)).
- Overall limit (sec. 70111, new IRC 68): itemized deductions cut by 2/37 of the lesser of the
  itemized amount or taxable income above the start of the 37% bracket, from 2026. Irrelevant below
  the 37% bracket.
- Charity from 2026: non-itemizers deduct up to $1,000 ($2,000 MFJ) (sec. 70424); itemizers only
  above 0.5% of the contribution base (sec. 70425).
- Medical: above 7.5% of AGI; Medicare Part B and Part D premiums and qualified long-term care
  services count (Schedule A 2025 instructions).
- **The senior $6,000 deduction is kept by itemizers** (Form 1040 line 13b, Schedule 1-A: "you can
  claim these deductions if you take the standard deduction or if you itemize"); the 65+ additional
  standard deduction ($1,650 per person MFJ in 2026, Rev. Proc. 2025-32 sec. 3.14) is part of the
  standard deduction and is lost by itemizers.
- AMT: Owl does not model it (grep for "alternative minimum" / `amt` in `src/owlplanner` finds
  none). SALT is an AMT add-back; at this household's income it is unlikely to bind (recalled, not
  computed).

New York (IT-196-I 2025):

- **Itemizing on NY is allowed whether or not one itemizes federally.**
- NY itemized starts from Schedule A computed under the IRC as before TCJA: **state and local
  income taxes are subtracted (line 41, item A), real estate taxes are not capped** ("not subject to
  this federal limit"), mortgage limit $1M (+$100k home equity).
- NYAGI over $100,000: itemized deduction adjustment (line 46). For MFJ the worksheet's start is
  $200,000 and the cut is 25% x min(NYAGI - start, 50,000)/50,000 of the deduction (Worksheet 3; the
  filing-status-to-amount mapping on line 2 is garbled in the PDF text: single/MFS $100,000, HoH
  $150,000, MFJ $200,000 is my reading, to confirm on the form image). 50% above $525,000, other
  rules above $1M: out of this household's range. *(Confirmed 2026-10-11: pypdf's layout mode
  gives the filing-status circles as private-use glyphs U+F081/F083 -> $100,000, U+F084 ->
  $150,000, U+F082/F085 -> $200,000, i.e. statuses 1/3, 4, 2/5.)*
- **Medical: above 10% of federal AGI** (IT-196 (2025) form, line 3: "Multiply line 2 by 10%
  (0.10)", line 2 = IT-201 line 19, federal AGI). Not the federal 7.5%. *(Added 2026-10-11 in the
  step 2 review; step 2 had shipped 7.5.)*
- Property tax credits/rebates reduce the real estate taxes deducted (lines 5-7).
- NY standard deduction MFJ $16,050, not indexed (`taxes_state.toml`).

New Jersey: no itemized deductions; **line 31 medical expenses above 2% of NJ gross income**
(NJ-1040 instructions, Worksheet F). Line 41 property tax deduction already modeled.

### 3.2 First-order stakes (probe, not a model)

`fork-notes/model-review/itemized_probe.py`: the Phase 1 synthetic couple ($1.5M tax-deferred,
`maxBequest`, budget = $80k core + $25k property tax, exact LP), solved with the standard deduction
as Owl does today; then, year by year with income held fixed, the deduction is recomputed as
max(standard, itemized) and the tax saved read off the plan's own brackets. No LP response, no
Medicare premiums (exact LP), so a lower bound. Lifetime, today's $:

| Case | Federal, statutory law | Federal, Owl's default (pre-TCJA from 2032) | NY + Yonkers, statutory | NY + Yonkers, 2032 default |
|---|---:|---:|---:|---:|
| Yonkers owner, $25k property tax | **0** (0 yrs) | 22,431 (25 yrs) | **22,068** (31 yrs) | 10,009 |
| same + $600k mortgage at 6.5% | 17,977 (9 yrs) | 93,100 (31 yrs) | 34,168 | 25,954 |
| NJ owner, $25k property tax | **0** | 21,449 | – | – |
| NJ owner + $600k mortgage | 15,735 (9 yrs) | 87,801 | – | – |

Reading:

- **Without a mortgage and under the law as written, federal itemizing never wins** for this
  couple: $25k property tax + ~$5k state tax stays under the $32.2k-38.6k standard deduction in
  2026-2029, and the cap is $10k from 2030.
- **NY itemizing wins every year** for an owner with property tax above $16,050 (and grows, because
  NY's standard deduction is not indexed while the property tax line is). Worth ~$10-34k lifetime.
  Today the fork models NJ's property tax relief (line 41) but not NY's, so **the NY-vs-NJ owner
  comparison is biased toward NJ** by an amount of this order (the 2026-10-07 NJ-minus-NY owner
  difference was +$62,830 exact / +$46,703 LS at $20k property tax).
- **Federal itemizing matters with a mortgage** ($16-18k statutory) and **a lot under Owl's
  2032 reversion** ($88-93k), because pre-TCJA itemizing has no SALT cap. That is the cash-vs-mortgage
  question of Scenario 5, where the earlier made-up comparison had cash ahead by ~$280k of bequest:
  the deduction narrows it, it is unlikely to reverse it at those inputs (inferred from magnitudes,
  not run).
- **Medical** was not probed (Medicare off). Medicare B+D premiums alone are under the 7.5% floor at
  this income (recalled amounts); it matters with `care`/medical budget lines (Phase 4's LTC years).

### 3.3 A bug found while planning: NJ deduction under essential budget lines

`processDebtsAndFixedAssets` sets `st_ptd_share_n` = (property tax + 18% rent) / total budget, and
`_add_property_tax_deduction` bounds `st_pt_n <= share_n * g_n`. With essential lines,
`g_n = E_n + k D_n`, so the bound is wrong whenever k != 1. Measured (NJ couple born 1975, essential
core $50k + property tax $12k, discretionary travel $38k, exact LP):

| Objective | k | Bound share x g | Property tax paid | Claimed |
|---|---:|---:|---:|---:|
| `maxSpending` | 1.137 | 12,625 | 12,000 | 12,625 |
| `maxBequest`, netSpending 80 | 0.474 | 9,600 | 12,000 | 9,600 |

Fix: express each line type's amount as an affine function of `g_n`, essential part constant and
discretionary part scaled (§5, step 1). Phase 3 needs exactly that helper for SALT, charity and
medical, so the fix comes first.

### 3.4 Senior property-tax relief, dropped in Phase 2, is large and income-tiered

Verified on nj.gov (Stay NJ page, updated 2026-08-20): Stay NJ pays homeowners 65+ who owned and
lived in the home the whole year; for the 2025 tax year (paid 2027) the maximum benefit is
**$6,500 for income up to $100,000, $5,000 to $150,000, $4,000 to $200,000, $0 above**. The FY2027
act cut the 2026 payments mid-year ("a lower overall benefit for calendar year 2026"), and the
tiers are stated "assuming no changes to the Stay NJ Program in the FY2028 budget". ANCHOR:
homeowners with NJ gross income up to $250,000, renters up to $150,000 (amounts not on the fetched
page; not verified). How Stay NJ computes the benefit below the maximum (recalled: 50% of the
property tax bill, less other relief) and which income it uses were not on the fetched pages.

Enhanced STAR (tax.ny.gov): 65+, income up to $110,750 for 2026 benefits ($113,550 for 2027),
where **income = federal AGI minus the taxable part of IRA distributions**, from the tax year two
years earlier. Conversions and IRA withdrawals do not count, so for this household it is close to
a fixed amount; entering property tax net of STAR (as the notes already say) is adequate.

Reading: at up to $4,000-6,500 a year, Stay NJ is an order of magnitude larger than any NY-vs-NJ
income-tax difference measured so far (NJ minus NY $430-1,006/yr under local search and the
exact LP), and it has income cliffs at $100k/$150k/$200k,
the same shape as the NJ exclusion that the fork already solves as a MILP. It is also the least
certain number in the comparison (annual appropriations).

### 3.5 Owl's default reverts federal tax law in 2032

`Plan.yOBBBA = 2032` (`plan.py:516`), schema default `obbba_expiration_year = 2032`, and all 18
upstream example cases set 2032 explicitly. From that year Owl uses pre-TCJA brackets and standard
deduction. P.L. 119-21 made the TCJA rates and standard deduction permanent (verified for the SALT
and mortgage sections; the rate sections not reread), so 2032 is the maintainer's speculation, not
law. The household template (`fork-notes/phase0/Case_us.template.toml`) does not set it, so it
inherits 2032. The probe shows the setting moves the plan well before 2032 (the optimizer front-loads
income: 2028 ordinary taxable income $48,581 under statutory law vs $106,524 under the 2032
default, same case) and multiplies the federal value of itemizing by 4-5. This is a modeling choice
for the user (§7, D1), and it matters more than most of Phase 3.

---

## 4. Phase 3 redefined

Old title: "Itemized deductions (federal + NY)". New framing: **deductions follow the expenses that
cause them**: an expense in the budget or in Debts lowers taxable income through whichever deduction
the law gives it, chosen by the optimizer when the choice depends on the plan.

| Part | Content | Where it lives | Value for the household (from §3) | Order |
|---|---|---|---|---|
| 3.0 | Per-type budget amounts as affine functions of `g_n`; NJ `st_pt` fix; mortgage interest from Debts | fork (helper upstreamable with the budget) | prerequisite; fixes a live bug | 1 |
| 3.1 | **NY itemized deduction** (property tax uncapped, mortgage, charity, medical; income taxes excluded; NYAGI adjustment) | fork only | ~$10-34k lifetime for a NY owner; removes the NY/NJ owner bias | 2 |
| 3.2 | **Federal itemized deduction** (SALT incl. Owl's own state/local income tax, mortgage interest, charity, medical) with max(standard, itemized), senior bonus kept | fork, then design note upstream | $0 (no mortgage, statutory) to ~$90k (mortgage, 2032 reversion) | 3 |
| 3.3 | Medical floors (federal 7.5%, NJ line 31 2%) wired to `medical`/`care` lines and Owl's Medicare premiums | fork (federal part with 3.2) | small now; large in LTC years (Phase 4) | 4 |
| 3.4 | NJ senior relief (Stay NJ) | fork; **scenario lever first, code only if needed** | up to $4-6.5k/yr, policy risk | decide (D3) |

Out of scope, documented: AMT; the 2/37 overall limit (warn if an itemizing year reaches the 37%
bracket); SALT MAGI phase-down handled in loop mode only (warn above the threshold); NY rules above
NYAGI $475k; NYC household/school credits; car-loan interest (Schedule 1-A); Pease after a pre-TCJA
reversion (warn); part-year residency; state conformity of other states' itemizing (data key is
generic, only NY's values verified).

---

## 5. Implementation plan

Conventions throughout (CLAUDE.md): one LP, order-1 coefficients (divide dollar rows by a
reference amount), never the same column twice in a row, every new binary block in
`localsearch.FAMILIES` or `ALWAYS_FREE`, any node cap a new binary block needs set in
`Plan._node_limit` (the one place since the upstream 2026.10.10 merge, so the Summary's node rows
report it, §9), every new "at most" bound on a tax benefit covered by the
tie check, anything `processDebtsAndFixedAssets()` reads initialized in `Plan.__init__`, compare
variants the same day, full suite before calling a commit green.

### Step 0: decisions (done 2026-10-10, §7)

- D1: statutory base. The template now sets `obbba_expiration_year = 2066` (any year after the
  plan's last year means no reversion; the UI accepts at most this year + 40, so not the code's
  2099 sentinel); the 2032 reversion is a sensitivity run in `phase0-scenarios.md`.
- D2: no household inputs in this environment; the finished product runs on them locally. So the
  build order rests on the synthetic evidence of §3.2, and every piece must report its own value on
  the user's case: per-year deduction choice and amounts in the results (steps 2-3), and an
  `owlcli compare` recipe with `withItemized` on and off (step 7) that answers "does this matter
  for us" locally, without sending numbers anywhere.
- D3-D5 as recommended.

### Step 1 (3.0): shared plumbing and the `st_pt` fix — size S

1. `budget.py`: `Budget.by_type(*types, essential=None)` (None = all lines, True/False = one tier).
   New types `"medical"` and `"charity"` in `BUDGET_TYPES` (survivor default: the case's %);
   `"care"` stays non-deductible by default (assisted-living room and board is not medical unless
   care is the main reason; recalled), documented with "use `medical` for deductible care".
   Docs: Documentation.py Budget table, PARAMETERS, JSON schema in `budget.py`.
2. `Plan._budget_amount_terms(types)` -> `(const_n, coef_n)` with
   amount_n = const_n + coef_n * g_n, nominal $:
   - no essential lines: const = 0, coef = by_type/total (today's behaviour);
   - essential lines: coef = by_type(essential=False)/D_n, const = gamma_n * (by_type(essential=True)
     - coef * E_n) (so amount = essential part + share of the discretionary part of g_n - E_n).
   Initialized in `__init__`, computed in `processDebtsAndFixedAssets()` next to `st_ptd_share_n`.
3. `_add_property_tax_deduction`: row `st_pt - coef*g <= const` from the helper; `st_ptd_share_n`
   kept only as the "any deductible line" flag. Regression test = §3.3's two cases (claimed equals
   paid when the cap does not bind).
4. `debts.py`: `get_mortgage_interest_array(debts_df, N_n, thisyear, payoffs, fixed_assets_df)` ->
   interest paid per calendar year and average balances `(3, N_n)` by Pub. 936 Table 1 category
   (grandfathered / before 2018 / after 2017, from the loan's `year`), for `type == "mortgage"`
   rows not linked to a `real estate` asset (a rental's interest is Schedule E): payments in the
   year minus the fall in balance (same amortization as `get_debt_payments_array`; the payoff year
   pays principal only). `Plan.mortgage_interest_n`, `Plan.mortgage_balance_cn` set in
   `processDebtsAndFixedAssets()`, zeros in `__init__`. Deductible interest per year =
   interest x min(1, qualified loan limit / total balance), the limit from Table 1 lines 1-11
   (`tax_federal.qualified_loan_limit`; `pre_tcja=True` gives the $1M rule for a pre-TCJA
   reversion and for NY). *(Revised after review, 2026-10-10: the first version kept one aggregate
   balance and a per-loan limit, which cannot combine loans of different categories; Pub. 936
   (2025) Table 1 verified on irs.gov.)*
5. `tax_federal.py`: `salt_cap(year, magi, yOBBBA)` (schedule above, `inf` from `yOBBBA`),
   `qualified_loan_limit`, `deductible_mortgage_interest`, constants `MORTGAGE_LIMIT`,
   `MORTGAGE_LIMIT_LEGACY`, `MEDICAL_FLOOR = 0.075`, `CHARITY_FLOOR = 0.005`,
   `NONITEMIZER_CHARITY = [1000, 2000]`, and `standard_without_bonus(...)` giving per year the
   standard amount without the senior bonus, the amount an itemized deduction is compared with
   (today `taxParams` folds the bonus into `sigmaBar`; same `no_bonus` call as
   `_add_standard_exemption_bounds`).
6. Tests (`tests/tax/test_itemized_data.py`): cap schedule 2025-2031 and the phase-down floor;
   interest vs a hand amortization, payoff year, the Table 1 worksheet (mixed categories), a loan
   on real estate left out; helper with and
   without essentials; JSON/HFP round trip of the new types.

### Step 2 (3.1): NY itemized deduction — size M

Data (`taxes_state.toml`, NY_MFJ and NY_Single; generic keys, documented in the header):

```toml
itemized = { allowed = true, income_taxes = false, salt_cap = 0, mortgage_limit = 1000000,
             medical_floor = 10, adjustment_agi_start = 200000, adjustment_width = 50000,
             adjustment_pct = 25 }   # IT-196-I (2025) lines 41 and 46, Worksheet 3
```

(single: `adjustment_agi_start = 100000`; confirm both on the IT-196 form image.) Parsed into
`StateTaxParams.itemized` (fork's typed params), per year like the other flags, following moves.

LP (new builder `_add_state_itemized`, called beside `_add_state_tax_bounds`; not
`@_fixedAcrossIterations` because it reads loop values):

- Years where the state itemizes (`st_item_ok_n`). Per year, a priori bounds from budget amounts:
  `LB_n` (essential property tax + mortgage interest) and `UB_n` (all deductible lines at their
  largest plausible scale + mortgage interest + medical upper bound).
  - `LB_n >= st_sigmaBar_n`: itemize fixed, no binary;
  - `UB_n <= st_sigmaBar_n`: standard fixed, no rows;
  - otherwise binary `zsi_n`.
- Variables per itemizing year: `st_ipt` (property tax claimed), `st_ich` (charity), `st_imed`
  (medical). Rows (dollar rows divided by a reference amount, as upstream does):
  - `st_ipt - coef_pt*g <= const_pt` (the property tax paid);
  - `st_imed - coef_med*g + 0.075*AGI <= const_med + medicare_n` (Owl's Medicare premiums in loop
    mode as a constant; under `withMedicare="optimize"` the LP expression);
  - each of them `<= UB * zsi` (only where `zsi` exists);
  - deduction: `st_e <= st_sigmaBar*(1 - zsi) + (1 - rho_n)*(st_ipt + st_ich + st_imed +
    mi_ny_n*zsi)` where `rho_n` is the NYAGI adjustment from the previous iterate (below).
  The current column bound `st_e <= st_sigmaBar_n` (`_add_state_tax_bounds`) is raised to the
  larger of the two in itemizing years.
- NYAGI adjustment `rho_n` = pct x min(max(NYAGI_prev - start, 0), width)/width: a bilinear term
  (rate x deduction), so loop mode, a new `_SC_PARAMS` entry `NYIR_n`, from `st_agi_n`. Lower than
  start in every probe year, so it is a safeguard here, not a driver.
- Yonkers (surcharge on net NY tax) and NYC (brackets on NY taxable income) follow automatically.
- Binaries `zsi`: in `localsearch.ALWAYS_FREE` if at most a handful per plan (expected: the a priori
  rule fixes most years), otherwise a family `"zsi"` ("state itemizing").

Reporting: `st_item_n` (claimed, 0 when standard), `st_itemizing_n` (bool); Taxes sheet columns and
Summary line only when nonzero (as recapture); `plan_metrics` key `state_itemized_today`;
`assistant/explain.py` tags; MCP explain text.

Tests (`tests/tax/test_state_itemized.py`): hand IT-196 on a fixed-income NY plan (property tax
$25k, mortgage interest, AGI under $200k: NY taxable income = NYAGI - itemized); NYAGI $225k:
12.5% cut; renter: unchanged plan and `vm` (guard); Yonkers surcharge on the reduced NY tax; NJ and
FL unchanged; a move NY -> NJ stops the deduction in the move year; constraint replay; local search
returns an integral plan; tie check (§step 4).

### Step 3 (3.2): federal itemized deduction — size L

Option `withItemized = "None" | "loop" | "optimize"` (mirror every `withSeniorBonus` hit: `plan.py`
known options and `_buildOffsetMap`, `config/schema.py`, `config/ui_bridge.py`,
`assistant/tools.py`, `utils.py` normalization, UI keys). Default: D4.

Per year n, `S_n` = standard deduction without the senior bonus (+ non-itemizer charity
min(cap, charity lines)), `B_n` = the senior bonus (loop value or `_sb_lp` terms), `MI_n` = deductible
mortgage interest.

- Candidate years: `UB_item_n > S_n` where `UB_item_n = salt_cap_n + MI_n + charity UB + medical UB`.
  With no mortgage and no medical/charity lines that is 2026-2029 only, and none when property tax +
  state tax cannot reach the standard amount. `LB >= S` fixes itemizing as in Step 2.
- Variables: binary `zi_n`; continuous `isalt_n`, `ich_n`, `imed_n` (claimed amounts).
- Rows:
  1. deduction: `e_n - isalt - ich - imed + (S_n - MI_n)*zi <= S_n + B_n`
     (under `withSeniorBonus="optimize"` this replaces `senior_bonus_deduction`:
     `e_n + k p_n - isalt - ich - imed + (S_n - MI_n)*zi <= S_n + k*SENIOR_BONUS`);
     `zi=0` gives `e <= S + B`, `zi=1` gives `e <= MI + isalt + ich + imed + B`;
  2. `isalt <= salt_cap_n * zi`; `ich <= UBch * zi`; `imed <= UBmed * zi`;
  3. SALT paid: `isalt - coef_pt*g - [state and local income tax terms] <= const_pt +
     STR_n*(1 + sur_n)`. The state terms are exactly those `_add_net_cash_flow` charges
     (`st_f` x `st_theta`(1+surcharge), `-st_c`(1+surcharge), `lt_f` x `lt_theta`): factor them into
     one helper `_state_tax_terms(n)` used by both rows, so the deduction cannot drift from the
     tax paid. Cash basis: Owl pays year n's state tax in year n, so it is deducted in year n.
  4. charity: `ich - coef_ch*g + 0.005*AGI <= const_ch`; medical: as in Step 2 with the federal
     AGI. AGI is the existing `magi` variable (`_add_magi_lp`, AGI basis, as NIIT uses it): extend
     its trigger to `withItemized="optimize"` when a floor applies.
  5. column bound of `e_n` raised to `max(S_n, UB_item_n) + B_n`.
- SALT cap phase-down: `salt_cap_n` from the previous iterate's MAGI (no binary); warn when MAGI
  exceeds the threshold. Under a pre-TCJA reversion (`year >= yOBBBA`): no SALT cap, $1M mortgage
  limit, no charity floor, Pease not modeled (warn if AGI passes its threshold, recalled amounts).
- Loop mode: the same rows with `zi_n` fixed to the previous iterate's choice (itemize when the
  itemized amount at the previous solution exceeded `S_n`; iteration 0 from budget amounts and zero
  state tax), as `_rx_fixed` does for the NJ tiers. The LP then still prices state tax against its
  deductibility inside the chosen branch. A flip of `zi` counts in the loop residual. The kink is
  continuous (both branches equal at the switch), so a 2-cycle costs little, unlike the NJ cliffs;
  measure it anyway (step 6).
- Local search: `zi` in `ALWAYS_FREE` when at most ~4 per plan (the no-mortgage case), else a
  family `"zi"`, labelled "itemizing". Decide by measurement; test both shapes.
- MIP scaling (#178, `mipScaleOrder`): coefficients `S_n - MI_n` on a binary are dollar-sized like
  upstream's big-M terms; check the scaled matrix once (`test_mip_scale` pattern).

Interactions to test explicitly: LTCG brackets (taxable income falls, so more LTCG at 0%: the rows
already read `e_n`); NIIT, IRMAA, ACA and SS taxability unaffected (deductions are below AGI; the
`magi` row must not include them); states with `standard_deduction = "federal"` still conform to the
standard amount only (no state follows federal itemizing in the data; documented).

Reporting: `item_n`, `item_salt_n`, `item_mi_n`, `item_char_n`, `item_med_n`, `itemizing_n`;
Taxes sheet and Summary (only when nonzero); `plan_metrics` `itemized_deductions_today`; plots
unchanged (taxes already shown); explain/MCP.

Tests (`tests/tax/test_itemized.py`):
- guard: no mortgage/medical/charity lines and property tax + state tax below the standard amount
  -> no new columns, same objective to the dollar (all 17 example cases unchanged);
- fixed-income hand cases: itemized above standard (deduction = itemized + bonus), below
  (standard + bonus), both spouses 65+ (the 65+ additions lost, the bonus kept), under
  `withSeniorBonus="optimize"` too;
- SALT: = min(cap, property tax + state + local income tax) on a NY and a Yonkers plan; 2030 cap
  $10k; state tax deductibility shows in the LP (the marginal cost of a conversion falls in an
  itemizing year, checked by finite difference);
- mortgage: interest by year from Debts, payoff at a linked sale (#173) stops it;
- charity floor and non-itemizer $2,000; medical floor;
- loop vs optimize: equal far from the switch, optimize >= loop at it;
- local search integral; constraint replay; tie check; pre-TCJA reversion uncapped SALT;
- `maxSpending` with essentials: claimed property tax equals paid (step 1 helper).

### Step 4: ties where cash has no price — size S

Extend the fork's tie machinery (`_exclusion_shortfall`, `plan.py:4962`, and the bracket-order
check) to the new benefits: in a year with positive taxable income, an itemizing year whose
claimed SALT/charity/medical/property tax is below what was paid, or whose `e_n`/`st_e_n` is below
its branch's bound, switches tax pricing on and re-solves. Tests: a no-bequest plan with late cash
of no value, before and after.

### Step 5 (3.3): medical floors — size S (after steps 2-3)

Federal and NY rows already exist; this step wires `medical` lines and Owl's Medicare premiums
(Part B/D + IRMAA in `M_n`; the ACA net premium `ACA_n` pre-65) into them, and adds NJ line 31
(`st_imed_nj`: medical above 2% of NJ gross income, a bounded LP variable beside `st_pt`, no binary)
in `_add_state_taxable_income`. Test: a care line of $100k/yr for three late years: federal itemizes
in those years, deduction = care + premiums - 7.5% AGI.

### Step 6: measure — size M

Rerun on the synthetic couple (the household case is run locally by the user, D2), same day,
exact LP and local search, statutory law (base, D1) and the 2032 reversion (sensitivity):

1. `itemized_probe.py` cases in-model (`withItemized="optimize"` and `"loop"`): in-model gain vs the
   first-order numbers in §3.2, and loop vs optimize gap.
2. NY owner vs NJ owner at $20k and $25k property tax, with NY itemizing (the 2026-10-07 table
   rerun).
3. Scenario 5 rent / cash / mortgage with the deduction (Scenario 5 text loses its caveat).
4. Solve times (binaries per plan, local search time) and, from the Summary rows upstream added in
   2026.10.10, the MIP nodes and the solves stopped at a node limit (§9): the measure that decides
   `ALWAYS_FREE` vs a family for `zsi` / `zi`.

Record in PROGRESS.md; raw output next to the script.

### Step 7: docs — size S

Documentation.py and PARAMETERS (Budget types, `withItemized`), modeling-capabilities (remove
"itemized deductions not modeled"), CHANGELOG (fork section), `taxes_state.toml` header (`itemized`
keys), `phase0-scenarios.md` section 5 (drop the "not modeled" caveat; add the `withItemized`
option) and the template (`withItemized`, `obbba_expiration_year` per D1).

### Step 8: upstream — after step 6

- Federal part only, at the concept level, in the #175 Discussion or a new design issue, after the
  measured stakes exist: "Owl already knows two itemizable amounts (mortgage interest from Debts,
  its own state income tax); the budget knows the rest (property tax, charity, medical). Would you
  take max(standard, itemized) in core, as `withItemized` loop/optimize like `withSeniorBonus`, with
  Owl-budget supplying deductible categories?" Lessons 2, 4, 7, 8: propose the contract, offer the
  patch on stock `dev` only if asked, expect his design.
- NY itemizing, NJ line 31, Stay NJ: fork only (lesson 3).
- Not before #158 has a reply, if the user prefers not to stack (lesson 9).

### Step 9 (3.4): Stay NJ — scenario lever now (D3), code later only if needed — size S, then M

Scenario first (no code; the recipe goes in `phase0-scenarios.md` in step 7, for the user to run
locally). Enter it through the HFP sheet, not the MCP `big_ticket_items` parameter (its sign is
reversed, §8): the expected benefit as a positive big-ticket item (or a negative-amount
budget line if allowed) from the first year at 65+, by income tier, in the NJ owner scenarios;
see whether the NY-vs-NJ ranking turns on it. Code only if the household's NJ income sits near
$100k/$150k/$200k: a tiered credit on NJ income with binaries, reusing the NJ exclusion's
disaggregated form (`_add_state_tiered_exclusion`, `zx`), after verifying the benefit formula and
the income definition on the PAS-1 instructions. Lookup between years (benefit for tax year Y paid
in Y+2) stays out: the benefit is placed in the year of the income it depends on (documented).

---

## 6. Risks

- **Binary count with a mortgage** (up to one `zi` per mortgage year): mitigated by the a priori
  fixing; measured in step 6. Fallback: loop mode.
- **The SALT row couples federal and state taxes inside one year**: no new loop quantity, but the
  state tax terms appear in two rows; the shared helper keeps them identical.
- **Upstream edits to the senior bonus rows** (`_add_senior_bonus_lp`, 2026-10-09, still moving:
  `upstream/claude/magical-archimedes-2uo16r` touches local search the same week): the federal
  deduction row replaces theirs under `_sb_lp`. Expect merge conflicts there; keep the change local.
- **Policy**: SALT schedule, Stay NJ funding and Owl's 2032 reversion are all assumptions about
  law; each is a parameter to vary, not a fact.
- **Loop noise**: any NY-vs-NJ difference under ~1% stays unresolved unless local search and the
  exact LP agree (Phase 1 rule).

## 7. Decisions (answered 2026-10-10: D1 statutory base; D2 no real inputs here, the product runs
locally on them; D3-D5 as recommended)

- **D1. Federal law after 2031.** Owl's default reverts to pre-TCJA in 2032; the law as enacted does
  not. Recommended: base case `obbba_expiration_year` far in the future (statutory), the 2032
  reversion as a sensitivity run. Changes every scenario, not only Phase 3.
- **D2. Phase 0 before or after Phase 3.** Recommended: at least step 0's household inputs before
  step 2, so the order 3.1 > 3.2 > 3.4 is confirmed on real numbers; the full baseline can follow.
- **D3. Stay NJ.** Recommended: as a scenario lever now (no code), code only if the household's NJ
  income is near a tier boundary.
- **D4. Default of `withItemized` in the fork.** Recommended: `"optimize"` in the household's case
  files (exact, few binaries), upstream-style default `"loop"` in code when deductible inputs exist,
  `"None"` reproducing today's plans.
- **D5. Medical in Phase 3 or Phase 4.** Recommended: rows in Phase 3 (they share the AGI floor
  machinery), the healthcare cost model itself in Phase 4.

## 8. Upstream issue on MCP `big_ticket_items` (filed by someone else; checked 2026-10-10)

**Resolved upstream** in 2026.10.10 (`6deb074`, "Refs #180", merged here 2026-10-10): the amounts
stay signed, negative = expense, as in the HFP; only the MCP docstrings, the intake prompt and
`info/mcp.md` changed. The fork takes it as is. The text below is the check that preceded it.

Claim: the MCP helpers (`_build_plan_from_params`, `save_case` in `assistant/tools.py`) add
`annual_amount` to `Lambda_in` with its sign, the docstrings call the items "extra expenses that
reduce the spending budget" with positive examples, and the cash-flow row (`_add_net_cash_flow`)
treats a positive `Lambda_in` as an inflow, so a documented expense raises spending.

Checked on this branch (fork code identical to upstream `dev` `d6970b2` in these lines):

- Code: `tools.py:1106-1116` adds the amount; the comment says "positive = extra expense";
  docstrings at `tools.py:1577`, `3218`, `4539`, `4836`, `5172` describe expenses with positive
  examples. `_add_net_cash_flow` adds `Lambda_in` to the right-hand side with wages and SS
  (`plan.py:3812-3820`). The HFP convention is the opposite of the docstrings: signed column,
  negative = outflow (`hfp_io.py:299`; `save_case` writes `Lambda_in` as is, `hfp_io.py:689`).
- Run (the MCP test helper's single person, TX, `maxSpending`, exact LP, 5-year item):
  no item 84,352; `annual_amount = 25,000` -> **90,832**; `-25,000` -> 77,864 (year-1 net spending).
  So the direction is confirmed. The issue's "increases by ~$25k/yr" is not what happens for a
  multi-year item under a profile: the windfall is spread over the plan (+$6,480/yr here).
- MCP test `test_big_ticket_items_populate_lambda_in` asserts only the stored value, as the issue
  says.

Effect on us: none on the paths the fork uses (HFP workbooks, TOML, `owlcli`, the UI: all signed,
negative = expense; the fork's notes and scripts use negative amounts). It does affect anyone, the
user included, who drives Owl through the MCP assistant locally: an assistant following the
docstrings enters expenses as income, and a case saved that way carries the wrong sign into its
HFP. Until upstream decides (its fix will define the sign), enter expenses through the HFP, or pass
negative amounts to the MCP and check the saved HFP. Fork fix not made: the maintainer has not
confirmed which option he wants, and we take his fix when it lands (CLAUDE.md, Syncing).

## 9. Upstream 2026.10.10 merged (2026-10-10): effect on this plan

Merged upstream `dev` `f41fcdc` (six commits after `d6970b2`; `main` = `dev`). Read in the diff:

- `6deb074`, `da85e43`: #180 settled as signed amounts (§8). No code change.
- `3a1285b`, `514c0ab`, `f41fcdc`: branch-and-bound node counts in the Summary (*MIP nodes*, *MIP
  node limit*, *Local search step node limit*, *MIP solves stopped at node limit*); the solver option
  `mipMaxNodes` becomes public (HiGHS default 1,000,000 nodes, MOSEK none); local-search steps are
  flagged (`_localSearchStep`) and tallied apart.
- `bad669a`: UI finds a MOSEK license at `~/mosek/mosek.lic`. No effect.

Interaction with fork code, resolved in the merge:

- The fork's NJ-exclusion cap (`RX_NODE_LIMIT`, 20,000 HiGHS nodes when neither `maxTime` nor
  `mipMaxNodes` is given) now goes through `Plan._node_limit`, which falls back to upstream's
  `_mipNodeLimit`. Upstream's tally used its own limit, so a solve stopped at the RX cap would not
  have counted as stopped at the limit (checked: the RX node-limit test reads 0 of N without the
  fix). The Summary's *MIP node limit* row adds "20,000 on the exclusion-tier MILP" when that cap
  applied; before, it would have shown only 1,000,000.
- The fork's node-limit warning was silenced whenever `mipMaxNodes` was set (it used to mean a
  local-search step). It now stays silent only for local-search steps, and a user's `mipMaxNodes`
  cut-off is reported with "Raise mipMaxNodes". It reads the last run's own status
  (`kSolutionLimit`) and count, not the sum over HiGHS's infeasibility retries.
- The SC-loop trace keeps the fork's `_SC_PARAMS` registry; upstream's per-iteration `nodes` entry
  is added beside it.

Effect on Phase 3: none on the tax content. Steps 2-3 inherit node counting for `zsi` / `zi` for
free; any cap they need goes in `_node_limit` (§5 conventions); step 6 measures with the new rows.

# Phase 5 plan: work, part-time work and the Social Security earnings test (2026-10-17)

Fork-only planning note. Written on `claude/lucid-noether-20vnnv` (= `main` `50b152c`, after
`claude/intelligent-faraday-pfhera`; upstream `dev` `7abed19` merged). No code changed yet.

How each claim below is backed:

- **Verified**: read in the primary text. For SSA rules: the POMS on `secure.ssa.gov` (section,
  transmittal and date given) and, from 2026-10-18, 20 CFR 404 subpart E as of 2026-10-15 from
  the eCFR versioner API. Access, tested 2026-10-18 (the first draft said eCFR and `ssa.gov`
  were unreachable; for eCFR that was wrong, see below):
  - **eCFR works** through `https://www.ecfr.gov/api/versioner/v1/full/<date>/title-20.xml?part=404&subpart=E`
    with a browser User-Agent, `Accept: application/xml` and `--compressed`. The HTML pages
    redirect automated clients to `unblock.federalregister.gov`, which the proxy refuses, and
    after a few calls the API answered "Your IP address has been blocked ... Support Code 02";
    the first draft's 403/404 were a wrong API path and that block, not the allow list.
  - **`www.ssa.gov`**: the proxy passes it, but SSA's Akamai edge answers "Access Denied" (403)
    to curl with any User-Agent and to WebFetch (`/oact/cola/AWI.html`, `/oact/cola/cbb.html`,
    `/OP_Home/ssact/title02/0209.htm`).
  - **`ssa.gov`** (no www): the server sends its `*.ssa.gov` certificate without the DigiCert
    intermediate ("DigiCert Global G2 TLS RSA SHA256 2020 CA1"), so TLS verification fails; the
    intermediate's host `cacerts.digicert.com` is refused by the proxy, and verification is not
    to be switched off. So the Act and the AWI series are still unread here.
  - `www.federalregister.gov` is refused by the proxy.
- **Read in code**: cited by file and line on this commit.
- **Measured**: a script in `fork-notes/phase5/` and its saved output.
- **Inferred** or **recalled**: marked where used; each recalled item has a step-0 check.

---

## 1. What Phase 5 has to answer, and what Owl does today

The household's open questions that involve work (CLAUDE.md, `Case_us.template.toml`): when each
spouse stops working (end of 2026 or later), whether one keeps working part time, and when each
claims SS given that. Both were born in 1964 (FRA 67 in 2031; template), so every year from
2026 to 2031 falls between 62 and FRA, which is the earnings test's whole window.

What Owl does today (read in code):

| Piece | Today | Where |
|---|---|---|
| Wages | Fixed per-person, per-year input `anticipated wages`, nominal, **net of all contribution columns** (employer contributions included in those columns) | `plan.py:2320`, `ui/Documentation.py:440` |
| Earnings test | Not modeled; documented as a limitation | `socialsecurity.py:19-22`, `papers/owl.tex:407` |
| SS streams | `compute_social_security_benefits(pias, ages, ...)` in today's $, annual, payments one month in arrears; called at `setSocialSecurity` (`plan.py:1397`), for the one-free-spouse tabulation (`plan.py:3131`) and on each loop iteration under `withSSAges` (`plan.py:8433`); `build_own_benefit_table` for `B_own` (`plan.py:3099`) | `socialsecurity.py:602`, `:735` |
| Claiming-age choice | `withSSAges`: binaries `zssa` over 97 months, `ssb = B_own·zssa (+ B_cross·zssa_partner)`; exact when one spouse is free, spousal/survivor in a loop offset when both are | `plan.py:5174` (`_configure_ss_age_variables`) |
| PIA | Fixed input; extra work years do not change it | `plan.py:1439` |
| Payroll tax | No FICA, SECA or Additional Medicare Tax found: a case-insensitive grep for `fica`, `payroll`, `0.0765`, `wage base`, `additional medicare`, `seca` in `src/owlplanner` hits only `ssecAmounts`/`ssecAges` and two unrelated comments | — |
| Medicare | Every person from 65 (`mediVals`: `yob + 65`), IRMAA on the household MAGI; HSA contributions zeroed from 65 | `tax_federal.py:383`, `plan.py:2333-2355` |
| ACA | One household start year (`aca_start_year`) | `plan.py:569`, `:2825` |

Scenario 4b (`phase0-scenarios.md`) works around the gaps by hand: optimize only the claiming age
of the spouse who stops, keep the worker at 67+, a PIA per scenario, and `aca_start_year` at the
year after the worker's last year.

## 2. Rules

### 2.1 Verified (POMS, read 2026-10-17)

- **Exempt amounts** (RS 02501.025 D, TN 55, 11/21/2025): 2026 annual $24,480 (monthly $2,040)
  below the FRA year, $1 withheld per $2 above it; in the FRA year $65,160 (monthly $5,430), $1
  per $3. 2025: $23,400 / $62,160; 2024: $22,320 / $59,520. They follow "the increases in the
  level of nationwide earnings" (section A), i.e. wages, not prices; the exact indexing formula
  was not read.
- **What counts** (RS 02501.021 B, TN 53, 04/24): below the FRA year, the whole taxable year's
  earnings, even months without entitlement; in the FRA year, earnings in the months before the
  FRA month only. The test does not apply at or after FRA. For survivor (WIB) benefits the
  **retirement** FRA controls the test.
- **Excess** (RS 02501.080, TN 39, 11/23): (earnings − exempt)/2, or /3 in the FRA year, rounded
  down to the dollar. Worked examples there: $12,121 − $9,600 → $1,260; ($30,000 − $17,000)/3 →
  $4,333.
- **Charging** (RS 02501.095, TN 38, 11/23): from the first month of entitlement in the year,
  month by month until the excess is recovered or the year's benefits are exhausted; **never
  carried into the next year**. The worker's excess is charged to the **total family benefit** on
  the worker's record (worker plus auxiliaries, e.g. a spouse's benefit); an auxiliary's own
  excess only to that auxiliary's benefits, after the worker's excess. Examples there: $2,094
  against a $698 family benefit → January-March withheld; worker $2,076 against $519 → January-
  April, then the spouse's own $865 against the spouse's $173 → May-September.
- **Partial month** (RS 02501.110, TN 47, 11/23): the month where the excess runs out is paid in
  part, split among the family in proportion to their original benefits.
- **Monthly test / grace year** (RS 02501.030, TN 37, 11/23): in a grace year, full benefits for
  any **non-service month** (a month of entitlement before FRA with wages not above the monthly
  exempt amount and no substantial services in self-employment), whatever the annual excess. The
  initial grace year is the first taxable year with a non-service month in or after the month of
  entitlement. (This is what lets someone retire in June and claim in July without losing July-
  December.)
- **Adjustment of the reduction factor (ARF)** (RS 00615.480, TN 77; RS 00615.482, TN 76, 08/24):
  automatic at FRA (retirement and spouse's benefits; widow(er)'s at 62 and FRA). Months with a
  full **or partial** work deduction are crediting months and drop out of the reduction. A spouse
  gets crediting months for deductions caused by the spouse's own work and by the worker's.
- **Earnings that count** (RS 02505.005, TN 17; RS 01402.010, TN 33; RS 01402.036, TN 25;
  RS 02505.045, TN 29): wages as defined for SS (no annual cap), so **salary-reduction amounts
  (401(k)/403(b) deferrals) count**; §125 cafeteria-plan amounts (payroll health premiums, a
  payroll HSA) do not; employer payments into a retirement fund (the match) do not; net earnings
  from self-employment count (RS 02501.080 B.1.c). In practice this is W-2 box 5 (Medicare wages)
  plus net self-employment earnings (inferred from the definitions above; box 5 itself was not
  checked against them).

### 2.1b Verified in 20 CFR 404 subpart E (eCFR, 2026-10-15 text, read 2026-10-18)

- **Indexing** (404.430(a)(2)): the lower monthly exempt amount is $670 x AWI(year − 2) /
  AWI(1992), the higher one $2,500 x AWI(year − 2) / AWI(2000), each rounded to the nearest $10
  ($5 rounds up); annual = 12 x monthly; never below the amount in effect when it is set. So they
  follow wages with a two-year lag.
- **FRA year** (404.430(b), 404.435(a)(3), 404.434(c)): only earnings of the months before the
  FRA month count, and no month at FRA is charged. This settles the first inference of the first
  draft.
- **Charging** (404.434(a)-(b)): from the beginning of the year, $1 of the worker's excess per $1
  of all benefits on the worker's record; an auxiliary's excess only against the auxiliary's own
  remaining benefits, after the worker's. Same as RS 02501.095.
- **Non-service months and grace year** (404.435(a)(7), (b)), with Example 1 there: retire in
  April, part time under the monthly amount after it → May-December paid although the year's
  earnings exceed the annual amount; later years annual test only. **Presumption**
  (404.435(e)): wages above the monthly amount are presumed in every month until shown
  otherwise, which is what `months worked` lets the user show.
- **ARF** (404.412): months subject to deduction under 404.415 are not counted in the reduction;
  the increase is effective with the month of FRA (widow(er)s: also at 62).
- **Earnings** (404.429(a)): wages for services in the taxable year plus net earnings from
  self-employment minus a net SE loss; which payments are wages is in the POMS sections above.

### 2.2 Inferred

- The ARF is equivalent to recomputing the reduction factor at the claiming age plus the crediting
  months (capped at FRA), so `getSelfFactor(fra, claim + c/12)` / `getSpousalFactor(...)` can be
  reused. To check against an RS 00615.490 worked example in step 1.

### 2.3 Recalled, to check in step 0

- 2026 SS wage base $184,500; Additional Medicare Tax 0.9% above $250,000 MFJ (statutory, not
  indexed). Source to use: IRS Pub. 15 (2026) and Form 8959 instructions on `irs.gov` (reachable
  in earlier sessions).
- SSA Statement estimates assume the person keeps earning at the latest level until each claiming
  age, so a Statement PIA overstates the PIA of someone who stops earlier. Check on the user's own
  Statement text (local) or a POMS/SSA page reachable from here.
- AWI series and the PIA formula (42 U.S.C. 415(a), govinfo.gov was reachable on 2026-10-04) are
  only needed if D4 picks the script.

## 3. Evidence gathered for this plan (measured)

`fork-notes/phase5/et_examples.py`, output `et_examples_2026-10-17.txt`: of the 18 upstream
examples, **3 pay SS before FRA in a year with wages above the exempt amount**, so Owl pays a
benefit SSA would largely or entirely withhold:

| Example | Who | Claims | Years | Wages | SS Owl pays that year (today's $) | (wages − $24,480)/2 |
|---|---|---|---|---|---:|---:|
| alex+jamie | Jamie, born 1961-01 (already collecting) | 62y1m | 2026, 2027 | $80,000 | 10,140 | 27,760 |
| chris+pat | Pat, born 1966-01 | 62y1m | 2028 | $85,000 | 9,858 | 30,260 |
| jack+jill | Jill, born 1966-01 | 62y1m | 2028 | $85,000 | 11,562 | 30,260 |

The last column is a first-order size only (nominal wages against the 2026 amount). In every
row it exceeds the year's benefit, so under the annual test the whole year is withheld, the
withheld months come back through the ARF at FRA, and taxes on SS (Psi) and MAGI move with it.
Pat's and Jill's 2028 is also their last year of wages: whether that year is withheld depends on
**when in 2028 they stop working**, which Owl's annual wages do not say (the grace-year rule
above). That is the main input question of this phase (§4.2, D2).

jack+jill is also the case upstream's user guide walks through (`info/USER_GUIDE.md:41`), so this
table is the evidence for the upstream issue (step 9).

## 4. Design

### 4.1 Principle: a deterministic table, not a new LP piece

Earnings are inputs, so for a given claiming month everything the earnings test does (withheld
dollars per year, crediting months, the higher benefit from FRA) is a fixed function of that
month. It therefore goes **into the SS streams Owl already builds**, before the LP sees them:

- fixed ages: `zeta_in` with the test applied;
- `withSSAges`, one free spouse: the 97 tabulated pair streams (`B_own`/`B_cross`), built by the
  same function, so the MILP's choice stays exact;
- `withSSAges`, both free: `B_own` holds each person's own benefit with their own excess charged
  and their own ARF (exact); the part of a worker's excess charged to the partner's spousal
  add-on goes through the existing spousal offset and is exact at convergence, the same status
  the spousal and survivor amounts already have there.

No new variables, rows, binaries, loop parameters or local-search families; taxes, IRMAA, ACA
and the Summary follow the net benefit automatically. This is the property that makes the piece
cheap and upstream-shaped (lesson 5 of `phase3-plan.md`: one model, rows in the one LP).

### 4.2 Inputs

Two optional per-person columns in the Wages and Contributions table (HFP sheet / UI / JSON
through `hfp_io`), so they ride on `timeLists`, `rawHFP` and `clone` like every other column
(`plan_bridge.py:641` re-reads `rawHFP` for a new horizon):

- **`gross earnings`** (name to settle in D1): earnings as the test counts them, nominal $: W-2
  box 5 plus net self-employment earnings. Absent: `anticipated wages` is used, which understates
  by the payroll deferrals (wages are net of contributions) and includes nothing from `other inc`;
  a warning names the years where a deferral column is non-zero in a test year.
- **`months worked`** (D2): 0-12, months at the start of the year with earnings, default 12 when
  the year has earnings. Earnings are taken as spread evenly over those months. It decides the
  non-service months of the grace year and the share of FRA-year earnings before the FRA month.
  Tied to the year row, so it is not a free-floating date (lesson 6).

Exempt amounts: a table in `socialsecurity.py` (2024-2026 from RS 02501.025 D, source comment),
projected in today's dollars at the last known amount, i.e. growing with inflation. By statute
they follow the AWI with a two-year lag (404.430(a)(2)); Owl has no wage index, so this slightly
overstates withholding after 2026; the horizon that matters is at most 5 years (62 to FRA).
Stated in the docstring. The 2027 amounts are already fixed by the 2025 AWI and are normally
announced in October (recalled): add them to the table in step 1 if a primary copy is reachable (POMS
RS 02501.025 D is updated each November).

### 4.3 The function

`socialsecurity.earnings_test(...)` (internal, new), on a monthly grid from the first plan month
to each horizon, in today's dollars:

1. Monthly entitlement streams per person, by entitlement month (Owl's payments are one month in
   arrears, `_payment_start`; shift by one month at the end, as today): own benefit
   `PIA x selfFactor(claim)`, spousal add-on from the later claim (`_add_spousal_benefit`'s rule),
   survivor stream (`compute_survivor_stream`).
2. For each calendar year before the worker's FRA year inclusive: countable earnings, excess,
   chargeable months (entitlement months before FRA, minus non-service months if the year is the
   grace year), charge the worker's excess against the family benefit on their record month by
   month (last month split in proportion), then each person's own excess against what is left of
   their own benefits. Record withheld dollars per person and crediting months per record.
3. ARF: from FRA, own benefit `PIA x selfFactor(fra, claim + c_own/12)`, spousal at the spouse's
   FRA with the spousal factor and the spouse's crediting months; survivor per RS 00615.580 (D7).
4. Aggregate to annual payment-year amounts.

`compute_social_security_benefits` and `build_own_benefit_table` gain an optional
`earnings_in` / `work_months_in` (today's $) and call it; with `earnings_in=None` both return
exactly what they return now (upstream behaviour, and the no-op test).

### 4.4 Where it plugs into `Plan`

- Earnings are known only after the HFP is read, and `setSocialSecurity` can run before that. So
  `zeta_in` is rebuilt with the test where `zetaBar_in` is set at solve time (`plan.py:2753`,
  inside `_adjustedParameters`), through one helper `Plan._ss_streams(ages)` that all four call
  sites use. Same pattern as the Budget profile (`xi_n` built in `solve()`, CLAUDE.md gotcha).
  `_adjustedParameters` must be reset when the HFP is re-read, or a second solve keeps stale
  streams (test it).
- Outputs: `Plan.ss_withheld_in` (nominal), `Plan.ss_arf_months_i`; Summary rows "SS withheld by
  the earnings test" and "ARF months"; a worksheet column next to SS; `owlcli explain` / MCP SS
  block gains both; a warning when a fixed claiming age pays nothing before FRA ("all benefits
  withheld 2026-2027; benefit raised at FRA by the ARF"), since that usually means the age is a
  typo or a plan to revisit.
- Switch: `solver_options.withEarningsTest` (D6).

### 4.5 Out of scope (decided here unless the user objects)

- Earnings after claiming that raise the PIA (automatic recomputation): PIA stays an input.
- Substantial services in self-employment as a monthly test: self-employment earnings are spread
  over `months worked` like wages.
- Family maximum, divorced spouses, child benefits: not modeled anywhere in Owl.
- Optimizing the retirement date or the part-time level: the objective has no value for leisure,
  so the optimizer would always work longer. These are scenario levers (§5 step 6), and the
  output is the price of each extra year of rest, which the household judges.

## 5. Implementation plan

Conventions (CLAUDE.md): full suite before a commit is green; re-record moved fixtures under the
frozen test date; flake8 and Ruff (`zip(strict=)`); `$` escaped in Markdown/UI text; upstream
names and style in upstream files; PROGRESS.md updated each session.

### Step 0: sources and stakes — size S

1. Check the §2.3 items on `irs.gov` and in POMS; record what was and was not verified in this
   file.
2. Stakes without the LP: `fork-notes/phase5/et_stakes.py` on the stand-in couple (both 1964,
   PIAs $3,000 / $2,400 as in `nj_stakes.py`), using a prototype of the step-1 function. Grid:
   worker's earnings {0, 20k, 30k, 40k, 60k, 100k} x last work year {2026 ... 2031} x
   `months worked` in the last year {6, 12} x claiming age {62, 63, ..., 70}. Print lifetime
   benefits (today's $, no discounting, and at 2% real) with and without the test. What it
   answers: how far "claim at 62 while working" moves once withholding and the ARF are counted,
   and whether the best age moves at part-time earnings near the exempt amount (where the test is
   partial and the ARF small). Expected (inferred, not computed): above roughly 2x the exempt
   amount plus the benefit, early claiming is close to claiming at the stop date.
3. Gate: if the household-relevant cells (part time 20-60k, stop 2026-2029) show no change in
   best age and lifetime benefits within about 1%, stop after step 4 with the test as a
   correctness fix (it is still wrong for 3 of 18 examples) and skip steps 6-8's LP sweeps.

### Step 1: the rules as a pure function — size M

`socialsecurity.py`: exempt-amount table and projection, `earnings_test(...)` (§4.3). Tests
(`tests/ss/test_earnings_test.py`) taking the exempt amounts as parameters, so the POMS examples
run with their own year's numbers:

- RS 02501.080 examples ($1,260; $4,333; the FRA-year wage cut at the FRA month);
- RS 02501.095 examples (3 family months; 4 family months then 5 spouse-only months);
- partial last month split in proportion (RS 02501.110);
- grace year: claim in July of the last work year with `months worked` = 6 → nothing withheld;
  same with 12 → withheld; a second year with non-service months gets no grace;
- ARF: claim at 62, 12 crediting months → from FRA, the factor of claiming at 63; a partial
  deduction month counts;
- no carry-over into the next year; nothing at or after FRA;
- earnings zero → streams identical to today's.

Confirm the §2.2 inference against an RS 00615.490 worked example while writing this.

### Step 2: inputs — size S

`hfp_io.py` (columns, typo check, write-back), `plan.py` `readHFP` (`timeLists` → arrays
`etEarnings_in`, `etMonths_in`, zeros in `__init__`), `zeroWagesAndContributions`, the UI Wages
and Contributions editor and its column list, the JSON/TOML HFP path, `Documentation.py`,
`PARAMETERS.md`, the HFP template. Defaults and the warning of §4.2. Tests: round trip workbook →
plan → workbook; absent columns → defaults; `clone` with a new expectancy keeps them; bad values
(months outside 0-12, negative earnings) refused like other columns.

### Step 3: fixed claiming ages — size M

`Plan._ss_streams(ages)`; rebuild `zeta_in` at solve time (§4.4); the option of D6; outputs and
warning (§4.4); `export.py` Summary/worksheet rows; `cmd_explain` SS block. Tests: the three
examples of §3 with the test on (Jill: 2028 withheld with `months worked` 12, not with 6; ARF
months; taxes on SS follow the net); no-op on the other 15 (objective identical to the cent);
a second solve after editing wages sees the new earnings. Then the full suite; list every
recorded value that moves and why (expected: only the three examples, and only with the switch
on).

### Step 4: `withSSAges` — size M

`build_own_benefit_table(earnings_in=...)`, pair tabulation through `_ss_streams`, loop update at
`plan.py:8433` through the same helper. Tests (exact-LP settings, `withMedicare="none"`,
`withSSTaxability=0.85`, `maxBequest` with `netSpending`, per the degenerate-tests gotcha):
one free spouse who works → the MILP's objective equals the best of the 97 fixed-age solves
(brute force on a coarse grid, plus the MILP's pick and its neighbours); both free → converges,
and the result is not worse than the best one-at-a-time alternation; the 3 examples with
`withSSAges` on the earner. Local search: no new family, check that a run with the test equals
branch-and-bound on one case.

Upstream checkpoint: after step 4 the fork has a working, measured piece (step 9).

### Step 5: payroll tax — size S (D3)

If D3 = core: `solver_options.withPayrollTax` (default off), from `gross earnings` (or the
fallback): 6.2% up to the wage base (indexed with inflation after 2026), 1.45%, 0.9% on the
household's earnings above $250,000 MFJ / $200,000 single (not indexed); self-employment:
15.3% x 92.35% with half deductible above the line (only if D3 includes it). A constant outflow
in the cash-flow row and a Summary line; no LP change except the constant and, for SE, a
constant in the AGI rows. Tests: hand computation for one year; off → no-op on all examples.

### Step 6: scenarios and sweep — size M (D4, D5)

`fork-notes/phase5/work_sweep.py` (fork-notes, not core; the HFP builder belongs to Owl-budget,
#175): from a base case + HFP and a small JSON of work variants (per person: last work year,
`months worked` that year, part-time earnings and years, deferral % — real numbers stay in
`otherFiles/`), write one HFP per variant, set `aca_start_year` and the PIA per variant, run each
with local search and with the exact LP (CLAUDE.md "loop noise"), and print per variant: the
objective, the claiming ages chosen (`withSSAges` on both), lifetime SS withheld, federal + state
tax, Medicare + ACA, and the difference from the base. The same day, one machine, one at a time.
PIA per variant from D4. Rewrite `phase0-scenarios.md` §4 and §4b around it.

### Step 7: working past 65 — dropped (D5 = no, 2026-10-18)

Kept for reference, in case a scenario changes: only if a scenario has someone working past 65 with employer coverage. Per-person Medicare start
(delayed Part B: no premium and no IRMAA until coverage ends) in `mediVals`, and HSA contributions
allowed until that start (Owl zeroes them at 65, `plan.py:2333`). Rules to verify before coding:
the special enrollment period and Part A/HSA interaction (recalled: claiming SS at 65+ enrolls
in Part A, which ends HSA contributions).

### Step 8: measure on the stand-in couple — size M

With steps 1-6: the grid of step 0 inside the LP, both claiming ages optimized.
Report: (a) the value of the test against the scenario-4b workaround (worker fixed at 67) per
variant; (b) how much Owl without the test overstates a "claim at 62 while working" plan; (c) the
price of each extra work year and of part time vs stopping, with and without payroll tax. Decide
differences only above the spread between local search and the exact LP. PROGRESS.md section;
CLAUDE.md gotcha "Earnings test: not modeled" replaced.

### Step 9: upstream — after step 4 (or 8)

A design issue at the concept level (lesson 8), federal SS only (lesson 3): the limitation
upstream documents is live in 3 of its 18 examples (§3 table, rerun on stock `dev`); proposal
§4.1 (deterministic, no LP change); questions for the maintainer: an earnings input separate from
`anticipated wages` (which is net of contributions) or a derived one; how to express the stop
month; default on or off for existing cases. Draft in `fork-notes/issue-earnings-test.md`, the
user files it. Payroll tax as a separate, later issue if D3 = core. When upstream implements its
own design, take theirs and drop ours, as before.

### Step 10: docs — size S

`socialsecurity.py` module docstring (limitation → what is modeled and the assumptions: even
spread over `months worked`, exempt amounts at inflation, family charging exact only with one free
age), `modeling-capabilities.md` SS row, `Documentation.py`, `PARAMETERS.md`, template comments,
CLAUDE.md state and gotchas.

## 6. Decisions

**Answered by the user 2026-10-18: D1-D8 as recommended, D5 no** (no scenario works past 65 with
employer coverage, so step 7 is dropped). So: D1 `gross earnings` column with the
`anticipated wages` fallback and warning; D2 `months worked` column; D3 payroll tax in core,
opt-in `withPayrollTax`, self-employment only if a variant has consulting income; D4 PIA per
variant from SSA's calculator, by hand; D6 `withEarningsTest` off in code, on in the household
template; D7 survivor benefits in step 1 if the engine makes it cheap; D8 upstream issue after
step 4. The table keeps the options as they were put.

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Earnings the test uses | (a) new optional column `gross earnings`, fallback `anticipated wages` + warning; (b) derive from `anticipated wages` + `401k ctrb` + `Roth 401k ctrb` (overstates by the employer match, which sits in the same columns); (c) `anticipated wages` only | (a): the only one that is right when the match is non-zero; the fallback keeps old files working |
| D2 | When the last year's work stops | (a) optional `months worked` column; (b) assume the last work year ends before the claim (grace year always applies); (c) assume work through December | (a). (b) and (c) give opposite answers for Jill and Pat (§3), so an assumption alone decides the result |
| D3 | Payroll tax on earnings | (a) core, opt-in `withPayrollTax`; (b) written by the sweep script as a negative big-ticket item (big-ticket items enter the cash-flow row, `plan.py:4839`, and not the taxable-income row, `:4928-4940`); (c) leave out | (a) once D1 exists: about 7.65% of earnings is a cost of every work variant (on $40k part time, about $3k/yr; inferred arithmetic), and (b) is lost whenever wages are edited by hand. Self-employment only if a variant has consulting income |
| D4 | PIA per work scenario | (a) SSA's own calculator in the user's account, one PIA per variant, entered by hand; (b) `pia_from_record.py` from the earnings record (needs the AWI series; `www.ssa.gov` denies us) | (a) first; (b) only if the sweep needs more than a handful of variants |
| D5 | Does any scenario work past 65 with employer coverage? | yes → step 7; no → skip | Your call; it decides step 7 |
| D6 | Default of `withEarningsTest` | (a) on; (b) off in code, on in the household template | (b) for now: on, it moves recorded results of jack+jill, chris+pat and alex+jamie, which 32 test files reference (grep; how many pin numbers is counted in step 3), and every upstream re-record of those cases would then conflict at merge. Revisit when upstream decides (step 9) |
| D7 | Survivor benefits under the test (a survivor under FRA who works) | (a) include in step 1; (b) defer | (a) if step 1's engine makes it cheap, since it is the same charging rule; otherwise (b) and documented |
| D8 | Upstream timing | after step 4 / after step 8 | After step 4: the evidence is the upstream examples, not the household |

## 7. Risks

- **Upstream redesign.** The maintainer may implement the test with another input (lesson 2). Keep the fork's
  code in two places (`socialsecurity.py` function, `_ss_streams`) so it can be dropped for his.
- **Monthly vs annual.** Owl is annual; the test is monthly. The even-spread assumption is the
  weak point for a year with a raise or a bonus. Mitigation: the user enters `months worked` and
  `gross earnings` for the transition years only; everything else is unaffected.
- **Exempt amounts in real terms.** Held at 2026's level in today's dollars; real wage growth of
  about 1%/yr (recalled) would raise them by under 5% by 2031.
- **Both ages free.** Family charging across spouses is exact only at convergence (offset), like
  the spousal amounts today; the loop may need more iterations when withholding switches on and
  off between candidate ages. Measure in step 4; if it cycles, recommend optimizing one spouse at a
  time (as upstream's docs already do).
- **Stale streams.** `zeta_in` built before the HFP is read would silently skip the test; the
  step-3 test of a second solve after editing wages guards it.
- **Data access.** POMS and eCFR (API, browser User-Agent, rate-limited) work; `www.ssa.gov` is
  denied by SSA's edge and `ssa.gov` fails TLS (header of this note). Any number not found in
  POMS, eCFR or on `irs.gov` stays marked recalled.

## 8. Order and size

Step 0 (S) → 1 (M) → 2 (S) → 3 (M) → 4 (M) → [9 upstream draft] → 5 (S) → 6 (M) → 7 (conditional)
→ 8 (M) → 10 (S). Steps 1-4 are the earnings test itself; 5-8 turn it into answers for the
household. All decisions answered 2026-10-18 (§6); step 7 dropped.

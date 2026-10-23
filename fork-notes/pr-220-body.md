# PR for #220: the SSA earnings test (opened as PR #222)

Status: drafted 2026-10-23; opened by the user the same day as
https://github.com/mdlacasse/Owl/pull/222. Branch `fmateoc:earnings-test-pr`, base `mdlacasse/Owl` `dev`
(`e3592e7`), built from stock `dev` by porting the fork's earnings test (`claude/phase5-step1`
at `e82f6bb`, which includes the two review fixes of 2026-10-23) without the fork's other work:
no payroll tax (`withPayrollTax`), no itemizing, STAR, budget, local tax or state-move code. The
session cannot open a PR on `mdlacasse/Owl` (GitHub access covers the fork only): the user opens
it from the branch with the title and text below.

Branch commit `c6fcedb`. Checked on it: full suite 3140 passed, 1 skipped (8:55); flake8
(`--max-line-length=120`, and CI's strict selection) and Ruff clean; the fifteen untouched
examples equal to the cent with and without the test; jack+jill re-recorded under the frozen
test date (PROGRESS.md "#220: earnings test reviewed; PR built on stock `dev`").

---

**Title:** #220: the SSA earnings test

As offered in #220: the earnings test as part of the model, with no option. A case without
earnings up to someone's FRA year is unchanged.

**Where it sits.** `socialsecurity.earnings_test` builds the same monthly entitlement streams as
`compute_social_security_benefits` and applies the test to them; `Plan._ss_streams` calls it from
`setSocialSecurity` and again at solve time in `_adjustParameters` (the HFP can be read after
`setSocialSecurity`, so the solve-time rebuild is the one that counts, like `zetaBar_in`). Where
the test withholds nothing and credits no month, the plan keeps
`compute_social_security_benefits`' own output, so untouched cases do not depend on the new
builder. For a given claiming age everything is a fixed number: no new column, row, binary or
loop quantity. Under `withSSAges` each candidate is a fixed-age solve on a clone, so the search
sees the test (the clone carries the two columns).

**Rules** (POMS on secure.ssa.gov and 20 CFR 404 subpart E, as cited in #220 and in the module):
- excess: \$1 per \$2 above the annual exempt amount before the FRA year; \$1 per \$3 above the
  higher amount in the FRA year, counting earnings of the months before the FRA month only
  (RS 02501.080, RS 02501.021 B); exempt amounts 2024-2026 from RS 02501.025 D, later years held
  at the 2026 amount in today's dollars (Owl has no wage index);
- charging (RS 02501.095, .110): the worker's excess against everything paid on their record
  (own benefit, then the spouse's spousal benefit in the same months), month by month from
  entitlement, a partial last month split by original shares; then each auxiliary's own excess
  against what is left of their own check; no carry-over into the next year;
- initial grace year (404.435, RS 02501.030): the first year with a non-service month after
  entitlement; its non-service months are paid whatever the annual excess;
- ARF (RS 00615.480/.482/.490): crediting months subtracted from the reduction months at FRA,
  separately on the own record and on the spouse record; the survivor benefit starts from the
  deceased's benefit after their ARF when they reached FRA;
- not modeled: the test on checks paid from the year of the first death on, the survivor ARF
  (RS 00615.580), substantial services in self-employment, earnings before the plan (someone
  entitled before the plan has used their grace year).

**Inputs.** Two optional columns in each Wages and Contributions sheet (and the UI table, the
template workbook and the workbook writer):
- *gross earnings*: W-2 box 5 plus net self-employment earnings, nominal \$. 0 or absent means
  *anticipated wages*, which are net of the *ctrb* columns: the solve warns, once per person,
  about the years the test can reach that have wages and a non-zero taxable, 401k or IRA
  contribution (HSA left out: a payroll HSA is not in box 5). *other inc* is not read.
- *months worked*: 0-12, months of work at the start of the year; 0 or absent means 12 in a
  year with earnings. An absent column of either kind is not reported as "treated as zero".

**Outputs.** Summary rows *SS withheld by the earnings test* and *ARF months* for a household
with earnings in a plan year up to someone's FRA year (\$0 and "none" included, so two claiming
ages compare row by row); a *SS withheld* column next to *social sec* in the per-person worksheets
when something is withheld; `ss_withheld_today` / `ss_withheld_nominal` in `plan_metrics` and
the JSON summary; an `earnings_test` block per person in `owlcli explain` (and the MCP
`explain_case` docstring); a warning when a fixed claiming age pays nothing before FRA.

**Cost of the full MILP** (#220, measured on the fork at the examples' own claiming ages,
`breakpointMethod="branch-and-bound"`): same columns and binaries; 8 rows fewer (the
SS-taxability rows of a year whose benefits are fully withheld); every case solved faster with the
test, two with more nodes. Building the streams takes about 1 ms.

**Docs.** Documentation (HFP columns), Financial Profile help, `info/PARAMETERS.md`,
`info/modeling-capabilities.md` (Social Security row), `papers/owl.tex` (the two "not modeled"
sentences), CHANGELOG under *Version WIP*.

**Tests** (new files; expected values are hand numbers from the rules, not from the code):
- `tests/ss/test_earnings_test.py`: the POMS and CFR worked examples (excess, charging, partial
  months, grace year, ARF), stream-level pins, and zero earnings equal to
  `compute_social_security_benefits` on a grid of cases (couples, survivors, trims, claims before
  the plan);
- `tests/ss/test_earnings_test_always.py`: every solve applies it, the untouched path is the
  original builder's output, the Summary rows' gate;
- `tests/ss/test_earnings_test_plan.py`: on the examples, the fifteen untouched ones equal to the
  cent, jack+jill / chris+pat / alex+jamie withheld and raised at FRA, outputs, warnings (once per
  solve, under `withSSAges` and local search), units;
- `tests/ss/test_earnings_test_ssages.py`: each `withSSAges` candidate equals an independent
  fixed-age solve with the test;
- `tests/config/test_hfp_earnings_columns.py`: the columns (round trip, defaults, refusals,
  clone, UI sync, the fallback warning);
- `tests/ui/test_financial_profile.py`: the absent-column notice.

Recorded results: jack+jill's net spending 102,535 -> 102,621 in `test_toml_cases.py`
(102,531.46 without the test, 102,620.63 with it, under the frozen test date: Jill's \$14,302
withheld in 2028, 11 months credited at FRA); the example-workbook header check no longer requires
the two columns (absent means "not given"; only the template carries them). Full suite: 3140
passed, 1 skipped; flake8 with CI's strict selection: 0.

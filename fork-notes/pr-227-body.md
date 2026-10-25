# PR for #227 (payroll tax), for the user to open

Status: drafted 2026-10-25, revised the same day after a review of the branch. Head
`fmateoc:payroll-tax-pr` (pushed), four commits on upstream `dev` `22ce72b` (the version kick
after `03aaef3`): `55b49ba` (the feature), `36cdddf` (review fixes), `3167318` (one filing-status
rule) and `033c9d8` (MOSEK records left empty), base `dev`. Built in a worktree
of stock `dev`; no fork code.
Everything below is from real runs on that branch (HiGHS, linux, frozen test date) unless marked.

---

**Title:** [feat] The employee's payroll tax is paid on wages (#227)

**Body:**

Closes #227, in the shape you described.

**Engine**

- `tax_federal.payrollTax(N_i, earnings_in, gamma_n, n_d, N_n)`: a pure function, one total per
  year. 6.2% of each person's earnings up to the wage base (`payrollWageBase` = \$184,500 times
  `gamma_n`, i.e. the 2026 base held in today's dollars), 1.45% on all of them, and 0.9% of the
  household's combined earnings above \$250,000 through the year of the first death and \$200,000
  after (not indexed). Constants next to NIIT's. The filing status of each year comes from a new
  `filingStatus_n(N_i, n_d, N_n)` (joint while `n < n_d`, single after; single throughout for one
  person).
- One copy of that rule. `filingStatus_n` replaces the ten copies of it: `capitalGainTax`,
  `taxParams`, `seniorBonusSchedule`, `taxBrackets`, `computeNIIT`,
  `compute_social_security_taxability`, `tax_state.st_taxParams`, and the inline ones in the SS
  taxability, LTCG and NIIT rows of `plan.py` (the NIIT rows also stop hard-coding 200,000 /
  250,000 and read `niitThreshold`). The loops stay loops: vectorizing `computeNIIT` and the payroll
  tax saved 9 µs and 100 µs per call (30-year couple), about 0.15 ms of joe's 70 ms solve and
  0.2 ms of jack+jill's 1.3 s, below run-to-run noise, so it was not worth the change. Every pinned
  plan is unchanged (full suite), and `computeNIIT` equals the old decrementing loop to the bit on
  20 random cases (`tests/tax/test_filing_status.py`). Not touched, because they are other rules:
  `_filers_alive` / `deposit_split` (who is alive), `irmaaStatus` (the return two years back,
  #213), the home-sale window (two years after the death).
- `Plan.payroll_n`: zeros in `__init__`, rebuilt at solve time in the `_adjustedParameters` block
  right after `_ss_streams`, from `_earnings_test_inputs()` (wages plus the year's tax-deferred
  contributions, payroll HSA left out). `solve()` resets `_adjustedParameters`, so a change of
  wages, contributions or death year is seen by the next solve (tested).
- The cash-flow row: `rhs -= self.debt_payments_n[n] + self.payroll_n[n]`. No column, row or
  binary. Not in `T_n`, not in `_actual_effective_tax_rate`, not in any income-tax row; `omega_in`
  is untouched.
- No option.

**Outputs**

- Cash Flow sheet: `payroll tax` (negative) right after `NIIT`, when any year has one. The sheet
  still balances: a new test sums every column of the actual sheet against net spending, row by row.
- `planData` (CSV): the same column, same place; `Tax bills + Med.` in the Income sheet and the CSV.
- Taxes sheet: a `payroll tax` column after `10% penalty`, when any year has one, outside its
  `total` (which is `T_n`), so the sheet reconciles with *Tax bills + Med.*
- `_check_cashflow_balance`: on the outflow side.
- `lifetime_allocation()["outflows"]["taxes"]`, and the same term in `annual_cashflow_mix()` so the
  two stay consistent (not in your list; say if you would rather leave the mix alone).
- Not done, your call: the taxes plot (`showTaxes`, `allTaxes = T_n + U_n + J_n`) does not show the
  payroll tax. It could join the "income tax" line or be its own line, which needs a new series in
  both plotting backends.
- Summary: *Total payroll tax paid* (today's \$ and nominal) after the NIIT line, for every case
  (\$0 without earnings).
- `plan_metrics`: `payroll_tax_today` / `payroll_tax_nominal`, in `METRICS_COLUMN_MAP`, so
  `owlcli compare` reports the delta. Also in `owlcli run`'s JSON (`_metrics_to_summary` and each
  `by_year` row), which serializes by hand-listed keys.
- Docs: a *Payroll tax (FICA)* row in `modeling-capabilities.md` with self-employment tax as a
  limitation (SE earnings in *anticipated wages* pay only the employee's 7.65%, and half of SE tax
  is not deducted); `PARAMETERS.md` (*anticipated wages*); `Documentation.py`; the paper
  (`\mathcal{F}_n` in the parameter list, in the net-spending equation, in Eq. C4 and in
  `v[J_5(n)]`). CHANGELOG entry under Version WIP.

**Tests** (`tests/plan/test_payroll_tax.py`, hand numbers from Pub. 15 and the Form 8959
instructions)

- The pure function: a single filer above the wage base after 10% inflation, with the 0.9% above
  \$200,000; a couple whose threshold switches from \$250,000 to \$200,000 at `n_d`; two \$150,000
  earners owing the 0.9% on the combined \$50,000; a couple with no death in the plan.
- jack+jill by hand (\$195,000 / \$195,000 / \$185,000 of earnings, 7.65%); a second solve after
  editing wages; the cash-flow identity and no balance warning; the Cash Flow sheet's column order
  and row sums; `T_n` is still the bracket sum; metrics, Summary columns, lifetime allocation, the
  Taxes sheet (column place, value, `total` still `T_n`), Income sheet and the CSV; the Summary row
  at \$0 and no Cash Flow or Taxes column without earnings.
- The twelve examples without wages derive no earnings and pay nothing (parametrized); the seven
  with wages pay something.
- `tests/tax/test_filing_status.py`: `filingStatus_n` on couples (death inside, at 0, at and past
  the end, None) and singles; `computeNIIT` equal to the old loop on 20 random cases.
- Two existing identities gained the term: `test_cashflow_balance._assert_cashflow_balance` and
  `test_export.test_cash_flow_sheet_balances_to_zero`.

**Measured: all 19 examples as shipped**, `dev` `22ce72b` vs this branch (frozen test date, HiGHS):

| case | objective | payroll tax (nominal) | before | after | change |
|---|---|---:|---:|---:|---:|
| alex+jamie | maxSpending | 43,987.50 | 228,076.76 | 225,076.85 | -2,999.91 |
| chris+pat | maxSpending | 48,083.85 | 116,836.89 | 114,042.80 | -2,794.09 |
| jack+jill | maxSpending | 43,987.50 | 102,572.09 | 100,669.12 | -1,902.97 |
| joe | maxSpending | 25,245.00 | 92,574.18 | 91,275.84 | -1,298.34 |
| john+sally | maxBequest | 8,797.50 | 16,802.68 | 21.00 | -16,781.68 |
| jon+jane | maxSpending | 100,138.50 | 160,611.20 | 155,455.03 | -5,156.17 |
| riley+casey | maxSpending | 3,672.00 | 116,803.61 | 116,561.47 | -242.14 |
| the other twelve | | 0 | | | 0.00 |

The twelve without wages are unchanged to the cent in basis, bequest, federal and state tax. Six
rows match the #227 repro to the dollar; riley+casey (added since) is 7.65% of Riley's \$48,000.

**Re-pinned** (HiGHS, linux). I don't have a MOSEK license, so none of these was run under
MOSEK; `test_toml_cases.py` and `test_repro.py` hold a MOSEK run to the same values:

- `test_toml_cases.py`: jack+jill 102,621 -> 100,669, joe 92,575 -> 91,276, john+sally
  16,803 -> 21. One table, as before.
- `test_repro.py`: SPENDING1 89,154 -> 87,226, BEQUEST1 959,477 -> 859,316, SPENDING2
  99,246 -> 97,199, SPENDING1_FIXED 93,255 -> 90,852, the same in the darwin, linux and win32
  tables. **Only linux was run**; darwin and win32 take the linux values, as in the earlier
  updates noted there. BEQUEST1's \$100k is linear in the tax: \$2.28 of bequest per dollar at
  half the tax and at all of it, on 1969 returns.
- `amo_mip_reference.json`: HiGHS basis and bequest re-recorded for alex+jamie, jack+jill, joe,
  john+sally and jon+jane (other fields unchanged), and the five added to `_rerecorded_cases`.
  **Not run under MOSEK** (no license, as above): their MOSEK records are
  left empty (`null`, with a `_mosek_not_recorded` note in the fixture), and
  `test_objective_matches_reference` skips the five under MOSEK until you record them.
- `test_local_search.py` (deep): the #197 tests. With the tax, john+sally no longer exercises
  #197: the full search, the search without (b'), the search with the full LTCG link rows
  (`_relax_links` returning the plan's rows) and the search with neither all give 14,013.49. So
  the tests now solve john+sally without the tax (`payrollTax` patched to zero), where the four
  give 31,778.17, 31,778.17, 30,823.25 and 20,004.43:
  - the existing test keeps the branch-and-bound bar, now 31,500 (was 31,000, which the full link
    rows' 30,823 came close to);
  - a new one runs on the full link rows and asserts > 30,000, so (b') is tested on its own. On
    `dev` today nothing tests it: with the relaxation, john+sally reaches 31,778 without (b').
  - Checked by reverting each part on this branch: no relaxation fails the first (30,823), no
    (b') fails the second (20,004), neither fails both.

**john+sally: \$16,803 -> \$21.** You asked whether a floor or constraint binds. It does, and not
in a way the tax causes:

- The loop's consistent plans fall on a straight line. Scaling the tax by s, the bequest drops a
  constant \$1.968 per dollar of tax from s = 0 to 0.97 (0.25 steps, then 0.9, 0.95, 0.96, 0.97,
  all on the line to within \$1), with a zero fixed-point residual. That is compounding: 2026's
  withdrawals all come from the taxable account, and the portfolio's real growth from 2026 to the
  horizon is 1.998 (every account 60/40 throughout); the rest is, I take it, tax drag on the
  taxable account (inferred, not measured).
- At that slope the bequest reaches zero at s = 0.97 (\$8,534 of tax). The bequest is the
  objective, and the final balances cannot go below zero, so past that point the loop's
  consistent plan is infeasible. The loop then ends on plans whose bequest stays near zero and
  that undercharge IRMAA: residual \$67 at s = 0.975, \$117 at 0.98, \$250 at 0.99, **\$374 at the
  full tax** (`plan_convergence`; exit "monotonic", where every s below 0.97 exits "oscillatory"
  with no residual). At s = 1.2 it ends on "unsolvable iterate", bequest \$0.98, residual \$2,809.
  So the shipped \$21 is a plan \$374 short on IRMAA, not a real bequest.
- Local search: 31,778.17 / 22,895.83 / 14,013.49 at s = 0 / 0.5 / 1, a constant \$2.019 per
  dollar, no residual; branch-and-bound gives 14,013.49 at s = 1. (`withMedicare="optimize"`
  alone ends on "unsolvable iterate" at s = 1, 7,238.50 with \$0 of LTCG tax, so it is no
  reference.)

The tax only pushed this case past the edge: the loop's plan without it leaves \$16,803 where local
search leaves \$31,778. For the pins, the \$21 is reproducible here, but it sits on the loop's
failure mode, so it may be the first value to move on MOSEK or another HiGHS. Options I see, your
call: keep it; pin john+sally under local search; or lower its `netSpending` so the shipped plan
is not at the edge (the description's numbers would change too). I changed nothing in the example.

**Checks:** `pytest -n 4`: 3232 passed, 1 skipped (default markers; rerun on the head with the MOSEK records emptied, the same); `pytest -m deep`: 5
passed. flake8 clean. Ruff: only the three B905 already on `dev` (`localsearch.py:194`,
`test_local_search.py`, `test_roth_maturation_losses.py:49`).

---

## Before opening (user)

- Decide whether to keep the john+sally paragraph's three options or name one.
- The `annual_cashflow_mix` change is beyond his list; it is flagged in the text, as is the
  taxes plot left for him to decide.
- Four commits: squash them if you prefer one (he squashed #222 on landing).

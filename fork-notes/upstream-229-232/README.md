# Upstream issues #229-#232 (filed 2026-10-26): validity and effect on the fork

Checked 2026-10-26 on `claude/clever-hypatia-6l8txj` (= `main`, upstream `dev` `4dcfabb` merged;
upstream `dev` and `main` are still at `4dcfabb`, so none of the four is fixed yet). All four were filed by
`rationalpiper` and have no comments yet. All four are about code that came from the fork and landed upstream:
the derived earnings `Plan._earnings_test_inputs` (#221 rule, read by the payroll tax of PR #228
and by the earnings test of PR #222), and `socialsecurity.earnings_test` (PR #222). The fork and
`dev` are identical in every function named below.

Issue texts were read through GitHub's web page (summarized by the fetch tool, not verbatim; the
GitHub API and github.com both answer 403 for upstream from this session).

**How each verdict was reached:**
- *Code*: the cited code read on this commit.
- *Repro*: the reporter's numbers reproduced here with our own script
  (`check_229_232.py`, output `check_229_232_2026-10-26.txt`), built from the issue's
  setup, not from the reporter's script (`docs/upstream/repro-v55-earnings-test.py` in their
  tree, not available here).
- *Recalled*: law cited by the reporter and not read from a source this session.

## Verdicts

| # | Claim | Verdict | Checked |
|---|---|---|---|
| 229 | The `omega_in > 0` gate drops the deferral in a year whose pay is all deferred (401(k), or a deductible IRA equal to the pay): $1 of wages turns on FICA and the earnings test for the whole deferral | **Valid** | Code (`plan.py` `_earnings_test_inputs`: `np.where(self.omega_in > 0, self.omega_in + deferred, 0.0)`); Repro: 0.00 / 1,797.83 (law 1,797.75) and 0.00 / 535.58 (law 535.50), as filed; 3121(v)(1)(A) recalled |
| 230 | Employer contributions in `401k ctrb` and nondeductible IRA contributions in `IRA ctrb` are counted as earnings | **Valid** (the first part is stated in our own docstring: "a plan whose 401k column includes one overstates the earnings by it") | Code (same line; docstring; `info/PARAMETERS.md:83` "Employer contributions are not subtracted", `:99` after-tax contributions stay in wages); Repro: +459.00 and +535.50, as filed; 3121(a)(5)(A) recalled |
| 231 | Exempt amounts after the table: 2026's nominal amounts are used as first-year dollars, so a plan starting 2027 loses a year of indexing; 2027 amounts (25,560 / 67,920) missing; adding 2027 as is would be inflated twice | **Valid** as to code and arithmetic; 2027 amounts **not verified** | Code (`_earningsTestResult` deflates earnings by `gamma`, `get_exempt_amounts` returns nominal table values, docstring says "today's dollars"); Repro: +540.00, +920.00, 234.72, and 318.78 (filed 318.77, a rounding difference); the 2027 notice (91 FR 67380) could not be fetched (federalregister.gov does not resolve, ssa.gov 403); the amounts divide by 12 into whole tens ($2,130 / $5,660), consistent with 403(f)(8)(B)'s rounding (recalled) |
| 232 | After the spouse's FRA, the worker's excess is charged on the spouse's pre-ARF add-on and the remainder rescaled: paid + withheld < benefits due | **Valid** | Code (charge loop on `paid_sp` before the ARF block; `paid_sp[i, k0:] *= new / old`); Repro: due 32,460.00 vs 31,649.89 (missing 810.11) and 32,760.00 vs 31,378.69 (missing 1,381.31), as filed; "due" computed independently from `getSelfFactor` / `getSpousalFactor` / `arf_spousal_factor` |

No claim found wrong.

## Notes beyond the issues

- **Our own test pins #229's behavior:** `tests/ss/test_earnings_test_plan.py::test_earnings_are_the_wages_before_pre_tax_deferrals`
  ends with "Without wages, contributions are not earnings" (`omega_in = 0` gives earnings 0).
  The gate is there for a spousal IRA (PARAMETERS.md:99: no wages, `IRA ctrb` plus a negative
  `other inc`). So #229's first fix (gate on `omega + kappa[:, 1]`) would count a spousal IRA as
  earnings unless it goes with the second (401(k) and IRA passed separately). From the arrays,
  "all pay to a deductible IRA" and "spousal IRA" look the same (zero wages, `IRA ctrb` > 0),
  apart from the negative `other inc` of the spousal case. A 401(k) deferral is always from pay,
  so it needs no gate at all.
- **#232 also falsifies a comment:** `socialsecurity.py:1268` ("ARF is effective only from the FRA
  month and charging never reaches that month") holds for the own benefit only. The reporter's
  first fix keeps the crediting months, which count only months before FRA
  (`withheld_sp[i, : pre_fra[i]]`).
- **#231 also covers a docstring:** `ExemptAmounts` says "today's dollars" and the table holds
  nominal amounts. The fork's comment above `_EXEMPT_TABLE` describes the after-2026 projection
  as a slight overstatement. That holds only for a plan starting in 2026.

## Effect on the fork

- **Examples:** none of the 19 examples has a year with zero wages and a 401k/IRA contribution
  (#229), or a worker over the exempt amount after a spouse's FRA while under their own FRA
  (#232) (`scan_examples.py`: a condition scan, not a run of a fixed version; the scan's
  condition was not itself tried on a positive case). #231 does not reach the tests (date frozen
  at 2026-01-01) but reaches every plan built on or after 2027-01-01. #230 cannot be read from
  the data (the examples do not say whether `401k ctrb` holds a match). So fixes to #229 and
  #232 should move only our gate test. #231 moves nothing pinned unless it changes the 2026 path.
- **Household (Phase 5 step 6):**
  - #229 matters if a last working year is all deferred.
  - #230 matters if the HFP puts the employer match in `401k ctrb`. Then the payroll tax is
    7.65% of the match too high, and the earnings test runs on the match if someone claims
    before FRA while working. A stopgap for the tax only: a positive `big-ticket items` entry
    of 7.65% of the match (below the wage base; untaxed cash).
  - #231 matters for any run made on or after 2027-01-01.
  - #232 matters only if one spouse draws a spousal add-on and the worker earns over the exempt
    amount after that spouse's FRA.
  - Whether the household's inputs meet these conditions cannot be checked here (`otherFiles/`).
- **Action:** none in code for now. The reporter's repros are correct. The maintainer fixed this
  reporter's #199-#217 himself within two days. When he fixes these, merge his version and drop
  our gate test if it conflicts. If the step-6 sweep has to run first on inputs that meet a
  condition, patch the fork then.

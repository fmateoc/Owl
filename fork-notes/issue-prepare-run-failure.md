# Issue draft: the interface solves a case whose configuration failed to apply

Status: **draft, not filed** (2026-11-07, UX review B3, `fork-notes/ux-review.md`). For the user
to file on `mdlacasse/Owl`. Checked on upstream `dev` `73dc8815` (2026-11-07). Patch:
`fork-notes/issue-prepare-run-failure.patch` (applies to stock `dev` with `git apply`; verified
there: `tests/ui` and `tests/tax/test_aca.py` 231 passed; the new test fails on stock `dev`).
Repro script: `fork-notes/issue-prepare-run-failure-repro.py` (run with the repo root as
argument). The output below is from real runs of that script in this container on stock `dev`
and on `dev` with the patch.

Revised 2026-11-07 (user): the first draft also proposed a new `setACA` hint for an ACA start
year before 2000 (1999 gave "e.g. 4025") and used 1999 as its trigger. Nobody enters 1999, so
that part is dropped, from the patch too, and the trigger is now a move to the starting state,
which Create Case warns about but accepts. The fork's `setACA` and `test_aca.py` are upstream's
again.

---

**Title:** UI solves a case after "Failed to apply configuration" and shows the old plan's results

**`ui/owlbridge.prepareRun` reports a failure, but every caller solves anyway.** `prepareRun`
catches the exception from `apply_config_to_plan`, shows *"Failed to apply configuration: ..."*
and returns. Its callers do not know: `runPlan` (owlbridge.py 214), `runHistorical` (267),
`runMC` (311), `runStochasticSpending` (611), `runSpendingBequestFrontier` (860) and
`runConversionRegret` (2662) go on and solve. The plan then holds only the part of the case
applied before the exception (`apply_config_to_plan` stops at the failing step), and the
Financial Profile tables are not applied at all: `_setContributions` comes after
`apply_config_to_plan` in `prepareRun`.

One way to get there: a case in CA with *Move to another state during the plan* on and FL as
the new state; then *State of residence* is set to FL too, to look at moving now. Create Case
warns *"The new state is the starting state."* but keeps both. On Reports, `setStateTax`
refuses the move, and the page shows the error above the results of a solve in CA, as the
case's results. Wages added on Financial Profile before that are missing from the results, and
Reports then applies them to the plan's tables after the solve (`saveContributions`), so the
workbook offered for download has them.

**Repro (stock `dev` `73dc8815`):** the script renders `ui/Reports.py` through Streamlit's
`AppTest` with `Case_dana.toml` (CA), *State of residence* FL, a move to FL in 2031 and \$50,000
of wages added for 2026, and counts `Plan.solve` calls. Click path: load dana; on Create Case
turn on the move with FL as the new state, then set the state of residence to FL; on Financial
Profile add \$50,000 of wages in 2026; open **Reports**.

```text
$ PYTHONPATH=$PWD/src python issue-prepare-run-failure-repro.py $PWD
solves: 1
caseStatus: solved
case: state FL; plan: state 'CA' moves []
results shown: total state income tax $29,910, total wages $0
2026 wages: case 50,000, plan's table after the page 50,000
error: Failed to apply configuration: Invalid state in config: The move goes to the starting state ('FL').
```

(FL has no income tax; the \$29,910 is CA's. With the same wage edit and the case left in CA
with no move, the same page shows total wages \$50,000: the \$0 above is the skipped tables.)

**With the patch:**

```text
solves: 0
caseStatus: invalid input
case: state FL; plan: state 'CA' moves []
2026 wages: case 50,000, plan's table after the page 0
error: The case was not solved: one of its inputs could not be applied. Invalid state in config: The move goes to the starting state ('FL').
```

**Patch (attached), minimal:**

- `prepareRun` returns `True`/`False`; the five clone-and-solve callers return when it is
  `False` (the error is shown once, as now).
- `runPlan` applies through a helper `_applyConfig` that returns the reason, records
  `caseStatus = "invalid input"` with the reason as `solverMessage`, and does not solve;
  `showCaseStatus` explains it, so Reports and Graphs show one message. `sskeys.caseHasNotRun`
  lists the new status, so the page does not also say the case definition is incomplete.
  Editing the input marks the case modified again, so the next visit re-runs it.
- New `tests/ui/test_prepare_run_failure.py`: Reports with the move above shows one error,
  calls `Plan.solve` zero times and records `invalid input`. It fails on stock `dev` (one
  solve) and passes with the patch.

Found by a review of the interface in our fork (`fmateoc/Owl`); the fork carries the same patch.

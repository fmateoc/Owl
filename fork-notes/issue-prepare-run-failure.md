# Issue draft: the interface solves a case whose configuration failed to apply

Status: **draft, not filed** (2026-11-07, UX review B3, `fork-notes/ux-review.md`). For the user
to file on `mdlacasse/Owl`. Checked on upstream `dev` `73dc8815` (2026-11-07). Patch:
`fork-notes/issue-prepare-run-failure.patch` (applies to stock `dev` with `git apply`; verified
there: `tests/ui` and `tests/tax/test_aca.py` 233 passed). Repro script:
`fork-notes/issue-prepare-run-failure-repro.py` (run with the repo root as argument). The
output below is from real runs of that script in this container on stock `dev` and on `dev`
with the patch (re-run 2026-11-07 after the script's label changed; upstream `dev` still `73dc8815`).

---

**Title:** UI solves a case after "Failed to apply configuration"; setACA's year hint says "e.g. 4025"

Two small things, found together.

**1. `ui/owlbridge.prepareRun` reports a failure but every caller solves anyway.**
`prepareRun` catches the exception from `apply_config_to_plan`, shows *"Failed to apply
configuration: ..."* and returns. Its callers do not know: `runPlan` (owlbridge.py 214),
`runHistorical` (267), `runMC` (311), `runStochasticSpending` (611),
`runSpendingBequestFrontier` (860) and `runConversionRegret` (2662) go on and solve. The plan
then holds only the part of the case applied before the exception: `apply_config_to_plan`
stops at the failing step, so with an ACA error `setStateTax` (the state and moves) and the
HFP contributions (`_setContributions`) are the previous run's or the defaults.

What a person sees depends on the case. On `Case_jack+jill.toml` with *ACA start year* set to
1999 (and a benchmark premium, so `setACA` runs), Reports shows the error and then the
results of the half-applied plan as solved. On a case with a purchase and a budget (our
synthetic household), the second message was *"No plan satisfies all the constraints. An
input has to give: ..."*, which points at the wrong input.

**2. `Plan.setACA`'s hint** for a start year before 2000 is `date.today().year + sy`, which
suits a small offset (3 -> 2029) but gives *"e.g. 4025"* for 1999.

**Repro (stock `dev` `73dc8815`):**

```text
$ PYTHONPATH=$PWD/src python issue-prepare-run-failure-repro.py $PWD
setACA error: setACA: start_year=1999 looks like an offset rather than a calendar year. Use a 4-digit calendar year (e.g. 4025).
solves: 1
caseStatus: solved
error: Failed to apply configuration: setACA: start_year=1999 looks like an offset rather than a calendar year. Use a 4-digit calendar year (e.g. 4025).
```

(The script renders `ui/Reports.py` through Streamlit's `AppTest` with jack+jill, `slcspAnnual`
20 and `acaStartYear` 1999, and counts `Plan.solve` calls. Click path: load jack+jill, set a
benchmark premium and *ACA start year* 1999 on the ACA settings, open **Reports**.)

**With the patch:**

```text
setACA error: setACA: start_year=1999 is before 2000. Use a 4-digit calendar year such as 2027.
solves: 0
caseStatus: invalid input
error: The case was not solved: one of its inputs could not be applied. start_year=1999 is before 2000. Use a 4-digit calendar year such as 2027.
```

**Patch (attached), minimal:**

- `prepareRun` returns `True`/`False`; the five clone-and-solve callers return when it is
  `False` (the error is shown once, as now).
- `runPlan` applies through a helper `_applyConfig` that returns the reason, records
  `caseStatus = "invalid input"` with the reason as `solverMessage`, and does not solve;
  `showCaseStatus` explains it, so Reports and Graphs show one message. `sskeys.caseHasNotRun`
  lists the new status, so the page does not also say the case definition is incomplete.
  Editing the input marks the case modified again, so the next visit re-runs it.
- The method name (`setACA: `) is dropped from the message shown on the page.
- `setACA`: the offset hint only below 100; from 100 to 1999 *"is before 2000. Use a 4-digit
  calendar year such as <next year>"*. `test_start_year_offset_raises_for_typical_offsets`
  is split accordingly (1-10 still "looks like an offset"; 100 and 1999 "is before 2000").
- New `tests/ui/test_prepare_run_failure.py`: the two hints, and Reports with 1999 shows one
  error and calls `Plan.solve` zero times. On stock `dev` two of its three tests fail (the old
  year's hint, and the Reports test: one solve); with the patch all three pass.

Found by a review of the interface in our fork (`fmateoc/Owl`); the fork carries the same patch.

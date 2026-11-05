# Run-library step 6: review of the second increment (2026-11-05)

Independent review of step 6's second increment on `claude/run-library-step6-inc2` at
`0964e351` (the `death` (I2) and `sequence` (I11) variant dimensions, member values and the
save dialogs' "Collection" field; the sensitivity tornado (I9); the conversion and bracket
view with the regret sweep (I8); the `ages_thorough` preset -- commits `0bc64ca0`..`0964e351`
from `main` `92daa09`), read against `run-library-design.md` sections 6.2-6.3, 7, 8.1, 9.1-9.3,
11, 14.1 and 14.3 (I2/I8/I9/I11), and the R2/R3/R4/T1/U7 rules. Findings **AE1-AE3**
(1 medium, 2 low, no nits worth a fold); prefix AE because AC and AD are taken (the core's
two reviews). None repeats an AC/AD item and none is a call the PROGRESS entry records as
the user's own (the death dimension's one person per action; the two-direction reversion
mover; the tornado children under the exact LP).

Environment: Windows, Python 3.14.7 (the repository `.venv`), MOSEK/HiGHS. Every probe wrote
only to the session's scratch folder (`probe1.py`); **nothing in `src/`, `ui/` or `tests/`
was changed by this review**. The tree under review also carries two commits this session
made before it (the `work_sweep` move `bc4e38ec` and the full-grid check's pool bound
`263def48`); the findings read the increment's own diffs (`git show 0bc64ca0..0964e351`).

## What was run

| Command | Result |
|---|---|
| `pytest tests/library tests/ui -q` | **825 passed, 1 skipped** (3:40; the move's run at `bc4e38ec`) |
| `pytest tests/library/test_tornado.py test_variants.py test_builder.py test_worker.py test_presets.py test_scenario.py tests/plan/test_brackets.py tests/tax/test_aca.py -q` | **308 passed** (3:32; the increment's own files) |
| full suite (`pytest -q -n 4`) | **4346 passed, 2 skipped** (14:39; the increment's 4345 + the move's one pin; contended by the overnight check) |
| `flake8` / `ruff` on the increment's touched files | clean |
| probes (`probe1.py`, below) | AE1 and AE2 reproduced; two other suspects cleared |
| `run_suite.py --jobs 2` on two condo rows (`suite_probe2.log`) | both solved (200.9 s / 371.9 s), the report and its checks written |
| `check_library_variants.py --full` | first attempt **failed** on the suite's own 16-job pool (`BrokenProcessPool`, 263def48 bounds it at 6); the bounded re-run is in flight, its result the acceptance |

## Findings

### AE1 (medium): a death at the person's age today passes `check_death_age`, and when it is the last death the plan refuses to build -- with a raw `ValueError`

`library.builder.check_death_age` refuses `int(age) < start - birth` ("a death before the
plan starts"), and that boundary is right per person -- a death at the age one is now is
still ahead, and it gives that person a one-year horizon ("life horizon from 2026 -> 2026").
But the increment's own text promises more: "not before the plan start (`check_death_age`:
a horizon of zero years would give the plan nothing to solve)". When the death at the
plan-start age is the **last** horizon (`basic_info.life_expectancy` `[62, 62]` for the
1964-born couple at plan year 2026, or a single person dying at their current age), the
plan that follows is one year long, and the model refuses it where it is built:
`ValueError: Plan needs more than 1 years.` (`Plan` requires `N_n > 1`) from deep inside
`config_to_plan`, not a `ScenarioError` with the window in the message.

Reachable from every death route: the Scenario page's death table (`_death_events` takes
any whole age and defers to the build), "make variants" with a `death` value at that age
for a single-person case (or a parent that already carries the other person's death), and
the tornado's "<person> dies at 80" for a person already past 80 is skipped correctly but
the boundary case is not covered.
The pages show it (their save handlers flash any exception -- `ui/Scenario.py` 394/482,
`ui/Collections.py` 242), but as "not saved (... Plan needs more than 1 years.)" -- an
unnamed model-internal error where the design names the refusal.

Probe (`probe1.py`): `check_death_age("Ari", 62)` accepted / 61 refused; `config_to_plan`
with `life_expectancy` `[62, 89]` builds (`N_n=28`, horizons `[1, 28]`), `[62, 63]` builds
(`N_n=2`), `[62, 62]` raises `ValueError: Plan needs more than 1 years.`

Suggested fold: check the window, not only the person. After the death events set `life`
in `build`, refuse `end_year <= start` (the plan needs more than one year) with the window
in the message -- that is the door every route passes -- and mirror it in
`variants._check_value` and `tornado._death` (compute the max horizon across people there)
so the tables refuse or skip at the cell, as `check_death_age` does today.

### AE2 (low): `member_values` accepts a dimension name it does not know

`ui/variant_tables.member_values` ("dimension: label" pairs, the Members section's "Values"
popover for a hand-added run) validates the `year` label but not the dimension:
`member_values("yaer: 2027; place: yonkers")` returns `{"yaer": "2027", "place": "yonkers"}`
(probe). The pair is stored as the member's values and takes part in the grid's keying
(`grid_layout`: "no dimension dropped"), so a typo places the member in a phantom
dimension and gives the grid a stray row or column. AD6's rule was the other way ("a typo
is refused, not cash"), and `claim`'s people and the sequences table's `kind` refuse
unknowns the same way.

Suggested fold: refuse `dim not in variants.DIMENSIONS` with the known list in the message
(the year's label rule stays as it is).

### AE3 (low): `regret.json` is a second copy of the summary, while the docs say the full curve lives there

`worker._regret_sweep` writes `summarize_conversion_regret(result)` to `regret.json` and
the same dict into `record.json`'s `regret`; the sweep's own result (`grid`, `v_star`,
`v_at`, `x_star`, the per-scenario regret curves of `stresstests.run_conversion_regret_sweep`)
is discarded. Three texts promise otherwise: `results.build_record`'s docstring ("its full
curve is `regret.json` beside the record"), the run page's caption ("the curves and the
per-scenario spread are in `regret.json` in this results folder"), and PROGRESS's own
entry ("`regret.json` joins the artifacts, the summary is in `record.json` (`regret`)").
The summary's `by_grid` carries per-grid-point statistics (mean/median/p90/max, infeasible
count, oscillation bar) and the valley/asymmetry/convergence blocks, but re-plotting the
curves or re-summarizing with other bands (`summarize_conversion_regret`'s docstring: "a
sweep saved before lifting summarizes the same as a new one") needs the per-scenario data,
which is 18 x 9 numbers and is not saved.

Suggested fold: write the sweep's result (or at least its per-scenario regret curves) to
`regret.json`, keep the summary in `record.json` -- or, if the summary is all that should
be kept, fix the three texts.

## Checked and not a finding

- **The rate movers' transforms** (`tornado._shift_rates`): for a hand table
  `builder.plan_rates_table` returns the file's rows and the child keeps
  `reverse_sequence`/`roll_sequence` (shifting commutes with both); for a generated path
  the rows are already reversed or rolled and the child resets the transforms to identity.
  Both branches shift the effective path exactly once (read against `builder._rates_table`
  / `_generated_rates`).
- **Two death events' provenance**: `basic_info.life_expectancy` records `deaths[0]["id"]`,
  which is the established pattern (`claims[0]["id"]`, `work_ids[0]`, `downs[0]["id"]`).
- **`_sequence_value`'s empty cells**: `records()` normalizes an empty `start` cell to
  `None`, so "no sequence but a placement" fires only on a real placement; a named sequence
  with no placement is refused (probe).
- **`aca_table_year`**: round-trips through both config bridges and `plan_to_config`, never
  writes `None` into the case dict (the round-trip suite's catch), and all five
  `acaCosts`/`acaVals` call sites pass it (`plan` x3, `explain`, `thresholds`). The mover's
  skip conditions (no benchmark premium, already pinned) and the medical cap (`le=10.0`)
  match the schema.
- **The claiming-age map's sources**: the run folder's `scores.json` first, then the newest
  results folder that has one (only "Ages, thorough" writes it), then a picked file (I7).
- **`compare.pair_tolerance`**'s public call shape matches `difference`'s own use.
- The tornado's bars sort by effect with the no-result rows last, and every mover that does
  not fit is skipped with its reason (the button handler also flashes per-mover save or
  queue failures).

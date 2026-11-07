# UX fixes: independent review of `claude/ux-fixes` (2026-11-07)

Independent review of branch `claude/ux-fixes` at `6396c755` (5 commits on `baf32e72`,
`claude/optimistic-mccarthy-pidkig`), against the work order `fork-notes/ux-fixes-handoff.md`,
the UX review `fork-notes/ux-review.md` and PROGRESS.md's "UX review: the four bugs" and "UX
review: quick wins Q1-Q9". Findings **AK1-AK7** (1 medium, 3 low, 3 nit); prefix AK after AJ.

Environment: Linux, Python 3.11 `.venv`, HiGHS only, Streamlit from the lock file.
**Nothing in `src/`, `ui/`, `tests/` or the docs was changed by this review** (only this file).
Probes are scripts in the session's scratchpad (`probes/test_probe_*.py`, `same_name.py`);
reverts were made in throw-away `git worktree`s (removed afterwards), with `PYTHONPATH` set to
the worktree's `src` and `owlplanner.__file__` checked.

## What was run

| Command | Result |
|---|---|
| `pytest -n 4 tests/library tests/ui tests/tax/test_aca.py` (HEAD) | **1003 passed** (1:44) |
| `flake8` / `ruff` on the branch's changed Python files | clean |
| `check_library_builder.py` | **46/46** |
| B3 patch on stock upstream `dev` `73dc8815` (fresh worktree, `git apply --check` then apply) | applies; `tests/ui/test_prepare_run_failure.py tests/tax/test_aca.py` **74 passed** there |
| `issue-prepare-run-failure-repro.py` on stock `dev` and on patched `dev` | output identical to the draft's two blocks (stock: "e.g. 4025", `solves: 1`, `caseStatus: solved`; patched: "such as 2027", `solves: 0`, `invalid input`) |
| Fail-before spot checks (reverting the fix hunk in a worktree) | B1: `test_decision_queues_its_exact_companion` fails (`['decision']`); Q8 test fails on the old Queue; B4 source check flags the old label; B2: 4 builder tests + the page refusal test fail with the builder hunks reverted; Q4 UI test fails with the old `a_idx`/`b_idx` |
| Not run | full suite (the author records 4459 passed / 1 skipped), `check_library_roundtrip.py`, `check_library_compare.py`, `check_library_jobs.py`, the Playwright journeys |

## Findings

### AK1 (medium): a purchase named like the hand home is not refused, and the plan silently keeps the old home's loan and down payment

`src/owlplanner/library/builder.py:1084` skips any hand Fixed Assets row whose name equals the
purchase's (`row[at["name"]] == purchase["name"]`), "the event's own row (kept by name from a
pages save)". But a hand row with the event's name is not only the event's own row: by design
(review X2, `casefiles._drop_generated`) a generated row **replaces a hand row of the same name**
(`_merge_tables`, builder.py:1153-1157). So an imported case whose home is `yonkers condo`,
plus a purchase event the user names `yonkers condo` (the page's "Home (the rows' name)" field
invites naming it after the condo), is not refused: the hand home row is replaced, while every
other hand row of the old purchase stays.

Reproduced (`same_name.py`): `import_case(Case_ari+noa_condo.toml,
HFP_ari+noa_condo_yonkers_2029_mortgage.xlsx)`, one purchase event `yonkers condo`, 2031, cash:

```text
BUILT Fixed Assets [[True, 'yonkers condo', 'residence', 2031, 803644, 803644]]
BUILT Debts [[True, 'yonkers mortgage', 'mortgage', 2029, 30, 608370]]
Ari [(2029, -187074), (2031, -803644)]
```

The plan pays the 2029 down payment and carries the 2029 mortgage on a home it buys for cash in
2031 (the hand owner's budget lines happen to share the generated names and are replaced; the
hand rent rows still end in 2028, so 2029-2030 have no housing cost). No warning. This is the
B2 trap (a) again, one text field away.

Fix: drop the name exception (no test needs it: the event's own rows are taken out of the hand
tables by `_drop_generated` on a pages save), or keep it only when the base scenario's
provenance marks that row as generated; otherwise refuse with the same message. A test: the
condo case + a purchase named `yonkers condo` is refused.

### AK2 (low): with *Move there* and another state, the page keeps the case's NY locality and district; the run fails only at solve time

`ui/Scenario.py:268-269`: `_choices(options, value)` appends the pre-filled value (from the
case: `Yonkers`, `City of Yonkers / Yonkers`) to the options whatever the State says, and the
stale-value check (`ui/Scenario.py:271-273`) therefore never fires for it. Reproduced
(`test_probe_page.py::test_state_change_with_move`, AppTest on a NY/Yonkers case): tick *Buy a
home*, tick *Move there*, type State `CT`:

```text
loc opts ['(none)', 'Yonkers'] Yonkers
dist opts ['(none)', 'City of Yonkers / Yonkers'] City of Yonkers / Yonkers
errors []
stored place {'locality': 'Yonkers', 'move': True, 'school_district': 'City of Yonkers / Yonkers', 'state': 'CT'}
moves [{'year': 2027, 'state': 'CT', 'locality': 'Yonkers', 'school_district': 'City of Yonkers / Yonkers'}]
```

The page saves and builds; the solve then stops in `residency.normalize` with
"Unknown locality 'Yonkers' for state 'CT'. Known: none." (verified by calling it). Before the
branch the fields were blank free text, so this is a side effect of the pre-fill.

Fix: append the event's own value only when it belongs to the state shown (or when it is the
event's stored value for that same state), so a state change resets both pickers to "(none)";
and/or validate a move's place in the builder (`residency.normalize` -> `ScenarioError`), so
the page says "Not buildable yet".

### AK3 (low): a hand home with a blank `year`, or a table without `year`/`yod` columns, escapes the second-home refusal

`builder.py:1087`: `int(row[at["year"]])` raises on `None`/NaN and the row is skipped
(`continue`); `builder.py:1076` returns without any check when the table lacks one of
`name, type, year, yod`. But `fixedassets._get_reference_year` reads a blank `year` as the plan's
first year ("for backward compatibility"), i.e. a home owned now. Reproduced
(`test_probe_builder.py`): a hand residence with `year` `None` or `nan`, `yod` 0, plus a 2027
purchase builds `['old', 'yonkers condo']`, two homes. The missing-column branch is inferred
from reading (not checked how `hfp_io` fills an old workbook's absent columns).

Fix: read the reference year as `fixedassets` does (blank -> plan start) and skip only rows
whose `type` is not a residence; treat a missing `year` column the same way.

### AK4 (low): old scenarios whose purchase stored a blank district meaning "none" change meaning without a migration

Before this branch a variants-table `-` was stored as `""` (`ui/variant_tables.py`, old
`_place_value`), and a blank district on a no-move purchase built `school_district = ""`. With
`BUILDER_VERSION` 6 the same stored `""` builds the case's district. The bump makes such runs
"built with an older builder" (their frozen files are untouched), but nothing rewrites the
stored scenario: opening such a run on the Scenario page shows the case's district, the
change line says "none yet" (verified for a blank district: `test_probe_resave.py`, first
case), and *Save as a new run* or *Make variants* from it builds a child **with** a district its
parent did not have. Inferred for the old-variant origin (no pre-branch library was at hand);
the page behaviour verified. Small in practice (the synthetic grid states every district).

Fix: a scenario migration is overkill for this; a line in design 6.2 / the changelog that a
pre-6 purchase with a blank district now keeps the case's would do, or the page could note
"built with an older builder: the district rule changed" for a pre-6 run with such an event.

### AK5 (nit): `active` = 0 counts as active in the check, inactive in the model

`builder.py:1082` skips only `is False`; `utils.is_row_active` (used by `fixedassets`) treats any
falsy value (0) as inactive. Reproduced: an `active` 0 hand home is refused ("the case already
holds a home"). Use `not utils.is_row_active`-style logic (None/NaN active, falsy inactive).

### AK6 (nit): the State field's upper-casing is a phantom edit for a stored lowercase state

`ui/Scenario.py:262` now `.strip().upper()`s the State. An event stored with `"state": "ny"`
(typed in a variants table, say) shows a change with no edit. Reproduced
(`test_probe_resave.py`, fourth case): "Changes against this run: purchase: ... ->
... (place.state: removed (was 'ny'))". Keep the event's spelling when the upper-cased forms
match, as `_place_to_store` does for the district.

### AK7 (nit): documentation wording

- `fork-notes/CHANGELOG-fork.md`: "Runs built before carry an older builder version (6)" reads
  as if the old runs carry 6; they carry 5 or older, the builder is now 6.
- The changelog's "(Q9; inputs hashes unchanged)" and CLAUDE.md's "no inputs hash moves" are
  true of Q9 only. The same branch's B2 bump changes **every** run's inputs hash
  (`scenario_hash` includes `builder_version` for all scenarios, events or not), so a save of an
  unchanged pre-branch scenario is no longer found as identical to its run. That is R9 working
  as designed, but the sentence invites the opposite reading; say "Q9 moves no hash; the
  builder bump (B2) moves all of them, as every bump does".
- `run-library-design.md` 6.2: "the event's own row (kept by name from a pages save) [is]
  allowed" -- see AK1: any hand row of that name is allowed, and replaced.
- The repro script prints `setACA: setACA: start_year=...` (its own label plus the message's
  prefix); harmless, but the issue text pastes it as is -- a label like `setACA error:` would
  read better.

## Checked and fine

- **B1.** `ui/Queue.py` loops over `preset_solves` and flashes `ScenarioError`/`JobsError`;
  the existing "another plan year" test still sees its error after the rerun. A failure on the
  second solve leaves the first queued (same as the Run page).
- **B2 semantics otherwise.** Overlap test `start < yod and bought < sale` matches
  `fixedassets` (disposal at the start of `yod`; zero/negative from the plan end, `end + yod +
  1`): probes for `yod` -1 (refused, "sold in 2053"), 2027 = purchase year (allowed), 2028
  (refused), a hand home bought in or after the event's sale year (allowed) all behave as the
  design says. `place_text`/`NO_PLACE` for moves (blank or `-` = none) and no-move purchases
  (blank keeps, `-` = none) as documented; the variants table stores a cleared district as `-`
  and a cleared locality as blank. `_place_to_store`: unedited saves of an existing event with
  a blank district, a `-` district, and a move to White Plains report "none yet" (probe); a new
  purchase saved unedited keeps the case's district (test and probe). `BUILDER_VERSION` 6 is
  justified (built output changes for a blank no-move district) and sufficient for the
  frozen-file R9 rule. `check_library_builder.py` 46/46.
- **B3.** The patch is byte-for-byte the fork's change to `owlbridge.py`, `sskeys.py` and
  `plan.py`, applies to stock `dev` `73dc8815`, and its tests pass there; the draft's line
  numbers (214, 267, 311, 611, 860, 2662) match stock `dev`. Every `prepareRun` caller stops
  (five clone-and-solve callers; `runPlan` through `_applyConfig`; `runAllCases` goes through
  `runPlan`). `"invalid input"`: `caseHasNotRun` lists it, `isCaseUnsolved` routes Reports,
  Graphs and Worksheets to `showCaseStatus`, which explains it; no other `ui/` code interprets
  `caseStatus` values beyond `== "solved"`. Not stuck: every page edit goes through
  `setCaseKey` -> `flagModified` -> `"modified"`, so the next visit re-runs. `setACA`'s two
  hints as described.
- **B4.** The source check catches the old label (verified); its blind spots are labels built
  in variables (e.g. `librarypresets.HELP`, `PATH_LABELS`), none of which holds two `$`.
- **Q1.** Grep of the six pages, `variant_tables.py`, `librarypresets.py`, `libraryjobs.py` and
  the library modules' raised/appended messages: the remaining codes and file names are in
  comments and docstrings only; `scores.json` / `work_sweep.py --json` only in the uploader's
  tooltip.
- **Q2.** `librarypresets.select` returns ids; toggling *Expert presets* off while `custom` is
  selected falls back to `quick` with no exception (AppTest probe). Every page that shows a
  preset uses `librarypresets.name`; none compares display names. No test covers the toggle
  (the probe did).
- **Q4.** `default_pair`: B the newest main solved result, A the newest main result of B's
  parent, else another run, else another result of B's run; never B; ties by page order,
  missing times last; companions and unsolved results excluded.
- **Q6.** The four `by_year` charts say nominal; the brackets and regret charts keep their
  correct today's-$ titles; *What moved* has the separators, `hide_index` and the heading.
- **Q7.** `claiming_ages_how` handles a list, a name string, `"optimize"` and absent
  (= fixed); `_frozen_solver_options` reads `inputs/Case.toml` (TOML and decode errors are
  `ValueError`s). `spent_down_by_design` only under maxSpending with a zero bequest target.
- **Q8.** States match `results.py` (`waiting`, `running`, `done`, `failed`, `interrupted`);
  "Waiting for another solve to finish" is right for `max_parallel` 1 (the default); the
  local-search regex matches `localsearch.py:263`'s message.
- **Q9.** `NO_OP_DEFAULTS` match `plan.py` (`noLateSurplus` False at 5069, `timePreference`
  0.0 at 6131, `spendingSlack` 0 at 6857). A non-default (True, a non-zero) is still shown;
  an int 0 for `noLateSurplus` or `False` for `spendingSlack` is shown rather than hidden
  (errs toward showing). `scenario_from_ui` is unchanged.
- **Privacy.** Only the synthetic household and upstream's examples appear.

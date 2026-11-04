# Run-library build step 5b: independent review (2026-11-04)

Reviewed: commits `c99d3551` ("[feat] Run-library step 5b: a rates CSV the case names, read by a
new rate method") and `44676043` ("[feat] Run-library step 5b: the acceptance check and the
docs") on branch `claude/run-library-step5b`, against `main` (`43fa1b13`), i.e. `git diff main`
(26 files): `src/owlplanner/rate_models/table.py`, `plan.py`, `rate_models/{constants,loader}.py`,
`config/{plan_bridge,ui_bridge,schema}.py`, `library/{builder,casefiles,scenario,sequences}.py`,
`data/downturn_sequences.toml`, `ui/{Rates,Scenario,owlbridge,Documentation}.py`,
`fork-notes/synthetic/check_library_rates.py`, the two new test files, and the docs
(`PROGRESS.md`, `fork-notes/CHANGELOG-fork.md`, `fork-notes/run-library-design.md` sections 5,
6.2, 6.3a, `info/PARAMETERS.md`, `info/RATE_MODELS.md`, `CLAUDE.md`). Read against the design's
sections 5, 6.1-6.4, 7, 8.2-8.3, 9.1, 11 (the step-5b row), 14.1 (I11), 15 (D11), the PROGRESS
entry "Run-library step 5b", and the house reviews (`run-library-step5-review.md` W1-W8,
`run-library-step5-review-2.md` Y1-Y5). Windows, Python 3.14.7 (`.venv`, editable install
confirmed to point at `C:\Projects\Owl\src`), HiGHS only. Nothing in the repository was changed
except this file; every probe ran from `C:\Users\fmate\AppData\Local\Temp\opencode\` and wrote
only to temp directories.

The step's recorded decisions are taken as given and judged only as implementations: the
sequence fills only its window and the years outside keep the run's own rate method (baseline +
overlay); the pages get safety + Scenario rows only (no Rates-page table editor); one downturn
event per run; a hand table and a downturn event refuse to coexist.

## What was run

| Command | Result |
|---|---|
| `.venv\Scripts\python -m pytest tests/rate_models tests/library tests/config tests/ui -q -p no:cacheprovider -n 4` | **1204 passed, 1 skipped** (111 s) — the step's 42 new tests included and green |
| `.venv\Scripts\python -m pytest tests/rate_models/test_rate_model_table.py tests/library/test_rates_table.py --collect-only -q` | **42 tests collected** (20 + 22) — the count claim holds |
| `.venv\Scripts\python fork-notes\synthetic\check_library_rates.py` | **11/11 step-5b checks pass** — PROGRESS's acceptance claim reproduces |
| `.venv\Scripts\python -m flake8 src tests ui --max-line-length=120` | only upstream's known `stochastic` E301/E304 |
| `.venv\Scripts\python -m ruff check src tests ui` | the four known upstream B905s (`localsearch.py:244`, `tests/plan/test_local_search.py:288`, `tests/plan/test_roth_maturation_losses.py:49`, `ui/Run_Options.py:260`) |

The full suite (PROGRESS: "4094 passed, 2 skipped") was **not** re-run (the brief excludes it);
the four suites the step touches are green.

Probes (all under `C:\Users\fmate\AppData\Local\Temp\opencode\`, none in the repo):

- `probe_review_z1.py` — a changed `rates.csv` against a plan that already read it
  (`apply_config_to_plan`, `plan.setRates`, a fresh plan as contrast).
- `probe_review_z2.py` — determinism of `builder.rates_table` / `export_case` for stochastic
  baselines (`reproducible_rates` with and without `rate_seed`), recording every
  `rates_table()` call inside one export.
- `probe_review_z3.py` — the Import-tab upload set (no rates file) through `import_case`, and
  `scenario_from_ui(base=None)` on a table case whose plan holds the rows.
- `probe_review_z4.py` — downturn placements at 2020, 2024, 2069, 2075 and at anchor
  `age:Jack:60`, compared row by row against the un-overlaid baseline.
- `probe_review_z5.py` — `method = "table"` with no `rates_file`; a BOM CSV (Excel's "CSV
  UTF-8"); `nan` / `inf` cells through `read_rates_csv`, `config_to_plan` and `import_case`.
- `probe_review_z6.py` — T1 re-import of a downturn run's frozen files; the sequence window
  edited in place (hash vs generated table); `sequences()`' `lru_cache` after an edit.
- `probe_review_z7.py` — AppTest of `ui/Rates.py` on a table case (read-only block, case keys
  and `ui_to_config` after two visits; and the pathological state with no `rateType` key).

## Findings

| # | Severity | What / why | Evidence | Code location | Recommendation |
|---|---|---|---|---|---|
| Z1 | **medium** | **A plan that has read a rates table never reads it again: a changed `rates.csv` is silently replaced by the in-memory rows.** The reuse is unconditional — `setRates` copies `old.rows` whenever the previous model is a table with the same file name, without trying the file — so a long-lived plan (the interface's session) solves with the old numbers while `owlcli run` and the worker of the same frozen inputs read the new ones. | `probe_review_z1.py`: `1) first read : 2027 rate = -0.3`; after the file is edited to -55.0, `2) after apply_config_to_plan: 2027 rate = -0.3`, `3) after plan.setRates again : 2027 rate = -0.3`, `STALE ROWS WIN, FILE IGNORED: True`, contrast `4) a fresh plan reads the file: 2027 rate = -0.55`. | `src/owlplanner/plan.py:1822-1832` (the fallback, whose comment says "cannot re-read"); `config/plan_bridge.py:210-212`; `ui/owlbridge.py:965-973` | Try the file first when `base_dir` resolves, and fall back to `old.rows` only when it cannot be read (the existing test `test_a_plan_that_cannot_re_read_the_file_reuses_its_rows` passes either way). Correct the comment and PROGRESS's "cannot re-read" wording. |
| Z2 | **medium** | **With `reproducible_rates = true` and no `rate_seed`, one export freezes a `rates.csv` that is not the rate path its own workbook was priced with, and re-exporting the same scenario writes different frozen files.** The X3 guard's message says "unless the case fixes its seed" but it checks `plan.reproducibleRates`; `setReproducible(True, None)` mints a fresh time-based seed per plan build, and `build()` and `export_case` each compute the table from a new throwaway plan. | `probe_review_z2.py`: `two rates_table() calls equal: False (2027: 18.435 vs 12.4531)`; `one export: build() saw 2 table(s); written csv == build()'s table: False` (`build=[2026.0, -7.7387, ...] csv=[2026.0, 9.2369, ...]`); `two exports write the same rates.csv: False`; with `rate_seed=42` everything is equal. | `src/owlplanner/library/builder.py:531` (the guard), `:629` and `casefiles.py:811` (two computations of one table), `plan.py:1724-1731` (the time-based seed) | Require a fixed `rate_seed` (or any deterministic method) in `_throwaway_plan`'s guard, matching its own message; and have `export_case` write the table `build()` used instead of recomputing it. Design 6.2's "the pure function" / "deterministic" wording holds only then. |
| Z3 | **low** | **The two table workflows the interface's own text recommends both dead-end.** "Import a case" uploads only the case, workbook and budget file (no rates-file uploader and no `rates_path=`), so a hand-table case cannot enter the library through the pages; and "Save the current case" of a table case not opened from a run is refused with "import the CSV beside the case file" — an action the pages cannot perform — although the plan holds the table in memory. The Rates page's caption recommends exactly these two routes ("import a case with another table", "edit the scenario's downturn event"; the second is refused for a hand table: "a hand table and a downturn event refuse to coexist"). | `probe_review_z3.py`: `(a) import without the CSV refused: FileNotFoundError: Rates table 'rates.csv' not found or beside the case file (...)`; `(b) the plan holds 45 rows in memory` / `(b) save with base=None refused: the case names a rate table ... but the scenario holds none: import the CSV beside the case file`. Grep: `import_case(..., rates_path=)` has no caller in `ui/`. | `ui/Library.py:144-148` (the uploaders), `:84-85` (the import call); `library/casefiles.py:490` (`rates_table` only from `base`); `ui/Rates.py:115-118` (the caption); `library/scenario.py:148-153` | Add a rates-file uploader beside the budget one (passing `rates_path=`), and take `rates_table` from `plan.rateModel.rows` in `scenario_from_ui` when there is no base; until then fix the caption to name what the pages can actually do. (Not a table editor — the recorded decision stands.) |
| Z4 | **low** | **A downturn placement that reaches outside the plan is silently truncated, and one that misses it entirely silently does nothing.** The overlay skips any window year the plan does not cover with no warning (`if row is not None: ...`), and neither `validate_events` nor the Scenario page bounds the placement; a natural anchor that lands before the plan start produces a run whose "downturn" is the baseline — the stress question is silently unasked while the event is recorded as if applied. | `probe_review_z4.py`: `placement 2020: years changed vs baseline = []  <-- event has no effect at all` (same for 2069 and 2075); `placement 2024: years changed = [2026]` (a 3-year window, one year applied); `anchor age:Jack:60 (Jack born 1963 -> 2023): years changed = []`; `validate_events accepts start=2020 (no plan in scope): yes`. | `src/owlplanner/library/builder.py:607-610` (the skip), `:397-401` (any year accepted), `:450-468` (`resolve_years`, unbounded) | At `rates_table()` — where the plan's years are known — raise when no window year lands in the plan and warn (or raise) on a partial overlap; the past-the-end truncation can stay the documented "simply not used". |
| Z5 | **low** | **`method = "table"` with no `rates_file` fails with a bare `KeyError: 'rates_file'`.** The schema declares the field Optional and `from_config` indexes it unconditionally, so the error names no cause and contradicts `info/PARAMETERS.md`, which presents `rates_file` as the table's parameter. | `probe_review_z5.py`: `(a) no rates_file -> KeyError: 'rates_file'` (through `config_to_plan` → `_apply_rates_to_plan` → `from_config`). | `src/owlplanner/rate_models/table.py:1441` (`section["rates_file"]`), `config/schema.py:195-198` (Optional), `config/plan_bridge.py:210` | Validate `rates_file` where the model declares it `required_parameters` (or raise a named ValueError in `from_config`, as `generate` does for `start_year`). |
| Z6 | **low** | **The CSV reader's hostile-input surface: an Excel BOM is refused with a misleading message, and `nan` / `inf` cells pass silently into the plan on the plain case path.** A hand table is most naturally authored in Excel ("CSV UTF-8" writes a BOM); the reader then reports "missing the column(s) ['year']" while the header visibly reads `year`. `float()` accepts `nan`, `inf` and `1e999`, so `owlcli run` of such a case builds a plan whose `tau_kn` is nan with no complaint; the library catches the same cell at import but only as "not a number: None" (its NaN→None normalize runs before the check). | `probe_review_z5.py`: `(b) BOM csv -> ValueError: ... is missing the column(s) ['year'] ...`; `(c) read_rates_csv on a 'nan' cell: row 2027 = [2027, nan, 4.5, 3.0, 2.5]  (no complaint)`; `(c) plain case path: plan.tau_kn[0,1] = nan`; `(c) library import refused: ScenarioError: rates_table row 1: not a number: None`; `inf` likewise. | `src/owlplanner/rate_models/table.py:1357-1379` (header and `float()`); `library/scenario.py:49-50` (normalize), `:162-164` (the message) | Open the file with `utf-8-sig`, and reject non-finite values in `read_rates_csv` (named row and cell), which fixes both the plan path and the library's confusing message. |
| Z7 | **low** | **The sequence window is an input the inputs hash does not see.** A scenario records a downturn event's sequence *name* and placement, not its window; editing `data/downturn_sequences.toml` (or shipping a fix to it) changes the generated `rates.csv` while `scenario_hash` stays equal, so two runs can share a hash with different frozen files and `save_run`'s "identical to X" duplicate check refuses the second scenario. `sequences()` is also `lru_cache`d, so a long-lived server keeps generating from the old window after the edit. `BUILDER_VERSION` covers builder code but not this data file. | `probe_review_z6.py`: `(b) scenario_hash before/after the window edit equal: True`; `generated 2030 row before: [2030, -30.0, ...]` vs `after : [2030, -45.0, ...]`; `cached window after an edit is the old one: True`. (The solve itself is safe: grep shows `sequences()` is read only by `builder`/`Scenario.py`, never by the worker — the frozen `rates.csv` is what a solve reads.) | `src/owlplanner/library/sequences.py:19` (`lru_cache`), `:14`; `scenario.py:73-76` (the hash), `:38` (`BUILDER_VERSION`); `store.py:410-412` ("identical to") | Treat the data file as builder input: fold a hash of the windows into `scenario_hash` (or a `SEQUENCES_VERSION` into the builder version), and say in the design's section 5 which of the two it is. |
| Z8 | **low** | **The acceptance record overstates what was compared: T1 does not hold for the downturn run, and the check never compares `summary.json` metrics.** PROGRESS's acceptance bullet reads "for a downturn run and a hand-table run alike; ... re-importing the frozen files gives the run's own inputs hash (T1)", but the check tests T1 on the hand-table run only, and for a downturn run it fails: the frozen files carry the generated table and no events, so the re-import is a different scenario. The check's own docstring says the two solves "agree ... and the run's `summary.json` metrics"; the code compares only `plan.json` (nulling `solve_time_seconds`) and checks `summary.json` for one key's existence. | `probe_review_z6.py`: `(a) downturn run hash: e9914cedbd23e624` vs `(a) re-imported files' hash: 0b2b770d931967da`, `T1 holds: False`, `re-imported scenario has events: False, has rates_table: True`. `check_library_rates.py:311-317` (`_same_plan`, `plan.json` only) and `:386-390` (the summary existence check). The check run itself: `11/11 step-5b checks pass`, `the solve wrote summary.json metrics: 61 metrics`. | `fork-notes/synthetic/check_library_rates.py:8-13` (docstring), `:386-390`; `PROGRESS.md` "Run-library step 5b", the acceptance bullet | Scope the bullet to the hand table (events are lost to every re-import by design, step 4 onward), and either compare the summary metrics the docstring names or drop the phrase. |
| Z9 | nit | **Comment drift:** `canonicalize`'s inline comment still says "stored scenarios are current-version (2, with events)" on a schema-v3 build. | Read: `src/owlplanner/library/casefiles.py:172` vs `scenario.py:30` (`SCHEMA_VERSION = 3`). | `src/owlplanner/library/casefiles.py:172` | "(3, with events)" — or point at `SCHEMA_VERSION`. |

## Claims checked (verified, worth recording)

- **The acceptance check reproduces exactly as claimed** (verified): `check_library_rates.py`
  on the synthetic household prints 11/11, including `owlcli run` from another working
  directory reproducing the worker's `plan.json` for the downturn and the hand-table runs, the
  window at its placement with the baseline outside it (`row 2030 = ['-9.03', '9.38', '16.66',
  '3.39'], row 2029 = ['6.0', '4.0', '3.3', '2.8']`), `record.json`'s `rates.method = "table"`,
  and byte-identical `rates.csv` on re-export. The timing null is honest (`_same_plan` pops
  exactly `solve_time_seconds`). The hand-table path is the real library path
  (`import_case` → `save_run` → worker → `owlcli`).
- **"The pages keep a table case intact" holds on a real render** (verified, `probe_review_z7.py`):
  AppTest of `Rates.py` on a table case shows the read-only block (`Rates from a Table`), leaves
  `rateType = "table"`, `plan.rateMethod = "table"` and the rates untouched, and `ui_to_config`
  still writes `method = "table"` + `rates_file = "rates.csv"` after two visits (the
  `runOncePerCase(initRates)` → `_setRates("table", ...)` path included). The unit-level claim
  is also pinned by `test_a_pages_save_keeps_the_table` (hash equality after a pages save) and
  `test_a_pages_save_keeps_the_downturn_events` (events kept, no `rates_table` stored).
- **The recorded decisions are implemented as stated** (verified): the overlay fills only its
  window on the case's own rate path (`test_the_window_sits_at_the_placement_and_the_baseline_elsewhere`,
  `test_the_overlay_sits_on_the_cases_own_rates`); one downturn event per scenario
  (`builder.py:421-423`); a hand table and an event refuse to coexist with the "drop one"
  message (`builder.py:556-559`, test); a sequence over a `table` case is refused
  (`builder.py:591-595`, test).
- **Schema v2 runs stay readable** (verified via the step's tests): `validate` accepts
  versions 1-3 (`test_v2_stays_readable`), `migrate` 2→3 keeps events
  (`test_v2_keeps_its_events`), and the hash change on re-import is recorded in PROGRESS ("the
  schema bump means re-importing a run saved before step 5b gives a new hash", like v1→v2).
- **`to_config`/`from_config` round trip and the units** (verified): only `rates_file` and
  `in_percent` reach the case file (`test_config_round_trip_keeps_only_the_file_name`), percent
  in / decimal out by year (`test_rows_are_matched_to_years`, `test_in_percent_false_keeps_the_values`),
  rows any order, extra columns ignored, missing/duplicate years named
  (`test_missing_years_are_named`, `test_a_duplicate_year_is_an_error`). `in_percent` works
  through `extra="allow"` although the schema does not declare it (`schema.py:180`); harmless,
  but PARAMETERS.md documents it as a parameter while `rates_file` is declared — worth one line
  if the schema is touched again.
- **File resolution order** (verified): `TableRateModel._read_rows` tries the name as given
  (CWD) then beside the case (`plan.py:1827`'s `_config_dir`), the same order as the HFP
  workbook (`plan_bridge.py:398-401`) and the budget sidecar (`casefiles.py:649-662`), so
  PROGRESS's "CWD-then-beside-the-case (the HFP workbook's order)" is accurate. (The docs'
  shorthand "beside the case file (as the HFP workbook is)" omits the CWD-first shadowing
  hazard; consistent with the neighbours, so not a finding.)
- **An edited `downturn_sequences.toml` between save and solve cannot change a solve**
  (verified by grep): `sequences()` is read only by `library/builder.py`, `ui/Scenario.py` and
  the check; the worker and `owlcli` read the frozen `rates.csv`. Editing the file does affect
  later exports (Z7).
- **Lint and test-count claims** (verified): 42 new tests collected (20 + 22); flake8 and ruff
  show only the upstream's known items listed in CLAUDE.md.
- **Design amendments are accurate** (verified against the code): section 5's `rates.csv` line,
  6.2's paragraph (the table is named in the generated case with provenance only when an event
  generates it — `builder.py:629-635`; nominal amounts from the table's inflation —
  `builder.py:673`), and 6.3a's version history all match. The one overreach is 6.2's "the pure
  function" (Z2).

## Unverified / to check

- **What a solve does with `nan` rates** (Z6's downstream): `probe_review_z5.py` shows `nan`
  reaching `plan.tau_kn` silently through the plain case path; whether HiGHS then refuses,
  crashes or returns a garbage plan was not run (a solve with nan coefficients is a poor use of
  the remaining budget). The fix does not depend on the answer.
- **Reachability of the selector-reset state** (the brief's "does it bite in some state"):
  `probe_review_z7.py` case 3 shows that a Rates-page visit with *no* `rateType` key rewrites a
  table plan to `historical_average` (the old hazard, real in that state), but every real
  entrance into the pages sets the key — `config_to_ui` (`ui_bridge.py:448-451`) and `genDic`
  (`owlbridge.py:2232-2236`) — and both unit and AppTest paths keep it. Whether any third path
  builds case keys without going through either was not exhaustively traced (cf. step-5 review
  W6's "defense in depth" disposition).
- **A year boundary in anger**: the generate/solve pairing is enforced by `check_plan_year`
  (code and tests) and every probe ran inside one year; a run exported on Dec 31 and solved on
  Jan 1 is refused by that rule rather than exercised here.
- The full-suite count (4094 passed / 2 skipped) is taken on trust; the four touched suites
  were re-run green.

## What the step gets right

The step delivers its contract cleanly: one new rate method with a narrow, tested surface
(year-keyed rows, percent units, named error paths), a schema bump with a migration, and the
downturn overlay implemented exactly as the user decided it — the case's own rate path, the
sequence's window at its placement, the two refusals in place — with provenance and the pages
save round-tripping to the same inputs hash. The frozen-files story works end to end: the
acceptance check really does show `owlcli run` of the frozen inputs reproducing the worker's
solve for both a generated and a hand table, and the pages keep a table case intact on a real
render. The 42 new tests are pointed and cover the units, the refusals and the round trips,
and the docs track the code closely outside the acceptance wording flagged in Z8.

## Verdict

A careful, well-tested step whose main paths do what the design says; fix the stale-rows
override (Z1) and the seedless-stochastic export (Z2) — and warn on a no-op downturn placement
(Z4) — before step 6 builds variant grids on top of the generated table.

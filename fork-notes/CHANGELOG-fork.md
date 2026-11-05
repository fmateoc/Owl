# Fork changelog (`fmateoc/Owl`; not part of upstream)

Moved here from the top of `CHANGELOG.md` on 2026-10-25, so that `CHANGELOG.md` stays upstream's
and stops conflicting at every sync (upstream edits its top on nearly every commit). New fork
entries go here. Not complete: Phase 5 (the payroll tax, the earnings test, which upstream now
has) is logged in `PROGRESS.md` only.

## Unreleased

### Run library, build step 6, second increment: I8, I9, the I2/I11 dimensions and the leftovers (2026-11-05)

The second increment of step 6 (`fork-notes/run-library-design.md` 8.1, 9.3, 14.1, 14.3):
the core's "left for the next increment" list -- I8, I9, the I2/I11 variant dimensions,
"Ages, thorough", member values for hand-added runs and the save dialog's "Collection"
field. The user's calls: the full list, this agent's build order; "the 2027 marketplace
benchmark" mover is **both** the ACA-rules mover and a benchmark-premium mover, and "the
2032 reversion" mover is **both** directions.
- **The `death` (I2) and `sequence` (I11) variant dimensions** (`library.variants`):
  `death` is {"person", "age"} -- one child per value ("Ari dies at 75", each spouse in
  turn) -- and a `death` event kind in the builder gives `basic_info.life_expectancy` (a
  generated case field, provenance marked; one per person, a whole age 1-120 and not before
  the plan start). `sequence` is {"sequence", "start"}: the named downturn overlay placed at
  a year or an anchor (step 5b's `downturn` event, one per scenario; `sequence: None` takes
  the overlay off, the grid's "no downturn" cell). The Collections page edits both, the
  Scenario page keeps a run's death events (a table, as claims).
- **Member values by hand** and the save dialogs' **"Collection"** field (design section 7):
  a hand-added member's `{dimension: label}` pairs are set in its "Values" popover
  (`ui/variant_tables.member_values`), and the Library and Scenario save dialogs can put the
  saved run into a collection as it is.
- **The sensitivity tornado (I9)** (`library.tornado`, one button on the run page): one
  child per key input moved by a set step -- returns -1 point, inflation +1 point, medical
  inflation +2 points, condo price +10%, the marketplace benchmark premium +10% / -10%,
  the 2027 marketplace rules, the 2032 reversion and no reversion, and the first death at 80
  per person -- each queued under the exact LP ("for speed") into a "Sensitivity: <run>"
  collection, and bars sorted by the size of the effect, each with its tolerance (R2). A
  mover that does not fit the scenario is skipped with its reason. The rate movers write the
  run's own rate path out as a shifted `rates_table` (a downturn overlay baked in; AB1's
  transform reset); the marketplace-rules mover pins `aca_settings.aca_table_year`, a small
  generic model knob (`tax_federal._aca_table`'s `table_year` through `acaCosts`/`acaVals`,
  `plan.aca_table_year`, the config bridges).
- **The conversion and bracket view (I8)** (`owlplanner.brackets`, in `plan.json`'s
  `brackets` block; D7): per year, the ordinary taxable income, the Roth conversion layer
  and MAGI against the ordinary bracket edges (the bracket it fills, the room to the next),
  the 0% gains edge, the IRMAA tier edges (the premium year m+2's, in the tax year's
  dollars) and the ACA lines (the Medicaid limit, where the credit starts, the 400% FPL
  cliff). The run page draws it (bars + the lines stepped over them, and a table) and its
  **regret sweep** button queues one `regret` job per request: the base solve, then
  `stresstests.run_conversion_regret_sweep` at "Quick look" size (18 historical scenarios,
  a 7-point grid), `regret.json` beside the artifacts and the summary in `record.json` (a
  failed sweep keeps the solve).
- **The `ages_thorough` preset** (section 8.1's "Ages, thorough"): `work_sweep.py`'s own
  `run_variant` (stage (a)'s exact-LP search plus stage (c)'s sweep of every whole-year
  pair, each scored by branch-and-bound at gap 1e-5; the loop search and the deposit-split
  check off) decides the ages, the solve runs at them (`record.json`'s `age_search`, as
  `ages`), and the sweep's row lands in `scores.json` in the results folder -- which the
  claiming-age map (I7) reads. The sweep stays phase 5's, shared with `run_suite.py` by
  loading `fork-notes/phase5/work_sweep.py` (moved into `src/owlplanner` as
  `owlplanner.work_sweep` on 2026-11-05; the loaders are plain imports since).
- Tests: `tests/library/test_tornado.py`, `tests/plan/test_brackets.py` and additions across
  `test_variants.py`, `test_builder.py`, `test_scenario.py`, `test_worker.py`,
  `test_presets.py`, `tests/tax/test_aca.py`, `tests/ui/test_variant_tables.py`,
  `test_collections_page.py`, `test_scenario_page.py`, `test_library_pages.py`. Checked:
  `check_library_builder.py` 46/46 after the `death` event.

### Run library, build step 6: collections, "make variants", the grid view and the Ages preset (2026-11-04)

`fork-notes/run-library-design.md` sections 8.1, 9.3 and 11, step 6 (the core; the user's
call: I8/I9 and the I2/I11 variant dimensions are this step's second increment, the check is
a reduced grid). First increment:
- **The `ages` preset** (section 8.1): `owlplanner.library.agesearch` is `run_suite.py`'s
  `two_stage_ages`, one implementation shared by the suite and the interface -- stage 1
  searches the claiming ages under the exact LP (Medicare off, SS taxability 0.85; ACA stays
  on the loop), stage 2 scores the pick and each searched person's pick +-1 year at fixed
  ages under the case's own model and the best score wins. The worker runs it before the
  final solve at the chosen ages when the case says "let Owl choose", and `record.json` gains
  the `age_search` block (the pick and every candidate's score; the stages' warnings stay out
  of the record, run_suite's rule). The preset forces nothing (R4's exception);
  "Ages, thorough" (`work_sweep.py`) is a later increment. The exact-model option lists
  (`EXACT_MODEL` / `EXACT_GROUP`) moved to `agesearch`, and `presets` and `run_suite.py` read
  them.
- **Collections** (`store.Collection` / `store.Member`, in `library.json` under
  `library.lock`): a named set of runs answering one question, with the question and the
  comparison rule written on it (section 9.3), a reference run, members carrying their
  variant values and a grid layout (the values' dimensions as rows and columns). A deleted
  run leaves every collection; a collection deletes no runs.
- **"Make variants"** (`library.variants`): one child scenario per value of a chosen
  dimension -- place, purchase year, financing, the last work year, the claiming ages -- and
  several dimensions give their product (the grid of section 4). Each value is a small edit
  to the scenario's events (a place value carries the home's name, price, locality and
  yearly costs; a financing value the loan's terms, its `name` taking `{place}`); the
  children are scenarios like any other and freeze through `save_run` with their parent and
  change summary. A single-valued dimension holds every child (the suite's rule: the condo
  grid runs at the baseline's claiming ages). The UI is a section of the new Collections
  page, and each child can be queued when created.
- **The grid view** (`library.grid`): the pivot of `run_suite.py`'s `condo_pivot` -- rows of
  the row dimensions against the column dimension, each cell the score's difference from the
  reference and the home at the end below it, coloured by the comparison rule (R3: leads /
  trade-off / the reference leads, grey inside the 1% noise band), the best score per row
  marked by score only. `front()` lists the variants no other variant beats on both numbers
  (the score and the home, never added), each with whether its lead is resolved. The
  reference is shown as the caption's number, not a cell (a run's variant values are what
  place it; a member with none is listed beside the grid).
- The step's check is `fork-notes/synthetic/check_library_variants.py`: the synthetic condo
  grid through the interface -- the reference scenario solved with the `ages` preset, the
  children made by `plan_variants` at the baseline's ages and solved through the worker with
  `decision` -- matches `run_suite.py`'s own `report.md` cell for cell within the noise
  rule, and the children's events are `make_cases.py`'s grid scenarios. The user's call: a
  reduced grid (one place x three purchase years x cash/mortgage) is the recorded check; the
  full 42-cell grid is an offline/overnight run (`--full`).
- Tests: `tests/library/test_agesearch.py`, `test_collections.py`, `test_variants.py`,
  `test_grid.py`, `tests/ui/test_collections_page.py`, plus the `test_presets.py` update
  (`PRESETS` now offers `ages`).
- Reviewed twice (`fork-notes/run-library-step6-review.md` AC1-AC10, AC1-AC7 folded;
  `run-library-step6-review-2.md` AD1-AD9, AD1-AD6 folded 2026-11-05). The second review's
  folds: the make-variants tables read an empty cell as "keep the parent's" (it was NaN, and
  a place's empty costs reached the plan as \$0; parsing in `ui/variant_tables.py`, `-`
  clears a text cell), and `variants` / the builder refuse a non-finite number from any
  route; the grid's default layout places every varied dimension (the year as columns) and
  "make variants" stores it; the row's star marks the best member itself; a cell's colour is
  R3's verdict on the two numbers (`~` marks a score difference inside the noise band); a
  flag lists the cells solved at claiming ages other than the reference's, and Make variants
  warns after an `ages` solve with the claiming boxes empty; `move` is a checkbox and `kind`
  a select box.

### Run library, build step 5b: the rates table and the named downturn sequences (2026-11-04)

`fork-notes/run-library-design.md` section 11, step 5b (D11, I11, review R13): a year-by-year
rates CSV the case file names, and the named downturn sequences placed at a year.
- **The `table` rate method** (`rate_models/table.py`): `[rates_selection] method = "table"`
  with a `rates_file` reads returns from that CSV instead of generating them -- a `year` column
  and the four rate columns of `data/rates.csv` (extra columns ignored, so that history file
  itself can be named), values in percent. The file is resolved beside the case file
  (`Plan._config_dir`; first since review AB3), rows are matched to the plan's calendar years, and the
  file is re-read at every `Plan.setRates` (review Z1) -- a plan falls back to the rows it
  already holds only when the file cannot be resolved or read (the paths that have no case
  directory in reach). `to_config` writes only the file name back.
- **The run library** stores the table in the scenario (`rates_table`, schema v3 with a
  migration; `BUILDER_VERSION` 4), so it is in the inputs hash (R13), imports it with the case
  (`import_case`, resolved as the workbook is) and writes the run's `rates.csv` beside
  `Case.toml`, which names it. The two consistency rules are `validate`'s: a table and the
  case must agree on `method = "table"`.
- **Downturn events (I11):** a scenario event `{kind: "downturn", sequence, start}` places a
  named sequence at a year or an anchor (`purchase`, `age:Ari:70`, ...). The builder generates
  the run's rates table as **the case's own rate path with the sequence's window overlaid at
  the placement** (the user's call), so the years outside the window keep the run's own method
  and the stress question is "the same plan, but the market does this". The named sequences
  (`data/downturn_sequences.toml`, `library/sequences.py`) carry their sources: `crash-30` is
  an invented stress year, `three-negative-years` (2000-2002) and `poor-decade` (1973-1982)
  replay rows of Owl's own rate history. One downturn event per run for now (the variant
  dimension is step 6). A run's nominal amounts are built from the table's inflation path when
  there is one, so a downturn overlay moves the purchase price and the rent rows with it.
- **The pages keep a table case intact** (the user's call: safety + Scenario rows): the Rates
  page shows the table read-only (its caption names what can change it), `config_to_ui` /
  `ui_to_config` / `genDic` / `_setRates` carry `method = "table"` and its file name instead of
  resetting the method (the selectors' "not available" reset would have rewritten the case), and
  the Scenario page edits the downturn event like the other events (sequence picker with its
  source, placement with the anchor grammar).
- The step's check is `fork-notes/synthetic/check_library_rates.py`: `owlcli run` of a run's
  frozen `inputs/Case.toml`, called from another working directory, reproduces the interface's
  worker solve array for array (`plan.json`), for a downturn run and a hand-table run alike.
- Tests: `tests/rate_models/test_rate_model_table.py` and
  `tests/library/test_rates_table.py` (42 at the step, 63 after the review below).
  `info/RATE_MODELS.md` regenerated (the generator adds the `table` section; nothing else
  moves).
- **Review Z1-Z9 folded** (`fork-notes/run-library-step5b-review.md`; the user's call: all
  nine): a changed `rates.csv` is re-read -- the rows a plan holds are reused only when the
  file cannot be resolved or read (Z1); a stochastic baseline must fix its seed **in the
  case** (`reproducible_rates` and `rate_seed`) and one export computes one table
  (`build(rates_table=)`), so the frozen `rates.csv` is the table the run was priced with
  (Z2); the Import tab takes a rates CSV (`rates_path=`) and a no-base save stores the table
  the plan holds in memory (Z3); a downturn placement in no plan year -- before the plan or
  past its end -- and one whose window starts before the plan and would be cut are refused
  (Z4); `method = "table"` with no `rates_file` and a `nan`/`inf` cell name what is wrong by
  row and column, and an Excel BOM is read (Z5, Z6); the named sequences' windows are builder
  input, in the inputs hash (only runs with a downturn change hash), and `sequences()` is no
  longer cached (Z7); the acceptance record is scoped (T1 is the hand-table run's; the
  summary metrics compared are `plan.json`'s) (Z8); a comment's schema number (Z9).
- **Second review, AA1-AA3 folded** (`fork-notes/run-library-step5b-review-2.md`): the table's
  units survive the pages (`in_percent` rides with `ratesFile` through `config_to_ui` /
  `genDic` / `ui_to_config`, and `scenario_from_ui` takes it from the plan when there is no
  base), so a decimal table (`in_percent = false`) neither freezes nor solves a run with rates
  100x off (AA1 -- the same loss re-priced the session plan at every solve); `clone` re-reads
  a changed `rates.csv` like every other path (AA2); `build` enforces the table/event
  refusals however it is given the table, and refuses `rates_table=None` for a downturn run
  (AA3).
- **Third review, AB1-AB4 folded** (`fork-notes/run-library-step5b-review-3.md`): a downturn
  run's generated case resets the hand case's `reverse_sequence` / `roll_sequence` (marked with
  the event, so a pages save keeps the hand values), because its table is the plan's rate path
  already reversed or rolled -- the frozen run used to transform it again, moving the window
  off its placement and every other year off the parent's path (AB1; `BUILDER_VERSION` 5); the
  Rates page re-applies a table with the case's `in_percent` and sequence options (AB2); a
  relative `rates_file` is looked up beside the case file first, then in the working directory,
  so a stray `rates.csv` cannot replace a run's own (AB3; the import reads it the same way); an
  uploaded table case that cannot find its CSV says where to open it instead (AB4).

### Run library, build step 5: the Budget editor and the missing fork widgets (2026-11-03)

`fork-notes/run-library-design.md` section 11, step 5: the inputs the case pages could not edit.
- **Budget editor** (`ui/Financial_Profile.py`): the Budget sheet gets a table of its own beside
  Debts and Fixed Assets (the same `houseEditorBase` pattern), with bubble help for all 14
  columns, and the model's own "adds nothing to the plan" checks (`budget.lines_left_out`, the
  ones `_evaluateBudget` logs at solve time) reported beside it as the rows are edited
  (`owlbridge.checkBudgetRows`). `houseListBudget` joins the case keys; `syncHouseLists` already
  carried it, and a case naming `budget_file` says the interface does not read the file.
- **A restored run keeps its tables** (`owlbridge.seedProfileTables`): "Open in Owl" restores a
  solved Plan into the pages (design 9.1), and the Financial Profile page zeroed the plan's
  Wages and Contributions on arrival (`resetTimeLists`) and showed empty tables. The page now
  seeds its keys from the plan when the plan holds tables, without marking the case modified;
  a plan with no tables still starts from the zeroed skeleton.
- **Saving the current case to the library syncs the pages' tables first**
  (`owlbridge.syncContributions`, called by `ui/Library.py`): `scenario_from_ui` takes the
  tables from the plan ("the caller syncs first"), so a table edited and not yet run or
  downloaded was missing from the saved run.
- **`withItemized` and `withSTAR`** (Run Options, *Advanced options* -> *Deductions and
  Credits*): radios bound to the passthrough names, so the solve path (`getSolveParameters`)
  and the save path (`ui_to_config`) read the same case key and cannot drift. Both stay
  editable under local search: it solves STAR with MILP like "optimize" does, and honors
  "none"; the itemizing switch is not a breakpoint family.
- **All moves** (`ui/Create_Case.py`): moves after the first are edited under *Further moves*,
  one block of cascading selects per move (year, state, city, school district) with a Remove
  button, and the mistakes `residency` refuses at solve time (a duplicate year, a move to the
  residence it leaves) are reported as the rows are edited.
- Tests: `tests/ui/test_budget_editor.py`, `tests/ui/test_run_options_deductions.py`, the
  further moves in `tests/ui/test_create_case_move.py`, several moves in
  `tests/config/test_config_ui_bridge.py`. `tests/conftest.py`'s frozen date now accepts plain
  `datetime.date` instances (`_FixedDateMeta.__instancecheck__`): AppTest hands widget state
  back as one, and streamlit's `date_input` rejected it on the second run of a page with a
  date widget.
- **Second review, Y1-Y4** (`fork-notes/run-library-step5-review-2.md`): further moves are read
  in the spelling the Create Case selects list (`ui_bridge._ui_further_move`: state upper-cased,
  canonical city and district), so a spelling residency accepts ("Yonkers" for the district, a
  lower-case city) is no longer dropped on the first render (Y1); a further move dated this year
  or earlier renders with its warning instead of stopping the page (Y2); Run Options no longer
  stores `withItemized` / `withSTAR` defaults, which made an unchanged case save as a changed
  run (Y3); the library save stops with a message when the plan refuses the pages' tables,
  instead of saving its previous ones (Y4).

### Run library, build step 4: the scenario model and builder (2026-11-03)

Scenario schema v2 and `owlplanner.library.builder` (`fork-notes/run-library-design.md`
sections 6.1-6.3, D6, I1). A scenario carries **events** -- work, claiming, rent, a home
purchase and care -- beside its hand rows, and `build(scenario) -> (case, hfp, provenance)`
turns them into the coupled edits of section 6.2 in one place (deterministic, no side effects).
- **Anchors (I1):** the year fields of the rent, purchase and care events (work spans take
  plain years) may name a calendar year or anchor to `age:Ari:86` (the year they turn that
  age), `work:Noa` / `after:Noa` (their last work year / the year after it), `purchase`, or
  `event:care+2`; the rent end and the owner lines follow from the purchase by construction.
- **Provenance markers (section 6.3's first increment; S11):** every generated row, cell and
  case field records which event produced it; generated rows are regenerated wholesale and
  hand rows untouched. Per-cell overrides are not built yet: an edit to a generated value does
  not survive a regeneration.
- **Schema v2** migrates v1 (every row stays a hand row); `BUILDER_VERSION` is 2, so runs of
  older builders are flagged rather than aliasing new output (R9); 3 after the second review.
- `make_cases.py` shares the builder's row builders and writes `scenarios.json` (46 scenarios
  with the case each one's `set` builds); `check_library_builder.py` shows the builder
  reproduces its **39 workbooks cell for cell** (case fields and hfp edits included).
- New `ui/Scenario.py` in the Run Library section (the events, the markers, the computed
  change summary, save-as-a-child-run); "Edit the scenario" on the Run page.
- Second review (`fork-notes/run-library-step4-review-2.md`, X1-X9), folded the same day:
  a save from the case pages keeps the run's events and puts back the hand values they
  replaced (X1, X2); a case whose rates draw a new inflation path at every build is refused
  where a purchase or rent needs that path (X3); the Scenario page uses the builder's
  defaults, keeps the keys it does not edit, and its change summary shows the price and any
  field the words do not (X4); `event:<id>` round-trips ids ending in `-<digits>` (X5); an
  anchor to a claim is refused and `event:rent` reads the rent's start (X6); a person with no
  claim event keeps the hand `withSSAges` choice (X7); a new purchase defaults to the year
  after the plan year, and a schema-1 run shows no phantom change (X8). `BUILDER_VERSION` is 3.

### Run library, build step 2: the `as_of` input dropped (2026-11-02)

The user dropped the frozen "as of" date. The fork reads the date as upstream does again:
- `owlplanner.asof` and `owlcli --as-of` are removed, and the 78 call sites in 16 modules are
  back to upstream's `date.today()`;
- `tests/conftest.py` and four test files are upstream's again.

The library now:
- records each run's `plan_year`: the start date's year, else the year of capture, with
  `start_date = "today"` stored as the capture day;
- refuses to queue or solve a run outside its plan year (`casefiles.check_plan_year`; the worker
  writes a "refused" record, and the Queue page shows the message);
- keeps `plan_year` in `status.json` and `record.json` in place of `as_of`.

Within the plan year a fixed-age run solves the same on any day. The `withSSAges` claiming
window follows the real month on purpose. The upstream issue draft is withdrawn.

### Run library, build step 2: third review's minors fixed (2026-11-02)

`fork-notes/run-library-step2-review-3.md`, N1-N5.
- **Two-stage cancel.** Cancel is cooperative, and the row then offers Kill. A verified kill
  writes the attempt's "interrupted" record and drops its staging folders. The heartbeat
  continues while a cancel is pending.
- **Caption.** The Queue page's elapsed-time caption is corrected.
- **No stale write.** `JobRecord.update` no longer writes its in-memory copy over a record it
  cannot read.
- **All-or-nothing re-queue.** `requeue` renames everything aside first and puts it back if a
  file is in use. The old log is kept as `solve.prev.log`.
- **`quick` is the loop.** `quick` puts every `"optimize"` family on the loop, with no MIP and
  no local search (`presets.resolve_options`). The synthetic baseline's quick solve went from
  17.6 s to 1.1 s.

### Run library, build step 2: third review fixed (2026-11-02)

`fork-notes/run-library-step2-review-3.md`, H1-H6.
- **Process-wide freeze in the worker.** The worker now freezes the date with
  `asof.process_as_of()`, so `withSSAges`' candidate threads read the run's date; with the
  thread-local `as_of(...)` they read the real one.
- **Determinism tests that can fail.** These tests now clear the suite's date pin
  (`no_session_pin` fixture), and the worker test runs at an `as_of` other than the pin's. Each
  new test was checked to fail with its fix reverted.
- **Offset-aware stamps.** Job stamps are local time with a UTC offset (`now_iso`,
  `stamp_seconds`), so the hour the clocks fall back no longer marks live workers dead, and the
  queue is ordered by instant.
- **`record.json` under the job's lock.** It is written under the lock with the token checked
  inside (`JobRecord.publish_record`), so a stale worker cannot leave its record after "run
  again".
- **A ticker thread.** The server's manager ticks in a daemon thread
  (`JobManager.start_ticker`, started by `ui/libraryjobs.py` from `main.py`), so the queue moves
  with no Queue page open.
- **`plan.pkl` keyed on the code.** The cache is also keyed on Owl's version and commit, plus the
  package diff of a dirty tree (`code_stamp`, `record.json`'s `plan_pkl_code`), and a pickle that
  fails to load is dropped.

### Run library, build step 2: jobs and the `as_of` date (2026-11-02)

`src/owlplanner/library/` + `owlplanner.asof`: the "as of" date is a first-class input (design
section 8.3 b, S1, S7) -- `asof.set_as_of()` / `asof.today()`, honoured by every calendar read in
the backend (every `date.today()` in `src/owlplanner` now goes through it), settable by
`owlcli run|compare|frontier|explain --as-of YYYY-MM-DD` and by the worker, recorded in
`record.json`; `tests/conftest.py` pins the suite with it. The scenario (schema v1) records it as
the balances' date (`basic_info.start_date`), validated to fall in the run's plan year, and both
entry paths capture at it (V5's import conditioning pinned). Background jobs (section 8.2):
detached worker processes (`worker.py`) with a PID, a process start token and a 30 s heartbeat, a
per-server `JobManager` over a queue that lives on disk (`status.json` in the results folder from
the moment a job is queued, S2), adoption/interrupt on restart (S8), cancel by token and by
verified kill (S9), "run again"; each solve writes its results folder: `record.json` (preset and
options, Owl version and commit, the frozen date, solver, status, gap, iterations, converged, wall
time, warnings, rate method and seed, Python and package versions), `summary.json`, `plan.json`,
`Results.xlsx`, `solve.log` and the `plan.pkl` cache (hash- and environment-checked, dropped when
stale; R10, S6). UI: a Queue page (`ui/Queue.py`) and "Open in Owl" (`owlbridge.openCaseFromPlan`
+ `sskeys.openCaseFromPlan`) restoring a cached plan into the pages with no solve. Found and fixed
by the check: `owlbridge.genDic` named three accounts of four (every HSA case broke) and was never
called before. Presets `quick` and `custom` (`presets.py`; the two Ages presets come with step 6).
Checks: `fork-notes/synthetic/check_library_jobs.py` 4/4 on the synthetic baseline (background
solve in 11 s, restart survival, 128 page keys from the cached plan, two solves on different days
identical); 55 new tests (`tests/library/` 137, `tests/ui/test_open_in_owl.py` 2). An independent
review of the step's code (F1-F10, race probes included) was folded in the same day: job dispatch
is a compare-and-swap under a per-job OS lock (`status.lock`, serialized read-modify-write with a
retrying rename -- heartbeats, cancels and two managers no longer lose updates on Windows), every
worker write is token-guarded (a worker that wakes after "run again" cannot clobber the new
attempt), an interrupted solve keeps its record and a retry starts clean, the determinism tests
straddle a New Year and pin the claiming-ages month sensitivity, and `asof`'s context freeze is
thread-local (one session's capture cannot date another session's solve).

### Run library, build step 1: second review fixed (2026-11-02)

`fork-notes/run-library-step1-review-2.md`, T1-T4. The stored case dictionary is canonical (the
library's own file names, floats as the generated `Case.toml` holds them; table cells typed as a
workbook holds them), so re-importing a run's own files gives the same hash; saving from the pages
takes the opened run as `base=` and applies only the fields the pages changed, keeping the base's
plan year (`ui_to_config` fills in defaults and puts the current year in the start date);
`Library.open` removes only stale staging folders, not another session's save in progress; the
change summary compares canonical JSON (1 vs 1.0, True vs 1). `save_run` canonicalizes a scenario
it generates with the default builder. T5: `library.lock` is an OS file lock (`flock` /
`msvcrt.locking`), released by the kernel when its holder dies, instead of a create-exclusive file
with a staleness timeout. T6: S1's evidence corrected in the design. 84 tests in `tests/library/`;
the synthetic round-trip check now compares inputs hashes (39/39).

### Run library, build step 1: the library core (2026-11-01)

`src/owlplanner/library/`: scenario schema v1 (hand rows: the case dictionary and the HFP tables
as JSON, with a canonical form and inputs hash), the run folder storage (`run.json`, save-as with
the identical-inputs notice, lineage, rename and delete to trash, `library.lock`), and
import/export of `Case.toml` + `HFP.xlsx` through `toml_io` and `hfp_io` (a `budget_file` case
keeps its JSON as a sidecar). 65 tests in `tests/library/`; the synthetic round-trip check is
`fork-notes/synthetic/check_library_roundtrip.py`. An independent review
(`fork-notes/run-library-step1-review.md`, V1-V10) was folded in the same day: saves are staged
and published with one rename, the budget sidecar resolves like the plan resolves it, the stored
scenario is exactly the document the frozen files were built from, and a damaged `run.json` is
reported rather than fatal. The design is `fork-notes/run-library-design.md`;
the opt-in UI section comes with later steps.

### Upstream: docs pass and DCC-GARCH fix (`dev` `226ff54`, merged 2026-10-29)

Taken, with the doc conflicts resolved toward upstream's text (`papers/owl.tex` keeps only the
fork's state-tax paragraph). Fork follow-up: the city-tax identity `local_taxable_income` and the
STAR big-M link `star_enhanced_income` registered in the explainer's `CONSTRAINT_FAMILIES`, which
upstream's new registry test requires.

### Upstream: #235 (`dev` `b6a3ba7`, merged 2026-10-28)

Taken as is, no conflicts. The earnings test reads the five years before the plan for someone
already claiming (grace year, months withheld before the plan, the December check before the
plan). Version 2026.10.28 and dependency bumps. Fork follow-up: `check235_after.py` (the
law-side figures of the 2026-10-26 check reproduced).

### Upstream: #233, #234, #236, #238, #239 (`dev` `1bdc3b2`, merged 2026-10-28)

Taken as is, no conflicts. #233 (ours): a sticky-binaries tie no longer takes a plan outside the
requested gap (our patch). #234: the worksheet nets only a surplus round trip that realizes no
gain. #236: `spousal_surplus_deposit_fraction = "optimize"`. #238: the survivor's inherited
taxable account is stepped up at the first death; an initially empty taxable account is tracked
from a $0 basis. #239: a warning when the LTCG loop does not settle. Fork follow-up: the
`work_sweep.py` docstring.

### Upstream: #229-#232 fixed (`dev` `07b9a77`, merged 2026-10-27)

Taken as is. A 401k deferral counts as earnings with or without wages, and the employer's
contributions have their own HFP column, `employer ctrb` (never earnings). Exempt amounts and the
payroll wage base are nominal tables by year, 2027 included. After the spouse's FRA, the worker's
excess is charged on the ARF-adjusted add-on. Fork follow-ups: the strict xfails in
`tests/ss/test_earnings_test_properties.py` removed, the #229 case entering the deferral as
`kappa401k_in`, a case for the IRA rule, and `employer ctrb` in the household HFP generator
(`fork-notes/phase0/gen_hfp_us.py`).

### Upstream: the payroll tax is upstream's (#227, PR #228)

PR #228 landed upstream as `3a2dfc33` (2026-10-25), tree identical to the PR head, followed by
upstream's own changes: MOSEK records for the five re-pinned cases, the payroll tax as its own line
in the taxes plot ("Taxes and Premiums") and as its own *Payroll tax* slice and band in the
lifetime allocation and cash-flow mix (the fork had it inside *Taxes*), and a Summary with the same
rows for every plan. Merged here the same day; the fork's payroll code, tests and fixture are
upstream's. The entry below is the history before the landing.

### Changed: the payroll tax takes the shape of the upstream PR for #227

The fork's payroll-tax code is now the PR's (`payroll-tax-pr`, built on upstream `dev` `22ce72b`
at the maintainer's request): `Plan.payroll_n` (was `payroll_tax_n`), one yearly total from
`tax_federal.payrollTax(N_i, earnings_in, gamma_n, n_d, N_n)`, the wage base a single constant in
today's dollars. *Total payroll tax paid* is now in the Summary of every case (\$0 without
earnings), the fork's *Additional Medicare tax* line under it is gone, and the Cash Flow and CSV
*payroll tax* column sits after *NIIT*. Rules and amounts unchanged: every pinned case gives the
PR's values. With the PR's review fixes: a *payroll tax* column in the Taxes worksheet, and
`tax_federal.filingStatusIndex_n` in place of the fork's `tax_state.filing_status_by_year` (same rule),
then of the other copies, upstream's and the fork's (the itemizing warning, the non-itemizer
charity cap), except upstream's `taxParams` and `seniorBonusSchedule`, which keep theirs as in the
PR.

### Removed: the fork's age-anchored smile (back to upstream's smile)

The smile is upstream's again: one cosine period over the plan's length, starting `smile_delay`
years after the first plan year. Gone: the fixed 30-year period, `smile_start_age` (a case that
still carries it has it ignored), the survivor's age after the first death, the old-case warning
and the UI's start-age field. The six example cases no longer carry `smile_start_age`, and the
pinned results of the smile cases are upstream's again where no other fork feature moves them
(jack+jill's spending basis 102,621 in `test_toml_cases`; the AMO records of jordan+taylor and
morgan, MOSEK entries included). For the household's horizon (ages 62-92, 31 years) both curves
were identical.

### Removed: the fork's New Jersey rules (back to upstream's New Jersey)

The household dropped New Jersey as a place to live (2026-10-17), and the fork's three NJ-only
rules were used by no other state: the income-tiered retirement exclusion (NJ-1040 lines 28a-28c, a
MILP with tier binaries, its node cap and the tiers kept after a capped solve), the property tax
deduction (line 41) and the medical deduction (line 31). An NJ case now runs on upstream's NJ:
brackets and the \$1,000 personal and 65+ exemptions, with no retirement exclusion, so it overstates
NJ tax for retirees aged 62+ with NJ income up to \$150,000. With the exclusion's node cap gone,
HiGHS uses upstream's node limit and the Summary's *MIP node limit* row is upstream's; the fork's
log warnings for a MILP stopped at its time or node limit went with it. Plans in other states are
unchanged.

### New: NY STAR credit (`withSTAR`, `school_district`) (fork)

The School Tax Relief credit (Tax Law sec. 606(eee)) for a NY owner: `basic_info.school_district`
(and a move's `school_district`) names the home's municipality and school district, and the credit
applies in the years the budget has a `property tax` line. Basic while the income two years
earlier (federal AGI less IRA distributions) is at most \$500,000; Enhanced from the year an owner
turns 65 while that income is at most the Enhanced standard (\$110,750 for 2026, \$113,550 for
2027, then indexed), kept by a surviving spouse who was 62 at the death. District amounts are the
2025 final credits from tax.ny.gov (Westchester and New York City in
`data/property_tax_relief.toml`), growing 2% a year, the statutory cap. The credit is charged
against the state income tax, as it is in law: the cash flow and the SALT deduction follow, and
NY's itemized deduction subtracts it from real estate taxes (IT-196 line 6). `withSTAR = "loop"`
(default), `"optimize"` (one binary per year for the Enhanced credit; set by `breakpointMethod`)
or `"none"`; `previousSTARIncomes` gives the two years before the plan. The Taxes sheet has a
*STAR credit* column and the Summary a total.

### New: itemized deductions, federal and state (`withItemized`)

Each year deducts the larger of the standard deduction and the itemized total, built from the
expenses the plan already knows. Federally (Schedule A, P.L. 119-21): SALT, which is the budget's
`property tax` lines plus the state and local income tax the plan pays (cash basis, the same terms
the cash flow charges), capped at \$40,400 in 2026, +1%/yr through 2029 and \$10,000 from 2030, the
cap reduced by 30% of MAGI over \$505,000 (2026) before 2030; home mortgage interest from `Debts`
rows of type `mortgage` (Pub. 936 Table 1: \$750,000 of acquisition debt, \$1M for loans taken out
before 2018; a loan linked to `real estate` is a rental's and is left out); `charity` lines above
0.5% of AGI; and `medical` lines (or, in a plan without one, the `other_medical_expenses` amount
of `setMedicalExpenses`) plus Owl's Medicare Part B/D (IRMAA included) and ACA net premiums, less
the year's HSA distributions (Pub. 502), above 7.5% of AGI. Itemizers keep the
OBBBA \$6,000 senior bonus and lose the 65+ additions; non-itemizers also deduct up to \$1,000
(\$2,000 MFJ) of cash charity. After a pre-TCJA reversion (`obbba_expiration_year`) SALT is
uncapped, the mortgage limit is \$1M and the OBBBA charity rules end.

New York's own itemized deduction (IT-196, 2025): property tax without a cap, charity, medical
above 10% of federal AGI, mortgage interest under the \$1M limit, state and local income taxes left
out, and the line 46 cut (up to 25% of the deduction between NYAGI \$200,000 and \$250,000 MFJ;
\$100,000-\$150,000 single). New York lets a filer itemize whether or not the federal return
itemizes. Data: `itemized` entries in `taxes_state.toml`.

`withItemized = "loop"` (default) or `"none"` (the standard deduction everywhere, federal and
state, as before). The branch (itemize or not) and which side of each floor an amount is on come
from the previous iteration of the self-consistent loop, as do the floors, the SALT phase-down and
the NY cut: itemizing adds rows on existing columns, never a column or a binary, and a year that
never itemizes leaves the plan exactly as `"none"` builds it. The loop's lag shows in the plan:
a warning when a year takes the smaller deduction, and the *itemized*, *state itemized* and
*state medical* entries of `fixedPointResidual`. Not modeled, reported as warnings: the 2/37
limit in the 37% bracket and Pease after a reversion. Not modeled: AMT, other Schedule A items,
NY's rules above \$525,000. Results: Taxes sheet columns and Summary lines when nonzero;
`plan_metrics` keys `itemized_deductions_today` and `state_itemized_today`.

### New: `medical` and `charity` budget types

Two Budget line types for the deductions above. `care` stays non-deductible (assisted-living room
and board is not a medical expense unless care is the main reason): use `medical` for deductible
care. `Budget.by_type(..., essential=)` filters by tier.

### New: budget lines can follow an age clock; a JSON budget file

A Budget line's `clock` is `calendar` (default; `year` / `end`) or `age`: `start_age` / `end_age`
against `index`. Age-tied lines — travel "while we are able", care "from 80" — stay with the age
that causes them, so a longer life still includes them. Growth counts from the first year the line
pays. `index` `younger` (default) or `older` is a household line: that spouse's age while both are
alive, the survivor's after the first death (an `older` line can resume when the survivor reaches
its range). A person's name makes a personal line, which ends at that person's death.

`optimization_parameters.budget_file` points at a JSON budget profile (`schema_version` 1, the
same lines as the sheet, amounts in today's dollars like the sheet). It feeds the Budget sheet's
DataFrame, so one evaluator serves both; the workbook sheet wins when both are present. Refused
rather than read loosely: unknown fields, an unknown schema_version, a `type` outside the sheet's
list, numbers given as text, flags other than true/false, fractional years. `kind` is free text
kept with the line (also an optional sheet column). Lines read from the file are not written to the
HFP by `saveHFP` (or the MCP export), so the file stays their only source; reading a workbook makes
its Budget sheet the source again. The web interface does not read the file: it keeps its name when
saving the case, and a plan whose only lines are in an unread file says so when it is solved.
Owl-budget and MCP can hand lines over without writing Excel.

### Changed: the smile starts at an age of the younger spouse

`optimization_parameters.smile_start_age` (UI: *Smile starts at age (younger spouse)*) is the
younger spouse's age (calendar year minus birth year) when the smile starts; it replaces
`smile_delay`, which counted years from the current year and so moved the curve one year later,
relative to the household's ages, each year the same case was run again. A case with only
`smile_delay` is read with the delay turned into an age once (today's age plus the delay), so no plan
changes on the day of the upgrade; saved again, it carries the age. Owl also writes the equivalent
`smile_delay` (never negative) for readers that only know the delay. Reading a smile case without
`smile_start_age` warns, naming the age to add. The curve follows the younger spouse's age and, after
the first death, the survivor's: if the younger spouse dies first, it jumps ahead by the age gap
(of the example cases, only `Case_avery+quinn`, three years apart). An age earlier than today's
starts the plan partway through the smile (`gen_spending_profile` takes a negative `delay`). MCP
tools keep their `smile_delay` argument, read as years from the day of the call.

### Changed: the smile's period no longer follows the plan's length

The smile's cosine used to stretch one period over the plan's length (`span = N_n - 1 - delay`), so
a longer life widened the go-go years and moved the slow-go dip later. It now covers a fixed
`SMILE_SPAN` of 30 years from the start of the smile (plan start plus `smile_delay`); extra years
take the late-life rise instead of stretching the curve. At `N_n = 31` and `smile_delay = 0` the
curve is exactly the old one (`span` overrides the span and recovers the old curve when it equals
`N_n - 1`). The dip sits at `SMILE_SPAN/2` years after the smile starts on any horizon. Flat and
`"budget"` profiles are unchanged. `Case_jack+jill`'s expected basis moved with the shape (33-year
horizon); `Case_joe` (31 years) did not. The AMO references of the three smile cases that moved
(jack+jill +0.9%, jordan+taylor -2.0%, morgan +3.3% basis) were re-recorded with HiGHS; their MOSEK
entries were removed rather than left stale.

### New: essential budget lines (a spending floor)

A *Budget* line can be marked `essential` (optional column; blank means no). Essential lines are paid
at their amounts whatever the spending level, and only the other, discretionary lines scale: net
spending each year is the essential lines plus k times the discretionary ones. `maxSpending` maximizes
k, shown in the summary as *Discretionary spending (share of budget)* and in `plan_metrics()` as
`discretionary_scale`; a plan that cannot pay the essential lines is infeasible, which stochastic
spending and lifespan sampling count as a full shortfall. Under `maxBequest`, `netSpending` must cover
the essential lines; at exactly that amount nothing discretionary is spent, and the bequest is what
remains above the core. In the LP the profile rows become affine, with `spendingSlack` on the
discretionary part only; no binaries, and a budget without essential lines gives the plan it gave
before. Upstream's cost-function point on #175 (core versus discretionary spending).

### New: a budget spending profile

`spending_profile = "budget"` builds the spending profile from the lines of an optional *Budget*
sheet in the HFP workbook: core spending, rent, property tax, insurance, maintenance, a car, travel,
care, ..., each with a first and last year, an annual amount in today's dollars, a real growth rate
and the share a survivor keeps (by default the case's survivor percentage, and all of it for housing
costs). The profile is the lines' sum divided by its first year, so the optimizer and the LP are
unchanged: budgeting stays outside the optimizer, as upstream suggested on #175. With `maxBequest`,
net spending unset or 0 means the budget's first-year total (another amount scales the budget); with
`maxSpending`, the whole budget scales.
Renting and buying are compared with one budget per variant at a fixed spending level. The results
workbook has a *Budget* sheet that splits net spending along the lines. A *Housing* sheet (this
fork's first, ledger form, whose costs were paid outside net spending) is read as budget lines; at a
fixed spending level the two give the same plan.

### New: New York benefit recapture

Above \$107,650 of New York AGI, New York takes back the benefit of the lower brackets: the tax is the
bracket tax plus a supplemental amount that phases in over \$50,000 of AGI, tier by tier, until the
whole taxable income is taxed at the rate of its top bracket. For a married couple that is
about 0.7% more at the margin from \$107,650 to \$157,650 of AGI and 1.6% more from \$161,550 to \$211,550, and it was missing. It is
data (`recapture_agi_start`, `recapture_width`, `recapture_until` in `taxes_state.toml`) with the rule
in `tax_state.state_recapture`, whose tier amounts reproduce every constant on the 2025 IT-201-I
tax computation worksheets. The amounts follow from the brackets, so they use the 2026 rates without
another edit; the 2026 worksheets are not published yet.

The recapture enters as a self-consistent-loop quantity, like the NIIT: the LP is charged its amount
but does not see its marginal effect, so a Roth-conversion schedule is not steered away from the
phase-in range. `Plan.st_recap_n` gives it by year; it is included in `st_T_n`, and a Yonkers
surcharge applies to it. The fixed-point residual reports a `state recapture` family. The tax also
jumps when taxable income crosses a tier threshold while AGI is inside that tier's phase-in, exactly
as the worksheets compute it. The flat 10.9% above \$25M of AGI is not modeled.

### New: local income tax (`basic_info.locality`)

`locality = "NYC"` or `"Yonkers"` adds New York City's resident income tax (four brackets on New York
taxable income) or the Yonkers surcharge (16.75% of net New York tax). The tax appears inside the
state-tax figures, and `Plan.lt_T_n` gives the local part. Localities are data in
`data/taxes_local.toml`, whose header explains how to add one; a flat rate above a threshold is just
two brackets. Wage-only local taxes do not belong there. The NYC rates and thresholds and the Yonkers
rate were checked against the 2025 IT-201-I (2026 not yet published; the Yonkers rate is unchanged in
the 2026 withholding tables).

### Changed: several moves and a locality on top of upstream's change of state (#159)

Upstream 2026.10.6 models one change of state (`basic_info.moves`, `Plan.setStateTax(state, moves)`,
per-year state parameters). The fork keeps its own extension of the same model: any number of moves,
each optionally naming a `locality` (`moves = [{year = 2032, state = "NJ"}]`, or
`{year = 2030, state = "NY", locality = "Yonkers"}` for a move within the state), and a move may
stay in the state if it changes the locality. The residence in force on December 31 governs the
whole year. Plan attributes, the per-year flags (`st_conv_n`, `st_tax_ss_n`, `st_fed_sd_n`,
`st_senior_bonus_n`, `st_pension_eligible_n`) and `_states_n()` follow upstream's names. The web UI
uses upstream's move toggle for the first move, with a city selector, and edits further moves under
*Further moves* on the same page (run-library step 5; before it they were kept from the case file
as they were). The explanation reports the first move as upstream's `move` and,
when there are more, all of them in `moves`.

### Changed: state indexing and exemptions now come from upstream (#157)

The fork's single `indexed` flag and its New Jersey exemption data are replaced by upstream's
2026.10.3 fields (`brackets_indexed`, `deduction_indexed`, `exemptions_indexed`, and the per-filer
exemptions and credits below). Fork-only amounts follow the matching flag: New York's recapture
thresholds index with the brackets.
A personal credit offsets the state tax including recapture, and a local surcharge applies to the
tax after the credit. The `StateTaxParams` dataclass carries the credits as `credit_n`, so a move
takes the new state's credits from its year.

### Changed: `st_taxParams` and `st_schedule` return a `StateTaxParams` dataclass

Upstream's nine-element tuple (`st_taxParams`) and dict (`st_schedule`) are replaced by a frozen
dataclass with named fields, which also carries the fork's recapture and itemized-deduction arrays. Its flag
fields carry upstream's dict keys (`conv_n`, `tax_ss_n`, ...); `conv_n` holds upstream's three-valued
conversion treatment (`"exemption"`, `"taxed"`, `"excluded"`, #203) per year.

# Run library: a local web interface for the household's runs

Design draft, 2026-11-01. Nothing here is built yet. Decisions are marked **D1-D11** (section 15;
D1-D9 accepted in principle by the user on 2026-11-01, D4 as revised by R1 confirmed, D10
declined, D11 accepted). Reviewed the
same day (`fork-notes/run-library-review.md`, R1-R13); the fixes are in the text below.

## 1. What is asked

A web interface, run locally, in which the user:

- enters the household's data in plain forms, never seeing a TOML file or an Excel workbook;
- gets the case file and the workbooks generated from those forms, and saved together as one
  named run's inputs;
- can edit any input later, regenerate, and save again;
- runs a plan, and finds its results saved next to its inputs, to review later;
- is invited to name a new run whenever saved inputs differ from the ones loaded, so the runs
  build up into a library.

## 2. What exists today (checked in the code, 2026-11-01)

The Streamlit app in `ui/` (Streamlit 1.66.1, about 13,400 lines) already has:

- forms for almost every case parameter;
- table editors for the year-by-year person sheets, `Debts` and `Fixed Assets`
  (`ui/Financial_Profile.py`);
- several cases per browser session, a case selector, and a summary comparison across cases
  (`sskeys.compareSummaries`);
- results pages (Graphs, Worksheets, Reports) and downloads of the case file, the HFP workbook
  (`plan.saveContributions`, which writes the person sheets, Debts, Fixed Assets and Budget) and
  the results workbook.

What it lacks for this request:

| Gap | Where it shows |
|---|---|
| No storage | Everything lives in the browser session. Inputs come in by upload and leave by download; closing the tab loses the work. |
| No Budget editor | Budget lines arrive only in an uploaded HFP. `Financial_Profile.py` has editors for Debts and Fixed Assets only. |
| No household-level events | "Buy a condo in White Plains in 2029 with a mortgage" is, in Owl's terms, about ten coordinated edits: a move with locality and school district, a Fixed Assets row in purchase-year dollars, a Debts row linked to it, a big-ticket item, rent lines ending and owner lines starting. Only `fork-notes/synthetic/make_cases.py` makes these edits together, as a script. |
| No background runs | A solve runs inside the page request. Fork solves take minutes: 5 min 10 s for one synthetic condo run under local search (2026-11-01), up to hours for a work sweep. |
| No run record | Nothing keeps the solve date, the method, the gap, convergence, the Owl version or the warnings beside the results. Plans start "today", so a run solved on another day is a different run (CLAUDE.md, "Plans start today"). |
| Some fork inputs have no widget | `withItemized`, `withSTAR`, moves after the first. They are carried from the file (`config/ui_bridge.SOLVER_UI_PASSTHROUGH_KEYS`, checked) but cannot be edited. |

Checked in this session:

- A solved `Plan` pickles except three attributes that hold the log stream (`mylog`,
  `_interpolator`, `rateModel`). Pickling the rest, reloading it, reattaching a logger and
  writing the results workbook worked on `examples/Case_jack+jill.toml`. The plot methods ran
  without error, but their output was not looked at.
- `owlplanner.sh` does not set `server.address`, and a server started without it printed
  "Network URL" and "External URL" lines.

## 3. Recommendation in one paragraph

Add a **Library** section to the existing Streamlit app, switched on by an environment variable
that names the library folder (`OWL_LIBRARY_DIR=otherFiles/library`), the way `OWL_ASSISTANT=1`
switches on the assistant.

- Its source of truth is a **scenario**: a JSON document holding the household in plain terms,
  with life events (work, claiming, renting, buying, care) and tables.
- A pure function, the **builder**, turns a scenario into Owl's case dictionary and HFP workbook.
- Each saved scenario becomes an immutable **run** folder: the scenario, the generated
  `Case.toml` and `HFP.xlsx`, and (once solved) the results and a record of how they were
  obtained.
- Solves run as background jobs in separate processes, so runs survive a closed tab.
- For detail, a run opens in the existing case pages ("Open in Owl"), with its solved plan
  restored from a cache, so Graphs and Worksheets work without solving again.

The builder generalizes `make_cases.py`. The storage, run, job and comparison layers are generic
and could be offered upstream later as an opt-in for local installs (section 12).

## 4. Concepts

| Term | Meaning |
|---|---|
| **Scenario** | Everything the user entered: people, accounts, income, events, budget, assumptions, run method. Editable. |
| **Run** | A saved scenario (frozen), its generated files, and one results folder per solve. Never edited in place; editing makes a new run whose parent is this one. A run belongs to one **plan year**, the calendar year its balances and year rows were entered for (R1). |
| **Draft** | A run that has not been solved. It may be overwritten. |
| **Collection** | A named set of runs answering one question ("Where and when to buy?"), with a comparison rule. A grid of variants (place x year x financing) is a collection. |
| **Library** | The folder that holds the runs and collections. |

## 5. Storage (one folder per run, plain files)

```
otherFiles/library/                      # gitignored (otherFiles/ is ignored upstream)
  library.json                           # collections, tags, pins, the order shown
  runs/
    2026-11-03_wp-2029-mortgage/         # <date>_<slug>; the slug follows renames, the id does not
      run.json                           # id, name, parent id, created, notes, tags, plan year,
                                         # inputs hash, change summary against the parent
      inputs/
        scenario.json                    # the source of truth (with schema_version)
        Case.toml                        # generated: owlcli and the existing pages read it
        HFP.xlsx                         # generated
        rates.csv                        # generated when the run uses a downturn sequence (D11)
      results/                           # one folder per solve
        2026-11-03T14-02_local-search/
          record.json                    # solve date, method preset and options, Owl version and
                                         # commit, solver, status, gap, iterations, converged or
                                         # not, wall time, warnings, rate method and seed
          summary.json                   # plan_metrics (export.plan_metrics)
          plan.json                      # per-year arrays (cli/formatters.plan_to_dict)
          Results.xlsx                   # the workbook owlcli writes
          solve.log
          plan.pkl                       # cache of the solved Plan, valid only for the Owl
                                         # commit in record.json; dropped when stale
```

Rules:

- **Durable formats first.** `summary.json`, `plan.json` and `Results.xlsx` are what the library
  shows and compares. `plan.pkl` only lets the existing Graphs and Worksheets pages open without
  solving again. A pickle can fail to load after a code change, so it is a cache, and a stale
  one costs one re-solve, never the record.
- **Inputs hash.** A hash of the canonical `scenario.json` and the builder version. Saving inputs
  identical to an existing run's says so ("identical to *wp-2029-mortgage*") instead of making a
  duplicate.
- **Frozen generated files (R9).** A run's `Case.toml`, `HFP.xlsx` and `rates.csv` are what its
  solves read; solving again never regenerates them. A builder change shows as a "built with an
  older builder" badge (regenerating would give different files), and editing the run makes a new
  run built by the current builder.
- **Atomic writes (R5).** Every file is written to a temporary name and renamed. A worker writes
  only inside its own results folder; only the interface writes `run.json` and `library.json`.
- **Several results per run.** The same inputs solved on two days, or with local search and with
  the exact LP, are two results of one run. Comparisons pick results, not runs.
- **Backup** is copying the folder. No database and no git: the user can open any file with
  Excel or a text editor, and `owlcli run runs/<run>/inputs/Case.toml` reproduces a run outside
  the interface.

## 6. Scenario and builder

### 6.1 Scenario contents (plain terms, today's dollars, monthly where people think monthly)

| Section | Fields |
|---|---|
| People | names, birth dates, life horizon (89), filing status (from married/single) |
| Accounts | joint brokerage (amount and cost basis, split in two halves by the builder), each IRA, Roth/HSA if any, "as of" date |
| Work | per person: full-time through year Y; optional part-time years with pay; months worked in the last year; IRA or 401k contribution per year; employer contribution |
| Social Security | per person: PIA per work pattern (a small table: "if I stop in 2026 / 2027 / part time"), claiming ages fixed or "let Owl choose" |
| Health | marketplace from (derived from the last work year unless overridden), benchmark premium, gold-plan extra lines, out-of-pocket |
| Home | rent (monthly, flat until year, then inflation); a purchase: place (Yonkers, White Plains, Queens), year, price, financing (cash / mortgage / 5-year / 30-year, rate, down payment), closing costs, HOA, property tax, insurance, growth, selling commission; an optional sale year |
| Care | start year (or the last years of each life, I12), yearly cost, condo kept or sold that year |
| Spending | core spending; other lines (car, travel, charity, ...) with start/end, essential or not, survivor share |
| Goal (R7) | objective (spend the most each year, or leave the most), bequest floor on savings, survivor's spending share |
| Assumptions | rate method (with window or seed, or a named downturn sequence, D11), federal law (statutory or the 2032 reversion), inflation, the heirs' tax rate |
| Owl settings (R7) | Roth conversions (cap, first year, none), asset allocation, the two years' income before the plan (`previousMAGIs`, `previousSTARIncomes`), the spousal deposit split; each defaulting to the template's value and shown on an "Advanced" page |
| Run method | a preset (section 8.1) |

### 6.2 Builder

`build(scenario) -> (case_dict, hfp_workbook, provenance)` is deterministic and has no side
effects. It does the coupled edits of section 2 in one place:

- the place gives the state, locality, school district and a move in the purchase year;
- the purchase gives a Fixed Assets row in purchase-year dollars (grown by the case's own
  inflation path, as `make_cases.py` does), a Debts row linked to it by name, the big-ticket
  outflow, the owner's Budget lines from that year, and rent lines ending the year before;
- the last work year gives the marketplace start year, `months worked`, and the wages and
  contributions in the person sheets.

It starts from `make_cases.py` (`rent_lines`, `owner_lines`, `write_hfp`, `case`) moved into a
module with tests, so the suite and the interface share one implementation.

### 6.3 Generated rows versus hand edits

The user may want to adjust a single generated value, for example the 2029 closing costs.
**Provenance** keeps that from clashing with regeneration:

- Every generated row or cell records which event produced it (Budget, Debts and Fixed Assets
  rows by their `name`; person-sheet cells by event and year).
- An edit to a generated value is stored in the scenario as an **override** on that event ("closing
  costs 2029: 24,000 instead of 21,700"), shown with a marker and a "back to computed" button.
- A per-year cell that sums several sources (big-ticket items) stores the hand-entered part as the
  remainder, so later regeneration keeps it.
- When an event changes so that an override no longer applies (the purchase moved to 2031), the
  override is shown as orphaned and kept until the user drops it, never silently reapplied
  elsewhere.

### 6.3a Schema versions (R8)

`scenario.json` carries a `schema_version`. Version 1 (build step 1) holds hand rows only: the
case dictionary and the HFP tables as JSON. Events arrive in a later version (step 4). Each
format change ships a migration. A run whose scenario cannot be migrated stays readable and
solvable from its frozen files (section 5); only "edit as new run" needs the migration.

### 6.4 Bringing in existing files

"Import a case" reads a TOML and an HFP, such as `otherFiles/Case_us.toml` or a run made with
`make_cases.py`, into a scenario with no events: every row is a hand row. The run is usable at
once, and the user can turn rows into events later, or keep them as they are.

## 7. Saving, naming and versioning

```
Open a run ──edit──▶ unsaved changes (banner: "3 changes since wp-2029-mortgage")
                         │
                    [Save] │
                         ▼
          ┌───────────────────────────────────────────────┐
          │ Save as a new run                             │
          │ Changes: purchase year 2029 → 2031;           │
          │          down payment 20% → 30%               │
          │ Name: [wp-2031-mortgage-30down        ]       │  ← suggested from the changes
          │ Notes: [                               ]      │
          │ Collection: [Where and when to buy ▾]         │
          │ (Run it now: [Quick look ▾])                  │
          │      [Save as new]   [Overwrite draft]*       │  * only when the open run is an
          └───────────────────────────────────────────────┘    unsolved draft
```

- **The rename invitation is a save-as.** A solved run is never overwritten: its results belong
  to its inputs. "Overwrite" is offered only for an unsolved draft.
- **The change summary is computed**, not typed: a field-by-field diff of the two scenarios,
  worded per event ("purchase: White Plains 2029 mortgage → White Plains 2031 mortgage"). It
  suggests the name and is stored in `run.json`, so the library can show what each run changed
  from its parent.
- **Lineage:** every run records its parent, so the library can show a tree ("baseline → stop
  2027 → stop 2027 + part time"). Deleting a run keeps its children (their parent is shown as
  deleted).
- **Unsaved changes are kept** in a per-browser draft (browser storage, a convenience only), so a
  closed tab does not lose them. Nothing in the library depends on it.

## 8. Running

### 8.1 Presets instead of solver options

| Preset | What it runs | Use |
|---|---|---|
| Quick look | the default loop, claiming ages held at the scenario's values (no age search) | while entering data |
| Decision | local search, ages held fixed; the exact LP as a second result, read as an agreement check (does it order the variants the same way?), not as a tolerance (R2) | comparing variants |
| Ages | `run_suite.py`'s two-stage search: the exact LP searches, then the pick and its ±1-year neighbours are scored at fixed ages under the case's own model | when "let Owl choose" is set for claiming ages |
| Ages, thorough | `work_sweep.py`: every whole-year pair scored by branch-and-bound at gap 1e-5 (29-51 min per variant on the chris+pat dry run) | the final claiming decision |
| Custom | the existing Run Options page, for anything else | advanced |

The preset is part of the scenario, so it is in the inputs hash and in the change summary.
Every preset except the two Ages presets fixes the claiming ages (R4). The template's
`withSSAges = "optimize"` with `withMedicare = "optimize"` would make every age candidate a
branch-and-bound MIP (`phase0-scenarios.md`, section 4), so "quick" would not be quick.

### 8.2 Background jobs

- A job is one solve of one run in a separate worker program: a fresh interpreter, like `spawn`
  (CLAUDE.md, "Fork after HiGHS hangs"). It writes `solve.log` and `status.json` (state, PID, a
  heartbeat time) in its results folder.
- **One manager per server (R5).** The job manager is a process-wide singleton
  (`st.cache_resource`), so two browser tabs see one queue, and the queue itself lives on disk.
- **Detached workers (R5).** Without a choice made here, whether a worker outlives the server
  depends on how the server stops (recalled POSIX and `multiprocessing` behaviour, not tested
  here):
  - Ctrl-C in the terminal signals the whole process group, workers included;
  - a server killed alone leaves its workers running;
  - `multiprocessing` waits at exit for non-daemon children.

  So workers are started in their own session (`subprocess.Popen(..., start_new_session=True)`)
  and keep running across a server restart. At start-up the manager reads every `status.json`: a
  live PID with a fresh heartbeat is adopted, and a dead one is marked interrupted, with "run
  again". A "stop all jobs" button covers the case where the user wants them gone.
- A **Queue** page lists jobs: waiting, running (elapsed time, the last log line, the loop
  iteration), done, failed, interrupted. It refreshes on its own (`st.fragment(run_every=...)`,
  present in the installed Streamlit 1.66.1). Jobs can be cancelled (by PID).
- **Parallel jobs:** a setting, default 1 until measured. HiGHS and the claiming-age search use
  threads of their own, and `work_sweep.py` runs its own process pool.
- A time estimate comes from past solves of the same preset in the library.

### 8.3 The "as of" date

Owl's plan starts in the calendar year of the solve, whatever the case file says: `start_date`'s
year is ignored (`Plan._setStartingDate`: "Year is ignored"; every `thisyear` in `plan.py` is
`date.today().year`, checked 2026-11-01). Two consequences (R1):

- **Within the plan year**, results move from day to day: among other things, the date sets the
  share of the first year left (`yearFracLeft`).
- **Across a year boundary, a run's inputs become wrong.** Balances entered as of January 2026,
  solved in 2027, are read as January 2027 balances. The 2026 row of the workbook falls before
  the plan, and the purchase year is one year closer. Nothing warns.

So (D4, revised):

- (a) Record the solve date. Flag comparisons across dates ("solved 3 days apart: run both again
  today?"), with a "run the whole collection again today" button.
- (b) Freeze the worker's date (`date.today()`, the way `tests/conftest.py` does) to a date in the
  run's plan year. Results are then reproducible, and old runs can be solved again. This is now
  required, not optional, so it moves to step 2. Not yet checked outside pytest: if the freeze
  cannot be made reliable, the library refuses to solve a run outside its plan year.
- A run for a new year is made by the yearly check-in (I4): new balances, a new plan year, the
  old run as its parent.

## 9. Reviewing and comparing

### 9.1 A run's page

- **Header:** name, change summary, parent, solve date and method, status, and a plain-language
  quality line ("settled", or "the loop did not settle; differences under 1% are not
  meaningful").
- **Headline numbers:** the score (under `maxSpending` with essential lines, the first year's
  discretionary spending, as `run_suite.py` scores it), the home at the end and the savings at
  the end (today's \$), total taxes, the claiming ages used, SS withheld by the earnings test.
- **Charts** drawn from `plan.json`: spending over time, account balances, taxes by kind,
  income sources.
- **Tables:** the Results workbook's sheets.
- **Buttons:** "Open in Owl" (the existing pages, from the cached plan), "Download everything"
  (a zip of the run folder), "Edit as new run".

### 9.2 Comparison (the main decision screen)

- Pick two or more results.
- **Inputs:** the scenario diff in words.
- **Outputs:** side by side, with the difference.
- **Each difference is judged** against the noise rules (R2; CLAUDE.md, "Loop noise"; as
  `run_suite.py` does):
  - for proved plans (branch-and-bound), *resolved* when it is larger than both tolerances
    (reported gap x objective);
  - otherwise (loop or local search, which report no gap), *unresolved* (grey, "~") under 1%;
  - when the exact LP was run too, whether it orders the two the same way ("agree" /
    "disagree"). In plan years with marketplace coverage the exact LP mis-prices the ACA trade,
    so a disagreement there goes to the local-search result, not to a tie;
  - flagged when the runs were solved on different days or with different presets.
- **Two numbers, not one (R3).** With savings spent by 89, a plan's outcome is the score and the
  home at the end, reported side by side and never added: a cheaper or later purchase can buy
  more spending with less home (`run_suite.py`, its docstring). A variant "leads" only when it is
  at least as good on both and better on one beyond the noise rule; otherwise the comparison
  says "trade-off" and shows both.
- **"What moved":** the year-by-year differences in taxes, IRMAA, ACA, Roth conversions,
  withdrawals and claiming, so the user sees why one variant wins, not only that it wins.

### 9.3 Collections and grids

- "Make variants" from a run: choose a dimension (purchase year 2027, 2029, 2031, 2034, 2038;
  place; financing; last work year; claiming ages) and get one child draft per value, all in one
  collection, queued together.
- **Grid view:** the pivot `run_suite.py` writes in `report.md` (purchase year by place and
  financing), each cell showing the score's difference from the reference and the home at the
  end, coloured by the comparison rule.
- **The collection's question and rule are written on it**, for example "Maximize first-year
  discretionary spending, condo kept; reference: Yonkers 2027 cash". The page then shows the
  variants no other variant beats on both numbers, and whether each lead is resolved (R3).

## 10. Privacy and safety

- The library sits under `otherFiles/` (gitignored) by default; the interface refuses a library
  folder inside the repository that git does not ignore (checked with `git check-ignore`).
- **Localhost only (R11).** A running app cannot rebind its own server. So library mode ships a
  launcher that passes `--server.address=localhost`, and the app refuses library mode unless
  `st.get_option("server.address")` is `localhost` or `127.0.0.1`. No usage statistics. The AI
  pages stay off.
- "Load a Case Example" reads `examples/` from the local checkout (`ui/tomlexamples.loadCaseExample`),
  although its caption says GitHub.
- **Pickles (R10).** Loading a pickle can run code, so the library loads only `plan.pkl` files it
  wrote itself, checked against a hash in `record.json`. A run brought in from a zip comes
  without its pickles.
- No telemetry, no accounts. One user, one machine.
- Deleting a run moves it to `library/trash/`, emptied by hand.

## 11. Build steps

| Step | Content | Check |
|---|---|---|
| 1 | Library core (`run.json`, folders, inputs hash, save-as, lineage); scenario schema v1 (hand rows, R8); import of an existing TOML + HFP; saving from the existing pages through `config.ui_to_config` and `owlbridge.saveContributions`, not `getCaseString`, which is empty before the first run (R6) | unit tests; the synthetic cases import and export with the same case dictionary and HFP tables; an edited, never-solved case saves |
| 2 | Jobs: detached worker processes with PID and heartbeat, the singleton manager, queue page, results folder, `record.json`, plan cache; the frozen "as of" date (D4 b, R1) | a synthetic run solves in the background; a closed tab and a server restart do not lose it; "Open in Owl" restores Graphs without a solve (`owlbridge.genDic` builds the page keys from a Plan, unverified); two solves on different days give identical results |
| 3 | Library page, run page, comparison of two results with the noise rule | the synthetic baseline against a variant |
| 4 | Scenario model and builder from `make_cases.py`; scenario editor pages with provenance and overrides | the builder reproduces `make_cases.py`'s 39 workbooks cell for cell |
| 5 | Budget editor; the missing fork widgets (`withItemized`, `withSTAR`, all moves) | |
| 5b | Rate table in the case file (D11): a year-by-year rates CSV the case names, read by a new rate method; the named downturn sequences | `owlcli run` of a case with a table reproduces the interface's result |
| 6 | Collections, "make variants", grid view; the presets that run `run_suite.py`'s two-stage age search | the synthetic condo grid through the interface matches `run_suite.py`'s report |

Steps 1-3 give a library over the existing case pages, with hand-entered tables; until step 5,
Budget lines come only from an imported workbook. Step 4 is what removes the need to know Owl's
rows.

## 12. Upstream

- Steps 1-3 (storage, jobs, comparison) and the Budget editor are generic. The maintainer's hosted
  app has no disk to keep runs on, so they would come as an opt-in for local and Docker installs,
  proposed as a design issue first, per the fork's conventions (CLAUDE.md, "Upstream").
- The builder's events are partly generic (work, claiming, rent, purchase, care) and partly
  household-specific (the three places, HOA, the ARM stand-ins). The places would be a data file.
- The builder and scenario format would stay fork-only until the maintainer shows interest. His
  answer on #175 put budgeting in a separate project ("Owl-budget"), and the scenario's spending
  section overlaps it.

## 13. Further ideas

- **Readiness panel:** the `phase0-scenarios.md` checklist as live checks on the scenario
  (balances' "as of" date matches the start date, PIAs entered for each work pattern, wages
  entered as AGI wages, `months worked` in the last work year) before a run is allowed into a
  Decision comparison.
- **Assumptions page:** one page showing every assumption the household decided, with the
  reasons from the notes: statutory law (2066), savings spent by 89, the condo kept for care,
  ARM modeled as 5-year and 30-year loans. Each run's record lists which ones it used.
- **Stale runs:** a badge on results solved with an older Owl commit or before a scenario-format
  change, and "run again" for a collection.
- **Notes and pins:** free notes per run and per collection; pinned "candidates" at the top of
  the library.
- **Rounding:** headline numbers rounded to the run's tolerance (for example to \$100/yr when it
  is \$1-340/yr), so no false precision shows.
- **The synthetic household as a sandbox:** a read-only demo library built from `make_cases.py`,
  to try the interface before entering real data.

## 14. Ideas from other retirement planners (2026-11-01)

The user asked which features of popular planners (Boldin, ProjectionLab, MaxiFi, Pralana,
Income Lab) are worth taking, even where that means backend work in the fork.

### 14.0 Sources and how far they were checked

The first pass used web search summaries only. After the user allowed boldin.com and
robberger.com, Boldin's own pages were read with curl through the proxy. WebFetch still does not
resolve those hosts.

| Page | Date shown | Read |
|---|---|---|
| [Boldin vs. ProjectionLab](https://www.boldin.com/retirement/boldin-vs-projectionlab/) | 2026-04-17 | yes |
| [MaxiFi vs. Boldin](https://www.boldin.com/retirement/maxifi-vs-boldin-which-is-the-better-retirement-planning-tool-for-you/) | 2026-05-31 | yes |
| [Best retirement planning software](https://www.boldin.com/retirement/newretirement-vs-best-retirement-planning/) | 2026-06-04 | yes |
| [Roth conversion strategies in the Boldin Planner](https://www.boldin.com/retirement/how-to-model-roth-conversion-strategies-in-the-newretirement-planner/) | 2023-10-18 | yes |
| [Home equity in retirement](https://www.boldin.com/retirement/how-to-use-home-equity-in-retirement/) | 2026-10-10 | yes |
| [Planning for long-term care](https://www.boldin.com/retirement/planning-for-long-term-care/) | 2026-09-07 | yes |
| [Long-term health care costs](https://www.boldin.com/retirement/long-term-health-care/) | 2025-03-20 | yes |
| robberger.com (Boldin, ProjectionLab, MaxiFi reviews) | | no: a Cloudflare "you have been blocked" page |
| help.boldin.com, projectionlab.com, maxifi.com, incomelaboratory.com | | no: the proxy refuses the connection (403); not on the allow list |

Labels used below:

- **Verified (Boldin page):** read on one of the Boldin pages above.
- **Per Boldin:** a competitor's feature as Boldin's comparison pages describe it. These are
  read, but they are a competitor's description, not the product's own documentation.
- **Reported:** seen only in search summaries.
- **Recalled:** from memory, not checked.

Owl's side was checked in the code (grep, 2026-11-01). Owl already has:

- Monte Carlo and historical-range backtests (`ui/Monte_Carlo.py`, `ui/Historical_Range.py`);
- a frontier between committed spending and shortfall risk, with spending at a target success
  rate (`stresstests.g_for_success_rate`, `ui/Spending_Optimization.py`);
- a spending-versus-bequest frontier, annuities (SPIA), medical inflation above CPI, and the
  smile spending profile;
- Roth conversions optimized inside the model;
- year-by-year rate sequences, but only programmatically (`owlcli list-rates`: the `dataframe`
  model, "Programmatic use only").

Searches with no hit in `src` or `ui`: "sankey", "milestone", "reverse mortgage",
"long-term care". "guardrail" appears once, in an unrelated comment in `plan.py`.

Corrections to the first pass (2026-11-01):

- **Scenario counts:** Boldin keeps up to 10 saved scenarios and MaxiFi 25, and they compare
  2-3 and 3 side by side respectively (per Boldin). The first pass said "up to 10 side by side".
- **Milestone "bindings":** Boldin's page says only that ProjectionLab models "life milestones
  with custom timing". The "dynamic bindings" wording came from a search summary and is
  unconfirmed.
- **Boldin's "Insights":** it appears to be a section of charts ("Insights > Income & Expenses >
  Estimated Expenses", reported, help center), not threshold alerts. I3 no longer cites it.
- **The Roth Conversion Explorer** (verified, 2023 page):
  - it runs a "greedy-type" algorithm toward one of four goals: maximize the estate, minimize
    lifetime taxes, convert up to a tax bracket, convert up to an IRMAA bracket;
  - it shows the IRMAA fees with and without the conversions;
  - it ignores conversions already in the plan and says nothing about the current year;
  - "The Planner does not currently model ACA subsidies so these are not considered by the
    Explorer."
  - Kotlikoff's criticism (no pricing of future taxes and IRMAA) is reported only, and the 2023
    page contradicts its IRMAA half.

### 14.1 Worth taking, in order of value to this household

| # | Idea | Seen in | What Owl has | Proposal | Cost |
|---|---|---|---|---|---|
| I1 | **Events dated relative to other events**, so moving one moves the rest | ProjectionLab: "life milestones with custom timing" (per Boldin); bindings unconfirmed | Fixed calendar years everywhere | Builder events take anchors: "the year after Noa's last work year", "at age 86", "the purchase year". The marketplace start, `months worked`, the rent end and the owner lines follow by construction. | Builder only (section 6) |
| I2 | **Survivor and longevity variants** | Boldin models the first death: separate longevities, the survivor SS switch, RMD and asset transitions, single filing (per Boldin). MaxiFi's Survivor Report sizes life insurance (per Boldin). Pralana survivor scenarios (reported). | One fixed horizon per person (89); Owl already handles the death mechanics | A "make variants" dimension: first death at 75, 80, 85, each spouse in turn. Shows what the 60% survivor share and single filing cost, and whether the condo plan holds for a survivor. | Builder and collections; no backend |
| I3 | **"Things to look at" (threshold proximity)** | No planner verified | Thresholds known inside the model; `owlcli explain` reports some | After each solve, list the years where MAGI sits just below or just over a threshold (IRMAA tiers, NY recapture, the Enhanced STAR limit, the 0% gains bracket, the SS taxability bands, the marketplace subsidy limits), each with its amount. An invented example: "2031: \$1,200 over IRMAA tier 1, cost \$1,900". | Backend: a report from the solved arrays; no model change |
| I4 | **Yearly check-in: plan against actual** | Boldin links accounts through Plaid, Finicity and MX (verified); ProjectionLab enters balances by hand or through plugins (per Boldin) | Nothing; a plan starts from the balances entered | Offline, no linking. Once a year the user enters actual balances and the year's spending; the library makes a child run from that date. A drift chart shows projected against actual balances over the years, and the new plan's spending against the old. | Library and builder (balances' date, #167's first-year rule); no model change |
| I5 | **Spending guardrails**: a spending level plus portfolio levels at which to cut or raise it | Boldin: "Safe Spending Target is calibrated to maintain roughly an 80% success rate, with upper (95%) and lower (70%) thresholds", on 1,000 simulations (verified). Income Lab: risk-based guardrails (reported; advisor software only, per Boldin). | Spending at a target success rate from the stochastic frontier; no rule for later years | For a solved run, compute the spending at the target success rate for a grid of starting balances one year ahead, and report the two portfolio levels at which that spending leaves a band (70% and 95%, as Boldin). Shown as "if savings fall below \$X next January, plan again; expected cut \$Y/yr". | Backend: one stochastic frontier per grid point; measure the cost first (D9) |
| I6 | **Cash-flow Sankey for one year** | ProjectionLab "displays projected income, spending, and asset flows as a Sankey diagram ... year by year" (per Boldin); Boldin's "Money Flows" (verified name, contents not read) | A cash-flow mix chart over all years; the Cash Flow sheet | On a run's page, pick a year and see the sources (wages, SS, each account, the condo sale) flow to the uses (spending lines, taxes by kind, premiums, the purchase, conversions). Most useful for the purchase year and the first Medicare year. | UI only, from `plan.json` plus the cash-flow arrays |
| I7 | **Claiming-age map** | Boldin: "compare claiming ages and spousal benefit strategies and see what timing does to your tax bracket and withdrawal sequencing" (per Boldin) | `withSSAges` picks ages; `work_sweep.py` scores all whole-year pairs and writes `scores.json` | A heat map of the objective over the two claiming ages, ties within tolerance shaded together, for each work variant. | UI only, over `work_sweep.py` output |
| I8 | **Conversion and bracket view** | Boldin's Explorer (verified, 14.0); MaxiFi's Roth Conversion Optimizer "searches across many possible conversion patterns" for lifetime discretionary spending (per Boldin); Boldin shows "how distributions affect your tax bracket over time and where conversion windows close" (per Boldin) | Conversions optimized with IRMAA, ACA, SS taxability and state tax in the model; no explorer needed | Explain them instead: per year, taxable income against the bracket edges and the IRMAA and ACA lines, with the conversion shown as the layer that fills them. The regret sweep (`stresstests.run_conversion_regret_sweep`) gives "what a different conversion would have cost". | UI, plus a regret-sweep run per request |
| I9 | **Sensitivity "tornado"** | Generic (no planner named) | Single variants, compared one at a time | One button on a run: re-solve with each key input moved by a set step (returns -1 point, inflation +1 point, medical inflation +2 points, condo price +10%, the 2027 marketplace benchmark, the 2032 reversion, the first death at 80). Bars sorted by effect, each with its tolerance. | Collections, under the exact LP for speed; no backend |
| I10 | **Tapping the condo: reverse mortgage (HECM)** (declined, D10) | Boldin: "Reverse mortgage. Model one in Home & Real Estate and compare your savings at 85 and 95"; for care, "Choose home equity as a way to pay for care and see how long it lasts" (verified). Reported (help center, not read): a line of credit from 62 or later, drawn after after-tax savings run out and before retirement savings; no lump sums or income streams. | Fixed assets can be sold (`fixedassets.sale_year_in_plan`); loans are fixed-rate amortizing (`debts.py`); home equity cannot be borrowed against | The condo is the long-term-care reserve. Selling it is modeled (the suite's `ltc` group); borrowing against it is not. A HECM line of credit, whose balance grows and is repaid at the sale or the last death, would be a new Debts kind tied to the residence. **Needs HUD's own rules before any design.** | Backend (new debt kind, LP rows for draws); largest item here |
| I11 | **Named downturn sequences** | Boldin's Market Risk Explorer: "custom downturns, a decade of poor returns, or a three-year sequence of negative returns as stress tests" (verified) | Historical windows replayed in order; constant rates; year-by-year sequences only programmatically (`dataframe`) | A "make variants" dimension of named sequences placed at a chosen year (retirement, the purchase year): a 30% fall in year 1, three negative years, a poor decade. Their effect is largest at the start of retirement, where the household's decisions sit. | Backend: a year-by-year rate table a case file can name (for example a CSV next to `Case.toml`), so `owlcli run` reproduces the run; generic, could go upstream |
| I12 | **Care anchored to the end of life** | Boldin models care by default "during the last 28 months of your life", at national medians (\$1,966/mo for 12 months, then \$5,900/mo for 16, today's \$; verified, 2025 page) | Budget lines on an age clock (Track B); the synthetic case's care line is a stand-in from age 86 | The care event (D6) defaults to the last N months of each life, so it moves with the I2 longevity variants, with NY-metro costs from a cited survey in place of national medians. The source and figures are still to be found and checked. | Builder; a data file of regional costs |

### 14.2 Seen, not proposed

- **Monte Carlo "chance of success"** (Boldin, 1,000 paths, verified; ProjectionLab up to 2,000
  trials, per Boldin). Owl has Monte Carlo and the success-rate frontier; the library would only
  show their results on the run page.
- **Living-standard Monte Carlo**, where spending adjusts each year instead of holding fixed
  (MaxiFi, per Boldin, with "Upside Investing" and "Full Risk Investing" variants). Owl's
  stochastic spending frontier answers a neighbouring question; adding a second method is not
  worth it before I5.
- **Historical backtesting** (ProjectionLab, per Boldin). Owl's Historical Range covers it, and
  the suite's rate group runs every 28-year window.
- **Many saved scenarios** (Boldin 10, MaxiFi 25; 2-3 and 3 side by side, per Boldin). The library
  keeps any number, and section 9.2 compares any number of results.
- **Account linking** (Boldin, verified). It contradicts the offline rule; I4 does it by hand
  once a year.
- **An AI assistant that reads and edits the plan** (Boldin AI, verified). It sends the
  household's data to a service, against the offline rule, like Owl's own opt-in Assistant and
  MCP server.
- **Monthly cash flow** (recalled for Boldin). Owl is annual; a monthly budget belongs to
  Owl-budget (#175).

### 14.3 Where they fit in the build steps

- **I1, I2 and I12** come with step 4 (builder) and step 6 (collections).
- **I3, I6 and I7** come with step 3 (run page).
- **I4** comes after step 6.
- **I8 and I9** come with step 6.
- **I11** is build step 5b (D11), then the variant dimension with step 6.
- **I5** is a separate backend project, measured before it is designed (D9).
- **I10** is declined (D10).

## 15. Decisions

The user's answers of 2026-11-01: "D1-D9 in principle", then "D11 yes, D10 no". The review
(`run-library-review.md`) revised D4.

| # | Question | Proposal | Status |
|---|---|---|---|
| D1 | Inside the existing Streamlit app (new section, opt-in) or a separate app? | Inside: the case pages, results pages and multi-case session are reused; "Open in Owl" needs the same session. | accepted in principle |
| D2 | Source of truth: the scenario (events) or Owl's own TOML + HFP? | The scenario, with TOML + HFP generated and saved beside it; imports become scenarios with hand rows. | accepted in principle |
| D3 | May a solved run's inputs be overwritten? | No: save-as only. Drafts may be overwritten. | accepted in principle |
| D4 | "As of" date: record and flag (a), or also freeze (b)? | Both, in step 2 (revised after R1: a run solved outside its plan year has wrong inputs, so (b), or a refusal, is required). | accepted in principle; revision R1 confirmed 2026-11-01 |
| D5 | Where does the library live? | `otherFiles/library/`, configurable. | accepted in principle |
| D6 | First events to build | Work (with PIA per pattern), claiming, rent, condo purchase (three places, cash/mortgage/ARM stand-ins), care. Moves without a purchase, sale and re-buy later. | accepted in principle |
| D7 | Charts on the run page: from `plan.json` (durable) or Owl's own plots from the cached plan? | `plan.json` for the library and comparisons; Owl's plots through "Open in Owl". | accepted in principle |
| D8 | Upstream: propose steps 1-3 as a design issue after they work in the fork? | Yes, after step 3. | accepted in principle |
| D9 | Guardrails (I5): worth a measurement of their cost (one stochastic frontier per grid point)? | Yes, once the household's case runs offline and the yearly check-in (I4) exists; before that, the success-rate spending of the existing frontier is enough. | accepted in principle |
| D10 | Reverse mortgage (I10): research HUD's HECM rules as a possible use of the condo reserve? | Only if the long-term-care question becomes "keep the condo and borrow" rather than "keep or sell". Boldin models exactly this trade (14.1, I10). | declined |
| D11 | Downturn sequences (I11): add a case-file rate table so named sequences run through `owlcli`? | Yes, as a generic backend addition, before step 6 (build step 5b). | accepted |

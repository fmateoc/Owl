# Run library: a local web interface for the household's runs

Design draft, 2026-11-01. Nothing here is built yet. Decisions for the user are marked **D1-D8**
at the end; each proposes an answer.

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
| **Run** | A saved scenario (frozen), its generated files, and at most one result per solve. Never edited in place; editing makes a new run whose parent is this one. |
| **Draft** | A run that has not been solved. It may be overwritten. |
| **Collection** | A named set of runs answering one question ("Where and when to buy?"), with a comparison rule. A grid of variants (place x year x financing) is a collection. |
| **Library** | The folder that holds the runs and collections. |

## 5. Storage (one folder per run, plain files)

```
otherFiles/library/                      # gitignored (otherFiles/ is ignored upstream)
  library.json                           # collections, tags, pins, the order shown
  runs/
    2026-11-03_wp-2029-mortgage/         # <date>_<slug>; the slug follows renames, the id does not
      run.json                           # id, name, parent id, created, notes, tags,
                                         # inputs hash, change summary against the parent
      inputs/
        scenario.json                    # the source of truth
        Case.toml                        # generated: owlcli and the existing pages read it
        HFP.xlsx                         # generated
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
| Care | start year, yearly cost, condo kept or sold that year |
| Spending | core spending; other lines (car, travel, charity, ...) with start/end, essential or not, survivor share |
| Assumptions | rate method (with window or seed), federal law (statutory or the 2032 reversion), inflation, the heirs' tax rate |
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
| Quick look | the default loop | while entering data; minutes or less |
| Decision | local search, and the exact-LP cross-check as a second result of the same run | comparing variants (CLAUDE.md, "Loop noise") |
| Ages | the two-stage claiming-age search of `run_suite.py` / `work_sweep.py` | when "let Owl choose" is set for claiming ages |
| Custom | the existing Run Options page, for anything else | advanced |

The preset is part of the scenario, so it is in the inputs hash and in the change summary.

### 8.2 Background jobs

- A job is one solve of one run, in its own process started with `spawn` (CLAUDE.md, "Fork after
  HiGHS hangs"), writing `solve.log` and a status file in the run's results folder.
- A **Queue** page lists jobs: waiting, running (elapsed time, the last log line, the loop
  iteration), done, failed, interrupted. It refreshes on its own (`st.fragment(run_every=...)`, present in the installed Streamlit 1.66.1).
  Jobs can be cancelled.
- The number of parallel jobs is a setting (default: cores / 2).
- Jobs survive a closed tab. When the server stops, running jobs stop too; at the next start they
  show as interrupted, with "run again".
- A time estimate comes from past solves of the same preset in the library.

### 8.3 The "as of" date

Plans start on the solve day, so one run's results move from day to day. Two options (**D4**):

- (a) Record the solve date and flag comparisons across dates ("solved 3 days apart: run both
  again today?"), with a "run the whole collection again today" button.
- (b) Also let a run fix its "as of" date: the worker freezes `date.today()` before solving, the
  way `tests/conftest.py` does. Results are then reproducible. Not yet checked outside pytest.

## 9. Reviewing and comparing

### 9.1 A run's page

- **Header:** name, change summary, parent, solve date and method, status, and a plain-language
  quality line ("settled", or "the loop did not settle; differences under 1% are not
  meaningful").
- **Headline numbers:** spending per year (today's \$), the condo and savings at the end, total
  taxes, the claiming ages used, SS withheld by the earnings test.
- **Charts** drawn from `plan.json`: spending over time, account balances, taxes by kind,
  income sources.
- **Tables:** the Results workbook's sheets.
- **Buttons:** "Open in Owl" (the existing pages, from the cached plan), "Download everything"
  (a zip of the run folder), "Edit as new run".

### 9.2 Comparison (the main decision screen)

- Pick two or more results.
- **Inputs:** the scenario diff in words.
- **Outputs:** side by side, with the difference.
- **Each difference is judged** against the noise rules (CLAUDE.md, "Loop noise"):
  - *resolved* when it is larger than both runs' tolerances (the gap times the objective for a
    proved plan, or the spread between local search and the exact LP);
  - *unresolved* (grey, "~") otherwise;
  - flagged when the runs were solved on different days or with different presets.
- **"What moved":** the year-by-year differences in taxes, IRMAA, ACA, Roth conversions,
  withdrawals and claiming, so the user sees why one variant wins, not only that it wins.

### 9.3 Collections and grids

- "Make variants" from a run: choose a dimension (purchase year 2027, 2029, 2031, 2034, 2038;
  place; financing; last work year; claiming ages) and get one child draft per value, all in one
  collection, queued together.
- **Grid view:** the pivot `run_suite.py` writes in `report.md` (purchase year by place and
  financing), each cell coloured by the comparison rule against the collection's reference run.
- **The collection's question and rule are written on it**, for example "Maximize first-year
  spending, condo kept; reference: Yonkers 2027 cash". The page then shows the current leader and
  whether its lead is resolved.

## 10. Privacy and safety

- The library sits under `otherFiles/` (gitignored) by default; the interface refuses a library
  folder inside the repository that git does not ignore (checked with `git check-ignore`).
- In library mode the server binds to `localhost` and sends no usage statistics. The AI pages
  stay off, and "Load a Case Example" (which fetches from GitHub) is the only network use.
- No telemetry, no accounts. One user, one machine.
- Deleting a run moves it to `library/trash/`, emptied by hand.

## 11. Build steps

| Step | Content | Check |
|---|---|---|
| 1 | Library core (`run.json`, folders, inputs hash, save-as, lineage) and import of an existing TOML + HFP | unit tests; the synthetic cases import and export with the same case dictionary and HFP tables |
| 2 | Jobs: spawn worker, status, queue page, results folder, `record.json`, plan cache | a synthetic run solves in the background; a closed tab does not stop it; "Open in Owl" restores Graphs without a solve |
| 3 | Library page, run page, comparison of two results with the noise rule | the synthetic baseline against a variant |
| 4 | Scenario model and builder from `make_cases.py`; scenario editor pages with provenance and overrides | the builder reproduces `make_cases.py`'s 39 workbooks cell for cell |
| 5 | Budget editor; the missing fork widgets (`withItemized`, `withSTAR`, all moves) | |
| 6 | Collections, "make variants", grid view; the presets that run `run_suite.py`'s two-stage age search | the synthetic condo grid through the interface matches `run_suite.py`'s report |
| 7 | As-of date (if D4 b) | two solves on different days give identical results |

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

## 14. Decisions for the user

| # | Question | Proposal |
|---|---|---|
| D1 | Inside the existing Streamlit app (new section, opt-in) or a separate app? | Inside: the case pages, results pages and multi-case session are reused; "Open in Owl" needs the same session. |
| D2 | Source of truth: the scenario (events) or Owl's own TOML + HFP? | The scenario, with TOML + HFP generated and saved beside it; imports become scenarios with hand rows. |
| D3 | May a solved run's inputs be overwritten? | No: save-as only. Drafts may be overwritten. |
| D4 | "As of" date: record and flag (a), or also freeze (b)? | (a) in step 2; (b) in step 7, if the freeze works outside pytest. |
| D5 | Where does the library live? | `otherFiles/library/`, configurable. |
| D6 | First events to build | Work (with PIA per pattern), claiming, rent, condo purchase (three places, cash/mortgage/ARM stand-ins), care. Moves without a purchase, sale and re-buy later. |
| D7 | Charts on the run page: from `plan.json` (durable) or Owl's own plots from the cached plan? | `plan.json` for the library and comparisons; Owl's plots through "Open in Owl". |
| D8 | Upstream: propose steps 1-3 as a design issue after they work in the fork? | Yes, after step 3. |

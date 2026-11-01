# Run library: a local web interface for the household's runs

Design draft, 2026-11-01. Nothing here is built yet. Decisions for the user are marked **D1-D10**
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

## 14. Ideas from other retirement planners (2026-11-01)

The user asked which features of popular planners (Boldin, ProjectionLab, MaxiFi, Pralana,
Income Lab) are worth taking, even where that means backend work in the fork.

**Sources and how far they were checked:**

- **"Reported"** means the feature appeared in web search results on 2026-11-01. Those results
  are mostly the vendors' own pages and affiliate reviews, seen only as search summaries. The
  pages could not be opened: boldin.com and robberger.com do not resolve from this container.
- **"Recalled"** means from memory, not checked.
- **Owl's side** was checked in the code (grep, 2026-11-01). Owl already has:
  - Monte Carlo and historical-range backtests (`ui/Monte_Carlo.py`, `ui/Historical_Range.py`);
  - a frontier between committed spending and shortfall risk, with spending at a target success
    rate (`stresstests.g_for_success_rate`, `ui/Spending_Optimization.py`);
  - a spending-versus-bequest frontier, annuities (SPIA), medical inflation above CPI, and the
    smile spending profile;
  - Roth conversions optimized inside the model, rather than proposed by a separate explorer.
- **Searches with no hit in `src` or `ui`:** "sankey", "milestone", "reverse mortgage",
  "long-term care". "guardrail" appears once, in an unrelated comment in `plan.py`.

### 14.1 Worth taking, in order of value to this household

| # | Idea | Seen in | What Owl has | Proposal | Cost |
|---|---|---|---|---|---|
| I1 | **Milestones with bindings**: events dated relative to other events, so moving one moves the rest | ProjectionLab (reported: "milestones ... dynamic bindings") | Fixed calendar years everywhere | Builder events take anchors: "the year after Noa's last work year", "at age 86", "the purchase year". The marketplace start, `months worked`, the rent end and the owner lines follow by construction. | Builder only (section 6) |
| I2 | **Survivor and longevity variants** | Pralana (reported: "examines ... survivor scenarios"); MaxiFi plans to a maximum age (recalled) | One fixed life horizon per person (89) | A "make variants" dimension: first death at 75, 80, 85, each spouse in turn, with the survivor's spending share. Shows what the 60% survivor share and the single filer's brackets cost, and whether the condo plan holds for a survivor. | Builder and collections; no backend |
| I3 | **"Things to look at" (threshold proximity)** | Boldin "Insights" (recalled) | Thresholds known inside the model; `owlcli explain` reports some | After each solve, list the years where MAGI sits just below or just over a threshold: IRMAA tiers, NY recapture, the Enhanced STAR limit, the 0% gains bracket, the SS taxability bands, the marketplace subsidy limits. Each with its amount (an invented example: "2031: \$1,200 over IRMAA tier 1, cost \$1,900"). | Backend: a report from the solved arrays; no model change |
| I4 | **Yearly check-in: plan against actual** | Boldin and ProjectionLab track progress through linked accounts (recalled) | Nothing; a plan starts from the balances entered | Offline, no account linking. Once a year the user enters the actual balances and the year's spending; the library makes a child run from that date. A drift chart shows the plan's projected balances against the actual ones over the years, and the new plan's spending against the old. | Library and builder (balances' date, #167's first-year rule); no model change |
| I5 | **Spending guardrails**: a spending level plus portfolio levels at which to cut or raise it | Income Lab (reported: risk-based guardrails, lower and upper portfolio triggers); Boldin (reported: safe spending target at 80% chance of success, guardrails at 95% and 70% when retired) | Spending at a target success rate from the stochastic frontier; no rule for the next years | For a solved run, compute the spending at the target success rate for a grid of starting balances one year ahead, and report the two portfolio levels at which that spending leaves a band (for example 70% and 95%). Shown as "if savings fall below \$X next January, plan again; expected cut \$Y/yr". | Backend: repeated stochastic-frontier solves (expensive: a Monte Carlo run per grid point); measure the cost first |
| I6 | **Cash-flow Sankey for one year** | ProjectionLab (reported: a Sankey of money in and out for each simulated year) | A cash-flow mix chart over all years; the Cash Flow sheet | On a run's page, pick a year and see sources (wages, SS, each account, the sale of the condo) flow to uses (spending lines, taxes by kind, premiums, the purchase, conversions). The purchase year and the first Medicare year are where it explains the most. | UI only, from `plan.json` plus the cash-flow arrays |
| I7 | **Claiming-age map** | Boldin and MaxiFi each have a Social Security explorer or strategy finder (reported) | `withSSAges` picks ages; `work_sweep.py` scores all whole-year pairs and writes `scores.json` | A heat map of the objective over the two claiming ages, ties within tolerance shaded together, for each work variant. Read from the sweep's saved scores. | UI only, over `work_sweep.py` output |
| I8 | **Conversion and bracket view** | Boldin's Roth conversion explorer and MaxiFi's Roth optimizer (reported); Kotlikoff criticizes Boldin's explorer for not pricing future taxes and IRMAA (reported) | The conversions are optimized, with IRMAA, ACA, SS taxability and state tax in the model, so no explorer is needed | Explain them instead: per year, taxable income against the bracket edges and the IRMAA and ACA lines, with the conversion shown as the layer that fills them. The regret sweep (`stresstests.run_conversion_regret_sweep`) gives "what a different conversion would have cost". | UI, plus a regret-sweep run per request |
| I9 | **Sensitivity "tornado"** | Generic (recalled; no planner named here) | Single variants, compared one at a time | One button on a run: re-solve with each key input moved by a set step (returns -1 point, inflation +1 point, medical inflation +2 points, condo price +10%, the 2027 marketplace benchmark, the 2032 reversion, the first death at 80). Bars sorted by effect, each with its tolerance. Tells the household which inputs deserve the most care. | Collections, under the exact LP for speed; no backend |
| I10 | **Tapping the condo: reverse mortgage (HECM)** | Boldin models home equity (recalled; not checked) | Fixed assets can be sold (`fixedassets.sale_year_in_plan`) and loans are fixed-rate amortizing (`debts.py`); home equity cannot be borrowed against | The condo is the household's long-term-care reserve. Selling it is modeled (the suite's `ltc` group); borrowing against it is not. A HECM line of credit, whose balance grows and is repaid at the sale or the last death, would be a new Debts kind tied to the residence. **Needs the rules from HUD's own documents before any design.** | Backend (new debt kind, LP rows for draws); largest item here |

### 14.2 Seen, not proposed

- **Monte Carlo "chance of success"** (Boldin, reported: 1,000 simulations). Owl has Monte Carlo
  and the success-rate frontier. The library would only show their results on the run page.
- **Living-standard Monte Carlo**, where spending adjusts each year instead of holding fixed
  (MaxiFi, reported). Owl's stochastic spending frontier answers a neighbouring question; adding
  a second method is not worth it before I5.
- **Historical backtesting** (ProjectionLab, reported). Owl's Historical Range covers it, and the
  suite's rate group runs every 28-year window.
- **Side-by-side comparison of up to 10 scenarios** (Boldin, reported). Section 9.2 already
  compares any number of results.
- **Account linking** (Boldin, recalled). It contradicts the offline rule; I4 does it by hand
  once a year.
- **Monthly cash flow** (recalled for Boldin). Owl is annual; a monthly budget belongs to
  Owl-budget (#175).

### 14.3 Where they fit in the build steps

- **I1 and I2** come with step 4 (builder) and step 6 (collections).
- **I3, I6 and I7** come with step 3 (run page).
- **I4** comes after step 6.
- **I8 and I9** come with step 6.
- **I5 and I10** are separate backend projects, each measured or researched before it is
  designed (D9, D10).

## 15. Decisions for the user

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
| D9 | Guardrails (I5): worth a measurement of their cost (one stochastic frontier per grid point)? | Yes, once the household's case runs offline and the yearly check-in (I4) exists; before that, the success-rate spending of the existing frontier is enough. |
| D10 | Reverse mortgage (I10): research HUD's HECM rules as a possible use of the condo reserve? | Only if the long-term-care question becomes "keep the condo and borrow" rather than "keep or sell". |

# UX and ergonomics review of the browser UI (2026-11-07)

Audit only: no code was changed. The yardstick is the user's spouse, a physician: analytical,
reads longitudinal charts and probability ranges, wants to know *why* the plan does what it does,
and has no interest in the solver, TOML keys, tracebacks or sign conventions.

## Status of the fixes (2026-11-07, branches `claude/ux-fixes` and `claude/dazzling-gauss-69epxn`)

Work orders `fork-notes/ux-fixes-handoff.md` and `fork-notes/ux-q10-q20-handoff.md`; details in
PROGRESS.md "UX review: the four bugs", "UX review: quick wins Q1-Q9" and "UX review: quick wins
Q10-Q20, and B3's issue reworked".

| Item | State |
|---|---|
| Q3 (= bug B1) Queue's "decision" | **Done**: `preset_solves`, two jobs queued (re-driven) |
| bug B2 purchase on an imported run | **Done**: refused as two homes; a blank district keeps the case's, `-` is none; the purchase box pre-fills from the case with dropdowns (part of Q19) |
| Q21 (= bug B3) solve after a failed configuration | **Done** in the fork with the stock-`dev` patch; issue draft `fork-notes/issue-prepare-run-failure.md`, not filed. Revised 2026-11-07 (user): the `setACA` hint for a year before 2000 dropped (fork back to upstream's), the repro is a move to the starting state |
| Q5 (= bug B4) dollar labels as math | **Done**, with a source check over `ui/` |
| Q1 codes in rendered strings | **Done** on Run, Compare, Scenario, Collections, Library, Queue and the comparison's notes; file names kept only in a help tooltip (the scores-file uploader) |
| Q2 preset names | **Done** (`ui/librarypresets.py`); times as measured: quick ~1 s, Careful ~5 min; Ages not timed, so "slow" |
| Q4 Compare's default pair | **Done**; no pinned baseline: nothing in the library sets `pins` |
| Q6 units, separators, index | **Done** for axes and the two tables; no today's-\$ toggle (`plan.json` has no deflator: structural) |
| Q7 headline wording | **Done** (`view.claiming_ages_phrase`, `view.spent_down_by_design`) |
| Q8 Queue phase in words | **Done** (`libraryjobs.job_phase`) |
| Q9 change summaries | **Done in the diff** (`scenario.PATH_LABELS`, `NO_OP_DEFAULTS`); `scenario_from_ui` unchanged, so no inputs hash moves |
| Q10 import form | **Done**: companions named by the case, refusal by name, no temp path, form kept open (`ui/library_import.py`) |
| Q11 workbook confirmation | **Done** (for everyone; "(Optional)" dropped for a budget profile, fork only); issue draft `fork-notes/issue-create-case.md`, not filed |
| Q12 after Open in Owl | **Done** in `owlbridge.openCaseFromPlan` (fork only: no upstream route reaches it) |
| Q13 Edit as new run | **Done**: switches to Run Options, message under the title bar |
| Q14 library-mode chrome | **Done**: `--client.toolbarMode=viewer` (not `minimal`, which also hides Print), Welcome's AI paragraph hidden; *Connect your AI* kept (the user's call, W9) |
| Q15 brackets chart | **Done** (`ui/run_charts.py`) |
| Q16 taxes and premiums, income sources | **Done**; the purchase year from `cash_flow`, `plan.json` unchanged |
| Q17 one-year Sankey | **Done**: paragraph and Sankey from the same groups |
| Q18 buttons gated on a text field | **Done** on Collections and Create Case (reproduced with Playwright first); issue draft `fork-notes/issue-create-case.md`, not filed; duplicate collection names refused |
| Q19 purchase box | **Done** (the dropdowns were B2's) |
| Q20 Goals / Run Options wording | **Done**: Goals in library mode only; the SLCSP field for everyone, issue draft `fork-notes/issue-slcsp-field.md`, not filed |
| S5 | **Partly done** (QW-2/QW-3, 2026-11-07, `claude/upbeat-planck-c731oy`): crossings of the IRMAA tiers, the 400% FPL line and the Enhanced STAR limit reported beyond the band with their cost, in a compact table of their own; the NY decomposition (`by_year` recapture, local tax, STAR) not built |
| S6 | **Partly done** (QW-1): the paragraph, the Sankey and a two-column sources/uses table with group subtotals and a totals line share one set of words; no separate year card |
| S9 | **Partly done** (QW-4, QW-8): \$20M balance warning; Roth, swap and ACA years bounded by the plan (the ACA start a toggle); financing ranges refused and unit slips warned on Scenario and Collections; no benchmark-premium range flag, errors not rewritten |
| S1-S4, S7, S8, S10 | Not started (the user's call) |

## How this was checked

- **The app was run and driven.** It ran in library mode (`OWL_LIBRARY_DIR=otherFiles/library`,
  `--server.address=localhost`, as `owlplanner-library.sh` starts it) on `main` at `1623d2e`,
  Streamlit 1.66.1. A headless Chromium (Playwright) drove it at 1440x900, one browser session
  per journey, so `session_state` behaved as it does for a person. The case was the synthetic
  household (`fork-notes/synthetic/`, `Case_ari+noa_condo.toml` with
  `HFP_ari+noa_condo_yonkers_2029_cash.xlsx`), never the real one.
- **What actually ran:**
  - an import into the library;
  - three background solves, all finished: "decision" in 4 min 49 s, its exact companion in
    9 s, and a what-if in 5 min 25 s;
  - one foreground solve on the classic Graphs page, which had not finished after 22 minutes;
  - "Open in Owl", Compare, the Scenario page, Collections, and the input-validation probes
    below.
- **Tags.** Each finding says how it is known:
  - **[seen]**: observed in the running app (screenshot or captured page text);
  - **[ran]**: checked by running the library code directly or reading a solve's own files
    (`plan.json`, `Results.xlsx`);
  - **[code]**: read in the source and not exercised.
- **Not walked:** the Stress Tests pages (Historical Range, Monte Carlo, Spending Optimization,
  Spending vs Bequest); Tools (Settings, Logs); Help (Documentation, Parameters Reference),
  except that a grep found no mention of the Run Library in `Welcome.py` or `Documentation.py`;
  the sensitivity tornado and the regret sweep, which were not queued; a collection grid with
  solved members (it needs an event-built run; see F3); widths other than 1440 px; Windows.
- The screenshots are in the session scratchpad and are not committed.

---

## 1. Top 5 high-impact friction points

### F1. Two apps, no home: nothing opens the household, and the classic route blocks and forgets

- **Cold start [seen].**
  - Opening `localhost:8501` lands on upstream's marketing **Welcome** page under a disclaimer
    modal, the same in every new session.
  - The page's third headline is "Powered by Actual Intelligence — connect it to your AI
    assistant", the opposite of the household's offline rule (`running-locally.md`, "Not the
    MCP server").
  - The library sits in the sixth top-bar menu, "Run Library". The household baseline is
    never opened automatically.
  - Shortest path to the baseline: dismiss the modal → **Run Library** → **Library** →
    **Open**, then the Run page.
- **The case pages start empty [seen].** Case Setup and Results stay empty until **Open in
  Owl** on a Run page. That step is fast: 4 s, no re-solve.
  - After it, Financial Profile says *"Case '… 2026-11-06T23-33' refers to file
    'otherFiles/library/runs/…/inputs/HFP.xlsx' that has not yet been uploaded"* above
    budget, debt and wage tables that are in fact loaded.
  - The Case Setup progress strip reads *"(12%) - Step 8 of 8"*.
- **The classic route is upstream's two-step ceremony.**
  - Create Case → *Upload Your Own Case File* takes the TOML; a second uploader, headed
    *"Upload Financial Profile (Optional)"*, then appears for the workbook [seen].
  - After a successful workbook upload the uploader vanishes and nothing confirms it [seen].
    The confirmation appears only on the Financial Profile page.
  - The workbook is labelled optional, yet this case's budget spending profile needs it.
- **The classic Results pages solve in the foreground [seen].**
  - Opening **Graphs** solved the case in the page request, with its own options: claiming
    ages "optimize" and local search.
  - For **22 minutes** the page showed only its header band, with no message, no elapsed
    time and no estimate. The only sign of work was Streamlit's corner "running" icon and a
    *Stop* link. It had not finished when the check was stopped.
  - The same solve under the library's "decision" preset (ages held) took 4 min 49 s in the
    background.
  - `owlbridge.runPlan` has no spinner or progress [code: no `st.spinner`/progress call in
    `ui/` around `plan.solve`].
- **A reload forgets everything [seen].** Reloading the tab after "Open in Owl" returned
  *"A case must first be created before running this page"*: every case and unsaved edit in
  the classic pages lives only in the browser session.
- **Upstream chrome left in [seen].** A **Deploy** button (Streamlit Community Cloud) sits
  top right, because `.streamlit/config.toml` sets no `client.toolbarMode`. **Tools →
  Connect your AI** stays in the menu in library mode (`ui/main.py` keeps it on purpose).

**Why it matters for her:** there is no page that says "this is your plan". The pages she
would reach first argue for things the household decided against, and the route that looks
like the main one (Case Setup → Results) blocks for tens of minutes and forgets on reload.

### F2. Solver and design internals on every decision screen

All quotes below are rendered text, captured from the page [seen] unless marked.

| Where | What she reads |
|---|---|
| Run page header | *"decision · local search (SS, IRMAA, ACA, LTCG, NIIT, STAR) · Owl 2026.10.30 (1623d2e)"*; the result selector shows `2026-11-06T23-33-36_decision · decision`; a "Quality: settled" line |
| Run page headline | **Score** 108,516 (no \$, no unit; the unit is in a tooltip); caption *"…reported side by side and never added (R3)."* |
| Run page, preset picker | options `quick`, `decision`, `ages`, `ages_thorough`, `custom`; tooltip: *"the self-consistent loop for every tax family (no MIP, no local search)… each pair scored by branch-and-bound at gap 1e-5 (slow: 29-51 min per variant on the chris+pat dry run)"* [code: `_PRESET_HELP`] |
| Run page, brackets | *"(review AI1)"*, *"(design 14.1, I8)"*, *"(review AG10)"* |
| Run page, claiming-age map | *"work_sweep.py output, its --json file… section 8.1's 'Ages, thorough'"* |
| Run page, tornado | *"solved under the exact LP… Medicare priced exactly (review AJ1)… tolerance (R2)"* [code] |
| Compare | *"~ unresolved / ~ the 1% loop-noise band: the loop can make it, with either sign"*; *"Noise rule (R2): a proved plan (branch-and-bound) is judged by its reported gap x objective"* |
| Compare / Library, "what changed" | `case.solver_options.maxRothConversion: 50.0 → 200`, `case.solver_options.noLateSurplus: removed (was False)`, `case.solver_options.timePreference: removed (was 0.0)` |
| Queue | *"2026-11-06 23:33:50 \| DEBUG \| localsearch:_step:263 \| Local search, iteration 0: round 0 (a): STAR free: objective 3,764,029 in 0.09s."* |
| Scenario | *"Event id"*; year fields typed as `age:Ari:86`, `after:Noa`, `event:care+2`; *"(section 6.3)"*, *"(D3)"*, *"Case.toml, HFP.xlsx … rates.csv … frozen (section 5)"* |
| Collections | *"I2"*, *"I11"*, *"`{place}`"*, *"`-` clears a text cell (a place with no local income tax: locality -)"*, *"{dimension: label} pairs"*, *"(section 9.3)"* |
| Library | *"save-as only, D3"*, *"library/trash/"*, *"owlcli run runs/<run>/inputs/Case.toml"* |
| Run Options → Advanced | radios `loop / none`, `loop / optimize / none`, `loop / value / optimize`; six *"… with MILP (expert)"* toggles; *"MILP strategy: branch-and-bound / local-search"*; *"Linear programming solver"*; *"Extra solver options (expert)"* |
| Goals | *"Profile slack (%)"*, *"Time preference (%/year)"*, a chart axis titled **ξ** |
| Errors | *"Failed to apply configuration: setACA: start_year=1999 looks like an offset … (e.g. 4025)"*; *"Solution failed: {e}"* / *"The solve raised {type}: {e}"* [code: `owlbridge.runPlan`] |

A count over one text capture of each of five pages found 19 design or review codes (R2, R3,
D3, I2, I8, I11, "review AI1", "section 6.3", …) and 24 solver terms (MILP, loop,
branch-and-bound, objective, local search, …) [seen]:

| Page | Codes | Solver terms |
|---|---:|---:|
| Run | 10 | 4 |
| Compare | 1 | 7 |
| Scenario | 5 | 0 |
| Collections | 3 | 0 |
| Run Options, advanced | 0 | 13 |

Help tooltips and collapsed expanders are not in that count.

Two of these are wrong or misleading, not merely technical:

- **Phantom changes.** The what-if changed one field, the Roth cap. Its change summary also
  lists `noLateSurplus: added (False)`, and Compare adds `timePreference: removed (was 0.0)`.
  Those are defaults the pages write in; she never touched them [seen].
- **Held ages shown as the plan's ages.** The headline shows **"Claiming ages: Ari 67y0m,
  Noa 67y0m"**, but the "decision" preset forced `withSSAges = "fixed"` while the case says
  "optimize" [ran: `record.json` options]. Nothing says the ages were held rather than chosen,
  so "the plan says claim at 67" is the natural, wrong reading.

### F3. A what-if is about 20 interactions over 6 pages, with traps that produce a wrong comparison

The Roth-cap what-if as performed [seen]:

1. **Library → Open** (baseline).
2. **Edit as new run**. It only shows a toast; it does not navigate.
3. **Case Setup → Run Options**, change *Maximum annual Roth conversion*.
4. **Run Library → Library**. *Add a run to the library* is collapsed once runs exist: expand
   it.
5. Tab *Save the current case*. The default name is the case name `ari+noa`, not "Baseline
   … variant" [code: `value=kz.currentCaseName()`].
6. **Save as a new run**, then **Open** the new run.
7. Expand *Solve this run*, pick a preset, **Solve**.
8. Wait about 5 minutes (the Queue page shows progress).
9. **Run Library → Compare**, then swap A and B.

The traps along the way:

- **The Queue page's "decision" is not the Run page's "decision" [seen + code].**
  - The Run page expands it into two solves (`preset_solves`).
  - The Queue page calls `manager.enqueue(..., preset=preset)` directly, so the exact-model
    companion is never queued.
  - Compare then says *"No exact-model companion on both sides … (solve both with the
    Decision preset)"*, which is advice she had already followed.
- **Compare reverses the comparison by default [seen].** *Result A (the reference)* defaults
  to the newest result, here the what-if. The inputs therefore read *"maxRothConversion:
  50.0 → 200"* and every difference is baseline minus what-if.
- **The verdict is not a sentence [seen].**
  - The score moved −8 (*"~ unresolved"*), lifetime taxes moved −4,263 (*"resolved"*), and the
    heading says *"no difference beyond the noise rule"*.
  - The finding for her is "raising the cap from \$50k to \$200k changes spending by \$8/yr,
    which is noise, and lowers lifetime taxes by about \$4.3k". The page never says it.
- **Scenario edits vanish on navigation [seen].** A purchase typed on the Scenario page (price
  \$850,000, year 2031) was gone after a trip to Library and back: *"Changes against this
  run: none yet"*. Widget keys are per run id and Streamlit drops them when the page is left.
- **Imported runs cannot be varied [seen + ran].**
  - Importing the household's own TOML and workbook gives a run with no events: its purchase
    lives in hand rows (`import_case` → `scenario_from_case`, no events).
  - On it, Collections → *Make variants* with purchase years 2027, 2031 answers *"No
    variants: the 'year' dimension needs a purchase event in the scenario: nothing to vary"*.
  - The Scenario page says *"Nothing yet: add an event above."* and lets her add one, with
    the two failures below.
- **A purchase event added to an imported run doubles the home [ran].** The builder output
  had two residences in Fixed Assets: `yonkers condo` 2029 (hand row) and `home` 2031
  (event). The page warned of nothing [seen: the change line read only *"purchase: home at
  850000 (today's \$) in 2031, cash (added)"*].
- **The purchase box wipes the STAR district [ran].** Locality and School district default to
  blank (free-text fields). The generated case field `basic_info.school_district` became `''`
  (was *"City of Yonkers / Yonkers"*), so the NY STAR credit would silently stop.
- **The first click on *Create collection* is swallowed [seen].** The button is disabled
  until the typed name commits on blur, so the click that blurs it hits a disabled button. One
  real mouse click left *"The library has no collections yet"*; the second click created it.

### F4. The cliffs that shape this plan are not shown where she would look

On the baseline (Yonkers, cash purchase in 2029) [ran: the solve's `plan.json` and
`Results.xlsx`]:

- **2029 lands in IRMAA tier 2, unannounced.**
  - The 2029 purchase year has MAGI **\$328,025** (today's \$), between IRMAA tier 2
    (\$289,559) and tier 3 (\$361,420).
  - **2031 Medicare premiums are \$13,158** against **\$6,284 in 2032** (nominal): about
    \$6.9k of IRMAA.
- **2027-2029 sit above the ACA cliff.**
  - 2027-2028 MAGI is about **\$133,000** against the 400%-FPL cliff at **\$84,202** (today's
    \$). The household pays the full marketplace premium: **\$21,745** and **\$22,689**
    nominal.
  - 2029 is also over (MAGI \$328,025, ACA premiums \$13,810 in the year Noa is still under
    65).
- **What "Things to look at" shows instead [seen].** It lists four NY-recapture rows with
  costs of \$3-\$26. It lists neither the IRMAA crossing nor the ACA overshoot, because by
  design (`thresholds.NEAR_BAND`) it shows only years within 5% of a line. So the two largest
  threshold effects in the plan never appear in the one place that promises "things to look
  at".
- **The Conversions and brackets chart [seen].**
  - It draws only IRMAA **tier 1**.
  - Its "top of the bracket" line zigzags, because it follows whichever bracket the year is
    in. It reads as a threshold that moves.
  - The ACA and IRMAA lines are two dotted greens of similar shade.
  - The table under it is a 28-row Markdown grid.
- **Premiums appear in no Run page chart [seen + code].** The *Taxes by kind* tab plots
  federal, gains, NIIT, payroll and "State + local" only. Medicare/IRMAA and ACA premiums are
  in `plan.json` `by_year` but nowhere on the page.
- **The NY items are folded together [ran].** STAR, the Yonkers surcharge and recapture are
  all inside "State + local", although the run's own `Results.xlsx` *Taxes* sheet has *State
  tax*, *of which recapture*, *of which local*, *STAR credit* and *Medicare+IRMAA* columns
  (2031: state \$3,290, local \$614, STAR \$990).
- **The classic Graphs → Taxes tab [seen].** Its bracket chart scales to the 35% line
  (\$770k), so the income line lies flat along the bottom. Medicare (with IRMAA) is one dotted
  line, and nothing ties the 2031 bump to 2029.

So the optimizer's reasons stay invisible. A Roth conversion that stops at a line, or a
premium that jumps two years after a sale, looks like a quirk.

### F5. Inputs are accepted silently and fail later with a wrong diagnosis

The probes on the opened case, with what came back at the widget [seen]:

| Input | At the widget | Later |
|---|---|---|
| ACA start year **1999** | accepted, no message | On Reports: *"Failed to apply configuration: setACA: start_year=1999 looks like an offset … Use a 4-digit calendar year (e.g. 4025)"*, then a second message: *"No plan satisfies all the constraints … most often a bequest or a spending floor set higher than the assets can support"* |
| Roth conversions start **2060** (the plan ends 2053) | accepted, no message | not solved separately |
| Benchmark silver premium **208.4** \$k/yr (a 10x slip) | accepted, no message | — |
| Ari's taxable account **800000** (\$k, i.e. \$800 million: a dollars-for-thousands slip) | accepted, no message | — |
| Ari's cost basis \$2,000k above an \$800k balance | **immediate plain warning** | (the model to copy) |

- **Why the second message appears [code].** `owlbridge.prepareRun` catches the configuration
  error and returns; `runPlan` solves anyway on a half-applied configuration. The second,
  misleading message comes from that solve.
- **The "4025" [code].** It is `date.today().year + start_year` in `plan.setACA`, a hint
  built for small offsets.
- **Mixed units with nothing reconciling them [seen].**
  - Balances are in \$k; Scenario prices are in \$; the down payment is a share (`0.20`)
    while the rate is in percent (`6.25`) and the selling cost in percent.
  - Budget lines are in today's \$, while the wage and debt tables are in nominal \$ and
    Fixed Assets in reference-year \$ with a nominal basis.
  - The benchmark silver premium shows **20.8** for a stored 20.84 (format `%.1f`), and its
    +/- buttons step by \$10k.
- **Sign conventions are exposed [seen].** The Financial Profile page tells her to pay
  after-tax contributions *"with a negative big-ticket items entry"*. The Budget table encodes
  "through the plan's end" as `end = 0` and "counted back" as a negative `end`.
- **Partly good [ran].** The Scenario page validates its year anchors live, with messages like
  *"buy.year = 1999 is outside the plan (2026-2053)"* and *"… cannot be resolved (a missing
  person or event, or a cycle): buy.year"*. A misspelled person (`after:Noah`) passes the
  parser and is caught only by the builder, in that second, vaguer message.

---

## 2. Page-by-page walkthrough

### Global chrome

- **Disclaimer modal in every new session [seen].** It needs an "OK" click each time.
  Remembering the acceptance in the library folder would remove it.
- **Top menus [seen].** Six menus (Case Setup, Results, Stress Tests, Tools, Help, Run
  Library), with the household's own section last.
- **Case selector [seen].**
  - It sits in every classic page header and shows names like *"Baseline: Yonkers 2029 cash
    2026-11-06T23-33🔻"*.
  - The red 🔻 marks the *current* case (`sskeys.flagCurrentCase`), but reads as a warning.
- **Deploy button** (F1) [seen].

### Run Library → Library

- **Import form [seen].**
  - Four uploaders, all marked optional except the case file.
  - The workbook the TOML names (`HFP_file_name`) is not shown.
  - Importing without it fails with *"Cannot import this case: HFP workbook
    'HFP_ari+noa.xlsx' not found for /tmp/tmpp242byv5/Case_ari+noa_condo.toml"*: a temp path,
    and the expander collapses again.
- **Run list [seen].**
  - Each entry carries the folder name (`2026-11-06_baseline-yonkers-2029-cash`), "plan year
    2026" (meaningless to her), the raw-key change summary (F2) and "2 solve(s), latest:
    done".
  - It shows no headline number, so runs cannot be compared from the list.
- **Buttons [seen].** *Zip*, *Rename*, *Delete* sit at equal weight beside *Open*.

### Run Library → Run (the key page; about 4,000 px tall at 1440 px wide)

- **Order [seen].** Run selector, result selector, method line, quality, six headline
  metrics, *Things to look at*, five chart tabs, *Conversions and brackets* (chart + 28-row
  table), regret-sweep prompt, *Results workbook* expander, four action buttons, *Solve this
  run*, *Sensitivity (tornado)*, *Claiming-age map* (an empty uploader for a work_sweep
  JSON).
  - The actions she needs (*what-if*, *compare with baseline*) are at the bottom or absent.
  - Developer tools (the regret sweep, the scores-file upload) sit mid-page.
- **Headline [seen].**
  - *Score* 108,516 is "first year's discretionary spending" only.
  - Reports, for the same result, headlines *"Yearly spending (today's \$) \$161,016"* [seen].
    Two different "spending" numbers, nothing tying them together.
  - *Savings left* shows **0** with no note that spending savings down to zero is the goal
    (the household's choice, CLAUDE.md).
- **Charts [seen + ran].**
  - The *Spending*, *Account balances*, *Taxes by kind* and *Income sources* tabs plot
    `plan.json` `by_year`, which is **nominal** [ran: 2026 spending 161,016 → 2053 260,919].
    Their axes say only *"\$ per year"*.
  - The headline above them, and the brackets chart below, are in today's \$.
  - So the *Spending* tab shows spending rising 160k → 260k while the classic Graphs page,
    in today's \$, shows it falling 164k → 122k.
- **Income sources [seen].** The 2029 purchase (about \$1.0M of withdrawals) sets the y-axis,
  which flattens every other year. Nothing marks it as the condo. The legend lists SPIAs and
  Pensions though both are zero.
- **Cash flow (one year) [seen].** See section 3.
- **Things to look at [seen].**
  - *Side* reads "over/under"; *Amount (\$)* has no thousands separators (`3982`).
  - Its note repeats the same sentence on every row.
- **Buttons [seen].**
  - *Edit as new run* gives a toast and stays put (F3).
  - *Open in Owl* works in 4 s, and its toast says "see the Results section".

### Run Library → Queue

- **Raw log as status [seen].** The "Last log line" column shows DEBUG lines with module,
  function and line number (F2). The "iter 12" counter means nothing to her.
- **No time estimate [seen].** A "decision" solve took about 5 minutes; the page shows only
  elapsed time.
- **"decision" here skips the exact companion [seen + code]** (F3). The preset help on this
  page explains only `quick` and `custom` [code].

### Run Library → Compare

- **Selectors [seen].** Labels such as *"What-if: Roth cap 50k
  (2026-11-06_what-if-roth-cap-50k) · 2026-11-06T23-49-53_decision · decision · 2026-11-06 ·
  solved"*, truncated in the box.
- **Reference and inputs [seen].** A defaults to the newest result (F3). The inputs are raw
  keys plus phantom changes (F2).
- **Outputs grid [seen].** Fine in shape. The *reading* column carries noise-rule jargon.
- ***What moved* [seen].**
  - It is in **nominal** dollars, directly under an outputs grid in today's dollars.
  - It shows a pandas index column (0, 1, 2, …) and numbers without separators (`7570`,
    `3924`).
  - Its columns adapt to what moved, which is good.

### Run Library → Scenario

- **Editing model [seen + ran].**
  - The year fields take a text syntax (`age:Ari:86`, `work:Noa`, `event:care+2`) explained in
    a 118-word caption.
  - *Event id* is user-editable. *Paid from (person)* is free text.
  - *State*, *Locality*, *School district* are free text here, although Create Case offers
    them as validated dropdowns (`_locality_choices`, `_district_choices`).
  - The blank default district wipes the case's district (F3).
- **Unit bug [seen].** *"Property tax (/yr, today's )"* renders with the dollar signs eaten
  and a code-styled fragment. The unescaped `$…$` in `Scenario.py` (`"Property tax ($/yr,
  today's $)"`) is read as math.
- **Shares and percents mixed [seen].** *Down payment (share)* 0.20, *Closing costs (share)*
  0.03, *Loan closing (share)* 0.02 sit beside *Rate (%)* 6.25 and *Selling cost (%)*.
- **Silent zeros [seen].** Property tax, HOA and insurance default to 0, so a purchase with
  no carrying costs saves without a word.
- **Generated output [seen].** *"What the events generate (marked)"* shows sheet names, row
  names and case-field paths (`basic_info.school_district`). The Fixed Assets value appears
  as 975853 (2031 nominal) for a price entered as 850,000 today's \$, unformatted and
  unexplained.
- **Drafts are not kept** across navigation (F3).

### Run Library → Collections

- **Creating a collection [seen].** The first screen asks for a free-text *Question* and
  *Comparison rule* before anything else. The swallowed first click is described in F3.
- **Make variants [seen].**
  - The form has nine sub-blocks of free text and editable tables.
  - Its conventions are typed by hand: years as `2027, 2031`; `-` to clear a cell; `{place}`
    templating; claiming ages comma separated per person.
  - On an imported run it fails as in F3.
- **The grid view** was not reached: no event-built run was solved.

### Case Setup (classic pages)

- **Create Case [seen].**
  - The two-uploader ceremony and the missing workbook confirmation (F1).
  - *Copy parameters*, *Create case* and *Delete case* sit side by side at equal size.
  - *Create case* is disabled until the names commit [code: `cantcreate = kz.isIncomplete()
    or diz1`]: probably the swallowed-click pattern of Collections, not exercised.
- **Financial Profile [seen].**
  - A false "not yet uploaded" warning after Open in Owl (F1).
  - Unit and sign rules sit in captions (F5).
  - The Budget editor shows raw columns: `active, name, type, year, end, amount, rate,
    survivor, essential, clock, start_age, end_age, index, …`, many cells `None`, and a line
    with `year = 0` for age-clock rows.
  - The rent shows as two lines, *rent* \$48,000 and *rent from 2027* \$46,693. That is how
    the generator encodes "flat in 2027, then inflation", and it looks like a data error.
- **Fixed Income [seen].**
  - The claiming-age fields are greyed when Owl chooses the ages. The reason is only in a
    tooltip (*"Set by optimizer — shown as last solved result"*) [code].
  - The collapsed *Advanced options* holds the survivor-benefit claiming age and the
    SS benefit reduction [seen].
- **Account Balances [seen].**
  - The cost-basis warning is good (F5).
  - Balances are in \$k with no plausibility check (F5).
- **Asset Allocation, Rates.** Upstream pages, not reviewed in depth. Rates labels a series
  *"Cash Assets/Inflation"* [seen].
- **Goals [seen].**
  - *"Fixed assets contribute an additional \$753k to bequest"* is clear.
  - *Profile slack (%)*, *Time preference (%/year)* and the **ξ** axis are not.
- **Run Options [seen].**
  - The main panel is reasonable (Roth cap, medical, ACA, Medicare, claiming).
  - *"ACA start year (0 = plan start, else 4-digit year)"* is a sentinel encoding in the
    label itself.
  - *Advanced options* exposes the solver (F2), and its NY STAR and itemizing choices are
    offered as `loop/optimize/none`.

### Results (classic pages)

- **All three pages solve on open** when the case changed (`caseIsRunReady` → `runPlan`)
  [code]. Results are therefore never stale, but the page blocks for the whole solve (F1).
- **Graphs [seen].**
  - The dollar-unit toggle (*nominal* / *today*) exists here, but not on the Run page.
  - *"Income, Big-Ticket Items, and Debts"* stacks **15 series** with codes (`BTI Ari`,
    `RothX Noa`, `+dist Ari`, `RMD`, `txbl acc wdrwl Noa`, `ssec Ari`). Colors repeat:
    `txbl acc wdrwl Ari` and `BTI Ari` are both orange, `tax-free wdrwl Noa` and `ssec Noa`
    both purple.
  - The 2029 purchase spikes the scale (−700k / +900k).
- **Worksheets [seen].**
  - Five tabs of collapsed expanders (*Cash Flow* alone has four).
  - The *Cash Flow* table has abbreviated headers (`all other inc`, `all net inv`, `all
    BTI's`, `FA ord inc`, `all wdrwls`, `ord taxes`, `div taxes`, …), negatives in
    parentheses and horizontal scrolling. It is nominal unless a toggle is set.
- **Reports [seen].**
  - Four metrics, then a *Synopsis* table in a scroll box about ten rows high.
  - Downloads of the TOML case file and the workbook as "input files".

---

## 3. Visual and data-storytelling gaps (NY, Yonkers, ACA)

**One-year question, as it should read.** "Where does our money come from in 2029, and what
tax do we pay?" From the solve's own `plan.json` [ran], the page should be able to say, in
one block (nominal 2029 dollars):

> 2029: spending \$147,319 plus the condo \$783,276. All of it comes from savings: \$967,652
> from the brokerage accounts and \$32,871 from the IRAs. Taxes \$53,814: capital gains
> \$31,252, New York + Yonkers \$18,520, NIIT \$4,042, federal income tax \$0. Health
> premiums \$16,115 (marketplace \$13,810, Medicare \$2,305).

Today the Run page's Sankey has all of this but shows amounts **only on hover** [seen].

- Its labels collide at the bottom (*Medicare premiums*, *NIIT*, *State and local tax*, *gold
  over benchmark, 2029*, *out of pocket medical*), and the hub is an unlabelled grey bar.
- The taxes are split over five nodes with no total.
- The classic route needs three tables: Cash Flow, Household Sources, Taxes [seen].

What to show, using data that already exists:

1. **A threshold timeline per year, MAGI against every line that bites, with the cause.**
   - For each year: MAGI as a line; IRMAA tiers 1-5 as faint horizontal bands labelled with
     the premium year they set ("2029 income → 2031 Medicare"); the 138% and 400% FPL lines
     only in marketplace years; the NY recapture start; the Enhanced STAR limit; the 0%
     gains edge.
   - Mark events on the axis: retirement, each person's Medicare start, claiming, the
     purchase.
   - **Annotate crossings, not only near-misses.** "2029: \$38k into IRMAA tier 2 → +\$6.9k
     Medicare in 2031"; "2027-28: \$49k over the marketplace cliff → full premium
     \$21.7-22.7k".
   - `thresholds.py` already computes the cost of a gap at the boundary. Extend it to report
     crossings beyond `NEAR_BAND`, at least for IRMAA and ACA.
   - Data: `plan.json` `brackets.years[*].irmaa_edges` (all five tiers with `premium_year`)
     and `aca_lines` are already written [ran].
2. **A New York decomposition, not "State + local".**
   - Stack per year: NY base tax, NY recapture, the Yonkers surcharge (or NYC), and the STAR
     credit as a negative bar.
   - Add a residence strip above it (locality and school district by year, from the moves) so
     a Queens or White Plains variant shows visibly different tax years.
   - Data: the *Taxes* sheet of the run's `Results.xlsx` already has *State tax*, *of which
     recapture*, *of which local*, *STAR credit* [ran]. Add them to `plan.json` `by_year`
     (`cli/formatters.plan_to_dict`) so the Run page draws them without reading the workbook.
3. **A marketplace card for the pre-65 years.** Who is on the marketplace each year (Noa
   through 2029), the benchmark premium, MAGI against the 138%/400% lines, the premium paid
   and, where the model prices it, what getting under the cliff would cost. Today the only
   trace is a green dotted segment on the brackets chart [seen].
4. **One dollar convention per page, switchable.**
   - Default the Run page and Compare (including *What moved*) to today's \$, with the
     *nominal / today* toggle the classic Graphs page already has.
   - Title every axis with the convention ("\$/yr, 2026 dollars").
   - Reconcile the two spending numbers in the headline: "Discretionary \$108,516 of total
     \$161,016 (2026)".
5. **Charts that respect the eye.**
   - Hide all-zero series (SPIAs, Pensions); use readable series names and at most about 7
     distinguishable series per chart.
   - Group the classic 15-series chart by account type, with persons as a toggle.
   - Mark the purchase year as an annotated bar ("condo \$783k"), or show it on a broken or
     log axis, so it does not set the scale.
   - Give IRMAA and ACA lines distinct hues and dashes; a dotted green pair is not enough.

---

## 4. Concrete remediation plan

### Quick wins: labels, defaults, layout (no model or storage change)

| # | Change | Where |
|---|---|---|
| Q1 | Drop design and review codes (R2, R3, D3, I2, I8, I11, "review AI1", "section 6.3", "design 14.1") from every rendered string; keep them in code comments | `ui/Run.py` (`_PRESET_HELP`, captions in `_things_to_look_at`, `_conversions_and_brackets`, `_claiming_age_map`, tornado block), `ui/Compare.py`, `ui/Scenario.py`, `ui/Collections.py`, `ui/Library.py` |
| Q2 | Preset names for people: *Quick look (~1 min)*, *Careful (~5 min)*, *Let Owl choose claiming ages (~30+ min)*; `custom` and `ages_thorough` behind an "Expert" toggle; `format_func` on both selectors | `ui/Run.py` and `ui/Queue.py` `st.selectbox("Preset", ...)`, `ui/Collections.py` |
| Q3 | Queue page "Solve" goes through `preset_solves` (it skips the exact companion today) | `ui/Queue.py`, the `col3.button("Solve")` handler |
| Q4 | Compare: default *A* = the pinned baseline, else B's parent; never the newest | `ui/Compare.py` `a_idx`/`b_idx` |
| Q5 | Escape the dollars: `"Property tax (\\$/yr, today's \\$)"`; grep `ui/` for unescaped `$…$` in labels | `ui/Scenario.py` (cost columns) |
| Q6 | Units on every axis and table; thousands separators (`st.column_config.NumberColumn(format=...)`); `hide_index=True` on *What moved*; today's \$ in *What moved*, or say "nominal" in its heading | `ui/Run.py` chart tabs, `_things_to_look_at`; `ui/Compare.py` *What moved* |
| Q7 | Headline renames: *Score* → "Discretionary spending, first year (\$/yr, today's)"; *Savings left 0* → add "spent down by design"; claiming ages → "held at 67 / 67 (not searched in this solve)" when the solve forced `fixed` against a case that says "optimize" | `ui/Run.py` metrics; `library/view.claiming_ages_text` (add held/chosen from `record.json` options) |
| Q8 | Queue: replace the DEBUG line with a phase ("Searching tax breakpoints, step 12"); raw log in an expander | `ui/Queue.py` `queue_fragment` |
| Q9 | Change summaries in words ("Roth conversion cap: \$200k → \$50k"); stop recording defaults the pages add (`noLateSurplus`, `timePreference`) as changes | `library/scenario.diff_summaries` (label map); `library/casefiles.scenario_from_ui` (do not write keys left at default) |
| Q10 | Import form: workbook labelled "required when the case names one", the expected file name shown, no temp path in errors, the form kept open with files kept after an error | `ui/Library.py` `_save_uploaded_run`, import expander |
| Q11 | Create Case: "✓ HFP_x.xlsx loaded: 2 people, 11 budget lines" after the upload; drop "(Optional)" when the spending profile is "budget" | `ui/Create_Case.py` HFP block |
| Q12 | After *Open in Owl*: no "file not yet uploaded" warning, progress strip marked complete | `ui/Financial_Profile.py` (HFP notice), `ui/case_progress.py`, `sskeys.openCaseFromPlan` |
| Q13 | *Edit as new run* navigates (to Run Options, or to a "what changed" panel) instead of a toast | `ui/Run.py` col3 handler (`st.switch_page`) |
| Q14 | Library mode hides Deploy (`client.toolbarMode = "minimal"` in the launcher), *Connect your AI* and the AI paragraph of Welcome | `owlplanner-library.sh` / `.cmd` options; `ui/main.py` page dict |
| Q15 | Brackets chart: all IRMAA tiers, each labelled with its premium year; bracket edges as faint horizontal bands instead of the zigzag "top of the bracket" line; distinct hue and dash for IRMAA and FPL | `ui/Run.py` `_conversions_and_brackets` |
| Q16 | *Taxes by kind*: add Medicare (IRMAA) and marketplace premiums as their own series; *Income sources*: annotate the purchase year, hide zero series | `ui/Run.py` chart tabs (`medicare_premiums`, `aca_premiums` are already in `by_year`) |
| Q17 | Sankey: amounts printed on the nodes (`node.customdata` with a value texttemplate), a labelled hub ("2029 cash flow"), a sum line for taxes, and the one-paragraph summary of section 3 above it | `ui/Run.py` `_cash_flow_sankey` |
| Q18 | Buttons gated on a text field validate on click instead (`disabled=not name.strip()` swallows the first click) | `ui/Collections.py:71`; check `ui/Create_Case.py` *Create case* |
| Q19 | Scenario purchase box: State, Locality and School district as the same dropdowns as Create Case, defaulting to the current residence; *Paid from* a person dropdown; down payment and closing costs in %; *Event id* hidden; a warning when property tax, HOA and insurance are all 0 | `ui/Scenario.py` purchase expander; reuse `ui/Create_Case.py` `_locality_choices`/`_district_choices` |
| Q20 | Goals: *Profile slack* and *Time preference* behind "Advanced" with a plain sentence; the **ξ** axis titled "spending relative to year 1"; benchmark premium shown to 2 decimals with step 1 | `ui/Goals.py`, `owlbridge` profile plot; `ui/Run_Options.py` `getNum(... "slcspAnnual")` |
| Q21 | Fix the setACA hint ("e.g. 4025") and stop the solve when the configuration did not apply | `src/owlplanner/plan.py` `setACA`; `ui/owlbridge.py` `prepareRun` returns success, `runPlan` returns on failure |

### Structural UX improvements

| # | Change | Where | Notes |
|---|---|---|---|
| S1 | **A household home page.** In library mode the default page shows the pinned baseline run: headline numbers, the year-by-year spending chart, *Things to look at*, the two or three open questions (collections) with their current answer, and buttons for *What if…* and *Compare*. Disclaimer acceptance remembered in the library folder. Library sections first in the menu; upstream sections under "Owl (advanced)" | new `ui/Home.py`; `ui/main.py` (page order, `default=True`); pins in `library.json` (`store.Library`; the design already lists pins, section 5) | Replaces upstream's Welcome only in library mode; upstream untouched |
| S2 | **A what-if panel on the Run page.** About ten household levers in plain words: last work year per person, claiming ages (or "let Owl choose"), Roth cap, spending or bequest goal, purchase place / year / cash-or-loan, care start. *Save and run* makes the child run, queues "Careful" (with its companion) and opens Compare with the baseline as A | `ui/Run.py` (new section) building on `library.builder` events and `Library.save_run`; `JobManager.enqueue` via `preset_solves` | Removes F3's six-page path; the case pages stay for the rare edit |
| S3 | **Drafts that survive navigation.** Scenario and what-if edits held in `st.session_state` under a non-widget key per run (re-seeded into widgets on return), or saved as a library draft (a run with no results folder: design section 4 already defines drafts) | `ui/Scenario.py` (`_assemble` input → `st.session_state[f"scn_draft_{run.id}"]`) | Fixes the silent loss in F3 |
| S4 | **Imported runs become event runs.** On import, recognise the purchase pattern: a Fixed Assets residence row, a big-ticket outflow that year, owner Budget lines, an optional linked Debts row, rent ending the year before. Offer "Treat this as a purchase event". Until that exists, the Scenario page refuses a purchase event when hand rows already hold a residence, and *Make variants* explains how to start from the rent-only baseline | `library/casefiles.import_case` / `scenario_from_case`; `ui/Scenario.py`; `library/variants.py` error text | Closes the double-home trap and makes the variant grid reachable from her own files |
| S5 | **Threshold timeline and NY decomposition** (section 3, items 1-3) | `owlplanner/thresholds.py` (crossings beyond `NEAR_BAND` for IRMAA and ACA, with cost); `cli/formatters.plan_to_dict` (`by_year` gains `state_recapture`, `local_tax`, `star_credit`); `ui/Run.py` (new tab or section, replacing the 28-row Markdown table with a compact, sortable table) | Old results without the new fields show the current view |
| S6 | **A year card** (section 3): pick a year, get the paragraph, the Sankey with amounts, and a two-column sources/uses table with tax and premium subtotals | `ui/Run.py` `_cash_flow_sankey` → `_year_card`; `library/view.cash_flow_year` already returns both sides | Answers journey 4 on one screen |
| S7 | **No foreground minutes-long solves.** In library mode, the classic pages' *Re-run* (and the solve-on-open) queue a background job for the case, show "solving in the background, about 5 min" with elapsed time and Cancel, and reload the result when done. Outside library mode at least a spinner with elapsed time, and a warning before a claiming-age search that it can take 30+ minutes | `ui/owlbridge.runPlan`, `ui/Graphs.py` / `Worksheets.py` / `Reports.py` (`caseIsRunReady` → enqueue); `library/jobs.JobManager` | The library already has the job machinery |
| S8 | **Verdicts as sentences.** Compare renders "Too close to call: \$8/yr (within the 1% band)" / "B is better by \$1,240/yr" / "Trade-off: B spends \$900/yr more, leaves \$40k less home" from the existing `compare.compare` result; the noise-rule explanation goes in a "How sure is this?" expander; the agreement check is shown as "a second method agrees / disagrees" | `ui/Compare.py`; wording map over `C.compare(...).lead` / `rows[*].verdict` | No change to the rule (R2/R3) itself |
| S9 | **Widget-level plausibility.** Balances over \$20M in a \$k field ("did you enter dollars?"); ACA start, Roth start and purchase years bounded by the plan years at the widget; benchmark premium outside \$5-60k/yr flagged; cost basis keeps its warning. Errors rewritten for people, the raw exception in an expander | `ui/Account_Balances.py`, `ui/Run_Options.py`, `ui/Scenario.py`; `sskeys.getNum`/`getIntNum` (`min_value`/`max_value` from the plan years) | Model: the existing cost-basis warning |
| S10 | **Library help.** A short "How to use your plan" page (open the baseline, ask a what-if, read a comparison, what "too close to call" means), linked from the home page; the Documentation page's sections on solver options marked "advanced" | new `ui/Library_Help.py` or a section in `ui/Documentation.py` | A grep finds no mention of the library in `Welcome.py` or `Documentation.py` |

### Suggested order

1. Q1-Q9 and Q14 first: wording, defaults and two real bugs (Q3, Q5). They are cheap, and
   each removes something she would trip on.
2. Then S1 + S2 + S3 together: one home, one what-if path, no lost drafts.
3. S5 + S6: the "why" views.
4. S7 when the classic pages are still in use; S4 before the variant grids are run from the
   household's own files.

Two items are defects, not taste, and could be filed or fixed separately:

- Q3: the Queue page drops the exact companion.
- F3's purchase-event traps on imported runs (S4's interim refusal): the double home and the
  wiped school district.

Q21's partial-configuration solve is a third.

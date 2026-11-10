# Is the fork, run locally, usable by a non-technical person? (2026-11-10)

Report only: no code was changed. The reader in mind is the user's spouse, a physician: at ease
with numbers, charts and uncertainty, not with a terminal, a TOML file, tax acronyms or solver
vocabulary. Earlier reviews (`ux-review.md` and its follow-ups) looked at the pages one by one;
this one asks the wider question: can she **use** the fork on the household's computer, and what
does she still need someone else for?

## Answer

Two different roles, two different answers.

- **Reading a plan and asking what-ifs in a library someone else set up and keeps alive:**
  workable today after a short walkthrough. The decision screens now say things in sentences
  (the Compare verdict, the one-year cash flow, "Things to look at"). Section B lists what she
  would still trip on; two of those are defects.
- **Operating it alone** (install, start, enter the household's data, carry the plan into a new
  year, update, recover from an error): no. Every one of those steps needs a terminal, a text
  editor on a TOML file, or Excel with Owl's column conventions. Section A.

The most urgent item is not cosmetic: **on 1 January 2027 every run in the library stops
solving**, and the route the refusal message suggests does not produce a run that solves (A1).

## How this was checked

- **The app was run and driven** in library mode (`OWL_LIBRARY_DIR`, the launcher's own options)
  at `a7b539b`, Streamlit 1.67.0, on an empty library, with a headless Chromium (Playwright) at
  **1366x768**, a common laptop size. The case was the synthetic household
  (`fork-notes/synthetic/`: `Case_ari+noa_condo.toml` with
  `HFP_ari+noa_condo_yonkers_2029_cash.xlsx`), never the real one.
- **What ran:** first launch; the import; a Quick look (2 s); a Careful solve (5 min 4 s, plus
  8 s for its companion); the home conversion; a what-if on the Scenario page (purchase 2029 →
  2031), saved and solved; Compare; a collection with three purchase-year variants queued
  together; the grid; an unaffordable what-if (a \$7M home) to see a failed solve; *Edit as new
  run* and three classic pages; a second copy of the server on the same library; the year
  rollover with the clock moved to 2027-01-02 (library code, not the pages).
- **Tags:** **[seen]** observed in the running app (page text or screenshot); **[ran]** checked
  by running library code or a repository test; **[code]** read in the source, not exercised;
  **[grep]** a mechanical search, with what was searched.
- **Not checked:** Windows (the launcher `.cmd`, a double-click start, file dialogs); the
  household's real files; printing; the Stress Tests pages; the tornado and regret sweep with
  results; a Careful solve of the variants; screen readers; whether a Scenario draft survives
  a visit to another page (PROGRESS.md records it as driven for S-2; not re-driven here).
  Screenshots are in the session scratchpad and are not committed.

---

## A. What she cannot do alone

### A1. The new year: every run refuses to solve, and the suggested way out loops back

- **[ran]** A run imported today has plan year 2026. With the clock at 2027-01-02,
  `casefiles.check_plan_year` refuses it:

  > the run's plan year is 2026 but this is 2027: its balances and year rows were entered for
  > 2026, and Owl would read them as 2027's. Make a run for 2027 with this year's balances (save
  > it as a new run from the pages).

- **[ran]** "Save it as a new run from the pages" does not work for a run opened from the
  library. *Edit as new run* marks the case as edited from that run, and a save against a base
  run keeps the base's plan year, even when the start date is changed in the pages:
  `tests/library/test_casefiles.py::test_the_base_plan_year_is_kept` passes (base 2025, start
  date moved, saved plan year still 2025). `ui/library_save.py:56` calls
  `scenario_from_ui(dic, plan, base=base, ...)` with no `plan_year=` **[code]**. So in 2027 the
  new run is a 2026 run again and is refused again.
- **[ran]** Importing the same files again in 2027 also gives plan year 2026, because the case
  file says `start_date = "2026-01-01"` (the template does too, `Case_us.template.toml:24`).
- **What does work**, as far as the code says **[code, not driven]**: edit `start_date` in the
  TOML by hand and import again, or upload the case through Create Case (no base run, so the
  save takes the current year). Either way the events (purchase, rent) are lost and the home has
  to be converted again, and the new balances are typed on Account Balances in \$k.
- The yearly check-in the design plans for this (I4) is not built **[grep: "check-in" appears in
  `src/owlplanner/library` only in the docstring of `check_plan_year`]**.

That is seven weeks away. Until something replaces it, the turn of the year is a job for the
person who knows the files, and the message should say so instead of pointing at the pages.

### A2. Starting it, stopping it, keeping it

- **Start [code]:** `owlplanner-library.cmd` / `.sh` in a checkout: `git`, `uv`, a terminal and a
  first run that downloads the packages (about 280 MB of wheels by the lock file's sizes for
  Linux; over 20 minutes on this container's connection). There is no desktop shortcut and no
  installer.
- **No written instructions for library mode [grep]:** `owlplanner-library` appears in
  `CLAUDE.md`, `PROGRESS.md` and three UX notes, and nowhere else; `running-locally.md` still
  describes only `owlplanner.sh` and the classic pages, and still says "The Budget lines have no
  editor" and that `withItemized` / `withSTAR` have no control (lines 99-101); the Financial
  Profile page has a Budget table now **[seen]**, and PROGRESS.md records both as built in
  run-library step 5.
- **The terminal window [ran]:** it has to stay open, and it scrolls Owl's DEBUG lines (51 of
  the first 57 lines of the server's output). Closing it stops the app; solves already running
  go on (by design) with nothing on screen to say so. I did not find a way to quit from the
  pages (searched `ui/main.py`, `Run.py`, `Library.py`, `libraryjobs.py` for
  shutdown/quit/stop the app).
- **Starting it twice [ran]:** a second launch starts a second server on port 8502 over the
  same library, with no warning. Whether two servers' job managers interfere was not tested
  (dispatch is built as a compare-and-swap for this case).
- **Backup and trash [seen]:** "backing up is copying the library folder"; deleted runs go to a
  `trash/` folder "emptied by hand". She would need to know where the library folder is.
- **Updates [code]:** `git pull` and `uv sync`.

### A3. Getting the household's data in

- **[seen]** An empty library says "import a case on the Library page"; the import takes a TOML
  case file and an `.xlsx` workbook. The form itself is clear (it names the workbook the case
  needs, and refuses without it in words).
- **[code]** Producing those two files is developer work: a template TOML with `TODO`s, a
  generated workbook with Owl's conventions (wages as they enter AGI, signed big-ticket items,
  balances in \$k as of the start date), or an edited copy of `make_cases.py`
  (`running-locally.md` section 2).
- The pages can build a case from nothing (Create Case and the Case Setup pages), but that is
  upstream's eight-page setup in upstream's vocabulary.

This is a fair division of labour if it is said out loud: he prepares and maintains, she
explores. The app does not say it anywhere.

### A4. No help for her inside the app

- **[grep]** A case-insensitive search of `Welcome.py`, `Documentation.py` and `About_Owl.py`
  for "run library" and "library mode" gives three hits, all code comments in `Welcome.py`
  (lines 28, 46, 71): nothing addressed to the reader. No file in `ui/*.py` contains
  "glossary".
- **[seen]** One Run page for the Careful result is about 660 words and uses IRMAA 9 times, MAGI
  8, FPL 3, plus STAR, Roth conversion, "400% FPL", "bracket top", "tier", "essential /
  discretionary", "today's dollars", "noise", "tolerance". Each is explained, where it is
  explained, in a grey caption next to the chart that uses it. Nothing explains them once, in
  one place, in order.
- **[seen]** The menu offers 28 pages in six groups. She needs five or six of them (Run,
  Scenario, Compare, Collections, Queue, sometimes Library). Stress Tests, Tools → *Connect your
  AI* and Help → *Welcome* (upstream's public-site text) are one click away and are not for her.

---

## B. What she would trip on in daily use

Ordered by how likely it is to stop or mislead her.

### B1. The Queue page breaks after variants are queued together (defect) [seen]

*Make variants* with "Queue them when created" queued three Quick looks in one second. Two got
the same results-folder name (`2026-11-09T23-48-55_quick`, each inside its own run), and the
Queue page keys its buttons by that name:

> streamlit.errors.StreamlitDuplicateElementKey: There are multiple elements with the same
> key='open_2026-11-09T23-48-55_quick' ... File "ui/Queue.py", line 128, in queue_fragment

The list stops at the traceback and stays broken for as long as those rows are listed. The same
keys are used for *Kill*, *Cancel* and *Run again* (`ui/Queue.py:108-128`) **[code]**, so the
page would break while the variants are still running too. The fix is to key by the run as well
as the job (`job.doc["run_id"]` is on the record).

Streamlit's error box also offers **Ask Google** and **Ask ChatGPT** links **[seen]**: one click
pastes a traceback with local paths into a search. `client.showErrorDetails` is not set in the
launcher or `.streamlit/config.toml` **[grep]**.

### B2. After *Solve*, the Run page does not change [seen]

The Quick look finished in 2 s (status file: queued 23:23:26, done 23:23:28). Fifteen seconds
later the page still read "This run has no results yet: solve it below." A toast is the only
sign that anything was queued. Only the Queue page refreshes itself **[grep: `st.fragment` /
`run_every` occur in `ui/Queue.py` only, among the six library pages, `background_solve.py` and
`libraryjobs.py`]**. For a 5-minute Careful solve she has to know to go to the Queue, or to
reload.

### B3. A what-if is still 13 actions over 4 pages, and ends on the wrong comparison [seen]

Buying in 2031 instead of 2029, as driven:

1. Scenario page; 2. check the run in *Run to edit* (from the menu, in a new session, it opened
on the newest run in the library, while the Run page opens on the baseline); 3. change the year; 4. type a
name; 5. *Save as a new run*; 6. Library; 7. *Open* the new run; 8. expand *Solve this run*;
9. *Solve*; 10. wait and reload; 11. Compare; 12. pick A; 13. pick B.

- Saving does not offer to solve, and the Run page afterwards opens on the baseline, not on the
  run just saved.
- Compare's default pair was the converted run against the baseline (the newest solve and its
  parent), not the what-if: "Too close to call: \$920/yr" for two runs with identical inputs
  solved by different methods. The pair has to be picked from labels about 190 characters long,
  cut off in the box: `Our plan: Yonkers condo 2029, cash, home as events
  (2026-11-09_our-plan-yonkers-condo-2029-cash-home-as-events) · 2026-11-09T23-40-30_quick ·
  Quick look (about a second) · 2026-11-09 · solved`.
- With the right pair the page is good: "*Our plan ...* comes out ahead: \$1,630/yr more
  discretionary spending and \$7,477 more home at the end." It called a 1.5% difference between
  two Quick looks "resolved" without suggesting a Careful solve of both; the "second method"
  check needs one (10 minutes of solving for the pair).

### B4. The home conversion leaves two baselines [seen]

*Turn the home rows into a purchase event* saved a child run "..., home as events" and stayed on
the original. Afterwards:

- the pin, the landing page and the solved results are on the original; the run that can be
  varied is the child, with no results;
- the button is still offered on the original;
- *Make variants* defaults its *From run* to the pinned original and answers "No variants: the
  'year' dimension needs a purchase event ..." (the message does say what to do);
- every variant inherits the child's name: "Our plan: Yonkers condo 2029, cash, home as events
  2027" is the 2027 purchase.

### B5. The retirement year cannot be varied from the household's own files [ran + code]

The converted run has `purchase` and `rent` events only **[ran]**. The *Last work year*
dimension needs exactly one full-time work event per person (`variants.py:308-315`) **[code]**,
and on the Scenario page the work table is empty **[seen]**: nine columns (wages in AGI, 401k
deferral, employer contribution, IRA contribution, months worked ...) to retype from the
workbook. "When to retire" is the first of the household's four questions, and it is the one the
what-if tools cannot reach on an imported plan.

### B6. The collection grid shows nothing until three more steps are done [seen]

After the variants were solved: "Choose a reference below: the grid's cells are differences from
it." The run the variants were made from is not a member, so it has to be added, given its value
by hand ("the same {dimension: label} pairs ... for example `year: 2027; place: yonkers`") and
set as the reference. Then the grid is compact and readable; its reference cell shows only the
home (753,309) where the other cells show the spending difference first.

Also on this page: the *Make variants* form folds shut after a refused attempt and after
choosing another *From run* (typed values kept); the *Place(s)* table is ten free-text columns
(state, locality, school district typed by hand; only *cash or loan* and the downturn sequence
are dropdowns, `ui/Collections.py:188, 233`) **[code]**.

### B7. A failed solve reads as a solved one with missing numbers [seen]

The \$7M home. The Queue says it well: "Failed: No plan satisfies all the constraints. An input
has to give ...". The Run page for the same solve says:

- "**Solved** 2026-11-09 23:56 · Quick look" in the header;
- "This solve did not finish: infeasible";
- headline labels "Final bequest (today's \$)" and "The solve maximizes the final bequest" for a
  case that maximizes spending;
- "The Results workbook is gone from this folder; solve again to get it" (there never was one).

### B8. The landing page's first screen holds no number [seen]

At 1366x768 the first screen of the app is: the title "Run", the run selector, "The baseline",
the run's name, its folder name and plan year, the conversion button, the result selector
(`2026-11-09T23-23-26_quick · ...`), "Solved ...", *Technical solve details*, "Quality:
settled". The first number (first year's spending) starts at the bottom edge. The page is about
3,900 px tall, and its lower half is the brackets table, the regret-sweep offer, an uploader for
a "claiming-age scores file" and the sensitivity block: specialist tools at the same weight as
the plan.

### B9. Smaller things [seen unless marked]

- Change summaries still show raw paths for the conversion: `hfp.Ari.rows[8][15]: -783276 → 0;
  hfp.Budget.rows: 11 → 6 rows`.
- On a run with no result the Run page has no *Edit the scenario*, *Edit as new run* or
  *Download everything* (they are inside the result block, `ui/Run.py:483-721`).
- At 1366 px the *Note* column of "Things to look at" and *Next limit* of the brackets table are
  cut off.
- Scenario page: the work table has no heading; empty cells read "None"; the purchase box shows
  a *Year* dropdown above a *Year* field; loan term, rate and down payment stay editable with
  *cash*; the page still explains the typed anchor syntax (`age:Ari:86`, `event:care+2`) above
  pickers that make it unnecessary; "What the events generate (marked)" lists sheet names and
  event ids (`buy`).
- The headline's large numbers carry no "\$"; the unit is in the tooltip and the line below.
- Graphs after *Edit as new run*, with nothing edited: "The case changed since its last solve".
- Queue: "beat 5s ago", "Jobs are detached processes".

---

## C. What already works for her [seen]

Stated as observations, to mark what should not be disturbed.

- The Compare verdict is a sentence with the runs' names and both numbers; "Too close to call"
  is used where it applies; different presets on the two sides are flagged.
- The one-year cash flow reads as a paragraph: "2029: spending \$147,309 plus big-ticket
  purchases \$783,276. All of it comes from savings: ... Taxes \$53,777: capital gains tax
  \$31,230, state and local tax \$18,511 ...".
- "Things to look at" lists the three crossings that cost money on this plan (the marketplace
  cliff 2027-2029, IRMAA tier 2 for 2029 income paid in 2031, the Enhanced STAR limit) with
  their cost and the year paid.
- Solves run in the background at the stated times (Careful: 5 min 4 s); the Queue names the
  phase in words and offers *Open result*.
- The import form names the workbook the case requires; refusals on Collections say what to do
  next; the reminder is asked once per library.

---

## D. What would change the answer

In the order I would do them. Items 1-3 are what stands between "usable with help nearby" and
"usable when he is not there".

| # | Change | Why | Where |
|---|---|---|---|
| 1 | Key the Queue's buttons by run and job | B1: the page breaks on the collection workflow | `ui/Queue.py:108-128` |
| 2 | A "Start *year* from this run" action: a child run with this year as its plan year, the events kept, landing on Account Balances for the new balances. Until then, correct the refusal message (it points at a route that keeps the old year) | A1: seven weeks away | `library/casefiles.py` (`check_plan_year` text; `scenario_from_ui(plan_year=)` exists), `ui/library_save.py`, `ui/Run.py` |
| 3 | The Run page shows "solving, about 5 minutes" while a solve of this run is queued or running, and redraws when it ends (the Queue page's fragment) | B2 | `ui/Run.py` |
| 4 | *Save and solve* on the Scenario page: queue Careful, open the new run's page, with a *Compare with its parent* button that opens Compare on that pair | B3: 13 actions to about 5, and the right pair | `ui/Scenario.py`, `ui/Compare.py` (a pair passed in the session) |
| 5 | After the home conversion: offer to make the converted run the baseline and solve it; stop offering the button on the original; name variants by their values ("Buy in 2027") | B4 | `ui/housing_convert.py`, `ui/Collections.py` |
| 6 | *Make variants* adds its parent as a member with its own value and as the reference | B6 | `ui/Collections.py`, `library/variants.py` |
| 7 | Work events from an imported plan's wage rows (the conversion's pattern, applied to wages) | B5: the retirement question | `library/casefiles.py` |
| 8 | One page for her inside the app: how to read the Run page, how to ask a what-if, what "too close to call" means, and a glossary (IRMAA, MAGI, FPL, STAR, Roth conversion, essential / discretionary, today's dollars) | A4 | new help page in the Run Library group |
| 9 | A plain view of the Run page: numbers in the first screen (selectors and folder names folded), the brackets table, regret sweep, scores uploader and sensitivity under "More analysis" | B8 | `ui/Run.py` |
| 10 | The failed-solve page: "Did not finish", the Queue's sentence, no objective guess, no "workbook is gone" | B7 | `ui/Run.py`, `library/view.py` |
| 11 | Launcher and paper: a library-mode section in `running-locally.md` (start, stop, where the library folder is, backup, update, the new year); a desktop shortcut; DEBUG lines off in the terminal; a second launch opens the running app instead of a second server; `client.showErrorDetails` so an error box carries no web links | A2, B1 | `owlplanner-library.cmd` / `.sh`, `fork-notes/running-locally.md` |
| 12 | Library mode's menu: the six library pages, and one "Inputs and advanced" group for everything else | A4 | `ui/main.py` |

Items 1, 3 and 10 are small. Item 2 is the only one with a date on it.

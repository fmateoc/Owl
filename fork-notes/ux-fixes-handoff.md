# Handoff: the UX review's four bugs, then Q1-Q9 (2026-11-07)

For the **next session**. The user's call on `fork-notes/ux-review.md`: **fix the four bugs
first, then the quick wins Q1-Q9**, in a new session. This note is the work order. The review
holds the evidence, with each finding tagged [seen] / [ran] / [code]. Nothing of it is fixed
yet.

Two of the four bugs are quick wins in the report too: B1 = Q3 and B4 = Q5. Do them once, as
bugs, and skip them in the Q pass.

## Where things stand

- **Branches.** The review sits on `claude/optimistic-mccarthy-pidkig`, `f154e58` plus this
  note. `main` is at `1623d2e` and does not have the review. Start from this branch. Do **not**
  fast-forward `main`: the user decides.
- **Upstream.** `dev` `73dc881` was fetched 2026-11-07. It is the same as the last merge
  (CLAUDE.md, "Upstream").
- **Full suite.** Last green run: **4422 passed, 1 skipped** (2026-11-06, Linux, `-n 4`).

## Setup (CLAUDE.md "Setup", plus what the review needed to drive the UI)

- `uv sync --python 3.11`, then the tests, lint and HiGHS-only notes as in CLAUDE.md.
- Synthetic household: `.venv/bin/python fork-notes/synthetic/make_cases.py`. It writes
  `fork-notes/synthetic/cases/` (gitignored).
- App in library mode. `otherFiles/` is gitignored; create it first.
  ```bash
  mkdir -p otherFiles && OWL_LIBRARY_DIR=otherFiles/library .venv/bin/streamlit run ./ui/main.py --server.address=localhost --server.headless=true --browser.gatherUsageStats=false
  ```
- **Playwright is Node's, not Python's:** `require('playwright')` under `/opt/node22/bin/node`.
  What the review learned about driving Streamlit 1.66:
  - The menu is the top bar. Click the section (`[data-testid="stTopNavSection"]`), then the
    page link. A `page.goto` to a page URL starts a **new session**, which loses the session
    state.
  - A selectbox is a react-aria combobox. Inside its `[data-testid="stSelectbox"]`, click the
    button named "Open", then `getByRole('option')`.
  - Number and text inputs: locate `[data-testid="stNumberInput"]` /
    `[data-testid="stTextInput"]` filtered by label text, then `input`; `getByLabel` missed
    labels that contain `\$`. Values commit on Enter or blur.
  - Expanders: `[data-testid="stExpander"] summary`.
  - The disclaimer modal needs its "OK" in every new session.
  - The main area scrolls inside its own container, so `fullPage` screenshots cut off. Set the
    viewport to the content height instead.
  - Wait for `[data-testid="stStatusWidget"]` to be gone before reading the page.
- **The review's test case:** import `Case_ari+noa_condo.toml` with
  `HFP_ari+noa_condo_yonkers_2029_cash.xlsx` on the Library page.
- **Measured solve times** on that case (this container): `quick` 0.8 s; `decision` 304 s
  (baseline) and 323 s (a what-if); `decision_exact` 9 s. The `ages` and `ages_thorough`
  presets were **not** measured; the design notes 29-51 min per variant for `ages_thorough` on
  chris+pat. Do not invent times for them.
- **Never solve the case on the classic Graphs page.** It solves in the page request with the
  case's own options (claiming ages "optimize" + local search) and had not finished after
  22 min. To get the classic Results pages, use "Open in Owl" from a solved run.
- Real household data never: synthetic cases only (CLAUDE.md, "Household data stays
  offline").

## Part 1: the four bugs (in this order)

For each bug, write a test that fails before the fix, and record in PROGRESS.md that it did.

### B1 (= Q3): the Queue page's "decision" queues no exact companion

- **Symptom [seen + code].** `ui/Queue.py` (the `col3.button("Solve")` handler) calls
  `manager.enqueue(labels[choice], preset=preset)` directly.
  - The Run page (`ui/Run.py`, "Solve this run") and Collections
    (`ui/Collections.py` 255, 481) loop over `preset_solves(preset)`.
  - From the Queue page, "decision" therefore queues local search only. Compare then shows
    *"No exact-model companion on both sides … (solve both with the Decision preset)"*.
- **Fix.** Go through `preset_solves`. Handle `JobsError` as Run.py does (the Queue page
  catches only `ScenarioError`). Show the error through `libraryjobs.flash` across the rerun.
  The Queue page's preset help explains only `quick` and `custom`; Q2 rewrites it anyway.
- **Test.** Selecting "decision" on the Queue page queues two jobs, `decision` and
  `decision_exact`. Extend `tests/ui/test_queue_page.py` (AppTest).

### B2: a purchase event on an imported run (two traps)

**Trap (a): double residence [ran].**

- Import a case whose workbook already holds the purchase (Fixed Assets `yonkers condo`,
  residence, 2029; the condo case above).
- On the Scenario page, tick "Buy a home" and save. `builder.build` gives **two** active
  residences, `yonkers condo` 2029 and `home` 2031.
- No warning appears. The page's change line reads only *"purchase: home at 850000 (today's
  \$) in 2031, cash (added)"*.

**Trap (b): the school district wiped [ran].**

- The purchase box's Locality and School district are free text and default to blank
  (`builder.PLACE_DEFAULTS`).
- For a purchase without "Move there", `builder.build` sets
  `basic_info.school_district = place["school_district"]` (builder.py about line 984). The
  case's *"City of Yonkers / Yonkers"* became `''`, so the NY STAR credit stops silently.

**Fix direction.** Settle the semantics, then write them in the design (6.2) and in
CHANGELOG-fork.md.

- **The page** pre-fills the purchase's state, locality and school district from the case's
  current residence. Use the same dropdowns as Create Case (`_locality_choices` /
  `_district_choices` in `ui/Create_Case.py`). That also covers part of Q19.
- **The builder** must not blank the case's district through an empty field.
  - Either an empty district keeps the case's, or the event must state it.
  - An explicit "no district" needs a spelling. The variants tables already use `-` to clear
    a text cell (`variants.py`, `ui/variant_tables.py`): reuse that convention, don't invent
    another.
- **Double residence.** Refuse with a plain `ScenarioError` (the Scenario page shows it as
  "Not buildable yet: …") when a purchase event meets an active hand Fixed Assets row of type
  residence. Allow it only if that row is sold before the event's year, if that case is worth
  keeping; check what the builder already knows about hand rows. If you choose a warning
  instead of a refusal, say why in PROGRESS.md.
- **Variants.** On an imported run, *Make variants* fails with *"the 'year' dimension needs
  a purchase event in the scenario: nothing to vary"*. Make that message say how to get a
  purchase event: start from the rent-only baseline and add the purchase on the Scenario
  page. The full import-to-events conversion is S4 and not in scope.
- **Builder version.** If the built output of any existing scenario changes, bump
  `BUILDER_VERSION` (R9).
- **Checks that must stay green:** `fork-notes/synthetic/check_library_builder.py`
  **46/46** (its scenarios carry explicit places; check that none relied on an empty
  district), `check_library_roundtrip.py` **39/39**.

### B3: the classic pages solve after the configuration failed to apply (upstream code)

- **Symptom [seen].**
  - Set *ACA start year* to 1999 on Run Options, then open Reports.
  - First message: *"Failed to apply configuration: setACA: start_year=1999 looks like an
    offset rather than a calendar year. Use a 4-digit calendar year (e.g. 4025)."*
  - Second message, from a solve on a half-applied configuration: *"No plan satisfies all the
    constraints. An input has to give: most often a bequest or a spending floor…"*.
- **Causes (both upstream code, checked on `dev` `73dc881`).**
  - `ui/owlbridge.prepareRun` catches the exception, shows it and returns `None`. Every
    caller solves anyway: `runPlan` (owlbridge.py about line 214), `runHistorical` (267),
    `runMC` (311), and the calls at 611, 860 and 2819.
  - `plan.setACA` (src/owlplanner/plan.py, the "looks like an offset" `ValueError`) builds
    its hint as `date.today().year + sy`, meant for small offsets. 1999 gives "e.g. 4025".
- **Fix (minimal, the shape an upstream patch would take).**
  - `prepareRun` returns whether it applied.
  - Each caller stops when it did not. `runPlan` records a status that `showCaseStatus`
    explains, so only one message shows: the real one, without the `setACA:` prefix where
    the page can say it better.
  - In `setACA`, give the year hint only for an offset (say `sy < 100`); otherwise say "a
    4-digit calendar year such as 2027".
  - Fork-only behaviour stays out of this patch.
- **Upstream.** Both are upstream bugs.
  - Re-check them on the current upstream `dev`.
  - Draft an issue for the user to file: `fork-notes/issue-prepare-run-failure.md`, both
    points, a stock repro (setACA in two lines of Python; `prepareRun` through Streamlit's
    `AppTest`, or a written click path if AppTest cannot set it up), and a minimal patch
    `fork-notes/issue-prepare-run-failure.patch` verified against stock `dev`.
  - Fix the fork with the same patch (CLAUDE.md, "Upstream").
  - The session does not file anything.

### B4 (= Q5): "Property tax (\$/yr, today's \$)" renders as math

- **Symptom [seen].** The Scenario page shows *"Property tax (/yr, today's )"* with a
  code-styled fragment. The unescaped `$…$` in `ui/Scenario.py` (`"Property tax ($/yr,
  today's $)"`) is read as math.
- **Fix.** Escape it (`\\$`, upstream's convention since 2026-10-11). Then grep `ui/` (and the
  library's user-facing strings) for other label, caption and help strings with two unescaped
  dollar signs and fix those too.
- **Test.** Assert the rendered label text, or add a source check that no `st.*` label in
  `ui/Scenario.py` holds two unescaped `$`. Pick whichever is less brittle and say which.

## Part 2: quick wins Q1-Q9 (Q3 and Q5 are done above)

Each item below is from the report's table "Quick wins". Keep them to wording, display and
defaults: none may change a solve, the inputs hash of an existing run, or a stored file's
format unless the note says so.

- **Q1: drop design and review codes from rendered strings.**
  - Targets: R2, R3, D3, I2, I8, I11, "review AI1", "section 6.3", "design 14.1".
  - Files: `ui/Run.py` (`_PRESET_HELP`, the captions in `_things_to_look_at`,
    `_conversions_and_brackets`, `_claiming_age_map`, the tornado block), `ui/Compare.py`,
    `ui/Scenario.py`, `ui/Collections.py`, `ui/Library.py`.
  - Keep each sentence's meaning in plain words: "(R3)" → "the two are never added together".
    The codes stay in code comments.
  - Also on screen: `work_sweep.py`, `--json`, `plan.json`, `scores.json`, `regret.json`,
    `Case.toml`, `HFP.xlsx`, `rates.csv`, `library/trash/`,
    `owlcli run runs/<run>/inputs/Case.toml`. Where a file name is the point (the scores-file
    uploader), say what the file is in words, and keep the name in a help tooltip.
- **Q2: preset names for people.**
  - Use `format_func` only; the stored preset ids (`PRESETS`, `record.json`, folder names) do
    not change.
  - Suggested: "Quick look (about a second)" for `quick`; "Careful (about 5 minutes)" for
    `decision`; "Let Owl choose the claiming ages (slow)" for `ages`. Put `ages_thorough` and
    `custom` behind an "Expert" toggle.
  - Times only as measured (above).
  - Apply on Run, Queue and Collections ("Queue them when created", "Run the collection
    again"). Rewrite the preset help texts in plain words.
- **Q4: Compare's default pair** (`ui/Compare.py` `a_idx` / `b_idx`).
  - B = the newest main result. A = the newest main result of B's parent run, else a pinned
    baseline (`library.json` has a `pins` list in `store.py`; check whether anything sets it),
    else the current fallback.
  - Never the newest result as A.
  - Test with `fork-notes/synthetic/check_library_compare.py` (6/6) plus a UI test of the
    default.
- **Q6: units, separators, index.**
  - The Run page's four `by_year` charts are **nominal** (`plan.json` `by_year`, checked:
    2026 spending 161,016 → 2053 260,919). `plan.json` carries no deflator series, so title
    their axes "nominal \$ per year".
  - A today's-\$ toggle needs a deflator in `plan.json` (`cli/formatters.plan_to_dict`): that
    is structural (S-level), so leave it unless it is trivial and covered by tests.
  - *Things to look at*: thousands separators (`st.column_config.NumberColumn(format=...)`).
  - Compare's *What moved*: separators, `hide_index=True`, and "nominal \$" in the heading.
- **Q7: headline wording** (`ui/Run.py` metrics, `library/view.py`).
  - *Score* → "Discretionary spending, first year (\$/yr, today's)", or `view.score_label`'s
    own words in the metric's label. Under `maxBequest` the first number is the savings left
    (`view.first_number`, review AJ3): keep that case right.
  - *Savings left* 0: a note "spent down by design" only when the case's bequest target is 0.
  - Claiming ages: say "held at …" when the solve forced `withSSAges = "fixed"`
    (`record.json` `method.options`) while the run's case asks for "optimize". Say "chosen by
    Owl" when an Ages preset searched them (`record.json` `age_search`).
  - Do this in `view.claiming_ages_text` or beside it, so Compare and the grid can use it.
- **Q8: the Queue's "Last log line"** (`ui/Queue.py` `queue_fragment`).
  - Today it shows `… | DEBUG | localsearch:_step:263 | …`. Show a phase in words instead
    ("Solving, step 12"; "Waiting for another solve to finish"), and keep the raw line in a
    tooltip or expander.
  - Failed and interrupted jobs keep their error text visible.
- **Q9: change summaries in words, and no phantom changes.**
  - `library/scenario.diff_summaries` prints raw paths
    (`case.solver_options.maxRothConversion: 200 → 50.0`). Add a label map for the paths a
    person meets, and keep the raw path as the fallback.
  - **Phantom changes.** Saving from the case pages adds `noLateSurplus: False` (change
    summary) and Compare shows `timePreference: removed (was 0.0)`; the user changed only
    the Roth cap.
    - The root is `casefiles.scenario_from_ui` writing defaults that the base run did not
      have. Changing what it stores moves inputs hashes and "identical to" detection
      (T1/V3).
    - The safer fix is in the diff: an addition equal to the schema default, or a removal of
      a default value, is not a change. If you also stop `scenario_from_ui` from writing
      such keys, prove that existing runs keep their hashes:
      `fork-notes/synthetic/check_library_roundtrip.py` 39/39 and the
      `tests/library/test_casefiles.py` / `test_scenario.py` pins.

## Done means

- The tests for B1-B4 fail before their fixes (record it). Targeted tests:
  `tests/library tests/ui` + anything touched under `tests/`.
- **Full suite green** (CLAUDE.md, "Tests"). Record the count and time.
- Lint: flake8 and ruff, with only upstream's listed items left.
- `check_library_builder.py` 46/46, `check_library_roundtrip.py` 39/39,
  `check_library_compare.py` 6/6, `check_library_jobs.py` 5/5.
- **Re-drive the review's journeys with Playwright** on the synthetic case and quote what the
  pages now say for every [seen] item you touched: the Queue page queues two jobs; Compare
  defaults A to the parent; the purchase box shows the case's district and refuses the second
  home; Reports shows one message for ACA year 1999; the Property tax label reads right.
- Docs:
  - PROGRESS.md: a section per part;
  - `fork-notes/CHANGELOG-fork.md`: an entry;
  - CLAUDE.md's "State": a bullet for the branch;
  - the review: mark Q-items and bugs done, or say why not;
  - `run-library-design.md` 6.2 for B2's semantics.
- Commit with CONTRIBUTING tags and push the session's branch.
- Then **stop and report.** The user decides on an independent review and on the
  fast-forward of `main`.
- The issue draft for B3 is left for the user to file.

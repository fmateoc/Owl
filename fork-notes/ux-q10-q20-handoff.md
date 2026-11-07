# Handoff: the UX review's quick wins Q10-Q20 (2026-11-07)

For the **next session**. The work order for the rest of the quick wins in
`fork-notes/ux-review.md` ("Quick wins", section 4). The review holds the evidence, with each
finding tagged [seen] / [ran] / [code]; its page-by-page notes (section 2) and its
storytelling section (section 3) give the detail behind each row. Q1-Q9 and the four bugs were
done on `claude/ux-fixes` (`fork-notes/ux-fixes-handoff.md`, PROGRESS.md "UX review: the four
bugs", "UX review: quick wins Q1-Q9", "UX fixes: the independent review's AK1-AK7 folded").
Q21 was bug B3 and is done.

## Where things stand

- **Branches.** `main` = `claude/ux-fixes` (fast-forwarded 2026-11-07, `fb2d8a1`, plus this
  note). Start a new session branch from `origin/main`. Do **not** fast-forward `main`: the
  user decides.
- **Upstream.** `dev` `73dc8815`, the same as the last merge (checked 2026-11-07).
- **Full suite.** Last green run: **4472 passed, 1 skipped** (2026-11-07, Linux, `-n 4`,
  10:32).
- **Done already, do not redo:**
  - Q19's dropdowns: the purchase box's State, Locality and School district already start
    from the case's residence, with the Create Case choices (B2, AK2, AK6). The rest of Q19
    is open (below).
  - Q2's preset names (`ui/librarypresets.py`) and Q1's plain wording are the model for new
    strings. Use `\$` for dollars; `tests/ui/test_ui_dollar_math.py` checks the pages.

## Decisions for the user before or during the work

Ask these at the start (one question each, with a recommendation); do not settle them alone.

1. **Upstream's own pages.** Q11, Q12 (in part), Q18 (Create Case), Q20 and Q14's Welcome
   paragraph change upstream files: `ui/Create_Case.py`, `ui/Financial_Profile.py`,
   `ui/case_progress.py`, `ui/Goals.py`, `ui/Run_Options.py`, `ui/Welcome.py`, and possibly
   `src/owlplanner/plotting/plotly_backend.py` (the **ξ** axis title, line 140).
   - Every fork change there is a merge cost at each sync (CLAUDE.md, "Syncing").
   - Options: (a) change them in the fork only under library mode (`OWL_LIBRARY_DIR`), so
     upstream's behaviour is untouched outside it; (b) change them for everyone and draft an
     upstream issue with a patch on stock `dev`, as with B3; (c) leave them.
   - Recommendation: (b) for plain defects that hold for every user (Q12's false "not yet
     uploaded" warning if it reproduces outside Open in Owl, Q18's swallowed click on *Create
     case* if it reproduces, Q11's missing confirmation); (a) for wording aimed at this
     household (Q20's hiding of options, Q14's Welcome paragraph).
2. **Q14, *Connect your AI* in library mode.** `ui/main.py` keeps it on purpose (comment at
   line 92, step-3 review 3, W9: the chat stays off, the MCP instructions page stays). The UX
   review asks to hide it. This reverses a recorded decision: the user's call.
3. **Q13's destination.** *Edit as new run* can go to Run Options (where the review's what-if
   was made) or to Create Case. Recommendation: Run Options, with a flash message saying the
   case is the run's and that saving happens on the Library page.

## The items

Keep them to wording, display, defaults and navigation. None may change a solve, a stored
file's format, or an existing run's inputs hash, unless the note says so. Where an item needs
data the result files do not carry, say so and stop at what the files have (the structural
items S1-S10 are out of scope).

### Q10: the import form (`ui/Library.py`)

- [seen] Four uploaders, all marked optional except the case file. The workbook the TOML names
  (`HFP_file_name`) is not shown. Importing without it fails with *"Cannot import this case:
  HFP workbook 'HFP_ari+noa.xlsx' not found for /tmp/tmpp242byv5/Case_ari+noa_condo.toml"*:
  a temp path. The expander (`ui/Library.py` 154, `expanded=not lib.runs()`) collapses again,
  and the files are gone.
- Do:
  - after the case file is chosen, read its `HFP_file_name` (and `budget_file`,
    `rates_file`) and label the matching uploaders "required: <name>";
  - no temp path in the error: name the missing file and the uploader to use;
  - keep the expander open after an error. The files themselves cannot survive a rerun in
    Streamlit unless their bytes are kept in `st.session_state`; keep them that way, or say
    plainly that they must be chosen again.
- `_save_uploaded_run` (line 86) is where the error is raised and caught.

### Q11: confirm the workbook on Create Case (`ui/Create_Case.py` 555-590; upstream page)

- [seen] After a successful upload the HFP uploader vanishes and nothing confirms it; the
  heading says *"Upload Financial Profile (Optional)"* although a budget spending profile
  needs the workbook.
- Do: after `owb.readHFP` succeeds, show "Loaded <file>: <n> people, <m> budget lines" (count
  from what `readHFP` stored; check the keys it sets). Drop "(Optional)" when the case's
  spending profile is "budget". Decision 1 applies.

### Q12: after *Open in Owl* (`ui/Financial_Profile.py` 330; `ui/case_progress.py`; `sskeys.openCaseFromPlan` 340)

- [seen] Financial Profile warns that the run's `inputs/HFP.xlsx` "has not yet been uploaded"
  above tables that are loaded; the progress strip reads *"(12%) - Step 8 of 8"*.
- Do: `openCaseFromPlan` (fork code) marks the workbook as loaded the way an upload does
  (find the key the warning reads, `stHFP` or similar) and marks the Case Setup pages visited
  (`case_progress.mark_page_visited`). Prefer fixing it in the fork's own function over
  changing the upstream pages. Test with `tests/ui/test_open_in_owl.py`.

### Q13: *Edit as new run* navigates (`ui/Run.py` 598)

- [seen] It only shows a toast and stays put.
- Do: after loading the files, `st.switch_page` to the destination of decision 3, with a
  `libraryjobs.flash` message carried across. A toast does not survive `switch_page`; check
  whether `show_flashes` runs on the destination page, which is an upstream page.

### Q14: library-mode chrome

- [seen] A **Deploy** button: `.streamlit/config.toml` sets no `client.toolbarMode`. Add
  `--client.toolbarMode=minimal` to `owlplanner-library.sh` and `.cmd` (library mode only).
  Check that the option name exists in Streamlit 1.66 (`streamlit config show`).
- *Connect your AI*: decision 2.
- Welcome's third headline (*"Powered by Actual Intelligence — connect it to your AI
  assistant"*, `ui/Welcome.py` 76-81) argues against the household's offline rule. In
  library mode, hide that paragraph (decision 1, option a). The review's S1 (a home page) is
  the real fix and is out of scope.

### Q15: the conversions and brackets chart (`ui/Run.py` `_conversions_and_brackets`, 279)

- [seen] Only IRMAA tier 1 is drawn (`(row.get("irmaa_edges") or [{}])[0]`, 323). The "top of
  the bracket" line (318) zigzags because it follows whichever bracket the year is in. The
  IRMAA and ACA lines are two dotted greens.
- Do:
  - all IRMAA tiers from `irmaa_edges`, each labelled with its premium year ("2029 income →
    2031 Medicare");
  - the ordinary bracket edges as faint horizontal bands, not one zigzag line;
  - distinct hue and dash for IRMAA and for the 400% FPL line.
- The data is in `plan.json` `brackets.years[*]` (`irmaa_edges` with `premium_year`,
  `aca_lines`, `ordinary_edges`). Check what an older result without some keys shows, and
  keep the chart drawing there.
- The 28-row table under the chart: at least thousands separators and `hide_index`.

### Q16: *Taxes by kind* and *Income sources* (`ui/Run.py` chart tabs, about line 522)

- [seen + code] Medicare (with IRMAA) and marketplace premiums are in `by_year`
  (`medicare_premiums`, `aca_premiums`) but on no chart. Add them to *Taxes by kind* as their
  own series, and retitle the tab if it then holds more than taxes (for example "Taxes and
  premiums").
- [seen] *Income sources*: the purchase year sets the scale; SPIAs and Pensions are listed at
  zero. Hide all-zero series. Annotate the purchase year: find where the Run page can learn
  it, either the scenario's purchase event or the hand Fixed Assets row in the run's inputs.
  `by_year` may carry no purchase field; check, and do not add one to `plan.json` here.
- The axes stay "nominal \$" (Q6).

### Q17: the one-year Sankey (`ui/Run.py` `_cash_flow_sankey`, 106)

- [seen] Amounts show only on hover; labels collide; the hub is an unlabelled grey bar; taxes
  are split over five nodes with no total.
- Do:
  - amounts on the nodes (`node.customdata` with a value texttemplate);
  - a labelled hub ("2029 cash flow");
  - a taxes total;
  - the one-paragraph summary above it, built from `view.cash_flow_year` (the review's
    section 3 quotes the 2029 text it should produce, nominal dollars).
- The paragraph's numbers must come from the same rows the Sankey draws. Test that they add
  up (`check_library_compare.py` checks sources = uses already).

### Q18: buttons gated on a text field (`ui/Collections.py` 72; `ui/Create_Case.py` 601)

- [seen] *Create collection* is `disabled=not name.strip()`. The click that blurs the name
  field hits a disabled button, so the first real click is swallowed.
- Do: enable the button and validate on click (flash "Give the collection a name" when it is
  blank). Grep the library pages for the same pattern.
- *Create case* (`cantcreate = kz.isIncomplete() or diz1`, upstream) may have the same
  problem; the review did not exercise it. Reproduce it with Playwright before changing it
  (decision 1).
- AppTest cannot reproduce a blur-then-click; test the click-on-blank message with AppTest,
  and the swallowed click with Playwright.

### Q19: the rest of the purchase box (`ui/Scenario.py` purchase expander)

- *Paid from (person)* (line 224): a dropdown of the case's names.
- *Down payment*, *Closing costs*, *Loan closing* (236-240): shown in percent (20, 3, 2)
  while the event keeps shares. Convert at the widget only, and keep the event's own value
  when the shown percent is unchanged (no phantom edit; review X4, AK6), so no inputs hash
  moves.
- *Event id* (lines 190, 211, 307, 332): hide it behind an "Advanced" expander. The ids are
  provenance markers and anchors (`event:care+2`), so keep the default ids and keep editing
  possible.
- A warning (not a refusal) when property tax, HOA and insurance are all 0.

### Q20: Goals and Run Options wording (upstream pages)

- `ui/Goals.py` 153-167: *Profile slack (%)* and *Time preference (%/year)* behind an
  "Advanced" expander, each with one plain sentence.
- The **ξ** axis: `src/owlplanner/plotting/plotly_backend.py` 140 (and the matplotlib one,
  `matplotlib_backend.py` 457), "spending relative to year 1".
- `ui/Run_Options.py` 181: the benchmark premium `getNum` shown to 2 decimals with step 1
  (`format="%.2f"`, `step=1.0`; `sskeys.getNum` takes both).
- Decision 1 applies to all three.

## Suggested order

1. Decisions 1-3 first.
2. Q14, Q18, Q13, Q12: small, and each removes a trap on the first path through the app.
3. Q10, Q11.
4. Q19.
5. Q15, Q16, Q17: the Run page's "why" views (the most code, and the most value for the
   spouse; see the review's F4 and section 3).
6. Q20.

## Setup and driving (from the last two sessions)

- CLAUDE.md "Setup"; synthetic household from `fork-notes/synthetic/make_cases.py`
  (`fork-notes/synthetic/cases/`, gitignored). **Synthetic only, never the real household.**
- App in library mode: `mkdir -p otherFiles && OWL_LIBRARY_DIR=otherFiles/library
  .venv/bin/streamlit run ./ui/main.py --server.address=localhost --server.headless=true
  --browser.gatherUsageStats=false`. Restart the server after editing `src/` (it does not
  reload library modules); kill it by PID, not by pattern (CLAUDE.md).
- **No synthetic workbook is rent-only**: all 39 HFP files hold a condo. For a run that can
  take a purchase event, drop the baseline's condo rows (Fixed Assets, Debts, owner budget
  lines, the big-ticket outflow) through the library API, as PROGRESS.md "UX review: the four
  bugs" describes.
- Playwright is Node's (`/opt/node22/bin/node`, `require('playwright')`). Last session's
  helpers are worth rewriting the same way:
  - nav: click `[data-testid="stTopNavSection"]`, then the page link (a `page.goto` starts a
    new session);
  - selectbox: inside `[data-testid="stSelectbox"]`, the button "Open", then
    `getByRole('option')`; read the value with the inner `input`'s `inputValue()`;
  - toggles: `page.getByText('<label>')`;
  - the Queue page's *Solve a run* and the Library page's *Add a run* expanders collapse once
    runs or jobs exist: open them first;
  - wait for `[data-testid="stStatusWidget"]` to be gone; the disclaimer needs "OK" in every
    session; set the viewport to the content height for a full-page screenshot.
- Solve times measured on the condo case in this container: Quick look 0.8 s; Careful
  304-323 s (5 min 18 s with the test suite running beside it), plus 9 s for its exact
  companion. Never solve the case on the classic Graphs/Reports pages with its own options
  (claiming ages "optimize" + local search: over 22 minutes).

## Done means

- A test per item where one can be written (AppTest for page behaviour, unit tests for any
  helper); for a defect (Q12's false warning, Q18's swallowed click), the test fails before
  the fix: record that in PROGRESS.md.
- `tests/library tests/ui` plus anything touched; then the **full suite** green, with the
  count and time recorded.
- Lint: flake8 and ruff, only upstream's listed items left.
- `check_library_builder.py` 46/46 and `check_library_roundtrip.py` 39/39 if anything under
  `library/` or the Scenario page's stored values changed; `check_library_compare.py` 9/9 if
  the Run page's cash-flow numbers or Compare changed.
- **Re-drive with Playwright** on the synthetic case and quote what the pages now say for
  every [seen] item touched.
- Any upstream issue drafts (decision 1, option b) in `fork-notes/issue-*.md` with a stock
  repro and a patch verified on stock `dev`. **Not filed**: the user files them.
- Docs: PROGRESS.md (a section), `fork-notes/CHANGELOG-fork.md` (an entry), CLAUDE.md's
  "State" (a bullet for the branch), the review's status table (`fork-notes/ux-review.md`,
  top) updated per item.
- Commit with CONTRIBUTING tags, push the session's branch, **stop and report**. The user
  decides on an independent review and on fast-forwarding `main`.

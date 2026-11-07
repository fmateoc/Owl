# UX quick wins Q10-Q20: independent review of `claude/dazzling-gauss-69epxn` (2026-11-07)

Independent review of branch `claude/dazzling-gauss-69epxn` at `3617bb5` (the work is
`eaadfb7..3617bb5`, 11 commits), against the work order `fork-notes/ux-q10-q20-handoff.md`,
the UX review `fork-notes/ux-review.md` (sections 2-4) and PROGRESS.md's "UX review: quick wins
Q10-Q20, and B3's issue reworked". Findings **AL1-AL6** (2 low, 4 nit; no high or medium);
prefix AL after AK.

Environment: Linux, Python 3.11 `.venv`, HiGHS only, Streamlit 1.66.1 from the lock file, Node
22 Playwright with the pre-installed Chromium. Synthetic household only
(`fork-notes/synthetic/make_cases.py`).
**Nothing in `src/`, `ui/`, `tests/` or the existing docs was changed by this review** (only this
file). Probes and Playwright scripts were kept in the session's scratchpad (`pw/j1.js`-`j9.js`,
`pw/test_probe_q19.py`, `seed.py`); reverts and the stock/patched runs were made in throw-away
`git worktree`s (removed afterwards), with `PYTHONPATH` set to the worktree's `src` and
`owlplanner.__file__` printed.

**Status (2026-11-07):** AL1 and AL2 folded on `claude/review-ux-q10-q20` (the user's call;
PROGRESS.md "UX quick wins: the independent review's AL1-AL2 folded"); AL3-AL6 stand.

## What was run

| Command | Result |
|---|---|
| Full suite, `pytest -n 4 -q -p no:cacheprovider` on `3617bb5` (worktree) | **4510 passed, 1 skipped** (9:55) |
| `flake8 src tests ui --max-line-length=120` | only upstream's E301/E304 in `tests/stochastic/test_spending_{bequest_frontier,units}.py` |
| `ruff check src tests ui` | 4 B905, all upstream's listed items (`localsearch.py:244`, `test_local_search.py:288`, `test_roth_maturation_losses.py:49`, `ui/Run_Options.py:263`) |
| `check_library_builder.py` / `check_library_roundtrip.py` / `check_library_compare.py` | **46/46**, **39/39**, **9/9** |
| The three patches on stock upstream `dev` `73dc8815` (fresh worktree) | each `git apply --check` clean; all three apply together |
| New test files (copied) on stock `dev` / on `dev` + the three patches | stock: 4 failed, 1 passed (`test_create_case_button` 2 of 3, `test_prepare_run_failure` 1, `test_run_options_slcsp_field` 1); patched: **5 passed** |
| `tests/ui tests/tax/test_aca.py` on stock (with the new files) / patched | 4 failed, 231 passed / **235 passed**. Per-draft counts reconcile: without the new files `tests/ui` has 159 tests and `test_aca.py` 71, so B3 alone gives 231, Create Case 162, SLCSP 160, as the drafts say |
| `issue-prepare-run-failure-repro.py` on stock and patched | output **identical** to both blocks in the draft (stock: `solves: 1`, `$29,910`, wages `$0`; patched: `solves: 0`, `invalid input`) |
| The draft's control (same script, case left in CA, no move) on stock | `total wages $50,000`, as the draft says |
| `issue-create-case-repro.js` / `issue-slcsp-field-repro.js` against a stock and a patched server | output **identical** to the drafts (stock: disabled at the click, second click creates, no caption; 22.0 / 20.8 / 30.8. Patched: one click, the caption; 22.00 / 20.84 / 21.84) |
| Fork vs patch, function by function (AST) | B3: `prepareRun`, `_applyConfig`, `runPlan`, `runHistorical`, `runMC`, `showCaseStatus` identical to the patched stock file. Create Case: same apart from the fork-only Budget count and heading. SLCSP: same call (comment differs). The three test files byte-identical |
| `setACA` and `tests/tax/test_aca.py` against upstream `dev` | no diff (the 1999 hint is gone, as the user asked) |
| Reverts (worktree, the fix hunk removed) | Q12: both `test_open_in_owl` tests fail. Q13: `test_run_options_draws_the_message_edit_as_new_run_left` fails. Q19 with a plain `/100`: both share tests fail, and the probe below |
| Q19 probe (AppTest, `test_probe_q19.py`): unedited *Save as a new run* on four purchase events (loan 0.07/0.029/0.02; `pay_on` "Bill"; shares 0.1234567/0.02125; cash) | all four: *"Identical to ... not saved again"*, caption "none yet". With the plain `/100` revert, two of the four save a new run (`financing.closing: 0.029 -> 0.029000000000000005`) |
| Playwright, library mode (`OWL_LIBRARY_DIR`, `--client.toolbarMode=viewer`), one Quick-look solve of `Case_ari+noa_condo` + `HFP_..._yonkers_2027_cash` | see "What holds" |
| Playwright, the fork without `OWL_LIBRARY_DIR` (classic pages) | Welcome keeps *"Powered by Actual Intelligence ..."*; Deploy present; Goals has no *Advanced* and the profile axis reads "ξ"; menu keeps Rerun / Clear cache |
| Not run | `check_library_jobs.py`, `check_library_variants.py`, `check_library_rates.py` (nothing under `library/` changed beyond `case_references`); Windows |

## What holds (each claim checked; how)

- **Q10** [Playwright + tests]: after choosing `Case_ari+noa_condo.toml` the captions read
  *"Required: this case names HFP_ari+noa.xlsx."* / *"Not needed: this case names none."* (x2);
  importing without the workbook gives *"Not imported: this case names HFP_ari+noa.xlsx (choose
  it under Household workbook). Add it and import again."*, the expander stays open; with the
  workbook added the run is saved (toast *"Saved as Case_ari+noa_condo ..."*), the form is
  cleared and closed. No temporary path appears. `case_references` on `"None"` and on an empty
  case gives empty strings (probe).
- **Q11** [Playwright, stock/patched/fork]: one click creates; *"✅ HFP_ari+noa.xlsx loaded:
  wages and contributions for Ari; 0 debts, 1 fixed asset, 10 budget lines."* on the fork. The
  name check (`_createCase`) checks exactly what `isIncomplete` checks (`ui/sskeys.py:204`).
- **Q12** [Playwright + revert]: after *Open in Owl*, Financial Profile shows no "not yet
  uploaded" notice and the strip reads *"(100%)"*. The `stHFP` side effect checked: a table edit
  now appends " *" to `hfpFileName` (`ui/Financial_Profile.py:285-288`), but the stored case
  rewrites `HFP_file_name` to `HFP.xlsx` / `"None"` (`casefiles.py:300`, `:863-866`), so no
  saved file changes (code reading, not run).
- **Q13** [Playwright + revert]: lands on Run Options with the info message quoted in PROGRESS.
- **Q14** [Playwright]: no Deploy button; menu *System / Light / Dark / Print / Record screen*;
  no AI headline in library mode; all three back outside it.
- **Q15-Q17** [Playwright + probes]: the legend, the *"Above the chart, never reached: IRMAA
  tier 5 (from 771,000)."* caption, the tab names, the income series, the *"↑ 974,971 incl. a
  741,188 purchase"* annotation and the 2027 paragraph and Sankey labels are exactly as quoted in
  PROGRESS. Sources = uses in every year of that run (probe, within \$2). Units: brackets in
  today's \$ (`brackets.py:158`), `by_year` premiums nominal (`cli/formatters.py`), axes say so.
  `brackets_figure` on rows without any line keys draws with no note; `brackets_table([])` would
  raise, but the page returns before it on an empty `years` (`ui/Run.py`, the `if not years`).
- **Q18** [Playwright]: both buttons enabled at the click, one click creates (Collections
  verified in `library.json`); the fork's Create Case repro in library mode creates on one click.
- **Q19** [AppTest probe + Playwright]: labels *Down payment (%)*, *Closing costs (% of the
  price)*, *Loan closing (% of the loan)*, *Paid from (person)*; four *Advanced* popovers;
  unedited saves store nothing (table above).
- **Q20** [Playwright]: SLCSP shows 20.84 with step 1; Goals' *Advanced* holds the two inputs
  with their sentences in library mode only; the axis reads *"spending relative to the first
  year"* on the budget-profile run (the plotted curve is `xi_n` itself, `plotly_backend.py:134`).
- **Gating** [code + Playwright]: Welcome (`OWL_LIBRARY_DIR`), Goals, the axis title and
  `titleBar`'s flash (`kz.library_mode()`) are library-only; the launchers' flag is in the
  library launchers only. The Create Case Budget heading is fork-only but not gated (budget
  profiles are a fork feature), as PROGRESS says.
- **No solve, format or hash moved** [suite + checks + probe]: `src/` changes are `case_references`
  (read-only) and `setACA` back to upstream's; the builder and round-trip checks are unchanged;
  the Scenario page's unedited saves are refused as identical.
- **B3 draft** [runs + code]: the six caller lines (214, 267, 311, 611, 860, 2662) and the
  Create Case warning (`ui/Create_Case.py:186`, *"The new state is the starting state."*) are
  on stock `dev` as cited; the partial application shows in the output (`plan: state 'CA'`).
- **Create Case draft**: its line numbers (267, 320 on stock `dev`) hold.
- **SLCSP draft**: its line number (178) and `getNum`'s defaults (`%.1f`, step 10) hold.

## Findings

### AL1 (low): the Scenario page's *Save as a new run* swallows the first click after a field is corrected

`ui/Scenario.py:605`: `st.button("Save as a new run", type="primary", disabled=built is None)`.
It is the Q18 pattern (a button gated on what a text field holds), on a library page; the work
order asked to grep the library pages for it, and PROGRESS lists Q18 as done on Collections and
Create Case only.

Reproduced (`pw/j8.js`, library mode, the synthetic run, *Edit the scenario*): tick *A care
span*, type `bogus` in its *From* and press Enter (*"Not buildable yet: care.from: 'bogus' is not
a year ..."*, Save disabled); then type `2040` without Enter and click Save with the mouse:

```text
save disabled at the click: true
after one click: []
save disabled now: false
```

The click lands on the still-disabled button and nothing is saved; a second click is needed.
Only reachable after the page was in a not-buildable state, hence low. Fix as on the other two:
enable the button and, on a click while `built is None`, say why (the page already shows the
reason above it).

### AL2 (low): after *Edit as new run* the progress strip still reads a quarter done

Q13 now sends *Edit as new run* to Run Options, a Case Setup page. That branch
(`ui/Run.py:548-566`) loads the run through `kz.createCaseFromFile` and `owb.readHFP`, not
through `openCaseFromPlan`, so Q12's marking of the eight pages as visited
(`ui/owlbridge.py`, `openCaseFromPlan`) does not run. Observed (`pw/j3.js`): after *Edit as new
run* and a visit to Financial Profile the strip reads *"Case Setup Progress: (25%) - Step 2 of
8"*; after *Open in Owl* it reads *"(100%)"*. The "not yet uploaded" notice is gone on both
paths (`readHFP` sets `stHFP`). The review's [seen] item was about *Open in Owl*, so this is a
twin, not a regression. Fix: mark the pages visited in the *Edit as new run* branch as well
(one shared helper).

Inferred, not reproduced: if `readHFP` fails there (it returns `False` and shows `st.error`),
the branch still flashes "The inputs ... are open" and switches page, and the error does not
survive the switch.

### AL3 (nit): Create Case's new confirmation prints the run's absolute path after *Open in Owl*

Q11's `_hfpLoadedText` (`ui/Create_Case.py`, fork copy) uses `hfpFileName` as is. After *Open in
Owl* that is the plan's workbook path, so the new line reads (`pw/j4.js`):

```text
✅ /tmp/.../scratchpad/lib/runs/2026-11-07_condo-yonkers-2027-cash/inputs/HFP.xlsx loaded: wages and contributions for Ari and Noa; 0 debts, 1 fixed asset, 10 budget lines.
```

PROGRESS records the same full path on Financial Profile's own (upstream) line and leaves it,
but this line is new fork text. Fix: show `Path(name).name` in the fork's copy (stock `dev`
never puts a path there through an upload, so the upstream patch need not change).

### AL4 (nit): the one-year paragraph calls a STAR refund "income" under its row name, and names differ from the Sankey's

`ui/run_charts.py` `_source_group` puts every non-savings source in "income", and
`INCOME_WORDS` has no entry for `view.cash_flow_year`'s "..., net refund" rows, so in 23 of the
synthetic run's 28 years the paragraph reads (probe on the solved run):

```text
2031: spending $154,199. The money comes from savings, $133,424 (...), and from income, $29,645
(Social Security $28,931, State and local tax, net refund $714). Taxes $2,847: federal income tax $2,847. ...
```

so the NY tax appears as income and not under *Taxes*. Also: the paragraph says *marketplace*
/ *Medicare* while the Sankey's nodes say *ACA premiums* / *Medicare premiums*; and with one
premium line there is no *Health premiums* node (`sankey_figure` gives a group its own node only
with two or more lines), though PROGRESS lists "Spending / Taxes / Health premiums nodes carrying
totals". The arithmetic is right (sources = uses each year). Suggestion: a phrase for the refund
rows (for example "a state tax refund (STAR) \$714") and the same words on both.

### AL5 (nit): two new branches have no test

The axis title's smile branch (*"spending, relative scale (the profile's shape)"*) and
`_setYTitle`'s matplotlib branch (`ui/owlbridge.py`, `showProfile`) are not exercised:
`grep` finds only the flat case in `tests/ui/test_ux_chrome.py:138`. The synthetic household
has no smile case, so neither was driven here either.

### AL6 (nit, docs): the final suite count is promised but not recorded

PROGRESS.md's section says *"the full suite on the final code is recorded below"*; nothing
follows (`grep -n "4507\|final code" PROGRESS.md` finds only line 7337/7339), and CLAUDE.md's
latest count is 4507 at `bdfebd9`. This review's run on `3617bb5`: **4510 passed, 1 skipped**
(9:55, Linux, `-n 4`).

## Summary

| Severity | Findings |
|---|---|
| High | none |
| Medium | none |
| Low | AL1 (Scenario *Save* loses the first click after a fix), AL2 (*Edit as new run* leaves the strip at 25%) |
| Nit | AL3 (absolute path in Create Case's new line), AL4 (refund called income; wording differs from the Sankey), AL5 (smile / matplotlib title untested), AL6 (final suite count not recorded) |

The three issue drafts hold as written: their patches apply to stock `dev` `73dc8815`, their new
tests fail on stock and pass patched, and every pasted output was reproduced exactly. The user
decides what gets folded.

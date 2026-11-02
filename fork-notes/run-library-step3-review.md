# Review of run-library step 3 (2026-11-02)

Independent review of build step 3 (`claude/run-library-step3`, commits `b392838f`..`f4ac3803`):
"Library page, run page, comparison of two results with the noise rule" — design
`fork-notes/run-library-design.md` sections 5, 7, 8.1-8.3, 9 (9.1/9.2), 10, 11, against the
code, its tests and the build's self-description (PROGRESS.md's step-3 entry, CLAUDE.md's
State bullet). Nothing was fixed; every finding below is backed by a probe or a line
reference. Probes live in `C:\Users\fmate\AppData\Local\Temp\opencode\probe*.py`.

## How I checked

| What | How |
|---|---|
| Noise rule (R2) vs sources of truth | read `fork-notes/synthetic/run_suite.py` (`score`, `score_label`, `_score_plan`, `group_table`'s `~` rule incl. its `> 0.5` guard, `agreement`, `run_checks`, `EXACT_GROUP`), CLAUDE.md "Loop noise" / "Plans start today"; walked `view.py`/`compare.py` line by line; `probe8_lead_verdict.py` brute-forced R3's rule over every sign/verdict combination |
| Score / home / taxes derivations | `export.plan_metrics`, `cli/formatters.plan_to_dict`/`plan_convergence`, `library/results.build_record` read against `view.py`; `probe1_exact_lp_fingerprint.py` (the `decision_exact` fingerprint end to end through `resolve_options` → `parse_solver_options` → `build_record` → `record_is_exact_lp`); `probe2_missing_summary.py` (missing `summary.json`) |
| Companion lookup | `probe3_companions.py` (self-companion, cross-companion, shared companion) |
| Zip path | `probe4_run_zip.py` (arcname separators, files vanishing mid-zip, `.requeue-*` leakage) |
| Streamlit pages | `probe5_apptest_widgets.py` / `probe5b_apptest_widgets.py` (Streamlit `AppTest`: "Open" from the Library page, result-selector shrink, `Compare.py` label changes under a rerun) |
| `_open_log` (N4 fix) | `probe6_open_log.py` (rename-while-open, error path, handle release) |
| `git check-ignore` refusal (M2) | `probe7_git_ignored.py` plus direct `git check-ignore -v` probes in the repo and in scratch repos isolating the trigger (git 2.52.0.windows.1) |
| Test suites | `.venv\Scripts\python -m pytest tests\library tests\ui -q -p no:cacheprovider` → **384 passed, 1 skipped (155 s)**; full suite `-q -n 4` → **3836 passed, 2 skipped (687 s)**; `pytest --collect-only` for the count claims |
| Acceptance check | ran `fork-notes/synthetic/check_library_compare.py` myself: **6/6**, output matches every figure PROGRESS claims (108,959 / 760,861 / 0 / 310,107; 67y0m+67y0m; −13.34%; 2 input changes; 28 years moved; re-solve all +0; d_quick −14,530, d_exact −15,672 resolved) |

## Findings

### P1 — blocker

**P1. The section-10 `git check-ignore` refusal does not fire for any *new* library folder
inside the real repository; `Library.open` happily creates one under `src/`.**
PROGRESS ("`Library.open` refuses a library folder inside a git repository that does not
ignore it") and CLAUDE.md claim this works. It does not, on this repo and this git.

Evidence (probe7, plus direct probes):

```
git -C C:\Projects\Owl check-ignore -q -- "C:/Projects/Owl/src/probe9/"   → exit 0 (says "ignored")
git check-ignore -v -- "src/probe9/"     → .gitignore:103: <empty pattern>  src/probe9/
git check-ignore -v -- "noexist/"        → .gitignore:103:  noexist/     (bogus)
git check-ignore -v -- "docs/"           → exit 1  (tracked dir: correctly not ignored)
```

`_git_ignored` (`store.py:68-98`) appends a trailing "/" precisely so it can classify a
folder that does not exist yet — and that trailing slash is what trips the quirk: with a
CRLF `.gitignore` containing a blank line (the repo's is CRLF; line 103 is blank), git
2.52.0.windows.1 reports **every not-yet-existing trailing-slash path — and every existing
*untracked* trailing-slash path — as ignored**, matching the blank pattern. Minimal repro
(`scratchrepo2`): `.gitignore` = `"build\r\n\r\n*.log\r\n"` → `check-ignore -v -- "nope/"`
exits 0; with LF endings or without the blank line it exits 1.

End to end: `Library.open(Path(r"C:\Projects\Owl\src\probe7b"))` **created** the library
(`git status` showed `?? src/probe7b/`; I removed it afterwards). The refusal only fires for
paths that are themselves tracked folders (e.g. pointing `OWL_LIBRARY_DIR` at `docs/`) —
the opposite of the useful case. The default (`otherFiles/library`) is genuinely ignored
(`otherFiles/` matches), so the launcher default is safe; the hole is exactly the case M2
was written for ("Queue.py will create a library anywhere OWL_LIBRARY_DIR points, a public
repo included").

Tests have no teeth here: `test_store.py:308` probes a repo with **no** `.gitignore`, and
`:315` writes a **LF** `.gitignore` — neither shape reproduces the real repo.

Suggested fix: treat "ignored" as authoritative only when a *non-empty* pattern matched
(`git check-ignore -v`/`-z` and parse the pattern; the bogus match reports an empty one), or
probe through a real marker file created inside the folder and classified without a trailing
slash; add a regression test with a CRLF `.gitignore` containing a blank line.

---

### P2 — should-fix

**P2. The Library page's "Open" stops switching runs once the Run page has rendered once.**
`ui/Run.py:67-70` computes `default`/`index` from `st.session_state["library_selected_run"]`,
but the selectbox `key="run_page_run"` keeps its own widget value across reruns/pages and
overrides `index`. probe5 (AppTest):

```
first render header:        ['## bill one']
at.session_state["library_selected_run"] = <bill's id>   # what Library.py's Open button sets
after Open(bill) header:    ['## bill one']               # unchanged; selectbox value unchanged
```

So "Open" works only the first time in a session; every later click silently shows the
previously selected run. (The *selector itself* works, so the impact is confusion, not data
loss.) Fix direction: drive the selectbox from the session value explicitly (e.g. set
`st.session_state["run_page_run"]` to the chosen label before `switch_page`, or reset the
widget key when `library_selected_run` changes).

**P3. A result with a missing (or empty) `summary.json` reports every number as $0 and the
quality as "settled", and comparisons judge those zeros "resolved".**
`view.load_result` fails soft to `{}`; `Result.solved` checks only `record.status` and
`plan`; `score`/`home_at_end`/`savings_left`/`total_taxes_today` default to `0.0`
(`view.py:80-131`). probe2 (record "solved", plan.json present, summary.json absent):

```
solved: True   score: 0.0   home_at_end: 0.0   quality: []
rows: [('score', 0.0, 82000.0, 82000.0, 'resolved'), ...]
lead: {'verdict': 'the second result leads', ...}
```

The same path is reachable in practice: `JobRecord.publish` renames the artifacts one by one
(`results.py:343-344`), so a reader in that window can see `summary.json` without `plan.json`
or a new summary beside an old plan; a hand-deleted file also lands here. Missing keys should
read as "no numbers" (`None`, the row's "-") plus a quality note, not as zeros that a
comparison calls resolved. (Same defaulting: `score` treats a missing `objective` in
plan.json as `maxBequest`-like and returns the bequest — `view.py:79`.)

**P4. The exact-model companion lookup can pair results wrongly whenever a run has more than
one exact solve, and one result can be both sides' companion.**
`compare.exact_companion` skips only ids in `exclude`, and `ui/Compare.py:128-129` passes
`exclude={job_a.id}` for A's companion and `exclude={job_b.id}` for B's — the other
selection is not excluded, and `compare()`'s guard (`compare.py:282`) only checks
`a_exact != a and b_exact != b`. probe3:

- one run with LS1, LS2, E1, E2: A=LS1, B=LS2 → **a_exact is b_exact is E1**; the "exact
  model" difference is then `score(E1)-score(E1) = 0` and the verdict comes out
  `"unresolved: the two models disagree on the sign"` (a zero exact difference looks like a
  sign disagreement);
- A=E1, B=E2 (both exact) → each other's "companion": `d_ex = −d_ls` → always
  "unresolved: the two models disagree on the sign";
- `exact_companion` returns the **first** match in `manager.jobs()` order = the *oldest*
  exact solve of the run, even when a newer one belongs to the compared pair's day (the S13
  day flag covers only A vs B, not the companions).

`tests/library/test_compare.py:165` even codifies the shared companion
(`compare(a, b, a_exact=exact, b_exact=exact)` asserted to have an agreement) and nothing
guards `a_exact is b`. Fix direction: exclude **both** selected ids per lookup, require four
distinct results, prefer the companion queued together with the pair's solve.

**P5. `run_zip` is computed eagerly on every page render and can crash the page or ship a
wrong zip.**
`ui/Library.py:183` builds a full zip **for every run on every rerun** (including all
`Results.xlsx`/`plan.pkl` bytes) just to render the button; `ui/Run.py:204` does the same for
one run. probe4:

- a file removed between `rglob` and `is_file()` is **silently skipped** → the downloaded
  "everything" zip can be missing `plan.json` with no warning;
- a file removed between `is_file()` and `zipfile.write` (the `requeue`/"run again" window)
  raises `FileNotFoundError`, uncaught in the page → the whole page errors;
- a requeue's transient `.requeue-<hex>` trash folder **is included** (probe4 case 3), which
  PROGRESS's "everything but lock files and `.attempt-*` staging" does not mention.

Fix direction: build the zip lazily on click (`st.download_button` with `on_click`/cached
data keyed by run), skip `.requeue-*` like `.attempt-*`, and either catch the vanished-file
case or snapshot the listing under the job's lock.

---

### P3 — minor

**P6. "A dollar or less is no difference" is not what the code does.** The guard is
`TIE_DOLLARS = 0.5` (`compare.py:45`, `abs(delta) <= TIE_DOLLARS` → "no difference"), i.e.
**50 cents**; a $0.75 difference is judged normally. run_suite's guard is also `|delta| > 0.5`
(its `~` marker). The "dollar or less" wording appears in `compare.py`'s docstring,
PROGRESS's step-3 entry, CLAUDE.md's State bullet, and the test name
(`test_a_difference_of_a_dollar_or_less_is_no_difference` tests exactly 0.5). Reword to
"fifty cents" or change the constant.

**P7. The ACA rule is announced but not applied.** Design 9.2: "a disagreement there goes to
the local-search result, not to a tie". `compare.agreement` keeps the verdict
"unresolved: ..." and only appends a note that says the disagreement "goes to the local-search
result, not to a tie" (`compare.py:185-194`) — the screen contradicts itself, and the test
(`test_in_aca_years_a_disagreement_goes_to_the_local_search_result`) asserts only the note's
text. Either make the verdict defer to the local-search difference in ACA years, or reword
the note to describe what is actually shown. (PROGRESS discloses "(the note is shown)", so
this is a rule left unimplemented, not a false claim.)

**P8. `view.tolerance` and PROGRESS cite a CLAUDE.md gotcha "Branch-and-bound gap" that does
not exist.** (`view.py:253-260`, PROGRESS line ~5135.) The substance ("read the reported gap
before calling a difference") is in CLAUDE.md's **"Plans start 'today'"** bullet; grep finds
no "Branch-and-bound gap" section anywhere. Fix the citation.

**P9. `tolerance()` uses gap x *score*, not gap x *objective*.** `view.py:271-272`
(`value = score(result); return gap * abs(value)`), and `test_view.py:179` pins
`1e-4 * 82_000` (the discretionary score) for a `maxSpending` plan whose objective value is
the spending basis. The design and CLAUDE.md say "reported gap x objective": the proof bound
is on the MIP objective (≈ spending basis incl. essential lines), which is larger, so the
tolerance is understated whenever essential lines are big (e.g. essential 400k +
discretionary 50k → tolerance should be ~9x larger). Use the objective value (spending basis
under `maxSpending`, bequest under `maxBequest`) or document the choice.

**P10. Test-count claim does not match the diff.** PROGRESS: "67 new `tests/library` tests";
`git diff 7366cdee HEAD` adds 51 `def test_` in tests/library (compare 18, view 22,
presets 4, store 5, results 2; 0 deleted). `tests/ui` claim of 13 is exact. (Commit
e223d866's "Tests: 71 + 31 in tests/library" is likewise unexplained.) Count again or drop
the number.

**P11. Same-second catalog ties sort by a random uuid.** `Library.runs()` sorts by
`(created, id)` with `created` at second resolution and `id = uuid4().hex` (`store.py:344,
423`) — two runs saved in the same second appear in arbitrary (though stable) order, while
`library.json`'s `order` list, which records the save order exactly for this purpose
("the order shown", `store.py:5`), is maintained (append/prune) but never read. Likewise
results folders (`jobs._queued_order`, `(queued stamp, folder name)`) tie-break by folder
name, which interleaves a `decision` job and its `decision_exact` companion oddly. Use the
`order` list (or a monotonic sequence) as the tie-break.

**P12. Test gaps in exactly the new surfaces.** No UI test exercises either zip button (the
race in P5 is untested), none checks the S13 flags' rendering on the Compare page (only the
pure `flags()` function), and nothing drives `preset_solves("decision")` through
`JobManager.enqueue`/Run.py's Solve button (two queued jobs; only `preset="quick"` is ever
enqueued in tests — `test_jobs.py:85`, `test_worker.py:306`). `test_edit_as_new_run...`
asserts `library_base_run_id in {r.id for r in library.runs()}` — any run passes, so a wrong
base run would not fail it.

**P13. `library_base_run_id` is never cleared.** It is set only by "Edit as new run"
(`Run.py:218`) and read by "Save the current case" (`Library.py:90,136`), which then uses it
as the diff base and as `parent`. Loading a case any other way afterwards (upload, "Load a
Case Example", "Open in Owl" from *another* run) leaves the stale id in the session, so the
next save claims the wrong parent and gets a change summary against the wrong scenario —
this is the one thing `scenario_from_ui(base=...)` (T1/T3) depends on. Clear the key
whenever a case is opened from something other than "Edit as new run". (Also: "Edit as new
run" twice in a session fails the second time with `sskeys.createCaseFromFile`'s "Case name
'…' already exists" and silently skips the HFP read and the base setting.)

**P14. Tiny wordings.** Run.py shows an unsolved result's problem twice (the `st.error` at
`Run.py:110-113` and `quality_notes`' "not solved: …" as a `st.warning`); Compare.py's
agreement caption says "under local search" although the primary pair may be any presets
(the acceptance check itself compares a `quick` pair and prints "d_quick"); PROGRESS's
"Everything the run page shows derives from record.json/summary.json/plan.json alone" — the
workbook sheets come from `Results.xlsx` (the `plan.pkl`-independence claim itself is true
and checked).

---

## Verified as sound

- **The noise rule's substance (R2).** Direction is consistently `b − a`
  (`compare.difference`, `agreement`, `what_moved`, and the page says so). Tolerances:
  proved = reported gap from `record.json` (`plan.solverGap`, −1 when none) and "larger than
  both" = `max` of the pair's tolerances; unproved = 1% of the row's reference value,
  `<= tol` reads "within noise"; the mixed pair takes the stricter tolerance. Matches
  `run_suite`'s `~` rule (|%| < 1 with the `> 0.5` guard) apart from the $0.50-vs-$1 wording
  (P6), the score-vs-objective question (P9), and the exactly-1% boundary (`<=` here vs
  `<` in run_suite — negligible).
- **R3's leads/trade-off rule.** `probe8_lead_verdict.py` covers every combination of
  {resolved ±, within noise, no difference} × the two numbers: leads exactly when at least as
  good on both and better on one; both directions trade off; "not comparable" when a number
  is missing. Correct in every combination.
- **The score rule and the derivations.** `discretionary_year1` (k × D₀) → spending basis →
  final bequest matches `_score_plan`/`score`/`score_label` exactly;
  `home_at_end = final_bequest_today − final_bequest_savings_today` matches run_suite's
  `home_at_end_today`; the summary/plan key names match `plan_metrics`/`plan_to_dict`
  (the acceptance check derives all headline numbers from real worker artifacts). Claiming
  ages via `plan.json`'s new `claiming_ages`/`individuals` pair correctly.
- **The `decision_exact` fingerprint.** probe1: the worker's path
  (`resolve_options` → `parse_solver_options` → `build_record`) leaves options that
  `record_is_exact_lp` matches exactly; `quick`/`decision`/`custom` never match; `EXACT_GROUP`
  (loop, Medicare none, SS taxability 0.85, `withLTCG="optimize"`) is reproduced in
  `presets._FORCED` and is what `run_suite`'s agreement rule reads. The declared deviation
  ("exact model" vs the design's "exact LP") is worded consistently in `presets.py`,
  `view.py`, `compare.py`, the Compare page caption, PROGRESS and the amended design 8.1
  (`f4ac3803`).
- **The agreement rule itself** (same sign and larger than spread + the four error bars,
  `error_bar` = `oscillationAbs/2` = `objective_error_bar_today_dollars`) matches
  `run_suite.agreement` term for term; the zero-difference edge ("disagree on the sign") is
  run_suite's own behavior too.
- **`quality_notes`/`quality_line`** mirror `run_checks` (same convergence strings —
  "monotonic"/"oscillatory"/"max iteration"/"unsolvable iterate"/"undefined", checked against
  `plan.py`; same `error_bar > 0.5` threshold; same warning filters).
- **The N4 fix (`_open_log`).** probe6: the old handle keeps writing into the renamed
  `solve.prev.log` after `requeue` (the regression's purpose), a new attempt can create its
  own `solve.log`, the handle is released on close, and the error path raises `OSError`
  with a message and no handle to leak. (Only a narrow leak remains if `msvcrt.open_osfhandle`
  itself raised after `CreateFileW` succeeded.)
- **`record_is_exact_lp` defaulting:** the run page defaults to the newest non-exact solve
  and the Compare page's default pair skips exact companions, as PROGRESS claims.
- **Test suites green:** `tests\library tests\ui` 384 passed, 1 skipped (155 s); the full
  suite `-n 4`: **3836 passed, 2 skipped in 687 s** — no flakes (including H6's git-stamp
  flake, which its two new regression tests target); `check_library_compare.py` 6/6 with
  every number matching PROGRESS.
- **The localhost guard** (`libraryjobs.library_address_ok`) matches its claim and is tested.

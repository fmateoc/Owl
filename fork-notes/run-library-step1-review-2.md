# Second review of run-library build step 1 (2026-11-02)

Review of branch `claude/run-library-step1` at `c970bf05` (step 1 plus the V1-V10 fixes) against
`fork-notes/run-library-design.md` (sections 4-7, step 1), `run-library-review-2.md` (S1-S13) and
`run-library-step1-review.md` (V1-V10). Findings are numbered **T1-T6**. Every finding below was
reproduced by a probe run here (scripts in the session scratchpad, on Linux, Python 3.11, real
date 2026-11-02, not pytest's frozen 2026-01-01) unless it says "inferred".

## Checks run

- `pytest tests/library -q -p no:cacheprovider` -> **65 passed** (4.6 s).
- `flake8 --max-line-length=120` and `ruff check` on `src/owlplanner/library`, `tests/library`,
  `check_library_roundtrip.py` -> clean.
- `make_cases.py` then `check_library_roundtrip.py` -> **39/39 pairs round-trip unchanged**, exit 0.
- Full suite not run: the branch changes no file under `src/` outside `library/` (`git diff --stat`).

## Findings

| # | Severity | Finding | Evidence |
|---|---|---|---|
| T1 | high | **The stored case dictionary is not canonical, so the inputs hash and the change summary see differences that are not inputs.** Three sources: (a) `HFP_file_name` (and a flattened `budget_file`) keep the source file's name in `scenario.case`, while the generated `Case.toml` names `HFP.xlsx`; (b) `ui_to_config` fills defaults the TOML omits, so the import path and the UI path give different case dicts for one unedited case; (c) the UI path keeps full float precision, which `save_toml` truncates to 8 significant figures in the frozen `Case.toml` (V10). Effects: saving a run's own generated files unchanged with the run as parent creates a **new run** with change summary `HFP_file_name: 'HFP_ari+noa.xlsx' -> 'HFP.xlsx'`; the unedited jack+jill case through the two paths gives a different hash and **20 diff lines** (`aca_settings` added, `social_security_ages[1]: 62.08333 -> 62.083333333333336`, `liquidation_tax_rate` added, ...); a UI-path scenario differs from its own `Case.toml` re-imported (`62.083333333333336 -> 62.083333`). So V3's "`scenario.json` is exactly the document the frozen files were built from" holds for the bytes generated, not for what those files read back as, and V9's "both paths hash the same" (`casefiles.py:26-27`) is false: its test (`test_both_entry_paths_agree_without_a_workbook`) asserts only `imported["hfp"] == from_ui["hfp"]`, not the hash its docstring names. Any step-3 "open, edit one field, save as" will show the real change buried in ~20 spurious lines, and the dedupe will not fire across paths. | probes 1-3; `casefiles.py:118`, `296`, `302`; `toml_io._clean_float` |
| T2 | medium | **`Library.open` deletes every staging folder, including a save in progress elsewhere.** The comment assumes one opener per library ("at start-up no save is running"), but nothing enforces it, and the design itself plans for two tabs (S5). A second `Library.open` during another session's `generate` makes that save fail with `FileNotFoundError` and no run. Fix: drop only staging folders older than some bound (hours), or move the cleanup into the singleton manager's start-up (step 2) and document that `open` must not be called per page. | probe 4; `store.py:110-115` |
| T3 | medium | **The UI path rewrites the plan year to the current year.** `config_to_ui` turns `start_date` into today's year (`ui_bridge._start_date_to_ui`, lines 151-158), so `scenario_from_ui` records `plan_year` = this year whatever year the run was entered for: a case with `start_date = "2025-01-01"` saved today gets `plan_year 2026` and `start_date 2026-01-01`. R1's rule ("a run belongs to one plan year") is the reason `plan_year` exists; a run opened in 2027 and saved as a child would silently move to 2027 with 2026's balances. The tests cannot see it: they freeze the date at 2026-01-01 and use 2026 cases. Fix: in `scenario_from_ui`, take the plan year (and the start date's year) from the parent run or the loaded case, not from the UI dict; add a test with a non-current year under the real date or a different frozen date. | probe 5 |
| T4 | low | **`diff_summaries` uses Python equality** (`normalize(old) == normalize(new)`, `scenario.py:160`), so `1 -> 1.0` and `True -> 1` report no change while the hash, by V3's design, differs: an int->float edit made a new run with `changes: []`. Fix: compare `canonical_json` of the two values. | probe 1 (P2, P3) |
| T5 | low (inferred) | **Stale-lock takeover races.** Two waiters can both judge the lock stale; the second `unlink`s the first's fresh lock and both proceed (`store.py:168-174`), and a holder whose lock was taken over deletes the new holder's lock in its `finally`. Only after a crash leaves a stale lock, and with V6 the hold is short. A token in the lock file (check it before unlink) closes both. Not probed. | code reading |
| T6 | low (design note) | **S1's mechanism is not the one in the code.** `yearFracLeft` comes from the case's own `start_date` month/day; only `start_date = "today"` (or none) reads today's day (`plan.py:881-895`), and the synthetic and household templates give an explicit date (`make_cases.py:250`). The day of the frozen date still matters, but through `_ssaCurrentAgeMonths` (`plan.py:5425`: the current **month** bounds the earliest claimable age under `withSSAges`) and through the year everywhere else (`hfp_io`, `debts`, `fixedassets`, `pension`). S1's conclusion (freeze to the run's own "as of" date) stands; its evidence line should name these. | grep of `date.today()` in `src/owlplanner` |

## Checked and fine

- Budget and workbook lookup order (explicit, CWD, then beside the case) matches Owl's own
  (`plan_bridge.py:83-88`, `391-395`), so V1's fix resolves what Owl resolves.
- Staging plus a single `os.replace` publish, the dedupe under the lock, `dropped` (V8), damaged
  `run.json` skipped (V7), trash with collision suffixes: as described, and tested.
- The removed `otherFiles/PROGRESS.md` was a Phase 1 progress log (only its first 30 lines read
  here; no household amounts in them).

## Suggested order

T1 and T3 before step 3 builds on `scenario_from_ui` (both decide what a "change" and a "plan
year" mean on the run page); T2 with step 2's manager; T4 with T1 (same diff path); T5 and T6
when convenient. For T1, a canonical form that reads back from the generated TOML (write with
`save_toml`, parse, substitute the library's own file names) settles (a) and (c); (b) needs a
choice: filling Owl's defaults on import through `config_to_ui` -> `ui_to_config` is **not**
lossless (on `Case_ari+noa_condo.toml` it drops `asset_allocation.interpolation_center` and
`interpolation_width`), so either fill defaults another way or compare and dedupe on a
defaults-filled view while storing the dict as entered.

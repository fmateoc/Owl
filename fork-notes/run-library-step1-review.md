# Independent review of run-library build step 1 (2026-11-01)

Review of the step-1 implementation (`src/owlplanner/library/`, `tests/library/`,
`fork-notes/synthetic/check_library_roundtrip.py`) by an independent reviewer agent on
2026-11-01, against `fork-notes/run-library-design.md` sections 4-7 and 11 (step 1) and
`fork-notes/run-library-review-2.md` (S1-S13). The reviewer verified everything against the
code and ran the checks itself (fresh context; it did not read the summaries as truth). Findings
are numbered **V1-V10**. The commit reviewed was `2a9751c2`.

Commands run from `C:\Projects\Owl`:

- `uv run python -m pytest tests/library -q -p no:cacheprovider` -> **50 passed**
- `uv run python fork-notes/synthetic/check_library_roundtrip.py` -> **39/39 pairs round-trip unchanged**
- `uv run python -m flake8 src tests ui --max-line-length=120` -> only the known E301/E304 in `tests/stochastic/test_spending_bequest_frontier.py`, `test_spending_units.py`
- `uv run ruff check src tests ui` -> only the known B905 at `localsearch.py:244`, `test_local_search.py:288`, `test_roth_maturation_losses.py:49`, `Run_Options.py:257`
- Ad-hoc probes in `%TEMP%\opencode` (`probe_step1.py`, `probe_budget.py`); nothing written inside the repo.

## Findings

| # | Severity | Finding | Evidence | Suggested fix |
|---|---|---|---|---|
| V1 | high | **Saving from the pages fails for any `budget_file` case unless `budget.json` happens to be in the server's CWD.** `scenario_from_ui` re-resolves `plan.budgetFileName` with `case_path=None`, and `_resolve_sibling` then tries the CWD only -- while `plan_bridge._load_budget_file` had already found the file CWD-then-beside-the-case at plan build. A plan that loaded its budget fine therefore cannot be saved: the save raises `ScenarioError: budget file 'budget.json' not found`. *(probe B: fails from the repo CWD, succeeds only after chdir to the case's folder.)* | `src/owlplanner/library/casefiles.py:128-131`, `155-168`; contrast `src/owlplanner/config/plan_bridge.py:83-88` | Resolve against the case's directory (pass one in), or take the already-loaded budget from the plan instead of re-resolving the bare name. |
| V2 | medium | **A case that names `budget_file` and whose Budget sheet wins exports a broken frozen pair.** The sidecar is captured only when `plan.budgetFromFile` is set; when the sheet wins (Owl's own rule) the case dict keeps `budget_file = "budget.json"` but no sidecar is written, so the frozen `Case.toml` references a file that does not exist in `inputs/` and the run's own generated files fail to load. *(probe A.)* | `src/owlplanner/library/casefiles.py:128-131`, `237-245`, `208-209` | Write the sidecar whenever the case names a `budget_file`, or drop/normalize the reference when no sidecar is written. |
| V3 | medium | **`scenario.json` is not the document the frozen files were generated from, and the hash aliases documents that generate different files.** `save_run` writes `scenario.json` through `pretty_json` -> `_normalize` (integral floats become ints, NaN becomes null) but hands the raw scenario to `generate`. And because `_normalize` collapses int/float, two scenarios hashing "identical" can produce differently typed generated files (TOML keeps `24000` and `24000.0` apart; `toml_io._clean_float` preserves the distinction deliberately). *(probe 3.)* | `src/owlplanner/library/store.py:273` vs `278`; `src/owlplanner/library/scenario.py:43`, `61-63` | Normalize the scenario once up front (before hashing *and* generating), and drop the int->float collapse so the hash reflects the generated text. |
| V4 | medium | **NaN (or None) inside the case dict passes `validate` and then breaks export.** `_json_safe` does not recurse into containers, so a nested `float("nan")` (a legal TOML value) survives `scenario_from_case`, passes `validate`, and makes `export_case`/`save_run` die with a raw `ValueError` from `toml_io._clean_float`; a nested `None` is worse: `save_toml` silently drops the key. *(probe 4, probe 10; latent today: no example case carries such values.)* | `src/owlplanner/library/casefiles.py:34-54`; `src/owlplanner/library/scenario.py:82-84`; `src/owlplanner/config/toml_io.py:86` | Reject non-finite floats and `None` in case values with a clear `ScenarioError` at validate time (checked afterwards: `ui_to_config` and `load_toml` emit neither on `examples/Case_jack+jill.toml`, `Case_joe.toml`, `Case_chris+pat.toml`, `Case_bill.toml`, so fail-loud blocks nothing legitimate). |
| V5 | medium | **Import stores `hfp_io.read`'s conditioned tables, which are date-dependent and silently rewrite/drop hand rows.** Conditioning adds zero rows for every missing year in `[today-5, today+horizon)`, drops rows outside that window, and clamps a past Fixed Assets `year` to today. The same files imported in 2026 vs 2027 yield different tables and different inputs hashes; schema v1's "every row is a row the user entered" is not strictly true. | `src/owlplanner/hfp_io.py:330`, `361-374`, `663-673`; called from `src/owlplanner/library/casefiles.py:203-206` | Document this now; pin the conditioning year to the scenario's `plan_year` with step 2's `as_of` (S1/S7) so import is deterministic. |
| V6 | medium | **A save slower than `lock_stale` gets its lock stolen while legitimately holding it.** The lock's mtime is set at creation and never refreshed; `save_run` holds it across `generate` (workbook + TOML writes). With `lock_stale=10` a slow `generate` lets a second writer's stale-takeover proceed concurrently *(probe 7)*. Also the `except OSError: continue` in the stat path loops without a deadline. | `src/owlplanner/library/store.py:143-167`, `258`, `294-295` | Generate into a staging folder before taking the lock (the hold becomes fast metadata work), and bound the retry loop by the deadline. |
| V7 | medium | **One corrupt `run.json` bricks the whole library.** `_info_from_dir` does no error handling, so a hand-edited or damaged file makes `runs()` raise, which also kills `save_run`, `get`, `rename_run` and `delete_run`. Every step-3 page will call `runs()`. *(probe 8.)* | `src/owlplanner/library/store.py:175-201`, `213-217`, `259` | Catch `(OSError, ValueError, KeyError)` in `_info_from_dir` and surface the folder as damaged (skip + a `damaged` list) instead of propagating. |
| V8 | low | **The identical-inputs dedupe silently discards the requested name, notes, tags and parent** (and a differing `plan_year` argument). The dedupe itself is per design; the silent metadata loss is the problem. | `src/owlplanner/library/store.py:258-261`, `240-243` | Surface the discarded fields in `SaveResult` so the step-3 dialog can tell the user. |
| V9 | low | **The two entry paths disagree for cases with no HFP workbook.** `scenario_from_ui` records zero-filled tables and exports `HFP.xlsx`; `import_case` yields `hfp = {}` and the `"None"` sentinel. The same case hashes differently through the two paths. `scenario_from_ui`'s "caller must sync the tables first" contract is also docstring-only. *(probe 6.)* | `src/owlplanner/library/casefiles.py:113-131` vs `191-210`, `247-257` | Normalize the no-workbook case across both paths (e.g. `import_case` takes the plan's zero tables too), and/or have `scenario_from_ui` call the sync itself. |
| V10 | low | **Import -> export does not preserve floats beyond 8 significant figures** (`save_toml`'s `_clean_float` truncates to `:.8g`). Inherited from Owl's own save path, but it bounds the "same case dictionary" claim; the synthetic cases cannot see it (clean literals). *(probe 2: ints and unknown sections round-trip exactly.)* | `src/owlplanner/config/toml_io.py:78-91`, `215-217`; `src/owlplanner/library/casefiles.py:259-262` | None needed in step 1; document the precision bound where the round-trip guarantee is claimed. |

## Checked and fine

- **Canonical JSON / S10** (`scenario.py:34-58`): sorted keys, compact separators, UTF-8,
  non-finite -> null, tuples -> lists, bool distinct from int; hash stable over key order and
  includes `BUILDER_VERSION` (tested).
- **run.json matches design section 5** (id, name, parent, created, notes, tags, plan year,
  inputs hash, change summary) and is written last (`store.py:273-293`); an exception mid-save
  cleans the folder (tested). A hard kill leaves a partial folder that `runs()` skips (the
  documented rule).
- **S4**: folder name fixed at creation, rename touches `run.json` only (tested); slugs are
  Windows-safe. Only an unbounded run-name length can blow MAX_PATH.
- **S5**: every read-modify-write of `run.json`/`library.json` holds `library.lock`
  (save/rename/delete); crash recovery via stale takeover works (tested).
- **Trash** (design section 10): `delete_run` moves to `trash/` with collision suffixes, clears
  `order`/`pins`, children keep their parent id (tested).
- **No `save_toml` path call** in the new code -- the `case_` rename trap is avoided (a StringIO
  is written verbatim to exactly `Case.toml`; tested).
- **Empty tables and missing house sheets** round-trip exactly (probe 9); a missing **person**
  sheet fails loudly (raw `ValueError`, `hfp_io.py:334-335` -- cosmetic inconsistency only).
- **Per-cell NaN/None/numpy round trips** through JSON and Excel are correct (tested). The gap is
  only case-dict values (V4).
- **Unknown case sections** survive import/export; TOML ints round-trip exactly (probe 2).
- **Budget sidecar, healthy branch**: written with the reference preserved, nested refs kept,
  absolute/`..` refs flattened and rewritten (tested; probe 5b).
- **Lineage / computed change summary** matches section 7; S3's draft/overwrite is untouched --
  step 1 is save-as only, no contradiction.
- Schema v1 holds only the case dict + HFP tables + the budget sidecar; `validate` rejects other
  `schema_version`s and `migrate` correctly refuses.

## Acceptance checks (design section 11, step 1)

| Check | Verdict | Evidence |
|---|---|---|
| unit tests | **met** | `tests/library/` -- 50 pass; flake8/ruff show only the upstream-known findings. |
| the synthetic cases import and export with the same case dictionary and HFP tables | **met** (caveats) | 39/39 (the reviewer ran it). Caveats: the comparison equalizes `HFP_file_name` (export necessarily rewrites the workbook reference to `HFP.xlsx`), and the synthetic floats are 8-sig-fig-clean, so the check cannot see V10. |
| an edited, never-solved case saves | **partially** | `test_casefiles.py:84-101` genuinely exercises `ui_to_config` + `saveContributions` with no solve (R6 honored). But the edit is a case-field only (table edits depend on the caller syncing first, V9), and a case with a named `budget_file` cannot save from the pages unless the file is in the CWD (V1). |

## Verdict

Step 1 is sound in its core: the storage design (folders, run.json-last, atomic writes,
save-as-only, lineage, trash, lock discipline, S4/S5/S10) is faithfully implemented, the
schema/hash machinery is clean and well tested, and the headline checks run green -- a good
foundation. But the save path has one outright bug class that should be fixed before step 2-3
code builds on it: the budget sidecar handling (V1, V2), plus three consistency holes: the
scenario stored is not the document the frozen files were generated from and the hash aliases
int/float and NaN/None (V3, V4), and import's date-dependent conditioning (V5) quietly undercuts
the "identical inputs" promise. The API shape holds together for what comes next (the `generate`
hook will carry `rates.csv`; `RunInfo`/`save_run`/`SaveResult` are enough for the run and library
pages; nothing needs reshaping), with two things to carry forward: `runs()` must degrade on a
damaged folder (V7), and the dedupe's discarded metadata (V8) needs a decision before the save
dialog is designed.

## Dispositions (2026-11-01, after the review)

All findings were acted on the same day (the user's call: fix V1-V7 now, V8-V10 with them where
cheap). 65 tests in `tests/library/` (15 new); the synthetic check stays 39/39; flake8 and ruff
clean on the changed files.

| # | Disposition |
|---|---|
| V1 | Fixed: `_resolve_ref` resolves explicit -> CWD -> `case_dir`; `scenario_from_ui` takes `case_dir=` / `budget_path=`, `import_case` passes the case file's folder; the error says which to pass. Tests `test_sidecar_resolves_against_the_case_dir`, `test_a_missing_budget_file_says_how_to_pass_it`. |
| V2 | Fixed: the sidecar is captured whenever the case names a `budget_file` (not only when `plan.budgetFromFile`), and `export_case` refuses to write a frozen pair whose case references a budget file the scenario does not carry. Test `test_export_refuses_a_dangling_budget_reference`. |
| V3 | Fixed: the scenario is normalized once (in `scenario_from_case` and again defensively in `save_run`) before hashing and generating, and `normalize` preserves int/float (the hash no longer aliases documents that generate different TOML). Design section 5 reworded. Tests `test_the_stored_scenario_is_the_generated_document`, `test_int_and_float_of_one_value_hash_differently`. |
| V4 | Fixed: `validate` rejects `None` values and non-finite floats anywhere in `case` with a key-path message (checked first: `load_toml` and `ui_to_config` emit neither on four example cases, so nothing legitimate is blocked). Tests `test_none_in_the_case_is_rejected`, `test_non_finite_in_the_case_is_rejected`. |
| V5 | Documented (design section 6.4, `casefiles` docstring); the conditioning year is pinned to the run's plan year with build step 2's `as_of` (S1/S7). Deferred by design: the pin needs the date mechanism. |
| V6 | Fixed: `generate` runs outside the lock into `runs/../.staging/<id>`, and the run is published under the lock with one rename (complete or not at all); `Library.open` drops stale staging folders; the lock retry loop is deadline-bounded. Tests `test_a_failed_generate_leaves_no_partial_run`, `test_open_clears_stale_staging`, `test_a_held_lock_raises`. |
| V7 | Fixed: `_info_from_dir` treats an unreadable `run.json` as a damaged run; `runs()` skips it, `damaged()` reports it. Test `test_a_damaged_run_json_does_not_break_the_library`. |
| V8 | Fixed: `SaveResult.dropped` reports the name, notes, tags, parent and plan_year the dedupe did not apply. Test `test_dedupe_reports_dropped_metadata`. |
| V9 | Fixed: with no workbook, `import_case` takes the plan's zero-filled tables through the same route `scenario_from_ui` uses, so both paths agree. Test `test_both_entry_paths_agree_without_a_workbook`. The sync contract of `scenario_from_ui` stays documented for the step-3 caller. |
| V10 | Documented (design section 6.4, `casefiles` docstring). No code change: the truncation is `save_toml`'s, Owl's own. |

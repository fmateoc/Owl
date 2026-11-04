# Run-library step 5b: second review (2026-11-04)

Second independent review of run-library build step 5b on `claude/run-library-step5b` at the
branch head `365b72c5` ("[fix] Run-library step 5b: the review's Z1-Z9 folded"), which folds the
first review's Z1-Z9 on top of the step's own commits `c99d3551` (the rates CSV and the `table`
rate method) and `44676043` (the acceptance check and the docs). Read against
`git diff 43fa1b13..365b72c5` (31 files) and `git show 365b72c5` (the fix fold), the design's
sections 5, 6.2, 6.3a, 6.4, 8.3, 11, 14.1 (I11), 15 (D11), the three PROGRESS entries ("Run-library
step 5b", "the independent review (Z1-Z9)", "Z1-Z9 folded"), and -- as history, re-checked
finding by finding in the current code, not assumed fixed -- `fork-notes/run-library-step5b-review.md`
and `fork-notes/run-library-step5b-handoff.md`. Findings **AA1-AA6** (1 medium, 3 low, 2 nit);
the prefix is `AA` because U, V, W, X, Y and Z all appear in earlier reviews' finding IDs
(`run-library-step1..step5b`).

The recorded decisions are given and judged only as implementations: a downturn sequence fills
only its window and the years outside keep the run's own rate method (baseline + overlay); the
pages get safety + Scenario rows only (no Rates-page table editor); one downturn event per run;
a hand-entered table and a downturn event refuse to coexist ("drop one"); and Z4's ruling -- a
window landing in no plan year (before the plan or entirely past its end) is refused, only a
window that starts inside the plan and runs past its end is silently truncated (documented).

Environment: Windows, Python 3.14.7 (`.venv\Scripts\python.exe`, editable install confirmed to
point at `C:\Projects\Owl\src` -- every probe prints `owlplanner.__file__`), HiGHS only.
**Nothing in the repository was changed except this file; every probe ran from
`C:\Users\fmate\AppData\Local\Temp\opencode\`** (`probe2_a_reread.py`, `probe2_b_determinism.py`,
`probe2_c_placement.py`, `probe2_d_hostile.py`, `probe2_d2_upload.py`, `probe2_e_hash.py`,
`probe2_f_import.py`, `probe2_g_pages.py`, `probe2_g2_hashdiff.py`, `probe2_h_nanwindow.py`,
`probe2_i_ratespage.py`) and wrote only to temp directories.

## What was run

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest tests\library tests\rate_models tests\config tests\ui -q -p no:cacheprovider -n 4` | **1225 passed, 1 skipped** (95 s) -- matches PROGRESS's claim exactly |
| `.venv\Scripts\python.exe -m pytest tests\rate_models\test_rate_model_table.py tests\library\test_rates_table.py --collect-only -q` | **63 tests collected** (29 + 34 as claimed) |
| `.venv\Scripts\python.exe fork-notes\synthetic\check_library_rates.py` | **11/11 step-5b checks pass** (four solves), incl. `owlcli run` reproducing the worker's `plan.json` for the downturn and hand-table runs, the window at its placement (`row 2030 = ['-9.03', '9.38', '16.66', '3.39']`), `record.json`'s `rates.method = 'table'`, T1 on the hand-table run, byte-identical `rates.csv` on re-export |
| `.venv\Scripts\python.exe -m flake8 src tests ui --max-line-length=120` | only upstream's known `stochastic` E301/E304 |
| `.venv\Scripts\python.exe -m ruff check src tests ui` | only the four known upstream B905s (`localsearch.py:244`, `tests/plan/test_local_search.py:288`, `tests/plan/test_roth_maturation_losses.py:49`, `ui/Run_Options.py:260`) |
| full suite | **not re-run** (the brief names the four targeted suites as the bar; the fix commit's record, 4115 passed / 2 skipped in 12:20, is taken on trust) |
| `probe2_a_reread.py` | Z1's fix verified on `apply_config_to_plan`/`setRates`/fallback/bad-content; **clone keeps stale rows (AA2)** |
| `probe2_b_determinism.py` | one table per export, two exports byte-identical, all four seed-less variants refused; **`build(rates_table=)` bypasses the refusals (AA3)** |
| `probe2_c_placement.py` | the placement matrix matches the Z4 ruling exactly (10 plain/anchor cases + through `build()`) |
| `probe2_d_hostile.py` / `probe2_d2_upload.py` | BOM, nan/inf/1e999, missing/blank `rates_file`, missing/duplicate years, empty file, short/bad rows all named on both paths; **a directory as `rates_file` and a stray rates upload (AA6)** |
| `probe2_e_hash.py` | window edits move only the downturn run's hash; no cache; hashing mutates nothing; a missing data file raises (recorded below) |
| `probe2_f_import.py` | the Import upload path and the no-base save verified; **`in_percent` lost on the no-base save (AA1)** |
| `probe2_g_pages.py` / `probe2_g2_hashdiff.py` | AppTest of `Rates.py`: read-only block, two visits, pages-save hash round trip (clean apart from real page edits) |
| `probe2_h_nanwindow.py` | a nan window freezes a `rates.csv` the run's own reader refuses (AA6) |
| `probe2_i_ratespage.py` | **a table case's Rates page hides the fiscal assumptions (AA4)** |

## Findings

| # | Severity | What and why | Evidence | Code location | Recommendation |
|---|---|---|---|---|---|
| AA1 | **medium** | **A no-base "Save the current case" of a table case drops `in_percent` and silently re-scales the frozen run's rates 100x.** `ui_to_config`'s `table` branch returns early and carries only `rates_file`, so the saved case loses `in_percent` (and `reproducible_rates`/`rate_seed`) while `_rates_table_from_plan` stores the plan's **raw** rows (decimals for an `in_percent = false` case). The frozen `Case.toml` then reads those decimal rows as percent (`in_percent` defaults true) and divides by 100 again: the solve runs on rates 100x smaller than the session's plan. `in_percent` is a documented parameter (`info/PARAMETERS.md:216`). The with-base save is safe (`_apply_page_edits` keeps keys neither side mentions). | `probe2_f_import.py` `(f3)`: plan reads `2030 rate = -0.3` (in_percent=false); `saved case's rates_selection: {... 'method': 'table', ... 'rates_file': 'rates.csv'}` (in_percent gone); `saved table row 2030: [2030, -0.3, 0.02, 0.01, 0.02]` (raw decimals); `the frozen run's plan 2030: -0.003 (what the solve would use)`; `FROZEN RUN DRIFTED: True`. Contrast `(f2)`/`(f4)`: the percent-default flows round-trip to the same hash. | `src/owlplanner/config/ui_bridge.py:790-794` (`_ui_rates_to_config`'s early return), `src/owlplanner/library/casefiles.py:493-495` + `:514-528` (`_rates_table_from_plan`) | Carry the units on the no-base path: take `in_percent` from `plan.rateModel.params` in `scenario_from_ui` when there is no base (or add an `inPercent` case key as `ratesFile` has), or normalize the stored rows to percent and drop the key. A test: the (f3) scenario, asserting the frozen plan's rate equals the session plan's. |
| AA2 | **low** | **`clone(plan, expectancy=...)` never re-reads the file, and its comment says it does.** The fix commit made `Plan.setRates` try the file first, but clone passes `rates_rows=<the source plan's rows>` unconditionally, so `"rows" in model_config` skips the file-first branch entirely: the clone keeps the rows the source plan last read even when the file has changed. The comment promises the opposite ("is re-read beside the case file, or taken from the rows the source plan already holds **when its file cannot be found**"), and `plan.py`'s new comment says "the file is tried first at **every** `setRates`" -- both false for this path. Reach is narrow (`clone`'s `expectancy=` path is `stresstests.py`'s MC ensembles and the assistant's probes; the solve itself re-applies config first, `owlbridge.prepareRun` -> `apply_config_to_plan`), but it is the same stale-rows class Z1 closed, on the one seam that bypasses the fix. | `probe2_a_reread.py` `(a5)`: `source plan: 2027 rate = -0.55`; after editing the file to -77.0, `clone after the edit: 2027 rate = -0.55 (file now says -0.77)` vs `fresh plan contrast: 2027 rate = -0.77`; `CLONE SEES STALE ROWS: True`. (a1)-(a4) confirm the fixed main path: re-read on re-apply and on `setRates`, fallback when the file is gone, named `FileNotFoundError` for another name, a readable-but-bad file raises rather than swapping. | `src/owlplanner/config/plan_bridge.py:679-688` (the comment and the unconditional `rates_rows=`), `src/owlplanner/plan.py:1822-1839` | In `clone`, pass `rates_rows` only when the file cannot be read (e.g. `try_read_rates_csv` first), matching its own comment; or widen the comment to "clone copies the source plan's rows" and drop "at every `setRates`" from `plan.py`. |
| AA3 | **low** | **`build(scenario, rates_table=...)` trusts the caller completely: every rates-table refusal lives only in `rates_table()`.** A caller-supplied table skips `_rates_table` and with it the "drop one" rule (recorded decision 4), the "a sequence over a `table` case is refused" rule, and the Z4 placement refusals -- and a supplied `None` for a downturn scenario would silently generate **no** table at all (the run's case keeps its own method and the stress is never applied). Today every real caller is safe (`export_case` computes via `rates_table()`, which refuses; `ui/Scenario.py`, `scenario_from_ui`'s `build(base)`, `check_library_builder.py` pass nothing), but the fix commit created the seam while moving the invariant out of `build`. | `probe2_b_determinism.py` `(b5)`: `hand + downturn via rates_table(): refused -> the run has both a hand-entered rates table and a ...` but `same doc via build(rates_table=): NOT refused; case method = table \| provenance: {'rates_selection.method': 's', ...}` -- the generated case is built and marked as if the event generated the table. | `src/owlplanner/library/builder.py:646-665` (`_TABLE_UNSET`, `table = _rates_table(...) if rates_table is _TABLE_UNSET else rates_table`) | Run the consistency refusals (hand+downturn, table-case+downturn) inside `build` regardless of the keyword, or have `build` assert `rates_table == _rates_table(scenario)` when one is passed; at minimum state the contract in the docstring. |
| AA4 | **low** | **A table case's Rates page hides every non-method section: the heirs' tax rate, the OBBBA expiration year, the dividend rate and the two liquidation rates are unreachable in the pages -- and a table case is every downturn run's generated case.** The read-only block ends in `st.stop()`, so the "Income taxes", "Other Rates", "Liquid balance sheet" and "Rate sequence" sections below never render; those five assumption widgets exist on no other page. The recorded decision ("safety + Scenario rows, no table editor") covers the rate table itself; hiding the fiscal assumptions is collateral of the `st.stop()`. A pages save still keeps the case's values, so nothing is lost silently -- the user simply cannot edit them from the app for any table/downturn run. | `probe2_i_ratespage.py`: a table case renders only `['#### :orange[Rates from a Table]']` with `number inputs: []`; a normal case renders 12 sections incl. `Income taxes`, `Other Rates`, `Liquid balance sheet` with `['Heirs marginal tax rate (%)', 'OBBBA expiration year', 'Dividend rate (%)', 'Liquidation tax rate (%)', 'Liquidation cap-gains rate (%)', ...]`; `(i3)` lists the five unreachable widgets. Grep: `heirsTx`/`yOBBBA`/`divRate`/`liquidationTx`/`liquidationCG` occur only in `ui/Rates.py:583-621`. | `ui/Rates.py:106-130` (the table branch's `st.stop()`), `:577-623` (the hidden Advanced options) | Move the `st.stop()` after the Advanced options (the read-only block replaces only the method selectors), or move the fiscal assumptions to a page that stays reachable; if the freeze is deliberate, say so in the caption and the docs. |
| AA5 | nit | **The "one table per export" test does not pin what its docstring claims, and `build` carries two name shadows.** `test_z2_one_export_computes_one_table` spies only `builder.rates_table`; a regression where `export_case` calls `rates_table()` **and** `build` recomputes via `_rates_table` (the pre-fix shape) still passes -- the spy never sees `_rates_table`, and the written-vs-computed comparison uses the export's own call. (With Z2's seed guard every exportable case is deterministic or seeded, so the two computations would agree anyway -- the guard, not this test, is what makes the frozen file safe.) In `build`, the `rates_table=` parameter shadows the module function (the code routes around it via `_rates_table`, but a future `rates_table(scenario)` call inside `build` would call the parameter), and `for table in HOUSE_TABLES` (`builder.py:827`) shadows the local rates-table `table` from line 665. | Read: `tests/library/test_rates_table.py:333-352` vs `src/owlplanner/library/builder.py:665, 827`. `probe2_b_determinism.py` `(b1)` instruments both names: one public call per export (the delegation to `_rates_table` is what the second spy sees). | `tests/library/test_rates_table.py:333-352`, `src/owlplanner/library/builder.py:646-665, 827` | Spy `builder._rates_table` too (or compare the workbook's gamma against the written file); rename the local at line 827 (`for sheet in HOUSE_TABLES`) and/or the keyword (`table=`), or note the shadow in a comment. |
| AA6 | nit | **Hostile-input leftovers around the fixed reader.** (a) A directory named as `rates_file` passes `os.path.exists` and fails as a bare `PermissionError [Errno 13]` (Windows) instead of a named message. (b) A rates CSV uploaded on the Import tab for a case that reads no table refuses the **whole import** with the schema-level "the scenario holds a rate table but the case's rates_selection.method is 'historical'" -- the uploader is advertised "(optional)". (c) `load_sequences` accepts non-finite window values (`float('nan')` passes), so a hand-edited `downturn_sequences.toml` exports a `rates.csv` the run's own reader then refuses: `save_run` succeeds and the frozen run is unsolvable (loud at solve, but runs are immutable). Z6's finite check went to `read_rates_csv`; the sequences reader got none. | `probe2_d_hostile.py` `(d23)`: `PermissionError: [Errno 13] Permission denied: ...` (also `probe2_a_reread.py` `(a6)`); `probe2_d2_upload.py` `(d22)`/`(d22b)`: the schema message for a `'historical'`/`'user'` case + `rates_path=`; `probe2_h_nanwindow.py`: `(h1) load_sequences accepts a nan window: [[nan, 2.0, 1.0, 2.0]]`, `(h2) export froze row 2030 as: ['2030,nan,2.0,1.0,2.0']`, `(h3)`/`(h4)` re-import and plan load both refuse with the Z6 error. | `src/owlplanner/rate_models/table.py:84-94` (`resolve_rates_csv`'s `os.path.exists`), `src/owlplanner/library/casefiles.py:755-768` (`_read_rates_table` with `explicit` on a non-table case), `src/owlplanner/library/sequences.py:50-53` | `os.path.isfile` in `resolve_rates_csv`; ignore (or name) a rates upload when the case reads no table; reject non-finite window values in `load_sequences` with the same "row/column is not a finite number" wording as Z6's. |

## Claims checked (verified, worth recording)

- **The nine fixes are in and each behaves as the Z1-Z9 entry records** (verified with fresh
  probes, not the first review's): Z1's file-first re-read and fallback (`probe2_a_reread.py`
  (a1)-(a4); the solve path re-applies config first -- `owlbridge.prepareRun` ->
  `apply_config_to_plan` -- so a solve sees an edited file, read); Z2's case-level seed guard
  refuses all four seed-less shapes (reproducible-without-seed, nothing, seed-without-reproducible,
  reproducible-False-with-seed) and accepts `rate_seed = 0`, the rent/X3 path included, and one
  export computes and writes one table (`probe2_b_determinism.py`); Z3's two workflows work
  (`probe2_f_import.py` (f1): the uploaded CSV feeds import even not beside the case -- and wins
  over a beside-case file of the same name; (f2): the no-base save stores the plan's rows and
  exports/re-imports to the same hash; `probe2_g_pages.py` (g1): the caption names the Import
  route); Z4's refusals match the user's ruling case for case (`probe2_c_placement.py`: 2020,
  2024 (3y and 10y windows), 2023, 2071, 2075 and `age:Jack:60` refused with the placement and
  the plan window named; 2070, 2069 and 2068 truncate silently as documented; `build()` refuses
  the same placements and `ui/Scenario.py:358-367` surfaces the refusal as "Not buildable yet");
  Z5/Z6 name every hostile input on both paths (`probe2_d_hostile.py`); Z7's window term moves
  only downturn runs' hashes and `sequences()` has no cache (`probe2_e_hash.py`); Z8/Z9 are
  wording/comment fixes, present as recorded (read + the check reruns 11/11).
- **The acceptance check reproduces at 11/11** (verified by running it): including `owlcli run`
  from another working directory reproducing the worker's `plan.json` for both runs, the window
  at its placement with the baseline outside it, and byte-identical `rates.csv` on re-export.
  The Z8 scoping in the check's docstring and the PROGRESS bullet matches the code (T1 is the
  hand-table run's; `summary.json` is checked for its metrics, not compared).
- **One table per export end to end** (verified): `store.save_run`'s `generate` default is
  `export_case` (store.py:424-445), so every saved run goes through the fixed single-computation
  path; `ui/Scenario.py:363`, `scenario_from_ui`'s `build(base)` and `check_library_builder.py`
  call `build()` without the keyword and compute once internally. No caller was missed.
- **The pages keep a table case intact on a real render** (verified, `probe2_g_pages.py`): the
  read-only block appears, `rateType`/`plan.rateMethod`/the rates survive two visits and
  `ui_to_config` still writes `method = "table"` + `rates_file`; a pages save round-trips to the
  base's hash and table -- `probe2_g2_hashdiff.py` shows the only field a save can move is one
  the pages really edited (my probe's own `case_name` rename; the unit test
  `test_a_pages_save_keeps_the_table` pins the unrenamed case).
- **The selector-reset hazard is latent but real** (verified): a Rates visit with no `rateType`
  key still rewrites a table plan to `historical_average` (`probe2_g_pages.py` (g5)). All four
  case-dict creators set the key (read: `sskeys.createCaseFromFile`/`openCaseFromPlan` ->
  `owlbridge.genDic`, `createNewCase` -> `config_to_ui`, `copyCase` deepcopies an existing dict),
  so the trigger remains a hand-injected dict (tests, future code); no defense in depth was added.
- **`scenario_hash`'s shape** (verified, `probe2_e_hash.py`): window edits and window length
  changes move the downturn run's hash only, hashing mutates nothing, and a plain run neither
  changes hash nor touches the data file. Two recorded behaviors worth keeping in view: a
  missing/broken `downturn_sequences.toml` makes `scenario_hash` of a downturn run **raise**
  `SequenceError` (loud and arguably right -- the input is missing; (e5)), and the Z7 formula
  change rode without a `BUILDER_VERSION` bump, so a downturn run saved before the fix loses
  dedupe identity with an identical save after it (nothing recomputes stored hashes -- read
  `store.find_by_hash`, `worker._inputs_hash` -- so nothing breaks; PROGRESS records the hash
  change "for downturn runs only").
- **The worker/`owlcli` paths read the frozen file fresh** (verified by read + the check):
  `worker.py:199-220` builds with `config_to_plan(..., dirname=inputs/)` and no `rates_rows`;
  the acceptance's two `owlcli run` comparisons pass.
- **Test and lint claims** (verified): 63 tests collected in the two files (29 + 34); the four
  suites 1225 passed / 1 skipped; flake8 and ruff show only the upstream items CLAUDE.md lists.
  The new tests pin what they claim apart from AA5, and my probes independently reproduce every
  behavior they assert (Z1's twin, the Z2 trio, Z3's pair, Z4's trio, Z6's four, Z7's pair).
- **Docs track the code** (verified by reading): the Z1 wording fixes in PROGRESS/CHANGELOG/CLAUDE,
  section 5's window-in-the-hash paragraph, Z8's scoped acceptance bullet, Z9's "(3, with events
  and the rates table)", and `info/PARAMETERS.md`/`RATE_MODELS.md`'s `table` entries all match
  the implementation.

## Unverified / to check

- The full suite (4115 passed / 2 skipped) was **not** re-run; the four targeted suites are the
  bar per the brief and are green at exactly PROGRESS's count.
- The fix commit's "20 of the 21 new tests were checked to fail before their fix" is taken on
  trust (the repo is read-only here, so the stashed-src rerun was not repeated). Every behavior
  those tests assert was independently reproduced by my probes, and the pre-fix code visibly
  lacks each fix in `git show 365b72c5`.
- What a solve does with `nan` rates (the first review's open item): the CSV route is now closed
  at the reader (Z6), and the sequences route fails loudly at solve (`probe2_h_nanwindow.py`);
  a `user`/`dataframe` case with non-finite `values` in the case file itself was not probed.
- Whether AA2's stale rows can bite inside a live flow (the solve re-applies config first; the
  window is "the file changes between a plan's last rates application and a clone mid-run") --
  read, not exercised.
- A year boundary in anger (a run exported Dec 31, solved Jan 1): `check_plan_year` refuses it by
  design; not exercised.

## What the step gets right

The step delivers its contract cleanly and the Z1-Z9 fold is surgical: each fix sits at the
narrowest point that enforces it (the case-level seed guard, the single table computation at
export, the placement refusals where the plan's years are known, the finite/BOM checks in the one
reader both paths share), and the recorded decisions are implemented exactly -- the overlay fills
only its window on the run's own rate path, one event per run, the "drop one" refusal, no table
editor. The frozen-files story is real: the acceptance check's `owlcli run` reproduces the
worker's solve for a generated and a hand table alike, and the pages keep a table case intact on
a real render. The 63 tests are pointed and my independent probes reproduce every claim they
pin; the docs track the code closely.

## Verdict

Ready for step 6 (collections / variant grids) to build on: the table, the overlay, the hash and
the export machinery do what the design says and the Z1-Z9 fold closed the two medium holes.
Fix AA1 (the `in_percent` loss on the no-base save) before a variant grid freezes such a run --
it is the one finding that silently changes results -- and pick up AA2/AA3 as comment-and-seam
hygiene while the step is hot; AA4 is a product call about the Rates page, not a blocker.

## Dispositions (2026-11-04, the user's call: fix AA1-AA3)

- **AA1 folded:** `in_percent` rides with `ratesFile` through `config_to_ui`, `genDic` and
  `_ui_rates_to_config` (the root: every solve re-applies the rates from the case keys, so the
  loss drifted the session plan too), and `scenario_from_ui` takes the units from
  `plan.rateModel.params` when there is no base. Tests:
  `test_aa1_a_no_base_save_keeps_the_table_units` (the (f3) scenario end to end) and
  `test_aa1_the_pages_round_trip_keeps_the_table_units`.
- **AA2 folded:** `clone` tries `try_read_rates_csv` first and keeps the source rows only when
  the file cannot be resolved or read; `plan.py`'s comment names the rows-carrying callers.
  Tests: `test_a_clone_re_reads_a_changed_file` (checked to fail before) and
  `test_a_clone_with_no_file_keeps_the_source_rows` (the preserved fallback).
- **AA3 folded:** the two consistency rules moved to `_check_table_events`, enforced in `build`
  however the table arrives, plus a named refusal for `rates_table=None` on a downturn run.
  Tests: `test_aa3_build_enforces_the_refusals_however_it_gets_the_table`,
  `test_aa3_build_refuses_no_table_for_a_downturn_run`.
- **AA4-AA6 not folded** (this round's call was AA1-AA3): AA4 is a product call (where the
  Rates page's `st.stop()` belongs); AA5 and AA6 stand as written.

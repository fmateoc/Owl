# Handoff: fold run-library step 5b's review findings Z1-Z9 (2026-11-04)

For the **next session**. The user's call on `fork-notes/run-library-step5b-review.md`:
**fold all nine findings (Z1-Z9)**. This note is the work order; the review holds the evidence
(each finding names the probe that reproduces it, under `C:\Users\fmate\AppData\Local\Temp\opencode\`
on this machine). Nothing of it is folded yet.

## Where things stand

- Branch `claude/run-library-step5b` at the handoff commit (review + this note on top of
  `44676043`). `main` is at `43fa1b13` (run-library step 5); do **not** fast-forward it before
  the fixes are folded and checked (the user decides the fast-forward).
- What step 5b built: `method = "table"` (`src/owlplanner/rate_models/table.py`, a year-keyed
  rates CSV beside the case file), the scenario's `rates_table` (schema v3, `BUILDER_VERSION` 4),
  the `downturn` event + `data/downturn_sequences.toml` (baseline + overlay at a placement), the
  pages' read-only handling (`config/ui_bridge.py`, `ui/{Rates,Scenario,owlbridge}.py`), the
  acceptance `fork-notes/synthetic/check_library_rates.py` (11/11). PROGRESS.md "Run-library
  step 5b" and `fork-notes/CHANGELOG-fork.md` describe it; the design amendments are in
  `run-library-design.md` sections 5, 6.2, 6.3a.
- Full suite before the fixes: **4094 passed / 2 skipped** (Windows, `-n 4`, 9:40).

## Setup (this machine: Windows; CLAUDE.md's Linux commands map like this)

- Python: `.venv\Scripts\python.exe` (3.14.7; the editable install points at
  `C:\Projects\Owl\src` — print `owlplanner.__file__` in a probe when it matters).
- Targeted tests: `.venv\Scripts\python.exe -m pytest tests\library tests\rate_models tests\config tests\ui -q -p no:cacheprovider -n 4`.
- Full suite: `.venv\Scripts\python.exe -m pytest -n 4 -q -p no:cacheprovider` (about 10 min).
- Lint: `... -m flake8 src tests ui --max-line-length=120` and `... -m ruff check src tests ui`
  (upstream's known items only, CLAUDE.md "Lint").
- The acceptance: `.venv\Scripts\python.exe fork-notes\synthetic\check_library_rates.py`
  (about 8 min; four solves). Expected before the fixes: 11/11; it must still be 11/11 after,
  with the wording fixes of Z8.
- HiGHS only (no MOSEK license). Never `pkill`; never `python -I`. Probes go to
  `C:\Users\fmate\AppData\Local\Temp\opencode\`, read-only with respect to the repo.

## The fixes (in a sensible order; each with its verification)

**Z2 first** (it touches what Z1 and Z7 sit on): `reproducible_rates = true` without
`rate_seed` must not pass `_throwaway_plan`'s determinism guard, and one export must use one
table.
- `library/builder.py` `_throwaway_plan` (the guard near line 531): the case must fix its seed.
  The plan cannot tell a minted seed from a fixed one (`setReproducible(True, None)` mints
  one), so check the **case**: refuse when the method is stochastic and
  (`not reproducible_rates` OR `rates_selection.rate_seed` is absent). Make the message say
  exactly that. Keep the deterministic-method path as is.
- One table per export: `casefiles.export_case` currently computes `rates_table` again after
  `build()` already did (two throwaway plans, two draws). Give `builder.build` an optional
  `rates_table=` keyword (or return it), and have `export_case` compute the table once and
  pass it in. `build()`'s three-value return stays (its callers unpack three).
- Tests (`tests/library/test_rates_table.py`): with a seeded stochastic baseline two exports
  write byte-identical `rates.csv`; with `reproducible_rates` and **no** `rate_seed` the build
  is refused with the named message (the case: `rates_selection.method = "histochastic"` style,
  as `tests/library/test_builder.py`'s `TestSecondReviewFixes._histochastic` does).
- Check probe `probe_review_z2.py` reruns clean after the fix.

**Z1**: a changed `rates.csv` must be re-read.
- `plan.py` `setRates`'s table hunk (lines ~1822-1832): try the file first; reuse `old.rows`
  **only** when the file cannot be resolved/read (that is the interface's path, the budget
  file's precedent). Fix the comment ("cannot re-read" is the only fallback case) and the
  PROGRESS wording that says otherwise.
- Tests: `test_a_plan_that_cannot_re_read_the_file_reuses_its_rows` must still pass; add its
  twin — the file changed on disk, `plan.setRates` again (or `apply_config_to_plan`) sees the
  new value (`probe_review_z1.py`'s scenario).

**Z7**: the sequence window must be part of the inputs identity.
- The agreed variant: `library/scenario.py`'s `scenario_hash` folds in a hash of the **named
  sequences the scenario's downturn events use** (name + window), only when such an event
  exists — runs without a downturn keep their hash. Lazy-import `library.sequences`.
- Drop `functools.lru_cache` from `sequences.load_sequences` (the file is tiny; a live server
  must see edits).
- Document the choice in the design's section 5 (the windows are builder input, in the hash),
  and note in PROGRESS that this changes the hash of downturn runs only.
- Tests: editing the window changes the hash of a downturn scenario and not of a plain one;
  `sequences()` sees an edited file without a restart (pass `path=`).

**Z4**: a placement that misses the plan must not look applied.
- `builder.rates_table`'s overlay (near line 607): when **no** window year lands in the plan's
  years, raise `ScenarioError` naming the placement and the plan window; when the window starts
  before the plan (a left-truncated window), raise too (the placement is wrong). Running past
  the plan's end stays "simply not used" (documented).
- Tests from `probe_review_z4.py`: placements 2020 and `age:Jack:60` (before the plan) raise;
  2069/2075 (past the end) truncate as documented; 2024 (a 3-year window starting before the
  plan) raises.

**Z5**: `method = "table"` with no `rates_file` gets a named error.
- `rate_models/table.py` `from_config`: raise `ValueError("rate method 'table' needs a
  'rates_file' ...")` when the section has none (blank counts as none). (`required_parameters`
  already declares it for the model itself.)
- Test: `config_to_plan` on such a case raises that message (not `KeyError`).

**Z6**: hostile CSV input.
- `rate_models/table.py` `read_rates_csv`: open with `encoding="utf-8-sig"` (Excel's "CSV
  UTF-8" writes a BOM); reject non-finite values (`nan`, `inf`, `1e999`) naming the row and
  cell — this fixes both the plain plan path and the library's confusing "not a number: None".
- Tests: a BOM file reads; a `nan`/`inf` cell raises with the row named;
  `import_case` of such a CSV raises the same named error.

**Z3**: the two workflows the pages' own text recommends.
- `ui/Library.py` (the import tab, near the budget uploader ~lines 144-148): add a rates-file
  uploader, passed as `rates_path=` to `import_case`.
- `library/casefiles.py` `scenario_from_ui`: with **no base** and a plan that holds a table
  (`plan.rateModel` of model `table`), take `rates_table` from its rows
  (`{"columns": RATE_TABLE_COLUMNS, "rows": ...}`) instead of refusing — the plan holds the
  table in memory exactly as it holds the budget lines' precedent. Keep the refusal when the
  plan holds no table.
- `ui/Rates.py` caption: name only what the pages can actually do after this fix.
- Tests: a no-base `scenario_from_ui` of a table plan stores the table and saves; the Import
  uploader path (AppTest or the `import_case(rates_path=)` test) works.

**Z8**: the acceptance record must not overstate.
- PROGRESS.md's acceptance bullet: scope the T1 claim to the hand-table run (a downturn run's
  re-import is a hand-table scenario **by design** — every re-import drops events, since step
  4), and say the plan comparison includes the summary metrics *inside `plan.json`*.
- `check_library_rates.py` docstring: drop the "and the run's `summary.json` metrics" phrase
  (or state that `plan.json`'s `summary` block is what is compared). Keep the existence check
  or fold it into the wording.
- Rerun the check: 11/11.

**Z9**: `library/casefiles.py:172`'s comment "(2, with events)" -> "(3, with events and the
rates table)" or point at `SCHEMA_VERSION`.

## After the fixes

1. Targeted suites green, then the full suite (record the new count: expect 4094 + the new
   tests), lint clean but for upstream's known items.
2. `check_library_rates.py`: 11/11.
3. Docs: a "review folded" bullet in the changelog's step-5b entry (like step 5's "Second
   review, Y1-Y4" bullet); PROGRESS.md entry "Run-library step 5b: Z1-Z9 folded" listing the
   dispositions and the test delta (the fork's pattern: say which tests were checked to fail
   before the fix); CLAUDE.md's state bullet extended ("reviewed: `run-library-step5b-review.md`
   Z1-Z9, all folded") and its test-count line.
4. Commits: `[fix] Run-library step 5b: the review's Z1-Z9 folded` (code + tests), and docs
   where they ride along (the fork has folded docs into the fix commit; either is fine, no
   `[no ci]` while code changes).
5. Then report to the user; `main` fast-forward is their call.

## Optional (the review's "unverified / to check", not part of the nine)

- What a solve does with `nan` rates (Z6's downstream) — the fix does not depend on it.
- Whether any path builds page case keys without `config_to_ui`/`genDic` (the selector-reset
  hazard of step 5's W6 neighborhood) — defense in depth is open.
- A year boundary in anger (a run exported Dec 31, solved Jan 1) — `check_plan_year` refuses
  it by design; not exercised.

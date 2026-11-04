# Run-library step 5b: third review (2026-11-04)

Third independent review of run-library build step 5b on `claude/run-library-step5b` at the
branch head `3b15dd97` ("review 2's AA1-AA3 folded"), read against `git diff 43fa1b13..3b15dd97`
(32 files) with the first two reviews (`run-library-step5b-review.md` Z1-Z9,
`run-library-step5b-review-2.md` AA1-AA6) and the handoff as history. Findings **AB1-AB4**
(1 medium, 2 low, 1 nit); prefix AB because AA is taken. None of them repeats a Z or AA item;
AB3 revisits a point the first review recorded as "not a finding" (see there).

Environment: Linux container, Python 3.11 (`uv sync --python 3.11`), HiGHS only. Every probe
printed `owlplanner.__file__` = `/home/user/Owl/src/owlplanner/__init__.py` and ran from the
session's scratchpad, writing only to temp directories. **Nothing in `src/`, `ui/` or `tests/`
was changed.**

## What was run

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest tests/library tests/rate_models tests/config tests/ui -q -p no:cacheprovider -n 4` | **1232 passed** (48 s; Windows recorded 1231 passed / 1 skipped -- the platform-specific skip) |
| `fork-notes/synthetic/make_cases.py`, then `check_library_rates.py` | **11/11** step-5b checks pass |
| `flake8 src tests ui --max-line-length=120` / `ruff check src tests ui` | only upstream's known items (the `stochastic` E301/E304; four B905s) |
| full suite | **not run** (PROGRESS records 4121 passed / 2 skipped on Windows at this head) |
| probes (below) | AB1-AB4 reproduced |

## Findings

### AB1 (medium): a downturn run applies the hand case's `reverse_sequence` / `roll_sequence` twice

`_generated_rates` writes `rates.csv` from the throwaway plan's `tau_kn`, which `Plan.setRates`
has **already** reversed or rolled (`plan.py`, `rates.apply_rate_sequence_transform`, applied
to every non-constant model). `build` then sets only `rates_selection.method` and `rates_file`
on the generated case, so the frozen `Case.toml` keeps `reverse_sequence = true` /
`roll_sequence = N`. `TableRateModel` is `constant = False`, so every load of the frozen run
(`worker`, `owlcli run`) transforms the table a second time. The `rates.csv` is right; the
solve's rates are not.

Probe (`examples/Case_jack+jill.toml`, `historical` 1969-2001, a `crash-30` downturn at 2030;
frozen `Case.toml` loaded as the worker loads it):

```
{'reverse_sequence': True} frozen rates_selection: {'method': 'table', 'reverse_sequence': True, 'rates_file': 'rates.csv'}
  base S&P y0..y0+5: [-11.85, -9.03, 20.89, 28.34, 33.1, 22.68]
  run  S&P y0..y0+5: [-8.24, 3.56, 14.22, 18.76, -14.31, -25.9]
  crash at 2030 in run? False
  years outside the window that differ from the baseline: 31 of 32
rates.csv row 2030: ['2030,-30.0,2.0,1.0,2.0']
years the solve sees -30.0: [2054]
{'roll_sequence': 5} ...
  crash at 2030 in run? False
  years outside the window that differ from the baseline: 32 of 32
{} ...
  crash at 2030 in run? True
  years outside the window that differ from the baseline: 0 of 32
```

So with either option the downturn lands in the wrong year (2054 for the reversed case) and
every other year leaves the parent's path, silently: the Compare page would attribute the whole
difference to "the downturn". `build`'s `_gamma(case, rates_rows=...)` reads the same
re-transformed table, so the purchase price and rent rows are priced on it too (consistent with
the solve, wrong against the intent). The acceptance check cannot see it (its baseline is
constant and its case has neither option), and the unit tests stub `_throwaway_plan`.

A hand-table run is **not** affected: the scenario stores the file's raw rows and the frozen
case re-applies the same transform the imported case applied (consistent by construction).

Location: `src/owlplanner/library/builder.py` `build` (the `if table is not None:` block that
sets `method` / `rates_file`) and `_generated_rates`.

Recommendation: when a downturn generates the table, also write `reverse_sequence = false` and
`roll_sequence = 0` into the generated case and mark both with the event in
`provenance["case_fields"]` (so `_drop_generated_case` puts the hand values back on a pages
save), and compute `gamma` after that. Test: a `historical` hand case with `reverse_sequence`
(and one with `roll_sequence`) plus a downturn; the frozen plan's `tau_kn` equals the parent's
outside the window and holds the window at its placement.

### AB2 (low): the Rates page's `_setRates` drops `in_percent` (and reverse/roll) for a table case

AA1's fold made the units ride through `config_to_ui`, `genDic` and `_ui_rates_to_config`, but
`ui/owlbridge.py` `_setRates`'s table branch still calls
`plan.setRates("table", rates_file=...)` with neither `in_percent` (key `inPercent`) nor
`reverse` / `roll`. The Rates page runs it once per case (`kz.runOncePerCase(initRates)` ->
`owb.setRates()`), so a decimal table (`in_percent = false`) is re-priced 100x smaller in the
session plan, and the read-only table on the same page shows it that way.

Probe, call level (decimal rows `0.06, 0.045, 0.03, 0.025`, `in_percent = false`):

```
after load:     S&P 0.06 gamma[-1] 2.2588508612171205
after _setRates: S&P 0.0006 gamma[-1] 1.0082830854100784 params in_percent: True
```

Probe, page level (`AppTest` of `ui/Rates.py`, case keys from `config_to_ui`, which carry
`inPercent = False`):

```
ui keys: rateType table inPercent False
exceptions: []
errors: []
shown first row: [2026.0, 0.06, 0.045, 0.03, 0.025]      # a 6% stock year shown as 0.06 (%)
session plan after the visit: S&P 0.0006 gamma[-1] 1.0083
```

Reach (read, not exercised): a solve re-applies the case keys first (`prepareRun` ->
`apply_config_to_plan`, which carries `in_percent` since AA1), and the no-base save reads the
units from the case keys and the raw `model.rows`, so neither a solve nor a saved run drifts.
What is wrong is the page's own table and whatever reads the session plan between a Rates visit
and the next solve (for instance `owlbridge`'s fixed-assets bequest value, which reads
`gamma_n`). The same branch drops `reverse_sequence` / `roll_sequence`, so a reversed hand table
is shown unreversed until the next solve. CLAUDE.md's state line ("`config_to_ui`/`ui_to_config`/
`genDic`/`_setRates` carry `method = "table"`") is true of the method, not of the units.

Location: `ui/owlbridge.py` `_setRates` (the `if rateType == "table":` block).

Recommendation: pass `in_percent=kz.getCaseKey("inPercent") is not False` and the case's
`reverse_sequence` / `roll_sequence`, as `_setRates`'s varying branch passes them (verified,
`owlbridge.py:1028-1033`); a test on the AppTest above (the shown row and the session plan's rate after a
visit).

### AB3 (low): a `rates.csv` in the working directory replaces a frozen run's own table

`resolve_rates_csv` tries the name relative to the **working directory** before the case's
directory. Every library run names its table `rates.csv`, the worker inherits the server's
working directory (`jobs._spawn`'s `Popen` sets no `cwd`; the launcher runs streamlit from where
it is started), and `owlcli run` uses the shell's. So any file called `rates.csv` there wins over
`inputs/rates.csv`, silently, and the frozen run no longer reproduces (R13).

Probe (a downturn run's frozen inputs, loaded as the worker loads them, from a directory holding
a `rates.csv` of 99% stock years):

```
S&P 2030 the run should use: -30.0; read: 99.0
```

The first review saw the order and called it "not a finding" because it matches the HFP
workbook (`plan_bridge.py:398-401`, upstream's) and the budget sidecar. I would keep it as a
finding for the `table` method: the code is the fork's own, the generated name is fixed and
generic (Owl's own history file is also called `rates.csv`), and the whole point of the method
is that one frozen file reproduces a run everywhere. The library's generated `HFP.xlsx` has the
same CWD-first shadowing since step 1 (upstream's order, not part of this step).

Location: `src/owlplanner/rate_models/table.py` `resolve_rates_csv`.

Recommendation: for a relative name with a `base_dir`, try beside the case first and fall back
to the working directory (or refuse the ambiguity when both exist); document the order in
`RATE_MODELS.md` / PARAMETERS. Whether to change `HFP.xlsx` too is an upstream question.

### AB4 (nit): Create Case cannot open a table case from an upload

The Create Case page's file upload (`owlbridge.createCaseFromFile`: `load_toml(StringIO)`, so
`dirname = ''`) cannot resolve `rates.csv`, and there is no rates uploader on that path (the HFP
has its own on the Financial Profile page):

```
dirname from an upload: ''
refused: FileNotFoundError Rates table 'rates.csv' not found.
```

The page shows "Failed to parse case file: Rates table 'rates.csv' not found." for a run's
downloaded `Case.toml` ("Download everything" carries `rates.csv` beside it). The Library's
Import (which has the uploader since Z3) is the working route, and the Rates page's caption
names it, but nothing tells the Create Case user. Recommendation: say so in the error (point to
the Library's Import), or accept a rates upload there.

## Claims checked (verified)

- The targeted suites and the acceptance check pass as recorded (table above; Linux this time).
- The AA1-AA3 folds are present as described: the units in `config_to_ui` / `genDic` /
  `_ui_rates_to_config` and from `plan.rateModel.params` on a no-base save (read; the page-level
  probe shows `config_to_ui` emitting `inPercent = False`); `clone` tries the file first (read,
  `plan_bridge.py` `clone`); `_check_table_events` runs in `build` whatever `rates_table=` is
  (read).
- The hand-table path keeps reverse/roll consistent (AB1's contrast): the scenario stores raw
  file rows (`_rates_table_from_plan`, `_read_rates_table`) and the frozen case keeps the same
  transform keys (read).

## Not checked

- The full suite at this head (taken from PROGRESS).
- Whether anything besides the fixed-assets bequest value reads the session plan's rates
  between a Rates visit and a solve (AB2's reach is from reading `owlbridge`, not a page sweep).
- A stochastic seeded baseline with `reverse_sequence` (AB1 shown on `historical` only; the
  mechanism -- transform in `setRates`, keys kept in the case -- is the same by reading).

## Dispositions (2026-11-04, the user's call: fold AB1-AB4)

- **AB1 folded:** `build` resets `rates_selection.reverse_sequence` / `roll_sequence` in a
  downturn run's case where the hand case sets them, marked with the event in
  `provenance["case_fields"]` (a pages save puts the hand values back through
  `_drop_generated_case`); `gamma` is read after the reset. Cases without the options build as
  before. `BUILDER_VERSION` 5 (R9: the builder's output changed for these runs). Tests:
  `TestThirdReview::test_ab1_the_frozen_run_sees_the_window_at_its_placement` (reverse and
  roll), `test_ab1_the_reset_is_generated_and_a_pages_save_puts_the_hand_value_back`,
  `test_ab1_a_case_without_the_options_is_built_as_before`.
- **AB2 folded:** `owlbridge._setRates`'s table branch passes `in_percent` (from `inPercent`)
  and `reverse` / `roll` (from the case keys, as the varying branch does). Tests:
  `tests/ui/test_rates_page_table.py` (`test_ab2_*`, AppTest of the Rates page: the shown row
  and the session plan after a visit).
- **AB3 folded:** `resolve_rates_csv` tries beside the case file first, then the working
  directory (only the working directory with no case directory); `import_case` resolves a
  rates CSV the same way (an explicit `rates_path` still wins). Docs: `table.py`,
  `info/PARAMETERS.md`, `info/RATE_MODELS.md` (regenerated). `HFP.xlsx` and the budget
  sidecar keep upstream's working-directory-first order. Tests:
  `test_ab3_the_file_beside_the_case_beats_one_in_the_working_directory`,
  `test_ab3_the_working_directory_is_the_fallback`,
  `TestThirdReview::test_ab3_a_frozen_run_reads_its_own_table_from_any_working_directory`.
- **AB4 folded:** `owlbridge.createCaseFromFile` adds a hint to a table case's
  `FileNotFoundError` (the Run Library's **Import a case** takes the rates CSV; or `owlcli run`
  beside the CSV); other upload errors are unchanged. Tests: `test_ab4_*`.

Verification of the fold: the 11 new tests (9 checked to fail before their fix; the other two
pin kept behavior), full suite on Linux 4133 passed / 1 skipped (9:22), `check_library_rates.py`
11/11, lint only upstream's items.

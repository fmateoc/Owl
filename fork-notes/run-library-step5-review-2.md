# Run-library step 5: second review (2026-11-04)

Second independent review of `claude/run-library-step5` at `4aefd31` (the step, `26054d5`, and the
first review's W1-W5, W7-W8 folded). Scope: the code diff against `main` (`src/owlplanner/library/
casefiles.py`, `ui/Create_Case.py`, `ui/Financial_Profile.py`, `ui/Library.py`, `ui/Run_Options.py`,
`ui/owlbridge.py`, `tests/conftest.py`), read against the first review and PROGRESS.md's claims.
Findings Y1-Y5. Nothing is fixed here; the dispositions are the user's call.

Every finding below states how it was checked. "Probe" means a scratch test or script run in a
worktree of `4aefd31` (with `PYTHONPATH=<worktree>/src`, see CLAUDE.md), not committed; its output
is quoted as printed.

## What holds (verified)

- `tests/ui tests/config tests/library`: **817 passed** (Linux, `-n 4`, 27 s). PROGRESS says 816
  passed / 1 skipped on Windows; the skip is platform-dependent, so the totals agree.
- flake8: only upstream's `stochastic` E301/E304. Ruff: the four known B905s
  (`ui/Run_Options.py:261` is upstream's `:257`, moved by the step's four new `initCaseKey` lines).
- W1's report has no false positives on the synthetic suite. Probe: for every scenario in
  `make_cases.py`'s `scenarios.json` that has events, `canonicalize` -> `export_case` ->
  `config_to_plan(loadHFP=True)` -> `scenario_from_ui(config_to_ui(case), plan, base=..., dropped=...)`:
  `0 of 46 event scenarios report a 'not kept' edit with no edit`. This covers rent, purchase
  (Debts, Fixed Assets, owner Budget lines), care and work cells, through the real workbook round
  trip (int/float, blanks, the percent-formatted rate cells).
- The Run Options help's claims: `Plan._applyBreakpointOptions` forces `withSTAR` to "optimize"
  unless it is "none" (`plan.py:7002-7003`), and `withItemized` does not appear in that function
  (grep), so leaving both radios enabled under local search is right.
- `checkBudgetRows` builds `ages_in`, `thisyear`, `n_d` and `i_d` as `_evaluateBudget` does
  (`plan.py:1700-1705`). A blank `year` cannot reach `lines_left_out`'s `int(row["year"])`:
  `conditionDebtsAndFixedAssetsDF` fills Budget `year`/`end` with 0 (`hfp_io.py`, the `int_cols`
  branch), which `_line_years` reads as the plan start / end.
- `syncContributions` before the Library save is a no-op when the Financial Profile page was never
  visited (`_setContributions` returns at `timeList0 is None`), so a run opened and saved without
  visiting it keeps the plan's tables.

## Findings

### Y1 (medium): a further move written in a spelling residency accepts loses its district or city on the first visit to Create Case

`config_to_ui` canonicalizes the first move's school district (`_ui_district`) but copies the
further moves raw (`dic["stateMovesMore"] = [dict(m) for m in moves[1:]]`). `_renderMoreMoves` then
drops any `locality` / `school_district` that is not literally in the select's canonical choices
(`_dropMoreMoveField`, which also `setCaseKey`s the list, so the case reads "modified"). Spellings
that `residency.normalize` accepts are lost: the district alone where it names one row
(`star.canonical_district`'s documented short form, "Yonkers"), and any case variant of a city
(`tax_local.canonical_locality` is case-insensitive). The next solve or save runs the move without
STAR or without the city tax, with no message.

Probe (AppTest on `Create_Case.py`, jack+jill with `state = "NY"`, the `_render` helper of
`tests/ui/test_create_case_move.py`), moves `[{2030, FL}, {2034, NY, <field>}]`:

```
normalize ('NY', '', 'City of Yonkers / Yonkers')                    # residency accepts it
stateMovesMore after render: [{'year': 2034, 'state': 'NY'}] status modified
normalize ('NY', 'Yonkers', '')                                      # locality = "yonkers"
stateMovesMore after render: [{'year': 2034, 'state': 'NY'}] status modified
```

Related, same root cause: a further move with `state = "ny"` keeps "ny" in the case (residency
upper-cases it, so the solve uses NY) but the State select shows the blank choice, which on this
page means "stop modeling state taxes" (`shown: [('State of move 2', ''), ...]`).

Reach: the fork's own files use canonical spellings (`make_cases.py` `PLACES`, the template's
commented example; grep), and runs opened from the library come through `genDic`, whose moves are
`Residence` values already normalized. So it takes a hand-written case file; the household's own
offline case is one.

Fix suggested: canonicalize each further move in `config_to_ui` as `residency.normalize` does
(state upper-cased, `canonical_locality`, `_ui_district`), falling back to the raw value on
`ValueError` as `_ui_district` does; then the render's drop only removes values that are truly
foreign to the state. A test: the probe's two cases, asserting the canonical value is kept.

### Y2 (medium): a further move dated this year or earlier crashes the Create Case page

The further-move year widget passes `value=int(move["year"])` with `min_value=thisyear + 1`.
Streamlit raises when the value is below the minimum, so the whole page stops. Probe, moves
`[{2030, FL}, {2026, NY}]` under the tests' frozen date (2026-01-01):

```
streamlit.errors.StreamlitValueBelowMinError: The `value` 2026 is less than the `min_value` 2027.
  ... ui/Create_Case.py, in _renderMoreMoves  st.number_input(
```

The first move does not crash in the same situation (probe: moves `[{2026, FL}]` renders; its
`getIntNum` seeds session state instead of passing `value=`). Residency refuses such a move at
solve time anyway, but here the user cannot reach the row to fix or remove it, and W4's bounds
warning ("must fall after the first plan year") is unreachable for exactly these years. Reach: a
case file reopened in a later calendar year (plans start in the solve year whatever `start_date`
says, CLAUDE.md), or "Open in Owl" on a run from an earlier year.

Fix suggested: `min_value=min(thisyear + 1, year)` (or no minimum, leaving the guard to W4's
warning, which needs a plan, and the solve's refusal). A test: the probe's chain renders with a
warning instead of an exception.

### Y3 (low): visiting Run Options makes an unchanged case save as a changed run

`Run_Options.py` now runs `kz.initCaseKey("withItemized", "loop")` and `("withSTAR", "loop")`.
`ui_to_config` writes every non-None passthrough key, so after one visit to the page a case whose
file did not name them gains both in `solver_options`, and `scenario_from_ui(..., base=)`
(`_apply_page_edits`: a key in `after` but not in `before` is added) carries them into the child.
Probe (`scenario_from_ui` on jack+jill against its own `import_case`, the UI dict with the two keys
as the page leaves them):

```
base has withItemized: False
hash equal: False
diff: ["case.solver_options.withItemized: added ('loop')", "case.solver_options.withSTAR: added ('loop')"]
```

Same plan (both default to "loop" in `Plan`), but a save after merely opening Run Options shows
two changes nobody made and a different `scenario_hash` than its base, so `test_an_unedited_save_is_
identical_to_its_base`'s property no longer holds through the pages. The probe set the keys by
hand; that the page sets them follows from `initCaseKey` (it stores when the key is missing,
`sskeys.py:530-549`) and was not driven through AppTest.

Fix suggested: drop the two `initCaseKey` lines. `getRadio` already shows `choices[0]` ("loop" for
both) when neither widget state nor case key exists, and it writes the case key only from its
`on_change` callback (`sskeys.py:951-988`), so the key then appears only when the user picks a value.

### Y4 (low): the Library save ignores a refused table sync

`_save_current_case` calls `owb.syncContributions()` and discards its result. When
`_setContributions` cannot accept the tables it shows `st.error` and returns `False`; the save
then goes ahead with the plan's previous tables, and the `st.rerun()` after the button wipes the
error. Probe (AppTest on `Library.py`, jack+jill, `timeList0` edited to wages 123,456 in 2026 plus
`months worked = 13`, which `hfp_io.read` refuses):

```
errors shown after rerun: []
runs saved: 1
saved wages 2026 [100000] months [0]
```

The run is saved without the wages edit and nothing says so. Reach through the real editor not
established: the timetable's column config and the QCD entry check probably keep a refused value
out of `timeList*` (not verified), so this is defense in depth, like W6. Fix suggested: if
`syncContributions()` returns `False`, `libraryjobs.flash("error", ...)` and return before saving.

### Y5 (nit): help text and a dead fallback

- STAR radio help: "(Basic, and Enhanced from 65 under the income limit)" reads as if Basic had no
  limit; the model applies Basic's own limit too (`star.py:146`, `basic_income_limit = 500000.0` in
  `property_tax_relief.toml`). The same wording is in `_district_help` (pre-existing). The radio
  helps quote their values with U+2019 on both sides (’loop’); the other helps on the page use
  plain quotes or none.
- `seedProfileTables`' fallback `resetTimeLists()` and its docstring line "A plan that holds no
  tables (a fresh case) still starts from the zeroed skeleton" do not match the code path: `Plan.
  __init__` always calls `zeroWagesAndContributions()` (`plan.py:785`), so every plan holds tables
  (probe: a fresh `Plan(['A'], ...)` has `timeLists` `['A']`), and the seeding branch is the one
  taken for fresh cases too. Outcome for a fresh case is the same zero tables, but stored with
  `storeCaseKey` instead of `setCaseKey`, and without `resetTimeLists`' " *" mark on `hfpFileName`
  when `stHFP` is set. I did not find a path where `timeList0` is None while `stHFP` is set, so the
  mark difference looks unreachable; not checked further.

## Not covered by this review

- Windows: nothing run there.
- The Budget editor's `st.data_editor` loop itself (AppTest cannot drive it; covered through the
  storage path, as PROGRESS says).
- The Documentation page text beyond the lines in the diff.
- The full suite (only `tests/ui tests/config tests/library` were run).

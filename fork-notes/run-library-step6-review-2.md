# Run-library step 6: second review of the core (2026-11-05)

Second, independent review of run-library build step 6's core on `claude/run-library-step6`
at `97b6059` (the core plus the first review's AC1-AC7 folds; `e898f699..97b6059`), read
against `fork-notes/run-library-design.md` sections 4, 8.1, 9.2 and 9.3 and the first review
(`run-library-step6-review.md`). Findings **AD1-AD9** (1 high, 1 medium, 4 low, 3 nit);
prefix AD because AC is the first review's. None repeats an AC item; AD3 is about AC4's fold.

Environment: Linux, Python 3.11, HiGHS only, Streamlit 1.66.1, pandas from `uv sync`.
**Nothing in `src/`, `ui/` or `tests/` was changed.** The probes wrote only to temporary
directories; they are reproduced below where a finding rests on them.

## What was run

| Command | Result |
|---|---|
| `pytest -n 4 tests/library tests/ui` | **693 passed** (0:30; the first review's 685 + 1 skipped on Windows, + 7 fold tests; the Windows skip runs on Linux) |
| `flake8 --max-line-length=120` on `src/owlplanner/library`, `ui/Collections.py`, `tests/library`, `tests/ui`, `check_library_variants.py` | clean |
| `make_cases.py` | 39 workbooks, 46 scenarios (the probes' inputs) |
| Streamlit's own edit code (`data_editor._apply_dataframe_edits`) on the page's empty tables, then `_dimensions` (lifted from `ui/Collections.py` by `ast`), `plan_variants`, `builder.build`, `Library.save_run`, `config_to_plan` | AD1, AD6 |
| AppTest of the real page, members with synthetic results (the test file's `_write_result`) | AD2, AD3, AD4, AD9 |
| full suite, `check_library_variants.py` | not run (no code changed; PROGRESS records 4203 / 2 skipped and 5/5) |

## Findings

### AD1 (high): an empty cell in the places or financing table becomes NaN, and a place's empty costs reach the plan as \$0

The page says "Leave a table or field empty to keep the parent's". Streamlit's data editor
hands back `None` for a cell the user did not touch, but `_dimensions` walks the tables with
`DataFrame.iterrows()`, which turns that `None` into `NaN` (pandas, object columns), and every
guard is `row.get(k) not in (None, "")` or `row.get(k)` truthiness. NaN passes all of them:

- **costs:** each empty cost is kept as NaN, `normalize` stores it as `None`, the builder
  writes the Budget row with no amount, and the plan reads **\$0**. A White Plains row with
  label, name, price, district and move typed and the three costs left empty "to keep the
  parent's" (Yonkers: property tax 9,500, HOA 9,600, insurance 900) saves and solves with
  **no condo costs at all**: \$20,000 a year of essential spending gone. The grid then shows
  it as a lead.
- **price:** an empty price (to keep the parent's) becomes NaN, passes `_check_value`
  (`nan <= 0` is false), is stored as `None`, and `validate` refuses the child: "No
  variants: ... price must be a positive number".
- **loan:** a mortgage row with label, kind, term and rate only (section 6.2's defaults
  for down, closing and extra) gets `down = closing = extra = NaN` and `name = "nan"`, and
  `build` raises `ValueError: cannot convert float NaN to integer` (`round(price * (1 -
  down))`); the page's `except Exception` flashes "not saved (cannot convert float NaN to
  integer)" for every variant.
- **name, label, locality:** an empty `name` becomes the text `"nan"` (the Fixed Assets row
  and the loan are named "nan"); an empty label is `"nan"`, so AC6's "a row with data but no
  label is skipped and named" never fires on real editor output; an empty locality is NaN
  in the move.

Probe (Streamlit 1.66.1's own edit code on the page's table; the cells the user did not
type are absent from `added_rows`, as the frontend sends them):

```
editor row: {'label': 'whiteplains', 'name': 'whiteplains condo', 'price': '700000', 'state': 'NY',
             'locality': None, ..., 'move': 'True', 'property tax': None, 'hoa': None, 'insurance': None}
iterrows: nan True                       # row.get('locality'), and `not in (None, "")`
place value from the page: [{... 'place': {'state': 'NY', 'locality': nan, ...},
                             'costs': {'property tax': nan, 'hoa': nan, 'insurance': nan}}]
saved: True 2026-11-05_wp
plan Budget:   property tax  2027  0.0 / HOA  2027  0.0 / condo insurance  2027  0.0
financing value from the page: [{'label': 'mortgage', 'financing': {'kind': 'loan', 'term': 30.0,
             'rate': 5.9, 'down': nan, 'closing': nan, 'extra': nan, 'name': 'nan'}}]
ValueError: cannot convert float NaN to integer       # builder.py:779
```

Why nothing caught it: `check_library_variants.py` calls `plan_variants` with Python dicts,
never the page's tables, and no test feeds the tables (the AC6 test sets the claim box only;
AppTest does not drive a data editor -- recalled, not checked). The page's table path has
never run on real editor output.

Location: `ui/Collections.py` `_dimensions` / `_row_values` (the `iterrows()` loops).
Recommendation: read the tables as records with missing cells as `None`
(`df.astype(object).where(df.notna(), None).to_dict("records")`), and treat a blank-looking
string as missing. Independently, `variants._check_value` should refuse a non-finite number
(price, costs, financing terms) and `validate` a `None` cost, so a NaN that reaches the
library from any route is a `ScenarioError`, never a \$0 line. Test: Streamlit's
`_apply_dataframe_edits` on `_places_table()` / `_financing_table()` with partly typed rows
(the probe), then `_dimensions` -> `plan_variants` -> `build`: the empty costs keep the
parent's amounts, a loan with term and rate only builds with the defaults.

### AD2 (medium): the page's default grid layout drops a dimension, or pivots one against itself

When the collection has no saved layout (the case after "make variants": the handler never
writes one), the page takes `rows = [dims[0]]` and `columns = [dims[-1]]` of the
**alphabetically sorted** dimensions. For the design's own grid (place x year x financing)
that is `financing` rows against `year` columns: **place is not in the layout**. The
members that differ only by place then share cell keys, so one place fills the grid and the
others are listed "beside the grid" under a caption that says they have "the same values"
(they do not). With one dimension, rows and columns are the same dimension and the grid is a
diagonal with a star on every row. A saved layout with `rows: []` cannot mean "no row
dimension" either: the empty list falls back to `[dims[0]]` (the page test's own fixture,
`{"rows": [], "columns": ["year"]}`, renders a year x year diagonal).

`grid.grid_view`'s own defaults (`row_dims=("place", "financing")`, `col_dims=("year",)`) are
the right ones for section 9.3, and the acceptance script passes them explicitly; the page
overrides them.

Probe (AppTest, 8 members place x year x financing, no saved layout; then 3 members, year only):

```
| financing | 2027 | 2029 |
| cash | 150,000 | +6,000 ★ / 150,000 |
| mortgage | +3,000 / 150,000 | +9,000 ★ / 150,000 |
CAPTION: Beside the grid (its cell shows **v0**, the same values): **v4**, score 92,000
... (v5, v6, v7 likewise: the four white-plains members)

| year | 2027 | 2029 | 2031 |
| 2027 | 150,000 |  |  |
| 2029 |  | +3,000 ★ |  |
| 2031 |  |  | +6,000 ★ |
```

Location: `ui/Collections.py`, "The grid" (`rows = ... or [dims[0]]`, `columns = ... or
[dims[-1]]`). Recommendation: default the columns to `year` when present (else the last
dimension) and the rows to every other dimension; allow empty rows (one row); let "make
variants" store that layout when it creates the members. Test: an AppTest with a 2 x 2 x 2
collection and no saved layout shows all eight members in cells, none beside the grid.

### AD3 (low): AC4's fold puts the row's star on a number that is not the row's best

`grid_view` gives the best-score mark to the shown cell at the best member's key
(`holder = shown[(key, _key(best.values, col_dims))]`). When the best member is a collided
one, the star is drawn on the **shown member's** delta, and the page's caption says "★ is the
best score in its row". In AD2's probe, row "cash" stars `+6,000` (v1, 86,000) while the
row's best cash score is v5's 95,000 (+15,000), which appears only in a caption.
`test_ac4_two_members_with_the_same_values_never_vanish` pins this behaviour (the star on the
cell whose entry is not the best). With AD2 fixed, collisions are rare (two runs with the
same values); with AD2 as is, they are the normal case for a three-dimension grid.
Location: `src/owlplanner/library/grid.py` (the best-score pass). Recommendation: mark the
best member itself -- a starred caption line when it is a collided member, and no star on the
cell -- or show the best of the colliding members in the cell.

### AD4 (low): a cell is grey when R3 says the variant leads

`_cell_md` colours a cell grey unless the **score's** verdict is "resolved", and only then by
the lead verdict. R3 (design 9.2) judges the two numbers: a variant with the score inside the
noise band and a resolved larger home leads. The cell is grey ("within the noise band") while
"What nothing beats" on the same page says it leads.

Probe (AppTest, reference 80,000 / home 150,000; variant 80,400 / 250,000; both local search):

```
| place | queens | yonkers |
| queens | <span style='color:#757575'><b>+400 ★</b></span><br>...250,000 |  |
FRONT: - **v1**: score 80,400, home 250,000; leads v0
  vs *v0*: within noise (+400) -- ~ the 1% loop-noise band
```

Location: `ui/Collections.py` `_cell_md`. Recommendation: colour by `cell.lead["verdict"]`
(grey only for "no difference beyond the noise rule" / "not comparable"), and keep the
score's own verdict in the number's style (for example "~" before an unresolved delta).

### AD5 (low): nothing says when a cell's claiming ages differ from the reference's

The usual flow (`check_library_variants.py`'s) solves the reference with the `ages` preset
and the children with `decision`, which forces `withSSAges = "fixed"` (`presets._FORCED`), so
a child with no `claim` value solves at the case's `social_security_ages` (the builder keeps
the hand ages for a person with no age, `builder.py` lines 828-840), not at the reference's
pick. The design's rule that makes a housing grid one question (a single-valued `claim`
dimension holds every child) is on the page only as the optional "Fill the ages from the
run's last solve" button. When it is not used, every cell's difference includes the
claiming ages, and the only caveat shown is S13's "solved with different presets (ages vs
decision)". `grid.py` and `compare.py` never read the claiming ages (grep: `claiming` occurs
in `compare.py` only as the label of the SS-income row). Verified by reading; not run.
Recommendation: a flag in `grid_view` when a cell's `claiming_ages` (plan.json) differ from the
reference's, and on the page a note under "Make variants" when the parent's latest result is
an `ages` result and the claim boxes are empty.

### AD6 (low): the `move` cell reads any text as True

`place["move"] = bool(row["move"])`: the places table's columns are empty object columns,
which Streamlit treats as `ColumnDataKind.EMPTY` and returns the frontend's value as is
(`data_editor._parse_value`), so a typed "False", "no" or "0" is a non-empty string and
reads **True** (checked: `_dimensions` gives `move: True` for each of the three). That the
frontend sends a string for that column is inferred (an empty column edited as text), not
observed in a browser. A wrong `move` puts the purchase's locality into a move or leaves the
hand locality in force (`builder.py` 792-803). Location: `ui/Collections.py` `_dimensions`.
Recommendation: a checkbox column (`st.column_config.CheckboxColumn`) or an explicit
true/false parse that refuses anything else.

### AD7 (nit): the two captions disagree on what an empty claiming box means

"Leave a table or field empty to keep the parent's" and, for the claiming boxes, "empty: let
Owl choose". The code follows the second: with one person's ages typed and the other's box
empty, every child gets the other person's claim event with `age = None`, which makes that
person searched (`withSSAges` names them; `builder.py` 844-855) where the parent may have held
them fixed. The label says so ("Noa: let Owl choose"), so it is visible, but the general
caption is wrong for this field. Recommendation: one caption; and consider "keep the
parent's" for an empty box when another person's box is filled.

### AD8 (nit): `agesearch` -- stage 1 is a pure LP only for some cases, and stage 2 ignores the noise rule

- The module docstring says stage 1 is "a pure LP per candidate". `EXACT_MODEL` sets
  Medicare off, SS taxability 0.85 and the loop, but leaves the case's other families as
  written, so a case with `withLTCG`, `withNIIT`, `withSTAR` or `withACA = "optimize"` makes
  every stage-1 candidate a MIP. The template sets none of these (`Case_us.template.toml`:
  `withMedicare = "optimize"`, `withACA = "loop"`), so the household's case is a pure LP;
  the inherited run_suite behaviour is unchanged. A sentence in the docstring would do.
- Stage 2 takes `max(score)` over the pick and its neighbours with no tolerance, while the
  rest of the library judges every difference by R2 (the template's default model is
  branch-and-bound at `MILP_GAP` 3e-3 under `withMedicare = "optimize"`, CLAUDE.md's
  "Branch-and-bound gap"). The record keeps every candidate's score, so the evidence is
  there, but neither `record.json` nor the run page says whether the pick beat its
  neighbours beyond the noise rule. Faithful to run_suite (design 8.1); noted, not a defect.

### AD9 (nit): the reference's own cell is a bare number

The reference's cell shows only its home at the end (`_cell_md` returns `home` when
`delta is None`), with no mark that it is the reference, and when the reference holds the
row's best score its star is dropped. In AD2's probe, `cash / 2027` reads `150,000` beside
`+6,000 ★ / 150,000`. Recommendation: "reference" (or "0") in the cell.

## Claims checked (verified)

- The first review's folds hold where tested: the AC1-AC7 tests pass on Linux (part of the
  693), and AD2's probes render the page with no exception after the AC2/AC3 route change.
- `run_suite.py` uses the shared implementation: `EXACT_GROUP`, `fixed_ages` and
  `two_stage_ages` come from `agesearch`; no reference to the removed `EXACT` or
  `_score_plan` remains (grep: only the comment at line 287). Its old list reading
  (`[names.index(n) for n in sel]`) walked a string's characters for a single name;
  `searched_names` does not (read).
- Ages pinned through `fixed_ages` round to 4 decimals in the record (`round(float(a), 4)`);
  Owl reads claiming ages as `round(age * 12)` months (`socialsecurity.py:1199`, `plan.py:5471`),
  so a rounded pick such as 67.8333 pins the same month (813.9996 -> 814).
- `worker._solve` runs the search only for `preset == "ages"` with `withSSAges` not
  `fixed`, keeps the stages' warnings out of the record (`_LogTee.quiet` returns before the
  line parsing) while still checking for cancellation, and records `age_search` on success
  (read; AC9 stands for the failure path).
- `latest_result` cannot pick up a staging folder: `.attempt-<token>` folders live inside a
  results folder, not in `results/` (`results.py` 523-529).
- `store` collections: every read-modify-write is under `library.lock`; `delete_run` clears
  memberships and the reference (read; `tests/library/test_collections.py` passes).

## Not checked

- A browser session of the page (the data-editor behaviour in AD1 and AD6 was reproduced
  with Streamlit's own edit-application code, not through the frontend).
- `check_library_variants.py` (reduced or `--full`) and the full suite: no code changed.
- The "Queue them when created" and "Queue every member" paths against a live job manager.

## Dispositions (2026-11-05, the user's call: fold AD1-AD6; AD7-AD9 stand as written)

- **AD1 folded**, at both doors:
  - *The page:* the editors' parsing moved to `ui/variant_tables.py` (pure functions, so the
    tests feed them what the data editor returns). `records` reads each row with every
    missing cell (`None`, NaN, blank text) as `None`, so an empty cell keeps the parent's
    value as the caption says: empty costs keep the parent's amounts, an empty price the
    parent's price, a loan with term and rate only takes the builder's defaults (named
    "<home> mortgage", not "nan"), and a row with data but no label is skipped and named.
    A text cell set to `-` clears the parent's value (`CLEAR`): a White Plains row from a
    Yonkers parent needs locality `-`, or the move would carry Yonkers' local tax.
  - *The library:* `variants._check_value` refuses NaN or infinity anywhere in a value, a
    cost that is not a number of 0 or more, a place field of the wrong type (`move` a bool,
    the rest text), a loan term that is not a number and a loan name that is not text; the
    builder's `validate_events` refuses a cost or financing term that is not a finite number
    and a non-finite price. A NaN from any route is a `ScenarioError`, never a \$0 line.
- **AD2 folded:** `variant_tables.grid_layout` -- a saved layout with columns is used as
  saved (empty rows: one row); otherwise the purchase year is the columns (else the last
  dimension) and every other dimension a row, in the variant order (place, financing, work,
  claim). "Make variants" stores that layout on a collection that has none, and the layout
  editor shows the layout in use. The collided caption says "the same row and column".
- **AD3 folded:** `grid_view` stars the best member itself: a cell only when it shows that
  member; a best member listed beside the grid is in `Grid.best_beside` and its caption says
  so. AC4's test now pins this (no star on the row; `best_beside == ("dup",)`).
- **AD4 folded:** `_cell_md` colours by R3's lead verdict (grey only when there is no
  difference beyond the noise rule or no comparison) and prefixes `~` to a score difference
  inside the noise band; the caption says so.
- **AD5 folded:** `grid.claiming_ages_flag` adds one flag listing the cells solved at
  claiming ages other than the reference's (compared in whole months; members whose values
  vary the claiming ages are left out: there the ages are the question). Make variants warns
  when the parent's last solve searched the claiming ages (`age_search` in its record) and
  every claiming box is empty.
- **AD6 folded:** `move` is a checkbox column, and typed text is read by `flag` (true/false,
  yes/no, 1/0; anything else refused); `kind` is a select box, and a kind other than
  cash/loan/mortgage is refused (a typo used to become cash).

Tests +47: `tests/ui/test_variant_tables.py` 21 (Streamlit's own `_apply_dataframe_edits`
on the page's tables -- AppTest cannot drive a data editor), `tests/library/test_variants.py`
+14, `tests/library/test_grid.py` +5 (AC4's test re-pinned), `tests/ui/test_collections_page.py`
+7 (AppTest of the grid, the flags and the stored layout). Checked to fail before the fold
(the `src/` and `ui/` changes stashed): 23 new tests and AC4's re-pinned one failed, and the 21
table tests errored (their module is new; the old parsing's NaN is the review's probe above);
the three that passed are guards (no flag where none is due, twice, and a one-row layout
`grid_view` already handled).

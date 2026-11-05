# Run-library step 6: review of the core (2026-11-04)

Review of run-library build step 6's core on `claude/run-library-step6` at `9372c7d9`
(collections, "make variants", the grid view and the `ages` preset; the first increment of
the step, `e898f699..9372c7d9`), read against `fork-notes/run-library-design.md` sections
4, 8.1, 9.2, 9.3 and 11. Findings **AC1-AC10** (2 medium, 5 low, 3 nit); prefix AC because
AA and AB are taken. None repeats a Z/AA/AB item (those were step 5b's rates-table work).

Environment: Windows, Python 3.11 (`src/owlplanner` the editable install), MOSEK/HiGHS.
Every probe wrote only to the session's temp directory. **Nothing in `src/`, `ui/` or
`tests/` was changed.** The probes are in the session's scratch folder
(`probe_lib.py`, `probe_ui2.py`, `probe_ui3.py`, `probe_ages.py`, `mini.py`).

## What was run

| Command | Result |
|---|---|
| `pytest tests\library tests\ui -q` | **685 passed, 1 skipped** (2:16) |
| full suite (`pytest -q -n 4`) | **4196 passed, 2 skipped** (9:16; matches PROGRESS at this head) |
| `flake8` / `ruff` on `src/owlplanner/library`, `ui/Collections.py`, `tests/library`, `tests/ui` | clean |
| `two_stage_ages` on `examples/Case_bill.toml` (`withSSAges = "optimize"`) | works: pick `[67.0]`, 3 candidates, ties resolved to the pick (0.6 s) |
| probes (below) | AC1-AC7 reproduced |
| `check_library_variants.py` | not run (recorded 5/5 in PROGRESS; ~45 min of solves) |

## Findings

### AC1 (medium): "Fill the ages from the run's last solve" is dead on click

`ui/Collections.py`'s fill button (`key="col_variant_fill"`, line 174) writes
`st.session_state[f"col_variant_claim_{person}"]` for each person. The claim `text_input`s
with exactly those keys are instantiated two lines above (line 172), so every click raises
Streamlit's `StreamlitWidgetAlreadyInstantiatedError`
("`st.session_state['col_variant_claim_Bill']` cannot be modified after the widget with
that key is instantiated") and the page ends in the error. The handler body never gets
past the first name, and none of the boxes is filled. (An inline button handler runs
mid-script, after the widgets above it; the exception is for `on_click` callbacks, which
run first.)

Probe (AppTest of the real page, a bill run with a solved result):

```
-- 'Fill the ages from the run's last solve' clicked --
exception: ["str: `st.session_state['col_variant_claim_Bill']` cannot be modified after the widget with that key is instantiated. ..."]
claim text state: None
```

Location: `ui/Collections.py` ("Fill the ages from the run's last solve" handler).
Recommendation: make it an `on_click` callback (`st.button(..., on_click=_fill, args=...)`,
which runs before the widgets are instantiated), or write a plain (non-widget) session key
that the claim inputs read at instantiation. Test: an AppTest click that asserts the boxes
end at `67` / `70` and no exception -- `tests/ui/test_collections_page.py` only asserts the
button's label exists, which is why this hid.

### AC2 (medium): "Create the variants" ends in the same exception when it succeeds

The handler's tail (`ui/Collections.py:272`) calls `_open_collection(coll_target.id)`,
which writes `st.session_state["col_page_collection"]` -- the key of the collection picker,
instantiated at line 82 of the same run. Every successful click therefore ends in
`StreamlitWidgetAlreadyInstantiatedError` after the work is done: the children are saved
and their members added (before line 272), but the run ends in the error before the
`st.rerun()` that would show the success flash (it surfaces only on some later
interaction), and the page's last word is an exception that says nothing about the
variants.

Probe (the page, a synthetic purchase-year variant; the parent has a purchase event):

```
exception: ["str: `st.session_state['col_page_collection']` cannot be modified after the widget with that key is instantiated. ..."]
members of First question: [('c73866', {'year': 2029})]      # the work survived
runs: ['bill', 'reference', 'reference 2029']
```

Location: `ui/Collections.py` (`_open_collection`, called from the make-variants handler).
Recommendation: as AC1 -- the intent is "open the collection on the next render", which the
page already supports through the plain key `library_selected_collection` (popped and
mapped to the picker's label before the picker instantiates, lines 76-81). Having
`_open_collection` set that key instead of the widget key fixes this and AC3 together.
Test: an AppTest click on "Create the variants" asserting no exception and the target
collection shown.

### AC3 (low): "Create collection" opens the wrong collection

`_open_collection` stores the collection's **id** in `col_page_collection`, but the picker's
options are **labels** (`f"{name}  ({n} run(s))"`; `labels[st.selectbox(...)]` on line 82).
The write itself is legal there (the "Create collection" button is instantiated before the
picker, line 63), so no exception: on the rerun the id is not one of the options and the
picker falls back to the **first** collection. Creating "Third question" while "Second
question" is selected lands the page on "First question" -- the new collection is never
opened and the previous selection is lost. (AppTest cannot even round-trip the state: its
widget-state serialization raises `ValueError: list.index(x): x not in list`.)

Probe:

```
-- 'Create collection' clicked while 'Second question' is selected --
page header: ['## Second question']
... click ...
exception: []
page header: ['## First question']            # not the new "Third question"
collections in store: ['First question', 'Second question', 'Third question']
```

Location: `ui/Collections.py` `_open_collection` (and its two callers). The
`library_selected_collection` path (line 76-81) shows the intended form: an id translated
to the picker's label, set before the picker instantiates.
Recommendation: store the id in a plain key and translate it once, before the picker (the
same map `library_selected_collection` uses); never write the widget's key inline.

### AC4 (low): the grid silently drops a member whose cell key collides

`grid.grid_view` keys `cells` by run id but builds each row's cell map with
`next(e for e in placed if keys match)`, so when two members share one (row key, column
key) -- two runs carrying the same variant values, e.g. "make variants" run twice and both
children added -- the second member appears **nowhere**: not in a cell (the first entry
takes it), and not in `unplaced` (it has values). If the hidden member holds the row's best
score the "best" star is marked on *its* cell (`cells[best.run_id]`), which is never
rendered, so the row shows no star and the pivot hides its best variant.

Probe (three entries, two sharing `{"place": "yonkers", "year": 2029, "financing": "cash"}`):

```
entries handed in: 3; entries in the pivot: ['ref', 'dup1']
unplaced: []
```

Location: `src/owlplanner/library/grid.py` `grid_view` (the `rows` build and the best-score
pass). Recommendation: a cell holds every entry of its key (the run_suite pivot's groups are
unique, so this never arose there) -- or list colliding members in `unplaced`/a "two runs in
one cell" note, and mark the best on the entry the cell actually shows. Test: two members
with equal values, both visible.

### AC5 (low): `plan_variants` raises TypeError on a string price

`variants._check_value`'s place branch explicitly allows `price` to be "a number or a
string" (the `isinstance(..., (str, int, float))` shape check) and then compares it:
`if price is not None and price <= 0`. A string price (`"850000"`, the natural paste from
a listing) raises `TypeError: '<=' not supported between instances of 'str' and 'int'`
instead of the `ScenarioError` every other refusal gives -- and `ScenarioError` is what
`ui/Collections.py` catches and flashes (`except ScenarioError`); a TypeError escapes to
the page.

Probe (`plan_variants(scenario, {"place": [{"label": "queens", "price": "850000"}]})`):

```
TypeError: '<=' not supported between instances of 'str' and 'int'
```

Location: `src/owlplanner/library/variants.py` `_check_value` (the `price` check).
Recommendation: reject a non-numeric price with `ScenarioError` (or coerce `float(price)`
first -- but the scenario stores numbers, so a refusal is the honest reading of the
docstring "only the keys given change" plus the builder's numeric price).

### AC6 (low): the make-variants editors convert numbers unguarded

The click handler wraps the years text and the work years in `try/except ValueError` (a
flash), but the places table (`float(row["price"])`, `float(row[field])` for term, rate,
down, closing, extra) and the claiming boxes (`float(part)` in `_claim_combos`) convert
unguarded. A non-numeric cell ends the page with a raw exception instead of a flash.

Probe (AppTest of the real page, the claiming box set to `67x`):

```
exception: ["str: could not convert string to float: '67x'"]
```

Location: `ui/Collections.py` ("Create the variants" handler and `_claim_combos`).
Recommendation: one `_number(text) -> float` helper raising the flash's error, as the years
field already does; the same loop should also skip (and name) a places row that has no
label -- today it is dropped silently (`if value["label"]:`).

### AC7 (low): a collection with no runs crashes the page

With one collection and no runs yet (the natural first minute: the page expands "New
collection" when the library is empty), the Make-variants block runs on every render and
`st.selectbox("From run", [])` returns `None`, so `lib.scenario(parent)` raises
`LibraryError: no run with id None` and the page shows an exception. Everything above the
block still renders (so the collection can still be deleted), but the grid, the members and
"Run the collection again" are below the crash point and never appear.

Probe (a fresh library, one collection, zero runs):

```
exception: ['str: no run with id None']
```

Location: `ui/Collections.py` ("Make variants", `lib.scenario(parent)`).
Recommendation: skip the block (a caption: "save a run first") when `lib.runs()` is empty.

### AC8 (nit): `searched_names` is not quite `plan._parseSSAgesOption`'s reading

Its docstring claims "plan._parseSSAgesOption's reading"; the readings differ in three
ways: an unknown name is silently dropped (the plan raises `ValueError`), `"fixed"` /
`"none"` would select a person literally named that (the plan reserves both), and
`"optimize"` is matched case-insensitively while the plan is case-sensitive -- so
`withSSAges = "Optimize"` passes the worker's gate and `searched_names`, then stage 1's
solve raises the plan's `ValueError: Unknown individual 'Optimize'`. All three are behind
stage 1's own solve (which raises first for the bad-name case), so the reach is the
case-spelling one. Location: `src/owlplanner/library/agesearch.py` `searched_names`.

### AC9 (nit): a failed or interrupted final solve drops the search record

`Worker.run`'s error and cancellation handlers write their record without `age_search`
(only `_solve`'s success path passes it), so when the two-stage search has finished --
minutes of solves, with each candidate's score -- and the final solve then fails or is
cancelled, `record.json` shows none of it. The candidates are the "how it was obtained"
evidence the record exists for (and the run page's "Claiming ages searched" caption). The
age_search block is a local variable of `_solve`; hoisting it (or passing it into the error
path) would keep it. Location: `src/owlplanner/library/worker.py` (`run`, `_solve`).

### AC10 (nit): `front()` silently re-bases an unsolved reference

`grid.front(entries, reference=...)` falls back to the first solved member when the named
reference has no solved result (`next(..., solved[0])`), while still reporting
`vs_reference` as a judgment against "the reference". The Collections page guards this
(it calls `front` only with a solved reference), so nothing on screen is wrong today;
direct callers can be misled. A `None`/`not comparable` verdict, or an explicit
"reference has no numbers" entry, would say what happened. Location:
`src/owlplanner/library/grid.py` `front`.

## Claims checked (verified)

- The targeted suites pass as recorded (table above; 685 passed / 1 skipped -- the same
  platform skip PROGRESS records).
- The `ages` preset's pieces are wired as described: `presets.PRESETS` offers `ages` and
  `_FORCED["ages"] = {}` (R4's exception); the worker runs `two_stage_ages` before the
  final solve only when the case's `withSSAges` is not `fixed`, pins the pick through
  `fixed_ages`, and `record.json` carries `age_search` (read; the wiring tests
  `tests/library/test_agesearch.py` pass, and a real search ran per the table).
- `run_suite.py` shares the one implementation cleanly: `EXACT_GROUP_SETS`, `fixed_ages`
  and `two_stage_ages` are imported from `agesearch`, its own duplicates are gone, and no
  dangling reference to the removed `_score_plan` / `EXACT` remains (grep).
- The collections CRUD obeys its rules (tests + read): `add_member` idempotent,
  `delete_run` leaves every collection and clears the reference, `delete_collection`
  deletes no runs, a malformed `library.json` entry is skipped not fatal, and the lock is
  held around each read-modify-write.
- The grid's judgments are `compare`'s R2/R3 rules reused, not re-implemented: the score
  through `difference` (the 1% band), the home through the fifty-cent rule
  (`from_inputs=True`), the lead through `lead_verdict`, and `front` is the non-dominated
  set on the two numbers (`tests/library/test_grid.py` pins the trade-off and lead cases).
- The acceptance script's five checks cover the numbers at scale and the events parity;
  the run it records (5/5) is in PROGRESS. What no test covers is the page's make-variants
  click handler end to end (AC1-AC3, AC6 hid behind that gap; the tests assert only that
  the buttons and fields exist).

## Not checked

- `check_library_variants.py --full` (the 42-cell grid; the recorded run is the reduced
  grid).
- The "Queue every member" / "Queue them when created" paths against a live job manager
  (the probes queue nothing; `enqueue`'s refusal cases are step 2's and covered there).
- Whether `StreamlitWidgetAlreadyInstantiatedError` also reaches the Run page's or the
  Queue page's handlers (their buttons were not swept; step 3's review covered those pages'
  own flows).


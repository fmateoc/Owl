# Run-library step 6: second review of the second increment (2026-11-05)

Independent review of step 6's second increment on `claude/run-library-step6-inc2` at
`f0c51438` -- the four build commits `0bc64ca0` (the `death` (I2) and `sequence` (I11)
dimensions, member values, the save dialogs' "Collection" field), `532a8016` (the
sensitivity tornado (I9), the `aca_table_year` knob), `6a67936a` (the conversion and
bracket view (I8), the `regret` job), `06baba60` (the `ages_thorough` preset) -- plus the
fold `447f6f49` (AE1-AE3) read as part of the current state. Read against
`run-library-design.md` sections 6.2-6.3, 7, 8.1 ("Ages, thorough"), 9.1-9.3, 11, 14.1 and
14.3 (I2/I8/I9/I11) and the R2/R3/R4/T1/U7 rules. Findings **AF1-AF8** (5 low, 3 nit, no
medium); prefix AF because AC (the core), AD (the core's second review) and AE (this
increment's first review) are taken. None repeats an AC/AD/AE item -- AF1, AF2 and AF5 are
defects in AE1-AE3's *folds*, which the brief asks for; AF3, AF4, AF6 and AF8 are new.

Environment: Windows, Python 3.14.7 (the repository `.venv`), MOSEK/HiGHS. Every probe
wrote only to the session's scratch folder (`probe1.py`, `probe2.py`, `probe3.py` under
`%TEMP%\opencode\af_review`); **nothing in `src/`, `ui/`, `tests/` or `PROGRESS.md` was
changed by this review**. Like the previous session's, the tree under review also carries
`bc4e38ec` (the `work_sweep` move) and `263def48` (the full-grid check's pool bound) between
the increment and the fold; AF7 is read from the current state and attributed there.

## What was run

| Command | Result |
|---|---|
| `pytest tests/library/test_tornado.py test_variants.py test_builder.py test_worker.py test_presets.py test_scenario.py tests/plan/test_brackets.py tests/tax/test_aca.py -q` | **311 passed** (2:05; the increment's own files) |
| `pytest tests/library tests/ui -q` | **830 passed, 1 skipped** (4:22) |
| `pytest tests/plan tests/config tests/tax tests/cli -q` | **1333 passed, 4 deselected** (16:06; the model-side suites the increment touches) |
| `flake8` / `ruff check` on the increment's touched files | clean (flake8 exit 0; ruff "All checks passed!") |
| probes (`probe1.py`, `probe2.py`, `probe3.py`) | AF1-AF6 reproduced; the tornado's bars, the AE3 split and the conversion layer cleared |
| full suite (`pytest -q -n 4`) | not run (the machine is busy with `check_library_variants.py --full`, which this review must not disturb; the prior sessions record 4346 passed, 2 skipped) |

## Findings

### AF1 (low): AE1's fold leaves its own door unbolted -- a no-events scenario's one-year plan still fails with the raw `ValueError`

The fold (`447f6f49`) puts `check_death_window(scenario)` in `build` because that is "the
door every route passes". It does not: `build` returns at `if not events: return hand_case,
hand_hfp, provenance` (`src/owlplanner/library/builder.py` 813-814), which sits **before**
the window check (line 841). A scenario with no events at all -- exactly the shape section
6.4's "Import a case" produces ("into a scenario with no events: every row is a hand row"),
or any schema-v1 scenario -- whose `basic_info.life_expectancy` leaves one plan year is
frozen, saved and queued unchanged, and the solve then dies with AE1's own error:
`ValueError: Plan needs more than 1 years.`, unnamed and without the window.

Probe (`probe2.py`; 1964-born couple, plan year 2026, `life_expectancy` `[62, 62]`):

```
build (no events): RETURNED, no refusal
raw error downstream (build -> save -> solve): ValueError : Plan needs more than 1 years.
build (one event, same case) refuses: the plan would run 2026-2026: not more than one year,
    and a plan needs more than one (the last life horizon is at the plan start)
```

The same case with one event is refused correctly -- the check is right, its placement is
not. Suggested fold: hoist `check_death_window(scenario)` above the `if not events:` early
return (it reads only the scenario's case and events), or call it from `save_run`'s door as
well; extend `tests/library/test_builder.py`'s `TestDeathEvents` with the no-events case.

### AF2 (low): AE2's fold refuses the tornado's own values key -- every sensitivity member's "Values" round-trip is now broken

The fold makes `ui/variant_tables.member_values` refuse any dimension outside
`variants.DIMENSIONS` ("a typo is refused"). But the tornado -- the same increment --
stores its members' values as `{"mover": label}` (`library/tornado.py` 248, read back at
`ui/Run.py` 626), and `grid_layout` deliberately keeps unknown dims
(`variant_tables.py` 284: `sorted(d for d in dims if d not in DIMENSIONS)`). The Members
section's "Values" popover (`ui/Collections.py` 418-428) pre-fills
`values_text(member.values)` and saves through `member_values`, so for a sensitivity
member the text is `mover: returns -1 point` and **any Save -- even unchanged -- is
refused** with "not one of the dimensions [...]": the one editor of member values cannot
round-trip the values the library itself writes. A hand-added member of a sensitivity
collection likewise cannot be given a mover value to line up with the bars.

Probe (`probe1.py`):

```
values_text: mover: returns -1 point
member_values refused: not one of the dimensions ['place', 'year', 'financing', 'work',
    'claim', 'death', 'sequence']: 'mover: returns -1 point'
grid_layout(['mover']) keeps the unknown dim: ([], ['mover'])
```

`tests/ui/test_variant_tables.py`'s `test_values_text_round_trips` covers the DIMENSIONS
case only. Suggested fold: validate against the values keys the library writes
(`DIMENSIONS` plus the tornado's `mover`), or against the collection's own member dims; add
the tornado member's round-trip to that test.

### AF3 (low): the `sequence` dimension parses `event:<id>` placements without the scenario's ids, so an id ending in `-<digits>` is silently misread

`variants._start_ref` (75-80) calls `builder.parse_year_ref(value, where)` with no `ids`,
while `ui/Scenario.py` (328) passes them. `parse_year_ref`'s own contract is review X5's:
"a known id wins, else the trailing `+<n>` / `-<n>` is the offset" -- without ids every
id ending in `-<digits>` takes the second branch. The synthetic suite's own event ids are
shaped this way (`work-ari-2026`), and the Scenario page shows the id column to copy from.

Probe (`probe1.py`, `start: "event:work-ari-2026"` in the make-variants sequence table):

```
Scenario.py's call (ids known): {'anchor': 'event', 'id': 'work-ari-2026', 'offset': 0}
variants._start_ref (no ids):   {'anchor': 'event', 'id': 'work-ari', 'offset': -2026}
```

The value passes `_check_value`, `_apply_value` stores the wrong ref in the child's
downturn event, and the failure surfaces only at `resolve_years` ("event years that cannot
be resolved (a missing person or event, or a cycle)") -- or, when the scenario also holds an
event literally named `work-ari`, as a silently wrong placement that the window checks
catches only by luck. Suggested fold: pass
`ids=[e.get("id") for e in _events(scenario)]` from `_check_value`/`_apply_value`/
`_value_label`, as `ui/Scenario.py` does; a test with a `-<digits>` event id.

### AF4 (low): the bracket view's IRMAA edges in the last two plan years are the wrong year's, labeled as the right one's

`brackets.bracket_view` sets `n_prem = min(n + 2, N - 1)` (line 88) and labels each edge
`premium_year = p.year_n[n_prem]` (line 91). For the last two plan years the real premium
year (m+2) is outside the plan, and the clamped stand-in is presented as fact: the rows
carry a `premium_year` the year's MAGI does not set, and the edge amounts are the stand-in
year's tier thresholds. The module's own docstring promises "the premium year's tier amounts
-- the MAGI of year m sets the premiums of m + 2", and `thresholds._irmaa_entries` (the
convention the docstring cites) skips exactly these years (`if n_prem >= N ... continue`).
The run page's chart steps its "IRMAA tier 1" line through all years, so the last two are
wrong on screen and in the durable `plan.json`.

Probe (`probe1.py`, `FakePlan`, 12 plan years 2026-2037, gamma 1.025^n):

```
tax year 2035: tier-1 229036.25, labeled premium_year 2037 (m+2 would be 2037)
tax year 2036: tier-1 223450.0,  labeled premium_year 2037 (m+2 would be 2038)
tax year 2037: tier-1 218000.0,  labeled premium_year 2037 (m+2 would be 2039)
```

Suggested fold: skip the IRMAA edges for years whose premium year leaves the plan (as
`thresholds._irmaa_entries` does), or keep them with `premium_year: null` and a
"no premium year inside the plan" note; pin the last rows in `tests/plan/test_brackets.py`.

### AF5 (low): AE3's fold saves the sweep but its own summarizer cannot read the file back

The fold writes the sweep result to `regret.json` ("the per-scenario curves
`summarize_conversion_regret` reads", `447f6f49`'s message) and the summary to record.json.
The data is all there, but `summarize_conversion_regret(json.load(regret.json))` raises:
`lift_regret_baselines` coerces `v_at` to an array for its own use and writes `v_star`,
`x_star` and `v_star_lift` back into the copy it returns -- but not `v_at`, so
`summarize_conversion_regret` (stresstests.py 1024, `result["v_at"][ok, :]`) indexes a JSON
list with a tuple. AE3's own rationale for the fold -- "re-plotting the curves or
re-summarizing with other bands ... needs the per-scenario data" -- is therefore still
blocked after the fold: the saved sweep summarizes only through hand-rolled coercion.

Probe (`probe3.py`: a 2-scenario x 3-grid sweep, `_NumpyEncoder` round trip):

```
fresh (ndarrays) summarizes: valley {'x': 25000.0, 'mean_regret': 250.0}
RE-SUMMARIZE FROM THE SAVED FILE RAISED: TypeError : list indices must be integers or
    slices, not tuple
```

(Nothing in the product loads `regret.json` today -- the run page reads the summary from
record.json -- so the impact is on the documented follow-up use only.) Suggested fold: one
line in `lift_regret_baselines` (`out["v_at"] = v_at`) or `np.asarray` where summarize
indexes, and a test that summarizes a JSON round trip of the sweep.

### AF6 (nit): `member_values` keeps the last of a repeated dimension, silently

`member_values("year: 2027; year: 2029")` returns `{"year": 2029}` (probe1): the second pair
overwrites the first with no word. The fold's own rule two lines up is "a typo is refused"
(AD6); a repeated dimension is at least as likely a typo and is cheaper to refuse than to
resolve last-wins. Suggested fold: refuse a dimension given twice, with the pair in the
message.

### AF7 (nit): `presets.py` still says the preset imports the sweep from `fork-notes/`

`src/owlplanner/library/presets.py` 48-49: "The same implementation
`fork-notes/synthetic/run_suite.py` runs; the preset imports it from `fork-notes/` (moving
it into `src/owlplanner` stays open)." The tree's move (`bc4e38ec`, outside the increment's
diffs) put the sweep in `owlplanner.work_sweep` and updated the bullet's own first line (44)
and `worker._load_work_sweep`, but missed this sentence -- the module now contradicts
itself, and the move it defers has happened. Suggested fold: reword to the shared
`owlplanner.work_sweep` import (the move commit's own "live doc references updated" list).

### AF8 (nit): the 0% gains edge's measure is the one the view does not name

`brackets.py` 114 puts `gains_edge_0` (`tx.capGainRates[status][0]`, the base-year 0%->15%
edge) in the row beside `ordinary_taxable_income`, but the two are different measures: the
model edges the gains on the QDCG worksheet's line-1 income, `G_n + e_n + max(Q_n, 0) -
ded` (`thresholds._gains_entries`, itself a fix from step-3 review 2 Q1 -- "a year whose
ordinary income leaves deduction unused gives gains more 0% room than `G_n + Q_n` says").
The module docstring (14-17) enumerates the other measures ("the ordinary edges ... G_n,
the IRMAA and ACA lines against MAGI") and omits this one; the row offers nothing that says
what `gains_edge_0` is measured against. The chart does not draw it, so the misreading is
available in `plan.json` and the per-year table data only. Suggested fold: name the measure
in the row (a `gains_edge_measured_against` note or the docstring) as the other lines do.

## Checked and not a finding

- **The AE3 split itself** (record.json's summary, `regret.json`'s sweep): `results.build_record`'s
  docstring, the run page's caption and the fold now agree on which file holds what; the
  `regret` block's `{"error": ...}` shape on a failed sweep keeps the base solve (worker's
  try/except, `record.json` says why). Only the re-summarize path fails (AF5).
- **The `death` and `sequence` dimensions' combination rules**: one `death` value sets one
  person and the dimensions are dict-keyed, so no product can stack two deaths; the fold's
  `check_death_window` overlays the events' deaths plus the candidate at each door
  (`variants._check_value`, `tornado._death`), and the parent-scenario check is therefore
  complete; the `sequence: None` "no downturn" value drops the overlay and correctly bypasses
  the table-run refusals.
- **`check_death_age`'s boundary** (`int(age) < start - birth`): a death at the age one is
  now is a one-year horizon for that person and is the AE1 review's own call; the window
  check covers the case where it is the last horizon.
- **The tornado's rate movers** (`tornado._shift_rates` against `builder.plan_rates_table`):
  the transforms reset only for generated rows; a hand table keeps its case's transforms
  (review 1 cleared this; re-read and agree). `_obbba`'s "already assumes it" default (2032)
  matches the model's (`plan.yOBBBA = 2032`, `config/schema.py` 190).
- **`tornado.bars` and `result_of`**: `grid.latest_result` returns only solved results, so
  `view.score`'s None path is the no-result row (sorted last) and `base` is never an unsolved
  score; `validate(child)` outside `tornado_variants`' try cannot fire for these movers
  (`_check_case_values` refuses only None/non-finite, which the edits cannot produce).
- **`aca_table_year`**'s knob: review 1 cleared the round trips and the five call sites;
  `_aca_table`'s pinning matches its docstring (spot-checked).
- **The conversion layer in the chart**: `Plan.G_n` includes the Roth conversions (plan.py's
  `taxable_income` constraint adds `vm["x"]` into `sum_t f_tn`), so "income ex conversions"
  stacked with the conversion layer is the bracket base exactly; the caption's measures
  (IRMAA/ACA against MAGI) match the model's.
- **The 400% FPL "cliff" label** matches the model's current applicable-percentages tables
  ("No cap above 400%: full SLCSP (no PTC)", tax_federal 195-212); the Medicaid/credit-start
  lines follow `_ACA_MEDICAID_RATIO` and the PTC floor.
- **`_regret_sweep`'s call shape and size**: `runConversionRegret(...)`'s keywords exist as
  passed; `yend = year_n[0] - N_n` is `run_conversion_regret_sweep`'s own clamp ("histYendMax",
  stresstests.py 790); `REGRET_N_SCENARIOS = 18`, `REGRET_N_GRID = 7`, `milp_downgrade=True`
  are exactly `ui/owlbridge.REGRET_PRESETS["Quick look"]`.
- **`_ages_thorough`'s arguments** (`no_loop=True, decider="bb", gap=1e-5, eta=[]`) match
  `work_sweep.run_variant`'s stages (a + c, the loop search and the deposit-split check off);
  `best` is months and comes back as years for `fixed_ages`; `scores.json` is a one-row list,
  the shape `agemap.parse_scores`/`work_sweep --json` use.
- **R4** holds for the new presets: `_FORCED["regret"] = {"withSSAges": "fixed"}`, and the two
  Ages presets force nothing.
- **The save dialogs' "Collection" field** (`ui/Library.py`, `ui/Scenario.py`): an identical
  save joins the run it is (`result.identical_to`), `add_member` is idempotent and keeps an
  existing member's values on re-add from the Collections page.
- **The `sequence` dimension's table refusals** (a nameless sequence with a placement, a
  placement without a sequence, a run with a hand table) match `builder._check_table_events`;
  review 1 cleared the empty-cell reading.
- **The claiming-age map's sources and the `scores.json` artifact**: review 1 cleared the
  lookup order; the run page's "the newest 'Ages, thorough' solve" note matches
  `results/*/scores.json` being written only by that preset.

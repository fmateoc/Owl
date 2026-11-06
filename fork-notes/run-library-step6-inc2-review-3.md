# Run-library step 6: third review of the second increment (2026-11-06)

Independent review of step 6's second increment as it stands on `main` / `claude/great-galileo-j51nry`
at `37dfad4` -- the four build commits (`0bc64ca0`, `532a8016`, `6a67936a`, `06baba60`), the
`work_sweep` move, the folds of AE1-AE3, AF1-AF8 and the whole-step review's AG1-AG7/AG9-AG11,
and the two commits after them (`81ee26a`, the 2027 benchmark-jump mover; `a4fb24d`,
`aca_table_year` removed). Read against `run-library-design.md` 8.1, 9.3, 14.1 (I2, I8, I9,
I11) and R2/R4. The earlier reviews of this increment (AE, AF) read it before the AG folds and
the benchmark-jump mover; this one reads mostly what they did not see: the new mover, the AG
folds' code, the regret and "Ages, thorough" paths end to end against their consumers.
Findings **AH1-AH6** (1 medium, 4 low, 1 nit); prefix AH because AC-AG are taken. None repeats an
earlier item; AG8 (death and sequence judged as choices), which the user left standing, is
not re-raised.

Environment: Linux, Python 3.11 (`uv sync`), HiGHS only. **Nothing in `src/`, `ui/` or
`tests/` was changed by this review.** The probes are scripts in the session's scratchpad
(`ah_p1_jump.py` ... `ah_p4_requeue.py`, `ahtests/test_ah_regret_curve.py`; the AppTest probe
was copied into `tests/ui/` for one run, to reach the page tests' fixture, and removed); the
synthetic cases are `make_cases.py`'s (39 workbooks, 46 scenarios), written to the scratchpad
and solved on 2026-11-06 in plan year 2026.

## What was run

| Command | Result |
|---|---|
| `pytest -n 3 tests/library tests/ui tests/plan/test_brackets.py tests/tax/test_aca.py tests/stochastic/test_regret_sweep.py` | **976 passed** (2:00) |
| `flake8 src tests ui --max-line-length=120`, `ruff check src tests ui` | only the upstream items CLAUDE.md lists (E301/E304 in `test_spending_bequest_frontier.py` / `test_spending_units.py`; B905 in `localsearch.py`, `test_local_search.py`, `test_roth_maturation_losses.py`, `Run_Options.py:260`) |
| probes (below) | AH1-AH6 reproduced; the suspects under "Checked and not a finding" cleared |
| full suite, `check_library_*.py` | not run (PROGRESS records 4380 passed / 1 skipped on this tree, `check_library_builder.py` 46/46, `check_library_roundtrip.py` 39/39) |

## Findings

### AH1 (medium): "Ages, thorough" publishes a looser solve than the plan its sweep proved

The preset's sweep scores every whole-year pair by branch-and-bound at gap 1e-5
(`work_sweep._score_bb`: `breakpointMethod="branch-and-bound"`, `gap=1e-5`), then the worker
solves once more at the decided ages under `resolve_options("ages_thorough", ...)`, which forces
nothing (`presets._FORCED["ages_thorough"] = {}`): the case's own `[solver_options]`, with no
`gap`. Under `withMedicare = "optimize"` (the template's and the synthetic household's) that is
`plan.py`'s loosened `MILP_GAP` (3e-3). The published result -- the headline score, `plan.json`,
the workbook, the run's comparisons -- is that solve, not the plan the sweep proved, and the
run page says otherwise: "picked ... from N candidate(s), scored at fixed ages under the case's
own model" (`ui/Run.py:426-429`; true of `ages`, not of `ages_thorough`).

Measured (`ah_p2_thorough.py`: the synthetic baseline `Case_ari+noa.toml`, ages 70/70, the two
solves as the worker and `work_sweep.score` run them):

```
work_sweep cell (BB gap 1e-5): value 165,361.78 proved True gap 9.98e-06 (1271s)
final-solve options: {'breakpointMethod': None, 'gap': None, 'withMedicare': 'optimize', 'withACA': 'loop', 'withSSAges': 'fixed'}
worker final solve: value 164,153.49 gap 0.000683 method branch-and-bound (IRMAA) disc_y1 111,653.49 (12s)
```

The published plan is 1,208.29 below the cell the sweep proved at the same ages: 0.74% of the
objective and, since the objective here is the essential lines plus the discretionary score
(164,153.49 - 111,653.49 = 52,500.00), 1.08% of the score (inferred: the score of the proved
cell is not in the sweep's `METRICS`). That is outside the 1% band, and the record calls the
published solve proved at gap 6.8e-4 (`view.method_kind`: "branch-and-bound" in the method),
so a comparison reads it as accurate to about 112 dollars. The claiming-age map beside it shows
the sweep's value for the same cell. The preset's purpose is the thorough decision (29-51 min
per variant); its headline throws away the last 1% of it for a 12-second solve.

Suggested fold: solve the decided ages with the sweep's own scorer options (branch-and-bound
at the sweep's gap, as `_score_bb` builds them: `_FORCED["ages_thorough"] =
{"breakpointMethod": "branch-and-bound", "gap": 1e-5}` applied to the final solve only, or
reuse the decided cell's plan), so the published plan is the one the map's best cell scores;
and say on the run page which model scored the candidates for each preset. A test: the final
solve's options of an `ages_thorough` job carry the sweep's gap.

### AH2 (low): the 2027 benchmark jump reads a downturn run's inflation without its overlay

`tornado._benchmark_growth` (`tornado.py:183-196`) computes the factor the model grows
`slcsp_annual` by as `builder._gamma(case, rates_rows=table["rows"])` with `case` the
scenario's **hand** case. `config_to_plan` uses `rates_rows` only when the case's method is
`table` (`plan_bridge.py:211`), and a downturn run's hand case keeps its own method (the
builder sets `table` on the case it builds, `builder.py:805-806`). So for a downturn run the
mover divides the published figure by the case's own inflation path, while the solve reads
the overlaid one: the plan's benchmark in the published year is not the published amount.
The docstring says the opposite ("the run's rates table when it has one"), and `build`'s own
nominal amounts get this right (`builder.py:879` calls `_gamma` on the case after the method is
set).

Probe (`ah_p1_jump.py`: the synthetic `yonkers-2027-cash` scenario; the child's case and
table through `builder.build` / `builder.rates_table`, the 2027 benchmark as
`slcsp_annual x gamma[1] x 1.015`):

```
plain                          slcsp_annual 24.2376 -> plan's 2027 benchmark 25.290 (published 25.29)
downturn poor-decade at 2026   slcsp_annual 24.2376 -> plan's 2027 benchmark 26.744 (published 25.29)
```

The bar then measures a 2027 benchmark 5.7% above the published one (the 1973 window's
inflation in 2026 instead of the case's 2.8%). Only a downturn placed before the published
year moves it; a hand table run is unaffected (its case's method is `table`). Suggested
fold: build the gamma from the built case (`builder.build(scenario)[0]` with the table, as
`build` does) or set `rates_selection.method = "table"` on the copy before `_gamma`; a test
on a downturn run at the plan start.

### AH3 (low): the benchmark jump judges the marketplace start on the hand case, not the case the run solves

`_benchmark_jump` refuses when "the case's marketplace years start before the published
year", reading `aca_settings.aca_start_year` from the scenario's hand case
(`tornado.py:215`). A run with work events solves with the **generated** value (`build`:
`aca_start_year = last full-time work year + 1`, `builder.py:956-958`), which a page save keeps
out of the hand case (`casefiles._drop_generated_case` puts the hand value back). A run whose
hand case holds no `aca_start_year`, or an older value, is skipped with a false reason:

```
hand aca_start_year removed: built case's aca_start_year 2027; mover: ["the 2027 benchmark jump:
    the case's marketplace years start in 2026, before the published 2027 benchmark: scaling
    slcsp_annual would move 2026 too"]
hand aca_start_year 2026:    built case's aca_start_year 2027; mover: [same refusal]
```

(`ah_p1_jump.py`, the same scenario.) The converse also holds: a hand value later than the
generated one lets the mover through when the solved plan has marketplace years before the
published one (it then moves them too, which the refusal exists to prevent). The synthetic
household and the template carry a hand 2027 equal to the generated one, so neither shows
there. Suggested fold: read the start year from `builder.build(scenario)[0]` (the case the run
solves); a test with the hand value removed.

### AH4 (low): the regret curve is never drawn -- the page reads `by_grid`, the summary says `regret_by_grid`

`ui/Run.py:349` draws the curve from `regret.get("by_grid")`, but
`summarize_conversion_regret` names the list `regret_by_grid` (`stresstests.py:1131`). The
chart is therefore always skipped; the caption under it (AG7's fold) and the expander's JSON
are what the page shows. `tests/library/test_worker.py:335` builds its canned summary with
the invented key `by_grid`, so nothing caught it; AG7's page test uses the real summarizer
but checks the caption only. Same class as AG7, missed in the same section.

Probe (`ahtests/test_ah_regret_curve.py`: the real summarizer on a two-scenario sweep, in a
result's `record.json`; AppTest of the Run page, plotly charts counted and the one whose y-axis
says "mean regret" looked for):

```
rename=False: 6 charts, regret curve drawn: False     # the summarizer's own keys
rename=True:  7 charts, regret curve drawn: True      # regret_by_grid renamed to by_grid
```

Suggested fold: read `regret_by_grid`; the worker test's canned summary from the real keys,
and the AG7 page test asserting the chart.

### AH5 (low): one member with only an exact-LP result puts a whole decision collection on the exact LP

AG5's fold (`grid.member_results`) switches every member to its exact-LP result as soon as
**any** member has an exact-LP result and nothing else. The tornado's children are that shape,
but so is an ordinary "decision" member whose local-search solve is still running (its
`decision_exact` companion finishes first) or failed. Then every cell of a decision grid is an
exact-LP number -- including the members whose local-search result is there -- and the page's
caption explains it as "some members (the sensitivity runs) have no other"
(`ui/Collections.py:336`). While a solve runs this flips back once it finishes; after a failed
local search it stays.

Probe (`ah_p3_member_results.py`: members a and b with a decision and a decision_exact result,
member c with a failed decision solve and a solved exact companion):

```
exact: True {'a': '..._decision_exact', 'b': '..._decision_exact', 'c': '..._decision_exact'}
```

Suggested fold: switch only when the collection is the tornado's (its reference run's
"Sensitivity" collection, or members whose only results are `decision_exact` **by preset**),
and otherwise show such a member as "no headline result yet (its exact-LP companion solved)";
or keep the rule and make the caption name the members that caused it.

### AH6 (nit): "run again" leaves the previous attempt's `regret.json` and `scores.json`

`JobRecord.requeue` moves aside `summary.json`, `plan.json`, `Results.xlsx` and `plan.pkl`
(`results.py:472-473`), the list from before step 6; the two artifacts step 6 added stay.
N4's rule is that "the folder starts clean for the new attempt", and the claiming-age map reads
`results/*/scores.json` from the newest folder without looking at its record
(`ui/Run.py:219-224`), so an interrupted "Ages, thorough" attempt's map outlives a failed
re-run in the same folder. The window is narrow (a worker dying between the publish and the
record), so this is a nit.

Probe (`ah_p4_requeue.py`: an interrupted job folder holding every artifact, then `requeue`):

```
after run again: ['regret.json', 'scores.json', 'status.json', 'status.lock']
```

Suggested fold: add `REGRET_JSON` and `SCORES_JSON` to the list (one constant of every
published artifact, shared with `_publish_results`, would keep them in step).

## Checked and not a finding

- **The benchmark jump on the plain synthetic run** (`ah_p1_jump.py`): `slcsp_annual` 20.84 ->
  24.2376, and the built child's 2027 benchmark is 25.290, the published figure to the cent (the
  `81ee26a` measurement, reproduced). Only the downturn and hand-start cases (AH2, AH3) miss.
- **`plan_to_config` writes the published pair only when `slcsp_annual > 0`**: the same
  convention as `aca_start_year` beside it, and the mover refuses a case without a benchmark
  premium anyway.
- **Member values with colons in their labels** (`values_text` -> `member_values`): a sequence
  label "crash-30 at age:Ari:86", a claim label "Ari: let Owl choose / Noa 70y0m" and the
  tornado's `mover: none (this run)` round-trip unchanged (`partition` splits at the first
  colon only; run).
- **The Scenario page's death rows**: a blank id, a blank person and a second death for one
  person are each refused by `validate_events` with a named message (run).
- **A stale tornado base**: after a code change, "Make the sensitivity runs" re-solves the
  children but not a base that already has an exact-LP result; `compare.flags` (shown through
  `tornado.bar_flags`) names different commits and days, so the mix is flagged, not silent
  (read).
- **The AG folds re-read**: AG1's units (`in_percent` defaults to true in
  `rate_models/table.py`, as `_shift_rates` assumes), AG7's `mean_regret` caption, AG9's names,
  AG10's `person`, AG11's per-item cancel check, AF4's IRMAA edges (`n + 2 < N`), AF5's
  `v_at`, AF6's repeated-dimension refusal. No defect found in them beyond AH4 (the chart
  beside AG7's caption) and AH5 (AG5's switch rule).
- **R4 for the new presets**: `regret` forces `withSSAges = "fixed"`, the two Ages presets
  force nothing; `ages_thorough` on a case with fixed ages skips the sweep and solves as
  `custom` (read).

## Not checked

- An "Ages, thorough" or "regret" job end to end through the worker: AH1 reproduces the two
  solves the worker and `work_sweep.score` run, at one age pair; a full sweep is 29-51 min per
  variant.
- The full suite and the `check_library_*.py` scripts (not re-run; PROGRESS records them on this
  tree).
- A browser session of the pages (AppTest only).

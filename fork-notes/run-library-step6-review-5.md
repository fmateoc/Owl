# Run-library step 6: fifth review of the whole step (2026-11-06)

Independent review of run-library build step 6 **as a whole** on `claude/modest-gauss-6hg9z6`
at `59bc8d9` (= `main`: `e898f699..59bc8d9`, the core, the second increment, the seven earlier
reviews' folds AC-AI). It reads against `run-library-design.md` sections 4, 8.1, 9.1-9.3, 14
(I2, I7, I8, I9, I11) and R2/R3/R4. The earlier reviews (`run-library-step6-review.md` AC,
`-review-2.md` AD, `-review-3.md` AG, `-review-4.md` AI, `run-library-step6-inc2-review.md` AE,
`-inc2-review-2.md` AF, `-inc2-review-3.md` AH) are not repeated; the items they left standing
(AC8-AC10, AD7-AD9, AG8) are not re-raised. Earlier reviews read the tornado on hand-written
records or one mover at a time; this one runs **every mover through the real worker** and
compares the bars with the same movers under the case's own model, and runs the per-request
jobs (`regret`, `ages`) end to end. Findings **AJ1-AJ4** (2 medium, 1 low, 1 nit); prefix AJ
after AC-AI.

Environment: Linux, Python 3.11 (`uv sync`), HiGHS only, Streamlit 1.66.1 from the lock file.
**Nothing in `src/`, `ui/` or `tests/` was changed by this review.** The probes are scripts in
the session's scratchpad (`libhelp.py`, `r1_regret_warnings.py` ... `r6_past_trial.py`); their
outputs are pasted below. Each builds a fresh library in a temp folder from `make_cases.py`'s
`scenarios.json` (39 workbooks, 46 scenarios, regenerated this session) and solves through
`library.worker.run_job`, as `check_library_variants.py` does. All solves on 2026-11-06, plan
year 2026.

## What was run

| Command | Result |
|---|---|
| `pytest -n 3 tests/library tests/ui tests/plan/test_brackets.py tests/tax/test_aca.py tests/stochastic/test_regret_sweep.py` | **1004 passed** (2:11) |
| full suite (`pytest -n 3 -q`) | **4408 passed, 1 skipped** (13:21, Linux, run beside the probes; the count PROGRESS records after the AI folds) |
| `flake8 src tests ui --max-line-length=120`, `ruff check src tests ui` | only the upstream items CLAUDE.md lists (`test_spending_bequest_frontier.py` / `test_spending_units.py` E301/E304; B905 in `localsearch.py:244`, `test_local_search.py:288`, `test_roth_maturation_losses.py:49`, `Run_Options.py:260`) |
| probes r1-r6 (below) | AJ1-AJ4 reproduced; four suspects cleared |
| `check_library_variants.py` (reduced or `--full`) | not run (PROGRESS records 5/5 for both) |

## Findings

### AJ1 (medium): "medical inflation +2 points" is solved in a model with no Medicare premiums

The tornado solves every child and the run itself under `decision_exact` (design 14.1, I9:
"under the exact LP for speed"; review AG2 made both sides exact-LP). That model is
`agesearch.EXACT_GROUP` = the loop with **`withMedicare = "none"`**, SS taxability 0.85 and
LTCG exact (`agesearch.py:44-45`). `medical_inflation_excess` grows three things in Owl
(`Plan._medical_n`, `plan.py:2108`): Medicare premiums (`tax_federal.mediCosts` /
`mediVals`), the marketplace benchmark (`acaCosts`), and `other_medical_expenses` when the
budget has no `medical` line. With Medicare off, the first is gone; the household's budget
has a `medical` line, which grows at its own real rate and not with the excess
(`make_cases.py:191`); so the mover reaches only the three marketplace years (2027-2029).

Probe `r4_medical_mover.py` (`yonkers-2027-cash` and its `medical+2` child, the same two
scenarios solved under three presets) and `r5_movers_by_model.py` (every mover):

```
decision_exact  (16 s) method branch-and-bound (LTCG): base 114,428 medical+2 114,344  delta -83
     aca_today                                             55,334 ->         57,372
     medicare_today                                             0 ->              0
quick           (2 s) method loop: base 108,959 medical+2 107,058  delta -1,901
     aca_today                                             55,334 ->         57,372
     medicare_today                                       154,137 ->        211,410
decision        (629 s) method local search (SS, IRMAA, ACA, LTCG, NIIT, STAR): base 110,385 medical+2 108,573  delta -1,813
     aca_today                                             37,646 ->         38,063
     medicare_today                                       152,625 ->        209,807
```

```
mover                           decision_exact delta    medicare           quick delta    medicare
(this run)                                        +0           0                    +0     154,137
returns -1 point                              -7,914           0                -7,151     152,625
inflation +1 point                              -986           0                -1,086     152,625
medical inflation +2 points                      -83           0                -1,901     211,410
condo price +10%                              -4,632           0                -4,374     154,137
benchmark premium +10%                          -226           0                  -209     154,137
benchmark premium -10%                          +229           0                  +557     152,625
the 2027 benchmark jump                         -369           0                  -331     154,137
the 2032 reversion                            -2,846           0                -2,719     152,625
Ari dies at 80                                +3,525           0                +3,460     121,741
Noa dies at 80                                +3,525           0                +3,458     121,741
```

The +2 points move lifetime Medicare premiums by +57,182 (local search) to +57,273 (loop)
today's \$, and the score by -1,813 (local search; outside its 1% band of ±1,104) or -1,901;
the bar shows -83, "resolved" at ±0, sorted last of ten. Every other mover lands within about
10% of its exact-LP bar under the loop, except "benchmark premium -10%" (+229 vs +557, inside
the loop's ±1,090 band), so the model gap is specific to this mover: the one input whose main
channel the exact model removes. The mover's note ("medical_inflation_excess, 2 points
higher") and the page's caption say nothing of it. The design's I9 list names the mover and the
model together, so the conflict is the design's; for the household, Medicare premiums run from
2029-2030 to the plan's end in 2053, and they are what medical inflation moves.

Location: `library/tornado.py` (`movers`, `_medical_plus_2`) and `ui/Run.py` (the button
queues `decision_exact` for every child). Fold options, the user's call:
(a) solve the medical mover (and the run's own base for it) under a model with Medicare --
the exact model with `withMedicare = "loop"` (still an LP per iteration) or `decision`;
(b) skip it under the exact LP with the reason ("the exact LP has no Medicare premiums: this
mover moves only the marketplace years"), as unreachable movers are skipped (AG4);
(c) keep it and say so in its note and on the bar.

### AJ2 (medium): a `regret` job's record carries the sweep's 125 scenario warnings as its own

`Worker._solve` runs the regret sweep after publishing the base results, then writes
`record.json` with `warnings=sorted(self.tee.warnings)` (`worker.py:513`). The sweep re-solves
the plan on clones (`stresstests.py:849`), and `clone` without an expectancy hands each clone
the **plan's own logger** (`plan_bridge.py:675`), which writes to the worker's log tee. The
sweep turns verbosity off, so the `Iter:` lines (`vprint`) stay out, but `mylog.print` is
unconditional: every scenario's WARNING line reaches the tee, which is not `quiet` there (the
`ages` stages set `quiet`, `worker.py:298`; the sweep does not), and lands in the record as a
warning of the published plan. `view.quality_notes` (`view.py:258`) reads those warnings, and
the Run page shows each matching one as a problem with the plan.

Probe `r1_regret_warnings.py` (`yonkers-2027-cash`; the same base solve twice through the
worker: `custom` with the ages fixed, and `regret`, which is the case's own model with the
ages fixed, then the sweep):

```
== custom: state done, 15 s, status solved
   method: branch-and-bound (IRMAA) | iterations: 16 | convergence: oscillatory (cycle length 2)
   warnings (1):
     - Taxable Social Security did not settle: this plan's own income implies $2,232 of different ...
   quality line: settled
== regret: state done, 77 s, status solved
   method: branch-and-bound (IRMAA) | iterations: 16 | convergence: oscillatory (cycle length 2)
   warnings (126):
     - 1930 | Taxable Social Security did not settle: this plan's own income implies $1,458 ...
     ...
     - 1945 | Exiting loop on maximum iterations.
     - 1946 | Exiting loop on maximum iterations.
     - 1947 | Exiting loop on maximum iterations.
     - 1955 | Exiting loop on maximum iterations.
     - 1970 | Exiting loop on maximum iterations.
     - 1977 | Exiting loop on maximum iterations.
     - 33% (case 12 of 36)2026-11-06 20:41:47 | WARNING | plan:_scSolve:7859 | 1955 | Exiting loop on maximum iterations.
   quality line: 1945 | Exiting loop on maximum iterations.
   solve.log WARNING lines: 146
```

Same plan, same method, same 16 iterations; the regret solve's page reads "Quality: 7
problem(s)", each "Exiting loop on maximum iterations." of a historical scenario (the
thread tag `1945 |` is the sweep's scenario year; the sweep solves in loop mode,
`milp_downgrade=True`), where the `custom` solve reads "settled". One of the 126 warnings is
the base plan's own. The last line also shows the sweep's progress meter (no newline)
fused onto a log line. The regret summary in `record.json` has its own per-scenario
convergence counts (`convergence`, `n_failed_baselines`), so nothing is lost by keeping the
scenario lines out of `warnings`.

Location: `library/worker.py` `_solve` / `_regret_sweep`. Suggested fold: set `tee.quiet`
around the sweep (as the `ages` stages do: lines still go to `solve.log`, the cancel check
still runs), so `warnings` stays the base solve's; a test that a regret job's record has the
`custom` solve's warnings.

### AJ3 (low): under maxBequest, the tornado's bars and the grid's cells add the home to the score

`view.score` is `final_bequest_today` under maxBequest (`view.py:87`, run_suite's rule), which
**holds the home**. Step 3's W5 fixed R3's lead rule for this (`compare.lead_verdict` reads the
savings left and the home there), but step 6's other readers still use the score: the
tornado's bars and their sort (`tornado.bars`, `tornado.py:400`), the grid's bold number
and its star (`grid.grid_view`, `grid.py:127` and `:160`), and the front's "vs the reference"
(`grid.front`, `grid.py:337`); beside the bar (AI4) and under the cell, the home at the end
is shown again.

Probe `r2_maxbequest_tornado.py` (`yonkers-2027-cash` with `objective = "maxBequest"`, the
run and its "condo price +10%" child under `decision_exact`):

```
base      objective maxBequest  score 1,804,807  savings 1,043,946  home 760,861
condo+10  objective maxBequest  score 1,706,985  savings 870,038  home 836,947
tornado bar: {'label': 'condo price +10%', 'delta': -97822, 'tolerance': 0, 'verdict': 'resolved', 'note': 'the reported gap x objective', 'home_delta': 76086, 'home_verdict': 'resolved'}
grid cell ('condo price +10%',) delta -97822 home 836947 home_delta 76086 best True lead trade-off
lead_between(base, condo): {'verdict': 'trade-off', 'note': 'one leaves more savings, the other more home at the end; the two numbers are never added (R3)'}
savings delta: -173908
```

The bar reads -97,822 = -173,908 (savings) + 76,086 (home), with "home at the end +76,086"
beside it: the home counted in both columns, while the cell's colour says "trade-off ... never
added". The household runs maxSpending (no bequest goal), so its tornado and grids are not
affected; a maxBequest case's are. Location: the four readers above. Suggested fold: under
maxBequest the bar's and the cell's number is the savings left (`view.savings_left`, what the
solve maximizes, `view.objective_value`'s own reading), named so; the star and the sort
follow it.

### AJ4 (nit): the Ages preset's stage 2 can score a claiming month already past

`agesearch._trials` (`agesearch.py:115-120`) clips each searched person's neighbour to 62-70
but not to the person's age this month. Owl refuses a *searched* age already past
(`Plan._ssaCheckPastAges`) but reads a *fixed* past age as benefits already being collected,
with no warning, and stage 2 solves at fixed ages. Probe `r6_past_trial.py` (`yonkers-2027-cash`;
Ari born 1964-04-17 is 62y7m on 2026-11-06; stage 2's model, Noa at 70):

```
today 2026-11-06
trials around a pick of Ari 62y9m / Noa 70: [[62.75, 70.0], [62.0, 70.0], [63.75, 70.0], [62.75, 69.0]]
   Ari SS paid 2026-2028 (nominal): [0, 24399, 26618] withheld 2026-2028: [15527, 2280, 0]
Ari fixed at 62.0000 (62y0m): status solved, score 107,004, Ari's SS in 2026 (nominal) 0; claim/past warnings: none
   Ari SS paid 2026-2028 (nominal): [0, 25266, 27563] withheld 2026-2028: [2297, 2361, 0]
Ari fixed at 62.5833 (62y7m): status solved, score 107,381, Ari's SS in 2026 (nominal) 0; claim/past warnings: none
   Ari SS paid 2026-2028 (nominal): [0, 18900, 28350] withheld 2026-2028: [0, 0, 0]
Ari fixed at 63.0000 (63y0m): status solved, score 107,531, Ari's SS in 2026 (nominal) 0; claim/past warnings: none
```

A pick in Ari's first year of eligibility puts April 2026 among the candidates, solved
without a word as an entitlement from April 2026 (15,527 of 2026 benefits, withheld by the
earnings test because Ari has 2026 wages, and credited back through the ARF). Here it scores
lowest, and the synthetic baseline's pick is 70/70, so no harm is shown; a case with no wages
in that year would be paid the past months, and could pick a month that cannot be claimed. `run_suite.py` shares the code.
Suggested fold: clip at the person's age this month (`Plan._ssaCurrentAgeMonths`'s rule) as
well as at 62.

## Checked and not a finding

- **The exact-LP bars' tolerance** (probe `r3_tornado_tolerance.py`, all eleven solves): every
  record reads `branch-and-bound (LTCG)`, `compare.method_kind` "proved", tolerance gap x
  objective (±0 to ±15), so every bar is "resolved"; each loop exits "oscillatory" in 4-5
  iterations with an objective error bar of 0. `run_suite.py` marks `~` only in its `main`
  group (the case's own model; `group_table`, line 422), never in the exact groups, so the
  library's reading matches the suite. (The design's 8.1 calls the exact model "the loop"; R2's "proved" is read from Owl's
  label, which says branch-and-bound as soon as one family has binaries.)
- **"Ari dies at 80" = "Noa dies at 80" to the dollar** (+3,525 under the exact LP; +3,460 and
  +3,458 under the loop): both born in 1964, and the survivor keeps the larger of the two SS
  benefits whichever spouse dies, so the survivor phase is nearly symmetric. Not traced further.
- **The tornado's run folders** `slcsp-10` and `slcsp-10-2` (the slug drops `+`): the run
  names stay distinct (`... slcsp+10`, `... slcsp-10`, AG9); the folder suffix is
  `Library.save_run`'s collision rule.
- **A cancel during the regret sweep** (read, not measured): the sweep's thread pool waits for
  the futures already submitted when `on_scenario`'s check raises, so a cooperative cancel waits
  for the rest of the current phase; the whole sweep took about 60 s here.
- **AD7 qualified**: "Noa: let Owl choose" in a claim dimension makes Noa searched only under
  the Ages presets; under `quick` / `decision` (R4: ages fixed) Noa is held at the case's hand
  age while the label still says "let Owl choose". AD7 stands as filed; noted for its fold.

## Not checked

- `check_library_variants.py` (reduced and `--full`): PROGRESS records 5/5 for both.
- An "Ages, thorough" job end to end through the worker (29-51 min per variant).
- A browser session of the pages (AppTest only); Windows.

## Dispositions (2026-11-06, the user's call: fold AJ1-AJ4; for AJ1, "solve this mover under a model with Medicare")

- **AJ1 folded:** a new solve preset, `exact_medicare` (`presets.EXACT_MEDICARE` = the exact
  model with `withMedicare = "optimize"`, ages fixed), and `Mover.preset`: the medical-inflation
  child and the run's own base for its bar solve under it, every other mover under
  `decision_exact` as before. The model was chosen by measurement (scratchpad
  `f1_medicare_models.py`, the synthetic run and its `medical+2` child): Medicare on the loop
  -1,842 (±0, 18 s for the pair), Medicare priced exactly -1,842 (±198, the reported gap x
  objective, 14 s), the same at gap 1e-4 (±0, 51 s); `"optimize"` at the default gap is what
  local search does with Medicare and states its own tolerance. `tornado.bars` / `bar_flags`
  take {preset: the run's result under it} (one result is still read as the exact-LP base) and
  pair each bar with its mover's preset (`preset_of`); `base_result` / `result_of` /
  `is_current` take the preset. The Run page's button queues the base under every preset its
  children need (`presets_needed`) and each child under its own; the table gives each bar's
  model. `view.record_companion` names both companion presets, so neither is ever a run's
  headline: the Run page's default result, the Compare page's default pair and
  `grid.latest_result` (collections) skip them -- the base's `exact_medicare` solve was its
  newest non-exact-LP result and became its headline (SS pinned at 0.85). On the Collections
  page the medical child, which has no exact-LP result, says where its bar is. Probe
  (`f2_tornado_after.py`, the whole tornado through the worker): "medical inflation +2 points"
  -1,842 ±198, resolved, 6th of 10 (was -83 ±0, last); the other nine bars unchanged; the
  run's headline its `decision` solve.
- **AJ2 folded:** the log tee is quiet during the regret sweep (`worker._solve`): its lines go
  to `solve.log`, the record's warnings stay the base solve's. Probe `r1_regret_warnings.py`
  again: the `regret` job's record has 1 warning, its quality line "settled", as the `custom`
  twin's.
- **AJ3 folded:** `view.first_number` (with `first_number_name` / `first_number_label`): the
  score under maxSpending, the savings left under maxBequest. `tornado.bars`, the grid's cells
  and star (`grid.Entry.first`) and `grid.front`'s "vs the reference" (and its new `first`) read
  it; the Run page's axis and caption and the Collections page's caption name it. Probe
  `r2_maxbequest_tornado.py` again: the bar and the cell read -173,908 (the savings), the home
  +76,086 beside it (was -97,822).
- **AJ4 folded:** `agesearch._trials` takes each person's first open claiming age
  (`Plan._ssaOpenAges`: eligibility, 62y1m unless born on the 1st or 2nd, or this month,
  whichever is later), which `two_stage_ages` reads from the stage-1 plan; no neighbour goes
  below it. On the synthetic case on 2026-11-06: Ari 62y7m, Noa 62y1m. `run_suite.py` shares
  the code.

Tests: 14 new (`test_tornado.py` +5, `test_grid.py` +3, `test_agesearch.py` +2,
`test_presets.py` +1, `test_worker.py` +1, `test_library_pages.py` +1,
`test_collections_page.py` +1) and three re-pinned (the solve-preset list, the button's
queued presets, `is_current`'s stub, which takes the preset). With `src/` and `ui/` stashed,
13 of the 14 new tests failed and the re-pinned preset list with them; the 14th (the medical
child keeps a sensitivity collection on the exact LP) guards AG5's switch and passed before
too. `tests/library tests/ui` + the bracket/ACA/regret tests **1018 passed** (2:44, `-n 2`);
lint only upstream's listed items; full suite **4422 passed, 1 skipped** (11:47, Linux, `-n 4`; 4408 + the 14 new tests; two later edits, a docstring and the tornado axis label's escape, re-checked by the 8 tornado page tests).

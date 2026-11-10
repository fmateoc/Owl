# Performance review (2026-11-10)

The user's request: "review the project from a performance improvement perspective. Look for any
significant opportunities: architectural, algorithmic, memoization, dropping redundant steps."

Report only: nothing in `src/`, `ui/` or `tests/` changed. Measured on the synthetic household
(`fork-notes/synthetic/`), claiming ages fixed at 70/70, HiGHS 1.15.1, this container (4 cores,
Linux), at `abd8b6c`. The scripts are in `fork-notes/performance/`. Each statement below says
whether it was measured, read in the code, or inferred.

## 1. Answer

Solve time is solver time. In a *Careful* solve 344 of 346 s are inside `highspy.run` (71
calls); all of Owl's own Python, the model build included, is under 1%. So nothing in the
Python layer (vectorizing, caching the constraint build, `deepcopy`) can matter for solves, and
no HiGHS option tried made the slow calls faster. What can matter is how many solver calls are
made and how many run at once.

| # | Opportunity | Measured effect | Whose code | Cost |
|---|---|---|---|---|
| P1 | Run several jobs at once (`JobManager(max_parallel=...)`, default 1, never set by the interface) | 4 solves at once: +5% wall each, so about 3.8x the throughput on 4 cores | fork (`ui/libraryjobs.py:95`) | one setting; see the budget caveat in P3 |
| P2 | Local search: skip the node-capped steps in loop iterations where the binaries did not move | same plan to the cent in 6 of 6 variants; CPU -16% to -48% in the 4 that settle, none in the 2 that keep moving; -20% over the six | upstream (`localsearch.py`) | an upstream issue with these numbers, or a fork option |
| P3 | Local search: node cap 1,000 instead of 3,000 (`localSearchStepNodes`, an existing option), with P2 | same plan to the cent in 5 of 6, +\$1.75/yr in one; CPU -46% to -63% in the 4 that settle; -36% over the six | fork preset (`presets.py`) for the option; upstream for the default | a preset value |
| P4 | *Let Owl choose the claiming ages*: the final solve repeats a stage-2 candidate; stage 2 is serial | read in the code, not timed: 1 of 4-6 Careful solves is a repeat (about 6 min here); the others are independent | fork (`worker.py`, `agesearch.py`) | small (P4a), medium (P4b) |
| P5 | *Claiming ages, every pair tried* runs its sweep on a serial pool | read in the code; the same sweep's CLI runs on a process pool | fork (`worker.py:69`) | small |
| P6 | Library and Collections pages re-read every `run.json` once per run shown | 120 runs: Library page 1.5 s per click, 15,480 file reads; quadratic in the number of runs | fork (`store.py:415`) | small |
| P7 | Worker start: 1.5-2.0 s of imports before a 0.5-1 s Quick look | measured | upstream modules | lazy imports upstream; or leave |
| P8 | Test suite: 60 tests are 59% of the worker time | measured under load | 2 fork files (12%), the rest upstream's | `deep` marks on fork tests |

Not worth doing (section 4): solver options, the Python model build, a looser step gap, caching
the what-if parent (already done), the job ticker.

A 36-cell condo grid at *Careful* is about 3.3 hours as the interface queues it today (36 x 331 s,
the average wall time of the six variants measured, one at a time; computed, not run). With P1
alone it is about 50 minutes on four cores; with P1, P2 and P3 about 30 minutes (36 x 207 s / 4),
if the six variants are representative of the grid, which was not checked.

## 2. Where the time goes (measured)

`solve_probe.py`, the variant `yonkers_2027_mortgage`, machine otherwise idle:

| Preset | Wall | In HiGHS | HiGHS calls |
|---|---|---|---|
| Quick look (`quick`) | 0.5-1.0 s | 0.29 s | 15 LPs |
| Exact-model check (`decision_exact`) | 6.2 s | 5.9 s | 6 |
| Exact model with Medicare (`exact_medicare`) | 2.7 s | not split | 5 |
| Careful (`decision`) | 346-349 s | 343.8 s | 71 |

The model has 2,052 columns and 1,906 rows. Building the plan from the case and workbook takes
0.25 s, `plan_to_dict` + `plan_metrics` 0.06 s.

The Careful solve is the loop's own solve (14 iterations, about 5 s) followed by five loop
iterations with a local search inside each. By step, summed over the five (341 s):

| Step | Seconds | Calls | Calls that improved the plan |
|---|---|---|---|
| (b') SS within 4 flips, LTCG free | 142.8 | 5 | 0 |
| (b) SS within 4 flips | 139.1 | 7 | 2 (+557 and +2,138 on an objective of 3.72M) |
| (a') the other families jointly | 32.2 | 5 | 0 |
| (a) one family free (5 families) | 27.0 | 35 | 0 |
| starts (LP or repair) | 0.2 | 5 | |

All twelve (b) and (b') calls stopped at the 3,000-node cap, none with a proof: the first one
ended with a gap of 0.75% against a 0.01% target (HiGHS log: 21 binaries left after presolve,
"Thread count 2 (of 4 threads). Using 1 max workers. Parallel search off"). They are 83% of the
solve. Loop iterations 2, 3 and 4 start from the previous iteration's binaries, find no move, and
cost 58-63 s each for an objective change of \$176, \$74 and \$6 on 3.72M: the loop is waiting for
its fed-back parameters to settle (residual \$51k, \$4k, \$721), and each wait re-runs the capped
steps.

CPU time is 382 s for 349 s of wall: the solve uses about 1.1 cores.

## 3. Opportunities

### P1. Several jobs at once

`JobManager.__init__` takes `max_parallel` (default 1). The only place the interface builds one,
`ui/libraryjobs.py:95`, is `JobManager(Library.open(root))`: every queue runs one job at a time.
`run-library-step2` recorded "the `max_parallel` setting [is] not exposed yet".

Measured: four Careful solves started together took 367, 371, 231 and 136 s of wall for 381, 378,
240 and 137 s of CPU (the last two had lower node caps); the same solve alone took 349 s for
382 s. So four at once cost about 5% of wall each. Resident memory was 252-264 MB per process,
sampled once, 15 s into four solves.

What it changes: *Make variants* with "Queue them when created", the sensitivity tornado, "run
the collection again today", and Careful's own pair (the search and its exact-model companion).
A single what-if is not faster.

Caveat, measured (P3 below): local search's 300 s budget is wall-clock, and most Careful solves
here already run into it. Under four-way load each step takes about 5% longer, so a little more
of the search is cut off. Raise the budget or lower the work (P2, P3) together with P1.

A default of `os.cpu_count() - 1` leaves a core for the browser and the server; not tested for
responsiveness.

### P2. Local search: no capped steps while the binaries stand still (upstream's code)

Prototype (`quiet_patch.py`, an in-memory rewrite of `LocalSearch.solve`, nothing in `src/`): in
a loop iteration that follows one whose search made no move from its LP start, run the LP start
and the (a) steps and skip (b), (b') and (a'). Step (c) still runs.

CPU seconds and first-year discretionary spending, six variants, run one to four at a time (the
first base alone, the second among three, the rest among four). "hits" is how many loop
iterations of the base solve found the 300 s budget spent.

| Variant | Base | hits | P2 | P2 + 1,000 nodes | Spending: base / P2 / P2+1,000 |
|---|---|---|---|---|---|
| yonkers_2027_mortgage | 382 | 0 | 258 (-33%) | 185 (-52%) | 109,150.60 / same / same |
| queens_2031_cash | 349 | 0 | 181 (-48%) | 128 (-63%) | 104,511.03 / same / same |
| yonkers_2034_cash | 320 | 1 | 195 (-39%) | 126 (-61%) | 108,098.01 / same / same |
| queens_2027_arm5 | 333 | 1 | 280 (-16%) | 180 (-46%) | 106,893.12 / same / same |
| whiteplains_2029_mortgage | 318 | 2 | 317 (0%) | 320 (+1%) | 105,853.35 / same / same |
| whiteplains_2038_cash | 318 | 3 | 377 (+18%) | 344 (+8%) | 105,257.53 / same / 105,259.28 |
| Sum | 2,020 | | 1,608 (-20%) | 1,283 (-36%) | |

In the two White Plains variants the search keeps finding moves for three or more iterations, so
the rule rarely applies and the 300 s budget is what ends the search in every version; the time
freed is spent on further rounds (which is where the +\$1.75 comes from).

What the prototype leaves open: it never re-runs the full search once the loop has settled, so a
move that the parameter drift opened in (b) would be missed. In these six it changed no plan. A
confirming full search at convergence would give that back for one more iteration (55-65 s
here), which cuts the saving on the first four variants to roughly -10% to -30% (inferred from
the per-iteration times, not run).

`localsearch.py` is upstream's. By the fork's conventions this is an upstream issue with the
table above and a stock repro; the six variants carry fork features (itemizing, STAR, the budget
profile), so a stock example would have to be measured first. Not drafted.

### P3. The node cap, and the wall-clock budget behind it

`localSearchStepNodes` is an existing solver option; `STEP_NODES["HiGHS"] = 3000` is upstream's
default, chosen on the shipped examples ("lifting them changes results by 0.07% at most, for up
to 3.3x the time").

Measured without P2: 1,000 nodes gave the identical plan on both variants tried (yonkers_2027
382 -> 240 s CPU, queens_2031 349 -> 219 s); 300 nodes gave \$0.20/yr less on the one variant
tried (382 -> 137 s). With P2: the table above. Every difference seen is under \$3/yr; the
library reads local-search results with a 1% band (about \$1,050 here).

The budget, measured: `TOTAL_TIME = 300` s of wall per solve, tested at the start of each round.
The solve run alone used 341 s of search (its last round started at 278 s). Run four at a time,
4 of the 6 base solves logged "time budget spent" in one to three loop iterations; those
iterations then do their start step only. The effect on the result, on the two variants tried
with the budget lifted (`localSearchTime=7200`, `localSearchStepTime=1800`):

| Variant | 300 s budget | Budget lifted | CPU, lifted |
|---|---|---|---|
| whiteplains_2029_mortgage | 105,853.35 | 105,853.35 | 418 s |
| whiteplains_2038_cash | 105,257.53 | 105,260.34 (+\$2.81/yr) | 688 s |

So a Careful result on this machine can depend on machine speed and load, by dollars. Upstream's
header says the node cap is there "so that the answer does not depend on machine speed or load";
here the time budget binds before it. The message is a debug line (`localsearch.py:363`); a grep
of `src/owlplanner/library` and `ui` for "budget spent" finds nothing, so a result cut by the
budget is not marked in `record.json` or on the Run page. `work_sweep.py` already lifts both
caps for this reason (PROGRESS.md "Phase 5 step 6"); the library's `decision` preset
(`presets._FORCED`) does not.

Two fork-side choices follow, both in `presets.py`, neither built:

- Give `decision` a node cap of 1,000 and a lifted time budget. On the four settling variants
  that is faster than today and independent of load; on the two that keep moving it is slower
  than today (the budget no longer cuts them off; 418 and 688 s at 3,000 nodes, not measured at
  1,000 with the budget lifted).
- Or keep the budget and record that it was spent, so the Run page can say so.

A looser step gap does nothing: `STEP_GAP` 1e-3 instead of 1e-4 gave the same plan in the same
time (378 vs 381 s CPU), because the capped steps end at gaps near 0.7%.

### P4. *Let Owl choose the claiming ages* (`ages`)

Read in the code, not timed (a run is 20-35 min here).

- **P4a, a repeated solve.** `agesearch.two_stage_ages` scores the pick and each searched
  person's pick +-1 year with a full solve under the case's own model (local search for the
  template's options), and returns the ages and scores only. `Worker._solve` then builds the
  plan again at the chosen ages and solves it (`worker.py:317-332`). With no job overrides the options are the same ones
  (`resolve_options("ages", ...)` forces nothing), so the final solve repeats the winning
  stage-2 solve: 1 of 4 Careful solves for a pick at 70/70 (the synthetic baseline's pick), 1 of
  6 for an interior pick. Returning the winning plan from stage 2 drops it. `ages_thorough` has
  the same repeat, documented in `presets.py` ("That final solve repeats one scored plan's
  time").
- **P4b, serial candidates.** Stage 2's three to five solves are independent and run in a `for`
  loop. On a process pool (spawn, as `run_suite.py`) they would take one or two solves' time
  instead of three to five. The cancel check and the log tee are what the loop gives today.

Upstream's own `_ssAgeSearch` also re-solves at the best ages after scoring it on a clone
(`plan.py:7184`); under the exact LP that is under a second, so stage 1 is not worth touching.

### P5. *Claiming ages, every pair tried* (`ages_thorough`)

`worker.py:69` runs `work_sweep.run_variant` on `_SerialPool`; its docstring says "a pool would
work; the worker keeps the sweep serial". The CLI runs the same sweep on a spawn
`ProcessPoolExecutor` (`work_sweep.py:770`), and PROGRESS.md records 94-288 s per scored plan on
chris+pat. With P1 measured at 5% overhead for four processes, a four-process pool should cut
this preset's wall time by a factor near 3.8 (inferred; the preset was not run). If P1 is also
on, the worker's pool and the queue's parallel jobs must share the cores.

### P6. Library pages: one scan per run shown

`Library.get(run_id)` is `for info in self.runs()`, and `runs()` reads every `run.json`. The
Library page calls it once per row (`_run_name`), the Collections page once per member.

Measured on a library of 120 runs with 239 results (`library_bench.py`, `page_profile.py`):

| Page | Rerun | What the profile shows |
|---|---|---|
| Library | 1.50 s | `Library.runs()` called 128 times (15,480 `run.json` reads), 57% of the script; `JobManager.jobs()` 126 times, 36% |
| Collections | 0.58 s | `Library.runs()` 77 times, 72 of them from `Library.get` |
| Queue | 0.35 s, every 2 s | `JobManager.jobs()` 6 times per refresh |
| Run | 0.26 s | |

One scan per rerun (a dict by id passed down, or `get` reading the one folder) would remove
about half of the Library page's time at this size (inferred from the profile's shares, not
built); most of the rest is per-run job reads. At 40 runs
the page is already fast (the cost is quadratic). The library layer itself is cheap:
`Library.runs()` 4 ms, `JobManager.tick()` 47 ms every 2 s, `view.load_result` 0.8 ms.

### P7. Worker start

Each job is a fresh interpreter. `import owlplanner.library.worker` takes 1.5 s (`-X importtime`;
2.0 s of wall with other solves running): `scipy.optimize` and `scipy.stats` 0.59 s through
`rate_models.inflation_transform`, `matplotlib.pyplot` 0.31 s through `plotting.factory`, pandas
0.28 s. A Quick look in the worker's own code path (`run_job`, in process) takes 2.1 s: solve
1.28 s, the workbook 0.41 s, building the plan 0.21 s. So a Quick look costs about 4 s from the
click (the two figures added; not timed end to end), of which the solve is about 1 s, and the
Run page's 2 s poll adds up to 2 s more.

The imports are upstream modules; lazy imports there would save about 0.9 s per process (also
for `owlcli`). Irrelevant for Careful. Low priority.

### P8. Test suite

One run with `--durations=60` (4,838 passed, 1 skipped, 879 s; two solves were running beside it,
so the seconds are inflated and the shares are what to read): the 60 slowest tests are 2,061 of
about 3,516 worker-seconds (59%), the 10 slowest 1,113 (32%). By file: `test_snap_binaries.py`
339 s, `test_ss_ages.py` 332 s, `test_itemized.py` 303 s, `test_spending_bequest_frontier.py`
273 s, `test_star.py` 125 s, `test_mcp_compare_baseline.py` 120 s, `test_amo_postprocess.py`
110 s. Of these only `test_itemized.py` and `test_star.py` are fork files (checked against
`upstream/dev`): 428 s, 12% of the suite. Their local-search tests
(`test_local_search_keeps_the_loops_itemizing_branch` 201 s, `test_local_search_carries_the_star_family`
85 s) could carry upstream's `deep` mark or a `localSearchStepNodes` cap. Whether the fork's
features make upstream's slow tests slower than on stock `dev` was not measured.

## 4. Checked, no opportunity

- **HiGHS options** (`mip_probe.py` on two dumped capped steps, one that improves and one that
  does not, run four at a time): `threads=1`, `mip_heuristic_effort` 0 and 0.3, no cut
  separation at nodes, `mip_pscost_minreliable=1`, no symmetry detection, presolve off. At the
  defaults the two steps took 18.4 and 23.3 s. The only clearly faster setting, no node cuts
  (14.5 s on the second), was slower on the first (20.4 s). Heuristics off and
  `pscost_minreliable=1` were within 1.5 s of the defaults and ended the first step on a worse
  plan; `mip_heuristic_effort=0.3` and presolve off each found a slightly better plan on one
  step for 1.5x the time. Nothing is faster on both.
- **Owl's Python in a solve**: under 1% of a Careful solve; a few tenths of a second of a Quick
  look (0.29 s of it is HiGHS).
- **`STEP_GAP`**: see P3.
- **The what-if's parent** is already solved only when it has no Careful result from today
  (`ui/whatif.py`, `is_current` and `queue_what_if`).
- **The exact-model companion** of Careful is 6 s beside 340.
- **The tornado**: its movers run under the exact models, 2.7-6 s each plus the worker start.
- **The job ticker and the library layer**: 47 ms every 2 s at 239 results.

## 5. Not measured

- The household's own case (offline by decision) and the user's machine: every number here is
  this container's, which CLAUDE.md records as about 2.4x slower than the maintainer's for stock
  code. On a faster machine the 300 s budget binds less and P1's caveat weakens.
- P2 and P3 on stock upstream examples, on more than six of the 36 grid variants, or at other
  claiming ages.
- P4 and P5 end to end.
- Windows and macOS (process start cost, `spawn` pools).
- MOSEK (no license here).

## 6. Files

- `fork-notes/performance/solve_probe.py`: one timed solve, every HiGHS call recorded, optional
  dumps and the experiment knobs.
- `fork-notes/performance/quiet_patch.py`: P2's prototype.
- `fork-notes/performance/mip_probe.py`: one dumped HiGHS call re-solved with other options.
- `fork-notes/performance/library_bench.py`, `page_profile.py`: the 120-run library and the page
  profiles (the second needs `yappi`).

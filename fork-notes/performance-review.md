# Performance review (2026-11-10, revised 2026-11-11)

Revised on 2026-11-11 after a second review of the same request was audited claim by claim
(`performance-review-audit.md`): the first paragraph of section 1 is scoped, P6 gained the job
tick, P9, P10 and section 3b are new, section 4 carries the per-function timings. P1-P5, P7 and
P8 are as written on 2026-11-10.

**Built on 2026-11-11** (the user's call: "build both as recommended, one commit each"; section
6): P3's budget (`668a730`) and the cores, which are P1, P4b and P5 with the tick of P6
(`945c21f`). Later the same day (the user's call, section 6b): the queue's default of 4 cores,
no more than half the logical ones (`9063580`), and P4a (`cfd26e1`); then P4a for *Claiming
ages, every pair tried* and `run_suite.py` (`9e35def`, section 6c). Later still (the user's call
"build P9, P6's pages and P8, and prepare P2 issue", section 6d): P9 (`1628a9e`) and P6's pages
(`b5c2d7b`) built; P8 measured, not built, then dropped (the user's call: the node cap does not
shorten those tests); P2 measured on stock upstream, with and without a confirming search
(section 6e), and filed by the user as **#252** with the two options and no patch
(`fork-notes/issue-ls-settled-steps.md`). Not built: P7, P10, section 3b.

The user's request: "review the project from a performance improvement perspective. Look for any
significant opportunities: architectural, algorithmic, memoization, dropping redundant steps."

Report only: nothing in `src/`, `ui/` or `tests/` changed. Measured on the synthetic household
(`fork-notes/synthetic/`), claiming ages fixed at 70/70, HiGHS 1.15.1, this container (4 cores,
Linux), at `abd8b6c`. The scripts are in `fork-notes/performance/`. Each statement below says
whether it was measured, read in the code, or inferred.

## 1. Answer

A Careful solve's time is solver time. 344 of 346 s are inside `highspy.run` (71 calls); all
of Owl's own Python, the model build included, is under 1% (by function in section 4). So
nothing in the Python layer (vectorizing, caching the constraint build, `deepcopy`) can matter
for a Careful solve, and no HiGHS option tried made the slow calls faster. What can matter is
how many solver calls are made and how many run at once.

That does not hold for the small solves (revised 2026-11-11): a Quick look is 58% HiGHS and 42%
Python, a fifth of it the constraint build. One Quick look is under a second either way, but the
stress tests run hundreds of solves of that kind on a thread pool, and there the Python share
is what the pool cannot run in parallel (section 3b).

| # | Opportunity | Measured effect | Whose code | Cost |
|---|---|---|---|---|
| P1 | Run several jobs at once (`JobManager(max_parallel=...)`, default 1, never set by the interface) | 4 solves at once: +5% wall each, so about 3.8x the throughput on 4 cores | fork (`ui/libraryjobs.py:95`) | one setting; see the budget caveat in P3 |
| P2 | Local search: skip the node-capped steps in loop iterations where the binaries did not move | same plan to the cent in 6 of 6 variants; CPU -16% to -48% in the 4 that settle, none in the 2 that keep moving; -20% over the six | upstream (`localsearch.py`) | an upstream issue with these numbers, or a fork option |
| P3 | Local search: node cap 1,000 instead of 3,000 (`localSearchStepNodes`, an existing option), with P2 | same plan to the cent in 5 of 6, +\$1.75/yr in one; CPU -46% to -63% in the 4 that settle; -36% over the six | fork preset (`presets.py`) for the option; upstream for the default | a preset value |
| P4 | *Let Owl choose the claiming ages*: the final solve repeats a stage-2 candidate; stage 2 is serial | read in the code, not timed: 1 of 4-6 Careful solves is a repeat (about 6 min here); the others are independent | fork (`worker.py`, `agesearch.py`) | small (P4a), medium (P4b) |
| P5 | *Claiming ages, every pair tried* runs its sweep on a serial pool | read in the code; the same sweep's CLI runs on a process pool | fork (`worker.py:69`) | small |
| P6 | Library and Collections pages re-read every `run.json` once per run shown; the job tick scans the library three times | 120 runs: Library page 1.5 s per click, 15,480 file reads; quadratic in the number of runs. Tick: 47 ms every 2 s | fork (`store.py:415`, `jobs.py:146`) | small |
| P7 | Worker start: 1.5-2.0 s of imports before a 0.5-1 s Quick look | measured | upstream modules | lazy imports upstream; or leave |
| P8 | Test suite: 60 tests are 59% of the worker time | measured under load | 2 fork files (12%), the rest upstream's | `deep` marks on fork tests |
| P9 | Run page parses the whole results workbook on every render, expander closed or not | 93 ms of a 260 ms render | fork (`ui/Run.py:816`) | small |
| P10 | Download buttons build their workbook on every rerun of the page | 13-126 ms (Financial Profile), 58 ms and more (Reports) | upstream pages | a callable instead of the bytes |
| 3b | Stress tests: the thread pool gives 1.6x on 4 cores | 60 scenarios: 24.6 s on four threads, 39.6 s on one | upstream (`stresstests.py`) | a process pool; an upstream issue |

Not worth doing (section 4): solver options, the Python model build and its caches in a Careful
solve, a looser step gap, caching the what-if parent (already done).

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

**Fixed upstream** as `1d91494` (#252, filed 2026-11-11), merged here on 2026-11-12: section 6f.

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

### P3, measured on 2026-11-11: the caps lifted at 1,000 nodes, and what follows for P1

The user's two questions: lift the 300 s budget in the `decision` preset or keep it and mark a
result it cut; and how the queue's parallel jobs (P1) and the pools inside a worker (P4b, P5)
share the cores.

Measured (`lifted_budget.sh`): the two variants whose search keeps moving, both wall-clock caps
lifted as `work_sweep.py` does (`localSearchTime = 7200`, `localSearchStepTime = 1800`), all six
solves at once on the four cores.

| Variant | Nodes | P2 | CPU | Wall | First-year discretionary | Longest steps |
|---|---|---|---|---|---|---|
| whiteplains_2029_mortgage | 3,000 | | 495 s | 711 s | 105,853.35 | 57, 53, 47 s |
| whiteplains_2029_mortgage | 1,000 | | 443 s | 641 s | 105,853.35 | 30, 28, 27 s |
| whiteplains_2029_mortgage | 1,000 | yes | 365 s | 542 s | 105,853.35 | 29, 28, 27 s |
| whiteplains_2038_cash | 3,000 | | 804 s | 1,002 s | 105,260.34 | 81, 54, 53 s |
| whiteplains_2038_cash | 1,000 | | 572 s | 762 s | 105,259.28 | 47, 31, 31 s |
| whiteplains_2038_cash | 1,000 | yes | 483 s | 674 s | 105,259.28 | 48, 32, 31 s |

What this shows:

- **Lifted, the result does not depend on the load or the day.** The 3,000-node rows are the
  values of 2026-11-10 to the cent (105,853.35 and 105,260.34), measured then at another
  load (418 and 688 CPU-seconds) and now six at a time on four cores, a day later.
- **The step cap binds too.** `STEP_TIME = 60` s ("a backstop; the node limit below is the real
  cap", `localsearch.py:84`) would have cut the 81 s step, which ran to its 3,000 nodes here only
  because the step cap was lifted as well. So lifting `localSearchTime` alone leaves a second
  wall-clock dependence at 3,000 nodes under load; at 1,000 nodes the longest step was 48 s.
- **Six solves on four cores cost CPU, not only wall.** The same two 3,000-node solves took 418
  and 688 CPU-seconds on 2026-11-10 and 495 and 804 here: +17% to +18%. P1 measured +5% of wall
  for four solves on four cores. Past the core count the work itself grows.
- **Cost of the fork-only setting** (1,000 nodes, both caps lifted, no P2) against today's
  preset (3,000 nodes, 300 s budget; 318 CPU-seconds on both variants on 2026-11-10, cut by the
  budget): 443 and 572 CPU-seconds here, which at the load of 2026-11-10 would be about 375 and
  485 (scaled by 418/495 and 688/804; an estimate, not a run), so about +18% and +53%. On the two
  settling variants measured on 2026-11-10 the same node cap gave -37% (382 -> 240 and 349 -> 219 s)
  with the identical plan. The other two settling variants were not run at 1,000 nodes without P2.
- **Result of the fork-only setting** against the 3,000-node lifted reference: the identical
  plan on three of the four variants measured, \$1.06/yr less on whiteplains_2038_cash
  (105,259.28 against 105,260.34). The library reads local-search results with a 1% band, about
  \$1,050 here.

**Recommendation on the budget: lift both caps, with the 1,000-node cap, and mark a cut as well.**
Not one or the other:

1. The dollars do not matter (every difference seen is under \$3/yr against a \$1,050 band); what
   the budget costs is repeatability. Once P1 runs jobs side by side, load is the normal state
   (4 of 6 solves hit the budget at four at a time), and the same run solved twice on one day can
   show two numbers. The library's own checks compare to the dollar, and the what-if reuses "a
   Careful result from today" as *the* result.
2. `ages` picks by the raw score (`agesearch.py:164`, `max(good, key=...)`, no tolerance) among
   three to five local-search solves. Run on a pool (P4b) they load one another, so a
   budget-cut candidate can lose by a dollar or two to a neighbour. `_FORCED["ages"]` is empty
   (R4: the case's own model), so the lift has to reach that preset too, wherever the case's
   model is local search. A decision for the user: it adds two keys to a preset that forces
   nothing today.
3. With the result independent of load, running more processes than cores costs time only (the
   third bullet above), never the answer. That is what makes the core-sharing question below a
   matter of throughput.
4. The mark is still needed because a lifted cap is a larger cap. The round-level cut has a log
   line the worker already receives ("Local search: time budget spent", `localsearch.py:363`;
   the worker tees every log line), so `record.json` can carry it without touching upstream's
   file; a test would have to pin the wording. For a step ended by its time cap no marker was
   found (`grep -i "time limit\|kTimeLimit\|time_limit"` in `plan.py`, `localsearch.py`,
   `export.py` finds the option being set, nothing that reports it).

Where: `presets._FORCED["decision"]` gains `localSearchStepNodes`, `localSearchTime` and
`localSearchStepTime` (all three are existing solver options, `plan.py:6825`); nothing upstream
changes. Not built.

**Recommendation on the cores: the queue counts cores, the worker is told its share.** Each job
carries a weight in its `status.json`, the number of solves it will run at once (1 for a single
solve; for `ages` and `ages_thorough` the pool size it wants, at most the capacity).
`JobManager.tick()` dispatches the first waiting job while the weights of the running jobs plus
its own fit the capacity, and stops at the first that does not fit (first come first served, as
today). The worker reads its weight from its own record and sizes its pool by it.

- The manager is the only place that sees every job, the record is on disk, and dispatch is
  already a compare-and-swap under the job's lock, so the count survives a restart and adoption
  (S8) with no new race. A worker that sizes its pool from the slots it finds free at its start
  decides once, from a state that changes for the hours an `ages_thorough` sweep runs.
- It bounds the processes at the core count by construction, which the +17% above says is
  worth doing.
- It costs no throughput. With a full queue an inner pool adds nothing (the same solves, the
  same cores); it matters for a lone heavy job, and a lone job is dispatched with the whole
  capacity.
- Its cost: a heavy job at the head of the queue waits for the running jobs to end while cores
  go idle, at most one Careful solve's time (5-17 minutes here).
- P1 needs the weight even without P4b and P5 (read in the code, not measured in this
  combination): `_ssAgeSearch` already starts `os.cpu_count()` threads (`plan.py:7150`, stage 1
  of `ages`) and the regret sweep the same (`stresstests.py:845`), so an `ages` or `regret` job
  is more than one core's worth today. Section 3b measured such a thread pool at 1.6x.
- Not measured: the right capacity. `os.cpu_count()` counts logical cores; this container has
  four with no stated hyper-threading, and a laptop's eight logical cores are not eight solves'
  worth. A setting, with one four-variant batch timed on the machine that will run it.

### P4. *Let Owl choose the claiming ages* (`ages`)

Read in the code, not timed (a run is 20-35 min here).

- **P4a, a repeated solve** (built later on 2026-11-11, section 6b, for `ages` only).
  `agesearch.two_stage_ages` scores the pick and each searched
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

**Built** (`b5c2d7b`, section 6d): `Library.get` reads the one run's folder. The tick's part was
built in `945c21f` (section 6).

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
`Library.runs()` 4 ms, `view.load_result` 0.8 ms.

The job tick (added 2026-11-11; the first version filed it under "no opportunity").
`JobManager.tick()` calls `self.jobs()` three times (`adopt()`, the running count, the waiting
list; `jobs.py:146-158`, read), each a scan of every `run.json` and every `status.json`: 47 ms
per tick at 239 results, every 2 s from the ticker thread, and again from the Queue and Run
pages' own 2 s fragments while they are open (`ui/Queue.py:63`, `ui/Run.py:160`). `enqueue` ends
with a tick as well, so queuing a collection's variants scans the library three times per job.
One `jobs()` per tick, passed to `adopt`, removes two thirds of it; not built. On Linux this is
2% of one core and nothing a person sees. File opens cost more on Windows, where it was not
measured. Also small and in fork code, read and not timed: `grid.latest_result` loads a
folder's three files before it looks at the record's preset (`grid.py:388-391`), and
`Library.save_run` exports the case before it checks for a duplicate inputs hash
(`store.py:535` before `551`; a check before the export could be added, the one under the lock
has to stay).

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

**Dropped** (the user's call, 2026-11-11, after section 6d's measurement): a node cap does not
shorten the two fork tests below; what they spend is P2's pattern (loop iterations re-running
steps that find nothing) and the size of each restricted solve, not the node count. The tests
stay as they are, in the default run.

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

### P9. The Run page's workbook (added 2026-11-11)

**Built** (`1628a9e`, section 6d): read only while the expander is open, once per file.

`ui/Run.py:816-817`: inside `st.expander("Results workbook")` the page runs
`pd.read_excel(BytesIO(xlsx.read_bytes()), sheet_name=None)`. Streamlit runs an expander's body
whether it is open or not, so every render of the Run page parses all 16 sheets of the 48 kB
workbook: 93 ms (`audit/workbook_read.py`, three runs: 95, 93, 93 ms), against 260 ms for the
whole render (section P6's table; the two were measured a day apart on different libraries, so
the share, about a third, is approximate). It is the page library mode opens on. A read keyed
on the file's path and modification time (`st.cache_data`), or one that waits for a "show the
sheets" toggle, removes it; not built.

The same page loads every result of the run (`ui/Run.py:554-561`, then `whatif.main_results`
again): 0.8 ms each, so nothing until a run has hundreds of solves.

### P10. Download buttons (added 2026-11-11, upstream pages)

`ui/Financial_Profile.py:725` passes `data=owb.saveContributions()`, and `ui/Reports.py:69` and
`174` build `owb.saveContributions()` and `owb.saveWorkbook()`, on every rerun of the page,
which on the Financial Profile is every cell edit. Measured: 13 ms to build the contributions
workbook and 32-126 ms with the save to bytes; 58 ms for the results workbook before the save.
Streamlit 1.67.0's `download_button` takes a callable ("it is executed when the user clicks the
download button"; its docstring, read). Upstream's pages: an issue with these numbers, or leave.

## 3b. Stress tests (added 2026-11-11; upstream's `stresstests.py`)

Not looked at in the first version. In the library only the `regret` job runs this module; the
Stress Tests and Spending vs Bequest pages are upstream's.

Measured (`audit/stress_probe.py 60`): `run_stochastic_spending` over 60 historical start years
with Quick-look options takes 24.6 s on its four worker threads and 39.6 s on one: 1.6x. A
scenario takes 0.65 s alone and 1.6 s of thread time among four. The code's comment says "HiGHS
releases the GIL during solve, so threads give real parallelism"; that covers the 58% of a
loop-mode solve that is HiGHS and not the 42% that is Python. Two consequences, neither built
or measured:

- A process pool (spawn, as `work_sweep.py` and `run_suite.py` use) should give close to the
  core count, as P1 measured for whole jobs (+5% wall each at four at once). The clones would
  have to pickle; a solved Plan does not (`issue-run-library.md`), and whether these unsolved
  ones do was not checked.
- Or the Python share goes down: here, and only here, caching more of `_buildConstraints`
  across loop iterations (19% of a Quick look) would show.

`run_historical_range` and `run_mc` solve one scenario after another on the plan itself
(`stresstests.py:1309-1500`; no executor, grep). Giving them the same thread pool would be
worth the same 1.6x, not the core count.

Small, in the same module:

- The frontier. `_compute_efficient_frontier` solves 61 dense LPs and is called twice per run:
  0.13, 0.33 and 1.05 s per call at 100, 500 and 1,000 scenarios, 1.2% of the 60-scenario run.
  The LP has a closed form: with the bases sorted ascending, g* is the basis at index
  `min(ceil(S / lam) - 1, S - 1)` for lam > 1 and the largest basis otherwise. Checked against
  the LP at every lambda of the sweep for S = 7, 100 and 1,000 (`audit/quantile_check.py`):
  identical except at one tie (S = 1,000, lam = 1,000, where S / lam is an integer and the LP
  returns the other end of an interval of equal objective), 1.1 ms for the 61 points. The
  second review's index, `floor(S (1 - 1/lam))`, is the mirror image and wrong at 45 of 61
  points. Upstream's comment at `stresstests.py:1816` already weighs the second call ("Sixty
  small LPs against minutes of scenario solves").
- Clones. Every scenario's clone is built on the main thread before the pool starts
  (`stresstests.py:1665-1669`, `1732-1733`): 2.7 ms each without longevity sampling (0.6% of
  the run). With longevity sampling a clone is 47 ms, 41 ms of it `hfp_io._conditionTimetables`
  on the in-memory tables; against 0.4-0.65 s per scenario that is about a tenth of the run
  (inferred; Monte Carlo was not run, the synthetic case's rates are not stochastic). Held
  memory is 0.15 MB per clone.
- `run_spending_bequest_frontier` calls `run_stochastic_spending` once per bequest level
  (`stresstests.py:2078-2111`), cloning and drawing again each time. The solves, which differ
  per level, are nearly all of it.

## 4. Checked, no opportunity

- **HiGHS options** (`mip_probe.py` on two dumped capped steps, one that improves and one that
  does not, run four at a time): `threads=1`, `mip_heuristic_effort` 0 and 0.3, no cut
  separation at nodes, `mip_pscost_minreliable=1`, no symmetry detection, presolve off. At the
  defaults the two steps took 18.4 and 23.3 s. The only clearly faster setting, no node cuts
  (14.5 s on the second), was slower on the first (20.4 s). Heuristics off and
  `pscost_minreliable=1` were within 1.5 s of the defaults and ended the first step on a worse
  plan; `mip_heuristic_effort=0.3` and presolve off each found a slightly better plan on one
  step for 1.5x the time. Nothing is faster on both.
- **Owl's Python in a Careful solve** (timed by function on 2026-11-11, `audit/overhead_probe.py`,
  the `decision` preset at a 300-node cap, 129.4 s): `_run_highs` 128.74 s in 56 calls (99.48%);
  `_buildConstraints` 0.204 s in 18 calls; every top-level `copy.deepcopy` together 0.126 s in
  11 calls; `ConstraintMatrix.to_csr` 0.061 s in 60 calls; money scaling 0.014 s in 56 calls;
  `_adjustParameters` (the tax tables, the SS streams) 0.008 s in 20 calls; the repairs after
  the loop 0.004 s. Caching the CSR form or the scaling, dropping the deep copies, or not
  recomputing the SS streams (0.39 ms a call) would save under half a second. For a Quick look
  see section 1 and 3b.
- **Re-reading the workbook in `work_sweep.py`**: `make_plan` reads the `.xlsx` at every scored
  candidate, 89 ms a read, in a sweep whose scored plans take 94-288 s each.
- **Throwaway plans in `library/builder.py`**: 3.7 ms each.
- **`thresholds.threshold_proximity`**: 32 ms, once per result. **`star.star_schedule`'s district
  scan**: 0.16 ms per solve on the 75 rows of `data/property_tax_relief.toml` (Westchester and New
  York City), 2.4 ms if the table held all of the state's roughly 730 districts.
- **`git` in `code_stamp`**: `version.engine_commit` is cached per process; a dirty tree adds a
  3 ms `git diff` per call.
- **`STEP_GAP`**: see P3.
- **The what-if's parent** is already solved only when it has no Careful result from today
  (`ui/whatif.py`, `is_current` and `queue_what_if`).
- **The exact-model companion** of Careful is 6 s beside 340.
- **The tornado**: its movers run under the exact models, 2.7-6 s each plus the worker start.
- **The library layer** apart from P6: `Library.runs()` 4 ms, `view.load_result` 0.8 ms.

## 5. Not measured

- The household's own case (offline by decision) and the user's machine: every number here is
  this container's, which CLAUDE.md records as about 2.4x slower than the maintainer's for stock
  code. On a faster machine the 300 s budget binds less and P1's caveat weakens.
- P2 and P3 on stock upstream examples, on more than six of the 36 grid variants, or at other
  claiming ages.
- P4 and P5 end to end.
- Windows and macOS (process start cost, `spawn` pools, the cost of the tick's file opens, `git`).
- Stress tests under Monte Carlo and longevity sampling, on a process pool, and with other than
  Quick-look options; the bequest frontier and the regret sweep.
- MOSEK (no license here).

## 6. Built on 2026-11-11

Two commits, each with its tests. The full suite: 4855 passed, 1 skipped after the first; after
the second 4876 passed and 1 failed, a wording check on the Queue page's new tooltip (no page
says "score"), fixed in the commit, after which the 561 UI and text-encoding tests passed (the
full suite was not run again).

**The search budget (`668a730`).** `presets.LOCAL_SEARCH_EFFORT`: 1,000 nodes a step,
`localSearchTime` 7,200 s, `localSearchStepTime` 1,800 s.

- *Careful* (`decision`) sets it over the case's own settings and under an option given for
  the one job.
- *Let Owl choose the claiming ages* (`ages`) still forces nothing: where the case's model is
  local search it fills in the settings the case does not state, for stage 2
  (`two_stage_ages(effort=...)`) and for the final solve.
- `record.json` has `search_budget_cuts` (`{"solve": n, "stages": m}`), counted by the worker
  from upstream's log line (a test checks upstream still words it so); the Run page lists a cut
  among the result's problems.
- Checked: *Careful* on yonkers_2027_mortgage through the preset gives 109,150.60, the value of
  every configuration measured on 2026-11-10, in 201 CPU-seconds with the test suite running
  beside it (382 alone under the old preset), no step over 1,000 nodes, no cut.
- Not done: nothing marks a single step ended by its own time cap (no log line exists for it;
  at 1,800 s it would take a step 37 times the longest seen).

**The cores (`945c21f`).** `JobManager(cores=...)`; the interface uses `OWL_LIBRARY_CORES`, else
half the computer's logical cores (`jobs.default_cores`). That default is a choice, not a
measurement: `os.cpu_count()` counts logical cores, half of it is the physical count on most
desktop processors and leaves the browser room. With `OWL_LIBRARY_CORES=1` the queue is what it
was.

- A job's record states what it wants (`cores_wanted`: 1 for a single solve, 5 for `ages`,
  every core for `ages_thorough`, 2 for `regret`'s thread pool), the queue gives it that or all
  it has at dispatch (`cores`) and counts it while it runs; first come, first served, nothing
  jumps a job that waits for room.
- `worker._ProcessPool`: spawned processes, one plan each, ended at once on a cancel, ending
  with the worker when it is killed (`_follow_parent`; the test for it fails without the
  initializer, and the process it then leaves behind was seen sleeping on for its five
  minutes). `ages` scores stage 2 on it (P4b), `ages_thorough` its sweep (P5).
- A tick reads the library once (P6's three scans).
- Checked on the synthetic household through real workers
  (`fork-notes/synthetic/check_library_cores.py`, 7/7): four Quick looks side by side on four
  cores, one result; one after the other on one core; and *Let Owl choose the claiming ages*
  on yonkers_2027_mortgage, given four of the five cores it wants, 1,189 s in all: stage 1
  picked 70y0m / 69y8m, stage 2 scored it at 109,101.30 beside 108,816.38, 108,844.94 and
  109,150.60 for 70/70, which it chose; the plan then published alone, at 70/70, scores
  109,150.60 to the cent, with no search cut.
- Not measured: the same search on one core (so no speed-up figure: P4b's "one or two solves'
  time instead of three to five" stays an inference); `ages_thorough` on a pool with real
  plans (its pool is tested with the sweep stubbed); the default on any machine but this one;
  Windows (`_follow_parent` waits on the parent's handle there, by the documentation).
- P4a stands: the final solve of `ages` repeats the winning candidate (109,150.60 twice above).
  (Built later the same day, section 6b.)

## 6b. Built later on 2026-11-11: the default and P4a

The user's two calls: "we should default to 4 but no more than half the computer's logical
cores. Drop the repeated final solve of the age search." Two commits, each with its tests.

**The default (`9063580`).** `jobs.default_cores`: `OWL_LIBRARY_CORES` when set (any number,
above 4 too), else `min(4, os.cpu_count() // 2)`, at least 1 (a computer that does not say
counts as 2 logical cores, as before). 8 logical cores give 4, as before; 16 or 32 give 4
where they gave 8 or 16; 6 give 3. Not measured on any computer: the cap is the user's
choice, the half is section 6's reasoning.

**P4a (`cfd26e1`), for `ages`.** The worker publishes the winning stage-2 candidate's plan.
For that plan to be the one the old final solve gave, every candidate now solves with the
options the published solve uses: `agesearch.candidate_options` (the case's own, the job's
overrides on top, the library's effort where local search is the method), which
`presets.resolve_options("ages", ...)` now calls. Stage 2 did not take the job's overrides
before; the interface queues `ages` with none, so nothing it queues changes.

- `two_stage_ages(keep=True)` returns `agesearch.Winner` (plan, log, options). In a row it
  keeps the best plan so far and drops the others; on the pool each solved candidate comes
  back pickled (`score_trial`; 213 KB for Case_bill, 409 KB for the synthetic condo case,
  measured) and only the winner's is loaded. One rule (`_winner`, the first of equal scores)
  picks the ages and the plan.
- The worker writes one line saying the plan is the candidate's own, reads the winner's log
  (already in solve.log, written while the tee was quiet) as the published solve's
  (`_LogTee.adopt`: warnings, loop iterations, the clock's cuts), and records
  `age_search.stage_2_plan = true`.
- Checked: Case_bill with its ages searched, through real workers, on one core (in a row)
  and on two (the spawned pool): the same `plan.json`, summary and options as the base
  commit `b07e2e7` gives, the engine's commit stamp aside, with four plans built in solve.log
  instead of five. Tests: the kept plan equals a fresh solve at the chosen ages under
  `resolve_options("ages")` (`plan_to_dict` and `plan_metrics`), in a row and through a
  pickle round trip; the worker calls `Plan.solve` for nothing after the search. With the
  worker solving again and `candidate_options` dropping the job's options, 5 tests fail.
- Checked on the synthetic household: `check_library_cores.py` 7/7, its third check rewritten
  (`stage_2_plan`; the published score is the candidate's, 109,150.60 at 70/70 again; 5 plans
  built for 4 candidates: stage 1 and one each, none after; no clock cut).
- Timed (`fork-notes/performance/ages_timing.py`, `ages_timing_parse.py`): one `ages` job of
  yonkers_2027_mortgage on a four-core queue, at `b07e2e7` then at `cfd26e1`, one after the
  other with nothing else running.

  | | stage 1 | stage 2 | repeated solve | job |
  |---|---|---|---|---|
  | `b07e2e7` | 89 s | 1,163 s | 214 s | 1,467 s |
  | `cfd26e1` | 99 s | 1,155 s | none | 1,255 s |

  The same four scores to the cent and the same pick (70/70); the 61 summary keys, the
  options, the iterations and the warnings identical. Stage 2 lasts as long as its slowest
  candidate (69/69y8m: 1,162 s and 1,154 s; the winner took 242-252 s beside the others), so
  on a pool the saving is the winner's own solve alone, 214 s here (14%); in a row it is the
  same one solve. One pair of runs: the same job took 1,189 s at `945c21f` (section 6) and
  1,300 s in the check above, so the slowest candidate's time varies by minutes between runs.
- Not done: *Claiming ages, every pair tried* still re-solves its decided cell (its 81
  candidates are scored in `work_sweep.score`, which returns rows, not plans; keeping the
  best plan there means pickling each to a file in the pool's processes, or changing
  `work_sweep`, which the CLI shares). `run_suite.py` still re-solves at the chosen ages
  (its final solve can rescale the rates first, `nominal_gamma`). (Both built later the same
  day, section 6c.)

## 6c. Built later on 2026-11-11: P4a for "every pair tried" and for `run_suite.py`

The user's call: the two items 6b left. One commit.

**`ages_thorough`.** `work_sweep.score` keeps the plan it scores when the caller names a
folder (`cfg["keep_dir"]`, from `args.keep_dir` in `scorer_config`): the plan whose value the
cell records (branch-and-bound's, or local search's where that was kept instead) is pickled to
`kept_plan_path(keep_dir, ages)` with its own log and options (`KeptPlan`), written aside and
renamed. The worker names a staging folder of the attempt's (`.attempt-<token8>-plans`, so
`results.drop_staging` clears it after a kill and `store.run_zip` skips it), loads the decided
cell's plan (`load_kept_plan(keep_dir, row["best"])`), removes the folder, and publishes that
plan: one line in solve.log says so and the plan's own log follows it (the sweep's plans log
to their own buffers, so it was not in solve.log yet); `record.json`'s `age_search` has
`decided_plan: true`, and the Run page says "the decided cell's own, not solved again". Where
no plan was kept at the decided cell (it did not solve), the cell is solved again as before
(review AH1's route). The command (`python -m owlplanner.work_sweep`) names no folder: its
config, its cells and its `--json` are what they were.

- **The job's options.** For the plan published to be the one a solve again gave, the job's
  options must reach the sweep, as P4a made them reach stage 2 of `ages`. They now go into
  every scored plan (`scorer_config`'s `overrides`; `scorer_options`: the case's options less
  the method keys, the job's less the same keys, then the scorer's own). Before, they reached
  only the final solve, and only where the case did not state them: a job with
  `spendingSlack = 3` on Case_bill (whose case says 0) recorded 0 at `9648b7e` and records 3
  now (a scratch run on each checkout, not kept). The interface queues this preset with no
  options.
- **Deposit-split cells** (`eta_check`, off in the library) are not kept: they share the
  decided cell's ages.
- **Disk.** One file a scored cell while the sweep runs, removed at the end of the job:
  368-371 KB each on Case_cameron (measured: the plan and its log). Not measured on the
  synthetic household; section 6b measured 409 KB for one of its local-search candidates,
  which would make 81 cells about 33 MB (inferred).
- **What it saves:** the decided cell's own solve, whatever it took in the sweep (its
  `seconds` in `scores.json`): 94-288 s a plan on the chris+pat dry run. Not timed end to end
  (a synthetic `ages_thorough` is hours).

**`run_suite.py`.** `solve_one` calls `two_stage_ages(keep=True)` and publishes the winning
candidate's plan (its log reattached to the run's, its warnings read from its own solve's
log), except on a row that rescales the workbook's nominal amounts first (`nominal_gamma`),
where the candidates were scored on the amounts as written: there the plan is built and
solved again, as before. No row of the suite does both (the rate groups take the baseline's
ages). `results.json` records `stage_2_plan`.

**Checked.**

- Tests: `tests/library/test_work_sweep_keep.py` (12: the config, the rule for which plan a
  cell keeps, the deposit-split cells, the command's route, and a real sweep of Case_cameron:
  one file per scored cell, each holding its cell's plan, and the decided cell's plan equal to
  a solve again in every number of `plan_to_dict` and `plan_metrics`, the solve's clock
  aside); `tests/library/test_worker.py` (3 new: Case_bill's real sweep published without a
  solve after it, its `plan.json`, `summary.json`, options, warnings and iterations equal to
  the same job forced down the solve-again route; the job's options in the scored plans; the
  plans folder gone after a cancel). The stubbed sweeps of the AH1 tests now take the
  solve-again route (no plan kept), which they still check.
- Through real workers, outside pytest (`fork-notes/performance/thorough_kept_check.py`; the
  spawned pool cannot run under pytest's frozen date): three jobs of one run, on one core, on
  two (each cell pickled in a spawned process) and forced to solve again. Case_cameron (six
  cells, the decided cell the first scored): 8/8, the same `plan.json`, `summary.json` and
  options, `decided_plan` on the first two only, no staging folder left. Case_robin (six cells; stage (a) picked 65y10m, the sweep decided 66y0m, so the published file
  is not the first cell scored): 8/8, 44,225.35 on all three routes; 60.3 s on one core, 53.1 s on
  two, 71.0 s solved again (one run each, beside the test suite).
- `run_suite.py`'s baseline row (the synthetic household, `main/base`) through the suite at
  `9648b7e` and through the edited one, one after the other the same day
  (`fork-notes/performance/suite_winner_check.py`): the same ages (70/70), the same four
  candidates and scores, every key of the record equal (metrics, warnings, convergence, error
  bar), and the synopses equal but for "Case executed on" and "Solve time" (the published plan
  is the one solved during stage 2). 139.2 s and 127.7 s, one run each; the final solve the
  old suite repeated took 10.5 s.
- The full suite: 4903 passed, 1 skipped at `9e35def` (Linux, `-n 3`).

## 6d. Later on 2026-11-11: P9 and P6's pages built, P8 measured, P2 on stock upstream

The user's call: "build P9, P6's pages and P8, and prepare P2 issue". One commit each for P9
and P6; P8 not built (below); P2 as an issue draft.

**P9 (`1628a9e`).** The Run page's *Results workbook* expander tracks its state
(`on_change="rerun"`, Streamlit 1.67, the pinned version) and reads the workbook only while
open, through `_workbook_sheets(path, mtime_ns)` (`st.cache_data`, four entries). Test
(`tests/ui/test_library_pages.py`): no read with the expander closed, one when opened, none on
a change of sheet; it fails on the old page ("the workbook was read with its expander closed").
The 93 ms is the audit's measurement of the read (section P9); the page's render was not timed
again.

**P6's pages (`b5c2d7b`).** `Library.get` reads the folder where the last listing saw the run
and checks the id in its `run.json` (so the run returned is never a stale copy); a run it does
not hold any more costs one listing, as every call did. Every listing refreshes the index. So
the change is in the store, not the pages, and every caller gains (`JobManager.enqueue`, the
Collections members, the Library page's parents).

- Measured (`page_timing.py`, AppTest, median of five reruns, the 120-run library of
  `library_bench.py`, with three P2 solves running beside it): Library page 1.48 -> 0.76 s,
  Collections 0.64 -> 0.23 s; Run 0.22 s and Queue 0.42 s were not touched.
- What is left on the Library page (yappi, after): about 0.8 s of the 3.1 profiled seconds is the
  library layer, all of it linear in the runs (each run's job records, its zip's cache check,
  the housing-conversion check); the rest is Streamlit drawing 120 rows of buttons, popovers and
  columns.
- Tests (`tests/library/test_store.py`, `TestGet`, 6): one `run.json` read per `get` after a
  listing (fails on the old store: five reads per get with five runs), a new instance, a run
  saved by another instance, a rename and a delete through another instance, a damaged
  `run.json`, a folder holding another run's `run.json`.
- Not done: `grid.latest_result` still reads a folder's three files before the preset check,
  and `Library.save_run` still exports before the duplicate check (both small, P6's last
  paragraph).

**P8, measured, not built.** The recommendation was a `localSearchStepNodes` cap on the two fork
tests instead of a `deep` mark. Measured with three P2 solves on the other cores
(`tests/tax/test_itemized.py::test_local_search_keeps_the_loops_itemizing_branch`,
`tests/tax/test_star.py::test_local_search_carries_the_star_family`, through a scratch copy of
their setup):

| Test | As written | 300 nodes | 50 nodes | Other |
|---|---|---|---|---|
| itemizing | 88-100 s | 66-78 s | 67 s | 100 nodes, radius 1: 79 s; horizon 78/80: 59 s |
| STAR (`localSearchTime = 60`) | 83-97 s, the 60 s budget cut 3 searches | 188 s with the budget lifted (8 full searches) | | |

The restricted solves are slow per solve, not per node: in the itemizing test at 300 nodes, steps
that visit 1-3 nodes take 0.6-3.5 s and the capped ones 5-11 s, and its second and third searches
start from the previous binaries, move nothing, and spend 16 of their 17 s each in (b), (b') and
(a'), which is P2's pattern. The STAR test is bounded today by its wall-clock budget; a node cap
alone makes it slower. So the cap gives at most a fifth of these tests' time, and the options
left change what the default run covers (a `deep` mark: about 170 worker-seconds, some 40 s of
wall at `-n 4`) or wait for P2 upstream. **Dropped** (the user's call): nothing changed.

**P2 on stock upstream.** The issue needs a stock repro, so the prototype was written as a
patch to upstream's `localsearch.py` (`fork-notes/issue-ls-settled-steps.patch`, with a test)
and every shipped example solved on `dev` `8ec9c43` and on the patched checkout
(`performance/p2_stock_run.sh`, interleaved three at a time, both wall-clock caps lifted, the
date frozen at 2026-01-01; table by `performance/p2_stock_table.py`). The patch's rule is the
prototype's: an iteration that follows one whose search started from the previous binaries and
moved nothing runs (a) and (c) only.

| Example | Objective | Value, stock | Patched | Searches | Skipped | CPU stock | CPU patched | |
|---|---|---|---|---|---|---|---|---|
| Case_alex+jamie | maxSpending | 226,712.00 | same | 3 | 0 | 100.8 | 101.2 | +0% |
| Case_avery+quinn | maxBequest | 2,407,939.88 | same | 3 | 0 | 143.5 | 143.8 | +0% |
| Case_bill | maxSpending | 36,665.93 | same | 2 | 0 | 0.4 | 0.3 | -25% |
| Case_cameron | maxSpending | 18,996.31 | same | 2 | 0 | 1.0 | 1.1 | +10% |
| Case_chris+pat | maxSpending | 114,326.15 | same | 2 | 0 | 109.3 | 108.4 | -1% |
| Case_dana | maxSpending | 81,273.00 | same | 2 | 0 | 43.5 | 43.7 | +0% |
| Case_devon | maxSpending | 248,576.00 | same | 2 | 0 | 77.5 | 77.6 | +0% |
| Case_helen+ruth | maxSpending | 195,598.42 | same | 2 | 0 | 99.2 | 100.2 | +1% |
| Case_jack+jill | maxSpending | 111,038.88 | same | 4 | 1 | 291.6 | 239.0 | -18% |
| Case_joe | maxSpending | 99,080.90 | same | 5 | 3 | 191.1 | 97.2 | -49% |
| Case_john+sally | maxBequest | 14,013.49 | same | 2 | 0 | 51.8 | 51.6 | -0% |
| Case_jon+jane | maxSpending | 155,605.94 | same | 2 | 0 | 34.4 | 34.4 | +0% |
| Case_jordan+taylor-qcd | maxBequest | 1,206,372.88 | same | 2 | 0 | 69.2 | 69.2 | +0% |
| Case_jordan+taylor | maxBequest | 1,559,336.31 | same | 2 | 0 | 58.5 | 59.0 | +1% |
| Case_kim+sam-bequest | maxBequest | 1,962,072.42 | same | 2 | 0 | 250.6 | 251.7 | +0% |
| Case_kim+sam-spending | maxSpending | 186,383.24 | same | 2 | 0 | 219.7 | 220.3 | +0% |
| Case_morgan | maxSpending | 47,656.11 | same | 2 | 0 | 306.3 | 307.0 | +0% |
| Case_riley+casey | maxSpending | 118,949.85 | same | 4 | 0 | 769.3 | 767.7 | -0% |
| Case_robin | maxSpending | 44,159.28 | same | 2 | 0 | 18.6 | 19.4 | +4% |
| All 19 | | | 19 same | | 4 | 2,836.3 | 2,692.8 | -5.1% |

- **Every plan is the same to the cent** (19 of 19), as on the six fork variants of section P2.
- **The saving is concentrated** (read from each search's first step): in 14 examples the loop
  converges in two iterations, the second reusing the first plan (upstream's `785217c`), so there
  is nothing to skip. In `Case_alex+jamie`, `Case_avery+quinn` and `Case_riley+casey` the search
  that starts from the previous binaries and moves nothing is the last one, or is followed by a
  reuse. Only `Case_joe` (three searches skipped, -49% of CPU) and `Case_jack+jill` (one, -18%)
  have a search after one that moved nothing. Over the 19, -5.1%; on the six fork variants it
  was -20% (section P2), so the synthetic household's cases are among those that gain.
- **The repro** (`issue-ls-settled-steps-repro.py`, output in
  `issue-ls-settled-steps-repro-output.txt`, run beside other solves): `Case_joe`'s searches 2-4
  start from the previous binaries, move nothing and spend 89-91% of their time in (b), (b') and
  (a'); patched they take 3.5-4.9 s instead of 30-36 s, and the solve 102 instead of 199
  CPU-seconds.
- **The test** in the patch (`test_a_settled_search_skips_its_capped_steps`: Case_bill with the
  loop's convergence deferred to four iterations and the same-problem reuse turned off, 2.4 s)
  fails on stock `dev` and passes with the patch.

- **At upstream's default caps** (300 s per search, 60 s per step; `p2_stock_run.sh` with
  `CASES="Case_joe Case_jack+jill"` and `'{}'`, two solves at a time on an otherwise idle
  machine): the same plans, no budget cut on either side, `Case_joe` 190.2 -> 98.6 CPU-seconds
  (167 -> 84 s of wall), `Case_jack+jill` 291.4 -> 240.2 (269 -> 220 s).
- **Upstream's suite** on the patched checkout: 3318 passed, 1 skipped (10:53, `-n 2`, beside
  other solves).

The draft: `fork-notes/issue-ls-settled-steps.md`, **filed by the user as #252** with the two
options of section 6e and no patch. The open point it states is section P2's: no full search
confirms the plan once the loop has settled.

## 6e. Later on 2026-11-11: P2 with a confirming search

The user's question: "how do the P2 numbers change if we add a full search re-run to confirm the
plan? Is it still worth doing?"

**The variant** (`fork-notes/issue-ls-settled-steps-confirm.patch`, on upstream `dev` `8ec9c43`;
`localsearch.py` and four lines of `plan.py`). The rounds of the search move into
`LocalSearch._rounds`. When the loop's decision is "converged" and the search of that iteration
skipped its capped steps, `LocalSearch.confirm` runs the full rounds once on the same problem (the
plan's rows are still the last iteration's) from the accepted plan. It finds nothing: the loop
stops with the plan it had. It finds a better plan: the loop goes on from it, and its next
problem is searched in full. So at convergence the plan has had a full search on its own
problem, as on stock. Not covered: a loop that ends on a cycle, stagnation or its iteration cap
accepts an earlier iterate, whose problem is not the one in memory; there nothing is confirmed.
Two tests: the settled test extended (one confirmation, last in the log, with the capped steps);
a confirmation that finds a better plan sends the loop on (fails when the loop stops at it).
Upstream's suite with the variant: 3319 passed, 1 skipped (6:54, `-n 4`).

**Measured.** Same plans to the cent in every run; the confirming search found nothing in all 8
runs where it ran.

| | Base | P2 | P2 + confirmation | Confirming search |
|---|---|---|---|---|
| `Case_joe` (stock, caps lifted) | 193.5 | 99.6 (-49%) | 133.3 (-31%) | one full search |
| `Case_jack+jill` (stock, caps lifted) | 298.7 | 247.7 (-17%) | 303.9 (+2%) | one full search |
| Six synthetic variants, *Careful* (CPU) | 2,112 | 1,565 (-25.9%) | 1,841 (-12.8%) | 38-46 s each |
| Six synthetic variants, *Careful* (wall) | 1,893 | 1,386 (-26.8%) | 1,634 (-13.7%) | |

Stock: `p2_stock_run.sh` with `CASES="Case_joe Case_jack+jill"` and
`EXTRA="confirm=<checkout>"`, three at a time, interleaved; the other 17 examples skip nothing,
so the confirmation never runs there and their numbers are section 6d's. Over the 19, computed
from the two runs (the 17 from 6d, the two scaled by this run's ratios): about -1.9% of CPU with
the confirmation, against -5.1% without. Synthetic: `p2_fork_run.sh` (`solve_probe.py decision`,
today's preset: 1,000 nodes, both wall-clock caps lifted; ages 70/70), three checkouts of the
fork (`b5c2d7b` + nothing, + the patch, + the variant), three at a time, interleaved; table by
`p2_fork_table.py`. Per variant (CPU): queens_2027_arm5 -29% / -12%, queens_2031_cash -42% / -24%,
whiteplains_2029_mortgage -17% / -7%, whiteplains_2038_cash -15% / -6%, yonkers_2027_mortgage
-25% / -10%, yonkers_2034_cash -46% / -30%.

**What follows.** The confirmation costs one full search per solve that skipped anything, about
what a skipped iteration saved. So it halves the saving where two or three iterations were skipped
and cancels it where one was (`Case_jack+jill`). On the household's Careful solves: about 13%,
some 40 s of a 4-5 minute solve; on a 36-cell grid at four solves at a time (P1), about 7 minutes
of 50 (computed from the table, not run). On upstream's examples it is a `Case_joe` improvement and
nothing else.

The risk it insures against was not seen: in 25 cases (19 stock, 6 synthetic) the plan without the
confirmation was the stock plan to the cent, and in 8 confirmations nothing better was found.

## 6f. 2026-11-12: P2 fixed upstream (#252), checked on the fork

Upstream fixed #252 as `1d91494` ("Local search skips the capped steps once the binaries have
settled"), the first of the issue's two options: no confirming search. Merged here on 2026-11-12
(`c8a7d2e`, branch `claude/nice-euler-qy6161`; clean: `localsearch.py` is upstream's with the fork's
STAR family lines). Its code against `fork-notes/issue-ls-settled-steps.patch`: the same three
skips under the same condition; a `moved` flag set wherever a step is better replaces the patch's
comparison of the final objective with the start's (they differ only inside the `_IMPROVE` band,
1e-7 relative); the log line comes before the steps ("binaries settled; skipping (b), (b') and
(a')"). Its test runs `Case_joe` at `localSearchStepNodes = 100` with no monkeypatch.

**Checked on the six synthetic variants** (`p2_fork_run.sh`, `solve_probe.py decision`: today's
*Careful*, 1,000 nodes, both wall-clock caps lifted, ages 70/70; three checkouts, three at a time,
interleaved, 2026-11-12 00:58-01:21 UTC): `base` = the fork before the merge (`07b6c28`), `ours` =
the same with the draft patch, `upstream` = the merge (`c8a7d2e`). Table by `p2_fork_table.py`
(which now counts upstream's log line too).

| Variant | Spending (all three) | Searches | Skipped | CPU base | ours | upstream |
|---|---|---|---|---|---|---|
| queens_2027_arm5 | 106,893.12 | 5 | 2 | 255.8 | 180.6 (-29%) | 181.2 (-29%) |
| queens_2031_cash | 104,511.03 | 5 | 3 | 219.2 | 126.8 (-42%) | 127.7 (-42%) |
| whiteplains_2029_mortgage | 105,853.35 | 6 | 2 | 387.0 | 323.7 (-16%) | 324.3 (-16%) |
| whiteplains_2038_cash | 105,259.28 | 8 | 2 | 499.5 | 426.4 (-15%) | 426.0 (-15%) |
| yonkers_2027_mortgage | 109,150.60 | 5 | 2 | 247.2 | 183.6 (-26%) | 182.5 (-26%) |
| yonkers_2034_cash | 108,098.01 | 5 | 3 | 231.2 | 123.7 (-47%) | 123.8 (-46%) |
| Sum (CPU) | | | | 1,839.9 | 1,364.7 (-25.8%) | 1,365.5 (-25.8%) |
| Sum (wall) | | | | 1,637.3 | 1,193.1 (-27.1%) | 1,195.4 (-27.0%) |

Every plan the same to the cent in the three checkouts; every search of `upstream` has the same
steps, in the same order, with the same objectives, as `ours`; no search found its time budget
spent. The saving matches section 6e's (-25.9% CPU, -26.8% wall, another day's load: its base
summed 2,112 s). So the fork's *Careful* solves of these variants take about a quarter less, with
no change of plan; the confirming search (6e) is not in upstream and not in the fork.

## 7. Files

- `fork-notes/performance/solve_probe.py`: one timed solve, every HiGHS call recorded, optional
  dumps and the experiment knobs.
- `fork-notes/performance/quiet_patch.py`: P2's prototype (superseded by upstream's `1d91494`; it
  matches only the source before it).
- `fork-notes/performance/mip_probe.py`: one dumped HiGHS call re-solved with other options.
- `fork-notes/performance/library_bench.py`, `page_profile.py`: the 120-run library and the page
  profiles (the second needs `yappi`).
- `fork-notes/performance/audit/`: the 2026-11-11 scripts (its `README.md`).
- `fork-notes/performance/lifted_budget.sh`: the two non-settling variants with the caps lifted.
- `fork-notes/synthetic/check_library_cores.py`: the cores' check (section 6).
- `fork-notes/performance/ages_timing.py`, `ages_timing_parse.py`: one timed `ages` job, split by
  plan built (section 6b).
- `fork-notes/performance/thorough_kept_check.py`: "every pair tried" through real workers, kept
  plan against a solve again, on one core and on two (section 6c).
- `fork-notes/performance/suite_winner_check.py`: `run_suite.py`'s baseline row through two
  versions of the suite (section 6c).
- `fork-notes/performance/page_timing.py`: plain AppTest rerun times of the library pages (P6,
  section 6d).
- `fork-notes/performance/p2_stock_probe.py`, `p2_stock_run.sh`, `p2_stock_table.py`: P2 on the
  shipped examples, from checkouts of upstream `dev` (sections 6d, 6e).
- `fork-notes/performance/p2_fork_run.sh`, `p2_fork_table.py`: P2 on the six synthetic variants,
  from fork checkouts (sections 6e, 6f).
- `fork-notes/issue-ls-settled-steps.patch`, `issue-ls-settled-steps-confirm.patch`: P2 without
  and with the confirming search, on upstream `dev` `8ec9c43`.

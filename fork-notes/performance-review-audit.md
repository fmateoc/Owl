# Performance review: audit of a second review (2026-11-11)

The user pasted a second, anonymized answer to the same request as `performance-review.md`
("Owl Performance Review & Optimization Opportunities": a priority matrix of six P0, five P1
and two P2 items in four sections) and asked for its load-bearing claims to be checked, for
what is valid in it to be kept, and for `performance-review.md` to be revised.

Checked at `ff85a08` (code = `abd8b6c`) in this container (4 cores, Linux, HiGHS 1.15.1,
Streamlit 1.67.0), on the synthetic household, ages 70/70. Scripts: `fork-notes/performance/audit/`.
Every verdict says how it was reached: **read** (the cited lines read), **grep** (a text search),
**run** (a script's output, quoted). Nothing here was checked on Windows, where the second
review's paths say it was written.

Its line references match this checkout almost everywhere (`plan.py:7102`, `7184`, `7253`,
`8924`, `stresstests.py:131`, `189`, `1733`, `2111` all land on the named code), so it was
written against the same code.

## 1. Result

- **Its code reading is mostly right.** Of the 36 claims checked in section 3, 25 are as stated
  in structure, 2 are supported without a full check, 4 are partly wrong, 4 are false, and 1
  prediction is contradicted by a measurement; one sub-claim of a verified item is also false.
- **Its priorities are not supported.** It contains no timing: every figure is an estimate, and
  the ones that could be measured are off by one to three orders of magnitude where they
  matter. Its fifth P0 (cache the CSR matrix and money scaling, stop deep-copying in local
  search) addresses 0.25 s of a 129.4 s solve.
- **It found things `performance-review.md` missed**: the Run page parses the whole results
  workbook on every render (93 ms of a 260 ms page); `JobManager.tick()` scans the library
  three times; the stress tests, which the first review did not look at. Following the last one
  up produced a measurement neither review had: the stress tests' thread pool gives 1.6x on four
  cores, because 42% of a loop-mode solve is Python.
- **One statement of `performance-review.md` was too broad** and is corrected: "nothing in the
  Python layer ... can matter for solves" holds for a Careful solve (99.5% in HiGHS), not for
  Quick-look-class solves run by the hundred.

## 2. The measurements

### 2.1 A Careful solve, by function (`overhead_probe.py`)

`decision` preset, `yonkers_2027_mortgage`, `localSearchStepNodes = 300` (the setting where the
Python share is largest; at the default 3,000 the solve is 346 s and the Python is the same).
Cumulative time of top-level calls:

```
decision {'localSearchStepNodes': 300}: solved, wall 129.4 s
  Plan._run_highs                                 128.742 s     56 calls   99.48% of wall
  Plan._run_mip                                   121.717 s     42 calls   94.05% of wall
  Plan._buildConstraints                            0.204 s     18 calls    0.16% of wall
  copy.deepcopy (top level)                         0.126 s     11 calls    0.10% of wall
  ConstraintMatrix.to_csr                           0.061 s     60 calls    0.05% of wall
  LocalSearch._relax_links                          0.051 s      4 calls    0.04% of wall
  _MoneyScaling.for_mip                             0.014 s     56 calls    0.01% of wall
  Plan._adjustParameters                            0.008 s     20 calls    0.01% of wall
  Plan._configure_Medicare_binary_variables         0.007 s     18 calls    0.01% of wall
  LocalSearch._fingerprint                          0.007 s      4 calls    0.01% of wall
  Plan._configure_ss_taxability_lp                  0.006 s     18 calls    0.00% of wall
  Plan._snapBinaries                                0.006 s     53 calls    0.00% of wall
  Plan._repairBracketOrder                          0.003 s      2 calls    0.00% of wall
  Plan._ss_streams                                  0.002 s      3 calls    0.00% of wall
  Plan._earningsTestResult                          0.002 s      4 calls    0.00% of wall
  Plan._incomeCeiling                               0.002 s     18 calls    0.00% of wall
  Plan._restoreExclusions                           0.001 s      2 calls    0.00% of wall
  Plan._add_local_taxable_income                    0.000 s     18 calls    0.00% of wall
```

(`_run_mip` contains `_run_highs`; `_relax_links` contains a `deepcopy`.) Everything the second
review's sections 3.2, 4.2 and 4.3 propose to cache or drop sums to under 0.5 s.

### 2.2 A Quick look, by function (same script, `quick`)

```
quick {}: solved, wall 0.8 s
  Plan._run_highs                                   0.438 s     15 calls   57.99% of wall
  Plan._buildConstraints                            0.142 s     15 calls   18.77% of wall
  ConstraintMatrix.to_csr                           0.009 s     15 calls    1.16% of wall
  Plan._adjustParameters                            0.006 s     16 calls    0.76% of wall
  Plan._incomeCeiling                               0.002 s     15 calls    0.21% of wall
  Plan._ss_streams                                  0.001 s      2 calls    0.17% of wall
  Plan._earningsTestResult                          0.001 s      3 calls    0.16% of wall
```

Here 42% is Python, 19% of it the constraint build. One Quick look does not matter; section 2.4
is where this share does.

### 2.3 Single calls (`micro_timings.py`, `workbook_read.py`; best of 2-5)

| Operation | Time | Second review's item |
|---|---|---|
| `config_to_plan(loadHFP=True)` (`work_sweep.make_plan`) | 106 ms | 1.4 |
| `plan.readHFP(xlsx)` | 89 ms | 1.4 |
| `plan.readHFP(plan.rawHFP)` (what `clone(expectancy=)` runs) | 41 ms | 2.2 |
| `config_to_plan(loadHFP=False)` (`builder._throwaway_plan`) | 3.7 ms | 4.4 |
| `clone(plan)`, solved plan / unsolved plan | 11.6 ms / 2.7 ms | 1.2, 4.6 |
| `clone(plan, expectancy=...)`; memory held per clone | 47 ms; 0.15 MB | 1.2 |
| `copy.deepcopy(plan.A)` (978 rows, 1,296 columns, loop model) | 5.9 ms | 4.2 |
| `plan.A.to_csr()` | 0.39 ms | 4.2 |
| `amorepair.max_row_violation` | 2.9 ms | 2.5 |
| `plan._ss_streams` / `_earningsTestResult` | 0.39 / 0.25 ms | 4.3 |
| `thresholds.threshold_proximity(plan)` (once per result) | 32 ms | 2.4 |
| `brackets.bracket_view(plan)` | 1.7 ms | 4.6 |
| `export.plan_metrics(plan)` | 0.29 ms | 4.6 |
| `plan.saveWorkbook(saveToFile=False)` | 58 ms | 3.1, 4.6 |
| `plan.saveContributions()` (+ save to bytes) | 13 ms (32-126 ms) | 3.1 |
| `pd.read_excel(results workbook, sheet_name=None)`, 48 kB, 16 sheets | 93 ms | 3.1 |
| `results.environment()` | 4.9 ms | 3.5 |
| `results.code_stamp()`, clean tree, after the first call | 0.00 ms | 3.5 |
| `results.code_stamp()`, dirty tree (`git diff HEAD`) | 3 ms | 3.5 |
| `sequences.load_sequences()` | 0.58 ms | 3.3 |
| `_builtin_impl.load_historical_slice`, repeated | 0.00 ms | 3.4 |
| `_compute_efficient_frontier`, S = 100 / 500 / 1,000 | 0.13 / 0.33 / 1.05 s | 2.1 |

### 2.4 A stress test (`stress_probe.py 60`)

`run_stochastic_spending`, 60 historical start years, Quick-look options:

```
historical, 60 start years, 4 worker thread(s): wall 24.6 s
   clone (serial, main thread)                    0.16 s    60 calls  (0.6% of wall)
   _scenario_worker (summed over threads)        95.96 s    60 calls  (thread-seconds)
   _compute_efficient_frontier (serial)           0.29 s     2 calls  (1.2% of wall)
historical, 60 start years, 1 worker thread(s): wall 39.6 s
   clone (serial, main thread)                    0.10 s    60 calls  (0.2% of wall)
   _scenario_worker (summed over threads)        39.21 s    60 calls  (thread-seconds)
   _compute_efficient_frontier (serial)           0.25 s     2 calls  (0.6% of wall)
```

Four threads are 1.6x faster than one. A scenario takes 0.65 s alone and 1.6 s of thread time
among four: the Python share (section 2.2) holds the GIL. With the case's own options (local
search) the same 60 scenarios had not finished one pass in 400 s; that run was stopped.

Not run: Monte Carlo and longevity sampling (the synthetic case's rate method is not
stochastic; `run_stochastic_spending` refused it), the bequest frontier, the regret sweep.

## 3. Claims, one by one

Verdicts: **verified** (as stated), **supported** (the structure is as stated; the number is an
estimate nobody measured), **overstated** (the structure is as stated and the number was
measured to be much smaller), **false**, **not checkable here**.

### 3.1 The priority matrix

| # | Claim | Verdict | Basis |
|---|---|---|---|
| M1 | Closed form for `_stochastic_lp`: ">1,000x speedup on frontier construction (~1 GB fewer dense matrices; 122-1,586 LPs -> 1 sort)" | **The formula is false; the idea is verified; the priority is overstated** | run: section 4, F1. With a corrected formula the frontier goes from 1.05 s to 1.1 ms at S = 1,000, so ">1,000x" on that step holds. That step is 1.2% of the run measured (0.29 s of 24.6 s). The matrices are 8 MB each and live one at a time, not 1 GB |
| M2 | `Library.get()` scans every `run.json`; the Library page calls it per row | **verified** | read `store.py:415-419`, `ui/Library.py:43-46`, `206`, `219`. Same finding as P6 of `performance-review.md` (measured there: 128 scans, 15,480 reads at 120 runs). "3,360 reads at 60 runs" is the same order (supported) |
| M3 | `tick()` scans all `status.json` three times every 2 s | **verified; cost overstated** | read `jobs.py:146-158` (`adopt()` -> `jobs()`, then `jobs()` twice). Measured in the first review: `tick()` 47 ms at 120 runs / 239 results, 2.4% of one core. On Windows: not checkable here |
| M4 | The winning plan of the claiming-age search is solved again | **verified** | read `agesearch.py`, `worker.py:317-332` (P4a of the first review), `plan.py:7184`. "20-25% of Stage-2 time" matches 1 of 4-6 solves. For `_ssAgeSearch` it is 1 of `len(values) + 1` solves, each a second under the exact LP: not a P0 |
| M5 | "Cache CSR matrix & `_MoneyScaling`, and stop deep-copying ... Eliminates 8-12 full `ConstraintMatrix` deep-copies, 10+ CSR builds, and 1 `Plan.__dict__` deep-copy per SC-loop iteration" (P0) | **the copies exist (verified); the priority is false** | read `localsearch.py:226`, `374`, `plan.py:7253`, `8935`. run, section 2.1: 11 top-level deep copies in the whole solve, 0.126 s; 60 CSR builds, 0.061 s; money scaling 0.014 s. 0.2% of 129.4 s |
| M6 | Reuse scenario setup across the bequest grid; thread-local clones: "60-125x lower clone memory; eliminates 92% (12/13) of cloning & parameter setup" | **structure verified; numbers unsupported or overstated** | read `stresstests.py:1665-1669`, `1732-1733`, `2078-2111`. Memory per clone 0.15 MB (run), so 1,000 clones hold 150 MB. Cloning was 0.6% of the measured run. "13" is the caller's grid; the page's default has 5 points (`ui/Spending_vs_Bequest.py:37`, grep) |
| M7 | `work_sweep.py` re-reads the workbook 60-100 times per variant; `hfp_io.read` opens it twice | **verified; irrelevant in size** | read `work_sweep.py:214-222` and its six callers, `hfp_io.py:228`, `459`. 89 ms per read (run): 5-9 s per variant, in a sweep whose scored plans take 94-288 s each (CLAUDE.md) |
| M8 | Run page: every result loaded, the workbook parsed inside a collapsed expander on every render | **verified; a real miss of the first review** | read `ui/Run.py:554-561`, `816-817`; run: 93 ms per render, against the 260 ms the first review measured for the page. Its "150-400 ms": supported for another machine, 93 ms here. Its third sub-claim (the tornado loaded twice) is false, F4 |
| M9 | "Eliminate 4x redundant Social Security & `earnings_test` recomputations ... Cuts 75%+ of Social Security setup overhead" | **structure verified; irrelevant in size; the fix undoes a recorded decision** | read `plan.py:1532-1552`, `1488`, `2572`. run: `_ss_streams` 0.39 ms; 3 + 4 calls, 4 ms in a whole Careful solve. CLAUDE.md records why the builder's own output is used when the test withholds nothing ("plans the test does not touch follow upstream's builder by construction") |
| M10 | "move `_repairAmo` outside intermediate SC iterations ... Saves 1 extra LP solve + 2 Python row scans per intermediate SC iteration" | **false** | section 4, F2 |
| M11 | 15-25 throwaway `Plan` objects per sensitivity / export workflow | **verified; irrelevant in size** | read `builder.py:720`, `758`, `842`. 3.7 ms each (run): under 0.1 s |
| M12 | Vectorize `_conditionTimetables`, `thresholds.py`, `tax_federal.py`: "25-50x", "10-30x" | **structure verified; factors unsupported** | read `hfp_io.py:373`, `380`, `thresholds.py:124-131`, `tax_federal.py:1089-1095`. Base times: 41 ms, 32 ms once per result, and all of `_adjustParameters` 0.4 ms per call. Only the 41 ms recurs (per longevity clone) |
| M13 | `star.py`: "700 districts scanned per year ... 28,000 string formats/solve"; uncached rate-model fits | **the scan is verified; the count is New York's, not the table's (75 rows today); the fits are supported** | section 4, F5: 0.16 ms per solve today, 2.4 ms with a 730-row table; `grep -c lru_cache`: 0 in `copula.py`, `garch_dcc.py`, `vector_ar.py` |

### 3.2 Other load-bearing claims

| # | Claim | Verdict | Basis |
|---|---|---|---|
| S1 | Three 2-second loops poll at once (ticker thread, `Queue.py`, `Run.py`) | **verified** when both pages are open | grep `run_every`: `ui/Queue.py:63`, `ui/Run.py:160`; `jobs.py` `_tick_forever` |
| S2 | `run_historical_range` and `run_mc` are sequential and append with `df.loc[len(df)]` | **verified** | grep: `ThreadPoolExecutor` only at `stresstests.py:853`, `907`, `1751`; appends at `1390`, `1395`, `1495`, `1497` |
| S3 | Parallelizing them "(HiGHS releases the GIL) gives a 4x-12x wall-clock speedup" | **contradicted here for loop-mode scenarios** | run, section 2.4: the function that already does this gets 1.6x from four threads. Not measured for MIP-heavy scenarios, where the HiGHS share is higher |
| S4 | One fresh interpreter per job, `max_parallel = 1`; "1.5-3.5 seconds per job" on Windows | **verified** (structure); 1.5-2.0 s measured on Linux in the first review; Windows not checkable here | read `jobs.py:66`, `182` |
| S5 | `ages_thorough` runs on `_SerialPool`: "up to 81 MIP solves sequentially on 1 core (29-51 minutes)" | **structure verified; the minutes are unsupported** | read `worker.py:69`, `493` (P5 of the first review). 29-51 min is 21-38 s per solve; this repository records 94-288 s per scored plan on chris+pat here, which would be 2.1-6.5 h. Not checkable without the machine it was estimated for |
| S6 | `_tables_from_plan` round-trips through a temporary `.xlsx` | **verified; deliberate** | read `casefiles.py:523-530`; its docstring: "The HFP tables exactly as the Download button's workbook carries them" |
| S7 | The second frontier "is simply `frontier_g * xi_0`" when `with_longevity=False` | **verified, and already known to the code** | read `stresstests.py:1816-1819`: "Solved again rather than rescaled: ... on a fixed horizon this reproduces frontier_g * xi_0 exactly, while under longevity sampling ... no single factor is right. Sixty small LPs against minutes of scenario solves" |
| S8 | `grid.latest_result` loads each folder's three files before filtering on the record | **verified; small** | read `grid.py:388-391`; `view.load_result` 0.8 ms (first review) |
| S9 | `st.download_button(data=owb.saveContributions())` and `data=owb.saveWorkbook()` build workbooks on every rerun; a callable defers it | **verified** | grep: `ui/Financial_Profile.py:725`, `ui/Reports.py:174`. Streamlit 1.67.0's docstring: "data : str, bytes, file-like, or callable ... If a callable is passed, it is executed when the user clicks the download button". 13-126 ms and 58 ms+ per rerun (run). `Reports.py:69` is `hfp_buffer = owb.saveContributions()`, built on every rerun for the button at 138 (read) |
| S10 | `_fixedAcrossIterations` exists; `_incomeCeiling`, `_add_local_taxable_income`, `_configure_ss_taxability_lp`, `_configure_Medicare_binary_variables` are rebuilt per iteration | **verified; 15 ms in a Careful solve** | grep `plan.py:372`, `4396`, `4994`, `5334`, `5918` carry no decorator; run, section 2.1. Whether each is loop-invariant was not checked |
| S11 | `tx.taxParams(..., no_bonus, ...)` computed twice per iteration | **verified; under 0.4 ms** | read `plan.py:3051-3052`, `3553-3554`; all of `_adjustParameters` is 8 ms over 20 calls |
| S12 | `_irmaa_entries`: "`premiums(np.array(p.MAGI_n[:N]))[n_prem]` and `premiums(under_all)[n_prem]` are called on every year m even though their arguments do not depend on m" | **half false** | read `thresholds.py:128-131`: `under_all[m] = float(thresholds[0]) - 2 * _SLACK`. The first call's argument does not depend on `m`; the second's does |
| S13 | `max_row_violation` loops over rows in Python; a CSR product would be "~20 us vs ~4 ms" | **supported** | 2.9 ms measured; the CSR time not measured. Called twice per repair, once per solve (F2) |
| S14 | `plan_metrics` calls `budget_spending` twice; `bracket_view` calls `limits_cap` twice per year; `_format_col_sheet` rescans the sheet per column | **verified; under 2 ms, 2 ms, part of 58 ms** | read `export.py:1027-1028`, `brackets.py:262-263`, `export.py:282-289` |
| S15 | `save_run` exports the case before checking for a duplicate hash | **verified** | read `store.py:535` (`generate`) before `551` (`find_by_hash`, under the lock). A check before `generate` could be added; the one under the lock has to stay |
| S16 | `_diff_into` serializes both subtrees at every node | **verified; not timed** | read `scenario.py:404-407`; its comment gives the reason for canonical text over `==` (`1 == 1.0 == True`) |
| S17 | `canonicalize` validates events three times and the scenario twice | **partly verified** | read `casefiles.py:165-202`: `validate(scenario)` twice (lines 181, 201) and one `validate_events` call in view; the other two not looked for |
| S18 | `star.py` and `tax_local.py` use `toml`, `tax_state.py` `tomllib` | **verified** | grep: `star.py:40`, `tax_local.py:32`, `tax_state.py:29`. Both loaders are `lru_cache`d, so the parser runs once per process |
| S19 | `_fit_dcc` computes `eigvalsh`, `slogdet` and `solve` on the same matrix per step | **verified**; "3x faster" unsupported | read `garch_dcc.py:313-319` |
| S20 | "Every `load_plan()` call queries `importlib.metadata.version` for 8 packages and spawns `git rev-parse`, `git status --porcelain`, and (on a dirty tree) `git diff HEAD --binary` (100-500 ms on Windows)" | **partly false** | section 4, F6 |
| S21 | "`load_historical_slice(frm, to)` calls `pd.read_csv(file)` from disk on every call" | **false** | section 4, F3 |
| S22 | `_MoneyScaling.for_mip` is at `abcapi.py#L186-L246` | **false (wrong file)** | grep: `class _MoneyScaling` is `plan.py:222`; `abcapi.py` has `ConstraintMatrix` (91) and `to_csr` (175) |
| S23 | Collections: making K variants triggers "4K full library scans and 3K full job scans" | **supported** | `enqueue` ends with `self.tick()` (read `jobs.py:141`), three scans each; the page's loop was not read |
| S24 | `generate_historical_series`, `debts.py`, `fixedassets.py`, `copula.py` details; `_regret_objective_value`; `plan_to_excel` formatting twice; `clone` generating a throwaway rate series | **not checked** | |

## 4. The false and partly wrong claims, quoted

F1-F4 are false as quoted. F5 and F6 are partly wrong: each states something true beside
something that does not hold for this code.

**F1. The closed form.** "If lambda > 1: g* = max(0.0, b_(min(floor(S(1 - 1/lambda)), S-1)))" with
"b_(0) <= b_(1) <= ... <= b_(S-1)".

The objective's slope on the open interval between the m-th and (m+1)-th smallest basis is
1 - lambda m / S (m scenarios lie below g). It is positive while m < S / lambda, so the maximum
is at the sorted index ceil(S / lambda) - 1, not floor(S (1 - 1 / lambda)). The quoted index is
the mirror image: as lambda grows it goes to S - 1, the largest basis, where the function's
own docstring says "lambda->inf -> maximin (worst-case optimal)". `quantile_check.py`:

```
S=7: candidate formula differs at 43/61 lambdas (max |dg| 33,127.70); corrected differs at 0/61 (max |dg| 0.00, max objective gap 0.00e+00)
   lam=1000: LP g = 80452.64  min = 80452.64  max = 113580.34  candidate g = 113580.34
S=100: candidate formula differs at 45/61 lambdas (max |dg| 72,435.02); corrected differs at 0/61 (max |dg| 0.00, max objective gap 1.46e-11)
   lam=1000: LP g = 59332.56  min = 59332.56  max = 131767.58  candidate g = 131767.58
S=1000: candidate formula differs at 45/61 lambdas (max |dg| 102,477.19); corrected differs at 1/61 (max |dg| 7,029.41, max objective gap 0.00e+00)
   lam=1000: LP g = 53797.33  min = 46767.93  max = 156274.52  candidate g = 156274.52
```

The corrected form's one difference (S = 1,000, lambda = 1,000) is a tie: S / lambda = 1 exactly,
the slope between the two smallest bases is zero, and the LP returned the other end of the
interval with the same objective (gap 0). A replacement has to pick a rule for ties, and the
frontier's shortfall probability differs between the two ends. What would change this verdict:
a statement that the bases are sorted in descending order; the text says ascending.

**F2. `_repairAmo`.** "In `Plan.solve`, `if self.amo == "optimize": x = self._repairAmo(x)` runs
on **every intermediate SC-loop iteration**, executing an extra LP solve (`_solve_lp_relaxation`)
and two Python-loop `max_row_violation` passes per iteration".

`grep -rn "_repairAmo\|self\.amo\b" src ui tests fork-notes` finds nothing: neither the method
nor the attribute exists, and `plan.py:7016` is in the lines after `self._scSolve(...)`. The
repairs that call `amorepair.max_row_violation` are `_repairBracketOrder` and
`_restoreExclusions`, called at `plan.py:7974` and `7976`, after the loop. Counted (section 2.2):
one call of each in a Quick look of 15 loop iterations; two of each in the Careful solve of 18
constraint builds (the loop and the local search each end once). What would change this
verdict: a commit of this repository or of upstream in which the quoted line exists.

**F3. `load_historical_slice`.** Quoted in S21. `rate_models/_builtin_impl.py:32-33`:

```python
@functools.lru_cache(maxsize=None)
def load_historical_slice(frm: int, to: int):
    """Return (data_decimal, years) for the given year range, cached by (frm, to)."""
```

A repeated call takes 0.00 ms (section 2.3).

**F4. The tornado loaded twice.** "`tornado.base_result(run.path)` and `{m.run_id:
tornado.result_of(m.run_id) ...}` are evaluated **twice in a row** (at L988-992 and again at
L997-1001)".

`grep -n "tornado.base_result\|tornado.result_of" ui/*.py` finds two call sites, `ui/Run.py:988`
(one `base_result` per preset, two presets) and `ui/Run.py:1001` (one `result_of` per member,
inside the loop that starts at 992). Lines 988-992 load the bases and 997-1001 load the
children: each result once. The quoted dictionary comprehension is not in the file. That these
loads run with the expander collapsed is true, as for every Streamlit expander.

**F5. 700 school districts (partly wrong; corrected 2026-11-11 after the user's objection).** "it
linearly scans all ~700 NY school district dicts in `program(state)["districts"]` ... (~28,000
string formats per NY solve!)".

Two different counts are in play, and the first version of this audit named only one of them:

- *New York's districts.* About 700 is right for the state: the user reports 730 from
  data.nysed.gov. Not verified here (`curl https://data.nysed.gov/` is refused by this
  container's proxy, "CONNECT tunnel failed, response 403"); nothing here disputes it.
- *The rows the code scans.* `program(state)["districts"]` is the list in the fork's own data
  file, `src/owlplanner/data/property_tax_relief.toml`, which holds the STAR credit amounts
  typed in from tax.ny.gov's county pages. `grep -c '^\[\[NY\.districts\]\]'` on it gives 75
  (27 municipalities); its line 34 says "Only Westchester County and New York City are here; to
  add a county, copy its page's rows." So the quoted sentence is wrong about what runs today:
  at most 75 x 28 = 2,100 key comparisons per solve, not 28,000.

The scan itself (`star.py:97-101`, inside the year loop at 230-233) is as described, and
`star_schedule` runs once per solve. Measured (`audit/star_scan.py`, the plan's district placed
last, the worst case):

```
data file as it is: 75 district rows; Quick look 0.67 s; star_schedule called 1 times, 0.16 ms in total (0.02% of the solve)
padded to a statewide table: 730 district rows; Quick look 0.59 s; star_schedule called 1 times, 2.38 ms in total (0.41% of the solve)
```

So if the table is ever filled for the whole state, the second review's count becomes about
right (730 x 28 = 20,440) and the scan costs 2.4 ms per solve. A dictionary by key is a
three-line change and harmless; it is not a performance item at either size.

**F6. `git` on every `load_plan`.** Quoted in S20. `version.engine_commit` is
`@lru_cache(maxsize=1)` (`version.py:28`): `git rev-parse` and `git status` run once per
process. `results.environment()` is not cached (4.9 ms). Only `_package_diff_sha256` repeats,
and only on a dirty tree (3 ms here). "100-500 ms on Windows" is not checkable here, and would
apply to the first call and to dirty trees.

## 5. What is worth building on

1. **The Run page's workbook read** (M8). Fork code, 93 ms of every render of the page the
   interface opens on once a plan exists. Now P9 of `performance-review.md`.
2. **One library scan per tick and per page** (M2, M3, S23). The first review measured the tick
   at 47 ms and filed it under "no opportunity"; it is a three-line change that removes two
   thirds of it, and the same index removes P6's quadratic. Folded into P6.
3. **Download buttons as callables** (S9). Upstream pages; verified against the installed
   Streamlit. Now P10.
4. **The stress tests** (M1, M6, S2, S3). The first review did not cover them. The second
   review's own items there are small (the frontier 1.2%, cloning 0.6%), but the measurement
   they prompted is not: four threads give 1.6x. Now section 3b of `performance-review.md`.
5. **The closed form for the frontier**, with the corrected index and a tie rule: exact, removes
   122 `linprog` calls, and worth 0.25-2 s per stress test. An upstream nicety.
6. **`save_run`'s duplicate check before the export** (S15) and **`latest_result` reading the
   record first** (S8): correct, small, fork code.

Not worth building, on the measurements: M5, M9, M11, M12 (except `_conditionTimetables` under
longevity sampling, which was not run), S10, S11, S13, S14, S18.

## 6. What changed in `performance-review.md`

- Section 1's first paragraph: the claim about the Python layer is scoped to Careful solves,
  with the Quick-look split (58% HiGHS) beside it.
- P6: the tick's three scans added; one index serves the pages and the tick.
- New P9 (Run page workbook), P10 (download buttons), section 3b (stress tests: threads 1.6x;
  the frontier's closed form; longevity clones).
- Section 4: the per-function table of section 2.1 here replaces "under 1%" as the evidence; the
  ticker line moved to P6; the second review's measured non-opportunities listed.
- Section 5: stress tests under Monte Carlo and longevity, and Windows, named as not measured.
- P4a, P5, P1, P7 are unchanged: the second review reaches the same findings from the code
  (M4, S5, S4), without timings.

## 7. Agreed, disputed, open

**Agreed facts** (both reviews, each verified in the code): jobs run one at a time in a fresh
interpreter each; `Library.get` scans the whole library and the pages call it per row; the
claiming-age presets re-solve the plan they already solved; `ages_thorough` is serial; local
search deep-copies the constraint matrix and rebuilds its CSR form per call; the Run page loads
every result of the run.

**Disputed**

- *Priority.* The second review ranks Python-side caching in solves as P0/P1 (M5, M9, M10, S10).
  Measured: 0.2-0.4% of a Careful solve. Confidence that these are not worth doing for solve
  time: high for this household shape (one case, one machine, both a 129 s and a 346 s solve);
  the shares cannot grow on a faster machine, since both parts scale together.
- *The polling "storm".* Verified as three scans; 47 ms per tick on Linux at 239 results.
  Whether it is noticeable on Windows with a virus scanner on every file open is open: medium
  confidence that it is not, no measurement.
- *Thread parallelism for the remaining serial stress tests* (S3): 4-12x claimed, 1.6x measured
  in the sibling function for loop-mode scenarios. High confidence in the measurement, low in
  its transfer to MIP scenarios.
- *The two findings of `performance-review.md` the second review does not have* (P2, P3: the
  node-capped local-search steps are 83% of a Careful solve and most find nothing) are not
  contradicted by anything in it; it does not mention the solver's share at all.

**Open questions**

- Windows: process start, file-open cost, `git` cost, the 29-51 minutes of S5.
- Stress tests on a process pool, and with Monte Carlo and longevity sampling (clone 47 ms per
  scenario, serial, against 0.4-0.65 s per scenario: about a tenth of the run, inferred).
- Whether upstream wants the frontier's closed form given its comment at `stresstests.py:1816`.
- S24's items, unchecked.

**Confidence**

| Statement | Confidence | Why |
|---|---|---|
| F1-F4 are false as quoted | high | each reproduced by a run or a grep shown above |
| F5: the code scans 75 rows today, whatever the state's count | high | grep and run on the data file; the state's 730 is the user's figure, not checked here |
| F6 is partly false | high for the caching (read); none for Windows timings |
| 25 claims are as stated in structure | high | cited lines read at the same commit |
| Python-side caching is under 0.5% of a Careful solve | high | timers on a real solve |
| Threads give 1.6x in the stress tests | medium-high | one run each way, one case, loop-mode options |
| The Run page workbook read is 36% of that page's render | medium | 93 ms measured in isolation, 260 ms measured for the page a day earlier on a different library |
| The magnitudes on the user's Windows machine | low | nothing was run there |

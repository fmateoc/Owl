# Review of the run-library design (2026-11-01)

Review of `fork-notes/run-library-design.md` after the user's decisions (D1-D9 in principle,
D10 no, D11 yes). Each finding was checked against the code or the fork's notes. Where a finding
rests on something not checked, it says so. The design was then fixed in place; the last column
says where.

## Findings

| # | Severity | Finding | Evidence | Fixed in |
|---|---|---|---|---|
| R1 | high | **A run's inputs are valid only in the calendar year they were entered for.** Owl starts the plan in the solve year and ignores `start_date`'s year, so a run solved in 2027 reads its January-2026 balances as January-2027 balances, with no warning. The design's "run the whole collection again today" would do exactly that after New Year. | `Plan._setStartingDate` docstring: "Year is ignored"; `thisyear = date.today().year` at every use in `plan.py` (grep, 2026-11-01) | §4 (plan year), §8.3 (D4 revised: date freeze required, else refuse), step 2 |
| R2 | high | **The tolerance rule does not work for the Decision preset.** Local search reports no gap: the synthetic run's log showed `gap: -1.0e+00` on every local-search iteration. The exact LP mis-prices the ACA years this household has (2027-2029), so the gap between local search and the exact LP measures a model difference, not noise. | Log of the 2026-11-01 `owlcli run`; CLAUDE.md "Loop noise", "Not in ACA years"; `run_suite.py` marks under-1% differences `~` and reports an agreement table | §8.1 (Decision preset), §9.2 (judging rules) |
| R3 | high | **The outcome is two numbers.** With savings spent by 89 and the condo kept, `run_suite.py` reports the score (the first year's discretionary spending) and the home at the end side by side, "and does not add them". The design ranked by one number ("current leader", cells coloured by one difference), which would hide the main trade-off of the condo grid. | `run_suite.py` docstring, lines 47-53; `condo_pivot` shows both | §9.1 (headline numbers), §9.2 ("two numbers, not one", dominance), §9.3 |
| R4 | medium | **"Quick look" would not be quick on the template.** `withSSAges = "optimize"` with `withMedicare = "optimize"` makes every age candidate a branch-and-bound MIP. The "Ages" preset also named two different methods: `run_suite.py`'s two-stage search and `work_sweep.py`'s branch-and-bound over every pair. | Template comment; `phase0-scenarios.md` §4; `run_suite.two_stage_ages` docstring | §8.1: ages fixed except in the two Ages presets, now split in two |
| R5 | medium | **Job lifecycle was wrong or unspecified.** "When the server stops, running jobs stop too" depends on how the server stops: Ctrl-C reaches the whole process group, a server killed alone leaves its children running, and `multiprocessing` waits for non-daemon children at exit. Also missing: one manager for several tabs, concurrent writes, and thread oversubscription with "cores / 2" parallel jobs. | Process behaviour recalled, not tested here; threads: CLAUDE.md "Fork after HiGHS hangs" (claiming-age candidates run on threads), `work_sweep.py` has its own pool | §5 (atomic writes), §8.2 (own-session workers, PID and heartbeat, singleton manager, default 1 job) |
| R6 | medium | **Steps 1-3 could not save an unsolved case from the existing pages.** `owlbridge.getCaseString` returns an empty string until the first run, as its comment says. `config.ui_to_config` builds the case dictionary from the page keys and is what `prepareRun` uses. | `ui/owlbridge.py` `getCaseString` and lines 191-195 | Step 1 |
| R7 | medium | **The scenario lacked Owl inputs the template sets:** objective and bequest floor, Roth conversion policy (the suite's Roth pair), asset allocation, `previousMAGIs` / `previousSTARIncomes`, the spousal deposit split, the survivor's spending share. | `fork-notes/phase0/Case_us.template.toml` | §6.1 (Goal and Owl settings rows) |
| R8 | medium | **Build order contradicted D2.** Steps 1-3 store `scenario.json`, but the scenario model was step 4. There was also no plan for format changes. | Design §11 as drafted | §6.3a (schema v1 = hand rows in step 1, events later, migrations), step 1 |
| R9 | medium | **Undefined: what a re-solve reads.** If a re-solve regenerated the files, a builder fix would silently change old runs. | Design §5, §6.2 as drafted | §5: generated files frozen per run; builder badge |
| R10 | low | **Pickles run code when loaded.** "Open in Owl" from the cache is also unverified. A UI case can be built from a Plan by `owlbridge.genDic`, but that path was not tried. | Pickle semantics (recalled); `ui/owlbridge.py` `genDic` (line 1972) | §10 (own pickles only, hash-checked; none from zips); step 2 check marked unverified |
| R11 | low | **The localhost rule had no mechanism, and one claim was wrong.** A running app cannot rebind its own server, so the rule needs a launcher flag and a start-up check. "Load a Case Example" reads local files, not GitHub, despite its caption; the earlier claim is corrected in the design and in `running-locally.md`. | `ui/tomlexamples.loadCaseExample` and `loadWagesExample` open `../examples/...` | §10; `running-locally.md` |
| R12 | low | **I12 is annual in Owl.** "The last 28 months" becomes the last two or three plan years. Budget lines can count back from the plan end (`end` < 0) or end at a person's death (age clock). | `phase0-scenarios.md` §5; CLAUDE.md Track B | Noted here; I12 unchanged |
| R13 | low | **D11 has a near-miss.** Owl can load a rate model from a Python file (`load_rate_model(method, method_file)`, `plan.py`), but `method_file` is not settable from a case file (no hit in `config/`), and a case file that runs Python is worse than one that reads a table. The `dataframe` model is "Programmatic use only". | `rate_models/loader.py`, `rate_models/dataframe.py`; grep of `config/` | Step 5b: a rates CSV read by a new method, kept in the run's inputs and hash |

## Checked and left as designed

- **Immutability, save-as and the computed change summary** (§7). They are consistent with D3,
  and the inputs hash includes the builder version, so a builder change cannot alias two runs.
- **Several results per run** (§5). This is needed in any case: the Decision preset's second
  model, and re-solves on another day within the plan year.
- **The I4 check-in** fits R1: it is how a new plan year enters the library.
- **D10 (no) and D11 (yes)** are applied: I10 is marked declined, and the rate table is build
  step 5b.

## Still open after the review

- ~~R1: confirm the revision of D4~~: confirmed by the user, 2026-11-01.
- **The date freeze outside pytest** (step 2). It patches `date` in every loaded `owlplanner`
  module, as `tests/conftest.py` does; whether that covers every date use in a worker is to be
  tested.
- **"Open in Owl" from a cached plan** (step 2, R10): to be tried.
- **Parallel jobs:** measure how many solves fit at once before raising the default of 1.

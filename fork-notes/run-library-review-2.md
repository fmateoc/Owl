# Second review of the run-library design (2026-11-01)

Second pass over `fork-notes/run-library-design.md` after the first review's fixes (R1-R13,
`run-library-review.md`) were folded in. This review numbers its own findings **S1-S13**. Every
design claim that names code was checked again (the table below); where a finding rests on
recalled behaviour, it says so. The fixes are folded into the design; the last column says where.

## Claims checked (2026-11-01)

| Claim | Checked |
|---|---|
| `export.plan_metrics`, `cli/formatters.plan_to_dict`, `owlbridge.saveContributions` / `getCaseString` / `genDic`, `config.ui_bridge.ui_to_config` and `SOLVER_UI_PASSTHROUGH_KEYS` (with `withItemized`, `withSTAR`), `run_suite.two_stage_ages`, `stresstests.g_for_success_rate` / `run_conversion_regret_sweep`, `tomlexamples.loadCaseExample` | all exist as cited (grep) |
| `getCaseString` empty before the first run (R6) | its own comment, `ui/owlbridge.py:1914` |
| the date freeze D4 (b) relies on | `tests/conftest.py`: `_FixedDate`, `freeze_year()` patches `date` in "every already-imported module" |
| `make_cases.py`'s builder pieces; the joint brokerage split in two halves | `rent_lines` / `owner_lines` / `write_hfp` / `case`; "entered as two equal" halves |
| step 4's benchmark "39 workbooks" | generated here: 39 workbooks, 36 condo variants, 7 work variants |
| `otherFiles/` gitignored; `OWL_ASSISTANT=1` as the opt-in precedent; R1's "Year is ignored" | `.gitignore:88`; `ui/assistant_core.py`; `plan.py:872` |
| a date input for `owlcli` (S7) | none: no `--as-of` or date option in `src/owlplanner/cli/` (grep) |

## Findings

| # | Severity | Finding | Evidence | Fixed in |
|---|---|---|---|---|
| S1 | high | **"A date in the run's plan year" is not enough.** §8.3 (b) froze the worker's date to *a* date in the plan year, but the day within the year sets `yearFracLeft` (the share of the first year left), so two solves of identical inputs frozen at different days are different plans. That breaks step 2's own check ("two solves on different days give identical results") and cross-run comparison. The frozen date must be deterministic per run: the scenario's "as of" date, recorded in `record.json`. | `Plan._setStartingDate` reads today (R1); `yearFracLeft` follows from the start date (recalled from the code's use of today's date; the effect was not measured) | §4, §5 (`record.json`), §8.3 (b), step 2 |
| S2 | high | **Queued-but-unstarted jobs have no on-disk record.** §8.2 said "the queue itself lives on disk", but the only artifact described was `status.json`, written *by a worker*. A waiting job has no worker yet, so a server restart silently loses it — including a whole "run the collection again today" batch. | design §8.2 as drafted | §8.2 |
| S3 | medium | **"Overwrite draft" versus failed solves.** §7 offers overwrite only for "an unsolved draft", but a failed or interrupted solve leaves `record.json` and `solve.log` — evidence worth keeping. Whether such a run is "unsolved" was undefined. | design §4, §7 as drafted | §4, §7 |
| S4 | medium | **Rename versus folder name, and Windows.** §5's `<date>_<slug>` with "the slug follows renames" did not say whether the folder renames. Renaming a run's folder while a job writes inside it fails on Windows (open handles; recalled, not tested here). | design §5 as drafted | §5, §7 |
| S5 | medium | **Two tabs can lose `library.json` updates.** Atomic rename (R5) prevents corruption, not lost updates; the singleton manager covers jobs, not saves. Two sessions adding runs to one collection race on read-modify-write. | design §5 as drafted | §5 |
| S6 | medium | **`plan.pkl` staleness was keyed only on the Owl commit.** Pickles also break across Python versions (the env runs 3.14) and pandas/numpy upgrades, and a failed load should degrade, not error. | pickle semantics (recalled); `.python-version` | §5 |
| S7 | medium | **"Reproduces a run" was not achievable as designed.** §5 claims `owlcli run` reproduces a run and step 5b checks `owlcli run` against the interface, but the date freeze lives in a worker monkeypatch and there is no date input in `cli/` (checked). Also `tests/conftest.py`'s mechanism patches only already-imported modules: a lazy import during a solve sees the real date. | grep of `src/owlplanner/cli/`; `tests/conftest.py:78-88`; the mechanism is untested outside pytest (R1's open item) | §5, §8.3 (b), §12, step 2 |
| S8 | low | **Heartbeat versus laptop sleep or a long iteration.** A paused worker looks dead, is marked interrupted, and "run again" can then put two workers on one run. | design §8.2 as drafted; process behaviour (recalled) | §8.2 |
| S9 | low | **Cancel by PID** can signal a recycled PID if the worker died and the OS reused the number. | process behaviour (recalled) | §8.2 |
| S10 | low | **"Canonical `scenario.json`"** for the inputs hash was undefined; byte differences (key order, number formatting) defeat the identical-inputs dedupe. | design §5 as drafted | §5 |
| S11 | low | **§6.3's override machinery is the heaviest piece of step 4** (per-cell overrides, remainder decomposition, orphan semantics), and its motivating example (adjust one closing-cost figure) is a hand edit to a hand row in schema v1. Scope, not correctness: ship provenance markers first. | design §6.3 as drafted | §6.3, step 4 |
| S12 | low | **"Per-browser draft" in browser storage needs a custom Streamlit component** (no native localStorage). A server-side scratch entry is simpler, and the design already says nothing depends on it. | Streamlit API (recalled) | §7 |
| S13 | low | **Comparison flags cover dates and presets (§9.2) but not the Owl commit**, though `record.json` holds it. | design §9.2 as drafted | §9.2 |

## Checked and left as designed

- **Immutability, save-as and the computed change summary** (§7): consistent with D3, and the
  inputs hash includes the builder version.
- **Frozen generated files** (§5, R9) and the several-results rule: sound together.
- **Presets and the noise rule** (§8.1, §9.2, R2/R4): match `run_suite.py`'s docstring and
  `_score_plan` (checked).
- **The two-number outcome and the dominance rule** (§9.2, R3): match `run_suite.py` exactly
  ("the report shows both and does not add them", lines 46-53).
- **Scenario sections** (§6.1, R7) and the **schema plan** (§6.3a, R8): the build order no longer
  contradicts D2.
- **Privacy** (§10): localhost launcher plus start-up check, pickle hash, trash — sound.
- **S11's mechanism stays**: the note folded into §6.3 changes only what step 4 ships first.

## Still open after the review

- **The date freeze outside pytest** (R1's open item): now specified (§8.3 (b): the run's "as of"
  date as a first-class `as_of` input); to be built in step 2 and checked.
- **"Open in Owl" from a cached plan** (step 2, R10): to be tried.
- **Parallel jobs:** measure how many solves fit at once before raising the default of 1.

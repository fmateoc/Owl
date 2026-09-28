# Phase 1 / Part B Step 1 — Progress

State and local income tax accuracy for the NY-metro retirement case.
Master plan: `myfiles/requirements.md`. Upstream: `mdlacasse/Owl`.

## Done

| PR | Commit | What |
|----|--------|------|
| PR 1 `[fix]` | `d236bcad` | State tax base is AGI, not federal taxable income. `income_base` TOML field. `tss` SS-exclusion fix. Re-baselined 3 regression reference sets. |
| PR 2 `[refactor]+[feat]` | `964f0866` | Frozen `StateTaxParams` dataclass. `indexed = false` for NY (brackets not statutorily indexed). |
| PR 3 `[refactor]` | `86d24314` | `_SC_PARAMS` registry + `_snapshot_sc`/`_restore_sc`/`_blend_sc`/`_sc_trace_*`. Adding a loop-fed cost is now one line. |

All three on `main`, full suite green (2009 pass, 3 pre-existing Windows failures
that also fail on `main`). flake8 clean.

## Not yet done

### PR 4 — `[feat]` generic state benefit recapture (NY §601(d-1))
The next PR. `recapture` field in `StateTaxParams` is already `None`.
See requirements.md "PR 4" for the full spec: TOML `recapture`/`recapture_phase_width`,
`recapture_tiers()` + `state_recapture()` in `tax_state.py`, `withStateRecapture`
option wired like `withNIIT`, `STR_n` added to `_SC_PARAMS` (one line, thanks to PR 3),
loop + optimize modes, tests in `tests/tax/test_state_recapture.py`.

### PR 5 — `[feat]` pluggable local income-tax layer (Yonkers, NYC)
`data/taxes_local.toml`, `tax_local.py`, `Plan.setStateTax(state, locality)`,
bracket/surcharge LP types. See requirements.md "PR 5".

### Phase 0 — baseline case (user data required)
Scaffold is in `otherFiles/`: `Case_us.toml` (TODOs for balances/PIA/basis),
`HFP_us.xlsx` (fill 2026 wages + big-ticket items), `gen_hfp_us.py`,
`phase0-scenarios.md` (owlcli compare commands). Needs real financial data.

### Upstream
Issue filed at `mdlacasse/Owl` (state-base bug, 2026-09-28).
Repro script: `scripts/repro_state_base_bug.py`.
Issue body archived at `otherFiles/upstream-issue-state-base.md`.

## Key context for resuming

- `taxes_state.toml` is CRLF; binary-safe replacements needed for edits on Windows.
- `scripts/` and `otherFiles/` are gitignored; force-add with `git add -f` when needed.
- Regression baselines live in `tests/data/amo_mip_reference.json`, `EXPECTED_OBJECTIVE_VALUES`
  in `tests/plan/test_toml_cases.py`, and pins in `tests/stochastic/test_regret_sweep.py`.
  Re-baseline with `scripts/rebaseline_state_tax.py` after tax changes.
- MOSEK is not available on this machine (no license); only HiGHS is tested.
- The 3 pre-existing failures: 2x UnicodeDecodeError in `test_config_ui_bridge` (Windows
  cp1252 vs plan.py UTF-8), 1x stale seed reference in `test_seed_reproducibility`.

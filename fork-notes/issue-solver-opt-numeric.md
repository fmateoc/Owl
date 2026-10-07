# Draft upstream issue (mdlacasse/Owl): `--solver-opt withSSTaxability=0.85` is silently ignored

Status: draft, ready to file (2026-10-07). Repro run on stock `dev` `004c840`; patch
`fork-notes/issue-solver-opt-numeric.patch` verified on the same commit (see the end).

**Title:** CLI: a numeric `withSSTaxability` given with `--solver-opt` stays a string, and the plan runs the loop instead of the pinned fraction

---

`owlcli run` and `owlcli compare` pass `--solver-opt KEY=VALUE` values as text and let
`parse_solver_options()` coerce them through `SolverOptions`. That works for `Optional[float]` fields
(`netSpending=80` becomes `80.0`), but `withSSTaxability` is `Optional[Union[str, float]]`, and
pydantic keeps the text `"0.85"` as a `str`. `_build_sc_loop_policy` then sees no number
(`isinstance(ss_val, (int, float))` is false), so the fraction is not pinned and the loop's formula
runs instead. Nothing warns.

```python
>>> from owlplanner.config.schema import parse_solver_options
>>> parse_solver_options({"withSSTaxability": "0.85"})["withSSTaxability"]
'0.85'
```

**Repro** (stock `dev` `004c840`, `examples/`):

```bash
owlcli compare Case_jack+jill.toml --set solver_options.withSSTaxability=0.85
owlcli compare Case_jack+jill.toml --set solver_options.withSSTaxability=0.85 \
    --solver-opt withSSTaxability=0.85
```

`spending_basis` and `federal_income_tax_today` from the JSON output:

| Run | base | variant |
|---|---|---|
| `--set` only (the variant pinned) | 102,544.65 / 207,239.61 | 101,448.13 / 239,780.13 |
| plus `--solver-opt withSSTaxability=0.85` (both runs should be pinned) | 102,544.65 / 207,239.61 | 102,544.65 / 207,239.61 |

In the second run both cases come out equal to the unpinned base: the `--solver-opt` value
replaced the variant's numeric `0.85` with the string, and neither run pinned anything.

**Patch** (`issue-solver-opt-numeric.patch`, 2 files, +35): a `mode="before"` field validator on
`SolverOptions.withSSTaxability` that reads text parsing as a number as that number, and leaves
`"loop"`/`"optimize"` alone; three tests in `tests/config/test_solver_opt_numeric.py`. With it, the
second command gives 101,448.13 / 239,780.13 for both runs (both pinned). Full suite on `dev`
`004c840` with the patch alone: 2712 passed, 1 skipped (`dev` alone: 2709); flake8 clean on the new test file (the one long line in `schema.py`, 386, is upstream's own).

`withMedicare` (`Union[str, bool]`) and `withSSAges` (`Union[str, List[str]]`) have the same
shape. Their usual values are text ("loop", "optimize", "None"), so the patch leaves them alone; we
did not check how a boolean or a list typed with `--solver-opt` is read.

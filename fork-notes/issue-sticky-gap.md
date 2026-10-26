# Draft upstream issue: the sticky-binaries tie can take a plan outside a requested MIP gap

Status: **draft, not filed** (2026-10-26). Found while deciding claiming ages by branch-and-bound at
`gap=1e-5` in the fork's work sweep (PROGRESS.md "Why the reported gap exceeds `mip_rel_gap`",
"relTol equal to the gap, measured"). Every number below comes from stock upstream `dev` `4dcfabb`,
run 2026-10-26 (plans start today, so a later run can move by dollars):
- `fork-notes/issue-sticky-gap-repro.py`, output `issue-sticky-gap-repro-output.txt`, on stock and
  then with the patch;
- the patch `fork-notes/issue-sticky-gap.patch` (`plan.py` +9/-3, two tests in
  `tests/solver/test_sticky_binaries.py`; applies cleanly on `4dcfabb`; the refusal test fails on
  stock and passes with the patch).

Upstream suite on `4dcfabb` with the patch: 3248 passed, 1 skipped (7:03); `-m deep`: 6 passed,
3 skipped (6:21). The 3 skips are `test_pathological_cases_settle[joe, jack+jill, avery+quinn]`, the
convergence test that motivated the sticky binaries; it runs under MOSEK only and could not be run
here (HiGHS only, no licence).

Not in the issue: the simpler alternative of capping the tie at the gap, `_sticky_tol = min(rel_tol,
gap)`. It leaves every default run unchanged but bounds the plan only to 2 x gap, and on the 15 fork
plans measured it changed nothing (every keep was within 1e-5 of HiGHS's plan,
`reltol_probe_2026-10-26.txt`); in the repro below it would not remove a single keep.

---

**Title:** Branch-and-bound loop: a sticky-binaries tie can leave a plan outside the requested `gap`

With `breakpointMethod="branch-and-bound"` and a `gap` tighter than the loop's `relTol` (5e-5 by
default), the accepted plan can be outside the requested gap even though every HiGHS run met it.
On `Case_chris+pat.toml` as shipped, adding only `breakpointMethod="branch-and-bound", gap=1e-5`:

| | largest gap HiGHS reported | accepted `solverGap` | sticky keeps |
|---|---:|---:|---:|
| `dev` `4dcfabb` | 9.706e-06 | **1.833e-05** | 1 |
| with the patch | 9.942e-06 | 9.942e-06 | 0 |

**Why.** `_stickyBinaries` (from `6250a5b0`) keeps the previous iteration's binaries when the LP with
them pinned is within `_sticky_tol` of the new plan, and `_sticky_tol` is the loop's `rel_tol`
(`max(REL_TOL, gap/300)`, so 5e-5 unless `relTol` is given). It then re-expresses the solver's bound
against the kept plan, which is right, so the reported gap is honest: it simply grows past the
requested one. HiGHS itself stops within `mip_rel_gap` (1.15.1: the reported `mip_gap` and the
pruning test both use |primal + offset|), so the extra comes only from the tie. At the default gaps
(1e-4, and 3e-3 with Medicare as MILP) `relTol` is far inside the gap and nothing changes; it is only
when a user asks for a gap below `relTol` that the tie is looser than the request, as the docstring
already says it should not be ("a tie, not anything inside the gap").

In the repro the keeps cost little (the patched plans are \$0-1.23/yr better), but the bound a user
asked for is not the bound they get: at `gap=1e-5` a plan is guaranteed only to 1e-5 + 5e-5. The
patch has a time cost where it refuses a keep: those three solves took 39-98 s longer (presumably one
more loop iteration; iterations were not counted in this repro).

**Proposed fix** (patch attached, `plan.py` only, plus two tests in `test_sticky_binaries.py`): keep
the tie unless it would take a plan the solver proved within the requested gap outside it. When the
solve itself stopped above the requested gap (a node or time limit), the tie is kept as today, so the
loop keeps its convergence aid where it matters most.

```python
kept_gap = gap
if gap is not None and gap >= 0:  # the same bound, against the kept plan
    bound = obj - gap * abs(obj)
    kept_gap = (res[0] - bound) / max(abs(res[0]), 1e-12)
# A tie may not take a plan the solver proved within the requested gap outside it.
requested = u.get_numeric_option(options, "gap", GAP, min_value=0)
if gap is None or gap < 0 or gap > requested or kept_gap <= requested:
    chosen = (res[0], res[1], True, result[3], kept_gap)
```

Repro (stock examples, `breakpointMethod="branch-and-bound", gap=1e-5`; chris+pat as shipped, then
with `setACA(20, start_year=2029)` at three pairs of claiming ages):

| case | stock: HiGHS max gap / `solverGap` / keeps / value | patched: HiGHS max gap / `solverGap` / keeps / value |
|---|---|---|
| chris+pat as shipped | 9.706e-06 / **1.833e-05** / 1 / 114,325.86 (103 s) | 9.942e-06 / 9.942e-06 / 0 / 114,327.09 (142 s) |
| SLCSP 20, ages 67/63 | 9.872e-06 / **1.968e-05** / 1 / 113,450.58 (141 s) | 9.872e-06 / 9.867e-06 / 0 / 113,451.71 (220 s) |
| SLCSP 20, ages 70/63 | 9.976e-06 / **1.935e-05** / 1 / 113,361.62 (215 s) | 9.981e-06 / 9.981e-06 / 0 / 113,362.69 (313 s) |
| SLCSP 20, ages 68.5/63 | 9.834e-06 / 9.720e-06 / 0 / 113,542.48 (132 s) | 9.834e-06 / 9.720e-06 / 0 / 113,542.48 (137 s) |

Values are the `maxSpending` basis in today's \$/yr; every HiGHS run ended "Optimal"; four solves ran
at a time on 4 cores, so the times are relative.

What I could not check: whether refusing a tie in a solve that met its gap can bring back the MOSEK
non-convergence that `6250a5b0` fixed (joe, jack+jill, avery+quinn; `test_pathological_cases_settle`),
since this container has no MOSEK licence. At the default 3e-3 the patch refuses a keep only when
HiGHS stopped within the gap but closer to it than the keep's cost. With HiGHS, the full suite passes, the pinned cases within their test tolerances.

# Draft upstream issue: the sticky-binaries tie can take a plan outside a requested MIP gap

Status: **filed by the user as #233** (2026-10-26), the text below the `---` line as reviewed (patch first,
the `min(rel_tol, gap)` cap as the fallback). Drafted 2026-10-26. Found while deciding claiming ages by branch-and-bound at
`gap=1e-5` in the fork's work sweep (PROGRESS.md "Why the reported gap exceeds `mip_rel_gap`",
"relTol equal to the gap, measured"). Every number below comes from stock upstream `dev` `4dcfabb`,
run 2026-10-26 (plans start today, so a later run can move by dollars):
- `fork-notes/issue-sticky-gap-repro.py`, output `issue-sticky-gap-repro-output.txt`, on stock and
  then with the patch;
- the patch `fork-notes/issue-sticky-gap.patch` (`plan.py` +9/-3; in
  `tests/solver/test_sticky_binaries.py` three tests and one existing test given the gap it is about;
  applies cleanly on `4dcfabb`; the refusal test fails on stock and passes with the patch).

Reviewed 2026-10-26 (PROGRESS.md "Sticky-gap issue reviewed"): repro re-run with loop iterations
counted; `test_a_tie_keeps_the_previous_binaries` now passes `{"gap": 3e-3}` (with `{}` the patch
kept its tie through the stopped-above-the-gap branch, against a requested 1e-4, not the normal one)
and a test covers that branch; the default-gap paragraph corrected (the stated reason was wrong; HiGHS
stops within 0.4% of its gap, so the patch refuses almost every tie that happens, at any gap).

Upstream suite on `4dcfabb` with the patch: 3248 passed, 1 skipped (7:03); `-m deep`: 6 passed,
3 skipped (6:21). The 3 skips are `test_pathological_cases_settle[joe, jack+jill, avery+quinn]`, the
convergence test that motivated the sticky binaries; it runs under MOSEK only and could not be run
here (HiGHS only, no licence).

The simpler alternative, capping the tie at the gap (`_sticky_tol = min(rel_tol, gap)`), was left out
of the first draft; since the review it is named in the issue's last paragraph as the fallback if
the maintainer's MOSEK run of `test_pathological_cases_settle` fails with the patch. It leaves every
default run unchanged but bounds the plan only to 2 x gap; on the 15 fork plans measured it changed
nothing (every keep was within 1e-5 of HiGHS's plan, `reltol_probe_2026-10-26.txt`), and in the repro
it would not remove a single keep (measured on three of the four cases, which are in the reltol
probe; inferred for "as shipped"). Decided 2026-10-26 (user): lead with the patch, which guarantees
the requested gap but may cost MOSEK its convergence aid; keep the cap, which carries no such risk
and guarantees less, as the fallback.

---

**Title:** Branch-and-bound loop: a sticky-binaries tie can leave a plan outside the requested `gap`

With `breakpointMethod="branch-and-bound"` and a `gap` tighter than the loop's `relTol` (5e-5 by
default), the accepted plan can be outside the requested gap even though every HiGHS run met it.
On `Case_chris+pat.toml` as shipped, adding only `breakpointMethod="branch-and-bound", gap=1e-5`:

| | largest gap HiGHS reported | accepted `solverGap` | sticky keeps | loop iterations |
|---|---:|---:|---:|---:|
| `dev` `4dcfabb` | 9.706e-06 | **1.833e-05** | 1 | 2 |
| with the patch | 9.942e-06 | 9.942e-06 | 0 | 3 |

**Why.** `_stickyBinaries` (from `6250a5b0`) keeps the previous iteration's binaries when the LP with
them pinned is within `_sticky_tol` of the new plan, and `_sticky_tol` is the loop's `rel_tol`
(`max(REL_TOL, gap/300)`, so 5e-5 unless `relTol` is given). It then re-expresses the solver's bound
against the kept plan, which is right, so the reported gap is honest: it simply grows past the
requested one. HiGHS itself stops within `mip_rel_gap` (1.15.1: the reported `mip_gap` and the
pruning test both use |primal + offset|), so the extra comes only from the tie. A keep leaves the
gap whenever HiGHS's own gap plus the tie's cost exceeds the request, and HiGHS stops close to its
gap: 0.9706-0.9981 of it in every MIP solve of the repro, 0.9961-0.9999 of it with the same four
cases at `gap=1e-4`. So any keep can do this, at any gap. What makes small gaps different is only
how often a tie happens, and how loose it is next to the request (the docstring: "a tie, not
anything inside the gap"): three keeps in the four cases at 1e-5; none in the same four at 1e-4; at
each shipped example's own options under branch-and-bound (19 cases, mostly 3e-3 with Medicare as
MILP), one tie, in `Case_robin`, kept and still within the gap (2.94e-3).

In the repro the keeps cost little (the patched plans are \$0-1.23/yr better), but the bound a user
asked for is not the bound they get: at `gap=1e-5` a plan is guaranteed only to 1e-5 + 5e-5. The
patch has a time cost where it refuses a keep: each of those three solves took one more loop
iteration (3 instead of 2).

**Proposed fix** (patch attached: `plan.py`, three tests in `test_sticky_binaries.py`, and the gap it is
about passed to `test_a_tie_keeps_the_previous_binaries`): keep the tie unless it would take a plan
the solver proved within the requested gap outside it. When the solve itself stopped above the
requested gap (a node or time limit), the tie is kept as today, so the loop keeps its convergence aid
where it matters most.

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

| case | stock: HiGHS max gap / `solverGap` / keeps / iterations / value | patched: the same |
|---|---|---|
| chris+pat as shipped | 9.706e-06 / **1.833e-05** / 1 / 2 / 114,325.86 (106 s) | 9.942e-06 / 9.942e-06 / 0 / 3 / 114,327.09 (136 s) |
| SLCSP 20, ages 67/63 | 9.872e-06 / **1.968e-05** / 1 / 2 / 113,450.58 (145 s) | 9.872e-06 / 9.867e-06 / 0 / 3 / 113,451.71 (208 s) |
| SLCSP 20, ages 70/63 | 9.976e-06 / **1.935e-05** / 1 / 2 / 113,361.62 (220 s) | 9.981e-06 / 9.981e-06 / 0 / 3 / 113,362.69 (300 s) |
| SLCSP 20, ages 68.5/63 | 9.834e-06 / 9.720e-06 / 0 / 2 / 113,542.48 (137 s) | 9.834e-06 / 9.720e-06 / 0 / 2 / 113,542.48 (130 s) |

Values are the `maxSpending` basis in today's \$/yr; every HiGHS run ended "Optimal"; four solves ran
at a time on 4 cores, so the times are relative.

What I could not check: whether refusing a tie in a solve that met its gap can bring back the MOSEK
non-convergence that `6250a5b0` fixed (joe, jack+jill, avery+quinn; `test_pathological_cases_settle`),
since this container has no MOSEK licence. It turns on how close MOSEK stops to its gap there: the
patch refuses a keep when the solve's gap plus the keep's cost exceeds the request, and HiGHS stops
within 0.4% of its gap in every solve above, so with HiGHS's habits nearly every tie at 3e-3 would be
refused too (`Case_robin`'s was not: its solve stopped at 2.94e-3). If those cases fail with the
patch, a weaker fix that keeps every tie today's runs keep is to cap the tie at the gap,
`self._sticky_tol = min(rel_tol, gap)`: unchanged at default settings, but it bounds the plan only to
twice the requested gap, and in the repro it would not remove a single keep. With HiGHS, the full
suite passes with the patch, the pinned cases within their test tolerances.

"""Review of issue-sticky-gap.md (2026-10-26).
The issue's four cases, with the repair stage and each iteration's own gap recorded:
per iteration, HiGHS's MIP gap, whether the tie was kept, whether the repair improved, and the
returned plan's true gap against that iteration's HiGHS bound (vs the gap it reports)."""
import io
import os
import sys
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import owlplanner as owl
from owlplanner.plan import Plan

EX = os.path.join(os.getcwd(), "examples")
GAP = float(sys.argv[1]) if len(sys.argv) > 1 else 1e-5
CASES = [("as shipped", None, 0), ("SLCSP 20, 67/63", [67.0, 63.0], 20),
         ("SLCSP 20, 70/63", [70.0, 63.0], 20), ("SLCSP 20, 68.5/63", [68.5, 63.0], 20)]


def solve(case):
    label, ages, slcsp = case
    its = []
    o_milp, o_sticky = Plan._milpSolve, Plan._stickyBinaries
    state = {}

    def sticky(self, result, options, use_mosek):
        out = o_sticky(self, result, options, use_mosek)
        state["mip"] = result
        state["kept"] = out is not result
        return out

    def milp(self, objective, options):
        state.clear()
        out = o_milp(self, objective, options)
        mip = state.get("mip")
        if mip is not None and mip[4] is not None and mip[4] >= 0 and out[2]:
            bound = mip[0] - mip[4] * abs(mip[0])
            true = (out[0] - bound) / abs(out[0])
            its.append((mip[4], state["kept"], true, out[4]))
        return out

    Plan._milpSolve, Plan._stickyBinaries = milp, sticky
    buf = io.StringIO()
    try:
        p = owl.readConfig(os.path.join(EX, "Case_chris+pat.toml"), verbose=True, logstreams=[buf])
        if ages is not None:
            p.setSocialSecurity(list(p.ssecAmounts), ages)
        if slcsp:
            p.setACA(slcsp, start_year=2029)
        t0 = time.time()
        p.solve(p.objective, dict(p.solverOptions or {}, breakpointMethod="branch-and-bound", gap=GAP))
        log = buf.getvalue()
        return (label, p.caseStatus, p._objectiveValue(p.objective), float(p.solverGap), its,
                log.count("Iter: "), log.count("improved ("), p.convergenceType, time.time() - t0)
    finally:
        Plan._milpSolve, Plan._stickyBinaries = o_milp, o_sticky


if __name__ == "__main__":
    print("owlplanner", owl.__version__, owl.__file__, f"gap={GAP:.0e}", flush=True)
    with ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context("spawn")) as pool:
        for label, st, val, sg, its, nit, nrep, conv, s in pool.map(solve, CASES):
            print(f"{label:<18} {st} value={val:,.2f} solverGap={sg:.3e} iters={nit} repairs_improved={nrep} "
                  f"conv={conv!r} {s:.0f}s")
            for g, k, t, r in its:
                print(f"    MIP gap {g:.3e}  {'kept' if k else '    '}  "
                      f"returned plan: true gap {t:.3e}, reported {r:.3e}")

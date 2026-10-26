"""Review of issue-sticky-gap.md (2026-10-26).
Every _stickyBinaries tie at each example's own options under branch-and-bound (default gap):
HiGHS's gap, the gap against the kept plan, the requested gap, and whether the tie was kept."""
import glob
import io
import os
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import owlplanner as owl
from owlplanner.plan import Plan
from owlplanner import utils as u

EX = os.path.join(os.getcwd(), "examples")


def solve(path):
    ties = []
    buf = io.StringIO()
    orig, run_mip = Plan._stickyBinaries, Plan._run_mip

    def wrapped(self, result, options, use_mosek):
        seen = []

        def rec_mip(self2, *a, **k):
            r = run_mip(self2, *a, **k)
            if k.get("lp_relax"):
                seen.append(r)
            return r

        Plan._run_mip = rec_mip
        try:
            out = orig(self, result, options, use_mosek)
        finally:
            Plan._run_mip = run_mip
        obj, gap = result[0], result[4]
        for r in seen:
            if r[2] and r[0] is not None and r[0] <= obj + self._sticky_tol * abs(obj):
                kg = (r[0] - (obj - gap * abs(obj))) / max(abs(r[0]), 1e-12) if gap is not None and gap >= 0 else None
                req = u.get_numeric_option(options, "gap", 1e-4, min_value=0)
                ties.append((gap, kg, req, out is not result))
        return out

    Plan._stickyBinaries = wrapped
    t0 = time.time()
    try:
        p = owl.readConfig(path, verbose=True, logstreams=[buf])
        opts = dict(p.solverOptions or {})
        opts["breakpointMethod"] = "branch-and-bound"
        opts.pop("mipStrategy", None)
        p.solve(p.objective, opts)
        st = f"{p.caseStatus} iters={buf.getvalue().count('Iter: ')} conv={p.convergenceType!r}"
        nb, sg = getattr(p, "nbins", 0), getattr(p, "solverGap", None)
        val = p._objectiveValue(p.objective) if p.caseStatus == "solved" else None
    except Exception as e:  # noqa: BLE001
        st, nb, sg, val = f"error {e}", 0, None, None
    finally:
        Plan._stickyBinaries = orig
    return os.path.basename(path), st, nb, sg, val, ties, time.time() - t0


if __name__ == "__main__":
    print("owlplanner", owl.__version__, owl.__file__, flush=True)
    files = sorted(glob.glob(os.path.join(EX, "Case_*.toml")))
    with ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context("spawn")) as pool:
        for name, st, nb, sg, val, ties, s in pool.map(solve, files):
            fmt = [(f"{a:.2e}", None if b is None else f"{b:.2e}", f"{c:.0e}", "kept" if k else "refused")
                   for a, b, c, k in ties]
            leaving = sum(1 for a, b, c, k in ties if b is not None and a <= c < b)
            print(f"{name:<30} {st} bins={nb} solverGap={sg} value={val} ties={len(ties)} "
                  f"tie_leaves_gap={leaving} {fmt} {s:.0f}s", flush=True)

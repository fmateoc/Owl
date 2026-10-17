"""PR #196 check on stock fb8b10e (fmateoc:ss-convex-pr). One example: SS loop / convex / optimize (SS only) / local-search preset; objective, residuals, gap, time.
Date frozen at 2026-10-15. Usage: cmp.py REPO_ROOT CASE"""
import datetime, io, sys, time
from unittest.mock import patch
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import owlplanner as owl
from owlplanner.export import _compute_estate
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
root, case = sys.argv[1], sys.argv[2]
VARIANTS = [("loop", {"withSSTaxability": "loop"}),
            ("convex", {"withSSTaxability": "convex"}),
            ("SS optimize", {"withSSTaxability": "optimize"}),
            ("LS preset", {"breakpointMethod": "local-search"}),
            ("LS preset+convex", {"breakpointMethod": "local-search", "withSSTaxability": "convex"})]
for name, extra in VARIANTS:
    log = io.StringIO()
    p = owl.readConfig(f"{root}/examples/{case}.toml", verbose=True, logstreams=[log])
    opts = dict(p.solverOptions); opts.update(extra)
    t = time.time(); p.solve(p.objective, opts); dt = time.time() - t
    if p.caseStatus != "solved":
        print(f"{case:22s} {name:17s} {p.caseStatus}", flush=True); continue
    obj = float(p.basis) if p.objective == "maxSpending" else _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
    res = p.fixedPointResidual or {}
    tot = sum(v.get("abs_sum", 0.0) for v in res.values() if isinstance(v, dict))
    parts = " ".join(f"{k}={v.get('abs_sum',0):,.0f}" for k, v in res.items() if isinstance(v, dict) and v.get("abs_sum", 0) >= 1)
    gap = getattr(p, "solverGap", None)
    print(f"{case:22s} {name:17s} {obj:>13,.0f} {dt:7.1f}s {p.breakpointMethodUsed[:34]:34s} res {tot:>8,.0f} [{parts}] gap {gap}", flush=True)

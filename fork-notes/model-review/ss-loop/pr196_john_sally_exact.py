"""PR #196 check on stock fb8b10e (fmateoc:ss-convex-pr). john+sally: exact presets. Date frozen 2026-10-15."""
import datetime, sys, time
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
root, which = sys.argv[1], sys.argv[2]
V = {"conv+medopt": {"withSSTaxability": "convex", "withMedicare": "optimize"},
     "ssopt+medopt": {"withSSTaxability": "optimize", "withMedicare": "optimize"},
     "BB preset": {"breakpointMethod": "branch-and-bound", "maxTime": 900}}[which]
p = owl.readConfig(f"{root}/examples/Case_john+sally.toml", verbose=False)
opts = dict(p.solverOptions); opts.update(V)
t = time.time(); p.solve(p.objective, opts); dt = time.time() - t
res = p.fixedPointResidual or {}
tot = sum(v.get("abs_sum", 0.0) for v in res.values() if isinstance(v, dict))
print(which, p.caseStatus, f"{_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]:,.0f}", f"{dt:.1f}s", p.breakpointMethodUsed, f"res {tot:,.0f}", "gap", p.solverGap, flush=True)

"""PR #196 check on stock fb8b10e (fmateoc:ss-convex-pr). Every family exact (branch-and-bound) except SS: SS "convex" vs SS "optimize". Date frozen 2026-10-15.
Usage: pair.py REPO_ROOT CASE convex|optimize"""
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
root, case, ss = sys.argv[1:4]
p = owl.readConfig(f"{root}/examples/{case}.toml", verbose=False)
opts = dict(p.solverOptions)
opts.update(withSSTaxability=ss, withLTCG="optimize", withNIIT="optimize", withSeniorBonus="optimize",
            mipStrategy="branch-and-bound", maxTime=900)
if opts.get("withMedicare", "loop") not in ("none", "None", False):
    opts["withMedicare"] = "optimize"
if p.slcsp_annual > 0:
    opts["withACA"] = "optimize"
t = time.time(); p.solve(p.objective, opts); dt = time.time() - t
obj = float(p.basis) if p.objective == "maxSpending" else _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
res = p.fixedPointResidual or {}
tot = sum(v.get("abs_sum", 0.0) for v in res.values() if isinstance(v, dict))
print(f"{case:22s} SS {ss:8s} {p.caseStatus} {obj:>13,.0f} {dt:6.1f}s {p.breakpointMethodUsed} res {tot:,.0f} gap {p.solverGap:.2e}", flush=True)

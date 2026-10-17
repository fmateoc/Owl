"""One example, local-search preset: objective, time, label, node tally, residual. Date frozen 2026-10-15.
Usage: ex_ls.py ROOT CASE TAG"""
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
root, case, tag = sys.argv[1:4]
p = owl.readConfig(f"{root}/examples/{case}.toml", verbose=False)
o = dict(p.solverOptions); o["breakpointMethod"] = "local-search"
t = time.time(); p.solve(p.objective, o); dt = time.time() - t
obj = float(p.basis) if p.objective == "maxSpending" else _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
res = p.fixedPointResidual or {}
tot = sum(v.get("abs_sum", 0.0) for v in res.values() if isinstance(v, dict))
print(f"{case:24s} {tag:6s} {p.objective:11s} {obj:>14,.0f} {dt:7.1f}s res {tot:>7,.0f} {p.breakpointMethodUsed}", flush=True)

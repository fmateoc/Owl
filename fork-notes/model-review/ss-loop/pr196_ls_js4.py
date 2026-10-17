"""john+sally: local search with one family on optimize at a time (others loop). Date frozen 2026-10-15."""
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
root = sys.argv[1]
for name, extra in (("LS SS only", {"withSSTaxability": "optimize", "mipStrategy": "local-search"}),
                    ("BB SS only", {"withSSTaxability": "optimize"}),
                    ("LS Medicare only", {"withMedicare": "optimize", "mipStrategy": "local-search"}),
                    ("BB Medicare only", {"withMedicare": "optimize"}),
                    ("LS SS+Medicare", {"withSSTaxability": "optimize", "withMedicare": "optimize", "mipStrategy": "local-search"}),
                    ("convex+LS Medicare", {"withSSTaxability": "convex", "withMedicare": "optimize", "mipStrategy": "local-search"})):
    p = owl.readConfig(f"{root}/examples/Case_john+sally.toml", verbose=False)
    o = dict(p.solverOptions); o.update(extra)
    t = time.time(); p.solve(p.objective, o); dt = time.time() - t
    res = p.fixedPointResidual or {}
    tot = sum(v.get("abs_sum", 0.0) for v in res.values() if isinstance(v, dict))
    print(f"{name:20s} {_compute_estate(p, p.N_n)[3]/p.gamma_n[p.N_n]:>9,.0f} {dt:5.1f}s {p.breakpointMethodUsed:40s} res {tot:,.0f}", flush=True)

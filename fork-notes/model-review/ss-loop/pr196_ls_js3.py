"""john+sally: local-search preset vs branch-and-bound preset vs convex, per year. Date frozen 2026-10-15."""
import datetime, sys
from unittest.mock import patch
import numpy as np
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
R = {}
for name, extra in (("LS", {"breakpointMethod": "local-search"}), ("BB", {"breakpointMethod": "branch-and-bound"}),
                    ("convex", {"withSSTaxability": "convex"})):
    p = owl.readConfig(f"{root}/examples/Case_john+sally.toml", verbose=False)
    o = dict(p.solverOptions); o.update(extra); p.solve(p.objective, o)
    g = p.gamma_n[:-1]
    R[name] = dict(M=p.M_n/g, x=p.x_in.sum(0)/g, T=p.T_n/g, st=p.st_T_n/g, ss=p.Psi_n*np.sum(p.zetaBar_in,0)/g,
                   magi=p.MAGI_n/g, beq=_compute_estate(p, p.N_n)[3]/p.gamma_n[p.N_n], y=p.year_n)
    r = R[name]
    print(f"{name:7s} bequest {r['beq']:,.0f}  M {r['M'].sum():,.0f}  x {r['x'].sum():,.0f}  fedT {r['T'].sum():,.0f}  stT {r['st'].sum():,.0f}  taxSS {r['ss'].sum():,.0f}")
print("year | " + " | ".join(f"{k}: x M T" for k in R))
for n, y in enumerate(R["LS"]["y"][:14]):
    print(y, " | ".join(f"{R[k]['x'][n]:8,.0f} {R[k]['M'][n]:6,.0f} {R[k]['T'][n]:7,.0f}" for k in R))

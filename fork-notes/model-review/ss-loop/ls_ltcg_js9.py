"""john+sally, local-search preset vs branch-and-bound preset: ordinary taxable income G_n against the
LTCG thresholds T15/T20, and the zl / SS regime binaries, per year (today's $). Date frozen 2026-10-15."""
import datetime, sys
from unittest.mock import patch
import numpy as np
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import owlplanner as owl
from owlplanner import tax_federal as tx
from owlplanner.export import _compute_estate
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
root = sys.argv[1]
R = {}
for name in ("local-search", "branch-and-bound"):
    p = owl.readConfig(f"{root}/examples/Case_john+sally.toml", verbose=False)
    o = dict(p.solverOptions); o["breakpointMethod"] = name; p.solve(p.objective, o)
    g = p.gamma_n[:-1]
    st = np.array([0 if (p.N_i == 2 and n >= p.n_d) else p.N_i - 1 for n in range(p.N_n)])
    T15 = np.array([tx.capGainRates[s][0] for s in st]); T20 = np.array([tx.capGainRates[s][1] for s in st])
    ss = np.sum(p.zetaBar_in, 0)
    R[name] = dict(G=p.G_n / g, T15=T15, T20=T20, x=p.x_in.sum(0) / g, Q=p.Q_n / g, tss=p.Psi_n * ss / g,
                   beq=_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n], y=p.year_n)
    print(name, f"bequest {R[name]['beq']:,.0f}")
a, b = R["local-search"], R["branch-and-bound"]
print("T15/T20 (today's $, MFJ):", f"{a['T15'][0]:,.0f} / {a['T20'][0]:,.0f}")
print("year |  LS: G    x     Q  taxSS side15 | BB: G    x     Q  taxSS side15")
for n, y in enumerate(a["y"][:16]):
    s = lambda r: f"{r['G'][n]:8,.0f} {r['x'][n]:8,.0f} {r['Q'][n]:6,.0f} {r['tss'][n]:7,.0f} {'above' if r['G'][n] > r['T15'][n] + 1 else 'below'}"
    print(y, "|", s(a), "|", s(b))

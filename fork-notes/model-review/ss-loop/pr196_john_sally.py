"""PR #196 check on stock fb8b10e (fmateoc:ss-convex-pr). john+sally: convex vs SS optimize, per-year audit of taxable SS and taxes. Date frozen 2026-10-15."""
import datetime, sys
from unittest.mock import patch
import numpy as np
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import owlplanner as owl
from owlplanner import tax_federal as tf
from owlplanner.export import _compute_estate
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
root = sys.argv[1]
out = {}
for mode in ("convex", "optimize"):
    p = owl.readConfig(f"{root}/examples/Case_john+sally.toml", verbose=False)
    opts = dict(p.solverOptions); opts["withSSTaxability"] = mode
    p.solve(p.objective, opts)
    ss = np.sum(p.zetaBar_in, axis=0)
    tss = getattr(p, "tss_n", p.Psi_n * ss)
    pi = p.MAGI_aca_n - 0.5 * ss
    status = np.full(p.N_n, p.N_i - 1)
    if p.N_i == 2 and p.n_d < p.N_n: status[p.n_d:] = 0
    lo, hi = tf.ssTaxabilityLo[status], tf.ssTaxabilityHi[status]
    a50 = 0.5 * np.minimum(ss, np.minimum(hi - lo, np.maximum(0, pi - lo)))
    form = np.where(pi < lo, 0, np.where(pi < hi, a50, np.minimum(a50 + 0.85 * np.maximum(0, pi - hi), 0.85 * ss)))
    beq = _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
    g = p.gamma_n[:-1]
    out[mode] = dict(beq=beq, ss=ss/g, tss=tss/g, form=form/g, T=p.T_n/g, st=p.st_T_n/g, U=p.U_n/g, J=p.J_n/g,
                     M=p.M_n/g, x=p.x_in.sum(0)/g, G=p.G_n/g, MAGI=p.MAGI_aca_n/g, year=p.year_n, n_d=p.n_d)
    print(mode, f"bequest {beq:,.0f}", "status", p.caseStatus, "n_d", p.n_d, "method", p.breakpointMethodUsed)
    for k in ("T", "st", "U", "J", "M", "x", "tss", "form"):
        print(f"   total {k:5s} {out[mode][k].sum():>12,.0f}")
c, o = out["convex"], out["optimize"]
print("year  ss | conv: tss formula x  T  M | opt: tss formula x T M")
for n, y in enumerate(c["year"]):
    print(f"{y} {c['ss'][n]:7,.0f} | {c['tss'][n]:7,.0f} {c['form'][n]:7,.0f} {c['x'][n]:8,.0f} {c['T'][n]:7,.0f} {c['M'][n]:6,.0f} | "
          f"{o['tss'][n]:7,.0f} {o['form'][n]:7,.0f} {o['x'][n]:8,.0f} {o['T'][n]:7,.0f} {o['M'][n]:6,.0f}")

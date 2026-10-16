"""NY couple with a $600k mortgage, flat $105k net spending, maxBequest, 2032 reversion: runs on stock
upstream dev and on the fork (no fork-only API). Date frozen at 2026-10-15.
Usage: stock_repro.py [roth_stock_pct] [netSpending_k] [state]"""
import datetime, io, re, sys
from unittest.mock import patch
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import numpy as np, pandas as pd
import owlplanner as owl
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
roth = int(sys.argv[1]) if len(sys.argv) > 1 else 60
spend = float(sys.argv[2]) if len(sys.argv) > 2 else 105.0
state = sys.argv[3] if len(sys.argv) > 3 else "NY"
for ss in ("loop", "optimize"):
    log = io.StringIO()
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "repro", verbose=True, logstreams=[log])
    p.setSpendingProfile("flat")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
    a = [[60, 40, 0, 0], [60, 40, 0, 0]]
    r_ = [[roth, 100 - roth, 0, 0], [roth, 100 - roth, 0, 0]]
    p.setAllocationRatios("account", taxable=[a] * 2, taxDeferred=[a] * 2, taxFree=[r_] * 2)
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.houseLists["Debts"] = cond(pd.DataFrame([{"active": True, "name": "m", "type": "mortgage", "year": 2026,
                                               "term": 30, "amount": 600000.0, "rate": 6.5}]), "Debts")
    p.Lambda_in[0, 0] = 600000.0  # loan proceeds as cash in 2026, as in the fork probe (r123_cases.couple)
    p.setStateTax(state)
    p.setExpirationYearOBBBA(2032)
    p.solve("maxBequest", options={"noRothConversions": "None", "netSpending": spend, "withSSTaxability": ss})
    iters = len(re.findall(r"Iter: \d+", log.getvalue()))
    res = p.fixedPointResidual or {}
    worst = max(res.items(), key=lambda kv: kv[1]["abs_sum"]) if res else ("-", {"abs_sum": 0})
    if p.caseStatus != "solved":
        print(state, ss, p.caseStatus, log.getvalue()[-600:]); continue
    from owlplanner.export import _compute_estate
    beq = _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
    print(f"{owl.__file__.split('/src/')[0]} {state} roth{roth} spend{spend:.0f}k SS={ss:8s} {p.caseStatus} it={iters} "
          f"{p.convergenceType} bequest={beq:,.0f} worst={worst[0]} {worst[1]['abs_sum']:,.0f}", flush=True)
    g = p.gamma_n[:p.N_n]
    ss_n = np.sum(p.zetaBar_in, axis=0)
    psi = p.Psi_n
    ph = (ss_n > 0) & (psi < 0.849)
    print(f"   conversions (today $): total {np.sum(p.x_in / g):,.0f}; by year "
          f"{ {int(y): round(v) for y, v in zip(p.year_n, np.sum(p.x_in, axis=0) / g) if v > 1} }")
    print(f"   SS years in the phase-in (Psi < 0.85): {int(np.sum(ph))} of {int(np.sum(ss_n > 0))}; "
          f"taxable SS lifetime (today $) {np.sum(psi * ss_n / g):,.0f}; federal tax lifetime {np.sum(p.T_n / g):,.0f}")

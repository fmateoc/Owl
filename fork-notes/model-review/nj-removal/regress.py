"""Regression for the NJ code removal: one case per call, a JSON line out. Date frozen at 2026-10-15.

Usage: regress.py ROOT CASE    CASE = ex:<example>[:ls] | ny:<loc>:<mortgage>:<yob>:<loop|ls> | star:<loop|optimize>
       | nj:<mortgage>:<yob>:<loop|ls> (informational: NJ is expected to change)
"""
import datetime, io, json, sys, time
from unittest.mock import patch
import numpy as np
import pandas as pd
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import owlplanner as owl
from owlplanner.export import _compute_estate
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
root, case = sys.argv[1], sys.argv[2]
THISYEAR = 2026
line = lambda name, htype, amount: {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0,
                                    "amount": amount, "rate": 0.0, "survivor": np.nan}

def couple(state, loc, mortgage, yob, district=""):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "rg", verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.houseLists["Budget"] = cond(pd.DataFrame([line("core", "core", 80000.0), line("pt", "property tax", 25000.0)]), "Budget")
    if mortgage:
        p.houseLists["Debts"] = cond(pd.DataFrame([{"active": True, "name": "m", "type": "mortgage", "year": THISYEAR,
                                                    "term": 30, "amount": mortgage, "rate": 6.5}]), "Debts")
        p.Lambda_in[0, 0] = mortgage
    if district:
        p.setStateTax(state, locality=loc, school_district=district)
    else:
        p.setStateTax(state, locality=loc)
    p.setExpirationYearOBBBA(yob)
    return p

parts = case.split(":")
t = time.time()
if parts[0] == "ex":
    p = owl.readConfig(f"{root}/examples/{parts[1]}.toml", verbose=False, logstreams=[io.StringIO()])
    opts = dict(p.solverOptions)
    if len(parts) > 2 and parts[2] == "ls":
        opts["breakpointMethod"] = "local-search"
    p.solve(p.objective, opts)
elif parts[0] in ("ny", "nj"):
    if parts[0] == "ny":
        _, loc, mort, yob, meth = parts
        p = couple("NY", loc, float(mort), int(yob), district="Yonkers" if loc == "Yonkers" else "")
    else:
        _, mort, yob, meth = parts
        p = couple("NJ", "", float(mort), int(yob))
    p.solve("maxBequest", {"breakpointMethod": "local-search"} if meth == "ls" else {})
elif parts[0] == "star":
    p = owl.Plan(["Joe", "Jane"], ["1960-03-15", "1961-09-15"], [89, 92], "star", verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[850, 850], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([4200, 3600], [67, 67])
    p.houseLists["Budget"] = cond(pd.DataFrame([line("core", "core", 80000.0), line("pt", "property tax", 25000.0)]), "Budget")
    p.setStateTax("NY", locality="Yonkers", school_district="Yonkers")
    p.setExpirationYearOBBBA(2099)
    p.solve("maxBequest", {"withMedicare": "none", "withSSTaxability": 0.85, "withSTAR": parts[1]})
dt = time.time() - t
out = {"case": case, "status": p.caseStatus, "time": round(dt, 1)}
if p.caseStatus == "solved":
    g = p.gamma_n[: p.N_n]
    res = p.fixedPointResidual or {}
    out.update(obj=round(float(p.basis) if p.objective == "maxSpending" else float(_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]), 2),
               fed=round(float(np.sum(p.T_n / g)), 2), state=round(float(np.sum(p.st_T_n / g)), 2),
               resid=round(float(sum(v.get("abs_sum", 0.0) for v in res.values() if isinstance(v, dict))), 2),
               method=p.breakpointMethodUsed)
print(json.dumps(out), flush=True)

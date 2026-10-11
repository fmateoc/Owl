"""In-model gain as bequest vs as lifetime tax saved (today's $), probe nymort/ny, exact."""
import io, sys
import numpy as np, pandas as pd
import owlplanner as owl
from owlplanner.export import _compute_estate
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond
THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]
EXACT = {"noRothConversions": "None", "withMedicare": "None", "withSSTaxability": 0.85}
yob = int(sys.argv[1]) if len(sys.argv) > 1 else 2099
def line(n, t, a): return {"active": True, "name": n, "type": t, "year": THISYEAR, "end": 0, "amount": a, "rate": 0.0, "survivor": np.nan}
for state, loc in (("NY", "Yonkers"), ("NJ", "")):
  for mort in (False, True):
    res = {}
    for mode in ("none", "optimize"):
        p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "x", verbose=False, logstreams=[io.StringIO()])
        p.setSpendingProfile("budget")
        p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
        p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
        p.setRates("conservative"); p.setSocialSecurity([3000, 2400], [70, 70])
        p.houseLists["Budget"] = cond(pd.DataFrame([line("core", "core", 80000.0), line("pt", "property tax", 25000.0)]), "Budget")
        if mort:
            p.houseLists["Debts"] = cond(pd.DataFrame([{"active": True, "name": "m", "type": "mortgage", "year": THISYEAR, "term": 30, "amount": 600000.0, "rate": 6.5}]), "Debts")
            p.Lambda_in[0, 0] = 600000.0
        p.setStateTax(state, locality=loc); p.setExpirationYearOBBBA(yob)
        p.solve("maxBequest", options=dict(EXACT, withItemized=mode))
        g = p.gamma_n[:-1]
        res[mode] = (_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n], float(np.sum(p.T_n / g)), float(np.sum(p.st_T_n / g)), float(np.sum((p.T_n + p.st_T_n)/g)))
    d = [res["optimize"][k] - res["none"][k] for k in range(4)]
    print(f"{state} mort={mort} yOBBBA={yob}: bequest gain {d[0]:,.0f}; fed tax {d[1]:,.0f}; state tax {d[2]:,.0f}; total tax {d[3]:,.0f}")

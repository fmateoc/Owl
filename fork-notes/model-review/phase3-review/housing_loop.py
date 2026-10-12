"""Scenario 5 (rent / buy cash / buy mortgage) with withItemized none vs loop, exact LP, date frozen
at 2026-10-11 (as r123_cases.py). Same recipe as phase3_step6_measure.py's housing group."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import r123_cases as rc  # noqa: E402  (freezes the date on import)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import owlplanner as owl  # noqa: E402
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond  # noqa: E402

HOME, RENT, PT, INS, MAINT, CLOSING, DOWN = 600000.0, 36000.0, 15000.0, 2500.0, 6000.0, 0.02, 0.20
for yob in (2099, 2032):
    for kind in ("rent", "cash", "mortgage"):
        row = []
        for mode in ("none", "loop"):
            p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "h", verbose=False,
                         logstreams=[io.StringIO()])
            p.setSpendingProfile("budget")
            p.setAccountBalances(taxable=[500, 300], taxDeferred=[900, 600], taxFree=[75, 75])
            p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
            p.setRates("conservative")
            p.setSocialSecurity([3000, 2400], [70, 70])
            lines = [rc.line("core", "core", 80000.0)]
            lines += [rc.line("rent", "rent", RENT)] if kind == "rent" else [
                rc.line("pt", "property tax", PT), rc.line("ins", "insurance", INS), rc.line("maint", "maintenance", MAINT)]
            p.houseLists["Budget"] = cond(pd.DataFrame(lines), "Budget")
            if kind != "rent":
                p.houseLists["Fixed Assets"] = cond(pd.DataFrame([{
                    "active": True, "name": "home", "type": "residence", "year": 2026, "basis": HOME,
                    "value": HOME, "rate": 0.5, "yod": 0, "commission": 6.0}]), "Fixed Assets")
            if kind == "cash":
                p.Lambda_in[0, 0] = -(HOME * (1 + CLOSING))
            elif kind == "mortgage":
                p.houseLists["Debts"] = cond(pd.DataFrame([{
                    "active": True, "name": "m", "type": "mortgage", "year": 2026, "term": 30,
                    "amount": HOME * (1 - DOWN), "rate": 6.5, "property": "home"}]), "Debts")
                p.Lambda_in[0, 0] = -(HOME * DOWN + HOME * CLOSING)
            p.setStateTax("NY", locality="Yonkers")
            p.setExpirationYearOBBBA(yob)
            r = rc.solve(p, "maxBequest", dict(rc.EXACT, withItemized=mode))
            row.append(r)
        a, b = row
        print(f"yOBBBA {yob} {kind:9s} none {a['obj']:>13,.0f}  loop {b['obj']:>13,.0f}  diff {b['obj'] - a['obj']:+,.0f}"
              f"  fed item yrs {b['fed_item_yrs']}  st item yrs {b['st_item_yrs']} (none: {a['st_item_yrs']})", flush=True)

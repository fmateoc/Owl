"""Step-6 check: NY itemizing on vs off, same day, same recipe as phase3_step6_measure 'nynj'."""
import io
import sys
import time

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner.plan import Plan
from owlplanner.export import _compute_estate
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]
EXACT = {"noRothConversions": "None", "withMedicare": "None", "withSSTaxability": 0.85}
LS = {"noRothConversions": "None", "breakpointMethod": "local-search"}
ORIG = Plan._st_item_candidate_years


def line(name, htype, amount):
    return {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0,
            "amount": amount, "rate": 0.0, "survivor": np.nan}


def build(state, loc, pt):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "x",
                 verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.houseLists["Budget"] = cond(pd.DataFrame([line("core", "core", 80000.0),
                                                line("pt", "property tax", pt)]), "Budget")
    p.setStateTax(state, locality=loc)
    p.setExpirationYearOBBBA(2099)
    return p


methods = sys.argv[1].split(",") if len(sys.argv) > 1 else ["exact"]
for method in methods:
    base = EXACT if method == "exact" else LS
    for pt in (20000.0, 25000.0):
        for state, loc, item in (("NY", "Yonkers", True), ("NY", "Yonkers", False), ("NJ", "", True)):
            if method != "exact" and state == "NJ":
                continue  # NJ LS from the step-6 log (deterministic node caps)
            Plan._st_item_candidate_years = ORIG if item else (lambda self: [])
            p = build(state, loc, pt)
            t = time.time()
            p.solve("maxBequest", options=dict(base, withItemized="none"))
            dt = time.time() - t
            beq = _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
            st = float(np.sum(p.st_T_n / p.gamma_n[:-1]))
            print(f"{method} pt {pt:,.0f} {state} NYitem={item}: {p.caseStatus} bequest {beq:,.0f}"
                  f" state tax {st:,.0f} st_item yrs {int(np.count_nonzero(p.st_itemizing_n))} {dt:.1f}s",
                  flush=True)
Plan._st_item_candidate_years = ORIG

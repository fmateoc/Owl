"""Housing as a fixed ledger vs housing folded into a custom spending profile (xi_n).

Run from the repository root on claude/phase2-housing (needs the Phase 2 Housing ledger).
Output recorded in fork-notes/phase2b-budget-plan.md (2026-10-08).
"""
import io

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner import spending
from owlplanner.export import _compute_estate
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond

RENT = 30.0   # $k/yr, today's $
CORE = 80.0   # $k/yr non-housing, today's $
OPTS = {"withMedicare": "None", "withSSTaxability": 0.85, "maxRothConversion": 100}


def base():
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "env", verbose=False,
                 logstreams=[io.StringIO()])
    p.setSpendingProfile("flat", 60)
    p.setAccountBalances(taxable=[300, 300], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.setStateTax("NY")
    return p


def bequest(p):
    return _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]


def ledger():
    p = base()
    Y = int(p.year_n[0])
    p.houseLists["Housing"] = cond(pd.DataFrame([dict(active=True, name="rent", type="rent", year=Y, end=0,
                                                      amount=RENT * 1000, rate=0.0)]), "Housing")
    return p


def envelope():
    p = base()
    core = spending.gen_spending_profile("flat", 0.6, p.n_d, p.N_n)   # survivor 60% on core only
    total = CORE * core + RENT                                         # rent is household-level
    p.xi_n = total / total[0]
    return p, total[0]


for obj in ("maxBequest", "maxSpending"):
    a = ledger()
    b, tot0 = envelope()
    if obj == "maxBequest":
        a.solve(obj, options={**OPTS, "netSpending": CORE})
        b.solve(obj, options={**OPTS, "netSpending": tot0})
    else:
        a.solve(obj, options={**OPTS, "bequest": 0})
        b.solve(obj, options={**OPTS, "bequest": 0})
    ga = (a.g_n + a.housing_costs_n) / a.gamma_n[:-1]     # total outlay incl. housing, today's $
    gb = b.g_n / b.gamma_n[:-1]
    print(f"{obj}: ledger bequest {bequest(a):12,.0f}  envelope bequest {bequest(b):12,.0f}")
    print(f"   year-0 total outlay ledger {ga[0]:9,.0f} envelope {gb[0]:9,.0f};"
          f" last year ledger {ga[-1]:9,.0f} envelope {gb[-1]:9,.0f}; max |diff| {np.max(np.abs(ga - gb)):9,.0f}")
    if obj == "maxSpending":
        print(f"   ledger: core basis {a.basis:,.0f} + rent {RENT*1000:,.0f};"
              f" envelope: basis {b.basis:,.0f} = {b.basis / (tot0*1000):.4f} x the budget")

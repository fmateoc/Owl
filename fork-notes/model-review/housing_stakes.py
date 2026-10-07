"""Housing / NJ property tax deduction stakes, on the Phase 1 synthetic couple.

Couple born 1964-03-15 and 1964-09-15, life expectancies 89 and 92, SS $3,000 and $2,400/month
at 70, $150k taxable each, $75k Roth each, conservative rates, 60/40, maxBequest at a fixed
net spending (so the house/rent is comparable: final bequest counts the residence).

Usage: housing_stakes.py exact|default|ls [tax-deferred in $k for each spouse, e.g. 900,600]
Lifetime state tax in today's dollars. Housing costs in nominal first-year dollars.
"""
import io
import sys
import time

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

mode = sys.argv[1]
td = [float(v) for v in sys.argv[2].split(",")] if len(sys.argv) > 2 else [900.0, 600.0]
opts = {
    "noRothConversions": "None",
    "maxRothConversion": 0,
    "withMedicare": "None",
    "netSpending": 80.0,
}
if mode == "exact":
    opts.update({"withSSTaxability": 0.85})
elif mode == "ls":
    opts.update({"breakpointMethod": "local-search"})

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]


def housing_df(rows):
    return conditionDebtsAndFixedAssetsDF(pd.DataFrame(rows), "Housing")


def run(state, kind, amount=0.0):
    """kind: 'owner' (property tax), 'tenant' (rent), 'bigticket' (same cost, no deduction), or 'none'."""
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "housing stakes",
                 verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("flat")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=td, taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    if kind in ("owner", "tenant"):
        htype = "property tax" if kind == "owner" else "rent"
        p.houseLists["Housing"] = housing_df(
            [{"active": True, "name": "h", "type": htype, "year": THISYEAR, "end": 0,
              "amount": amount, "rate": 0.0}]
        )
    elif kind == "bigticket":
        # Same cash cost as a negative big-ticket item: no NJ deduction.
        g = p.gamma_n
        p.Lambda_in[0, :] = -amount * g[: p.N_n] / g[0]
    p.setStateTax(state)
    t = time.time()
    p.solve("maxBequest", options=dict(opts))
    dt = time.time() - t
    st = float(np.sum(p.st_T_n / p.gamma_n[:-1]))
    ptd = float(np.sum(p.st_pt_n / p.gamma_n[:-1]))
    return p.basis, st, ptd, dt, p.caseStatus


label = f"${sum(td) / 1000:.1f}M"
cases = [
    ("NJ pt $20k bigticket", "NJ", "bigticket", 20000.0),
    ("NJ pt $20k Housing", "NJ", "owner", 20000.0),
    ("NJ rent $30k Housing", "NJ", "tenant", 30000.0),
    ("NY pt $20k Housing", "NY", "owner", 20000.0),
]
for name, state, kind, amount in cases:
    basis, st, ptd, dt, status = run(state, kind, amount)
    print(f"| {label} | {name} | bequest {basis:,.0f} | state tax {st:,.0f} | ptd {ptd:,.0f} |"
          f" {dt:.1f} s |" + ("" if status == "solved" else f" {status}"))
    sys.stdout.flush()

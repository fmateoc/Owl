"""Housing / NJ property tax deduction stakes, on the Phase 1 synthetic couple.

Couple born 1964-03-15 and 1964-09-15, life expectancies 89 and 92, SS $3,000 and $2,400/month
at 70, $150k taxable each, $75k Roth each, conservative rates, 60/40, maxBequest at a fixed
net spending (so the house/rent is comparable: final bequest counts the residence).

Usage: housing_stakes.py exact|default|ls [tax-deferred in $k, e.g. 900,600] [case;case...]
Case keys: bt, own, rent, ny.
Prints the objective (final bequest after heirs' tax, today's $), lifetime state tax and lifetime
property tax deduction claimed (today's $). Housing costs in nominal first-year dollars.

The deduction claimed is only meaningful in years where it lowers the tax: in a year where NJ
taxable income is zero without it, any amount up to the allowed one gives the same plan, and the
solver's pick there is arbitrary. Compare the bequest, not the lifetime deduction.
(Until 2026-10-07 this script printed p.basis, which under maxBequest is the fixed net spending.)
Since 2026-10-08 (Phase 2b) the housing cost is a line of a "budget" spending profile, with core
spending as the other line, instead of Phase 2's Housing ledger outside net spending; at a fixed
spending level the two are the same plan.
"""
import io
import sys
import time

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner.export import _compute_estate
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
only = sys.argv[3].split(";") if len(sys.argv) > 3 else None

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]


def budget_df(rows):
    return conditionDebtsAndFixedAssetsDF(pd.DataFrame(rows), "Budget")


def line(name, htype, amount):
    return {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0, "amount": amount,
            "rate": 0.0, "survivor": np.nan}


def run(state, kind, amount=0.0):
    """kind: 'owner' (property tax), 'tenant' (rent), 'bigticket' (same cost, no deduction), or 'none'."""
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "housing stakes",
                 verbose=False, logstreams=[io.StringIO()])
    budget = kind in ("owner", "tenant")
    p.setSpendingProfile("budget" if budget else "flat")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=td, taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    myopts = dict(opts)
    if budget:
        # Core spending (flat, 60% survivor) plus the housing line, which a survivor keeps paying.
        # netSpending is left to the budget: its first-year total, core + housing.
        htype = "property tax" if kind == "owner" else "rent"
        p.houseLists["Budget"] = budget_df([line("core", "core", 1000.0 * opts["netSpending"]),
                                            line("h", htype, amount)])
        myopts.pop("netSpending")
    elif kind == "bigticket":
        # Same cash cost as a negative big-ticket item: no NJ deduction.
        g = p.gamma_n
        p.Lambda_in[0, :] = -amount * g[: p.N_n] / g[0]
    p.setStateTax(state)
    t = time.time()
    p.solve("maxBequest", options=myopts)
    dt = time.time() - t
    st = float(np.sum(p.st_T_n / p.gamma_n[:-1]))
    ptd = float(np.sum(p.st_pt_n / p.gamma_n[:-1]))
    bequest = _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n] if p.caseStatus == "solved" else float("nan")
    return bequest, st, ptd, dt, p.caseStatus


label = f"${sum(td) / 1000:.1f}M"
cases = [
    ("bt", "NJ pt $20k bigticket", "NJ", "bigticket", 20000.0),
    ("own", "NJ pt $20k budget", "NJ", "owner", 20000.0),
    ("rent", "NJ rent $30k budget", "NJ", "tenant", 30000.0),
    ("ny", "NY pt $20k budget", "NY", "owner", 20000.0),
]
for key, name, state, kind, amount in cases:
    if only and key not in only:
        continue
    bequest, st, ptd, dt, status = run(state, kind, amount)
    print(f"| {label} | {name} | bequest {bequest:,.0f} | state tax {st:,.0f} | ptd {ptd:,.0f} |"
          f" {dt:.1f} s |" + ("" if status == "solved" else f" {status}"))
    sys.stdout.flush()

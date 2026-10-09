"""Essential vs discretionary budget lines (#175, the maintainer's cost-function point), on the Phase 1
synthetic couple.

Couple born 1964-03-15 and 1964-09-15, life expectancies 89 and 92 (or as given), SS $3,000 and
$2,400/month at 70, $150k taxable each, $75k Roth each, tax-deferred as given ($k), conservative
rates, 60/40, NY, exact LP (Medicare off, SS taxability 0.85), no Roth conversions, bequest 0.

Budget (today's $): living $50k and rent $36k (the essentials when flagged; a survivor keeps rent
in full and 60% of living), travel $20k through 2044 and other $10k (discretionary, 60% kept).

Usage: essential_stakes.py fixed|longevity [tax-deferred, e.g. 900,600]
  fixed      maxSpending with the whole budget scaled vs essentials fixed, at life expectancies
             89/92 and 95/98; then maxBequest at the essentials only and at the budget.
  longevity  runStochasticSpending, 200 Monte Carlo scenarios ("histochastic" rates drawn from
             1928-2024, seed 42) with sampled lifespans (SSA tables; historical sequences
             refuse lifespan sampling): the share of scenarios that cannot fund the plan (with
             essentials: cannot fund the essentials), and first-year spending percentiles.
"""
import io
import sys
import time

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner.export import _compute_estate, budget_spending
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

mode = sys.argv[1]
td = [float(v) for v in sys.argv[2].split(",")] if len(sys.argv) > 2 else [900.0, 600.0]
OPTS = {"withMedicare": "None", "withSSTaxability": 0.85, "noRothConversions": "None", "maxRothConversion": 0}
COLS = ["active", "name", "type", "year", "end", "amount", "rate", "survivor", "essential"]
THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]


def lines(essential):
    def line(name, btype, amount, ess, end=0):
        return {"active": True, "name": name, "type": btype, "year": THISYEAR, "end": end, "amount": amount,
                "rate": 0.0, "survivor": np.nan, "essential": ess and essential}
    return [line("living", "core", 50000.0, True), line("rent", "rent", 36000.0, True),
            line("travel", "travel", 20000.0, False, end=2044), line("other", "other", 10000.0, False)]


def plan(essential, expectancy=(89, 92)):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], list(expectancy), "essential stakes",
                 verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("budget", 60)
    p.setAccountBalances(taxable=[150, 150], taxDeferred=td, taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.setStateTax("NY")
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(lines(essential), columns=COLS), "Budget")
    return p


def row(label, p, t):
    if p.caseStatus != "solved":
        print(f"{label:<44} {p.caseStatus}")
        return
    lns, _ = budget_spending(p)
    g = p.gamma_n[:-1]
    life = np.sum(p.g_n / g)
    beq = _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
    k = p.discretionary_scale
    print(f"{label:<44} yr0 {p.g_n[0]:>9,.0f}  rent {lns['rent'][0]:>7,.0f}  travel {lns['travel'][0]:>7,.0f}"
          f"  last yr {p.g_n[-1] / g[-1]:>8,.0f}  lifetime {life:>10,.0f}  bequest {beq:>10,.0f}"
          f"  k {'-' if k is None else f'{k:.3f}'}  {t:.1f} s")


if mode == "fixed":
    print(f"tax-deferred {td} ($k); amounts in today's $")
    for le in ((89, 92), (95, 98)):
        for ess in (False, True):
            p = plan(ess, le)
            t = time.time()
            p.solve("maxSpending", {**OPTS, "bequest": 0})
            row(f"maxSpending LE {le} {'essentials fixed' if ess else 'whole budget scaled'}", p, time.time() - t)
    for ns, label in ((86, "essentials only"), (None, "the budget")):
        p = plan(True)
        t = time.time()
        p.solve("maxBequest", {**OPTS, **({"netSpending": ns} if ns else {})})
        row(f"maxBequest at {label}", p, time.time() - t)
elif mode == "longevity":
    for ess in (False, True):
        p = plan(ess)
        p.setReproducible(True, seed=42)
        p.setRates("histochastic", 1928, 2024)
        t = time.time()
        r = p.runStochasticSpending({**OPTS, "bequest": 0}, "mc", N=200,
                                    with_longevity=True, sexes=["M", "F"], seed=42)
        b = np.asarray(r["bases_year1"])
        print(f"{'essentials fixed' if ess else 'whole budget scaled':<20} scenarios {len(b)}  unfunded {np.sum(b == 0)}"
              f"  first-year spending p10/p50/p90 {np.percentile(b, 10):,.0f} / {np.percentile(b, 50):,.0f} /"
              f" {np.percentile(b, 90):,.0f}  {time.time() - t:.0f} s")

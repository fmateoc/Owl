"""Repro for the SS-taxability loop issue (fork-notes/issue-ss-loop.md). Runs on stock Owl.

A married couple born 1964 (life expectancy 89/92), $150k taxable, $900k/$600k tax-deferred and
$75k Roth each, SS $3,000/$2,400 a month at 70, a $600k 30-year mortgage at 6.5% taken in 2026
(its proceeds counted as cash that year), flat net spending, maxBequest, New York, conservative
rates, Owl's default reversion to pre-TCJA law in 2032. Every account holds 60/40 unless the Roth's
stock share is given. The date is frozen at 2026-10-15 so the numbers do not move day to day.

Part 1: default loop vs withSSTaxability="optimize", several spending levels, two Roth mixes, NJ.
Part 2: where the loop's plan differs from the exact one (conversions, taxable SS, federal tax).
Part 3: at a fixed SS fraction (pure LP: withSSTaxability=0.85, withMedicare="none"), force one
        withdrawal $13k higher and $13k lower and compare the bequest and the plan.
Part 4: what the Summary reports for the loop (convergence, objective error bar).
Part 5: local search on the $105k case.
"""
import datetime
import io
import re
import sys
from unittest.mock import patch

_REAL = datetime.date


class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)


import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import owlplanner as owl  # noqa: E402
from owlplanner.export import _compute_estate  # noqa: E402
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF  # noqa: E402

for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()


def plan(spend, roth=60, state="NY"):
    log = io.StringIO()
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "ss-loop", verbose=True,
                 logstreams=[log])
    p.setSpendingProfile("flat")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
    mix, rmix = [[60, 40, 0, 0]] * 2, [[roth, 100 - roth, 0, 0]] * 2
    p.setAllocationRatios("account", taxable=[mix] * 2, taxDeferred=[mix] * 2, taxFree=[rmix] * 2)
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.houseLists["Debts"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(
        [{"active": True, "name": "m", "type": "mortgage", "year": 2026, "term": 30, "amount": 600000.0,
          "rate": 6.5}]), "Debts")
    p.Lambda_in[0, 0] = 600000.0
    p.setStateTax(state)
    p.setExpirationYearOBBBA(2032)
    p.netSpending = spend
    return p, log


def bequest(p):
    return _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]


def solve(spend, roth=60, state="NY", **opts):
    p, log = plan(spend, roth, state)
    p.solve("maxBequest", options=dict({"noRothConversions": "None", "netSpending": spend}, **opts))
    iters = len(re.findall(r"Iter: \d+", log.getvalue()))
    ss = (p.fixedPointResidual or {}).get("SS", {}).get("abs_sum", 0.0)
    return p, iters, ss


print("Part 1: bequest (today's $), default loop vs withSSTaxability='optimize'")
for state, roth, spend in [("NY", 60, s) for s in (95, 100, 105, 110, 115)] + [("NY", 61, 105), ("NJ", 60, 105)]:
    a, ia, ra = solve(spend, roth, state)
    b, ib, _ = solve(spend, roth, state, withSSTaxability="optimize")
    print(f"  {state} spending ${spend}k Roth {roth}/{100 - roth}: loop {bequest(a):>9,.0f} ({ia} iterations, "
          f"{a.convergenceType}, SS residual ${ra:,.0f}) | exact {bequest(b):>9,.0f} ({ib} iterations) | "
          f"loop short by {bequest(b) - bequest(a):,.0f}")

print("\nPart 2: NY $105k, Roth 61/39 (the loop settles), lifetime totals in today's $")
for label, opts in (("loop", {}), ("exact", {"withSSTaxability": "optimize"})):
    p, _, _ = solve(105, 61, **opts)
    g = p.gamma_n[: p.N_n]
    conv = np.sum(p.x_in, axis=0) / g
    taxable_ss = np.sum(p.Psi_n * np.sum(p.zetaBar_in, axis=0) / g)
    print(f"  {label:5s}: Roth conversions {np.sum(conv):,.0f} (2026: {conv[0]:,.0f}, 2027: {conv[1]:,.0f}); "
          f"taxable SS {taxable_ss:,.0f}; federal income tax {np.sum(p.T_n / g):,.0f}; bequest {bequest(p):,.0f}")

print("\nPart 3: fixed SS fraction (withSSTaxability=0.85, withMedicare='none'), NY $105k, all accounts 60/40")
EXACT = {"withSSTaxability": 0.85, "withMedicare": "none"}
base, _, _ = solve(105, **EXACT)
n = list(base.year_n).index(2036)
w0 = base.w_ijn[0, 1, n]
print(f"  free:   Joe's 2036 tax-deferred withdrawal {w0 / base.gamma_n[n]:,.0f} (today's $), "
      f"bequest {bequest(base):,.2f}")
for delta in (+13000.0, -13000.0):
    target = max(0.0, w0 + delta * base.gamma_n[n])
    p, log = plan(105)
    orig = type(p)._buildConstraints

    def pinned(self, objective, options, orig=orig, target=target):
        orig(self, objective, options)
        self.B.setRange(self.vm["w"].idx(0, 1, n), target, target)

    with patch.object(type(p), "_buildConstraints", pinned):
        p.solve("maxBequest", options=dict({"noRothConversions": "None", "netSpending": 105}, **EXACT))
    dw = np.abs(p.w_ijn - base.w_ijn)[:, :, : p.N_n] / p.gamma_n[: p.N_n]
    print(f"  pinned: Joe's 2036 tax-deferred withdrawal {target / p.gamma_n[n]:,.0f}, bequest {bequest(p):,.2f} "
          f"(change {bequest(p) - bequest(base):+,.2f}); withdrawals moved by more than $1 in "
          f"{int(np.sum(dw > 1))} account-years, the largest {np.max(dw):,.0f}")

print("\nPart 4: what the Summary reports for the default loop (NY, Roth 60/40)")
for spend in (100, 105, 115):
    p, _, _ = solve(spend)
    print(f"  ${spend}k: Convergence '{p.convergenceType}', objective error bar +- {p.oscillationAbs / 2:,.0f} "
          f"(+- {100 * p.oscillationRel / 2:.2f}%), bequest {bequest(p):,.0f}")

print("\nPart 5: local search (breakpointMethod='local-search'), NY $105k, Roth 60/40")
p, _, _ = solve(105, breakpointMethod="local-search")
print(f"  bequest {bequest(p):,.0f}, convergence '{p.convergenceType}', "
      f"SS residual {(p.fixedPointResidual or {}).get('SS', {}).get('abs_sum', 0.0):,.0f}")

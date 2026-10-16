"""#193 follow-up: the repro's cases under the loop, exact SS (branch-and-bound), exact SS with
mipStrategy="local-search", and the breakpointMethod presets ("local-search" and
"branch-and-bound": every family set to "optimize"). Runs on stock Owl; same couple and frozen date
as issue-ss-loop-repro.py (plan() below is a copy of it).

Usage: issue-193-ls.py [maxTime seconds for the branch-and-bound preset, default 600] [method,...]
  methods: loop, ss-bb, ss-ls, convex, preset-ls, preset-bb (default: all but convex)
"""
import datetime
import io
import sys
import time
from unittest.mock import patch

_REAL = datetime.date


class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)


import pandas as pd  # noqa: E402
import owlplanner as owl  # noqa: E402
from owlplanner.export import _compute_estate  # noqa: E402
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF  # noqa: E402

for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()

BB_TIME = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0


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
    return p


METHODS = [
    ("loop", {}),
    ("SS convex", {"withSSTaxability": "convex"}),
    ("SS exact, B&B", {"withSSTaxability": "optimize"}),
    ("SS exact, local search", {"withSSTaxability": "optimize", "mipStrategy": "local-search"}),
    ("preset local-search", {"breakpointMethod": "local-search"}),
    ("preset B&B", {"breakpointMethod": "branch-and-bound", "maxTime": BB_TIME}),
]

KEYS = ["loop", "convex", "ss-bb", "ss-ls", "preset-ls", "preset-bb"]
pick = sys.argv[2].split(",") if len(sys.argv) > 2 else ["loop", "ss-bb", "ss-ls", "preset-ls", "preset-bb"]
METHODS = [m for k, m in zip(KEYS, METHODS, strict=True) if k in pick]

print(f"Bequest (today's $); time; method the Summary reports; total fixed-point residual (today's $)."
      f" B&B preset with maxTime={BB_TIME:.0f} s.")
for state, roth, spend in [("NY", 60, s) for s in (95, 100, 105, 110, 115)] + [("NY", 61, 105), ("NJ", 60, 105)]:
    print(f"{state} spending ${spend}k Roth {roth}/{100 - roth}")
    for label, opts in METHODS:
        p = plan(spend, roth, state)
        t = time.time()
        p.solve("maxBequest", options=dict({"noRothConversions": "None", "netSpending": spend}, **opts))
        dt = time.time() - t
        if p.caseStatus != "solved":
            print(f"  {label:24s} {p.caseStatus} ({dt:.1f} s)", flush=True)
            continue
        beq = _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
        resid = sum(v["abs_sum"] for v in (p.fixedPointResidual or {}).values())
        gap = getattr(p, "solverGap", -1)
        print(f"  {label:24s} {beq:>10,.0f}  {dt:7.1f} s  {p.breakpointMethodUsed:60s} residual {resid:>8,.0f}"
              f"{f'  gap {gap:.2%}' if gap is not None and gap > 0 else ''}", flush=True)

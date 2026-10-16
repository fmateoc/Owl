"""withSSTaxability="convex" (upstream #193 fix, merged 2026-10-16) on the fork's probe couple.

Same couple as itemized_convergence.couple (born 1964, $1.5M tax-deferred, $80k core + $25k
property tax budget), NY Yonkers and NJ, with and without a $600k mortgage, law as enacted (2099)
and Owl's 2032 reversion, maxBequest, fork defaults (withItemized="loop", recapture, local tax, NJ
exclusion MILP). Methods: the default loop, withSSTaxability="convex", and
breakpointMethod="local-search" as the reference. Date frozen at 2026-10-15.

Usage: convex_fork.py [method,...]   methods: loop, convex, ls (default: all three)
"""
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
sys.argv = ["x", "/dev/null"]
sys.path.insert(0, os.path.join(HERE, "..", "phase3-review"))
import itemized_convergence as ic  # noqa: E402  (freezes the date at 2026-10-15)

METHODS = {"loop": {}, "convex": {"withSSTaxability": "convex"}, "ls": {"breakpointMethod": "local-search"}}
pick = argv[0].split(",") if argv else list(METHODS)

for yob in (2032, 2099):
    for state, loc in (("NY", "Yonkers"), ("NJ", "")):
        for mort in (None, 600000.0):
            name = f"{state}{'mort' if mort else ''} {yob}"
            for key in pick:
                log = io.StringIO()
                p = ic.couple(state, loc, mort, yob, log)
                t = time.time()
                p.solve("maxBequest", options=dict({"noRothConversions": "None"}, **METHODS[key]))
                r = ic.record(p, log, time.time() - t)
                resid = sum(v["abs_sum"] for v in (p.fixedPointResidual or {}).values())
                print(f"{name:14s} {key:7s} bequest {r.get('obj', float('nan')):>10,.0f}  {r['time']:6.1f} s  "
                      f"it={r['iters']:2d} {r['conv']:32s} residual {resid:>8,.0f} worst {r.get('resid_worst')}",
                      flush=True)

"""Where the fork's NY + mortgage 2032 case loses $10.7k under withSSTaxability="convex" against
breakpointMethod="local-search" (2026-10-16): exact SS alone (branch-and-bound and local search),
then "convex" plus one more family set to "optimize". Couple as convex_fork.py. Date frozen at
2026-10-15. Usage: convex_attr.py [variant numbers, e.g. 0,1,2; default all]
"""
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
sys.argv = ["x", "/dev/null"]
sys.path.insert(0, os.path.join(HERE, "..", "phase3-review"))
import itemized_convergence as ic  # noqa: E402

V = [
    ("SS optimize B&B", {"withSSTaxability": "optimize"}),
    ("SS optimize LS", {"withSSTaxability": "optimize", "mipStrategy": "local-search"}),
    ("convex + Medicare optimize", {"withSSTaxability": "convex", "withMedicare": "optimize"}),
    ("convex + LTCG optimize", {"withSSTaxability": "convex", "withLTCG": "optimize"}),
    ("convex + NIIT optimize", {"withSSTaxability": "convex", "withNIIT": "optimize"}),
    ("convex + senior bonus optimize", {"withSSTaxability": "convex", "withSeniorBonus": "optimize"}),
]
pick = [int(k) for k in argv[0].split(",")] if argv else range(len(V))
for k in pick:
    name, o = V[k]
    log = io.StringIO()
    p = ic.couple("NY", "Yonkers", 600000.0, 2032, log)
    t = time.time()
    p.solve("maxBequest", options=dict({"noRothConversions": "None"}, **o))
    dt = time.time() - t
    r = ic.record(p, log, dt)
    resid = sum(v["abs_sum"] for v in (p.fixedPointResidual or {}).values())
    print(f"NYmort 2032 {name:30s} bequest {r.get('obj', float('nan')):>10,.0f} {dt:6.1f} s "
          f"{p.breakpointMethodUsed} residual {resid:,.0f}", flush=True)

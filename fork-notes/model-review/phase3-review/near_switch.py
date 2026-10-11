"""Near-switch synthetic cases: loop vs optimize (default gap and 1e-7), exact LP and full loop."""
import sys, time
sys.path.insert(0, "tests/tax")
import numpy as np
from test_itemized import _plan, OPTS
from owlplanner.export import _compute_estate

def obj(p):
    return float(p.basis) if p.objective == "maxSpending" else _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]

CASES = {
 "FL mtg560k": dict(state="FL", property_tax=0.0, mortgage=(560_000.0, 6.5, 30)),
 "FL mtg480k pt12k": dict(state="FL", property_tax=12_000.0, mortgage=(480_000.0, 6.5, 30)),
 "NY pt25k ch5k med4k": dict(state="NY", property_tax=25_000.0, charity=5_000.0, medical=4_000.0),
 "NJ pt15k mtg400k": dict(state="NJ", property_tax=15_000.0, mortgage=(400_000.0, 6.5, 30)),
 "NY mtg300k pt18k": dict(state="NY", property_tax=18_000.0, mortgage=(300_000.0, 6.5, 30)),
}
for objective in ("maxBequest", "maxSpending"):
  for base_name, base in (("exact", OPTS), ("fullloop", {"noRothConversions": "None"})):
    for name, kw in CASES.items():
        r = {}
        for mode, extra in (("loop", {}), ("opt", {}), ("opt-tight", {"gap": 1e-7})):
            p = _plan(**kw)
            o = dict(base); o.update(extra); o["withItemized"] = "loop" if mode == "loop" else "optimize"
            if objective == "maxSpending":
                o["bequest"] = 0
            t = time.time(); p.solve(objective, options=o); d = time.time() - t
            r[mode] = (obj(p) if p.caseStatus == "solved" else float("nan"), d, int(np.count_nonzero(p.itemizing_n)))
        L = r["loop"][0]
        print(f"{objective:11s} {base_name:8s} {name:22s} loop {L:>13,.1f} ({r['loop'][2]}y {r['loop'][1]:.1f}s)"
              f" opt {r['opt'][0]-L:+9.1f} ({r['opt'][2]}y {r['opt'][1]:.1f}s)"
              f" opt-tight {r['opt-tight'][0]-L:+9.1f} ({r['opt-tight'][2]}y {r['opt-tight'][1]:.1f}s)", flush=True)

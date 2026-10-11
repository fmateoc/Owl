"""withItemized loop vs optimize: 18 examples (their own options) and near-switch synthetic cases.
Plans start today (not frozen)."""
import io, sys, time, glob
from pathlib import Path
import numpy as np, pandas as pd
from unittest import mock
import datetime as dt
sys.path.insert(0, str(Path.cwd() / "tests"))
import owlplanner as owl
from owlplanner.export import _compute_estate

def obj(p):
    if p.objective == "maxSpending":
        return float(p.basis)
    return _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]

def run_case(path, mode, extra=None):
    p = owl.readConfig(path, verbose=False, logstreams=[io.StringIO()])
    o = dict(p.solverOptions); o["withItemized"] = mode
    if extra: o.update(extra)
    t = time.time(); p.solve(p.objective, o); d = time.time() - t
    return p, d

which = sys.argv[1] if len(sys.argv) > 1 else "examples"
extra = {"breakpointMethod": "local-search"} if "ls" in sys.argv[2:] else None
if which == "examples":
    for path in sorted(glob.glob("examples/Case_*.toml")):
        r = {}
        for mode in ("loop", "optimize"):
            p, d = run_case(path, mode, extra)
            r[mode] = (p.caseStatus, obj(p) if p.caseStatus == "solved" else float("nan"), d,
                       int(np.count_nonzero(getattr(p, "itemizing_n", []))))
        dl = r["optimize"][1] - r["loop"][1]
        print(f"{Path(path).stem:28s} loop {r['loop'][1]:>14,.2f} ({r['loop'][3]} yrs, {r['loop'][2]:.1f}s)"
              f"  optimize {r['optimize'][1]:>14,.2f} ({r['optimize'][3]} yrs, {r['optimize'][2]:.1f}s)  diff {dl:+,.2f}"
              f" ({100*dl/max(abs(r['loop'][1]),1):+.4f}%)", flush=True)

"""18 examples: withSSTaxability loop vs MODE (optimize by default, or convex), objective, iterations, time.
Date frozen at 2026-10-15. Usage: ex_ss.py REPO_ROOT [MODE]"""
import datetime, glob, io, re, sys, time
from pathlib import Path
from unittest.mock import patch
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import owlplanner as owl
from owlplanner.export import _compute_estate
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
root = sys.argv[1]
MODE = sys.argv[2] if len(sys.argv) > 2 else "optimize"
for path in sorted(glob.glob(f"{root}/examples/Case_*.toml")):
    row = []
    for ss in ("loop", "other"):
        log = io.StringIO()
        p = owl.readConfig(path, verbose=True, logstreams=[log])
        opts = dict(p.solverOptions)
        opts["withSSTaxability"] = "loop" if ss == "loop" else MODE
        t = time.time(); p.solve(p.objective, opts); dt = time.time() - t
        obj = float(p.basis) if p.objective == "maxSpending" else _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
        res = p.fixedPointResidual or {}
        ssr = res.get("SS", {}).get("abs_sum", 0.0)
        row.append((obj, len(re.findall(r"Iter: \d+", log.getvalue())), dt, p.convergenceType, ssr))
    (a, ia, ta, ca, ra), (b, ib, tb, cb, rb) = row
    print(f"{Path(path).stem:24s} loop {a:>13,.0f} it={ia:2d} {ta:5.1f}s SSres {ra:>7,.0f} {ca[:22]:22s} | {MODE[:4]} {b:>13,.0f} it={ib:2d} {tb:6.1f}s SSres {rb:>7,.0f} {cb[:22]:22s} | {100*(b-a)/abs(a):+6.2f}%", flush=True)

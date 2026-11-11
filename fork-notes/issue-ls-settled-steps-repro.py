"""Repro for the issue draft `issue-ls-settled-steps.md`, on stock upstream `dev`.

    python issue-ls-settled-steps-repro.py examples/Case_joe.toml

Solves the shipped example under local search with both wall-clock caps lifted (so that the
result does not depend on load), the claiming ages fixed, and the date frozen at 2026-01-01 as
the test suite does. Prints the plan's value, the CPU time, and per loop iteration of the search
its start, whether it moved the plan, and the seconds spent in the capped steps (b), (b'), (a').
Run it on `dev` and on `dev` with `issue-ls-settled-steps.patch`.
"""
import datetime
import io
import sys
import time

import owlplanner as owl
from owlplanner import plan as planmod

_REAL_DATE = datetime.date


class _FixedDate(_REAL_DATE):
    @classmethod
    def today(cls):
        return _REAL_DATE(2026, 1, 1)


for _mod in list(sys.modules.values()):
    if _mod is not None and getattr(_mod, "date", None) is _REAL_DATE:
        _mod.date = _FixedDate

planmod._mosek_available = lambda: False
p = owl.readConfig(sys.argv[1], verbose=False, logstreams=[io.StringIO()])
opts = {**p.solverOptions, "breakpointMethod": "local-search", "withSSAges": "fixed", "solver": "HiGHS",
        "localSearchTime": 7200, "localSearchStepTime": 1800}
t = time.process_time()
p.solve(p.objective, options=opts)
cpu = time.process_time() - t
value = p.g_n[0] if p.objective == "maxSpending" else p.bequest
print(f"{p.objective}: {value:,.2f}   CPU {cpu:.1f} s   {p.breakpointMethodUsed}")
for k, it in enumerate(p.localSearchLog):
    steps = it["steps"]
    if not steps:
        print(f"  search {k}: same problem as the last, plan reused")
        continue
    starts = [s for s in steps if s["step"].startswith("start:") and s["ok"]]
    start = starts[-1]["objective"] if starts else None
    objs = [s["objective"] for s in steps if s["ok"] and s["objective"] is not None]
    moved = start is not None and min(objs) < start - 1e-7 * abs(start)
    capped = sum(s["seconds"] for s in steps if s["step"].split(": ")[0].endswith(("(b)", "(b')", "(a')")))
    print(f"  search {k}: {starts[-1]['step'] if starts else 'no start'}; {'moved' if moved else 'no move'}; "
          f"{it['time']:.1f} s, of which (b), (b'), (a') {capped:.1f} s")

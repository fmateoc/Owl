"""One shipped example solved under local search, timed: P2's measurement on stock upstream.

    PYTHONPATH=<checkout>/src .venv/bin/python fork-notes/performance/p2_stock_probe.py \
        <Case_x.toml> <out.json> [options JSON]

Run it once from a checkout of upstream `dev` and once from the same checkout with the P2 patch
(`fork-notes/issue-ls-settled-steps.patch`); `owlplanner.__file__` in the output says which ran.
The case is the shipped example, read from that checkout's `examples/`, with
`breakpointMethod = "local-search"`, the claiming ages fixed (`withSSAges = "fixed"`), and the
options JSON laid over it (`{"localSearchTime": 7200, "localSearchStepTime": 1800}` lifts the
wall-clock caps so that the result does not depend on load). The date is frozen at 2026-01-01, as
upstream's `tests/conftest.py` does, so that two runs on different days solve the same plan.

Performance review, P2 (`fork-notes/performance-review.md`).
"""
import datetime
import io
import json
import sys
import time
from pathlib import Path

import owlplanner as owl
from owlplanner import localsearch, plan as planmod  # noqa: F401 (imported before the freeze)

_REAL_DATE = datetime.date


class _FixedDate(_REAL_DATE):
    @classmethod
    def today(cls):
        return _REAL_DATE(2026, 1, 1)


for _mod in list(sys.modules.values()):
    if _mod is not None and getattr(_mod, "date", None) is _REAL_DATE:
        _mod.date = _FixedDate

case, out = sys.argv[1], sys.argv[2]
extra = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
root = Path(owl.__file__).resolve().parents[2]
log = io.StringIO()
p = owl.readConfig(str(root / "examples" / case), verbose=True, logstreams=[log])
planmod._mosek_available = lambda: False
opts = {**p.solverOptions, "breakpointMethod": "local-search", "withSSAges": "fixed", "solver": "HiGHS", **extra}
t, c = time.time(), time.process_time()
p.solve(p.objective, options=opts)
wall, cpu = time.time() - t, time.process_time() - c

iterations = []
for it in getattr(p, "localSearchLog", None) or []:
    steps = it["steps"]
    cap = int(extra.get("localSearchStepNodes") or localsearch.STEP_NODES["HiGHS"])
    capped = [s for s in steps if (s.get("nodes") or 0) >= cap]
    iterations.append({
        "time": it["time"],
        "steps": len(steps),
        "capped": len(capped),
        "labels": [f'{s["step"]} {s["seconds"]}s n={s.get("nodes")}' for s in steps],
    })
text = log.getvalue()
value = float(p.g_n[0] if p.objective == "maxSpending" else p.bequest)
json.dump({
    "case": case, "owlplanner": owl.__file__, "objective": p.objective, "status": p.caseStatus,
    "value": round(value, 2), "method": p.breakpointMethodUsed, "wall": round(wall, 1), "cpu": round(cpu, 1),
    "budget_spent": text.count("time budget spent"), "skipped_iterations": text.count("capped steps skipped"),
    "loop_iterations": text.count("Iter: "), "iterations": iterations, "options": extra,
}, open(out, "w"), indent=1)
print(case, p.caseStatus, round(value, 2), f"wall {wall:.1f}s cpu {cpu:.1f}s", owl.__file__)

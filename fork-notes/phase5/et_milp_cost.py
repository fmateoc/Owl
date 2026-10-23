"""
What the fork's earnings test costs the full MILP (#220, the maintainer's condition, 2026-10-23).

For the three shipped examples that pay SS before FRA in a work year (chris+pat, alex+jamie,
jack+jill), at the case's own claiming ages, with breakpointMethod="branch-and-bound" (every MILP
family on "optimize", solved by branch-and-bound) and the fork's other additions off where they
could apply (withItemized="none"): test off and on, each solved twice in alternation. Reports the
model size (columns, binaries, rows), wall time, branch-and-bound nodes, gap, the
time spent building the SS streams (Plan._ss_streams, which applies the test), and the basis.

Run from the repository root (plans start today):

    .venv/bin/python fork-notes/phase5/et_milp_cost.py | tee fork-notes/phase5/et_milp_cost_YYYY-MM-DD.txt

Resume an interrupted run: `... et_milp_cost.py alex+jamie --reps=1 --tests=on`.
"""

import io
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import owlplanner as owl  # noqa: E402
from owlplanner.plan import Plan  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
BASE = {"withItemized": "none", "breakpointMethod": "branch-and-bound"}
STREAMS = {"t": 0.0, "calls": 0}
_orig = Plan._ss_streams


def _timed(self, *a, **k):
    t0 = time.perf_counter()
    try:
        return _orig(self, *a, **k)
    finally:
        STREAMS["t"] += time.perf_counter() - t0
        STREAMS["calls"] += 1


Plan._ss_streams = _timed


def run(case, test):
    p = owl.readConfig(os.path.join(EX, f"Case_{case}.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, f"HFP_{case}.xlsx"))
    STREAMS.update(t=0.0, calls=0)
    t0 = time.time()
    p.solve(p.objective, dict(p.solverOptions or {}, **BASE, withEarningsTest=test))
    dt = time.time() - t0
    assert p.caseStatus == "solved", (case, test, p.caseStatus)
    return p, dt


def main(cases=("chris+pat", "alex+jamie", "jack+jill"), reps=(1, 2), tests=(False, True)):
    print(f"owlplanner from {owl.__file__}; run {date.today()}; options {BASE}")
    for case in cases:
        print(f"\n{case}")
        for rep in reps:
            for test in tests:
                p, dt = run(case, test)
                wh = float(p.ss_withheld_in.sum()) if getattr(p, "ss_withheld_in", None) is not None else 0.0
                print(f"  test {'on ' if test else 'off'} #{rep}: columns {p.vm.nvars} binaries {p.nbins} "
                      f"rows {p.A.ncons}; {dt:6.1f}s, nodes {p.solverNodes}, gap {p.solverGap:.1e}; SS streams "
                      f"{STREAMS['t'] * 1000:.0f} ms in {STREAMS['calls']} calls; basis {float(p.basis):,.2f}; "
                      f"withheld {wh:,.0f} nominal")


if __name__ == "__main__":
    # Optional: case names, then --reps=1,2 and --tests=off,on (to resume an interrupted run).
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    kw = {}
    if args:
        kw["cases"] = args
    if "reps" in opts:
        kw["reps"] = [int(r) for r in opts["reps"].split(",")]
    if "tests" in opts:
        kw["tests"] = [t == "on" for t in opts["tests"].split(",")]
    main(**kw)

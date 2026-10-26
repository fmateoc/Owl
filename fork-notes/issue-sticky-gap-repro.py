"""
Repro for the sticky-binaries tie being looser than a requested MIP gap (issue draft
`fork-notes/issue-sticky-gap.md`). Stock examples only; runs on any checkout.

Each case is solved with breakpointMethod="branch-and-bound" and gap=1e-5. Every HiGHS run of the
solve is recorded (status and the mip_gap HiGHS reports); the script prints the largest MIP gap
HiGHS reported, the accepted solve's Plan.solverGap, how many times _stickyBinaries kept the previous
iteration's plan, the loop's iterations, and the objective value.

Run from the root of the checkout to test (plans start today), for example:

    PYTHONPATH=$PWD/src .venv/bin/python issue-sticky-gap-repro.py
"""

import io
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date

import owlplanner as owl
from owlplanner.plan import Plan

EX = os.path.join(os.getcwd(), "examples")
GAP = 1e-5
CASES = [  # (label, Case_chris+pat claiming ages or None for the file's, SLCSP $k/yr from 2029 or 0)
    ("chris+pat as shipped", None, 0),
    ("chris+pat, SLCSP 20 from 2029, ages 67/63", [67.0, 63.0], 20),
    ("chris+pat, SLCSP 20 from 2029, ages 70/63", [70.0, 63.0], 20),
    ("chris+pat, SLCSP 20 from 2029, ages 68.5/63", [68.5, 63.0], 20),
]


def solve(case):
    label, ages, slcsp = case
    runs = []  # this case's HiGHS runs only: a worker may solve more than one case
    run_highs = Plan._run_highs

    def recorded(self, *a, **k):
        res = run_highs(self, *a, **k)
        runs.append((res[3], res[4]))
        return res

    Plan._run_highs = recorded
    try:
        buf = io.StringIO()
        p = owl.readConfig(os.path.join(EX, "Case_chris+pat.toml"), verbose=True, logstreams=[buf])
        if ages is not None:
            p.setSocialSecurity(list(p.ssecAmounts), ages)
        if slcsp:
            p.setACA(slcsp, start_year=2029)
        t0 = time.time()
        p.solve(p.objective, dict(p.solverOptions or {}, breakpointMethod="branch-and-bound", gap=GAP))
    finally:
        Plan._run_highs = run_highs
    mip = [g for _, g in runs if g >= 0]
    log = buf.getvalue()
    return {"label": label, "status": p.caseStatus, "seconds": time.time() - t0,
            "value": p._objectiveValue(p.objective) if p.caseStatus == "solved" else None,
            "solver_gap": float(p.solverGap), "max_highs_gap": max(mip, default=None),
            "statuses": sorted({st for st, _ in runs}), "sticky": log.count("Kept the previous binaries"),
            "iterations": log.count("Iter: "), "sticky_tol": getattr(p, "_sticky_tol", None)}


def main():
    print(f"issue-sticky-gap-repro.py, {date.today().isoformat()}, owlplanner {owl.__version__} from {owl.__file__}")
    print(f"breakpointMethod='branch-and-bound', gap={GAP:.0e}, default relTol")
    with ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context("spawn")) as pool:
        res = list(pool.map(solve, CASES))
    print(f"{'case':<46}{'HiGHS max gap':>14}{'solverGap':>11}{'keeps':>6}{'iter':>5}{'_sticky_tol':>12}"
          f"{'value':>13}{'s':>5}")
    for r in res:
        if r["status"] != "solved":
            print(f"{r['label']:<46}{r['status']}")
            continue
        print(f"{r['label']:<46}{r['max_highs_gap']:>14.3e}{r['solver_gap']:>11.3e}{r['sticky']:>6}{r['iterations']:>5}"
              f"{r['sticky_tol']:>12.1e}{r['value']:>13,.2f}{r['seconds']:>5.0f}")
    print(f"HiGHS statuses: {sorted({s for r in res for s in r['statuses']})}")


if __name__ == "__main__":
    sys.exit(main())

"""
Phase 5 step 6 (2026-10-26): is the dip at Pat 64y0m in the chris+pat dry run the model's, or
local search's noise?

work_sweep.py's dry run (`work_sweep_chris+pat_2026-10-25.txt`) scored Pat 64y0m below both 63y0m
and 65y0m in all four variants (by 13-38 $/yr), with ACA and Medicare flat and more federal tax at
64y0m. Here the same plans (the dry run's base variant: Pat works through 2028, stand-in
slcsp_annual 20 from 2029; Chris held at 68y6m) are solved by branch-and-bound
(breakpointMethod="branch-and-bound": every family exact, the case's own model), one process per
age. If branch-and-bound proves each plan within its gap and still shows the dip, the dip is the
model's; if it fills it in, local search missed a plan there.

Run from the repository root (today's date; the variant files are rebuilt in --out-dir):

    .venv/bin/python fork-notes/phase5/ws_bb_check.py [--variant base] [--pat 63 64 65]

Output: `ws_bb_check_YYYY-MM-DD.txt` beside this script (written by the caller with tee).
"""

import argparse
import json
import os
import sys
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

import work_sweep as ws  # noqa: E402

import owlplanner as owl  # noqa: E402
from owlplanner.export import plan_metrics  # noqa: E402
from owlplanner.plan import TIME_LIMIT, Plan  # noqa: E402

HERE = os.path.dirname(__file__)
CASE = os.path.join(HERE, "..", "..", "examples", "Case_chris+pat.toml")
SPEC = os.path.join(HERE, "work_sweep_chris+pat.json")
LS_SCORES = os.path.join(HERE, "work_sweep_chris+pat_2026-10-25.json")


def bb(args):
    diconf, dirname, ages, gap, max_time = args
    p, buf = ws.make_plan(diconf, dirname, ages)
    # Without a gap option, withMedicare="optimize" loosens the gap to MILP_GAP (3e-3, about
    # $340/yr here): more than the dip being tested. maxTime is per MIP solve.
    opts = ws.base_options(p, withSSAges="fixed", breakpointMethod="branch-and-bound", gap=gap, maxTime=max_time)
    runs = []  # every HiGHS run of the solve: (status, gap, seconds)
    run_highs = Plan._run_highs

    def recorded(self, *a, **k):
        t = time.time()
        res = run_highs(self, *a, **k)
        runs.append((res[3], res[4], round(time.time() - t, 1)))
        return res

    Plan._run_highs = recorded  # one plan per worker process
    t0 = time.time()
    p.solve(p.objective, opts)
    dt = time.time() - t0
    out = {"ages": list(ws.months(ages)), "status": p.caseStatus, "seconds": dt, "runs": runs,
           "time_limit_hits": sum("time limit" in str(st).lower() for st, _, _ in runs),
           "max_run_gap": max((g for _, g, _ in runs), default=-1.0), "log_tail": buf.getvalue()[-1500:]}
    if p.caseStatus == "solved":
        m = plan_metrics(p)
        out.update({
            "value": p._objectiveValue(p.objective),
            "gap": float(p.solverGap),
            "nodes_total": getattr(p, "solverNodesTotal", None),
            "node_limit_hits": getattr(p, "solverNodeLimitHits", None),
            "residual": p._fixedPointResidualTotal(),
            "method": getattr(p, "breakpointMethodUsed", None),
            "federal": m["federal_income_tax_today"] + m["ltcg_tax_today"] + m["niit_today"],
            "aca": m["aca_today"], "medicare": m["medicare_today"],
            "ss_paid": m["ss_income_today"], "ss_withheld": m["ss_withheld_today"],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="base")
    ap.add_argument("--chris", type=float, default=68.5)
    ap.add_argument("--pat", type=float, nargs="*", default=[63.0, 64.0, 65.0])
    ap.add_argument("--gap", type=float, default=1e-5, help="relative MIP gap (Owl's GAP is 1e-4)")
    ap.add_argument("--max-time", type=float, default=TIME_LIMIT, help="seconds per MIP solve")
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "..", "otherFiles", "sweep-bb"))
    ap.add_argument("--json")
    args = ap.parse_args()

    with open(SPEC, encoding="utf-8") as f:
        spec = json.load(f)
    by = {v[0]: v for v in ws.build_variants(CASE, spec, args.out_dir)}
    _, d, dirname, sets = by[args.variant]
    print(f"ws_bb_check.py, {date.today().isoformat()}, owlplanner {owl.__version__} from {owl.__file__}")
    print(f"chris+pat dry-run variant '{args.variant}': {'; '.join(sets)}")
    print(f"branch-and-bound at fixed ages, Chris {ws.ym(args.chris)}, gap {args.gap:.0e}, maxTime "
          f"{args.max_time:.0f}s per MIP; objective: annual spending, today's $/yr")

    ls = {}
    if os.path.exists(LS_SCORES):
        with open(LS_SCORES, encoding="utf-8") as f:
            for row in json.load(f):
                if row["name"] == args.variant:
                    ls = {tuple(r["ages"]): r.get("value") for r in row["results"].values()}

    trials = [[args.chris, a] for a in args.pat]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=len(trials), mp_context=mp.get_context("spawn")) as pool:
        results = list(pool.map(bb, [(d, dirname, t, args.gap, args.max_time) for t in trials]))
    print(f"\n{'Pat':>6}{'B&B':>13}{'local search':>14}{'B&B - LS':>10}{'gap':>10}{'nodes':>10}"
          f"{'node cap':>10}{'time cap':>9}{'residual':>10}{'seconds':>9}")
    for t, r in zip(trials, results, strict=True):
        key = tuple(ws.months(t))
        v_ls = ls.get(key)
        if r["status"] != "solved":
            print(f"{ws.ym(t[1]):>6}  {r['status']}  ({r['seconds']:.0f}s)")
            print(r["log_tail"])
            continue
        diff = f"{r['value'] - v_ls:>10,.2f}" if v_ls is not None else f"{'-':>10}"
        hits = r["node_limit_hits"]
        print(f"{ws.ym(t[1]):>6}{r['value']:>13,.2f}{(v_ls or 0):>14,.2f}{diff}{r['gap']:>10.1e}"
              f"{r['nodes_total']:>10}{str(hits[0] if hits else 0):>10}{r['time_limit_hits']:>9}"
              f"{r['residual']:>10,.0f}{r['seconds']:>9.0f}")
    print(f"\n{'Pat':>6}{'federal':>11}{'ACA':>9}{'Medicare':>10}{'SS paid':>12}{'SS withheld':>12}  method")
    for t, r in zip(trials, results, strict=True):
        if r["status"] == "solved":
            print(f"{ws.ym(t[1]):>6}{r['federal']:>11,.0f}{r['aca']:>9,.0f}{r['medicare']:>10,.0f}"
                  f"{r['ss_paid']:>12,.0f}{r['ss_withheld']:>12,.0f}  {r['method']}")
    print("\ngap: the accepted solve's; node cap: main MIP solves stopped at the node limit; time cap: HiGHS")
    print("runs stopped on time;")
    print("residual: the plan's fixed-point residual, today's $ summed over families.")
    for t, r in zip(trials, results, strict=True):
        print(f"Pat {ws.ym(t[1])}: {len(r['runs'])} HiGHS runs, largest gap {r['max_run_gap']:.1e}, "
              f"statuses {sorted({st for st, _, _ in r['runs']})}")
    print(f"Total {time.time() - t0:.0f}s.")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1, default=str)


if __name__ == "__main__":
    main()

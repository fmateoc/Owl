"""
Does relTol equal to the MIP gap make branch-and-bound plans follow the gap? (2026-10-26)

`highs_gap_probe.py` traced the reported gap above --gap to the loop's sticky binaries, whose tie
tolerance is the loop's relTol (5e-5 by default): at gap 1e-5 a plan is bounded only to 1e-5 + 5e-5.
This re-solves plans of the branch-and-bound dry run (`work_sweep_chris+pat_bb_2026-10-26.json`)
at gap 1e-5 twice, with the default relTol and with relTol = 1e-5, and prints per plan: value,
reported gap, how the loop ended, iterations, sticky keeps, HiGHS runs and their largest MIP gap,
fixed-point residual and time. Plans: the 12 whose reported gap exceeded 1e-5, and each variant's
decided plan.

Run from the repository root (plans start today; compare with the dry run only on its date):

    .venv/bin/python fork-notes/phase5/reltol_probe.py [--jobs 4] [--json FILE]
"""

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

import work_sweep as ws  # noqa: E402

import owlplanner as owl  # noqa: E402

HERE = os.path.dirname(__file__)
CASE = os.path.join(HERE, "..", "..", "examples", "Case_chris+pat.toml")
SPEC = os.path.join(HERE, "work_sweep_chris+pat.json")
RUN = os.path.join(HERE, "work_sweep_chris+pat_bb_2026-10-26.json")


def solve(args):
    diconf, dirname, ages, gap, rel_tol = args
    ws._record_highs_runs()
    ws._HIGHS_RUNS.clear()
    p, buf = ws.make_plan(diconf, dirname, [m / 12 for m in ages])
    extra = {"gap": gap} if rel_tol is None else {"gap": gap, "relTol": rel_tol}
    opts = ws.base_options(p, withSSAges="fixed", breakpointMethod="branch-and-bound", **extra)
    t0 = time.time()
    p.solve(p.objective, opts)
    log = buf.getvalue()
    runs = list(ws._HIGHS_RUNS)
    mip_gaps = [g for _, g in runs if g >= 0]
    out = {"status": p.caseStatus, "seconds": time.time() - t0, "iterations": log.count("Iter: "),
           "sticky_keeps": log.count("Kept the previous binaries"),
           "convergence": getattr(p, "convergenceType", None), "sticky_tol": getattr(p, "_sticky_tol", None),
           "highs_runs": len(runs),
           "highs_statuses": sorted({st for st, _ in runs}), "max_mip_gap": max(mip_gaps, default=None)}
    if p.caseStatus == "solved":
        out.update({"value": p._objectiveValue(p.objective), "gap": float(p.solverGap),
                    "residual": p._fixedPointResidualTotal()})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", type=float, default=1e-5)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "..", "otherFiles", "sweep-reltol"))
    ap.add_argument("--json")
    args = ap.parse_args()

    with open(SPEC, encoding="utf-8") as f:
        spec = json.load(f)
    by = {v[0]: v for v in ws.build_variants(CASE, spec, args.out_dir)}
    with open(RUN, encoding="utf-8") as f:
        rows = json.load(f)
    plans = []  # (variant, ages in months, the dry run's value and gap)
    for r in rows:
        for c in r["results"].values():
            if c.get("gap") is not None and c["gap"] > args.gap * 1.0001 or c["ages"] == r["best"]:
                plans.append((r["name"], tuple(c["ages"]), c.get("value"), c.get("gap"), c["ages"] == r["best"]))

    print(f"reltol_probe.py, {date.today().isoformat()}, owlplanner {owl.__version__} from {owl.__file__}")
    print(f"{len(plans)} plans of {os.path.basename(RUN)}, branch-and-bound at gap {args.gap:.0e}, "
          f"default relTol vs relTol = {args.gap:.0e}; jobs {args.jobs}")
    jobs = []
    for name, ages, _, _, _ in plans:
        _, d, dirname, _ = by[name]
        for rel in (None, args.gap):
            jobs.append((d, dirname, ages, args.gap, rel))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.jobs, mp_context=mp.get_context("spawn")) as pool:
        res = list(pool.map(solve, jobs))

    print(f"\n{'variant':<22}{'ages':>12}  {'relTol':<8}{'value':>12}{'d value':>9}{'gap':>10}{'conv':>12}"
          f"{'iter':>5}{'stick':>6}{'MIP gap':>10}{'resid':>7}{'sec':>6}")
    out = []
    for k, (name, ages, v_run, g_run, decided) in enumerate(plans):
        a, b = res[2 * k], res[2 * k + 1]
        label = "/".join(ws.ym(m / 12) for m in ages) + ("*" if decided else "")
        for tag, r in (("default", a), ("= gap", b)):
            if r["status"] != "solved":
                print(f"{name:<22}{label:>12}  {tag:<8}{r['status']:>12}")
                continue
            dv = r["value"] - a["value"] if tag == "= gap" and a.get("value") is not None else 0.0
            mg = "-" if r["max_mip_gap"] is None else f"{r['max_mip_gap']:.2e}"
            print(f"{name:<22}{label:>12}  {tag:<8}{r['value']:>12,.2f}{dv:>9.2f}{r['gap']:>10.2e}"
                  f"{str(r['convergence']):>12}{r['iterations']:>5}{r['sticky_keeps']:>6}{mg:>10}"
                  f"{r['residual']:>7.0f}{r['seconds']:>6.0f}")
        out.append({"variant": name, "ages": list(ages), "decided": decided, "dry_run": {"value": v_run, "gap": g_run},
                    "default": a, "reltol_gap": b})
    print("\n* = the variant's decided plan in the dry run. d value: relTol = gap less default. gap: the accepted")
    print("solve's reported gap. stick: sticky-binary keeps. MIP gap: largest gap HiGHS reported on any MIP run.")
    print(f"Total {time.time() - t0:.0f}s.")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    main()

"""Does federal/state itemizing in loop mode make the self-consistent loop cycle? (#185, 2026-10-15)

The maintainer's concern on #185: "Adding more stuff to the recursion loop is what causes cycling
and prevents monotonic convergence." This runs the same plans with withItemized = "none" and
"loop" under the default loop (no local search, no exact-LP pins) and records, for each solve, the
number of loop iterations, how the loop ended (convergenceType), whether the objective sequence was
monotonic, the largest fixed-point residual family, and the objective.

Cases: the Phase 3 probe couple (r123_cases.py: born 1964, $1.5M tax-deferred, budget $80k core +
$25k property tax), NY Yonkers and NJ, with and without a $600k mortgage, under the law as enacted
(yOBBBA 2099) and under Owl's default reversion (2032), maxBequest and maxSpending; then the 18
examples as shipped. Date frozen at 2026-10-15 (plans start "today").

Usage: itemized_convergence.py OUT.json [probe,nyattr,ptsweep,ls,examples]
"""
import datetime
import io
import json
import re
import sys
import time
from unittest.mock import patch

_REAL = datetime.date


class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)


def _freeze():
    for mod in list(sys.modules.values()):
        if mod is not None and getattr(mod, "date", None) is _REAL:
            patch.object(mod, "date", _Day).start()


import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import owlplanner as owl  # noqa: E402
from owlplanner.export import _compute_estate  # noqa: E402
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond  # noqa: E402

_freeze()
THISYEAR = 2026
ITER = re.compile(r"Iter: (\d+); f: ([-\d,.$]+)")


def line(n, t, a):
    return {"active": True, "name": n, "type": t, "year": THISYEAR, "end": 0, "amount": a, "rate": 0.0,
            "survivor": np.nan}


def couple(state, loc, mortgage, yob, log):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "conv", verbose=True,
                 logstreams=[log])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.houseLists["Budget"] = cond(pd.DataFrame([line("core", "core", 80000.0),
                                                line("pt", "property tax", 25000.0)]), "Budget")
    if mortgage:
        p.houseLists["Debts"] = cond(pd.DataFrame([{"active": True, "name": "m", "type": "mortgage",
                                                    "year": THISYEAR, "term": 30, "amount": mortgage,
                                                    "rate": 6.5}]), "Debts")
        p.Lambda_in[0, 0] = mortgage
    p.setStateTax(state, locality=loc)
    p.setExpirationYearOBBBA(yob)
    return p


def record(p, log, dt):
    its = [(int(i), float(f.replace(",", "").replace("$", ""))) for i, f in ITER.findall(log.getvalue())]
    out = {"status": p.caseStatus, "iters": len(its), "time": round(dt, 1), "conv": p.convergenceType}
    if p.caseStatus != "solved":
        return out
    f = [v for _, v in its]
    # Monotonic as upstream defines it (non-increasing after iteration 0), with a $1 tolerance.
    out["monotonic"] = all(f[k] <= f[k - 1] + 1.0 for k in range(2, len(f)))
    out["f_seq"] = [round(v) for v in f]
    res = p.fixedPointResidual or {}
    if res:
        name, val = max(res.items(), key=lambda kv: kv[1]["abs_sum"])
        out["resid_worst"] = [name, round(float(val["abs_sum"]), 0)]
        out["resid_item"] = {k: round(float(v["abs_sum"]), 0) for k, v in res.items()
                             if "itemiz" in k or "medical" in k}
    out["obj"] = round(float(p.basis) if p.objective == "maxSpending"
                       else float(_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]), 0)
    out["fed_item_yrs"] = int(np.count_nonzero(getattr(p, "itemizing_n", [])))
    out["st_item_yrs"] = int(np.count_nonzero(getattr(p, "st_itemizing_n", [])))
    return out


def run_probe(out):
    for yob in (2099, 2032):
        for s, loc in (("NY", "Yonkers"), ("NJ", "")):
            for m in (None, 600000.0):
                for objective in ("maxBequest", "maxSpending"):
                    for mode in ("none", "loop"):
                        name = f"{s}{'mort' if m else ''} {yob} {objective} {mode}"
                        log = io.StringIO()
                        p = couple(s, loc, m, yob, log)
                        opts = {"noRothConversions": "None", "withItemized": mode}
                        if objective == "maxSpending":
                            opts["bequest"] = 0
                        t = time.time()
                        p.solve(objective, options=opts)
                        out[name] = record(p, log, time.time() - t)
                        r = out[name]
                        print(f"{name:34s} it={r['iters']:2d} {r['conv']:32s} mono={r.get('monotonic')} "
                              f"obj={r.get('obj')} fed={r.get('fed_item_yrs')} st={r.get('st_item_yrs')} "
                              f"{r.get('resid_worst')}", flush=True)


def run_nyattr(out):
    """NY + mortgage with federal itemizing only: NY's IT-196 years patched to none (attribution)."""
    for yob in (2099, 2032):
        for objective in ("maxBequest", "maxSpending"):
            name = f"NYmort {yob} {objective} fed-only"
            log = io.StringIO()
            p = couple("NY", "Yonkers", 600000.0, yob, log)
            opts = {"noRothConversions": "None", "withItemized": "loop"}
            if objective == "maxSpending":
                opts["bequest"] = 0
            t = time.time()
            with patch.object(type(p), "_st_item_candidate_years", lambda self: []):
                p.solve(objective, options=opts)
            out[name] = record(p, log, time.time() - t)
            r = out[name]
            print(f"{name:34s} it={r['iters']:2d} {r['conv']:32s} obj={r.get('obj')} "
                  f"fed={r.get('fed_item_yrs')} st={r.get('st_item_yrs')} {r.get('resid_worst')}", flush=True)


def run_ptsweep(out):
    """NY + mortgage, 2032, maxBequest: property tax $15k-30k, none vs loop (where the loop fails)."""
    for pt in (15000.0, 20000.0, 22500.0, 25000.0, 27500.0, 30000.0):
        for mode in ("none", "loop"):
            name = f"NYmort 2032 maxBequest pt{pt / 1000:g}k {mode}"
            log = io.StringIO()
            p = couple("NY", "Yonkers", 600000.0, 2032, log)
            p.houseLists["Budget"] = cond(pd.DataFrame([line("core", "core", 80000.0),
                                                        line("pt", "property tax", pt)]), "Budget")
            t = time.time()
            p.solve("maxBequest", options={"noRothConversions": "None", "withItemized": mode})
            out[name] = record(p, log, time.time() - t)
            r = out[name]
            print(f"{name:40s} it={r['iters']:2d} {r['conv']:32s} obj={r.get('obj')} "
                  f"fed={r.get('fed_item_yrs')} st={r.get('st_item_yrs')} {r.get('resid_worst')}", flush=True)


def run_ls(out):
    """NY + mortgage, maxBequest, local search: none / federal only / federal + NY."""
    for yob in (2032, 2099):
        for mode in ("none", "fed-only", "loop"):
            name = f"NYmort {yob} maxBequest LS {mode}"
            log = io.StringIO()
            p = couple("NY", "Yonkers", 600000.0, yob, log)
            opts = {"noRothConversions": "None", "breakpointMethod": "local-search",
                    "withItemized": "none" if mode == "none" else "loop"}
            t = time.time()
            if mode == "fed-only":
                with patch.object(type(p), "_st_item_candidate_years", lambda self: []):
                    p.solve("maxBequest", options=opts)
            else:
                p.solve("maxBequest", options=opts)
            out[name] = record(p, log, time.time() - t)
            r = out[name]
            print(f"{name:40s} obj={r.get('obj')} {r.get('resid_worst')} {r['time']}s", flush=True)


def run_examples(out):
    import glob
    from pathlib import Path
    for path in sorted(glob.glob("examples/Case_*.toml")):
        for mode in ("none", "loop"):
            log = io.StringIO()
            p = owl.readConfig(path, verbose=True, logstreams=[log])
            opts = dict(p.solverOptions)
            opts["withItemized"] = mode
            t = time.time()
            p.solve(p.objective, opts)
            name = f"{Path(path).stem} {mode}"
            out[name] = record(p, log, time.time() - t)
            r = out[name]
            print(f"{name:34s} it={r['iters']:2d} {r['conv']:32s} mono={r.get('monotonic')} "
                  f"obj={r.get('obj')} fed={r.get('fed_item_yrs')} st={r.get('st_item_yrs')} "
                  f"{r.get('resid_worst')}", flush=True)


if __name__ == "__main__":
    out_path = sys.argv[1]
    groups = sys.argv[2].split(",") if len(sys.argv) > 2 else ["probe", "nyattr", "ptsweep", "ls", "examples"]
    try:
        out = json.load(open(out_path))
    except (OSError, ValueError):
        out = {}
    runs = {"probe": run_probe, "nyattr": run_nyattr, "ptsweep": run_ptsweep, "ls": run_ls, "examples": run_examples}
    for grp in groups:
        runs[grp](out)
        json.dump(out, open(out_path, "w"), indent=1)

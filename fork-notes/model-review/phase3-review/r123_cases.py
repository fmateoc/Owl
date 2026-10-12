"""R1-R3 before/after: the cases the review measured, with the date frozen at 2026-10-11.

Usage: r123_cases.py OUT.json [group,...]   groups: probe, probels, med, nynj, housing, examples
Run once on the code before the change and once after; compare the JSON files.
"""
import datetime
import io
import json
import sys
import time
from unittest.mock import patch

_REAL = datetime.date


class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 11)


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
EXACT = {"noRothConversions": "None", "withMedicare": "None", "withSSTaxability": 0.85}
LS = {"noRothConversions": "None", "breakpointMethod": "local-search"}
LOOP = {"noRothConversions": "None"}


def line(n, t, a):
    return {"active": True, "name": n, "type": t, "year": THISYEAR, "end": 0, "amount": a, "rate": 0.0,
            "survivor": np.nan}


def couple(state, loc, lines, mortgage=None, taxable=(150, 150), yob=2099):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "r123", verbose=False,
                 logstreams=[io.StringIO()])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=list(taxable), taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.houseLists["Budget"] = cond(pd.DataFrame(lines), "Budget")
    if mortgage:
        p.houseLists["Debts"] = cond(pd.DataFrame([{"active": True, "name": "m", "type": "mortgage",
                                                   "year": THISYEAR, "term": 30, "amount": mortgage,
                                                   "rate": 6.5}]), "Debts")
        p.Lambda_in[0, 0] = mortgage
    p.setStateTax(state, locality=loc)
    p.setExpirationYearOBBBA(yob)
    return p


def record(p, dt):
    if p.caseStatus != "solved":
        return {"status": p.caseStatus}
    g = p.gamma_n[:-1]
    bins = {k: int(v.size) for k, v in p.vm._blocks.items() if v.start >= p.vm.nconts and v.size}
    obj = float(p.basis) if p.objective == "maxSpending" else float(_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n])
    return {"status": "solved", "obj": round(obj, 2), "time": round(dt, 1), "bins": bins,
            "fed_tax": round(float(np.sum(p.T_n / g)), 0), "st_tax": round(float(np.sum(p.st_T_n / g)), 0),
            "fed_item_yrs": int(np.count_nonzero(getattr(p, "itemizing_n", []))),
            "st_item_yrs": int(np.count_nonzero(getattr(p, "st_itemizing_n", []))),
            "st_item": round(float(np.sum(getattr(p, "st_item_n", np.zeros(p.N_n)) / g)), 0),
            "st_med": round(float(np.sum(getattr(p, "st_med_n", np.zeros(p.N_n)) / g)), 0),
            "conv": p.convergenceType, "method": getattr(p, "breakpointMethodUsed", "")}


def solve(p, objective, opts):
    t = time.time()
    p.solve(objective, options=opts)
    return record(p, time.time() - t)


PT = [line("core", "core", 80000.0), line("pt", "property tax", 25000.0)]
MED = PT + [line("med", "medical", 3000.0)]
CASES = {
    "probe": [(f"{s}{'mort' if m else ''} {mode}", s, loc, PT, m, "maxBequest", dict(EXACT, withItemized=mode))
              for s, loc in (("NY", "Yonkers"), ("NJ", "")) for m in (None, 600000.0) for mode in ("none", "loop")],
    "probels": [(f"{s}{'mort' if m else ''} LS", s, loc, PT, m, "maxBequest", dict(LS))
                for s, loc in (("NY", "Yonkers"), ("NJ", "")) for m in (None, 600000.0)],
    "med": [(f"NY med3k maxSpending {b}", "NY", "Yonkers", MED, None, "maxSpending", dict(o, bequest=0))
            for b, o in (("exact", EXACT), ("loop", LOOP))]
           + [("NJ med3k maxSpending loop", "NJ", "", MED, None, "maxSpending", dict(LOOP, bequest=0)),
              ("NY med3k maxBequest LS", "NY", "Yonkers", MED, None, "maxBequest", dict(LS))],
    "nynj": [(f"{s} pt{pt // 1000}k {m}", s, loc, [line("core", "core", 80000.0), line("pt", "property tax", float(pt))],
              None, "maxBequest", o)
             for pt in (20000, 25000) for s, loc in (("NY", "Yonkers"), ("NJ", "")) for m, o in (("exact", EXACT), ("LS", LS))],
}


def run_examples(out):
    import glob
    from pathlib import Path
    for path in sorted(glob.glob("examples/Case_*.toml")):
        p = owl.readConfig(path, verbose=False, logstreams=[io.StringIO()])
        t = time.time()
        p.solve(p.objective, dict(p.solverOptions))
        out[Path(path).stem] = record(p, time.time() - t)
        print(Path(path).stem, out[Path(path).stem].get("obj"), flush=True)


if __name__ == "__main__":
    out_path = sys.argv[1]
    groups = sys.argv[2].split(",") if len(sys.argv) > 2 else list(CASES) + ["examples"]
    try:
        out = json.load(open(out_path))
    except (OSError, ValueError):
        out = {}
    for grp in groups:
        if grp == "examples":
            run_examples(out)
        else:
            for name, s, loc, lines, m, objective, opts in CASES[grp]:
                out[name] = solve(couple(s, loc, lines, mortgage=m), objective, opts)
                print(name, out[name].get("obj"), out[name].get("time"), out[name].get("bins"), flush=True)
        json.dump(out, open(out_path, "w"), indent=1)


def compare(before_path, after_path):
    """Print the before/after table of two JSON files written by this script."""
    b, a = json.load(open(before_path)), json.load(open(after_path))
    for k, x in b.items():
        y = a.get(k, {})
        if x.get("status") != "solved" or y.get("status") != "solved":
            print(k, x.get("status"), y.get("status"))
            continue
        d = y["obj"] - x["obj"]
        print(f"{k:32s} {x['obj']:>14,.2f} {y['obj']:>14,.2f} {d:>+10,.2f} {100 * d / max(abs(x['obj']), 1):>+8.4f}%"
              f" {x['time']:>6.1f}s {y['time']:>6.1f}s")

"""
Phase 5 plan review (2026-10-22, after upstream dev 37afa2a): which method should pick claiming ages
in the step-6 sweep?

Upstream's withSSAges solves the plan at every open claiming month (up to 97 per searched person,
each spouse in turn until neither moves), in the case's own tax modes. Step 4 measured the loop at
about 0.6 s per solve, local search about 120 s and the exact LP (withMedicare="none",
withSSTaxability=0.85) about 0.2 s, so a local-search age search is out of reach for a sweep. This
probe asks whether the cheap searches pick ages that local search also ranks best:

1. chris+pat, withEarningsTest on, Pat searched (withSSAges=["Pat"]), under the loop and under the
   exact LP: the pick and the wall time of each search.
2. Local search at fixed ages: both picks, and Pat's whole-year ages 62-70 around them, so the
   ranking local search gives is visible.

Run from the repository root (today's date):

    .venv/bin/python fork-notes/phase5/et_plan_review_probe.py

Output: `et_plan_review_probe_YYYY-MM-DD.txt` beside this script (written by the caller with tee).
"""

import io
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import owlplanner as owl  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
EXACT = {"withMedicare": "none", "withSSTaxability": 0.85}
LS = {"breakpointMethod": "local-search"}


def plan():
    p = owl.readConfig(os.path.join(EX, "Case_chris+pat.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, "HFP_chris+pat.xlsx"))
    return p


def value(p):
    return float(p.basis) if p.objective == "maxSpending" else float(p.bequest)


def search(extra):
    p = plan()
    t0 = time.time()
    p.solve(p.objective, dict(p.solverOptions or {}, withEarningsTest=True, withSSAges=["Pat"], **extra))
    assert p.caseStatus == "solved", extra
    return list(p.ssecAges), time.time() - t0


def fixed(ages, extra):
    p = plan()
    p.setSocialSecurity(list(p.ssecAmounts), list(ages))
    t0 = time.time()
    p.solve(p.objective, dict(p.solverOptions or {}, withEarningsTest=True, **extra))
    assert p.caseStatus == "solved", (ages, extra)
    return value(p), time.time() - t0


def ym(age):
    m = int(round(age * 12))
    return f"{m // 12}y{m % 12}m"


def main():
    print(f"et_plan_review_probe.py, {date.today().isoformat()}, owlplanner from {owl.__file__}")
    print("chris+pat, withEarningsTest on, Pat searched; basis in today's $")
    picks = {}
    for name, extra in (("loop", {}), ("exact LP", EXACT)):
        ages, dt = search(extra)
        picks[name] = ages
        print(f"  search under {name:<9}: Chris {ym(ages[0])} / Pat {ym(ages[1])}  ({dt:6.1f}s for the search)")
    chris = picks["loop"][0]
    pats = sorted({round(a * 12) for a in [picks["loop"][1], picks["exact LP"][1]] + list(range(62, 71))})
    print()
    print(f"Local search at fixed ages (Chris {ym(chris)}):")
    rows = []
    for m in pats:
        pat = max(m / 12, 62 + 1 / 12)
        v, dt = fixed([chris, pat], LS)
        tag = " <- loop pick" if abs(pat - picks["loop"][1]) < 1e-9 else ""
        tag += " <- exact-LP pick" if abs(pat - picks["exact LP"][1]) < 1e-9 else ""
        rows.append((v, pat))
        print(f"  Pat {ym(pat):>7}: {v:>12,.2f}  ({dt:5.1f}s){tag}")
    best = max(rows)
    print(f"  best under local search among these: Pat {ym(best[1])} at {best[0]:,.2f}")


if __name__ == "__main__":
    main()

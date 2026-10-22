"""
Cross-check of et_issue_measure.py's pick difference (chris+pat, withItemized="none", test on):
Pat 62y6m (the pick without the test, also stock dev's) against 63y2m (the pick with the test),
Chris 70y0m, solved at fixed ages under local search and the exact LP (withMedicare="none",
withSSTaxability=0.85; no ACA in this case, so the CLAUDE.md rule applies). Today's date.

    .venv/bin/python fork-notes/phase5/et_issue_crosscheck.py

Output: `et_issue_crosscheck_YYYY-MM-DD.txt` beside this script (written by the caller with tee).
"""

import io
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import owlplanner as owl  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
METHODS = {
    "loop": {},
    "local search": {"breakpointMethod": "local-search"},
    "exact LP": {"withMedicare": "none", "withSSTaxability": 0.85},
}


def solve(pat, extra):
    p = owl.readConfig(os.path.join(EX, "Case_chris+pat.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, "HFP_chris+pat.xlsx"))
    p.setSocialSecurity(list(p.ssecAmounts), [70.0, pat])
    p.solve(p.objective, dict(p.solverOptions or {}, withItemized="none", withEarningsTest=True, **extra))
    assert p.caseStatus == "solved"
    return float(p.basis)


def main():
    print(f"et_issue_crosscheck.py, {date.today().isoformat()}, owlplanner from {owl.__file__}")
    print("chris+pat, withItemized='none', test on, Chris 70y0m; basis in today's $")
    d = {}
    for name, extra in METHODS.items():
        t0 = time.time()
        a, b = solve(62.5, extra), solve(63 + 2 / 12, extra)
        d[name] = b - a
        print(f"  {name:<13} Pat 62y6m {a:>12,.2f}  Pat 63y2m {b:>12,.2f}  difference {b - a:>8,.2f}"
              f"  ({(time.time() - t0) / 2:5.1f}s per solve)")
    ls, lp = d["local search"], d["exact LP"]
    spread = abs(ls - lp)
    same = (ls > 0) == (lp > 0) and ls != 0 and lp != 0
    print(f"  local search vs exact LP: spread {spread:,.2f}; same sign: {same}; "
          f"resolved: {same and min(abs(ls), abs(lp)) > spread}")


if __name__ == "__main__":
    main()

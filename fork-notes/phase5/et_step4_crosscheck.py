"""
Phase 5 step 4 cross-check: are the pick changes of `et_step4_probe.py` above loop noise?

Run from the repository root (today's date):

    .venv/bin/python fork-notes/phase5/et_step4_crosscheck.py

The probe's section 3 prices the no-test pick against the test-on pick, both with the
test on, under the default self-consistent loop: about $170/yr of basis on chris+pat,
under the ~1% band where loop fixed points can reorder variants (CLAUDE.md, "Loop
noise"). Here each pair of picks is solved at fixed ages, with the test on, three ways:
the loop (the case's options), the local-search preset (`breakpointMethod="local-search"`)
and the exact LP (`withMedicare="none"`, `withSSTaxability=0.85`). The verdict is the
CLAUDE.md rule: a difference is resolved when local search and the exact LP agree in sign
and it is larger than the spread between those two. The loop is printed for reference only:
its fixed-point noise is what the rule sets aside. (The first version of this script, run
2026-10-21, also counted the loop in the spread, a stricter rule than the documented one,
and called the both-free pair unresolved; corrected in the review of step 4.)

Output: `et_step4_crosscheck_YYYY-MM-DD.txt` beside this script.
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

# (label, ages of the no-test pick, ages of the test-on pick), from et_step4_probe_2026-10-21.txt
PAIRS = [
    ("withSSAges=['Pat']", [70.0, 62 + 3 / 12], [70.0, 63.0]),
    ("withSSAges=optimize", [68 + 9 / 12, 62 + 1 / 12], [69 + 4 / 12, 63.0]),
]


def solve(ages, extra):
    p = owl.readConfig(os.path.join(EX, "Case_chris+pat.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, "HFP_chris+pat.xlsx"))
    p.setSocialSecurity(list(p.ssecAmounts), list(ages))
    p.solve(p.objective, dict(p.solverOptions or {}, withEarningsTest=True, **extra))
    assert p.caseStatus == "solved", (ages, extra)
    return float(p.basis) if p.objective == "maxSpending" else float(p.bequest)


def ym(age):
    m = int(round(age * 12))
    return f"{m // 12}y{m % 12}m"


def main():
    print(f"et_step4_crosscheck.py, {date.today().isoformat()}")
    print("chris+pat, withEarningsTest on, fixed ages; basis in today's $")
    for label, no_test, test_on in PAIRS:
        print()
        print(
            f"{label}: no-test pick Chris {ym(no_test[0])} / Pat {ym(no_test[1])}, "
            f"test-on pick Chris {ym(test_on[0])} / Pat {ym(test_on[1])}"
        )
        diffs = {}
        for name, extra in METHODS.items():
            t0 = time.time()
            a = solve(no_test, extra)
            b = solve(test_on, extra)
            diffs[name] = b - a
            print(
                f"  {name:<13} no-test pick {a:>12,.2f}  test-on pick {b:>12,.2f}  "
                f"difference {b - a:>9,.2f}  ({(time.time() - t0) / 2:5.1f}s per solve)"
            )
        ls, lp = diffs["local search"], diffs["exact LP"]
        spread = abs(ls - lp)
        same_sign = (ls > 0 and lp > 0) or (ls < 0 and lp < 0)
        resolved = same_sign and min(abs(ls), abs(lp)) > spread
        print(
            f"  local search vs exact LP: spread {spread:,.2f}; same sign: {same_sign}; resolved: {resolved}"
            f"  (loop {diffs['loop']:,.2f}, not part of the verdict)"
        )


if __name__ == "__main__":
    main()

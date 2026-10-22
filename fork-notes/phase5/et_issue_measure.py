"""
Numbers for the step-9 issue (fork-notes/issue-earnings-test.md), measured in the fork with its own
additions off where they could apply (withItemized="none"), so the plan differs from stock upstream
by the earnings test only. chris+pat (FL, no budget, no debts) and alex+jamie (CO), today's date:

1. Pat searched (withSSAges=["Pat"]), test off and on: the pick, and with the test the withholding
   and ARF months. The test-off pick is checked against stock dev's (issue-earnings-test-repro).
2. The test-off pick solved at fixed ages with the test on: what following it costs.
3. alex+jamie at the case's fixed ages (Jamie collecting since 2023, $80k wages 2026-2027): basis,
   withheld and ARF months, test off and on.

Run from the repository root:

    .venv/bin/python fork-notes/phase5/et_issue_measure.py

Output: `et_issue_measure_YYYY-MM-DD.txt` beside this script (written by the caller with tee).
"""

import io
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import owlplanner as owl  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
BASE = {"withItemized": "none"}


def load(case):
    p = owl.readConfig(os.path.join(EX, f"Case_{case}.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, f"HFP_{case}.xlsx"))
    return p


def run(case, extra, ages=None):
    p = load(case)
    if ages is not None:
        p.setSocialSecurity(list(p.ssecAmounts), list(ages))
    t0 = time.time()
    p.solve(p.objective, dict(p.solverOptions or {}, **BASE, **extra))
    assert p.caseStatus == "solved", (case, extra)
    return p, time.time() - t0


def ym(age):
    m = int(round(age * 12))
    return f"{m // 12}y{m % 12}m"


def show(label, p, dt):
    wh = float(p.ss_withheld_in.sum()) if getattr(p, "ss_withheld_in", None) is not None else 0.0
    arf = list(getattr(p, "ss_arf_months_i", [0] * p.N_i))
    ages = " / ".join(f"{n} {ym(a)}" for n, a in zip(p.inames, p.ssecAges, strict=True))
    print(f"  {label:<26} {ages:<26} basis {float(p.basis):>12,.2f}  withheld {wh:>9,.0f} nominal"
          f"  ARF months {arf}  ({dt:5.1f}s)")


def main():
    print(f"et_issue_measure.py, {date.today().isoformat()}, owlplanner from {owl.__file__}")
    print("withItemized='none'; basis in today's $")
    print("\nchris+pat, withSSAges=['Pat']")
    off, dt = run("chris+pat", {"withSSAges": ["Pat"]})
    show("test off", off, dt)
    on, dt = run("chris+pat", {"withSSAges": ["Pat"], "withEarningsTest": True})
    show("test on", on, dt)
    follow, dt = run("chris+pat", {"withEarningsTest": True}, ages=off.ssecAges)
    show("test-off pick, test on", follow, dt)
    print(f"  cost of following the test-off pick: {float(on.basis) - float(follow.basis):,.2f}/yr of basis")
    print("\nalex+jamie, case's ages")
    for label, extra in (("test off", {}), ("test on", {"withEarningsTest": True})):
        p, dt = run("alex+jamie", extra)
        show(label, p, dt)


if __name__ == "__main__":
    main()

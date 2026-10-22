"""
Phase 5 plan review (2026-10-22): cost and effect of an ACA-exact reference for step 6.

The CLAUDE.md "exact LP" (withMedicare="none", withSSTaxability=0.85) leaves ACA in the loop.
chris+pat has no benchmark premium, so step 4 never met that. Here chris+pat gets one:
slcsp_annual = 20 ($k/yr, a stand-in value, not a quote) from 2029, the year after Pat's last
work year (Chris is on Medicare from January 2028). With withEarningsTest on, at fixed ages
(Chris 70y0m, Pat 63y0m), solve four ways and print basis, lifetime ACA cost and time:

- loop (the case's options);
- exact LP (ACA in the loop);
- exact LP + withACA="optimize" (ACA bracket binaries in the ACA years, branch-and-bound);
- local search preset (sets withACA="optimize" itself when an SLCSP is set).

Then time a Pat age search (withSSAges=["Pat"]) under the exact LP + withACA="optimize".

Run from the repository root (today's date):

    .venv/bin/python fork-notes/phase5/et_aca_reference_probe.py

Output: `et_aca_reference_probe_YYYY-MM-DD.txt` beside this script (written by the caller with tee).
"""

import io
import os
import sys
import time
from datetime import date

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import owlplanner as owl  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
EXACT = {"withMedicare": "none", "withSSTaxability": 0.85}
METHODS = {
    "loop": {},
    "exact LP (ACA loop)": EXACT,
    "exact LP + ACA optimize": dict(EXACT, withACA="optimize"),
    "local search": {"breakpointMethod": "local-search"},
}


def plan():
    p = owl.readConfig(os.path.join(EX, "Case_chris+pat.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, "HFP_chris+pat.xlsx"))
    p.setACA(20, start_year=2029)
    return p


def value(p):
    return float(p.basis) if p.objective == "maxSpending" else float(p.bequest)


def ym(age):
    m = int(round(age * 12))
    return f"{m // 12}y{m % 12}m"


def main():
    print(f"et_aca_reference_probe.py, {date.today().isoformat()}, owlplanner from {owl.__file__}")
    print("chris+pat + slcsp_annual 20 ($k) from 2029, withEarningsTest on; basis and ACA in today's $")
    for name, extra in METHODS.items():
        p = plan()
        p.setSocialSecurity(list(p.ssecAmounts), [70.0, 63.0])
        t0 = time.time()
        p.solve(p.objective, dict(p.solverOptions or {}, withEarningsTest=True, **extra))
        dt = time.time() - t0
        if p.caseStatus != "solved":
            print(f"  {name:<24} {p.caseStatus}  ({dt:6.1f}s)")
            continue
        aca = float(np.sum(p.aca_costs_n / p.gamma_n[: p.N_n]))
        print(f"  {name:<24} basis {value(p):>12,.2f}  lifetime ACA {aca:>9,.0f}  ({dt:6.1f}s)")
    p = plan()
    t0 = time.time()
    p.solve(p.objective, dict(p.solverOptions or {}, withEarningsTest=True, withSSAges=["Pat"], **METHODS[
        "exact LP + ACA optimize"]))
    print(f"\nPat age search under exact LP + ACA optimize: {p.caseStatus}, Pat {ym(p.ssecAges[1])}, "
          f"basis {value(p):,.2f}  ({time.time() - t0:.1f}s for the search)")


if __name__ == "__main__":
    main()

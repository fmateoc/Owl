"""
Phase 5 plan review (2026-10-22): does local search miss the ACA cliff move on chris+pat?

et_aca_reference_probe.py found, at fixed ages (Chris 70y0m, Pat 63y0m), withEarningsTest on and
slcsp_annual 20 ($k) from 2029: local search pays $19,906 of lifetime ACA, while the exact LP with
withACA="optimize" pays $1,203. The exact LP is another model (no Medicare, SS at 85%), so this
compares like with like: the case's own model with only ACA exact, by branch-and-bound
(withACA="optimize", the other families in the loop), against the loop and local search; plus
the local search's ACA per year and MAGI against 400% FPL.

Run from the repository root (today's date):

    .venv/bin/python fork-notes/phase5/et_aca_ls_check.py

Output: `et_aca_ls_check_YYYY-MM-DD.txt` beside this script (written by the caller with tee).
"""

import io
import os
import sys
import time
from datetime import date

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import owlplanner as owl  # noqa: E402
from owlplanner import tax_federal as tx  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
METHODS = {
    "loop": {},
    "ACA optimize only (B&B)": {"withACA": "optimize"},
    "local search": {"breakpointMethod": "local-search"},
}


def solve(extra):
    p = owl.readConfig(os.path.join(EX, "Case_chris+pat.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, "HFP_chris+pat.xlsx"))
    p.setACA(20, start_year=2029)
    p.setSocialSecurity(list(p.ssecAmounts), [70.0, 63.0])
    t0 = time.time()
    p.solve(p.objective, dict(p.solverOptions or {}, withEarningsTest=True, **extra))
    return p, time.time() - t0


def main():
    print(f"et_aca_ls_check.py, {date.today().isoformat()}, owlplanner from {owl.__file__}")
    print("chris+pat + slcsp_annual 20 ($k) from 2029, ages 70y0m / 63y0m, withEarningsTest on; today's $")
    for name, extra in METHODS.items():
        p, dt = solve(extra)
        if p.caseStatus != "solved":
            print(f"  {name:<24} {p.caseStatus} ({dt:.1f}s)")
            continue
        g = p.gamma_n[: p.N_n]
        aca = p.aca_costs_n / g
        yrs = [n for n in range(p.N_n) if aca[n] > 0.5 or 2029 <= p.year_n[n] <= 2031]
        print(f"  {name:<24} basis {float(p.basis):>12,.2f}  lifetime ACA {float(np.sum(aca)):>9,.0f}  ({dt:6.1f}s)")
        for n in yrs:
            y = int(p.year_n[n])
            cliff = 4 * tx._aca_fpl(y, 2 if n < p.n_d else 1, p.gamma_n, int(p.year_n[0])) / g[n]
            print(f"      {y}: ACA {aca[n]:>8,.0f}  ACA MAGI {p.MAGI_aca_n[n] / g[n]:>10,.0f}  400% FPL {cliff:>9,.0f}")


if __name__ == "__main__":
    main()

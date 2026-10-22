"""
Repro for the earnings-test design issue (fork-notes/issue-earnings-test.md), on stock upstream dev.

1. Which shipped examples pay Social Security before FRA in a year with wages above the 2026
   annual exempt amount ($24,480, POMS RS 02501.025 D): the year, the wages, the benefit Owl pays
   (today's $) and (wages - 24,480)/2, a first-order size of what SSA would withhold.
2. chris+pat and jack+jill with withSSAges on the spouse who works: the claiming age Owl picks.

Run from the root of a stock upstream checkout (today's date):

    python issue-earnings-test-repro.py
"""

import glob
import io
import os
import time

import owlplanner as owl
from owlplanner import socialsecurity as socsec

EXEMPT_2026 = 24480


def load(path):
    p = owl.readConfig(path, verbose=False, logstreams=[io.StringIO()], loadHFP=True)
    return p


def ym(age):
    m = int(round(age * 12))
    return f"{m // 12}y{m % 12}m"


def main():
    print(f"owlplanner {owl.__version__} from {os.path.dirname(owl.__file__)}")
    print("\n1. SS paid before FRA in a year with wages above $24,480")
    for f in sorted(glob.glob("examples/Case_*.toml")):
        p = load(f)
        fras = socsec.getFRAs(p.yobs, p.mobs, p.tobs)
        y0 = int(p.year_n[0])
        for i in range(p.N_i):
            if p.ssecAmounts[i] == 0:
                continue
            claim = p.yobs[i] + (p.mobs[i] - 1) / 12 + p.ssecAges[i]
            fra = p.yobs[i] + (p.mobs[i] - 1) / 12 + fras[i]
            for n in range(p.N_n):
                w = float(p.omega_in[i, n])
                if w > EXEMPT_2026 and y0 + n + 1 > claim and y0 + n < fra:
                    print(f"  {os.path.basename(f):<26} {p.inames[i]:<6} claims at {ym(p.ssecAges[i])}  {y0 + n}  "
                          f"wages {w:>8,.0f}  SS paid {float(p.zeta_in[i, n]):>7,.0f}  "
                          f"(wages - 24,480)/2 {(w - EXEMPT_2026) / 2:>7,.0f}")
    print("\n2. withSSAges on the spouse who works")
    for case, who in (("chris+pat", "Pat"), ("jack+jill", "Jill")):
        p = load(f"examples/Case_{case}.toml")
        t0 = time.time()
        p.solve(p.objective, dict(p.solverOptions or {}, withSSAges=[who]))
        i = p.inames.index(who)
        print(f"  {case}: {who} claims at {ym(p.ssecAges[i])} ({p.caseStatus}, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()

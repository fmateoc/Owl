"""Repro for the draft issue `issue-ls-ltcg.md`: local search stops short when the LTCG family is
searched, on the shipped example Case_john+sally.toml.

Plain Python on stock Owl. Run from the root of an Owl checkout:
    python issue-ls-ltcg-repro.py [path/to/Case_john+sally.toml]
The date is frozen at 2026-10-15 so that the numbers do not move from one day to the next.
"""
import datetime
import io
import sys
import time
from unittest.mock import patch

import numpy as np

_REAL = datetime.date


class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)


import owlplanner as owl  # noqa: E402
from owlplanner import tax_federal as tx  # noqa: E402
from owlplanner.export import _compute_estate  # noqa: E402

for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()

CASE = sys.argv[1] if len(sys.argv) > 1 else "examples/Case_john+sally.toml"


def run(label, **extra):
    p = owl.readConfig(CASE, verbose=False, logstreams=[io.StringIO()])  # log kept out of the output
    opts = dict(p.solverOptions)
    opts.update(extra)
    t = time.time()
    p.solve(p.objective, opts)
    dt = time.time() - t
    bequest = _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
    print(f"  {label:44s} {bequest:>9,.0f}  {dt:5.1f} s  {p.breakpointMethodUsed}")
    return p


print(f"Owl {owl.__version__}; {CASE}; bequest in today's $")
print("1. Presets")
ls = run('breakpointMethod="local-search"', breakpointMethod="local-search")
bb = run('breakpointMethod="branch-and-bound"', breakpointMethod="branch-and-bound")

print('2. Local search on some families only ("optimize"; the rest on the loop)')
fam = dict(withSSTaxability="optimize", withMedicare="optimize", mipStrategy="local-search")
run("SS + IRMAA", **fam)
run("SS + IRMAA + NIIT", **fam, withNIIT="optimize")
run("SS + IRMAA + senior bonus", **fam, withSeniorBonus="optimize")
run("SS + IRMAA + LTCG", **fam, withLTCG="optimize")
run("SS + IRMAA + LTCG, branch-and-bound", withSSTaxability="optimize", withMedicare="optimize",
    withLTCG="optimize")

print("3. Ordinary taxable income G_n against the LTCG 0% threshold T15 (today's $), and taxable SS")
print("   year |   local search: G_n    taxable SS |  branch-and-bound: G_n  taxable SS")
for n, year in enumerate(ls.year_n[:14]):
    status = 0 if (ls.N_i == 2 and n >= ls.n_d) else ls.N_i - 1
    t15 = tx.capGainRates[status][0]
    cells = []
    for p in (ls, bb):
        g = p.gamma_n[n]
        ss = np.sum(p.zetaBar_in[:, n]) * p.Psi_n[n] / g
        side = "above" if p.G_n[n] / g > t15 + 1 else "below"
        cells.append(f"{p.G_n[n] / g:>10,.0f} {side} {ss:>9,.0f}")
    print(f"   {year} | {cells[0]} | {cells[1]}   (T15 {t15:,.0f})")

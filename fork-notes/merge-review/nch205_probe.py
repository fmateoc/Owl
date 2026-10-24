"""#205 guard in non-itemizer charity years: probe (2026-10-24).

The fork's _ltcg_deduction_widens_n() keeps the gains brackets unwidened in years with a
non-itemizer charity deduction, as in itemized years. Such years can have ordinary income below
the deduction (retired, SS deferred, living on a taxable account), where #205 matters most.
Couple born 1964, SS at 70, $4M taxable, $100k tax-deferred (third case: $1.2M taxable, none
tax-deferred, $60k core spending), FL (no state tax), a $3,000 charity
budget line (standard deduction + Schedule 1-A charity). For each withLTCG mode: withItemized
"none" (upstream's #205 rows), "loop" with the guard, "loop" with the guard off.
Run inside pytest's frozen date:
.venv/bin/python -m pytest fork-notes/merge-review/nch205_probe.py -s -q -p no:cacheprovider
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tests", "tax"))
import owlplanner  # noqa: E402
from owlplanner.plan import Plan  # noqa: E402
from test_itemized import _plan, _solve  # noqa: E402


def _case(mortgage=None, property_tax=0.0, deferred=(50, 50), taxable=(2000, 2000), core=90000.0):
    return _plan(state="", property_tax=property_tax, core=core, charity=3000.0, mortgage=mortgage,
                 taxable=taxable, deferred=deferred)


def _report(p, label):
    Nn = p.N_n
    bequest = owlplanner.export._compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
    narrow = ~p._ltcg_deduction_widens_n()
    low = narrow & (p.G_n[:Nn] < 1)
    print(f"{label}: bequest today {bequest:,.0f}; LTCG tax {np.sum(p.U_n):,.0f} "
          f"(years unwidened {int(narrow.sum())}, of them G_n = 0: {int(low.sum())}, "
          f"LTCG tax there {np.sum(p.U_n[low]):,.0f})")
    for n in np.flatnonzero(low)[:2]:
        print(f"  {p.year_n[n]}: G {p.G_n[n]:8,.0f} e {p.e_n[n]:8,.0f} sigma {p.sigmaBar_n[n]:8,.0f} "
              f"Q {p.Q_n[n]:9,.0f} LTCG tax {p.U_n[n]:7,.0f}")


def test_probe(monkeypatch):
    print("\nowlplanner from", owlplanner.__file__)
    cases = (("charity only", {}), ("mortgage", {"mortgage": (400_000.0, 6.5, 30), "property_tax": 12000.0}),
             ("no tax-deferred", {"deferred": (0, 0), "taxable": (600, 600), "core": 60000.0}))
    for case, kw in cases:
        for mode in ("optimize", "loop"):
            _report(_solve(_case(**kw), withLTCG=mode, withItemized="none"), f"[{case}] withLTCG={mode} none        ")
            _report(_solve(_case(**kw), withLTCG=mode, withItemized="loop"), f"[{case}] withLTCG={mode} loop guard  ")
            with monkeypatch.context() as m:
                m.setattr(Plan, "_ltcg_deduction_widens_n", lambda self: np.ones(self.N_n, dtype=bool))
                _report(_solve(_case(**kw), withLTCG=mode, withItemized="loop"),
                        f"[{case}] withLTCG={mode} loop no guard")

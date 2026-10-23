"""Upstream #205 (e3592e7) against the fork's itemized deduction: probe (2026-10-23).

Upstream widens the 0%/15% gains brackets by sigma_n - e_n, with sigma_n the standard deduction.
In the fork, e_n can exceed sigma_n (itemized years, non-itemizer charity). Mortgage couple with
pensions (ordinary income above the deduction) and a taxable account; for each withLTCG mode,
the plan's LTCG tax against the QDCG worksheet at the deduction the plan took (taxable income =
G_n + gains, since ordinary income fills the deduction), with the fork's guard and with upstream's
rows in every year (the guard switched off). Run inside pytest's frozen date:
.venv/bin/python -m pytest fork-notes/phase5/merge205_itemized_probe.py -s -q -p no:cacheprovider
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tests", "tax"))
import owlplanner  # noqa: E402
from owlplanner import tax_federal as tx  # noqa: E402
from owlplanner.plan import Plan  # noqa: E402
from test_itemized import _plan, _solve  # noqa: E402


def _report(p, label):
    Nn = p.N_n
    gains = np.maximum(p.Q_n, 0)
    taxable = np.maximum(0, p.G_n + gains)
    owed = tx.capitalGainTax(p.N_i, taxable, np.minimum(gains, taxable), p.gamma_n[:Nn], p.n_d, Nn)
    bequest = owlplanner.export._compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
    item = p.e_n > p.sigmaBar_n[:Nn] + 1
    print(f"{label}: bequest today {bequest:,.0f}; LTCG tax paid {np.sum(p.U_n):,.0f}, worksheet "
          f"{np.sum(owed):,.0f}; in years e > sigma: paid {np.sum(p.U_n[item]):,.0f}, "
          f"worksheet {np.sum(owed[item]):,.0f} ({int(item.sum())} years)")
    for n in np.flatnonzero(item)[:3]:
        print(f"  {p.year_n[n]}: G {p.G_n[n]:9,.0f} e {p.e_n[n]:8,.0f} sigma {p.sigmaBar_n[n]:8,.0f} "
              f"Q {gains[n]:9,.0f} paid {p.U_n[n]:7,.0f} worksheet {owed[n]:7,.0f}")


def _case():
    p = _plan(state="", property_tax=12000.0, core=110000.0, mortgage=(500_000.0, 6.5, 30),
              taxable=(900, 900), deferred=(100, 100))
    p.setPension([3000, 2500], [62, 62])
    return p


def test_probe(monkeypatch):
    print("\nowlplanner from", owlplanner.__file__)
    for guard in (True, False):
        if not guard:
            monkeypatch.setattr(Plan, "_ltcg_deduction_widens_n", lambda self: np.ones(self.N_n, dtype=bool))
        for mode in ("optimize", "loop"):
            p = _solve(_case(), withLTCG=mode, withItemized="loop")
            _report(p, f"guard {'on ' if guard else 'off'} withLTCG={mode}")

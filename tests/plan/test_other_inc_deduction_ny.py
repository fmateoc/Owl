"""
Fork: upstream's #225 deduction (a negative "other inc", e.g. an HSA contribution made without
wages) through the fork's NY rows: the state base, the Yonkers surcharge and the NYC tax.

Upstream tests the deduction in PA and CA (tests/assets/test_hsa.py); the fork's NY base (pension
exclusion, NY standard deduction) and its local taxes are not upstream's. A 60-year-old whose only
income is a fixed $30,000 Roth conversion: without the deduction NY taxes a small base, with a
$5,400 deduction the NY base goes below zero, so state and local tax are nil (the lost part of the
deduction is the `dl` column), and the federal AGI drops by the full amount.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import io

import pandas as pd
import pytest

from owlplanner import Plan


def _ny_retiree(rows, locality, options):
    p = Plan(["A"], ["1966-07-01"], [62], "NY HSA retiree", verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("flat")
    p.setAccountBalances(taxable=[0], taxDeferred=[30], taxFree=[300], startDate="01-01")
    p.setAllocationRatios("individual", generic=[[[100, 0, 0, 0], [100, 0, 0, 0]]])
    p.setRates("user", values=[6, 4, 4, 2.5])
    p.setDividendRate(0)
    p.setStateTax("NY", locality=locality)
    base = {"year": int(p.year_n[0]), "Roth conv": 30_000, "Roth conv fixed": True}
    p.readHFP({"A": pd.DataFrame([{**base, **rows}])})
    p.solve("maxSpending", {"bequest": 0, "withMedicare": "None", **options})
    assert p.caseStatus == "solved", p.caseStatus
    return p


@pytest.mark.parametrize("options", [{}, {"breakpointMethod": "branch-and-bound"}], ids=["loop", "optimize"])
@pytest.mark.parametrize("locality", ["", "Yonkers", "NYC"])
def test_negative_other_inc_in_the_ny_rows(locality, options):
    base = _ny_retiree({}, locality, options)
    hsa = _ny_retiree({"HSA ctrb": 5400, "other inc": -5400}, locality, options)
    assert hsa.MAGI_n[0] == pytest.approx(base.MAGI_n[0] - 5400, abs=1)
    assert hsa.T_n[0] < base.T_n[0]
    assert base.st_T_n[0] > 0
    assert hsa.st_T_n[0] == pytest.approx(0, abs=0.01)
    if locality:
        assert base.lt_T_n[0] > 0
        assert hsa.lt_T_n[0] == pytest.approx(0, abs=0.01)

"""
The employee payroll tax is part of the model (fork, 2026-10-24; it was an opt-in switch,
decision D3 of Phase 5):

- every solve charges it on the earnings the plan holds (the SSA earnings test's derived
  earnings), with no option;
- the Summary rows and the Cash Flow column appear for a household with earnings in the plan,
  and a household without earnings gets none.

Hand numbers as in tests/plan/test_payroll_tax.py: IRS Pub. 15 (2026), 7.65% under the
\\$184,500 wage base; jack+jill's 2026 earnings are \\$195,000 (Jack \\$100,000 + his \\$15,000
401k, Jill \\$80,000).

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
import os

import numpy as np
import pytest

import owlplanner as owl
from owlplanner.export import build_summary_dic

_EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "examples")


def _load(case):
    p = owl.readConfig(os.path.join(_EXAMPLES, f"Case_{case}.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(_EXAMPLES, f"HFP_{case}.xlsx"))
    return p


def _solve(p, **extra):
    p.solve(p.objective, dict(p.solverOptions or {}, **extra))
    assert p.caseStatus == "solved"
    return p


def test_charged_with_no_option():
    p = _load("jack+jill")
    _solve(p)
    assert p.payroll_tax_n[0] == pytest.approx(0.0765 * 195_000.0)


def test_rows_only_for_a_household_with_earnings():
    p = _solve(_load("jack+jill"))
    dic = build_summary_dic(p)
    assert sum(k.startswith("Total payroll tax paid") for k in dic) == 2

    q = _load("jack+jill")
    q.omega_in[:, :] = 0.0
    _solve(q)
    assert np.all(q.payroll_tax_n == 0)
    assert not any(k.startswith("Total payroll tax paid") for k in build_summary_dic(q))
    wb = q.saveWorkbook(saveToFile=False)
    ws = next(w for w in wb.worksheets if w.title == "Cash Flow")
    assert "payroll tax" not in [cell.value for cell in ws[1]]


def test_the_switch_attribute_is_gone():
    p = _solve(_load("jack+jill"))
    assert not hasattr(p, "_payrollTaxOn")
    assert not hasattr(p, "payroll_tax_applied")

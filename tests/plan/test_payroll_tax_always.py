"""
The employee payroll tax is part of the model (fork, 2026-10-24; was the opt-in switch
``withPayrollTax``, decision D3 of Phase 5):

- every solve charges it on the earnings the plan holds (the SSA earnings test's derived
  earnings), with no option;
- ``withPayrollTax`` in a saved case is reported as a deprecated option and changes nothing
  (the household template carried it);
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
from owlplanner.mylogging import Logger

_EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "examples")

SPEC = pytest.mark.xfail(strict=True, reason="spec: the payroll tax without an option")


def _load(case):
    p = owl.readConfig(os.path.join(_EXAMPLES, f"Case_{case}.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(_EXAMPLES, f"HFP_{case}.xlsx"))
    return p


def _solve(p, **extra):
    p.solve(p.objective, dict(p.solverOptions or {}, **extra))
    assert p.caseStatus == "solved"
    return p


@SPEC
def test_charged_with_no_option():
    p = _load("jack+jill")
    assert "withPayrollTax" not in (p.solverOptions or {})
    _solve(p)
    assert p.payroll_tax_n[0] == pytest.approx(0.0765 * 195_000.0)


@SPEC
def test_the_old_key_is_deprecated_and_changes_nothing():
    p = _load("jack+jill")
    buf = io.StringIO()
    p.mylog = Logger(verbose=False, logstreams=[buf])
    _solve(p, withPayrollTax=False)
    assert "Ignoring deprecated solver option 'withPayrollTax'" in buf.getvalue()
    assert p.payroll_tax_n[0] == pytest.approx(0.0765 * 195_000.0)


def test_a_saved_case_with_the_key_still_loads():
    # A guard (passes before and after): the key must not make a saved case fail to load.
    from owlplanner.config import load_toml
    from owlplanner.config.schema import parse_solver_options

    assert "withPayrollTax" not in parse_solver_options({}).keys()
    diconf, _, _ = load_toml(os.path.join(_EXAMPLES, "Case_joe.toml"))
    diconf["solver_options"]["withPayrollTax"] = True
    opts = parse_solver_options(diconf["solver_options"])
    assert opts["withPayrollTax"] is True  # kept as an unknown key (extra="allow"), not coerced


@SPEC
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


@SPEC
def test_the_switch_attribute_is_gone():
    p = _solve(_load("jack+jill"))
    assert not hasattr(p, "_payrollTaxOn")
    assert not hasattr(p, "payroll_tax_applied")

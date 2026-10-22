"""
Tests for the employee payroll tax on earnings (fork, Phase 5 step 5, decision D3).

``solver_options.withPayrollTax`` (off by default) charges the employee's share of the
payroll tax on each person's earnings as a cash outflow of the year:

- social security tax, 6.2% of earnings up to the wage base (\\$184,500 in 2026, held at
  that level in today's dollars afterwards, like the earnings test's exempt amounts);
- Medicare tax, 1.45% of all earnings;
- Additional Medicare Tax, 0.9% of the household's earnings above \\$250,000 while the
  couple files jointly and \\$200,000 single (not indexed).

Earnings are what the SSA earnings test reads (``Plan._earnings_test_inputs``): ``gross
earnings`` where given, else ``anticipated wages``. The tax is not deductible, so only the
cash-flow row changes: no LP column, row or binary.

Expected values are hand numbers from the primary text, not from the code under test:
IRS Pub. 15 (2026), "What's New" and section 9 (rates and the \\$184,500 wage base), and
the Instructions for Form 8959 (2025), "Threshold Amounts for Additional Medicare Tax"
(MFJ \\$250,000; single and qualifying surviving spouse \\$200,000; "aren't indexed for
inflation"); both read on irs.gov on 2026-10-18 and again on 2026-10-22.

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
from owlplanner import tax_federal as tx
from owlplanner.config import load_toml
from owlplanner.export import build_summary_dic
from owlplanner.mylogging import Logger

# Step 5 was written test-first (phase5-plan.md §5b): the spec commit marked every test
# xfail(strict=True); the implementation commit removed the marker.

# Frozen plan start (tests/conftest.py freezes the date; keep this in step with it).
THISYEAR = 2026

_EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "examples")

# Pub. 15 (2026) and the Form 8959 instructions.
SS_RATE = 0.062
MEDICARE_RATE = 0.0145
ADDL_RATE = 0.009
WAGE_BASE_2026 = 184_500.0


def _load(case):
    p = owl.readConfig(
        os.path.join(_EXAMPLES, "Case_" + case + ".toml"), verbose=False, logstreams=[io.StringIO()]
    )
    hfp = os.path.join(_EXAMPLES, "HFP_" + case + ".xlsx")
    if os.path.exists(hfp):
        p.readHFP(hfp)
    return p


def _solve(p, on, **extra):
    """Resolve the plan with the payroll tax switched on or off (D3: off by default)."""
    opts = dict(p.solverOptions or {}, **extra)
    if on:
        opts["withPayrollTax"] = True
    else:
        opts.pop("withPayrollTax", None)
    p.solverOptions = opts
    p.resolve()
    assert p.caseStatus == "solved"
    return p


def _n(p, year):
    return int(year) - int(p.year_n[0])


def _warn_log(p):
    buf = io.StringIO()
    p.mylog = Logger(verbose=False, logstreams=[buf])
    return buf


def _warn_lines(buf):
    return [line.split(" | ", 3)[-1] for line in buf.getvalue().splitlines() if "| WARNING |" in line]


# --------------------------------------------------------------------------------------
# The rule, by hand
# --------------------------------------------------------------------------------------


def test_one_person_below_and_above_the_wage_base():
    """Single filer. 2026: \\$85,000, under the base: 6.2% and 1.45% of it. 2027, after 10%
    inflation: \\$250,000 nominal, above the base, which is \\$184,500 in today's dollars,
    so \\$202,950 nominal; Medicare on all of it; 0.9% above the single threshold of
    \\$200,000, which is not indexed."""
    earnings = np.array([[85_000.0, 250_000.0, 0.0]])
    gamma = np.array([1.0, 1.1, 1.21])
    ss_in, med_in, addl_n = tx.payrollTax(earnings, gamma, n_d=3, N_n=3, thisyear=THISYEAR)
    assert ss_in[0] == pytest.approx([5_270.0, 0.062 * 202_950.0, 0.0])
    assert med_in[0] == pytest.approx([1_232.5, 3_625.0, 0.0])
    assert addl_n == pytest.approx([0.0, 450.0, 0.0])


def test_couple_then_survivor():
    """Couple filing jointly in year 0: \\$200,000 + \\$100,000. Social security tax is per
    person (the first capped at the base); the Additional Medicare Tax is on the combined
    \\$300,000 above \\$250,000. From the first death (n_d = 1) the survivor files single:
    \\$230,000, threshold \\$200,000."""
    earnings = np.array([[200_000.0, 0.0], [100_000.0, 230_000.0]])
    gamma = np.array([1.0, 1.0])
    ss_in, med_in, addl_n = tx.payrollTax(earnings, gamma, n_d=1, N_n=2, thisyear=THISYEAR)
    assert ss_in[0] == pytest.approx([11_439.0, 0.0])
    assert ss_in[1] == pytest.approx([6_200.0, 11_439.0])
    assert med_in[0] == pytest.approx([2_900.0, 0.0])
    assert med_in[1] == pytest.approx([1_450.0, 3_335.0])
    assert addl_n == pytest.approx([450.0, 270.0])


def test_two_earners_each_under_200k_still_owe_the_additional_tax():
    """Form 8959: the joint threshold applies to the combined Medicare wages, so two
    \\$150,000 earners owe 0.9% of \\$50,000 although neither employer withholds it."""
    earnings = np.array([[150_000.0], [150_000.0]])
    _, _, addl_n = tx.payrollTax(earnings, np.array([1.0]), n_d=1, N_n=1, thisyear=THISYEAR)
    assert addl_n == pytest.approx([450.0])


def test_wage_base_after_the_last_known_year():
    """A plan starting in 2030: the base stays \\$184,500 in today's dollars."""
    earnings = np.array([[300_000.0]])
    ss_in, _, _ = tx.payrollTax(earnings, np.array([1.0]), n_d=1, N_n=1, thisyear=2030)
    assert ss_in[0] == pytest.approx([SS_RATE * WAGE_BASE_2026])


# --------------------------------------------------------------------------------------
# On the plan
# --------------------------------------------------------------------------------------


def test_switch_off_is_a_no_op():
    """Off (the default): nothing is charged, no Summary row, no Cash Flow column."""
    p = _solve(_load("jack+jill"), on=False)
    assert np.all(p.payroll_tax_n == 0)
    assert p.payroll_tax_applied is False
    assert not any(k.startswith("Total payroll tax paid") for k in build_summary_dic(p))
    wb = p.saveWorkbook(saveToFile=False)
    ws = next(w for w in wb.worksheets if w.title == "Cash Flow")
    assert "payroll tax" not in [cell.value for cell in ws[1]]


def test_jack_jill_by_hand():
    """jack+jill: Jack earns \\$100,000 in 2026-2028, Jill \\$80,000 in 2026-2027 and
    \\$85,000 in 2028 (HFP, nominal). All under the base and the household under
    \\$250,000: 7.65% of the wages, nothing after 2028."""
    p = _solve(_load("jack+jill"), on=True)
    assert p.payroll_tax_applied is True
    assert p.payroll_tax_n[_n(p, 2026)] == pytest.approx(0.0765 * 180_000.0)
    assert p.payroll_tax_n[_n(p, 2027)] == pytest.approx(0.0765 * 180_000.0)
    assert p.payroll_tax_n[_n(p, 2028)] == pytest.approx(0.0765 * 185_000.0)
    assert np.all(p.payroll_tax_n[_n(p, 2029):] == 0)


def test_gross_earnings_are_taxed_where_given():
    """`gross earnings` (W-2 box 5, deferrals included) is what the tax reads where it is
    given; `anticipated wages` elsewhere."""
    p = _load("jack+jill")
    p.etEarnings_in[0, _n(p, 2026)] = 115_000.0  # Jack's \$100k plus his \$15k 401k
    _solve(p, on=True)
    assert p.payroll_tax_n[_n(p, 2026)] == pytest.approx(0.0765 * (115_000.0 + 80_000.0))
    assert p.payroll_tax_n[_n(p, 2027)] == pytest.approx(0.0765 * 180_000.0)


def test_additional_medicare_tax_on_the_plan():
    """jon+jane with Jon's 2026 wages raised to \\$300,000: his social security tax stops
    at the base, and the couple owes 0.9% of (\\$300,000 + \\$80,000 - \\$250,000)."""
    p = _load("jon+jane")
    p.omega_in[0, 0] = 300_000.0
    _solve(p, on=True)
    expected = (
        SS_RATE * WAGE_BASE_2026 + MEDICARE_RATE * 300_000.0 + 0.0765 * 80_000.0 + ADDL_RATE * 130_000.0
    )
    assert p.payroll_tax_n[0] == pytest.approx(expected)


def test_the_tax_is_paid_from_the_plan():
    """A cash outflow: the plan spends less with it (maxSpending), the cash flow still
    balances, and the Cash Flow sheet carries it so that its rows still sum to zero."""
    off = _solve(_load("jack+jill"), on=False)
    p = _load("jack+jill")
    buf = _warn_log(p)
    _solve(p, on=True)
    assert p.basis < off.basis
    assert not [w for w in _warn_lines(buf) if "Cash flow balance" in w]
    lhs = (
        p.g_n + p.s_n + p.T_n + p.st_T_n + p.U_n + p.J_n + p.m_n + p.M_n + p.aca_costs_n
        + p.debt_payments_n + p.payroll_tax_n
    )
    rhs = (
        np.sum(p.omega_in + p.other_inc_in + p.netinv_in + p.zetaBar_in + p.piBar_in + p.spiaBar_in, axis=0)
        + np.sum(p.Lambda_in, axis=0)
        + p.fixed_assets_ordinary_income_n
        + p.fixed_assets_capital_gains_n
        + p.fixed_assets_tax_free_n
        + np.sum(p.w_ijn, axis=(0, 1))
    )
    np.testing.assert_allclose(lhs, rhs, atol=1.0)

    # The Cash Flow sheet's columns sum to net spending (tests/export/test_export.py):
    # the tax is one of them, as an outflow.
    wb = p.saveWorkbook(saveToFile=False)
    ws = next(w for w in wb.worksheets if w.title == "Cash Flow")
    headers = [cell.value for cell in ws[1]]
    assert "payroll tax" in headers
    col = headers.index("payroll tax")
    values = [row[col] for row in ws.iter_rows(min_row=2, values_only=True)]
    assert values[_n(p, 2026)] < 0
    assert values[_n(p, 2029)] == 0


def test_lifetime_allocation_counts_it_as_tax():
    p = _solve(_load("jack+jill"), on=True)
    inv_g = 1.0 / p.gamma_n[: p.N_n]
    expected = float(np.sum((p.T_n + p.U_n + p.J_n + p.payroll_tax_n) * inv_g))
    assert p.lifetime_allocation()["outflows"]["taxes"] == pytest.approx(expected)
    expected_n = (p.T_n + p.U_n + p.J_n + p.payroll_tax_n) * inv_g
    assert p.annual_cashflow_mix()["outflows"]["taxes"] == pytest.approx(expected_n)


def test_a_second_solve_follows_the_switch():
    """Built at every solve: on, then off, then on again."""
    p = _load("jack+jill")
    _solve(p, on=True)
    assert np.any(p.payroll_tax_n > 0)
    _solve(p, on=False)
    assert np.all(p.payroll_tax_n == 0)
    p.omega_in[1, _n(p, 2026)] = 90_000.0
    _solve(p, on=True)
    assert p.payroll_tax_n[_n(p, 2026)] == pytest.approx(0.0765 * 190_000.0)


# --------------------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------------------


def test_summary_rows_whenever_the_tax_is_applied():
    """'Total payroll tax paid' whenever the switch is on (\\$0 included, so the UI's case
    comparison keeps the row between two variants that both apply it); the Additional
    Medicare Tax only where it is owed."""
    p = _solve(_load("jack+jill"), on=True)
    dic = build_summary_dic(p)
    rows = [k for k in dic if k.startswith("Total payroll tax paid")]
    assert len(rows) == 2
    nominal = float(dic["Total payroll tax paid (nominal)"].lstrip("$").replace(",", ""))
    assert nominal == pytest.approx(0.0765 * (180_000 * 2 + 185_000), abs=1.0)
    assert not any("Additional Medicare" in k for k in dic)

    p = _load("jack+jill")
    p.omega_in[:, :] = 0.0
    _solve(p, on=True)
    dic = build_summary_dic(p)
    assert all(dic[k] == "$0" for k in dic if k.startswith("Total payroll tax paid"))

    p = _load("jon+jane")
    p.omega_in[0, 0] = 300_000.0
    _solve(p, on=True)
    dic = build_summary_dic(p)
    assert any(k.startswith("»  Additional Medicare tax") for k in dic)


def test_plan_metrics_report_it():
    from owlplanner.export import METRICS_COLUMN_MAP, plan_metrics

    on = _solve(_load("jack+jill"), on=True)
    m = plan_metrics(on)
    assert m["payroll_tax_nominal"] == pytest.approx(0.0765 * (180_000 * 2 + 185_000))
    inv_g = 1.0 / on.gamma_n[: on.N_n]
    assert m["payroll_tax_today"] == pytest.approx(float(np.sum(on.payroll_tax_n * inv_g)))
    columns = on.summaryDf().columns
    for key in ("payroll_tax_today", "payroll_tax_nominal"):
        assert METRICS_COLUMN_MAP[key][0] in columns

    off = plan_metrics(_solve(_load("jack+jill"), on=False))
    assert off["payroll_tax_nominal"] == 0.0


# --------------------------------------------------------------------------------------
# Warnings: the fallback to `anticipated wages` leaves out payroll deferrals
# --------------------------------------------------------------------------------------


def test_fallback_warning_names_the_years_with_deferrals():
    """Jack's 2026-2027 carry a \\$15,000 401k deferral and no `gross earnings`: the tax
    reads \\$100,000 where FICA wages are \\$115,000. Jill has no deferral: not named."""
    p = _load("jack+jill")
    buf = _warn_log(p)
    _solve(p, on=True)
    warned = [w for w in _warn_lines(buf) if "payroll tax" in w]
    assert len(warned) == 1
    assert "Jack" in warned[0]
    assert "2026" in warned[0] and "2027" in warned[0]
    assert "2028" not in warned[0]
    assert "Jill" not in warned[0]


def test_no_fallback_warning_where_gross_earnings_are_given_or_switch_off():
    p = _load("jack+jill")
    p.etEarnings_in[0, _n(p, 2026)] = 115_000.0
    p.etEarnings_in[0, _n(p, 2027)] = 115_000.0
    buf = _warn_log(p)
    _solve(p, on=True)
    assert p.payroll_tax_applied is True
    assert not [w for w in _warn_lines(buf) if "payroll tax" in w]

    p = _load("jack+jill")
    buf = _warn_log(p)
    _solve(p, on=False)
    assert not [w for w in _warn_lines(buf) if "payroll tax" in w]


def test_local_search_warns_once():
    """The local search's nested solves are one user-visible solve: one warning, and the
    tax is charged in the plan it returns."""
    p = _load("jack+jill")
    buf = _warn_log(p)
    p.solve(
        p.objective,
        dict(
            p.solverOptions or {},
            withPayrollTax=True,
            withSSTaxability="optimize",
            mipStrategy="local-search",
            localSearchTime=2,
            localSearchStepTime=1,
        ),
    )
    assert p.caseStatus == "solved"
    assert len([w for w in _warn_lines(buf) if "payroll tax" in w]) == 1
    assert p.payroll_tax_n[_n(p, 2026)] == pytest.approx(0.0765 * 180_000.0)


# --------------------------------------------------------------------------------------
# The switch: parsing and round trips
# --------------------------------------------------------------------------------------


def test_switch_spellings_match_the_schema():
    from owlplanner.config.schema import parse_solver_options

    p = _load("jack+jill")
    for value in (True, False, 0, 1, "on", "off", "yes", "no", np.True_, np.int64(0)):
        expected = bool(parse_solver_options({"withPayrollTax": value})["withPayrollTax"])
        assert p._payrollTaxOn({"withPayrollTax": value}) is expected, value
    assert p._payrollTaxOn({}) is False  # D3: opt-in
    for value in (2, 0.5, "sometimes", "loop"):
        with pytest.raises(ValueError, match="withPayrollTax"):
            p._payrollTaxOn({"withPayrollTax": value})
        with pytest.raises(ValueError, match="withPayrollTax"):
            parse_solver_options({"withPayrollTax": value})


def test_solve_refuses_a_bad_switch_value():
    p = _load("jack+jill")
    with pytest.raises(ValueError, match="withPayrollTax"):
        p.solve(p.objective, dict(p.solverOptions or {}, withPayrollTax="sometimes"))


def test_with_payroll_tax_round_trips(monkeypatch):
    """Through the case file, the UI's flat keys and the UI's run options (#156's shape:
    a setting one builder forgets is ignored by the run)."""
    import ui.sskeys as kz

    from owlplanner.config.ui_bridge import config_to_ui, ui_to_config

    diconf, _, _ = load_toml(os.path.join(_EXAMPLES, "Case_joe.toml"))
    diconf["solver_options"]["withPayrollTax"] = True
    uidic = config_to_ui(diconf)
    assert uidic["withPayrollTax"] is True
    assert ui_to_config(uidic)["solver_options"]["withPayrollTax"] is True
    monkeypatch.setattr(kz, "getCaseKey", uidic.get)
    _, run_opts = kz.getSolveParameters()
    assert run_opts["withPayrollTax"] is True

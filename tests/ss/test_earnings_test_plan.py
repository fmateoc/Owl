"""
Tests for applying the SSA earnings test to the plan (Phase 5 step 3).

Properties from phase5-plan.md §5 step 3 and §5b, on the shipped examples:

- the switch (``solver_options.withEarningsTest``, off in code, D6) off, or no earnings,
  leaves every stream exactly as it is today;
- the three examples of plan §3 that pay Social Security before FRA in a year with wages
  above the exempt amount (jack+jill and chris+pat in 2028, alex+jamie in 2026-2027) show
  the withholding, the ARF that replaces it at FRA, and taxes on the *net* benefit;
- the other fifteen are a no-op to the cent;
- a second solve after editing wages sees the new earnings;
- the outputs reach the Summary and the worksheet, ``owlcli explain`` reports both of
  them, and the solve warns (once, and only with the switch on) where the test cannot be
  right.

Expected values are hand numbers from the primary rules — 20 CFR 404.410 reduction rates
(5/9 of 1% for each of the first 36 months before FRA, 5/12 of 1% beyond) and the 2026
exempt amounts of POMS RS 02501.025 D — not from the code under test. Streams are in
today's dollars, as `zeta_in` is. Checks are paid one month in arrears, so a payment year
carries the December check of the year before.

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

import glob
import io
import os

import numpy as np
import pytest

import owlplanner as owl
from owlplanner import socialsecurity as ss
from owlplanner.export import build_summary_dic
from owlplanner.mylogging import Logger

# Step 3 was written test-first (phase5-plan.md §5b): the spec commit carried these
# tests with pytest.mark.xfail(strict=True); the implementation commit removes the
# markers.

# Frozen plan start (tests/conftest.py freezes the date; keep this in step with it).
THISYEAR = 2026

_EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "examples")

# Plan §3: the three examples that pay SS before FRA in a year with wages above the
# exempt amount (jack+jill and chris+pat: the second spouse's last work year 2028;
# alex+jamie: 2026-2027).
THE_THREE = ["alex+jamie", "chris+pat", "jack+jill"]


# Reduction factor of a benefit claimed `months` months before FRA 67, from the rates of
# 20 CFR 404.410 (5/9 of 1% per month for the first 36 months, 5/12 of 1% beyond).
def _factor(months):
    early = min(months, 36) * 5.0 / 9.0 + max(months - 36, 0) * 5.0 / 12.0
    return 1.0 - early / 100.0


def _hfp_for(case):
    """The example's workbook, or None (Case_bill ships without one)."""
    name = case.replace("Case_", "HFP_").replace("-spending", "").replace("-bequest", "")
    path = os.path.join(_EXAMPLES, name + ".xlsx")
    return path if os.path.exists(path) else None


def _load(case):
    p = owl.readConfig(
        os.path.join(_EXAMPLES, "Case_" + case + ".toml"), verbose=False, logstreams=[io.StringIO()]
    )
    hfp = _hfp_for(case)
    if hfp is not None:
        p.readHFP(hfp)
    return p


def _solve(p, test_on):
    """Resolve the plan with the earnings test switched on or off (D6: off by default)."""
    opts = dict(p.solverOptions or {})
    if test_on:
        opts["withEarningsTest"] = True
    else:
        opts.pop("withEarningsTest", None)
    p.solverOptions = opts
    p.resolve()
    assert p.caseStatus == "solved"
    return p


def _n(p, year):
    """Plan-year index of a calendar year."""
    return int(year) - int(p.year_n[0])


def _both_alives(p):
    """Plan-year indices where both spouses are alive (before the first death)."""
    return range(int(np.min(p.horizons)))


# --------------------------------------------------------------------------------------
# No-op: the switch off, or no earnings (§5b)
# --------------------------------------------------------------------------------------


def test_switch_off_keeps_todays_streams():
    """With the switch off the streams are exactly ``compute_social_security_benefits``,
    and nothing is reported as withheld or credited."""
    p = _solve(_load("jack+jill"), test_on=False)
    base, _ = ss.compute_social_security_benefits(
        p.ssecAmounts, p.ssecAges, p.yobs, p.mobs, p.tobs, p.horizons, p.N_i, p.N_n
    )
    assert np.allclose(p.zeta_in, base, rtol=0.0, atol=1e-6)
    assert np.all(p.ss_withheld_in == 0)
    assert np.all(p.ss_arf_months_i == 0)
    assert np.all(p.ss_arf_months_spousal_i == 0)


def test_no_earnings_with_the_switch_on_is_a_no_op():
    """Earnings are what the test reads: with none of them, the switch changes nothing."""
    p = _load("jack+jill")
    base, _ = ss.compute_social_security_benefits(
        p.ssecAmounts, p.ssecAges, p.yobs, p.mobs, p.tobs, p.horizons, p.N_i, p.N_n
    )
    p.omega_in[:, :] = 0.0
    p.etEarnings_in[:, :] = 0.0
    p.etMonths_in[:, :] = 0.0
    _solve(p, test_on=True)
    assert np.allclose(p.zeta_in, base, rtol=0.0, atol=1e-6)
    assert np.all(p.ss_withheld_in == 0)


def _other_fifteen():
    cases = []
    for path in sorted(glob.glob(os.path.join(_EXAMPLES, "Case_*.toml"))):
        case = os.path.basename(path)[len("Case_") : -len(".toml")]
        if case not in THE_THREE:
            cases.append(case)
    assert len(cases) == 15
    return cases


@pytest.mark.parametrize("case", _other_fifteen())
def test_no_op_objective_on_the_other_fifteen(case):
    """Plan §5 step 3: no-op on the other fifteen examples, objective identical to the
    cent. Nobody there claims before FRA in a year with wages above the exempt amount."""
    off = _solve(_load(case), test_on=False)
    on = _solve(_load(case), test_on=True)
    assert round(float(on.basis), 2) == round(float(off.basis), 2)
    assert round(float(on.bequest), 2) == round(float(off.bequest), 2)
    assert np.allclose(on.zeta_in, off.zeta_in, rtol=0.0, atol=1e-6)
    assert np.all(on.ss_withheld_in == 0)
    assert np.all(on.ss_arf_months_i == 0)


# --------------------------------------------------------------------------------------
# The three examples of plan §3 with the test on
# --------------------------------------------------------------------------------------


def test_jack_jill_2028_is_fully_withheld():
    """jack+jill: Jill (born 1966-01, claims 62y1m in Feb 2028) earns $85k in 2028, her
    last work year. The excess ((85,000 - 24,480)/2, before deflating) is larger than the
    whole year's benefit, so every month of her 2028 is withheld and comes back through
    the ARF at FRA (2033)."""
    p = _solve(_load("jack+jill"), test_on=True)
    assert p.zeta_in[1, _n(p, 2028)] == 0.0
    assert p.ss_withheld_in[1, _n(p, 2028)] > 0
    # 11 crediting months: her entitlement months Feb-Dec 2028 (62y1m from Jan 1966).
    assert p.ss_arf_months_i[1] == 11
    assert p.ss_arf_months_spousal_i[1] == 0
    # From FRA: PIA x the factor at the claiming age plus 11 months = 63 exactly,
    # i.e. 48 reduction months (59 at 62y1m less 11 credited): _factor(48) = 0.75.
    from_fra = 12.0 * 1642.0 * _factor(48)
    for n in _both_alives(p):
        if n >= _n(p, 2034):
            assert p.zeta_in[1, n] == pytest.approx(from_fra)


def test_jack_jill_2028_is_spared_with_six_months():
    """The grace year (404.435): with `months worked` 6 the months after June are
    non-service months and are paid whatever the annual excess. The five worked months of
    her entitlement (Feb-Jun) are still withheld."""
    p = _load("jack+jill")
    p.etMonths_in[1, _n(p, 2028)] = 6.0
    _solve(p, test_on=True)
    # Five checks paid in 2028 (entitlement Jul-Nov 2028), the five worked months withheld.
    paid = 5.0 * 1642.0 * _factor(59)
    assert p.zeta_in[1, _n(p, 2028)] == pytest.approx(paid)
    assert p.ss_arf_months_i[1] == 5
    # From FRA: 54 reduction months left (59 less 5 credited) -> 0.725.
    from_fra = 12.0 * 1642.0 * _factor(54)
    for n in _both_alives(p):
        if n >= _n(p, 2034):
            assert p.zeta_in[1, n] == pytest.approx(from_fra)


def test_jack_jill_taxes_on_ss_follow_the_net():
    """Taxes on Social Security are computed from what is paid: the taxable share in 2028
    is zero with the test on (nothing is paid there) and positive without it."""
    off = _solve(_load("jack+jill"), test_on=False)
    on = _solve(_load("jack+jill"), test_on=True)
    n28 = _n(off, 2028)
    taxable_off = float(off.Psi_n[n28] * np.sum(off.zetaBar_in[:, n28]))
    taxable_on = float(on.Psi_n[n28] * np.sum(on.zetaBar_in[:, n28]))
    assert taxable_off > 0
    assert taxable_on == 0.0


def test_chris_pat_2028_is_fully_withheld():
    """chris+pat: Pat (born 1966-01, claims 62y1m in Feb 2028) earns $85k in 2028, the
    last work year; Chris claims at 70 and never meets the test. No spousal add-on for
    either (0.5 x the other PIA is below their own), so the streams are own benefits."""
    p = _solve(_load("chris+pat"), test_on=True)
    assert p.zeta_in[1, _n(p, 2028)] == 0.0
    assert p.ss_arf_months_i[1] == 11
    assert np.all(p.ss_withheld_in[0] == 0)
    from_fra = 12.0 * 1400.0 * _factor(48)
    for n in _both_alives(p):
        if n >= _n(p, 2034):
            assert p.zeta_in[1, n] == pytest.approx(from_fra)


def test_alex_jamie_2026_27_are_fully_withheld():
    """alex+jamie: Jamie (born 1961-01, collecting since 62y1m in 2023) earns $80k in
    2026 and 2027, her last two years before FRA (Jan 2028). Every entitlement month of
    both years is withheld; the one check of 2026 is for December 2025, a pre-plan month
    the test cannot charge. Jamie's spousal add-on only starts with Alex's claim at 69
    (2029), so the years below carry her own benefit alone."""
    p = _solve(_load("alex+jamie"), test_on=True)
    assert p.zeta_in[1, _n(p, 2027)] == 0.0
    assert p.zeta_in[1, _n(p, 2026)] == pytest.approx(1200.0 * _factor(59))
    # Every month of 2026 and 2027 is a crediting month (24); from FRA the factor is the
    # one for 59 - 24 = 35 reduction months.
    assert p.ss_arf_months_i[1] == 24
    # 2028 still carries the December 2027 check, withheld; then 11 checks at FRA.
    assert p.zeta_in[1, _n(p, 2028)] == pytest.approx(11.0 * 1200.0 * _factor(35))


# --------------------------------------------------------------------------------------
# A second solve sees edited wages (§5: "stale streams" risk)
# --------------------------------------------------------------------------------------


def test_second_solve_after_editing_wages():
    """The streams are rebuilt at solve time (zeta_in is built before the HFP is read),
    so wages edited between two solves move the test."""
    p = _solve(_load("jack+jill"), test_on=True)
    assert p.zeta_in[1, _n(p, 2028)] == 0.0

    # The UI path: the edited tables are re-read (owlbridge._setContributions).
    tables = {n: p.timeLists[n].copy() for n in p.inames}
    tables["Jill"].loc[tables["Jill"].index[5 + _n(p, 2028)], "anticipated wages"] = 20_000.0
    p.readHFP(tables, houseTables=False)
    _solve(p, test_on=True)
    assert p.zeta_in[1, _n(p, 2028)] > 0  # 20,000 < the 24,480 exempt amount
    assert np.all(p.ss_withheld_in[1] == 0)
    assert p.ss_arf_months_i[1] == 0


# --------------------------------------------------------------------------------------
# Warnings (plan §4.4, §5 step 3), once per solve and only with the switch on
# --------------------------------------------------------------------------------------


def _warn_log(p):
    """A logger for p writing to a buffer; read it with _warn_lines after the solve."""
    buf = io.StringIO()
    p.mylog = Logger(verbose=False, logstreams=[buf])
    return buf


def _warn_lines(buf):
    """The WARNING messages logged into buf."""
    return [line.split(" | ", 3)[-1] for line in buf.getvalue().splitlines() if "| WARNING |" in line]


def test_no_warnings_with_the_switch_off():
    """chris+pat falls back to `anticipated wages` in 2028, and alex+jamie is fully
    withheld before FRA: both warn with the test on, neither with it off."""
    for case in ("chris+pat", "alex+jamie"):
        p = _load(case)
        buf = _warn_log(p)
        _solve(p, test_on=False)
        warned = [w for w in _warn_lines(buf) if "gross earnings" in w or "withheld" in w]
        assert not warned
        assert np.all(p.ss_withheld_in == 0)  # and the test was not applied


def test_fallback_warning_names_only_the_reachable_years():
    """`gross earnings` is not given for Pat in 2028 (401k deferrals, wages $85k) and Pat
    claims that year, so the fallback understates what the test counts. Chris claims at
    70, past the FRA year, and Pat's 2026-2027 are before entitlement: neither is named."""
    p = _load("chris+pat")
    buf = _warn_log(p)
    _solve(p, test_on=True)
    warned = [w for w in _warn_lines(buf) if "gross earnings" in w]
    assert len(warned) == 1
    assert "Pat" in warned[0]
    assert "2028" in warned[0]
    assert "Chris" not in warned[0]
    assert "2027" not in warned[0]


def test_no_fallback_warning_for_a_late_claim():
    """Jack's 2026-2027 carry 401k deferrals, but he claims at 70: no entitlement month
    before his FRA year, so the test never reads those years (plan §5 step 3). It is
    applied to Jill all the same (her 2028 is withheld, 11 crediting months)."""
    p = _load("jack+jill")
    buf = _warn_log(p)
    _solve(p, test_on=True)
    warned = [w for w in _warn_lines(buf) if "gross earnings" in w]
    assert not any("Jack" in w for w in warned)
    assert p.ss_arf_months_i[1] == 11


def test_warning_when_a_claiming_age_pays_nothing_before_fra():
    """alex+jamie: every month of Jamie's entitlement before FRA (2026-2027) is withheld,
    so the early claim buys nothing until the ARF at FRA. The warning names the years and
    does not fire when the test is off."""
    p = _load("alex+jamie")
    buf = _warn_log(p)
    _solve(p, test_on=True)
    warned = [w for w in _warn_lines(buf) if "withheld" in w]
    assert len(warned) == 1
    assert "Jamie" in warned[0]
    assert "2026-2027" in warned[0]
    assert "ARF" in warned[0]


# --------------------------------------------------------------------------------------
# Outputs: Summary, worksheet, explain (plan §4.4)
# --------------------------------------------------------------------------------------


def test_summary_rows_appear_only_with_withholding():
    on = _solve(_load("jack+jill"), test_on=True)
    dic = build_summary_dic(on)
    assert any(k.startswith("SS withheld by the earnings test") for k in dic)
    assert "ARF months" in dic
    assert "11" in dic["ARF months"]

    off = _solve(_load("jack+jill"), test_on=False)
    dic = build_summary_dic(off)
    assert not any(k.startswith("SS withheld by the earnings test") for k in dic)
    assert "ARF months" not in dic


def test_worksheet_column_next_to_ss():
    """The per-person Sources sheet carries 'SS withheld' next to 'social sec', and only
    when something is withheld."""
    on = _solve(_load("jack+jill"), test_on=True)
    wb = on.saveWorkbook(saveToFile=False)
    ws = next(w for w in wb.worksheets if w.title == on.inames[1] + "'s Sources")
    headers = [cell.value for cell in ws[1]]
    assert "SS withheld" in headers
    assert headers.index("SS withheld") == headers.index("social sec") + 1

    off = _solve(_load("jack+jill"), test_on=False)
    wb = off.saveWorkbook(saveToFile=False)
    ws = next(w for w in wb.worksheets if w.title == off.inames[1] + "'s Sources")
    assert "SS withheld" not in [cell.value for cell in ws[1]]


def test_explain_ss_block_gains_both():
    """`owlcli explain` describes the case without solving: it reports what the earnings
    test would withhold at the entered claiming ages, and whether the solve applies it."""
    from owlplanner.cli.cmd_explain import _plan_to_explain

    p = _load("jack+jill")
    block = _plan_to_explain(p, "Case_jack+jill.toml", [])["social_security"]
    by_name = {entry["name"]: entry for entry in block}
    jill = by_name["Jill"]["earnings_test"]
    assert jill["applied"] is False  # D6: off unless the case asks for it
    assert jill["arf_months"] == 11
    assert jill["arf_months_spousal"] == 0
    # Every month of 2028 withheld, one month's benefit each (today's $).
    assert jill["ss_withheld_total_today"] == pytest.approx(11 * 1642 * _factor(59), abs=1.0)
    assert by_name["Jack"]["earnings_test"]["arf_months"] == 0
    assert by_name["Jack"]["earnings_test"]["ss_withheld_total_today"] == 0

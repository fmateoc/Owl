"""
Property tests of the SSA earnings test and the earnings it reads (fork).

The example-based tests in this directory check hand numbers on chosen households. The
properties here hold for every household in a stated domain, so they reach the corners the
examples miss (upstream #229, #231, #232 were all found this way):

- **Conservation:** in every payment year, benefits paid + withheld = benefits due, where
  "due" is each benefit at its own rate in each month: reduced before its owner's FRA, at
  the ARF rate from it (RS 00615.480/.482). Charging only moves dollars from paid to
  withheld; it never makes them disappear.
- **Excess bound:** the test never withholds more than the excess earnings it charges.
- **Continuity in wages:** one more dollar of pay moves the earnings by one dollar. A
  pre-tax 401(k) deferral is always paid from pay (26 U.S.C. 3121(v)(1)(A) keeps it in FICA
  wages), so it counts whatever is left in AGI wages.
- **Start-year invariance:** for a calendar year the exempt table covers, the nominal amount
  withheld depends on that year's nominal earnings and exempt amount, not on the year the
  plan starts (42 U.S.C. 403(f)(8): the amounts are published in nominal dollars).

The cases that fail today are strict xfails naming their upstream issue, so a fix shows up as
an XPASS to remove. "Due" below is rebuilt from the rule functions (`getSelfFactor`,
`getSpousalFactor`, `arf_*_factor`), not from the charging code under test. Domain of the
random households: no death within the plan (equal horizons), no trim, claims between
eligibility and FRA (no delayed credits), births on the 1st, 2nd or 15th.

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

import datetime
import io
import sys

import numpy as np
import pytest

import owlplanner as owl
from owlplanner import socialsecurity as ss

THISYEAR = 2026  # tests/conftest.py freezes the date at 2026-01-01
N_YEARS = 25


def _known(issue, reason):
    """A strict xfail for a property that fails today on upstream issue `issue`."""
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason=f"{issue}: {reason}")


XFAIL_229 = _known("#229", "the omega_in > 0 gate drops an all-deferred year's deferral")
XFAIL_231 = _known("#231", "nominal exempt amounts read as the plan's first-year dollars")
XFAIL_232 = _known("#232", "the worker's excess is charged on the spouse's pre-ARF add-on")


# --------------------------------------------------------------------------------------
# Benefits due, rebuilt from the rule functions
# --------------------------------------------------------------------------------------


def _due(pias, ages, yobs, mobs, tobs, n_years, res, thisyear=THISYEAR):
    """
    Benefits due by payment year, shape (N_i, n_years), today's dollars: own benefit and
    spousal add-on at their reduced rates before each owner's FRA and at the ARF rate from
    it, with the ARF months the test reports. Same grid as the test: entitlement months from
    the December before the plan, each check paid the next month, checks paid after the
    plan dropped.
    """
    n_i = len(pias)
    fras = ss.getFRAs(np.asarray(yobs), np.asarray(mobs), np.asarray(tobs))
    sb = ss.getSpousalBenefits(np.asarray(pias, dtype=np.int32))
    first = [tobs[i] == 1 for i in range(n_i)]
    claim = [float(a) for a in res.ages]  # after the eligibility reset
    ent = [ss._ent_start_abs(yobs[i], mobs[i], claim[i]) for i in range(n_i)]
    fra_abs = [ss._ent_start_abs(yobs[i], mobs[i], ss._fra_conventional_age(fras[i], first[i])) for i in range(n_i)]
    g0 = thisyear * 12 - 1
    end = (thisyear + n_years) * 12
    due = np.zeros((n_i, n_years))

    def add(i, start, rate_before, rate_after):
        for a in range(max(start, g0), end):
            pay_n = (a + 1) // 12 - thisyear
            if pay_n < n_years:
                due[i, pay_n] += rate_before if a < fra_abs[i] else rate_after

    for i in range(n_i):
        own = pias[i] * ss.getSelfFactor(fras[i], claim[i], first[i])
        own_arf = pias[i] * ss.arf_self_factor(fras[i], claim[i], int(res.arf_months[i]), first[i])
        add(i, ent[i], own, own if res.arf_months[i] == 0 else own_arf)
    if n_i == 2:
        latest = max(ent)
        for i in range(2):
            if sb[i] <= 0:
                continue
            sp_age = max(62.0, (latest - (yobs[i] * 12 + mobs[i] - 1)) / 12.0)
            sp = sb[i] * ss.getSpousalFactor(fras[i], sp_age, first[i])
            sp_arf = sb[i] * ss.arf_spousal_factor(fras[i], sp_age, int(res.arf_months_spousal[i]), first[i])
            add(i, latest, sp, sp if res.arf_months_spousal[i] == 0 else sp_arf)
    return due, fra_abs, sb


def _run(pias, ages, yobs, mobs, tobs, earnings, months=None):
    n_i = len(pias)
    return ss.earnings_test(
        pias, ages, yobs, mobs, tobs, [N_YEARS] * n_i, n_i, N_YEARS, earnings,
        work_months_in=months, thisyear=THISYEAR,
    )


def _random_household(rng, couple):
    """A random household in the domain of the module docstring."""
    n_i = 2 if couple else 1
    yobs = [int(rng.integers(1958, 1969)) for _ in range(n_i)]
    mobs = [int(rng.integers(1, 13)) for _ in range(n_i)]
    tobs = [int(rng.choice([1, 2, 15])) for _ in range(n_i)]
    pias = [int(rng.integers(300, 3600)) for _ in range(n_i)]
    if couple and rng.random() < 0.6:
        pias[1] = int(rng.integers(0, pias[0] // 2))  # a spousal add-on on 0's record
    fras = ss.getFRAs(np.asarray(yobs), np.asarray(mobs), np.asarray(tobs))
    ages = []
    for i in range(n_i):
        eligible_m = 62 * 12 + (0 if tobs[i] <= 2 else 1)
        fra_m = int(round(ss._fra_conventional_age(fras[i], tobs[i] == 1) * 12))
        ages.append(int(rng.integers(eligible_m, fra_m + 1)) / 12.0)
    earnings = np.zeros((n_i, N_YEARS))
    months = np.zeros((n_i, N_YEARS))
    for i in range(n_i):
        n_work = int(rng.integers(0, 9))
        earnings[i, :n_work] = rng.integers(0, 90_000, size=n_work)
        months[i, :n_work] = rng.choice([0, 3, 7, 12], size=n_work)
    return pias, ages, yobs, mobs, tobs, earnings, months


def _addon_owner_reaches_fra_first(fra_abs, sb):
    """True where an add-on's owner reaches FRA before the worker it is paid on, so the
    worker's excess can be charged on the add-on after its ARF (#232's case)."""
    if len(sb) < 2:
        return False
    return any(sb[j] > 0 and fra_abs[j] < fra_abs[1 - j] for j in range(2))


def _households(seed, count, couple, keep):
    rng = np.random.default_rng(seed)
    out = []
    while len(out) < count:
        h = _random_household(rng, couple)
        res = _run(*h)
        due, fra_abs, sb = _due(*h[:5], N_YEARS, res)
        if keep(_addon_owner_reaches_fra_first(fra_abs, sb)):
            out.append((h, res, due))
    return out


# --------------------------------------------------------------------------------------
# Conservation and the excess bound
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("couple", [False, True], ids=["single", "couple"])
def test_paid_plus_withheld_is_the_benefit_due(couple):
    """Outside #232's case (an add-on's owner reaching FRA before the worker it is paid on),
    every payment year conserves the benefit due, for random households."""
    for h, res, due in _households(seed=232 + couple, count=60, couple=couple, keep=lambda hit: not hit):
        assert np.all(res.zeta_in >= -1e-9) and np.all(res.withheld_in >= -1e-9), h
        np.testing.assert_allclose(res.zeta_in + res.withheld_in, due, atol=1e-6, err_msg=str(h))


def test_random_households_reach_the_charging_paths():
    """The random domain is not vacuous: it withholds, credits ARF months on both records,
    and charges an auxiliary's own excess."""
    hs = _households(seed=233, count=60, couple=True, keep=lambda hit: not hit)
    assert sum(r.withheld_in.sum() > 0 for _, r, _ in hs) >= 20
    assert any(r.arf_months_spousal.max() > 0 for _, r, _ in hs)
    assert any(r.excess_by_year[1].sum() > 0 and h[0][1] < h[0][0] // 2 for h, r, _ in hs)


@XFAIL_232
@pytest.mark.parametrize("wage", [60_000, 70_000])
def test_paid_plus_withheld_is_due_after_the_spouses_fra(wage):
    """#232's two households: W born 1963-08-15, PIA 2,400, claims at 62y1m, earns `wage` in
    2026-2030; S born 1962-03-15, PIA 400, claims at 63y10m (add-on from January 2026, FRA
    March 2029). The issue reports 810.11 and 1,381.31 missing in payment year 2029."""
    h = ([2400, 400], [62 + 1 / 12, 63 + 10 / 12], [1963, 1962], [8, 3], [15, 15], np.zeros((2, N_YEARS)))
    h[5][0, :5] = wage
    res = _run(*h)
    due, _, _ = _due(*h[:5], N_YEARS, res)
    np.testing.assert_allclose(res.zeta_in + res.withheld_in, due, atol=1e-6)


@pytest.mark.parametrize("couple", [False, True], ids=["single", "couple"])
def test_withheld_never_exceeds_the_excess(couple):
    """Each dollar of excess is charged at most once (#232's households included: they lose
    benefits, not the excess bound)."""
    for h, res, _ in _households(seed=234 + couple, count=60, couple=couple, keep=lambda hit: True):
        assert res.withheld_in.sum() <= res.excess_by_year.sum() + 1e-6, h


# --------------------------------------------------------------------------------------
# Continuity of the earnings in wages
# --------------------------------------------------------------------------------------


def _earnings(wages, deferral):
    p = owl.Plan(["A"], ["1976-07-01"], [90], "props", verbose=False, logstreams=[io.StringIO()])
    p.omega_in[0, 0] = wages
    p.kappa_ijn[0, 1, 0] = deferral
    return p._earnings_test_inputs()[0][0, 0]


@pytest.mark.parametrize(
    "wages, deferral",
    [
        pytest.param(0, 23_500, marks=XFAIL_229),
        (1, 23_500),
        (50_000, 23_500),
        (0, 0),
        (50_000, 0),
    ],
)
def test_a_dollar_of_pay_moves_the_earnings_by_a_dollar(wages, deferral):
    """`anticipated wages` are AGI wages, net of the 401(k) deferral (#221); the deferral is
    pay too, so earnings = wages + deferral whatever the wages."""
    assert _earnings(wages, deferral) == pytest.approx(wages + deferral)
    assert _earnings(wages + 1, deferral) - _earnings(wages, deferral) == pytest.approx(1.0)


# --------------------------------------------------------------------------------------
# Start-year invariance
# --------------------------------------------------------------------------------------


def _start_in(monkeypatch, year):
    """Make every owlplanner module see January 1 of `year` as today (as tests/conftest.py
    does for 2026)."""

    class _Day(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(year, 1, 1)

    for name, mod in list(sys.modules.items()):
        if name.startswith("owlplanner") and mod is not None:
            d = getattr(mod, "date", None)
            if isinstance(d, type) and issubclass(d, datetime.date):
                monkeypatch.setattr(mod, "date", _Day)


def _nominal_withheld_for_2027(monkeypatch, start, inflation, earnings_2027):
    """Nominal amount withheld for work in calendar 2027 by a plan starting in `start`.
    The worker (born 1963-08-15, PIA 2,000, claim at 62y1m) is entitled before either plan,
    so the initial grace year (2025) is outside both and only 2027 has earnings."""
    with monkeypatch.context() as mp:
        _start_in(mp, start)
        p = owl.Plan(["W"], ["1963-08-15"], [89], "props", verbose=False, logstreams=[io.StringIO()])
        p.setSocialSecurity([2000], [62 + 1 / 12])
        n = 2027 - start
        p.omega_in[0, n] = earnings_2027
        gamma = (1 + inflation) ** np.arange(p.N_n + 1)
        res = p._earningsTestResult(gamma_n=gamma)
    return float(np.sum(res.withheld_in[0] * gamma[: p.N_n]))


@pytest.mark.parametrize(
    "inflation",
    [
        0.0,
        pytest.param(0.025, marks=XFAIL_231),
    ],
)
def test_withholding_in_a_tabled_year_does_not_depend_on_the_start_year(monkeypatch, inflation):
    """With 2027 in the exempt table (the amounts #231 cites; the property needs only that the
    year is covered), a 2026 plan and a 2027 plan withhold the same nominal amount for 2027's
    $40,000. The excess (7,220) is below the year's benefit, so the amount withheld is the
    excess itself and the PIA, entered in each plan's own today's dollars, does not enter. At
    zero inflation the two dollar bases coincide: that case checks the start-year harness
    itself."""
    table = dict(ss._EXEMPT_TABLE)
    table[2027] = (25_560.0, 67_920.0)
    monkeypatch.setattr(ss, "_EXEMPT_TABLE", table)
    early = _nominal_withheld_for_2027(monkeypatch, 2026, inflation, 40_000)
    late = _nominal_withheld_for_2027(monkeypatch, 2027, inflation, 40_000)
    assert early > 0
    assert early == pytest.approx(late, abs=1.0)

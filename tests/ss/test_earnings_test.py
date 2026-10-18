"""
Tests for the SSA earnings-test rules (Phase 5 step 1).

Expected values come from the primary worked examples, not from the code under test.
Each test names its source. Exempt amounts are passed in so the POMS examples run
with their own year's numbers.

Sources (POMS on secure.ssa.gov, read 2026-10-18):
  RS 02501.025 D  exempt amounts (TN 55, 11/21/2025)
  RS 02501.030    monthly test / grace year / non-service months
  RS 02501.080    excess examples (TN 39)
  RS 02501.095    family charging examples (TN 38)
  RS 02501.110    partial-month split examples (TN 47)
  RS 00615.480/.482/.490  ARF procedure (TN 77/76/24)
  20 CFR 404.435 Example 1  grace year (eCFR 2026-10-15 text)

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

import math

import numpy as np
import pytest

from owlplanner import socialsecurity as ss

# Step 1 is test-first (phase5-plan.md §5b). The spec commit carried these tests with
# pytest.mark.xfail(strict=True); the implementation commit removes the markers.
#
# Month indexing (locked API — do not mix them):
#   charge_excess_months: 0-based month index within the charged span (0 = first month).
#   is_non_service_month / initial_grace_year: 1-based calendar month (1 = January).


# Frozen plan start (tests/conftest.py freezes the date; keep this in step with it).
THISYEAR = 2026

# 2026 statutory amounts (RS 02501.025 D, TN 55). Built lazily so this file collects
# without the implementation (module-level ExemptAmounts would error at import, and
# collection errors are not xfail).
_EXEMPT_2026_VALUES = (24_480.0, 65_160.0)


def _exempt_2026(_year):
    return ss.ExemptAmounts(*_EXEMPT_2026_VALUES)


# --------------------------------------------------------------------------------------
# Excess earnings — RS 02501.080
# --------------------------------------------------------------------------------------


def test_excess_under_fra_rounds_down():
    """RS 02501.080 B.1 EXAMPLE: $12,121 − $9,600 → $1,260 (1999 amounts)."""
    # ($12,121 − $9,600) / 2 = $1,260.5 → $1,260 rounded down.
    assert ss.excess_earnings(12_121.0, 9_600.0, is_fra_year=False) == 1260


def test_excess_fra_year_divides_by_three():
    """RS 02501.080 B.2 EXAMPLE: $30,000 − $17,000 → $4,333 (FRA-year amounts)."""
    # ($30,000 − $17,000) / 3 = $4,333.33 → $4,333 rounded down.
    assert ss.excess_earnings(30_000.0, 17_000.0, is_fra_year=True) == 4333


def test_excess_fra_year_wage_cut_at_fra_month():
    """RS 02501.080 B.2.b EXAMPLE: attained FRA in 6/00; Jan-May $30,000, Jun-Dec $10,000.

    Only $30,000 counts; excess = ($30,000 − $17,000) / 3 = $4,333.

    Owl spreads earnings evenly over ``months worked`` (Phase 5 D2), which matches the
    NESE prorating of B.2.c, not the wages month-by-month shape of B.2.b (the example's
    $30k/$10k split cannot be expressed as an even spread). What must hold: only the
    months *before* the FRA month count, and the FRA-year divisor is 3.
    """
    # Example as written (uneven wages): the rule applied to the pre-FRA total.
    assert ss.excess_earnings(30_000.0, 17_000.0, is_fra_year=True) == 4333
    # Even-spread form of the cut: 5 of 12 months before June.
    countable = ss.countable_earnings(40_000.0, months_worked=12, is_fra_year=True, fra_month_in_year=6)
    assert countable == pytest.approx(40_000.0 * 5 / 12)
    # A worker whose months-worked period is entirely before the FRA month counts all of it.
    assert ss.countable_earnings(30_000.0, months_worked=5, is_fra_year=True, fra_month_in_year=6) == 30_000.0
    # FRA in January: no month before the FRA month counts.
    assert ss.countable_earnings(10_000.0, months_worked=12, is_fra_year=True, fra_month_in_year=1) == 0.0
    # FRA month past the last worked month: the whole year counts.
    assert ss.countable_earnings(40_000.0, 12, is_fra_year=True, fra_month_in_year=13) == pytest.approx(
        40_000.0
    )


def test_excess_never_negative():
    assert ss.excess_earnings(10_000.0, 24_480.0, is_fra_year=False) == 0
    assert ss.excess_earnings(24_480.0, 24_480.0, is_fra_year=False) == 0


# --------------------------------------------------------------------------------------
# Family charging — RS 02501.095
# --------------------------------------------------------------------------------------


def test_nh_excess_charges_family_three_months():
    """RS 02501.095 B.2 EXAMPLE: NH RIB $378, spouse and child $160 each, excess $2,094.

    Family $698/month; January-March withheld (3 × $698 = $2,094).
    """
    monthly = [[378.0] * 12, [160.0] * 12, [160.0] * 12]
    withheld, n_ded, partial = ss.charge_excess_months(monthly, 2094.0)
    assert n_ded == 3
    assert partial is None
    for m in range(3):
        assert withheld[0][m] == pytest.approx(378.0)
        assert withheld[1][m] == pytest.approx(160.0)
        assert withheld[2][m] == pytest.approx(160.0)
    for m in range(3, 12):
        assert withheld[0][m] == 0
        assert withheld[1][m] == 0
        assert withheld[2][m] == 0


def test_aux_excess_after_nh_four_then_five_months():
    """RS 02501.095 B.4 EXAMPLE: NH RIB $346, spouse $173; NH excess $2,076; spouse $865.

    NH's excess: January-April against family $519 (4 × $519 = $2,076).
    Spouse's own excess then charges May-September against $173 (5 × $173 = $865).

    This unit test drives the two passes explicitly. The *order* (NH first, then aux)
    as ``earnings_test`` behavior is asserted in
    ``test_family_charge_order_and_spousal_arf_crediting``.
    """
    # First: NH worker excess against the family.
    family = [[346.0] * 12, [173.0] * 12]
    w1, n1, _ = ss.charge_excess_months(family, 2076.0)
    assert n1 == 4
    for m in range(4):
        assert w1[0][m] == pytest.approx(346.0)
        assert w1[1][m] == pytest.approx(173.0)
        assert family[0][m] == 0
        assert family[1][m] == 0

    # Then: auxiliary's own excess against what is left of the aux benefit.
    remaining = [[family[1][m] for m in range(12)]]  # spouse's remaining check
    w2, n2, _ = ss.charge_excess_months(remaining, 865.0)
    assert n2 == 5
    for m in range(5):
        # May-September are months 4..8 of the year (0-based).
        assert w2[0][4 + m] == pytest.approx(173.0)
    for m in (0, 1, 2, 3, 9, 10, 11):
        assert w2[0][m] == 0


def test_no_carry_over_into_next_year():
    """RS 02501.095 B.1: excess of one year is never charged into the next.

    A year with a small benefit and a large excess exhausts that year's months
    and leaves the rest of the excess uncharged (it does not spill into the next
    year's months).
    """
    # One beneficiary, $100/month, excess $300: 3 months charged, nothing more.
    monthly = [[100.0] * 12]
    withheld, n_ded, _ = ss.charge_excess_months(monthly, 300.0)
    assert n_ded == 3
    assert sum(withheld[0]) == pytest.approx(300.0)
    # Larger excess than the year's family benefit: all 12 months, remainder dropped.
    monthly = [[100.0] * 12]
    withheld, n_ded, _ = ss.charge_excess_months(monthly, 10_000.0)
    assert n_ded == 12
    assert sum(withheld[0]) == pytest.approx(1200.0)


# --------------------------------------------------------------------------------------
# Partial last month — RS 02501.110
# --------------------------------------------------------------------------------------


def test_partial_month_split_in_proportion():
    """RS 02501.110 C EXAMPLE 2: NH $800, four aux at $101, excess $6,624.

    Family $1,204; January-May full; June pays the family $600, split NH $200
    and each auxiliary $100 (2/6 and 1/6 shares).
    """
    monthly = [[800.0] * 12] + [[101.0] * 12 for _ in range(4)]
    shares = [2.0, 1.0, 1.0, 1.0, 1.0]
    withheld, n_ded, partial = ss.charge_excess_months(monthly, 6624.0, shares=shares)
    assert n_ded == 6
    assert partial == 5  # June (0-based)
    for m in range(5):
        assert withheld[0][m] == pytest.approx(800.0)
    # June: family paid $600 → NH $200, each aux $100; withheld = rate − paid.
    assert monthly[0][5] == pytest.approx(200.0)
    for b in range(1, 5):
        assert monthly[b][5] == pytest.approx(100.0)
    assert withheld[0][5] == pytest.approx(600.0)
    for b in range(1, 5):
        assert withheld[b][5] == pytest.approx(1.0)


def test_partial_month_share_capped_at_rate():
    """RS 02501.110 C EXAMPLE 3 (first apportionment + reapportionment).

    Partial family benefit $93; NH $117, aged spouse $16, two children $19.90.
    Shares 2:1:1:1. First split NH $37.20, each other $18.60; the spouse is capped
    at $16 and $2.60 is reapportioned (NH +$1.30, each child +$0.65) →
    NH $38, spouse $16, each child $19 (rounded down).
    """
    rates = [117.0, 16.0, 19.90, 19.90]
    shares = [2.0, 1.0, 1.0, 1.0]
    family = sum(rates)  # 172.80
    # Pay $93 in June: withhold family - 93 = 79.80 from that month.
    monthly = [[rates[b]] * 12 for b in range(4)]
    excess = family - 93.0
    withheld, n_ded, partial = ss.charge_excess_months(monthly, excess, shares=shares, start=5)
    assert partial == 5
    assert n_ded == 1
    # Paid amounts in the partial month (exact share math, then the dollar floor).
    # POMS Exhibit 3 pays the floored dollars: $38 / $16 / $19 / $19.
    assert monthly[0][5] == pytest.approx(38.50)
    assert monthly[1][5] == pytest.approx(16.0)
    assert monthly[2][5] == pytest.approx(19.25)
    assert monthly[3][5] == pytest.approx(19.25)
    assert math.floor(monthly[0][5]) == 38
    assert math.floor(monthly[1][5]) == 16
    assert math.floor(monthly[2][5]) == 19
    assert math.floor(monthly[3][5]) == 19


# --------------------------------------------------------------------------------------
# Non-service months and the grace year — RS 02501.030 / 404.435
# --------------------------------------------------------------------------------------


def test_non_service_month_definitions():
    """404.435(a)(7): no work, or wages at or below the monthly exempt amount."""
    assert ss.is_non_service_month(1, 0.0, 0, 2040.0) is True
    # $24,000/12 = $2,000 <= $2,040 monthly exempt → non-service.
    assert ss.is_non_service_month(1, 24_000.0, 12, 2040.0) is True
    # $30,000/12 = $2,500 > $2,040 → service month.
    assert ss.is_non_service_month(1, 30_000.0, 12, 2040.0) is False
    # After the months-worked period: no wages that month.
    assert ss.is_non_service_month(7, 40_000.0, 6, 2040.0) is True
    assert ss.is_non_service_month(6, 40_000.0, 6, 2040.0) is False


def test_grace_year_claim_in_july_with_six_months_work():
    """Claim in July of the last work year, `months worked` = 6 → nothing withheld.

    July-December are non-service months in or after entitlement, so the year is the
    initial grace year and the monthly test pays those months in full (404.435 Example 1
    is the same shape: retire mid-year, later months paid although annual earnings
    exceed the exempt amount).
    """
    # Hand-built year-level check of the grace-year rule.
    earn = {2028: 40_000.0}
    months = {2028: 6}
    grace = ss.initial_grace_year(
        earn,
        ent_start_month_in_year=7,
        start_year=2028,
        exempt_for_year=_exempt_2026,
        months_worked_by_year=months,
    )
    assert grace == 2028


def test_grace_year_claim_in_july_with_twelve_months_work_is_not_spared():
    """Same with `months worked` = 12 → the annual test applies (no non-service month)."""
    earn = {2028: 40_000.0}
    months = {2028: 12}
    # Every month has wages above the monthly exempt amount ($3,333 > $2,040),
    # so there is no non-service month in 2028.
    for m in range(1, 13):
        assert ss.is_non_service_month(m, 40_000.0, 12, 2040.0) is False
    grace = ss.initial_grace_year(
        earn,
        ent_start_month_in_year=7,
        start_year=2028,
        exempt_for_year=_exempt_2026,
        months_worked_by_year=months,
    )
    assert grace is None


def test_second_year_with_non_service_months_gets_no_grace():
    """Only one initial grace year (404.435(b)); a later year gets the annual test only."""
    earn = {2026: 0.0, 2027: 50_000.0, 2028: 0.0}
    months = {2026: 0, 2027: 12, 2028: 0}
    grace = ss.initial_grace_year(
        earn,
        ent_start_month_in_year=1,
        start_year=2026,
        exempt_for_year=_exempt_2026,
        months_worked_by_year=months,
        end_year=2028,
    )
    # 2026 has no work → non-service months → grace year is 2026, not 2028.
    assert grace == 2026


def test_year_after_entitlement_with_no_earnings_uses_up_grace():
    """404.435(a)(7),(b): claim in 2026 while not working; work above the limit in 2027.

    2026 is the initial grace year (all months non-service). 2027 is then the annual
    test only: no non-service months are spared (plan §5 step 1). Hand pin: claim 62y1m
    (April 2026), PIA $3,000 → $2,112.50/mo. 2027: ``months worked`` = 3, earnings
    $50,000 → excess ($50,000−$24,480)/2 = $12,760. If 2027 were still a grace year only
    the three service months would be charged (3 × $2,112.50 = $6,337.50). Because the
    grace year was used in 2026, the whole $12,760 is charged.
    """
    earn = {2026: 0.0, 2027: 50_000.0}
    months = {2026: 0, 2027: 3}
    grace = ss.initial_grace_year(
        earn,
        ent_start_month_in_year=4,
        start_year=2026,
        exempt_for_year=_exempt_2026,
        months_worked_by_year=months,
        end_year=2027,
    )
    assert grace == 2026

    pias, ages, yobs, mobs, tobs, horizons, N_i, N_n = _single_worker(claim=62.0, N_n=28)
    earnings = np.zeros((N_i, N_n))
    earnings[0, 1] = 50_000.0  # 2027 only
    work_months = np.zeros((N_i, N_n), dtype=int)
    work_months[0, 1] = 3
    res = ss.earnings_test(
        pias,
        ages,
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        work_months_in=work_months,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    monthly = 3000.0 * ss.getSelfFactor(67, 62 + 1 / 12, False)  # 2112.50
    # Grace used up in 2026 → 2027 charges the full excess (not just the 3 service months).
    assert res.withheld_in.sum() == pytest.approx(12_760.0)
    assert res.withheld_in.sum() > 3 * monthly  # more than the grace-year spare would leave


# --------------------------------------------------------------------------------------
# ARF — RS 00615.480 / .482 / .490 and the §2.2 inference
# --------------------------------------------------------------------------------------


def test_arf_hand_rates_claim_62_fra_67():
    """404.410 rates: 5/9 of 1% per month for the first 36, 5/12 of 1% beyond.

    Claim at 62 with FRA 67 = 60 reduction months → factor 70%.
    12 crediting months leave 48 → the factor of claiming at 63 (75%).
    """
    assert ss.getSelfFactor(67, 62, False) == pytest.approx(0.70)
    assert ss.getSelfFactor(67, 63, False) == pytest.approx(0.75)
    assert ss.arf_self_factor(67, 62, crediting_months=12, born_on_first=False) == pytest.approx(
        ss.getSelfFactor(67, 63, False)
    )
    assert ss.arf_self_factor(67, 62, crediting_months=12, born_on_first=False) == pytest.approx(0.75)
    # Zero crediting months: unchanged.
    assert ss.arf_self_factor(67, 62, crediting_months=0, born_on_first=False) == pytest.approx(0.70)
    # Claiming at FRA: no ARF.
    assert ss.arf_self_factor(67, 67, crediting_months=12, born_on_first=False) == pytest.approx(1.0)
    # Partial year of crediting months: 6 months → claim 62.5.
    assert ss.arf_self_factor(67, 62, crediting_months=6, born_on_first=False) == pytest.approx(
        ss.getSelfFactor(67, 62.5, False)
    )


def test_arf_partial_deduction_month_counts():
    """RS 00615.482 B.1: full *or partial* work deduction months are crediting months.

    charge_excess_months counts a month with any deduction (including the partial
    last month) in its ``months_with_deduction`` return.
    """
    monthly = [[100.0] * 12]
    withheld, n_ded, partial = ss.charge_excess_months(monthly, 250.0)
    # 2 full months + a partial third → 3 crediting months.
    assert n_ded == 3
    assert partial == 2
    assert withheld[0][2] == pytest.approx(50.0)


def test_arf_spousal_factor_matches_own_rule():
    """RS 00615.482 B.2: a spouse is credited for deductions from their own and the
    worker's work. The spousal factor uses the same crediting-month subtraction.

    Spousal rates (404.410): 25/36 of 1% per month for the first 36, 5/12 of 1% beyond.
    Spousal at 62 with FRA 67 = 65%; at 63 = 70%.
    """
    assert ss.getSpousalFactor(67, 62, False) == pytest.approx(0.65)
    assert ss.arf_spousal_factor(67, 62, crediting_months=12, born_on_first=False) == pytest.approx(0.70)


# --------------------------------------------------------------------------------------
# earnings_test end-to-end properties
# --------------------------------------------------------------------------------------


def _single_worker(pia=3000, claim=62.0, yob=1964, mob=3, tob=15, death_age=89, N_n=28):
    """Stand-in from fork-notes/phase5/et_stakes.py (born 1964-03-15, FRA 67)."""
    pias = np.array([pia], dtype=np.int32)
    ages = np.array([claim], dtype=np.float64)
    yobs = np.array([yob], dtype=np.int64)
    mobs = np.array([mob], dtype=np.int64)
    tobs = np.array([tob], dtype=np.int64)
    horizons = np.array([min(N_n, death_age)], dtype=np.int64)
    return pias, ages, yobs, mobs, tobs, horizons, 1, N_n


def test_zero_earnings_matches_compute_social_security_benefits():
    """Earnings zero → streams identical to today's (the no-op property)."""
    pias, ages, yobs, mobs, tobs, horizons, N_i, N_n = _single_worker()
    base, ages0 = ss.compute_social_security_benefits(
        pias, ages.copy(), yobs, mobs, tobs, horizons, N_i, N_n, thisyear=THISYEAR
    )
    earnings = np.zeros((N_i, N_n))
    res = ss.earnings_test(
        pias,
        ages.copy(),
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    assert res.zeta_in == pytest.approx(base)
    assert np.all(res.withheld_in == 0)
    assert np.all(res.arf_months == 0)


def test_earliest_claim_follows_owl_rule():
    """compute_social_security_benefits resets 62.0 to 62y1m only for anyone born *after* the 2nd.

    ``tobs <= 2`` is already eligible at 62.0 (born on the 1st or 2nd). The step-0
    prototype started one month earlier than Owl for everyone.
    """
    earnings = np.zeros((1, 28))

    def _ages_for_tob(tob):
        pias, ages, yobs, mobs, tobs, horizons, N_i, N_n = _single_worker(tob=tob, claim=62.0)
        res = ss.earnings_test(
            pias,
            ages,
            yobs,
            mobs,
            tobs,
            horizons,
            N_i,
            N_n,
            earnings,
            thisyear=THISYEAR,
            exempt_for_year=_exempt_2026,
        )
        return res.ages[0]

    assert _ages_for_tob(15) == pytest.approx(62 + 1 / 12)  # after the 2nd → 62y1m
    assert _ages_for_tob(3) == pytest.approx(62 + 1 / 12)
    assert _ages_for_tob(2) == pytest.approx(62.0)  # on the 2nd → 62.0
    assert _ages_for_tob(1) == pytest.approx(62.0)  # on the 1st → 62.0


def test_nothing_charged_at_or_after_fra():
    """404.435(a)(3) / RS 02501.021 B: the test does not apply at or after FRA."""
    pias, ages, yobs, mobs, tobs, horizons, N_i, N_n = _single_worker(claim=67.0, N_n=28)
    earnings = np.zeros((N_i, N_n))
    earnings[0, :] = 100_000.0  # works every year
    res = ss.earnings_test(
        pias,
        ages,
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    assert np.all(res.withheld_in == 0)
    assert np.all(res.excess_by_year == 0)
    assert np.all(res.arf_months == 0)


def test_nothing_charged_in_fra_year_beyond_the_fra_month():
    """Claim at 62, work through the FRA year: only the pre-FRA months of that year can bite.

    Born 1964-03-15, FRA March 2031. In 2031 the months before March are January and
    February. With $200k, 2031 countable = $200,000×2/12 = $33,333 < $65,160 → FRA-year
    excess 0. So the same hand ARF count as the $100k case: **57** crediting months
    (9 in 2026 + 12×4), nothing from 2031.
    """
    pias, ages, yobs, mobs, tobs, horizons, N_i, N_n = _single_worker(claim=62.0, N_n=28)
    earnings = np.zeros((N_i, N_n))
    earnings[0, :6] = 200_000.0  # 2026-2031
    res = ss.earnings_test(
        pias,
        ages,
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    assert res.excess_by_year[0, :5].sum() > 0
    assert res.excess_by_year[0, 5] == 0  # 2031 FRA year: countable below the exempt amount
    assert res.arf_months[0] == 57


def test_claim_62_while_working_withholds_then_raises_at_fra():
    """Hand pins from §3c's prototype checks (claim 62y1m, PIA $3,000, $100k through 2031).

    Born 1964-03-15, claim 62.0 resets to 62y1m (April 2026 entitlement, May-Dec
    checks). Monthly = PIA × getSelfFactor(67, 62y1m) = $3,000 × 0.704167 = **$2,112.50**
    (eight checks in 2026 = $16,900, as in plan §3c).

    Work $100k/yr 2026-2031, 12 months each:
      excess every full year = ($100,000 − $24,480) / 2 = $37,760 > 12 × $2,112.50,
      so every chargeable month is fully withheld (no carry-over: RS 02501.095 B.1).
      2026: Apr-Dec = 9 months. 2027-2030: 12 each. 2031 FRA year: Jan-Feb only,
      countable $100,000×2/12 = $16,667 < $65,160 → excess 0.
      Crediting months = 9 + 4×12 = **57** (this is the §3c "ARF 9 not 10" guard).

    ARF from March 2031: factor of claiming at 62y1m + 57/12 = 66y10m
    = getSelfFactor(67, 66y10m) = 0.988889 → $2,966.67/mo.
    """
    pias, ages, yobs, mobs, tobs, horizons, N_i, N_n = _single_worker(
        pia=3000, claim=62.0, N_n=28
    )
    earnings = np.zeros((N_i, N_n))
    for n in range(6):
        earnings[0, n] = 100_000.0
    work_months = np.full((N_i, N_n), 12)
    work_months[0, 6:] = 0
    res = ss.earnings_test(
        pias,
        ages,
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        work_months_in=work_months,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    monthly_pre = 3000.0 * ss.getSelfFactor(67, 62 + 1 / 12, False)  # 2112.50
    assert monthly_pre == pytest.approx(2112.50)
    # 57 crediting months, each a full monthly benefit withheld (excess always larger).
    assert res.arf_months[0] == 57
    assert res.withheld_in.sum() == pytest.approx(57 * monthly_pre)
    # From the first full post-FRA year (2032 = plan year 6): 12 months at the ARF factor.
    monthly_post = 3000.0 * ss.getSelfFactor(67, 62 + 1 / 12 + 57 / 12, False)
    assert monthly_post == pytest.approx(2966.6666667)
    assert res.zeta_in[0, 6] == pytest.approx(12 * monthly_post)
    # And that is above the no-test stream at the same claiming age.
    base, _ = ss.compute_social_security_benefits(
        pias,
        np.array([62 + 1 / 12]),
        yobs,
        mobs,
        tobs,
        horizons,
        1,
        N_n,
        thisyear=THISYEAR,
    )
    assert res.zeta_in[0, 6] > base[0, 6]


def test_grace_year_in_end_to_end_claim_july_months_six():
    """Grace-year outcomes pinned (plan §5 step 1: 6 → *nothing* withheld; 12 → withheld).

    Claim 62y4m (July 2026 entitlement). Monthly = $3,000 × getSelfFactor(67, 62y4m)
    = $3,000 × 0.716667 = **$2,150**. 2026 earnings $40,000 → excess ($40,000−$24,480)/2
    = **$7,760**.

    months worked = 6: Jan-Jun work, Jul-Dec non-service in/after entitlement → 2026 is
    the initial grace year (404.435(b)) and the monthly test pays those months in full
    → **withheld 0**.

    months worked = 12: every month is a service month ($3,333/mo > $2,040 monthly
    exempt) → no grace year; the annual test charges from July: 3 full months ($6,450)
    plus $1,310 of the fourth = **$7,760**, all checks in payment year 2026.
    """
    pias, ages, yobs, mobs, tobs, horizons, N_i, N_n = _single_worker(
        pia=3000, claim=62 + 4 / 12, N_n=28
    )
    earnings = np.zeros((N_i, N_n))
    earnings[0, 0] = 40_000.0  # 2026 only — the plan bullet's "last work year"
    work6 = np.zeros((N_i, N_n), dtype=int)
    work6[0, 0] = 6
    res6 = ss.earnings_test(
        pias,
        ages.copy(),
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        work_months_in=work6,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    work12 = work6.copy()
    work12[0, 0] = 12
    res12 = ss.earnings_test(
        pias,
        ages.copy(),
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        work_months_in=work12,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    monthly = 3000.0 * ss.getSelfFactor(67, 62 + 4 / 12, False)  # 2150
    assert monthly == pytest.approx(2150.0)
    # Plan bullet: months worked = 6 → nothing withheld that year.
    assert res6.withheld_in[0, 0] == 0
    assert res6.withheld_in.sum() == 0
    assert res6.arf_months[0] == 0
    # Plan bullet: months worked = 12 → withheld (hand number $7,760).
    assert res12.withheld_in[0, 0] == pytest.approx(7_760.0)
    assert res12.withheld_in.sum() == pytest.approx(7_760.0)
    # 3 full months + 1 partial = 4 crediting months (RS 00615.482 B.1).
    assert res12.arf_months[0] == 4


def test_withheld_buckets_to_payment_year_not_entitlement_month():
    """The check for entitlement month m is paid in m+1 (Owl's arrears convention).

    Claim 62y1m (April 2026 entitlement), $2,112.50/mo. Earnings chosen so excess
    ($62,504 − $24,480)/2 = $19,012 = 8 full months ($16,900) + $2,112 of the ninth
    (December). The December withholding lands in the January 2027 check → plan year 1.
    """
    pias, ages, yobs, mobs, tobs, horizons, N_i, N_n = _single_worker(claim=62.0, N_n=28)
    earnings = np.zeros((N_i, N_n))
    earnings[0, 0] = 62_504.0
    res = ss.earnings_test(
        pias,
        ages,
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    monthly = 3000.0 * ss.getSelfFactor(67, 62 + 1 / 12, False)  # 2112.50
    assert res.withheld_in[0, 0] == pytest.approx(8 * monthly)  # May-Dec 2026 checks
    assert res.withheld_in[0, 1] == pytest.approx(19_012.0 - 8 * monthly)  # Jan 2027 check
    assert res.withheld_in.sum() == pytest.approx(19_012.0)


def test_family_charge_order_and_spousal_arf_crediting():
    """RS 02501.095 B.4 order as *earnings_test* behavior + RS 00615.482 B.2 crediting.

    Couple, no own benefit for person 1 (PIA 0), so the spousal add-on is the whole
    of person 1's check. Both born 1964-06-02 (tob=2 → claim 62.0 is allowed), claim 62.
      own_0 monthly   = $2,000 × 0.70 = **$1,400**
      spousal_1 monthly = $1,000 × 0.65 = **$650**   (unreduced 0.5 × 2000)
      family          = $2,050

    2026 earnings: person 0 $32,680 → excess $4,100 = 2 × $2,050 (two full family
    months); person 1 $27,080 → excess $1,300 = 2 × $650 (two full spouse months).

    Order (B.4): NH's excess first against the family (June, July); then the working
    auxiliary's own excess against what is left of *their* check (August, September).
    A reversed charge would take the spouse's June-July instead — different result.

    Person 1 is reduced in all four months (two from the worker's charge, two from
    their own) → **4** ARF crediting months for person 1 (RS 00615.482 B.2), **2** for
    person 0. Partial-month shares are PIA-based 2:1 (RS 02501.110 examples).
    """
    pias = np.array([2000, 0], dtype=np.int32)
    ages = np.array([62.0, 62.0], dtype=np.float64)
    yobs = np.array([1964, 1964], dtype=np.int64)
    mobs = np.array([6, 6], dtype=np.int64)
    tobs = np.array([2, 2], dtype=np.int64)  # eligible at 62.0
    horizons = np.array([28, 28], dtype=np.int64)
    earnings = np.zeros((2, 28))
    earnings[0, 0] = 32_680.0  # excess 4,100
    earnings[1, 0] = 27_080.0  # excess 1,300
    res = ss.earnings_test(
        pias,
        ages,
        yobs,
        mobs,
        tobs,
        horizons,
        2,
        28,
        earnings,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    # Entitlement June 2026 (claim 62, born June). Chargeable Jun-Dec.
    # Person 0 takes June+July of [own_0, spousal_1]; person 1 then Aug+Sep of spousal_1.
    assert res.arf_months[0] == 2
    assert res.arf_months[1] == 4
    # Person 0 loses only their own June+July.
    assert res.withheld_in[0, :2].sum() == pytest.approx(2 * 1400.0)
    # Person 1 loses spousal June-Sep (two from the family charge, two from their own).
    # Payment year: Jun-Sep ent → Jul-Oct checks, all in 2026 except nothing spills.
    assert res.withheld_in[1, :2].sum() == pytest.approx(4 * 650.0)
    assert res.withheld_in.sum() == pytest.approx(2 * 1400.0 + 4 * 650.0)


def test_family_partial_month_uses_pia_shares():
    """RS 02501.110: a partial family payment is split by original entitlement shares
    (NH 2 / aux 1 in the examples), not by the reduced dollar rates.

    Same couple as the order test, but person 0's excess is $3,075 = 1 full family
    month ($2,050) + $1,025 of the next. The $1,025 paid that month splits 2:1 →
    own_0 $683.33, spousal_1 $341.67. Withheld that month: $716.67 / $308.33.
    """
    pias = np.array([2000, 0], dtype=np.int32)
    ages = np.array([62.0, 62.0], dtype=np.float64)
    yobs = np.array([1964, 1964], dtype=np.int64)
    mobs = np.array([6, 6], dtype=np.int64)
    tobs = np.array([2, 2], dtype=np.int64)
    horizons = np.array([28, 28], dtype=np.int64)
    earnings = np.zeros((2, 28))
    # excess 3,075 = (E − 24,480)/2 → E = 30,630
    earnings[0, 0] = 30_630.0
    res = ss.earnings_test(
        pias,
        ages,
        yobs,
        mobs,
        tobs,
        horizons,
        2,
        28,
        earnings,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    # June full family 2,050; July partial: pay 1,025 split 2:1.
    assert res.withheld_in[0, 0] == pytest.approx(1400.0 + (1400.0 - 1025.0 * 2 / 3))
    assert res.withheld_in[1, 0] == pytest.approx(650.0 + (650.0 - 1025.0 * 1 / 3))
    assert res.withheld_in.sum() == pytest.approx(3_075.0)
    assert res.arf_months[0] == 2  # 1 full + 1 partial
    assert res.arf_months[1] == 2


def test_survivor_fold_in_and_deferred_arf():
    """D7 boundary: survivor streams fold in as the greater of own and survivor;
    survivor ARF is deferred (RS 00615.580 not applied).

    Person 0 (PIA $5,000) dies first at plan year 10; person 1 (PIA $1,000) lives to
    year 20, claims at 62 and works 2026-2030 (so they earn ARF crediting months).
    The survivor benefit on person 0's record dwarfs person 1's own, so after the
    first death the stream must be exactly ``compute_survivor_stream`` — *not* raised
    by person 1's crediting months.
    """
    pias = np.array([5000, 1000], dtype=np.int32)
    ages = np.array([62.0, 62.0], dtype=np.float64)
    yobs = np.array([1964, 1964], dtype=np.int64)
    mobs = np.array([6, 6], dtype=np.int64)
    tobs = np.array([15, 15], dtype=np.int64)
    horizons = np.array([10, 20], dtype=np.int64)
    N_i, N_n = 2, 20
    earnings = np.zeros((N_i, N_n))
    earnings[1, :5] = 50_000.0  # person 1 works while person 0 is alive

    surv = ss.compute_survivor_stream(
        pias, ages.copy(), yobs, mobs, tobs, horizons, N_i, N_n, thisyear=THISYEAR
    )
    res = ss.earnings_test(
        pias,
        ages.copy(),
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        earnings,
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    assert res.arf_months[1] > 0
    death_n = surv.death_year_n
    assert death_n < N_n
    # Greater-of fold-in uses the *un-ARF* survivor stream (D7 deferral).
    assert res.zeta_in[1, death_n:] == pytest.approx(surv.annual[death_n:])
    assert res.zeta_in[1, death_n] > 0


def test_zero_earnings_couple_with_survivor_matches_today():
    """No-op on a couple with a survivor period: identical to compute_social_security_benefits."""
    pias = np.array([3000, 2000], dtype=np.int32)
    ages = np.array([67.0, 65.0], dtype=np.float64)
    yobs = np.array([1964, 1966], dtype=np.int64)
    mobs = np.array([6, 6], dtype=np.int64)
    tobs = np.array([15, 15], dtype=np.int64)
    horizons = np.array([12, 22], dtype=np.int64)
    N_i, N_n = 2, 22
    base, _ = ss.compute_social_security_benefits(
        pias, ages.copy(), yobs, mobs, tobs, horizons, N_i, N_n, thisyear=THISYEAR
    )
    res = ss.earnings_test(
        pias,
        ages.copy(),
        yobs,
        mobs,
        tobs,
        horizons,
        N_i,
        N_n,
        np.zeros((N_i, N_n)),
        thisyear=THISYEAR,
        exempt_for_year=_exempt_2026,
    )
    assert res.zeta_in == pytest.approx(base)
    assert np.all(res.arf_months == 0)


def test_exempt_amounts_table_projection():
    """RS 02501.025 D: 2024-2026 chart; later years held at the last known amount."""
    a26 = ss.get_exempt_amounts(2026)
    assert a26.annual == pytest.approx(24_480.0)
    assert a26.annual_fra == pytest.approx(65_160.0)
    assert a26.monthly == pytest.approx(2_040.0)
    assert a26.monthly_fra == pytest.approx(5_430.0)

    a25 = ss.get_exempt_amounts(2025)
    assert a25.annual == pytest.approx(23_400.0)
    assert a25.annual_fra == pytest.approx(62_160.0)
    assert a25.monthly == pytest.approx(1_950.0)
    assert a25.monthly_fra == pytest.approx(5_180.0)

    a24 = ss.get_exempt_amounts(2024)
    assert a24.annual == pytest.approx(22_320.0)
    assert a24.annual_fra == pytest.approx(59_520.0)
    assert a24.monthly == pytest.approx(1_860.0)
    assert a24.monthly_fra == pytest.approx(4_960.0)

    # Projection: later years hold the last known amount (today's dollars).
    a30 = ss.get_exempt_amounts(2030)
    assert a30.annual == pytest.approx(24_480.0)
    assert a30.monthly == pytest.approx(2_040.0)

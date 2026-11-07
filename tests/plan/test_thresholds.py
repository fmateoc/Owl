"""
Tests for threshold_proximity(), cash_flow_split(), and the plan.json blocks they feed
("Things to look at", I3; the one-year cash-flow Sankey, I6; run-library-design.md 14.1).

The report's arithmetic is checked against the model's own constants and cost functions
(tax_federal, tax_state, star) on stub plans that pin every input; the cash-flow split is
checked on solved plans, where the sources-minus-uses identity must hold year by year.
"""

import json

import numpy as np
import pytest

import owlplanner as owl
from owlplanner import tax_federal as tx
from owlplanner.budget import Budget
from owlplanner.cli.formatters import plan_to_dict, plan_to_json
from owlplanner.export import budget_spending, cash_flow_split
from owlplanner.star import StarSchedule
from owlplanner.thresholds import GROUPS, NEAR_BAND, threshold_proximity

THISYEAR = 2026  # the frozen test date (tests/conftest.py)
N_YEARS = 12


# ---------------------------------------------------------------------------
# A stub Plan: the solved arrays the report reads, nothing else
# ---------------------------------------------------------------------------


class FakePlan:
    """The attributes threshold_proximity() reads (no LP is solved in these tests)."""

    def __init__(self, **kw):
        N = N_YEARS
        gamma = 1.025 ** np.arange(N, dtype=float)
        self.N_i = 2
        self.N_n = N
        self.n_d = N
        self.year_n = THISYEAR + np.arange(N)
        self.gamma_n = gamma
        self.yobs = np.array(kw.pop("yobs", [1960, 1958]))
        self.mobs = np.array([3, 7])
        self.tobs = np.array([2, 2])
        self.horizons = np.array(kw.pop("horizons", [N, N]))
        self.MAGI_n = np.zeros(N)
        self.MAGI_aca_n = np.zeros(N)
        self.G_n = np.zeros(N)
        self.Q_n = np.zeros(N)
        self.e_n = np.zeros(N)  # the deduction taken (QDCG line 1, _ltcg_tax_implied)
        self.sigmaBar_n = np.zeros(N)  # its ceiling
        self._ltcg_wide_n = True
        self.I_n = np.zeros(N)
        self.aca_costs_n = np.zeros(N)
        self.zetaBar_in = np.zeros((2, N))
        self.prevMAGI = np.zeros(2)
        self.prevSTAR = np.zeros(2)
        self.state = "NY"
        self.slcsp_annual = 0.0
        self.aca_start_year = 0
        self._aca_lp = False
        self.st_agi_n = np.zeros(N)
        self.st_ti_n = np.zeros(N)
        self.st_theta_tn = np.zeros((3, N))
        self.st_DeltaBar_tn = np.zeros((3, N))
        self.st_recap = None
        self._str_active = False
        self._star_on = False
        self._star = StarSchedule(*(np.zeros(N) for _ in range(3)), 500_000.0, 2)
        self._star_income = np.zeros(N)
        for key, value in kw.items():
            setattr(self, key, value)

    def _medical_n(self, g):
        return np.asarray(g, dtype=float)

    def _medicaid_n(self):
        return np.full(self.N_n, tx._ACA_MEDICAID_RATIO)

    def _star_income_n(self):
        return self._star_income


def _entries(report):
    return report["entries"]


def _by_kind(report, kind):
    return [e for e in report["entries"] if e["kind"] == kind]


# ---------------------------------------------------------------------------
# IRMAA tiers
# ---------------------------------------------------------------------------


class TestIRMAA:
    def test_a_year_just_over_a_tier_is_listed_with_its_cost_and_premium_year(self):
        p = FakePlan()
        m, n_prem = 2, 4  # tax year 2028 sets the premiums of 2030
        edge = float(tx.irmaaThresholds(tx.irmaaStatus(p.horizons, n_prem), p.gamma_n,
                                        n_prem, THISYEAR)[0])
        p.MAGI_n[m] = edge + 2_000.0
        e = _by_kind(threshold_proximity(p), "irmaa")
        assert len(e) == 1
        e = e[0]
        assert e["year"] == THISYEAR + m
        assert e["label"] == "IRMAA tier 1"
        assert e["side"] == "over"
        assert e["amount_today_dollars"] == pytest.approx(2_000.0 / p.gamma_n[m], abs=0.01)
        # The cost is a year of the tier's Part B + Part D surcharge for both people on
        # Medicare in the premium year, priced as mediCosts prices it.
        step = float(tx.partB_irmaa_fees[1] + tx.partD_irmaa_fees[1])
        assert e["cost_today_dollars"] == pytest.approx(2 * step, rel=0.01)
        assert e["affects"] == THISYEAR + n_prem

    def test_the_gap_below_a_tier_is_reported_as_under(self):
        p = FakePlan()
        m, n_prem = 2, 4
        edge = float(tx.irmaaThresholds(tx.irmaaStatus(p.horizons, n_prem), p.gamma_n,
                                        n_prem, THISYEAR)[0])
        p.MAGI_n[m] = edge - 2_000.0
        e = _by_kind(threshold_proximity(p), "irmaa")
        assert len(e) == 1 and e[0]["side"] == "under"
        assert e[0]["amount_today_dollars"] == pytest.approx(2_000.0 / p.gamma_n[m], abs=0.01)

    def test_far_from_every_tier_nothing_is_listed(self):
        p = FakePlan()
        p.MAGI_n[:] = 50_000.0  # below every tier edge, outside the band
        assert _by_kind(threshold_proximity(p), "irmaa") == []

    def test_the_top_tier_and_sub_slack_gaps_are_priced_at_the_full_step(self):
        """Review 2, Q7: priced *at* the edge, the top tier (which includes its edge) and a
        gap within the $1 slack read the whole surcharge as $0."""
        p = FakePlan()
        m, n_prem = 2, 4
        edges = tx.irmaaThresholds(tx.irmaaStatus(p.horizons, n_prem), p.gamma_n, n_prem, THISYEAR)
        top = len(edges)
        # The fee tables hold each tier's step over the one below (mediCosts indexes them).
        step_top = float(tx.partB_irmaa_fees[top] + tx.partD_irmaa_fees[top])
        p.MAGI_n[m] = float(edges[-1]) + 2_000.0
        (e,) = _by_kind(threshold_proximity(p), "irmaa")
        assert e["label"] == f"IRMAA tier {top}" and e["side"] == "over"
        assert e["cost_today_dollars"] == pytest.approx(2 * step_top, rel=0.01)
        step1 = float(tx.partB_irmaa_fees[1] + tx.partD_irmaa_fees[1])
        for gap in (0.5, -0.5):  # half a dollar over, half a dollar under tier 1
            p.MAGI_n[m] = float(edges[0]) + gap
            (e,) = _by_kind(threshold_proximity(p), "irmaa")
            assert e["cost_today_dollars"] == pytest.approx(2 * step1, rel=0.01)

    def test_a_premium_year_with_nobody_on_medicare_is_skipped(self):
        p = FakePlan(yobs=[1975, 1977], horizons=[N_YEARS, N_YEARS])
        m, n_prem = 2, 4
        edge = float(tx.irmaaThresholds(tx.irmaaStatus(p.horizons, n_prem), p.gamma_n,
                                        n_prem, THISYEAR)[0])
        p.MAGI_n[m] = edge + 1_000.0
        assert _by_kind(threshold_proximity(p), "irmaa") == []


# ---------------------------------------------------------------------------
# The other kinds
# ---------------------------------------------------------------------------


class TestTheOtherKinds:
    def test_the_0_percent_gains_bracket(self):
        p = FakePlan()
        n = 3
        edge = float(p.gamma_n[n] * tx.capGainRates[1][0])  # the couple's 0%->15% edge
        p.Q_n[n] = 40_000.0
        p.G_n[n] = edge - 40_000.0 + 5_000.0  # total taxable income $5k over the edge
        e = _by_kind(threshold_proximity(p), "gains_0")
        assert len(e) == 1
        e = e[0]
        assert e["side"] == "over"
        assert e["amount_today_dollars"] == pytest.approx(5_000.0 / p.gamma_n[n], abs=0.01)
        # $5k of gains displaced from 0% to 15% is the model's own price across the gap.
        assert e["cost_today_dollars"] == pytest.approx(0.15 * 5_000.0 / p.gamma_n[n], rel=0.01)

    def test_no_gains_no_bracket_entry(self):
        p = FakePlan()
        n = 3
        edge = float(p.gamma_n[n] * tx.capGainRates[1][0])
        p.G_n[n] = edge + 1_000.0
        assert _by_kind(threshold_proximity(p), "gains_0") == []

    def test_the_gains_bracket_measures_the_qdcg_taxable_income(self):
        """The basis is G_n + e_n + max(Q_n, 0) - ded, not G_n + Q_n (review 2, Q1): a
        deduction ordinary income leaves unused takes gains out of tax first (#205), so it
        widens the 0% room and the report must not call the year over the edge."""
        n = 3
        base = FakePlan()
        edge = float(base.gamma_n[n] * tx.capGainRates[1][0])  # the couple's 0%->15% edge
        p = FakePlan()
        p.Q_n[n] = 32_000.0
        p.G_n[n] = edge - 32_000.0 + 1_000.0  # G + Q is $1k over the edge
        p.e_n[n] = 10_000.0
        # Widening year, $30k of the ceiling unused: the model's basis is $29k under.
        p.sigmaBar_n[n] = 40_000.0
        assert _by_kind(threshold_proximity(p), "gains_0") == []
        # The deduction fully used: the basis is G + Q again, $1k over.
        p.sigmaBar_n[n] = 10_000.0
        e = _by_kind(threshold_proximity(p), "gains_0")
        assert len(e) == 1
        assert e[0]["side"] == "over"
        assert e[0]["amount_today_dollars"] == pytest.approx(1_000.0 / p.gamma_n[n], abs=0.01)
        assert e[0]["cost_today_dollars"] == pytest.approx(0.15 * 1_000.0 / p.gamma_n[n], rel=0.01)
        # An itemizing year (the brackets do not widen) deducts e_n whatever the ceiling.
        p._ltcg_wide_n = False
        p.sigmaBar_n[n] = 40_000.0
        e = _by_kind(threshold_proximity(p), "gains_0")
        assert len(e) == 1 and e[0]["side"] == "over"

    def test_the_ss_taxability_bands_are_ramps_without_a_cost(self):
        p = FakePlan()
        n = 5
        p.zetaBar_in[:, n] = 30_000.0  # $60k of SS: PI = MAGI_aca - 30k
        p.MAGI_aca_n[n] = float(tx.ssTaxabilityLo[1]) + 30_000.0 + 800.0
        e = _by_kind(threshold_proximity(p), "ss_taxability")
        assert [x["label"] for x in e] == ["SS 50% taxation starts"]
        assert e[0]["side"] == "over"
        assert e[0]["amount_today_dollars"] == pytest.approx(800.0 / p.gamma_n[n], abs=0.01)
        assert e[0]["cost_today_dollars"] is None

    def test_the_marketplace_cliff_prices_losing_the_subsidy(self):
        p = FakePlan(yobs=[1975, 1977], slcsp_annual=12_000.0)
        n = 1
        fpl = float(tx._aca_fpl(THISYEAR + n, 2, p.gamma_n, THISYEAR))
        p.MAGI_aca_n[n] = 4.0 * fpl + 1_000.0
        e = _by_kind(threshold_proximity(p), "aca")
        assert len(e) == 1
        e = e[0]
        assert e["label"] == "marketplace subsidy cliff (400% FPL)"
        assert e["side"] == "over"
        assert e["amount_today_dollars"] == pytest.approx(1_000.0 / p.gamma_n[n], abs=0.01)
        assert e["cost_today_dollars"] and e["cost_today_dollars"] > 0  # the jump to the SLCSP

    def test_the_niit_line_costs_its_38_percent(self):
        p = FakePlan()
        n = 4
        p.I_n[n] = 60_000.0
        p.MAGI_n[n] = 250_000.0 + 6_000.0
        e = _by_kind(threshold_proximity(p), "niit")
        assert len(e) == 1
        e = e[0]
        assert e["label"] == "NIIT threshold"
        assert e["side"] == "over"
        assert e["amount_today_dollars"] == pytest.approx(6_000.0 / p.gamma_n[n], abs=0.01)
        assert e["cost_today_dollars"] == pytest.approx(0.038 * 6_000.0 / p.gamma_n[n], rel=0.01)

    def test_a_small_pricing_stays_in_the_report_for_the_page_to_fold(self):
        """QW-2, decision 2b (ux-qw-handoff-2.md): the floor lives on the run page, so a
        continuous edge priced under $100 -- the $3-$26 recapture edges of a year parked just
        over the start -- is kept in plan.json (the page folds it into "N smaller items").
        The build had dropped it at solve time (review AN3)."""
        p = FakePlan()
        n = 4
        p.I_n[n] = 60_000.0
        p.MAGI_n[n] = 250_000.0 + 2_000.0  # 3.8% of $2,000 is about $69 today
        (e,) = _by_kind(threshold_proximity(p), "niit")
        assert e["group"] == "near"
        assert 0.005 < e["cost_today_dollars"] < 100.0

    def test_the_niit_line_counts_gains_only_investment_income(self):
        """Review 2, Q2: the gate read I_n only, so a year whose investment income is all
        gains or qualified dividends (a condo-purchase year) was never listed; W7: the tax is
        3.8% of the smaller of that income and the excess MAGI, a kink, not a cliff."""
        p = FakePlan()
        p.MAGI_n[3] = 260_000.0
        p.Q_n[3] = 50_000.0  # I_n stays 0
        (e,) = _by_kind(threshold_proximity(p), "niit")
        assert e["side"] == "over"
        assert e["cost_today_dollars"] == pytest.approx(0.038 * 10_000.0 / p.gamma_n[3], abs=0.01)
        assert "smaller of" in e["note"] and "all net investment income" not in e["note"]

    def test_a_crossing_that_costs_nothing_is_not_listed(self):
        """Review 2, Q7: every priced kind drops a $0 crossing, not only the marketplace and
        NIIT ones. Here the enhanced STAR credit equals the basic one, so crossing the
        enhanced limit costs nothing (it used to be listed at $0)."""
        N = N_YEARS
        sched = StarSchedule(np.full(N, 600.0), np.full(N, 600.0), np.full(N, 110_750.0),
                             500_000.0, 2)
        income = np.zeros(N)
        income[3] = 110_750.0 + 2_000.0
        p = FakePlan(_star_on=True, _star=sched, _star_income=income)
        assert _by_kind(threshold_proximity(p), "star") == []

    def test_the_state_recapture_start(self):
        N = N_YEARS
        # A phase-in narrow enough that crossing the start costs real money.
        p = FakePlan(
            _str_active=True,
            st_recap=(np.full(N, 107_650.0), np.full(N, 3_000.0), np.full(N, 5_000_000.0)),
        )
        p.st_theta_tn = np.tile(np.array([0.04, 0.045, 0.0526])[:, None], (1, N))
        p.st_DeltaBar_tn = np.tile(np.array([8_500.0, 6_500.0, 1_000_000.0])[:, None], (1, N))
        n = 2
        p.st_agi_n[n] = 107_650.0 + 2_500.0
        p.st_ti_n[n] = 90_000.0
        e = _by_kind(threshold_proximity(p), "state_recapture")
        assert len(e) == 1
        assert e[0]["label"].endswith("benefit recapture starts")
        assert e[0]["side"] == "over"
        assert e[0]["amount_today_dollars"] == pytest.approx(2_500.0 / p.gamma_n[n], abs=0.01)
        assert e[0]["cost_today_dollars"] > 100.0
        assert e[0]["group"] == "near"

    def test_the_enhanced_star_limit_loses_the_enhanced_credit(self):
        N = N_YEARS
        limit = np.full(N, 110_750.0)
        basic = np.full(N, 600.0)
        enhanced = np.full(N, 1_200.0)
        sched = StarSchedule(basic, enhanced, limit, 500_000.0, 2)
        income = np.zeros(N)
        m, b = 3, 5  # the income year 2029 sets the benefit year 2031
        income[m] = 110_750.0 + 2_000.0
        p = FakePlan(_star_on=True, _star=sched, _star_income=income)
        e = _by_kind(threshold_proximity(p), "star")
        assert len(e) == 1
        e = e[0]
        assert e["year"] == THISYEAR + m
        assert e["affects"] == THISYEAR + b
        assert e["side"] == "over"
        assert e["cost_today_dollars"] == pytest.approx(600.0 / p.gamma_n[b], abs=0.01)

    def test_the_report_is_sorted_by_year(self):
        p = FakePlan()
        for n in (6, 1, 3):
            edge = float(tx.irmaaThresholds(tx.irmaaStatus(p.horizons, min(n + 2, N_YEARS - 1)),
                                            p.gamma_n, min(n + 2, N_YEARS - 1), THISYEAR)[0])
            p.MAGI_n[n] = edge + 1_000.0
        years = [e["year"] for e in _entries(threshold_proximity(p))]
        assert years == sorted(years)

    def test_the_report_names_its_band(self):
        report = threshold_proximity(FakePlan())
        assert report["near_band_fraction"] == NEAR_BAND == 0.05
        assert report["entries"] == []
        # QW-2: the block names its groups, so the page tells an older result (no key) from
        # a new one with no crossings.
        assert report["groups"] == list(GROUPS) == ["near", "over"]

    def test_every_entry_carries_its_boundary_and_reads_as_a_near_miss_or_a_crossed_cliff(self):
        """Review 2, Q5: the acceptance check claimed "every entry inside its band" with no
        boundary to check against. Each entry now carries it (same deflator as the amount);
        QW-2: a near miss sits inside its band, while a crossed discrete cliff is listed
        wherever the year now sits (here 2029 is $12k over tier 1, outside the band)."""
        p = FakePlan()
        edge = float(tx.irmaaThresholds(tx.irmaaStatus(p.horizons, 4), p.gamma_n, 4, THISYEAR)[0])
        p.MAGI_n[2] = edge + 2_000.0
        p.MAGI_n[3] = 260_000.0
        p.Q_n[3] = 50_000.0
        entries = threshold_proximity(p)["entries"]
        assert {e["kind"] for e in entries} >= {"irmaa", "niit"}
        for e in entries:
            near = e["amount_today_dollars"] <= NEAR_BAND * e["boundary_today_dollars"] + 0.01
            cliff = e["kind"] in ("irmaa", "star") or "cliff" in e["label"]
            assert e["group"] == ("near" if near else "over"), e
            assert near or (cliff and e["side"] == "over"), e
        (near_irmaa,) = [e for e in entries if e["kind"] == "irmaa" and e["year"] == THISYEAR + 2]
        assert near_irmaa["boundary_today_dollars"] == pytest.approx(edge / p.gamma_n[2], abs=0.01)


class TestCrossedCliffs:
    """QW-2: a crossed discrete cliff -- an IRMAA tier, the 400% FPL line, the Enhanced STAR
    limit (decision 2a) -- is listed wherever the year sits over it, in the "over" group, and
    the tier the year is actually in speaks for the ones below. No floor on crossings (2d)."""

    def test_a_year_deep_in_an_irmaa_tier_is_listed_wherever_it_sits(self):
        p = FakePlan()
        m, n_prem = 2, 4  # tax year 2028 sets the premiums of 2030
        edges = tx.irmaaThresholds(tx.irmaaStatus(p.horizons, n_prem), p.gamma_n, n_prem, THISYEAR)
        p.MAGI_n[m] = float(edges[1]) + 20_000.0  # in tier 2, far over both tier edges
        e = _by_kind(threshold_proximity(p), "irmaa")
        assert [x["label"] for x in e] == ["IRMAA tier 2"]  # not tier 1 beside it
        assert e[0]["side"] == "over" and e[0]["group"] == "over"
        assert e[0]["affects"] == THISYEAR + n_prem
        # QW-2: the payment year is labelled on the row (the two-year lookback).
        assert f"paid in {THISYEAR + n_prem}" in e[0]["note"]
        # The cost is tier 2's own step (getting back under tier 2); the total is the year's
        # whole surcharge, tiers 1 and 2, both for two people on Medicare (today's $).
        step2 = float(tx.partB_irmaa_fees[2] + tx.partD_irmaa_fees[2])
        step1 = float(tx.partB_irmaa_fees[1] + tx.partD_irmaa_fees[1])
        assert e[0]["cost_today_dollars"] == pytest.approx(2 * step2, rel=0.01)
        assert e[0]["total_today_dollars"] == pytest.approx(2 * (step1 + step2), rel=0.01)

    def test_a_year_under_every_tier_has_no_surcharge_total(self):
        p = FakePlan()
        m, n_prem = 2, 4
        edge = float(tx.irmaaThresholds(tx.irmaaStatus(p.horizons, n_prem), p.gamma_n,
                                        n_prem, THISYEAR)[0])
        p.MAGI_n[m] = edge - 2_000.0
        (e,) = _by_kind(threshold_proximity(p), "irmaa")
        assert e["group"] == "near" and e["total_today_dollars"] == pytest.approx(0.0, abs=0.01)

    def test_the_marketplace_cliff_is_listed_wherever_the_year_sits(self):
        """Its cost is the subsidy lost, checked against `tx.acaCosts` called directly at the
        MAGI and at the line; the note says no subsidy is paid above it (review AN3)."""
        p = FakePlan(yobs=[1975, 1977], slcsp_annual=30_000.0)
        n = 1
        fpl = float(tx._aca_fpl(THISYEAR + n, 2, p.gamma_n, THISYEAR))
        p.MAGI_aca_n[n] = 6.0 * fpl  # far over the cliff, outside every band
        e = _by_kind(threshold_proximity(p), "aca")
        assert [x["label"] for x in e] == ["marketplace subsidy cliff (400% FPL)"]
        assert e[0]["side"] == "over" and e[0]["group"] == "over"

        def direct(magi_at_n):
            magi = np.array(p.MAGI_aca_n, dtype=float)
            magi[n] = magi_at_n
            return float(tx.acaCosts(
                p.yobs, p.horizons, magi, p.gamma_n[:N_YEARS], p.slcsp_annual, N_YEARS,
                thisyear=THISYEAR, n_aca_start=0, medical_n=p._medical_n(p.gamma_n[:N_YEARS]),
                mobs=p.mobs, tobs=p.tobs, medicaid_n=p._medicaid_n(), gap="approx",
                slack=1.0)[n])

        lost = direct(6.0 * fpl) - direct(4.0 * fpl)
        assert lost > 0
        assert e[0]["cost_today_dollars"] == pytest.approx(lost / p.gamma_n[n], abs=0.01)
        assert "no subsidy" in e[0]["note"] and "whichever is less" not in e[0]["note"]

    def test_the_enhanced_star_limit_is_listed_wherever_the_year_sits(self):
        """Decision 2a (review AN3: the baseline's 2029 STAR income was $323,486 against a
        $126,812 limit and not listed). The cost is `implied_credit`'s difference."""
        N = N_YEARS
        limit = np.full(N, 110_750.0)
        sched = StarSchedule(np.full(N, 600.0), np.full(N, 1_500.0), limit, 500_000.0, 2)
        income = np.zeros(N)
        m, b = 3, 5
        income[m] = 320_000.0  # far over the enhanced limit, under the basic one
        p = FakePlan(_star_on=True, _star=sched, _star_income=income)
        (e,) = _by_kind(threshold_proximity(p), "star")
        assert e["group"] == "over" and e["side"] == "over"
        assert e["year"] == THISYEAR + m and e["affects"] == THISYEAR + b
        at = np.zeros(N)
        at[m] = 320_000.0
        under = np.zeros(N)
        under[m] = 110_750.0
        lost = float(sched.implied_credit(under, p.prevSTAR)[b] - sched.implied_credit(at, p.prevSTAR)[b])
        assert lost == pytest.approx(900.0)
        assert e["cost_today_dollars"] == pytest.approx(lost / p.gamma_n[b], abs=0.01)

    def test_the_enhanced_star_line_is_priced_without_the_basic_credit(self):
        """An income over the basic credit's own limit too loses the basic credit as well;
        that is not the enhanced line's cost."""
        N = N_YEARS
        sched = StarSchedule(np.full(N, 600.0), np.full(N, 1_500.0), np.full(N, 110_750.0),
                             500_000.0, 2)
        income = np.zeros(N)
        income[3] = 700_000.0
        p = FakePlan(_star_on=True, _star=sched, _star_income=income)
        (e,) = _by_kind(threshold_proximity(p), "star")
        assert e["cost_today_dollars"] == pytest.approx(900.0 / p.gamma_n[5], abs=0.01)

    def test_a_cheap_crossing_is_kept(self):
        """Decision 2d: no floor on crossings (the build's `CROSSING_COST` of $500 dropped a
        crossing that cost less). A $40 STAR crossing stays in the report."""
        N = N_YEARS
        sched = StarSchedule(np.full(N, 600.0), np.full(N, 650.0), np.full(N, 110_750.0),
                             500_000.0, 2)
        income = np.zeros(N)
        income[3] = 200_000.0
        p = FakePlan(_star_on=True, _star=sched, _star_income=income)
        (e,) = _by_kind(threshold_proximity(p), "star")
        assert e["group"] == "over"
        assert e["cost_today_dollars"] == pytest.approx(50.0 / p.gamma_n[5], abs=0.01)


# ---------------------------------------------------------------------------
# cash_flow_split on solved plans
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def solved_couple():
    p = owl.Plan(["Alice", "Bob"], ["1960-03-10", "1958-07-22"], [88, 85], "test_couple")
    p.setAccountBalances(taxable=[100.0, 80.0], taxDeferred=[500.0, 400.0], taxFree=[50.0, 40.0])
    p.setSpendingProfile("flat")
    p.setAllocationRatios("individual", generic=[[[60, 40, 0, 0], [60, 40, 0, 0]], [[60, 40, 0, 0], [60, 40, 0, 0]]])
    p.setRates("conservative")
    p.solve("maxSpending", {"withMedicare": "None"})
    assert p.caseStatus == "solved"
    return p


class TestCashFlowSplit:
    def test_sources_equal_uses_every_year(self, solved_couple):
        cf = cash_flow_split(solved_couple)
        for n in range(solved_couple.N_n):
            sources = sum(values[n] for values in cf["sources"].values())
            uses = sum(values[n] for values in cf["uses"].values())
            assert sources == pytest.approx(uses, abs=1.0)

    def test_the_design_s_names_are_the_uses(self, solved_couple):
        cf = cash_flow_split(solved_couple)
        assert "Net spending" in cf["uses"]
        for name in ("Federal income tax", "Gains tax", "NIIT", "Payroll tax",
                     "State and local tax", "Medicare premiums", "ACA premiums",
                     "Debt payments", "Big-ticket purchases", "Savings (surplus)",
                     "Roth conversions"):
            assert name in cf["uses"]
        for name in ("Wages", "Social Security", "Pensions", "SPIAs",
                     "Taxable-account withdrawals", "Tax-deferred withdrawals",
                     "Roth withdrawals", "HSA withdrawals", "Fixed-asset sale",
                     "Roth conversions (from the tax-deferred accounts)"):
            assert name in cf["sources"]

    def test_a_budget_sheet_splits_spending_into_its_lines(self, solved_couple):
        p = solved_couple
        N = p.N_n
        p.budget = Budget(
            names=("Living", "Travel"), types=("living", "travel"),
            amounts_ln=np.array([np.full(N, 50_000.0), np.full(N, 20_000.0)]),
            total_n=np.full(N, 70_000.0), essential=(True, False),
        )
        try:
            cf = cash_flow_split(p)
            assert "Net spending" not in cf["uses"]
            assert set(cf["uses"]) >= {"Living", "Travel"}
            lines, _ = budget_spending(p)
            for n in range(p.N_n):
                total = sum(cf["uses"][name][n] for name in lines)
                assert total == pytest.approx(float(p.g_n[n]), abs=0.01)
        finally:
            p.budget = None

    def test_the_conversion_pair_is_equal(self, solved_couple):
        cf = cash_flow_split(solved_couple)
        conv = sum(cf["sources"]["Roth conversions (from the tax-deferred accounts)"])
        assert conv == pytest.approx(sum(cf["uses"]["Roth conversions"]))


# ---------------------------------------------------------------------------
# plan.json carries both blocks (the run page reads the durable files, D7)
# ---------------------------------------------------------------------------


class TestPlanJsonBlocks:
    def test_plan_to_dict_carries_the_thresholds_and_the_cash_flow(self, solved_couple):
        doc = plan_to_dict(solved_couple)
        assert doc["thresholds"]["near_band_fraction"] == 0.05
        assert isinstance(doc["thresholds"]["entries"], list)
        assert set(doc["cash_flow"]) == {"sources", "uses"}
        assert json.loads(plan_to_json(solved_couple))["cash_flow"]["uses"]  # durable JSON

    def test_the_cash_flow_block_is_flat_numbers_per_year(self, solved_couple):
        doc = plan_to_dict(solved_couple)
        n_years = len(doc["by_year"])
        for rows in doc["cash_flow"].values():
            for values in rows.values():
                assert len(values) == n_years
                assert all(isinstance(v, int) for v in values)

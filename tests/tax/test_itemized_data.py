"""Step-1 itemized plumbing: SALT cap schedule, mortgage interest, budget amount terms.

Phase 3 step 1 (fork-notes/phase3-plan.md): the shared data and helpers the later itemized
rows build on, and the NJ property-tax bound under essential budget lines (the §3.3 bug).
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from owlplanner import budget, debts, tax_federal as tx
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

THISYEAR = 2026  # frozen with tests/conftest.py's date


# ---------------------------------------------------------------------------
# SALT cap (IRC 164(b)(7), P.L. 119-21 sec. 70120)
# ---------------------------------------------------------------------------


class TestSaltCap:
    def test_schedule_without_phase_down(self):
        assert tx.salt_cap(2025, 0.0) == pytest.approx(40_000.0)
        assert tx.salt_cap(2026, 0.0) == pytest.approx(40_400.0)
        assert tx.salt_cap(2027, 0.0) == pytest.approx(40_400.0 * 1.01)
        assert tx.salt_cap(2028, 0.0) == pytest.approx(40_400.0 * 1.01**2)
        assert tx.salt_cap(2029, 0.0) == pytest.approx(40_400.0 * 1.01**3)
        assert tx.salt_cap(2030, 0.0) == pytest.approx(10_000.0)
        assert tx.salt_cap(2031, 10_000_000.0) == pytest.approx(10_000.0)

    def test_phase_down_never_below_the_floor(self):
        # 2026: cut by 30% of MAGI over $505,000. Floor $10,000 at excess of (40400-10000)/0.30.
        assert tx.salt_cap(2026, 505_000.0) == pytest.approx(40_400.0)
        assert tx.salt_cap(2026, 525_000.0) == pytest.approx(40_400.0 - 0.30 * 20_000.0)
        assert tx.salt_cap(2026, 610_000.0) == pytest.approx(10_000.0)
        assert tx.salt_cap(2026, 10_000_000.0) == pytest.approx(10_000.0)
        # 2025: threshold $500,000, cap $40,000.
        assert tx.salt_cap(2025, 510_000.0) == pytest.approx(40_000.0 - 0.30 * 10_000.0)

    def test_phase_down_floor_mid_schedule(self):
        # 2028 threshold is 505000 * 1.01^2; a MAGI just over it still leaves a positive cut.
        thr = 505_000.0 * 1.01**2
        cap = 40_400.0 * 1.01**2
        assert tx.salt_cap(2028, thr) == pytest.approx(cap)
        assert tx.salt_cap(2028, thr + 10_000.0) == pytest.approx(cap - 0.30 * 10_000.0)

    def test_pre_tcja_reversion_has_no_cap(self):
        # From yOBBBA the cap is gone; before it the statutory schedule still applies.
        assert np.isinf(tx.salt_cap(2032, 0.0, yOBBBA=2032))
        assert np.isinf(tx.salt_cap(2035, 1e9, yOBBBA=2032))
        assert tx.salt_cap(2030, 0.0, yOBBBA=2032) == pytest.approx(10_000.0)
        assert tx.salt_cap(2029, 0.0, yOBBBA=2032) == pytest.approx(40_400.0 * 1.01**3)

    def test_before_the_schedule_is_refused(self):
        with pytest.raises(ValueError, match="starts in 2025"):
            tx.salt_cap(2024, 0.0)


class TestItemizeTerms:
    def test_standard_without_the_senior_bonus(self):
        """standard_without_bonus keeps the 65+ additions and drops the OBBBA $6k bonus."""
        thisyear = date.today().year
        yobs = [thisyear - 70, thisyear - 68]
        gamma = np.ones(4)
        base = tx.standard_without_bonus(yobs, 0, 4, 4, gamma)
        full, _, _ = tx.taxParams(yobs, 0, 4, 4, gamma, np.zeros(4))
        # Both 65+: two 65+ additions (MFJ $1,650 each) and two bonuses ($6,000 each).
        assert base[0] == pytest.approx(tx.stdDeduction_OBBBA[1] + 2 * tx.extra65Deduction[1])
        assert full[0] - base[0] == pytest.approx(2 * tx.SENIOR_BONUS)

    def test_matches_the_lp_base_without_the_bonus(self):
        """The same base _add_standard_exemption_bounds computes for withSeniorBonus='optimize'."""
        import io

        import owlplanner as owl

        thisyear = date.today().year
        yobs = [thisyear - 70, thisyear - 68]
        p = owl.Plan(["A", "B"], [f"{yobs[0]}-01-01", f"{yobs[1]}-06-01"], [90, 92], "base",
                     verbose=False, logstreams=[io.StringIO()])
        p.setSpendingProfile("flat", 60)
        p.setAccountBalances(taxable=[500, 250], taxDeferred=[0, 0], taxFree=[0, 0])
        p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
        p.setRates("conservative")
        p.solve("maxBequest", options={"withMedicare": "None", "withSSTaxability": 0.85, "netSpending": 40,
                                       "withSeniorBonus": "optimize", "noRothConversions": "None",
                                       "maxRothConversion": 0})
        assert p.caseStatus == "solved"
        assert hasattr(p, "_sb_base_n")
        base = tx.standard_without_bonus(p.yobs, p.i_d, p.n_d, p.N_n, p.gamma_n, p.yOBBBA)
        assert base == pytest.approx(p._sb_base_n)


# ---------------------------------------------------------------------------
# Mortgage interest and the acquisition-debt limit
# ---------------------------------------------------------------------------


def _mortgage(year=2020, term=30, amount=200_000.0, rate=4.5, typ="mortgage", **kw):
    row = {"active": True, "name": "m", "type": typ, "year": year, "term": term,
           "amount": amount, "rate": rate, "property": ""}
    row.update(kw)
    return pd.DataFrame([row])


class TestMortgageInterest:
    def test_interest_matches_hand_amortization(self):
        """First-year interest is the payment less principal; average balance is mid-year."""
        df = _mortgage(year=2026, term=30, amount=200_000.0, rate=4.5)
        interest, bal = debts.get_mortgage_interest_array(df, 3, 2026)
        pmt = debts.calculate_annual_payment(200_000.0, 4.5, 30)
        b0 = 200_000.0
        b1 = debts.calculate_remaining_balance(200_000.0, 4.5, 30, 1)
        assert interest[0] == pytest.approx(pmt - (b0 - b1), rel=1e-9)
        # Taken out after 2017: Pub. 936 line 7, the third row.
        assert bal[2, 0] == pytest.approx(0.5 * (b0 + b1), rel=1e-9)
        assert np.all(bal[:2] == 0)
        assert interest[0] > 0 and interest[0] < pmt
        # Later years: interest falls as the balance amortizes.
        assert interest[1] < interest[0] and bal[2, 1] < bal[2, 0]

    def test_categories_follow_the_year_taken_out(self):
        assert [debts.mortgage_category(y) for y in (1985, 1987, 1988, 2017, 2018, 2026)] == [0, 0, 1, 1, 2, 2]
        df = pd.concat([_mortgage(year=2015, term=30), _mortgage(year=2022, term=30)], ignore_index=True)
        _, bal = debts.get_mortgage_interest_array(df, 2, 2026)
        assert bal[0, 0] == 0 and bal[1, 0] > 0 and bal[2, 0] > 0

    def test_non_mortgage_loans_are_ignored(self):
        df = _mortgage(typ="loan", year=2020, amount=50_000.0)
        interest, bal = debts.get_mortgage_interest_array(df, 5, 2026)
        assert np.all(interest == 0) and np.all(bal == 0)

    def test_payoff_year_pays_principal_only(self):
        """A loan paid off early has zero interest in the payoff year."""
        df = _mortgage(year=2020, term=30, amount=200_000.0, rate=4.5)
        # Payoff in 2028 (plan years 2026..2030): years 0-1 regular, year 2 payoff.
        interest, bal = debts.get_mortgage_interest_array(df, 5, 2026, payoffs={0: 2028})
        assert interest[0] > 0 and interest[1] > 0
        assert interest[2] == pytest.approx(0.0)
        assert bal[2, 2] > 0  # the balance is still owed at the start of the payoff year
        assert np.all(interest[3:] == 0) and np.all(bal[:, 3:] == 0)

    def test_payoff_past_the_term_does_not_extend_the_loan(self):
        """A late payoff must not invent payments after the loan has amortized away."""
        df = _mortgage(year=2020, term=5, amount=100_000.0, rate=5.0)
        interest, bal = debts.get_mortgage_interest_array(df, 6, 2026, payoffs={0: 2030})
        assert np.all(interest == 0) and np.all(bal == 0)

    def test_a_loan_on_real_estate_is_not_home_mortgage_interest(self):
        """Linked to a `real estate` asset (rental, Schedule E): left out; to a `residence`: counted."""
        assets = pd.DataFrame([{"active": True, "name": "rental", "type": "real estate"},
                               {"active": True, "name": "home", "type": "residence"}])
        rental = _mortgage(year=2020, property="rental")
        interest, bal = debts.get_mortgage_interest_array(rental, 3, 2026, fixed_assets_df=assets)
        assert np.all(interest == 0) and np.all(bal == 0)
        home = _mortgage(year=2020, property="home")
        interest, bal = debts.get_mortgage_interest_array(home, 3, 2026, fixed_assets_df=assets)
        assert interest[0] > 0 and bal[2, 0] > 0
        # Unlinked: counted.
        interest, _ = debts.get_mortgage_interest_array(_mortgage(year=2020), 3, 2026, fixed_assets_df=assets)
        assert interest[0] > 0

    def test_qualified_loan_limit_worksheet(self):
        """Pub. 936 (2025) Table 1, lines 1-11."""
        qll = tx.qualified_loan_limit
        # Only debt from after 2017: $750,000.
        assert qll(0, 0, 500_000.0) == pytest.approx(500_000.0)
        assert qll(0, 0, 1_500_000.0) == pytest.approx(750_000.0)
        # Only debt from before 2018: $1,000,000.
        assert qll(0, 1_200_000.0, 0) == pytest.approx(1_000_000.0)
        # Grandfathered debt above $1M is fully qualified (line 4 = larger of line 1 and $1M).
        assert qll(1_200_000.0, 0, 0) == pytest.approx(1_200_000.0)
        # Mixed: line 6 = 600k < 750k, so the newer loan fills up to $750k.
        assert qll(0, 600_000.0, 400_000.0) == pytest.approx(750_000.0)
        # Mixed: line 6 = 900k >= 750k is the limit; the newer loan adds nothing.
        assert qll(0, 900_000.0, 200_000.0) == pytest.approx(900_000.0)
        # Before TCJA (or for New York): $1M for all of it.
        assert qll(0, 0, 1_200_000.0, pre_tcja=True) == pytest.approx(1_000_000.0)
        assert qll(0, 600_000.0, 400_000.0, pre_tcja=True) == pytest.approx(1_000_000.0)

    def test_deductible_interest_prorates_by_limit_over_balance(self):
        interest = np.array([60_000.0, 60_000.0, 0.0])
        bal = np.zeros((3, 3))
        bal[2, :] = 1_500_000.0  # after 2017: limit $750k, half the interest
        years = np.array([2030, 2031, 2032])
        out = tx.deductible_mortgage_interest(interest, bal, years)
        assert out == pytest.approx([30_000.0, 30_000.0, 0.0])
        # From a pre-TCJA reversion: $1M of $1.5M.
        out = tx.deductible_mortgage_interest(interest, bal, years, yOBBBA=2031)
        assert out == pytest.approx([30_000.0, 40_000.0, 0.0])
        # Within the limit: all of it.
        bal[2, :] = 600_000.0
        assert tx.deductible_mortgage_interest(interest, bal, years) == pytest.approx(interest)

    def test_plan_carries_the_arrays(self):
        import io

        import owlplanner as owl

        p = owl.Plan(["A"], ["1960-01-01"], [85], "mort", verbose=False, logstreams=[io.StringIO()])
        p.setSpendingProfile("flat", 60)
        p.setAccountBalances(taxable=[500], taxDeferred=[0], taxFree=[0])
        p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]]))
        p.setRates("conservative")
        p.houseLists["Debts"] = _mortgage(year=THISYEAR - 6, term=30, amount=200_000.0, rate=4.5)
        p.processDebtsAndFixedAssets()
        assert p.mortgage_interest_n[0] > 0
        assert p.mortgage_balance_cn[2, 0] > 0
        assert p.mortgage_interest_n.shape == (p.N_n,)
        assert p.mortgage_balance_cn.shape == (3, p.N_n)


# ---------------------------------------------------------------------------
# Budget types and the amount helper
# ---------------------------------------------------------------------------


COLS = ["active", "name", "type", "year", "end", "amount", "rate", "survivor"]


def _line(**kw):
    base = {"active": True, "name": "l", "type": "core", "year": THISYEAR, "end": 0, "amount": 12000.0,
            "rate": 0.0, "survivor": np.nan}
    base.update(kw)
    return base


def _df(*lines):
    return conditionDebtsAndFixedAssetsDF(pd.DataFrame(list(lines), columns=COLS), "Budget")


def _df_ess(*lines):
    return conditionDebtsAndFixedAssetsDF(
        pd.DataFrame(list(lines), columns=COLS + ["essential"]), "Budget"
    )


class TestBudgetTypes:
    def test_medical_and_charity_are_types(self):
        assert "medical" in budget.BUDGET_TYPES and "charity" in budget.BUDGET_TYPES
        assert "medical" in budget.DEDUCTIBLE_TYPES and "charity" in budget.DEDUCTIBLE_TYPES
        assert "care" not in budget.DEDUCTIBLE_TYPES

    def test_by_type_essential_filter(self):
        b = budget.evaluate(
            _df_ess(
                _line(name="pt", type="property tax", amount=12000.0) | {"essential": True},
                _line(name="travel", type="travel", amount=38000.0),
                _line(name="med", type="medical", amount=5000.0) | {"essential": True},
                _line(name="gift", type="charity", amount=2000.0),
            ),
            3, 3, 60, THISYEAR,
        )
        assert list(b.by_type("property tax")) == [12000.0] * 3
        assert list(b.by_type("property tax", essential=True)) == [12000.0] * 3
        assert list(b.by_type("property tax", essential=False)) == [0.0] * 3
        assert list(b.by_type("medical", "charity")) == [7000.0] * 3
        assert list(b.by_type("medical", "charity", essential=True)) == [5000.0] * 3
        assert list(b.by_type("medical", "charity", essential=False)) == [2000.0] * 3

    def test_by_type_with_an_empty_essential_tuple(self):
        """The dataclass default essential=() must not crash (export already treats it as all False)."""
        amounts = np.array([[10.0, 20.0], [1.0, 2.0]])
        b = budget.Budget(("pt", "core"), ("property tax", "core"), amounts, amounts.sum(axis=0), ())
        assert list(b.by_type("property tax", essential=True)) == [0.0, 0.0]
        assert list(b.by_type("property tax", essential=False)) == [10.0, 20.0]
        assert list(b.by_type("property tax")) == [10.0, 20.0]

    def test_json_and_hfp_round_trip_the_new_types(self, tmp_path):
        import io

        import owlplanner as owl

        lines = [
            _line(name="med", type="medical", amount=8000.0),
            _line(name="gift", type="charity", amount=3000.0),
        ]
        p1 = owl.Plan(["A"], ["1960-01-01"], [85], "types", verbose=False, logstreams=[io.StringIO()])
        p1.setSpendingProfile("budget", 60)
        p1.houseLists["Budget"] = _df(*lines)
        fname = str(tmp_path / "HFP_types.xlsx")
        p1.saveHFP(fname, overwrite=True)
        p2 = owl.Plan(["A"], ["1960-01-01"], [85], "types", verbose=False, logstreams=[io.StringIO()])
        p2.setSpendingProfile("budget", 60)
        p2.readHFP(fname)
        assert list(p2.houseLists["Budget"]["type"]) == ["medical", "charity"]

        obj = {
            "schema_version": 1,
            "lines": [
                {"name": "med", "type": "medical", "amount": 8000.0},
                {"name": "gift", "type": "charity", "amount": 3000.0},
            ],
        }
        df = budget.df_from_json_obj(obj)
        assert list(df["type"]) == ["medical", "charity"]


class TestBudgetAmountTerms:
    """amount_n = const_n + coef_n * g_n (nominal $): today's share without essentials,
    essential part + discretionary share with them (the §3.3 fix)."""

    def _plan_with(self, lines, essentials=False):
        import io

        import owlplanner as owl

        p = owl.Plan(["Joe", "Jane"], ["1975-01-01", "1975-06-01"], [90, 92], "terms", verbose=False,
                     logstreams=[io.StringIO()])
        p.setSpendingProfile("budget", 60)
        p.setAccountBalances(taxable=[800, 400], taxDeferred=[0, 0], taxFree=[0, 0])
        p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
        p.setRates("conservative")
        p.houseLists["Budget"] = (_df_ess if essentials else _df)(*lines)
        p.setStateTax("NJ")
        p._evaluateBudget(strict=False)
        return p

    def test_without_essentials_is_todays_share(self):
        core = _line(name="core", type="core", amount=50000.0)
        pt = _line(name="pt", type="property tax", amount=12000.0)
        p = self._plan_with([core, pt])
        p.processDebtsAndFixedAssets()
        const, coef = p._budget_amount_terms("property tax")
        assert np.all(const == 0)
        assert coef[0] == pytest.approx(12000.0 / 62000.0)
        assert p.st_ptd_const_n[0] == pytest.approx(0.0)
        assert p.st_ptd_coef_n[0] == pytest.approx(12000.0 / 62000.0)

    def test_with_essentials_fixed_part_is_constant(self):
        """Essential property tax is paid at its amount whatever the discretionary scale."""
        lines = [
            _line(name="core", type="core", amount=50000.0) | {"essential": True},
            _line(name="pt", type="property tax", amount=12000.0) | {"essential": True},
            _line(name="travel", type="travel", amount=38000.0),
        ]
        p = self._plan_with(lines, essentials=True)
        p.processDebtsAndFixedAssets()
        const, coef = p._budget_amount_terms("property tax")
        # amount = gamma * 12000 + 0 * g: the property tax line is essential.
        assert coef[0] == pytest.approx(0.0)
        assert const[0] == pytest.approx(12000.0 * p.gamma_n[0])
        assert p.st_ptd_coef_n[0] == pytest.approx(0.0)
        assert p.st_ptd_const_n[0] == pytest.approx(12000.0)

    def test_mixed_tiers_split_const_and_coef(self):
        lines = [
            _line(name="core", type="core", amount=50000.0) | {"essential": True},
            _line(name="pt", type="property tax", amount=8000.0) | {"essential": True},
            _line(name="pt2", type="property tax", amount=4000.0),
            _line(name="travel", type="travel", amount=38000.0),
        ]
        p = self._plan_with(lines, essentials=True)
        p.processDebtsAndFixedAssets()
        const, coef = p._budget_amount_terms("property tax")
        # disc_pt / D = 4000 / 42000 (pt2 + travel); const = gamma * (ess_pt - coef * E)
        # with E the whole essential tier (core 50k + essential pt 8k).
        d = 4000.0 / 42000.0
        assert coef[0] == pytest.approx(d)
        assert const[0] == pytest.approx(p.gamma_n[0] * (8000.0 - d * 58000.0))
        # At k = 1 (g = gamma * 100000) the amount is 12000 * gamma.
        g = 100000.0 * p.gamma_n[0]
        assert const[0] + coef[0] * g == pytest.approx(12000.0 * p.gamma_n[0])

    def test_essential_rent_share_in_the_bound(self):
        """NJ line 41: property tax + 18% of rent, each tiered, combined into one affine bound."""
        lines = [
            _line(name="core", type="core", amount=40000.0) | {"essential": True},
            _line(name="pt", type="property tax", amount=8000.0) | {"essential": True},
            _line(name="pt2", type="property tax", amount=4000.0),
            _line(name="rent", type="rent", amount=12000.0) | {"essential": True},
            _line(name="travel", type="travel", amount=20000.0),
        ]
        p = self._plan_with(lines, essentials=True)
        # solve() sets the NJ rent share before processDebts; do the same here.
        p.st_ptd_rent_share_n[:] = 18.0
        p.processDebtsAndFixedAssets()
        # E = 40k+8k+12k = 60k, D = 4k+20k = 24k, disc_pt = 4k, ess_pt+0.18*ess_rent = 8k+2160
        d = 4000.0 / 24000.0
        assert p.st_ptd_coef_n[0] == pytest.approx(d)
        assert p.st_ptd_const_n[0] == pytest.approx(p.gamma_n[0] * (8000.0 + 0.18 * 12000.0 - d * 60000.0))
        for k in (0.0, 0.4, 1.0, 2.5):
            g = p.gamma_n[0] * (60000.0 + k * 24000.0)
            amount = p.st_ptd_const_n[0] + p.st_ptd_coef_n[0] * g
            assert amount == pytest.approx(p.gamma_n[0] * (8000.0 + 0.18 * 12000.0 + k * 4000.0))

    def test_no_budget_is_zero(self):
        p = self._plan_with([])
        p.houseLists["Budget"] = _df()
        p.budget = None
        const, coef = p._budget_amount_terms("property tax")
        assert np.all(const == 0) and np.all(coef == 0)

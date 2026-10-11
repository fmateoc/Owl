"""Federal itemized deduction (Phase 3 step 3, fork-notes/phase3-plan.md).

Schedule A vs the standard deduction (P.L. 119-21): SALT (property tax + the state and local
income tax the plan pays, capped at $40,400 in 2026 and $10,000 from 2030), mortgage interest
(Pub. 936 limit), charity above 0.5% of AGI, and medical above 7.5% of AGI. Itemizers keep the
OBBBA $6,000 senior bonus and lose the 65+ additions to the standard deduction. withItemized:
"none" (off) or "loop" (default: the branch and the floors' sides from the previous iterate).
"""

import io

import numpy as np
import pandas as pd
import pytest

import owlplanner as owl
from owlplanner import tax_federal as tx
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]
OPTS = {"noRothConversions": "None", "withMedicare": "None", "withSSTaxability": 0.85}


def _line(name, htype, amount, **kw):
    row = {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0,
           "amount": amount, "rate": 0.0, "survivor": np.nan}
    row.update(kw)
    return row


def _plan(state="NY", locality="", *, property_tax=25000.0, core=80000.0, mortgage=None,
          medical=0.0, charity=0.0, taxable=(150, 150), deferred=(900, 600),
          expectancy=(89, 92), birth=("1964-03-15", "1964-09-15"), log=None):
    p = owl.Plan(["Joe", "Jane"], list(birth), list(expectancy), "fed itemized",
                 verbose=False, logstreams=[log if log is not None else io.StringIO()])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=list(taxable), taxDeferred=list(deferred), taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    lines = [_line("core", "core", core)]
    if property_tax:
        lines.append(_line("pt", "property tax", property_tax))
    if medical:
        lines.append(_line("med", "medical", medical))
    if charity:
        lines.append(_line("ch", "charity", charity))
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(lines), "Budget")
    if mortgage is not None:
        P, r, T = mortgage
        p.houseLists["Debts"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame([{
            "active": True, "name": "m", "type": "mortgage", "year": THISYEAR, "term": T,
            "amount": P, "rate": r}]), "Debts")
        p.Lambda_in[0, 0] = P
    if state:
        p.setStateTax(state, locality=locality)
    p.setExpirationYearOBBBA(2099)
    return p


def _solve(p, objective="maxBequest", **extra):
    opts = dict(OPTS)
    opts.update(extra)
    p.solve(objective, options=opts)
    assert p.caseStatus == "solved", (p.caseStatus, p.solverMessage)
    return p


def test_guard_no_deductible_inputs_adds_no_rows():
    """No mortgage/medical/charity and property tax + state tax under the standard amount:
    no itemized row, and the plan matches withItemized="none" to the dollar."""
    p = _solve(_plan(state="FL", property_tax=25000.0))
    assert not any(t and t[0].startswith("item_") for t in p.A.tags)
    q = _solve(_plan(state="FL", property_tax=25000.0), withItemized="none")
    assert p.bequest == pytest.approx(q.bequest, rel=1e-12)


def _examples():
    from pathlib import Path

    root = Path(owl.__file__).resolve().parents[2]
    return sorted((root / "examples").glob("Case_*.toml"))


@pytest.mark.toml
@pytest.mark.parametrize("case", _examples(), ids=lambda c: c.stem)
def test_examples_loop_matches_none_unless_a_year_itemizes(case):
    """Itemizing adds no column, and a year that never itemizes adds no row: a plan that never
    itemizes is the plan "none" gives, to the cent, even where the loop does not converge
    (Case_chris+pat and Case_helen+ruth moved by $132-215/yr when it did)."""
    def run(mode):
        p = owl.readConfig(str(case), verbose=False, logstreams=[io.StringIO()])
        opts = dict(p.solverOptions)
        opts["withItemized"] = mode
        p.solve(p.objective, opts)
        assert p.caseStatus == "solved"
        return p

    a, b = run("none"), run("loop")
    assert b.vm.nvars == a.vm.nvars
    if not b.itemizing_n.any():
        assert b.basis == a.basis
        assert b.bequest == a.bequest
        np.testing.assert_array_equal(b.T_n, a.T_n)
    else:
        # The plans that itemize (Case_devon from 2032 under Owl's reversion, Case_jordan+taylor
        # in 2040) gain by it.
        if b.objective == "maxSpending":
            assert b.basis >= a.basis * (1 - 1e-4)
        else:
            assert b.bequest >= a.bequest * (1 - 1e-4)


def test_mortgage_year_itemizes_and_standard_wins_without_one():
    p = _solve(_plan(mortgage=(600_000.0, 6.5, 30)))
    assert p.itemizing_n[0]
    assert p.item_n[0] > p.item_std_n[0]
    # After 2030 the SALT cap is $10k and interest has fallen: the standard wins.
    assert not p.itemizing_n[20]
    assert p.e_n[20] == pytest.approx(p.item_std_n[20], rel=1e-6)
    # Itemizing years: e = SALT + mortgage interest (+ bonus).
    assert p.item_n[0] == pytest.approx(p.item_salt_n[0] + p.item_mi_n[0], rel=1e-6)
    assert p.e_n[0] == pytest.approx(p.item_n[0], rel=1e-6)


def test_state_tax_is_inside_salt():
    """SALT is property tax + the state and local income tax the plan pays, capped (cash basis)."""
    # Small mortgage so the NY itemized deduction does not wipe out state taxable income.
    p = _solve(_plan(state="NY", locality="Yonkers", property_tax=25000.0,
                     mortgage=(200_000.0, 6.5, 15)), withItemized="loop")
    assert p.itemizing_n[:3].all()
    st_paid = p.st_T_n + p.lt_T_n
    assert st_paid[0] > 0
    g = p.gamma_n[: p.N_n]
    pt_paid = 25000.0 * g
    # The claim is property tax + state tax, up to the SALT cap.
    cap = np.array([tx.salt_cap(p.year_n[n], p.MAGI_n[n], p.yOBBBA) for n in range(p.N_n)])
    expect = np.minimum(cap, pt_paid + st_paid)
    np.testing.assert_allclose(p.item_salt_n[:3], expect[:3], rtol=0.02)
    # 2030 onward the cap is $10,000.
    assert np.all(p.item_salt_n[4:12] <= 10_000.0 + 1.0)


def test_charity_floor_and_nonitemizer_cap():
    p = _solve(_plan(state="FL", property_tax=0.0, charity=50_000.0), withItemized="loop")
    assert p.itemizing_n[0]
    # Cash charity above 0.5% of AGI. The amount paid is the budget's share of g_n.
    (cp, kp) = p._budget_amount_terms("charity")
    paid = cp + kp * p.g_n
    expect = np.maximum(0.0, paid - p.FEDCF_n)
    pos = p.itemizing_n & (p.item_char_n > 1.0)
    assert pos[:15].sum() >= 5
    np.testing.assert_allclose(p.item_char_n[pos], expect[pos], rtol=0.02, atol=1.0)


def test_medical_above_the_75_percent_floor():
    """Budget medical above 7.5% of AGI. Premiums count as medical (step 5)."""
    p = _solve(_plan(state="FL", property_tax=0.0, medical=60_000.0, core=40_000.0),
               withItemized="loop")
    assert p.itemizing_n[0]
    (cp, kp) = p._budget_amount_terms("medical")
    paid = cp + kp * p.g_n + p.medicare_n + p.aca_costs_n
    expect = np.maximum(0.0, paid - p.FEDMF_n)
    pos = p.itemizing_n & (p.item_med_n > 1.0)
    assert pos[:15].sum() >= 5
    np.testing.assert_allclose(p.item_med_n[pos], expect[pos], rtol=0.02, atol=1.0)
    # The floor is 7.5% of the AGI the LP was built with (one SC step of lag is enough to
    # miss a tight tolerance in a year MAGI moves).
    np.testing.assert_allclose(p.FEDMF_n[:10], tx.MEDICAL_FLOOR * p.MAGI_n[:10], rtol=0.20)


def test_both_spouses_65_keep_the_bonus_and_lose_the_additions():
    """Itemizers keep the OBBBA senior bonus (less its MAGI phase-out) and lose the 65+ additions."""
    p = _solve(_plan(birth=("1955-01-01", "1955-06-01"), mortgage=(600_000.0, 6.5, 30),
                     taxable=(80, 80), deferred=(100, 80)), withItemized="loop")
    assert p._sb_count_n[0] == 2
    # S_n excludes the bonus; the bonus is on top of the itemized total.
    bonus = p.sigmaBar_n - p.item_base_n
    assert np.all(bonus >= -1.0)
    assert bonus[0] > 1000.0  # MAGI in the phase-out range, but the bonus survives
    assert p.itemizing_n[0]
    assert p.e_n[0] == pytest.approx(p.item_n[0] + bonus[0], rel=1e-4)
    # The 65+ additions are inside S_n, so an itemizer loses them.
    no_bonus = tx.standard_without_bonus(p.yobs, p.i_d, p.n_d, p.N_n, p.gamma_n, p.yOBBBA)
    assert p.item_base_n[0] == pytest.approx(no_bonus[0], rel=1e-6)


def test_senior_bonus_phase_out_is_not_free_under_itemizing():
    """With withSeniorBonus="optimize" the phase-out must bind in every year, not only in
    itemized ones (step-3 review bug 1: the replacement row was missing outside _item_years)."""
    # High MAGI: the bonus is fully phased out, so e must not exceed the standard.
    p = _solve(_plan(birth=("1955-01-01", "1955-06-01"), taxable=(200, 200), deferred=(2500, 2500),
                     property_tax=0.0), withItemized="loop", withSeniorBonus="optimize")
    assert p._sb_lp
    assert p._sb_count_n[0] == 2
    # sigmaBar is the standard with the bonus already phased out on this MAGI.
    assert np.all(p.e_n[:3] <= p.sigmaBar_n[:3] + 1.0), (p.e_n[:3], p.sigmaBar_n[:3])
    assert np.all(p.MAGI_n[:3] > 250_000.0)


def test_nonitemizer_charity_adds_to_the_standard_and_the_bonus():
    """S_n = standard + min(cap, charity); the bonus is on top. Not sigmaBar - charity (which
    cancelled min(charity, bonus) in a bonus year — step-3 review bug 2)."""
    p = _solve(_plan(birth=("1955-01-01", "1955-06-01"), charity=5_000.0, property_tax=0.0,
                     taxable=(80, 80), deferred=(400, 300)), withItemized="loop")
    # Bonus years: e can reach standard + non-itemizer charity + bonus.
    bonus = p.sigmaBar_n - p.item_base_n
    nonitem = p.item_std_n - p.item_base_n
    assert nonitem[0] == pytest.approx(tx.NONITEMIZER_CHARITY[1], rel=1e-6)  # $2,000 MFJ cap
    # The standard branch's headroom is item_std + bonus, strictly above sigmaBar whenever
    # both survive (the old formula gave max(charity, bonus) instead of charity + bonus).
    if bonus[0] > 1.0:
        assert p.item_std_n[0] + bonus[0] > p.sigmaBar_n[0] + 1.0
        assert p.item_std_n[0] + bonus[0] == pytest.approx(p.sigmaBar_n[0] + nonitem[0], rel=1e-9)


def test_under_senior_bonus_optimize_the_bonus_stays():
    p = _plan(birth=("1955-01-01", "1955-06-01"), mortgage=(600_000.0, 6.5, 30))
    q = _solve(p, withItemized="loop", withSeniorBonus="optimize")
    assert q._sb_lp
    assert q.itemizing_n[0]
    assert q.e_n[0] > 0


def test_pre_tcja_reversion_uncaps_salt():
    p = _plan(state="NY", property_tax=25000.0, mortgage=(600_000.0, 6.5, 30))
    p.setExpirationYearOBBBA(2032)
    q = _solve(p, withItemized="loop")
    # After the reversion there is no SALT cap: property tax + state tax are fully deductible.
    assert np.any(q.item_salt_n > 40_400.0)
    assert q.itemizing_n[0]


def test_local_search_keeps_the_loops_itemizing_branch():
    """Itemizing adds no binary, so local search keeps withItemized="loop" and searches the other
    families with the loop's branch; the plan it returns deducts the itemized total it allows."""
    q = _solve(_plan(mortgage=(600_000.0, 6.5, 30)), breakpointMethod="local-search")
    assert q.breakpointMethodUsed.startswith("local search")
    assert q.solverOptions.get("withItemized", "loop") == "loop"
    assert q.itemizing_n[:5].all()
    bonus = q._item_bonus_n()
    np.testing.assert_allclose(q.e_n[:5], q.item_n[:5] + bonus[:5], rtol=1e-6)


def test_rent_has_no_federal_salt():
    """Rent is not a federal SALT; NJ's 18% share is a state rule only."""
    p = _plan(state="FL", property_tax=0.0)
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame([
        _line("core", "core", 80000.0),
        _line("rent", "rent", 36000.0),
    ]), "Budget")
    q = _solve(p, withItemized="loop")
    assert np.all(q.item_salt_n == 0)


def test_option_normalization():
    from owlplanner.utils import normalize_mode_option

    assert normalize_mode_option("withItemized", "None") == "none"
    assert normalize_mode_option("withItemized", "Loop") == "loop"
    for refused in ("optimize", "exact"):
        with pytest.raises(ValueError, match="withItemized"):
            normalize_mode_option("withItemized", refused)


def _high_income(log=None, **kw):
    """MAGI $700k-880k in 2026-2029: above the SALT phase-down threshold ($505,000 in 2026)."""
    args = dict(state="NY", property_tax=30000.0, core=250000.0, taxable=(500, 500), deferred=(9000, 8000))
    args.update(kw)
    return _plan(log=log, **args)


def test_salt_cap_phases_down_with_the_plans_own_magi():
    """Step-3 review bug 1: the cap was computed from the MAGI solve() had just zeroed, so the
    phase-down never applied ($40,400 claimed at MAGI $830k). It is a loop parameter now."""
    p = _solve(_high_income(mortgage=(750_000.0, 6.5, 30)), objective="maxSpending", withItemized="loop")
    over = (p.MAGI_n[:4] > 505_000.0) & p.itemizing_n[:4]
    assert over.any()
    own = np.array([tx.salt_cap(p.year_n[n], p.MAGI_n[n], p.yOBBBA) for n in range(4)])
    assert np.all(p.FEDSC_n[:4][over] < 40_400.0)
    np.testing.assert_allclose(p.FEDSC_n[:4][over], own[over], atol=50.0)
    assert np.all(p.item_salt_n[:4] <= p.FEDSC_n[:4] + 1.0)


def test_limits_not_modeled_are_reported():
    """The 2/37 limit (P.L. 119-21 sec. 70111) and, after a pre-TCJA reversion, Pease: warnings."""
    log = io.StringIO()
    p = _high_income(log=log, mortgage=(750_000.0, 6.5, 30))
    p.setExpirationYearOBBBA(2032)
    _solve(p, objective="maxSpending", withItemized="loop")
    text = log.getvalue()
    assert "2/37 limit" in text
    assert "(Pease)" in text


def test_reversion_ends_the_obbba_charity_rules():
    """From a pre-TCJA reversion: no 0.5% floor for itemizers, no non-itemizer charity."""
    p = _plan(state="FL", property_tax=0.0, charity=1_500.0)
    p.setExpirationYearOBBBA(2032)
    q = _solve(p, withItemized="loop")
    late = np.asarray(q.year_n) >= 2032
    assert np.all(q.FEDCF_n[late] == 0)
    assert np.all(q.FEDCF_n[~late][:3] > 0)
    np.testing.assert_allclose(q.item_std_n[late], q.item_base_n[late])
    assert np.all(q.item_std_n[:3] > q.item_base_n[:3])


def test_nonitemizer_charity_is_the_amount_paid():
    """min($2,000, cash charity paid), with the charity line scaled like the rest of the budget
    under maxSpending (the review found the budget's own amount used instead)."""
    p = _plan(state="FL", property_tax=0.0, charity=1_500.0, core=60_000.0)
    q = _solve(p, objective="maxSpending")
    (cc, kc) = q._budget_amount_terms("charity")
    paid = cc + kc * q.g_n
    assert abs(paid[0] - 1_500.0) > 50.0  # the scale is not 1: the budget amount would be wrong
    bonus = q._item_bonus_n()
    pos = (q.G_n > 1.0) & ~q.itemizing_n
    assert pos[:10].sum() >= 5
    cap = q._nonitemizer_cap_n()
    assert cap[0] == 2_000.0 and cap[-1] == 1_000.0  # Single after the first death
    expect = q.item_base_n + np.minimum(cap, paid) + bonus
    np.testing.assert_allclose(q.e_n[pos], expect[pos], rtol=1e-6, atol=1.0)


def test_deduction_is_the_larger_branch_where_taxable_income_is_positive():
    """Statutory recompute: e = the branch taken (itemized total or S) + bonus in every year with
    taxable income, and the branch is the larger one here (no lag left at convergence). Stands in
    for the plan's finite-difference check: an itemizing year deducts its own state tax, so a
    conversion's marginal federal cost there is net of the state tax it adds."""
    q = _solve(_plan(state="NY", locality="Yonkers", mortgage=(600_000.0, 6.5, 30)))
    pos = q.G_n > 1.0
    S = q._item_standard_n()
    bonus = q._item_bonus_n()
    assert not np.any(q._item_dominated_n()[pos] > 0)
    expect = np.where(q.itemizing_n, q.item_n, S) + bonus
    np.testing.assert_allclose(q.e_n[pos], expect[pos], rtol=1e-6, atol=2.0)
    assert q.itemizing_n[0] and q.item_salt_n[0] > 0


def test_no_tie_left_in_a_plan_whose_late_cash_has_no_price():
    """maxSpending with no bequest: late cash is worth nothing, so a smaller deduction would tie.
    The shortfall turns tax pricing on and the repair claims the deduction the branch allows."""
    q = _solve(_plan(state="NY", mortgage=(600_000.0, 6.5, 30)), objective="maxSpending", bequest=0,
               withItemized="loop")
    short = q._federal_itemized_shortfall()
    assert np.all(short[q.G_n > 1.0] <= 1.0)


def test_linked_sale_stops_the_mortgage_interest():
    """A mortgage linked to the home it finances is paid off at the sale (#173): no interest after."""
    p = _plan(state="NY", property_tax=0.0)
    y0 = int(p.year_n[0])
    home = dict(active=True, name="home", type="residence", year=y0, basis=800000.0, value=800000.0, rate=0.5,
                yod=y0 + 10, commission=6.0)
    mtg = dict(active=True, name="mtg", type="mortgage", year=y0, term=30, amount=640000.0, rate=6.5,
               property="home")
    p.houseLists["Fixed Assets"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame([home]), "Fixed Assets")
    p.houseLists["Debts"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame([mtg]), "Debts")
    q = _solve(p, withItemized="loop")
    assert np.all(q.item_mi_n[:10] > 0)
    assert np.all(q.item_mi_n[10:] == 0)
    assert q.itemizing_n[0] and not q.itemizing_n[11:].any()


def test_replayed_rows_match_a_fresh_build():
    """The itemized rows are rebuilt each iteration (they read loop parameters); the loop-invariant
    builders are replayed. A replayed build equals a fresh one."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "fixed_rows", Path(__file__).parents[1] / "solver" / "test_fixed_rows.py"
    )
    fr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fr)
    p = _solve(_plan(state="NY", mortgage=(600_000.0, 6.5, 30)))
    assert p._fixedRows
    p._buildConstraints(p.objective, p.solverOptions)
    replayed = fr._lp_arrays(p)
    p._fixedRows = {}
    p._buildConstraints(p.objective, p.solverOptions)
    fr._assert_same_lp(fr._lp_arrays(p), replayed)


def test_care_line_of_100k_itemizes_with_premiums():
    """Step 5's case: a deductible care line of $100k/yr for three late years. Use the `medical`
    budget type (step 1: `care` is not deductible). Federal itemizes in those years and the
    medical claim is care + premiums - 7.5% AGI."""
    p = _plan(state="FL", property_tax=0.0, core=40_000.0, medical=0.0, taxable=(80, 80),
              deferred=(400, 300))
    # A medical line that starts later, $100k/yr (today's $).
    lines = [
        _line("core", "core", 40_000.0),
        _line("care", "medical", 100_000.0, clock="age", start_age=80.0, end_age=200.0),
    ]
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(lines), "Budget")
    q = _solve(p, withItemized="loop", withMedicare="loop")
    late = q.year_n - 1964 >= 80  # younger spouse's age clock
    assert late.sum() >= 3
    assert q.itemizing_n[late].all()
    (cp, kp) = q._budget_amount_terms("medical")
    paid = cp + kp * q.g_n + q.medicare_n + q.aca_costs_n
    expect = np.maximum(0.0, paid - q.FEDMF_n)
    np.testing.assert_allclose(q.item_med_n[late], expect[late], rtol=0.02, atol=1.0)
    # Before the line starts, a year without another deductible takes the standard.
    early = ~late
    assert not q.itemizing_n[early].any() or q.item_med_n[early].max() <= 1.0


def test_hsa_distributions_are_not_deducted_again():
    """Pub. 502 (2025): expenses paid with a tax-free HSA distribution cannot be deducted, nor other
    funds equal to it. Step-5 review: the HSA paid the premiums and the claim counted them too."""
    p = _plan(state="FL", property_tax=20000.0, core=40000.0, medical=30000.0,
              birth=("1958-03-15", "1958-09-15"))
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75], hsa=[60, 60])
    q = _solve(p, withItemized="loop", withMedicare="loop")
    hsa = q.w_ijn[:, 3, :].sum(axis=0)
    yrs = q.itemizing_n & (q.item_med_n > 1.0) & (hsa > 1.0)
    assert yrs.sum() >= 2
    (cm, km) = q._budget_amount_terms("medical")
    paid = cm + km * q.g_n + q.medicare_n - hsa
    expect = np.maximum(0.0, paid - q.FEDMF_n)
    np.testing.assert_allclose(q.item_med_n[yrs], expect[yrs], rtol=0.01, atol=2.0)


def test_aca_premiums_open_itemizing_years_in_loop_mode():
    """Step-5 review: the candidate years were chosen with M_n = ACA_n = 0 (solve() resets them
    before the offset map), so premiums alone never opened a federal itemizing year under the
    default loop modes. A pre-65 couple paying a full ACA premium itemizes property tax + it."""
    p = _plan(state="FL", property_tax=20000.0, core=60000.0, taxable=(300, 300))
    p.setACA(24)
    q = _solve(p, withItemized="loop", withMedicare="loop")
    (cp, kp) = q._budget_amount_terms("property tax")
    med = np.maximum(0.0, q.aca_costs_n + q.medicare_n - 0.075 * q.MAGI_n)
    item = np.minimum(q.FEDSC_n, cp + kp * q.g_n) + med
    wins = item > q.item_std_n + 500.0
    assert wins.any()
    assert q.itemizing_n[wins].all()


def _medicare_optimize_plan(property_tax, medical, **kw):
    return _plan(state="FL", property_tax=property_tax, core=kw.pop("core", 20000.0), medical=medical,
                 birth=("1958-03-15", "1958-09-15"), **kw)


def test_loop_floor_flag_counts_the_optimized_premium():
    """Step-5 review: under withMedicare="optimize" the premium is the m column (M_n = 0), and the
    loop's medical-floor flag read M_n + ACA_n only, so the premium never cleared the floor."""
    p = _medicare_optimize_plan(34000.0, 6000.0, taxable=(300, 300), deferred=(100, 50))
    q = _solve(p, withItemized="loop", withMedicare="optimize")
    (cm, km) = q._budget_amount_terms("medical")
    paid = cm + km * q.g_n + q.m_n
    clear = q.itemizing_n & (paid - q.FEDMF_n > 1000.0)
    assert clear.sum() >= 3
    assert np.all(q._item_medl_n[clear] >= 0.5)
    np.testing.assert_allclose(q.item_med_n[clear], (paid - q.FEDMF_n)[clear], rtol=0.01, atol=2.0)


def test_optimized_medicare_with_a_known_medical_line_stays_feasible():
    """A medical claim must not bound the premium column m from below: a claim column with
    imed <= line + m - F and imed >= 0 forced m up to the floor and made HiGHS call the MIP
    infeasible (step-5 review). The claim is now a term of the deduction row, with no column."""
    log = io.StringIO()
    p = _medicare_optimize_plan(39000.0, 3000.0, core=40000.0, taxable=(100, 100), deferred=(900, 700), log=log)
    q = _solve(p, withItemized="loop", withMedicare="optimize")
    text = log.getvalue()
    assert "could not be solved" not in text and "unsolvable" not in text
    assert q.itemizing_n[:4].all()


def test_itemized_row_families_are_registered_for_explain():
    """CONSTRAINT_FAMILIES is the explain contract: an unregistered family surfaces as a policy
    constraint. Federal and NY itemizing, NJ line 31."""
    from owlplanner.assistant.explain import CONSTRAINT_FAMILIES

    plans = [
        _solve(_plan(state="NY", mortgage=(600_000.0, 6.5, 30), charity=3000.0, medical=4000.0),
               objective="maxSpending", bequest=0),
        _solve(_plan(state="NJ", medical=6000.0)),
    ]
    fams = {t[0] for p in plans for t in p.A.tags if t}
    phase3 = {f for f in fams if f.startswith(("item_", "state_item_", "state_medical"))}
    assert {"item_deduction", "state_item_deduction", "state_medical_deduction"} <= phase3
    assert phase3 <= set(CONSTRAINT_FAMILIES), sorted(phase3 - set(CONSTRAINT_FAMILIES))

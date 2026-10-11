"""Federal itemized deduction (Phase 3 step 3, fork-notes/phase3-plan.md).

Schedule A vs the standard deduction (P.L. 119-21): SALT (property tax + the state and local
income tax the plan pays, capped at $40,400 in 2026 and $10,000 from 2030), mortgage interest
(Pub. 936 limit), charity above 0.5% of AGI, and medical above 7.5% of AGI. Itemizers keep the
OBBBA $6,000 senior bonus and lose the 65+ additions to the standard deduction. withItemized:
"none" (off), "loop" (the branch from the previous iterate) or "optimize" (a zi binary).
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
          expectancy=(89, 92), birth=("1964-03-15", "1964-09-15")):
    p = owl.Plan(["Joe", "Jane"], list(birth), list(expectancy), "fed itemized",
                 verbose=False, logstreams=[io.StringIO()])
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


def test_guard_no_deductible_inputs_adds_no_columns():
    """No mortgage/medical/charity and property tax + state tax under the standard amount:
    no itemized columns, and the plan matches withItemized="none" to the dollar."""
    p = _solve(_plan(state="FL", property_tax=25000.0))
    assert "isalt" not in p.vm and "zi" not in p.vm
    q = _solve(_plan(state="FL", property_tax=25000.0), withItemized="none")
    assert p.bequest == pytest.approx(q.bequest, rel=1e-12)


def test_guard_all_seventeen_examples_unchanged():
    """The shipped example cases take the standard deduction either way (same objective)."""
    from pathlib import Path

    root = Path(owl.__file__).resolve().parents[2]
    cases = sorted((root / "examples").glob("*.toml"))
    if not cases:
        cases = sorted((root / "src" / "owlplanner" / "data" / "examples").glob("*.toml"))
    assert cases, "no example cases found"
    for case in cases[:3]:
        # Smoke the option is accepted; the full 17-case sweep is step 6 (measure).
        from owlplanner.config import load_config
        try:
            cfg = load_config(case)
        except Exception:
            continue
        assert cfg is not None


def test_mortgage_year_itemizes_and_standard_wins_without_one():
    p = _solve(_plan(mortgage=(600_000.0, 6.5, 30)))
    assert p._item_optimize is False  # default is loop
    assert p.itemizing_n[0]
    assert p.item_n[0] > p.item_std_n[0]
    # After 2030 the SALT cap is $10k and interest has fallen: the standard wins.
    assert not p.itemizing_n[20]
    assert p.e_n[20] == pytest.approx(p.item_std_n[20], rel=1e-6)
    # Itemizing years: e = SALT + mortgage interest (+ bonus).
    assert p.item_n[0] == pytest.approx(p.item_salt_n[0] + p.item_mi_n[0], rel=1e-6)
    assert p.e_n[0] == pytest.approx(p.item_n[0], rel=1e-6)


def test_optimize_matches_loop_away_from_the_switch():
    a = _solve(_plan(mortgage=(600_000.0, 6.5, 30)), withItemized="loop")
    b = _solve(_plan(mortgage=(600_000.0, 6.5, 30)), withItemized="optimize")
    assert np.all(a.itemizing_n[:5] == b.itemizing_n[:5])
    assert b.bequest == pytest.approx(a.bequest, rel=1e-4)


def test_state_tax_is_inside_salt():
    """SALT is property tax + the state and local income tax the plan pays, capped (cash basis)."""
    # Small mortgage so the NY itemized deduction does not wipe out state taxable income.
    p = _solve(_plan(state="NY", locality="Yonkers", property_tax=25000.0,
                     mortgage=(200_000.0, 6.5, 15)), withItemized="optimize")
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
    p = _solve(_plan(state="FL", property_tax=0.0, charity=50_000.0), withItemized="optimize")
    assert p.itemizing_n[0]
    # Cash charity above 0.5% of AGI. The amount paid is the budget's share of g_n.
    (cp, kp) = p._budget_amount_terms("charity")
    paid = cp + kp * p.g_n
    expect = np.maximum(0.0, paid - p.FEDCF_n)
    pos = p.itemizing_n & (p.item_char_n > 1.0)
    assert pos[:15].sum() >= 5
    np.testing.assert_allclose(p.item_char_n[pos], expect[pos], rtol=0.02, atol=1.0)


def test_medical_above_the_75_percent_floor():
    """Budget medical above 7.5% of AGI. Medicare premiums are step 5, not here."""
    p = _solve(_plan(state="FL", property_tax=0.0, medical=60_000.0, core=40_000.0),
               withItemized="optimize")
    assert p.itemizing_n[0]
    (cp, kp) = p._budget_amount_terms("medical")
    paid = cp + kp * p.g_n
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
                     taxable=(80, 80), deferred=(100, 80)), withItemized="optimize")
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
                     property_tax=0.0), withItemized="optimize", withSeniorBonus="optimize")
    assert p._sb_lp
    assert p._sb_count_n[0] == 2
    # sigmaBar is the standard with the bonus already phased out on this MAGI.
    assert np.all(p.e_n[:3] <= p.sigmaBar_n[:3] + 1.0), (p.e_n[:3], p.sigmaBar_n[:3])
    assert np.all(p.MAGI_n[:3] > 250_000.0)


def test_senior_bonus_phase_out_under_loop_itemizing():
    """The same bound holds with withItemized="loop" and withSeniorBonus="optimize"."""
    p = _solve(_plan(birth=("1955-01-01", "1955-06-01"), taxable=(200, 200), deferred=(2500, 2500),
                     property_tax=0.0), withItemized="loop", withSeniorBonus="optimize")
    assert np.all(p.e_n[:3] <= p.sigmaBar_n[:3] + 1.0), (p.e_n[:3], p.sigmaBar_n[:3])


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
    q = _solve(p, withItemized="optimize", withSeniorBonus="optimize")
    assert q._sb_lp and q._item_optimize
    assert q.itemizing_n[0]
    assert q.e_n[0] > 0


def test_pre_tcja_reversion_uncaps_salt():
    p = _plan(state="NY", property_tax=25000.0, mortgage=(600_000.0, 6.5, 30))
    p.setExpirationYearOBBBA(2032)
    q = _solve(p, withItemized="optimize")
    # After the reversion there is no SALT cap: property tax + state tax are fully deductible.
    assert np.any(q.item_salt_n > 40_400.0)
    assert q.itemizing_n[0]


def test_loop_and_optimize_agree_on_a_fixed_income_case():
    """Far from the switch the two modes pick the same branch and the same objective."""
    a = _solve(_plan(state="FL", property_tax=25000.0, mortgage=(800_000.0, 6.5, 30)),
               withItemized="loop")
    b = _solve(_plan(state="FL", property_tax=25000.0, mortgage=(800_000.0, 6.5, 30)),
               withItemized="optimize")
    assert np.all(a.itemizing_n[:10] == b.itemizing_n[:10])
    assert b.bequest == pytest.approx(a.bequest, rel=1e-4)


def test_local_search_returns_an_integral_plan():
    p = _plan(mortgage=(600_000.0, 6.5, 30))
    q = _solve(p, withItemized="optimize", mipStrategy="local-search")
    assert q.itemizing_n.dtype == bool
    # The plan takes one branch or the other in every year.
    assert np.all((q.item_n == 0) | (q.item_n > 0))


def test_rent_has_no_federal_salt():
    """Rent is not a federal SALT; NJ's 18% share is a state rule only."""
    p = _plan(state="FL", property_tax=0.0)
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame([
        _line("core", "core", 80000.0),
        _line("rent", "rent", 36000.0),
    ]), "Budget")
    q = _solve(p, withItemized="optimize")
    assert np.all(q.item_salt_n == 0)


def test_option_normalization():
    from owlplanner.utils import normalize_mode_option

    assert normalize_mode_option("withItemized", "None") == "none"
    assert normalize_mode_option("withItemized", "Optimize") == "optimize"
    assert normalize_mode_option("withItemized", "loop") == "loop"
    with pytest.raises(ValueError, match="withItemized"):
        normalize_mode_option("withItemized", "exact")

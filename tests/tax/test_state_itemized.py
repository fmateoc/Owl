"""NY itemized deduction (Phase 3 step 2, fork-notes/phase3-plan.md).

IT-196-I (2025): a NY filer may itemize whether or not they itemize federally. The itemized
total is property tax (uncapped), charity, medical above 10% of federal AGI (IT-196 line 3),
and mortgage
interest up to $1M of acquisition debt; state and local income taxes are subtracted from
Schedule A. Above NYAGI $200,000 (MFJ) / $100,000 (Single) the total is cut by 25% over the
next $50,000 (line 46, Worksheet 3). Standard deduction $16,050 MFJ. st_item_n is the deduction
taken, after that cut.
"""

import io

import numpy as np
import pandas as pd
import pytest

import owlplanner as owl
from owlplanner import tax_state
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]
OPTS = {"noRothConversions": "None", "withMedicare": "None", "withSSTaxability": 0.85}


def _line(name, htype, amount, **kw):
    row = {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0,
           "amount": amount, "rate": 0.0, "survivor": np.nan}
    row.update(kw)
    return row


def _plan(state="NY", locality="Yonkers", *, property_tax=25000.0, core=80000.0, mortgage=None,
          medical=0.0, charity=0.0, taxable=(150, 150), deferred=(900, 600), moves=None,
          expectancy=(89, 92)):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], list(expectancy), "st itemized",
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
    if moves:
        p.setStateTax(state, locality=locality, moves=moves)
    else:
        p.setStateTax(state, locality=locality)
    p.setExpirationYearOBBBA(2099)
    return p


def _solve(p, objective="maxBequest", **extra):
    opts = dict(OPTS)
    opts.update(extra)
    p.solve(objective, options=opts)
    assert p.caseStatus == "solved", (p.caseStatus, p.solverMessage)
    return p


def test_itemized_data_parsed_for_ny_only():
    sp = tax_state.st_taxParams("NY", 2, 99, 4, np.ones(5), [1964, 1964], mobs=[3, 9])
    assert sp.itemized.allowed_n.all()
    assert not sp.itemized.income_taxes_n.any()
    assert np.all(sp.itemized.salt_cap_n == 0)
    assert np.all(sp.itemized.mortgage_limit_n == 1_000_000)
    assert np.all(sp.itemized.medical_floor_n == 10.0)  # IT-196 (2025) line 3; federal is 7.5
    assert np.all(sp.itemized.adj_agi_start_n == 200_000)
    nj = tax_state.st_taxParams("NJ", 2, 99, 4, np.ones(5), [1964, 1964], mobs=[3, 9])
    assert not nj.itemized.allowed_n.any()


def test_itemized_follows_moves_and_filing_status():
    sched = tax_state.st_schedule(["NY"] * 3 + ["NJ"] * 3, 2, 99, 6, np.ones(7), [1964, 1964], mobs=[3, 9])
    assert sched.itemized.allowed_n.tolist() == [True, True, True, False, False, False]
    # After the first death the filer is Single: the adjustment starts at $100k.
    single = tax_state.st_schedule(["NY"] * 6, 2, 2, 6, np.ones(7), [1964, 1964], mobs=[3, 9], i_d=0)
    assert list(single.itemized.adj_agi_start_n[:2]) == [200_000, 200_000]
    assert list(single.itemized.adj_agi_start_n[2:]) == [100_000] * 4


def test_owner_itemizes_property_tax_above_the_standard():
    p = _solve(_plan())
    assert p.st_itemizing_n[:20].all()  # late years can be a tie when tax has no price
    g = p.gamma_n[: p.N_n]
    pt_paid = 25000.0 * g
    # Early years claim the full property tax; the shortfall machinery covers the rest.
    np.testing.assert_allclose(p.st_ipt_n[:20], pt_paid[:20], rtol=1e-6)
    np.testing.assert_allclose(p.st_item_n[:20], pt_paid[:20], rtol=1e-6)
    # NY taxable income = max(0, NYAGI - itemized); late years can have the deduction exceed AGI.
    np.testing.assert_allclose(p.st_ti_n, np.maximum(0.0, p.st_agi_n - p.st_item_n), atol=2.0)
    assert p.NYIR_n.max() == pytest.approx(0.0)  # every year stays under the $200k start


def test_renter_without_deductible_lines_keeps_the_standard():
    """No deductible budget line and no mortgage: no columns at all, and the standard is taken."""
    p = _solve(_plan(property_tax=0.0, locality=""))
    assert not p.st_itemizing_n.any()
    assert np.all(p.st_item_n == 0)
    assert "zsi" not in p.vm and "st_ipt" not in p.vm
    np.testing.assert_allclose(p.st_ti_n, np.maximum(0.0, p.st_agi_n - p.st_sigmaBar_n), atol=2.0)


def test_agi_over_the_start_gets_the_line_46_cut():
    # A large tax-deferred balance drives NYAGI above $200k in early years.
    p = _solve(_plan(deferred=(2500, 2500), taxable=(200, 200)))
    over = p.st_agi_n > 200_000
    assert over.any(), "expected some years above the $200k adjustment start"
    # rho is fed from the previous iterate's AGI (NYIR_n is the rate the accepted LP was built
    # with): it tracks the formula on this plan's own AGI to the loop's tolerance.
    excess = np.clip(p.st_agi_n - 200_000.0, 0.0, 50_000.0)
    expect_rho = 0.25 * excess / 50_000.0
    np.testing.assert_allclose(p.NYIR_n[:20], expect_rho[:20], atol=1e-4)
    assert np.all((p.NYIR_n >= 0) & (p.NYIR_n <= 0.25))
    # st_item is the deduction taken: the property tax after the line 46 cut (1 - rho).
    g = p.gamma_n[: p.N_n]
    taken = p.st_agi_n - p.st_ti_n
    expect_taken = np.where(p.st_itemizing_n, p.st_item_n, p.st_sigmaBar_n)
    np.testing.assert_allclose(taken[:20], expect_taken[:20], atol=2.0)
    item = p.st_itemizing_n[:20]
    assert item.any()
    # At the rate the LP was built with.
    np.testing.assert_allclose(p.st_item_n[:20][item], ((1.0 - p.NYIR_n) * 25000.0 * g)[:20][item], rtol=1e-6)


def test_nj_and_fl_have_no_state_itemized_block():
    for state, loc in (("NJ", ""), ("FL", "")):
        p = _solve(_plan(state=state, locality=loc))
        assert "zsi" not in p.vm
        assert not p.st_itemizing_n.any()
        assert np.all(p.st_item_n == 0)


def test_move_to_nj_stops_the_itemizing():
    moves = [(THISYEAR + 5, "NJ", "")]
    p = _solve(_plan(moves=moves))
    assert p.st_itemizing_n[:5].all()
    assert not p.st_itemizing_n[5:].any()
    assert np.all(p.st_item_n[5:] == 0)


def test_yonkers_surcharge_follows_the_reduced_state_tax():
    p_y = _solve(_plan(locality="Yonkers"))
    p_n = _solve(_plan(locality=""))
    # Same plan, so the surcharge is a share of the (already lower) NY tax.
    assert p_y.lt_surcharge_n[0] > 0
    np.testing.assert_allclose(p_y.lt_T_n, p_y.lt_surcharge_n * (p_y.st_T_n - p_y.lt_T_n), rtol=1e-6)
    assert p_y.st_T_n[0] > p_n.st_T_n[0]  # Yonkers adds its surcharge on top


def test_mortgage_interest_is_deductible_up_to_the_state_limit():
    p = _solve(_plan(mortgage=(600_000.0, 6.5, 30)))
    assert p.st_item_mi_n[0] > 0
    assert p.st_itemizing_n[:20].all()
    g = p.gamma_n[: p.N_n]
    expect = 25000.0 * g + p.st_item_mi_n
    np.testing.assert_allclose(p.st_item_n[:20], expect[:20], rtol=1e-5)


def test_medical_above_the_floor_is_deductible():
    """A medical line large enough to beat the standard: the claim is paid - 10% of federal AGI.

    Under maxBequest every g_n is pinned, so the amount paid is known before the solve and the
    claim is a column bound (no zmed binary).
    """
    p = _solve(_plan(medical=40_000.0, core=40_000.0, property_tax=0.0))
    assert p.st_itemizing_n[:20].all()
    assert "zmed" not in p.vm
    g = p.gamma_n[: p.N_n]
    claim = np.maximum(0.0, 40_000.0 * g - p.STMF_n)
    assert np.all(p.STMF_n[:20] > 0)
    # The floor is the previous iterate's federal AGI x 10%.
    np.testing.assert_allclose(p.STMF_n[:20], 0.10 * p.MAGI_n[:20], rtol=0.02)
    pos = p.st_ti_n > 1.0
    assert pos[:20].sum() >= 10
    np.testing.assert_allclose(p.st_imed_n[pos], claim[pos], atol=1.0)


def test_charity_is_inside_the_itemized_total():
    p = _solve(_plan(charity=30_000.0, property_tax=0.0))
    assert p.st_itemizing_n[:20].all()
    g = p.gamma_n[: p.N_n]
    np.testing.assert_allclose(p.st_ich_n[:20], 30_000.0 * g[:20], rtol=1e-6)


def test_deduction_taken_is_one_of_the_two_branches():
    p = _solve(_plan())
    # The deduction actually taken is either the (cut) itemized total or the standard, capped at
    # NYAGI so taxable income never goes negative.
    taken = p.st_agi_n - p.st_ti_n
    expect = np.minimum(np.where(p.st_itemizing_n, p.st_item_n, p.st_sigmaBar_n), p.st_agi_n)
    np.testing.assert_allclose(taken[:20], expect[:20], atol=2.0)


def _free_cols(p, name):
    "Columns of block `name` whose bounds the builder left open (lb < ub)."
    if name not in p.vm:
        return 0
    lb, ub = p.B.arrays()
    blk = p.vm._blocks[name]
    return int(np.sum(lb[blk.start : blk.end] < ub[blk.start : blk.end]))


def test_maxbequest_decides_every_year_before_the_solve():
    """maxBequest without spending slack pins every g_n, so the property tax paid is known and the
    a priori rule fixes zsi in every year ($25k > $16,050): no free binary, no big-M gate."""
    p = _solve(_plan())
    assert len(p._st_item_years) > 0
    assert _free_cols(p, "zsi") == 0
    assert not any(t and t[0] == "state_item_pt_gate" for t in p.A.tags)
    # A $10k property tax grows with inflation while the $16,050 NY standard is not indexed: the
    # rule fixes the standard while 10k*gamma is below it and itemizing once it is above.
    q = _solve(_plan(property_tax=10_000.0))
    assert _free_cols(q, "zsi") == 0
    pt = 10_000.0 * q.gamma_n[: q.N_n]
    clear = np.abs(pt - q.st_sigmaBar_n) > 1.0
    np.testing.assert_array_equal(q.st_itemizing_n[clear], (pt > q.st_sigmaBar_n)[clear])
    assert not q.st_itemizing_n[0] and q.st_itemizing_n[-1]


def test_maxspending_leaves_the_choice_to_the_solver():
    """Net spending is free under maxSpending, so the property tax paid is not known a priori."""
    p = _plan()
    _solve(p, objective="maxSpending", bequest=0)
    assert _free_cols(p, "zsi") > 0
    assert p.st_itemizing_n[:20].all()
    g = p.gamma_n[: p.N_n]
    # The property tax paid is its share of net spending; the claim follows it.
    share = 25_000.0 / 105_000.0
    np.testing.assert_allclose(p.st_ipt_n[:20], share * p.g_n[:20], rtol=1e-5)
    assert np.all(p.st_item_n[:20] > p.st_sigmaBar_n[:20] - 1.0)
    assert g[0] == 1.0


def test_medicare_premiums_alone_add_no_binaries():
    """In loop mode the premium is the loop's M_n, known before the solve: a column bound, not a
    zmed binary per Medicare year (the first version added 28 of them to this plan)."""
    p = _solve(_plan(), withMedicare="loop")
    assert p.M_n.max() > 0
    assert "zmed" not in p.vm
    F = p.STMF_n  # the floor the LP was built with: 10% of the previous iterate's AGI
    cap = np.maximum(0.0, p.M_n - F)
    assert np.all(p.st_imed_n <= cap + 1.0)


def test_medicare_optimize_gets_a_switch_per_medicare_year():
    """Under withMedicare="optimize" the premium is the m variable: the claim needs zmed."""
    p = _solve(_plan(), withMedicare="optimize")
    assert "zmed" in p.vm
    assert len(p._st_item_med_years) == int(np.sum(p._medicare_premium_ub_n > 0))
    F = p.STMF_n  # the floor the LP was built with: 10% of the previous iterate's AGI
    cap = np.maximum(0.0, p.m_n + p.M_n - F)
    assert np.all(p.st_imed_n <= cap + 1.0)


def test_medical_below_the_floor_claims_nothing():
    """max(0, paid - F) where paid < F: the zmed = 0 branch. Under maxSpending the medical line is a
    share of free net spending, so the year has a zmed binary."""
    p = _plan(medical=3_000.0, expectancy=(76, 76))
    _solve(p, objective="maxSpending", bequest=0)
    assert "zmed" in p.vm
    paid = 3_000.0 / 108_000.0 * p.g_n
    F = p.STMF_n  # the floor the LP was built with: 10% of the previous iterate's AGI
    below = (paid < F - 50.0) & p.st_itemizing_n
    assert below.any()
    assert np.all(p.st_imed_n[below] <= 1.0)


def test_medical_claim_under_maxspending_is_paid_less_the_floor():
    p = _plan(medical=15_000.0, expectancy=(76, 76))
    _solve(p, objective="maxSpending", bequest=0)
    assert "zmed" in p.vm
    paid = 15_000.0 / 120_000.0 * p.g_n
    claim = np.maximum(0.0, paid - p.STMF_n)
    # Where NY taxable income is zero the deduction has no price and any claim is as good.
    pos = (p.st_ti_n > 1.0) & p.st_itemizing_n
    assert pos.sum() >= 5 and claim[pos].max() > 0
    np.testing.assert_allclose(p.st_imed_n[pos], claim[pos], atol=1.0)


def test_local_search_keeps_the_itemizing_choice_integral():
    """zsi is a local-search family: under maxSpending it is free, and the plan the search returns
    takes one branch or the other in every year (a fractional zsi would mix them)."""
    p = _plan(medical=3_000.0, expectancy=(76, 76))  # a short plan keeps the search to seconds
    _solve(p, objective="maxSpending", bequest=0, breakpointMethod="local-search", localSearchTime=1,
           withMedicare="loop")
    assert p.breakpointMethodUsed.startswith("local search")
    assert _free_cols(p, "zsi") > 0
    taken = p.st_agi_n - p.st_ti_n
    expect = np.minimum(np.where(p.st_itemizing_n, p.st_item_n, p.st_sigmaBar_n), p.st_agi_n)
    pos = p.st_ti_n > 1.0
    np.testing.assert_allclose(taken[pos], expect[pos], atol=2.0)
    # And the medical claim stays within max(0, paid - floor) at the floor the LP was built with.
    paid = 3_000.0 / 108_000.0 * p.g_n
    assert np.all(p.st_imed_n <= np.maximum(0.0, paid + p.M_n - p.STMF_n) + 1.0)


def test_guard_plan_without_itemizing_is_unchanged():
    """A FL plan has no state itemized rows at all: the variable map has no zsi block."""
    p = _solve(_plan(state="FL", locality=""))
    assert "st_ipt" not in p.vm and "zsi" not in p.vm


def test_line_46_cut_can_make_the_standard_win():
    """The a priori rule compares keep*LB and keep*UB with the standard, not the raw totals.

    $20k property tax beats the $16,050 standard before the cut, but at NYAGI $225k (rho=0.125)
    the cut leaves $17,500 — still above. At rho=0.25 (NYAGI >= $250k) it leaves $15,000, below
    the standard, so the year must not be forced to itemize.
    """
    p = _solve(_plan(property_tax=20_000.0, deferred=(2500, 2500), taxable=(200, 200)))
    # Years at the full 25% cut must not be forced into itemizing below the standard.
    full = p.NYIR_n >= 0.25 - 1e-9
    assert full.any(), "expected some years at the full 25% cut"
    # $20k x 0.75 = $15,000 < $16,050: if zsi were pinned to 1 the deduction would lose.
    taken = p.st_agi_n - p.st_ti_n
    assert np.all(taken[full] >= p.st_sigmaBar_n[full] - 2.0)
    assert p.NYIR_n.max() > 0.1


def test_shortfall_is_zero_when_the_deduction_is_fully_claimed():
    """A fully claimed plan must not leave a shortfall (it would keep the tax tie-break on)."""
    p = _solve(_plan())
    short = p._itemized_shortfall()
    # Early years claim the whole property tax and have no medical/charity: no shortfall.
    assert np.all(short[:20] <= 1.0), short[:20]


def test_shortfall_sees_the_deduction_left_on_the_table():
    """A smaller deduction than was available must show up as a shortfall in today's dollars."""
    p = _solve(_plan())
    saved = p.st_ti_n.copy()
    p.st_ti_n = p.st_ti_n + 5_000.0  # pretend $5k less deduction was taken
    short = p._itemized_shortfall()
    assert short[0] > 4_000.0
    p.st_ti_n = saved


def test_shortfall_counts_no_itemized_total_in_years_without_columns():
    """A NY year without a deductible line can take only the standard: Medicare above the floor
    there must not show as a shortfall the repair cannot remove (review finding 6)."""
    p = _plan()
    lines = p.houseLists["Budget"].copy()
    lines.loc[lines["name"] == "pt", "end"] = THISYEAR + 9  # the house is sold after ten years
    p.houseLists["Budget"] = lines
    _solve(p)
    no_cols = np.ones(p.N_n, dtype=bool)
    no_cols[p._st_item_years] = False
    assert no_cols.any() and not no_cols[:10].any()
    p.M_n = np.full(p.N_n, 1e6)  # premiums far above any floor
    short = p._itemized_shortfall()
    st_e = p.st_agi_n - p.st_ti_n - p.st_rx_n - p.st_pt_n
    np.testing.assert_allclose(short[no_cols], np.maximum(0.0, p.st_sigmaBar_n - st_e)[no_cols], atol=1e-6)


def test_shortfall_is_zero_in_states_without_itemizing():
    """A NY->NJ move must not leave a phantom shortfall in the NJ years (review finding 3)."""
    p = _solve(_plan(moves=[(THISYEAR + 5, "NJ", "")]))
    short = p._itemized_shortfall()
    assert np.all(short[5:] == 0.0), short[5:8]


def test_medical_with_medicare_optimize_counts_the_premium():
    """The medical claim counts premiums; under withMedicare='optimize' they are the m variable."""
    p = _solve(_plan(medical=15_000.0), withMedicare="optimize")
    g = p.gamma_n[: p.N_n]
    # Against the floor the LP was built with (the previous iterate's AGI), in years where the
    # deduction still has a price (positive NY taxable income).
    claim = np.maximum(0.0, 15_000.0 * g + p.m_n + p.M_n - p.STMF_n)
    assert p.m_n.max() > 0
    pos = (p.st_ti_n > 1.0) & p.st_itemizing_n
    assert pos.sum() >= 10
    np.testing.assert_allclose(p.st_imed_n[pos], claim[pos], atol=1.0)


def test_medical_floor_is_not_clamped_away():
    """max(0, paid - 10% AGI): a $40k medical line at AGI ~$120k may claim at most ~$28k.

    The earlier clamped form dropped the floor whenever it exceeded the constant part of paid
    and let the whole $40k through.
    """
    p = _solve(_plan(medical=40_000.0, core=40_000.0, property_tax=0.0))
    g = p.gamma_n[: p.N_n]
    paid = 40_000.0 * g
    F = p.STMF_n  # the floor the LP was built with: 10% of the previous iterate's AGI
    cap = np.maximum(0.0, paid - F)
    # Claimed medical sits at or below paid - 10% AGI wherever the floor bites.
    biting = F > 1.0
    assert biting.any()
    assert np.all(p.st_imed_n[biting] <= cap[biting] + 1.0), (p.st_imed_n[biting], cap[biting])
    # And it is not zero everywhere: something clears the floor.
    assert p.st_imed_n.max() > 0


def test_essential_lines_still_get_itemized_columns():
    """A negative _budget_amount_terms const must not hide the deduction (review finding 1)."""
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "ess", verbose=False,
                 logstreams=[io.StringIO()])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame([
        _line("core", "core", 40_000.0, essential=True),
        _line("pt", "property tax", 25_000.0),
    ]), "Budget")
    p.setStateTax("NY", locality="")
    p.setExpirationYearOBBBA(2099)
    _solve(p)
    assert "zsi" in p.vm, "essential core must not hide the property tax deduction"
    assert p.st_itemizing_n[:20].any()
    assert p.st_item_n.max() > 0

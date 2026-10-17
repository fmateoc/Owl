"""NY STAR credit (fork; src/owlplanner/star.py, data/property_tax_relief.toml).

Tax Law sec. 606(eee): a refundable NY income tax credit for a resident owner. Basic: income
(federal AGI less IRA distributions, two years before the benefit year) at most $500,000.
Enhanced: an owner 65+ on December 31 and income at most the Enhanced standard ($110,750 for 2026,
$113,550 for 2027, then the SS cost-of-living adjustment, never lower); a surviving spouse of 62+
keeps it. Amounts per municipality and school district (tax.ny.gov, 2025 final credits), at most
2% a year more (RPTL sec. 1306-a). The plan charges the credit against the state tax; IT-196
line 6 subtracts it from real estate taxes.
"""

import io

import numpy as np
import pandas as pd
import pytest

import owlplanner as owl
from owlplanner import residency, star
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]
EXACT = {"withMedicare": "none", "withSSTaxability": 0.85}


# ----- data and lookups -------------------------------------------------------------------------
def test_district_lookup():
    assert star.canonical_district("NY", "Yonkers") == "City of Yonkers / Yonkers"
    assert star.canonical_district("NY", " city of yonkers / YONKERS ") == "City of Yonkers / Yonkers"
    assert star.canonical_district("NY", "New York City (class 1)") == "New York City / New York City (class 1)"
    assert star.canonical_district("NY", "") == ""
    with pytest.raises(ValueError, match="several municipalities"):
        star.canonical_district("NY", "Scarsdale")  # Town of Scarsdale and Town of Greenburgh
    with pytest.raises(ValueError, match="Unknown school district"):
        star.canonical_district("NY", "Nowhere")
    with pytest.raises(ValueError, match="no STAR data"):
        star.canonical_district("NJ", "Yonkers")


def test_district_amounts_from_tax_ny_gov():
    # 2025 final credits, Westchester page of tax.ny.gov (read 2026-10-17).
    rows = {star.district_key(r): r for r in star.program("NY")["districts"]}
    assert rows["City of Yonkers / Yonkers"]["basic"] == 879.0
    assert rows["City of Yonkers / Yonkers"]["enhanced"] == 2455.0
    assert rows["New York City / New York City (class 1)"]["enhanced"] == 730.0
    # Homestead rows only (Rye Neck has a Non-Homestead class too).
    assert rows["City of Rye / Rye Neck"]["basic"] == 1184.34
    assert len(rows) == 75


def _schedule(yobs=(1961, 1966), years=10, horizons=(30, 30), n_d=30, i_d=0, gamma=None, pt=20000.0,
              district="City of Yonkers / Yonkers"):
    year_n = np.arange(2026, 2026 + years)
    gamma_n = np.ones(years + 1) if gamma is None else gamma
    return star.star_schedule(
        ["NY"] * years, [district] * years, np.ones(years, dtype=bool), np.full(years, pt), year_n,
        gamma_n, np.array(yobs), np.array(horizons), n_d, i_d,
    )


def test_amounts_grow_two_percent_and_cap_at_property_tax():
    sc = _schedule()
    assert sc.basic_n[0] == pytest.approx(879.0 * 1.02)  # 2026 from the 2025 amount
    assert sc.basic_n[3] == pytest.approx(879.0 * 1.02**4)
    capped = _schedule(pt=1000.0)
    assert np.all(capped.basic_n <= 1000.0) and np.all(capped.enhanced_n <= 1000.0)


def test_enhanced_age_test():
    # Older spouse born 1961: 65 on December 31, 2026.
    sc = _schedule(yobs=(1961, 1966))
    assert np.all(sc.enhanced_n > sc.basic_n)
    young = _schedule(yobs=(1962, 1966))  # 65 in 2027
    assert young.enhanced_n[0] == 0 and young.enhanced_n[1] > young.basic_n[1]


def test_surviving_spouse_keeps_enhanced_from_62():
    # The older spouse (65 in 2026) dies after 2028; the survivor, born 1966, is 62 in 2028.
    sc = _schedule(yobs=(1961, 1966), horizons=(3, 30), n_d=3, i_d=0)
    assert np.all(sc.enhanced_n[3:] > sc.basic_n[3:])  # 2029 on: survivor 63+
    # A survivor under 62 gets the Basic credit until 65.
    sc = _schedule(yobs=(1961, 1970), horizons=(3, 30), n_d=3, i_d=0)
    assert sc.enhanced_n[3] == 0  # 2029: survivor 59
    assert sc.enhanced_n[2032 - 2026] == 0  # 62 in 2032, but the age test then is the survivor's own
    assert sc.enhanced_n[2035 - 2026] > 0  # 65 in 2035


def test_income_standard_indexed_and_never_lower():
    gamma = np.cumprod(np.r_[1.0, [1.03] * 4, [0.99] * 6])
    sc = _schedule(gamma=gamma)
    assert sc.limit_n[0] == 110750.0
    assert sc.limit_n[1] == 113550.0
    assert sc.limit_n[2] == pytest.approx(113550.0 * 1.03)
    assert np.all(np.diff(sc.limit_n) >= 0)  # deflation does not lower it


def test_implied_credit_two_year_lag():
    sc = _schedule()
    income = np.full(10, 100_000.0)
    income[0] = 120_000.0  # above the Enhanced standard: the credit of year 2 is Basic
    income[1] = 600_000.0  # above the Basic limit: no credit in year 3
    got = sc.implied_credit(income, prior=[50_000.0, 200_000.0])
    assert got[0] == sc.enhanced_n[0]  # 2024 income
    assert got[1] == sc.basic_n[1]  # 2025 income above the standard
    assert got[2] == sc.basic_n[2]
    assert got[3] == 0.0
    assert np.all(got[4:] == sc.enhanced_n[4:])


# ----- residence ---------------------------------------------------------------------------------
def test_move_can_change_only_the_school_district():
    moves = [{"year": THISYEAR + 2, "state": "NY", "school_district": "City of Rye / Rye"}]
    by_year = residency.school_district_by_year("NY", "", "Yonkers", moves, THISYEAR, 4)
    assert by_year == ["City of Yonkers / Yonkers"] * 2 + ["City of Rye / Rye"] * 2
    # It does not carry over a move that names none.
    by_year = residency.school_district_by_year("NY", "", "Yonkers", [(THISYEAR + 1, "NJ")], THISYEAR, 3)
    assert by_year == ["City of Yonkers / Yonkers", "", ""]
    with pytest.raises(ValueError, match="goes to the starting state"):
        residency.residence_by_year("NY", "", [(THISYEAR + 1, "NY", "", "Yonkers")], THISYEAR, 3, "Yonkers")


# ----- plan ---------------------------------------------------------------------------------------
def _line(name, htype, amount):
    return {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0, "amount": amount,
            "rate": 0.0, "survivor": np.nan}


def _plan(district="Yonkers", property_tax=25000.0, taxable=(400, 400), ss=(3000, 2400), dobs=None,
          expectancy=(89, 92)):
    log = io.StringIO()
    p = owl.Plan(["Joe", "Jane"], dobs or ["1960-03-15", "1961-09-15"], list(expectancy), "star", verbose=False,
                 logstreams=[log])
    p._test_log = log
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=list(taxable), taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity(list(ss), [67, 67])
    lines = [_line("core", "core", 80000.0)]
    if property_tax:
        lines.append(_line("pt", "property tax", property_tax))
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(lines), "Budget")
    p.setStateTax("NY", locality="Yonkers", school_district=district)
    p.setExpirationYearOBBBA(2099)
    return p


def _solve(p, **opts):
    o = dict(EXACT)
    o.update(opts)
    p.solve("maxBequest", options=o)
    assert p.caseStatus == "solved", p.solverMessage
    return p


def _bequest(p):
    return owl.export._compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]


def test_credit_comes_off_the_state_tax_and_it196():
    p = _solve(_plan())
    assert p._star_on and not p._star_lp
    # Both spouses 65+ from 2026, income well under the standard: the Enhanced credit each year.
    assert np.allclose(p.st_star_n, p._star.enhanced_n)
    assert p.st_star_n[0] == pytest.approx(2455.0 * 1.02)
    state = np.sum(p.st_T_tn, axis=0) + p.STR_n - p.st_c_n
    assert np.allclose(p.st_T_n, state + p.lt_T_n - p.st_star_n, atol=0.01)
    # The Yonkers surcharge is a share of the tax before the credit.
    assert np.allclose(p.lt_T_n, p.lt_surcharge_n * state, atol=0.01)
    # IT-196 line 6: real estate taxes less the credit, in the years the plan itemizes.
    on = p.st_itemizing_n
    assert np.any(on)
    pt = 25000.0 * p.gamma_n[: p.N_n]
    assert np.allclose(p.st_ipt_n[on], (pt - p.st_star_n)[on], atol=0.01)
    assert p.fixedPointResidual["STAR"]["abs_sum"] < 1.0
    none = _solve(_plan(), withSTAR="none")
    assert not none._star_on and np.all(none.st_star_n == 0)
    assert _bequest(p) > _bequest(none)


def test_no_credit_without_a_district_or_for_a_renter():
    p = _solve(_plan(district=""))
    assert not p._star_on and np.all(p.st_star_n == 0)
    p = _plan(property_tax=0.0)
    _solve(p)
    assert not p._star_on
    assert "STAR credit goes to owners" in p._test_log.getvalue()


def test_previous_incomes_set_the_first_two_years():
    p = _solve(_plan(), previousSTARIncomes=[200.0, 600.0])
    assert p.st_star_n[0] == pytest.approx(p._star.basic_n[0])
    assert p.st_star_n[1] == 0.0
    assert p.st_star_n[2] == pytest.approx(p._star.enhanced_n[2])


@pytest.mark.parametrize("taxable", [800, 850])
def test_optimize_keeps_enhanced_where_the_loop_loses_it(taxable):
    # Income near the Enhanced standard: the binaries trade income for the credit, which the loop,
    # charging the credit its previous iterate's income implies, cannot.
    loop = _solve(_plan(taxable=(taxable, taxable), ss=(4200, 3600)), withSTAR="loop")
    opt = _solve(_plan(taxable=(taxable, taxable), ss=(4200, 3600)), withSTAR="optimize")
    assert opt._star_lp and "zst" in opt.vm
    enh = lambda q: int(np.sum(np.isclose(q.st_star_n, q._star.enhanced_n) & (q._star.enhanced_n > 0)))  # noqa: E731
    assert enh(opt) > enh(loop)
    assert _bequest(opt) > _bequest(loop)
    # Consistent: every credit received is the one the plan's own income allows.
    assert opt.fixedPointResidual["STAR"]["abs_sum"] < 1.0
    inc = opt._star.tested_income(opt._star_income_n(), opt.prevSTAR)
    got = opt.st_star_n > opt._star.basic_n + 1
    assert np.all(inc[got] <= opt._star.limit_n[got])


def test_config_round_trip(tmp_path):
    from owlplanner.config import plan_bridge

    p = _plan(district="yonkers")
    p.setStateTax("NY", locality="Yonkers", school_district="yonkers",
                  moves=[{"year": THISYEAR + 5, "state": "NY", "school_district": "City of Rye / Rye"}])
    conf = plan_bridge.plan_to_config(p)
    assert conf["basic_info"]["school_district"] == "City of Yonkers / Yonkers"
    assert conf["basic_info"]["moves"][0]["school_district"] == "City of Rye / Rye"
    q = owl.Plan(["Joe", "Jane"], ["1960-03-15", "1961-09-15"], [89, 92], "star2", verbose=False)
    plan_bridge._apply_state_to_plan(q, conf)
    assert q.school_district == "City of Yonkers / Yonkers"
    assert q._school_district_n()[5] == "City of Rye / Rye"


def test_local_search_carries_the_star_family():
    # breakpointMethod="local-search" sets withSTAR="optimize"; zst is one of the families it moves.
    p = _plan(taxable=(800, 800), ss=(4200, 3600), expectancy=(78, 80))  # short: the search ends quickly
    _solve(p, breakpointMethod="local-search", localSearchTime=60)
    assert p._star_lp and "zst" in p.vm
    assert "zst" in owl.localsearch.FAMILIES
    assert p.fixedPointResidual["STAR"]["abs_sum"] < 1.0


def test_ui_bridge_keeps_the_district():
    from owlplanner.config import ui_bridge

    conf = {"basic_info": {"status": "married", "names": ["Joe", "Jane"], "date_of_birth": ["1960-03-15", "1961-09-15"],
                           "life_expectancy": [89, 92], "state": "NY", "school_district": "yonkers",
                           "moves": [{"year": THISYEAR + 5, "state": "NY", "school_district": "City of Rye / Rye"}]},
            "solver_options": {"withSTAR": "optimize", "previousSTARIncomes": [100.0, 110.0]}}
    ui = ui_bridge.config_to_ui(conf)
    # Canonical, so that the selectbox on the Create Case page finds it.
    assert ui["schoolDistrict"] == "City of Yonkers / Yonkers"
    assert ui["stateMoveSchoolDistrict"] == "City of Rye / Rye"
    back = ui_bridge.ui_to_config(ui)
    assert back["basic_info"]["school_district"] == "City of Yonkers / Yonkers"
    assert back["basic_info"]["moves"][0]["school_district"] == "City of Rye / Rye"
    assert back["solver_options"]["withSTAR"] == "optimize"
    assert back["solver_options"]["previousSTARIncomes"] == [100.0, 110.0]

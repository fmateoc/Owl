"""Tests for the Housing ledger: recurring costs and the NJ property tax deduction."""

import numpy as np
import pandas as pd
import pytest

import owlplanner as owl
from owlplanner import housing, tax_state
from owlplanner.export import plan_metrics
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]


def _rows(*rows):
    cols = ["active", "name", "type", "year", "end", "amount", "rate"]
    return conditionDebtsAndFixedAssetsDF(pd.DataFrame(list(rows), columns=cols), "Housing")


def _one(**kw):
    base = {"active": True, "name": "h", "type": "rent", "year": THISYEAR, "end": 0, "amount": 12000.0, "rate": 0.0}
    base.update(kw)
    return base


def _pt_row(amount=20000.0):
    return [{"active": True, "name": "pt", "type": "property tax", "year": THISYEAR,
             "end": 0, "amount": amount, "rate": 0.0}]


class TestGetHousingArrays:
    def test_empty(self):
        t, p, r = housing.get_housing_arrays(pd.DataFrame(columns=housing.HOUSING_TYPES), 5, np.ones(6), THISYEAR)
        assert np.all(t == 0) and np.all(p == 0) and np.all(r == 0)

    def test_constant_rent_through_plan_end(self):
        df = _rows(_one(type="rent", amount=24000.0, end=0))
        gamma = np.ones(6)
        t, p, r = housing.get_housing_arrays(df, 5, gamma, THISYEAR)
        assert np.all(t == 24000.0) and np.all(r == 24000.0) and np.all(p == 0)

    def test_end_year_is_inclusive(self):
        df = _rows(_one(type="rent", amount=12000.0, end=THISYEAR + 1))
        t, _, _ = housing.get_housing_arrays(df, 5, np.ones(6), THISYEAR)
        assert list(t) == [12000.0, 12000.0, 0, 0, 0]

    def test_end_zero_is_through_the_last_year(self):
        df = _rows(_one(type="rent", amount=12000.0, end=0))
        t, _, _ = housing.get_housing_arrays(df, 5, np.ones(6), THISYEAR)
        assert np.all(t == 12000.0)

    def test_end_negative_counts_from_the_plan_end(self):
        df = _rows(_one(type="rent", amount=12000.0, end=-1))
        t, _, _ = housing.get_housing_arrays(df, 5, np.ones(6), THISYEAR)
        assert list(t) == [12000.0, 12000.0, 12000.0, 12000.0, 0]

    def test_year_bounds(self):
        df = _rows(_one(type="rent", amount=12000.0, year=THISYEAR + 2, end=0))
        t, _, _ = housing.get_housing_arrays(df, 5, np.ones(6), THISYEAR)
        assert list(t) == [0, 0, 12000.0, 12000.0, 12000.0]

    def test_inactive_row_is_skipped(self):
        df = _rows(_one(active=False, type="rent", amount=12000.0))
        t, _, _ = housing.get_housing_arrays(df, 5, np.ones(6), THISYEAR)
        assert np.all(t == 0)

    def test_real_growth_and_inflation(self):
        # amount is in `year` dollars; rate is real growth above inflation.
        df = _rows(_one(type="property tax", amount=10000.0, rate=2.0, end=0))
        gamma = np.array([1.0, 1.03, 1.03**2, 1.03**3, 1.03**4, 1.03**5])
        t, p, r = housing.get_housing_arrays(df, 5, gamma, THISYEAR)
        assert r[0] == 0 and p[0] == pytest.approx(10000.0)
        assert p[1] == pytest.approx(10000.0 * 1.02 * 1.03)
        assert p[2] == pytest.approx(10000.0 * 1.02**2 * 1.03**2)
        assert np.all(t == p)

    def test_split_types(self):
        df = _rows(
            _one(type="property tax", amount=8000.0),
            _one(type="rent", amount=20000.0),
            _one(type="insurance", amount=2000.0),
        )
        t, p, r = housing.get_housing_arrays(df, 3, np.ones(4), THISYEAR)
        assert np.all(p == 8000.0) and np.all(r == 20000.0) and np.all(t == 30000.0)


# ---------------------------------------------------------------------------
# Plan: cash flow and NJ property tax deduction
# ---------------------------------------------------------------------------


def _bequest_opts():
    return {"noRothConversions": "None", "maxRothConversion": 0, "withMedicare": "None", "netSpending": 40}


def _plan(state="NJ", housing_rows=None, taxable=(200, 100)):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1965-09-15"], [89, 92], "housing", verbose=False)
    p.setSpendingProfile("flat")
    p.setAccountBalances(taxable=list(taxable), taxDeferred=[0, 0], taxFree=[0, 0])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    if housing_rows is not None:
        p.houseLists["Housing"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(housing_rows), "Housing")
    if state:
        p.setStateTax(state)
    return p


def test_housing_costs_are_subtracted_like_big_ticket_items():
    """A Housing sheet must give the same objective as the same amounts as negative big-ticket items.

    Housing `amount` is in year dollars and tracks inflation (rate=0); big-ticket items are
    nominal. The comparison therefore enters the same inflated series as negative big-ticket items.
    """
    amount = 18000.0
    rows = [{"active": True, "name": "rent", "type": "rent", "year": THISYEAR, "end": 0, "amount": amount, "rate": 0.0}]
    p_h = _plan(state="", housing_rows=rows, taxable=(800, 400))
    p_h.setSocialSecurity([2800, 2200], [70, 70])
    p_h.solve("maxSpending", options={"bequest": 0, "withMedicare": "None", "withSSTaxability": 0.85})
    assert p_h.caseStatus == "solved"

    p_b = _plan(state="", housing_rows=None, taxable=(800, 400))
    p_b.setSocialSecurity([2800, 2200], [70, 70])
    # Match the inflated housing series: one person's Lambda_in column carries the whole cost.
    p_b.Lambda_in[0, :] = -p_h.housing_costs_n
    p_b.Lambda_in[1, :] = 0.0
    p_b.solve("maxSpending", options={"bequest": 0, "withMedicare": "None", "withSSTaxability": 0.85})
    assert p_b.caseStatus == "solved"
    assert p_h.basis == pytest.approx(p_b.basis, rel=1e-6)
    assert p_h.g_n == pytest.approx(p_b.g_n, rel=1e-6)


def test_nj_property_tax_deduction_owner():
    """A homeowner paying $20,000 property tax deducts the $15,000 cap."""
    rows = _pt_row()
    p = _plan(state="NJ", housing_rows=rows, taxable=(400, 200))
    p.setSocialSecurity([2800, 2200], [70, 70])
    p.setPension([4000, 3000], [62, 62], [False, False])
    p.solve("maxBequest", options=_bequest_opts())
    assert p.caseStatus == "solved"
    assert p.st_ptd_n[0] == pytest.approx(15000.0)
    assert p.st_pt_n[0] == pytest.approx(15000.0, abs=1.0)
    # Taxable income is below line 27 by the deduction (and the other deductions).
    assert p.st_ti_n[0] < p.st_agi_n[0]


def test_nj_property_tax_deduction_tenant():
    """A tenant paying $30,000 rent deducts 18% of rent ($5,400)."""
    rows = [
        {"active": True, "name": "rent", "type": "rent", "year": THISYEAR, "end": 0, "amount": 30000.0, "rate": 0.0}
    ]
    p = _plan(state="NJ", housing_rows=rows, taxable=(400, 200))
    p.setSocialSecurity([2800, 2200], [70, 70])
    p.setPension([4000, 3000], [62, 62], [False, False])
    p.solve("maxBequest", options=_bequest_opts())
    assert p.caseStatus == "solved"
    assert p.st_ptd_n[0] == pytest.approx(5400.0)
    assert p.st_pt_n[0] == pytest.approx(5400.0, abs=1.0)


def test_ny_has_no_property_tax_deduction():
    """NY has no property tax deduction: the rule is off, whatever the Housing rows."""
    rows = _pt_row()
    p = _plan(state="NY", housing_rows=rows, taxable=(400, 200))
    p.setSocialSecurity([2800, 2200], [70, 70])
    p.setPension([4000, 3000], [62, 62], [False, False])
    p.solve("maxBequest", options=_bequest_opts())
    assert p.caseStatus == "solved"
    assert np.all(p.st_ptd_n == 0)
    assert np.all(p.st_pt_n == 0)


def test_move_to_new_jersey_deducts_only_there():
    rows = _pt_row()
    p = _plan(state="NJ", housing_rows=rows, taxable=(400, 200))
    p.setStateTax("NJ", [(THISYEAR + 3, "FL")])
    p.setSocialSecurity([2800, 2200], [70, 70])
    p.setPension([4000, 3000], [62, 62], [False, False])
    p.solve("maxBequest", options=_bequest_opts())
    assert p.caseStatus == "solved"
    assert np.all(p.st_ptd_n[:3] == 15000.0)
    assert np.all(p.st_ptd_n[3:] == 0)


def test_deduction_does_not_change_the_exclusion_tier():
    """Line 41 comes after line 39: the tier is set on income before the property tax deduction."""
    rows = _pt_row()
    p = _pension_only(housing_rows=rows)
    # The deduction is taken.
    assert p.st_pt_n[0] == pytest.approx(15000.0, abs=1.0)
    # Line 27 (st_agi_n) is about $109k, in the 50% tier; the deduction would take it to about $94k,
    # in the 100% tier, if it moved the tier. The exclusion claimed must be the statute's, set on line 27.
    share, implied = p._tiered_exclusion_implied()
    assert 100000 < p.st_agi_n[0] < 115000 and share[0] == 0.5
    assert p.st_rx_n[0] == pytest.approx(implied[0], abs=2.0)
    # And taxable income is below line 27 minus the exclusion and exemptions, by the deduction.
    statutory_ti = max(0.0, np.round(p.st_agi_n[0]) - p.st_rx_n[0] - p.st_sigmaBar_n[0])
    assert p.st_ti_n[0] == pytest.approx(statutory_ti - 15000.0, abs=2.0)


def _pension_only(housing_rows=None):
    p = owl.Plan(["Joe", "Jane"], ["1962-06-15", "1963-12-15"], [85, 85], "NJ ptd", verbose=False)
    p.setSpendingProfile("flat")
    p.setAccountBalances(taxable=[0, 0], taxDeferred=[0, 0], taxFree=[0, 0])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([2800, 2200], [70, 70])
    p.setPension([5000, 4000], [62, 62], [False, False])
    if housing_rows is not None:
        p.houseLists["Housing"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(housing_rows), "Housing")
    p.setStateTax("NJ")
    p.solve("maxBequest", options=_bequest_opts())
    assert p.caseStatus == "solved"
    return p


def test_local_search_runs_with_the_deduction():
    rows = _pt_row()
    p = _plan(state="NJ", housing_rows=rows, taxable=(400, 200))
    p.setSocialSecurity([2800, 2200], [70, 70])
    p.solve(
        "maxSpending",
        options={"breakpointMethod": "local-search", "localSearchTime": 1, "withMedicare": "None", "bequest": 0},
    )
    assert p.caseStatus == "solved"
    assert p.st_pt_n[0] == pytest.approx(min(15000.0, p.st_ptd_n[0]), abs=1.0)


def test_only_new_jersey_has_the_property_tax_deduction():
    for s in tax_state.valid_states():
        for filing in (0, 1):
            entry = tax_state.get_state_entry(s, filing)
            assert ("property_tax_deduction" in entry) == (s == "NJ")


def test_hfp_round_trip_with_a_housing_sheet(tmp_path):
    rows = [
        {"active": True, "name": "tax", "type": "property tax", "year": THISYEAR,
         "end": 0, "amount": 12000.0, "rate": 1.0},
        {"active": False, "name": "old", "type": "rent", "year": THISYEAR,
         "end": 0, "amount": 9000.0, "rate": 0.0},
    ]
    p1 = _plan(state="NJ", housing_rows=rows)
    fname = str(tmp_path / "HFP_housing.xlsx")
    p1.saveHFP(fname, overwrite=True)
    p2 = _plan(state="NJ", housing_rows=None)
    p2.readHFP(fname)
    h2 = p2.houseLists["Housing"]
    assert len(h2) == 2
    assert list(h2["active"]) == [True, False]
    assert h2["name"].iloc[0] == "tax"
    assert h2["amount"].iloc[0] == pytest.approx(12000.0)
    assert h2["rate"].iloc[0] == pytest.approx(1.0)
    assert h2["end"].iloc[0] == 0


def test_replayed_rows_match_a_fresh_build_with_nj_housing():
    """The loop-invariant builders are replayed after the first iteration (upstream #151)."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "fixed_rows", Path(__file__).parents[1] / "solver" / "test_fixed_rows.py"
    )
    fr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fr)

    rows = _pt_row(20000.0)
    p = _plan(state="NJ", housing_rows=rows, taxable=(400, 200))
    p.setSocialSecurity([2800, 2200], [70, 70])
    p.setPension([4000, 3000], [62, 62], [False, False])
    p.solve("maxBequest", options=_bequest_opts())
    assert p.caseStatus == "solved"
    assert p.st_pt_n.sum() > 0
    assert p._fixedRows
    p._buildConstraints(p.objective, p.solverOptions)
    replayed = fr._lp_arrays(p)
    p._fixedRows = {}
    p._buildConstraints(p.objective, p.solverOptions)
    fr._assert_same_lp(fr._lp_arrays(p), replayed)


def test_process_before_any_solve():
    """The UI computes the fixed-asset bequest before the first solve (owlbridge.getFixedAssetsBequestValue)."""
    p = _plan(state="NJ", housing_rows=_pt_row())
    fa = pd.DataFrame([{"active": True, "name": "home", "type": "residence", "year": THISYEAR, "basis": 500000.0,
                        "value": 800000.0, "rate": 0.0, "yod": 0, "commission": 5.0}])
    p.houseLists["Fixed Assets"] = conditionDebtsAndFixedAssetsDF(fa, "Fixed Assets")
    p.processDebtsAndFixedAssets()
    assert p.fixed_assets_bequest_value > 0
    assert np.all(p.st_ptd_n == 0)  # the state rule is only known once solve() reads the state
    assert p.housing_property_tax_n[0] == pytest.approx(20000.0)


def test_rows_left_out_are_named():
    df = _rows(
        _one(name="term typed as end", end=10),
        _one(name="after the plan", year=THISYEAR + 50),
        _one(name="fine", end=0),
        _one(name="inactive", active=False, end=10),
    )
    out = housing.rows_left_out(df, 5, THISYEAR)
    assert [name for name, _ in out] == ["term typed as end", "after the plan"]


def test_rows_left_out_warn_in_the_plan():
    import io

    log = io.StringIO()
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1965-09-15"], [89, 92], "w", verbose=False, logstreams=[log])
    p.houseLists["Housing"] = _rows(_one(name="typo", end=10))
    p.processDebtsAndFixedAssets()
    assert "Housing row 'typo' ends in 10" in log.getvalue()
    assert np.all(p.housing_costs_n == 0)


def test_metrics_and_explanation_report_housing():
    from owlplanner.assistant.explain import build_explanation
    from owlplanner.assistant.explain_schema import PlanExplanation

    rows = _pt_row()
    p = _plan(state="NJ", housing_rows=rows, taxable=(400, 200))
    p.setSocialSecurity([2800, 2200], [70, 70])
    p.setPension([4000, 3000], [62, 62], [False, False])
    p.solve("maxBequest", options={**_bequest_opts(), "withDuals": True})
    m = plan_metrics(p)
    assert m["housing_costs_today"] == pytest.approx(20000.0 * p.N_n, rel=1e-6)
    assert m["housing_costs_nominal"] == pytest.approx(float(np.sum(p.housing_costs_n)))
    ex = build_explanation(p)
    PlanExplanation.model_validate(ex)
    assert ex["this_year"]["state_tax"]["property_tax_deduction"] == pytest.approx(15000.0, abs=1.0)
    by_year = ex["state_tax_brackets"]["by_year"]
    assert any(r.get("property_tax_deduction_today", 0) > 0 for r in by_year)

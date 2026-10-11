"""NJ line 31 medical deduction (Phase 3 step 5, fork-notes/phase3-plan.md).

NJ-1040 (2025) line 31, Worksheet F: unreimbursed medical expenses above 2% of NJ gross
income (line 29 = total income less the retirement exclusion). Includes Medicare Part B
premiums. st_med is a bounded LP variable beside st_pt; no binary.
"""

import io

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]
OPTS = {"noRothConversions": "None", "withMedicare": "None", "withSSTaxability": 0.85}


def _line(name, htype, amount, **kw):
    row = {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0,
           "amount": amount, "rate": 0.0, "survivor": np.nan}
    row.update(kw)
    return row


def _plan(state="NJ", *, property_tax=12000.0, core=50000.0, medical=0.0, taxable=(80, 80),
          deferred=(400, 300)):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "nj medical",
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
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(lines), "Budget")
    if state:
        p.setStateTax(state)
    p.setExpirationYearOBBBA(2099)
    return p


def _solve(p, objective="maxBequest", **extra):
    opts = dict(OPTS)
    opts.update(extra)
    p.solve(objective, options=opts)
    assert p.caseStatus == "solved", (p.caseStatus, p.solverMessage)
    return p


def test_data_parsed_for_nj_only():
    from owlplanner import tax_state

    nj = tax_state.st_taxParams("NJ", 2, 99, 4, np.ones(5), [1964, 1964], mobs=[3, 9])
    assert np.all(nj.med_floor_pct_n == 2.0)  # Worksheet F line 2
    ny = tax_state.st_taxParams("NY", 2, 99, 4, np.ones(5), [1964, 1964], mobs=[3, 9])
    assert np.all(ny.med_floor_pct_n == 0.0)


def test_medical_above_the_floor_is_claimed():
    """A $100k medical line clears 2% of NJ gross income: claim = paid - floor."""
    p = _solve(_plan(medical=100_000.0, core=40_000.0, taxable=(200, 200), deferred=(2000, 1500),
                     property_tax=0.0), withMedicare="loop")
    assert "st_med" in p.vm
    assert p.st_med_n.max() > 1000.0
    (cp, kp) = p._budget_amount_terms("medical")
    paid = cp + kp * p.g_n + p.medicare_n + p.aca_costs_n
    floor = p.st_medd_floor_pct_n / 100.0 * np.maximum(0.0, p.st_agi_n - p.st_rx_n)
    expect = np.maximum(0.0, paid - floor)
    pos = p.st_med_n > 1.0
    np.testing.assert_allclose(p.st_med_n[pos], expect[pos], rtol=0.05, atol=2.0)
    # Never above what was paid (the row's hard bound); the floor's SC lag can leave a few dollars.
    paid_all = cp + kp * p.g_n + p.medicare_n + p.aca_costs_n
    assert np.all(p.st_med_n <= paid_all + 2.0)


def test_no_medical_line_adds_no_column():
    """Without a medical line and with Medicare off, no st_med column."""
    p = _solve(_plan(medical=0.0))
    assert "st_med" not in p.vm
    assert np.all(p.st_med_n == 0.0)


def test_medicare_alone_can_create_the_column():
    """Owl's premiums are medical (NJ-1040 names Part B): Medicare on adds st_med."""
    p = _solve(_plan(medical=0.0), withMedicare="loop")
    assert "st_med" in p.vm


def test_fl_has_no_medical_deduction():
    p = _solve(_plan(state="FL", medical=50_000.0, property_tax=0.0, taxable=(200, 200),
                     deferred=(2000, 1500)))
    assert "st_med" not in p.vm
    assert np.all(p.st_med_n == 0.0)


def test_ny_has_no_nj_line_31():
    """NY itemizes medical on IT-196; NJ's line 31 is a separate variable."""
    p = _solve(_plan(state="NY", medical=50_000.0, property_tax=0.0, taxable=(200, 200),
                     deferred=(2000, 1500)))
    assert "st_med" not in p.vm
    assert np.all(p.st_med_n == 0.0)
    # NY still claims medical on its own schedule where the floor is cleared.
    assert p.st_imed_n.max() > 0.0


def test_claim_is_zero_below_the_floor():
    """A small medical line does not clear 2% of NJ gross income at high income: nothing claimed."""
    p = _solve(_plan(medical=3_000.0, core=80_000.0, taxable=(200, 200), deferred=(2000, 1500),
                     property_tax=0.0))
    assert "st_med" in p.vm
    # The floor the accepted LP used (2% of the previous iterate's line 29), and the nominal
    # amount paid ($3,000 today grows with inflation), not 3,000.
    floor = p.NJMF_n
    (cm, km) = p._budget_amount_terms("medical")
    paid = cm + km * p.g_n
    below = floor > paid + 1.0
    assert below.any()
    assert np.all(p.st_med_n[below] <= 1.0)
    above = paid > floor + 1.0
    np.testing.assert_allclose(p.st_med_n[above], (paid - floor)[above], rtol=0.05, atol=2.0)


def test_explanation_reports_the_medical_deduction():
    """Step-5 review: explain emitted medical_deduction keys its schema (extra="forbid") rejected,
    so any NJ plan whose premiums clear 2% of NJ gross income failed to explain."""
    from owlplanner.assistant.explain import build_explanation

    p = _solve(_plan(), withMedicare="loop", withDuals=True)  # premiums only, no medical line
    assert (p.st_med_n > 0.5).any()
    ex = build_explanation(p)
    assert "error" not in ex
    rows = ex["state_tax_brackets"]["by_year"]
    assert any(r.get("medical_deduction_today", 0) > 0 for r in rows)


def test_optimized_medicare_never_bounds_the_premium_from_below():
    """Under withMedicare="optimize" the premium is the m column. A claim row with st_med >= 0 in
    a year flagged from the previous iterate was a lower bound on m (step-5 review); the claim may
    go negative instead, and the loop solves every iterate."""
    log = io.StringIO()
    p = owl.Plan(["Joe", "Jane"], ["1958-03-15", "1958-09-15"], [89, 92], "nj medicare optimize",
                 verbose=True, logstreams=[log])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[200, 200], taxDeferred=[900, 700], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(
        pd.DataFrame([_line("core", "core", 60_000.0), _line("med", "medical", 2_000.0)]), "Budget")
    p.setStateTax("NJ")
    p.setExpirationYearOBBBA(2099)
    q = _solve(p, withMedicare="optimize")
    assert "st_med" in q.vm
    text = log.getvalue()
    assert "unsolvable" not in text and "could not be solved" not in text
    (cm, km) = q._budget_amount_terms("medical")
    paid = cm + km * q.g_n + q.medicare_n
    # Against the floor the accepted LP used (NJMF_n, the previous iterate's line 29).
    assert np.all(q.st_med_n <= np.maximum(0.0, paid - q.NJMF_n) + 2.0)
    assert (q.st_med_n > 1.0).any()

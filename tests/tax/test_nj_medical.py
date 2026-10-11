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
    if "st_med" in p.vm:
        floor = p.st_medd_floor_pct_n / 100.0 * np.maximum(0.0, p.st_agi_n - p.st_rx_n)
        # Where the floor exceeds what was paid, the claim is zero.
        below = floor > 3_000.0
        assert below.any()
        assert np.all(p.st_med_n[below] <= 1.0)

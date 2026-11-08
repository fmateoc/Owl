"""plan.json's per-year deflator and state-tax parts (ergonomics review S-4).

Each `by_year` row carries `deflator` (gamma_n), `local_tax` (lt_T_n), `state_recapture`
(st_recap_n), `star_credit` (st_star_n) and `wages_by_person` (omega_in). `state_tax` keeps its
meaning, st_T_n: state base + recapture + local tax - STAR credit, the base being the bracket
tax less personal credits (`Plan._finalize_state_tax`).
"""

import io

import numpy as np
import pandas as pd
import pytest

import owlplanner as owl
from owlplanner.cli.formatters import plan_to_dict
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF


@pytest.fixture(scope="module")
def solved():
    """A NY couple in Yonkers (a local surcharge) with a school district and a property tax
    line: the STAR credit every year (as tests/tax/test_star.py's `_plan`)."""
    p = owl.Plan(["Joe", "Jane"], ["1960-03-15", "1961-09-15"], [89, 92], "star", verbose=False,
                 logstreams=[io.StringIO()])
    year = int(p.year_n[0])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[400, 400], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [67, 67])
    lines = [{"active": True, "name": n, "type": t, "year": year, "end": 0, "amount": a, "rate": 0.0,
              "survivor": np.nan} for n, t, a in (("core", "core", 80000.0), ("pt", "property tax", 25000.0))]
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame(lines), "Budget")
    p.setStateTax("NY", locality="Yonkers", school_district="Yonkers")
    p.setExpirationYearOBBBA(2099)
    p.solve("maxBequest", options={"withMedicare": "none", "withSSTaxability": 0.85})
    assert p.caseStatus == "solved", p.solverMessage
    return p, plan_to_dict(p)


def test_the_new_keys_are_on_every_row(solved):
    p, doc = solved
    for n, row in enumerate(doc["by_year"]):
        assert row["deflator"] == pytest.approx(p.gamma_n[n], abs=1e-6)
        assert row["local_tax"] == round(p.lt_T_n[n])
        assert row["state_recapture"] == round(p.st_recap_n[n])
        assert row["star_credit"] == round(p.st_star_n[n])
        assert row["wages_by_person"] == [round(p.omega_in[i, n]) for i in range(p.N_i)]
    assert doc["by_year"][0]["deflator"] == 1.0


def test_the_state_tax_identity(solved):
    p, doc = solved
    base = np.sum(p.st_T_tn, axis=0) + p.STR_n - p.st_c_n  # the state's own tax, recapture inside
    rows = doc["by_year"]
    assert any(r["local_tax"] > 0 for r in rows) and any(r["star_credit"] > 0 for r in rows)
    for n, r in enumerate(rows):
        # three rounded integers: within $1.5 of the plan's own parts
        assert r["state_tax"] - r["local_tax"] + r["star_credit"] == pytest.approx(base[n], abs=1.5)
        assert r["state_tax"] == pytest.approx(p.st_T_n[n], abs=0.51)

"""
Tests for the conversion and bracket view (I8): `owlplanner.brackets.bracket_view`, and
the `brackets` block `plan_to_dict` writes into plan.json (run-library-design.md 14.1).

The per-year arithmetic is checked against the model's own constants (tax_federal) on a
stub plan that pins every input; the plan.json wiring is checked on a solved couple, as
`test_thresholds.py` checks the I3/I6 blocks.
"""

import numpy as np
import pytest

import owlplanner as owl
from owlplanner import tax_federal as tx
from owlplanner.brackets import bracket_view
from owlplanner.cli.formatters import plan_to_dict

THISYEAR = 2026  # the frozen test date (tests/conftest.py)
N_YEARS = 12


class FakePlan:
    """The attributes bracket_view() reads (no LP is solved here)."""

    def __init__(self, **kw):
        N = N_YEARS
        self.N_i = 2
        self.N_n = N
        self.n_d = N
        self.year_n = THISYEAR + np.arange(N)
        self.gamma_n = 1.025 ** np.arange(N, dtype=float)
        self.yobs = np.array([1960, 1958])
        self.mobs = np.array([3, 7])
        self.tobs = np.array([2, 2])
        self.horizons = np.array([N, N])
        self.G_n = np.zeros(N)
        self.Q_n = np.zeros(N)
        self.e_n = np.zeros(N)
        self.sigmaBar_n = np.zeros(N)
        self._ltcg_wide_n = True
        self.x_in = np.zeros((2, N))
        self.MAGI_n = np.zeros(N)
        self.slcsp_annual = 0.0
        self.aca_start_year = 0
        self.aca_table_year = 0
        self.yOBBBA = 2032
        for key, value in kw.items():
            setattr(self, key, value)

    def _medicaid_n(self):
        return np.full(self.N_n, tx._ACA_MEDICAID_RATIO)


class TestOneYear:
    def test_the_income_the_conversion_and_the_lines(self):
        p = FakePlan()
        p.G_n = np.full(N_YEARS, 100_000.0)  # nominal
        p.x_in = np.zeros((2, N_YEARS))
        p.x_in[0] = 20_000.0
        rows = bracket_view(p)["years"]
        assert len(rows) == N_YEARS
        first = rows[0]
        g = float(p.gamma_n[0])
        assert first["year"] == THISYEAR and first["ages"] == [66, 68]
        assert first["ordinary_taxable_income"] == pytest.approx(100_000.0 / g)
        assert first["conversion"] == pytest.approx(20_000.0 / g)
        assert [e["label"] for e in first["ordinary_edges"]] == list(tx.taxBracketNames[:-1])
        status = int(tx.filingStatusIndex_n(p.N_i, p.n_d, N_YEARS)[0])
        assert first["gains_edge_0"] == round(float(tx.capGainRates[status][0]), 2)

    def test_the_irmaa_lines_are_the_premium_years_in_the_tax_years_dollars(self):
        p = FakePlan()
        rows = bracket_view(p)["years"]
        first = rows[0]
        assert [e["label"] for e in first["irmaa_edges"]] == [
            "IRMAA tier 1", "IRMAA tier 2", "IRMAA tier 3", "IRMAA tier 4", "IRMAA tier 5"]
        assert first["irmaa_edges"][0]["premium_year"] == THISYEAR + 2
        expected = tx.irmaaThresholds(tx.irmaaStatus(p.horizons, 2), p.gamma_n, 2, THISYEAR)
        assert first["irmaa_edges"][0]["amount"] == pytest.approx(
            round(float(expected[0]) / float(p.gamma_n[0]), 2))

    def test_a_premium_year_past_the_plan_has_no_irmaa_edges(self):
        # Review AF4: m + 2 past the plan is not clamped to the last year -- there is no
        # premium year to name (`thresholds._irmaa_entries` skips those years).
        p = FakePlan()
        rows = bracket_view(p)["years"]
        assert rows[-3]["irmaa_edges"][0]["premium_year"] == THISYEAR + N_YEARS - 1
        assert rows[-2]["irmaa_edges"] == [] and rows[-1]["irmaa_edges"] == []

    def test_the_aca_lines_appear_only_with_the_marketplace(self):
        assert all(not row["aca_lines"] for row in bracket_view(FakePlan())["years"])
        # A couple still pre-Medicare: the marketplace is in the plan for them.
        p = FakePlan(slcsp_annual=12_000.0, yobs=np.array([1975, 1973]))
        lines = bracket_view(p)["years"][0]["aca_lines"]
        assert [line["label"] for line in lines] == [
            "Medicaid limit (138% FPL)", "the credit starts (100% FPL)",
            "400% FPL (the subsidy cliff)"]
        fpl = tx._aca_fpl(THISYEAR, 2, np.asarray(p.gamma_n, dtype=float), THISYEAR)
        assert lines[-1]["amount"] == pytest.approx(round(4.0 * fpl / float(p.gamma_n[0]), 2))

    def test_the_bracket_the_income_fills_and_the_room_to_the_next(self):
        p = FakePlan()
        # The 12/15% edge of a couple in 2026 (the OBBBA table, base dollars).
        edge = float(tx.taxBrackets(2, N_YEARS, N_YEARS)["12/15%"][0])
        p.G_n = np.full(N_YEARS, (edge - 5_000.0) * float(p.gamma_n[0]))
        row = bracket_view(p)["years"][0]
        assert row["fills_bracket"] == "10%"
        assert row["room_to_next_edge"] == pytest.approx(5_000.0)
        p.G_n = np.full(N_YEARS, 1e9)
        row = bracket_view(p)["years"][0]
        assert row["room_to_next_edge"] is None  # above every edge


# ---------------------------------------------------------------------------
# plan.json carries the block (the run page reads the durable files, D7)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def solved_couple():
    p = owl.Plan(["Alice", "Bob"], ["1960-03-10", "1958-07-22"], [88, 85], "test_couple")
    p.setAccountBalances(taxable=[100.0, 80.0], taxDeferred=[500.0, 400.0], taxFree=[50.0, 40.0])
    p.setSpendingProfile("flat")
    p.setAllocationRatios("individual", generic=[[[60, 40, 0, 0], [60, 40, 0, 0]],
                                                 [[60, 40, 0, 0], [60, 40, 0, 0]]])
    p.setRates("conservative")
    p.solve("maxSpending", {"withMedicare": "None"})
    assert p.caseStatus == "solved"
    return p


class TestPlanJson:
    def test_plan_to_dict_carries_the_brackets_block(self, solved_couple):
        doc = plan_to_dict(solved_couple)["brackets"]
        assert doc["units"] == "today's dollars"
        years = doc["years"]
        assert len(years) == solved_couple.N_n
        for row in years:
            assert set(row) >= {"year", "ordinary_taxable_income", "conversion", "magi",
                                "ordinary_edges", "irmaa_edges", "aca_lines"}

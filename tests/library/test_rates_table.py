"""The run's rates table (step 5b, D11): a hand table, the downturn event that generates one
(I11), and what the frozen files carry.

Covers:
- a hand table: stored in the scenario, written as `rates.csv`, named by the generated
  `Case.toml`, and re-imported to the same inputs hash (T1);
- the downturn event: the sequence's window overlaid at its placement (plain years and
  anchors), the baseline kept outside it, the generated case fields marked with the event,
  and the refusal to mix a sequence with a hand table;
- the schema's two consistency rules between the table and the case dictionary;
- a pages save: the table and the events survive it untouched (the pages edit neither).
"""

import copy
from pathlib import Path

import numpy as np
import pytest

from owlplanner.config import config_to_plan, load_toml
from owlplanner.config.toml_io import save_toml
from owlplanner.config.ui_bridge import config_to_ui
from owlplanner.library import ScenarioError, canonicalize, export_case, import_case, scenario_hash
from owlplanner.library import builder as b
from owlplanner.library import scenario as sc
from owlplanner.library.casefiles import scenario_from_case, scenario_from_ui
from owlplanner.library.sequences import sequences

CASE = str(Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml")
HFP = str(Path(__file__).resolve().parents[2] / "examples" / "HFP_jack+jill.xlsx")
CRASH = [-30.0, 2.0, 1.0, 2.0]  # sequences()["crash-30"]["window"][0]


def _rows(first=2026, last=2070):
    """A hand table that covers any plan horizon these tests can ask for."""
    return {
        "columns": ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"],
        "rows": [[year] + (CRASH if year == 2030 else [6.0, 4.5, 3.0, 2.0])
                 for year in range(first, last + 1)],
    }


def _table_case(tmp_path, table=None):
    """A case file whose rates come from a rates.csv beside it (as a run's inputs hold it)."""
    import shutil

    table = _rows() if table is None else table
    case, _, _ = load_toml(CASE)
    case["rates_selection"] = {"method": "table", "rates_file": "rates.csv"}
    shutil.copy(HFP, tmp_path / "HFP_jack+jill.xlsx")
    path = tmp_path / "Case_table.toml"
    save_toml(case, str(path))
    with open(tmp_path / "rates.csv", "w", encoding="utf-8") as f:
        f.write(",".join(table["columns"]) + "\n")
        for row in table["rows"]:
            f.write(",".join(str(v) for v in row) + "\n")
    return path


def _stub_plan(first=2026, years=45, stocks=6.0, cpi=2.0):
    """The baseline rate path `_generated_rates` overlays on: constant rates, known years."""
    import types

    return types.SimpleNamespace(
        year_n=list(range(first, first + years)),
        tau_kn=np.array([[stocks / 100] * years, [0.045] * years, [0.03] * years, [cpi / 100] * years]),
    )


@pytest.fixture
def stub_baseline(monkeypatch):
    monkeypatch.setattr(b, "_throwaway_plan", lambda case, rates_rows=None: _stub_plan())


class TestHandTable:
    def test_the_import_stores_the_table_and_the_files_carry_it(self, tmp_path):
        scenario = import_case(_table_case(tmp_path), hfp_path=HFP)
        assert scenario["rates_table"]["columns"] == ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"]
        assert scenario["rates_table"]["rows"][4] == [2030] + CRASH

        out = tmp_path / "inputs"
        written = {p.name for p in export_case(scenario, out)}
        assert written == {"Case.toml", "HFP.xlsx", "rates.csv"}
        case, _, _ = load_toml(str(out / "Case.toml"))
        assert case["rates_selection"]["method"] == "table"
        assert case["rates_selection"]["rates_file"] == "rates.csv"
        assert (out / "rates.csv").read_text(encoding="utf-8").splitlines()[5] == "2030,-30,2,1,2"

    def test_a_round_trip_reimports_identically(self, tmp_path):
        scenario = import_case(_table_case(tmp_path), hfp_path=HFP)
        out = tmp_path / "inputs"
        export_case(scenario, out)
        again = import_case(out / "Case.toml")
        assert scenario_hash(again) == scenario_hash(scenario)

    def test_owlcli_reads_the_same_rates(self, tmp_path):
        """The step's acceptance in small: `owlcli run` loads the frozen files the same way."""
        scenario = import_case(_table_case(tmp_path), hfp_path=HFP)
        out = tmp_path / "inputs"
        export_case(scenario, out)
        case, dirname, _ = load_toml(str(out / "Case.toml"))
        plan = config_to_plan(case, dirname, verbose=False, loadHFP=True)
        assert plan.rateMethod == "table"
        table = {row[0]: row[1:] for row in scenario["rates_table"]["rows"]}
        for k, year in enumerate(plan.year_n):
            assert list(np.round(100 * plan.tau_kn[:, k], 4)) == table[int(year)]

    def test_a_name_outside_the_run_is_normalized(self, tmp_path):
        case, _, _ = load_toml(CASE)
        case["rates_selection"] = {"method": "table", "rates_file": "my rates.csv"}
        path = tmp_path / "Case_table.toml"
        save_toml(case, str(path))
        table = _rows()
        with open(tmp_path / "my rates.csv", "w", encoding="utf-8") as f:
            f.write(",".join(table["columns"]) + "\n")
            for row in table["rows"]:
                f.write(",".join(str(v) for v in row) + "\n")
        scenario = import_case(path, hfp_path=HFP)
        assert scenario["case"]["rates_selection"]["rates_file"] == "rates.csv"


class TestValidate:
    def test_a_table_needs_the_case_to_name_it(self):
        doc = {"schema_version": 3, "plan_year": 2026,
               "case": {"case_name": "x", "rates_selection": {"method": "historical_average"}},
               "hfp": {}, "rates_table": _rows(first=2026, last=2027)}
        with pytest.raises(ScenarioError, match="must name method = 'table'"):
            sc.validate(doc)

    def test_a_named_table_must_be_present(self):
        doc = {"schema_version": 3, "plan_year": 2026,
               "case": {"case_name": "x", "rates_selection": {"method": "table", "rates_file": "rates.csv"}},
               "hfp": {}}
        with pytest.raises(ScenarioError, match="holds none"):
            sc.validate(doc)

    def test_the_table_is_shape_checked(self):
        doc = {"schema_version": 3, "plan_year": 2026,
               "case": {"case_name": "x", "rates_selection": {"method": "table"}}, "hfp": {},
               "rates_table": {"columns": ["year", "S&P 500"], "rows": [[2026]]}}
        with pytest.raises(ScenarioError, match="rates_table row"):
            sc.validate(doc)


class TestDownturn:
    def test_the_window_sits_at_the_placement_and_the_baseline_elsewhere(self, stub_baseline):
        scenario = {"schema_version": 3, "plan_year": 2026,
                    "case": {"case_name": "x", "rates_selection": {"method": "historical_average"}},
                    "hfp": {},
                    "events": [{"id": "stress", "kind": "downturn", "sequence": "crash-30", "start": 2030}]}
        table = b.rates_table(scenario)
        rows = {row[0]: row[1:] for row in table["rows"]}
        assert rows[2030] == CRASH
        assert rows[2029] == [6.0, 4.5, 3.0, 2.0] and rows[2031] == [6.0, 4.5, 3.0, 2.0]
        assert table["columns"] == ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"]

    def test_the_window_reaches_as_far_as_the_sequence(self, stub_baseline):
        scenario = {"schema_version": 3, "plan_year": 2026,
                    "case": {"case_name": "x"}, "hfp": {},
                    "events": [{"id": "s", "kind": "downturn", "sequence": "three-negative-years",
                                "start": 2040}]}
        rows = {row[0]: row[1:] for row in b.rates_table(scenario)["rows"]}
        window = sequences()["three-negative-years"]["window"]
        for i, values in enumerate(window):
            assert rows[2040 + i] == values

    def test_a_window_past_the_plan_end_is_ignored(self, stub_baseline):
        short = {"schema_version": 3, "plan_year": 2026, "case": {"case_name": "x"}, "hfp": {},
                 "events": [{"id": "s", "kind": "downturn", "sequence": "three-negative-years",
                             "start": 2069}]}
        rows = {row[0]: row[1:] for row in b.rates_table(short)["rows"]}
        window = sequences()["three-negative-years"]["window"]
        assert rows[2069] == window[0] and rows[2070] == window[1]
        assert 2071 not in rows  # the stub's plan ends at 2070; the third window year is unused

    def test_an_anchor_places_it(self, stub_baseline):
        scenario = import_case(CASE)
        scenario["events"] = [{"id": "s", "kind": "downturn", "sequence": "crash-30",
                               "start": {"anchor": "age", "person": "Jack", "age": 70}}]
        born = int(str(scenario["case"]["basic_info"]["date_of_birth"][0])[:4])
        rows = {row[0]: row[1:] for row in b.rates_table(scenario)["rows"]}
        assert rows[born + 70] == CRASH

    def test_the_generated_case_fields_are_marked_with_the_event(self, stub_baseline):
        scenario = import_case(CASE)
        scenario["events"] = [{"id": "stress", "kind": "downturn", "sequence": "crash-30", "start": 2030}]
        case, _tables, provenance = b.build(scenario)
        assert case["rates_selection"]["method"] == "table"
        assert case["rates_selection"]["rates_file"] == "rates.csv"
        assert provenance["case_fields"] == {"rates_selection.method": "stress",
                                             "rates_selection.rates_file": "stress"}

    def test_build_is_deterministic(self, stub_baseline):
        scenario = import_case(CASE)
        scenario["events"] = [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]
        assert b.rates_table(scenario) == b.rates_table(scenario)

    def test_a_hand_table_and_a_sequence_refuse_to_coexist(self, stub_baseline):
        scenario = {"schema_version": 3, "plan_year": 2026, "case": {"case_name": "x",
                    "rates_selection": {"method": "table"}}, "hfp": {}, "rates_table": _rows(2026, 2027),
                    "events": [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]}
        with pytest.raises(ScenarioError, match="drop one"):
            b.rates_table(scenario)

    def test_a_sequence_on_a_table_case_is_refused(self, stub_baseline):
        scenario = {"schema_version": 3, "plan_year": 2026,
                    "case": {"case_name": "x", "rates_selection": {"method": "table"}}, "hfp": {},
                    "events": [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]}
        with pytest.raises(ScenarioError, match="edit the table itself"):
            b.rates_table(scenario)

    def test_an_unknown_sequence_is_refused(self):
        with pytest.raises(ScenarioError, match="sequence"):
            b.validate_events([{"id": "s", "kind": "downturn", "sequence": "nope", "start": 2030}], [])

    def test_the_names_are_the_data_files(self):
        names = sorted(sequences())
        assert ["crash-30", "poor-decade", "three-negative-years"] == names
        for entry in sequences().values():
            assert entry["source"] and entry["description"]
            assert all(len(row) == 4 for row in entry["window"])


class TestRealBaseline:
    def test_the_overlay_sits_on_the_cases_own_rates(self):
        """The real path (no stub): the baseline is the case's own method, as the solve sees it."""
        scenario = import_case(CASE)
        baseline = b._throwaway_plan(scenario["case"])
        scenario["events"] = [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]
        rows = {row[0]: row[1:] for row in b.rates_table(scenario)["rows"]}
        for k, year in enumerate(baseline.year_n):
            expected = CRASH if int(year) == 2030 else list(np.round(100 * baseline.tau_kn[:, k], 4))
            assert rows[int(year)] == expected

    def test_the_gamma_of_a_table_run_is_the_tables_inflation(self):
        """A downturn overlay moves the plan's prices, so it moves the nominal amounts (step 5b)."""
        scenario = import_case(CASE)
        case = copy.deepcopy(scenario["case"])
        case["rates_selection"] = {"method": "table", "rates_file": "rates.csv"}
        rows = [[year, 6.0, 4.5, 3.0, 5.0] for year in range(2026, 2071)]
        gamma = b._gamma(case, rates_rows=rows)
        assert gamma[1] == pytest.approx(1.05)
        assert gamma[2] == pytest.approx(1.05**2, rel=1e-9)


class TestPagesSave:
    def test_a_pages_save_keeps_the_table(self, tmp_path):
        base = import_case(_table_case(tmp_path), hfp_path=HFP)
        case, dirname, _ = load_toml(str(tmp_path / "Case_table.toml"))
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        uidic = config_to_ui(copy.deepcopy(case))
        assert uidic["rateType"] == "table" and uidic["ratesFile"] == "rates.csv"

        scenario = scenario_from_ui(uidic, plan, base=base)
        assert scenario["rates_table"] == base["rates_table"]
        assert scenario_hash(scenario) == scenario_hash(base)

    def test_a_pages_save_keeps_the_downturn_events(self, monkeypatch):
        from owlplanner.library import builder

        monkeypatch.setattr(builder, "_throwaway_plan", lambda case, rates_rows=None: _stub_plan())
        base = import_case(CASE)
        base = dict(base, events=[{"id": "stress", "kind": "downturn", "sequence": "crash-30",
                                   "start": 2030}])
        base = canonicalize(base)
        case, dirname, _ = load_toml(CASE)
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        uidic = config_to_ui(copy.deepcopy(base["case"]))
        scenario = scenario_from_ui(uidic, plan, base=base)
        assert scenario["events"] == base["events"]
        assert "rates_table" not in scenario  # generated from the event, not stored (section 6.3)
        assert scenario_hash(scenario) == scenario_hash(base)


class TestScenarioFromCase:
    def test_a_table_needs_the_case_to_agree(self):
        with pytest.raises(ScenarioError, match="must name method = 'table'"):
            scenario_from_case({"case_name": "x", "rates_selection": {"method": "user"}}, {},
                               rates_table=_rows(2026, 2027))

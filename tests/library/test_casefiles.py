"""Scenario <-> Case.toml / HFP.xlsx: import, export, the round trip, the UI save path.

The example pair examples/Case_jack+jill.toml + HFP_jack+jill.xlsx stands in for the
household's own files (which stay in otherFiles/, offline).
"""

import copy

import pandas as pd
import pytest

from owlplanner.config.plan_bridge import config_to_plan
from owlplanner.config.toml_io import load_toml
from owlplanner.config.ui_bridge import config_to_ui
from owlplanner.library import (
    Library,
    ScenarioError,
    export_case,
    import_case,
    scenario_from_case,
    scenario_from_ui,
)
from owlplanner.library.casefiles import df_to_table, table_to_df

CASE = "examples/Case_jack+jill.toml"


def _normalized_case(case):
    """The case dict with the workbook name (our bookkeeping) equalized."""
    case = copy.deepcopy(case)
    case.setdefault("household_financial_profile", {})["HFP_file_name"] = "HFP.xlsx"
    return case


class TestTables:
    def test_df_to_table_round_trip(self):
        df = pd.DataFrame({"year": [2026, 2027], "amount": [1.5, 2.0]})
        table = df_to_table(df)
        assert table["columns"] == ["year", "amount"]
        assert table_to_df(table).equals(df)

    def test_nan_is_stored_as_null(self):
        df = pd.DataFrame({"year": [2026], "amount": [float("nan")]})
        table = df_to_table(df)
        assert table["rows"] == [[2026, None]]

    def test_numpy_scalars_are_unwrapped(self):
        df = pd.DataFrame({"year": [2026], "flag": [True]})
        table = df_to_table(df)
        assert table["rows"] == [[2026, True]]
        assert all(isinstance(v, (int, bool)) for v in table["rows"][0])


class TestRoundTrip:
    def test_import_export_import_gives_the_same_inputs(self, tmp_path):
        scenario = import_case(CASE)
        assert scenario["schema_version"] == 1
        assert scenario["plan_year"] == 2026
        assert set(scenario["hfp"]) >= {"Debts", "Fixed Assets", "Budget"}

        written = export_case(scenario, tmp_path)
        assert {p.name for p in written} == {"Case.toml", "HFP.xlsx"}

        again = import_case(tmp_path / "Case.toml")
        assert _normalized_case(again["case"]) == _normalized_case(scenario["case"])
        assert again["hfp"] == scenario["hfp"]
        assert again["plan_year"] == scenario["plan_year"]

    def test_the_exported_pair_builds_like_owlcli_does(self, tmp_path):
        """owlcli run: load_toml + config_to_plan(loadHFP=True) on the frozen files."""
        scenario = import_case(CASE)
        export_case(scenario, tmp_path)
        case, dirname, _ = load_toml(str(tmp_path / "Case.toml"))
        plan = config_to_plan(case, dirname, verbose=False, loadHFP=True)
        assert plan is not None
        assert not plan.houseLists["Debts"].empty  # the workbook was found and read

    def test_import_missing_workbook_is_reported(self, tmp_path):
        with pytest.raises(ScenarioError, match="not found"):
            import_case(CASE, hfp_path=tmp_path / "nope.xlsx")


class TestSaveFromThePages:
    def test_an_edited_never_solved_case_saves(self, tmp_path):
        """Build step 1's check: ui_to_config + saveContributions, no solve, no getCaseString."""
        case, dirname, _ = load_toml(CASE)
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        uidic = config_to_ui(copy.deepcopy(case))
        uidic["name"] = "jack+jill edited"
        uidic["txbl0"] = 123.0  # UI $k, same as config $k

        scenario = scenario_from_ui(uidic, plan)
        lib = Library.open(tmp_path / "library")
        result = lib.save_run(name="jack+jill edited", scenario=scenario)
        assert result.created and result.identical_to is None

        inputs = result.run.path / "inputs"
        assert {p.name for p in inputs.iterdir()} >= {"scenario.json", "Case.toml", "HFP.xlsx"}
        saved, _, _ = load_toml(str(inputs / "Case.toml"))
        assert saved["case_name"] == "jack+jill edited"
        assert saved["savings_assets"]["taxable_savings_balances"][0] == 123.0

    def test_two_identical_saves_dedupe(self, tmp_path):
        case, dirname, _ = load_toml(CASE)
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        uidic = config_to_ui(copy.deepcopy(case))
        scenario = scenario_from_ui(uidic, plan)

        lib = Library.open(tmp_path / "library")
        first = lib.save_run(name="one", scenario=scenario)
        second = lib.save_run(name="two", scenario=scenario)
        assert first.created and not second.created
        assert second.identical_to.id == first.run.id


class TestBudgetSidecar:
    def test_the_sidecar_is_written_and_referenced(self, tmp_path):
        case = {
            "case_name": "budgeted",
            "optimization_parameters": {"budget_file": "budget.json"},
        }
        scenario = scenario_from_case(
            case, {}, {}, budget_file={"ref": "budget.json", "text": '{"lines": []}'}
        )
        export_case(scenario, tmp_path)
        assert (tmp_path / "budget.json").read_text(encoding="utf-8") == '{"lines": []}'
        saved, _, _ = load_toml(str(tmp_path / "Case.toml"))
        assert saved["optimization_parameters"]["budget_file"] == "budget.json"

    def test_a_reference_outside_inputs_is_flattened(self, tmp_path):
        case = {
            "case_name": "budgeted",
            "optimization_parameters": {"budget_file": "../shared/budget.json"},
        }
        scenario = scenario_from_case(
            case, {}, {}, budget_file={"ref": "../shared/budget.json", "text": "[]"}
        )
        export_case(scenario, tmp_path)
        assert (tmp_path / "budget.json").exists()
        saved, _, _ = load_toml(str(tmp_path / "Case.toml"))
        assert saved["optimization_parameters"]["budget_file"] == "budget.json"

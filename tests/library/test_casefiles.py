"""Scenario <-> Case.toml / HFP.xlsx: import, export, the round trip, the UI save path.

The example pair examples/Case_jack+jill.toml + HFP_jack+jill.xlsx stands in for the
household's own files (which stay in otherFiles/, offline).
"""

import copy
import io
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from owlplanner.config.plan_bridge import config_to_plan
from owlplanner.config.toml_io import load_toml
from owlplanner.config.ui_bridge import config_to_ui
from owlplanner.library import (
    Library,
    ScenarioError,
    canonicalize,
    diff_summaries,
    export_case,
    import_case,
    scenario_from_case,
    scenario_from_ui,
    scenario_hash,
)
from owlplanner.library.casefiles import df_to_table, table_to_df

CASE = str(Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml")


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

    def test_export_refuses_a_dangling_budget_reference(self, tmp_path):
        """V2: a frozen pair must never reference a file it does not carry."""
        case = {"case_name": "budgeted", "optimization_parameters": {"budget_file": "budget.json"}}
        scenario = scenario_from_case(case, {}, {})
        with pytest.raises(ScenarioError, match="sidecar"):
            export_case(scenario, tmp_path)


class TestBudgetFromThePages:
    def test_sidecar_resolves_against_the_case_dir(self, tmp_path, monkeypatch):
        """V1: the pages' save finds budget.json beside the case, not only in the CWD."""
        casedir = tmp_path / "case"
        casedir.mkdir()
        (casedir / "budget.json").write_text('{"lines": []}', encoding="utf-8")
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)

        case, _, _ = load_toml(CASE)
        case = copy.deepcopy(case)
        case["optimization_parameters"]["budget_file"] = "budget.json"
        case["household_financial_profile"]["HFP_file_name"] = "None"
        plan = config_to_plan(copy.deepcopy(case), str(casedir), verbose=False, loadHFP=False)
        uidic = config_to_ui(copy.deepcopy(case))

        scenario = scenario_from_ui(uidic, plan, case_dir=casedir)
        assert scenario["budget_file"] == {"ref": "budget.json", "text": '{"lines": []}'}

        out = tmp_path / "out"
        export_case(scenario, out)
        assert (out / "budget.json").read_text(encoding="utf-8") == '{"lines": []}'
        saved, _, _ = load_toml(str(out / "Case.toml"))
        assert saved["optimization_parameters"]["budget_file"] == "budget.json"
        again = import_case(out / "Case.toml")
        assert again["budget_file"] == scenario["budget_file"]

    def test_a_missing_budget_file_says_how_to_pass_it(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        case, _, _ = load_toml(CASE)
        case = copy.deepcopy(case)
        case["optimization_parameters"]["budget_file"] = "budget.json"
        plan = config_to_plan(copy.deepcopy(case), str(tmp_path), verbose=False, loadHFP=False)
        uidic = config_to_ui(copy.deepcopy(case))
        with pytest.raises(ScenarioError, match="budget_path"):
            scenario_from_ui(uidic, plan)


class TestNoWorkbook:
    def test_both_entry_paths_agree_without_a_workbook(self, tmp_path):
        """V9: a no-HFP case must hash the same whichever way it was saved."""
        from owlplanner.config.toml_io import save_toml

        case, _, _ = load_toml(CASE)
        case = copy.deepcopy(case)
        case["household_financial_profile"]["HFP_file_name"] = "None"
        buf = io.StringIO()
        save_toml(case, buf)
        case_file = tmp_path / "Case_none.toml"
        case_file.write_text(buf.getvalue(), encoding="utf-8")

        imported = import_case(case_file)
        plan = config_to_plan(copy.deepcopy(case), str(tmp_path), verbose=False, loadHFP=False)
        from_ui = scenario_from_ui(config_to_ui(copy.deepcopy(case)), plan)
        assert imported["hfp"] == from_ui["hfp"]
        # The hash itself agrees once the pages save against the run they were opened from
        # (T1: without a base, ui_to_config's filled-in defaults differ from the file's).
        on_base = scenario_from_ui(config_to_ui(copy.deepcopy(case)), plan, base=imported)
        assert scenario_hash(on_base) == scenario_hash(imported)


def _pages(case_toml=CASE, edit=None):
    """(loaded case, plan, uidic) as the pages hold them after opening a case file."""
    case, dirname, _ = load_toml(str(case_toml))
    plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
    uidic = config_to_ui(copy.deepcopy(case))
    if edit:
        uidic.update(edit)
    return case, plan, uidic


class TestCanonicalCase:
    """T1: the stored case is the case its generated Case.toml reads back as."""

    def test_a_runs_own_files_reimport_identically(self, tmp_path):
        lib = Library.open(tmp_path / "library")
        first = lib.save_run(name="base", scenario=import_case(CASE))
        again = import_case(first.run.path / "inputs" / "Case.toml")
        assert scenario_hash(again) == first.run.inputs_hash
        second = lib.save_run(name="reopened", scenario=again, parent=first.run)
        assert not second.created and second.identical_to.id == first.run.id

    def test_canonicalize_is_idempotent(self):
        scenario = import_case(CASE)
        assert canonicalize(copy.deepcopy(scenario)) == scenario

    def test_floats_are_stored_as_the_toml_reads_them(self, tmp_path):
        import toml

        scenario = scenario_from_case({"case_name": "x", "basic_info": {"age": 62 + 1 / 12}}, {}, {})
        assert scenario["case"]["basic_info"]["age"] == 62.083333
        export_case(scenario, tmp_path)
        assert toml.load(tmp_path / "Case.toml") == scenario["case"]

    def test_table_cells_do_not_depend_on_how_they_were_read(self):
        one = scenario_from_case({"case_name": "x"}, {"A": {"columns": ["v"], "rows": [[0.0], [1.5]]}}, {})
        two = scenario_from_case({"case_name": "x"}, {"A": {"columns": ["v"], "rows": [[0], [1.5]]}}, {})
        assert one["hfp"]["A"]["rows"] == [[0], [1.5]]
        assert scenario_hash(one) == scenario_hash(two)

    def test_a_page_scenario_matches_its_generated_files(self, tmp_path):
        _, plan, uidic = _pages()
        scenario = scenario_from_ui(uidic, plan)
        export_case(scenario, tmp_path)
        assert scenario_hash(import_case(tmp_path / "Case.toml")) == scenario_hash(scenario)

    def test_a_hand_built_scenario_is_canonicalized_on_save(self, tmp_path):
        lib = Library.open(tmp_path / "library")
        raw = {"schema_version": 1, "case": {"case_name": "x", "v": 1 / 3}, "hfp": {}}
        result = lib.save_run(name="x", scenario=raw)
        stored = lib.scenario(result.run)
        assert stored["case"]["v"] == 0.33333333
        assert stored["case"]["household_financial_profile"]["HFP_file_name"] == "None"


class TestSaveOnABase:
    """T1, T3: the pages save against the run they were opened from."""

    def test_an_unedited_save_is_identical_to_its_base(self):
        base = import_case(CASE)
        _, plan, uidic = _pages()
        scenario = scenario_from_ui(uidic, plan, base=base)
        assert diff_summaries(base, scenario) == []
        assert scenario_hash(scenario) == scenario_hash(base)

    def test_an_edit_is_the_only_change(self):
        base = import_case(CASE)
        _, plan, uidic = _pages(edit={"txbl0": 123.0})
        scenario = scenario_from_ui(uidic, plan, base=base)
        changes = diff_summaries(base, scenario)
        assert len(changes) == 1
        assert changes[0].startswith("case.savings_assets.taxable_savings_balances")

    def test_without_a_base_the_page_defaults_show(self):
        """Why base= exists: ui_to_config fills fields the file leaves out."""
        base = import_case(CASE)
        _, plan, uidic = _pages()
        assert diff_summaries(base, scenario_from_ui(uidic, plan)) != []

    def test_the_base_plan_year_is_kept(self, tmp_path):
        case, _, _ = load_toml(CASE)
        case["basic_info"]["start_date"] = "2025-01-01"
        case["household_financial_profile"]["HFP_file_name"] = str(Path(CASE).parent / "HFP_jack+jill.xlsx")
        buf = io.StringIO()
        from owlplanner.config.toml_io import save_toml

        save_toml(case, buf)
        case_file = tmp_path / "Case_2025.toml"
        case_file.write_text(buf.getvalue(), encoding="utf-8")
        base = import_case(case_file)
        assert base["plan_year"] == 2025

        _, plan, uidic = _pages(case_file)
        assert uidic["startDate"].year == date.today().year  # the pages show the current year
        scenario = scenario_from_ui(uidic, plan, base=base)
        assert scenario["plan_year"] == 2025
        assert scenario["case"]["basic_info"]["start_date"] == "2025-01-01"
        assert scenario_hash(scenario) == scenario_hash(base)

        _, plan, uidic = _pages(case_file, edit={"startDate": date(date.today().year, 3, 15)})
        moved = scenario_from_ui(uidic, plan, base=base)
        assert moved["plan_year"] == 2025
        assert moved["case"]["basic_info"]["start_date"] == "2025-03-15"

    def test_plan_year_without_a_base(self):
        _, plan, uidic = _pages()
        scenario = scenario_from_ui(uidic, plan, plan_year=2025)
        assert scenario["plan_year"] == 2025
        assert scenario["case"]["basic_info"]["start_date"].startswith("2025-")

    def test_the_base_sidecar_is_reused(self, tmp_path, monkeypatch):
        casedir = tmp_path / "case"
        casedir.mkdir()
        (casedir / "budget.json").write_text('{"lines": []}', encoding="utf-8")
        case, _, _ = load_toml(CASE)
        case["optimization_parameters"]["budget_file"] = "budget.json"
        case["household_financial_profile"]["HFP_file_name"] = "None"
        plan = config_to_plan(copy.deepcopy(case), str(casedir), verbose=False, loadHFP=False)
        base = scenario_from_ui(config_to_ui(copy.deepcopy(case)), plan, case_dir=casedir)

        monkeypatch.chdir(tmp_path)  # the file is no longer reachable: the base carries it
        scenario = scenario_from_ui(config_to_ui(copy.deepcopy(case)), plan, base=base)
        assert scenario["budget_file"] == base["budget_file"]
        assert scenario_hash(scenario) == scenario_hash(base)

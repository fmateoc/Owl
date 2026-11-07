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
    SCHEMA_VERSION,
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
        assert scenario["schema_version"] == SCHEMA_VERSION
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

    def test_a_case_opened_under_its_run_s_name_saves_unchanged(self, tmp_path):
        """QW-7.3: "Edit as new run" opens a run's case under the run's own name, made unique
        in the session ("bill later (2)"); the save against that run keeps the run's case
        name, so an unedited save is still identical to it (no "case_name" change)."""
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
        uidic = config_to_ui(copy.deepcopy(case))
        uidic["name"] = "some run (2)"
        on_base = scenario_from_ui(uidic, plan, base=imported)
        assert on_base["case"]["case_name"] == imported["case"]["case_name"]
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
        assert changes[0].startswith("taxable savings balances[0]: ")  # in words (UX review Q9)

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


class TestDropGenerated:
    def _base(self, monkeypatch):
        from owlplanner.library import builder

        monkeypatch.setattr(builder, "_gamma", lambda case, rates_rows=None: [1.0, 1.02])
        base = import_case(CASE)
        return dict(base, events=[
            {"id": "w", "kind": "work", "person": "Jack", "start": 2026, "end": 2026, "wages": 5000},
            {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2026, "flat_until": 2027},
        ])

    def test_a_pages_save_drops_the_generated_rows_and_cells(self, monkeypatch):
        """Markers first (S11): the plan's tables carry the generated values too (the pages load
        the run's frozen files); a save keeps only the hand rows and cells. Section 6.3's
        per-cell overrides are the later increment."""
        from owlplanner.library import builder
        from owlplanner.library.casefiles import _drop_generated

        base = self._base(monkeypatch)
        _case, _tables, provenance = builder.build(base)
        columns = list(base["hfp"]["Jack"]["columns"])
        rows = [list(row) for row in base["hfp"]["Jack"]["rows"]]
        for row in rows:
            if row[columns.index("year")] == 2026:
                row[columns.index("anticipated wages")] = 777  # generated: dropped
                row[columns.index("Roth conv")] = 5  # hand: kept
        budget_columns = list(builder.BUDGET_COLUMNS)
        house_lists = {"Budget": {"columns": budget_columns, "rows": [
            [True, "rent", "rent", 2026, 2026, 999, 0, None, True] + [None] * 5,
            [True, "charity", "charity", 2026, 0, 3000, 0, None, False] + [None] * 5,
        ]}}
        clean_time, clean_house = _drop_generated({"Jack": {"columns": columns, "rows": rows}},
                                                  house_lists, provenance)
        jack = {row[columns.index("year")]: row for row in clean_time["Jack"]["rows"]}
        assert jack[2026][columns.index("anticipated wages")] == 0
        assert jack[2026][columns.index("Roth conv")] == 5
        names = [row[budget_columns.index("name")] for row in clean_house["Budget"]["rows"]]
        assert names == ["charity"]  # "rent" is generated: regenerated wholesale at build time

    def test_a_pages_save_drops_the_generated_case_fields(self, monkeypatch):
        """Review U1: the pages hold the generated case fields too (their `before` is the hand
        case, their `after` the materialized one), and `build` writes a generated field only
        while its event exists. A saved hand case must not carry them, or deleting an event
        later leaves stale, unmarked inputs steering the plan."""
        from owlplanner.library import builder
        from owlplanner.library.casefiles import _drop_generated_case

        base = self._base(monkeypatch)
        base["events"] = [
            *base["events"],
            {"id": "buy", "kind": "purchase", "name": "h", "price": 700000, "year": 2027,
             "pay_on": "Jack",
             "place": {"state": "NY", "locality": "", "school_district": "City of Yonkers / Yonkers", "move": True},
             "financing": {"kind": "cash", "closing": 0.03}},
            {"id": "claim", "kind": "claim", "person": "Jack", "age": 62.0},
        ]
        _case, _tables, provenance = builder.build(base)
        assert set(provenance["case_fields"]) >= {
            "basic_info.moves", "aca_settings.aca_start_year", "solver_options.withSSAges"}
        cleaned = _drop_generated_case(_case, provenance, base["case"])
        assert "moves" not in cleaned["basic_info"]  # the base's hand case held none
        # The hand values the events overrode are back: the claiming ages (the fallback for a
        # person with no claim event) and the case's own switch.
        assert (cleaned["fixed_income"]["social_security_ages"]
                == base["case"]["fixed_income"]["social_security_ages"])
        assert (cleaned.get("solver_options", {}).get("withSSAges")
                == base["case"].get("solver_options", {}).get("withSSAges"))
        # Rebuilding with the purchase deleted leaves no move behind (the U1 probe).
        events = [e for e in base["events"] if e["id"] != "buy"]
        rebuilt, _tables2, provenance2 = builder.build(dict(base, case=cleaned, events=events))
        assert "moves" not in rebuilt["basic_info"]
        assert provenance2["case_fields"].get("basic_info.moves") is None


class TestPagesSaveWithEvents:
    """Review X1/X2: "Edit as new run" and a save from the case pages, end to end, on a run
    with events: the events stay the run's, the hand values they replaced come back, and an
    unedited save is the base itself (T1)."""

    EVENTS = [
        # Over a year whose hand cell holds wages (the hand value must come back on delete).
        {"id": "w", "kind": "work", "person": "Jack", "start": 2026, "end": 2026, "wages": 5000},
        {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2026, "flat_until": 2027},
        {"id": "buy", "kind": "purchase", "name": "condo", "price": 700000, "year": 2028,
         "pay_on": "Jack", "costs": {"property tax": 9500},  # jack+jill live in TN: no district
         "financing": {"kind": "loan", "term": 30, "rate": 6.25}},
        {"id": "c", "kind": "claim", "person": "Jill", "age": 64.0},
    ]

    def _base(self, hand_budget_row=None):
        base = import_case(CASE)
        if hand_budget_row is not None:  # a hand row the purchase's owner lines replace by name
            budget = base["hfp"].setdefault("Budget", {"columns": None, "rows": []})
            from owlplanner.library import builder

            budget["columns"] = budget.get("columns") or list(builder.BUDGET_COLUMNS)
            budget["rows"] = [*budget["rows"], hand_budget_row]
        return canonicalize(dict(base, events=copy.deepcopy(self.EVENTS)))

    def _pages_save(self, base, tmp_path):
        """What the pages do: open the run's frozen files, then save against the run."""
        export_case(base, tmp_path)
        case, _, _ = load_toml(str(tmp_path / "Case.toml"))
        plan = config_to_plan(copy.deepcopy(case), str(tmp_path), verbose=False)
        return scenario_from_ui(config_to_ui(copy.deepcopy(case)), plan, base=base)

    def _jack(self, hfp, year, column):
        table = hfp["Jack"]
        row = next(r for r in table["rows"] if r[table["columns"].index("year")] == year)
        return row[table["columns"].index(column)]

    def test_an_unedited_save_keeps_the_events_and_is_the_base(self, tmp_path):
        base = self._base()
        hand_wages = self._jack(base["hfp"], 2026, "anticipated wages")
        assert hand_wages not in (0, 5000)  # the event overrides a real hand value
        child = self._pages_save(base, tmp_path)
        assert child["events"] == base["events"]
        assert diff_summaries(base, child) == []
        assert scenario_hash(child) == scenario_hash(base)

    def test_deleting_an_event_after_a_save_brings_the_hand_value_back(self, tmp_path):
        from owlplanner.library import builder

        base = self._base()
        hand_wages = self._jack(base["hfp"], 2026, "anticipated wages")
        child = self._pages_save(base, tmp_path)
        gone = canonicalize(dict(child, events=[e for e in child["events"] if e["id"] != "w"]))
        _case, hfp, _provenance = builder.build(gone)
        assert self._jack(hfp, 2026, "anticipated wages") == hand_wages

    def test_a_hand_row_replaced_by_name_comes_back_in_place(self, tmp_path):
        from owlplanner.library import builder

        hand = builder.budget_row("property tax", "property tax", 2026, 0, 1234, rate=1.0, essential=True)
        base = self._base(hand_budget_row=hand)
        child = self._pages_save(base, tmp_path)
        assert child["hfp"]["Budget"] == base["hfp"]["Budget"]
        assert scenario_hash(child) == scenario_hash(base)

    def test_drop_generated_restores_from_the_base(self, monkeypatch):
        from owlplanner.library import builder
        from owlplanner.library.casefiles import _drop_generated

        monkeypatch.setattr(builder, "_gamma", lambda case, rates_rows=None: [1.0, 1.02, 1.0404])
        base = self._base()
        _case, tables, provenance = builder.build(base)
        clean_time, _clean_house = _drop_generated({"Jack": tables["Jack"]}, {}, provenance, base["hfp"])
        assert (self._jack(clean_time, 2026, "anticipated wages")
                == self._jack(base["hfp"], 2026, "anticipated wages"))

    # Review W1: an edit to a value the events generate is regenerated away on save; the
    # save reports it (`dropped`) rather than losing it silently.

    def _saved_with(self, base, tmp_path, edit):
        """The pages' save after `edit(plan)`: (the saved scenario, the `dropped` report)."""
        export_case(base, tmp_path)
        case, _, _ = load_toml(str(tmp_path / "Case.toml"))
        plan = config_to_plan(copy.deepcopy(case), str(tmp_path), verbose=False)
        edit(plan)
        dropped = []
        child = scenario_from_ui(config_to_ui(copy.deepcopy(case)), plan, base=base, dropped=dropped)
        return child, dropped

    def test_an_edit_to_a_generated_row_is_reported_and_not_kept(self, tmp_path):
        def edit(plan):
            budget = plan.houseLists["Budget"]
            assert "rent" in list(budget["name"])  # the event's rows are in the frozen workbook
            budget.loc[budget["name"] == "rent", "amount"] = 12345.0

        child, dropped = self._saved_with(self._base(), tmp_path, edit)
        assert any(d.startswith("Budget row 'rent'") for d in dropped), dropped
        rows = child["hfp"]["Budget"]
        name_at = rows["columns"].index("name")
        assert all(row[name_at] != "rent" for row in rows["rows"])  # regenerated at export

    def test_an_edit_to_a_generated_cell_is_reported(self, tmp_path):
        def edit(plan):
            jack = plan.timeLists["Jack"]
            jack.loc[jack["year"] == 2026, "anticipated wages"] = 4321.0

        _child, dropped = self._saved_with(self._base(), tmp_path, edit)
        assert any(d.startswith("Jack anticipated wages 2026") for d in dropped), dropped

    def test_an_unedited_save_reports_nothing(self, tmp_path):
        base = self._base()
        child, dropped = self._saved_with(base, tmp_path, lambda plan: None)
        assert dropped == []
        assert scenario_hash(child) == scenario_hash(base)

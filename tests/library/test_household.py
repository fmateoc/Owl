"""A household's first inputs without a case file (`library.household`; the first-time setup).

Answers in dollars -> a complete Owl case, an empty workbook to fill in Excel, a filled one
read back in words, the first run's scenario. The tests run at the suite's frozen date
(2026-01-01).
"""

import copy
import io
from datetime import date

import openpyxl
import pytest

from owlplanner.library import Library, ScenarioError, check_plan_year, export_case
from owlplanner.library import household as H

TODAY = date(2026, 1, 1)


def _answers(**changes):
    answers = H.blank_answers(TODAY)
    answers["people"][0].update(name="Ari", born="1964-04-17", taxable=800_000, tax_deferred=550_000,
                                ss_monthly=3150)
    answers["people"][1].update(name="Noa", born="1964-12-09", taxable=800_000, tax_deferred=400_000,
                                ss_monthly=2500)
    answers.update(state="NY", locality="Yonkers")
    answers.update(changes)
    return answers


def _filled(tmp_path, answers):
    """The empty workbook, then what a person would type in Excel."""
    book = H.write_workbook(tmp_path / "Household.xlsx", answers, TODAY)
    wb = openpyxl.load_workbook(book)
    wb["Ari"]["B2"] = 168_000
    wb["Ari"]["P4"] = -40_000  # a car in 2028
    wb["Budget"].append([True, "rent", "rent", 2026, 0, 48_000, 0.0, None, True, None, None, None, None, None])
    wb["Budget"].append([True, "everything else", "core", 2026, 0, 60_000, 0.0, None, False,
                         None, None, None, None, None])
    wb.save(book)
    return book


class TestProblems:
    def test_blank_answers_say_what_is_missing(self):
        found = H.problems(H.blank_answers(TODAY), TODAY)
        assert "Person 1 has no name yet." in found
        assert any("date of birth is missing" in p for p in found)
        assert any("No savings are entered" in p for p in found)

    def test_complete_answers_have_none(self):
        assert H.problems(_answers(), TODAY) == []

    def test_one_person(self):
        answers = _answers(couple=False)
        answers["people"][1] = copy.deepcopy(H._PERSON)  # the second person is not asked
        assert H.problems(answers, TODAY) == []

    @pytest.mark.parametrize("change, said", [
        ({"name": "Budget"}, "cannot name a workbook sheet"),
        ({"name": "A/B"}, "cannot name a workbook sheet"),
        ({"born": "2020-01-01"}, "Check the date of birth"),
        ({"plan_to_age": 62}, "Plan at least two years ahead"),
        ({"ss_monthly": 38_000}, "not a yearly one"),
        ({"ss_age": 71.0}, "between 62 and 70"),
        ({"cost_basis": 900_000}, "cannot be more than they are worth"),
        ({"taxable": -5}, "must be an amount of zero or more"),
    ])
    def test_a_persons_mistakes_are_said_in_words(self, change, said):
        answers = _answers()
        answers["people"][0].update(change)
        assert any(said in p for p in H.problems(answers, TODAY)), H.problems(answers, TODAY)

    def test_the_same_name_twice(self):
        answers = _answers()
        answers["people"][1]["name"] = "Ari"
        assert any("different names" in p for p in H.problems(answers, TODAY))

    def test_balances_of_another_year(self):
        assert any("as of a date in 2026" in p for p in H.problems(_answers(balance_date="2025-12-31"), TODAY))

    def test_the_goals_own_amounts(self):
        assert any("how much you spend" in p for p in H.problems(_answers(goal="leave"), TODAY))
        assert H.problems(_answers(goal="leave", spending=90_000), TODAY) == []
        assert any("benchmark premium" in p for p in H.problems(_answers(marketplace=True), TODAY))


class TestTheCase:
    def test_dollars_become_the_cases_thousands(self):
        case = H.case_from_answers(_answers(bequest=250_000), today=TODAY)
        assert case["savings_assets"]["taxable_savings_balances"] == [800.0, 800.0]
        assert case["savings_assets"]["tax_deferred_savings_balances"] == [550.0, 400.0]
        assert case["solver_options"]["bequest"] == 250.0
        assert case["fixed_income"]["social_security_pia_amounts"] == [3150.0, 2500.0]  # monthly, as typed

    def test_the_people_and_the_place(self):
        info = H.case_from_answers(_answers(), today=TODAY)["basic_info"]
        assert info["status"] == "married" and info["names"] == ["Ari", "Noa"]
        assert info["date_of_birth"] == ["1964-04-17", "1964-12-09"] and info["life_expectancy"] == [89, 89]
        assert (info["state"], info["locality"], info["start_date"]) == ("NY", "Yonkers", "2026-01-01")
        single = H.case_from_answers(_answers(couple=False), today=TODAY)
        assert single["basic_info"]["status"] == "single" and single["basic_info"]["names"] == ["Ari"]
        assert len(single["asset_allocation"]["generic"]) == 1

    def test_claiming_ages_left_to_owl(self):
        answers = _answers()
        assert H.case_from_answers(answers, today=TODAY)["solver_options"]["withSSAges"] == "fixed"
        answers["people"][1]["ss_age"] = None
        case = H.case_from_answers(answers, today=TODAY)
        assert case["solver_options"]["withSSAges"] == ["Noa"]
        assert case["fixed_income"]["social_security_ages"] == [67.0, 67.0]
        answers["people"][0]["ss_age"] = None
        assert H.case_from_answers(answers, today=TODAY)["solver_options"]["withSSAges"] == "optimize"

    def test_the_goal(self):
        spend = H.case_from_answers(_answers(), today=TODAY)
        assert spend["optimization_parameters"]["objective"] == "maxSpending"
        leave = H.case_from_answers(_answers(goal="leave", spending=90_000), today=TODAY)
        assert leave["optimization_parameters"]["objective"] == "maxBequest"
        assert leave["solver_options"]["netSpending"] == 90.0 and "bequest" not in leave["solver_options"]

    def test_the_cost_basis_and_the_marketplace_only_when_given(self):
        plain = H.case_from_answers(_answers(), today=TODAY)
        assert "taxable_cost_basis" not in plain["savings_assets"] and "aca_settings" not in plain
        answers = _answers(marketplace=True, marketplace_year=2027, marketplace_premium=20_840)
        answers["people"][0]["cost_basis"] = 500_000
        case = H.case_from_answers(answers, today=TODAY)
        assert case["savings_assets"]["taxable_cost_basis"] == [500.0, 800.0]  # unknown: no gain assumed
        assert case["aca_settings"] == {"slcsp_annual": 20.84, "aca_start_year": 2027}

    def test_the_assumptions_nobody_was_asked(self):
        rates = H.case_from_answers(_answers(), today=TODAY)["rates_selection"]
        assert rates["method"] == "conservative" and rates["obbba_expiration_year"] == 2066


class TestTheWorkbook:
    def test_the_empty_workbook_has_a_sheet_per_person_and_a_row_per_year(self, tmp_path):
        book = H.write_workbook(tmp_path / "Household.xlsx", _answers(), TODAY)
        wb = openpyxl.load_workbook(book)
        assert wb.sheetnames == ["Instructions", "Ari", "Noa", "Budget", "Debts", "Fixed Assets"]
        years = [row[0].value for row in wb["Ari"].iter_rows(min_row=2)]
        assert years == list(range(2026, 2054))  # to the year both reach 89
        assert wb["Ari"]["B1"].value == "anticipated wages" and "tax return" in wb["Ari"]["B1"].comment.text
        assert [c.value for c in wb["Budget"][1]][:6] == ["active", "name", "type", "year", "end", "amount"]

    def test_it_never_replaces_a_file(self, tmp_path):
        H.write_workbook(tmp_path / "Household.xlsx", _answers(), TODAY)
        with pytest.raises(ScenarioError, match="is not replaced"):
            H.write_workbook(tmp_path / "Household.xlsx", _answers(), TODAY)

    def test_it_needs_the_names(self, tmp_path):
        with pytest.raises(ScenarioError, match="give each person a name"):
            H.write_workbook(tmp_path / "Household.xlsx", H.blank_answers(TODAY), TODAY)

    def test_the_untouched_workbook_reads_as_nothing(self, tmp_path):
        book = H.write_workbook(tmp_path / "Household.xlsx", _answers(), TODAY)
        read = H.read_workbook(book, _answers(), TODAY)
        assert read["lines"][0] == "**Ari**: no wages."
        assert any(line.startswith("**Budget**: none") for line in read["lines"])
        assert read["scenario"]["case"]["optimization_parameters"]["spending_profile"] == "flat"

    def test_a_filled_workbook_is_read_back_in_words(self, tmp_path):
        read = H.read_workbook(_filled(tmp_path, _answers()), _answers(), TODAY)
        assert read["lines"][0] == ("**Ari**: wages from 2026 to 2026 (the largest year $168,000); "
                                    "one-time amounts: 2028: -40,000.")
        assert "**Budget**: 2 budget lines (rent, everything else)." in read["lines"]
        # Budget lines make the plan spend by them.
        assert read["scenario"]["case"]["optimization_parameters"]["spending_profile"] == "budget"

    def test_a_mistyped_heading_is_refused_by_name(self, tmp_path):
        book = H.write_workbook(tmp_path / "Household.xlsx", _answers(), TODAY)
        wb = openpyxl.load_workbook(book)
        wb["Ari"]["B1"] = "Anticipated  Wages"
        wb.save(book)
        with pytest.raises(Exception, match="(?i)anticipated"):
            H.read_workbook(book, _answers(), TODAY)


class TestTheFirstRun:
    def test_incomplete_answers_make_no_scenario(self):
        with pytest.raises(ScenarioError, match="no name yet"):
            H.first_scenario(H.blank_answers(TODAY), today=TODAY)

    def test_the_scenario_is_a_run_the_library_solves_this_year(self, tmp_path):
        scenario = H.first_scenario(_answers(), _filled(tmp_path, _answers()), name="Our plan", today=TODAY)
        lib = Library.open(tmp_path / "library")
        run = lib.save_run(name="Our plan", scenario=scenario).run
        assert run.plan_year == 2026 and check_plan_year(lib.scenario(run)) == 2026
        export_case(lib.scenario(run), tmp_path / "out")
        assert (tmp_path / "out" / "Case.toml").exists() and (tmp_path / "out" / "HFP.xlsx").exists()

    def test_the_plan_solves(self, tmp_path):
        """End to end: the answers' case and workbook through Owl's own loader, solved."""
        from owlplanner.config.plan_bridge import config_to_plan
        from owlplanner.config.toml_io import load_toml
        from owlplanner.library import resolve_options

        scenario = H.first_scenario(_answers(), _filled(tmp_path, _answers()), today=TODAY)
        export_case(scenario, tmp_path / "out")
        case, dirname, _ = load_toml(str(tmp_path / "out" / "Case.toml"))
        plan = config_to_plan(case, dirname, verbose=False, logstreams=[io.StringIO()], loadHFP=True)
        plan.solve(plan.objective, resolve_options("quick", plan.solverOptions, None))
        assert plan.caseStatus == "solved"
        assert plan.year_n[0] == 2026 and plan.year_n[-1] == 2053


class TestTheFolder:
    def test_the_household_folder(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OWL_HOME_DIR", raising=False)
        assert H.home_dir(tmp_path / "home" / "library") == (tmp_path / "home").resolve()
        monkeypatch.setenv("OWL_HOME_DIR", str(tmp_path / "elsewhere"))
        assert H.home_dir(tmp_path / "home" / "library") == tmp_path / "elsewhere"

    def test_the_workbooks_in_it(self, tmp_path):
        for name in ("b.xlsx", "a.xlsx", "~$a.xlsx", "notes.txt"):
            (tmp_path / name).write_bytes(b"x")
        assert [p.name for p in H.workbooks(tmp_path)] == ["a.xlsx", "b.xlsx"]
        assert H.workbooks(tmp_path / "missing") == []

    def test_an_upload_is_kept_once_and_never_over_another_file(self, tmp_path):
        first = H.keep_upload(tmp_path, "ours.xlsx", b"one")
        assert H.keep_upload(tmp_path, "ours.xlsx", b"one") == first
        other = H.keep_upload(tmp_path, "ours.xlsx", b"two")
        assert other.name == "ours (2).xlsx" and first.read_bytes() == b"one"

    def test_the_draft_is_kept_and_read_back(self, tmp_path):
        answers = _answers()
        H.save_draft(tmp_path, answers)
        assert H.load_draft(tmp_path, TODAY) == answers
        H.drop_draft(tmp_path)
        assert H.load_draft(tmp_path, TODAY) == H.blank_answers(TODAY)

    def test_a_draft_of_last_year_keeps_the_people_and_asks_for_this_years_date(self, tmp_path):
        H.save_draft(tmp_path, _answers(balance_date="2025-03-01"))
        draft = H.load_draft(tmp_path, TODAY)
        assert draft["people"][0]["name"] == "Ari" and draft["balance_date"] == "2026-01-01"

    def test_a_damaged_draft_starts_over(self, tmp_path):
        (tmp_path / H.DRAFT_JSON).write_text("{not json", encoding="utf-8")
        assert H.load_draft(tmp_path, TODAY) == H.blank_answers(TODAY)

    @pytest.mark.parametrize("platform, name, calls", [
        ("win32", "Start Owl.cmd", 'owlplanner-library.cmd" "%~dp0."'),
        ("darwin", "Start Owl.command", "owlplanner-library.sh"),
        ("linux", "start-owl.sh", "owlplanner-library.sh"),
    ])
    def test_the_starter_file(self, tmp_path, platform, name, calls):
        starter = H.write_starter(tmp_path, platform)
        assert starter.name == name and calls in starter.read_text(encoding="utf-8")
        starter.write_text("mine", encoding="utf-8")
        assert H.write_starter(tmp_path, platform).read_text(encoding="utf-8") == "mine"  # left alone

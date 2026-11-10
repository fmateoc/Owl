"""The first-time setup through the pages (Start, Set up our plan), rendered by AppTest.

With no plan in the folder the Start page offers to make one or to bring in files; the Setup
page asks for the household's figures in a form (no case file), reads or writes the workbook,
and makes the first run, pinned and queued for a first solve. With a plan, the Start page
asks what to do with it and shows the steps.
"""

import json
from pathlib import Path

import openpyxl
import pytest

from owlplanner.library import JobManager, Library, import_case
from owlplanner.library import household as H

UI_DIR = Path(__file__).resolve().parents[2] / "ui"


@pytest.fixture
def home(tmp_path, monkeypatch):
    folder = tmp_path / "Our Plan"
    monkeypatch.setenv("OWL_HOME_DIR", str(folder))
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(folder / "library"))
    monkeypatch.syspath_prepend(str(UI_DIR))
    monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # no real worker
    return folder


def _answers():
    answers = H.blank_answers()
    answers["people"][0].update(name="Ari", born="1964-04-17", taxable=800_000, tax_deferred=550_000,
                                ss_monthly=3150)
    answers["people"][1].update(name="Noa", born="1964-12-09", taxable=800_000, tax_deferred=400_000,
                                ss_monthly=2500, ss_age=None)
    answers.update(state="NY", locality="Yonkers")
    return answers


def _page(name, state=None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / name), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    for key, value in (state or {}).items():
        at.session_state[key] = value
    return at.run()


def _stop_at_switch(monkeypatch):
    import streamlit as st

    opened = []

    def switch(page):
        opened.append(page)
        st.stop()

    monkeypatch.setattr("streamlit.switch_page", switch)
    return opened


def _text(at):
    return "\n".join([m.value for m in at.markdown] + [c.value for c in at.caption]
                     + [i.value for i in at.info] + [w.value for w in at.warning] + [e.value for e in at.error])


class TestAnEmptyFolder:
    def test_start_offers_the_two_ways_in(self, home, monkeypatch):
        opened = _stop_at_switch(monkeypatch)
        at = _page("Start.py")
        assert not at.exception, [e.value for e in at.exception]
        assert "This folder has no plan yet" in _text(at) and str(home) in _text(at)
        assert {b.label for b in at.button} >= {"Set up our plan", "Bring in files"}
        at.button(key="start_setup").click().run()
        assert opened == ["Setup.py"]

    def test_start_leaves_a_starter_file_in_the_folder(self, home):
        _page("Start.py")
        starters = [p.name for p in home.iterdir() if p.is_file()]
        assert len(starters) == 1 and starters[0] in ("Start Owl.cmd", "Start Owl.command", "start-owl.sh")

    def test_setup_says_what_is_still_needed_and_makes_nothing(self, home):
        at = _page("Setup.py")
        assert not at.exception, [e.value for e in at.exception]
        assert "Still needed:" in _text(at) and "Person 1 has no name yet." in _text(at)
        at.button(key="setup_make").click().run()
        assert any("Not yet" in w.value for w in at.warning)
        assert Library.open(home / "library").runs() == []


class TestSetup:
    def test_what_is_typed_is_kept_in_the_folder(self, home):
        at = _page("Setup.py")
        at.text_input(key="setup_name0").set_value("Ari").run()
        at.number_input(key="setup_txbl0").set_value(800_000).run()
        draft = json.loads((home / "library" / H.DRAFT_JSON).read_text(encoding="utf-8"))
        assert draft["people"][0]["name"] == "Ari" and draft["people"][0]["taxable"] == 800_000
        # A new session (a closed tab) finds it.
        again = _page("Setup.py")
        assert again.text_input(key="setup_name0").value == "Ari"
        assert "Savings entered: **\\$800,000** in all." in _text(again)

    def test_the_plan_is_made_pinned_and_queued(self, home, monkeypatch):
        opened = _stop_at_switch(monkeypatch)
        at = _page("Setup.py", {"setup_answers": _answers()})
        assert "Still needed:" not in _text(at)
        at.button(key="setup_make").click().run()
        assert not at.exception, [e.value for e in at.exception]
        lib = Library.open(home / "library")
        (run,) = lib.runs()
        assert run.name == "Our plan" and run.plan_year == 2026 and lib.baseline().id == run.id
        case = lib.scenario(run)["case"]
        assert case["basic_info"]["names"] == ["Ari", "Noa"] and case["basic_info"]["locality"] == "Yonkers"
        assert case["savings_assets"]["taxable_savings_balances"] == [800.0, 800.0]  # dollars typed, $k stored
        assert case["solver_options"]["withSSAges"] == ["Noa"]
        assert [job.doc["preset"] for job in JobManager(lib).jobs(run)] == ["quick"]
        assert opened == ["Run.py"] and at.session_state["library_selected_run"] == run.id
        assert not (home / "library" / H.DRAFT_JSON).exists()  # the run holds the answers now

    def test_an_empty_workbook_is_written_into_the_folder_and_read(self, home):
        at = _page("Setup.py", {"setup_answers": _answers()})
        at.radio(key="setup_book_mode").set_value("new").run()
        at.button(key="setup_book_make").click().run()
        assert not at.exception, [e.value for e in at.exception]
        book = home / H.WORKBOOK_NAME
        assert openpyxl.load_workbook(book).sheetnames[:3] == ["Instructions", "Ari", "Noa"]
        assert "is ready. Open it in Excel" in _text(at) and "**Ari**: no wages." in _text(at)
        # Filled in Excel, saved: the page reads it again.
        wb = openpyxl.load_workbook(book)
        wb["Ari"]["B2"] = 168_000
        wb["Budget"].append([True, "rent", "rent", 2026, 0, 48_000, 0.0, None, True, None, None, None, None, None])
        wb.save(book)
        at.button(key="setup_book_again").click().run()
        assert "wages from 2026 to 2026 (the largest year \\$168,000)" in _text(at)
        assert "**Budget**: 1 budget line (rent)." in _text(at)

    def test_a_workbook_already_in_the_folder_is_offered_and_used(self, home, monkeypatch):
        opened = _stop_at_switch(monkeypatch)
        home.mkdir(parents=True)
        book = H.write_workbook(home / "ours.xlsx", _answers())
        wb = openpyxl.load_workbook(book)
        wb["Noa"]["B2"] = 121_000
        wb.save(book)
        at = _page("Setup.py", {"setup_answers": _answers()})
        assert at.radio(key="setup_book_mode").value == "existing"
        assert at.selectbox(key="setup_book_pick").value.name == "ours.xlsx"
        at.button(key="setup_make").click().run()
        assert not at.exception, [e.value for e in at.exception]
        lib = Library.open(home / "library")
        table = lib.scenario(lib.runs()[0])["hfp"]["Noa"]
        row = next(r for r in table["rows"] if r[table["columns"].index("year")] == 2026)
        assert row[table["columns"].index("anticipated wages")] == 121_000 and opened == ["Run.py"]

    def test_an_uploaded_workbook_is_copied_once_and_its_copy_is_the_one_read(self, home, tmp_path):
        """The uploader holds its bytes for as long as the page lives. Copied at every rerun,
        a copy corrected in Excel no longer matched them: the old bytes were written again as
        "theirs (2).xlsx" and that file was read, so the correction never showed (review AQ7)."""
        elsewhere = H.write_workbook(tmp_path / "theirs.xlsx", _answers())
        at = _page("Setup.py", {"setup_answers": _answers()})
        at.radio(key="setup_book_mode").set_value("existing").run()
        at.file_uploader(key="setup_book_up").set_value(("theirs.xlsx", elsewhere.read_bytes(),
                                                         "application/vnd.ms-excel")).run()
        assert not at.exception, [e.value for e in at.exception]
        copy = home / "theirs.xlsx"
        assert copy.exists() and "Read from `theirs.xlsx`" in _text(at) and "**Ari**: no wages." in _text(at)
        wb = openpyxl.load_workbook(copy)  # corrected in Excel, in the folder
        wb["Ari"]["B2"] = 168_000
        wb.save(copy)
        at.button(key="setup_book_again").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert sorted(p.name for p in home.glob("*.xlsx")) == ["theirs.xlsx"]
        assert "the largest year \\$168,000" in _text(at)

    def test_a_workbook_that_cannot_be_read_says_why_and_is_not_used(self, home):
        home.mkdir(parents=True)
        book = H.write_workbook(home / "ours.xlsx", _answers())
        wb = openpyxl.load_workbook(book)
        wb["Ari"]["B1"] = "Anticipated  Wages"
        wb.save(book)
        at = _page("Setup.py", {"setup_answers": _answers()})
        assert not at.exception, [e.value for e in at.exception]
        assert any("`ours.xlsx` cannot be read as it is" in e.value for e in at.error)


class TestStartWithAPlan:
    @pytest.fixture
    def plan(self, home):
        lib = Library.open(home / "library")
        run = lib.save_run(name="Our plan", scenario=H.first_scenario(_answers(), name="Our plan")).run
        lib.pin(run.id)
        return lib, run

    def test_it_asks_what_to_do_and_shows_the_steps(self, plan, monkeypatch):
        opened = _stop_at_switch(monkeypatch)
        lib, run = plan
        at = _page("Start.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "What do you want to do with *Our plan*?" in text
        assert ":material/check_circle: **2.** The plan is for 2026." in text
        assert ":material/arrow_circle_right: **3.** Solve it" in text
        at.button(key="start_see_solve").click().run()
        assert sorted(j.doc["preset"] for j in JobManager(lib).jobs(run)) == ["decision", "decision_exact"]
        assert opened == ["Run.py"] and at.session_state["library_selected_run"] == run.id

    def test_a_what_if_goes_to_the_scenario_page_on_the_plan(self, plan, monkeypatch):
        opened = _stop_at_switch(monkeypatch)
        _lib, run = plan
        at = _page("Start.py")
        at.radio(key="start_wish").set_value("whatif").run()
        assert "*Save and solve*" in _text(at)
        at.button(key="start_whatif").click().run()
        assert opened == ["Scenario.py"] and at.session_state["library_selected_run"] == run.id

    def test_a_plan_of_last_year_is_sent_to_start_this_year(self, home, monkeypatch, tmp_path):
        opened = _stop_at_switch(monkeypatch)
        scenario = import_case("examples/Case_bill.toml")
        scenario["plan_year"] = 2025
        scenario["case"]["basic_info"]["start_date"] = "2025-01-01"
        lib = Library.open(home / "library")
        lib.pin(lib.save_run(name="bill 2025", scenario=scenario).run.id)
        at = _page("Start.py")
        assert at.radio(key="start_wish").value == "update"
        assert "*Start 2026 from this run*" in _text(at)
        at.button(key="start_update").click().run()
        assert opened == ["Run.py"]

    def test_the_files_answer_names_the_folder(self, plan, home):
        at = _page("Start.py")
        at.radio(key="start_wish").set_value("files").run()
        assert f"**Your files** are in `{home}`" in _text(at) and "**To back up**, copy that whole folder" in _text(at)


def test_the_run_page_of_an_empty_folder_points_to_start(home, monkeypatch):
    opened = _stop_at_switch(monkeypatch)
    at = _page("Run.py")
    assert not at.exception, [e.value for e in at.exception]
    assert any("There is no plan here yet" in i.value for i in at.info)
    at.button(key="run_page_to_start").click().run()
    assert opened == ["Start.py"]

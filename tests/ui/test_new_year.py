"""The way into a new plan year through the pages (local-use review D2), rendered by AppTest.

A run is solved only in its plan year. The Run page of a run from an earlier year says so
before any click, and *Start <year> from this run* opens the run's inputs carried over to
this year (`library.newyear.start_year`) on Account Balances; the Library page's save then
makes the run for this year, its events kept. The tests run at the suite's frozen date
(2026-01-01) on a run made for 2025.
"""

import io
from pathlib import Path

import pytest

from owlplanner.config.toml_io import load_toml, save_toml
from owlplanner.library import JobManager, Library, canonicalize, check_plan_year, import_case

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
CASE = "examples/Case_jack+jill.toml"
EVENTS = [
    {"id": "w", "kind": "work", "person": "Jack", "start": 2025, "end": 2026, "wages": 5000},
    {"id": "rent", "kind": "rent", "monthly": 2000, "start": 2025, "flat_until": 2025},
]


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    case, _, _ = load_toml(CASE)
    case["basic_info"]["start_date"] = "2025-01-01"
    case["household_financial_profile"]["HFP_file_name"] = str(Path(CASE).resolve().parent / "HFP_jack+jill.xlsx")
    buf = io.StringIO()
    save_toml(case, buf)
    case_file = tmp_path / "Case_2025.toml"
    case_file.write_text(buf.getvalue(), encoding="utf-8")
    scenario = canonicalize(dict(import_case(case_file), events=EVENTS))
    assert scenario["plan_year"] == 2025
    lib = Library.open(root)
    lib.save_run(name="our plan - 2025", scenario=scenario)
    return lib


def _page(name, state=None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / name), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    for key, value in (state or {}).items():
        at.session_state[key] = value
    return at.run()


def _started(monkeypatch):
    """The Run page after a click on *Start 2026 from this run*: (the page, where it went)."""
    opened = []
    monkeypatch.setattr("streamlit.switch_page", lambda page: opened.append(page))
    at = _page("Run.py")
    assert not at.exception, [e.value for e in at.exception]
    at.button(key="run_page_new_year").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at, opened


def _session(at):
    return {key: at.session_state[key] for key in ("cases", "currentCase")}


def _save(state):
    at = _page("Library.py", state)
    assert not at.exception, [e.value for e in at.exception]
    next(b for b in at.button if b.label == "Save as a new run").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_the_run_page_says_it_before_any_click(library):
    at = _page("Run.py")
    assert not at.exception, [e.value for e in at.exception]
    warning = next(w.value for w in at.warning if "made for 2025" in w.value)
    assert "Start 2026 from this run" in warning and "Account Balances" in warning
    assert at.button(key="run_page_new_year").label == "Start 2026 from this run"
    solve = next(b for b in at.button if b.label == "Solve")
    assert solve.disabled  # prevented at the input, not refused after the click
    assert not any("solve it below" in i.value for i in at.info)


def test_a_run_of_this_year_offers_nothing(library):
    scenario = library.scenario(library.runs()[0])
    scenario["case"]["basic_info"]["start_date"] = "2026-01-01"
    scenario["plan_year"] = 2026
    scenario["events"] = []
    library.save_run(name="this year", scenario=scenario)
    at = _page("Run.py", {"library_selected_run": library.runs()[-1].id})
    assert not at.exception, [e.value for e in at.exception]
    assert "run_page_new_year" not in [b.key for b in at.button]
    assert not next(b for b in at.button if b.label == "Solve").disabled


def test_start_opens_the_carried_over_inputs_on_account_balances(library, monkeypatch):
    at, opened = _started(monkeypatch)
    assert opened == ["Account_Balances.py"]
    case = at.session_state["cases"][at.session_state["currentCase"]]
    assert at.session_state["currentCase"] == "our plan - 2026"  # the year in the name replaced
    assert case["library_base_run_id"] == library.runs()[0].id
    assert case["library_new_year"] == 2026
    assert case["plan"].year_n[0] == 2026
    text = case["library_new_year_steps"]  # kept with the case, drawn by the Case Setup pages
    assert "**2026, started from *our plan - 2025*.**" in text
    assert "this year's account balances" in text and "now read in 2026's dollars" in text
    assert "The rent started in 2025 and goes on" in text  # the roll's own notes
    assert len(library.runs()) == 1  # nothing is stored yet


def test_account_balances_draws_the_steps(library, monkeypatch):
    import streamlit as st

    at, _ = _started(monkeypatch)
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    page = _page("Account_Balances.py", _session(at))
    assert not page.exception, [e.value for e in page.exception]
    assert any("started from *our plan - 2025*" in i.value and "Financial Profile" in i.value for i in page.info)
    for box in page.selectbox:  # keep the decorated case option (as test_library_pages does)
        if box.label == "Case selector":
            box.set_value(box.options[0])
    page.run()  # still there after an edit's rerun: a one-time message was gone at the first one
    assert any("started from *our plan - 2025*" in i.value for i in page.info)


def test_the_save_is_a_run_for_this_year_with_its_events(library, monkeypatch):
    at, _ = _started(monkeypatch)
    state = _session(at)
    case = state["cases"][state["currentCase"]]
    case["txbl0"] = float(case["txbl0"]) + 25.0  # this year's balance, as Account Balances stores it
    page = _save(state)
    base, new = library.runs()
    assert (new.name, new.plan_year, new.parent) == ("our plan - 2026", 2026, base.id)
    scenario = library.scenario(new)
    assert check_plan_year(scenario) == 2026  # the library solves it this year
    events = {e["id"]: e for e in scenario["events"]}
    assert events["w"]["start"] == 2026 and events["rent"]["start"] == {"year": 2026}
    assert scenario["case"]["basic_info"]["start_date"].startswith("2026-")
    monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # no real worker
    assert JobManager(library).enqueue(new, preset="quick").state == "waiting"
    assert not any("account balances of 2025" in w.value for w in page.warning)
    assert any("2025 -> 2026" in line or "2025 → 2026" in line for line in new.change_summary), new.change_summary


def test_a_save_with_last_years_balances_says_so(library, monkeypatch):
    at, _ = _started(monkeypatch)
    page = _save(_session(at))
    assert library.runs()[-1].plan_year == 2026
    assert any("with the account balances of 2025" in w.value for w in page.warning)


def test_once_saved_the_case_is_the_new_runs(library, monkeypatch):
    """After the save with this year's balances the pages stop saying "Nothing is saved yet",
    and a later save is a child of the run for the new year, not another one beside it from
    last year's run (review AQ5)."""
    import streamlit as st

    at, _ = _started(monkeypatch)
    state = _session(at)
    case = state["cases"][state["currentCase"]]
    case["txbl0"] = float(case["txbl0"]) + 25.0
    state = _session(_save(state))
    base, new = library.runs()
    case = state["cases"][state["currentCase"]]
    assert case["library_base_run_id"] == new.id and case["library_base_run_name"] == "our plan - 2026"
    assert "library_new_year" not in case and "library_new_year_steps" not in case
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    assert not any("Nothing is saved yet" in i.value for i in _page("Account_Balances.py", state).info)
    case["txbl0"] = float(case["txbl0"]) + 5.0  # a correction after the save
    _save(state)
    later = library.runs()[-1]
    assert (later.name, later.plan_year, later.parent) == ("our plan - 2026 variant", 2026, new.id)


def test_saved_with_last_years_balances_the_steps_stay(library, monkeypatch):
    at, _ = _started(monkeypatch)
    state = _session(_save(_session(at)))
    case = state["cases"][state["currentCase"]]
    assert case["library_new_year"] == 2026 and "Nothing is saved yet" in case["library_new_year_steps"]
    assert case["library_base_run_id"] == library.runs()[0].id


def test_the_library_page_names_the_year(library, monkeypatch):
    at, _ = _started(monkeypatch)
    page = _page("Library.py", _session(at))
    assert any("for plan year 2026, with *our plan - 2025* as its parent" in c.value for c in page.caption)
    assert any(t.value == "our plan - 2026" for t in page.text_input if t.label == "Run name")


def test_an_ordinary_edit_of_an_old_run_is_flagged_at_the_save(library, monkeypatch):
    """*Edit as new run* keeps the parent's plan year (T3): in a later year that run cannot be
    solved, and the save says where the way on is."""
    from test_library_pages import _write_result

    _write_result(library.runs()[0], "2025-11-02T10-00-00_decision")
    monkeypatch.setattr("streamlit.switch_page", lambda page: None)
    at = _page("Run.py")
    next(b for b in at.button if b.label == "Edit as new run").click().run()
    assert not at.exception, [e.value for e in at.exception]
    state = _session(at)
    case = state["cases"][state["currentCase"]]
    assert "library_new_year" not in case
    case["txbl0"] = float(case["txbl0"]) + 25.0  # an edit, or the save is the base itself
    page = _save(state)
    assert library.runs()[-1].plan_year == 2025
    assert any("is for plan year 2025" in w.value and "*Start 2026 from this run*" in w.value
               for w in page.warning)


def test_the_new_runs_name_keeps_its_stem_from_year_to_year(library):
    import library_save

    assert library_save.new_year_name("our plan", 2027) == "our plan - 2027"
    assert library_save.new_year_name("our plan - 2026", 2027) == "our plan - 2027"
    assert library_save.new_year_name("Yonkers condo 2029", 2027) == "Yonkers condo 2029 - 2027"


def test_the_scenario_page_warns_before_a_what_if(library, monkeypatch):
    opened = []
    monkeypatch.setattr("streamlit.switch_page", lambda page: opened.append(page))
    at = _page("Scenario.py")
    assert not at.exception, [e.value for e in at.exception]
    assert any("This run is for 2025" in w.value and "start 2026 from it" in w.value for w in at.warning)
    at.button(key="scenario_to_run_page").click().run()
    assert opened == ["Run.py"]


def test_the_refusal_names_the_route(library):
    from owlplanner.library import ScenarioError

    with pytest.raises(ScenarioError, match=r"use \*Start 2026 from this run\*"):
        JobManager(library).enqueue(library.runs()[0], preset="quick")

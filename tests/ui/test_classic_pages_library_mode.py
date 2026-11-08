"""The classic results pages in library mode (ergonomics review S-6, decision 9).

In library mode Graphs, Worksheets and Reports do not solve a modified case on open: they
offer *Save as a new run and solve it in the background* (the Library page's save, then a
Careful enqueue). Outside library mode they solve as upstream does.
"""

import io
from pathlib import Path

import pytest

from owlplanner import readConfig
from owlplanner.config import config_to_ui, load_toml
from owlplanner.library import Library

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
CASE = Path(__file__).resolve().parents[2] / "examples" / "Case_bill.toml"


def _modified_case():
    plan = readConfig(str(CASE), verbose=False, logstreams=[io.StringIO()])
    diconf, _, _ = load_toml(str(CASE))
    case = config_to_ui(diconf)
    case.update({"plan": plan, "id": "t1", "name": "t", "caseStatus": "modified", "summaryDf": None,
                 "timeList0": plan.timeLists.get("Bill"), "houseListDebts": plan.houseLists.get("Debts"),
                 "houseListFixedAssets": plan.houseLists.get("Fixed Assets"), "logs": io.StringIO()})
    return case


def _render(page, monkeypatch, calls):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    import owlbridge

    monkeypatch.setattr(owlbridge, "runPlan", lambda *a, **k: calls.append(page))
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    at = AppTest.from_file(str(UI_DIR / page), default_timeout=120)
    at.session_state["cases"] = {"t": _modified_case()}
    at.session_state["currentCase"] = "t"
    return at.run()


@pytest.fixture
def library_mode(tmp_path, monkeypatch):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    return Library.open(root)


@pytest.mark.parametrize("page", ["Graphs.py", "Worksheets.py", "Reports.py"])
def test_library_mode_does_not_solve_and_offers_the_background_solve(library_mode, monkeypatch, page):
    calls = []
    at = _render(page, monkeypatch, calls)
    assert not at.exception, [e.value for e in at.exception]
    assert calls == []  # no foreground solve
    assert any(b.label == "Save as a new run and solve it in the background" for b in at.button)
    assert any("solved in the background" in i.value for i in at.info)


def test_the_button_saves_the_case_and_queues_a_careful_solve(library_mode, monkeypatch):
    """The button's action (`background_solve._save_and_queue`), run as a script with the
    modified case in the session (AppTest cannot rerun a page whose title bar formats the case
    selector's options: it looks the raw value up among the formatted labels)."""
    from streamlit.testing.v1 import AppTest

    def script():
        import libraryjobs

        import background_solve

        queued = []

        class _Job:
            def __init__(self, preset):
                self.id = f"job-{preset}"

        class _Manager:
            library = libraryjobs.get_manager().library

            def enqueue(self, run, preset):
                queued.append(f"{run.name}:{preset}")
                return _Job(preset)

        real = libraryjobs.get_manager
        libraryjobs.get_manager = lambda: _Manager()
        try:
            background_solve._save_and_queue()
        finally:
            libraryjobs.get_manager = real  # a module attribute: never leak it to later tests
        import streamlit as st

        st.session_state["queued"] = queued

    at = AppTest.from_function(script, default_timeout=120)
    at.session_state["cases"] = {"t": _modified_case()}
    at.session_state["currentCase"] = "t"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert [r.name for r in library_mode.runs()] == ["t"]
    assert at.session_state["queued"] == ["t:decision", "t:decision_exact"]
    assert at.session_state["library_selected_run"] == library_mode.runs()[0].id


def test_outside_library_mode_the_pages_still_solve(monkeypatch):
    monkeypatch.delenv("OWL_LIBRARY_DIR", raising=False)
    monkeypatch.syspath_prepend(str(UI_DIR))
    calls = []
    at = _render("Graphs.py", monkeypatch, calls)
    assert calls == ["Graphs.py"]
    assert not any(b.label == "Save as a new run and solve it in the background" for b in at.button)
    assert any(b.label == "Re-run" for b in at.button)

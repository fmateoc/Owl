"""
The withItemized and withSTAR widgets on the Run Options page (run-library step 5).

Both are fork-only solver inputs (config.ui_bridge.SOLVER_UI_PASSTHROUGH_KEYS): carried
between the case file and the pages verbatim, with no widget until here. They bind to the
passthrough names, so the solve path (`sskeys.getSolveParameters`) and the save path
(`ui_bridge.ui_to_config`) read the same case key and cannot drift (#156's lesson).

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from pathlib import Path

import pytest

import sskeys as kz
from owlplanner import readConfig
from owlplanner.config import config_to_ui, load_toml, ui_to_config

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
CASE = Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml"


def _render(monkeypatch, solver_options=None):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    diconf, _, _ = load_toml(str(CASE))
    diconf["solver_options"].update(solver_options or {})
    case = config_to_ui(diconf)
    case.update({"plan": readConfig(str(CASE), verbose=False), "id": "t1", "caseStatus": "new", "summaryDf": None})
    at = AppTest.from_file(str(UI_DIR / "Run_Options.py"), default_timeout=120)
    at.session_state["cases"] = {"t": case}
    at.session_state["currentCase"] = "t"
    at.run()
    assert not at.exception, [str(e.message) for e in at.exception]
    return at


def _radio(at, label):
    found = [r for r in at.radio if r.label == label]
    assert len(found) == 1, [r.label for r in at.radio]
    return found[0]


def _rerun(at):
    # The sidebar's case selector decorates the case name in its options; keep it on that
    # option (as test_ui_disabled_options does), or the rerun cannot re-serialize it.
    for box in at.selectbox:
        if box.label == "Case selector":
            box.set_value(box.options[0])
    at.run()
    assert not at.exception, [str(e.message) for e in at.exception]
    return at


@pytest.mark.toml
def test_the_radios_show_the_case_file_values(monkeypatch):
    at = _render(monkeypatch, {"withItemized": "none", "withSTAR": "optimize"})
    assert _radio(at, "Itemized deductions").value == "none"
    assert _radio(at, "NY STAR credit").value == "optimize"


@pytest.mark.toml
def test_the_default_is_the_loop(monkeypatch):
    at = _render(monkeypatch)
    assert _radio(at, "Itemized deductions").value == "loop"
    assert _radio(at, "NY STAR credit").value == "loop"


@pytest.mark.toml
def test_a_visit_writes_nothing_to_the_case(monkeypatch):
    """Review Y3: showing the radios must not store their default. ui_to_config writes every
    passthrough key the case holds, so a stored "loop" made an unchanged case save as a changed
    run (two "added" options and another scenario hash)."""
    at = _render(monkeypatch)
    _rerun(at)
    case = at.session_state["cases"]["t"]
    assert "withItemized" not in case and "withSTAR" not in case
    saved = ui_to_config(case)["solver_options"]
    assert "withItemized" not in saved and "withSTAR" not in saved


@pytest.mark.toml
def test_neither_radio_is_disabled_by_local_search(monkeypatch):
    """Local search forces the breakpoint families to MILP (the caption under its toggle),
    but STAR = "none" and the itemizing switch are honored there too, so both stay editable
    and the STAR help says what local search does to the other two values."""
    at = _render(monkeypatch, {"breakpointMethod": "local-search"})
    assert _radio(at, "Itemized deductions").disabled is False
    assert _radio(at, "NY STAR credit").disabled is False
    assert "local search" in _radio(at, "NY STAR credit").help.lower()


@pytest.mark.toml
def test_a_choice_reaches_the_solve_and_the_save_the_same_way(monkeypatch):
    at = _render(monkeypatch)
    _radio(at, "Itemized deductions").set_value("none")
    _rerun(at)
    _radio(at, "NY STAR credit").set_value("optimize")
    _rerun(at)
    case = at.session_state["cases"]["t"]
    assert case["withItemized"] == "none"
    assert case["withSTAR"] == "optimize"

    monkeypatch.setattr(kz, "getCaseKey", case.get)
    _, run_opts = kz.getSolveParameters()
    file_opts = ui_to_config(case)["solver_options"]
    assert run_opts["withItemized"] == "none" and run_opts["withSTAR"] == "optimize"
    assert run_opts == file_opts


@pytest.mark.toml
def test_a_choice_survives_the_case_file_round_trip(monkeypatch):
    at = _render(monkeypatch)
    _radio(at, "Itemized deductions").set_value("none")
    _rerun(at)
    case = at.session_state["cases"]["t"]
    saved = ui_to_config(case)["solver_options"]
    assert saved["withItemized"] == "none" and "withSTAR" not in saved  # untouched: not written (Y3)

    monkeypatch.setattr(kz, "getCaseKey", case.get)
    _, run_opts = kz.getSolveParameters()
    assert run_opts == saved

    back = config_to_ui({"basic_info": {"names": ["Jack", "Jill"], "status": "married"},
                         "solver_options": saved})
    assert back["withItemized"] == "none" and back.get("withSTAR") is None

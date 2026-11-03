"""
The change-of-state controls on the Create Case page (#159).

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

from owlplanner.config import config_to_ui, load_toml

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
CASE = Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml"


def _render(monkeypatch, moves):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    # AppTest has no multipage context, so st.page_link raises KeyError('url_pathname').
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)

    diconf, _, _ = load_toml(str(CASE))
    diconf["basic_info"]["state"] = "NY"
    if moves:
        diconf["basic_info"]["moves"] = moves
    case = config_to_ui(diconf)
    case.update({"plan": None, "id": "t1", "caseStatus": "new", "summaryDf": None})
    at = AppTest.from_file(str(UI_DIR / "Create_Case.py"), default_timeout=120)
    at.session_state["cases"] = {"t": case}
    at.session_state["currentCase"] = "t"
    at.run()
    assert not at.exception, [str(e.message) for e in at.exception]
    return at


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
def test_move_fields_hidden_without_a_move(monkeypatch):
    at = _render(monkeypatch, None)
    toggle = [t for t in at.toggle if t.label == "Move to another state during the plan"]
    assert len(toggle) == 1 and toggle[0].value is False
    assert not [s for s in at.selectbox if s.label == "New state"]


@pytest.mark.toml
def test_move_fields_show_the_move(monkeypatch):
    at = _render(monkeypatch, [{"year": 2031, "state": "FL"}])
    toggle = [t for t in at.toggle if t.label == "Move to another state during the plan"]
    assert toggle[0].value is True
    assert [n.value for n in at.number_input if n.label == "Year of the move"] == [2031]
    assert [s.value for s in at.selectbox if s.label == "New state"] == ["FL"]


# -- moves after the first (fork; run-library step 5) ------------------


def _add_move(at):
    next(b for b in at.button if b.label.startswith("Add a move")).click()
    return _rerun(at)


@pytest.mark.toml
def test_further_moves_show_their_values(monkeypatch):
    at = _render(monkeypatch, [{"year": 2031, "state": "FL"}, {"year": 2035, "state": "TX"}])
    assert [n.value for n in at.number_input if n.label == "Year of move 2"] == [2035]
    assert [s.value for s in at.selectbox if s.label == "State of move 2"] == ["TX"]


@pytest.mark.toml
def test_a_move_can_be_added_edited_and_removed(monkeypatch):
    at = _render(monkeypatch, [{"year": 2031, "state": "FL"}])
    assert at.session_state["cases"]["t"]["stateMovesMore"] == []

    _add_move(at)
    more = at.session_state["cases"]["t"]["stateMovesMore"]
    assert len(more) == 1 and more[0]["state"] == "FL"  # starts from the move above

    [s for s in at.selectbox if s.label == "State of move 2"][0].set_value("CA")
    _rerun(at)
    assert at.session_state["cases"]["t"]["stateMovesMore"][0]["state"] == "CA"

    removes = [b for b in at.button if b.label == ":material/delete:"]
    assert len(removes) == 1
    removes[0].click()
    _rerun(at)
    assert at.session_state["cases"]["t"]["stateMovesMore"] == []


@pytest.mark.toml
def test_the_further_moves_reach_the_case_file(monkeypatch):
    moves = [
        {"year": 2031, "state": "NY", "locality": "Yonkers", "school_district": "City of Yonkers / Yonkers"},
        {"year": 2035, "state": "FL"},
    ]
    at = _render(monkeypatch, moves)
    assert at.session_state["cases"]["t"]["stateMovesMore"] == [{"year": 2035, "state": "FL"}]
    from owlplanner.config.ui_bridge import ui_to_config

    assert ui_to_config(at.session_state["cases"]["t"])["basic_info"]["moves"] == moves


@pytest.mark.toml
def test_two_moves_in_one_year_warn(monkeypatch):
    at = _render(monkeypatch, [{"year": 2031, "state": "FL"}])
    _add_move(at)
    [n for n in at.number_input if n.label == "Year of move 2"][0].set_value(2031)
    _rerun(at)
    warns = [str(w.value) for w in at.warning]
    assert any("Two moves in 2031" in w for w in warns), warns


@pytest.mark.toml
def test_a_move_to_the_residence_it_leaves_warns(monkeypatch):
    at = _render(monkeypatch, [{"year": 2031, "state": "FL"}])
    _add_move(at)  # defaults to the destination of the move above
    warns = [str(w.value) for w in at.warning]
    assert any("goes to the move in 2031" in w for w in warns), warns


@pytest.mark.toml
def test_a_move_back_to_the_starting_state_does_not_warn(monkeypatch):
    """The rule is that a move changes the residence it leaves, not that it never returns."""
    at = _render(monkeypatch, [{"year": 2031, "state": "FL"}])
    _add_move(at)
    [s for s in at.selectbox if s.label == "State of move 2"][0].set_value("NY")
    _rerun(at)
    warns = [str(w.value) for w in at.warning]
    assert not any("goes to" in w for w in warns), warns


@pytest.mark.toml
def test_the_pages_see_every_move_of_a_plan():
    """"Open in Owl" builds the page keys from a Plan (`genDic`): the split matches
    `config_to_ui`'s, so the further moves land in the same editor."""
    import owlbridge as owb
    from owlplanner.config import config_to_plan

    diconf, dirname, _ = load_toml(str(CASE))
    diconf["basic_info"]["state"] = "NY"
    diconf["basic_info"]["moves"] = [{"year": 2031, "state": "FL"}, {"year": 2035, "state": "TX"}]
    plan = config_to_plan(diconf, dirname, verbose=False, loadHFP=True)
    _, dic = owb.genDic(plan)
    assert dic["stateMoveYear"] == 2031 and dic["stateMoveState"] == "FL"
    assert dic["stateMovesMore"] == [{"year": 2035, "state": "TX"}]

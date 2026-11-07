"""
A case whose inputs cannot be applied is not solved.

`prepareRun` used to show "Failed to apply configuration" and return, and every caller solved
anyway, on a plan that held only part of the case: a move to the starting state (which Create
Case warns about but accepts) left the plan in its previous state, and Reports showed that
plan's results as the case's.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import io
from pathlib import Path

import pytest

import owlplanner as owl
from owlplanner import readConfig
from owlplanner.config import config_to_ui, load_toml

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
CASE = Path(__file__).resolve().parents[2] / "examples" / "Case_dana.toml"


@pytest.mark.toml
def test_reports_shows_one_message_and_does_not_solve(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    solves = []
    monkeypatch.setattr(owl.Plan, "solve", lambda self, *a, **k: solves.append(1))
    plan = readConfig(str(CASE), verbose=False, logstreams=[io.StringIO()])
    diconf, _, _ = load_toml(str(CASE))
    case = config_to_ui(diconf)
    case.update({
        "plan": plan, "id": "t1", "name": "t", "caseStatus": "modified", "summaryDf": None,
        "timeList0": plan.timeLists[plan.inames[0]],
        "houseListDebts": plan.houseLists["Debts"], "houseListFixedAssets": plan.houseLists["Fixed Assets"],
        "hfpAbsentCols": dict(getattr(plan, "hfpAbsentCols", {})), "logs": io.StringIO(),
        # The case is in CA; a move to FL, then the starting state set to FL as well.
        "state": "FL", "stateMoveEnabled": True, "stateMoveYear": 2031, "stateMoveState": "FL",
    })
    at = AppTest.from_file(str(UI_DIR / "Reports.py"), default_timeout=120)
    at.session_state["cases"] = {"t": case}
    at.session_state["currentCase"] = "t"
    at.run()
    assert not at.exception, [str(e.message) for e in at.exception]
    assert solves == []
    errors = [e.value for e in at.error]
    assert len(errors) == 1, errors
    assert "goes to the starting state" in errors[0]
    assert not at.warning, [w.value for w in at.warning]
    assert at.session_state["cases"]["t"]["caseStatus"] == "invalid input"

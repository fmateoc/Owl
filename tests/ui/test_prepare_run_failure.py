"""
A case whose inputs cannot be applied is not solved.

`prepareRun` used to show "Failed to apply configuration" and return, and every caller solved
anyway, on a plan that held only part of the case: Reports then showed the solve's verdict too
(an ACA start year of 1999 gave "No plan satisfies all the constraints"). And setACA's hint
added the year to today's ("e.g. 4025") whatever the number.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import io
from datetime import date
from pathlib import Path

import pytest

import owlplanner as owl
from owlplanner import readConfig
from owlplanner.config import config_to_ui, load_toml

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
CASE = Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml"


def _plan():
    return owl.Plan(["Joe"], ["1961-01-15"], [80], "test", verbose=False)


def test_set_aca_hint_for_an_offset():
    with pytest.raises(ValueError, match=rf"offset.*e\.g\. {date.today().year + 2}"):
        _plan().setACA(slcsp=10, start_year=2)


def test_set_aca_hint_for_an_old_year():
    with pytest.raises(ValueError) as info:
        _plan().setACA(slcsp=10, start_year=1999)
    assert "offset" not in str(info.value)
    assert f"such as {date.today().year + 1}" in str(info.value)
    assert str(date.today().year + 1999) not in str(info.value)


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
        "timeList0": plan.timeLists["Jack"], "timeList1": plan.timeLists["Jill"],
        "houseListDebts": plan.houseLists["Debts"], "houseListFixedAssets": plan.houseLists["Fixed Assets"],
        "hfpAbsentCols": dict(getattr(plan, "hfpAbsentCols", {})), "logs": io.StringIO(),
        "slcspAnnual": 20.0, "acaStartYear": 1999,
    })
    at = AppTest.from_file(str(UI_DIR / "Reports.py"), default_timeout=120)
    at.session_state["cases"] = {"t": case}
    at.session_state["currentCase"] = "t"
    at.run()
    assert not at.exception, [str(e.message) for e in at.exception]
    assert solves == []
    errors = [e.value for e in at.error]
    assert len(errors) == 1, errors
    assert "start_year=1999" in errors[0] and "setACA:" not in errors[0]
    assert not at.warning, [w.value for w in at.warning]
    assert at.session_state["cases"]["t"]["caseStatus"] == "invalid input"

"""
Create Case: the first click on *Create case* is not lost, and a workbook read is confirmed.

*Create case* was disabled until the names were in, so it was still disabled when the click
that leaves the last name field (the field commits on blur) landed: that click did nothing.
It is enabled now and says what is missing. After a workbook upload the uploader disappears;
a line now says what was read.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "ui"
JACK_JILL = ROOT / "examples" / "Case_jack+jill.toml"


def _page(monkeypatch, dic, name):
    import datetime

    import streamlit as st
    import streamlit.elements.widgets.time_widgets as time_widgets
    from streamlit.testing.v1 import AppTest

    # AppTest has no multipage context: st.page_link cannot resolve the pages.
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    # The session's date freeze (conftest.freeze_year) rebinds `date` in streamlit's date
    # widget too, which then refuses the plain dates AppTest hands back on a rerun.
    real_date = next(c for c in datetime.date.__mro__ if c.__module__ == "datetime" and c.__name__ == "date")
    monkeypatch.setattr(time_widgets, "date", real_date)
    at = AppTest.from_file(str(UI_DIR / "Create_Case.py"), default_timeout=60)
    at.session_state["cases"] = {name: dic}
    at.session_state["currentCase"] = name
    at.run()
    assert not at.exception, [str(e.message) for e in at.exception]
    return at


def _new_case(monkeypatch, **case):
    from owlplanner.config import config_to_ui, default_config

    dic = config_to_ui(default_config(ni=1))
    dic.update({"name": "probe", "id": None, "plan": None, "caseStatus": "unknown",
                "summaryDf": None, **case})
    return _page(monkeypatch, dic, "probe")


def _click_create(at):
    # The case selector decorates the case name in its options; keep it on that option, or
    # the rerun cannot re-serialize it.
    for box in at.selectbox:
        if box.label == "Case selector":
            box.set_value(box.options[0])
    next(b for b in at.button if b.label.startswith("Create case")).click().run()
    assert not at.exception, [str(e.message) for e in at.exception]


def test_create_case_is_enabled_before_the_names_and_asks_for_them(monkeypatch):
    import owlbridge

    created = []
    monkeypatch.setattr(owlbridge, "createPlan", lambda: created.append(1))
    at = _new_case(monkeypatch, iname0="")
    assert not next(b for b in at.button if b.label.startswith("Create case")).disabled
    _click_create(at)
    assert created == []
    assert any(w.value == "Enter your first name first." for w in at.warning)


def test_create_case_creates_once_the_names_are_in(monkeypatch):
    import owlbridge

    created = []
    monkeypatch.setattr(owlbridge, "createPlan", lambda: created.append(1))
    at = _new_case(monkeypatch, iname0="Jack")
    _click_create(at)
    assert created == [1]
    assert not any("first." in w.value for w in at.warning)


@pytest.mark.toml
def test_create_case_confirms_the_workbook_it_read(monkeypatch):
    from owlplanner import readConfig
    from owlplanner.config import config_to_ui, load_toml

    plan = readConfig(str(JACK_JILL), verbose=False, logstreams=[io.StringIO()])
    diconf, _, _ = load_toml(str(JACK_JILL))
    dic = config_to_ui(diconf)
    # What owlbridge.readHFP leaves after an upload (AppTest cannot upload a file).
    dic.update({"plan": plan, "id": "t1", "name": "jj", "caseStatus": "modified",
                "summaryDf": None, "stHFP": "HFP_jack+jill.xlsx", "hfpFileName": "HFP_jack+jill.xlsx",
                "timeList0": plan.timeLists["Jack"], "timeList1": plan.timeLists["Jill"],
                "houseListDebts": plan.houseLists["Debts"],
                "houseListFixedAssets": plan.houseLists["Fixed Assets"]})
    at = _page(monkeypatch, dic, "jj")
    shown = [c.value for c in at.caption if "loaded" in c.value]
    assert shown == [":white_check_mark: *HFP_jack+jill.xlsx* loaded: wages and contributions for "
                     "Jack and Jill; 1 debt, 1 fixed asset."], [c.value for c in at.caption]

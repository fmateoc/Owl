"""
Run Options: the year fields are bounded by the plan horizon, and the ACA start year is a
plain calendar year defaulting to this one (UX remediation QW-8).

The Roth conversion window and the converter switch used to take any year (2500 included);
the marketplace start year asked for "0 = plan start", an input nobody enters meaningfully.
A stored year outside the field's bounds is clamped to them: the case keeps what the field
shows (Streamlit silently shows the bound instead).

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import io
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "examples" / "Case_riley+casey.toml"


def _render(monkeypatch, **updates):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    from owlplanner import readConfig
    from owlplanner.config import config_to_ui, load_toml

    # AppTest has no multipage context: st.page_link cannot resolve the pages.
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    plan = readConfig(str(CASE), verbose=False, logstreams=[io.StringIO()])
    diconf, _, _ = load_toml(str(CASE))
    dic = config_to_ui(diconf)
    dic.update({"plan": plan, "id": "t1", "name": "rc", "caseStatus": "modified", "summaryDf": None})
    dic.update(updates)
    at = AppTest.from_file(str(ROOT / "ui" / "Run_Options.py"), default_timeout=60)
    at.session_state["cases"] = {"rc": dic}
    at.session_state["currentCase"] = "rc"
    return at.run(), dic, plan


def test_the_roth_conversion_years_are_bounded_by_the_plan(monkeypatch):
    at, dic, plan = _render(monkeypatch, startRothConversions=2500,
                            stopRothConversionsEnabled=True, stopRothConversions=2500)
    assert not at.exception, [str(e.value) for e in at.exception]
    end = int(plan.year_n[-1])
    start = next(w for w in at.number_input if w.label.startswith("Year to start"))
    stop = next(w for w in at.number_input if w.label.startswith("Year to stop"))
    assert start.max == end and stop.max == end
    # A stored year past the horizon is clamped to it: the field shows what the case holds.
    assert dic["startRothConversions"] == end == start.value
    assert dic["stopRothConversions"] == end == stop.value


def test_the_roth_window_defaults_stay_inside_the_plan(monkeypatch):
    at, dic, plan = _render(monkeypatch, stopRothConversionsEnabled=True)
    assert not at.exception, [str(e.value) for e in at.exception]
    end = int(plan.year_n[-1])
    assert dic["startRothConversions"] == date.today().year
    assert dic["stopRothConversions"] == min(date.today().year + 10, end)


def test_the_aca_start_year_defaults_to_this_year_not_zero(monkeypatch):
    at, dic, _ = _render(monkeypatch, acaStartYear=0)
    assert not at.exception, [str(e.value) for e in at.exception]
    field = next(w for w in at.number_input if w.label.startswith("ACA start year"))
    thisyear = date.today().year
    # The plan starts in the solve year, so the old "0 = plan start" reads as this year.
    assert dic["acaStartYear"] == thisyear == field.value
    assert field.min == thisyear
    assert "0 = plan start" not in field.label  # no more code words in the label


def test_a_real_aca_start_year_is_kept(monkeypatch):
    year = date.today().year + 3
    at, dic, _ = _render(monkeypatch, acaStartYear=year)
    assert not at.exception, [str(e.value) for e in at.exception]
    assert dic["acaStartYear"] == year
    assert next(w for w in at.number_input if w.label.startswith("ACA start year")).value == year

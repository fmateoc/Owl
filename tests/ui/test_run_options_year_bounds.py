"""
Run Options: the year fields take any year up to `last_year_entered` (upstream #250: a year
past the plan is a legitimate "never"), the stop year cannot precede the start year (fork),
and the ACA start year is a toggle, "Marketplace coverage from the plan start" (storing 0, the
code's own sentinel), with a year box when it is off (UX remediation QW-8; decision 5).

A stored year outside the field's bounds is clamped to them: the case keeps what the field
shows (Streamlit silently shows the bound instead), and the page says so in the field's words.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import io
from datetime import date
from pathlib import Path

from owlplanner.utils import last_year_entered

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "examples" / "Case_riley+casey.toml"
JACK_JILL = ROOT / "examples" / "Case_jack+jill.toml"


def _render(monkeypatch, case=CASE, **updates):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    from owlplanner import readConfig
    from owlplanner.config import config_to_ui, load_toml

    # AppTest has no multipage context: st.page_link cannot resolve the pages.
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    plan = readConfig(str(case), verbose=False, logstreams=[io.StringIO()])
    diconf, _, _ = load_toml(str(case))
    dic = config_to_ui(diconf)
    dic.update({"plan": plan, "id": "t1", "name": "rc", "caseStatus": "modified", "summaryDf": None})
    dic.update(updates)
    at = AppTest.from_file(str(ROOT / "ui" / "Run_Options.py"), default_timeout=60)
    at.session_state["cases"] = {"rc": dic}
    at.session_state["currentCase"] = "rc"
    return at.run(), dic, plan


def test_a_roth_year_past_the_plan_is_kept(monkeypatch):
    """Upstream #250: a year beyond the plan says "never" and survives a change of longevity;
    the fork's first build clamped it to the plan's last year, which changed its meaning."""
    at, dic, plan = _render(monkeypatch, caseStatus="solved", startRothConversions=2100,
                            stopRothConversionsEnabled=True, stopRothConversions=2120)
    assert not at.exception, [str(e.value) for e in at.exception]
    assert int(plan.year_n[-1]) < 2100
    last = last_year_entered(date.today().year)
    start = next(w for w in at.number_input if w.label.startswith("Year to start"))
    stop = next(w for w in at.number_input if w.label.startswith("Year to stop"))
    assert start.max == last and stop.max == last
    assert (dic["startRothConversions"], dic["stopRothConversions"]) == (2100, 2120) == (start.value, stop.value)
    assert not any("shown as" in c.value for c in at.caption)
    assert dic["caseStatus"] == "solved"


def test_a_roth_year_past_the_last_accepted_year_is_clamped_and_said(monkeypatch):
    at, dic, _ = _render(monkeypatch, caseStatus="solved", startRothConversions=2500,
                         stopRothConversionsEnabled=True, stopRothConversions=2500)
    assert not at.exception, [str(e.value) for e in at.exception]
    last = last_year_entered(date.today().year)
    assert dic["startRothConversions"] == last == dic["stopRothConversions"]
    # Review AM3: a move is never silent, in the field's words (review AN2), never its key.
    said = "\n".join(c.value for c in at.caption)
    assert (f"Year to start considering Roth conversions: 2500 is past the last year accepted, "
            f"{last}; shown as {last}") in said
    assert "RothConversions" not in said
    assert dic["caseStatus"] == "modified"


def test_the_roth_window_defaults(monkeypatch):
    at, dic, _ = _render(monkeypatch, stopRothConversionsEnabled=True)
    assert not at.exception, [str(e.value) for e in at.exception]
    assert dic["startRothConversions"] == date.today().year
    assert dic["stopRothConversions"] == date.today().year + 10


def test_the_stop_year_cannot_precede_the_start_year(monkeypatch):
    thisyear = date.today().year
    at, dic, _ = _render(monkeypatch, caseStatus="solved", startRothConversions=thisyear + 6,
                         stopRothConversionsEnabled=True, stopRothConversions=thisyear + 2)
    assert not at.exception, [str(e.value) for e in at.exception]
    stop = next(w for w in at.number_input if w.label.startswith("Year to stop"))
    assert stop.min == thisyear + 6
    assert dic["stopRothConversions"] == thisyear + 6 == stop.value
    said = "\n".join(c.value for c in at.caption)
    assert (f"Year to stop considering Roth conversions: {thisyear + 2} is before the start year, "
            f"{thisyear + 6}; shown as {thisyear + 6}") in said
    assert dic["caseStatus"] == "modified"


def _toggle(at):
    return next(t for t in at.toggle if t.label == "Marketplace coverage from the plan start")


def _rerun(at):
    """Rerun keeping the decorated case option ("rc ✓"), as test_create_case_move does."""
    for box in at.selectbox:
        if box.label == "Case selector":
            box.set_value(box.options[0])
    return at.run()


def test_an_unmodified_upstream_example_shows_no_message_and_keeps_zero(monkeypatch):
    """Review AN2: on upstream's Case_jack+jill.toml and Case_riley+casey.toml, unmodified,
    the build said "A stored year outside its field's range was set to the nearest allowed
    year: acaStartYear 0 → 2026", and the next save wrote aca_start_year = 2026."""
    for case in (JACK_JILL, CASE):
        at, dic, _ = _render(monkeypatch, case=case, caseStatus="solved")
        assert not at.exception, [str(e.value) for e in at.exception]
        assert dic.get("acaStartYear", 0) == 0
        assert not any("outside" in c.value or "shown as" in c.value for c in at.caption)
        assert _toggle(at).value is True
        assert not any(w.label.startswith("ACA start year") for w in at.number_input)
        assert dic["caseStatus"] == "solved"


def test_turning_the_toggle_off_shows_a_bounded_year_box(monkeypatch):
    at, dic, _ = _render(monkeypatch, slcspAnnual=20.84)
    _toggle(at).set_value(False)
    _rerun(at)
    assert not at.exception, [str(e.value) for e in at.exception]
    thisyear = date.today().year
    assert dic["acaStartYear"] == thisyear + 1
    field = next(w for w in at.number_input if w.label == "ACA start year")
    assert (field.min, field.max) == (thisyear, last_year_entered(thisyear))
    assert field.value == thisyear + 1
    _toggle(at).set_value(True)
    _rerun(at)
    assert dic["acaStartYear"] == 0  # back to the sentinel


def test_a_real_aca_start_year_is_kept(monkeypatch):
    year = date.today().year + 3
    at, dic, _ = _render(monkeypatch, acaStartYear=year)
    assert not at.exception, [str(e.value) for e in at.exception]
    assert dic["acaStartYear"] == year
    assert next(w for w in at.number_input if w.label.startswith("ACA start year")).value == year
    assert _toggle(at).value is False
    assert not any("shown as" in c.value for c in at.caption)

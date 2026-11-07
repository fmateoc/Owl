"""UX review Q14 and Q18 (2026-11-07): the library-mode chrome, and Create case's first click.

Q14: library mode runs offline on household data, so the launchers hide Streamlit's developer
menu items (Deploy) and Welcome leaves out its pitch for connecting an AI assistant. Q18:
*Create case* was disabled until the names were in, and so still disabled when the click that
leaves the last name field (it commits on blur) landed: that click did nothing (reproduced
with Playwright; AppTest cannot drive a blur). It is enabled now and says what is missing.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "ui"
AI_HEADLINE = "Powered by Actual Intelligence"


def _welcome(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    # AppTest has no multipage context: st.page_link cannot resolve the pages.
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    monkeypatch.setenv("OWL_SKIP_DISCLAIMER", "1")
    at = AppTest.from_file(str(UI_DIR / "Welcome.py"), default_timeout=60)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    return at.run()


def test_welcome_leaves_out_the_ai_pitch_in_library_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(tmp_path / "library"))
    at = _welcome(monkeypatch)
    assert not at.exception, [e.value for e in at.exception]
    text = "\n".join(m.value for m in at.markdown)
    assert "Built for US Retirees" in text
    assert AI_HEADLINE not in text


def test_welcome_keeps_the_ai_pitch_outside_library_mode(monkeypatch):
    monkeypatch.delenv("OWL_LIBRARY_DIR", raising=False)
    at = _welcome(monkeypatch)
    assert not at.exception, [e.value for e in at.exception]
    assert AI_HEADLINE in "\n".join(m.value for m in at.markdown)


@pytest.mark.parametrize("launcher", ["owlplanner-library.sh", "owlplanner-library.cmd"])
def test_the_library_launchers_hide_the_developer_menu(launcher):
    from streamlit import config

    assert config.get_option("client.toolbarMode") is not None  # the option exists here
    assert "--client.toolbarMode=viewer" in (ROOT / launcher).read_text(encoding="utf-8")


def _create_case_page(monkeypatch, **case):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    from owlplanner.config import config_to_ui, default_config

    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    dic = config_to_ui(default_config(ni=1))
    dic.update({"name": "probe", "id": None, "plan": None, "caseStatus": "unknown",
                "summaryDf": None, **case})
    at = AppTest.from_file(str(UI_DIR / "Create_Case.py"), default_timeout=60)
    at.session_state["cases"] = {"probe": dic}
    at.session_state["currentCase"] = "probe"
    at.run()
    assert not at.exception, [str(e.message) for e in at.exception]
    return at


def _click_create(at):
    # The case selector decorates the case name in its options; keep it on that option (as
    # test_create_case_move does), or the rerun cannot re-serialize it.
    for box in at.selectbox:
        if box.label == "Case selector":
            box.set_value(box.options[0])
    next(b for b in at.button if b.label.startswith("Create case")).click().run()
    assert not at.exception, [str(e.message) for e in at.exception]


def test_create_case_is_enabled_before_the_names_and_asks_for_them(monkeypatch):
    import owlbridge

    created = []
    monkeypatch.setattr(owlbridge, "createPlan", lambda: created.append(1))
    at = _create_case_page(monkeypatch, iname0="")
    assert not next(b for b in at.button if b.label.startswith("Create case")).disabled
    _click_create(at)
    assert created == []
    assert any(w.value == "Enter your first name first." for w in at.warning)


def test_create_case_creates_once_the_names_are_in(monkeypatch):
    import owlbridge

    created = []
    monkeypatch.setattr(owlbridge, "createPlan", lambda: created.append(1))
    at = _create_case_page(monkeypatch, iname0="Ari")
    _click_create(at)
    assert created == [1]
    assert not any("first." in w.value for w in at.warning)

"""UX review Q14 and Q11 (2026-11-07): the library-mode chrome, and the workbook heading.

Q14: library mode runs offline on household data, so the launchers hide Streamlit's developer
menu items (Deploy) and Welcome leaves out its pitch for connecting an AI assistant. Q11 (fork
part): a case with the budget spending profile needs its workbook, so the upload heading drops
"(Optional)" there. Create case's first click and the upload confirmation (Q18, Q11) are tested
in `test_create_case_button.py`, the upstream issue's own test file
(`fork-notes/issue-create-case.md`).

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


# -- Q11: the workbook heading (fork) ---------------------------------------------------

JACK_JILL = ROOT / "examples" / "Case_jack+jill.toml"


def _create_case_with_plan(monkeypatch, profile):
    """jack+jill with its plan and no workbook read yet (the upload block shows)."""
    import io

    import streamlit as st
    from streamlit.testing.v1 import AppTest

    from owlplanner import readConfig
    from owlplanner.config import config_to_ui, load_toml

    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    plan = readConfig(str(JACK_JILL), verbose=False, logstreams=[io.StringIO()])
    diconf, _, _ = load_toml(str(JACK_JILL))
    dic = config_to_ui(diconf)
    dic.update({"plan": plan, "id": "t1", "name": "jj", "caseStatus": "modified", "summaryDf": None,
                "stHFP": None})
    dic["spendingProfile"] = profile
    at = AppTest.from_file(str(UI_DIR / "Create_Case.py"), default_timeout=60)
    at.session_state["cases"] = {"jj": dic}
    at.session_state["currentCase"] = "jj"
    at.run()
    assert not at.exception, [str(e.message) for e in at.exception]
    return at


@pytest.mark.toml
def test_the_workbook_heading_drops_optional_for_a_budget_profile(monkeypatch):
    at = _create_case_with_plan(monkeypatch, "budget")
    heads = [m.value for m in at.markdown if "Upload Financial Profile" in m.value]
    assert heads == ["#### :orange[Upload Financial Profile]"]
    at = _create_case_with_plan(monkeypatch, "flat")
    heads = [m.value for m in at.markdown if "Upload Financial Profile" in m.value]
    assert heads == ["#### :orange[Upload Financial Profile (Optional)]"]

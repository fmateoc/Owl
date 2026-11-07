"""
Account Balances: a \\$k balance that reads as \\$50M or more is flagged (UX remediation QW-8).

The fields are thousands of dollars. A balance over 50,000 in them is almost certainly
dollars typed into a \\$k field; the page says so instead of solving it silently.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "examples" / "Case_riley+casey.toml"


def _render(monkeypatch, **updates):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    from owlplanner import readConfig
    from owlplanner.config import config_to_ui, load_toml

    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    plan = readConfig(str(CASE), verbose=False, logstreams=[io.StringIO()])
    diconf, _, _ = load_toml(str(CASE))
    dic = config_to_ui(diconf)
    dic.update({"plan": plan, "id": "t1", "name": "rc", "caseStatus": "modified", "summaryDf": None})
    dic.update(updates)
    at = AppTest.from_file(str(ROOT / "ui" / "Account_Balances.py"), default_timeout=60)
    at.session_state["cases"] = {"rc": dic}
    at.session_state["currentCase"] = "rc"
    return at.run()


def test_a_balance_reading_as_fifty_million_warns(monkeypatch):
    at = _render(monkeypatch, txbl0=60_000)
    assert not at.exception, [str(e.value) for e in at.exception]
    warns = [w.value for w in at.warning if "50M" in w.value]
    assert warns and "60,000k" in warns[0], warns


def test_ordinary_balances_do_not_warn(monkeypatch):
    at = _render(monkeypatch, txbl0=5_000, txDef0=2_500)
    assert not at.exception, [str(e.value) for e in at.exception]
    assert not [w.value for w in at.warning if "50M" in w.value]

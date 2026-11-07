"""
Account Balances: a \\$k balance that reads as \\$20M or more is flagged (UX remediation QW-8;
second pass, decision 4: \\$20M, not \\$50M, and the amount named in dollars, review AN11).

The fields are thousands of dollars. A balance of 20,000 or more in them is most likely
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


def test_a_balance_reading_as_sixty_million_warns_in_dollars(monkeypatch):
    at = _render(monkeypatch, txbl0=60_000)
    assert not at.exception, [str(e.value) for e in at.exception]
    warns = [w.value for w in at.warning if "million" in w.value]
    assert warns == ["Riley's taxable accounts: 60,000 here means \\$60 million (amounts are in "
                     "thousands). If you typed dollars, divide by 1,000."], warns


def test_a_balance_between_twenty_and_fifty_million_warns_too(monkeypatch):
    """Dollars typed for a \\$25,000 balance: the build's \\$50M threshold missed it."""
    at = _render(monkeypatch, txDef0=25_000)
    warns = [w.value for w in at.warning if "million" in w.value]
    assert warns and "25,000 here means \\$25 million" in warns[0], warns


def test_ordinary_balances_do_not_warn(monkeypatch):
    at = _render(monkeypatch, txbl0=5_000, txDef0=19_999)
    assert not at.exception, [str(e.value) for e in at.exception]
    assert not [w.value for w in at.warning if "million" in w.value]

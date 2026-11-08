"""The Run page's "Turn the home rows into a purchase event" (ergonomics review S-3)."""

import copy
from pathlib import Path

import pytest

from owlplanner.library import Library, builder, import_case

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"
EVENTS = [
    {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2026, "flat_until": 2028},
    {"id": "buy", "kind": "purchase", "name": "condo", "price": 700000, "year": 2029, "pay_on": "Bill",
     "costs": {"property tax": 9500, "hoa": 9600, "insurance": 900},
     "financing": {"kind": "cash", "closing": 0.03}},
]


def _library(tmp_path, monkeypatch, tamper=False):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.setenv("OWL_SKIP_DISCLAIMER", "1")
    monkeypatch.syspath_prepend(str(UI_DIR))
    scenario = dict(import_case(BILL), events=copy.deepcopy(EVENTS))
    case, tables, _ = builder.build(scenario)
    if tamper:
        budget = tables["Budget"]
        at, amount = budget["columns"].index("name"), budget["columns"].index("amount")
        next(r for r in budget["rows"] if r[at] == "rent in 2027")[amount] += 100
    lib = Library.open(root)
    lib.save_run(name="imported", scenario=dict(scenario, case=case, hfp=tables, events=[]))
    return lib


def _run_page():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / "Run.py"), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    return at.run()


def _button(at):
    return next(b for b in at.button if b.label == "Turn the home rows into a purchase event")


def test_the_conversion_saves_a_child_run(tmp_path, monkeypatch):
    lib = _library(tmp_path, monkeypatch)
    at = _run_page()
    assert not at.exception, [e.value for e in at.exception]
    _button(at).click().run()
    assert not at.exception, [e.value for e in at.exception]
    runs = {r.name: r for r in lib.runs()}
    child = runs["imported, home as events"]
    assert child.parent == runs["imported"].id
    assert [e["kind"] for e in lib.scenario(child)["events"]] == ["rent", "purchase"]


def test_a_mismatch_is_shown_and_nothing_is_saved(tmp_path, monkeypatch):
    lib = _library(tmp_path, monkeypatch, tamper=True)
    at = _run_page()
    _button(at).click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Not converted" in w.value for w in at.warning)
    assert "rent in 2027" in str(at.dataframe[-1].value)
    assert len(lib.runs()) == 1


def test_no_button_without_a_hand_home(tmp_path, monkeypatch):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    Library.open(root).save_run(name="bill", scenario=import_case(BILL))
    at = _run_page()
    with pytest.raises(StopIteration):
        _button(at)

"""The Scenario page's drafts, dropdowns and goal box (ergonomics review S-2).

Edits typed on the Scenario page used to vanish on a visit to another page (UX review F3:
Streamlit drops a widget's state when its page is not drawn). The page now keeps a session
draft per run. These tests drive the real app (`ui/main.py` in library mode) and switch pages
with AppTest's `switch_page`, which runs the other page's script and so drops the Scenario
page's widget state as the browser does. The data_editor tables cannot be driven from AppTest
(it does not surface them); their draft is checked in the browser (PROGRESS.md, S-2).
"""

import copy
from pathlib import Path

import pytest

from owlplanner.library import Library, import_case

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"

EVENTS = [
    {"id": "w-bill", "kind": "work", "person": "Bill", "start": 2026, "end": 2026, "wages": 90000},
    {"id": "buy", "kind": "purchase", "name": "condo", "price": 700000, "year": 2027, "pay_on": "Bill",
     "costs": {"property tax": 9500, "hoa": 9600, "insurance": 900},
     "financing": {"kind": "cash", "closing": 0.03}},
]


@pytest.fixture
def app(tmp_path, monkeypatch):
    from streamlit import config
    from streamlit.testing.v1 import AppTest

    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.setenv("OWL_SKIP_DISCLAIMER", "1")
    monkeypatch.syspath_prepend(str(UI_DIR))
    previous = config.get_option("server.address")
    config.set_option("server.address", "localhost")  # library mode is localhost only (R11)
    lib = Library.open(root)
    lib.save_run(name="bill", scenario=dict(import_case(BILL), events=copy.deepcopy(EVENTS)))
    at = AppTest.from_file(str(UI_DIR / "main.py"), default_timeout=90)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    at.switch_page("Scenario.py").run()
    assert not at.exception, [e.value for e in at.exception]
    yield lib, at
    config.set_option("server.address", previous)


def _price(at):
    return next(n for n in at.number_input if n.label.startswith("Price"))


def _changes(at):
    return next(c.value for c in at.caption if c.value.startswith("Changes against this run"))


def _save(at, name):
    next(t for t in at.text_input if t.label == "Name").set_value(name)
    next(b for b in at.button if b.label == "Save as a new run").click().run()
    assert not at.exception, [e.value for e in at.exception]


def test_an_edit_survives_a_trip_to_the_run_page(app):
    """Fails before S-2: the price came back as 700000 and the page said "none yet"."""
    _lib, at = app
    _price(at).set_value(800000.0).run()
    assert "condo at 800000" in _changes(at)
    at.switch_page("Run.py").run()
    assert not at.exception, [e.value for e in at.exception]
    # The Run page names the draft and offers the way back.
    assert any("unsaved changes for this run" in i.value for i in at.info)
    at.switch_page("Scenario.py").run()
    assert not at.exception, [e.value for e in at.exception]
    assert _price(at).value == 800000.0
    assert "condo at 800000" in _changes(at)
    assert any("Unsaved changes against *bill*" in w.value for w in at.warning)


def test_a_second_edit_after_the_trip_keeps_the_first(app):
    _lib, at = app
    _price(at).set_value(800000.0).run()
    at.switch_page("Run.py").run()
    at.switch_page("Scenario.py").run()
    next(n for n in at.number_input if n.label.startswith("HOA")).set_value(12000.0).run()
    at.switch_page("Run.py").run()
    at.switch_page("Scenario.py").run()
    assert _price(at).value == 800000.0
    assert next(n for n in at.number_input if n.label.startswith("HOA")).value == 12000.0


def test_reset_drops_the_draft(app):
    _lib, at = app
    _price(at).set_value(800000.0).run()
    next(b for b in at.button if b.label == "Reset to the run").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert _price(at).value == 700000.0
    assert _changes(at).endswith("none yet")
    at.switch_page("Run.py").run()
    assert not any("unsaved changes for this run" in i.value for i in at.info)


def test_a_save_drops_the_draft_and_opens_the_new_run(app):
    lib, at = app
    _price(at).set_value(800000.0).run()
    _save(at, "bill, pricier")
    child = next(r for r in lib.runs() if r.name == "bill, pricier")
    assert at.selectbox(key="scenario_page_run").value == child.id
    assert _price(at).value == 800000.0  # the child's own price
    assert _changes(at).endswith("none yet")


def test_the_page_comes_back_on_the_run_being_edited(app):
    """With two runs, the selector used to come back on the newest one, away from the draft."""
    lib, at = app
    parent = lib.runs()[0]
    lib.save_run(name="other", scenario=dict(import_case(BILL), events=[]))  # now the newest
    at.switch_page("Run.py").run()
    at.switch_page("Scenario.py").run()
    at.selectbox(key="scenario_page_run").set_value(parent.id).run()
    _price(at).set_value(800000.0).run()
    at.switch_page("Run.py").run()
    at.switch_page("Scenario.py").run()
    assert at.selectbox(key="scenario_page_run").value == parent.id
    assert _price(at).value == 800000.0


def test_a_goal_edit_shows_in_the_summary_and_the_saved_case(app):
    lib, at = app
    assert _changes(at).endswith("none yet")  # the goal box itself changes nothing
    stem = next(n.key for n in at.number_input if n.key and n.key.startswith("scn_goal_bequest_"))
    at.number_input(key=stem).set_value(250.0).run()
    assert "bequest target" in _changes(at)
    stop = next(c.key for c in at.checkbox if c.key and c.key.startswith("scn_roth_stop_on_"))
    at.checkbox(key=stop).check().run()
    assert "Roth conversions stop" in _changes(at)
    _save(at, "bill, bequest")
    child = next(r for r in lib.runs() if r.name == "bill, bequest")
    so = lib.scenario(child.id)["case"]["solver_options"]
    assert so["bequest"] == 250.0
    assert so["stopRothConversions"] == 2036  # the plan year (2026, frozen) + 10


def test_ap1_raising_roth_start_above_stop_moves_the_saved_stop_year(tmp_path, monkeypatch):
    """Review AP1: raising `startRothConversions` above an existing `stopRothConversions` showed
    the clamped stop year in the widget while `_year_shown` kept the old stop year in the saved
    case (`startRothConversions = 2040 > stopRothConversions = 2035`)."""
    from streamlit.testing.v1 import AppTest

    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    lib = Library.open(root)
    scenario = dict(import_case(BILL), events=copy.deepcopy(EVENTS))
    scenario["case"].setdefault("solver_options", {})["stopRothConversions"] = 2035
    lib.save_run(name="bill", scenario=scenario)
    at = AppTest.from_file(str(UI_DIR / "Scenario.py"), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    at.run()
    start = next(n.key for n in at.number_input if n.key and n.key.startswith("scn_roth_start_"))
    at.number_input(key=start).set_value(2040).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Roth conversions stop: 2035 -> 2040" in _changes(at)
    assert not any("kept unless you change it" in c.value for c in at.caption)
    _save(at, "bill, roth 2040")
    child = next(r for r in lib.runs() if r.name == "bill, roth 2040")
    so = lib.scenario(child.id)["case"]["solver_options"]
    assert so["startRothConversions"] == 2040
    assert so["stopRothConversions"] == 2040


def test_the_year_picker_offers_the_other_events(app):
    _lib, at = app
    stem = next(b.key for b in at.selectbox if b.key and b.key.startswith("scn_buy_sale_")
                and b.key.endswith("_mode"))[:-5]
    box = at.selectbox(key=f"{stem}_mode")
    assert box.value == "blank"
    box.set_value("event").run()
    events = at.selectbox(key=f"{stem}_event")
    shown = [o.split(" ")[0] for o in events.options]  # AppTest shows the formatted labels
    assert "w-bill" in shown and "buy" not in shown  # the purchase does not anchor on itself
    at.number_input(key=f"{stem}_offset").set_value(10).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not any("Not buildable" in e.value for e in at.error)
    assert not _changes(at).endswith("none yet")  # a sale now: a change against the run

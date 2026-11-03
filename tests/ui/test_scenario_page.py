"""The Scenario page (run-library step 4), rendered for real by Streamlit's AppTest.

`ui/Scenario.py` edits a run's events (work, claiming, rent, a home purchase, care) and shows
what the builder generates with provenance markers (design section 6.3, markers first per
S11). The events here are written by hand in the fixture; what the builder makes of them is
unit-tested in `tests/library/test_builder.py` and at scale by
`fork-notes/synthetic/check_library_builder.py`; this checks the page renders, marks and saves.
"""

import copy
from pathlib import Path

import pytest

from owlplanner.library import Library, import_case

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"

EVENTS = [
    {"id": "w-bill", "kind": "work", "person": "Bill", "start": 2026, "end": 2026, "wages": 90000},
    {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2026, "flat_until": 2027},
    {"id": "buy", "kind": "purchase", "name": "condo", "price": 700000,
     "year": {"anchor": "work_end", "person": "Bill", "after": True}, "pay_on": "Bill",
     "growth": 0.5, "commission": 5.0,
     "place": {"state": "NY", "locality": "Yonkers", "school_district": "City of Yonkers / Yonkers",
               "move": False},
     "costs": {"property tax": 9500, "hoa": 9600, "insurance": 900},
     "financing": {"kind": "cash", "closing": 0.03}},
    {"id": "care", "kind": "care", "amount": 110000,
     "year": {"anchor": "event", "id": "buy", "offset": 20}, "essential": True},
]


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    lib = Library.open(root)
    scenario = import_case(BILL)
    scenario = dict(scenario, events=copy.deepcopy(EVENTS))
    lib.save_run(name="bill", scenario=scenario)
    return lib


def _page():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / "Scenario.py"), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    return at.run()


def _text(at):
    parts = [m.value for m in at.markdown]
    parts += [c.value for c in at.caption]
    parts += [i.value for i in at.info]
    parts += [w.value for w in at.warning]
    parts += [e.value for e in at.error]
    return "\n".join(parts)


class TestScenarioPage:
    def test_the_page_renders_and_explains_the_anchors(self, library):
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "age:Ari:86" in text  # the anchor grammar, explained
        assert "after:Noa" in text

    def test_the_generated_rows_carry_their_markers(self, library):
        at = _page()
        text = _text(at)
        assert "What the events generate (marked)" in text
        assert "regenerated wholesale" in text  # markers first (S11)
        frames = at.dataframe
        assert frames, "no generated-rows table rendered"
        cells = "\n".join(str(f.value) for f in frames)
        assert "rent" in cells and "condo" in cells and "care" in cells
        assert "buy" in cells and "w-bill" in cells  # the event markers

    def test_the_events_are_shown_as_anchors(self, library):
        at = _page()
        year = next(t for t in at.text_input if t.label == "Year")
        assert year.value == "after:Bill"  # the purchase's year anchor, in its text form
        care_from = next(t for t in at.text_input if t.key.startswith("scn_care_year_"))
        assert care_from.value == "event:buy+20"

    def test_a_changed_price_changes_the_summary_and_saves_a_child_run(self, library):
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        price = next(n for n in at.number_input if n.label.startswith("Price"))
        price.set_value(800000.0)
        at.run()
        text = _text(at)
        assert "purchase:" in text and "Changes against this run" in text
        name = next(t for t in at.text_input if t.label == "Name")
        name.set_value("bill, pricier condo")
        save = next(b for b in at.button if b.label == "Save as a new run")
        save.set_value(True)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        names = [r.name for r in library.runs()]
        assert "bill, pricier condo" in names
        child = next(r for r in library.runs() if r.name == "bill, pricier condo")
        parent = next(r for r in library.runs() if r.name == "bill")
        assert child.parent == parent.id
        saved = library.scenario(child.id)
        buy = next(e for e in saved["events"] if e["kind"] == "purchase")
        assert buy["price"] == 800000.0

    def test_a_no_edit_load_shows_no_changes_and_a_no_edit_save_dedupes(self, library):
        """Review U2: the widgets re-type event numbers as floats; canonical cells (T1/V3)
        keep that out of the change summary and the inputs hash."""
        at = _page()
        assert "Changes against this run: none yet" in _text(at)
        save = next(b for b in at.button if b.label == "Save as a new run")
        save.set_value(True)
        at.run()
        assert "Identical to" in _text(at)
        assert len(library.runs()) == 1

    def test_an_unbuildable_scenario_says_why(self, library):
        at = _page()
        year = next(t for t in at.text_input if t.label == "Year")
        year.set_value("event:nope")
        at.run()
        text = _text(at)
        assert "Not buildable yet" in text or "Cannot build" in text

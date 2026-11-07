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
        assert "regenerated whole" in text  # markers first (S11)
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


def _library_with(tmp_path, monkeypatch, events, *, schema_version=None):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    lib = Library.open(root)
    scenario = dict(import_case(BILL), events=copy.deepcopy(events))
    run = lib.save_run(name="bill", scenario=scenario).run
    if schema_version == 1:  # a run saved before events existed: rewrite its stored document
        import json

        path = run.path / "inputs" / "scenario.json"
        stored = json.loads(path.read_text(encoding="utf-8"))
        stored["schema_version"] = 1
        stored.pop("events", None)
        path.write_text(json.dumps(stored), encoding="utf-8")
    return lib


class TestSecondReview:
    """fork-notes/run-library-step4-review-2.md: X4 and X8 on the page."""

    # A purchase with keys the page's widgets do not edit (`type`, `basis`) and with the
    # financing terms left at the builder's defaults (no `closing`).
    BARE_BUY = [{"id": "buy", "kind": "purchase", "name": "condo", "price": 700000, "year": 2027,
                 "pay_on": "Bill", "type": "residence", "basis": 500000,
                 "financing": {"kind": "cash"}}]

    def test_x4_an_unedited_save_of_a_bare_purchase_changes_nothing(self, tmp_path, monkeypatch):
        lib = _library_with(tmp_path, monkeypatch, self.BARE_BUY)
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        assert "Changes against this run: none yet" in _text(at)
        save = next(b for b in at.button if b.label == "Save as a new run")
        save.set_value(True)
        at.run()
        assert "Identical to" in _text(at)
        assert len(lib.runs()) == 1

    def test_x4_an_edit_keeps_the_keys_no_widget_shows(self, tmp_path, monkeypatch):
        lib = _library_with(tmp_path, monkeypatch, self.BARE_BUY)
        at = _page()
        price = next(n for n in at.number_input if n.label.startswith("Price"))
        price.set_value(800000.0)
        at.run()
        assert "condo at 700000 (today's $) in 2027, cash -> condo at 800000 (today's $)" in _text(at)
        save = next(b for b in at.button if b.label == "Save as a new run")
        save.set_value(True)
        at.run()
        child = next(r for r in lib.runs() if r.name != "bill")
        [buy] = [e for e in lib.scenario(child.id)["events"] if e["kind"] == "purchase"]
        assert buy["basis"] == 500000 and buy["type"] == "residence"
        assert buy["financing"] == {"kind": "cash"}  # no closing cost added

    def test_x8_a_new_purchase_is_buildable_as_it_opens(self, tmp_path, monkeypatch):
        _library_with(tmp_path, monkeypatch, [])
        at = _page()
        box = next(c for c in at.checkbox if c.label == "Buy a home")
        box.check()
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "Not buildable yet" not in text and "Cannot build" not in text
        year = next(t for t in at.text_input if t.label == "Year")
        assert year.value == "2027"  # the year after the plan year (2026 under the frozen date)

    def test_x8_a_schema_1_run_shows_no_phantom_change(self, tmp_path, monkeypatch):
        _library_with(tmp_path, monkeypatch, [], schema_version=1)
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "Changes against this run: none yet" in text
        assert "saved in scenario schema 1" in text


class TestDeathEventsAndTheCollectionField:
    """I2's death events on the Scenario page, and the save dialog's "Collection" field
    (design section 7)."""

    DEATH = [{"id": "d", "kind": "death", "person": "Bill", "age": 88}]

    def test_the_death_editor_is_on_the_page(self, tmp_path, monkeypatch):
        _library_with(tmp_path, monkeypatch, EVENTS + self.DEATH)
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        assert "*Death*" in _text(at)

    def test_a_death_event_survives_an_edited_save(self, tmp_path, monkeypatch):
        # The page rebuilds the events list from its widgets (`_assemble`): a death event it
        # does not assemble would be dropped by every edited save.
        lib = _library_with(tmp_path, monkeypatch, EVENTS + self.DEATH)
        at = _page()
        price = next(n for n in at.number_input if n.label.startswith("Price"))
        price.set_value(800000.0)
        at.run()
        save = next(b for b in at.button if b.label == "Save as a new run")
        save.set_value(True)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        child = next(r for r in lib.runs() if r.name != "bill")
        assert [e for e in lib.scenario(child.id)["events"] if e["kind"] == "death"] == [
            {"id": "d", "kind": "death", "person": "Bill", "age": 88}]

    def test_the_save_dialog_s_collection_field_adds_the_run(self, library):
        coll = library.create_collection("Where to live")
        at = _page()
        at.selectbox(key="scenario_page_collection").select("Where to live")
        price = next(n for n in at.number_input if n.label.startswith("Price"))
        price.set_value(800000.0)
        at.run()
        save = next(b for b in at.button if b.label == "Save as a new run")
        save.set_value(True)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        child = next(r for r in library.runs() if r.name != "bill")
        assert library.collection(coll.id).member(child.id).values == {}

    def test_ag6_an_identical_save_keeps_the_member_s_values(self, library):
        """Review AG6: saving a grid member's run again unchanged with its collection chosen
        joins the run it is -- and used to wipe its variant values (`add_member` replaces)."""
        run = library.runs()[0]
        coll = library.create_collection("Where to live")
        library.add_member(coll.id, run, {"place": "yonkers", "year": 2027})
        at = _page()
        at.selectbox(key="scenario_page_collection").select("Where to live")
        at.run()
        save = next(b for b in at.button if b.label == "Save as a new run")
        save.set_value(True)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        assert [r.id for r in library.runs()] == [run.id]  # identical: nothing new saved
        assert library.collection(coll.id).member(run.id).values == {"place": "yonkers", "year": 2027}

"""The Scenario page's purchase box after UX review Q19 (2026-11-07).

*Paid from* is a dropdown of the case's people, the down payment and closing costs are shown
in percent while the event keeps shares, the event ids sit behind "Advanced", and a purchase
whose property tax, HOA and insurance are all 0 is warned about. An unedited save changes
nothing (review X4, AK6), so no inputs hash moves.
"""

from pathlib import Path

from owlplanner.library import Library, import_case

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"
LOAN = {"id": "buy", "kind": "purchase", "name": "condo", "price": 700000, "year": 2027,
        "place": {"state": "TX"}, "costs": {"property tax": 9500, "hoa": 9600},
        # 0.029 x 100 / 100 is not 0.029 in floats: an unedited save must still keep 0.029.
        "financing": {"kind": "loan", "term": 30, "rate": 5.9, "down": 0.07, "closing": 0.029,
                      "extra": 0.02}}


def _open(tmp_path, monkeypatch, events):
    from streamlit.testing.v1 import AppTest

    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    lib = Library.open(root)
    base = lib.save_run(name="bill", scenario=import_case(BILL)).run
    scenario = lib.scenario(base.id)
    scenario["events"] = events
    run = lib.save_run(name="with a purchase", scenario=scenario, parent=base.id).run
    at = AppTest.from_file(str(UI_DIR / "Scenario.py"), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    at.session_state["library_selected_run"] = run.id
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return lib, run, at


def test_shares_are_shown_in_percent_and_an_unedited_save_changes_nothing(tmp_path, monkeypatch):
    lib, run, at = _open(tmp_path, monkeypatch, [LOAN])
    key = run.id
    assert at.number_input(key=f"scn_buy_down_{key}").label == "Down payment (%)"
    assert round(at.number_input(key=f"scn_buy_down_{key}").value, 6) == 7.0
    assert round(at.number_input(key=f"scn_buy_closing_{key}").value, 6) == 2.9
    assert round(at.number_input(key=f"scn_buy_extra_{key}").value, 6) == 2.0
    assert any(c.value == "Changes against this run: none yet" for c in at.caption)


def test_a_percent_typed_is_stored_as_a_share(tmp_path, monkeypatch):
    lib, run, at = _open(tmp_path, monkeypatch, [LOAN])
    key = run.id
    at.number_input(key=f"scn_buy_down_{key}").set_value(25.0).run()
    at.button[[b.label for b in at.button].index("Save as a new run")].click().run()
    assert not at.exception, [e.value for e in at.exception]
    child = next(r for r in lib.runs() if r.id not in (run.id,) and r.name != "bill")
    buy = next(e for e in lib.scenario(child.id)["events"] if e["kind"] == "purchase")
    assert buy["financing"]["down"] == 0.25
    assert buy["financing"]["closing"] == 0.029 and buy["financing"]["extra"] == 0.02


def test_paid_from_is_a_dropdown_of_the_people(tmp_path, monkeypatch):
    lib, run, at = _open(tmp_path, monkeypatch, [LOAN])
    box = at.selectbox(key=f"scn_buy_pay_on_{run.id}")
    assert box.options == ["default (Bill)", "Bill"]
    assert box.value is None  # the event names nobody: the first person, unchanged on save


def test_the_event_id_is_behind_advanced_and_still_editable(tmp_path, monkeypatch):
    lib, run, at = _open(tmp_path, monkeypatch, [LOAN])
    assert any(p.proto.popover.label == "Advanced" for p in at.get("popover"))
    assert at.text_input(key=f"scn_buy_id_{run.id}").value == "buy"


def test_a_home_that_costs_nothing_to_own_is_warned_about(tmp_path, monkeypatch):
    free = {**LOAN, "costs": {}}
    _lib, _run, at = _open(tmp_path, monkeypatch, [free])
    assert any("all 0" in w.value for w in at.warning)
    _lib, _run, at = _open(tmp_path / "2", monkeypatch, [LOAN])
    assert not any("all 0" in w.value for w in at.warning)

"""The Scenario page's home purchase on a case with its own residence (UX review B2).

A new purchase starts from the case's state, locality and school district (dropdowns, as on
Create Case), and a purchase over a hand Fixed Assets home still owned is refused on the page
("Not buildable yet") instead of building two homes.
"""

from pathlib import Path

from owlplanner.library import Library, import_case
from owlplanner.library import builder

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"
YONKERS = "City of Yonkers / Yonkers"


def _library(tmp_path, monkeypatch, hand_home=False):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    lib = Library.open(root)
    scenario = import_case(BILL)
    info = scenario["case"].setdefault("basic_info", {})
    info.update(state="NY", locality="Yonkers", school_district=YONKERS)
    if hand_home:
        scenario["hfp"]["Fixed Assets"] = {
            "columns": list(builder.ASSET_COLUMNS),
            "rows": [[True, "yonkers condo", "residence", 2029, 714000, 714000, 0.5, 0, 5.0]]}
    lib.save_run(name="bill", scenario=scenario)
    return lib


def _page():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / "Scenario.py"), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    return at.run()


def _run_key(lib):
    return lib.runs()[0].id


def test_a_new_purchase_starts_from_the_case_s_district(tmp_path, monkeypatch):
    lib = _library(tmp_path, monkeypatch)
    at = _page()
    key = _run_key(lib)
    at.checkbox(key=f"scn_buy_on_{key}").check().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key=f"scn_place_district_{key}").value == YONKERS
    assert at.selectbox(key=f"scn_place_locality_{key}").value == "Yonkers"
    assert not [e.value for e in at.error]
    # Saved unedited, the case keeps its district (it used to become '').
    at.button[[b.label for b in at.button].index("Save as a new run")].click().run()
    child = next(r for r in lib.runs() if r.id != key)
    case, _hfp, _prov = builder.build(lib.scenario(child.id))
    assert case["basic_info"]["school_district"] == YONKERS


def test_a_district_picked_as_none_is_stated(tmp_path, monkeypatch):
    lib = _library(tmp_path, monkeypatch)
    at = _page()
    key = _run_key(lib)
    at.checkbox(key=f"scn_buy_on_{key}").check().run()
    at.selectbox(key=f"scn_place_district_{key}").set_value("").run()
    at.button[[b.label for b in at.button].index("Save as a new run")].click().run()
    child = next(r for r in lib.runs() if r.id != key)
    buy = next(e for e in lib.scenario(child.id)["events"] if e["kind"] == "purchase")
    assert buy["place"]["school_district"] == builder.NO_PLACE
    assert builder.build(lib.scenario(child.id))[0]["basic_info"]["school_district"] == ""


def test_a_second_home_is_refused_on_the_page(tmp_path, monkeypatch):
    lib = _library(tmp_path, monkeypatch, hand_home=True)
    at = _page()
    key = _run_key(lib)
    at.checkbox(key=f"scn_buy_on_{key}").check().run()
    assert not at.exception, [e.value for e in at.exception]
    errors = [e.value for e in at.error]
    assert any("Not buildable yet" in e and "two homes" in e and "yonkers condo" in e for e in errors), errors
    save = at.button[[b.label for b in at.button].index("Save as a new run")]
    assert save.disabled


def test_another_state_resets_the_pre_filled_place(tmp_path, monkeypatch):
    """Independent review AK2: with Move there and State CT, the case's Yonkers stayed and the
    run failed only at solve time. Another state starts both pickers at (none)."""
    lib = _library(tmp_path, monkeypatch)
    at = _page()
    key = _run_key(lib)
    at.checkbox(key=f"scn_buy_on_{key}").check().run()
    at.checkbox(key=f"scn_place_move_{key}").check().run()
    at.text_input(key=f"scn_place_state_{key}").set_value("CT").run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key=f"scn_place_locality_{key}").value == ""
    assert at.selectbox(key=f"scn_place_district_{key}").value == ""
    assert "Yonkers" not in at.selectbox(key=f"scn_place_locality_{key}").options
    assert not [e.value for e in at.error]


def test_an_unedited_save_keeps_a_lowercase_state(tmp_path, monkeypatch):
    """AK6: the State field upper-cases what is typed; an event stored with "ny" is not a
    change when nothing was edited."""
    lib = _library(tmp_path, monkeypatch)
    run = lib.runs()[0]
    scenario = lib.scenario(run.id)
    scenario["events"] = [{"id": "buy", "kind": "purchase", "name": "condo", "price": 700000,
                           "year": 2027, "place": {"state": "ny", "school_district": YONKERS},
                           "costs": {"property tax": 9500}, "financing": {"kind": "cash"}}]
    child = lib.save_run(name="lowercase", scenario=scenario, parent=run.id).run
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / "Scenario.py"), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    at.session_state["library_selected_run"] = child.id
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    captions = [c.value for c in at.caption]
    assert any(c == "Changes against this run: none yet" for c in captions), captions

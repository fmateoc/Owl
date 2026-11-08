"""Housing rows into events, on request (ergonomics review S-3).

`casefiles.convert_housing` reads a run's hand home (Fixed Assets residence, its loan, the
purchase outflow, the owner's budget lines, the rent before, a care line) as rent / purchase /
care events and accepts them only when they rebuild the run's tables and case cell for cell.
The hand runs here are made the way an import of a builder-made workbook is: the tables and
the case a scenario's events build, saved as hand rows with no events. The synthetic check
(`fork-notes/synthetic/check_library_builder.py`) does the same on all 39 workbooks.
"""

import copy

import pytest

from owlplanner.library import Library, builder, import_case
from owlplanner.library.casefiles import _table_differences, convert_housing, has_housing_rows, housing_events

BILL = "examples/Case_bill.toml"

RENT = {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2026, "flat_until": 2027}
LOAN = {"kind": "loan", "term": 30, "rate": 6.25, "down": 0.2, "closing": 0.03, "extra": 0.02}
BUY = {"id": "buy", "kind": "purchase", "name": "condo", "price": 700000, "year": 2029, "pay_on": "Bill",
       "growth": 0.5, "commission": 5.0, "costs": {"property tax": 9500, "hoa": 9600, "insurance": 900},
       "financing": LOAN}
CARE = {"id": "care", "kind": "care", "amount": 110000, "year": 2045, "essential": True}


def _hand(events, case_edit=None):
    """The hand run an import of this scenario's files gives: built tables, no events."""
    scenario = dict(import_case(BILL), events=copy.deepcopy(events))
    if case_edit:
        case_edit(scenario["case"])
    case, tables, _prov = builder.build(scenario)
    return dict(scenario, case=case, hfp=tables, events=[]), scenario


@pytest.mark.parametrize("events", [
    [RENT, BUY],
    [RENT, dict(BUY, financing={"kind": "cash", "closing": 0.03})],
    [RENT, dict(BUY, sale=2040), CARE],
    [dict(RENT, flat_until=2026), BUY],
    [BUY],
])
def test_a_builder_made_home_converts_and_rebuilds_the_same_tables(events):
    hand, _original = _hand(events)
    assert has_housing_rows(hand)
    converted, problems = convert_housing(hand)
    assert problems == [] and converted is not None
    kinds = [e["kind"] for e in converted["events"]]
    assert kinds == [e["kind"] for e in events]
    # The child's inputs produce the parent's tables (convert_housing checks; checked again).
    _case_a, tables_a, _ = builder.build(hand)
    _case_b, tables_b, _ = builder.build(converted)
    assert _table_differences(tables_a, tables_b) == []
    buy = next(e for e in converted["events"] if e["kind"] == "purchase")
    assert buy["price"] == 700000 and buy["name"] == "condo" and buy["pay_on"] == "Bill"
    assert not has_housing_rows(converted)  # a purchase event now: not offered again


def test_the_loan_terms_are_read_back():
    hand, _ = _hand([RENT, BUY])
    buy = next(e for e in housing_events(hand)["events"] if e["kind"] == "purchase")
    assert buy["financing"]["kind"] == "loan" and buy["financing"]["term"] == 30
    assert buy["financing"]["down"] == 0.2
    # closing + extra are read from one outflow: any pair that rebuilds it is the same plan
    f = buy["financing"]
    assert f["closing"] >= 0 and f["extra"] >= 0


def test_a_move_in_the_purchase_year_becomes_the_purchase_s_move():
    def ny(case):
        case["basic_info"].update(state="NY", locality="", school_district="")

    place = {"state": "NY", "locality": "Yonkers", "school_district": "City of Yonkers / Yonkers", "move": True}
    hand, _ = _hand([RENT, dict(BUY, place=place)], ny)
    assert hand["case"]["basic_info"]["moves"]
    converted, problems = convert_housing(hand)
    assert problems == []
    assert "moves" not in converted["case"]["basic_info"]  # the event makes it now
    buy = next(e for e in converted["events"] if e["kind"] == "purchase")
    assert buy["place"]["move"] and buy["place"]["locality"] == "Yonkers"


def test_a_tampered_rent_row_is_refused_with_its_cell():
    hand, _ = _hand([dict(RENT, flat_until=2028), BUY])
    budget = hand["hfp"]["Budget"]
    at, amount = budget["columns"].index("name"), budget["columns"].index("amount")
    row = next(r for r in budget["rows"] if r[at] == "rent in 2027")
    row[amount] += 100  # a hand edit the rent pattern cannot make
    converted, problems = convert_housing(hand)
    assert converted is None
    assert any("rent in 2027" in p and "amount" in p for p in problems), problems


def test_no_home_no_pattern():
    hand, _ = _hand([RENT])
    assert not has_housing_rows(hand)
    converted, problems = convert_housing(hand)
    assert converted is None and problems[0].startswith("no housing pattern")


def test_the_child_run_is_saved_with_the_parent_s_tables(tmp_path):
    lib = Library.open(tmp_path / "lib")
    hand, _ = _hand([RENT, BUY])
    parent = lib.save_run(name="imported", scenario=hand).run
    converted, problems = convert_housing(lib.scenario(parent))
    assert problems == []
    child = lib.save_run(name="imported, home as events", scenario=converted, parent=parent.id).run
    assert child.parent == parent.id
    _, tables_p, _ = builder.build(lib.scenario(parent))
    _, tables_c, _ = builder.build(lib.scenario(child))
    assert _table_differences(tables_p, tables_c) == []

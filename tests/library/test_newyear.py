"""A run for a new plan year (`library.newyear.start_year`; local-use review D2).

From 1 January every run is refused outside its plan year, and moving the year alone does
not make a run that builds: an event that starts in the old plan year is "outside the plan".
These tests pin what is carried over and how; the 46 synthetic scenarios rolled to 2027, 2028
and 2030, and three of them solved under a moved clock, are recorded in PROGRESS.md.
"""

import copy

import pytest

from owlplanner.library import ScenarioError, canonicalize, check_plan_year, newyear
from owlplanner.library import builder as b

from test_builder import BUY_CASH, GAMMA, RENT, WORK_ARI, WORK_NOA, _case, _scenario

BUY_LOAN_QUEENS = {
    **BUY_CASH, "name": "queens condo", "price": 850000,
    "place": {"state": "NY", "locality": "NYC",
              "school_district": "New York City / New York City (class 2)", "move": True},
    "financing": {"kind": "loan", "term": 30, "rate": 6.25, "down": 0.2, "closing": 0.03},
}


@pytest.fixture(autouse=True)
def flat_gamma(monkeypatch):
    monkeypatch.setattr(b, "_gamma", lambda case, rates_rows=None: list(GAMMA) + [GAMMA[-1] * 1.02 ** k
                                                                                  for k in range(1, 40)])


def _events(scenario):
    return {e["id"]: e for e in scenario.get("events") or []}


def _rows(tables, sheet, name=None):
    table = tables[sheet]
    at = table["columns"].index("name")
    return [r for r in table["rows"] if name is None or r[at] == name]


def _cell(tables, person, year, column):
    table = tables[person]
    row = next(r for r in table["rows"] if r[table["columns"].index("year")] == year)
    return row[table["columns"].index(column)]


class TestRefusals:
    def test_the_same_or_an_earlier_year_is_refused(self):
        scenario = _scenario([RENT])
        for year in (2026, 2025):
            with pytest.raises(ScenarioError, match="already for 2026"):
                newyear.start_year(scenario, year)

    def test_a_run_that_cannot_build_in_the_new_year_is_refused_with_the_reason(self):
        # Ari is 62 at the end of 2026: a death at 62 is before a plan that starts in 2027.
        death = {"id": "d", "kind": "death", "person": "Ari", "age": 62}
        with pytest.raises(ScenarioError, match="cannot be carried over to 2027"):
            newyear.start_year(_scenario([death]), 2027)


class TestThePlanYear:
    def test_hand_rows_only(self):
        rolled, notes = newyear.start_year(_scenario([]), 2027)
        assert rolled["plan_year"] == 2027
        assert rolled["case"]["basic_info"]["start_date"] == "2027-01-01"
        assert rolled["events"] == [] and notes == []

    def test_the_library_would_solve_it_in_its_year(self, pretend_today):
        scenario = canonicalize(_scenario([RENT]))
        with pretend_today("2027-01-02"):
            with pytest.raises(ScenarioError, match="Start 2027 from this run"):
                check_plan_year(scenario)  # the refusal names the route that works
            rolled, _ = newyear.start_year(scenario, 2027)
            assert check_plan_year(rolled) == 2027


class TestEventsUnderWay:
    def test_a_rent_that_goes_on_starts_in_the_new_year_at_the_same_nominal_rent(self):
        base = _scenario([RENT])  # 4000 a month from 2026, flat through 2027
        rolled, notes = newyear.start_year(base, 2027)
        rent = _events(rolled)["rent"]
        assert rent["start"] == {"year": 2027} and rent["flat_until"] == {"year": 2027}
        assert rent["monthly"] == 4000
        assert any("now starts in 2027" in n for n in notes)
        # The 2027 rent in 2027's money is the same before and after.
        _c, before, _p = b.build(canonicalize(copy.deepcopy(base)))
        _c, after, _p = b.build(rolled)
        tail = _rows(before, "Budget", "rent from 2027")[0]
        assert round(tail[5] * GAMMA[1]) == pytest.approx(48000, abs=1)
        assert _rows(after, "Budget", "rent")[0][3:6] == [2027, 0, 48000]

    def test_a_flat_period_already_over_is_no_year_before_the_plan(self):
        rolled, _ = newyear.start_year(_scenario([RENT]), 2029)
        rent = _events(rolled)["rent"]
        assert rent["start"] == {"year": 2029} and rent["flat_until"] == {"year": 2029}
        b.build(rolled)  # nothing "outside the plan"

    def test_work_under_way_starts_in_the_new_year_and_last_year_is_history(self):
        work = {**WORK_NOA, "end": 2028}
        rolled, _ = newyear.start_year(_scenario([work]), 2027)
        assert (_events(rolled)["work-noa"]["start"], _events(rolled)["work-noa"]["end"]) == (2027, 2028)
        assert _cell(rolled["hfp"], "Noa", 2026, "anticipated wages") == 121000  # a hand row now
        _c, tables, _p = b.build(rolled)
        assert [_cell(tables, "Noa", y, "anticipated wages") for y in (2026, 2027, 2028, 2029)] == \
            [121000, 121000, 121000, 0]

    def test_care_under_way_starts_in_the_new_year(self):
        care = {"id": "care", "kind": "care", "amount": 90000, "year": 2026}
        rolled, notes = newyear.start_year(_scenario([care]), 2027)
        assert _events(rolled)["care"]["year"] == {"year": 2027}
        assert any("care started in 2026" in n for n in notes)


class TestEventsThatAreOver:
    def test_finished_work_becomes_history_and_keeps_the_marketplace_year(self):
        base = _scenario([WORK_ARI, WORK_NOA, RENT])
        built_case, _t, _p = b.build(canonicalize(copy.deepcopy(base)))
        assert built_case["aca_settings"]["aca_start_year"] == 2027  # the year after the last work year
        case = _case()
        case["aca_settings"]["aca_start_year"] = 2031  # the hand value the work events override
        rolled, notes = newyear.start_year(_scenario([WORK_ARI, WORK_NOA, RENT], case=case), 2027)
        assert set(_events(rolled)) == {"rent"}
        assert _cell(rolled["hfp"], "Ari", 2026, "anticipated wages") == 168000
        assert _cell(rolled["hfp"], "Noa", 2026, "anticipated wages") == 121000
        assert rolled["case"]["aca_settings"]["aca_start_year"] == 2027
        assert sum("work to 2026 is over" in n for n in notes) == 2

    def test_a_rent_that_ended_before_the_purchase_is_dropped(self):
        rolled, notes = newyear.start_year(_scenario([RENT, BUY_CASH]), 2027)  # bought in 2027
        assert set(_events(rolled)) == {"buy"}
        assert _events(rolled)["buy"]["year"] == {"year": 2027}
        assert any("rent ended in 2026" in n for n in notes)

    def test_a_home_bought_and_sold_is_dropped(self):
        sold = {**BUY_CASH, "sale": 2028}
        rolled, notes = newyear.start_year(_scenario([RENT, sold]), 2029)
        assert rolled["events"] == []
        assert rolled["hfp"].get("Fixed Assets", {"rows": []})["rows"] == []
        assert any("bought in 2027 and sold in 2028" in n for n in notes)


class TestABoughtHome:
    """A home bought before the new plan year is the plan's own from then on: hand rows."""

    def _rolled(self, year=2028):
        base = canonicalize(_scenario([RENT, BUY_LOAN_QUEENS]))
        return base, *newyear.start_year(base, year)

    def test_the_event_becomes_the_rows_it_generated(self):
        base, rolled, notes = self._rolled()
        _c, built, _p = b.build(base)
        assert rolled["events"] == []  # the purchase and the rent that ended before it
        for sheet, names in (("Fixed Assets", ["queens condo"]), ("Debts", ["queens condo mortgage"]),
                             ("Budget", ["property tax", "HOA", "condo insurance"])):
            for name in names:
                assert _rows(rolled["hfp"], sheet, name) == _rows(built, sheet, name), (sheet, name)
        assert _rows(rolled["hfp"], "Budget", "rent") == []
        # The price stays in the dollars of the year it was bought in.
        assert _rows(rolled["hfp"], "Fixed Assets", "queens condo")[0][3:6] == [2027, 867000, 867000]
        assert any("queens condo was bought in 2027" in n for n in notes)

    def test_the_outflow_is_history(self):
        base, rolled, _ = self._rolled()
        _c, built, _p = b.build(base)
        paid = _cell(built, "Ari", 2027, "big-ticket items")
        assert paid < 0 and _cell(rolled["hfp"], "Ari", 2027, "big-ticket items") == paid

    def test_the_move_is_where_the_plan_starts(self):
        _base, rolled, _ = self._rolled()
        info = rolled["case"]["basic_info"]
        assert (info["state"], info["locality"]) == ("NY", "NYC")
        assert info["school_district"] == "New York City / New York City (class 2)"
        assert "moves" not in info

    def test_a_district_stated_without_a_move_is_the_cases(self):
        white_plains = {**BUY_CASH, "place": {"state": "NY", "locality": "",
                                              "school_district": "City of White Plains / White Plains",
                                              "move": False}}
        rolled, _ = newyear.start_year(_scenario([RENT, white_plains]), 2028)
        assert rolled["case"]["basic_info"]["school_district"] == "City of White Plains / White Plains"

    def test_it_builds_the_same_tables_it_built_as_an_event(self):
        """The exact-rebuild rule, seen from outside: apart from the rent that is over, the
        rolled run at the old plan year would build what the run built."""
        base, rolled, _ = self._rolled()
        _c, built, _p = b.build(base)
        again = canonicalize({**copy.deepcopy(rolled), "plan_year": 2026,
                              "case": {**rolled["case"], "basic_info": {**rolled["case"]["basic_info"],
                                                                        "start_date": "2026-01-01"}}})
        _c, tables, _p = b.build(again)
        for sheet in ("Fixed Assets", "Debts"):
            assert sorted(map(str, tables[sheet]["rows"])) == sorted(map(str, built[sheet]["rows"]))

    def test_year_by_year_with_the_purchase_the_only_event_left(self):
        """The yearly use: 2026 -> 2027 drops the rent that ended, 2027 -> 2028 freezes the home
        with no other event left, so the rebuild check builds a scenario with no events, which
        is the hand document as it is (no empty Debts table, where the build with the purchase
        has one). It refused every cash purchase the year after it: "Debts: columns differ"."""
        first, _ = newyear.start_year(_scenario([RENT, BUY_CASH]), 2027)
        assert [e["id"] for e in first["events"]] == [BUY_CASH["id"]]
        second, notes = newyear.start_year(first, 2028)
        assert second["events"] == [] and second["plan_year"] == 2028
        assert _rows(second["hfp"], "Fixed Assets", BUY_CASH["name"])
        assert any("was bought in 2027" in n for n in notes)
        third, _ = newyear.start_year(second, 2029)  # hand rows from then on
        assert _rows(third["hfp"], "Fixed Assets", BUY_CASH["name"])

    def test_the_check_still_sees_a_row_that_differs(self, monkeypatch):
        """Leaving empty tables and zero rows out of the comparison hides no row with a value."""
        tables = {"Ari": {"columns": ["year", "anticipated wages"], "rows": [[2026, 0], [2027, 5]]},
                  "Debts": {"columns": ["name", "year"], "rows": []}}
        other = {"Ari": {"columns": ["year", "anticipated wages"], "rows": [[2027, 6]]}}
        a, b_ = newyear._sorted_tables(tables), newyear._sorted_tables(other)
        assert "Debts" not in a and a["Ari"]["rows"] == [[2027, 5]]
        assert newyear._table_differences(a, b_) == ["Ari, row 1 (2027), anticipated wages: 5 -> 6"]

    def test_the_notes_ask_for_the_homes_value_every_year(self):
        """Owl reads a Fixed Assets value dated in the past as the worth at the plan's start
        (its reader resets the year), so a price carried over unchanged stands still: the
        freeze says so, and so does every later roll, for the row the run then holds."""
        first, _ = newyear.start_year(_scenario([RENT, BUY_CASH]), 2027)
        second, notes = newyear.start_year(first, 2028)
        frozen = [n for n in notes if "was bought in 2027" in n]
        assert len(frozen) == 1 and "worth in January 2028" in frozen[0] and "what was paid" in frozen[0]
        assert not any(n.startswith("Fixed Assets:") for n in notes)  # said once, by the freeze
        _third, notes = newyear.start_year(second, 2029)
        value = _rows(second["hfp"], "Fixed Assets", BUY_CASH["name"])[0][5]
        assert notes == [f"Fixed Assets: *{BUY_CASH['name']}* is valued at {value:,.0f}, as of 2027. The plan "
                         "reads that as what it is worth in January 2029: put in what it is worth now."]

    def test_a_property_sold_or_switched_off_or_valued_this_year_has_no_note(self):
        columns = list(b.ASSET_COLUMNS)
        rows = [[True, "sold", "residence", 2020, 1, 2, 0, 2026, 5], [False, "off", "residence", 2020, 1, 2, 0, 0, 5],
                [True, "now", "residence", 2027, 1, 2, 0, 0, 5], [True, "kept", "residence", 2020, 1, 300000, 0, 0, 5]]
        notes = newyear._owned_assets({"Fixed Assets": {"columns": columns, "rows": rows}}, 2027)
        assert len(notes) == 1 and "*kept* is valued at 300,000, as of 2020" in notes[0]

    def test_a_rebuild_that_differs_is_refused(self, monkeypatch):
        real = newyear._table_differences
        monkeypatch.setattr(newyear, "_table_differences", lambda a, b_: real(a, b_) + ["Debts: tampered"])
        with pytest.raises(ScenarioError, match="cannot be carried over as rows.*tampered"):
            self._rolled()

    def test_a_home_bought_later_stays_an_event(self):
        _base, rolled, notes = self._rolled(year=2027)
        assert _events(rolled)["buy"]["year"] == {"year": 2027}
        assert rolled["hfp"].get("Fixed Assets", {"rows": []})["rows"] == []
        assert not any("bought" in n for n in notes)


class TestAnchors:
    def test_a_year_anchored_to_an_event_that_left_is_its_calendar_year(self):
        care = {"id": "care", "kind": "care", "amount": 90000,
                "year": {"anchor": "event", "id": "buy", "offset": 20}}
        rolled, _ = newyear.start_year(_scenario([RENT, BUY_CASH, care]), 2028)
        assert _events(rolled)["care"]["year"] == {"year": 2047}

    def test_the_purchase_anchor_and_the_work_anchor(self):
        care = {"id": "care", "kind": "care", "amount": 90000, "year": {"anchor": "purchase"},
                "end": {"anchor": "work_end", "person": "Noa", "after": True}}
        work = {**WORK_NOA, "end": 2027}
        rolled, _ = newyear.start_year(_scenario([work, RENT, BUY_CASH, care]), 2028)
        # Bought in 2027 (before 2028): the care span starts with the plan and ends in the
        # year after Noa's last work year, both as calendar years now.
        assert _events(rolled)["care"]["year"] == {"year": 2028}
        assert _events(rolled)["care"]["end"] == {"year": 2028}

    def test_an_anchor_to_an_event_that_moved_keeps_the_year_it_meant(self):
        care = {"id": "care", "kind": "care", "amount": 90000,
                "year": {"anchor": "event", "id": "rent", "offset": 5}}  # five years into the rent
        rolled, _ = newyear.start_year(_scenario([RENT, care]), 2027)
        assert _events(rolled)["rent"]["start"] == {"year": 2027}
        assert _events(rolled)["care"]["year"] == {"year": 2031}  # 2026 + 5, not 2027 + 5

    def test_an_age_anchor_is_left_alone(self):
        care = {"id": "care", "kind": "care", "amount": 90000,
                "year": {"anchor": "age", "person": "Ari", "age": 86}}
        rolled, _ = newyear.start_year(_scenario([care]), 2027)
        assert _events(rolled)["care"]["year"] == {"anchor": "age", "person": "Ari", "age": 86}


class TestTheCase:
    def test_the_previous_years_move_with_the_plan(self):
        case = _case()
        case["solver_options"].update(previousMAGIs=[210.0, 190.0], previousSTARIncomes=[180.0, 170.0])
        rolled, notes = newyear.start_year(_scenario([], case=case), 2027)
        options = rolled["case"]["solver_options"]
        assert options["previousMAGIs"] == [190.0, 0.0]  # 2025's, then 2026's: not known here
        assert options["previousSTARIncomes"] == [170.0, 0.0]
        assert any("The MAGI" in n and "2026" in n and "Run Options" in n for n in notes)
        two, _ = newyear.start_year(_scenario([], case=copy.deepcopy(case)), 2028)
        assert two["case"]["solver_options"]["previousMAGIs"] == [0.0, 0.0]

    def test_unset_previous_years_say_nothing(self):
        case = _case()
        case["solver_options"]["previousMAGIs"] = [0.0, 0.0]
        _rolled, notes = newyear.start_year(_scenario([], case=case), 2027)
        assert notes == []

    @pytest.mark.parametrize("move_year", [2026, 2027])
    def test_a_move_no_longer_ahead_is_the_starting_residence(self, move_year):
        """Owl refuses a move in the plan's first year or before; the residence on December 31
        taxes the year, so a move dated in the new first year is the start too."""
        case = _case()
        case["basic_info"].update(state="NY", locality="Yonkers", moves=[
            {"year": move_year, "state": "NY", "locality": "NYC",
             "school_district": "New York City / New York City (class 2)"},
            {"year": 2040, "state": "FL"}])
        rolled, notes = newyear.start_year(_scenario([], case=case), 2027)
        info = rolled["case"]["basic_info"]
        assert (info["state"], info["locality"]) == ("NY", "NYC")
        assert info["moves"] == [{"year": 2040, "state": "FL"}]
        assert any(f"The move of {move_year}" in n for n in notes)


class TestAMoveInThePlansFirstYear:
    """The builder (found by the roll): a purchase with a move in the plan's first year built a
    case with `moves = [{year = <first year>}]`, which Owl refuses ("A move must fall after the
    first plan year"). It is the starting residence."""

    def test_it_is_the_starting_residence(self):
        first_year = {**BUY_LOAN_QUEENS, "year": 2026}
        case, _tables, provenance = b.build(canonicalize(_scenario([first_year])))
        info = case["basic_info"]
        assert (info["state"], info["locality"]) == ("NY", "NYC")
        assert info["school_district"] == "New York City / New York City (class 2)"
        assert "moves" not in info
        for field in ("state", "locality", "school_district", "moves"):
            assert provenance["case_fields"][f"basic_info.{field}"] == "buy"

    def test_a_later_move_is_a_move(self):
        case, _tables, _p = b.build(canonicalize(_scenario([RENT, BUY_LOAN_QUEENS])))
        assert case["basic_info"]["moves"] == [{
            "year": 2027, "state": "NY", "locality": "NYC",
            "school_district": "New York City / New York City (class 2)"}]
        assert case["basic_info"]["school_district"] == "City of Yonkers / Yonkers"

    def test_the_plan_takes_the_case(self, monkeypatch):
        """Not through the patched inflation path: the real plan build, which refused it."""
        import io
        import tempfile

        from owlplanner.config import config_to_plan
        from owlplanner.library import import_case

        monkeypatch.undo()
        base = import_case("examples/Case_jack+jill.toml")
        year = base["plan_year"]
        buy = {**BUY_LOAN_QUEENS, "year": year, "pay_on": base["case"]["basic_info"]["names"][0]}
        case, _tables, _p = b.build(canonicalize({**base, "events": [buy]}))
        plan = config_to_plan(copy.deepcopy(case), tempfile.gettempdir(), logstreams=[io.StringIO()],
                              loadHFP=False)
        assert plan.state_moves == [] or all(m.year > year for m in plan.state_moves)

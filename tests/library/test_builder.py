"""The scenario builder (step 4): events, anchors, generated rows and cells, provenance.

`check_library_builder.py` (fork-notes/synthetic) is the acceptance at scale: the builder
reproduces make_cases.py's 39 workbooks cell for cell. These tests pin the pieces: the row
builders, the event validation, the I1 anchors, and what build() generates and marks.
"""

import pytest

from owlplanner.library import ScenarioError
from owlplanner.library import builder as b

GAMMA = [1.0, 1.02, 1.0404, 1.061208]  # a flat 2% inflation path for the nominal amounts


def _case(names=("Ari", "Noa")):
    return {
        "basic_info": {"names": list(names), "date_of_birth": ["1964-04-17", "1964-12-09"],
                       "life_expectancy": [89, 89], "start_date": "2026-01-01",
                       "school_district": "City of Yonkers / Yonkers"},
        "fixed_income": {"social_security_ages": [67.0, 67.0]},
        "aca_settings": {"aca_start_year": 2027},
        "solver_options": {"withSSAges": "optimize"},
    }


def _scenario(events, case=None, hfp=None):
    return {"schema_version": 2, "plan_year": 2026,
            "case": case if case is not None else _case(),
            "hfp": hfp or {}, "events": events}


@pytest.fixture
def flat_gamma(monkeypatch):
    """The nominal amounts against a known inflation path (the real path is checked by
    check_library_builder.py and TestRealGamma below)."""
    monkeypatch.setattr(b, "_gamma", lambda case: list(GAMMA))


WORK_ARI = {"id": "work-ari", "kind": "work", "person": "Ari", "start": 2026, "end": 2026,
            "wages": 168000, "k401k": 31000, "employer": 7000}
WORK_NOA = {"id": "work-noa", "kind": "work", "person": "Noa", "start": 2026, "end": 2026,
            "wages": 121000}
RENT = {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2026, "flat_until": 2027}
BUY_CASH = {"id": "buy", "kind": "purchase", "name": "yonkers condo", "price": 700000,
            "year": 2027, "pay_on": "Ari", "growth": 0.5, "commission": 5.0,
            "place": {"state": "NY", "locality": "Yonkers", "school_district": "City of Yonkers / Yonkers",
                      "move": False},
            "costs": {"property tax": 9500, "hoa": 9600, "insurance": 900},
            "financing": {"kind": "cash", "closing": 0.03}}


class TestBudgetRows:
    def test_budget_row_has_the_fourteen_columns(self):
        row = b.budget_row("rent", "rent", 2026, 0, 48000, essential=True)
        assert row == [True, "rent", "rent", 2026, 0, 48000, 0.0, None, True,
                       None, None, None, None, None]

    def test_owner_rows(self):
        rows = b.owner_rows(9500, 9600, 900, 2027, 2049)
        assert [(r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows] == [
            ("property tax", "property tax", 2027, 2049, 9500, 1.0),
            ("HOA", "maintenance", 2027, 2049, 9600, 0.0),
            ("condo insurance", "insurance", 2027, 2049, 900, 0.0),
        ]
        assert all(r[8] is True for r in rows)

    def test_asset_and_debt_rows_link_by_name(self):
        asset = b.asset_row("yonkers condo", 2027, 714000, 0.5, 0, 5.0)
        assert asset == [True, "yonkers condo", "residence", 2027, 714000, 714000, 0.5, 0, 5.0]
        debt = b.debt_row("yonkers mortgage", 2027, 30, 571200, 6.25, "yonkers condo")
        assert debt == [True, "yonkers mortgage", "mortgage", 2027, 30, 571200, 6.25, "yonkers condo"]


class TestRentRows:
    def test_flat_through_2027_then_inflation(self):
        # The household's rent rule (make_cases.py's two rows).
        rows = b.rent_rows(48000, 2026, 2027, 0, GAMMA, 2026)
        assert [(r[1], r[3], r[4], r[5]) for r in rows] == [
            ("rent", 2026, 2026, 48000),
            ("rent from 2027", 2027, 0, round(48000 / 1.02)),
        ]

    def test_the_flat_nominal_amount_holds(self):
        rows = b.rent_rows(48000, 2026, 2027, 0, GAMMA, 2026)
        tail = rows[1]
        assert tail[5] * GAMMA[1] == pytest.approx(48000, abs=1)  # $4,000/mo in 2027 too

    def test_no_flat_year_is_one_row(self):
        rows = b.rent_rows(48000, 2026, 2026, 0, GAMMA, 2026)
        assert [r[1] for r in rows] == ["rent"]
        assert rows[0][4] == 0 and rows[0][5] == 48000

    def test_an_end_before_the_tail_drops_it(self):
        rows = b.rent_rows(48000, 2026, 2027, 2026, GAMMA, 2026)
        assert [r[1] for r in rows] == ["rent"]


class TestValidateEvents:
    def test_the_five_kinds_pass(self):
        events = b.validate_events(
            [WORK_ARI, {"id": "c", "kind": "claim", "person": "Ari", "age": 62.0}, RENT, BUY_CASH,
             {"id": "care", "kind": "care", "year": 2050, "amount": 110000}],
            ["Ari", "Noa"])
        assert [e["kind"] for e in events] == ["work", "claim", "rent", "purchase", "care"]

    def test_no_events_is_empty(self):
        assert b.validate_events(None, ["Ari"]) == []

    @pytest.mark.parametrize("event, match", [
        ({"id": "x", "kind": "tour", "person": "Ari"}, "kind"),
        ({"kind": "work", "person": "Ari", "start": 2026, "end": 2026}, "id"),
        ({"id": "w", "kind": "work", "person": "Zoe", "start": 2026, "end": 2026}, "person"),
        ({"id": "w", "kind": "work", "person": "Ari", "start": 2028, "end": 2027}, "before it starts"),
        ({"id": "w", "kind": "work", "person": "Ari", "start": 2026, "end": 2026, "months_worked": 13},
         "months_worked"),
        ({"id": "c", "kind": "claim", "person": "Ari"}, "age"),
        ({"id": "r", "kind": "rent", "monthly": 0, "start": 2026, "flat_until": 2027}, "monthly"),
        ({"id": "p", "kind": "purchase", "name": "h", "price": 1, "year": 2027}, "financing"),
        ({"id": "p", "kind": "purchase", "name": "h", "price": 1, "year": 2027,
          "financing": {"kind": "loan", "rate": 5.9}}, "term"),
        ({"id": "e", "kind": "care", "year": 2050}, "amount"),
    ])
    def test_bad_events_are_refused(self, event, match):
        with pytest.raises(ScenarioError, match=match):
            b.validate_events([event], ["Ari", "Noa"])

    def test_ids_must_be_unique(self):
        with pytest.raises(ScenarioError, match="used twice"):
            b.validate_events([dict(WORK_ARI), dict(WORK_ARI)], ["Ari", "Noa"])

    def test_one_home_purchase_rent_and_care(self):
        for kind, event in (("purchase", BUY_CASH), ("rent", RENT),
                            ("care", {"id": "k", "kind": "care", "year": 2050, "amount": 1})):
            other = dict(event, id=event["id"] + "2")
            with pytest.raises(ScenarioError, match=f"at most one {kind}"):
                b.validate_events([event, other], ["Ari", "Noa"])


class TestAnchors:
    def _resolve(self, events):
        return b.resolve_years(b.validate_events(events, ["Ari", "Noa"]), _case())

    def test_a_calendar_year(self):
        assert self._resolve([RENT])["rent"]["start"] == 2026

    def test_age_anchor(self):
        events = [{"id": "care", "kind": "care", "year": {"anchor": "age", "person": "Ari", "age": 86},
                   "amount": 1}]
        assert self._resolve(events)["care"]["year"] == 2050  # born 1964, turns 86 in 2050

    def test_work_end_anchors(self):
        work = {"id": "w", "kind": "work", "person": "Noa", "start": 2027, "end": 2028, "wages": 1}
        for anchor, expected in (({}, 2028), ({"after": True}, 2029)):
            events = [work, {"id": "care", "kind": "care", "amount": 1,
                             "year": {"anchor": "work_end", "person": "Noa", **anchor}}]
            assert self._resolve(events)["care"]["year"] == expected

    def test_purchase_and_event_anchors(self):
        events = [
            WORK_ARI,
            {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2026, "flat_until": 2027},
            dict(BUY_CASH, id="buy", year={"anchor": "work_end", "person": "Ari", "after": True}),
            {"id": "care", "kind": "care", "amount": 1,
             "year": {"anchor": "event", "id": "buy", "offset": 2}},
        ]
        resolved = self._resolve(events)
        assert resolved["buy"]["year"] == 2027  # Ari's 2026 work + 1
        assert resolved["care"]["year"] == 2029

    def test_the_purchase_year_anchor(self):
        events = [dict(BUY_CASH, id="buy", year=2031),
                  {"id": "care", "kind": "care", "amount": 1, "year": {"anchor": "purchase"}}]
        assert self._resolve(events)["care"]["year"] == 2031

    def test_an_unresolvable_anchor_is_refused(self):
        events = [{"id": "care", "kind": "care", "amount": 1,
                   "year": {"anchor": "event", "id": "nope"}}]
        with pytest.raises(ScenarioError, match="cannot be resolved"):
            self._resolve(events)

    def test_a_cycle_is_refused(self):
        events = [dict(BUY_CASH, id="buy", year={"anchor": "event", "id": "care"}),
                  {"id": "care", "kind": "care", "amount": 1,
                   "year": {"anchor": "event", "id": "buy"}}]
        with pytest.raises(ScenarioError, match="cannot be resolved"):
            self._resolve(events)


@pytest.mark.usefixtures("flat_gamma")
class TestBuild:
    def test_no_events_is_the_hand_document(self):
        hand = _scenario([])
        case, hfp, provenance = b.build(hand)
        assert case == hand["case"] and hfp == hand["hfp"]
        assert provenance == {"case_fields": {}, "rows": {}, "cells": []}

    def test_work_cells_and_the_marketplace_year(self):
        part = {"id": "work-part", "kind": "work", "person": "Ari", "start": 2027, "end": 2028,
                "level": "part", "wages": 60000, "months_worked": 12}
        case, hfp, provenance = b.build(_scenario([WORK_ARI, WORK_NOA, part]))
        rows = {row[0]: row for row in hfp["Ari"]["rows"]}
        columns = hfp["Ari"]["columns"]
        assert rows[2026][columns.index("anticipated wages")] == 168000
        assert rows[2026][columns.index("401k ctrb")] == 31000
        assert rows[2027][columns.index("anticipated wages")] == 60000
        assert rows[2027][columns.index("months worked")] == 12
        assert rows[2027][columns.index("401k ctrb")] == 0  # no cell generated, row zeroed
        noa = {row[0]: row for row in hfp["Noa"]["rows"]}
        assert noa[2026][columns.index("anticipated wages")] == 121000
        # Part-time work brings no employer coverage: the marketplace year stays 2027 (the last
        # full-time year is 2026).
        assert case["aca_settings"]["aca_start_year"] == 2027
        assert provenance["case_fields"]["aca_settings.aca_start_year"] == "work-ari"

    def test_full_time_work_moves_the_marketplace_year(self):
        more = dict(WORK_ARI, id="work-2027", start=2027, end=2027)
        case, _hfp, _provenance = b.build(_scenario([WORK_ARI, WORK_NOA, more]))
        assert case["aca_settings"]["aca_start_year"] == 2028

    def test_claiming_ages_and_the_switch(self):
        claims = [{"id": "claim-ari", "kind": "claim", "person": "Ari", "age": 62.0},
                  {"id": "claim-noa", "kind": "claim", "person": "Noa", "age": 62.0}]
        case, _hfp, provenance = b.build(_scenario(claims))
        assert case["fixed_income"]["social_security_ages"] == [62.0, 62.0]
        assert case["solver_options"]["withSSAges"] == "fixed"
        assert provenance["case_fields"]["solver_options.withSSAges"] == "claim-ari"

    def test_one_free_claiming_age_searches_only_that_person(self):
        claims = [{"id": "claim-ari", "kind": "claim", "person": "Ari", "age": None}]
        case, _hfp, _provenance = b.build(_scenario(claims))
        # U4: Owl's withSSAges takes a list of names -- the free one is searched, the other
        # person's age (kept from the case) is held.
        assert case["solver_options"]["withSSAges"] == ["Ari"]
        assert case["fixed_income"]["social_security_ages"] == [67.0, 67.0]  # the case's ages kept

    def test_everyone_free_searches_both(self):
        claims = [{"id": "c1", "kind": "claim", "person": "Ari", "age": None},
                  {"id": "c2", "kind": "claim", "person": "Noa", "age": None}]
        case, _hfp, _provenance = b.build(_scenario(claims))
        assert case["solver_options"]["withSSAges"] == "optimize"

    def test_a_purchase_cash(self):
        case, hfp, provenance = b.build(_scenario([WORK_ARI, WORK_NOA, RENT, BUY_CASH]))
        price = round(700000 * GAMMA[1])  # 2027 dollars on the 2026 base
        assets = hfp["Fixed Assets"]["rows"]
        assert assets == [[True, "yonkers condo", "residence", 2027, price, price, 0.5, 0, 5.0]]
        assert hfp["Debts"]["rows"] == []
        columns = hfp["Ari"]["columns"]
        ari = {row[0]: row for row in hfp["Ari"]["rows"]}
        assert ari[2027][columns.index("big-ticket items")] == -round(price * 1.03)
        budget = hfp["Budget"]["rows"]
        assert [row[1] for row in budget] == ["rent", "property tax", "HOA", "condo insurance"]
        assert budget[0][4] == 2026  # rent to the year before the purchase (by construction)
        assert case["basic_info"]["school_district"] == "City of Yonkers / Yonkers"
        assert provenance["rows"]["Fixed Assets|yonkers condo"] == "buy"
        assert ["Ari", "big-ticket items", 2027, "buy"] in provenance["cells"]

    def test_a_purchase_with_a_loan(self):
        buy = dict(BUY_CASH, financing={"kind": "loan", "term": 30, "rate": 6.25, "down": 0.20,
                                        "closing": 0.03, "extra": 0.02,
                                        "name": "yonkers mortgage"})
        _case_out, hfp, _provenance = b.build(_scenario([WORK_ARI, WORK_NOA, RENT, buy]))
        price = round(700000 * GAMMA[1])
        loan = round(price * 0.8)
        assert hfp["Debts"]["rows"] == [[True, "yonkers mortgage", "mortgage", 2027, 30, loan,
                                         6.25, "yonkers condo"]]
        columns = hfp["Ari"]["columns"]
        ari = {row[0]: row for row in hfp["Ari"]["rows"]}
        assert ari[2027][columns.index("big-ticket items")] == -round(price * 0.23 + loan * 0.02)

    def test_a_purchase_with_a_move(self):
        buy = dict(BUY_CASH, place={"state": "NY", "locality": "",
                                    "school_district": "City of White Plains / White Plains",
                                    "move": True})
        case, _hfp, provenance = b.build(_scenario([WORK_ARI, WORK_NOA, RENT, buy]))
        assert case["basic_info"]["moves"] == [{"year": 2027, "state": "NY", "locality": "",
                                                "school_district": "City of White Plains / White Plains"}]
        assert provenance["case_fields"]["basic_info.moves"] == "buy"

    def test_a_sale_ends_the_owner_lines(self):
        care = {"id": "care", "kind": "care", "year": {"anchor": "age", "person": "Ari", "age": 86},
                "amount": 110000}
        buy = dict(BUY_CASH, sale={"anchor": "event", "id": "care"})
        _case_out, hfp, _provenance = b.build(_scenario([WORK_ARI, WORK_NOA, RENT, buy, care]))
        budget = hfp["Budget"]["rows"]
        assert [row[1] for row in budget] == ["rent", "property tax", "HOA", "condo insurance", "care"]
        assert budget[1][4] == 2049  # the owner lines end the year before the sale
        assert budget[4][3] == 2050  # care at age 86 (the anchor)
        assert hfp["Fixed Assets"]["rows"][0][7] == 2050  # yod: the condo is sold that year

    def test_generated_rows_are_regenerated_wholesale(self):
        # A hand row named like a generated one is replaced (the name is the row's identity);
        # other hand rows are untouched (section 6.3, markers first, S11).
        hand = {"Budget": {"columns": list(b.BUDGET_COLUMNS), "rows": [
            b.budget_row("rent", "rent", 2026, 2026, 999),
            b.budget_row("charity", "charity", 2026, 0, 3000),
        ]}}
        _case_out, hfp, _provenance = b.build(_scenario([WORK_ARI, WORK_NOA, RENT, BUY_CASH], hfp=hand))
        budget = hfp["Budget"]["rows"]
        assert [row[1] for row in budget] == ["charity", "rent", "property tax", "HOA", "condo insurance"]
        assert budget[0][5] == 3000  # the hand row, untouched
        assert budget[1][5] == 48000  # the generated rent, not the hand row's 999

    def test_hand_person_rows_keep_their_cells(self):
        columns = list(b.PERSON_COLUMNS)
        rows = [[0] * len(columns) for _ in range(2)]
        rows[0][0], rows[1][0] = 2026, 2027
        rows[0][columns.index("Roth conv")] = 5000
        rows[0][columns.index("anticipated wages")] = 777777  # a generated cell: overwritten
        rows[1][columns.index("anticipated wages")] = 888888  # a hand cell: untouched
        hand = {"Ari": {"columns": columns, "rows": rows}}
        _case_out, hfp, _provenance = b.build(_scenario([WORK_ARI], hfp=hand))
        table = hfp["Ari"]
        assert table["rows"][0][columns.index("Roth conv")] == 5000
        assert table["rows"][0][columns.index("anticipated wages")] == 168000
        assert table["rows"][1][columns.index("anticipated wages")] == 888888

    def test_build_is_deterministic(self):
        scenario = _scenario([WORK_ARI, WORK_NOA, RENT, BUY_CASH])
        first = b.build(scenario)
        second = b.build(scenario)
        assert first == second


@pytest.mark.usefixtures("flat_gamma")
class TestReviewFixes:
    """The step-4 review's findings (fork-notes/run-library-step4-review.md), pinned."""

    def test_u3_an_event_anchor_reads_a_work_end_and_a_rent_start(self):
        events = b.validate_events([
            {"id": "w", "kind": "work", "person": "Ari", "start": 2026, "end": 2028, "wages": 1},
            {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2030, "flat_until": 2031},
            {"id": "care", "kind": "care", "amount": 1, "year": {"anchor": "event", "id": "w"}},
        ], ["Ari", "Noa"])
        assert b.resolve_years(events, _case())["care"]["year"] == 2028  # a span's end
        events = b.validate_events([
            {"id": "w", "kind": "work", "person": "Ari", "start": 2026, "end": 2028, "wages": 1},
            {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2030, "flat_until": 2031},
            {"id": "care", "kind": "care", "amount": 1, "year": {"anchor": "event", "id": "rent"}},
        ], ["Ari", "Noa"])
        assert b.resolve_years(events, _case())["care"]["year"] == 2030  # a rent's start

    def test_u5_a_hand_row_named_like_a_generated_row_in_another_table_is_kept(self):
        hand = {"Budget": {"columns": list(b.BUDGET_COLUMNS), "rows": [
            b.budget_row("yonkers condo", "core", 2026, 0, 1000),  # the home's name in Budget
        ]}}
        _case_out, hfp, _provenance = b.build(_scenario([WORK_ARI, BUY_CASH], hfp=hand))
        assert [row[1] for row in hfp["Budget"]["rows"]] == ["yonkers condo", "property tax", "HOA",
                                                            "condo insurance"]

    def test_u6_a_pay_on_typo_is_refused(self):
        buy = dict(BUY_CASH, pay_on="Zoe")
        with pytest.raises(ScenarioError, match="pay_on"):
            b.build(_scenario([WORK_ARI, buy]))

    def test_u7_an_age_anchor_takes_whole_years(self):
        with pytest.raises(ScenarioError, match="whole years"):
            b.validate_events([{"id": "c", "kind": "care", "amount": 1,
                                "year": {"anchor": "age", "person": "Ari", "age": 86.5}}], ["Ari"])

    def test_u7_years_outside_the_plan_are_refused(self):
        events = [WORK_ARI, dict(BUY_CASH, id="buy", year=2099)]
        with pytest.raises(ScenarioError, match="outside the plan"):
            b.build(_scenario(events))
        events = [WORK_ARI, dict(BUY_CASH, id="buy", year=2025)]
        with pytest.raises(ScenarioError, match="outside the plan"):
            b.build(_scenario(events))

    def test_u7_an_end_before_the_start_is_refused(self):
        events = [WORK_ARI, {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2030,
                             "flat_until": 2031, "end": 2028}]
        with pytest.raises(ScenarioError, match="before"):
            b.build(_scenario(events))

    def test_u7_the_plan_start_must_be_known(self):
        scenario = _scenario([WORK_ARI])
        scenario["case"]["basic_info"].pop("start_date")
        scenario.pop("plan_year")
        with pytest.raises(ScenarioError, match="start year is unknown"):
            b.build(scenario)

    def test_u8_a_kept_hand_age_keeps_its_type(self):
        case = _case()
        case["fixed_income"]["social_security_ages"] = [67, 70]  # ints, as TOML reads them
        claims = [{"id": "claim-noa", "kind": "claim", "person": "Noa", "age": 62.0}]
        built, _hfp, _provenance = b.build(_scenario(claims, case=case))
        assert built["fixed_income"]["social_security_ages"] == [67, 62.0]
        assert isinstance(built["fixed_income"]["social_security_ages"][0], int)


class TestYearRefText:
    @pytest.mark.parametrize("text", ["2029", "age:Ari:86", "work:Noa", "after:Noa", "purchase",
                                      "event:care", "event:care+2", "event:care-1"])
    def test_text_round_trips(self, text):
        ref = b.parse_year_ref(text)
        assert b.year_ref_text(ref) == text

    def test_an_event_id_with_a_dash_keeps_it(self):
        assert b.parse_year_ref("event:my-care") == {"anchor": "event", "id": "my-care", "offset": 0}
        assert b.parse_year_ref("event:my-care+2") == {"anchor": "event", "id": "my-care", "offset": 2}
        assert b.parse_year_ref("event:my-care-2") == {"anchor": "event", "id": "my-care", "offset": -2}

    def test_bad_text_is_refused_with_the_grammar(self):
        with pytest.raises(ScenarioError, match="not a year"):
            b.parse_year_ref("sometime")

    def test_an_anchor_dict_is_its_text(self):
        assert b.year_ref_text({"anchor": "age", "person": "Ari", "age": 86.0}) == "age:Ari:86"
        assert b.year_ref_text({"anchor": "work_end", "person": "Noa", "after": True}) == "after:Noa"


class TestRealGamma:
    def test_nominal_amounts_on_the_case_s_own_path(self):
        # The real inflation path (config_to_plan) with the example couple's case: build runs
        # end to end and the Fixed Assets value is the price grown to the purchase year.
        from owlplanner.library import import_case
        from pathlib import Path

        case_file = Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml"
        scenario = import_case(str(case_file))
        events = [
            {"id": "w1", "kind": "work", "person": "Jack", "start": 2026, "end": 2026, "wages": 1},
            {"id": "rent", "kind": "rent", "monthly": 4000, "start": 2026, "flat_until": 2027},
            {"id": "buy", "kind": "purchase", "name": "h", "price": 700000, "year": 2027,
             "financing": {"kind": "cash", "closing": 0.03}},
        ]
        scenario = dict(scenario, events=events)
        case, hfp, provenance = b.build(scenario)
        gamma = b._gamma(scenario["case"])
        price = round(700000 * float(gamma[1]))
        generated = next(row for row in hfp["Fixed Assets"]["rows"] if row[1] == "h")
        assert generated[4:6] == [price, price]
        assert provenance["rows"]["Budget|rent"] == "rent"
        again = b.build(scenario)
        assert again == (case, hfp, provenance)

""""Make variants" (design section 9.3, step 6): one child scenario per value, per
dimension -- `library.variants`. The acceptance at scale is
`fork-notes/synthetic/check_library_variants.py` (the synthetic condo grid through the
interface matches run_suite.py's report); these tests pin the edits."""

import copy

import pytest

from owlplanner.library import ScenarioError
from owlplanner.library import builder as b
from owlplanner.library import variants as v

GAMMA = [1.02 ** k for k in range(30)]  # a flat 2% inflation path for the nominal amounts

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


def _scenario(events=None):
    return {"schema_version": 2, "plan_year": 2026,
            "case": {
                "basic_info": {"names": ["Ari", "Noa"], "date_of_birth": ["1964-04-17", "1964-12-09"],
                               "life_expectancy": [89, 89], "start_date": "2026-01-01",
                               "school_district": "City of Yonkers / Yonkers"},
                "fixed_income": {"social_security_ages": [67.0, 67.0]},
                "aca_settings": {"aca_start_year": 2027},
                "solver_options": {"withSSAges": "optimize"},
            },
            "hfp": {},
            "events": events if events is not None else [WORK_ARI, WORK_NOA, RENT, BUY_CASH]}


def _purchase(variant):
    return next(e for e in variant.scenario["events"] if e["kind"] == "purchase")


class TestYear:
    def test_one_child_per_year_and_the_parent_is_untouched(self):
        parent = _scenario()
        before = copy.deepcopy(parent)
        out = v.plan_variants(parent, {"year": [2027, 2029, 2031]})
        assert parent == before  # never edited in place
        assert [x.label for x in out] == ["2027", "2029", "2031"]
        assert [x.values for x in out] == [{"year": 2027}, {"year": 2029}, {"year": 2031}]
        assert [_purchase(x)["year"] for x in out] == [{"year": 2027}, {"year": 2029}, {"year": 2031}]

    def test_the_rent_end_follows_the_purchase(self, monkeypatch):
        # The child is a scenario like any other: the builder couples the rows (section 6.2).
        monkeypatch.setattr(b, "_gamma", lambda case, rates_rows=None: list(GAMMA))
        child = v.plan_variants(_scenario(), {"year": [2031]})[0].scenario
        case, tables, _ = b.build(child)
        rent = [r for r in tables["Budget"]["rows"] if r[1] in ("rent", "rent from 2027")]
        assert max(r[4] for r in rent) == 2030  # rent ends the year before the purchase


class TestPlace:
    def test_only_the_given_fields_change(self):
        out = v.plan_variants(_scenario(), {"place": [
            {"label": "queens", "name": "queens condo", "price": 850000,
             "place": {"locality": "NYC", "move": True},
             "costs": {"property tax": 7000}},
        ]})
        buy = _purchase(out[0])
        assert out[0].values == {"place": "queens"}
        assert buy["name"] == "queens condo" and buy["price"] == 850000
        assert buy["place"] == {"state": "NY", "locality": "NYC",
                                "school_district": "City of Yonkers / Yonkers", "move": True}
        assert buy["costs"] == {"property tax": 7000, "hoa": 9600, "insurance": 900}
        assert buy["financing"] == {"kind": "cash", "closing": 0.03}  # untouched

    def test_a_value_needs_a_label(self):
        with pytest.raises(ScenarioError, match="label"):
            v.plan_variants(_scenario(), {"place": [{"price": 1}]})
        with pytest.raises(ScenarioError, match="price"):
            v.plan_variants(_scenario(), {"place": [{"label": "x", "price": -1}]})

    def test_ac5_a_price_that_is_not_a_number_is_refused(self):
        # Review AC5: the shape check takes "a number or a string" and the price is then
        # compared -- a string price raised TypeError where every refusal is ScenarioError.
        with pytest.raises(ScenarioError, match="price"):
            v.plan_variants(_scenario(), {"place": [{"label": "queens", "price": "850000"}]})


class TestFinancing:
    def test_the_loan_replaces_the_financing(self):
        out = v.plan_variants(_scenario(), {"financing": [
            {"label": "mortgage",
             "financing": {"kind": "loan", "term": 30, "rate": 6.25, "down": 0.2,
                           "closing": 0.03, "extra": 0.02, "name": "yonkers mortgage"}},
        ]})
        buy = _purchase(out[0])
        assert out[0].label == "mortgage"
        assert buy["financing"]["kind"] == "loan" and buy["financing"]["term"] == 30
        assert buy["financing"]["name"] == "yonkers mortgage"  # a given name is used as written

    def test_the_place_placeholder_fills_from_the_place_value(self):
        out = v.plan_variants(_scenario(), {
            "place": [{"label": "queens", "name": "queens condo", "price": 850000}],
            "financing": [{"label": "mortgage",
                           "financing": {"kind": "loan", "term": 30, "rate": 6.25, "name": "{place} mortgage"}}],
        })
        assert _purchase(out[0])["financing"]["name"] == "queens mortgage"

    def test_the_place_placeholder_without_a_place_value_is_refused(self):
        with pytest.raises(ScenarioError, match="place"):
            v.plan_variants(_scenario(), {"financing": [
                {"label": "mortgage", "financing": {"kind": "loan", "term": 30, "rate": 6.25,
                                                    "name": "{place} mortgage"}}]})

    def test_a_loan_value_needs_term_and_rate(self):
        with pytest.raises(ScenarioError, match="term"):
            v.plan_variants(_scenario(), {"financing": [
                {"label": "x", "financing": {"kind": "loan"}}]})


class TestWork:
    def test_the_person_s_full_time_work_event_moves(self):
        out = v.plan_variants(_scenario(), {"work": [{"person": "Ari", "end": 2028}]})
        work = next(e for e in out[0].scenario["events"] if e["id"] == "work-ari")
        assert work["end"] == 2028 and work["start"] == 2026
        assert out[0].values == {"work": "Ari to 2028"}

    def test_a_person_without_full_time_work_is_refused(self):
        scenario = _scenario([RENT, BUY_CASH])
        with pytest.raises(ScenarioError, match="full-time"):
            v.plan_variants(scenario, {"work": [{"person": "Ari", "end": 2028}]})


class TestClaim:
    def test_ages_go_on_the_claim_events(self):
        out = v.plan_variants(_scenario(), {"claim": [{"Ari": 62, "Noa": 67}]})
        claims = {e["person"]: e for e in out[0].scenario["events"] if e["kind"] == "claim"}
        assert claims["Ari"]["age"] == 62.0 and claims["Noa"]["age"] == 67.0
        assert out[0].values == {"claim": "Ari 62y0m / Noa 67y0m"}

    def test_none_is_let_owl_choose(self):
        out = v.plan_variants(_scenario(), {"claim": [{"Ari": None, "Noa": 70}]})
        claims = {e["person"]: e for e in out[0].scenario["events"] if e["kind"] == "claim"}
        assert claims["Ari"]["age"] is None and claims["Noa"]["age"] == 70.0
        assert out[0].values == {"claim": "Ari: let Owl choose / Noa 70y0m"}

    def test_an_existing_claim_event_is_edited_not_duplicated(self):
        scenario = _scenario([WORK_ARI, WORK_NOA, RENT, BUY_CASH,
                              {"id": "claim-ari", "kind": "claim", "person": "Ari", "age": 67.0}])
        out = v.plan_variants(scenario, {"claim": [{"Ari": 70, "Noa": 66}]})
        claims = [e for e in out[0].scenario["events"] if e["kind"] == "claim"]
        assert len(claims) == 2
        assert next(e for e in claims if e["person"] == "Ari")["age"] == 70.0

    def test_an_unknown_person_is_refused(self):
        with pytest.raises(ScenarioError, match="Zoe"):
            v.plan_variants(_scenario(), {"claim": [{"Zoe": 67}]})


class TestProduct:
    def test_the_grid_is_the_product_and_the_label_joins(self):
        out = v.plan_variants(_scenario(), {
            "place": [{"label": "yonkers", "name": "yonkers condo", "price": 700000},
                      {"label": "queens", "name": "queens condo", "price": 850000}],
            "year": [2027, 2029],
            "financing": [{"label": "cash", "financing": {"kind": "cash"}}],
        })
        assert [(x.label, x.values) for x in out] == [
            ("yonkers-2027-cash", {"place": "yonkers", "year": 2027, "financing": "cash"}),
            ("yonkers-2029-cash", {"place": "yonkers", "year": 2029, "financing": "cash"}),
            ("queens-2027-cash", {"place": "queens", "year": 2027, "financing": "cash"}),
            ("queens-2029-cash", {"place": "queens", "year": 2029, "financing": "cash"}),
        ]

    def test_a_single_valued_dimension_holds_every_child(self):
        # The claiming-ages dimension with one value pins every variant (the suite's rule:
        # the grid runs at the baseline's ages).
        out = v.plan_variants(_scenario(), {"year": [2027, 2029], "claim": [{"Ari": 67, "Noa": 67}]})
        assert len(out) == 2
        assert all(_purchase(x)["year"] in ({"year": 2027}, {"year": 2029}) for x in out)
        for x in out:
            claims = [e for e in x.scenario["events"] if e["kind"] == "claim"]
            assert sorted(e["age"] for e in claims) == [67.0, 67.0]


class TestRefusals:
    def test_an_unknown_dimension(self):
        with pytest.raises(ScenarioError, match="unknown dimension"):
            v.plan_variants(_scenario(), {"care": [2050]})

    def test_no_dimension(self):
        with pytest.raises(ScenarioError, match="no dimension"):
            v.plan_variants(_scenario(), {})

    def test_an_empty_value_list(self):
        with pytest.raises(ScenarioError, match="at least one value"):
            v.plan_variants(_scenario(), {"year": []})

    def test_a_purchase_dimension_without_a_purchase(self):
        with pytest.raises(ScenarioError, match="nothing to vary") as info:
            v.plan_variants(_scenario([WORK_ARI, WORK_NOA, RENT]), {"year": [2029]})
        # UX review B2: the message says how to get a purchase event.
        assert "rent-only run" in str(info.value) and "Scenario page" in str(info.value)

    def test_a_child_that_would_not_build_is_refused_where_it_is_saved(self, monkeypatch):
        # plan_variants checks the scenario's shape; the plan window is the builder's
        # (section 6.2, U7), and save_run builds -- so a year outside the plan stops there.
        monkeypatch.setattr(b, "_gamma", lambda case, rates_rows=None: list(GAMMA))
        child = v.plan_variants(_scenario(), {"year": [3000]})[0].scenario
        with pytest.raises(ScenarioError, match="outside the plan"):
            b.build(child)


class TestAD1NonFiniteValues:
    """Review AD1: a NaN from an editor cell passed `<= 0` and the type checks, `normalize`
    stored it as None, and a None cost became a $0 Budget line. Every number is refused
    unless it is one."""

    NAN = float("nan")

    @pytest.mark.parametrize("value", [
        {"label": "wp", "price": float("nan")},
        {"label": "wp", "costs": {"hoa": float("nan")}},
        {"label": "wp", "costs": {"hoa": None}},
        {"label": "wp", "costs": {"hoa": -1}},
        {"label": "wp", "place": {"locality": float("nan")}},
        {"label": "wp", "place": {"move": "False"}},
        {"label": float("nan")},
    ])
    def test_a_place_value_with_a_non_number_is_refused(self, value):
        with pytest.raises(ScenarioError):
            v.plan_variants(_scenario(), {"place": [value]})

    @pytest.mark.parametrize("field", ["term", "rate", "down", "closing", "extra"])
    def test_a_loan_term_that_is_not_a_number_is_refused(self, field):
        financing = {"kind": "loan", "term": 30, "rate": 5.9, field: float("nan")}
        with pytest.raises(ScenarioError, match=field):
            v.plan_variants(_scenario(), {"financing": [{"label": "m", "financing": financing}]})

    def test_a_loan_name_that_is_not_text_is_refused(self):
        with pytest.raises(ScenarioError, match="name"):
            v.plan_variants(_scenario(), {"financing": [
                {"label": "m", "financing": {"kind": "loan", "term": 30, "rate": 5.9, "name": float("nan")}}]})

    def test_the_builder_refuses_a_cost_or_term_left_empty(self):
        # The library's own door (any route, not only make variants): a stored None.
        doc = copy.deepcopy(_scenario())  # its events are shared fixtures: never edit in place
        buy = next(e for e in doc["events"] if e["kind"] == "purchase")
        buy["costs"] = {"property tax": None, "hoa": 9600, "insurance": 900}
        with pytest.raises(ScenarioError, match="costs.property tax"):
            v.validate(doc)
        buy["costs"] = {"hoa": 9600}
        buy["financing"] = {"kind": "loan", "term": 30, "rate": 5.9, "down": None}
        with pytest.raises(ScenarioError, match="financing.down"):
            v.validate(doc)


class TestDeath:
    """I2's longevity dimension ("first death at 75, 80, 85, each spouse in turn"): one
    child per value, the value moving one person's life horizon (`death` event)."""

    def test_one_child_per_value_and_the_label(self):
        out = v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                              {"death": [{"person": "Ari", "age": 75},
                                         {"person": "Ari", "age": 80},
                                         {"person": "Noa", "age": 85}]})
        assert [x.label for x in out] == ["ari-dies-at-75", "ari-dies-at-80", "noa-dies-at-85"]
        assert out[0].values == {"death": "Ari dies at 75"}

    def test_the_death_event_is_created_and_build_gives_the_horizon(self):
        child = v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                                {"death": [{"person": "Ari", "age": 75}]})[0].scenario
        assert [e for e in child["events"] if e["kind"] == "death"] == [
            {"id": "death-ari", "kind": "death", "person": "Ari", "age": 75}]
        case, _tables, provenance = b.build(child)
        assert case["basic_info"]["life_expectancy"] == [75, 89]
        assert provenance["case_fields"]["basic_info.life_expectancy"] == "death-ari"

    def test_an_existing_death_event_is_moved_not_duplicated(self):
        doc = _scenario([WORK_ARI, WORK_NOA,
                         {"id": "d1", "kind": "death", "person": "Ari", "age": 80}])
        child = v.plan_variants(doc, {"death": [{"person": "Ari", "age": 75}]})[0].scenario
        assert [e for e in child["events"] if e["kind"] == "death"] == [
            {"id": "d1", "kind": "death", "person": "Ari", "age": 75}]

    def test_a_label_is_used_as_written(self):
        out = v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                              {"death": [{"label": "early death", "person": "Noa", "age": 70}]})
        assert out[0].label == "early-death" and out[0].values == {"death": "early death"}

    @pytest.mark.parametrize("value, match", [
        ({"person": "Zeke", "age": 70}, "people"),
        ({"person": "Ari", "age": 75.5}, "whole number"),
        ({"person": "Ari", "age": 200}, "whole number"),
        ({"person": "Ari", "age": "75"}, "whole number"),
        ({"person": "Ari"}, "whole number"),
    ])
    def test_a_value_that_does_not_fit_is_refused(self, value, match):
        with pytest.raises(ScenarioError, match=match):
            v.plan_variants(_scenario([WORK_ARI, WORK_NOA]), {"death": [value]})

    def test_a_death_before_the_plan_start_is_refused(self):
        # Ari is 62 in the plan year (born 1964): a death at 55 would leave the plan no year
        # of life for them (`check_death_age`).
        with pytest.raises(ScenarioError, match="before the plan"):
            v.plan_variants(_scenario([WORK_ARI, WORK_NOA]), {"death": [{"person": "Ari", "age": 55}]})
        v.plan_variants(_scenario([WORK_ARI, WORK_NOA]), {"death": [{"person": "Ari", "age": 62}]})

    def test_a_value_that_leaves_the_plan_one_year_is_refused(self):
        # The parent carries Noa's death at 62 (her age in the plan year, born 1964); Ari's
        # at 62 leaves the plan one year -- `Plan` refuses that ("Plan needs more than 1
        # years"), so the door refuses it (review AE1).
        doc = _scenario([WORK_ARI, WORK_NOA,
                         {"id": "d1", "kind": "death", "person": "Noa", "age": 62}])
        with pytest.raises(ScenarioError, match="not more than one year"):
            v.plan_variants(doc, {"death": [{"person": "Ari", "age": 62}]})

    def test_ai6_a_death_before_the_person_s_own_work_end_is_refused(self):
        """Review AI6: a death value before the person's last work year is refused at the
        door, and so is a death and a work end varied together that disagree."""
        late = dict(WORK_ARI, start=2027, end=2027, id="w27")
        with pytest.raises(ScenarioError, match="works to 2027"):
            v.plan_variants(_scenario([WORK_ARI, late, WORK_NOA]),
                            {"death": [{"person": "Ari", "age": 62}]})
        with pytest.raises(ScenarioError, match="works to 2028"):
            v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                            {"death": [{"person": "Ari", "age": 63}],
                             "work": [{"person": "Ari", "end": 2027}, {"person": "Ari", "end": 2028}]})
        out = v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                              {"death": [{"person": "Ari", "age": 63}],
                               "work": [{"person": "Ari", "end": 2027}]})
        assert len(out) == 1

    def test_one_death_event_per_person(self):
        doc = _scenario([WORK_ARI, WORK_NOA,
                         {"id": "d1", "kind": "death", "person": "Ari", "age": 80},
                         {"id": "d2", "kind": "death", "person": "Ari", "age": 75}])
        with pytest.raises(ScenarioError, match="already has a death event"):
            v.validate(doc)


class TestSequence:
    """I11's named downturn sequences as a dimension (step 5b's `downturn` event: one
    overlay per scenario, placed at a year or an anchor)."""

    DOWNTURN = {"id": "stress", "kind": "downturn", "sequence": "crash-30", "start": 2030}

    def test_the_event_is_created_with_its_placement(self):
        out = v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                              {"sequence": [{"label": "crash at retirement",
                                             "sequence": "crash-30", "start": "after:Ari"}]})
        assert out[0].label == "crash-at-retirement"
        assert [e for e in out[0].scenario["events"] if e["kind"] == "downturn"] == [
            {"id": "downturn", "kind": "downturn", "sequence": "crash-30",
             "start": {"anchor": "work_end", "person": "Ari", "after": True}}]

    def test_an_event_anchor_is_read_against_the_scenario_s_ids(self):
        # Review AF3 (X5's rule): `event:<id>` is parsed against the scenario's ids -- an id
        # that itself ends in `-<digits>` wins over reading the digits as an offset.
        doc = _scenario([WORK_ARI, WORK_NOA, dict(BUY_CASH, id="buy-2027")])
        out = v.plan_variants(doc, {"sequence": [
            {"sequence": "crash-30", "start": "event:buy-2027"}]})
        assert [e for e in out[0].scenario["events"] if e["kind"] == "downturn"] == [
            {"id": "downturn", "kind": "downturn", "sequence": "crash-30",
             "start": {"anchor": "event", "id": "buy-2027", "offset": 0}}]

    def test_the_label_names_the_sequence_and_the_placement(self):
        out = v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                              {"sequence": [{"sequence": "poor-decade", "start": 2029}]})
        assert out[0].values == {"sequence": "poor-decade at 2029"}
        out = v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                              {"sequence": [{"sequence": "three-negative-years", "start": "purchase"}]})
        assert out[0].values == {"sequence": "three-negative-years at purchase"}

    def test_an_existing_overlay_is_moved_not_duplicated(self):
        doc = _scenario([WORK_ARI, WORK_NOA, dict(self.DOWNTURN)])
        child = v.plan_variants(doc, {"sequence": [
            {"sequence": "three-negative-years", "start": 2031}]})[0].scenario
        assert [e for e in child["events"] if e["kind"] == "downturn"] == [
            {"id": "stress", "kind": "downturn", "sequence": "three-negative-years",
             "start": {"year": 2031}}]

    def test_no_downturn_removes_the_overlay(self):
        doc = _scenario([WORK_ARI, WORK_NOA, dict(self.DOWNTURN)])
        out = v.plan_variants(doc, {"sequence": [{"sequence": None}]})
        assert out[0].values == {"sequence": "no downturn"}
        assert not [e for e in out[0].scenario["events"] if e["kind"] == "downturn"]

    @pytest.mark.parametrize("value, match", [
        ({"sequence": "nope", "start": 2029}, "is not one of"),
        ({"sequence": "crash-30"}, "start"),
        ({"sequence": "crash-30", "start": "someday"}, "start"),
    ])
    def test_a_value_that_does_not_fit_is_refused(self, value, match):
        with pytest.raises(ScenarioError, match=match):
            v.plan_variants(_scenario([WORK_ARI, WORK_NOA]), {"sequence": [value]})

    def test_a_run_with_a_rates_table_refuses_an_overlay(self):
        # `builder._check_table_events` at build time; the door says it too (the table the
        # overlay would generate is already there, hand-entered).
        doc = _scenario([WORK_ARI, WORK_NOA])
        doc["case"]["rates_selection"] = {"method": "table"}
        doc["rates_table"] = {"columns": ["year", "Inflation"], "rows": [[2026, 2.0]]}
        with pytest.raises(ScenarioError, match="hand-entered rates table"):
            v.plan_variants(doc, {"sequence": [{"sequence": "crash-30", "start": 2029}]})

    def test_a_table_case_refuses_an_overlay(self):
        doc = _scenario([WORK_ARI, WORK_NOA])
        doc["case"]["rates_selection"] = {"method": "table"}
        with pytest.raises(ScenarioError, match="reads a rates table"):
            v.plan_variants(doc, {"sequence": [{"sequence": "crash-30", "start": 2029}]})

    def test_the_child_is_a_scenario_like_any_other(self, monkeypatch):
        import types

        import numpy as np

        monkeypatch.setattr(b, "_throwaway_plan", lambda case, rates_rows=None: types.SimpleNamespace(
            year_n=list(range(2026, 2046)),
            tau_kn=np.array([[0.06] * 20, [0.045] * 20, [0.03] * 20, [0.02] * 20])))
        child = v.plan_variants(_scenario([WORK_ARI, WORK_NOA]),
                                {"sequence": [{"sequence": "crash-30", "start": 2030}]})[0].scenario
        case, _tables, _provenance = b.build(child)  # the overlay generates the rates table
        assert case["rates_selection"]["method"] == "table"
        assert case["rates_selection"]["rates_file"] == "rates.csv"

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
        with pytest.raises(ScenarioError, match="nothing to vary"):
            v.plan_variants(_scenario([WORK_ARI, WORK_NOA, RENT]), {"year": [2029]})

    def test_a_child_that_would_not_build_is_refused_where_it_is_saved(self, monkeypatch):
        # plan_variants checks the scenario's shape; the plan window is the builder's
        # (section 6.2, U7), and save_run builds -- so a year outside the plan stops there.
        monkeypatch.setattr(b, "_gamma", lambda case, rates_rows=None: list(GAMMA))
        child = v.plan_variants(_scenario(), {"year": [3000]})[0].scenario
        with pytest.raises(ScenarioError, match="outside the plan"):
            b.build(child)

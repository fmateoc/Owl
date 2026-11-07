"""A purchase event on a case that already has a district or a home (UX review B2).

(a) A hand Fixed Assets residence still owned at the purchase gives the plan two homes: the
builder refuses it. (b) A purchase without a move used to set the case's school district from
the event's (blank by default), so the NY STAR credit stopped silently: a blank field now
keeps the case's district, and "-" (the variants tables' "clear" spelling) states "none".
"""

import copy

import pytest

from owlplanner.library import ScenarioError
from owlplanner.library import builder as b

GAMMA = [1.0 + 0.02 * k for k in range(40)]
BUY_CASH = {"id": "buy", "kind": "purchase", "name": "yonkers condo", "price": 700000,
            "year": 2027, "pay_on": "Ari", "costs": {"property tax": 9500},
            "financing": {"kind": "cash"}}


def _scenario(events, hfp=None):
    case = {"basic_info": {"names": ["Ari", "Noa"], "date_of_birth": ["1964-04-17", "1964-12-09"],
                           "life_expectancy": [89, 89], "start_date": "2026-01-01",
                           "state": "NY", "locality": "Yonkers",
                           "school_district": "City of Yonkers / Yonkers"}}
    return {"schema_version": 2, "plan_year": 2026, "case": case, "hfp": hfp or {}, "events": events}


@pytest.fixture
def flat_gamma(monkeypatch):
    monkeypatch.setattr(b, "_gamma", lambda case, rates_rows=None: list(GAMMA))


YONKERS = "City of Yonkers / Yonkers"


def _buy(**place):
    event = copy.deepcopy(BUY_CASH)
    event["place"] = {"state": "NY", "locality": "Yonkers", "move": False, **place}
    return event


def _hand_home(year=2026, yod=0, active=True, typ="residence"):
    return {"Fixed Assets": {"columns": list(b.ASSET_COLUMNS),
                             "rows": [[active, "old condo", typ, year, 500000, 500000, 0.5, yod, 5.0]]}}


@pytest.mark.usefixtures("flat_gamma")
class TestDistrict:
    def test_a_blank_district_keeps_the_cases(self):
        case, _hfp, prov = b.build(_scenario([_buy(school_district="")]))
        assert case["basic_info"]["school_district"] == YONKERS
        assert "basic_info.school_district" not in prov["case_fields"]

    def test_a_missing_district_keeps_the_cases(self):
        event = _buy()
        event["place"].pop("school_district", None)
        case, _hfp, _prov = b.build(_scenario([event]))
        assert case["basic_info"]["school_district"] == YONKERS

    def test_a_dash_states_no_district(self):
        case, _hfp, prov = b.build(_scenario([_buy(school_district="-")]))
        assert case["basic_info"]["school_district"] == ""
        assert prov["case_fields"]["basic_info.school_district"] == "buy"

    def test_a_named_district_is_set(self):
        other = "City of White Plains / White Plains"
        case, _hfp, _prov = b.build(_scenario([_buy(school_district=other)]))
        assert case["basic_info"]["school_district"] == other

    def test_a_move_reads_a_dash_as_none(self):
        case, _hfp, _prov = b.build(_scenario([_buy(school_district="-", locality="-", move=True)]))
        assert case["basic_info"]["moves"][0]["school_district"] == ""
        assert case["basic_info"]["moves"][0]["locality"] == ""


@pytest.mark.usefixtures("flat_gamma")
class TestSecondHome:
    def test_a_hand_home_still_owned_is_refused(self):
        with pytest.raises(ScenarioError, match="already holds a home"):
            b.build(_scenario([_buy(school_district=YONKERS)], hfp=_hand_home()))

    def test_a_hand_home_bought_later_is_refused(self):
        with pytest.raises(ScenarioError, match="old condo"):
            b.build(_scenario([_buy(school_district=YONKERS)], hfp=_hand_home(year=2030)))

    def test_a_hand_home_sold_by_the_purchase_is_allowed(self):
        _case, hfp, _prov = b.build(_scenario([_buy(school_district=YONKERS)], hfp=_hand_home(yod=2027)))
        assert [r[1] for r in hfp["Fixed Assets"]["rows"]] == ["old condo", "yonkers condo"]

    def test_an_inactive_hand_home_is_allowed(self):
        b.build(_scenario([_buy(school_district=YONKERS)], hfp=_hand_home(active=False)))

    def test_a_hand_asset_that_is_no_home_is_allowed(self):
        b.build(_scenario([_buy(school_district=YONKERS)], hfp=_hand_home(typ="collectibles")))

    def test_a_hand_home_with_the_event_s_name_is_refused(self):
        # Independent review AK1: the event's row would replace it by name while the hand
        # home's loan and down payment stayed. The hand tables never hold the event's own rows
        # (a pages save drops them), so a same-name hand row is a home of the case's.
        hand = _hand_home()
        hand["Fixed Assets"]["rows"][0][1] = BUY_CASH["name"]
        with pytest.raises(ScenarioError, match="two homes"):
            b.build(_scenario([_buy(school_district=YONKERS)], hfp=hand))

    @pytest.mark.parametrize("year", [None, float("nan"), ""])
    def test_a_hand_home_with_a_blank_year_is_owned_from_the_plan_start(self, year):
        # AK3: fixedassets reads a blank year as the plan's first year.
        hand = _hand_home()
        hand["Fixed Assets"]["rows"][0][3] = year
        with pytest.raises(ScenarioError, match="from 2026"):
            b.build(_scenario([_buy(school_district=YONKERS)], hfp=hand))

    def test_a_table_without_year_or_yod_columns_is_still_checked(self):
        # AK3: no `year` column is the plan start, no `yod` column is kept.
        hfp = {"Fixed Assets": {"columns": ["active", "name", "type", "value"],
                                "rows": [[True, "old condo", "residence", 500000]]}}
        with pytest.raises(ScenarioError, match="kept to the end"):
            b.build(_scenario([_buy(school_district=YONKERS)], hfp=hfp))

    @pytest.mark.parametrize("active", [0, False])
    def test_a_falsy_active_cell_is_inactive(self, active):
        # AK5: utils.is_row_active reads any falsy, non-blank value as inactive.
        b.build(_scenario([_buy(school_district=YONKERS)], hfp=_hand_home(active=active)))

    @pytest.mark.parametrize("active", [None, float("nan")])
    def test_a_blank_active_cell_is_active(self, active):
        with pytest.raises(ScenarioError, match="two homes"):
            b.build(_scenario([_buy(school_district=YONKERS)], hfp=_hand_home(active=active)))


@pytest.mark.usefixtures("flat_gamma")
class TestPlaceIsValidated:
    """AK2: an unknown locality or district for the state is refused when the scenario is
    built, not when the plan is solved."""

    def test_a_move_to_another_state_with_a_ny_locality_is_refused(self):
        with pytest.raises(ScenarioError, match="buy.place: Unknown locality 'Yonkers' for state 'CT'"):
            b.build(_scenario([_buy(state="CT", locality="Yonkers", school_district="", move=True)]))

    def test_an_unknown_district_in_a_move_is_refused(self):
        with pytest.raises(ScenarioError, match="buy.place"):
            b.build(_scenario([_buy(school_district="Nowhere / Nothing", move=True)]))

    def test_a_known_move_builds(self):
        case, _hfp, _prov = b.build(_scenario([_buy(locality="", school_district="-", move=True)]))
        assert case["basic_info"]["moves"][0]["state"] == "NY"

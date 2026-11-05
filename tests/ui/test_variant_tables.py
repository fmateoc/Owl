"""The make-variants editors as Streamlit hands them back (review AD1, AD2, AD6):
`ui/variant_tables.py`.

AppTest cannot drive a data editor, so these tests apply Streamlit's own edit code
(`data_editor._apply_dataframe_edits`, the function the widget uses on the page's
DataFrame) to the page's empty tables, with the cells the user did not touch absent from
`added_rows` as the frontend sends them. The editor returns None for those cells;
`DataFrame.iterrows()` used to turn that None into NaN, which passed every guard: empty
costs reached the plan as $0, a loan without its default terms failed in the builder.
Streamlit's function is private: if it moves, these tests fail loudly rather than pass.
"""

import json
import math
from pathlib import Path

import pyarrow as pa
import pytest
from streamlit.elements.lib.column_config_utils import determine_dataframe_schema
from streamlit.elements.widgets import data_editor as de

from owlplanner.library import ScenarioError, variants
from owlplanner.library import builder as b
from owlplanner.library.builder import build

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
YONKERS = {"id": "buy", "kind": "purchase", "name": "yonkers condo", "price": 700000, "year": 2027,
           "pay_on": "Ari", "growth": 0.5, "commission": 5.0,
           "place": {"state": "NY", "locality": "Yonkers", "school_district": "City of Yonkers / Yonkers",
                     "move": False},
           "costs": {"property tax": 9500, "hoa": 9600, "insurance": 900},
           "financing": {"kind": "cash", "closing": 0.03}}


@pytest.fixture
def flat_gamma(monkeypatch):
    """A flat 2% inflation path for the nominal amounts (as tests/library/test_variants.py)."""
    monkeypatch.setattr(b, "_gamma", lambda case, rates_rows=None: [1.02 ** k for k in range(30)])


@pytest.fixture
def vt(monkeypatch):
    monkeypatch.syspath_prepend(str(UI_DIR))
    import variant_tables

    return variant_tables


def _edited(df, added_rows):
    """The DataFrame the data editor returns after the user added `added_rows`."""
    schema = determine_dataframe_schema(df, pa.Schema.from_pandas(df))
    de._apply_dataframe_edits(df, {"edited_rows": {}, "deleted_rows": [], "added_rows": added_rows}, schema)
    return df


def _scenario():
    return {"schema_version": 2, "plan_year": 2026,
            "case": {"basic_info": {"names": ["Ari", "Noa"], "date_of_birth": ["1964-04-17", "1964-12-09"],
                                    "life_expectancy": [89, 89], "start_date": "2026-01-01",
                                    "locality": "Yonkers",
                                    "school_district": "City of Yonkers / Yonkers"},
                     "fixed_income": {"social_security_ages": [67.0, 67.0]},
                     "solver_options": {"withSSAges": "optimize"}},
            "hfp": {}, "events": [json.loads(json.dumps(YONKERS))]}


def _dims(vt, places=None, fins=None):
    return vt.dimensions(["Ari", "Noa"], "", places if places is not None else vt.places_table(),
                         fins if fins is not None else vt.financing_table(), "(none)", "", {})


def _budget(hfp):
    table = hfp["Budget"]
    i_name, i_amount = table["columns"].index("name"), table["columns"].index("amount")
    return {row[i_name]: row[i_amount] for row in table["rows"]}


class TestEmptyCellsKeepTheParents:
    def test_the_editor_returns_none_for_an_untouched_cell(self, vt):
        # The premise: Streamlit's own code leaves an untouched cell None (iterrows made it NaN).
        df = _edited(vt.places_table(), [{"label": "wp", "move": True}])
        assert df.iloc[0]["locality"] is None
        assert vt.records(df)[0]["locality"] is None

    def test_ad1_empty_costs_keep_the_parent_s_and_reach_the_budget(self, vt, flat_gamma):
        # The review's probe: White Plains typed except the costs. The costs used to be NaN,
        # stored as None, and read as $0 by the plan; they now keep Yonkers' amounts.
        places = _edited(vt.places_table(), [
            {"label": "whiteplains", "name": "whiteplains condo", "price": "700000", "state": "NY",
             "locality": "-", "school_district": "City of White Plains / White Plains", "move": True}])
        dims, skipped = _dims(vt, places=places)
        assert skipped == []
        [value] = dims["place"]
        assert "costs" not in value
        assert value["place"] == {"state": "NY", "locality": "",
                                  "school_district": "City of White Plains / White Plains", "move": True}
        [child] = variants.plan_variants(_scenario(), dims)
        buy = next(e for e in child.scenario["events"] if e["kind"] == "purchase")
        assert buy["costs"] == {"property tax": 9500, "hoa": 9600, "insurance": 900}
        case, hfp, _ = build(child.scenario)
        budget = _budget(hfp)
        assert budget["HOA"] > 0 and budget["property tax"] > 0 and budget["condo insurance"] > 0
        # "-" cleared the parent's Yonkers locality in the move (White Plains has no local tax).
        assert case["basic_info"]["moves"][0]["locality"] == ""

    def test_ad1_one_cost_typed_changes_that_cost_only(self, vt):
        places = _edited(vt.places_table(), [{"label": "wp", "property tax": "11500"}])
        dims, _ = _dims(vt, places=places)
        assert dims["place"] == [{"label": "wp", "costs": {"property tax": 11500.0}}]

    def test_ad1_an_empty_price_keeps_the_parent_s(self, vt):
        places = _edited(vt.places_table(), [{"label": "wp", "name": "wp condo"}])
        dims, _ = _dims(vt, places=places)
        [child] = variants.plan_variants(_scenario(), dims)
        assert next(e for e in child.scenario["events"] if e["kind"] == "purchase")["price"] == 700000

    def test_ad1_a_loan_with_term_and_rate_builds_with_the_defaults(self, vt, flat_gamma):
        fins = _edited(vt.financing_table(), [{"label": "mortgage", "kind": "loan", "term": "30", "rate": "5.9"}])
        dims, _ = _dims(vt, fins=fins)
        assert dims["financing"] == [{"label": "mortgage",
                                      "financing": {"kind": "loan", "term": 30.0, "rate": 5.9}}]
        [child] = variants.plan_variants(_scenario(), dims)
        _case, hfp, _ = build(child.scenario)  # used to raise "cannot convert float NaN to integer"
        debts = hfp["Debts"]
        [row] = debts["rows"]
        assert row[debts["columns"].index("name")] == "yonkers condo mortgage"  # not "nan"
        amount = row[debts["columns"].index("amount")]
        assert math.isfinite(amount) and amount > 0

    def test_ad1_a_row_with_no_label_is_skipped_and_named(self, vt):
        places = _edited(vt.places_table(), [{"price": "700000"}])
        dims, skipped = _dims(vt, places=places)
        assert "place" not in dims and skipped == ["a place row with no label"]

    def test_a_bad_cell_is_a_scenario_error(self, vt):
        places = _edited(vt.places_table(), [{"label": "wp", "hoa": "lots"}])
        with pytest.raises(ScenarioError, match="hoa"):
            _dims(vt, places=places)


class TestMoveAndKind:
    @pytest.mark.parametrize("typed,expected", [(True, True), (False, False), ("False", False),
                                                ("no", False), ("0", False), ("yes", True), ("1", True)])
    def test_ad6_move_reads_true_and_false(self, vt, typed, expected):
        places = _edited(vt.places_table(), [{"label": "wp", "move": typed}])
        dims, _ = _dims(vt, places=places)
        assert dims["place"][0]["place"]["move"] is expected

    def test_ad6_a_move_that_is_not_true_or_false_is_refused(self, vt):
        places = _edited(vt.places_table(), [{"label": "wp", "move": "maybe"}])
        with pytest.raises(ScenarioError, match="move"):
            _dims(vt, places=places)

    def test_a_kind_that_is_not_cash_or_loan_is_refused(self, vt):
        # "laon" used to become cash silently.
        fins = _edited(vt.financing_table(), [{"label": "m", "kind": "laon", "term": "30", "rate": "5.9"}])
        with pytest.raises(ScenarioError, match="kind"):
            _dims(vt, fins=fins)


class TestGridLayout:
    def test_ad2_the_condo_grid_places_every_dimension(self, vt):
        assert vt.grid_layout(["financing", "place", "year"]) == (["place", "financing"], ["year"])

    def test_ad2_one_dimension_is_one_row(self, vt):
        assert vt.grid_layout(["year"]) == ([], ["year"])
        assert vt.grid_layout(["claim"]) == ([], ["claim"])

    def test_without_a_year_the_last_dimension_is_the_columns(self, vt):
        assert vt.grid_layout(["claim", "place"]) == (["place"], ["claim"])

    def test_a_saved_layout_is_used_as_saved(self, vt):
        saved = {"rows": [], "columns": ["year"]}
        assert vt.grid_layout(["place", "year"], saved) == ([], ["year"])
        saved = {"rows": ["year", "place"], "columns": ["year"]}
        assert vt.grid_layout(["place", "year"], saved) == (["place"], ["year"])

    def test_a_saved_layout_without_columns_falls_back(self, vt):
        assert vt.grid_layout(["place", "year"], {"rows": ["place"], "columns": []}) == (["place"], ["year"])


class TestDeathAndSequence:
    """The I2/I11 editors (first death ages; the downturn-sequence table)."""

    def _dims(self, vt, **kw):
        return vt.dimensions(["Ari", "Noa"], "", vt.places_table(), vt.financing_table(),
                             "(none)", "", {}, kw.get("death_person", "(none)"),
                             kw.get("death_ages", ""), kw.get("seqs"))

    def test_the_death_fields_give_one_value_per_age(self, vt):
        dims, skipped = self._dims(vt, death_person="Ari", death_ages="75, 80, 85")
        assert dims == {"death": [{"person": "Ari", "age": 75}, {"person": "Ari", "age": 80},
                                  {"person": "Ari", "age": 85}]}
        assert skipped == []

    def test_death_ages_with_no_person_are_ignored(self, vt):
        dims, _ = self._dims(vt, death_person="(none)", death_ages="75")
        assert "death" not in dims

    @pytest.mark.parametrize("text", ["75.5", "75x"])
    def test_a_death_age_that_is_not_a_whole_year_is_refused(self, vt, text):
        with pytest.raises(ScenarioError, match="death ages"):
            self._dims(vt, death_person="Ari", death_ages=text)

    def test_the_sequences_table_gives_one_value_per_row(self, vt):
        seqs = _edited(vt.sequences_table(), [
            {"label": "crash at retirement", "sequence": "crash-30", "start": "after:Ari"},
            {"sequence": "poor-decade", "start": "2029"}])
        dims, skipped = self._dims(vt, seqs=seqs)
        assert dims["sequence"] == [
            {"label": "crash at retirement", "sequence": "crash-30", "start": "after:Ari"},
            {"sequence": "poor-decade", "start": "2029"}]
        assert skipped == []

    @pytest.mark.parametrize("typed", ["-", "none", "No downturn", None])
    def test_a_cleared_sequence_cell_is_the_no_downturn_value(self, vt, typed):
        row = {"label": "baseline"} if typed is None else {"label": "baseline", "sequence": typed}
        seqs = _edited(vt.sequences_table(), [row])
        dims, _ = self._dims(vt, seqs=seqs)
        assert dims["sequence"] == [{"label": "baseline", "sequence": None}]

    def test_a_sequence_row_without_a_placement_is_refused(self, vt):
        seqs = _edited(vt.sequences_table(), [{"sequence": "crash-30"}])
        with pytest.raises(ScenarioError, match="placement"):
            self._dims(vt, seqs=seqs)

    def test_a_placement_without_a_sequence_is_refused(self, vt):
        seqs = _edited(vt.sequences_table(), [{"start": "2029"}])
        with pytest.raises(ScenarioError, match="names no sequence"):
            self._dims(vt, seqs=seqs)

    def test_an_empty_row_is_skipped_silently(self, vt):
        seqs = _edited(vt.sequences_table(), [{}])
        dims, skipped = self._dims(vt, seqs=seqs)
        assert "sequence" not in dims and skipped == []


class TestMemberValues:
    """A hand-added member's values (the grid places a member through them, however they
    were set)."""

    def test_pairs_are_read_with_the_year_as_a_year(self, vt):
        assert vt.member_values("year: 2027; place: yonkers") == {"year": 2027, "place": "yonkers"}
        assert vt.member_values("year: 2027\nplace: yonkers") == {"year": 2027, "place": "yonkers"}
        assert vt.member_values("claim: Ari 67y0m / Noa 70y0m") == \
            {"claim": "Ari 67y0m / Noa 70y0m"}
        assert vt.member_values("") == {} and vt.member_values(None) == {}

    @pytest.mark.parametrize("text", ["yonkers", "year:", ": 2027"])
    def test_a_part_that_is_not_a_pair_is_refused(self, vt, text):
        with pytest.raises(ScenarioError, match="pair"):
            vt.member_values(text)

    def test_the_year_label_must_be_one_year(self, vt):
        with pytest.raises(ScenarioError, match="one calendar year"):
            vt.member_values("year: 2027, 2029")
        with pytest.raises(ScenarioError, match="years"):
            vt.member_values("year: soon")

    def test_an_unknown_dimension_is_refused(self, vt):
        # AD6's rule: a typo is refused, not stored as a phantom grid dimension (review AE2).
        with pytest.raises(ScenarioError, match="not one of the dimensions"):
            vt.member_values("yaer: 2027; place: yonkers")

    def test_values_text_round_trips(self, vt):
        values = {"year": 2027, "place": "yonkers"}
        assert vt.member_values(vt.values_text(values)) == values
        assert vt.values_text({}) == ""

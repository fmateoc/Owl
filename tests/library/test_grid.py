"""The grid view and the leads (design section 9.3, step 6): `library.grid`.

The cells follow `run_suite.py`'s `condo_pivot` (the score's difference from the reference
and the home at the end), coloured by the comparison rule (R3, `compare`). These tests pin
the layout and the judgments on crafted results; the numbers at scale are checked by
`fork-notes/synthetic/check_library_variants.py`."""

import json
from pathlib import Path

import pytest

from owlplanner.library import view
from owlplanner.library.grid import Entry, front, grid_view, latest_result, lead_between

# A local-search solve: the noise rule is the 1% band of the reference's score (R2).
REF_SCORE, REF_HOME = 100_000.0, 400_000.0


def _result(score_value=REF_SCORE, home=REF_HOME, savings=0.0, method="local search",
            finished="2026-01-01T00:00:00", gap=None):
    record = {"status": "solved", "preset": "decision", "gap": gap,
              "method": {"breakpoint_method": method, "options": {}, "objective": "maxSpending"},
              "convergence": {"objective_error_bar_today_dollars": 0.0},
              "solve_date": {"finished": finished}}
    summary = {"discretionary_year1": score_value,
               "final_bequest_today": home + savings,
               "final_bequest_savings_today": savings}
    plan = {"objective": "maxSpending", "by_year": []}
    return view.Result(results_id="r", results_dir=Path("."), record=record,
                       summary=summary, plan=plan)


def _entry(run_id, values, result=None):
    return Entry(run_id=run_id, name=run_id, values=values, result=result)


def _grid_entries():
    """The condo grid's shape (run_suite's `condo_pivot`): a place and financing per row,
    the purchase year as columns. A later purchase buys more spending with less home; the
    Queens condo keeps far more home and spends less (R3's trade-off)."""
    return [
        _entry("ref", {"place": "yonkers", "year": 2027, "financing": "cash"}, _result()),
        _entry("yonkers-2029-cash", {"place": "yonkers", "year": 2029, "financing": "cash"},
               _result(score_value=REF_SCORE + 4_000.0, home=380_000.0)),
        _entry("yonkers-2031-cash", {"place": "yonkers", "year": 2031, "financing": "cash"},
               _result(score_value=REF_SCORE - 20_000.0, home=380_000.0)),
        _entry("queens-2027-cash", {"place": "queens", "year": 2027, "financing": "cash"},
               _result(score_value=REF_SCORE - 10_000.0, home=600_000.0)),
        _entry("queens-2029-cash", {"place": "queens", "year": 2029, "financing": "cash"},
               _result(score_value=REF_SCORE - 6_000.0, home=590_000.0)),
        _entry("queens-2031-cash", {"place": "queens", "year": 2031, "financing": "cash"},
               _result(score_value=REF_SCORE - 30_000.0, home=580_000.0)),
    ]


class TestLayout:
    def test_rows_are_place_and_financing_and_columns_the_year(self):
        grid = grid_view(_grid_entries(), reference="ref")
        assert grid.row_dims == ("place", "financing") and grid.col_dims == ("year",)
        assert grid.col_keys == ((2027,), (2029,), (2031,))
        assert [key for key, _ in grid.rows] == [("queens", "cash"), ("yonkers", "cash")]
        assert grid.unplaced == ()

    def test_the_cell_is_the_score_s_difference_and_the_home(self):
        grid = grid_view(_grid_entries(), reference="ref")
        row = dict(grid.rows)[("yonkers", "cash")]
        cell = row[(2029,)]
        assert cell.delta == 4_000.0
        assert cell.home == 380_000.0 and cell.home_delta == -20_000.0
        assert cell.verdict == "resolved"  # 4,000 > 1% of 100,000
        assert cell.lead["verdict"] == "trade-off"  # more spending, less home (R3)
        ref_cell = row[(2027,)]
        assert ref_cell.delta is None and ref_cell.entry.run_id == "ref"

    def test_a_small_difference_is_within_noise(self):
        entries = [
            _entry("ref", {"place": "yonkers", "year": 2027, "financing": "cash"}, _result()),
            _entry("small", {"place": "yonkers", "year": 2029, "financing": "cash"},
                   _result(score_value=REF_SCORE + 500.0, home=REF_HOME)),
        ]
        cell = dict(grid_view(entries, reference="ref").rows)[("yonkers", "cash")][(2029,)]
        assert cell.delta == 500.0 and cell.verdict == "within noise"

    def test_the_best_score_in_a_row_is_marked_by_score_only(self):
        grid = grid_view(_grid_entries(), reference="ref")
        for key, expected in ((("queens", "cash"), (2029,)), (("yonkers", "cash"), (2029,))):
            row = dict(grid.rows)[key]
            assert [col for col, cell in row.items() if cell.best] == [expected]

    def test_a_member_with_no_values_is_listed_not_placed(self):
        entries = _grid_entries() + [_entry("draft", {}, None)]
        grid = grid_view(entries, reference="ref")
        assert [e.run_id for e in grid.unplaced] == ["draft"]

    def test_a_missing_value_sits_in_its_dimension_s_none_bucket(self):
        entries = [_entry("ref", {"place": "yonkers", "year": 2027, "financing": "cash"}, _result()),
                   _entry("year only", {"year": 2029}, _result(score_value=REF_SCORE + 4_000.0))]
        grid = grid_view(entries, reference="ref")
        assert [key for key, _ in grid.rows] == [("yonkers", "cash"), (None, None)]
        assert dict(grid.rows)[(None, None)][(2029,)].delta == 4_000.0

    def test_ac4_two_members_with_the_same_values_never_vanish(self):
        # Review AC4: a second member with the very same values used to lose the cell to the
        # first and disappear from the pivot entirely (no cell, not even `unplaced`).
        entries = _grid_entries() + [
            _entry("dup", {"place": "yonkers", "year": 2029, "financing": "cash"},
                   _result(score_value=REF_SCORE + 30_000.0, home=REF_HOME))]
        grid = grid_view(entries, reference="ref")
        shown = {cell.entry.run_id for _, row in grid.rows
                 for cell in row.values() if cell is not None}
        assert "dup" not in shown  # one member per cell...
        assert [(e.run_id, s.run_id) for e, s in grid.collided] == [("dup", "yonkers-2029-cash")]
        # ...and the star marks the cell that holds the row's best score, here the
        # collided member's (130,000 over the shown cell's 104,000).
        row = dict(grid.rows)[("yonkers", "cash")]
        assert [col for col, cell in row.items() if cell.best] == [(2029,)]
        assert row[(2029,)].entry.run_id == "yonkers-2029-cash"

    def test_the_reference_must_be_one_of_the_entries(self):
        with pytest.raises(ValueError, match="reference"):
            grid_view(_grid_entries(), reference="nope")


class TestLeads:
    def test_more_spending_but_less_home_is_a_trade_off(self):
        ref = _entry("ref", {"year": 2027}, _result())
        other = _entry("other", {"year": 2029}, _result(score_value=REF_SCORE + 20_000.0,
                                                        home=REF_HOME - 50_000.0))
        assert lead_between(ref, other)["verdict"] == "trade-off"

    def test_better_on_both_leads(self):
        ref = _entry("ref", {"year": 2027}, _result())
        other = _entry("other", {"year": 2029}, _result(score_value=REF_SCORE + 20_000.0,
                                                        home=REF_HOME + 1.0))
        assert lead_between(ref, other)["verdict"] == "the second result leads"
        assert lead_between(other, ref)["verdict"] == "the first result leads"

    def test_the_front_holds_the_unbeaten_trade_offs(self):
        leaders = front(_grid_entries(), reference="ref")
        names = {d["entry"].name for d in leaders}
        # The four trade-off points; the two that are beaten on both numbers drop out.
        assert names == {"ref", "yonkers-2029-cash", "queens-2027-cash", "queens-2029-cash"}
        by_name = {d["entry"].name: d for d in leaders}
        assert "yonkers-2031-cash" in by_name["yonkers-2029-cash"]["leads"]
        assert by_name["yonkers-2029-cash"]["vs_reference"].verdict == "resolved"

    def test_nothing_solved_is_no_front(self):
        assert front([_entry("a", {"year": 2027}, None)]) == []


class TestLatestResult:
    def test_the_newest_solved_one_and_the_exact_companion_only_when_asked(self, tmp_path):
        results = tmp_path / "results"
        for stamp, exact in (("2026-01-01T00-00-00_decision", False),
                             ("2026-01-02T00-00-00_decision_exact", True),
                             ("2026-01-03T00-00-00_quick", False)):
            folder = results / stamp
            folder.mkdir(parents=True)
            options = {"withSSTaxability": 0.85, "withMedicare": "none", "withLTCG": "optimize",
                       "breakpointMethod": "loop"} if exact else {}
            (folder / "record.json").write_text(json.dumps({
                "status": "solved", "preset": "decision" if "decision" in stamp else "quick",
                "method": {"breakpoint_method": "loop", "options": options},
            }), encoding="utf-8")
            (folder / "summary.json").write_text('{"spending_basis": 1}', encoding="utf-8")
            (folder / "plan.json").write_text('{"objective": "maxSpending"}', encoding="utf-8")
        assert latest_result(tmp_path).results_id == "2026-01-03T00-00-00_quick"
        assert latest_result(tmp_path, prefer_exact=True).results_id == "2026-01-02T00-00-00_decision_exact"

    def test_a_run_with_no_solved_result_has_none(self, tmp_path):
        assert latest_result(tmp_path) is None

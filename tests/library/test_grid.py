"""The grid view and the leads (design section 9.3, step 6): `library.grid`.

The cells follow `run_suite.py`'s `condo_pivot` (the score's difference from the reference
and the home at the end), coloured by the comparison rule (R3, `compare`). These tests pin
the layout and the judgments on crafted results; the numbers at scale are checked by
`fork-notes/synthetic/check_library_variants.py`."""

import json
from pathlib import Path

import pytest

from owlplanner.library import view
from owlplanner.library.grid import Entry, front, grid_view, latest_result, lead_between, member_results

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
        # ...and the star goes to the best member itself (review AD3): the collided one
        # scores 130,000 over the shown cell's 104,000, so no cell of the row is starred (the
        # star used to sit on the shown cell's +4,000) and the member is named beside the grid.
        row = dict(grid.rows)[("yonkers", "cash")]
        assert [col for col, cell in row.items() if cell is not None and cell.best] == []
        assert grid.best_beside == ("dup",)

    def test_ad3_a_shown_best_member_keeps_its_star(self):
        grid = grid_view(_grid_entries(), reference="ref")
        row = dict(grid.rows)[("yonkers", "cash")]
        assert [col for col, cell in row.items() if cell is not None and cell.best] == [(2029,)]
        assert grid.best_beside == ()

    def test_no_row_dimension_is_one_row(self):
        # AD2: a layout with columns only (rows []) is one row, not a fallback dimension.
        grid = grid_view(_grid_entries(), reference="ref", row_dims=(), col_dims=("year",))
        assert [key for key, _ in grid.rows] == [()]

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


class TestMemberResults:
    """Review AG5: one model for a whole collection -- the exact-LP results when a member
    has nothing else (the tornado's children), the headline results otherwise."""

    @staticmethod
    def _write(path, stamp, exact):
        folder = path / "results" / stamp
        folder.mkdir(parents=True)
        options = {"withSSTaxability": 0.85, "withMedicare": "none", "withLTCG": "optimize",
                   "breakpointMethod": "loop"} if exact else {}
        (folder / "record.json").write_text(json.dumps({
            "status": "solved", "preset": "decision_exact" if exact else "decision",
            "method": {"breakpoint_method": "loop", "options": options},
        }), encoding="utf-8")
        (folder / "summary.json").write_text('{"spending_basis": 1}', encoding="utf-8")
        (folder / "plan.json").write_text('{"objective": "maxSpending"}', encoding="utf-8")

    def test_a_member_with_only_an_exact_result_puts_the_grid_on_the_exact_lp(self, tmp_path):
        parent, child = tmp_path / "parent", tmp_path / "child"
        self._write(parent, "2026-01-01T00-00-00_decision", exact=False)
        self._write(parent, "2026-01-01T00-00-01_decision_exact", exact=True)
        self._write(child, "2026-01-01T00-00-02_decision_exact", exact=True)
        results, exact = member_results([parent, child])
        assert exact is True
        assert results[parent].results_id.endswith("_decision_exact")
        assert results[child].results_id.endswith("_decision_exact")

    def test_headline_results_when_every_member_has_one(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        self._write(a, "2026-01-01T00-00-00_decision", exact=False)
        self._write(a, "2026-01-01T00-00-01_decision_exact", exact=True)
        self._write(b, "2026-01-01T00-00-02_decision", exact=False)
        results, exact = member_results([a, b])
        assert exact is False
        assert results[a].results_id.endswith("_decision")
        assert results[b].results_id.endswith("_decision")


class TestMemberResultsAH5:
    """Review AH5: only a member whose every solve is exact-LP (the tornado's children) puts
    the collection on the exact LP; a "decision" member whose local search is running or
    failed beside a solved exact companion shows as unsolved instead."""

    @staticmethod
    def _decision_member(path, i):
        TestMemberResults._write(path, f"2026-01-01T00-00-0{i}_decision", exact=False)
        TestMemberResults._write(path, f"2026-01-01T00-00-0{i + 1}_decision_exact", exact=True)

    def test_a_failed_local_search_does_not_switch_the_collection(self, tmp_path):
        a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
        self._decision_member(a, 0)
        self._decision_member(b, 2)
        TestMemberResults._write(c, "2026-01-01T00-00-06_decision_exact", exact=True)
        failed = c / "results" / "2026-01-01T00-00-05_decision"
        failed.mkdir()
        (failed / "record.json").write_text(json.dumps({"status": "failed", "preset": "decision"}),
                                            encoding="utf-8")
        results, exact = member_results([a, b, c])
        assert exact is False
        assert results[a].results_id.endswith("_decision") and results[c] is None

    def test_a_running_local_search_does_not_switch_it_either(self, tmp_path):
        a, c = tmp_path / "a", tmp_path / "c"
        self._decision_member(a, 0)
        TestMemberResults._write(c, "2026-01-01T00-00-06_decision_exact", exact=True)
        running = c / "results" / "2026-01-01T00-00-05_decision"
        running.mkdir()  # queued or running: a job record, no record.json yet
        (running / "status.json").write_text(json.dumps({"state": "running", "preset": "decision"}),
                                             encoding="utf-8")
        results, exact = member_results([a, c])
        assert exact is False and results[c] is None


class TestClaimingAgesFlag:
    """Review AD5: a cell solved at other claiming ages than the reference's is flagged."""

    @staticmethod
    def _aged(result, ages):
        result.plan["individuals"] = ["Ari", "Noa"]
        result.plan["claiming_ages"] = ages
        return result

    def test_a_cell_at_other_ages_is_flagged(self):
        ref = _entry("ref", {"year": 2027}, self._aged(_result(), [70.0, 70.0]))
        same = _entry("same", {"year": 2029}, self._aged(_result(), [70.0, 70.0]))
        other = _entry("other", {"year": 2031}, self._aged(_result(), [67.0, 70.0]))
        grid = grid_view([ref, same, other], reference="ref", row_dims=(), col_dims=("year",))
        [flag] = [f for f in grid.flags if "claiming ages" in f]
        assert "1 cell(s)" in flag and "other (Ari 67y0m, Noa 70y0m)" in flag
        assert "same" not in flag.split(":", 1)[1]

    def test_a_claim_variant_is_not_flagged(self):
        # Where the claiming ages are the varied dimension, they are the question.
        ref = _entry("ref", {"claim": "Ari 70y0m"}, self._aged(_result(), [70.0, 70.0]))
        other = _entry("other", {"claim": "Ari 67y0m"}, self._aged(_result(), [67.0, 70.0]))
        grid = grid_view([ref, other], reference="ref", row_dims=(), col_dims=("claim",))
        assert not [f for f in grid.flags if "claiming ages" in f]

    def test_the_same_month_is_the_same_age(self):
        ref = _entry("ref", {"year": 2027}, self._aged(_result(), [67.8333, 70.0]))
        other = _entry("other", {"year": 2029}, self._aged(_result(), [67.83333333, 70.0]))
        grid = grid_view([ref, other], reference="ref", row_dims=(), col_dims=("year",))
        assert not [f for f in grid.flags if "claiming ages" in f]


class TestReview5Folds:
    """`fork-notes/run-library-step6-review-5.md` AJ1 (a model companion is never a run's
    headline) and AJ3 (under maxBequest the cells, the star and the front read the savings
    left, not the score, which there holds the home)."""

    @staticmethod
    def _write(path, stamp, preset, medicare="none"):
        folder = path / "results" / stamp
        folder.mkdir(parents=True)
        options = ({"withSSTaxability": 0.85, "withMedicare": medicare, "withLTCG": "optimize",
                    "breakpointMethod": "loop"} if preset in ("decision_exact", "exact_medicare") else {})
        (folder / "record.json").write_text(json.dumps({
            "status": "solved", "preset": preset,
            "method": {"breakpoint_method": "loop", "options": options},
        }), encoding="utf-8")
        (folder / "summary.json").write_text('{"spending_basis": 1}', encoding="utf-8")
        (folder / "plan.json").write_text('{"objective": "maxSpending"}', encoding="utf-8")

    def test_aj1_the_medicare_companion_is_not_the_headline(self, tmp_path):
        """The tornado queues the run's own `exact_medicare` base: as the newest non-exact-LP
        result it used to become the run's headline (SS pinned at 0.85)."""
        self._write(tmp_path, "2026-01-01T00-00-00_decision", "decision")
        self._write(tmp_path, "2026-01-01T00-00-01_decision_exact", "decision_exact")
        self._write(tmp_path, "2026-01-01T00-00-02_exact_medicare", "exact_medicare", "optimize")
        assert latest_result(tmp_path).results_id.endswith("_decision")
        assert latest_result(tmp_path, prefer_exact=True).results_id.endswith("_decision_exact")
        assert latest_result(tmp_path, companion="exact_medicare").results_id.endswith("_exact_medicare")
        record = json.loads((tmp_path / "results" / "2026-01-01T00-00-02_exact_medicare"
                             / "record.json").read_text(encoding="utf-8"))
        assert view.record_companion(record) == "exact_medicare"
        assert not view.record_is_exact_lp(record)  # the agreement check reads the exact LP only

    def test_aj1_the_medical_child_keeps_the_collection_on_the_exact_lp(self, tmp_path):
        parent, child, medical = tmp_path / "parent", tmp_path / "child", tmp_path / "medical"
        self._write(parent, "2026-01-01T00-00-00_decision", "decision")
        self._write(parent, "2026-01-01T00-00-01_decision_exact", "decision_exact")
        self._write(parent, "2026-01-01T00-00-02_exact_medicare", "exact_medicare", "optimize")
        self._write(child, "2026-01-01T00-00-03_decision_exact", "decision_exact")
        self._write(medical, "2026-01-01T00-00-04_exact_medicare", "exact_medicare", "optimize")
        results, exact = member_results([parent, child, medical])
        assert exact is True
        assert results[parent].results_id.endswith("_decision_exact")
        assert results[medical] is None  # no exact-LP result: its bar is on the Run page

    @staticmethod
    def _bequest(savings, home):
        result = _result(home=home, savings=savings)
        result.plan["objective"] = "maxBequest"
        result.record["method"]["objective"] = "maxBequest"
        return result

    def test_aj3_under_max_bequest_the_cell_and_the_star_read_the_savings_left(self):
        ref = _entry("ref", {"mover": "none"}, self._bequest(1_043_946.0, 760_861.0))
        condo = _entry("condo", {"mover": "condo"}, self._bequest(870_038.0, 836_947.0))
        grid = grid_view([ref, condo], reference="ref", row_dims=(), col_dims=("mover",))
        cell = dict(grid.rows)[()][("condo",)]
        assert cell.delta == pytest.approx(-173_908.0)  # not -97,822, savings + home
        assert cell.home_delta == pytest.approx(76_086.0)
        # The star reads the savings left: the reference leaves more savings (1,043,946 against
        # 900,000) and the other the larger final bequest (2,400,000 against 1,804,807).
        rich_home = _entry("home", {"mover": "home"}, self._bequest(900_000.0, 1_500_000.0))
        grid = grid_view([ref, rich_home], reference="ref", row_dims=(), col_dims=("mover",))
        row = dict(grid.rows)[()]
        assert row[("none",)].best and not row[("home",)].best  # 1,043,946 > 900,000 savings
        item = next(i for i in front([ref, rich_home], reference="ref") if i["entry"].run_id == "home")
        assert item["first"] == pytest.approx(900_000.0)
        assert item["vs_reference"].delta == pytest.approx(-143_946.0)

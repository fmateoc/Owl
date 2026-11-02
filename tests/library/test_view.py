"""One result as the pages show it (design 9.1): the score rule of run_suite.py, the two
end-of-plan numbers, the quality line, and the method's noise tolerance (R2)."""

from pathlib import Path

from owlplanner.library import results as R
from owlplanner.library.view import (
    Result,
    age_text,
    claiming_ages,
    claiming_ages_text,
    error_bar,
    home_at_end,
    is_exact_lp,
    load_result,
    method_kind,
    method_text,
    quality_line,
    quality_notes,
    savings_left,
    score,
    score_label,
    ss_withheld_today,
    tolerance,
    total_taxes_today,
)

BASE_SUMMARY = {
    "spending_basis": 100_000.0,
    "discretionary_year1": 82_000.0,
    "essential_year1": 18_000.0,
    "final_bequest_today": 500_000.0,
    "final_bequest_savings_today": 350_000.0,
    "federal_income_tax_today": 120_000.0,
    "ltcg_tax_today": 10_000.0,
    "niit_today": 2_000.0,
    "payroll_tax_today": 3_000.0,
    "state_tax_today": 45_000.0,
    "ss_withheld_today": 7_000.0,
}

BASE_PLAN = {
    "objective": "maxSpending",
    "individuals": ["Noa", "Avi"],
    "claiming_ages": [66.1667, 70.0],
    "by_year": [],
}


def make_result(*, summary=None, plan=None, record=None, results_id="2026-11-02T10-00-00_decision"):
    rec = {
        "record_format": R.RECORD_FORMAT,
        "status": "solved",
        "preset": "decision",
        "method": {"objective": "maxSpending", "breakpoint_method": "local search (5 rounds)",
                   "options": {"breakpointMethod": "local-search", "withSSAges": "fixed"}},
        "engine": {"version": "2026.11.2", "commit": "abcdef1"},
        "solve_date": {"started": "2026-11-02T10:00:00+01:00", "finished": "2026-11-02T10:05:00+01:00"},
        "gap": -1.0,
        "convergence": {"convergence": "monotonic", "objective_error_bar_today_dollars": 0.0},
        "warnings": [],
    }
    rec.update(record or {})
    return Result(
        results_id=results_id,
        results_dir=Path("runs/x/results") / results_id,
        record=rec,
        summary=dict(BASE_SUMMARY if summary is None else summary),
        plan=dict(BASE_PLAN if plan is None else plan),
    )


class TestLoadResult:
    def test_reads_the_three_durable_files_and_fails_soft(self, tmp_path):
        (tmp_path / R.RECORD_JSON).write_text('{"status": "solved"}', encoding="utf-8")
        (tmp_path / R.SUMMARY_JSON).write_text('{"spending_basis": 1.0}', encoding="utf-8")
        (tmp_path / R.PLAN_JSON).write_text("not json", encoding="utf-8")
        result = load_result(tmp_path)
        assert result.record["status"] == "solved"
        assert result.summary == {"spending_basis": 1.0}
        assert result.plan == {} and not result.solved  # no plan.json: nothing to show

    def test_a_solved_result_needs_record_and_plan(self, tmp_path):
        (tmp_path / R.RECORD_JSON).write_text('{"status": "solved"}', encoding="utf-8")
        (tmp_path / R.PLAN_JSON).write_text('{"objective": "maxSpending"}', encoding="utf-8")
        assert load_result(tmp_path).solved


class TestTheScore:
    def test_essential_lines_score_the_first_year_s_discretionary_spending(self):
        result = make_result()
        assert score(result) == 82_000.0
        assert "discretionary" in score_label(result)

    def test_without_essential_lines_it_is_the_spending_basis(self):
        summary = dict(BASE_SUMMARY)
        summary.pop("discretionary_year1")
        summary.pop("essential_year1")
        assert score(make_result(summary=summary)) == 100_000.0
        assert "spending basis" in score_label(make_result(summary=summary))

    def test_maxbequest_scores_the_final_bequest(self):
        result = make_result(plan={"objective": "maxBequest"})
        assert score(result) == 500_000.0
        assert "bequest" in score_label(result)

    def test_an_unsolved_result_has_no_numbers(self):
        result = make_result(record={"status": "failed"})
        assert score(result) is None and home_at_end(result) is None
        assert savings_left(result) is None and total_taxes_today(result) is None


class TestTheTwoEndNumbers:
    def test_home_at_end_is_the_bequest_less_the_savings_part(self):
        result = make_result()
        assert home_at_end(result) == 150_000.0
        assert savings_left(result) == 350_000.0

    def test_total_taxes_sum_every_kind(self):
        assert total_taxes_today(make_result()) == 180_000.0

    def test_ss_withheld(self):
        assert ss_withheld_today(make_result()) == 7_000.0


class TestClaimingAges:
    def test_ages_travel_with_the_plan_json(self):
        result = make_result()
        assert claiming_ages(result) == [("Noa", 66.1667), ("Avi", 70.0)]
        assert claiming_ages_text(result) == "Noa 66y2m, Avi 70y0m"

    def test_age_text_uses_years_and_months(self):
        assert age_text(70.0) == "70y0m"
        assert age_text(62.5) == "62y6m"


class TestQuality:
    def test_a_settled_loop_says_settled(self):
        assert quality_notes(make_result()) == []
        assert quality_line(make_result()) == "settled"

    def test_an_unsettled_loop_warns_that_small_differences_mean_nothing(self):
        result = make_result(record={"convergence": {"convergence": "oscillatory",
                                                     "objective_error_bar_today_dollars": 2782.0}})
        assert error_bar(result) == 2782.0
        assert "did not settle" in quality_line(result)
        assert "under 1%" in quality_line(result)

    def test_an_early_stop_is_reported(self):
        result = make_result(record={"convergence": {"convergence": "max iteration"}})
        assert any("stopped early" in n for n in quality_notes(result))

    def test_cash_flow_warnings_are_reported(self):
        result = make_result(record={"warnings": ["Cash flow balance off by $3",
                                                  "an ordinary message"]})
        assert len(quality_notes(result)) == 1

    def test_a_failed_result_says_so(self):
        result = make_result(record={"status": "refused", "error": "outside its plan year"})
        assert "not solved: refused" in quality_notes(result)[0]
        assert "outside its plan year" in quality_notes(result)[0]


class TestMethodAndTolerance:
    def test_kinds(self):
        proved = make_result(record={"method": {"breakpoint_method": "branch-and-bound (12 nodes)"},
                                     "gap": 1e-5})
        assert method_kind(proved) == "proved"
        assert method_kind(make_result()) == "local search"
        looped = make_result(record={"method": {"breakpoint_method": "loop"}})
        assert method_kind(looped) == "loop"
        kept = make_result(record={"method": {"breakpoint_method": "local search -> loop"}})
        assert method_kind(kept) == "loop"  # the search kept the loop's plan: nothing proven
        assert method_kind(make_result(record={"status": "failed"})) == "no solve"

    def test_a_proved_plan_s_tolerance_is_gap_times_the_objective(self):
        proved = make_result(record={"method": {"breakpoint_method": "branch-and-bound"},
                                     "gap": 1e-4})
        assert tolerance(proved) == 1e-4 * 82_000.0

    def test_a_loop_or_local_search_solve_reports_no_gap(self):
        assert tolerance(make_result()) == 0.0
        proved_no_gap = make_result(record={"method": {"breakpoint_method": "branch-and-bound"},
                                            "gap": -1.0})
        assert tolerance(proved_no_gap) == 0.0

    def test_method_text_names_the_preset_the_method_and_the_commit(self):
        text = method_text(make_result())
        assert "decision" in text and "local search" in text and "abcdef1" in text


class TestIsExactLp:
    def test_the_exact_model_companion(self):
        exact = make_result(record={"method": {"breakpoint_method": "loop", "options": {
            "breakpointMethod": "loop", "withMedicare": "none", "withSSTaxability": 0.85,
            "withLTCG": "optimize"}}})
        assert is_exact_lp(exact)

    def test_everything_else_is_not(self):
        assert not is_exact_lp(make_result())
        for wrong in ({"withMedicare": "loop"}, {"withSSTaxability": 0.5},
                      {"withLTCG": "loop"}, {"breakpointMethod": "local-search"}):
            options = {"breakpointMethod": "loop", "withMedicare": "none",
                       "withSSTaxability": 0.85, "withLTCG": "optimize"}
            options.update(wrong)
            result = make_result(record={"method": {"breakpoint_method": "loop", "options": options}})
            assert not is_exact_lp(result), wrong

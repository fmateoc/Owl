"""One result as the pages show it (design 9.1): the score rule of run_suite.py, the two
end-of-plan numbers, the quality line, and the method's noise tolerance (R2)."""

from pathlib import Path

from owlplanner.library import results as R
from owlplanner.library import view
from owlplanner.library.view import (
    Result,
    age_text,
    cash_flow,
    cash_flow_year,
    claiming_ages,
    claiming_ages_text,
    error_bar,
    home_at_end,
    is_exact_lp,
    load_result,
    method_details,
    method_kind,
    method_text,
    objective_value,
    quality_line,
    quality_notes,
    savings_left,
    score,
    score_label,
    ss_withheld_today,
    threshold_band,
    thresholds,
    tolerance,
    total_taxes_today,
)

BASE_SUMMARY = {
    "spending_basis": 100_000.0,
    "spending_year1": 100_000.0,
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

    def test_a_solved_result_needs_record_plan_and_summary(self, tmp_path):
        (tmp_path / R.RECORD_JSON).write_text('{"status": "solved"}', encoding="utf-8")
        (tmp_path / R.PLAN_JSON).write_text('{"objective": "maxSpending"}', encoding="utf-8")
        assert not load_result(tmp_path).solved  # summary.json missing: no numbers (P3)
        (tmp_path / R.SUMMARY_JSON).write_text('{"spending_basis": 1.0}', encoding="utf-8")
        assert load_result(tmp_path).solved

    def test_a_missing_summary_reads_as_no_numbers_not_zeros(self):
        """P3: a record beside an empty summary is not $0 of everything judged 'resolved'."""
        result = make_result(summary={})
        assert not result.solved
        assert score(result) is None and home_at_end(result) is None
        assert total_taxes_today(result) is None and savings_left(result) is None
        assert "summary.json missing" in quality_notes(result)[0]


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

    def test_a_search_cut_by_the_clock_is_a_problem_to_read(self):
        """Performance review, 2026-11-11: `record.json` counts local search's budget cuts;
        a cut search can give another result on a busier computer, and the page says so."""
        assert quality_notes(make_result(record={"search_budget_cuts": {"solve": 0, "stages": 0}})) == []
        assert quality_notes(make_result(record={"search_budget_cuts": None})) == []  # an older record
        notes = quality_notes(make_result(record={"search_budget_cuts": {"solve": 2, "stages": 0}}))
        assert len(notes) == 1 and "time limit (2 time(s))" in notes[0] and "busier" in notes[0]
        notes = quality_notes(make_result(record={"preset": "ages",
                                                  "search_budget_cuts": {"solve": 0, "stages": 3}}))
        assert len(notes) == 1 and "claiming ages were compared" in notes[0]
        notes = quality_notes(make_result(record={"preset": "regret",
                                                  "search_budget_cuts": {"solve": 0, "stages": 1}}))
        assert len(notes) == 1 and "other solves" in notes[0]

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
        """R2's "reported gap x objective": the LP objective's value, not the score.

        Step-3 review P9: under essential lines the score is only the discretionary part of
        the objective (82,000 here), so gap x score would understate the tolerance.
        """
        proved = make_result(record={"method": {"breakpoint_method": "branch-and-bound"},
                                     "gap": 1e-4})
        assert objective_value(proved) == 100_000.0  # first-year spending under maxSpending
        assert tolerance(proved) == 1e-4 * 100_000.0
        bequest = make_result(plan={"objective": "maxBequest"},
                              record={"method": {"breakpoint_method": "branch-and-bound"},
                                      "gap": 1e-4})
        # Under maxBequest the LP maximizes the savings after the heirs' tax: not the final
        # bequest (500,000 here), which adds the home the solve does not move (review 2, Q8).
        assert objective_value(bequest) == 350_000.0
        assert tolerance(bequest) == 1e-4 * 350_000.0

    def test_a_loop_or_local_search_solve_reports_no_gap(self):
        assert tolerance(make_result()) == 0.0
        proved_no_gap = make_result(record={"method": {"breakpoint_method": "branch-and-bound"},
                                            "gap": -1.0})
        assert tolerance(proved_no_gap) == 0.0

    def test_method_text_is_plain_english_and_the_codes_are_details(self):
        """UX remediation QW-6: the header in plain English; the preset code, the binary
        families, the gap and the commit live in `method_details` (a collapsed expander on the
        run page). Second pass (review AN8): a local search is not called "exact ...
        optimization", which promised more than the comparison's 1% band grants it."""
        result = make_result(record={"method": {
            "objective": "maxSpending", "breakpoint_method": "local search (SS, IRMAA, LTCG)",
            "options": {"breakpointMethod": "local-search", "withSSAges": "fixed"}}})
        text = method_text(result)
        assert text == "Careful — taxes and premiums priced exactly, the plan found by a local search"
        assert "abcdef1" not in text and "exact tax" not in text and "optimization" not in text
        assert "(SS, IRMAA, LTCG)" not in text
        details = method_details(result)
        assert "`decision`" in details and "local search (SS, IRMAA, LTCG)" in details
        assert "abcdef1" in details and "2026.11.2" in details

    def test_the_fast_method_and_the_companions_say_what_they_are(self):
        looped = make_result(record={"method": {"breakpoint_method": "loop"}})
        assert method_text(looped) == "Careful — the fast approximate method"
        proved = make_result(record={"method": {"breakpoint_method": "branch-and-bound"},
                                     "gap": 1e-5})
        assert method_text(proved) == "Careful — taxes priced exactly, proved optimal within its gap"
        assert "branch-and-bound at gap" in method_details(proved)
        exact = make_result(record={"method": {"breakpoint_method": "loop", "options": {
            "breakpointMethod": "loop", "withMedicare": "none", "withSSTaxability": 0.85,
            "withLTCG": "optimize"}}})
        assert method_text(exact) == ("Careful: the exact-model check (a simpler model solved beside "
                                      "the Careful one, to check the order of the variants)")
        assert "exact LP" in method_details(exact)
        # Review AM4: the Medicare-priced companion's name is not said twice.
        medicare = make_result(record={"preset": "exact_medicare"})
        assert method_text(medicare) == "Exact model with Medicare priced"

    def test_every_preset_has_a_name_in_the_one_list(self):
        """Review AN8: one list of names (`presets.PRESET_NAMES`) for the method line and the
        picker, every stored preset in it."""
        from owlplanner.library.presets import PRESET_NAMES, PRESETS, SOLVE_PRESETS

        assert set(PRESETS) | set(SOLVE_PRESETS) <= set(PRESET_NAMES)


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


class TestTheRunPageBlocks:
    """"Things to look at" (I3) and the one-year cash flow (I6), read from plan.json (D7)."""

    def test_the_threshold_entries_and_their_band(self):
        plan = dict(BASE_PLAN, thresholds={
            "near_band_fraction": 0.05,
            "entries": [{"year": 2031, "kind": "irmaa", "label": "IRMAA tier 1",
                         "side": "over", "amount_today_dollars": 1_200.0,
                         "cost_today_dollars": 1_900.0, "affects": 2033,
                         "note": "the MAGI of 2031 sets the Medicare premiums of 2033"}],
        })
        result = make_result(plan=plan)
        (entry,) = thresholds(result)
        assert entry["label"] == "IRMAA tier 1"
        assert threshold_band(result) == 0.05

    def test_a_result_without_the_blocks_reads_as_empty(self):
        result = make_result()
        assert thresholds(result) == []
        assert cash_flow(result) == {}
        assert threshold_band(result) == 0.05  # the rule the report uses

    def test_the_cash_flow_block_is_passed_through(self):
        cf = {"sources": {"Wages": [100, 0]}, "uses": {"Net spending": [100, 0]}}
        assert cash_flow(make_result(plan=dict(BASE_PLAN, cash_flow=cf))) == cf

    def test_a_negative_flow_is_drawn_on_the_other_side(self):
        """Review 3, W1: STAR makes the state tax negative (a refund), a negative `other inc`
        is money out; dropping them broke the drawn balance. Both move sides and the two
        sides stay equal; flows of fifty cents or less are left out."""
        cf = {
            "sources": {"Wages": [50_000, 10_000], "Other income": [0, -1_000],
                        "Taxable-account withdrawals": [40_000, 71_000]},
            "uses": {"Net spending": [91_000, 80_000], "State and local tax": [-1_708, 0],
                     "Federal income tax": [708, 0], "Savings (surplus)": [0.4, 0]},
        }
        result = make_result(plan=dict(BASE_PLAN, cash_flow=cf))
        sources, uses = cash_flow_year(result, 0)
        assert sources == {"Wages": 50_000.0, "Taxable-account withdrawals": 40_000.0,
                           "State and local tax, net refund": 1_708.0}
        assert "State and local tax" not in uses and "Savings (surplus)" not in uses
        assert sum(sources.values()) == sum(uses.values()) == 91_708.0
        sources, uses = cash_flow_year(result, 1)
        assert uses["Other income, net outflow"] == 1_000.0
        assert sum(sources.values()) == sum(uses.values()) == 81_000.0
        assert cash_flow_year(result, 5) == ({}, {})  # a year past the rows: nothing


class TestHeadlineWords:
    """UX review Q7: how the claiming ages were set, and a zero that is the goal."""

    def test_ages_held_when_the_solve_fixed_what_the_case_searches(self):
        result = make_result()  # options withSSAges fixed
        assert view.claiming_ages_how(result, "optimize") == "held"
        assert view.claiming_ages_how(result, ["Ari"]) == "held"
        assert "held at these" in view.claiming_ages_phrase(result, "optimize")

    def test_nothing_said_when_the_case_fixes_them_itself(self):
        result = make_result()
        assert view.claiming_ages_how(result, "fixed") == ""
        assert view.claiming_ages_phrase(result, "fixed") == view.claiming_ages_text(result)

    def test_chosen_by_owl_after_an_age_search(self):
        result = make_result(record={"age_search": {"candidates": [[67, 70]]}})
        assert view.claiming_ages_how(result, "optimize") == "chosen by Owl"
        assert view.claiming_ages_phrase(result, "optimize").endswith("(chosen by Owl)")

    def test_spent_down_by_design_only_with_no_bequest_target(self):
        spent = make_result(summary={**BASE_SUMMARY, "final_bequest_savings_today": 0.0})
        assert view.spent_down_by_design(spent, None) is True
        assert view.spent_down_by_design(spent, 0) is True
        assert view.spent_down_by_design(spent, 100) is False
        assert view.spent_down_by_design(make_result(), 0) is (
            abs(BASE_SUMMARY.get("final_bequest_savings_today", 0.0)) < 0.5)

    def test_not_under_max_bequest(self):
        spent = make_result(summary={**BASE_SUMMARY, "final_bequest_savings_today": 0.0},
                            plan={**BASE_PLAN, "objective": "maxBequest"})
        assert view.spent_down_by_design(spent, 0) is False

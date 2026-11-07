"""Comparing two results (design 9.2): the noise rule (R2), the two numbers (R3), the flags
(S13), the agreement check and "what moved"."""

from pathlib import Path

from owlplanner.library import compare as C
from owlplanner.library import results as R
from owlplanner.library.compare import (
    agreement,
    compare,
    difference,
    exact_companion,
    flags,
    what_moved,
)
from owlplanner.library.view import Result, score

# run_suite.py's EXACT_GROUP, as `decision_exact` resolves it.
EXACT_OPTIONS = {"breakpointMethod": "loop", "withMedicare": "none",
                 "withSSTaxability": 0.85, "withLTCG": "optimize"}


def make_result(*, id="2026-11-02T10-00-00_decision", objective="maxSpending",
                score_value=82_000.0, home=150_000.0, savings=350_000.0, taxes=180_000.0,
                kind="local search", gap=-1.0, preset="decision", commit="abcdef1",
                finished="2026-11-02T10:05:00+01:00", options=None, by_year=None):
    method = {"objective": objective,
              "breakpoint_method": {"local search": "local search (5 rounds)",
                                    "loop": "loop",
                                    "proved": "branch-and-bound (12 nodes)"}[kind],
              "options": options or {"breakpointMethod": "local-search", "withSSAges": "fixed"}}
    summary = {
        "spending_basis": score_value,
        "discretionary_year1": score_value,
        "final_bequest_today": home + savings,
        "final_bequest_savings_today": savings,
        "federal_income_tax_today": taxes * 0.7,
        "ltcg_tax_today": taxes * 0.1,
        "niit_today": taxes * 0.05,
        "payroll_tax_today": taxes * 0.05,
        "state_tax_today": taxes * 0.1,
    }
    plan = {"objective": objective, "individuals": ["Noa", "Avi"], "claiming_ages": [66.0, 70.0],
            "by_year": by_year or []}
    record = {
        "record_format": R.RECORD_FORMAT, "status": "solved", "preset": preset,
        "method": method, "engine": {"version": "2026.11.2", "commit": commit},
        "solve_date": {"started": finished, "finished": finished},
        "gap": gap,
        "convergence": {"convergence": "monotonic", "objective_error_bar_today_dollars": 0.0},
        "warnings": [],
    }
    return Result(results_id=id, results_dir=Path("runs/x/results") / id,
                  record=record, summary=summary, plan=plan)


def test_a_difference_of_fifty_cents_or_less_is_no_difference():
    """TIE_DOLLARS, run_suite's `|delta| > 0.5` guard on the "~" marker (review P6)."""
    a, b = make_result(score_value=82_000.0), make_result(score_value=82_000.5)
    j = difference("score", score(a), score(b), ta=a, tb=b)
    assert j.verdict == "no difference"


def test_under_one_percent_on_a_loop_run_is_unresolved():
    a, b = make_result(score_value=100_000.0), make_result(score_value=100_500.0)
    j = difference("score", score(a), score(b), ta=a, tb=b)
    assert j.verdict == "within noise" and not j.resolved
    assert j.delta == 500.0 and "~" in j.note and "1%" in j.note


def test_one_percent_and_above_counts():
    a, b = make_result(score_value=100_000.0), make_result(score_value=101_500.0)
    j = difference("score", score(a), score(b), ta=a, tb=b)
    assert j.verdict == "resolved" and j.delta == 1_500.0


def test_a_proved_plan_is_judged_by_its_gap_times_the_objective():
    """R2: "resolved when it is larger than both tolerances (reported gap x objective)"."""
    a = make_result(kind="proved", gap=1e-4, score_value=100_000.0)  # tolerance $10
    b = make_result(kind="proved", gap=1e-3, score_value=100_000.0)  # tolerance $100
    within = difference("score", score(a), score(b) + 50, ta=a, tb=b)  # 0.05%: fine for a gap run
    assert within.verdict == "within noise" and "gap" in within.note
    beyond = difference("score", score(a), score(b) + 150, ta=a, tb=b)
    assert beyond.verdict == "resolved"


def test_a_mixed_pair_takes_the_stricter_tolerance():
    a = make_result(kind="proved", gap=1e-5, score_value=100_000.0)  # tolerance $1
    b = make_result(kind="loop")  # unproved: the 1% band applies
    j = difference("score", score(a), score(a) + 500, ta=a, tb=b)
    assert j.verdict == "within noise"  # 0.5% < 1%, though past the gap
    j = difference("score", score(a), score(a) + 1_500, ta=a, tb=b)
    assert j.verdict == "resolved"


class TestFlags:
    def test_the_same_day_preset_and_commit_flag_nothing(self):
        a, b = make_result(), make_result(id="2026-11-02T11-00-00_decision")
        assert flags(a, b) == ()

    def test_different_days_presets_and_commits_are_flagged(self):
        a = make_result(finished="2026-11-02T10:05:00+01:00")
        b = make_result(id="x", preset="quick", commit="1234567",
                        finished="2026-11-05T10:05:00+01:00")
        out = flags(a, b)
        assert len(out) == 3
        assert any("different days" in f and "run both again" in f for f in out)
        assert any("presets" in f for f in out)
        assert any("commits" in f for f in out)


class TestLead:
    def _rows(self, **kw):
        a, b = make_result(**kw.pop("a", {})), make_result(**kw.pop("b", {}))
        c = compare(a, b)
        return c

    def test_a_variant_leads_when_it_is_better_on_one_and_not_worse_on_the_other(self):
        c = self._rows(a={}, b={"score_value": 84_000.0})
        assert c.lead["verdict"] == "the second result leads"
        c = self._rows(a={"score_value": 84_000.0}, b={})
        assert c.lead["verdict"] == "the first result leads"

    def test_more_spending_with_less_home_is_a_trade_off(self):
        c = self._rows(a={}, b={"score_value": 84_000.0, "home": 100_000.0, "savings": 350_000.0})
        assert c.lead["verdict"] == "trade-off"

    def test_within_noise_everywhere_is_no_difference(self):
        c = self._rows(a={}, b={"score_value": 82_400.0, "home": 150_000.4, "savings": 350_000.0})
        assert c.lead["verdict"] == "no difference beyond the noise rule"

    def test_the_home_is_an_input_so_no_noise_band_hides_a_home_difference(self):
        """Review 3, W2: the home at the end is set from the Debts and Fixed Assets tables
        before any solve, so the 1% loop band (here 1,500) must not swallow a 1,000 home
        difference -- more spending with less home is a trade-off, not a lead."""
        c = self._rows(a={}, b={"score_value": 84_500.0, "home": 149_000.0, "savings": 350_000.0})
        home = next(r for r in c.rows if r.label == "home at the end")
        assert home.verdict == "resolved" and "set by the inputs" in home.note
        assert c.lead["verdict"] == "trade-off"
        # The score keeps its noise band: under 1% of 82,000 is still unresolved.
        c = self._rows(a={}, b={"score_value": 82_400.0, "home": 151_000.0, "savings": 350_000.0})
        score_row = next(r for r in c.rows if r.label == "score")
        assert score_row.verdict == "within noise"
        assert c.lead["verdict"] == "the second result leads"

    def test_a_proved_pair_judges_the_home_without_its_gap(self):
        """A proved plan's tolerance (gap x objective) is a property of the solve: the home
        difference is resolved even when it is smaller than that tolerance."""
        a = make_result(kind="proved", gap=1e-2, score_value=82_000.0)
        b = make_result(kind="proved", gap=1e-2, score_value=82_000.0, home=149_900.0)
        home = next(r for r in compare(a, b).rows if r.label == "home at the end")
        assert home.verdict == "resolved"


class TestLeadUnderMaxBequest:
    """Review 3, W5: under maxBequest the score is the final bequest, which already holds the
    home; judging it beside the home counted the home twice."""

    def test_more_home_and_less_savings_is_a_trade_off(self):
        a = make_result(objective="maxBequest", home=1_000_000.0, savings=300_000.0)
        b = make_result(objective="maxBequest", home=1_150_000.0, savings=200_000.0)
        c = compare(a, b)
        assert c.lead["verdict"] == "trade-off"
        assert "more savings" in c.lead["note"]

    def test_more_savings_with_the_same_home_leads(self):
        a = make_result(objective="maxBequest", home=1_000_000.0, savings=300_000.0)
        b = make_result(objective="maxBequest", home=1_000_000.0, savings=320_000.0)
        assert compare(a, b).lead["verdict"] == "the second result leads"

    def test_different_objectives_are_not_comparable_and_flagged(self):
        a = make_result(objective="maxSpending")
        b = make_result(objective="maxBequest")
        c = compare(a, b)
        assert c.lead["verdict"] == "not comparable" and "different objectives" in c.lead["note"]
        assert any("different objectives" in f for f in c.flags)


class TestAgreement:
    def test_the_same_ordering_is_resolved(self):
        a, b = make_result(score_value=100_000.0), make_result(score_value=103_000.0)
        a_ex = make_result(id="2026-11-02T11-00-00_decision_exact", score_value=90_000.0,
                           options=dict(EXACT_OPTIONS))
        b_ex = make_result(id="2026-11-02T11-30-00_decision_exact", score_value=92_800.0,
                           options=dict(EXACT_OPTIONS))
        out = agreement(a, b, a_ex, b_ex)
        assert out["verdict"].startswith("resolved") and "ahead of" in out["verdict"]
        assert out["delta_pair"] == 3_000.0 and out["delta_exact"] == 2_800.0

    def test_a_sign_disagreement_is_unresolved(self):
        a, b = make_result(score_value=100_000.0), make_result(score_value=100_200.0)
        a_ex, b_ex = make_result(score_value=90_000.0), make_result(score_value=89_000.0)
        out = agreement(a, b, a_ex, b_ex)
        assert "disagree on the sign" in out["verdict"]

    def test_a_difference_smaller_than_the_spread_is_unresolved(self):
        a, b = make_result(score_value=100_000.0), make_result(score_value=101_000.0)
        a_ex, b_ex = make_result(score_value=90_000.0), make_result(score_value=90_200.0)
        out = agreement(a, b, a_ex, b_ex)
        assert "smaller than the spread" in out["verdict"]

    def test_in_aca_years_a_disagreement_defers_to_the_pair_s_own_result(self):
        """Design 9.2: "a disagreement there goes to the local-search result, not to a tie"
        (review P7: the verdict must say so, not leave "unresolved" next to the note)."""
        years = [{"year": 2030, "aca_premiums": 12_000}]
        a = make_result(score_value=100_000.0, by_year=years)
        b = make_result(score_value=100_200.0, by_year=years)
        a_ex, b_ex = make_result(score_value=90_000.0), make_result(score_value=89_000.0)
        out = agreement(a, b, a_ex, b_ex)
        assert "the pair's own difference decides" in out["verdict"]
        assert "mis-prices the ACA trade" in out["note"]

    def test_compare_needs_four_distinct_results(self):
        """Review P4: no self-companion, no shared companion (a zero exact difference would
        read as a sign disagreement), no cross-companion."""
        a, b = make_result(), make_result(id="2026-11-02T10-00-00_decision_b", score_value=84_000.0)
        assert compare(a, b).agreement is None
        exact_a = make_result(id="2026-11-02T11-00-00_decision_exact", score_value=70_000.0,
                              options=dict(EXACT_OPTIONS))
        assert compare(a, b, a_exact=exact_a, b_exact=exact_a).agreement is None  # shared
        assert compare(a, b, a_exact=a, b_exact=exact_a).agreement is None  # self
        exact_b = make_result(id="2026-11-02T11-30-00_decision_exact", score_value=72_500.0,
                              options=dict(EXACT_OPTIONS))
        out = compare(a, b, a_exact=exact_a, b_exact=exact_b)
        assert out.agreement is not None and out.agreement["delta_exact"] == 2_500.0

    def test_exact_companion_skips_the_pair_and_prefers_the_newest_same_day(self):
        """Review P4: the companion is one of the run's *other* solves, of the pair's day."""
        day = "2026-11-02T12:00:00+01:00"
        near = make_result(id="2026-11-02T10-00-00_decision", finished=day)
        old = make_result(id="2026-11-01T09-00-00_decision_exact", score_value=70_000.0,
                          options=dict(EXACT_OPTIONS), finished="2026-11-01T09:05:00+01:00")
        picked = make_result(id="2026-11-02T10-30-00_decision_exact", score_value=71_000.0,
                             options=dict(EXACT_OPTIONS), finished=day)
        newest = make_result(id="2026-11-03T10-30-00_decision_exact", score_value=72_000.0,
                             options=dict(EXACT_OPTIONS), finished="2026-11-03T10:35:00+01:00")
        chosen = exact_companion([old, picked, newest], exclude={"2026-11-02T10-00-00_decision"},
                                 near=near)
        assert chosen is picked  # the same day, not the older or the later-day one
        assert exact_companion([old, newest], near=near) is newest  # no same-day one: newest
        assert exact_companion([picked],
                               exclude={"2026-11-02T10-30-00_decision_exact"}) is None


class TestWhatMoved:
    YEARS_A = [
        {"year": 2030, "federal_income_tax": 20_000, "state_tax": 5_000, "medicare_premiums": 3_000,
         "aca_premiums": 0, "roth_conversions": 0, "portfolio_withdrawals": 60_000,
         "ss_income": [0, 0], "spending": 90_000},
        {"year": 2031, "federal_income_tax": 21_000, "state_tax": 5_100, "medicare_premiums": 3_100,
         "aca_premiums": 0, "roth_conversions": 0, "portfolio_withdrawals": 61_000,
         "ss_income": [10_000, 0], "spending": 91_000},
    ]
    YEARS_B = [
        {"year": 2030, "federal_income_tax": 20_500, "state_tax": 5_000, "medicare_premiums": 3_000,
         "aca_premiums": 0, "roth_conversions": 40_000, "portfolio_withdrawals": 80_000,
         "ss_income": [0, 0], "spending": 90_000},
        {"year": 2031, "federal_income_tax": 21_000, "state_tax": 5_100, "medicare_premiums": 3_100,
         "aca_premiums": 0, "roth_conversions": 0, "portfolio_withdrawals": 61_000,
         "ss_income": [10_000, 0], "spending": 91_000},
    ]

    def test_only_years_that_moved_show_up(self):
        a = make_result(by_year=self.YEARS_A)
        b = make_result(by_year=self.YEARS_B)
        rows, totals, columns = what_moved(a, b)
        assert [r["year"] for r in rows] == [2030]
        assert rows[0]["changes"]["taxes"] == 500
        assert rows[0]["changes"]["roth_conversions"] == 40_000
        assert rows[0]["changes"]["portfolio_withdrawals"] == 20_000
        assert "spending" not in rows[0]["changes"]  # it never moved: not a column
        assert dict(totals)["Taxes (income, gains, NIIT, payroll, state)"] == 500
        assert dict(totals)["Roth conversions"] == 40_000
        assert [key for key, _ in columns] == ["taxes", "roth_conversions", "portfolio_withdrawals"]

    def test_no_movement_gives_no_table(self):
        a = make_result(by_year=self.YEARS_A)
        rows, totals, columns = what_moved(a, a)
        assert rows == () and totals == () and columns == ()


def test_what_moved_matches_the_plans_by_calendar_year():
    """Review 3, W6: two plans of different plan years were matched by position (A's 2027
    against B's 2028 under the label 2027). Same spending in the same calendar year is no
    movement; a year only one plan has is shown against zero."""
    a = make_result(by_year=[{"year": y, "spending": 1000 * (y - 2025)} for y in (2026, 2027, 2028)])
    b = make_result(id="b", by_year=[{"year": y, "spending": 1000 * (y - 2025)} for y in (2027, 2028, 2029)])
    rows, totals, _columns = what_moved(a, b)
    assert [(r["year"], r["changes"]["spending"]) for r in rows] == [(2026, -1000), (2029, 4000)]
    assert dict(totals) == {"Spending": 3000}


class TestDefaultPair:
    """UX review Q4: the Compare page's first selection."""

    def test_b_is_the_newest_and_a_its_parent(self):
        entries = [("c", None, 300.0, True), ("b", "a", 200.0, True), ("b", "a", 250.0, False),
                   ("a", None, 100.0, True)]
        a, b = C.default_pair(entries)
        assert b == 0  # run c's result is the newest main one
        # c has no parent: A is the newest main result of another run, b's.
        assert a == 1

    def test_a_is_the_parent_even_when_another_run_is_newer(self):
        entries = [("b", "a", 300.0, True), ("x", None, 250.0, True), ("a", None, 100.0, True)]
        assert C.default_pair(entries) == (2, 0)

    def test_a_companion_is_never_chosen(self):
        entries = [("b", "a", 300.0, True), ("a", None, 310.0, False), ("a", None, 100.0, True)]
        assert C.default_pair(entries) == (2, 0)

    def test_never_the_same_result(self):
        entries = [("a", None, 100.0, True), ("a", None, 200.0, True)]
        assert C.default_pair(entries) == (0, 1)

    def test_fewer_than_two_main_results(self):
        assert C.default_pair([("a", None, 1.0, True)]) == (0, 0)
        assert C.default_pair([("a", None, 1.0, False), ("b", None, 2.0, True)]) == (0, 1)

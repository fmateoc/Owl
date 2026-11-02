"""A run is solved only in its plan year (R1; design section 8.3, revised 2026-11-02).

Owl's plan starts in the calendar year of the solve whatever the case says, so a run's
balances and year rows are valid only in the year they were entered for. The library records
that year as the run's `plan_year` and refuses to queue or solve the run in any other year.
Within the plan year, what the backend reads beyond the year is:

- the day, for `start_date = "today"` only: the library stores the day of capture instead, so
  a run's first-year fraction does not move with the day it is solved on;
- the month, for the claiming ages `withSSAges` may still choose: read live on purpose (a
  month already past cannot be claimed), so a claiming-age search can change as months close.

There is no frozen "as of" date (dropped 2026-11-02: the fork stays closer to upstream).
"""

import pytest

from owlplanner.library import ScenarioError, check_plan_year, import_case, scenario_hash

BILL = "examples/Case_bill.toml"


class TestThePlanYear:
    def test_it_is_the_start_dates_year(self):
        scenario = import_case(BILL)  # start_date = "2026-01-01"
        assert scenario["plan_year"] == 2026
        assert check_plan_year(scenario) == 2026  # the suite's date is 2026-01-01

    def test_a_run_from_another_year_is_refused(self):
        scenario = import_case(BILL)
        scenario["plan_year"] = 2025
        with pytest.raises(ScenarioError, match="plan year is 2025 but this is 2026"):
            check_plan_year(scenario)

    def test_a_run_with_no_plan_year_is_refused(self):
        with pytest.raises(ScenarioError, match="no plan year"):
            check_plan_year({"case": {}})

    def test_the_new_year_refuses_last_years_run(self, pretend_today):
        scenario = import_case(BILL)
        with pretend_today("2027-01-01"):
            with pytest.raises(ScenarioError, match="plan year is 2026 but this is 2027"):
                check_plan_year(scenario)


class TestTodayAsTheStartDate:
    @pytest.fixture
    def today_case(self, tmp_path):
        """Case_bill with start_date = "today" (the UI's default)."""
        text = open(BILL, encoding="utf-8").read().replace('start_date = "2026-01-01"', 'start_date = "today"')
        assert 'start_date = "today"' in text
        case = tmp_path / "Case_today.toml"
        case.write_text(text, encoding="utf-8")  # Case_bill has no HFP workbook
        return case

    def test_it_is_stored_as_the_day_of_capture(self, today_case, pretend_today):
        with pretend_today("2026-03-02"):
            scenario = import_case(today_case)
        assert scenario["case"]["basic_info"]["start_date"] == "2026-03-02"
        assert scenario["plan_year"] == 2026

    def test_reimporting_on_another_day_keeps_the_hash(self, today_case, tmp_path, pretend_today):
        """The run's own files carry the absolute date, so they import the same any day."""
        from owlplanner.library import Library

        with pretend_today("2026-03-02"):
            run = Library.open(tmp_path / "lib").save_run(name="t", scenario=import_case(today_case)).run
        with pretend_today("2026-11-20"):
            again = import_case(run.path / "inputs" / "Case.toml")
        assert scenario_hash(again) == run.inputs_hash


class TestTheClaimingWindowIsLive:
    """The one month-dependent read: deliberately not frozen (a past month cannot be claimed)."""

    def _open_ages(self):
        import io

        import owlplanner as owl

        p = owl.Plan(["P"], ["1960-01-15"], [95], "t", verbose=False, logstreams=[io.StringIO()])
        p.setSocialSecurity([3800], [70])
        return list(p._ssaOpenAges(0))

    def test_the_open_ages_follow_the_month(self, pretend_today):
        with pretend_today("2026-01-16"):
            january = self._open_ages()
        with pretend_today("2026-09-16"):
            september = self._open_ages()
        assert september[0] > january[0] and set(september) < set(january)

"""The "as of" date input (run-library step 2; design section 8.3 b, R1, S1, S7).

Owl's plan starts in the solve year and the current month bounds the claiming ages, so
results move with the day the code runs on. A run must reproduce: the "today" Owl reads is
the `as_of` input (`owlplanner.asof`), settable by `owlcli --as-of` and by the worker, and
recorded in `record.json`. These tests pin the mechanism and its reproducibility claim:
two solves on different days give identical results.
"""

import json
import shutil
from datetime import date

import pytest
from click.testing import CliRunner

from owlplanner import asof
from owlplanner.cli._main import cli
from owlplanner.cli.cmd_run import _set_as_of
from owlplanner.config.toml_io import sanitize_config
from owlplanner.library import ScenarioError, import_case, resolve_as_of, scenario_hash
from owlplanner.library.scenario import validate

BILL = "examples/Case_bill.toml"


def _the_json_object(text):
    """The JSON document `--output-format json` printed (the plan's log shares the stream)."""
    decoder = json.JSONDecoder()
    idx = text.find("{")
    while idx != -1:
        try:
            doc, _ = decoder.raw_decode(text[idx:])
            return doc
        except ValueError:
            idx = text.find("{", idx + 1)
    raise AssertionError("no JSON object in the output")


@pytest.fixture(autouse=True)
def _restore_asof():
    """Every test here moves the pin; put it back whatever happens."""
    saved = asof.get_as_of()
    yield
    asof.set_as_of(saved)


class TestInput:
    def test_set_get_and_clear(self):
        assert asof.get_as_of() is not None  # the suite pins 2026-01-01 (tests/conftest.py)
        asof.set_as_of("2027-06-15")
        assert asof.today() == date(2027, 6, 15) == asof.get_as_of()
        asof.set_as_of(None)
        assert asof.get_as_of() is None and asof.today() == date.today()
        asof.set_as_of("2026-01-01")  # the suite's pin, restored

    def test_the_context_manager_restores(self):
        with asof.as_of("2027-06-15") as day:
            assert day == date(2027, 6, 15) and asof.today() == date(2027, 6, 15)
        assert asof.today() == date(2026, 1, 1)

    def test_dates_datetimes_and_strings_parse(self):
        assert asof.set_as_of(date(2027, 1, 2)) == date(2027, 1, 2)
        assert asof.set_as_of("2027-01-02") == date(2027, 1, 2)
        asof.set_as_of("2026-01-01")

    def test_bad_values_are_refused(self):
        with pytest.raises(ValueError):
            asof.set_as_of("01/02/2027")
        with pytest.raises(TypeError):
            asof.set_as_of(2027)
        assert asof.today() == date(2026, 1, 1)

    def test_the_frozen_date_dominates_the_wall_clock(self, pretend_today):
        with asof.as_of("2027-06-15"):
            with pretend_today("2027-12-31"):
                assert asof.today() == date(2027, 6, 15)

    def test_the_context_freeze_does_not_leak_across_threads(self):
        """F5: Streamlit sessions are threads; one capture must not date another solve."""
        import threading

        seen = []

        def other():
            seen.append(asof.today())

        with asof.as_of("2027-06-15"):
            thread = threading.Thread(target=other)
            thread.start()
            thread.join()
            assert asof.today() == date(2027, 6, 15)  # this thread is frozen
        assert seen == [date(2026, 1, 1)]  # the other thread saw the suite's pin


class TestBackendHonoursIt:
    def test_sanitize_config_pins_to_the_frozen_year(self):
        conf = {"solver_options": {"startRothConversions": 2025}}
        with asof.as_of("2027-06-15"):
            sanitize_config(conf)
        assert conf["solver_options"]["startRothConversions"] == 2027

    def test_a_run_refuses_an_as_of_outside_its_plan_year(self):
        scenario = import_case(BILL)
        assert scenario["plan_year"] == 2026 and scenario["as_of"] == "2026-01-01"
        scenario["as_of"] = "2027-01-01"
        with pytest.raises(ScenarioError):
            validate(scenario)
        with pytest.raises(ScenarioError):
            resolve_as_of({"plan_year": 2026, "case": {"basic_info": {"start_date": "2027-03-01"}}})

    def test_the_worker_date_lands_inside_the_plan_year(self):
        scenario = import_case(BILL)
        assert resolve_as_of(scenario).isoformat() == scenario["as_of"]


class TestImportIsPinned:
    def test_the_same_files_import_identically_on_different_days(self, pretend_today):
        """V5's date dependence, pinned: conditioning runs at the run's balances' date."""
        with pretend_today("2026-01-10"):
            one = import_case(BILL)
        with pretend_today("2026-11-20"):
            two = import_case(BILL)
        assert scenario_hash(one) == scenario_hash(two)


class TestCli:
    def test_as_of_option_rejects_a_bad_date(self):
        with pytest.raises(Exception) as excinfo:
            _set_as_of(None, None, "June 2027")
        assert "YYYY-MM-DD" in str(excinfo.value)

    def test_as_of_option_sets_the_input(self):
        _set_as_of(None, None, "2027-06-15")
        try:
            assert asof.today() == date(2027, 6, 15)
        finally:
            asof.set_as_of("2026-01-01")

    def test_two_solves_on_different_days_give_identical_results(self, tmp_path, pretend_today):
        """`owlcli run --as-of` reproduces a run (S7): the wall clock must not reach it.

        The two pretend days straddle a New Year (and ten months): a freeze that leaked any
        year or month read would move the plan year, the workbook conditioning or the open
        claiming ages, and the results would differ (S1).
        """
        case = tmp_path / "Case_bill.toml"
        shutil.copy(BILL, case)
        outputs = []
        for day in ("2026-01-10", "2027-02-01"):
            with pretend_today(day):
                result = CliRunner().invoke(
                    cli, ["run", "--as-of", "2026-06-15", "--output-format", "json", str(case)]
                )
            assert result.exit_code == 0, result.output
            doc = _the_json_object(result.output)
            doc["solve_time_seconds"] = None  # wall and CPU time are load-dependent
            outputs.append(doc)
        assert outputs[0] == outputs[1]
        assert outputs[0]["status"] == "solved"


class TestTheDateReachesTheSolve:
    def _open_ages(self):
        import io

        import owlplanner as owl

        p = owl.Plan(["P"], ["1960-01-15"], [95], "t", verbose=False, logstreams=[io.StringIO()])
        p.setSocialSecurity([3800], [70])
        return list(p._ssaOpenAges(0))

    def test_the_wall_clock_does_not_move_the_open_claiming_ages(self, pretend_today):
        """S1's month sensitivity: the open ages read the month of "today". With the freeze
        on, the wall clock must not reach them."""
        with asof.as_of("2026-06-16"):
            with pretend_today("2026-01-05"):
                jan = self._open_ages()
            with pretend_today("2026-09-20"):
                sep = self._open_ages()
        assert jan == sep

    def test_the_as_of_date_does_move_them(self):
        """And the function is date-sensitive at all (the test above has teeth)."""
        with asof.as_of("2026-01-16"):
            early = self._open_ages()
        with asof.as_of("2026-09-16"):
            late = self._open_ages()
        assert early != late

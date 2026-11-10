"""A what-if from the Scenario page to its comparison (local-use review D4), by AppTest.

*Save and solve* saves the child run, queues its Careful solve (and its parent's when the
parent has none from today), and opens the child's Run page; *Compare with its parent* there
opens Compare on that pair, whatever else the library holds.
"""

import copy
from pathlib import Path

import pytest

from owlplanner.library import JobManager, Library, import_case
from owlplanner.library import results as R

from test_library_pages import _write_result
from test_scenario_page import EVENTS

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"
TODAY = "2026-01-01"  # the suite's frozen date


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # no real worker
    lib = Library.open(root)
    lib.save_run(name="bill", scenario=dict(import_case(BILL), events=copy.deepcopy(EVENTS)))
    return lib


def _page(name, state=None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / name), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    for key, value in (state or {}).items():
        at.session_state[key] = value
    return at.run()


def _stop_at_switch(monkeypatch):
    """`st.switch_page` ends the script in the app: here it records the page and stops, so the
    session is what the next page would find."""
    import streamlit as st

    opened = []

    def switch(page):
        opened.append(page)
        st.stop()

    monkeypatch.setattr("streamlit.switch_page", switch)
    return opened


def _presets(library, run):
    return sorted(job.doc["preset"] for job in JobManager(library).jobs(run))


def _what_if(monkeypatch):
    """The Scenario page with the rent raised, after a click on *Save and solve*."""
    opened = _stop_at_switch(monkeypatch)
    at = _page("Scenario.py")
    assert not at.exception, [e.value for e in at.exception]
    rent = next(n for n in at.number_input if n.key and n.key.startswith("scn_rent_monthly_"))
    rent.set_value(4500.0).run()
    at.button(key="scenario_save_solve").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at, opened


def _child(library, **result):
    """A child of "bill" with one solved result, as *Save and solve* leaves it once solved."""
    parent = library.runs()[0]
    scenario = library.scenario(parent)
    next(e for e in scenario["events"] if e["id"] == "rent")["monthly"] = 4500
    child = library.save_run(name="bill, rent 4500", scenario=scenario, parent=parent.id).run
    _write_result(child, f"{TODAY}T11-00-00_decision", score=80_000.0, finished=f"{TODAY}T11:05:00+01:00",
                  **result)
    return parent, child


class TestSaveAndSolve:
    def test_it_saves_queues_and_opens_the_new_runs_page(self, library, monkeypatch):
        at, opened = _what_if(monkeypatch)
        parent, child = library.runs()
        assert child.parent == parent.id and child.name == "bill variant"
        assert _presets(library, child) == ["decision", "decision_exact"]
        assert opened == ["Run.py"]
        assert at.session_state["library_selected_run"] == child.id
        said = " ".join(text for _kind, text in at.session_state["library_flash"])
        assert "Saved as *bill variant*" in said and "*Careful (about 5 minutes)* solve is queued" in said

    def test_the_parent_is_solved_the_same_way_for_the_comparison(self, library, monkeypatch):
        at, _ = _what_if(monkeypatch)
        parent, child = library.runs()
        assert _presets(library, parent) == ["decision", "decision_exact"]
        said = " ".join(text for _kind, text in at.session_state["library_flash"])
        assert "*bill* is solved the same way after it, for the comparison." in said
        # The what-if first: its own result is what the reader waits for.
        order = [job.doc["run_id"] for job in JobManager(library).jobs() if job.doc["preset"] == "decision"]
        assert order == [child.id, parent.id]

    def test_a_parent_with_todays_careful_result_is_not_solved_again(self, library, monkeypatch):
        parent = library.runs()[0]
        _write_result(parent, f"{TODAY}T09-00-00_decision", finished=f"{TODAY}T09:05:00+01:00")
        _what_if(monkeypatch)
        parent, child = library.runs()
        assert _presets(library, parent) == ["decision"]  # the result it had, nothing queued
        assert _presets(library, child) == ["decision", "decision_exact"]

    def test_a_parent_with_an_older_or_a_quick_result_is_solved_again(self, library, monkeypatch):
        parent = library.runs()[0]
        _write_result(parent, "2025-12-20T09-00-00_decision", finished="2025-12-20T09:05:00+01:00")
        _write_result(parent, f"{TODAY}T09-00-00_quick", preset="quick", finished=f"{TODAY}T09:05:00+01:00")
        _what_if(monkeypatch)
        parent = library.runs()[0]
        assert _presets(library, parent) == ["decision", "decision", "decision_exact", "quick"]

    def test_save_as_a_new_run_still_only_saves(self, library, monkeypatch):
        opened = []
        monkeypatch.setattr("streamlit.switch_page", lambda page: opened.append(page))
        at = _page("Scenario.py")
        next(n for n in at.number_input if n.key and n.key.startswith("scn_rent_monthly_")).set_value(4500.0).run()
        at.button(key="scenario_save").click().run()
        assert not at.exception, [e.value for e in at.exception]
        parent, child = library.runs()
        assert opened == [] and _presets(library, child) == [] and _presets(library, parent) == []

    def test_the_run_page_it_opens_shows_the_solve(self, library, monkeypatch):
        at, _ = _what_if(monkeypatch)
        child = library.runs()[-1]
        state = {key: at.session_state[key] for key in (
            "library_selected_run", "library_flash", "run_page_show_newest", f"run_page_live_{child.id}")}
        run_page = _page("Run.py", state)
        assert not run_page.exception, [e.value for e in run_page.exception]
        assert any(m.value == "## bill variant" for m in run_page.markdown)
        solving = next(i.value for i in run_page.info if "Solving this run" in i.value)
        assert "**Careful**: waiting to start" in solving
        assert any("solve is queued" in i.value for i in run_page.info)

    def test_unchanged_events_solve_the_run_itself(self, library, monkeypatch):
        """Nothing edited: the inputs are the run's own, so nothing is saved, the run itself is
        solved and its page opens (it has no parent to solve beside it)."""
        opened = _stop_at_switch(monkeypatch)
        at = _page("Scenario.py")
        at.button(key="scenario_save_solve").click().run()
        assert not at.exception, [e.value for e in at.exception]
        (only,) = library.runs()
        assert _presets(library, only) == ["decision", "decision_exact"] and opened == ["Run.py"]
        said = " ".join(text for _kind, text in at.session_state["library_flash"])
        assert "Identical to *bill*" in said and "solve is queued" in said

    def test_unbuildable_events_save_and_queue_nothing(self, library, monkeypatch):
        opened = []
        monkeypatch.setattr("streamlit.switch_page", lambda page: opened.append(page))
        at = _page("Scenario.py")
        price = next(n for n in at.number_input if n.key and n.key.startswith("scn_buy_price_"))
        price.set_value(0.0).run()
        at.button(key="scenario_save_solve").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert len(library.runs()) == 1 and opened == []
        assert any("Not saved" in w.value for w in at.warning)


class TestCompareWithItsParent:
    def test_the_button_opens_compare_on_the_pair(self, library, monkeypatch):
        parent, child = _child(library)
        _write_result(parent, f"{TODAY}T10-00-00_quick", preset="quick", finished=f"{TODAY}T10:05:00+01:00")
        _write_result(parent, f"{TODAY}T09-00-00_decision", score=78_000.0, finished=f"{TODAY}T09:05:00+01:00")
        opened = []
        monkeypatch.setattr("streamlit.switch_page", lambda page: opened.append(page))
        at = _page("Run.py", {"library_selected_run": child.id})
        assert not at.exception, [e.value for e in at.exception]
        assert any(c.value == "Against *bill*." for c in at.caption)
        at.button(key="run_page_compare_parent").click().run()
        assert opened == ["Compare.py"]
        # The parent's result solved the same way, not its newer Quick look.
        assert at.session_state["compare_pair"] == {
            "a": (parent.id, f"{TODAY}T09-00-00_decision"), "b": (child.id, f"{TODAY}T11-00-00_decision")}

    def test_compare_opens_on_the_pair_whatever_else_was_solved_since(self, library):
        parent, child = _child(library)
        _write_result(parent, f"{TODAY}T09-00-00_decision", score=78_000.0, finished=f"{TODAY}T09:05:00+01:00")
        # Something else, solved later: Compare's own default pair is no longer the what-if.
        other = dict(import_case(BILL))
        other["case"]["basic_info"]["life_expectancy"] = [88]
        later = library.save_run(name="another plan", scenario=other).run
        _write_result(later, f"{TODAY}T12-00-00_decision", finished=f"{TODAY}T12:05:00+01:00")
        plain = _page("Compare.py")
        assert "another plan" in plain.selectbox(key="cmp_b").value
        asked = _page("Compare.py", {"compare_pair": {"a": (parent.id, f"{TODAY}T09-00-00_decision"),
                                                      "b": (child.id, f"{TODAY}T11-00-00_decision")}})
        assert not asked.exception, [e.value for e in asked.exception]
        assert asked.selectbox(key="cmp_a").value.startswith("bill (")
        assert f"{TODAY}T09-00-00_decision" in asked.selectbox(key="cmp_a").value
        assert asked.selectbox(key="cmp_b").value.startswith("bill, rent 4500 (")
        assert "compare_pair" not in asked.session_state  # asked once: the selectors are free again
        assert not asked.warning or not any("Session State API" in w.value for w in asked.warning)

    def test_no_parent_result_yet_says_what_is_missing(self, library, monkeypatch):
        parent, child = _child(library)
        at = _page("Run.py", {"library_selected_run": child.id})
        assert at.button(key="run_page_compare_parent").disabled
        assert any("*bill* has no solved result yet" in c.value for c in at.caption)
        JobManager(library).enqueue(parent, preset="decision")
        at.run()
        assert any("*bill* is being solved" in c.value for c in at.caption)

    def test_the_page_follows_the_parents_solve(self, library):
        """A what-if queues its parent's solve after its own: when that ends, the child's page
        redraws (the button and its caption read the parent's results) and says so once."""
        parent, child = _child(library)
        job = JobManager(library).enqueue(parent, preset="decision")
        at = _page("Run.py", {"library_selected_run": child.id})
        assert at.button(key="run_page_compare_parent").disabled
        _write_result(parent, job.id, score=78_000.0, finished=f"{TODAY}T12:05:00+01:00")
        at.run()  # the next tick
        assert not at.exception, [e.value for e in at.exception]
        assert not at.button(key="run_page_compare_parent").disabled
        assert any(c.value == "Against *bill*." for c in at.caption)
        assert any("*bill* is solved: *Compare with its parent* reads its new result." in c.value
                   for c in at.caption)
        at.run()
        assert not any("*bill* is solved" in c.value for c in at.caption)

    def test_a_parent_solved_another_way_is_said(self, library):
        parent, child = _child(library)
        _write_result(parent, f"{TODAY}T10-00-00_quick", preset="quick", finished=f"{TODAY}T10:05:00+01:00")
        at = _page("Run.py", {"library_selected_run": child.id})
        assert not at.button(key="run_page_compare_parent").disabled
        assert any("solved another way (Quick look)" in c.value for c in at.caption)

    def test_a_run_without_a_parent_has_no_button(self, library):
        parent = library.runs()[0]
        _write_result(parent, f"{TODAY}T09-00-00_decision", finished=f"{TODAY}T09:05:00+01:00")
        at = _page("Run.py")
        assert "run_page_compare_parent" not in [b.key for b in at.button]


class TestWhatIfRules:
    def test_is_current(self, library):
        import whatif

        manager = JobManager(library)
        run = library.runs()[0]
        assert not whatif.is_current(manager, run)
        job = manager.enqueue(run, preset="decision")
        assert whatif.is_current(manager, run)  # on the way
        job.finish(R.FAILED, error="no plan")
        assert not whatif.is_current(manager, run)
        _write_result(run, "2025-12-31T09-00-00_decision", finished="2025-12-31T09:05:00+01:00")
        assert not whatif.is_current(manager, run)  # yesterday's plan
        _write_result(run, f"{TODAY}T09-00-00_decision", finished=f"{TODAY}T09:05:00+01:00")
        assert whatif.is_current(manager, run)

    def test_main_results_leave_the_companion_out(self, library):
        import whatif

        run = library.runs()[0]
        _write_result(run, f"{TODAY}T09-00-00_decision", finished=f"{TODAY}T09:05:00+01:00")
        _write_result(run, f"{TODAY}T09-30-00_decision_exact", preset="decision_exact", exact=True,
                      finished=f"{TODAY}T09:35:00+01:00")
        assert [job.id for job, _ in whatif.main_results(JobManager(library), run)] == [f"{TODAY}T09-00-00_decision"]

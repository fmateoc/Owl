"""The Queue page (run-library step 2; review N1, N2): a two-stage cancel, rendered for real.

Streamlit's AppTest renders `ui/Queue.py` over a temporary library: a running job offers
Cancel; once a cancel is pending it offers Kill instead; a waiting job's Cancel stops it.
"""

import os
from pathlib import Path

import pytest

from owlplanner.library import Library, import_case
from owlplanner.library import results as R

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    lib = Library.open(root)
    lib.save_run(name="bill", scenario=import_case(BILL))
    return lib


def _running_job(lib, name, *, cancel=False):
    run = lib.runs()[0]
    job = R.JobRecord.create(run.path / "results" / name, run_id=run.id, run_name=run.name,
                             preset="quick", options={}, plan_year=2026)
    # A live, fresh, "ours" worker: this process, with no start token recorded.
    job.update(state=R.RUNNING, pid=os.getpid(), heartbeat=R.now_iso(), cancel=cancel)
    return job


def _page():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(UI_DIR / "Queue.py"), default_timeout=60).run()


def _labels(at):
    return sorted(b.label for b in at.button)


def _key(word, job):
    """A row button's key: the job among all the library's (`libraryjobs.job_key`)."""
    import libraryjobs

    return f"{word}_{libraryjobs.job_key(job)}"


def test_a_running_job_offers_cancel_then_kill(library):
    job = _running_job(library, "running")
    at = _page()
    assert not at.exception, [e.value for e in at.exception]
    assert "Cancel" in _labels(at) and "Kill" not in _labels(at)

    at.button(key=_key("cancel", job)).click().run()
    doc = R.JobRecord.read(job.results_dir).doc
    assert doc["cancel"] is True and doc["state"] == R.RUNNING  # cooperative: no kill
    assert "Kill" in _labels(at) and _key("cancel", job) not in [b.key for b in at.button]
    assert any("cancel pending" in c.value for c in at.caption)


def test_the_caption_says_when_elapsed_starts(library):
    at = _page()
    assert any("from the start of the solve" in c.value for c in at.caption)


def test_a_run_from_another_year_is_refused_with_a_message(library):
    """R1: the Solve button says why instead of raising."""
    import json

    run = library.runs()[0]
    path = run.path / "inputs" / "scenario.json"
    scenario = json.loads(path.read_text(encoding="utf-8"))
    scenario["plan_year"] = 2025
    path.write_text(json.dumps(scenario), encoding="utf-8")
    at = _page()
    solve = [b for b in at.button if b.label == "Solve"]
    assert solve, _labels(at)
    solve[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("plan year is 2025" in e.value for e in at.error)


def test_decision_queues_its_exact_companion(library, monkeypatch):
    """UX review B1: "decision" from the Queue page queues local search and its exact-model
    companion, as the Run and Collections pages do (`preset_solves`)."""
    from owlplanner.library import JobManager

    monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # no real worker
    at = _page()
    at.selectbox(key="queue_preset").set_value("decision").run()
    [b for b in at.button if b.label == "Solve"][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    run = library.runs()[0]
    presets = sorted(R.JobRecord.read(d).doc["preset"]
                     for d in (run.path / "results").iterdir() if (d / "status.json").exists())
    assert presets == ["decision", "decision_exact"], presets


def test_the_queue_says_what_a_job_is_doing_in_words(library):
    """UX review Q8: a phase in words, not the raw DEBUG line; a failed job keeps its error."""
    job = _running_job(library, "running")
    job.update(step="solving", last_log="2026-11-07 | DEBUG | localsearch:_step:263 | "
                                        "Local search, iteration 12: SS ball: moved in 1.20s.")
    run = library.runs()[0]
    failed = R.JobRecord.create(run.path / "results" / "failed", run_id=run.id, run_name=run.name,
                                preset="decision", options={}, plan_year=2026)
    failed.update(state=R.FAILED, error="ValueError: no plan")
    at = _page()
    assert not at.exception, [e.value for e in at.exception]
    shown = [m.value for m in at.markdown]
    assert "Solving: searching the tax breakpoints, step 12" in shown
    assert "Failed: ValueError: no plan" in shown
    assert not any("DEBUG" in m for m in shown)
    assert any("Careful (about 5 minutes)" in m for m in shown)  # Q2: the preset's name


def test_job_phase_words():
    import libraryjobs

    assert libraryjobs.job_phase({"state": "waiting"}, another_running=True).startswith("Waiting for another")
    assert libraryjobs.job_phase({"state": "waiting"}) == "Waiting to start"
    assert libraryjobs.job_phase({"state": "running", "step": "solving", "iteration": 3}) == \
        "Solving, loop iteration 3"
    assert libraryjobs.job_phase({"state": "interrupted"}) == "Interrupted"


def test_a_finished_row_opens_its_run(library, monkeypatch):
    """Ergonomics review S-6: "Open result" on a finished row selects the run and goes to Run."""
    import streamlit as st

    run = library.runs()[0]
    job = R.JobRecord.create(run.path / "results" / "done", run_id=run.id, run_name=run.name,
                             preset="quick", options={}, plan_year=2026)
    job.update(state=R.DONE, finished=R.now_iso())
    opened = []
    monkeypatch.setattr(st, "switch_page", lambda page: opened.append(page))
    at = _page()
    assert not at.exception, [e.value for e in at.exception]
    at.button(key=_key("open", job)).click().run()
    assert opened == ["Run.py"]
    assert at.session_state["library_selected_run"] == run.id


@pytest.mark.parametrize("state, word", [(R.DONE, "open"), (R.WAITING, "cancel"),
                                         (R.FAILED, "again"), (R.RUNNING, "kill")])
def test_two_runs_queued_in_the_same_second_keep_the_page_alive(library, monkeypatch, state, word):
    """Local-use review B1: *Make variants* with "Queue them when created" queues several runs
    in one second, and each run's results folder then has the same name. The row buttons were
    keyed by that name alone: StreamlitDuplicateElementKey, for as long as the rows were listed.
    Each button must also act on its own row's job."""
    import streamlit as st

    from owlplanner.library import JobManager

    monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # no real worker
    first = library.runs()[0]
    scenario = library.scenario(first)
    scenario["case"]["basic_info"]["life_expectancy"] = [88]  # other inputs: a second run
    second = library.save_run(name="bill to 88", scenario=scenario).run
    jobs = {}
    for run in (first, second):
        job = R.JobRecord.create(run.path / "results" / "2026-11-09T23-48-55_quick", run_id=run.id,
                                 run_name=run.name, preset="quick", options={}, plan_year=2026)
        if state == R.RUNNING:  # a live worker with a cancel pending: the row offers Kill
            job.update(state=R.RUNNING, pid=os.getpid(), heartbeat=R.now_iso(), cancel=True)
        elif state != R.WAITING:
            job.update(state=state, finished=R.now_iso())
        jobs[run.id] = job
    assert jobs[first.id].id == jobs[second.id].id  # the report's case: one name, two runs

    opened = []
    monkeypatch.setattr(st, "switch_page", lambda page: opened.append(page))
    at = _page()
    assert not at.exception, [e.value for e in at.exception]
    keys = [b.key for b in at.button if b.key and b.key.startswith(f"{word}_")]
    assert sorted(keys) == sorted(_key(word, job) for job in jobs.values())

    if state == R.DONE:  # the second run's row opens the second run
        at.button(key=_key("open", jobs[second.id])).click().run()
        assert opened == ["Run.py"] and at.session_state["library_selected_run"] == second.id
    elif state == R.WAITING:  # and cancels only its own job
        at.button(key=_key("cancel", jobs[second.id])).click().run()
        assert R.JobRecord.read(jobs[second.id].results_dir).state == R.INTERRUPTED
        assert R.JobRecord.read(jobs[first.id].results_dir).state == R.WAITING

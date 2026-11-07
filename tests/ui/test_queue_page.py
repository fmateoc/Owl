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


def test_a_running_job_offers_cancel_then_kill(library):
    job = _running_job(library, "running")
    at = _page()
    assert not at.exception, [e.value for e in at.exception]
    assert "Cancel" in _labels(at) and "Kill" not in _labels(at)

    at.button(key=f"cancel_{job.id}").click().run()
    doc = R.JobRecord.read(job.results_dir).doc
    assert doc["cancel"] is True and doc["state"] == R.RUNNING  # cooperative: no kill
    assert "Kill" in _labels(at) and f"cancel_{job.id}" not in [b.key for b in at.button]
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

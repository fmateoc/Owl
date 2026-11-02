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
                             preset="quick", options={}, as_of="2026-01-01")
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

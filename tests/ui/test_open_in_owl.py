""""Open in Owl" from a cached plan: step 2's check (design section 9.1; R10's open item).

`owlbridge.genDic` was said to build the page keys from a Plan -- unverified ("that path was
not tried"), and it did break: on every HSA case, at the account keys (it named three
accounts of four). This restores a run's cached `plan.pkl` into the pages and renders the
Graphs page from it with no solve, which is what the run page's "Open in Owl" button does.
"""

from pathlib import Path

import pytest

import owlbridge  # the bare module name Graphs.py binds, not ui.owlbridge

from owlplanner.library import Library, results as R
from owlplanner.library.worker import run_job

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"


@pytest.fixture(scope="module")
def cached_results(tmp_path_factory):
    """A solved run in a library: plan.pkl is the cache the run page opens."""
    from owlplanner.library import import_case

    library = Library.open(tmp_path_factory.mktemp("library"))
    run = library.save_run(name="bill", scenario=import_case(BILL)).run
    job = R.JobRecord.create(run.path / "results" / "j1", run_id=run.id, run_name=run.name,
                             preset="quick", options={"withSSAges": "fixed"}, as_of="2026-01-01")
    assert run_job(job.results_dir, job.token) == R.DONE
    return job.results_dir


def test_the_cached_plan_opens_with_the_page_keys(cached_results):
    plan = R.load_plan(cached_results)
    assert plan is not None and plan.caseStatus == "solved"
    name, dic = owlbridge.openCaseFromPlan(plan)
    for key in ("plan", "name", "caseStatus", "summaryDf", "metricsDict", "logs",
                "objective", "rateType", "interpMethod", "spendingProfile", "allocType"):
        assert key in dic, key
    assert dic["caseStatus"] == "solved" and dic["summaryDf"] is not None
    # The account keys every balance page reads (genDic named three of four until step 2).
    for key in ("txbl0", "txDef0", "txFree0", "hsa0"):
        assert key in dic, key


def test_the_graphs_page_restores_without_a_solve(monkeypatch, cached_results):
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    ran = []
    monkeypatch.setattr(owlbridge, "runPlan", lambda *a, **k: ran.append(1))
    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)

    plan = R.load_plan(cached_results)
    _, dic = owlbridge.openCaseFromPlan(plan)
    at = AppTest.from_file(str(UI_DIR / "Graphs.py"), default_timeout=120)
    at.session_state["cases"] = {"bill": dic}
    at.session_state["currentCase"] = "bill"
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert ran == []  # restored from the cache: the page did not re-run the case

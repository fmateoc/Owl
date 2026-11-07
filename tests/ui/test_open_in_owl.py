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
                             preset="quick", options={"withSSAges": "fixed"}, plan_year=2026)
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


def test_a_save_after_open_in_owl_keeps_the_aca_settings():
    """Found while folding review 3 (2026-11-06): `genDic` carried `slcsp_annual` only, and a
    pages save applies what differs from the run's case, so the missing `acaStartYear` read
    as an edit to 0 -- the marketplace premiums moved to the plan's first year, while the
    couple still works -- and the fork's `slcsp_published_*` were dropped."""
    import copy
    import io

    from owlplanner.config import config_to_plan
    from owlplanner.config.ui_bridge import config_to_ui, ui_to_config
    from owlplanner.library.casefiles import _apply_page_edits
    from owlplanner.library import import_case

    case = import_case(BILL)["case"]
    case["aca_settings"] = {"slcsp_annual": 20.84, "aca_start_year": 2027,
                            "slcsp_published_year": 2027, "slcsp_published_annual": 25.29}
    plan = config_to_plan(copy.deepcopy(case), ".", verbose=False, logstreams=[io.StringIO()],
                          loadHFP=False)
    _, dic = owlbridge.genDic(plan)
    before = ui_to_config(config_to_ui(copy.deepcopy(case)))
    saved = _apply_page_edits(case, before, ui_to_config(dic))
    assert saved["aca_settings"] == case["aca_settings"]


# -- UX review Q12: after "Open in Owl" -------------------------------------------------

JACK_JILL = "examples/Case_jack+jill.toml"


@pytest.fixture(scope="module")
def cached_workbook_results(tmp_path_factory):
    """A solved run whose case has a workbook (bill's has none)."""
    from owlplanner.library import import_case

    library = Library.open(tmp_path_factory.mktemp("library"))
    run = library.save_run(name="jack+jill", scenario=import_case(JACK_JILL)).run
    job = R.JobRecord.create(run.path / "results" / "j1", run_id=run.id, run_name=run.name,
                             preset="quick", options={"withSSAges": "fixed"}, plan_year=2026)
    assert run_job(job.results_dir, job.token) == R.DONE
    return job.results_dir


def _financial_profile(dic):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / "Financial_Profile.py"), default_timeout=120)
    at.session_state["cases"] = {"run": dic}
    at.session_state["currentCase"] = "run"
    return at.run()


def test_financial_profile_does_not_ask_for_the_runs_workbook(monkeypatch, cached_workbook_results):
    """Q12: the page said the run's workbook "has not yet been uploaded" above its tables."""
    import streamlit as st

    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    plan = R.load_plan(cached_workbook_results)
    assert plan.hfpFileName not in (None, "None")
    _, dic = owlbridge.openCaseFromPlan(plan)
    at = _financial_profile(dic)
    assert not at.exception, [str(e.value) for e in at.exception]
    shown = "\n".join([i.value for i in at.info] + [c.value for c in at.caption])
    assert "not yet been uploaded" not in shown, shown
    assert "loaded" in shown  # the upload's own confirmation line


def test_the_progress_strip_counts_the_runs_pages_as_visited(monkeypatch, cached_workbook_results):
    """Q12: the strip read "(12%) - Step 8 of 8" on a solved run."""
    import streamlit as st

    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    plan = R.load_plan(cached_workbook_results)
    _, dic = owlbridge.openCaseFromPlan(plan)
    at = _financial_profile(dic)
    strip = "\n".join(m.value for m in at.markdown if "Case Setup Progress" in m.value)
    assert "(100%)" in strip, strip


def test_the_workbook_is_named_without_its_folder(cached_workbook_results):
    """UX remediation QW-7 (review AL3): after "Open in Owl" the pages showed -- and the next
    save kept -- the run folder's workbook path. The pages know a file name."""
    plan = R.load_plan(cached_workbook_results)
    plan.hfpFileName = str(Path("runs") / "2026-11-07_x" / "inputs" / "HFP.xlsx")
    _, dic = owlbridge.openCaseFromPlan(plan)
    assert dic["hfpFileName"] == "HFP.xlsx"
    assert dic["stHFP"] == "HFP.xlsx"

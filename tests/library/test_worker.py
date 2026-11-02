"""The worker: one solve of one run, in its own results folder (design section 8.2).

Step 2's checks: a run solves in the background and writes the whole folder (record.json,
summary.json, plan.json, Results.xlsx, solve.log, plan.pkl); a cancelled job stops before
writing; a failed solve keeps its record (S3); and two solves on different days give
identical results (the frozen "as of" date, section 8.3 b).
"""

import json
import time

import pytest

from owlplanner import __version__
from owlplanner.library import JobManager, Library, results as R
from owlplanner.library.worker import run_job

BILL = "examples/Case_bill.toml"


@pytest.fixture(scope="module")
def scenario():
    from owlplanner.library import import_case

    return import_case(BILL)


@pytest.fixture
def library(tmp_path):
    return Library.open(tmp_path / "library")


@pytest.fixture
def run(library, scenario):
    return library.save_run(name="bill", scenario=scenario).run


def make_job(run, name="2026-01-01T00-00-00_quick", **kw):
    kw.setdefault("run_id", run.id)
    kw.setdefault("run_name", run.name)
    kw.setdefault("preset", "quick")
    kw.setdefault("options", {"withSSAges": "fixed"})
    kw.setdefault("as_of", "2026-01-01")
    return R.JobRecord.create(run.path / "results" / name, **kw)


def artifacts(results_dir):
    return sorted(p.name for p in results_dir.iterdir())


class TestOneSolve:
    def test_the_results_folder_is_complete(self, run):
        job = make_job(run)
        state = run_job(job.results_dir, job.token)
        assert state == R.DONE
        assert artifacts(job.results_dir) == [
            "Results.xlsx", "plan.json", "plan.pkl", "record.json", "solve.log",
            "status.json", "status.lock", "summary.json",
        ]

    def test_the_record_says_what_solved_how(self, run):
        job = make_job(run)
        run_job(job.results_dir, job.token)
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["status"] == "solved" and record["converged"] is True
        assert record["as_of"] == "2026-01-01" and record["preset"] == "quick"
        assert record["method"]["objective"] == "maxSpending"
        assert record["method"]["options"]["withSSAges"] == "fixed"
        assert record["engine"]["version"] == __version__ and record["engine"]["commit"]
        assert record["solver"] == "HiGHS" and record["gap"] == -1.0
        assert record["iterations"] >= 1 and record["wall_time_seconds"] > 0
        assert record["rates"]["method"] and record["environment"]["python"]
        assert record["inputs_hash"] and record["plan_pkl_sha256"]

    def test_the_plan_cache_opens_the_graphs_again(self, run):
        job = make_job(run)
        run_job(job.results_dir, job.token)
        plan = R.load_plan(job.results_dir)
        assert plan is not None and plan.caseStatus == "solved"
        assert float(plan.g_n[0]) == pytest.approx(
            json.loads((job.results_dir / R.SUMMARY_JSON).read_text(encoding="utf-8"))["spending_year1"], 1e-6
        )

    def test_a_cancelled_job_stops_before_writing(self, run):
        job = make_job(run)
        job.request_cancel()
        state = run_job(job.results_dir, job.token)
        assert state == R.INTERRUPTED
        # The interrupted solve keeps its record (S3): what stopped, and no results.
        assert artifacts(job.results_dir) == ["record.json", "solve.log", "status.json", "status.lock"]
        assert "cancelled" in R.JobRecord.read(job.results_dir).doc["error"]
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["status"] == "interrupted" and "cancelled" in record["error"]

    def test_a_failed_solve_keeps_its_record(self, run):
        job = make_job(run)
        (run.path / "inputs" / "Case.toml").write_text("not a toml file [", encoding="utf-8")
        state = run_job(job.results_dir, job.token)
        assert state == R.FAILED
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["status"] == "exception" and record["error"]
        assert "Traceback" in (job.results_dir / R.SOLVE_LOG).read_text(encoding="utf-8")


class TestTwoSolvesOnDifferentDays:
    def test_identical_results_whatever_the_wall_clock_says(self, run, pretend_today):
        """Step 2's check: the run's "as of" date, not the day of the solve, decides.

        The two pretend days straddle a New Year: a freeze that leaked any year or month
        read would move the plan (S1).
        """
        outputs = []
        for day, name in (("2026-01-10", "a"), ("2027-02-01", "b")):
            with pretend_today(day):
                job = make_job(run, name=f"2026-01-01T00-00-0{name}_quick")
                assert run_job(job.results_dir, job.token) == R.DONE
            summary = json.loads((job.results_dir / R.SUMMARY_JSON).read_text(encoding="utf-8"))
            plan_doc = json.loads((job.results_dir / R.PLAN_JSON).read_text(encoding="utf-8"))
            plan_doc["solve_time_seconds"] = None  # load-dependent
            record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
            outputs.append((summary, plan_doc, record))
        (sum_a, plan_a, rec_a), (sum_b, plan_b, rec_b) = outputs
        assert sum_a == sum_b
        assert plan_a == plan_b
        for key in ("status", "converged", "gap", "iterations", "as_of", "convergence"):
            assert rec_a[key] == rec_b[key]


class TestAStaleWorkerWritesNothing:
    def test_run_again_leaves_no_artifacts_of_the_old_attempt(self, run, library, monkeypatch):
        """G2: the artifact publish is token-guarded too (F2 covered the record only).

        The worker is held inside the results write while the job is re-queued ("run again"
        after a machine-sleep wake, S8's own scenario); released, it must leave the folder
        exactly as the re-queue left it -- the old attempt's summary/plan/workbook/pkl may
        not come back (probe: they did, mixed into the new attempt's clean folder).
        """
        import threading

        from owlplanner import plan as plan_mod

        job = make_job(run)
        old_token = job.token
        writing, resume = threading.Event(), threading.Event()
        real_save = plan_mod.Plan.saveWorkbook

        def held_save(self, *args, **kw):
            writing.set()
            assert resume.wait(timeout=120)
            return real_save(self, *args, **kw)

        monkeypatch.setattr(plan_mod.Plan, "saveWorkbook", held_save)
        result = {}
        thread = threading.Thread(target=lambda: result.update(state=run_job(job.results_dir, old_token)))
        thread.start()
        try:
            assert writing.wait(timeout=120), "the worker never reached the artifact block"
            job.finish(R.INTERRUPTED, error="stopped")  # the manager found it silent (S8)
            manager = JobManager(library)
            manager._spawn = lambda j: False  # the new attempt is not started in this test
            manager.run_again(job)
            stale = (R.SUMMARY_JSON, R.PLAN_JSON, R.RESULTS_XLSX, R.PLAN_PKL, R.RECORD_JSON)
            assert not any((job.results_dir / n).exists() for n in stale)  # the clean-up (F6)
        finally:
            resume.set()
            thread.join(timeout=180)
        # The stale worker stopped and published nothing over the cleaned folder.
        assert result.get("state") == R.INTERRUPTED
        assert artifacts(job.results_dir) == ["solve.log", "status.json", "status.lock"]
        doc = R.JobRecord.read(job.results_dir).doc
        assert doc["state"] == R.WAITING and doc["token"] != old_token


class TestInTheBackground:
    def test_a_run_solves_in_a_detached_worker(self, run, library):
        """The check of section 11: a run solves in the background, artifacts and all."""
        manager = JobManager(library)
        job = manager.enqueue(run, preset="quick")
        deadline = time.time() + 120
        while time.time() < deadline:
            job.refresh()
            if job.state in (R.DONE, R.FAILED, R.INTERRUPTED):
                break
            manager.tick()  # the queue page's own loop
            time.sleep(0.5)
        job.refresh()
        assert job.state == R.DONE, job.doc.get("error")
        assert job.doc["pid"] and job.doc["heartbeat"]  # it was a real process
        assert (job.results_dir / R.RECORD_JSON).exists()
        assert (job.results_dir / R.PLAN_PKL).exists()

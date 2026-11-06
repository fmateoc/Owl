"""The worker: one solve of one run, in its own results folder (design section 8.2).

Step 2's checks: a run solves in the background and writes the whole folder (record.json,
summary.json, plan.json, Results.xlsx, solve.log, plan.pkl); a cancelled job stops before
writing; a failed solve keeps its record (S3); two solves on different days of the plan year
give identical results; and a run is not solved outside its plan year (R1, section 8.3).
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
    kw.setdefault("plan_year", 2026)
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
        assert record["plan_year"] == 2026 and record["preset"] == "quick"
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
    def test_identical_results_within_the_plan_year(self, run, pretend_today):
        """Step 2's check, as revised (section 8.3): within its plan year a run with fixed
        claiming ages solves the same on any day."""
        outputs = []
        for day, name in (("2026-01-10", "a"), ("2026-11-20", "b")):
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
        for key in ("status", "converged", "gap", "iterations", "plan_year", "convergence"):
            assert rec_a[key] == rec_b[key]
        assert rec_a["plan_year"] == 2026

    def test_a_run_is_not_solved_outside_its_plan_year(self, run, pretend_today):
        """Queued on December 31, started after midnight: refused, and the record says why."""
        job = make_job(run, name="2026-12-31T23-59-59_quick")
        with pretend_today("2027-01-01"):
            assert run_job(job.results_dir, job.token) == R.FAILED
        record = R.read_record(job.results_dir)
        assert record["status"] == "refused" and record["plan_year"] == 2026
        assert "plan year is 2026 but this is 2027" in record["error"]
        assert R.JobRecord.read(job.results_dir).doc["error"] == record["error"]
        assert not (job.results_dir / R.SUMMARY_JSON).exists()

    def test_the_claiming_age_candidates_read_the_same_day_as_the_plan(self, run, pretend_today, monkeypatch):
        """`withSSAges` solves its candidates on a thread pool: every candidate must read the
        same date as the main thread (the date Owl reads is the process's own, not a
        thread-local setting)."""
        import threading
        from datetime import date

        from owlplanner import plan as plan_mod

        seen = []
        real = plan_mod.Plan.setSocialSecurity

        def spy(self, *args, **kw):
            seen.append((threading.current_thread().name.split("_")[0], plan_mod.date.today().isoformat()))
            return real(self, *args, **kw)

        monkeypatch.setattr(plan_mod.Plan, "setSocialSecurity", spy)
        job = make_job(run, preset="custom", options={"withSSAges": "optimize"})
        with pretend_today("2026-06-15"):
            assert run_job(job.results_dir, job.token) == R.DONE
        assert "ssages" in {name for name, _ in seen}, seen  # the search ran candidates on its pool
        assert {day for _, day in seen} == {date(2026, 6, 15).isoformat()}, seen


class TestPresetsInTheWorker:
    def test_quick_solves_every_family_on_the_loop(self, run):
        """N5: an "optimize" family in the case (here the job's own option, as the template's
        withMedicare is) is put on the loop by quick; the record says what was solved."""
        job = make_job(run, options={"withSSAges": "fixed", "withMedicare": "optimize",
                                     "breakpointMethod": "branch-and-bound"})
        assert run_job(job.results_dir, job.token) == R.DONE
        record = R.read_record(job.results_dir)
        assert record["method"]["options"]["withMedicare"] == "loop"
        assert record["method"]["options"]["breakpointMethod"] == "loop"
        assert record["method"]["breakpoint_method"] == "loop"


class TestCancelPending:
    def test_the_heartbeat_goes_on_while_a_cancel_is_pending(self, run):
        """N1: the worker stops at its next check, which a long MIP can delay; meanwhile it
        is alive and must look alive (before, the beat stopped and adoption marked the still
        running worker interrupted two minutes later)."""
        import threading

        from owlplanner.library.worker import Worker

        job = make_job(run)
        job.update(state=R.RUNNING, heartbeat="2026-01-01T00:00:00+00:00")
        job.request_cancel()
        worker = Worker(job.results_dir, job.token, heartbeat_seconds=0.05)
        thread = threading.Thread(target=worker._beat, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if R.JobRecord.read(job.results_dir).doc["heartbeat"] != "2026-01-01T00:00:00+00:00":
                    break
                time.sleep(0.05)
            doc = R.JobRecord.read(job.results_dir).doc
            assert doc["cancel"] is True and doc["heartbeat"] != "2026-01-01T00:00:00+00:00"
            assert thread.is_alive()
        finally:
            worker._beat_stop.set()
            thread.join(timeout=10)

    def test_the_heartbeat_stops_once_the_job_is_re_queued(self, run):
        import threading

        from owlplanner.library.worker import Worker

        job = make_job(run)
        job.finish(R.INTERRUPTED, error="stopped")
        worker = Worker(job.results_dir, job.token, heartbeat_seconds=0.05)
        job.requeue()  # a new token: the old worker's beat no longer writes, and ends
        thread = threading.Thread(target=worker._beat, daemon=True)
        thread.start()
        thread.join(timeout=20)
        assert not thread.is_alive()
        assert R.JobRecord.read(job.results_dir).doc["heartbeat"] is None


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
        # The old attempt's log is kept beside its record, as solve.prev.log (M1).
        assert artifacts(job.results_dir) == ["solve.prev.log", "status.json", "status.lock"]
        doc = R.JobRecord.read(job.results_dir).doc
        assert doc["state"] == R.WAITING and doc["token"] != old_token

    def test_run_again_while_the_record_is_built_leaves_no_old_record(self, run, library, monkeypatch):
        """H4: the record write is token-guarded under the job's lock, like the artifacts.

        The worker is held between its token check and the record write (where `build_record`
        runs `git`) while the job is re-queued. Before the fix the old attempt's "solved"
        record landed in the cleaned folder, pointing to a pickle the re-queue had deleted.
        """
        import threading

        job = make_job(run)
        old_token = job.token
        building, resume = threading.Event(), threading.Event()
        real_build = R.build_record

        def held_build(**kw):
            if kw.get("status") == "solved" and not building.is_set():
                building.set()
                assert resume.wait(timeout=120)
            return real_build(**kw)

        monkeypatch.setattr(R, "build_record", held_build)
        result = {}
        thread = threading.Thread(target=lambda: result.update(state=run_job(job.results_dir, old_token)))
        thread.start()
        try:
            assert building.wait(timeout=120), "the worker never reached the record"
            job.finish(R.INTERRUPTED, error="stopped")
            manager = JobManager(library)
            manager._spawn = lambda j: False
            manager.run_again(job)
        finally:
            resume.set()
            thread.join(timeout=180)
        assert not (job.results_dir / R.RECORD_JSON).exists()
        assert R.read_record(job.results_dir) is None
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


class TestTheRegretSweep:
    """I8's per-request job (the "regret" preset): the base solve, then the conversion
    regret sweep (`stresstests.run_conversion_regret_sweep`, canned here -- the sweep
    itself is tested in tests/stochastic). What the worker writes around it is checked:
    `regret.json` beside the artifacts and the summary in record.json; a failed sweep
    keeps the solve."""

    @staticmethod
    def _canned(monkeypatch, summary):
        monkeypatch.setattr("owlplanner.Plan.runConversionRegret",
                            lambda self, *args, **kw: {"canned": True})
        monkeypatch.setattr("owlplanner.summarize_conversion_regret", lambda result: summary)

    def test_the_preset_solves_then_sweeps(self, run, monkeypatch):
        summary = {"by_grid": [{"x": 0.0, "mean": 100.0}],
                   "valley": {"x": 0.0, "mean_regret": 100.0}, "n_scenarios": 3}
        self._canned(monkeypatch, summary)
        job = make_job(run, name="2026-01-01T00-00-00_regret", preset="regret")
        state = run_job(job.results_dir, job.token)
        assert state == R.DONE
        written = json.loads((job.results_dir / R.REGRET_JSON).read_text(encoding="utf-8"))
        assert written == {"canned": True}  # regret.json is the sweep itself (review AE3)
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["status"] == "solved"
        assert {k: v for k, v in record["regret"].items() if k != "person"} == summary

    def test_ag10_the_summary_names_whose_conversion(self, run, monkeypatch):
        """Review AG10: the sweep pins the first person's conversion; the record says whose."""
        self._canned(monkeypatch, {"valley": {"x": 0.0, "mean_regret": 1.0}, "n_scenarios": 1})
        job = make_job(run, name="2026-01-01T00-00-02_regret", preset="regret")
        assert run_job(job.results_dir, job.token) == R.DONE
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        names = json.loads((job.results_dir / R.PLAN_JSON).read_text(encoding="utf-8"))["individuals"]
        assert record["regret"]["person"] == names[0]

    def test_a_failed_sweep_keeps_the_solve(self, run, monkeypatch):
        def boom(*args, **kw):
            raise RuntimeError("the sweep died")

        monkeypatch.setattr("owlplanner.Plan.runConversionRegret", boom)
        job = make_job(run, name="2026-01-01T00-00-01_regret", preset="regret")
        state = run_job(job.results_dir, job.token)
        assert state == R.DONE  # the base solve stands
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["regret"] == {"error": "the sweep died"}
        assert (job.results_dir / R.PLAN_JSON).exists()
        assert not (job.results_dir / R.REGRET_JSON).exists()


class TestAgesThorough:
    """Section 8.1's "Ages, thorough": `work_sweep.py`'s whole-year sweep decides the ages
    (the sweep itself is phase 5's, now `owlplanner.work_sweep`; canned here -- it runs
    29-51 min per variant), the solve runs at them, and the sweep lands in scores.json
    (I7's claiming-age map reads it)."""

    ROW = {
        "name": "base", "free": ["Bill"], "best": [804],
        "result": {"status": "solved", "value": 82_000.0, "ages": [804], "tolerance": 1.0},
        "spread": None, "close": [], "ref": None, "loop": None,
        "ref_value": None, "loop_value": None, "eta": [],
        "sweeps": [{"pass": 0, "person": "Bill", "index": 0, "held": [804],
                    "points": [[792, 81_000.0], [804, 82_000.0]], "dips": []}],
        "results": {
            "66y0m": {"status": "solved", "value": 81_000.0, "ages": [792], "tolerance": 1.0},
            "67y0m": {"status": "solved", "value": 82_000.0, "ages": [804], "tolerance": 1.0},
        },
    }

    @pytest.fixture
    def searching_run(self, library, scenario):
        import copy

        doc = copy.deepcopy(scenario)  # the case says "let Owl choose" (R4's exception)
        doc["case"]["solver_options"]["withSSAges"] = "optimize"
        return library.save_run(name="bill searches", scenario=doc).run

    def _stub_sweep(self, monkeypatch, seen=None):
        import types

        from owlplanner.library import worker as W

        def run_variant(name, diconf, dirname, args, pool, log):
            if seen is not None:
                seen.append(args)
            return dict(self.ROW)

        monkeypatch.setattr(W, "_load_work_sweep",
                            lambda: types.SimpleNamespace(TIME_LIMIT=900.0, run_variant=run_variant))

    def test_the_sweep_lives_in_the_package(self):
        """The move (2026-11-05): `_load_work_sweep` is a plain import of `owlplanner.work_sweep`,
        one implementation shared with `run_suite.py` by name (and picklable across processes
        now, which the dynamically loaded file was not)."""
        from owlplanner import work_sweep
        from owlplanner.library import worker as W

        assert W._load_work_sweep() is work_sweep

    def test_the_sweep_decides_the_ages_and_the_solve_runs_at_them(self, searching_run, monkeypatch):
        seen = []
        self._stub_sweep(monkeypatch, seen)
        job = make_job(searching_run, name="2026-01-01T00-00-02_ages_thorough",
                       preset="ages_thorough")
        state = run_job(job.results_dir, job.token)
        assert state == R.DONE
        # The design's row: every whole-year pair scored by branch-and-bound at gap 1e-5.
        assert seen and seen[0].decider == "bb" and seen[0].gap == 1e-5
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["age_search"]["chosen"] == [67.0]  # 804 months
        assert record["age_search"]["candidates"] == [[[66.0], 81_000.0], [[67.0], 82_000.0]]
        assert record["method"]["options"]["withSSAges"] == "fixed"  # the solve pins them
        scores = json.loads((job.results_dir / R.SCORES_JSON).read_text(encoding="utf-8"))
        assert scores[0]["best"] == [804] and scores[0]["results"]

    def test_a_case_that_fixes_the_ages_just_solves(self, run, monkeypatch):
        self._stub_sweep(monkeypatch)
        job = make_job(run, name="2026-01-01T00-00-03_ages_thorough", preset="ages_thorough")
        state = run_job(job.results_dir, job.token)
        assert state == R.DONE
        assert not (job.results_dir / R.SCORES_JSON).exists()  # no search: no sweep
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["age_search"] is None

    def test_ag11_a_cancel_stops_the_sweep_between_scored_plans(self, searching_run, monkeypatch):
        """Review AG11: the sweep logs once per person pass, so the cancel check rides on the
        pool too -- a pending cancel stops before the next scored plan, not after the pass."""
        import types

        from owlplanner.library import worker as W

        scored = []
        job = make_job(searching_run, name="2026-01-01T00-00-04_ages_thorough",
                       preset="ages_thorough")

        def score(item):
            scored.append(item)
            job.request_cancel()  # the user clicks Cancel while the first plan is scored
            return item

        def run_variant(name, diconf, dirname, args, pool, log):
            pool.map(score, [1, 2, 3])  # no log line between the plans of one pass
            raise AssertionError("the pass should have stopped")

        monkeypatch.setattr(W, "_load_work_sweep",
                            lambda: types.SimpleNamespace(TIME_LIMIT=900.0, run_variant=run_variant))
        state = run_job(job.results_dir, job.token)
        assert state == R.INTERRUPTED
        assert scored == [1]

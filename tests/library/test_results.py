"""The results folder: status.json (the job record), record.json, the plan cache.

Build step 2 of `fork-notes/run-library-design.md`: the job record is on disk from the
moment the job is queued (S2), cancellation rides on a per-job token (S9), and plan.pkl is
loaded only when its hash and environment still match record.json (R10, S6).
"""

import hashlib
import json

import pytest

from owlplanner import __version__
from owlplanner.library import results as R


def make_job(tmp_path, **kw):
    kw.setdefault("run_id", "run-id")
    kw.setdefault("run_name", "bill")
    kw.setdefault("preset", "quick")
    kw.setdefault("options", {"withSSAges": "fixed"})
    kw.setdefault("plan_year", 2026)
    return R.JobRecord.create(tmp_path / "results" / "2026-01-01T00-00-00_quick", **kw)


class TestJobRecord:
    def test_it_is_on_disk_the_moment_it_is_queued(self, tmp_path):
        job = make_job(tmp_path)
        doc = json.loads((job.results_dir / R.STATUS_JSON).read_text(encoding="utf-8"))
        assert doc["state"] == R.WAITING and doc["token"] and doc["cancel"] is False
        assert doc["plan_year"] == 2026 and doc["preset"] == "quick"
        assert doc["queued"] and doc["attempts"] == 1

    def test_update_merges_onto_disk_and_keeps_a_cancel(self, tmp_path):
        job = make_job(tmp_path)
        stale = R.JobRecord.read(job.results_dir)  # a second tab's view
        job.update(cancel=True)                     # the interface cancels meanwhile
        stale.touch(last_log="Iter: 03")            # the worker's heartbeat, unaware
        fresh = R.JobRecord.read(job.results_dir)
        assert fresh.doc["cancel"] is True and fresh.doc["last_log"] == "Iter: 03"

    def test_claim_checks_the_token_and_stamps_the_process(self, tmp_path):
        job = make_job(tmp_path)
        with pytest.raises(R.ResultsError):
            job.claim("other-token", pid=1, pid_started=1)
        job.claim(job.token, pid=123, pid_started=456)
        doc = R.JobRecord.read(job.results_dir).doc
        assert doc["state"] == R.RUNNING and doc["pid"] == 123 and doc["pid_started"] == 456
        assert doc["started"] and doc["heartbeat"]

    def test_stop_reason_reads_the_record(self, tmp_path):
        job = make_job(tmp_path)
        job.claim(job.token, pid=1, pid_started=1)
        assert job.stop_reason(job.token) is None
        assert "token" in job.stop_reason("stolen")
        job.request_cancel()
        assert job.stop_reason(job.token) == "cancelled"

    def test_requeue_gives_a_fresh_token(self, tmp_path):
        job = make_job(tmp_path)
        first = job.token
        job.finish(R.INTERRUPTED, error="cancelled")
        job.requeue()
        doc = R.JobRecord.read(job.results_dir).doc
        assert doc["state"] == R.WAITING and doc["token"] != first and doc["attempts"] == 2
        assert doc["error"] is None and doc["pid"] is None

    def test_only_one_dispatcher_takes_a_waiting_job(self, tmp_path):
        """F1: two Queue fragments tick at once; the compare-and-swap lets one win."""
        job = make_job(tmp_path)
        assert job.take_for_dispatch() is True
        assert job.take_for_dispatch() is False  # the second dispatcher finds it taken
        assert R.JobRecord.read(job.results_dir).doc["state"] == R.RUNNING

    def test_a_stale_worker_never_writes_over_the_new_attempt(self, tmp_path):
        """F2: after "run again" the old token writes nothing (its wake must not clobber)."""
        job = make_job(tmp_path)
        stale_token = job.token
        job.finish(R.INTERRUPTED, error="stopped")
        job.requeue()
        assert job.update(stale_token, state=R.INTERRUPTED, error="stopped: woke up") is False
        doc = R.JobRecord.read(job.results_dir).doc
        assert doc["state"] == R.WAITING and doc["error"] is None

    def test_requeue_cleans_the_attempt_and_keeps_its_record(self, tmp_path):
        """F6: a fresh attempt starts clean; the old record is kept as record.prev.json (S3)."""
        job = make_job(tmp_path)
        (job.results_dir / R.RECORD_JSON).write_text("{}", encoding="utf-8")
        (job.results_dir / R.SUMMARY_JSON).write_text("{}", encoding="utf-8")
        (job.results_dir / R.PLAN_PKL).write_bytes(b"stale")
        job.finish(R.FAILED, error="boom")
        job.requeue()
        assert not (job.results_dir / R.SUMMARY_JSON).exists()
        assert not (job.results_dir / R.PLAN_PKL).exists()
        assert (job.results_dir / "record.prev.json").exists()
        assert not (job.results_dir / R.RECORD_JSON).exists()

    def test_requeue_keeps_the_old_log_beside_the_old_record(self, tmp_path):
        """M1: the kept record's log is kept too (the new attempt writes a fresh solve.log)."""
        job = make_job(tmp_path)
        (job.results_dir / R.RECORD_JSON).write_text("{}", encoding="utf-8")
        (job.results_dir / R.SOLVE_LOG).write_text("attempt 1\n", encoding="utf-8")
        job.finish(R.FAILED, error="boom")
        job.requeue()
        assert (job.results_dir / R.PREV_SOLVE_LOG).read_text(encoding="utf-8") == "attempt 1\n"
        assert not (job.results_dir / R.SOLVE_LOG).exists()

    def test_requeue_is_all_or_nothing(self, tmp_path, monkeypatch):
        """N4: a file that cannot be moved (Results.xlsx open in Excel, on Windows) leaves the
        folder and the job record exactly as they were, and the error names the file."""
        job = make_job(tmp_path)
        files = {R.RECORD_JSON: "{}", R.SUMMARY_JSON: "{}", R.PLAN_JSON: "{}", R.SOLVE_LOG: "log\n"}
        for name, text in files.items():
            (job.results_dir / name).write_text(text, encoding="utf-8")
        (job.results_dir / R.RESULTS_XLSX).write_bytes(b"xlsx")
        job.finish(R.FAILED, error="boom")
        before = R.JobRecord.read(job.results_dir).doc
        real_replace = R.os.replace

        def in_use(src, dst):
            if str(src).endswith(R.RESULTS_XLSX):
                raise PermissionError(13, "The process cannot access the file", str(src))
            return real_replace(src, dst)

        monkeypatch.setattr(R.os, "replace", in_use)
        with pytest.raises(R.ResultsError, match="Results.xlsx is in use"):
            job.requeue()
        monkeypatch.setattr(R.os, "replace", real_replace)
        for name, text in files.items():
            assert (job.results_dir / name).read_text(encoding="utf-8") == text
        assert (job.results_dir / R.RESULTS_XLSX).read_bytes() == b"xlsx"
        assert not (job.results_dir / R.PREV_RECORD_JSON).exists()
        assert not list(job.results_dir.glob(".requeue-*"))
        assert R.JobRecord.read(job.results_dir).doc == before  # same state, same token

    def test_an_unreadable_record_is_not_overwritten(self, tmp_path):
        """N3: update() used to write its in-memory copy back over a record it could not read,
        which could revert a cancel or a re-queue's new token."""
        job = make_job(tmp_path)
        (job.results_dir / R.STATUS_JSON).write_text("{ torn", encoding="utf-8")
        with pytest.raises(R.ResultsError):
            job.update(job.token, heartbeat=R.now_iso())
        assert (job.results_dir / R.STATUS_JSON).read_text(encoding="utf-8") == "{ torn"


class TestRecord:
    def test_the_documented_fields(self, tmp_path):
        plan_doc = {
            "objective": "maxSpending",
            "breakpoint_method": "loop",
            "engine": {"version": __version__, "commit": "abc123"},
            "convergence": {"convergence": "monotonic", "breakpoint_method": "loop", "unsettled": {}},
        }
        doc = R.build_record(
            run_id="run-id", results_id="results-id", plan_year=2026, preset="quick",
            options={"withSSAges": "fixed"}, plan_doc=plan_doc, status="solved",
            started="2026-11-03T14:02:11", finished="2026-11-03T14:02:12",
            wall_time_seconds=0.3, warnings=["something odd"], iterations=2,
            inputs_hash="feed", solver="HiGHS", gap=-1.0,
            rates={"method": "historical", "seed": None},
        )
        assert doc["record_format"] == R.RECORD_FORMAT
        assert doc["plan_year"] == 2026 and doc["inputs_hash"] == "feed"
        assert doc["solve_date"] == {"started": "2026-11-03T14:02:11", "finished": "2026-11-03T14:02:12"}
        assert doc["preset"] == "quick" and doc["method"]["options"] == {"withSSAges": "fixed"}
        assert doc["engine"]["version"] == __version__ and doc["solver"] == "HiGHS"
        assert doc["status"] == "solved" and doc["gap"] == -1.0 and doc["iterations"] == 2
        assert doc["converged"] is True and doc["convergence"]["convergence"] == "monotonic"
        assert doc["wall_time_seconds"] == 0.3 and doc["warnings"] == ["something odd"]
        assert doc["rates"] == {"method": "historical", "seed": None}
        assert doc["environment"]["python"] and "numpy" in doc["environment"]["packages"]

    def test_an_unsolved_record_is_not_converged(self):
        doc = R.build_record(
            run_id="r", results_id="x", plan_year=2026, preset="custom", options={},
            plan_doc=None, status="exception", started=None, finished=None,
            wall_time_seconds=None, warnings=[], iterations=None, error="boom",
        )
        assert doc["converged"] is False and doc["status"] == "exception" and doc["error"] == "boom"


class TestPlanCache:
    def test_it_round_trips(self, tmp_path):
        obj = {"solved": [1, 2, 3]}
        sha = R.save_plan(obj, tmp_path)
        assert sha == hashlib.sha256((tmp_path / R.PLAN_PKL).read_bytes()).hexdigest()
        record = {"plan_pkl_sha256": sha, "environment": R.environment(), "plan_pkl_code": R.code_stamp()}
        assert R.load_plan(tmp_path, record) == obj

    def test_a_wrong_hash_is_never_loaded(self, tmp_path):
        R.save_plan([1], tmp_path)
        (tmp_path / R.PLAN_PKL).write_bytes(b"not ours")
        record = {"plan_pkl_sha256": "0" * 64, "environment": R.environment(), "plan_pkl_code": R.code_stamp()}
        assert R.load_plan(tmp_path, record) is None
        assert not (tmp_path / R.PLAN_PKL).exists()  # dropped: a run from a zip keeps no pickles

    def test_a_stale_environment_is_dropped_soft(self, tmp_path):
        sha = R.save_plan([2], tmp_path)
        stale = {"plan_pkl_sha256": sha, "environment": {"python": "0.0.0", "packages": {}},
                 "plan_pkl_code": R.code_stamp()}
        assert R.load_plan(tmp_path, stale) is None
        assert not (tmp_path / R.PLAN_PKL).exists()

    def test_another_commit_is_dropped(self, tmp_path):
        """H6: a pickle restores attributes as they were; under other code it is stale."""
        sha = R.save_plan([4], tmp_path)
        other = dict(R.code_stamp(), commit="0000000")
        record = {"plan_pkl_sha256": sha, "environment": R.environment(), "plan_pkl_code": other}
        assert R.load_plan(tmp_path, record) is None
        assert not (tmp_path / R.PLAN_PKL).exists()

    def test_a_record_without_a_code_stamp_is_dropped(self, tmp_path):
        sha = R.save_plan([5], tmp_path)
        assert R.load_plan(tmp_path, {"plan_pkl_sha256": sha, "environment": R.environment()}) is None

    def test_a_pickle_that_does_not_load_is_dropped_soft(self, tmp_path):
        """H6: a renamed module raises inside pickle.loads; the cache goes, the call returns None."""
        blob = b"cno_such_module_h6\nPlan\n."  # GLOBAL: ModuleNotFoundError on load
        (tmp_path / R.PLAN_PKL).write_bytes(blob)
        record = {"plan_pkl_sha256": hashlib.sha256(blob).hexdigest(), "environment": R.environment(),
                  "plan_pkl_code": R.code_stamp()}
        assert R.load_plan(tmp_path, record) is None
        assert not (tmp_path / R.PLAN_PKL).exists()

    def test_the_record_carries_the_code_stamp(self):
        doc = R.build_record(
            run_id="r", results_id="x", plan_year=2026, preset="quick", options={},
            plan_doc=None, status="solved", started=None, finished=None, wall_time_seconds=None,
            warnings=[], iterations=None, plan_pkl_sha256="ab" * 32,
        )
        assert doc["plan_pkl_code"] == R.code_stamp()
        assert doc["plan_pkl_code"]["version"] == doc["engine"]["version"]

    def test_no_record_no_cache(self, tmp_path):
        R.save_plan([3], tmp_path)
        record = {"plan_pkl_sha256": None, "environment": R.environment(), "plan_pkl_code": R.code_stamp()}
        assert R.load_plan(tmp_path, record) is None

    def test_missing_cache_is_none(self, tmp_path):
        assert R.load_plan(tmp_path) is None


class TestTheCodeStampSurvivesAGitHiccup:
    """H6's flake, found under the parallel suite (2026-11-02): `git` failing transiently
    made one code stamp carry no diff hash and the next one carry it, so a perfectly good
    plan.pkl was dropped as stale (the plan-cache and test_open_in_owl tests flaked). Several
    processes stamp the code at once -- a server, its workers, the test suite's workers -- and
    git can time out under the load; a retry gets the answer."""

    def test_a_transient_git_failure_is_retried(self, monkeypatch):
        import subprocess

        calls = []
        real = subprocess.run

        def flaky(*args, **kw):
            calls.append(1)
            if len(calls) == 1:
                raise subprocess.SubprocessError("git timed out")
            return real(*args, **kw)

        monkeypatch.setattr(subprocess, "run", flaky)
        assert R._package_diff_sha256() is not None
        assert len(calls) == 2

    def test_a_persistent_git_failure_fails_soft(self, monkeypatch):
        import subprocess

        def dead(*args, **kw):
            raise subprocess.SubprocessError("no git")

        monkeypatch.setattr(subprocess, "run", dead)
        assert R._package_diff_sha256() is None

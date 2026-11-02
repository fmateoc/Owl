"""The job manager (design section 8.2): the queue on disk, adoption, cancellation, retry.

The checks step 2 names: a closed tab, a server restart and a still-waiting queue do not
lose a job (S2); a live worker is adopted, a dead one marked interrupted with "run again"
(S8); cancel is the per-job token first and a verified kill second (S9).
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from owlplanner.library import JobManager, JobsError, Library, ScenarioError
from owlplanner.library import results as R
from owlplanner.library.procs import kill_process, process_start_token

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


@pytest.fixture
def manager(library, monkeypatch):
    """A manager whose dispatch is recorded, never spawned (the worker is test_worker's)."""
    m = JobManager(library)
    m.dispatched = []
    monkeypatch.setattr(m, "_spawn", lambda job: m.dispatched.append(job))
    return m


def make_running_job(results_dir, *, pid, heartbeat=None, pid_started=None):
    job = R.JobRecord.create(results_dir, run_id="r", run_name="bill", preset="quick",
                             options={}, as_of="2026-01-01")
    job.update(state=R.RUNNING, pid=pid, pid_started=pid_started, heartbeat=heartbeat or R.now_iso())
    return job


def dead_pid():
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait(timeout=30)
    return proc.pid


def fresh(job):
    """The job record as it is on disk now (the manager writes through its own views)."""
    return R.JobRecord.read(job.results_dir)


class TestQueueOnDisk:
    def test_the_record_lands_before_any_dispatch(self, manager, run):
        job = manager.enqueue(run)
        assert [j.id for j in manager.dispatched] == [job.id]  # dispatched only after the record
        doc = json.loads((job.results_dir / R.STATUS_JSON).read_text(encoding="utf-8"))
        assert doc["state"] == R.WAITING and doc["token"] == job.token

    def test_a_restart_and_a_closed_tab_lose_nothing(self, library, manager, run, monkeypatch):
        job = manager.enqueue(run)  # queued and dispatched in memory only; the tab closes here

        restarted = JobManager(library)  # a new server process sees the queue on disk
        dispatched = []
        monkeypatch.setattr(restarted, "_spawn", lambda j: dispatched.append(j))
        restarted.tick()
        assert [j.id for j in dispatched] == [job.id]
        assert restarted.jobs()[0].state == R.WAITING

    def test_enqueue_records_the_preset_and_the_as_of(self, manager, run):
        job = manager.enqueue(run, preset="quick")
        assert job.doc["preset"] == "quick"
        assert job.doc["options"] == {"withSSAges": "fixed", "breakpointMethod": "loop"}
        assert job.doc["as_of"] == "2026-01-01" and job.doc["run"] == "bill"

    def test_the_queue_is_on_disk_not_in_memory(self, library, manager, run):
        queued = manager.enqueue(run)
        assert [j.id for j in JobManager(library).jobs()] == [queued.id]

    def test_enqueue_refuses_a_run_outside_its_plan_year(self, manager, run):
        scenario = json.loads((run.path / "inputs" / "scenario.json").read_text(encoding="utf-8"))
        scenario["as_of"] = "2027-03-01"
        (run.path / "inputs" / "scenario.json").write_text(json.dumps(scenario), encoding="utf-8")
        with pytest.raises(ScenarioError):
            manager.enqueue(run)

    def test_two_enqueues_at_once_get_their_own_folder(self, manager, run, monkeypatch):
        """G1: two sessions clicking Solve in the same second never share a results folder.

        The clock is frozen, so both threads pick the same candidate name, and both are held
        inside the record write, so both get past any exists() check -- only an atomic folder
        claim (the mkdir itself) gives each its own folder. Before the fix: one folder, one
        clobbered job record (probe: 2 enqueues, 1 job listed).
        """
        import threading

        from owlplanner.library import jobs as jobs_mod

        class Frozen(datetime):
            @classmethod
            def now(cls):
                return cls(2026, 11, 3, 14, 2, 11)

        monkeypatch.setattr(jobs_mod, "datetime", Frozen)
        real_create = R.JobRecord.create
        both_in = threading.Barrier(2, timeout=60)

        def slow_create(results_dir, **kw):
            both_in.wait()
            return real_create(results_dir, **kw)

        monkeypatch.setattr(R.JobRecord, "create", slow_create)
        queued = []
        threads = [threading.Thread(target=lambda: queued.append(manager.enqueue(run))) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        assert len(queued) == 2
        assert len({j.results_dir for j in queued}) == 2  # one folder each
        assert len(manager.jobs()) == 2                   # neither record lost
        for job in queued:
            assert R.JobRecord.read(job.results_dir).token == job.token


class TestAdoption:
    def test_a_live_worker_keeps_its_job(self, manager, run):
        job = make_running_job(run.path / "results" / "a", pid=os.getpid())
        manager.adopt()
        assert fresh(job).state == R.RUNNING  # adopted: the live worker carries on

    def test_a_dead_worker_is_marked_interrupted(self, manager, run):
        job = make_running_job(run.path / "results" / "b", pid=dead_pid())
        manager.adopt()
        doc = fresh(job).doc
        assert doc["state"] == R.INTERRUPTED and "died" in doc["error"]

    def test_a_silent_worker_is_marked_interrupted(self, manager, run):
        job = make_running_job(run.path / "results" / "c", pid=os.getpid())
        old = (datetime.now() - timedelta(seconds=2 * manager.heartbeat_max_age)).isoformat(timespec="seconds")
        job.update(heartbeat=old)
        manager.adopt()
        doc = fresh(job).doc
        assert doc["state"] == R.INTERRUPTED and "heartbeat" in doc["error"]

    def test_a_reused_pid_is_not_adopted(self, manager, run):
        """F7: a live PID whose start token is not the recorded one is not ours (S9)."""
        job = make_running_job(run.path / "results" / "i", pid=os.getpid(), pid_started=-1)
        manager.adopt()
        doc = fresh(job).doc
        assert doc["state"] == R.INTERRUPTED and "died" in doc["error"]


class TestClockChanges:
    """H3: stamps carry their UTC offset, so the hour the clocks fall back is not ambiguous."""

    @pytest.fixture
    def new_york(self, monkeypatch):
        import time

        if not hasattr(time, "tzset"):
            pytest.skip("time.tzset is POSIX-only")
        monkeypatch.setenv("TZ", "America/New_York")
        time.tzset()
        yield
        monkeypatch.undo()
        time.tzset()

    def test_a_fresh_heartbeat_in_the_repeated_hour_is_fresh(self, manager, run, new_york, monkeypatch):
        # 06:30:05 UTC on 2026-11-01 is 01:30:05 EST, the second pass of 01:xx that night.
        instant = datetime(2026, 11, 1, 6, 30, 5, tzinfo=timezone.utc).timestamp()
        job = make_running_job(run.path / "results" / "dst", pid=os.getpid(), heartbeat=R.now_iso(at=instant - 5))
        assert fresh(job).doc["heartbeat"] == "2026-11-01T01:30:00-05:00"
        assert fresh(job).heartbeat_age(now=instant) == 5.0  # a naive stamp read 3605 s here
        monkeypatch.setattr(R.time, "time", lambda: instant)
        manager.adopt()
        assert fresh(job).state == R.RUNNING  # the live worker keeps its job

    def test_the_queue_order_is_the_instants_not_the_text(self, manager, run):
        # 01:50 EDT comes before 01:10 EST (the clocks fell back between them); as text it sorts after.
        first = R.JobRecord.create(run.path / "results" / "z-first", run_id=run.id, run_name="bill",
                                   preset="quick", options={}, as_of="2026-01-01",
                                   queued="2026-11-01T01:50:00-04:00")
        second = R.JobRecord.create(run.path / "results" / "a-second", run_id=run.id, run_name="bill",
                                    preset="quick", options={}, as_of="2026-01-01",
                                    queued="2026-11-01T01:10:00-05:00")
        assert [j.id for j in manager.jobs()] == [first.id, second.id]

    def test_stamps_carry_their_offset(self):
        stamp = R.now_iso()
        assert datetime.fromisoformat(stamp).utcoffset() is not None
        assert R.stamp_seconds("not a date") is None and R.stamp_seconds(None) is None


class TestTicker:
    """H5: the queue moves with no page open; the server's manager ticks on its own."""

    def test_a_waiting_job_is_dispatched_with_no_page_ticking(self, library, run):
        import time

        manager = JobManager(library)
        spawned = []
        manager._spawn = lambda job: job.take_for_dispatch() and (spawned.append(job.id) or True)
        # Queued before a restart: nothing has ticked it in this process.
        job = R.JobRecord.create(run.path / "results" / "queued-earlier", run_id=run.id, run_name="bill",
                                 preset="quick", options={}, as_of="2026-01-01")
        assert manager.start_ticker(interval=0.05)
        try:
            assert not JobManager(library).start_ticker(interval=0.05)  # one ticker per folder
            deadline = time.monotonic() + 20
            while not spawned and time.monotonic() < deadline:
                time.sleep(0.05)
        finally:
            manager.stop_ticker()
        assert spawned == [job.id]
        assert fresh(job).state == R.RUNNING

    def test_a_tick_that_raises_does_not_stop_the_ticker(self, library, monkeypatch):
        import time

        manager = JobManager(library)
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise R.ResultsError("a lock timeout")

        monkeypatch.setattr(manager, "tick", flaky)
        assert manager.start_ticker(interval=0.02)
        try:
            deadline = time.monotonic() + 20
            while len(calls) < 3 and time.monotonic() < deadline:
                time.sleep(0.02)
        finally:
            manager.stop_ticker()
        assert len(calls) >= 3


class TestCancel:
    def test_a_waiting_job_stops_at_once(self, manager, run):
        job = manager.enqueue(run)
        manager.cancel(job)
        assert job.state == R.INTERRUPTED and job.doc["error"] == "cancelled"

    def test_a_running_job_is_cancelled_by_token(self, manager, run):
        job = make_running_job(run.path / "results" / "d", pid=os.getpid(), pid_started=-1)
        manager.cancel(job)  # cooperative only: -1 is not this process's start token
        assert job.doc["cancel"] is True and job.state == R.RUNNING

    def test_a_force_cancel_kills_only_the_recorded_process(self, manager, run):
        dummy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            job = make_running_job(run.path / "results" / "e", pid=dummy.pid,
                                   pid_started=process_start_token(dummy.pid))
            manager.cancel(job, force=True)
            assert job.state == R.INTERRUPTED
            dummy.wait(timeout=30)  # killed: it was the recorded process (S9)
        finally:
            if dummy.poll() is None:
                dummy.kill()
                dummy.wait(timeout=30)

    def test_a_plain_cancel_never_kills(self, manager, run):
        """N1: the Queue's Cancel is cooperative; only Kill (force) stops the process."""
        dummy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            job = make_running_job(run.path / "results" / "coop", pid=dummy.pid,
                                   pid_started=process_start_token(dummy.pid))
            assert manager.cancel(job) is False
            doc = fresh(job).doc
            assert doc["cancel"] is True and doc["state"] == R.RUNNING
            assert dummy.poll() is None  # the worker stops itself at its next check
        finally:
            dummy.kill()
            dummy.wait(timeout=30)

    def test_a_kill_leaves_a_record_and_no_staging(self, manager, run):
        """N1: a killed worker cannot write its own record (S3, F6), nor drop its staging."""
        dummy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            job = make_running_job(run.path / "results" / "killed", pid=dummy.pid,
                                   pid_started=process_start_token(dummy.pid))
            staging = job.results_dir / ".attempt-0123abcd"
            staging.mkdir()
            (staging / R.RESULTS_XLSX).write_bytes(b"half")
            assert manager.cancel(job, force=True) is True
            dummy.wait(timeout=30)
            record = R.read_record(job.results_dir)
            assert record["status"] == "interrupted" and record["error"].startswith("killed")
            assert record["run_id"] == "r" and record["as_of"] == "2026-01-01"
            assert not staging.exists()
            doc = fresh(job).doc
            assert doc["state"] == R.INTERRUPTED and doc["error"].startswith("killed")
        finally:
            if dummy.poll() is None:
                dummy.kill()
                dummy.wait(timeout=30)

    def test_a_kill_keeps_a_record_the_worker_already_wrote(self, manager, run):
        dummy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            job = make_running_job(run.path / "results" / "late", pid=dummy.pid,
                                   pid_started=process_start_token(dummy.pid))
            (job.results_dir / R.RECORD_JSON).write_text('{"status": "solved"}', encoding="utf-8")
            assert manager.cancel(job, force=True) is True
            assert R.read_record(job.results_dir) == {"status": "solved"}
        finally:
            if dummy.poll() is None:
                dummy.kill()
                dummy.wait(timeout=30)

    def test_a_reused_pid_is_never_killed(self, manager, run):
        dummy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            job = make_running_job(run.path / "results" / "f", pid=dummy.pid, pid_started=-1)
            manager.cancel(job, force=True)
            assert job.doc["cancel"] is True and job.state == R.RUNNING
            assert dummy.poll() is None  # untouched: the start token said it is not ours
            assert kill_process(job.doc["pid"], job.doc["pid_started"]) is False
        finally:
            dummy.kill()
            dummy.wait(timeout=30)


class TestRunAgain:
    def test_an_interrupted_job_requeues_under_a_new_token(self, manager, run):
        job = manager.enqueue(run)
        first = job.token
        manager.cancel(job)
        manager.run_again(job)
        doc = R.JobRecord.read(job.results_dir).doc
        assert doc["state"] == R.WAITING and doc["token"] != first and doc["attempts"] == 2

    def test_a_running_job_is_not_run_again(self, manager, run):
        job = make_running_job(run.path / "results" / "g", pid=os.getpid())
        with pytest.raises(JobsError):
            manager.run_again(job)


class TestStopAll:
    def test_everything_is_cancelled(self, manager, run):
        waiting = manager.enqueue(run)
        running = make_running_job(run.path / "results" / "h", pid=os.getpid(), pid_started=-1)
        manager.stop_all()
        assert fresh(waiting).state == R.INTERRUPTED
        # Cooperative for a process that is not ours to kill (the token stops its worker).
        doc = fresh(running).doc
        assert doc["state"] == R.RUNNING and doc["cancel"] is True

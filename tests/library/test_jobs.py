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
from owlplanner.library import jobs as jobs_module
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
                             options={}, plan_year=2026)
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

    def test_enqueue_records_the_preset_and_the_plan_year(self, manager, run):
        job = manager.enqueue(run, preset="quick")
        assert job.doc["preset"] == "quick"
        assert job.doc["options"] == {"withSSAges": "fixed", "breakpointMethod": "loop"}
        assert job.doc["plan_year"] == 2026 and job.doc["run"] == "bill"

    def test_the_queue_is_on_disk_not_in_memory(self, library, manager, run):
        queued = manager.enqueue(run)
        assert [j.id for j in JobManager(library).jobs()] == [queued.id]

    def test_enqueue_refuses_a_run_outside_its_plan_year(self, manager, run):
        scenario = json.loads((run.path / "inputs" / "scenario.json").read_text(encoding="utf-8"))
        scenario["plan_year"] = 2025  # last year's run, solved in 2026 (the suite's date)
        (run.path / "inputs" / "scenario.json").write_text(json.dumps(scenario), encoding="utf-8")
        with pytest.raises(ScenarioError, match="plan year is 2025 but this is 2026"):
            manager.enqueue(run)
        assert manager.jobs() == []  # nothing queued

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


class TestCores:
    """Performance review, 2026-11-11: the queue counts cores. A job states how many solves it
    runs at once when it can, the queue gives it that or all it has at dispatch and counts it
    while the job runs; the worker sizes its pool by its record."""

    @pytest.fixture
    def wide(self, library, monkeypatch):
        """A queue with four cores whose dispatch is the record's own swap, no worker started."""
        m = JobManager(library, cores=4)
        m.dispatched = []

        def spawn(job):
            if job.take_for_dispatch(m.share(job)):
                job.update(pid=os.getpid(), pid_started=process_start_token(os.getpid()))
                m.dispatched.append(job.id)
                return True
            return False

        monkeypatch.setattr(m, "_spawn", spawn)
        return m

    def states(self, manager):
        return [(job.doc["preset"], job.state, job.doc.get("cores")) for job in manager.jobs()]

    def test_one_core_is_one_job_at_a_time_as_before(self, library, run, monkeypatch):
        m = JobManager(library)
        monkeypatch.setattr(m, "_spawn", lambda job: job.take_for_dispatch(m.share(job))
                            and job.update(pid=os.getpid(), pid_started=process_start_token(os.getpid())))
        assert m.cores == 1
        for preset in ("ages_thorough", "quick", "ages"):
            m.enqueue(run, preset=preset)
        assert self.states(m) == [("ages_thorough", R.RUNNING, 1), ("quick", R.WAITING, None),
                                  ("ages", R.WAITING, None)]

    def test_single_solves_run_side_by_side_up_to_the_cores(self, wide, run):
        for _ in range(6):
            wide.enqueue(run, preset="quick")
        states = [state for _, state, _ in self.states(wide)]
        assert states == [R.RUNNING] * 4 + [R.WAITING] * 2
        assert all(cores == 1 for _, state, cores in self.states(wide) if state == R.RUNNING)

    def test_a_job_states_what_it_wants_and_gets_what_fits(self, wide, run, library):
        job = wide.enqueue(run, preset="ages")
        assert fresh(job).cores_wanted == 5 and fresh(job).cores == 4  # five wanted, four there are
        assert JobManager(library, cores=8).share(job) == 5
        assert JobManager(library, cores=1).share(job) == 1
        sweep = R.JobRecord.create(run.path / "results" / "x_ages_thorough", run_id=run.id, run_name=run.name,
                                   preset="ages_thorough", options={}, plan_year=2026, cores_wanted=0)
        assert JobManager(library, cores=6).share(sweep) == 6  # 0: as many as the queue has

    def test_enqueue_records_what_each_preset_wants(self, wide, run):
        wanted = {preset: wide.enqueue(run, preset=preset).cores_wanted
                  for preset in ("quick", "decision", "decision_exact", "custom", "regret", "ages", "ages_thorough")}
        assert wanted == {"quick": 1, "decision": 1, "decision_exact": 1, "custom": 1, "regret": 2,
                          "ages": 5, "ages_thorough": 0}

    def test_a_job_that_does_not_fit_waits_and_nothing_jumps_it(self, wide, run):
        """First come, first served: a sweep that wants every core waits for the running solve
        to end, and the quick solve queued behind it waits too, though it would fit."""
        first = wide.enqueue(run, preset="quick")
        sweep = wide.enqueue(run, preset="ages_thorough")
        wide.enqueue(run, preset="quick")
        assert self.states(wide) == [("quick", R.RUNNING, 1), ("ages_thorough", R.WAITING, None),
                                     ("quick", R.WAITING, None)]
        fresh(first).finish(R.DONE)
        wide.tick()
        assert self.states(wide) == [("quick", R.DONE, 1), ("ages_thorough", R.RUNNING, 4),
                                     ("quick", R.WAITING, None)]
        fresh(sweep).finish(R.DONE)
        wide.tick()
        assert self.states(wide)[2] == ("quick", R.RUNNING, 1)

    def test_the_running_jobs_shares_are_what_is_counted(self, wide, run):
        """A regret job counts for two (its thread pool), so two of them and no more fit
        beside... nothing: 2 + 2 = 4; the third job waits."""
        for _ in range(2):
            wide.enqueue(run, preset="regret")
        wide.enqueue(run, preset="quick")
        assert [(state, cores) for _, state, cores in self.states(wide)] == [
            (R.RUNNING, 2), (R.RUNNING, 2), (R.WAITING, None)]

    def test_the_count_survives_a_restart(self, wide, run, library, monkeypatch):
        """The shares are in the records: a new server over the same folder counts the jobs
        the old one started and dispatches nothing on top of them."""
        wide.enqueue(run, preset="ages")  # takes the four cores
        waiting = wide.enqueue(run, preset="quick")
        restarted = JobManager(library, cores=4)
        monkeypatch.setattr(restarted, "_spawn", lambda job: pytest.fail("no core is free"))
        restarted.tick()
        assert fresh(waiting).state == R.WAITING

    def test_a_record_from_before_the_count_is_one_core(self, wide, run):
        job = make_running_job(run.path / "results" / "2026-01-01T00-00-00_quick", pid=os.getpid(),
                               pid_started=process_start_token(os.getpid()))
        doc = dict(job.doc)
        doc.pop("cores"), doc.pop("cores_wanted")
        (job.results_dir / R.STATUS_JSON).write_text(json.dumps(doc), encoding="utf-8")
        assert fresh(job).cores == 1 and fresh(job).cores_wanted == 1
        for _ in range(4):
            wide.enqueue(run, preset="quick")
        assert [state for _, state, _ in self.states(wide)].count(R.RUNNING) == 4  # the old job and three

    def test_run_again_gets_a_new_share(self, wide, run, library):
        job = wide.enqueue(run, preset="ages")
        assert fresh(job).cores == 4
        fresh(job).finish(R.INTERRUPTED, error="stopped")
        fresh(job).requeue()
        assert fresh(job).cores == 1 and fresh(job).doc["cores"] is None  # waiting: no share yet
        narrow = JobManager(library, cores=2)
        narrow._spawn = lambda j: j.take_for_dispatch(narrow.share(j))
        narrow.tick()
        assert fresh(job).doc["cores"] == 2

    def test_the_interface_s_cores(self, monkeypatch):
        monkeypatch.setattr(jobs_module.os, "cpu_count", lambda: 8)
        monkeypatch.delenv(jobs_module.CORES_ENV, raising=False)
        assert jobs_module.default_cores() == 4  # half the logical cores
        monkeypatch.setattr(jobs_module.os, "cpu_count", lambda: 1)
        assert jobs_module.default_cores() == 1
        monkeypatch.setattr(jobs_module.os, "cpu_count", lambda: None)
        assert jobs_module.default_cores() == 1
        monkeypatch.setenv(jobs_module.CORES_ENV, "6")
        assert jobs_module.default_cores() == 6
        monkeypatch.setenv(jobs_module.CORES_ENV, "0")
        assert jobs_module.default_cores() == 1  # at least one
        monkeypatch.setenv(jobs_module.CORES_ENV, "many")
        monkeypatch.setattr(jobs_module.os, "cpu_count", lambda: 12)
        assert jobs_module.default_cores() == 6  # an unreadable setting is no setting

    def test_a_tick_reads_the_library_once(self, wide, run, monkeypatch):
        """Performance review P6: a tick scanned every run and every job record three times."""
        wide.enqueue(run)
        scans = []
        real = wide.jobs
        monkeypatch.setattr(wide, "jobs", lambda *a, **k: scans.append(1) or real(*a, **k))
        wide.tick()
        assert len(scans) == 1


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
                                   preset="quick", options={}, plan_year=2026,
                                   queued="2026-11-01T01:50:00-04:00")
        second = R.JobRecord.create(run.path / "results" / "a-second", run_id=run.id, run_name="bill",
                                    preset="quick", options={}, plan_year=2026,
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

        def spawn(job):
            # What _spawn does, with this live test process standing in for the worker: take
            # the job, then record the worker's PID and start token. Without the record, any
            # tick before stop_ticker() runs adopt(), which reads the PID-less running job as
            # dead and interrupts it (the race that failed the full suite once, 2026-11-03).
            if not job.take_for_dispatch():
                return False
            job.update(pid=os.getpid(), pid_started=process_start_token(os.getpid()))
            spawned.append(job.id)
            return True

        manager._spawn = spawn
        # Queued before a restart: nothing has ticked it in this process.
        job = R.JobRecord.create(run.path / "results" / "queued-earlier", run_id=run.id, run_name="bill",
                                 preset="quick", options={}, plan_year=2026)
        assert manager.start_ticker(interval=0.05)
        try:
            assert not JobManager(library).start_ticker(interval=0.05)  # one ticker per folder
            deadline = time.monotonic() + 20
            while not spawned and time.monotonic() < deadline:
                time.sleep(0.05)
            time.sleep(0.3)  # several more ticks: a dispatched job with a live worker stays running
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
            assert record["run_id"] == "r" and record["plan_year"] == 2026
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


class TestDeleteRun:
    """Review 3, W4: deleting a run under a live solve used to move the folder to trash/ while
    its worker kept solving, untracked by the queue."""

    def test_a_run_with_a_waiting_solve_is_not_deleted(self, library, manager, run):
        manager.enqueue(run)
        with pytest.raises(JobsError, match="still waiting"):
            manager.delete_run(run)
        assert run.path.is_dir() and [r.id for r in library.runs()] == [run.id]

    def test_a_run_with_a_running_solve_is_not_deleted(self, library, manager, run):
        make_running_job(run.path / "results" / "d", pid=os.getpid(),
                         pid_started=process_start_token(os.getpid()))
        with pytest.raises(JobsError, match="Cancel it on the Queue page first"):
            manager.delete_run(run)
        assert run.path.is_dir()

    def test_once_cancelled_the_run_goes_to_the_trash(self, library, manager, run):
        job = manager.enqueue(run)
        manager.cancel(job)
        target = manager.delete_run(run)
        assert target.parent.name == "trash" and not run.path.exists()
        assert library.runs() == []

    def test_a_run_with_no_solve_is_deleted(self, library, manager, run):
        target = manager.delete_run(run.id)
        assert target.is_dir() and library.runs() == []


def test_jobs_of_one_second_keep_the_order_they_were_queued_in(tmp_path, monkeypatch):
    """Local-use review D4: `queued` is whole seconds, so jobs of two runs queued by one click
    tied on it and on the folder name, and were dispatched in the library's run order: a
    what-if queued before its parent waited behind it. `queued_at` keeps the fractions."""
    from owlplanner.library import JobManager, Library, import_case
    from owlplanner.library import results as R
    from owlplanner.library.jobs import _queued_order

    lib = Library.open(tmp_path / "library")
    older = lib.save_run(name="parent", scenario=import_case("examples/Case_bill.toml")).run
    scenario = import_case("examples/Case_bill.toml")
    scenario["case"]["basic_info"]["life_expectancy"] = [88]
    newer = lib.save_run(name="what-if", scenario=scenario, parent=older.id).run
    monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)
    monkeypatch.setattr(R, "now_iso", lambda at=None: "2026-01-01T10:00:00+00:00")  # one second
    manager = JobManager(lib)
    first = manager.enqueue(newer, preset="quick")
    second = manager.enqueue(older, preset="quick")
    assert first.id == second.id and first.doc["queued"] == second.doc["queued"]
    assert [job.doc["run_id"] for job in manager.jobs()] == [newer.id, older.id]
    # A record from before `queued_at`: the readable stamp orders it, as it did.
    old = dict(first.doc, queued="2026-01-01T09:59:59+00:00")
    old.pop("queued_at")
    assert _queued_order(R.JobRecord(first.results_dir, old)) < _queued_order(second)

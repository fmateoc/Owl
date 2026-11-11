"""The job manager: one queue per server, and the queue on disk (design section 8.2).

A job is one solve of one run in a fresh interpreter. The job record (`status.json`, S2) is
in the run's results folder from the moment the job is queued, so a closed tab, a server
restart or a still-waiting queue never loses one: this manager adopts live workers (a live
PID with a heartbeat under two minutes old), marks dead ones interrupted with "run again",
and dispatches waiting jobs, first come first served, while they fit the cores the queue
may use (`cores`, default 1: one job at a time).

Cores (performance review, 2026-11-11). A job is not always one solve: the claiming-age
presets score several plans, and can score them side by side. So each job states how many
solves it runs at once when it can (`cores_wanted` in its record, from
`presets.cores_wanted`), the queue gives it that or all it has, whichever is less, when it
dispatches it (`cores` in the record), and counts what the running jobs were given against
its own cores. The worker sizes its pool by its record. The count lives in the records, so it
survives a server restart with the jobs it counts, and the processes of a library's jobs stay
within the queue's cores by construction: six solves on four cores cost 17-18% more CPU on
the synthetic household. A job that does not fit waits, and so does everything queued after
it (nothing jumps the queue): with the cores free a waiting job always fits, so none waits
longer than the running jobs take.

Workers are started detached in their own session (`start_new_session` / DETACHED_PROCESS)
so they survive the server; cancellation is the per-job token first (the worker checks it
before every step and on every heartbeat) and a verified kill second (`kill_process` only
against the recorded process start token, S9). One manager per server process: hold it in
`st.cache_resource`, never per session.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import List

from . import results as R
from .casefiles import check_plan_year
from .presets import SOLVE_PRESETS, cores_wanted, preset_options
from .procs import kill_process, pid_alive, process_start_token
from .store import Library, RunInfo

RESULTS_DIR = "results"

# The interface's setting for the queue's cores: a whole number in this environment variable.
CORES_ENV = "OWL_LIBRARY_CORES"


def default_cores() -> int:
    """The cores the interface's queue uses: `OWL_LIBRARY_CORES`, else half the computer's.

    `os.cpu_count()` counts logical cores, and two solves on the two threads of one physical
    core are not two cores' worth; half of it is the physical count on most desktop
    processors, and leaves the browser and the server room on the others. Not measured on any
    computer but the four-core container the review ran in: set the variable after timing a
    batch (four solves at once cost 5% of wall each there; six cost 17-18% of CPU).
    """
    raw = os.environ.get(CORES_ENV, "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass  # an unreadable setting is no setting
    return max(1, (os.cpu_count() or 2) // 2)


def _queued_order(job: R.JobRecord):
    """Queue order, first come first served: the queued instant (not its text, H3), then the
    folder name.

    `queued_at` is the instant with its fractions. `queued`, the stamp people read, is whole
    seconds: jobs of two runs queued by one click tied on it and on the folder name (the same
    "<second>_<preset>" in each run), and came out in the library's run order -- a what-if
    queued before its parent was solved after it (local-use review D4). A record written
    before `queued_at` existed falls back on `queued`.
    """
    at = job.doc.get("queued_at")
    if not isinstance(at, (int, float)) or isinstance(at, bool):
        at = R.stamp_seconds(job.doc.get("queued")) or 0.0
    return (float(at), job.id)


# One ticker thread per library folder per process (H5). A Streamlit code reload can build a
# second manager over the same folder; it then finds the first one's ticker still running.
_TICKERS = {}
_TICKERS_LOCK = threading.Lock()
TICK_SECONDS = 2.0


class JobsError(RuntimeError):
    """A job cannot be queued or found."""


class JobManager:
    """The queue of solves over one library folder."""

    def __init__(self, library: Library, *, cores: int = 1,
                 heartbeat_max_age: float = R.HEARTBEAT_MAX_AGE, worker_argv=None):
        self.library = library
        self.cores = max(1, int(cores))  # what the running jobs may use together
        self.heartbeat_max_age = float(heartbeat_max_age)
        self.worker_argv = worker_argv  # tests substitute their own command
        self._tick_lock = threading.Lock()  # Queue fragments tick concurrently (R5 is one manager)

    # -- the queue on disk ---------------------------------------------

    def job_dirs(self, run: "RunInfo | str | None" = None) -> List[Path]:
        """Every results folder with a job record, oldest first."""
        runs = [run if isinstance(run, RunInfo) else self.library.get(run)] if run else self.library.runs()
        found = []
        for info in runs:
            results = info.path / RESULTS_DIR
            if not results.is_dir():
                continue
            for folder in sorted(results.iterdir()):
                if folder.is_dir() and R.JobRecord.exists(folder):
                    found.append(folder)
        return found

    def jobs(self, run: "RunInfo | str | None" = None) -> List[R.JobRecord]:
        out = []
        for folder in self.job_dirs(run):
            try:
                out.append(R.JobRecord.read(folder))
            except R.ResultsError:
                continue  # a damaged record is skipped, never fatal (V7's rule)
        out.sort(key=_queued_order)
        return out

    def get(self, results_dir) -> R.JobRecord:
        return R.JobRecord.read(results_dir)

    # -- queueing ------------------------------------------------------

    def enqueue(self, run: "RunInfo | str", *, preset: str = "quick", options=None) -> R.JobRecord:
        """Queue one solve of a run: the job record lands on disk before any dispatch (S2).

        The run's plan year is checked here (R1): the library refuses to queue a run outside
        its plan year (the worker checks again when it starts). Returns the waiting record.
        """
        if preset not in SOLVE_PRESETS:
            raise JobsError(f"unknown preset {preset!r}: this build runs {SOLVE_PRESETS}")
        info = run if isinstance(run, RunInfo) else self.library.get(run)
        scenario = self.library.scenario(info)
        plan_year = check_plan_year(scenario)  # raises ScenarioError outside the plan year (R1)
        overrides = preset_options(preset, options)

        results_root = info.path / RESULTS_DIR
        results_root.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        folder = results_root / f"{stamp}_{preset}"
        n = 1
        while True:
            try:
                # The claim is the mkdir itself (G1): two sessions clicking Solve in the same
                # second pick the same candidate name, and only one can create it. A check
                # before the create (the old `folder.exists()`) left a window where both took
                # one folder and one job record was clobbered.
                folder.mkdir()
                break
            except FileExistsError:
                n += 1
                folder = results_root / f"{stamp}_{preset}-{n}"

        job = R.JobRecord.create(
            folder,
            run_id=info.id,
            run_name=info.name,
            preset=preset,
            options=overrides,
            plan_year=plan_year,
            cores_wanted=cores_wanted(preset),
        )
        self.tick()
        return job

    # -- the manager loop ----------------------------------------------

    def tick(self) -> List[R.JobRecord]:
        """Adopt what runs, interrupt what died, dispatch what waits. Returns dispatched."""
        with self._tick_lock:
            jobs = self.jobs()  # one scan of the library a tick (it was three)
            self.adopt(jobs)  # a job it interrupts reads so in this list: `finish` updates it
            used = sum(job.cores for job in jobs if job.state == R.RUNNING)
            dispatched = []
            for job in jobs:  # in queue order (`_queued_order`)
                if job.state != R.WAITING:
                    continue
                share = self.share(job)
                if used + share > self.cores:
                    break  # first come, first served: nothing jumps a job waiting for room
                if self._spawn(job):  # one dispatcher takes a waiting job (F1)
                    dispatched.append(job)
                    used += share
            return dispatched

    def share(self, job: R.JobRecord) -> int:
        """The cores a job gets at dispatch: what it wants, or all the queue has if that is less."""
        wanted = job.cores_wanted
        return self.cores if wanted == 0 else max(1, min(wanted, self.cores))

    def adopt(self, jobs=None) -> None:
        """Start-up rule (S8): live, ours and fresh is adopted; a dead or silent one is interrupted."""
        for job in (self.jobs() if jobs is None else jobs):
            if job.state != R.RUNNING:
                continue
            pid = job.doc.get("pid")
            alive = pid_alive(pid)
            stamped = job.doc.get("pid_started")
            # A reused PID is not ours (S9): the start token must be the recorded one.
            ours = stamped is None or process_start_token(pid) == stamped
            age = job.heartbeat_age()
            fresh = age is not None and age < self.heartbeat_max_age
            if alive and ours and fresh:
                continue  # adopted: a live worker keeps its job
            if not alive or not ours:
                job.finish(R.INTERRUPTED, error="the worker died")
            else:
                job.finish(R.INTERRUPTED, error="the worker's heartbeat stopped")

    def _spawn(self, job: R.JobRecord) -> bool:
        """Start one worker for a waiting job, with its share of the cores in its record;
        False when another dispatcher took it (F1)."""
        if not job.take_for_dispatch(self.share(job)):
            return False
        argv = self.worker_argv or [
            sys.executable, "-m", "owlplanner.library.worker", str(job.results_dir), job.token,
        ]
        kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True  # outlives the server (section 8.2)
        proc = subprocess.Popen([str(a) for a in argv], **kwargs)
        job.update(pid=proc.pid, pid_started=process_start_token(proc.pid))
        return True

    def start_ticker(self, interval: float = TICK_SECONDS) -> bool:
        """Tick in a background daemon thread, so the queue moves with no page open (H5).

        Without it the queue advanced only on `enqueue`, `run_again` and the Queue page's own
        refresh: a second waiting job stayed waiting once the tab closed. The server holds one
        manager (`st.cache_resource`) and starts its ticker once; the tick lock serializes the
        ticker with the pages' own ticks, and dispatch is a compare-and-swap anyway (F1).
        Returns False when this process already ticks this library folder.
        """
        key = str(Path(self.library.root).resolve())
        with _TICKERS_LOCK:
            running = _TICKERS.get(key)
            if running is not None and running[0].is_alive():
                return False
            stop = threading.Event()
            thread = threading.Thread(target=self._tick_forever, args=(stop, float(interval)),
                                      name="owl-library-ticker", daemon=True)
            _TICKERS[key] = (thread, stop)
            thread.start()
            return True

    def stop_ticker(self) -> None:
        """Stop this library folder's ticker thread, if one runs (tests, a clean shutdown)."""
        key = str(Path(self.library.root).resolve())
        with _TICKERS_LOCK:
            running = _TICKERS.pop(key, None)
        if running is not None:
            running[1].set()
            running[0].join(timeout=10.0)

    def _tick_forever(self, stop: threading.Event, interval: float) -> None:
        while not stop.wait(interval):
            if not Path(self.library.root).exists():
                return  # the library folder is gone (a test's temporary library): nothing to tick
            try:
                self.tick()
            except Exception:  # a damaged folder or a lock timeout must not stop the queue
                traceback.print_exc(file=sys.stderr)

    # -- cancelling ----------------------------------------------------

    def cancel(self, job: "R.JobRecord | str", *, force: bool = False) -> bool:
        """Cancel a job: cooperative token first, verified kill when forced (S9).

        The cooperative cancel lets the worker stop at its next step or log line and write
        its own "interrupted" record (S3, F6). A forced cancel kills the recorded process
        (only against its start token) and then writes that record itself, with what the
        job record knows, and drops the staged artifacts the worker could not clean up (N1).
        Returns whether the job was stopped now (a waiting job, or a verified kill).
        """
        job = job if isinstance(job, R.JobRecord) else self.get(job)
        job.refresh()  # act on the record as it is now, not as a page last read it
        if job.state == R.WAITING:
            job.finish(R.INTERRUPTED, error="cancelled")
            return True
        if job.state != R.RUNNING:
            return False
        job.request_cancel()
        if not force:
            return False
        if not kill_process(job.doc.get("pid"), job.doc.get("pid_started")):
            return False  # not ours to kill (PID reused or unknown): the token stops it
        token = job.token
        finished = R.now_iso()
        if R.read_record(job.results_dir) is None:
            doc = job.doc
            job.publish_record(token, R.build_record(
                run_id=str(doc.get("run_id") or ""), results_id=job.id, plan_year=job.plan_year,
                preset=str(doc.get("preset") or ""), options=doc.get("options") or {},
                plan_doc=None, status="interrupted", started=doc.get("started"), finished=finished,
                wall_time_seconds=None, warnings=[], iterations=None,
                error="killed: cancelled from the queue",
            ))
        R.drop_staging(job.results_dir)
        job.finish(R.INTERRUPTED, error="killed: cancelled from the queue", token=token)
        return True

    def run_again(self, job: "R.JobRecord | str") -> R.JobRecord:
        """Re-run an interrupted or failed job in the same results folder (S8).

        A fresh token: a worker of the previous attempt that wakes from sleep sees its job
        is no longer its own and stops, so "run again" never leaves two workers on one run.
        """
        job = job if isinstance(job, R.JobRecord) else self.get(job)
        if job.state not in (R.INTERRUPTED, R.FAILED):
            raise JobsError(f"only an interrupted or failed job is run again (it is {job.state!r})")
        job.requeue()
        self.tick()
        return job

    def delete_run(self, run: "RunInfo | str") -> Path:
        """Move a run to trash/ (`Library.delete_run`), refused while one of its solves is live.

        A waiting or running job lives in the run's own folder: moving it took the job out of
        the queue (the manager scans `runs/` only) while its worker kept solving, uncounted by
        the queue's cores and with nothing left on the Queue page to cancel; the trashed record
        then said "running" forever (step-3 review 3, W4). The check and the move happen under
        the tick lock, so the ticker cannot dispatch a waiting job in between.
        """
        info = run if isinstance(run, RunInfo) else self.library.get(run)
        with self._tick_lock:
            live = [job for job in self.jobs(info) if job.state in (R.WAITING, R.RUNNING)]
            if live:
                names = ", ".join(f"{job.id} ({job.state})" for job in live)
                raise JobsError(
                    f"{info.name} has a solve still {live[0].state}: {names}. Cancel it on the "
                    "Queue page first, then delete the run."
                )
            return self.library.delete_run(info)

    def stop_all(self) -> None:
        """Every waiting and running job is cancelled; running ones are killed (S9)."""
        for job in self.jobs():
            if job.state in (R.WAITING, R.RUNNING):
                self.cancel(job, force=True)

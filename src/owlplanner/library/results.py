"""One results folder per solve: status.json, record.json, the artifacts, the plan cache.

Layout of a run's results folder (`fork-notes/run-library-design.md`, section 5):

    runs/<run>/results/
        2026-11-03T14-02-11_quick/       <queued>_<preset>, one folder per solve
            status.json                  the job record (S2): on disk from the moment the job
                                         is queued -- state, PID, heartbeat, token, last log
            record.json                  what solved how, when, for which plan year: method
                                         preset and options, Owl version and commit, solver,
                                         status, gap, iterations, converged, wall time,
                                         warnings, rate method and seed, Python and packages
            summary.json                 plan_metrics (export.plan_metrics)
            plan.json                    per-year arrays (cli.formatters.plan_to_dict)
            Results.xlsx                 the workbook owlcli writes
            solve.log                    the solve's own log
            plan.pkl                     cache of the solved Plan: loaded only when its sha256
                                         matches record.json and the environment still matches
                                         (S6, R10); dropped when stale

Rules: a worker writes only inside its own results folder (section 5), every file is written
to a temporary name and renamed, and a failed solve keeps its record (S3). `plan.pkl` is a
cache only: a stale one costs one re-solve, never the record (durable formats first).
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import platform
import secrets
import shutil
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .scenario import pretty_json

STATUS_JSON = "status.json"
STATUS_LOCK = "status.lock"
RECORD_JSON = "record.json"
SUMMARY_JSON = "summary.json"
PLAN_JSON = "plan.json"
RESULTS_XLSX = "Results.xlsx"
SOLVE_LOG = "solve.log"
PLAN_PKL = "plan.pkl"
PREV_RECORD_JSON = "record.prev.json"  # the previous attempt's record, kept by "run again"
PREV_SOLVE_LOG = "solve.prev.log"      # and its log (M1)

JOB_FORMAT = 1
RECORD_FORMAT = 1

# Job states (section 8.2): waiting, running (PID + heartbeat), done, failed, interrupted.
WAITING = "waiting"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
INTERRUPTED = "interrupted"

# A heartbeat older than this is dead (S8); the manager adopts only fresh, live jobs.
HEARTBEAT_MAX_AGE = 120.0

# Versions recorded for plan.pkl staleness (S6): the packages a solved Plan is built from.
_STAMPED_PACKAGES = ("numpy", "scipy", "pandas", "highspy", "mosek", "openpyxl", "toml", "pydantic")


class ResultsError(RuntimeError):
    """A results folder or its job record is missing or malformed."""


class TokenChanged(ResultsError):
    """The job no longer runs under the writer's token (re-queued under a new one, S8)."""


def now_iso(at: Optional[float] = None) -> str:
    """Now, as local time **with its UTC offset** ('2026-11-01T01:30:00-05:00').

    Review H3: a naive local stamp is ambiguous in the hour the clocks fall back, and
    `datetime.fromisoformat(...).timestamp()` reads it as the first occurrence, so every
    heartbeat written in the repeated hour looked an hour old and adoption interrupted live
    workers. The offset makes the instant exact; the text stays readable as local time.
    `at` (epoch seconds) stamps another instant (tests).
    """
    moment = datetime.now(timezone.utc) if at is None else datetime.fromtimestamp(at, timezone.utc)
    return moment.astimezone().isoformat(timespec="seconds")


def stamp_seconds(iso: Optional[str]) -> Optional[float]:
    """A `now_iso` stamp as epoch seconds (None when absent or unreadable).

    Compare and sort stamps through this, never as strings: two stamps on either side of a
    clock change carry different offsets, and their text does not sort in time order. A naive
    stamp (written before H3's fix) is read as local time, as before.
    """
    if not iso:
        return None
    try:
        return datetime.fromisoformat(str(iso)).timestamp()
    except ValueError:
        return None


def _replace(tmp, path):
    """Rename onto the target, retrying: on Windows `os.replace` raises while any reader
    holds the file open (the Queue page reads every status.json every two seconds).

    A reader that holds the file for seconds cannot be renamed over at all (Windows, no
    FILE_SHARE_DELETE); after the retry budget the bytes are written in place instead, so a
    write is never lost. That write is not atomic and a reader may see a torn file
    momentarily; `JobRecord.read` retries those.
    """
    for _ in range(40):
        try:
            os.replace(tmp, path)
            return
        except OSError:
            time.sleep(0.05)
    try:
        with open(path, "wb") as f:
            f.write(Path(tmp).read_bytes())
    finally:
        Path(tmp).unlink(missing_ok=True)


def atomic_write(path, text: str) -> None:
    """Write a file to a temporary name and rename it (section 5: no half-written files)."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    _replace(tmp, path)


def atomic_write_bytes(path, blob: bytes) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(blob)
    _replace(tmp, path)


@contextmanager
def _status_lock(results_dir):
    """An OS file lock around one read-modify-write of status.json.

    The S5 lesson applied to the job record: the worker's heartbeat, the interface's cancel
    and two managers all write it, from different processes. Serialized under the lock (and
    the rename retry above), no update is lost and no write fails because a reader is looking.
    """
    from .store import _try_lock, _unlock

    path = Path(results_dir) / STATUS_LOCK
    deadline = time.monotonic() + 5.0
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        while not _try_lock(fd):
            if time.monotonic() > deadline:
                raise ResultsError(f"{path} is held by another writer")
            time.sleep(0.05)
        try:
            yield
        finally:
            _unlock(fd)
    finally:
        os.close(fd)


def environment() -> dict:
    """Python and package versions: plan.pkl is valid only for this environment (S6)."""
    from importlib import metadata

    packages = {}
    for name in _STAMPED_PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    return {"python": platform.python_version(), "packages": packages}


def _package_diff_sha256() -> Optional[str]:
    """sha256 of the uncommitted changes to the package's tracked files, or None."""
    import subprocess

    here = Path(__file__).resolve().parents[1]  # src/owlplanner
    try:
        out = subprocess.run(["git", "-C", str(here), "diff", "HEAD", "--binary", "--", "."],
                             capture_output=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return hashlib.sha256(out).hexdigest()


def code_stamp(engine: Optional[dict] = None) -> dict:
    """The code a cached Plan was pickled by: Owl's version and commit (S6, review H6).

    A pickle restores a Plan's attributes as they were; after a code change that renames or
    adds one, the pages break *after* a successful load. So `plan.pkl` is valid only for the
    code that wrote it, as design section 5 says (commit, Python and package versions).
    "-dirty" alone would match two different sets of uncommitted edits, so a dirty tree adds
    a hash of the package's diff against HEAD.
    """
    from owlplanner.version import engine_provenance

    stamp = dict(engine if engine is not None else engine_provenance())
    commit = stamp.get("commit")
    if commit and str(commit).endswith("-dirty"):
        stamp["diff_sha256"] = _package_diff_sha256()
    return stamp


class JobRecord:
    """status.json: the job record on disk from the moment the job is queued (S2).

    The interface creates it before dispatch and only ever flips `cancel`; the worker owns
    `state`, `pid`, `heartbeat`, `step`, `last_log`, `iteration`, `error`. Cancellation is a
    per-job `token` (S9): the worker stops when status.json no longer runs its own token.
    """

    def __init__(self, results_dir, doc: dict):
        self.results_dir = Path(results_dir)
        self.doc = doc

    # -- construction / IO ---------------------------------------------

    @classmethod
    def create(cls, results_dir, *, run_id: str, run_name: str, preset: str, options: dict,
               plan_year: int, queued: Optional[str] = None) -> "JobRecord":
        results_dir = Path(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        doc = {
            "job_format": JOB_FORMAT,
            "id": results_dir.name,
            "run_id": run_id,
            "run": run_name,
            "preset": preset,
            "options": dict(options),
            "plan_year": int(plan_year),
            "state": WAITING,
            "token": secrets.token_hex(16),
            "cancel": False,
            "queued": queued or now_iso(),
            "started": None,
            "finished": None,
            "pid": None,
            "pid_started": None,
            "heartbeat": None,
            "step": None,
            "last_log": None,
            "iteration": None,
            "error": None,
            "attempts": 1,
        }
        job = cls(results_dir, doc)
        job.write()
        return job

    @classmethod
    def read(cls, results_dir) -> "JobRecord":
        results_dir = Path(results_dir)
        path = results_dir / STATUS_JSON
        last = None
        for _ in range(4):  # a torn read of the in-place fallback, or a file mid-replace
            try:
                with open(path, encoding="utf-8") as f:
                    doc = json.load(f)
                return cls(results_dir, doc)
            except (OSError, ValueError) as exc:
                last = exc
                time.sleep(0.05)
        raise ResultsError(f"cannot read {path}: {last}") from last

    @staticmethod
    def exists(results_dir) -> bool:
        return (Path(results_dir) / STATUS_JSON).exists()

    def write(self) -> None:
        atomic_write(self.results_dir / STATUS_JSON, pretty_json(self.doc))

    def refresh(self) -> None:
        """Re-read the record from disk (the worker's wake check, S8)."""
        last = None
        for _ in range(4):
            try:
                self.doc = type(self).read(self.results_dir).doc
                return
            except ResultsError as exc:
                last = exc
                time.sleep(0.05)
        raise last

    def update(self, token: Optional[str] = None, **fields) -> bool:
        """Merge fields into the on-disk record, under the job's lock (S5's lesson).

        One read-modify-write of the given fields only, serialized against every other
        writer (heartbeat, cancel, re-queue, another manager): no update is lost. With
        `token=` the write only happens while the job still runs under that token (S8: a
        worker that woke after "run again" must not clobber the new attempt). Returns
        whether it wrote.

        An on-disk record that cannot be read raises `ResultsError` and writes nothing (N3):
        writing the in-memory copy back instead could revert a cancel flag or a re-queue's
        new token, and its token check would run against that stale copy.
        """
        with _status_lock(self.results_dir):
            doc = type(self).read(self.results_dir).doc
            if token is not None and doc.get("token") != token:
                return False
            doc.update(fields)
            self.doc = doc
            atomic_write(self.results_dir / STATUS_JSON, pretty_json(doc))
            return True

    def publish(self, token: str, staging, names) -> None:
        """Rename one attempt's staged artifacts into the results folder (G2).

        The artifact writes are token-guarded like the record writes (F2 covered `status.json`
        and `record.json` only; a stale worker that woke after "run again" used to re-create
        the artifacts `requeue` had just cleaned, mixing two attempts in one folder). The
        rename runs **under the job's lock** and only while the job still runs under `token`:
        `requeue` cleans the folder under the same lock, so a publish and a "run again" cannot
        interleave -- one comes before the other, and a publish that comes first is deleted by
        the clean-up. Raises `TokenChanged` when the job is no longer this worker's (nothing
        is published; the attempt's staging folder is the caller's to drop). A lock timeout
        stays a plain `ResultsError`: it is this attempt's failure, not a cancel.
        """
        with _status_lock(self.results_dir):
            doc = type(self).read(self.results_dir).doc
            if doc.get("token") != token:
                raise TokenChanged(f"job {self.id} is no longer this worker's (re-queued under a new token)")
            for name in names:
                _replace(Path(staging) / name, self.results_dir / name)

    def publish_record(self, token: str, doc: dict) -> bool:
        """Write this attempt's `record.json`, under the job's lock and only while the job
        still runs under `token` (review H4).

        F2 guarded the record with a check before the write, outside the lock; `requeue` could
        run between the two (the worker's `build_record` runs `git` in that window), and the
        old attempt's record then landed in the cleaned folder of the new one. Under the lock,
        a record write and `requeue` cannot interleave: a stale worker writes nothing, and a
        record written first is moved aside to `record.prev.json` by the re-queue. Returns
        whether it wrote.
        """
        with _status_lock(self.results_dir):
            current = type(self).read(self.results_dir).doc
            if current.get("token") != token:
                return False
            write_record(self.results_dir, doc)
            return True

    def take_for_dispatch(self) -> bool:
        """Mark a waiting job running *before* its worker starts (only one dispatcher wins).

        Two Queue fragments can tick at once; without this compare-and-swap one waiting job
        could be spawned twice, and "run again" then means two workers on one run (S8).
        """
        with _status_lock(self.results_dir):
            doc = type(self).read(self.results_dir).doc
            if doc.get("state") != WAITING:
                return False
            doc.update(state=RUNNING, started=now_iso(), heartbeat=now_iso())
            self.doc = doc
            atomic_write(self.results_dir / STATUS_JSON, pretty_json(doc))
            return True

    # -- fields --------------------------------------------------------

    @property
    def id(self) -> str:
        return str(self.doc.get("id") or self.results_dir.name)

    @property
    def state(self) -> str:
        return str(self.doc.get("state"))

    @property
    def token(self) -> str:
        return str(self.doc.get("token") or "")

    @property
    def plan_year(self) -> Optional[int]:
        value = self.doc.get("plan_year")
        return int(value) if value is not None else None

    # -- worker side ---------------------------------------------------

    def claim(self, token: str, *, pid: int, pid_started) -> None:
        """The worker takes the job: state=running, its PID and start token (S9).

        The dispatcher already marked it running (only one dispatcher takes a waiting job,
        `take_for_dispatch`); the token is what makes the job this worker's.
        """
        with _status_lock(self.results_dir):
            doc = type(self).read(self.results_dir).doc
            if doc.get("token") != token:
                raise TokenChanged(f"job {self.id} runs under another token")
            if doc.get("state") not in (WAITING, RUNNING):
                raise ResultsError(f"job {self.id} is {doc.get('state')!r}, not waiting")
            doc.update(state=RUNNING, pid=pid, pid_started=pid_started, started=now_iso(),
                       heartbeat=now_iso())
            self.doc = doc
            atomic_write(self.results_dir / STATUS_JSON, pretty_json(doc))

    def touch(self, token: Optional[str] = None, *, step=None, last_log=None, iteration=None) -> bool:
        """One heartbeat (every 30 s): state, step, the last log line, the loop iteration.

        Returns whether it wrote (False once the job runs under another token)."""
        fields = {"heartbeat": now_iso()}
        if step is not None:
            fields["step"] = step
        if last_log is not None:
            fields["last_log"] = last_log
        if iteration is not None:
            fields["iteration"] = iteration
        return self.update(token, **fields)

    def stop_reason(self, token: str) -> Optional[str]:
        """Why this worker must stop now (S8, S9), or None to carry on."""
        self.refresh()
        if self.doc.get("cancel"):
            return "cancelled"
        if self.token != token:
            return "the job is no longer this worker's (re-queued under a new token)"
        if self.state != RUNNING:
            return f"the job record says {self.state!r}"
        return None

    def finish(self, state: str, *, error: Optional[str] = None, token: Optional[str] = None) -> None:
        fields = {"state": state, "finished": now_iso()}
        if error is not None:
            fields["error"] = error
        self.update(token, **fields)

    # -- interface side ------------------------------------------------

    def request_cancel(self) -> None:
        """Cooperative cancel: the worker checks this before every step (S9)."""
        self.update(cancel=True)

    def requeue(self) -> None:
        """'Run again' on an interrupted or failed job: a fresh token, still one worker (S8).

        The folder starts clean for the new attempt: the partial artifacts of the old one go
        (they would sit beside the new record), its `record.json` is kept as
        `record.prev.json` (a failed or interrupted solve leaves its record, S3) and its
        `solve.log` as `solve.prev.log` (M1: the kept record's log).

        All or nothing (N4): every file is first moved aside by rename, and only then are the
        moved artifacts deleted. On Windows a file open in another program (`Results.xlsx` in
        Excel) can be neither renamed nor deleted; the renames done so far are then put back
        and `ResultsError` names the file, so the folder and the job record are unchanged and
        "run again" can be retried once the file is closed.
        """
        with _status_lock(self.results_dir):
            doc = type(self).read(self.results_dir).doc
            trash = self.results_dir / f".requeue-{secrets.token_hex(4)}"
            moves = [(self.results_dir / name, trash / name)
                     for name in (SUMMARY_JSON, PLAN_JSON, RESULTS_XLSX, PLAN_PKL)]
            moves += [(self.results_dir / RECORD_JSON, self.results_dir / PREV_RECORD_JSON),
                      (self.results_dir / SOLVE_LOG, self.results_dir / PREV_SOLVE_LOG)]
            moves = [(src, dst) for src, dst in moves if src.exists()]
            trash.mkdir()
            done = []
            try:
                for src, dst in moves:
                    os.replace(src, dst)
                    done.append((src, dst))
            except OSError as exc:
                for src, dst in reversed(done):
                    try:
                        os.replace(dst, src)
                    except OSError:
                        pass
                shutil.rmtree(trash, ignore_errors=True)
                name = Path(exc.filename).name if exc.filename else str(exc)
                why = ("the previous attempt's worker may still be running; cancel or kill it first"
                       if name == SOLVE_LOG else "close it (the workbook in Excel, for example)")
                raise ResultsError(f"cannot run {self.id} again: {name} is in use: {why}, "
                                   "then try again") from exc
            # Staging folders (`.attempt-*`) stay: the old attempt's worker may still be alive
            # and writing into its own (S8); it drops it itself, and a kill drops it (N1).
            shutil.rmtree(trash, ignore_errors=True)
            doc.update({
                "state": WAITING,
                "token": secrets.token_hex(16),
                "cancel": False,
                "started": None,
                "finished": None,
                "pid": None,
                "pid_started": None,
                "heartbeat": None,
                "step": None,
                "last_log": None,
                "iteration": None,
                "error": None,
                "attempts": int(doc.get("attempts") or 1) + 1,
            })
            self.doc = doc
            atomic_write(self.results_dir / STATUS_JSON, pretty_json(doc))

    def heartbeat_age(self, now: Optional[float] = None) -> Optional[float]:
        """Seconds since the last heartbeat, or None when the worker never beat."""
        then = stamp_seconds(self.doc.get("heartbeat"))
        if then is None:
            return None
        return (now if now is not None else time.time()) - then


def drop_staging(results_dir) -> None:
    """Remove the staged artifacts a killed attempt left (`.attempt-<token8>`; N1).

    A worker stages its artifacts before publishing them (G2) and drops the staging folder
    itself, except when it is killed. Nothing reads these folders; this keeps the results
    folder to what the design lists.
    """
    for folder in Path(results_dir).glob(".attempt-*"):
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)


# -- record.json -------------------------------------------------------


def build_record(*, run_id: str, results_id: str, plan_year: Optional[int], preset: str, options: dict,
                 plan_doc: Optional[dict], status: str, started: Optional[str],
                 finished: Optional[str], wall_time_seconds: Optional[float],
                 warnings: list, iterations: Optional[int], inputs_hash: Optional[str] = None,
                 solver: Optional[str] = None, gap: Optional[float] = None,
                 rates: Optional[dict] = None, plan_pkl_sha256: Optional[str] = None,
                 error: Optional[str] = None) -> dict:
    """The record.json of one solve (design section 5).

    `plan_doc` is `cli.formatters.plan_to_dict`'s output (None when the solve produced no
    plan); method and convergence come from it. `solver` is the engine used ("HiGHS" /
    "MOSEK", as `export._mip_node_limit` names it), `gap` the reported MIP gap
    (`plan.solverGap`, -1 when none), `rates` the rate method and seed.
    """
    from owlplanner.version import engine_provenance

    engine = engine_provenance()
    plan_doc = plan_doc or {}
    convergence = plan_doc.get("convergence")
    if not isinstance(convergence, dict):
        # plan_to_dict flattens plan_convergence: convergence is its type, the rest top-level.
        convergence = {
            "convergence": plan_doc.get("convergence", "undefined"),
            "breakpoint_method": plan_doc.get("breakpoint_method", "loop"),
            "fixed_point_residual_today_dollars": plan_doc.get("fixed_point_residual_today_dollars", {}),
            "unsettled": plan_doc.get("unsettled", {}),
            "objective_error_bar_today_dollars": plan_doc.get("objective_error_bar_today_dollars", 0.0),
        }
    return {
        "record_format": RECORD_FORMAT,
        "run_id": run_id,
        "results_id": results_id,
        "inputs_hash": inputs_hash,
        # The year the run's inputs were entered for, the solve year (R1; no frozen date: the
        # solve date below is the date Owl read, design section 8.3).
        "plan_year": plan_year,
        "solve_date": {"started": started, "finished": finished},
        "preset": preset,
        "method": {
            "objective": plan_doc.get("objective"),
            "options": dict(options),
            "breakpoint_method": plan_doc.get("breakpoint_method", "loop"),
        },
        # Owl version and commit (S13's comparison flags read this too).
        "engine": engine,
        "solver": solver,
        "status": status,
        "gap": gap,
        # The self-consistent loop's iterations, as the solve log reports them (the plan
        # keeps no count; a future branch-and-bound preset will record nodes as well).
        "iterations": iterations,
        "converged": convergence.get("convergence") in ("monotonic", "oscillatory"),
        "convergence": convergence,
        "wall_time_seconds": wall_time_seconds,
        "warnings": list(warnings),
        "rates": rates,
        "environment": environment(),
        "plan_pkl_sha256": plan_pkl_sha256,
        # The code the cache was pickled by (H6): load_plan drops it under any other code.
        "plan_pkl_code": code_stamp(engine) if plan_pkl_sha256 else None,
        "error": error,
    }


def write_record(results_dir, doc: dict) -> Path:
    path = Path(results_dir) / RECORD_JSON
    atomic_write(path, pretty_json(doc))
    return path


def read_record(results_dir) -> Optional[dict]:
    path = Path(results_dir) / RECORD_JSON
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# -- plan.pkl: the cache of a solved Plan (R10, S6) ---------------------


def save_plan(plan, results_dir) -> str:
    """Pickle the solved Plan as plan.pkl; returns its sha256 for record.json.

    A pickle can run code on load, so the library loads only the pickles it wrote, checked
    against this hash (section 10). The logger's streams do not pickle (`Logger.__getstate__`
    drops them); a loaded plan logs to the default streams until re-attached.
    """
    blob = pickle.dumps(plan)
    atomic_write_bytes(Path(results_dir) / PLAN_PKL, blob)
    return hashlib.sha256(blob).hexdigest()


def load_plan(results_dir, record: Optional[dict] = None):
    """The cached Plan, or None when absent, stale or not ours; drops a stale cache (S6).

    Stale means record.json's environment no longer matches this Python and these packages,
    or its code stamp no longer matches this code (Owl's version and commit, and the diff of
    a dirty tree: `code_stamp`, H6), or the bytes do not match the hash record.json carries
    (R10's check: the pickles a run carries must match the record this solve wrote -- a run
    brought in from elsewhere keeps its record only if the two agree, and importing one must
    drop its pickles). Fails soft: a pickle that does not load is dropped too, and a fresh
    solve replaces the cache.
    """
    results_dir = Path(results_dir)
    path = results_dir / PLAN_PKL
    if not path.exists():
        return None
    if record is None:
        record = read_record(results_dir)
    if record is None:
        return None
    blob = path.read_bytes()
    wanted = record.get("plan_pkl_sha256")
    if not wanted or hashlib.sha256(blob).hexdigest() != wanted:
        path.unlink(missing_ok=True)  # not ours: never load it
        return None
    if record.get("environment") != environment() or record.get("plan_pkl_code") != code_stamp():
        path.unlink(missing_ok=True)  # stale (S6, H6): one re-solve replaces it
        return None
    try:
        return pickle.loads(blob)
    except Exception:  # a renamed module or class: the cache is stale, the record stands (H6)
        path.unlink(missing_ok=True)
        return None

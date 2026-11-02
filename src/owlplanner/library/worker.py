"""The worker: one solve of one run, in a fresh interpreter (run-library-design.md, 8.2).

Run as ``python -m owlplanner.library.worker RESULTS_DIR TOKEN``. The interface writes
`status.json` (state=waiting) in the results folder before dispatch (S2); this program
claims it under its token (state=running, PID and the process start token, S9), freezes
Owl's "today" to the run's own "as of" date (`owlplanner.asof`, section 8.3 b), builds the
plan from the run's frozen files (`inputs/Case.toml` + `HFP.xlsx`, the `owlcli run` route),
solves it with the job's preset options, and writes the results folder's artifacts and
`record.json`.

Cancellation (S8, S9): every step, every heartbeat (30 s) and (throttled) every log line,
the worker re-reads its own `status.json`. It stops when the record carries a cancel flag,
a state other than running, or a different token -- so a worker that wakes after the machine
slept stops instead of racing a "run again". A stopped job writes no artifacts and keeps its
record folder for the retry: the artifacts are staged and published under the job's lock with
the token still owning the job (`JobRecord.publish`, G2), and every record write is
token-guarded (F2). Only the run's own results folder is written.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path

from owlplanner import asof

from . import results as R
from .casefiles import resolve_as_of
from .presets import resolve_options
from .procs import process_start_token

HEARTBEAT_SECONDS = 30.0
# The wake/cancel check during a long solve runs at most this often (each log line asks).
CHECK_SECONDS = 2.0

_ITER_RE = re.compile(r"\bIter:\s*(\d+)")
_WARN_RE = re.compile(r"WARNING|ERROR")


class JobCancelled(Exception):
    """The job record no longer runs under this worker's token (S8, S9)."""


class _LogTee:
    """A Plan log stream: appends to solve.log, keeps the last line, loop iteration, warnings.

    `print()` on a stream needs `write`; Owl's `Logger` writes every message through it. The
    cancellation check rides along (throttled): the solve runs between log lines, and a
    worker that has been marked interrupted stops at the next one (S8).
    """

    def __init__(self, path, check=None):
        self._fh = open(path, "w", encoding="utf-8", newline="\n")
        self._check = check
        self._checked = 0.0
        self._pending = ""
        self.last_line = ""
        self.iteration = None
        self.warnings = set()

    def write(self, text):
        self._fh.write(text)
        self._fh.flush()
        self._pending += text
        *lines, self._pending = self._pending.split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            self.last_line = stripped
            if _WARN_RE.search(stripped):
                self.warnings.add(stripped.split("|", 3)[-1].strip() if "|" in stripped else stripped)
            match = _ITER_RE.search(stripped)
            if match:
                self.iteration = max(self.iteration or 0, int(match.group(1)))
        if self._check is not None and time.monotonic() - self._checked > CHECK_SECONDS:
            self._checked = time.monotonic()
            self._check()

    def flush(self):
        self._fh.flush()

    def close(self):
        self._fh.close()


class Worker:
    """One solve of one run, tracked by its results folder's job record."""

    def __init__(self, results_dir, token, *, heartbeat_seconds=HEARTBEAT_SECONDS):
        self.results_dir = Path(results_dir)
        self.token = str(token)
        self.heartbeat_seconds = heartbeat_seconds
        self.run_dir = self.results_dir.parent.parent
        self.job = R.JobRecord.read(self.results_dir)
        self.tee = None
        self._beat_stop = threading.Event()
        self._beat_thread = None

    # -- cancellation --------------------------------------------------

    def check(self):
        """Raise JobCancelled when the record no longer runs under this token (S8, S9)."""
        reason = self.job.stop_reason(self.token)
        if reason is not None:
            raise JobCancelled(reason)

    def _beat(self):
        """Beat while this process lives and the job is still ours.

        A pending cancel does not stop the heartbeat (N1): the worker stops at its next step or
        log line, which a long MIP can delay, and until then the Queue shows it alive with the
        cancel pending and offers a verified kill. Before, the beat stopped at the cancel, and
        two minutes later adoption marked the still-running worker interrupted.
        """
        while not self._beat_stop.wait(self.heartbeat_seconds):
            try:
                if not self.job.touch(self.token, last_log=self.tee.last_line if self.tee else None,
                                      iteration=self.tee.iteration if self.tee else None):
                    return  # re-queued under a new token: the job is no longer ours (S8)
            except Exception:
                # A transient write failure (a reader mid-rename) must not kill the heartbeat:
                # the manager would mark a live worker silent (S8). Gone folder: stop.
                if not self.results_dir.exists():
                    return

    # -- the solve -----------------------------------------------------

    def run(self):
        """Claim the job, solve it, write the results folder. Returns the final state."""
        try:
            self.job.claim(self.token, pid=_pid(), pid_started=process_start_token(_pid()))
        except R.ResultsError:
            return self.job.state  # not ours: re-queued, cancelled or already taken (S8)
        self.tee = _LogTee(self.results_dir / R.SOLVE_LOG, check=self.check)
        self._beat_thread = threading.Thread(target=self._beat, daemon=True)
        self._beat_thread.start()
        try:
            state = self._solve()
        except JobCancelled as exc:
            state = R.INTERRUPTED
            self._write_record(status="interrupted", error=f"stopped: {exc}")
            self.job.finish(state, error=f"stopped: {exc}", token=self.token)
        except Exception as exc:  # a broken solve is a finding, not a dead worker (run_suite)
            state = R.FAILED
            self.tee.write(traceback.format_exc())
            self._write_record(status="exception", error=f"{type(exc).__name__}: {exc}")
            self.job.finish(state, error=f"{type(exc).__name__}: {exc}", token=self.token)
        else:
            self.job.finish(state, token=self.token)
        finally:
            self._beat_stop.set()
            if self._beat_thread is not None:
                self._beat_thread.join(timeout=5.0)
            self.tee.close()
        return state

    def _solve(self):
        from owlplanner.cli.formatters import plan_to_dict
        from owlplanner.config import config_to_plan, load_toml
        from owlplanner.config.schema import parse_solver_options
        from owlplanner.export import plan_metrics

        self.job.touch(self.token, step="reading the run's files")
        self.check()
        scenario = json.loads((self.run_dir / "inputs" / "scenario.json").read_text(encoding="utf-8"))
        as_of_date = resolve_as_of(scenario)  # validated: inside the run's plan year (R1)

        # Process-wide (H1): the claiming-age search runs its candidates on a thread pool,
        # and a thread-local freeze would leave them reading the real date. A worker solves
        # one job per process, so nothing else shares the freeze.
        with asof.process_as_of(as_of_date):
            started = R.now_iso()
            t0 = time.time()
            self.job.touch(self.token, step="building the plan")
            self.check()
            diconf, dirname, _ = load_toml(str(self.run_dir / "inputs" / "Case.toml"))
            plan = config_to_plan(diconf, dirname, verbose=True, logstreams=[self.tee], loadHFP=True)

            self.job.touch(self.token, step="solving")
            self.check()
            options = resolve_options(self.job.doc.get("preset", "custom"), plan.solverOptions,
                                      self.job.doc.get("options"))
            options = parse_solver_options(options)
            plan.solve(plan.objective, options)
            wall = time.time() - t0

            self.check()
            status = plan.caseStatus
            plan_doc = None
            plan_sha = None
            if status == "solved":
                self.job.touch(self.token, step="writing the results")
                plan_doc = plan_to_dict(plan)
                summary = plan_metrics(plan)
                plan_sha = self._publish_results(summary, plan_doc, plan)
            else:
                self.job.update(self.token, error=plan.solverMessage or status)

            self._write_record(
                status=status,
                as_of=as_of_date.isoformat(),
                started=started,
                finished=R.now_iso(),
                wall_time_seconds=round(wall, 3),
                plan_doc=plan_doc,
                options=options,
                solver="MOSEK" if getattr(plan, "_use_mosek", False) else "HiGHS",
                gap=float(getattr(plan, "solverGap", -1.0)),
                iterations=(self.tee.iteration + 1) if self.tee.iteration is not None else None,
                rates={
                    "method": getattr(plan, "rateMethod", None),
                    "from": getattr(plan, "rateFrm", None),
                    "to": getattr(plan, "rateTo", None),
                    "seed": getattr(plan, "rateSeed", None),
                    "reproducible": getattr(plan, "reproducibleRates", False),
                },
                plan_pkl_sha256=plan_sha,
            )
        return R.DONE if status == "solved" else R.FAILED

    # -- helpers -------------------------------------------------------

    def _publish_results(self, summary, plan_doc, plan) -> str:
        """Write the artifacts and publish them atomically with respect to "run again" (G2).

        The files are staged in a private folder beside the record and renamed into place
        under the job's lock, the token still owning the job (`JobRecord.publish`): a worker
        that wakes after "run again" publishes nothing, so one results folder never holds two
        attempts' artifacts (the F2 guard covered `status.json` and `record.json` only).
        Returns the plan cache's sha256 for record.json.
        """
        staging = self.results_dir / f".attempt-{self.token[:8]}"
        staging.mkdir(exist_ok=True)
        try:
            self._write_json(staging, R.SUMMARY_JSON, summary)
            self._write_json(staging, R.PLAN_JSON, plan_doc)
            plan.saveWorkbook(basename=str(staging / R.RESULTS_XLSX), overwrite=True,
                              with_config="first")
            plan_sha = R.save_plan(plan, staging)
            try:
                self.job.publish(self.token, staging,
                                 (R.SUMMARY_JSON, R.PLAN_JSON, R.RESULTS_XLSX, R.PLAN_PKL))
            except R.TokenChanged as exc:
                raise JobCancelled(str(exc)) from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return plan_sha

    def _write_json(self, folder, name, doc):
        from owlplanner.cli.formatters import _NumpyEncoder

        text = json.dumps(doc, cls=_NumpyEncoder, indent=1, sort_keys=True) + "\n"
        Path(folder, name).write_text(text, encoding="utf-8", newline="\n")

    def _write_record(self, *, status, as_of=None, plan_doc=None, options=None, started=None,
                      finished=None, wall_time_seconds=None, solver=None, gap=None,
                      iterations=None, rates=None, plan_pkl_sha256=None, error=None):
        doc = R.build_record(
            run_id=str(self.job.doc.get("run_id") or ""),
            results_id=self.job.id,
            as_of=as_of or self.job.as_of,
            preset=str(self.job.doc.get("preset") or ""),
            options=options if options is not None else self.job.doc.get("options") or {},
            plan_doc=plan_doc,
            status=status,
            started=started or self.job.doc.get("started"),
            finished=finished or self.job.doc.get("finished"),
            wall_time_seconds=wall_time_seconds,
            warnings=sorted(self.tee.warnings),
            iterations=iterations,
            inputs_hash=self._inputs_hash(),
            solver=solver,
            gap=gap,
            rates=rates,
            plan_pkl_sha256=plan_pkl_sha256,
            error=error,
        )
        # Under the job's lock, token checked inside it (H4): a stale worker that woke after
        # "run again" writes nothing ("run again" owns the folder now, S8, F2).
        self.job.publish_record(self.token, doc)

    def _inputs_hash(self):
        try:
            run_doc = json.loads((self.run_dir / "run.json").read_text(encoding="utf-8"))
            return run_doc.get("inputs_hash")
        except (OSError, ValueError):
            return None


def _pid() -> int:
    import os

    return os.getpid()


def run_job(results_dir, token, *, heartbeat_seconds=HEARTBEAT_SECONDS) -> str:
    """Run one job in this process (the worker program's body; tests use it directly)."""
    return Worker(results_dir, token, heartbeat_seconds=heartbeat_seconds).run()


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        sys.stderr.write("usage: python -m owlplanner.library.worker RESULTS_DIR TOKEN\n")
        return 2
    try:
        state = run_job(argv[0], argv[1])
    except Exception:
        # Nothing of the run's is touched here: the manager marks the dead job interrupted.
        traceback.print_exc(file=sys.stderr)
        return 1
    return 0 if state in (R.DONE, R.FAILED) else 3


if __name__ == "__main__":
    raise SystemExit(main())

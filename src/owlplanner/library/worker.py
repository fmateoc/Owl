"""The worker: one solve of one run, in a fresh interpreter (run-library-design.md, 8.2).

Run as ``python -m owlplanner.library.worker RESULTS_DIR TOKEN``. The interface writes
`status.json` (state=waiting) in the results folder before dispatch (S2); this program
claims it under its token (state=running, PID and the process start token, S9), checks that
this is the run's plan year (R1: a run is solved only in the year its inputs were entered
for; design section 8.3), builds the plan from the run's frozen files (`inputs/Case.toml` +
`HFP.xlsx`, the `owlcli run` route), solves it with the job's preset options, and writes the
results folder's artifacts and `record.json`.

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
import os
import re
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path

from . import results as R
from .agesearch import fixed_ages, two_stage_ages
from .casefiles import check_plan_year
from .scenario import ScenarioError
from .presets import resolve_options
from .procs import process_start_token

HEARTBEAT_SECONDS = 30.0
# The wake/cancel check during a long solve runs at most this often (each log line asks).
CHECK_SECONDS = 2.0

# The "regret" preset's sweep size (I8): "Quick look" of `ui/owlbridge.REGRET_PRESETS`, its
# cheapest -- 18 historical scenarios x (7 grid points + 2) full-horizon solves. Cutting the
# grid is far cheaper than cutting the scenarios (stresstests.run_conversion_regret_sweep).
REGRET_N_SCENARIOS = 18
REGRET_N_GRID = 7
REGRET_GRID_PAD = 45_000.0
REGRET_SEED = 1

_ITER_RE = re.compile(r"\bIter:\s*(\d+)")
_WARN_RE = re.compile(r"WARNING|ERROR")


def _open_log(path):
    """Open the solve log for the whole solve, in a way that still lets `requeue` rename it.

    "Run again" moves `solve.log` to `solve.prev.log` while the old attempt's worker may
    still be writing (S8's machine-sleep wake; the tests hold it there on purpose). On
    Windows a rename needs FILE_SHARE_DELETE on every open handle, and `open()` does not
    request it (WinError 32), so N4's all-or-nothing rename refused with "solve.log is in
    use" and "run again" could not work until the old worker died. This opens the file with
    all three sharing flags; after the rename the old worker's remaining lines follow the
    file into `solve.prev.log`, which is where they belong.
    """
    if os.name != "nt":
        return open(path, "w", encoding="utf-8", newline="\n")
    import ctypes
    import msvcrt

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                     ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                     ctypes.c_void_p]
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_ALL = 0x1 | 0x2 | 0x4  # read | write | delete
    CREATE_ALWAYS = 2
    FILE_ATTRIBUTE_NORMAL = 0x80
    handle = kernel32.CreateFileW(str(path), GENERIC_WRITE, FILE_SHARE_ALL, None,
                                  CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, None)
    if handle in (None, ctypes.c_void_p(-1).value):
        raise OSError(f"cannot open the solve log {path}")
    fd = msvcrt.open_osfhandle(handle, os.O_WRONLY | os.O_BINARY)
    return os.fdopen(fd, "w", encoding="utf-8", newline="\n")


class JobCancelled(Exception):
    """The job record no longer runs under this worker's token (S8, S9)."""


class _LogTee:
    """A Plan log stream: appends to solve.log, keeps the last line, loop iteration, warnings.

    `print()` on a stream needs `write`; Owl's `Logger` writes every message through it. The
    cancellation check rides along (throttled): the solve runs between log lines, and a
    worker that has been marked interrupted stops at the next one (S8).

    While `quiet` is set (the "Ages" preset's search stages, step 6), every line still goes
    to solve.log and the cancellation check still runs, but the line is not read as the
    solve's own: run_suite.py keeps the stage warnings out of the record ("their warnings
    are not in the report"), and an unsettled candidate is not a problem with the final
    solve.
    """

    def __init__(self, path, check=None):
        self._fh = _open_log(path)
        self._check = check
        self._checked = 0.0
        self._pending = ""
        self.quiet = False
        self.last_line = ""
        self.iteration = None
        self.warnings = set()

    def write(self, text):
        self._fh.write(text)
        self._fh.flush()
        if self.quiet:
            if self._check is not None and time.monotonic() - self._checked > CHECK_SECONDS:
                self._checked = time.monotonic()
                self._check()
            return
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
        from owlplanner.cli.set_override import apply_overrides
        from owlplanner.config import config_to_plan, load_toml
        from owlplanner.config.schema import parse_solver_options
        from owlplanner.export import plan_metrics

        self.job.touch(self.token, step="reading the run's files")
        self.check()
        scenario = json.loads((self.run_dir / "inputs" / "scenario.json").read_text(encoding="utf-8"))
        try:
            # Solved only in its plan year (R1): a job queued on December 31 and started after
            # midnight is refused here, with its record saying why.
            plan_year = check_plan_year(scenario)
        except ScenarioError as exc:
            self.job.update(self.token, error=str(exc))
            self._write_record(status="refused", plan_year=scenario.get("plan_year"), error=str(exc))
            return R.FAILED

        started = R.now_iso()
        t0 = time.time()
        self.job.touch(self.token, step="building the plan")
        self.check()
        diconf, dirname, _ = load_toml(str(self.run_dir / "inputs" / "Case.toml"))

        # The "Ages" preset (design 8.1, step 6): run_suite.py's two-stage claiming-age
        # search first, then the final solve at the ages it picked. The stages' logs go to
        # solve.log but their warnings stay out of the record (run_suite.py's rule).
        preset = str(self.job.doc.get("preset") or "custom")
        age_search = None
        if preset == "ages" and str(diconf.get("solver_options", {}).get("withSSAges", "fixed")
                                    ).strip().lower() != "fixed":
            self.job.touch(self.token, step="searching the claiming ages")
            self.check()
            self.tee.quiet = True
            try:
                ages, candidates = two_stage_ages(diconf, dirname, log=self.tee, check=self.check)
            finally:
                self.tee.quiet = False
            age_search = {"chosen": ages, "candidates": candidates}
            diconf = apply_overrides(diconf, fixed_ages(ages))
            self.job.touch(self.token, step="building the plan")
            self.check()

        plan = config_to_plan(diconf, dirname, verbose=True, logstreams=[self.tee], loadHFP=True)

        self.job.touch(self.token, step="solving")
        self.check()
        options = resolve_options(preset, plan.solverOptions, self.job.doc.get("options"))
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

        # I8's "regret" preset, one per request (design 14.1): the sweep runs after the base
        # results are published, so a failed sweep keeps them (record.json says what failed).
        regret = None
        if status == "solved" and preset == "regret":
            try:
                self.job.touch(self.token, step="the conversion regret sweep")
                self.check()
                regret = self._regret_sweep(plan, options)
            except JobCancelled:
                raise
            except Exception as exc:  # noqa: BLE001 - the sweep failed; the solve stands
                traceback.print_exc(file=self.tee)
                regret = {"error": str(exc)}

        self._write_record(
            status=status,
            plan_year=plan_year,
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
            age_search=age_search,
            regret=regret,
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

    def _regret_sweep(self, plan, options) -> dict:
        """I8's per-request run: "what a different conversion would have cost".

        `stresstests.run_conversion_regret_sweep` at "Quick look" size (its cheapest), over
        the historical windows whose starts fit a full horizon of data. `regret.json` joins
        the artifacts (published atomically, as the others) and the summary goes into
        record.json; the sweep re-solves the plan per scenario, so it can run a while (the
        job's heartbeat and cancel checks run between scenarios).
        """
        from owlplanner import summarize_conversion_regret
        from owlplanner.rates import FROM

        yend = int(plan.year_n[0]) - plan.N_n  # the last start with a full horizon (histYendMax)
        result = plan.runConversionRegret(
            plan.objective, options, FROM, yend,
            person=0,
            n_grid=REGRET_N_GRID, grid_pad=REGRET_GRID_PAD,
            n_scenarios=REGRET_N_SCENARIOS, seed=REGRET_SEED, milp_downgrade=True,
            on_scenario=lambda *args: self.check(),
        )
        summary = summarize_conversion_regret(result)
        staging = self.results_dir / f".attempt-{self.token[:8]}"
        staging.mkdir(exist_ok=True)
        try:
            self._write_json(staging, R.REGRET_JSON, summary)
            try:
                self.job.publish(self.token, staging, (R.REGRET_JSON,))
            except R.TokenChanged as exc:
                raise JobCancelled(str(exc)) from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return summary

    def _write_json(self, folder, name, doc):
        from owlplanner.cli.formatters import _NumpyEncoder

        text = json.dumps(doc, cls=_NumpyEncoder, indent=1, sort_keys=True) + "\n"
        Path(folder, name).write_text(text, encoding="utf-8", newline="\n")

    def _write_record(self, *, status, plan_year=None, plan_doc=None, options=None, started=None,
                      finished=None, wall_time_seconds=None, solver=None, gap=None,
                      iterations=None, rates=None, plan_pkl_sha256=None, age_search=None,
                      regret=None, error=None):
        doc = R.build_record(
            run_id=str(self.job.doc.get("run_id") or ""),
            results_id=self.job.id,
            plan_year=plan_year if plan_year is not None else self.job.plan_year,
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
            age_search=age_search,
            regret=regret,
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

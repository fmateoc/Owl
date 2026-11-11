"""The worker: one solve of one run, in a fresh interpreter (run-library-design.md, 8.2).

Run as ``python -m owlplanner.library.worker RESULTS_DIR TOKEN``. The interface writes
`status.json` (state=waiting) in the results folder before dispatch (S2); this program
claims it under its token (state=running, PID and the process start token, S9), checks that
this is the run's plan year (R1: a run is solved only in the year its inputs were entered
for; design section 8.3), builds the plan from the run's frozen files (`inputs/Case.toml` +
`HFP.xlsx`, the `owlcli run` route), solves it with the job's preset options, and writes the
results folder's artifacts and `record.json`.

Cores (performance review, 2026-11-11): the queue gives the job a share of its cores at
dispatch (`cores` in `status.json`, `JobManager.tick`). The two claiming-age presets score
many plans; with more than one core they score them side by side in that many processes
(`_ProcessPool`). Every other job is one solve and ignores the number.

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
from .presets import LOCAL_SEARCH_EFFORT, resolve_options
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
# Whose first-year conversion the sweep pins: the case's first person (upstream's interface
# offers a choice, `regret_person`; this job does not). The summary names the person (AG10).
REGRET_PERSON = 0


def _load_work_sweep():
    """`owlplanner.work_sweep`, the phase-5 claiming-age sweep.

    The "Ages, thorough" preset shares that one implementation with
    `fork-notes/synthetic/run_suite.py` (the fork's rule; `library.agesearch` is the same
    sharing for the two-stage search). Imported lazily: it pulls in the solver stack and
    only this preset runs it. (It used to be loaded from `fork-notes/phase5/work_sweep.py`
    by path; the sweep moved into `src/owlplanner`, 2026-11-05.)
    """
    from owlplanner import work_sweep

    return work_sweep


def _follow_parent():
    """A pool process ends when the worker that started it does (its initializer).

    A forced cancel kills the worker's process alone (`procs.kill_process`, against its start
    token); without this its pool would go on solving, each process to the end of its plan,
    on cores the queue already counts as free. A thread waits on the parent's handle (the
    solver releases the interpreter lock while it runs) and exits the process when it fires.
    """
    import multiprocessing

    parent = multiprocessing.parent_process()
    if parent is None:
        return

    def watch():
        parent.join()
        os._exit(1)

    threading.Thread(target=watch, daemon=True, name="owl-follow-parent").start()


class _ProcessPool:
    """`pool.map` on the cores the queue gave the job: one process a core (spawned).

    The interface of `_SerialPool` below, for `work_sweep.run_variant` and
    `agesearch.two_stage_ages`: `map(fn, items)` returns the results in the items' order, so
    what is decided from them is what the serial pool decides. `fn` and the items cross a
    process boundary (`work_sweep.score` and `agesearch.score_trial` are module-level
    functions over plain data). Spawned, never forked: a forked child of a process that has
    already solved spins in its first MIP (CLAUDE.md, "Fork after HiGHS hangs"), and the
    age search's first stage solves in this process before the pool is used.

    `check` (the worker's cancellation hook) runs while the pool works, every
    `CHECK_SECONDS`. When it raises, or a plan does, `close` ends the processes at once: the
    serial pool can only stop between two plans.
    """

    def __init__(self, cores, check=None):
        self.cores = max(1, int(cores))
        self._check = check
        self._executor = None

    def _pool(self):
        if self._executor is None:
            import multiprocessing
            from concurrent.futures import ProcessPoolExecutor

            self._executor = ProcessPoolExecutor(
                max_workers=self.cores, mp_context=multiprocessing.get_context("spawn"),
                initializer=_follow_parent)
        return self._executor

    def map(self, fn, items):
        from concurrent.futures import wait

        if self._check is not None:
            self._check()
        try:
            futures = [self._pool().submit(fn, item) for item in items]
            pending = set(futures)
            while pending:
                _, pending = wait(pending, timeout=CHECK_SECONDS)
                if pending and self._check is not None:
                    self._check()
            return [future.result() for future in futures]
        except BaseException:
            self.close()
            raise

    def close(self):
        """End the pool's processes now, whatever they are solving."""
        executor, self._executor = self._executor, None
        if executor is None:
            return
        stop = getattr(executor, "terminate_workers", None)  # Python 3.14
        if stop is not None:
            stop()
            return
        for process in list((getattr(executor, "_processes", None) or {}).values()):
            process.terminate()
        executor.shutdown(wait=False, cancel_futures=True)


class _SerialPool:
    """`work_sweep`'s pool interface (`pool.map`), run in this process.

    What a job with one core uses (the CLI's default, `--jobs 1`, is serial too); with more,
    `_ProcessPool`. `check` (the worker's cancellation hook) runs before every item:
    the sweep logs once per person pass, and a pass of nine ages at up to `TIME_LIMIT`
    (900 s) each kept a cooperative cancel waiting up to two hours (review AG11).
    """

    def __init__(self, check=None):
        self._check = check

    def map(self, fn, items):
        out = []
        for item in items:
            if self._check is not None:
                self._check()
            out.append(fn(item))
        return out

    def close(self):
        pass


_ITER_RE = re.compile(r"\bIter:\s*(\d+)")
_WARN_RE = re.compile(r"WARNING|ERROR")
# Upstream's line when local search finds its wall-clock budget spent at the start of a
# round (`localsearch.LocalSearch.solve`, a verbose line): the search stopped by the clock,
# not by its node caps, so the result can depend on how busy the computer was. The record
# counts them (`search_budget_cuts`); `tests/library/test_worker.py` checks upstream still
# words it so. No such line exists for a single step ended by its own time cap.
BUDGET_CUT_MARK = "Local search: time budget spent"


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

    While `quiet` is set (the "Ages" preset's search stages, step 6, and the "regret" job's
    sweep, review AJ2), every line still goes to solve.log and the cancellation check still
    runs, but the line is not read as the solve's own: run_suite.py keeps the stage warnings
    out of the record ("their warnings are not in the report"), and an unsettled candidate or
    historical scenario is not a problem with the published solve.

    Local search's "time budget spent" lines are counted either way, apart: `budget_cuts`
    for the published solve, `budget_cuts_stages` while quiet (a candidate cut by the clock
    is scored on a shorter search than its neighbours).

    `adopt` reads a log already written, quietly, as the published solve's (the "Ages"
    preset publishes its winning candidate's plan, P4a): the file is not written again.
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
        self.budget_cuts = 0
        self.budget_cuts_stages = 0

    def write(self, text):
        self._fh.write(text)
        self._fh.flush()
        self._pending += text
        *lines, self._pending = self._pending.split("\n")
        self._read(lines, self.quiet)
        if self._check is not None and time.monotonic() - self._checked > CHECK_SECONDS:
            self._checked = time.monotonic()
            self._check()

    def adopt(self, text):
        """Read `text`, a solve's log that is already in solve.log (written while quiet), as
        the published solve's own: its warnings, loop iterations, last line and clock cuts.

        The "Ages" preset publishes the winning stage-2 candidate's plan instead of solving it
        again (P4a); the record must say what that solve's log says, as it said what the
        repeated solve's did. Its clock cuts were counted among the stages' when it was
        written, and are the published solve's too.
        """
        self._read(text.split("\n"), False)

    def _read(self, lines, quiet):
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if BUDGET_CUT_MARK in stripped:
                if quiet:
                    self.budget_cuts_stages += 1
                else:
                    self.budget_cuts += 1
            if quiet:
                continue
            self.last_line = stripped
            if _WARN_RE.search(stripped):
                self.warnings.add(stripped.split("|", 3)[-1].strip() if "|" in stripped else stripped)
            match = _ITER_RE.search(stripped)
            if match:
                self.iteration = max(self.iteration or 0, int(match.group(1)))

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
        self.pool = None  # the claiming-age presets' pool, on the cores the queue gave
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
            if self.pool is not None:
                self.pool.close()
            self._beat_stop.set()
            if self._beat_thread is not None:
                self._beat_thread.join(timeout=5.0)
            self.tee.close()
        return state

    def _pool(self):
        """The pool the claiming-age presets score their plans on: one process for each core
        the queue gave this job (`cores` in its record), this process alone with one."""
        if self.pool is None:
            cores = self.job.cores  # as `claim` read it: the dispatcher wrote it before this process
            self.pool = _ProcessPool(cores, self.check) if cores > 1 else _SerialPool(self.check)
        return self.pool

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

        # The Ages presets (design 8.1, step 6): the search first, then the plan at the ages
        # it picked. "ages" runs run_suite.py's two-stage search (`library.agesearch`) and
        # publishes the winning candidate's own plan (P4a: it was solved again here, with
        # the same options); "ages_thorough" runs work_sweep.py's whole-year sweep
        # (`_ages_thorough`, section 8.1's "Ages, thorough") and solves the decided cell
        # again. The stages' logs go to solve.log but their warnings stay out of the record
        # (run_suite.py's rule); the kept candidate's are read as the published solve's.
        preset = str(self.job.doc.get("preset") or "custom")
        overrides = self.job.doc.get("options")
        age_search = None
        scores = None
        thorough = None  # "Ages, thorough": (work_sweep, its scorer config, the decided cell)
        winner = None  # "ages": the winning stage-2 candidate (`agesearch.Winner`), published as it is
        if preset in ("ages", "ages_thorough") and str(
                diconf.get("solver_options", {}).get("withSSAges", "fixed")
        ).strip().lower() != "fixed":
            self.job.touch(self.token, step="searching the claiming ages")
            self.check()
            self.tee.quiet = True
            try:
                if preset == "ages_thorough":
                    self.job.touch(self.token, step="the claiming-age sweep (every whole-year pair)")
                    ages, candidates, scores, thorough = self._ages_thorough(diconf, dirname)
                else:
                    pool = self._pool()
                    ages, candidates, winner = two_stage_ages(
                        diconf, dirname, log=self.tee, check=self.check, effort=LOCAL_SEARCH_EFFORT,
                        overrides=overrides, keep=True,
                        pool=pool if isinstance(pool, _ProcessPool) else None)
            finally:
                self.tee.quiet = False
            age_search = {"chosen": ages, "candidates": candidates}
            if winner is not None:
                age_search["stage_2_plan"] = True  # published as scored, not solved again (P4a)
            if thorough is not None:
                # What scored the decided cell (review AH1): the final solve repeats it.
                cell = thorough[2]
                age_search["decided"] = {"used": cell.get("used"), "value": cell.get("value"),
                                         "proved": cell.get("proved"), "gap": cell.get("gap")}
            if winner is None:
                diconf = apply_overrides(diconf, fixed_ages(ages))
                self.job.touch(self.token, step="building the plan")
                self.check()

        if winner is not None:
            # P4a: the winning candidate was solved at these ages with the options this solve
            # would use (`agesearch.candidate_options`, which `resolve_options` reads for
            # "ages"), so its plan is the one published. Its log is in solve.log among the
            # candidates'; the record reads it as this solve's.
            plan, options = winner.plan, winner.options
            self.tee.write(f"The plan at claiming ages {ages} is the stage-2 candidate's own, "
                           "published as solved there (not solved again).\n")
            self.tee.adopt(winner.log)
            self.check()
        else:
            plan = config_to_plan(diconf, dirname, verbose=True, logstreams=[self.tee], loadHFP=True)
            self.job.touch(self.token, step="solving")
            self.check()
            options = resolve_options(preset, plan.solverOptions, overrides)
        if thorough is not None:
            # "Ages, thorough" publishes the plan its sweep decided on (review AH1): the decided
            # cell re-solved with the options that scored it (branch-and-bound at the sweep's
            # gap, or the local search it fell back to), not the case's own -- with no gap,
            # `plan.py` loosens it to MILP_GAP under withMedicare = "optimize", and the plan
            # came out 1,208 below the decided cell on the synthetic household.
            ws, cfg, cell = thorough
            options = {k: v for k, v in options.items() if k not in ws.PRESET_KEYS}
            options.update(ws.scorer_options(plan, cfg, cell.get("used") or "branch-and-bound"))
        options = parse_solver_options(options)
        if winner is None:
            plan.solve(plan.objective, options)
        wall = time.time() - t0
        if thorough is not None and plan.caseStatus == "solved":
            age_search["published_value"] = float(plan._objectiveValue(plan.objective))

        self.check()
        status = plan.caseStatus
        plan_doc = None
        plan_sha = None
        if status == "solved":
            self.job.touch(self.token, step="writing the results")
            plan_doc = plan_to_dict(plan)
            summary = plan_metrics(plan)
            plan_sha = self._publish_results(summary, plan_doc, plan, scores)
        else:
            self.job.update(self.token, error=plan.solverMessage or status)

        # I8's "regret" preset, one per request (design 14.1): the sweep runs after the base
        # results are published, so a failed sweep keeps them (record.json says what failed).
        regret = None
        if status == "solved" and preset == "regret":
            # The sweep re-solves the plan on clones that share its logger, so every scenario's
            # warnings reach the tee: quiet, as during the Ages stages, they go to solve.log but
            # not into the record, which is the base solve's (review AJ2: 126 warnings against
            # the same solve's 1 under "custom", and the Run page listed seven historical
            # scenarios' "Exiting loop on maximum iterations." as problems of a settled plan).
            # The sweep's own convergence counts are in its summary.
            self.tee.quiet = True
            try:
                self.job.touch(self.token, step="the conversion regret sweep")
                self.check()
                regret = self._regret_sweep(plan, options)
            except JobCancelled:
                raise
            except Exception as exc:  # noqa: BLE001 - the sweep failed; the solve stands
                traceback.print_exc(file=self.tee)
                regret = {"error": str(exc)}
            finally:
                self.tee.quiet = False

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

    def _publish_results(self, summary, plan_doc, plan, scores=None) -> str:
        """Write the artifacts and publish them atomically with respect to "run again" (G2).

        The files are staged in a private folder beside the record and renamed into place
        under the job's lock, the token still owning the job (`JobRecord.publish`): a worker
        that wakes after "run again" publishes nothing, so one results folder never holds two
        attempts' artifacts (the F2 guard covered `status.json` and `record.json` only).
        `scores` is "Ages, thorough" whole-year sweep (`work_sweep.py`'s --json row, I7's
        claiming-age map reads it). Returns the plan cache's sha256 for record.json.
        """
        staging = self.results_dir / f".attempt-{self.token[:8]}"
        staging.mkdir(exist_ok=True)
        published = (R.SUMMARY_JSON, R.PLAN_JSON, R.RESULTS_XLSX, R.PLAN_PKL)
        try:
            self._write_json(staging, R.SUMMARY_JSON, summary)
            self._write_json(staging, R.PLAN_JSON, plan_doc)
            if scores is not None:
                self._write_json(staging, R.SCORES_JSON, [scores])
                published = published + (R.SCORES_JSON,)
            plan.saveWorkbook(basename=str(staging / R.RESULTS_XLSX), overwrite=True,
                              with_config="first")
            plan_sha = R.save_plan(plan, staging)
            try:
                self.job.publish(self.token, staging, published)
            except R.TokenChanged as exc:
                raise JobCancelled(str(exc)) from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return plan_sha

    def _regret_sweep(self, plan, options) -> dict:
        """I8's per-request run: "what a different conversion would have cost".

        `stresstests.run_conversion_regret_sweep` at "Quick look" size (its cheapest), over
        the historical windows whose starts fit a full horizon of data. `regret.json` joins
        the artifacts (published atomically, as the others) and holds the sweep itself -- the
        per-scenario curves `summarize_conversion_regret` reads (review AE3) -- while its
        summary goes into record.json; the sweep re-solves the plan per scenario, so it can
        run a while (the job's heartbeat and cancel checks run between scenarios).
        """
        from owlplanner import summarize_conversion_regret
        from owlplanner.rates import FROM

        yend = int(plan.year_n[0]) - plan.N_n  # the last start with a full horizon (histYendMax)
        result = plan.runConversionRegret(
            plan.objective, options, FROM, yend,
            person=REGRET_PERSON,
            n_grid=REGRET_N_GRID, grid_pad=REGRET_GRID_PAD,
            n_scenarios=REGRET_N_SCENARIOS, seed=REGRET_SEED, milp_downgrade=True,
            on_scenario=lambda *args: self.check(),
        )
        summary = dict(summarize_conversion_regret(result))
        # Whose first-year conversion the sweep pinned (review AG10): the run page names it.
        names = list(getattr(plan, "inames", []) or [])
        summary["person"] = names[REGRET_PERSON] if REGRET_PERSON < len(names) else None
        staging = self.results_dir / f".attempt-{self.token[:8]}"
        staging.mkdir(exist_ok=True)
        try:
            self._write_json(staging, R.REGRET_JSON, result)
            try:
                self.job.publish(self.token, staging, (R.REGRET_JSON,))
            except R.TokenChanged as exc:
                raise JobCancelled(str(exc)) from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return summary

    def _ages_thorough(self, diconf, dirname) -> tuple:
        """(ages in years, candidates, scores.json's row, (work_sweep, scorer config, decided
        cell)): section 8.1's "Ages, thorough".

        `owlplanner.work_sweep`'s own `run_variant`: stage (a)'s exact-LP search
        and stage (c)'s sweep of every whole-year pair of the searched people, each scored
        by branch-and-bound at gap 1e-5 (local search kept for a plan it does not prove);
        the loop search (b) is skipped and the deposit-split check (`--eta`) is off -- both
        are sensitivities, not the decision. Decided ages are months in the row (`best`);
        they come back as years for `fixed_ages`, and the row itself is `scores.json` (the
        claiming-age map reads it, I7). Runs a while (29-51 min per variant on the chris+pat
        dry run); the cancel checks run at every sweep message. The last item is what the final
        solve needs to re-solve the decided cell the way it was scored (review AH1). The plans
        of a pass are scored side by side when the queue gave the job more than one core
        (`_pool`): each cell is an independent solve, so the scores are the serial ones.
        """
        import types

        from .agemap import parse_scores

        ws = _load_work_sweep()
        args = types.SimpleNamespace(
            no_loop=True, decider="bb", gap=1e-5, max_time=ws.TIME_LIMIT,
            ls_time=7200.0, ls_step_time=1800.0, passes=2, eta=[])
        cfg = ws.scorer_config(args)  # `run_variant`'s own scorer settings, for the final solve

        def log(message):
            self.tee.write(str(message) + "\n")
            self.check()

        row = ws.run_variant("base", diconf, dirname, args, self._pool(), log)
        scores = {k: v for k, v in row.items() if k != "_cache"}
        chosen = [m / 12.0 for m in row.get("best") or []]
        amap = parse_scores([scores])[0]
        candidates = [[[m / 12.0 for m in cell.ages], cell.value]
                      for cell in sorted(amap.cells, key=lambda c: c.ages)]
        return chosen, candidates, scores, (ws, cfg, dict(row.get("result") or {}))

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
            search_budget_cuts={"solve": self.tee.budget_cuts, "stages": self.tee.budget_cuts_stages},
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

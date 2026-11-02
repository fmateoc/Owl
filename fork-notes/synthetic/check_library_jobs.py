"""Check build step 2's acceptance on the synthetic household.

`run-library-design.md` section 11, step 2, Check column:

1. "a synthetic run solves in the background" -- queued through `JobManager`, a real
   detached worker, artifacts and `record.json` written;
2. "a closed tab, a server restart and a still-waiting queue do not lose a job (S2)" -- a
   waiting job is dispatched by a fresh manager; a live worker's job is adopted; a dead
   one is marked interrupted with "run again";
3. "'Open in Owl' restores Graphs without a solve" -- `owlbridge.openCaseFromPlan` builds
   the page keys from the run's cached `plan.pkl` (the Graphs page render itself is
   `tests/ui/test_open_in_owl.py`);
4. "two solves on different days give identical results" -- the same run solved under two
   pretend wall-clock days of its plan year (design section 8.3, revised 2026-11-02: no frozen
   "as of" date; a run is solved only in its plan year);
5. a run is refused outside its plan year (R1) -- solved on a pretend January 1 of the next
   year, it fails with a "refused" record and writes no results.

Run after `make_cases.py`, from anywhere:

    uv run python fork-notes/synthetic/check_library_jobs.py

Prints one line per check and a summary; exits 1 if any check fails. The solves are the
synthetic baseline (`Case_ari+noa.toml` + its workbook) at the `quick` preset: the default
loop with the claiming ages held, as the run page queues it.
"""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "ui"))

from owlplanner.library import JobManager, Library, import_case  # noqa: E402
from owlplanner.library import results as R  # noqa: E402
from owlplanner.library.procs import pid_alive  # noqa: E402
from owlplanner.library.worker import run_job  # noqa: E402

CASES = Path(__file__).parent / "cases"
CASE = CASES / "Case_ari+noa.toml"
WORKBOOK = CASES / "HFP_ari+noa.xlsx"

# The plan's logger writes DEBUG to stdout/stderr; keep the script's own output readable.
_quiet = contextlib.redirect_stdout(io.StringIO())
_real_out = sys.stdout


@contextlib.contextmanager
def pretend_real_today(iso: str):
    """Pretend the wall clock reads `iso` for every direct `date.today()` (tests/library/conftest.py)."""
    import datetime as dt
    import sys as _sys

    real_date = dt.date
    day = real_date.fromisoformat(iso)

    class _Pretend(real_date):
        @classmethod
        def today(cls):
            return day

    saved = []
    for mod in list(_sys.modules.values()):
        if mod is None:
            continue
        cls = getattr(mod, "date", None)
        if isinstance(cls, type) and issubclass(cls, real_date):
            saved.append((mod, mod.date))
            mod.date = _Pretend
    try:
        yield day
    finally:
        for mod, old in saved:
            mod.date = old


def _job_for(run, name):
    scenario = json.loads((run.path / "inputs" / "scenario.json").read_text(encoding="utf-8"))
    return R.JobRecord.create(run.path / "results" / name, run_id=run.id, run_name=run.name,
                              preset="quick", options={"withSSAges": "fixed"},
                              plan_year=scenario["plan_year"])


def main() -> int:
    if not CASE.exists() or not WORKBOOK.exists():
        print(f"missing {CASE.name} / {WORKBOOK.name} (run make_cases.py first)")
        return 2

    failures = 0
    checks = 0
    with tempfile.TemporaryDirectory() as tmp, _quiet:
        library = Library.open(Path(tmp) / "library")
        scenario = import_case(CASE, hfp_path=WORKBOOK)
        run = library.save_run(name="ari+noa baseline", scenario=scenario).run

        # 1. a synthetic run solves in the background -----------------------------
        checks += 1
        manager = JobManager(library)
        job = manager.enqueue(run, preset="quick")
        deadline = time.time() + 1800
        while time.time() < deadline:
            job.refresh()
            if job.state in (R.DONE, R.FAILED, R.INTERRUPTED):
                break
            manager.tick()
            time.sleep(1.0)
        job.refresh()
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8")) \
            if (job.results_dir / R.RECORD_JSON).exists() else {}
        ok = job.state == R.DONE and record.get("status") == "solved"
        failures += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'} background solve: {job.state}"
              f" ({record.get('wall_time_seconds')}s, {record.get('preset')},"
              f" plan year {record.get('plan_year')}, gap {record.get('gap')},"
              f" {len(record.get('warnings', []))} warning(s))",
              file=_real_out)

        # 2. a closed tab, a restart, a still-waiting queue (S2) --------------------
        checks += 1
        waiting = _job_for(run, "s2-waiting")  # queued, never dispatched: the tab closes
        restarted = JobManager(library)       # a new server process
        dispatched = []
        real_spawn = restarted._spawn

        def _remember_and_spawn(j):
            dispatched.append(j)
            real_spawn(j)

        restarted._spawn = _remember_and_spawn
        restarted.tick()
        keeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
        try:
            live = _job_for(run, "s2-live")
            live.update(state=R.RUNNING, pid=keeper.pid, heartbeat=R.now_iso())
            dead = _job_for(run, "s2-dead")
            dead.update(state=R.RUNNING, pid=999_999_999, heartbeat=R.now_iso())
            restarted.adopt()
            deadline = time.time() + 1800
            while time.time() < deadline:
                waiting.refresh()
                if waiting.state in (R.DONE, R.FAILED, R.INTERRUPTED):
                    break
                restarted.tick()
                time.sleep(1.0)
            waiting.refresh()
            live.refresh()
            dead.refresh()
            ok = (any(j.id == waiting.id for j in dispatched) and waiting.state == R.DONE
                  and live.state == R.RUNNING and pid_alive(keeper.pid)
                  and dead.state == R.INTERRUPTED and "died" in (dead.doc.get("error") or ""))
            failures += 0 if ok else 1
            print(f"{'ok  ' if ok else 'FAIL'} restart: waiting dispatched ({waiting.state}),"
                  f" live adopted ({live.state}), dead interrupted ({dead.state})",
                  file=_real_out)
        finally:
            keeper.kill()
            keeper.wait(timeout=30)

        # 3. "Open in Owl" restores Graphs without a solve -------------------------
        checks += 1
        import owlbridge

        plan = R.load_plan(job.results_dir)
        keys_ok = False
        if plan is not None:
            _, dic = owlbridge.openCaseFromPlan(plan)
            needed = ("plan", "caseStatus", "summaryDf", "metricsDict", "objective",
                      "rateType", "interpMethod", "spendingProfile", "allocType",
                      "txbl0", "txDef0", "txFree0", "hsa0")
            keys_ok = dic.get("caseStatus") == "solved" and all(k in dic for k in needed)
        failures += 0 if keys_ok else 1
        print(f"{'ok  ' if keys_ok else 'FAIL'} open in owl: {len(dic) if plan is not None else 0}"
              " page keys from the cached plan, caseStatus 'solved'", file=_real_out)

        # 4. two solves on different days give identical results -------------------
        checks += 1
        outputs = []
        year = scenario["plan_year"]
        for day, name in ((f"{year}-01-10", "d1"), (f"{year}-11-20", "d2")):
            with pretend_real_today(day), _quiet:
                one = _job_for(run, f"s4-{name}")
                state = run_job(one.results_dir, one.token)
            summary = json.loads((one.results_dir / R.SUMMARY_JSON).read_text(encoding="utf-8")) \
                if state == R.DONE else None
            plan_doc = json.loads((one.results_dir / R.PLAN_JSON).read_text(encoding="utf-8")) \
                if state == R.DONE else None
            if plan_doc is not None:
                plan_doc["solve_time_seconds"] = None  # load-dependent
            outputs.append((summary, plan_doc))
        same = outputs[0] == outputs[1] and outputs[0][0] is not None
        failures += 0 if same else 1
        print(f"{'ok  ' if same else 'FAIL'} determinism: identical summary and plan"
              f" solved on two different days of {year}", file=_real_out)

        # 5. refused outside the plan year (R1) -------------------------------------
        checks += 1
        with pretend_real_today(f"{year + 1}-01-01"), _quiet:
            late = _job_for(run, "s5-new-year")
            state = run_job(late.results_dir, late.token)
        record = R.read_record(late.results_dir) or {}
        refused = (state == R.FAILED and record.get("status") == "refused"
                   and not (late.results_dir / R.SUMMARY_JSON).exists())
        failures += 0 if refused else 1
        print(f"{'ok  ' if refused else 'FAIL'} plan year: solved on {year + 1}-01-01, {state},"
              f" record {record.get('status')!r}", file=_real_out)

    print(f"{checks - failures}/{checks} step-2 checks pass", file=_real_out)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

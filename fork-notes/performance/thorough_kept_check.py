""""Claiming ages, every pair tried" publishes its decided cell's own plan (performance review
P4a for `ages_thorough`): checked through real workers on Case_cameron (six whole-year cells,
seconds), run outside pytest so the spawned pool's processes and the worker see the same date.

    .venv/bin/python fork-notes/performance/thorough_kept_check.py [CASE.toml]

Three jobs of one run, one after the other: on one core (the sweep in the worker's process), on
two (the cells scored in spawned processes, each kept plan pickled there and read back by the
worker), and on one core with no plan kept (`work_sweep.load_kept_plan` patched to None: the
route before the change, the decided cell solved again). Checks: the three publish the same
plan.json and summary.json (the solve's clock aside) and the same options; the first two say
`decided_plan`, the third does not; no staging folder is left.
"""

import copy
import json
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from owlplanner import work_sweep  # noqa: E402
from owlplanner.library import Library, import_case, results as R  # noqa: E402
from owlplanner.library.worker import run_job  # noqa: E402


def drop_clock(doc):
    if isinstance(doc, dict):
        doc.pop("solve_time_seconds", None)
        for value in doc.values():
            drop_clock(value)
    return doc


def read(job, name):
    return json.loads((job.results_dir / name).read_text(encoding="utf-8"))


def main():
    case = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "examples" / "Case_cameron.toml")
    doc = import_case(case)
    doc = copy.deepcopy(doc)
    doc["case"]["solver_options"]["withSSAges"] = "optimize"
    lib = Library.open(Path(tempfile.mkdtemp(prefix="owl-thorough-")) / "library")
    run = lib.save_run(name="searches", scenario=doc).run
    jobs = {}
    for label, cores, kept in (("one core", 1, True), ("two cores", 2, True), ("solved again", 1, False)):
        job = R.JobRecord.create(run.path / "results" / f"{len(jobs)}_ages_thorough", run_id=run.id,
                                 run_name=run.name, preset="ages_thorough", options={},
                                 plan_year=date.today().year)
        job.update(cores=cores)
        saved = work_sweep.load_kept_plan
        if not kept:
            work_sweep.load_kept_plan = lambda keep_dir, ages: None
        t0 = time.time()
        try:
            state = run_job(job.results_dir, job.token)
        finally:
            work_sweep.load_kept_plan = saved
        record = read(job, R.RECORD_JSON)
        search = record.get("age_search") or {}
        print(f"{label}: {state} in {time.time() - t0:.1f} s; ages {search.get('chosen')} of "
              f"{len(search.get('candidates') or [])} cells; decided_plan {search.get('decided_plan')}; "
              f"published {search.get('published_value')}, cell {(search.get('decided') or {}).get('value')}",
              flush=True)
        jobs[label] = job

    checks = []
    first = jobs["one core"]
    for label in ("two cores", "solved again"):
        other = jobs[label]
        for name in (R.PLAN_JSON, R.SUMMARY_JSON):
            checks.append((f"{label}: {name} as on one core",
                           drop_clock(read(first, name)) == drop_clock(read(other, name))))
        checks.append((f"{label}: the same options",
                       read(first, R.RECORD_JSON)["method"]["options"]
                       == read(other, R.RECORD_JSON)["method"]["options"]))
    flags = [read(jobs[k], R.RECORD_JSON)["age_search"].get("decided_plan") for k in jobs]
    checks.append(("decided_plan on the two kept jobs only", flags == [True, True, None]))
    left = [p.name for job in jobs.values() for p in job.results_dir.iterdir() if p.name.startswith(".attempt-")]
    checks.append(("no staging folder left", not left))
    for what, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
    print(f"{sum(ok for _, ok in checks)}/{len(checks)}")


if __name__ == "__main__":
    main()

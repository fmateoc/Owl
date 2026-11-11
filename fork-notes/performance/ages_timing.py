"""Time one "Let Owl choose the claiming ages" job (performance review P4a, section 6b).

One `ages` job of the synthetic condo variant (yonkers_2027_mortgage, local search) on a
four-core queue, through a real worker; copies its solve.log, record.json and summary.json to
OUT_DIR before the temporary library goes. `ages_timing_parse.py OUT_DIR` then splits the
solve log by plan built: stage 1, each candidate, and (before `cfd26e1`) the final solve.

Run after `fork-notes/synthetic/make_cases.py`, from the repository root (or from a worktree
of another commit with `PYTHONPATH=<worktree>/src`, which the worker and its pool inherit):

    .venv/bin/python fork-notes/performance/ages_timing.py OUT_DIR

About 20-25 minutes on four cores.
"""
import shutil
import sys
import tempfile
import time
from pathlib import Path
import owlplanner
from owlplanner.library import JobManager, Library, import_case
from owlplanner.library import results as R

CASES = Path(__file__).resolve().parents[1] / "synthetic" / "cases"
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
print("code:", owlplanner.__file__, flush=True)
scenario = import_case(CASES / "Case_ari+noa_condo.toml",
                       hfp_path=CASES / "HFP_ari+noa_condo_yonkers_2027_mortgage.xlsx")
scenario["case"]["solver_options"]["withSSAges"] = "optimize"
with tempfile.TemporaryDirectory() as tmp:
    lib = Library.open(Path(tmp) / "library")
    run = lib.save_run(name="condo", scenario=scenario).run
    m = JobManager(lib, cores=4)
    t0 = time.time()
    job = m.enqueue(run, preset="ages")
    while True:
        m.tick()
        rec = R.JobRecord.read(job.results_dir)
        if rec.state in (R.DONE, R.FAILED, R.INTERRUPTED):
            break
        time.sleep(1.0)
    print("state", rec.state, "wall", round(time.time() - t0), flush=True)
    for name in (R.SOLVE_LOG, R.RECORD_JSON, R.SUMMARY_JSON):
        shutil.copy(job.results_dir / name, out / name)

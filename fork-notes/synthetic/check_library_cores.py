"""Check the queue's cores on the synthetic household (performance review, 2026-11-11).

The queue counts cores (`JobManager(cores=...)`): a job states how many solves it runs at
once when it can, gets that or all the queue has at dispatch, and its worker sizes its pool
by its record. Through real detached workers:

1. four Quick looks of one run on a four-core queue run side by side (their running times
   overlap), each with one core, and give one result to the cent;
2. on a one-core queue two Quick looks run one after the other, as before;
3. "Let Owl choose the claiming ages" on a condo variant (local search) gets the queue's four
   cores, scores its stage-2 candidates on a pool of processes, and publishes the chosen
   candidate's own plan, brought back from its process (P4a, 2026-11-11): the record says
   so, the published plan scores what the candidate scored, and solve.log shows one plan
   built for stage 1 and one per candidate, none after. (Before P4a the plan was built and
   solved again at the chosen ages; that solve, alone, scored what the candidate had scored
   beside the others, to the cent.) No search was cut by the clock, and every candidate's
   log is in solve.log.

Run after `make_cases.py`, from the repository root:

    .venv/bin/python fork-notes/synthetic/check_library_cores.py [--skip-ages]

Check 3 is five Careful-class solves and takes 10-15 minutes on four cores; `--skip-ages`
leaves it out. Prints one line per check and a summary; exits 1 if any check fails.
"""

import copy
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from owlplanner.library import JobManager, Library, import_case  # noqa: E402
from owlplanner.library import results as R  # noqa: E402
from owlplanner.library import view  # noqa: E402
from owlplanner.library.presets import LOCAL_SEARCH_EFFORT  # noqa: E402
from owlplanner.library.worker import BUDGET_CUT_MARK  # noqa: E402

CASES = Path(__file__).parent / "cases"
CASE = CASES / "Case_ari+noa_condo.toml"
WORKBOOK = CASES / "HFP_ari+noa_condo_yonkers_2027_mortgage.xlsx"

results = []


def report(name, ok, detail=""):
    results.append(ok)
    print(f"{'ok  ' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}", flush=True)


def wait_for(manager, jobs, seconds):
    """Tick until every job has ended; the jobs' records as they are then."""
    end = time.time() + seconds
    while time.time() < end:
        manager.tick()
        now = [R.JobRecord.read(job.results_dir) for job in jobs]
        if all(job.state in (R.DONE, R.FAILED, R.INTERRUPTED) for job in now):
            return now
        time.sleep(1.0)
    manager.stop_all()
    raise TimeoutError(f"jobs still running after {seconds:.0f} s")


def span(job):
    return R.stamp_seconds(job.doc.get("started")), R.stamp_seconds(job.doc.get("finished"))


def overlapping(jobs):
    """The most jobs running at one instant, from the records' own stamps (whole seconds)."""
    spans = [span(job) for job in jobs]
    return max(sum(1 for s, f in spans if s <= t < f) for t, _ in spans)


def main(skip_ages):
    scenario = import_case(CASE, hfp_path=WORKBOOK)
    with tempfile.TemporaryDirectory() as tmp:
        library = Library.open(Path(tmp) / "library")
        run = library.save_run(name="condo, ages held", scenario=scenario).run

        # 1. Four single solves on four cores.
        wide = JobManager(library, cores=4)
        jobs = [wide.enqueue(run, preset="quick") for _ in range(4)]
        started_together = sum(1 for job in jobs if R.JobRecord.read(job.results_dir).state == R.RUNNING)
        jobs = wait_for(wide, jobs, 300)
        scores = {round(view.score(view.load_result(job.results_dir)), 2) for job in jobs}
        report("four Quick looks run side by side on four cores",
               started_together == 4 and all(job.state == R.DONE and job.cores == 1 for job in jobs)
               and len(scores) == 1,
               f"{started_together} running after the last was queued, at most {overlapping(jobs)} at one "
               f"stamped second, cores {[job.cores for job in jobs]}, scores {sorted(scores)}")

        # 2. One core: one after the other.
        narrow = JobManager(library, cores=1)
        pair = [narrow.enqueue(run, preset="quick") for _ in range(2)]
        second_waits = R.JobRecord.read(pair[1].results_dir).state == R.WAITING
        pair = wait_for(narrow, pair, 300)
        (s1, f1), (s2, f2) = span(pair[0]), span(pair[1])
        report("on one core they run one after the other",
               second_waits and all(job.state == R.DONE for job in pair) and s2 >= f1,
               f"second waited: {second_waits}; first {s1:.0f}-{f1:.0f}, second {s2:.0f}-{f2:.0f}")

        if skip_ages:
            return

        # 3. The claiming-age search on the pool.
        searching = copy.deepcopy(scenario)
        searching["case"]["solver_options"]["withSSAges"] = "optimize"
        srun = library.save_run(name="condo, Owl chooses", scenario=searching).run
        t0 = time.time()
        job = wait_for(wide, [wide.enqueue(srun, preset="ages")], 3600)[0]
        wall = time.time() - t0
        record = R.read_record(job.results_dir) or {}
        search = record.get("age_search") or {}
        candidates = search.get("candidates") or []
        chosen = search.get("chosen")
        published = view.score(view.load_result(job.results_dir)) if job.state == R.DONE else None
        scored = dict((tuple(ages), value) for ages, value in candidates)
        picked = scored.get(tuple(chosen or ()))
        options = (record.get("method") or {}).get("options") or {}
        log = (job.results_dir / R.SOLVE_LOG).read_text(encoding="utf-8", errors="replace")
        report("the age search gets the queue's cores", job.state == R.DONE and job.cores == 4,
               f"state {job.state}, wanted {job.cores_wanted}, given {job.cores}, {wall:.0f} s")
        report("every stage-2 candidate is scored", len(candidates) >= 3 and all(v is not None for _, v in candidates),
               "; ".join(f"{ages} {value:,.2f}" for ages, value in candidates if value is not None))
        builds = log.count("Preparing scenario")  # Plan.__init__'s line: one per plan built
        report("the plan published is the chosen candidate's own, not solved again",
               search.get("stage_2_plan") is True and published is not None and picked is not None
               and abs(published - picked) < 0.005 and builds == 1 + len(candidates),
               f"ages {chosen}: candidate {picked}, published {published}; {builds} plans built for "
               f"{len(candidates)} candidates; stage_2_plan {search.get('stage_2_plan')}")
        report("the search ran at the library's effort and was not cut by the clock",
               all(options.get(key) == value for key, value in LOCAL_SEARCH_EFFORT.items())
               and record.get("search_budget_cuts") == {"solve": 0, "stages": 0} and BUDGET_CUT_MARK not in log,
               f"{ {key: options.get(key) for key in LOCAL_SEARCH_EFFORT} }, cuts {record.get('search_budget_cuts')}")
        report("each candidate's log is in solve.log", log.count("Local search, iteration") >= len(candidates),
               f"{log.count('Objective:')} objective lines, {len(log.splitlines())} lines")


if __name__ == "__main__":
    main("--skip-ages" in sys.argv[1:])
    print(f"{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

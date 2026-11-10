"""Build a library of N runs with real results (one Quick look, copied), then time what the pages call.

    .venv/bin/python fork-notes/performance/library_bench.py 120 /tmp/bench/library

The folder must not exist (or hold a library this script built). Performance review 2026-11-10.
"""
import sys, os, time, json, shutil, cProfile, pstats, io, copy, contextlib
from pathlib import Path
N = int(sys.argv[1]); root = Path(sys.argv[2])
os.environ["OWL_LIBRARY_DIR"] = str(root)
from owlplanner.library import Library, import_case, view, grid
from owlplanner.library import results as R
from owlplanner.library.jobs import JobManager
from owlplanner.library.worker import run_job
CASES = Path(__file__).resolve().parents[1] / "synthetic" / "cases"

def T(label, fn, n=1):
    t = time.perf_counter()
    for _ in range(n):
        r = fn()
    dt = (time.perf_counter() - t) / n
    print(f"{label:<62s} {dt*1000:10.1f} ms", flush=True)
    return r

if not root.exists():
    lib = Library.open(root)
    sc = import_case(CASES / "Case_ari+noa_condo.toml", hfp_path=CASES / "HFP_ari+noa_condo_yonkers_2027_mortgage.xlsx")
    t = time.perf_counter(); base = lib.save_run(name="baseline", scenario=sc).run; print("save_run", time.perf_counter() - t)
    plan_year = json.loads((base.path / "inputs" / "scenario.json").read_text())["plan_year"]
    job = R.JobRecord.create(base.path / "results" / "2026-11-10T10-00-00_quick", run_id=base.id, run_name=base.name,
                             preset="quick", options={"withSSAges": "fixed", "breakpointMethod": "loop"}, plan_year=plan_year)
    pr = cProfile.Profile(); t = time.perf_counter(); pr.enable()
    with contextlib.redirect_stdout(io.StringIO()):
        run_job(job.results_dir, job.token)
    pr.disable(); print("run_job quick in-process", round(time.perf_counter() - t, 2), "s"); pr.dump_stats(str(root.parent / "run_job.prof"))
    src = job.results_dir
    print("results folder:", {p.name: p.stat().st_size for p in sorted(src.iterdir()) if p.is_file()})
    ids = []
    t = time.perf_counter()
    for i in range(N - 1):
        s = copy.deepcopy(sc)
        s["case"]["savings_assets"]["taxable_savings_balances"] = [800.0 + i + 1, 800.0]
        r = lib.save_run(name=f"variant {i+1}", scenario=s, parent=base.id).run
        ids.append(r.id)
        for stamp in ("2026-11-10T10-00-00_quick", "2026-11-10T10-05-00_decision"):
            dst = r.path / "results" / stamp
            shutil.copytree(src, dst)
            for name in ("status.json", "record.json"):
                p = dst / name
                d = json.loads(p.read_text()); d["run_id"] = r.id
                if name == "record.json" and "decision" in stamp:
                    d["preset"] = "decision"
                p.write_text(json.dumps(d))
    print(f"{N-1} save_run + copies: {time.perf_counter()-t:.1f} s")
    c = lib.create_collection("grid", question="q")
    for k, rid in enumerate(ids[:36]):
        lib.add_member(c.id, rid, values={"place": ["yonkers", "whiteplains", "queens"][k % 3], "year": 2027 + (k // 3) % 6, "financing": ["cash", "mortgage"][(k // 18) % 2]})

lib = Library.open(root)
print("runs:", len(lib.runs()))
runs = T("Library.runs()", lib.runs, 5)
T("Library.get(last id)", lambda: lib.get(runs[-1].id), 5)
T("Library.scenario(run)", lambda: lib.scenario(runs[-1]), 5)
T("Library.collections()", lib.collections, 5)
m = JobManager(lib)
T("JobManager.jobs()", m.jobs, 3)
T("JobManager.tick()", m.tick, 3)
rd = runs[-1].path / "results" / "2026-11-10T10-05-00_decision"
T("view.load_result(one)", lambda: view.load_result(rd), 5)
T("grid.latest_result(one run)", lambda: grid.latest_result(runs[-1].path), 5)
T("grid.latest_result over all runs", lambda: [grid.latest_result(r.path) for r in runs], 1)
T("R.load_plan (plan.pkl)", lambda: R.load_plan(rd), 2)

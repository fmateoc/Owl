"""Shares of one historical stress test (60 start years, Quick-look options): cloning, the frontier LPs, the solves; four worker threads against one."""
import io, time, sys, collections, threading
from pathlib import Path
from owlplanner import stresstests as st
from owlplanner.config import config_to_plan, load_toml
from owlplanner.cli.set_override import apply_overrides
from owlplanner.library.agesearch import fixed_ages
T = collections.defaultdict(float); N = collections.defaultdict(int); lock = threading.Lock()
def timed(name, fn):
    def w(*a, **k):
        t = time.perf_counter()
        try: return fn(*a, **k)
        finally:
            with lock: T[name] += time.perf_counter() - t; N[name] += 1
    return w
st.clone = timed("clone (serial, main thread)", st.clone)
st._compute_efficient_frontier = timed("_compute_efficient_frontier (serial)", st._compute_efficient_frontier)
st._scenario_worker = timed("_scenario_worker (summed over threads)", st._scenario_worker)
CASES = Path("fork-notes/synthetic/cases").resolve()
diconf, dirname, _ = load_toml(f"{CASES}/Case_ari+noa_condo.toml")
diconf = apply_overrides(diconf, ["household_financial_profile.HFP_file_name=HFP_ari+noa_condo_yonkers_2027_mortgage.xlsx"] + fixed_ages([70, 70]))
from owlplanner.library.presets import resolve_options
from owlplanner.config.schema import parse_solver_options
import os
_cpu = os.cpu_count
for workers in (4, 1):
    longevity = False; os.cpu_count = lambda: workers
    T.clear(); N.clear()
    plan = config_to_plan(diconf, dirname, verbose=False, logstreams=[io.StringIO()], loadHFP=True)
    n = int(sys.argv[1]); OPTS = parse_solver_options(resolve_options("quick", plan.solverOptions, {}))
    t = time.perf_counter()
    out = st.run_stochastic_spending(plan, OPTS, "historical", ystart=1928, yend=1928 + n - 1, with_longevity=longevity,
                                     sexes=["F", "M"] if longevity else None, seed=7)
    wall = time.perf_counter() - t
    print(f"historical, {n} start years, {workers} worker thread(s): wall {wall:.1f} s")
    for k in T: print(f"   {k:42s} {T[k]:8.2f} s  {N[k]:4d} calls  ({'%.1f%% of wall' % (100*T[k]/wall) if 'summed' not in k else 'thread-seconds'})")

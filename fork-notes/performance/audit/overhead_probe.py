"""Candidate claim 4.2 (and 3.2, 4.3): how much of a Careful solve is the Python the candidate wants cached?
Cumulative top-level timers on a real local-search solve (yonkers_2027_mortgage, ages 70/70)."""
import copy, io, json, sys, time, threading, collections
from pathlib import Path
from owlplanner import plan as planmod, abcapi, localsearch, amorepair
from owlplanner.config import config_to_plan, load_toml
from owlplanner.config.schema import parse_solver_options
from owlplanner.cli.set_override import apply_overrides
from owlplanner.library.presets import resolve_options
from owlplanner.library.agesearch import fixed_ages

T = collections.defaultdict(float); N = collections.defaultdict(int); tl = threading.local()
def timed(name, fn):
    def w(*a, **k):
        d = getattr(tl, "d", None)
        if d is None: d = tl.d = collections.defaultdict(int)
        d[name] += 1
        t = time.perf_counter()
        try: return fn(*a, **k)
        finally:
            d[name] -= 1
            if d[name] == 0:
                T[name] += time.perf_counter() - t; N[name] += 1
    return w
copy.deepcopy = timed("copy.deepcopy (top level)", copy.deepcopy)
abcapi.ConstraintMatrix.to_csr = timed("ConstraintMatrix.to_csr", abcapi.ConstraintMatrix.to_csr)
planmod._MoneyScaling.for_mip = classmethod(timed("_MoneyScaling.for_mip", planmod._MoneyScaling.for_mip.__func__))
for nm in ("_run_highs", "_restoreExclusions", "_repairBracketOrder", "_buildConstraints", "_adjustParameters", "_ss_streams", "_earningsTestResult",
           "_incomeCeiling", "_snapBinaries", "_run_mip", "_configure_ss_taxability_lp", "_configure_Medicare_binary_variables",
           "_add_local_taxable_income"):
    setattr(planmod.Plan, nm, timed("Plan." + nm, getattr(planmod.Plan, nm)))
amorepair.max_row_violation = timed("amorepair.max_row_violation", amorepair.max_row_violation)
localsearch.LocalSearch._fingerprint = timed("LocalSearch._fingerprint", localsearch.LocalSearch._fingerprint)
localsearch.LocalSearch._relax_links = timed("LocalSearch._relax_links", localsearch.LocalSearch._relax_links)

preset, hfp, extra = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
CASES = Path("fork-notes/synthetic/cases").resolve()
diconf, dirname, _ = load_toml(f"{CASES}/Case_ari+noa_condo.toml")
diconf = apply_overrides(diconf, [f"household_financial_profile.HFP_file_name={hfp}"] + fixed_ages([70, 70]))
plan = config_to_plan(diconf, dirname, verbose=True, logstreams=[io.StringIO()], loadHFP=True)
opts = resolve_options(preset, plan.solverOptions, extra)
t = time.perf_counter(); plan.solve(plan.objective, parse_solver_options(opts)); wall = time.perf_counter() - t
print(f"{preset} {extra}: {plan.caseStatus}, wall {wall:.1f} s, amo={getattr(plan, 'amo', None)!r}")
for k in sorted(T, key=T.get, reverse=True):
    print(f"  {k:45s} {T[k]:9.3f} s  {N[k]:5d} calls  {100*T[k]/wall:6.2f}% of wall")

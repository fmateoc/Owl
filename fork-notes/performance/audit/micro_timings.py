"""Milliseconds of the Python-side operations the second review proposes to cache or vectorize (synthetic household, ages 70/70)."""
import copy, io, pickle, time, sys
from pathlib import Path
import numpy as np
from owlplanner.config import config_to_plan, load_toml
from owlplanner.config.plan_bridge import clone
from owlplanner.config.schema import parse_solver_options
from owlplanner.cli.set_override import apply_overrides
from owlplanner.library.presets import resolve_options
from owlplanner.library.agesearch import fixed_ages
from owlplanner import hfp_io, star, thresholds, export, brackets, amorepair
from owlplanner.cli import formatters
from owlplanner.library import results as R, sequences, builder
from owlplanner.rate_models import _builtin_impl as bi

def t(label, fn, n=5):
    best = 1e9
    for _ in range(n):
        s = time.perf_counter(); out = fn(); best = min(best, time.perf_counter() - s)
    print(f"{label:62s} {best*1e3:10.2f} ms"); return out

CASES = Path("fork-notes/synthetic/cases").resolve()
hfp = "HFP_ari+noa_condo_yonkers_2027_mortgage.xlsx"
diconf, dirname, _ = load_toml(f"{CASES}/Case_ari+noa_condo.toml")
diconf = apply_overrides(diconf, [f"household_financial_profile.HFP_file_name={hfp}"] + fixed_ages([70, 70]))
mk = lambda load: config_to_plan(copy.deepcopy(diconf), dirname, verbose=True, logstreams=[io.StringIO()], loadHFP=load)
plan = t("config_to_plan, loadHFP=True (work_sweep.make_plan's body)", lambda: mk(True), 3)
t("config_to_plan, loadHFP=False (builder._throwaway_plan's body)", lambda: mk(False), 3)
t("plan.readHFP(xlsx path)", lambda: plan.readHFP(f"{CASES}/{hfp}"), 3)
t("plan.readHFP(plan.rawHFP), as clone(expectancy=) does", lambda: plan.readHFP(plan.rawHFP, filename_for_logging="x", houseTables=False), 3)
plan = mk(True)
opts = parse_solver_options(resolve_options("quick", plan.solverOptions, {}))
t("plan.solve, Quick look", lambda: plan.solve(plan.objective, opts), 1)
c = t("clone(plan) (deepcopy path)", lambda: clone(plan, verbose=False), 3)
t("clone(plan, expectancy=[89, 89])", lambda: clone(plan, expectancy=[89, 89], verbose=False), 3)
import tracemalloc
tracemalloc.start(); keep = [clone(plan, expectancy=[89, 89], verbose=False) for _ in range(10)]
cur, _ = tracemalloc.get_traced_memory(); tracemalloc.stop()
print(f"{'memory held by 10 clone(plan, expectancy=...) (tracemalloc), MB each':62s} {cur/10/1e6:10.2f}")
del keep
t("copy.deepcopy(plan.A)", lambda: copy.deepcopy(plan.A))
t("plan.A.to_csr()", lambda: plan.A.to_csr())
x = np.zeros(plan.nvars)
t("amorepair.max_row_violation(x, A)", lambda: amorepair.max_row_violation(x, plan.A))
print(f"   model: {plan.A.ncons} rows, {plan.nvars} columns")
t("plan._ss_streams(ages)", lambda: plan._ss_streams(plan.ssecAges))
t("plan._earningsTestResult()", lambda: plan._earningsTestResult())
t("export.plan_metrics(plan)", lambda: export.plan_metrics(plan))
t("cli.formatters.plan_to_dict(plan) (plan.json)", lambda: formatters.plan_to_dict(plan))
t("thresholds: plan.json block", lambda: thresholds.threshold_proximity(plan))
t("brackets.bracket_view(plan)", lambda: brackets.bracket_view(plan))
t("plan.saveWorkbook() (plan_to_excel + save to bytes)", lambda: plan.saveWorkbook(saveToFile=False), 2)
t("plan.saveContributions()", lambda: plan.saveContributions(), 2)
t("results.code_stamp()", lambda: R.code_stamp(), 3)
t("results.environment()", lambda: R.environment(), 3)
t("sequences.load_sequences()", lambda: sequences.load_sequences())
t("_builtin_impl.load_historical_slice(1928, 2024)", lambda: bi.load_historical_slice(1928, 2024))
prog = star.program("NY")
print(f"   star: {len(prog['districts'])} districts in property_tax_relief.toml for NY; plan district {getattr(plan, 'school_district', None)!r}, N_n {plan.N_n}")

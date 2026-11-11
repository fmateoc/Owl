"""STAR district lookup: rows in the data file, and the time of star.star_schedule with the file as it is
and with the list padded to 730 rows (a statewide table), the plan's district placed last (the worst case)."""
import copy, io, time
from pathlib import Path
from owlplanner import star, plan as planmod
from owlplanner.config import config_to_plan, load_toml
from owlplanner.config.schema import parse_solver_options
from owlplanner.cli.set_override import apply_overrides
from owlplanner.library.presets import resolve_options
from owlplanner.library.agesearch import fixed_ages

calls = []
orig = star.star_schedule
def wrapped(*a, **k):
    t = time.perf_counter(); out = orig(*a, **k); calls.append(time.perf_counter() - t); return out
star.star_schedule = wrapped

CASES = Path("fork-notes/synthetic/cases").resolve()
diconf, dirname, _ = load_toml(f"{CASES}/Case_ari+noa_condo.toml")
diconf = apply_overrides(diconf, ["household_financial_profile.HFP_file_name=HFP_ari+noa_condo_yonkers_2027_mortgage.xlsx"]
                         + fixed_ages([70, 70]))

def solve(label):
    calls.clear()
    plan = config_to_plan(copy.deepcopy(diconf), dirname, verbose=True, logstreams=[io.StringIO()], loadHFP=True)
    t = time.perf_counter()
    plan.solve(plan.objective, parse_solver_options(resolve_options("quick", plan.solverOptions, {})))
    wall = time.perf_counter() - t
    rows = star.program("NY")["districts"]
    print(f"{label}: {len(rows)} district rows; Quick look {wall:.2f} s; star_schedule called {len(calls)} times, "
          f"{sum(calls)*1e3:.2f} ms in total ({100*sum(calls)/wall:.2f}% of the solve); district {plan.school_district!r}, N_n {plan.N_n}")

solve("data file as it is")
rows = star.program("NY")["districts"]
mine = [r for r in rows if star.district_key(r) == "City of Yonkers / Yonkers"]
rest = [r for r in rows if r not in mine]
pad = [dict(rest[i % len(rest)], school_district=f"{rest[i % len(rest)]['school_district']} #{i}") for i in range(730 - len(rows))]
rows[:] = rest + pad + mine
solve("padded to a statewide table")

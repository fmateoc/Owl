"""The Run page's results-workbook read, saveContributions, and code_stamp on a dirty tree, timed."""
from io import BytesIO
from pathlib import Path
import pandas as pd
from owlplanner.config import config_to_plan, load_toml
from owlplanner.config.schema import parse_solver_options
from owlplanner.cli.set_override import apply_overrides
from owlplanner.library.presets import resolve_options
from owlplanner.library.agesearch import fixed_ages
from owlplanner.library import results as R
CASES = Path("fork-notes/synthetic/cases").resolve()
diconf, dirname, _ = load_toml(f"{CASES}/Case_ari+noa_condo.toml")
diconf = apply_overrides(diconf, ["household_financial_profile.HFP_file_name=HFP_ari+noa_condo_yonkers_2027_mortgage.xlsx"] + fixed_ages([70, 70]))
plan = config_to_plan(diconf, dirname, verbose=True, logstreams=[io.StringIO()], loadHFP=True)
plan.solve(plan.objective, parse_solver_options(resolve_options("quick", plan.solverOptions, {})))
wb = plan.saveWorkbook(saveToFile=False)
buf = BytesIO(); wb.save(buf); data = buf.getvalue()
print(f"results workbook: {len(data)/1e3:.0f} kB, {len(wb.sheetnames)} sheets")
for _ in range(3):
    t = time.perf_counter(); sheets = pd.read_excel(BytesIO(data), sheet_name=None); print(f"pd.read_excel(sheet_name=None): {(time.perf_counter()-t)*1e3:.0f} ms")
for _ in range(2):
    t = time.perf_counter(); b = plan.saveContributions(); bb = BytesIO(); b.save(bb) if hasattr(b, "save") else None; print(f"saveContributions + save: {(time.perf_counter()-t)*1e3:.0f} ms")
t = time.perf_counter(); R.code_stamp(engine={"version": "x", "commit": "abc-dirty"}); print(f"code_stamp on a dirty tree (git diff HEAD): {(time.perf_counter()-t)*1e3:.0f} ms")

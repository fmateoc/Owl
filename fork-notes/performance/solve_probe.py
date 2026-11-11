"""One solve of a synthetic condo variant, timed, with every HiGHS call recorded.

    .venv/bin/python fork-notes/performance/solve_probe.py <preset> <HFP file name> <out.json> [options JSON]

Run `fork-notes/synthetic/make_cases.py` first. Knobs (environment): OWL_AGES (JSON, default [70, 70]),
OWL_QUIET=1 (the `quiet_patch.py` prototype), OWL_STEP_GAP (localsearch.STEP_GAP), OWL_DUMP=<folder>
(pickle every HiGHS call over 5 s, for `mip_probe.py`). The options JSON is laid over the preset's
options (`{"localSearchStepNodes": 1000}`). Performance review 2026-11-10 (`fork-notes/performance-review.md`).

Since 2026-11-11 the `decision` preset carries `presets.LOCAL_SEARCH_EFFORT` (1,000 nodes, both wall-clock
caps lifted). The review's "base" figures were measured before it; to repeat them pass upstream's defaults:
`{"localSearchStepNodes": 3000, "localSearchTime": 300, "localSearchStepTime": 60}`.
"""
import io
import json
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
from owlplanner import localsearch, plan as planmod
from owlplanner.config import config_to_plan, load_toml
from owlplanner.config.schema import parse_solver_options
from owlplanner.cli.set_override import apply_overrides
from owlplanner.library.presets import resolve_options
from owlplanner.library.agesearch import fixed_ages
preset, hfp, out = sys.argv[1], sys.argv[2], sys.argv[3]
extra = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
ages = json.loads(os.environ.get("OWL_AGES", "[70, 70]"))
if os.environ.get("OWL_QUIET"):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import quiet_patch  # noqa
if os.environ.get("OWL_STEP_GAP"):
    localsearch.STEP_GAP = float(os.environ["OWL_STEP_GAP"])
calls = []
dump = os.environ.get("OWL_DUMP")
orig = planmod.Plan._run_highs
def wrapped(self, c, Lb, Ub, lbvec, ubvec, a_start, a_index, a_value, integrality, options, warm_x=None):
    t = time.time()
    r = orig(self, c, Lb, Ub, lbvec, ubvec, a_start, a_index, a_value, integrality, options, warm_x=warm_x)
    dt = time.time() - t
    k = len(calls)
    calls.append({"k": k, "mip": bool(np.asarray(integrality).any()), "nint_free": int(((np.asarray(integrality) > 0) & (np.asarray(Ub) > np.asarray(Lb))).sum()),
                  "seconds": round(dt, 3), "nodes": getattr(self, "_lastMipNodes", None), "warm": warm_x is not None,
                  "gap": r[4], "obj": r[0]})
    if dump and dt > 5:
        pickle.dump({"c": c, "Lb": Lb, "Ub": Ub, "lbvec": lbvec, "ubvec": ubvec, "a_start": a_start, "a_index": a_index,
                     "a_value": a_value, "integrality": integrality, "warm_x": warm_x,
                     "options": {k2: v for k2, v in options.items() if isinstance(v, (int, float, str, bool))}},
                    open(f"{dump}/mip_{k:03d}.pkl", "wb"))
    return r
planmod.Plan._run_highs = wrapped
CASES = Path(__file__).resolve().parents[1] / "synthetic" / "cases"
diconf, dirname, _ = load_toml(f"{CASES}/Case_ari+noa_condo.toml")
diconf = apply_overrides(diconf, [f"household_financial_profile.HFP_file_name={hfp}"] + fixed_ages(ages))
log = io.StringIO()
plan = config_to_plan(diconf, dirname, verbose=True, logstreams=[log], loadHFP=True)
opts = resolve_options(preset, plan.solverOptions, extra)
t = time.time(); c = time.process_time()
plan.solve(plan.objective, parse_solver_options(opts))
wall = time.time() - t; cpu = time.process_time() - c
from owlplanner.export import plan_metrics
m = plan_metrics(plan)
json.dump({"preset": preset, "extra": extra, "env": {k: v for k, v in os.environ.items() if k.startswith("OWL_")},
  "status": plan.caseStatus, "wall": wall, "cpu": cpu, "basis": m.get("spending_basis"),
  "disc": m.get("discretionary_year1"), "nvars": plan.nvars, "calls": calls,
  "ls": plan.localSearchLog, "log": log.getvalue()}, open(out, "w"), indent=1, default=str)
print(preset, extra, dict((k, v) for k, v in os.environ.items() if k.startswith("OWL_")), plan.caseStatus, "wall", round(wall, 1), "cpu", round(cpu, 1), m.get("spending_basis"), m.get("discretionary_year1"), flush=True)

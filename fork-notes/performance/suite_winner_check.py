"""run_suite.py's baseline row solved by two versions of the suite, one after the other, the
same day: BASE (a run_suite.py that builds and solves the plan again at the chosen ages) and
NEW (the edited suite, which publishes the winning stage-2 candidate's own plan).

    .venv/bin/python fork-notes/performance/suite_winner_check.py BASE_RUN_SUITE.py OUT_DIR

BASE_RUN_SUITE.py: `git show <commit>:fork-notes/synthetic/run_suite.py > file`. Both import
the same owlplanner (this checkout's src). Prints each version's time, the record keys that
differ (timing and the new `stage_2_plan` key aside), and whether the synopses (.txt) match.
"""

import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYN = ROOT / "fork-notes" / "synthetic"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    base_file, out = Path(sys.argv[1]), Path(sys.argv[2])
    case, condo = SYN / "cases" / "Case_ari+noa.toml", SYN / "cases" / "Case_ari+noa_condo.toml"
    scen = json.loads((SYN / "cases" / "condo_grid.json").read_text(encoding="utf-8"))
    recs = {}
    for label, path in (("base", base_file), ("new", SYN / "run_suite.py")):
        mod = load(path, f"run_suite_{label}")
        d = out / label
        d.mkdir(parents=True, exist_ok=True)
        jobs, _ = mod.build(mod.scenario_groups(case, condo, scen)[:1], None, str(d))
        t0 = time.time()
        rec = mod.solve_one(jobs[0], str(d))
        print(f"{label}: {rec['status']} in {time.time() - t0:.1f} s, ages {rec.get('ages')}, "
              f"candidates {rec.get('age_candidates')}", flush=True)
        recs[label] = rec
    skip = {"seconds", "stage_2_plan"}
    a, b = recs["base"], recs["new"]
    diff = sorted(k for k in set(a) | set(b) if k not in skip and a.get(k) != b.get(k))
    print("record keys that differ:", diff or "none")
    for k in diff:
        if isinstance(a.get(k), dict) and isinstance(b.get(k), dict):
            sub = sorted(j for j in set(a[k]) | set(b[k]) if a[k].get(j) != b[k].get(j))
            print(f"  {k}: {[(j, a[k].get(j), b[k].get(j)) for j in sub]}")
        else:
            print(f"  {k}: base {a.get(k)!r} / new {b.get(k)!r}")
    stem = f"{a['group']}_{a['name']}"
    ta = (out / "base" / f"{stem}.txt").read_text(encoding="utf-8")
    tb = (out / "new" / f"{stem}.txt").read_text(encoding="utf-8")
    print("synopsis (.txt) identical:", ta == tb)
    print("new stage_2_plan:", b.get("stage_2_plan"))


if __name__ == "__main__":
    main()

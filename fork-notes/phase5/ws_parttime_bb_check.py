"""Branch-and-bound scores (work_sweep's decider, gap 1e-5) of pat-part-time-2029-30 at ages today's sweep did not score."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
H = "/home/user/Owl"
sys.path.insert(0, f"{H}/fork-notes/phase5")
import work_sweep as ws
cfg = {"decider": "bb", "gap": 1e-5, "max_time": ws.TIME_LIMIT, "ls_time": 7200.0, "ls_step": 1800.0}
AGES = [[68 + 5 / 12, 65.0], [68 + 5 / 12, 64 + 7 / 12], [68.25, 64 + 7 / 12]]
if __name__ == "__main__":
    spec = json.load(open(f"{H}/fork-notes/phase5/work_sweep_chris+pat.json"))
    by = {v[0]: v for v in ws.build_variants(f"{H}/examples/Case_chris+pat.toml", spec, "otherFiles/sweep-parttime-check")}
    _, diconf, dirname, _ = by["pat-part-time-2029-30"]
    with ProcessPoolExecutor(3, mp_context=mp.get_context("spawn")) as pool:
        for ages, c in zip(AGES, pool.map(ws.score, [(diconf, dirname, a, cfg) for a in AGES]), strict=True):
            print("/".join(ws.ym(a) for a in ages), c.get("status"), f"{c.get('value', float('nan')):,.2f}",
                  f"gap {c.get('gap', float('nan')):.2e}", c.get("used"), f"{c.get('seconds', 0):.0f}s", flush=True)

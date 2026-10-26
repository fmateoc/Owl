"""
Does relTol reach the sticky tie? Two plans of `reltol_probe.py` at relTol 1e-5 and 1e-7 (2026-10-26).

At 1e-7 the sticky keep should be refused and the reported gap fall to HiGHS's own.

Run from the repository root (plans start today): .venv/bin/python fork-notes/phase5/reltol_check.py OUT_DIR
"""

import json
import multiprocessing as mp
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))

import reltol_probe as rp  # noqa: E402
import work_sweep as ws  # noqa: E402

PLANS = [("pat-stops-2027", (68 * 12 + 3, 62 * 12 + 1)), ("base", (67 * 12, 63 * 12))]


def main():
    with open(rp.SPEC, encoding="utf-8") as f:
        spec = json.load(f)
    by = {v[0]: v for v in ws.build_variants(rp.CASE, spec, sys.argv[1])}
    jobs = [(by[n][1], by[n][2], ages, 1e-5, rel) for n, ages in PLANS for rel in (1e-5, 1e-7)]
    with ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context("spawn")) as pool:
        res = list(pool.map(rp.solve, jobs))
    for job, r in zip(jobs, res, strict=True):
        ages, rel = job[2], job[4]
        print(f"{'/'.join(ws.ym(m / 12) for m in ages)} relTol {rel:.0e}: sticky_tol {r['sticky_tol']:.0e} "
              f"value {r['value']:,.2f} gap {r['gap']:.3e} stick {r['sticky_keeps']} iter {r['iterations']} "
              f"conv {r['convergence']} MIP gap {r['max_mip_gap']:.2e} resid {r['residual']:.0f} {r['seconds']:.0f}s")


if __name__ == "__main__":
    main()

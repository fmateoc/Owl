"""Candidate claim 2.1: closed form for _stochastic_lp. Check its formula, and a corrected one."""
import time
import numpy as np
from owlplanner.stresstests import _stochastic_lp, _compute_efficient_frontier

def candidate(bases, lam):
    b = np.sort(np.asarray(bases, float)); S = len(b)
    if lam <= 1:
        g = max(0.0, b[S - 1])
    else:
        g = max(0.0, b[min(int(np.floor(S * (1 - 1 / lam))), S - 1)])
    z = np.maximum(0.0, g - b)
    return g, z.mean(), (z > 0).mean()

def corrected(bases, lam):
    # slope of the objective on (b_(m-1), b_(m)) is 1 - lam*m/S: rise while m < S/lam
    b = np.sort(np.asarray(bases, float)); S = len(b)
    if lam <= 1:
        m = S - 1
    else:
        m = min(int(np.ceil(S / lam)) - 1, S - 1)
    g = max(0.0, b[m])
    z = np.maximum(0.0, g - b)
    return g, z.mean(), (z > 0).mean()

rng = np.random.default_rng(1)
for S in (7, 100, 1000):
    bases = rng.normal(100_000, 15_000, S)
    lambdas = np.concatenate([[0.0], np.logspace(-1, 3, 60)])
    bad_c = bad_k = 0; worst_c = worst_k = 0.0; obj_gap = 0.0
    for lam in lambdas:
        g, sf, pr = _stochastic_lp(bases, lam)
        gc, _, _ = candidate(bases, lam); gk, sfk, prk = corrected(bases, lam)
        bad_c += abs(gc - g) > 1e-6; worst_c = max(worst_c, abs(gc - g))
        bad_k += abs(gk - g) > 1e-6; worst_k = max(worst_k, abs(gk - g))
        obj_gap = max(obj_gap, abs((g - lam * sf) - (gk - lam * sfk)))
    print(f"S={S}: candidate formula differs at {bad_c}/61 lambdas (max |dg| {worst_c:,.2f}); "
          f"corrected differs at {bad_k}/61 (max |dg| {worst_k:,.2f}, max objective gap {obj_gap:.2e})")
    print("   lam=1000: LP g =", round(_stochastic_lp(bases, 1000.0)[0], 2), " min =", round(bases.min(), 2),
          " max =", round(bases.max(), 2), " candidate g =", round(candidate(bases, 1000.0)[0], 2))

for S in (100, 500, 1000):
    bases = rng.normal(100_000, 15_000, S)
    t = time.perf_counter(); _compute_efficient_frontier(bases); dt = time.perf_counter() - t
    t = time.perf_counter(); [corrected(bases, lam) for lam in np.concatenate([[0.0], np.logspace(-1, 3, 60)])]
    dk = time.perf_counter() - t
    print(f"S={S}: _compute_efficient_frontier (61 LPs) {dt:.2f} s; closed form {dk*1e3:.2f} ms")

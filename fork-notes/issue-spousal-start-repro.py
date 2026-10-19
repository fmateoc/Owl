"""Repro for fork-notes/issue-spousal-start.md: run on stock upstream dev."""

import numpy as np

from owlplanner import socialsecurity as ss


def run(pias, ages, yobs, mobs):
    zeta, _ = ss.compute_social_security_benefits(
        np.array(pias), np.array(ages, dtype=float), np.array(yobs), np.array(mobs),
        np.array([15, 15]), np.array([25, 25]), 2, 25, thisyear=2026,
    )
    return zeta


# 1. Both spouses collecting before the plan; person 1 gets a spousal add-on (0.5 x 3000 - 800).
z = run([3000, 800], [62.0, 62.0], [1961, 1962], [1, 5])
own, sp = 800 * (0.8 - 0.05 * 23 / 12), 700 * (0.75 - 0.05 * 23 / 12)
print(f"1. person 1, 2026: {z[1, 0]:,.2f}   expected 12 x (own {own:.2f} + spousal {sp:.2f}) = {12 * (own + sp):,.2f}")

# 2. Same couple listed in both orders; the later claimer enters 62.0 (reset to 62y1m).
a = run([1000, 3000], [62 + 1 / 12, 62.0], [1964, 1966], [3, 5])[0, 2]
b = run([3000, 1000], [62.0, 62 + 1 / 12], [1966, 1964], [5, 3])[1, 2]
expected = 8450 + 500 * (1 - 2.75 / 12) * 6
print(f"2. auxiliary, 2028: listed first {a:,.2f}, listed second {b:,.2f}   expected {expected:,.2f}")

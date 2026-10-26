import numpy as np
from owlplanner import socialsecurity as ss

N = 8
def run(earn0, months0):
    e = np.zeros((1, N)); m = np.zeros((1, N)); e[0, 0] = earn0; m[0, 0] = months0
    return ss.earnings_test([2000], [62 + 1 / 12], [1963], [6], [15], [N], 1, N, e, work_months_in=m, thisyear=2026)

r = run(80_000, 6)
print("case 1 (works Jan-Jun 2026 for 80,000): paid by payment year", {2026 + n: round(r.zeta_in[0, n], 2) for n in range(3)},
      "ARF months", int(r.arf_months[0]), "excess 2026", int(r.excess_by_year[0, 0]))
r = run(0, 0)
print("cases 2-3 (no plan-year work): paid", {2026 + n: round(r.zeta_in[0, n], 2) for n in (0, 4, 5)}, "ARF months", int(r.arf_months[0]))
f = ss.getFRAs(np.array([1963]), np.array([6]), np.array([15]))[0]
print("monthly at 62y1m:", round(2000 * ss.getSelfFactor(f, 62 + 1 / 12, False), 2),
      " with 6 crediting months from FRA:", round(2000 * ss.arf_self_factor(f, 62 + 1 / 12, 6, False), 2),
      " 12:", round(2000 * ss.arf_self_factor(f, 62 + 1 / 12, 12, False), 2),
      " 24:", round(2000 * ss.arf_self_factor(f, 62 + 1 / 12, 24, False), 2))

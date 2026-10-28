"""#235 after upstream's fix (92afe10, merged 2026-10-28): the earnings test with the five years before the
plan. Same person as check235.py (PIA 2,000, born 1963-06-15, claims at 62y1m = July 2025, plan from 2026).
Past years are 2021-2025, oldest first. Run from the repository root."""
import numpy as np
from owlplanner import socialsecurity as ss

N = 8


def run(earn0, months0, past_2025=None, past_months_2025=0):
    e = np.zeros((1, N)); m = np.zeros((1, N)); e[0, 0] = earn0; m[0, 0] = months0
    kw = {}
    if past_2025 is not None:
        pe = np.zeros((1, 5)); pm = np.zeros((1, 5)); pe[0, 4] = past_2025; pm[0, 4] = past_months_2025
        kw = {"past_earnings_in": pe, "past_work_months_in": pm}
    return ss.earnings_test([2000], [62 + 1 / 12], [1963], [6], [15], [N], 1, N, e, work_months_in=m,
                            thisyear=2026, **kw)


def show(label, r):
    print(f"{label}: paid {{2026: {r.zeta_in[0, 0]:,.2f}, 2027: {r.zeta_in[0, 1]:,.2f}, 2028: {r.zeta_in[0, 2]:,.2f}, "
          f"2030: {r.zeta_in[0, 4]:,.2f}, 2031: {r.zeta_in[0, 5]:,.2f}}}, ARF months {int(r.arf_months[0])}")


show("case 1, no past earnings (as before the fix)", run(80_000, 6))
show("case 1, worked all of 2025 for 80,000", run(80_000, 6, 80_000, 12))
show("case 2, no plan-year work, no past earnings", run(0, 0))
show("case 2, worked all of 2025 for 80,000 (Jul-Dec 2025 withheld)", run(0, 0, 80_000, 12))
f = ss.getFRAs(np.array([1963]), np.array([6]), np.array([15]))[0]
print("monthly with 6 crediting months from FRA:", round(2000 * ss.arf_self_factor(f, 62 + 1 / 12, 6, False), 2),
      "x 12 =", round(12 * 2000 * ss.arf_self_factor(f, 62 + 1 / 12, 6, False), 2))

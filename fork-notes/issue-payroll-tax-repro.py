"""Stock-dev repro for the payroll-tax issue (fork-notes/issue-payroll-tax.md).

Owl counts `anticipated wages` (the wages in AGI since #221) as cash, and charges no payroll tax
on them. The employee's FICA is a cash outflow that no income tax computation deducts, which is
exactly how Owl treats a negative big-ticket item. So this script measures what the missing tax
is worth on stock Owl, with no code change: each example with wages is solved as shipped, then
again with each person's FICA entered as a negative big-ticket item in each year.

FICA by hand (IRS Pub. 15 (2026): 6.2% up to the \\$184,500 wage base, 1.45% on all; Form 8959:
0.9% on the household's Medicare wages above \\$250,000 MFJ / \\$200,000 single, not indexed),
on the earnings Owl's earnings test already derives: wages plus that year's tax-deferred
contributions (Plan._earnings_test_inputs; W-2 boxes 3 and 5). The wage base is held at its
2026 level in today's dollars (it follows the wage index by statute).

Run from a checkout of stock `dev`, inside pytest so tests/conftest.py freezes the date:
    cp fork-notes/issue-payroll-tax-repro.py <stock>/tests/test_zz_payroll_repro.py
    cd <stock> && PYTHONPATH=src python -m pytest tests/test_zz_payroll_repro.py -s -q -p no:cacheprovider
"""
import io
import os

import numpy as np

import owlplanner as owl

CASES = ("alex+jamie", "chris+pat", "jack+jill", "joe", "john+sally", "jon+jane")
BASE_2026 = 184_500.0


def _fica(p):
    earnings = np.where(p.omega_in > 0, p.omega_in + p.kappa_ijn[:, 1, : p.N_n], 0.0)
    ss = 0.062 * np.minimum(earnings, BASE_2026 * p.gamma_n[: p.N_n])
    med = 0.0145 * earnings
    thr = np.where(np.arange(p.N_n) < p.n_d, 250_000.0 if p.N_i == 2 else 200_000.0, 200_000.0)
    addl = 0.009 * np.maximum(0.0, np.sum(earnings, axis=0) - thr)
    per_person = ss + med
    if p.N_i == 2:  # Additional Medicare Tax split by share of earnings, for the big-ticket entry
        share = np.divide(earnings, np.sum(earnings, axis=0), out=np.zeros_like(earnings), where=earnings > 0)
        per_person = per_person + share * addl
    else:
        per_person = per_person + addl
    return earnings, per_person


def _solve(case, fica=False):
    root = os.path.join(os.path.dirname(owl.__file__), "..", "..", "examples")
    p = owl.readConfig(os.path.join(root, f"Case_{case}.toml"), verbose=False, logstreams=[io.StringIO()])
    earnings, tax = _fica(p)
    if fica:
        p.Lambda_in[:, : p.N_n] -= tax
    p.solve(p.objective, dict(p.solverOptions or {}))
    assert p.caseStatus == "solved", (case, p.caseStatus)
    return p, earnings, tax


def test_repro():
    print("\nowlplanner from", owl.__file__)
    print(f"{'case':12} {'objective':11} {'wage years':10} {'earnings':>10} {'FICA':>8} "
          f"{'as shipped':>12} {'with FICA':>12} {'difference':>11}")
    for case in CASES:
        p, earnings, tax = _solve(case)
        q, _, _ = _solve(case, fica=True)
        key = "basis" if p.objective == "maxSpending" else "bequest"
        a, b = getattr(p, key), getattr(q, key)
        yrs = [int(p.year_n[n]) for n in range(p.N_n) if earnings[:, n].sum() > 0]
        span = f"{yrs[0]}-{yrs[-1]}" if len(yrs) > 1 else str(yrs[0])
        print(f"{case:12} {p.objective:11} {span:10} {earnings.sum():>10,.0f} {tax.sum():>8,.0f} "
              f"{a:>12,.0f} {b:>12,.0f} {b - a:>+11,.0f} ({100 * (b - a) / a:+.2f}%)")

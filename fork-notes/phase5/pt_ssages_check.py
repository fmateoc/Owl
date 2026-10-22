"""Phase 5 step 5: withSSAges with the payroll tax on (chris+pat, Pat searched).

The tax does not depend on claiming ages, but it is not a constant shift of the objective:
it takes cash the plan would otherwise keep, so withdrawals, taxes and SS taxability move,
and the pick can move (it did, by one month, in the first run). Checked: the plan returned
carries the tax and equals a fixed-age solve at its pick; and how much the pick made with
the tax off costs with the tax on (both ages solved fixed, tax on).
Run with the date frozen at 2026-01-01, as the tests are.
"""

import io
import os
import sys
from datetime import date
from unittest import mock

import numpy as np

import owlplanner as owl

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")


class _FrozenDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 1, 1)


def load():
    p = owl.readConfig(os.path.join(EX, "Case_chris+pat.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, "HFP_chris+pat.xlsx"))
    return p


def run(on, ssages):
    p = load()
    opts = dict(p.solverOptions or {}, withEarningsTest=True)
    if on:
        opts["withPayrollTax"] = True
    if ssages:
        opts["withSSAges"] = ["Pat"]
    p.solve(p.objective, opts)
    return p


def main():
    print("owlplanner from", owl.__file__)
    res = {}
    for on in (False, True):
        p = run(on, True)
        res[on] = p
        print(f"payroll {'on ' if on else 'off'}: Pat {p.ssecAges[1]:.4f}, basis {p.basis:,.2f}, "
              f"payroll total {np.sum(p.payroll_tax_n):,.2f}")
    q = load()
    q.setSocialSecurity(q.ssecAmounts, res[True].ssecAges)
    opts = dict(q.solverOptions or {}, withEarningsTest=True, withPayrollTax=True)
    q.solve(q.objective, opts)
    print(f"fixed at the pick, payroll on: basis {q.basis:,.2f}")
    r = load()
    r.setSocialSecurity(r.ssecAmounts, res[False].ssecAges)
    r.solve(r.objective, opts)
    print(f"fixed at the payroll-off pick, payroll on: basis {r.basis:,.2f} "
          f"(cost of that pick with the tax on: {q.basis - r.basis:,.2f}/yr)")


if __name__ == "__main__":
    # As tests/conftest.py: every loaded module holding the real date class.
    mods = [m for m in list(sys.modules.values()) if m is not None and getattr(m, "date", None) is date]
    patches = [mock.patch.object(m, "date", _FrozenDate) for m in mods]
    for pt in patches:
        pt.start()
    try:
        main()
    finally:
        for pt in patches:
            pt.stop()
    sys.stdout.flush()

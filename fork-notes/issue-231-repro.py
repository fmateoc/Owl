"""
Repro for the comment on upstream #231: what a plan withholds (earnings test) and charges
(payroll tax) for work in calendar 2027 depends on the year the plan starts. Run on stock
`dev` (from a checkout: PYTHONPATH=src python issue-231-repro.py).

Both are functions of 2027's nominal earnings and 2027's nominal SSA amounts, so a plan
starting in 2026 and one starting in 2027 should agree in nominal dollars. Withholding is
compared on $40,000, where it is the excess itself (below the year's benefit, so the PIA,
entered in each plan's own today's dollars, does not enter); the payroll tax on $250,000,
above the wage base. 0% inflation checks the harness: there the two dollar bases coincide.
"""

import datetime
import io
import pathlib
import sys

import numpy as np

import owlplanner as owl
from owlplanner import socialsecurity as ss
from owlplanner import tax_federal as tx

print("owlplanner from", pathlib.Path(owl.__file__).resolve().relative_to(pathlib.Path.cwd().resolve()))


def start_in(year):
    """Every owlplanner module sees January 1 of `year` as today (as tests/conftest.py does)."""

    class Day(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(year, 1, 1)

    for name, mod in list(sys.modules.items()):
        if name.startswith("owlplanner") and mod is not None:
            d = getattr(mod, "date", None)
            if isinstance(d, type) and issubclass(d, datetime.date):
                mod.date = Day


def for_2027(start, inflation, wages_2027):
    """Nominal earnings-test withholding and payroll tax for work in calendar 2027."""
    start_in(start)
    p = owl.Plan(["W"], ["1963-08-15"], [89], "r231", verbose=False, logstreams=[io.StringIO()])
    p.setSocialSecurity([2000], [62 + 1 / 12])  # entitled Sep 2025, before either plan
    n = 2027 - start
    p.omega_in[0, n] = wages_2027
    gamma = (1 + inflation) ** np.arange(p.N_n + 1)
    res = p._earningsTestResult(gamma_n=gamma)
    withheld = float(np.sum(res.withheld_in[0] * gamma[: p.N_n]))  # only 2027 has earnings
    payroll = float(tx.payrollTax(p.N_i, p._earnings_test_inputs()[0], gamma, p.n_d, p.N_n)[n])
    return withheld, payroll


print("\nEarnings test, $40,000 of 2027 wages: nominal amount withheld")
shipped = dict(ss._EXEMPT_TABLE)
for label, extra in (("shipped table (2024-2026)", {}), ("2027 added as (25,560, 67,920)", {2027: (25_560.0, 67_920.0)})):
    ss._EXEMPT_TABLE.clear()
    ss._EXEMPT_TABLE.update(shipped | extra)
    for infl in (0.0, 0.025):
        a, b = for_2027(2026, infl, 40_000)[0], for_2027(2027, infl, 40_000)[0]
        print(f"  {label:32s} inflation {infl:4.1%}: plan from 2026 {a:9,.2f}  plan from 2027 {b:9,.2f}  diff {a - b:8,.2f}")
ss._EXEMPT_TABLE.clear()
ss._EXEMPT_TABLE.update(shipped)

print(f"\nPayroll tax, $250,000 of 2027 wages (payrollWageBase = {tx.payrollWageBase:,.0f})")
for infl in (0.0, 0.025):
    a, b = for_2027(2026, infl, 250_000)[1], for_2027(2027, infl, 250_000)[1]
    print(f"  inflation {infl:4.1%}: plan from 2026 {a:10,.2f}  plan from 2027 {b:10,.2f}  diff {a - b:8,.2f}")

"""
Phase 5 step 4 probe: the SSA earnings test under `withSSAges` (plan §5 step 4).

Run from the repository root (the date is today's, not the test suite's frozen one):

    .venv/bin/python fork-notes/phase5/et_step4_probe.py

Since upstream #195 the claiming-age search solves the plan at fixed ages for every open
month and keeps the best, so the test reaches every candidate through step 3's fixed-age
path (tests/ss/test_earnings_test_ssages.py guards that). What the plan asks step 4 to
record, as there is no expected value before the run:

1. One age searched: jack+jill with Jill's age searched, test off / on, Jill's
   `months worked` in 2028 = 12 (the workbook) / 6; chris+pat with Pat's; alex+jamie with
   Alex's (Jamie, already collecting, keeps her age; her test years meet Alex's claim
   through her spousal add-on).
2. Both ages free (`withSSAges="optimize"`) on jack+jill and chris+pat, test off / on:
   the picks, the number of rounds of the alternating search (cap 5) and of solves, to
   see whether the test makes the search cycle (plan §7, "Both ages free").
3. Where a pick moves with the test: the no-test pick solved at fixed ages with the test on,
   i.e. what following the advice of Owl without the test is worth once SSA applies it,
   against the pick made with the test on (the test's value as a decision, today's $).

For each run: the ages picked, the objective (`basis` under maxSpending, the bequest under
maxBequest, today's $), the amounts withheld (nominal), the ARF months, the number of
fixed-age solves and the wall time.

Output: `et_step4_probe_YYYY-MM-DD.txt` beside this script.
"""

import io
import os
import sys
import time
from datetime import date

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import owlplanner as owl  # noqa: E402
from owlplanner.mylogging import Logger  # noqa: E402
from owlplanner.plan import Plan  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")


def load(case):
    p = owl.readConfig(os.path.join(EX, f"Case_{case}.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, f"HFP_{case}.xlsx"))
    return p


def ym(age):
    m = int(round(age * 12))
    return f"{m // 12}y{m % 12}m"


def run(case, ssages, test_on, months_2028=None, who=None):
    """Solve `case` with `withSSAges=ssages`; count rounds through `_ssaOpenAges` calls."""
    p = load(case)
    if months_2028 is not None:
        p.etMonths_in[who, 2028 - int(p.year_n[0])] = float(months_2028)
    calls = []
    open_ages = Plan._ssaOpenAges

    def _open(self, i):
        calls.append(i)
        return open_ages(self, i)

    opts = dict(p.solverOptions or {}, withSSAges=ssages, withEarningsTest=bool(test_on))
    buf = io.StringIO()
    p.mylog = Logger(verbose=True, logstreams=[buf])
    Plan._ssaOpenAges = _open
    t0 = time.time()
    try:
        p.solve(p.objective, opts)
    finally:
        Plan._ssaOpenAges = open_ages
    elapsed = time.time() - t0
    assert p.caseStatus == "solved", (case, ssages, test_on)
    free = len(set(calls)) or 1
    rounds = len(calls) // free
    solves = [line for line in buf.getvalue().splitlines() if "fixed-age solve(s)" in line]
    nsolves = solves[-1].split("best of ")[1].split(" ")[0] if solves else "?"
    value = float(p.basis) if p.objective == "maxSpending" else float(p.bequest)
    return {
        "ages": " / ".join(f"{n} {ym(a)}" for n, a in zip(p.inames, p.ssecAges, strict=True)),
        "value": value,
        "withheld": float(np.sum(p.ss_withheld_in)),
        "arf": " / ".join(
            f"{int(a)}+{int(s)}" for a, s in zip(p.ss_arf_months_i, p.ss_arf_months_spousal_i, strict=True)
        ),
        "rounds": rounds,
        "solves": nsolves,
        "time": elapsed,
        "objective": p.objective,
        "ssecAges": [float(a) for a in p.ssecAges],
    }


def fixed(case, ages, test_on):
    """A fixed-age solve of `case` at `ages`: (objective, amount withheld)."""
    p = load(case)
    p.setSocialSecurity(list(p.ssecAmounts), list(ages))
    p.solve(p.objective, dict(p.solverOptions or {}, withEarningsTest=bool(test_on)))
    assert p.caseStatus == "solved", (case, ages, test_on)
    value = float(p.basis) if p.objective == "maxSpending" else float(p.bequest)
    return value, float(np.sum(p.ss_withheld_in))


def show(label, r):
    unit = "basis" if r["objective"] == "maxSpending" else "bequest"
    print(
        f"  {label:<34} {r['ages']:<26} {unit} {r['value']:>12,.2f}  withheld {r['withheld']:>10,.2f}"
        f"  ARF own+sp {r['arf']:<9} rounds {r['rounds']}  solves {r['solves']:>4}  {r['time']:6.1f}s"
    )


def pair(case, ssages, results):
    """The search with the test off and on; both kept for section 3."""
    off = run(case, ssages, False)
    on = run(case, ssages, True)
    show("test off", off)
    show("test on", on)
    results.append((case, ssages, off, on))


def main():
    print(f"et_step4_probe.py, {date.today().isoformat()}")
    results = []
    print()
    print("== 1. One age searched")
    print("jack+jill, withSSAges=['Jill'] (case: Jill 62y1m, $85k in 2028, her last work year)")
    pair("jack+jill", ["Jill"], results)
    show("test on, months worked 2028 = 6", run("jack+jill", ["Jill"], True, months_2028=6, who=1))
    print("chris+pat, withSSAges=['Pat'] (case: Pat 62y1m, $85k in 2028)")
    pair("chris+pat", ["Pat"], results)
    print("alex+jamie, withSSAges=['Alex'] (Jamie collecting, $80k in 2026-2027)")
    pair("alex+jamie", ["Alex"], results)
    print()
    print("== 2. Both ages free (withSSAges='optimize'; alternating search, cap 5 rounds)")
    for case in ("jack+jill", "chris+pat"):
        print(case)
        pair(case, "optimize", results)
    print()
    print("== 3. Picks that move with the test: the no-test pick, solved at fixed ages with the test on")
    for case, ssages, off, on in results:
        if off["ssecAges"] == on["ssecAges"]:
            continue
        value, withheld = fixed(case, off["ssecAges"], True)
        unit = "basis" if on["objective"] == "maxSpending" else "bequest"
        print(f"{case}, withSSAges={ssages}")
        print(f"  no-test pick {off['ages']:<26} with the test: {unit} {value:>12,.2f}  withheld {withheld:>10,.2f}")
        print(f"  test-on pick {on['ages']:<26} with the test: {unit} {on['value']:>12,.2f}")
        print(f"  cost of following the no-test pick: {on['value'] - value:,.2f} {unit} (today's $)")


if __name__ == "__main__":
    main()

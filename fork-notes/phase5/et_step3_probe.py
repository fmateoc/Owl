"""
Phase 5 step 3 probe: what the SSA earnings test changes where it bites (plan §5 step 3).

Run from the repository root (the date is today's, not the test suite's frozen one):

    .venv/bin/python fork-notes/phase5/et_step3_probe.py

Two things are measured and printed:

1. The three examples of plan §3 with `solver_options.withEarningsTest` on and off
   (jack+jill and chris+pat in 2028, alex+jamie in 2026-2027): the objective, the amounts
   withheld (nominal), the ARF crediting months, and the taxable Social Security of 2028.
2. The step's warning contract: one earnings-test warning per solve, also under
   `withSSAges` (chris+pat with Pat's age searched: ~40 candidate solves, one warning),
   and none with the switch off.

Output: `et_step3_probe_YYYY-MM-DD.txt` beside this script.
"""

import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import owlplanner as owl  # noqa: E402
from owlplanner.mylogging import Logger  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "..", "examples")


def load(case):
    p = owl.readConfig(os.path.join(EX, f"Case_{case}.toml"), verbose=False, logstreams=[io.StringIO()])
    p.readHFP(os.path.join(EX, f"HFP_{case}.xlsx"))
    return p


def solve(p, test_on, extra=None):
    opts = dict(p.solverOptions or {})
    opts["withEarningsTest"] = bool(test_on)
    if extra:
        opts.update(extra)
    p.solverOptions = opts
    buf = io.StringIO()
    p.mylog = Logger(verbose=True, logstreams=[buf])
    p.resolve()
    assert p.caseStatus == "solved"
    return p, buf.getvalue()


def warn_lines(text):
    return [line.split(" | ", 3)[-1] for line in text.splitlines() if "| WARNING |" in line]


def stakes():
    """The three examples of plan §3, switch off vs on (today's date)."""
    print("== What the test changes on the three examples of plan §3")
    for case in ("jack+jill", "chris+pat", "alex+jamie"):
        off, _ = solve(load(case), False)
        on, _ = solve(load(case), True)
        print(f"\n{case}: basis {off.basis:12.2f} -> {on.basis:12.2f}"
              f"   bequest {off.bequest:12.2f} -> {on.bequest:12.2f}")
        for i, name in enumerate(on.inames):
            wh = float(on.ss_withheld_in[i].sum())
            if wh > 0 or on.ss_arf_months_i[i] or on.ss_arf_months_spousal_i[i]:
                print(f"   {name}: withheld {wh:10.2f} nominal, ARF "
                      f"{int(on.ss_arf_months_i[i])} own / {int(on.ss_arf_months_spousal_i[i])} spouse")
        n28 = 2028 - int(on.year_n[0])
        t_off = float(off.Psi_n[n28] * np.sum(off.zetaBar_in[:, n28]))
        t_on = float(on.Psi_n[n28] * np.sum(on.zetaBar_in[:, n28]))
        print(f"   taxable Social Security 2028: {t_off:.2f} -> {t_on:.2f}")


def warnings():
    """Once per solve, only with the switch on (plan §4.4)."""
    print("\n== Warnings")
    for case in ("chris+pat", "alex+jamie"):
        p, text = solve(load(case), False)
        et = [w for w in warn_lines(text) if "gross earnings" in w or "withheld" in w]
        print(f"{case}, switch off: {len(et)} earnings-test warning(s)")
        p, text = solve(load(case), True)
        et = [w for w in warn_lines(text) if "gross earnings" in w or "withheld" in w]
        print(f"{case}, switch on:  {len(et)} earnings-test warning(s)")
        for w in et:
            print(f"   {w}")
    p, text = solve(load("chris+pat"), True, {"withSSAges": ["Pat"]})
    et = [w for w in warn_lines(text) if "gross earnings" in w or "withheld" in w]
    print(f"chris+pat, switch on, withSSAges=['Pat'] (every candidate a solve): {len(et)} warning(s)")
    for w in et:
        print(f"   {w}")


if __name__ == "__main__":
    import contextlib
    import datetime

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        stakes()
        warnings()
    text = buf.getvalue()
    out = os.path.join(os.path.dirname(__file__), f"et_step3_probe_{datetime.date.today()}.txt")
    with open(out, "w", encoding="utf-8") as f:  # UTF-8: a PowerShell redirect writes UTF-16
        f.write(f"et_step3_probe.py, {datetime.date.today()}\n\n")
        f.write(text)
    print(text, end="")
    print(f"(saved to {os.path.basename(out)})")

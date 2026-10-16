"""Is the LP at a fixed Psi degenerate? (2026-10-16)

Rebuilds the LP of iteration IT of a trace written by trace.py (its SC parameters restored at the
loop's reset, maxIter 1), solves it, then solves it again with Joe's tax-deferred withdrawal in
YEAR pinned to the value it had at iteration ALT, and prints the objective change and the
withdrawals that moved. Same couple and options as trace.py's NY case.

Usage: tie.py TAG IT ALT YEAR   (e.g. tie.py ny 29 26 2036)
"""
import io
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
sys.argv = ["x", "/dev/null"]
sys.path.insert(0, os.path.join(HERE, "..", "phase3-review"))
import itemized_convergence as ic  # noqa: E402
import numpy as np  # noqa: E402

tag, IT, ALT, YEAR = argv[0], int(argv[1]), int(argv[2]), int(argv[3])
d = pickle.load(open(os.path.join(HERE, "out", f"{tag}.pkl"), "rb"))
rec, yr, g = d["rec"], d["year"], d["gamma"]
n = list(yr).index(YEAR)
TD_JOE = 1  # row of w: person 0, account 1 (tax-deferred)


def solve_lp(it, pin=None):
    snap = rec[it]["sc"]
    p = ic.couple("NY", "Yonkers", 600000.0, 2032, io.StringIO())
    cls = type(p)
    orig_nl, orig_bc, orig_app = cls._computeNLstuff, cls._buildConstraints, cls._sc_trace_append
    out = {}

    def nl(self, x, includeMedicare, fixedPsi=None):
        orig_nl(self, x, includeMedicare, fixedPsi)
        if x is None:
            for k, v in snap.items():
                setattr(self, k, np.array(v).copy())

    def bc(self, objective, options):
        orig_bc(self, objective, options)
        if pin is not None:
            self.B.setRange(self.vm["w"].idx(0, 1, n), pin, pin)

    def app(self, trace, sc_lp):
        orig_app(self, trace, sc_lp)
        xx = trace["solutions"][-1]
        out["obj"] = trace["objectives"][-1]
        out["w"] = np.array([[xx[self.vm["w"].idx(i, j, m)] for m in range(self.N_n)]
                             for i in range(self.N_i) for j in range(self.N_j)])

    cls._computeNLstuff, cls._buildConstraints, cls._sc_trace_append = nl, bc, app
    try:
        p.solve("maxBequest", options={"noRothConversions": "None", "withItemized": "none", "maxIter": 1})
    finally:
        cls._computeNLstuff, cls._buildConstraints, cls._sc_trace_append = orig_nl, orig_bc, orig_app
    return out


for it, alt in ((IT, ALT), (ALT, IT)):
    base = solve_lp(it)
    val = rec[alt]["w"][TD_JOE, n]
    pinned = solve_lp(it, pin=val)
    print(f"LP of iteration {it}: objective {base['obj']:,.2f}; Joe's tax-deferred withdrawal in {YEAR}: "
          f"{base['w'][TD_JOE, n] / g[n]:,.0f} (today $; the loop's iterate had {rec[it]['w'][TD_JOE, n] / g[n]:,.0f})")
    print(f"  pinned to iteration {alt}'s {val / g[n]:,.0f}: objective {pinned['obj']:,.2f}, "
          f"change {pinned['obj'] - base['obj']:+.4f}")
    moved = np.abs(pinned["w"] - base["w"]) / g[: len(yr)] > 1
    acct = ["taxable", "tax-deferred", "Roth", "HSA"]
    print("  withdrawals that moved (today $):",
          [(f"{'Joe' if r < 4 else 'Jane'} {acct[r % 4]}", int(yr[c]),
            round((pinned["w"][r, c] - base["w"][r, c]) / g[c]))
           for r, c in zip(*np.nonzero(moved), strict=True)][:14])

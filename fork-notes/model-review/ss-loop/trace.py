"""Trace the self-consistent loop on the Phase 3 probe couple with a mortgage (2026-10-16).

Records, per loop iteration, the SC parameters the LP was built with, the SS taxable fraction the
iterate's own income implies (IRS formula), MAGI, Roth conversions, withdrawals and bracket fills,
pickles them to out/<tag>.pkl, and prints the tables quoted in PROGRESS.md ("Why the NY + mortgage
loop fails"). Couple: itemized_convergence.couple (born 1964, $1.5M tax-deferred, $80k core +
property tax budget, $600k mortgage), maxBequest, withItemized="none". Date frozen at 2026-10-15.

Usage: trace.py TAG STATE LOCALITY|- YOB PT [option=value ...] [NORECAP]
  NORECAP: NY benefit recapture forced to zero (Plan._state_recapture_implied patched).
"""
import io
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
argv = sys.argv[1:]
sys.argv = ["x", "/dev/null"]
sys.path.insert(0, os.path.join(HERE, "..", "phase3-review"))
import itemized_convergence as ic  # noqa: E402  (freezes the date at 2026-10-15)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from owlplanner import tax_federal as tx  # noqa: E402


def run(tag, state, loc, yob, pt, opts, norecap=False):
    log = io.StringIO()
    p = ic.couple(state, "" if loc == "-" else loc, 600000.0, yob, log)
    p.houseLists["Budget"] = ic.cond(pd.DataFrame([ic.line("core", "core", 80000.0),
                                                   ic.line("pt", "property tax", pt)]), "Budget")
    cls = type(p)
    rec = []
    orig_append, orig_recap = cls._sc_trace_append, cls._state_recapture_implied

    def hook(self, trace, sc_lp):
        orig_append(self, trace, sc_lp)
        xx = trace["solutions"][-1]
        vm = self.vm
        ss_n = np.sum(self.zetaBar_in, axis=0)

        def block(name, shape):
            return np.array([xx[vm[name].idx(*ix)] for ix in np.ndindex(*shape)]).reshape(shape)

        rec.append({
            "f_obj": trace["scaledObjectives"][-1],
            "sc": {k: np.array(v).copy() for k, v in sc_lp.items()},
            "MAGI": self.MAGI_aca_n.copy(),
            "psi_impl": tx.compute_social_security_taxability(self.N_i, self.MAGI_aca_n, ss_n, n_d=self.n_d),
            "ss": ss_n.copy(),
            "x": block("x", (self.N_i, self.N_n)),
            "w": block("w", (self.N_i, self.N_j, self.N_n)).reshape(self.N_i * self.N_j, self.N_n),
            "f": block("f", vm["f"].shape),
            "fcap": self.DeltaBar_tn.copy(), "frate": self.theta_tn.copy(),
            "stf": block("st_f", vm["st_f"].shape) if "st_f" in vm else None,
            "stcap": self.st_DeltaBar_tn.copy(), "strate": self.st_theta_tn.copy(),
        })

    cls._sc_trace_append = hook
    if norecap:
        cls._state_recapture_implied = lambda self: np.zeros(self.N_n)
    try:
        p.solve("maxBequest", options=dict({"noRothConversions": "None", "withItemized": "none"}, **opts))
    finally:
        cls._sc_trace_append, cls._state_recapture_implied = orig_append, orig_recap
    r = ic.record(p, log, 0.0)
    print(f"{tag}: {state} {loc} yOBBBA {yob} pt {pt:,.0f} {opts}{' NORECAP' if norecap else ''}: "
          f"{r['iters']} iterations, {r['conv']}, bequest {r.get('obj'):,.0f}, worst residual {r.get('resid_worst')}")
    os.makedirs(OUT, exist_ok=True)
    pickle.dump({"rec": rec, "year": p.year_n, "gamma": p.gamma_n}, open(os.path.join(OUT, f"{tag}.pkl"), "wb"))
    return rec, p.year_n, p.gamma_n


def tables(rec, yr, g, first=2034, last=2042, window=10):
    """Per year over the last `window` iterations: SS, MAGI range, implied Psi range, fill of the
    top federal bracket used, state taxable income range (today's $)."""
    N = len(yr)
    tail = rec[-window:]
    print("  year     SS   MAGI min..max (today $)   Psi implied   fed bracket (fill)      state taxable income")
    for n in range(N):
        if not first <= yr[n] <= last:
            continue
        m = np.array([r["MAGI"][n] for r in tail]) / g[n]
        ps = np.array([r["psi_impl"][n] for r in tail])
        fills = []
        for r in tail:
            f, cap = r["f"][:, n], r["fcap"][:, n]
            t = int(np.max(np.nonzero(f > 1)[0])) if np.any(f > 1) else 0
            fills.append((r["frate"][t, n], f[t] / cap[t]))
        st = np.array([np.sum(r["stf"][:, n]) for r in tail]) / g[n] if tail[0]["stf"] is not None else np.zeros(1)
        rates = sorted({round(100 * a) for a, _ in fills})
        fl = [b for _, b in fills]
        print(f"  {yr[n]} {rec[-1]['ss'][n] / g[n]:7,.0f}  {m.min():9,.0f}..{m.max():9,.0f}   "
              f"{ps.min():.3f}..{ps.max():.3f}   {rates}% {100 * min(fl):3.0f}..{100 * max(fl):3.0f}%   "
              f"{st.min():8,.0f}..{st.max():8,.0f}")


if __name__ == "__main__":
    tag, state, loc, yob, pt = argv[0], argv[1], argv[2], int(argv[3]), float(argv[4])
    norecap = "NORECAP" in argv[5:]
    opts = dict(a.split("=", 1) for a in argv[5:] if "=" in a)
    rec, yr, g = run(tag, state, loc, yob, pt, opts, norecap)
    print("  objective per iteration:", [round(r["f_obj"]) for r in rec])
    tables(rec, yr, g)

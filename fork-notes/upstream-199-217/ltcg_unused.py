"""#205 stakes: years where ordinary taxable income is 0 while gains are taxed, on Owl's examples."""
import glob, io, os, sys
import numpy as np
sys.path.insert(0, "/home/user/Owl/src")
import owlplanner as owl
from owlplanner import tax_federal as tx
print(owl.__file__)
EX = "/home/user/Owl/examples"
for f in sorted(glob.glob(f"{EX}/Case_*.toml")):
    case = os.path.basename(f)[5:-5]
    try:
        p = owl.readConfig(f, verbose=False, logstreams=[io.StringIO()])
        hfp = f"{EX}/HFP_{case}.xlsx"
        if os.path.exists(hfp):
            p.readHFP(hfp)
        p.solve(p.objective, dict(p.solverOptions or {}))
    except Exception as e:
        print(case, "error", e); continue
    if p.caseStatus != "solved":
        print(case, p.caseStatus); continue
    Nn = p.N_n; g = p.gamma_n[:Nn]
    cap = np.maximum(p.sigmaBar_n[:Nn], p.e_n)
    unused = np.where(p.G_n < 1.0, cap - p.e_n, 0.0)
    owl_t = tx.capitalGainTax(p.N_i, p.G_n + p.Q_n, p.Q_n, g, p.n_d, Nn)
    ti = np.maximum(0.0, p.G_n + p.Q_n - unused)
    law_t = tx.capitalGainTax(p.N_i, ti, np.minimum(p.Q_n, ti), g, p.n_d, Nn)
    over = (owl_t - law_t) / g
    yrs = np.flatnonzero((unused > 1) & (p.Q_n > 1))
    print(f"{case:18s} years={len(yrs):2d} overstated LTCG tax (today's $) total={over.sum():9.0f} "
          f"max/yr={over.max():8.0f} first={[int(p.year_n[n]) for n in yrs[:4]]}", flush=True)

"""
Phase 5 evidence: which upstream examples pay Social Security before FRA in a year with wages.

Owl does not model the SSA earnings test, so in such a year it pays the full benefit. For each
hit the script prints the wages, the benefit Owl pays that year (today's $, own + spousal), and
half the wages above the 2026 annual exempt amount ($24,480, POMS RS 02501.025 D), a first-order
size of the withholding (the wages are nominal and the exempt amount is the 2026 one, so this is
not the statutory amount for later years). Run from the repo root:

    .venv/bin/python fork-notes/phase5/et_examples.py
"""

import glob
import logging
import os

import owlplanner as owl
from owlplanner import socialsecurity as socsec

EXEMPT_2026 = 24480

logging.disable(logging.CRITICAL)
os.chdir(os.path.join(os.path.dirname(__file__), "..", "..", "examples"))
for f in sorted(glob.glob("Case_*.toml")):
    p = owl.readConfig(f, verbose=False, loadHFP=True)
    fras = socsec.getFRAs(p.yobs, p.mobs, p.tobs)
    y0 = int(p.year_n[0])
    rows = []
    for i in range(p.N_i):
        if p.ssecAmounts[i] == 0:
            continue
        claim = p.yobs[i] + (p.mobs[i] - 1) / 12 + p.ssecAges[i]
        fra = p.yobs[i] + (p.mobs[i] - 1) / 12 + fras[i]
        for n in range(p.N_n):
            w = float(p.omega_in[i, n])
            if w > 0 and y0 + n + 1 > claim and y0 + n < fra:
                rows.append((p.inames[i], y0 + n, w, float(p.zeta_in[i, n]), max(0.0, (w - EXEMPT_2026) / 2)))
    if not rows:
        print(f"{f}: none")
        continue
    i0 = p.inames.index(rows[0][0])
    print(f"{f}: {rows[0][0]} born {p.yobs[i0]}-{p.mobs[i0]:02d}, claims at {p.ssecAges[i0]:.2f}, FRA {fras[i0]:.2f}")
    for name, yr, w, ss, half in rows:
        print(f"    {yr}  wages {w:9,.0f}  SS paid by Owl {ss:8,.0f}  (wages - 24,480)/2 {half:8,.0f}")

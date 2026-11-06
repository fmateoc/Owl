"""The conversion and bracket view (run-library-design.md 14.1, I8).

One row per plan year: the ordinary taxable income the plan earns, the Roth conversion
layer that fills the bracket, and the lines the year is measured against -- the ordinary
bracket edges, the 0% capital-gains edge, the IRMAA tier edges and the ACA lines (the
Medicaid limit, where the credit starts, and the 400% FPL cliff). Amounts are today's
dollars. `cli.formatters.plan_to_dict` writes the view into `plan.json`, so the run page
reads the durable files alone (D7); the per-request regret sweep
(`stresstests.run_conversion_regret_sweep`, one `regret` job per request) answers "what
would a different conversion have cost?".

The conversions themselves are already optimized in the model -- IRMAA, ACA, SS taxability
and state tax priced together -- so the design explains them here instead of adding an
explorer. The lines and the income are not all the same measure: the ordinary edges are
measured against ordinary taxable income (`Plan.G_n`), the IRMAA and ACA lines against
MAGI (`Plan.MAGI_n`), and the 0% capital-gains edge against the preferential-income base
the model edges the gains on -- the QDCG worksheet's line-1 income, `G_n + e_n +
max(Q_n, 0)` less the deduction the ordinary income leaves unused
(`thresholds._gains_entries`; review AF8) -- each shown per year so the reader sees which
line the conversion is filling. No model change: nothing here feeds back into an LP.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

from datetime import date

import numpy as np

from . import tax_federal as tx


def _edges(ordinary: dict, n: int) -> list:
    return [{"label": name, "amount": round(float(values[n]), 2)}
            for name, values in ordinary.items()]


def _fill(income: float, edges: list) -> tuple:
    """(the bracket the income fills, room to the next edge) from the ordinary edges."""
    above = [e for e in edges if e["amount"] > income]
    below = [e for e in edges if e["amount"] <= income]
    fills = below[-1]["label"] if below else "below the first bracket"
    if not above:
        return fills, None
    return fills, round(above[0]["amount"] - income, 2)


def bracket_view(p) -> dict:
    """The per-year view (today's dollars) of a solved plan: income, conversions and lines.

    Rows follow the plan's years; each holds `ordinary_taxable_income` (the bracket base,
    `Plan.G_n`), `conversion` (the Roth conversion layer within it), `magi`, and the year's
    lines. The IRMAA edges are the *premium* year's tier amounts -- the MAGI of year m sets
    the premiums of m + 2 (`tax_federal.mediCosts`, 20 CFR 418.1135(a)) -- and are read in
    the tax year's dollars, as `thresholds._irmaa_entries` reads them; a tax year whose
    premium year leaves the plan has none (review AF4). The ACA lines are
    the poverty line of the year's tax household (`tax_federal._aca_fpl`) times the
    Medicaid limit, 1.0 (where the credit starts) and 4.0 (the cliff). `gains_edge_0` (the
    0%->15% capital-gains edge) is measured against the QDCG worksheet's line-1 income,
    `G_n + e_n + max(Q_n, 0)` less the deduction the ordinary income leaves unused
    (`thresholds._gains_entries`), **not** `ordinary_taxable_income`; the block says so
    once for every row (review AF8).
    """
    N = p.N_n
    gamma = np.asarray(p.gamma_n[:N], dtype=float)
    thisyear = date.today().year
    status_n = tx.filingStatusIndex_n(p.N_i, p.n_d, N)
    ordinary = tx.taxBrackets(p.N_i, p.n_d, N, getattr(p, "yOBBBA", 2032))
    family_n, parts_n = tx._aca_coverage(p.yobs, p.horizons, N, p.mobs, p.tobs, thisyear)
    medicaid_n = np.asarray(p._medicaid_n(), dtype=float)
    aca_start = max(0, int(getattr(p, "aca_start_year", 0)) - int(p.year_n[0])) \
        if getattr(p, "aca_start_year", 0) > 0 else 0

    rows = []
    for n in range(N):
        year = int(p.year_n[n])
        g = float(gamma[n])
        income = float(p.G_n[n]) / g
        edges = _edges(ordinary, n)
        fills, room = _fill(income, edges)

        irmaa_edges = []
        n_prem = n + 2  # the premium year this tax year's MAGI sets (20 CFR 418.1135(a))
        if n_prem < N:  # a premium year past the plan has no edges to name (as `thresholds`
            # `_irmaa_entries` skips it; review AF4)
            irmaa = tx.irmaaThresholds(tx.irmaaStatus(p.horizons, n_prem), p.gamma_n, n_prem, thisyear)
            irmaa_edges = [{"label": f"IRMAA tier {k}", "amount": round(float(edge) / g, 2),
                            "premium_year": int(p.year_n[n_prem])}
                           for k, edge in enumerate(irmaa, start=1)]

        aca_lines = []
        if getattr(p, "slcsp_annual", 0.0) > 0 and n >= aca_start and parts_n[n]:
            fpl = float(tx._aca_fpl(year, int(family_n[n]), np.asarray(p.gamma_n, dtype=float),
                                    thisyear)) / g
            medicaid = float(medicaid_n[n])
            if medicaid > 0:
                aca_lines.append({"label": f"Medicaid limit ({medicaid * 100:g}% FPL)",
                                  "amount": round(medicaid * fpl, 2)})
            aca_lines.append({"label": "the credit starts (100% FPL)", "amount": round(fpl, 2)})
            aca_lines.append({"label": "400% FPL (the subsidy cliff)", "amount": round(4.0 * fpl, 2)})

        rows.append({
            "year": year,
            "ages": [int(year - int(p.yobs[i])) for i in range(p.N_i)],
            "ordinary_taxable_income": round(income, 2),
            "conversion": round(float(np.sum(np.asarray(p.x_in[:, n], dtype=float))) / g, 2),
            "magi": round(float(p.MAGI_n[n]) / g, 2),
            "fills_bracket": fills,
            "room_to_next_edge": room,
            "ordinary_edges": edges,
            "gains_edge_0": round(float(tx.capGainRates[status_n[n]][0]), 2),
            "irmaa_edges": irmaa_edges,
            "aca_lines": aca_lines,
        })
    return {"units": "today's dollars",
            "gains_edge_0_measured_against":
                "the QDCG worksheet's line-1 income (G_n + e_n + max(Q_n, 0) less the "
                "deduction the ordinary income leaves unused; thresholds._gains_entries), "
                "not ordinary_taxable_income",
            "years": rows}

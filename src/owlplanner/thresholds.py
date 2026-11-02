"""Threshold proximity: "Things to look at" after a solve (run-library-design.md, 14.1, I3).

A solved plan parks income near cliffs on purpose (the optimizer fills a bracket to its edge),
and a plan can sit just under one by accident. This report lists the years where the plan's own
income sits just below or just over a threshold the model knows -- IRMAA tiers, the 0% capital
gains bracket, the SS taxability bands, the marketplace subsidy limits, the state's benefit
recapture, the Enhanced STAR limit, and the NIIT line -- each with its distance and, where the
model prices the crossing, what crossing it costs. An invented example from the design:

    2031: $1,200 over IRMAA tier 1, cost $1,900

"Just below or just over" is a band of `NEAR_BAND` (5%) of the boundary amount (the user's
call, 2026-11-02). Amounts are reported in today's dollars. The cost of a boundary is the
model's own charge evaluated at the boundary plus the gap, less the charge at the boundary
(`cost` below): the price of closing that gap, one year, wherever the model lands it. Where
the boundary is a ramp rather than a cliff (the SS taxability bands) no cost is reported.

Everything here reads the solved arrays of a `Plan`; `cli.formatters.plan_to_dict` writes the
report into `plan.json`, so the run library shows it from the durable files alone (D7). No
model change: nothing here feeds back into an LP.
"""

from __future__ import annotations

from datetime import date

import numpy as np

from . import tax_federal as tx
from . import tax_state

# A year is "just below" or "just over" a boundary when its distance is within this fraction
# of the boundary amount (today's $, as reported).
NEAR_BAND = 0.05

# The kinds the report knows, in the order the run page explains them.
KINDS = ("irmaa", "gains_0", "ss_taxability", "aca", "state_recapture", "star", "niit")


def _entry(year, kind, label, side, distance, cost, affects, note):
    """One report row. `distance` and `cost` are in today's dollars; `cost` may be None."""
    return {
        "year": int(year),
        "kind": kind,
        "label": label,
        "side": side,
        "amount_today_dollars": round(float(distance), 2),
        "cost_today_dollars": None if cost is None else round(float(cost), 2),
        "affects": None if affects is None else int(affects),
        "note": note,
    }


def _near(distance, boundary):
    return abs(distance) <= NEAR_BAND * abs(boundary) and abs(distance) > 0.005


def _irmaa_entries(p):
    """IRMAA tiers: the MAGI of tax year m sets the premiums of year m + 2 (20 CFR 418.1135(a)).

    The tier edge is the premium year's own threshold amount, compared against the tax year's
    MAGI as `tax_federal.mediCosts` compares them. The cost of crossing an edge is one year of
    the added Part B + Part D surcharge for each month of Medicare coverage in the premium year,
    priced by `mediCosts` itself at the edge and across it.
    """
    entries = []
    N = p.N_n
    thisyear = date.today().year
    months = tx.medicareMonths(p.yobs, p.horizons, N, p.mobs, p.tobs, thisyear)
    include_part_d = getattr(p, "_include_medicare_part_d", True)
    part_d_base = getattr(p, "_medicare_part_d_base_annual_per_person", 0.0)
    medical_n = p._medical_n(np.asarray(p.gamma_n[:N], dtype=float))

    def premiums(magi):
        return tx.mediCosts(
            p.yobs, p.horizons, magi, p.prevMAGI, np.asarray(p.gamma_n[:N], dtype=float), N,
            include_part_d=include_part_d, part_d_base_annual_per_person=part_d_base,
            medical_n=medical_n, mobs=p.mobs, tobs=p.tobs, slack=1.0,
        )

    for m in range(N):
        n_prem = m + 2  # the premium year this tax year's MAGI sets
        if n_prem >= N or not np.any(months[:, n_prem] > 0):
            continue
        thresholds = tx.irmaaThresholds(
            tx.irmaaStatus(p.horizons, n_prem), p.gamma_n, n_prem, thisyear)
        magi = float(p.MAGI_n[m])
        for k, edge in enumerate(thresholds, start=1):
            edge = float(edge)
            distance = magi - edge
            if not _near(distance, edge):
                continue
            at_edge = np.array(p.MAGI_n[:N], dtype=float)
            at_edge[m] = edge
            across = at_edge.copy()
            across[m] = edge + abs(distance)
            cost = float(premiums(across)[n_prem] - premiums(at_edge)[n_prem])
            entries.append(_entry(
                p.year_n[m], "irmaa", f"IRMAA tier {k}",
                "over" if distance > 0 else "under", abs(distance) / float(p.gamma_n[m]),
                cost / float(p.gamma_n[n_prem]), p.year_n[n_prem],
                f"the MAGI of {int(p.year_n[m])} sets the Medicare premiums of "
                f"{int(p.year_n[n_prem])}",
            ))
    return entries


def _gains_entries(p):
    """The 0% capital-gains bracket: gains are free up to the 0%->15% edge of taxable income.

    The income measured against the edge is the model's own: the QDCG worksheet's line-1
    taxable income as `Plan._ltcg_tax_implied` computes it (plan.py) -- `G_n + e_n +
    max(Q_n, 0) - ded`, where `ded` is the deduction ceiling `sigmaBar_n` in the years whose
    gains brackets an unused deduction widens (all but the itemizing ones,
    `Plan._ltcg_deduction_widens_n`, #205) and the taken deduction `e_n` in the others. A
    year whose ordinary income leaves deduction unused gives gains more 0% room than
    `G_n + Q_n` says, and the report must not call it over on that account (step-3 review 2,
    Q1). The plan's gains stack on that income (`tax_federal.capitalGainTax`); crossing the
    edge taxes the gains it displaces at 15% (or more near the 20% edge), priced by
    `capitalGainTax` itself at the edge and across it.
    """
    entries = []
    N = p.N_n
    gamma = np.asarray(p.gamma_n[:N], dtype=float)
    status_n = tx.filingStatusIndex_n(p.N_i, p.n_d, N)
    # The QDCG line-1 basis (mirrors Plan._ltcg_tax_implied; e_n is None before the first
    # iterate, where G_n and Q_n are zero too).
    e_n = np.zeros(N) if getattr(p, "e_n", None) is None else np.asarray(p.e_n[:N], dtype=float)
    gains = np.maximum(np.asarray(p.Q_n[:N], dtype=float), 0.0)
    ded_n = np.where(getattr(p, "_ltcg_wide_n", True),
                     np.asarray(p.sigmaBar_n[:N], dtype=float), e_n)
    tx_income = np.maximum(0.0, np.asarray(p.G_n[:N], dtype=float) + e_n + gains - ded_n)

    def gains_tax(income):
        return tx.capitalGainTax(p.N_i, income, np.minimum(gains, income), gamma, p.n_d, N)

    for n in range(N):
        if gains[n] <= 0:
            continue
        edge = float(gamma[n] * tx.capGainRates[status_n[n]][0])
        distance = float(tx_income[n]) - edge
        if not _near(distance, edge):
            continue
        at_edge = tx_income.copy()
        at_edge[n] = edge
        across = at_edge.copy()
        across[n] = edge + abs(distance)
        cost = abs(float(gains_tax(across)[n] - gains_tax(at_edge)[n]))
        entries.append(_entry(
            p.year_n[n], "gains_0", "0% capital-gains bracket ends",
            "over" if distance > 0 else "under", abs(distance) / float(gamma[n]),
            cost / float(gamma[n]), None,
            "gains above the edge are taxed at 15%",
        ))
    return entries


def _ss_entries(p):
    """SS taxability bands: provisional income (MAGI with SS added back minus half of SS).

    Below the first band no SS is taxable, between the bands half of the excess is, above the
    second 85% of it is (`tax_federal.compute_social_security_taxability`). Both edges are
    ramps, not cliffs: no cost is reported. The bands are frozen at their 1983/1994 amounts.
    """
    entries = []
    N = p.N_n
    gamma = np.asarray(p.gamma_n[:N], dtype=float)
    status_n = tx.filingStatusIndex_n(p.N_i, p.n_d, N)
    ss_n = np.sum(p.zetaBar_in[:, :N], axis=0)
    magi_aca = np.asarray(p.MAGI_aca_n[:N], dtype=float)
    for n in range(N):
        if ss_n[n] <= 0:
            continue
        pi = float(magi_aca[n] - 0.5 * ss_n[n])
        for label, edge in (("SS 50% taxation starts", float(tx.ssTaxabilityLo[status_n[n]])),
                            ("SS 85% taxation starts", float(tx.ssTaxabilityHi[status_n[n]]))):
            distance = pi - edge
            if not _near(distance, edge):
                continue
            entries.append(_entry(
                p.year_n[n], "ss_taxability", label,
                "over" if distance > 0 else "under", abs(distance) / float(gamma[n]),
                None, None,
                "a ramp: the taxable share of SS rises through the band, no cliff",
            ))
    return entries


def _aca_entries(p):
    """Marketplace subsidy limits: the contribution shares of MAGI, against the FPL of the year.

    The cost of a boundary is `tax_federal.acaCosts` priced at the boundary and across it: the
    top edge (400% FPL from 2026) is the subsidy cliff, the Medicaid line hands the household
    over to Medicaid at no premium, and the middle ones are contribution steps.
    """
    entries = []
    if float(getattr(p, "slcsp_annual", 0.0) or 0.0) <= 0:
        return entries
    N = p.N_n
    thisyear = date.today().year
    gamma = np.asarray(p.gamma_n[:N], dtype=float)
    magi = np.asarray(p.MAGI_aca_n[:N], dtype=float)
    n_aca_start = max(0, p.aca_start_year - int(p.year_n[0])) if p.aca_start_year > 0 else 0
    medical_n = p._medical_n(gamma)
    medicaid_n = p._medicaid_n()
    family_n, parts_n = tx._aca_coverage(p.yobs, p.horizons, N, p.mobs, p.tobs, thisyear)

    def aca_cost(magi_n):
        return tx.acaCosts(
            p.yobs, p.horizons, magi_n, gamma, p.slcsp_annual, N,
            thisyear=thisyear, n_aca_start=n_aca_start, medical_n=medical_n,
            mobs=p.mobs, tobs=p.tobs, medicaid_n=medicaid_n,
            gap="exact" if getattr(p, "_aca_lp", False) else "approx", slack=1.0,
        )

    for n in range(N):
        if n < n_aca_start or not parts_n[n]:
            continue  # nobody enrolled this year
        fpl = float(tx._aca_fpl(int(p.year_n[n]), family_n[n], gamma, thisyear))
        table = tx._aca_table(int(p.year_n[n]))
        ratios = set(table[0]) | {float(medicaid_n[n])}
        for ratio in sorted(r for r in ratios if r > 0):
            edge = ratio * fpl
            distance = float(magi[n]) - edge
            if not _near(distance, edge):
                continue
            if abs(ratio - 4.0) < 1e-9:
                label = "marketplace subsidy cliff (400% FPL)"
            elif abs(ratio - float(medicaid_n[n])) < 1e-9:
                label = f"Medicaid line ({ratio:g}x FPL)"
            else:
                label = f"marketplace contribution step ({ratio:g}x FPL)"
            at_edge = magi.copy()
            at_edge[n] = edge
            across = at_edge.copy()
            across[n] = edge + abs(distance)
            cost = abs(float(aca_cost(across)[n] - aca_cost(at_edge)[n]))
            if cost <= 0.005 and float(p.aca_costs_n[n]) <= 0:
                continue  # a boundary that costs nothing here (not a marketplace year)
            entries.append(_entry(
                p.year_n[n], "aca", label,
                "over" if distance > 0 else "under", abs(distance) / float(gamma[n]),
                cost / float(gamma[n]), None,
                "the premium is a share of MAGI (or the SLCSP, whichever is less)",
            ))
    return entries


def _recapture_entries(p):
    """The state's benefit recapture (NY Tax Law sec. 601(d)): the tier start on state AGI."""
    entries = []
    recap = getattr(p, "st_recap", None)
    if recap is None or not getattr(p, "_str_active", False):
        return entries
    start_n, width_n, until_n = recap
    N = p.N_n
    gamma = np.asarray(p.gamma_n[:N], dtype=float)
    state = p.state or "state"
    for n in range(N):
        edge = float(start_n[n])
        if not np.isfinite(edge) or edge <= 0:
            continue
        agi = float(p.st_agi_n[n])
        distance = agi - edge
        if not _near(distance, edge):
            continue

        def recapture(at_agi, n=n, edge=edge):
            return tax_state.state_recapture(
                at_agi, float(p.st_ti_n[n]), p.st_theta_tn[:, n], p.st_DeltaBar_tn[:, n],
                edge, float(width_n[n]), float(until_n[n]))

        cost = abs(recapture(edge + abs(distance)) - recapture(edge))
        entries.append(_entry(
            p.year_n[n], "state_recapture", f"{state} benefit recapture starts",
            "over" if distance > 0 else "under", abs(distance) / float(gamma[n]),
            cost / float(gamma[n]), None,
            "the benefit of the state's lower brackets is taken back in tiers above the start",
        ))
    return entries


def _star_entries(p):
    """The Enhanced STAR limit: the credit drops from enhanced to basic above the income standard.

    The income tested is the STAR income of two benefit years earlier (`star.StarSchedule`);
    the report's year is that income year. The basic credit has its own, much higher limit and
    is not reported (known limit).
    """
    entries = []
    if not getattr(p, "_star_on", False):
        return entries
    sched = p._star
    N = p.N_n
    gamma = np.asarray(p.gamma_n[:N], dtype=float)
    tested = sched.tested_income(p._star_income_n(), p.prevSTAR)
    for b in range(N):
        if sched.enhanced_n[b] <= 0:
            continue
        m = b - sched.lag  # the income year the benefit year is tested on
        if m < 0:
            continue  # tested on a pre-plan income the plan cannot move
        edge = float(sched.limit_n[b])
        distance = float(tested[b]) - edge
        if not _near(distance, edge):
            continue

        def credit(at_income, b=b, m=m):
            return float(sched.implied_credit(
                np.eye(1, N, m, dtype=float)[0] * at_income, p.prevSTAR)[b])

        cost = abs(credit(edge + abs(distance)) - credit(edge))
        entries.append(_entry(
            p.year_n[m], "star", "Enhanced STAR limit",
            "over" if distance > 0 else "under", abs(distance) / float(gamma[m]),
            cost / float(gamma[b]), p.year_n[b],
            f"the {int(p.year_n[m])} income sets the STAR credit of {int(p.year_n[b])}",
        ))
    return entries


def _niit_entries(p):
    """The NIIT line: 3.8% of net investment income above the MAGI threshold (not indexed)."""
    entries = []
    N = p.N_n
    gamma = np.asarray(p.gamma_n[:N], dtype=float)
    status_n = tx.filingStatusIndex_n(p.N_i, p.n_d, N)
    magi = np.asarray(p.MAGI_n[:N], dtype=float)
    nii = np.asarray(p.I_n[:N], dtype=float)

    def niit(magi_n):
        return tx.computeNIIT(p.N_i, magi_n, p.I_n, p.Q_n, p.n_d, N)

    for n in range(N):
        if nii[n] <= 0:
            continue
        edge = 250_000.0 if status_n[n] == 1 else 200_000.0
        distance = float(magi[n]) - edge
        if not _near(distance, edge):
            continue
        at_edge = magi.copy()
        at_edge[n] = edge
        across = at_edge.copy()
        across[n] = edge + abs(distance)
        cost = abs(float(niit(across)[n] - niit(at_edge)[n]))
        if cost <= 0.005:
            continue
        entries.append(_entry(
            p.year_n[n], "niit", "NIIT threshold",
            "over" if distance > 0 else "under", abs(distance) / float(gamma[n]),
            cost / float(gamma[n]), None,
            "3.8% of all net investment income, once MAGI crosses the line",
        ))
    return entries


def threshold_proximity(plan) -> dict:
    """The report of one solved plan: every boundary its income sits just below or just over.

    Returns `{"near_band_fraction": NEAR_BAND, "entries": [...]}` with the entries sorted by
    year. Each entry: year, kind (KINDS), label, side ("over"/"under"),
    amount_today_dollars (the distance), cost_today_dollars (the price of closing the gap, or
    None at a ramp), affects (the year the crossing bites: the IRMAA premium year, the STAR
    benefit year) and a note. Today's dollars.
    """
    entries = []
    for build in (_irmaa_entries, _gains_entries, _ss_entries, _aca_entries,
                  _recapture_entries, _star_entries, _niit_entries):
        entries.extend(build(plan))
    entries.sort(key=lambda e: (e["year"], e["kind"], e["label"]))
    return {"near_band_fraction": NEAR_BAND, "entries": entries}

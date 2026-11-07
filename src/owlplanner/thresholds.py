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
(`cost` below): the price of closing that gap, one year, wherever the model lands it (IRMAA
is priced just outside the premium functions' $1 slack on each side). Where the boundary is
a ramp rather than a cliff (the SS taxability bands) no cost is reported.

Each entry is in one of two groups (UX remediation QW-2, `ux-qw-handoff-2.md` decisions 2a-d):

- **"over"**: the year is above one of the three discrete cliffs -- the IRMAA tier the year
  is in (the highest tier its MAGI has crossed), the marketplace's 400% FPL subsidy cliff, or
  the Enhanced STAR limit -- wherever it sits, just over the line included (review AO1: a
  crossing inside the band pays the whole step, as one beyond it does). Its cost is what
  getting back under the line would save;
- **"near"**: everything else, inside the band of a boundary: the under side of those three
  lines, and either side of a continuous edge (a bracket edge, the NY recapture start, the
  NIIT kink, the SS taxability ramps, the marketplace's contribution steps).

Every entry whose price is above half a cent, and every ramp, is kept: there is no floor at
solve time. The run page folds the small ones (under $100, and the ramps) into "N smaller
items", so a floor can change without a re-solve. The block names its groups (`"groups"`), so
the page can tell a result solved before this build from one with no crossings.

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

# The entry groups (QW-2): inside a boundary's band, or over a discrete cliff beyond it.
GROUPS = ("near", "over")

# The kinds the report knows, in the order the run page explains them.
KINDS = ("irmaa", "gains_0", "ss_taxability", "aca", "state_recapture", "star", "niit")

# The slack the premium functions read a MAGI parked on an edge with (`tx.irmaaTier`): within
# it, a MAGI counts on the lower side of a lower edge and on the upper side of the top edge.
_SLACK = 1.0


def _entry(year, kind, label, side, distance, cost, affects, note, *, boundary, group="near",
           total=None):
    """One report row. `distance`, `boundary` and `cost` are in today's dollars (same deflator
    for the distance and the boundary); `cost` may be None. The boundary lets a reader check
    the entry is inside its band (`NEAR_BAND x boundary`, review 2 Q5). `group` is "near" or
    "over" (`GROUPS`); `total` (IRMAA only) is the year's whole surcharge, today's dollars."""
    row = {
        "year": int(year),
        "kind": kind,
        "label": label,
        "side": side,
        "amount_today_dollars": round(float(distance), 2),
        "boundary_today_dollars": round(float(boundary), 2),
        "cost_today_dollars": None if cost is None else round(float(cost), 2),
        "affects": None if affects is None else int(affects),
        "note": note,
        "group": group,
    }
    if total is not None:
        row["total_today_dollars"] = round(float(total), 2)
    return row


def _near(distance, boundary):
    return abs(distance) <= NEAR_BAND * abs(boundary) and abs(distance) > 0.005


def _irmaa_entries(p):
    """IRMAA tiers: the MAGI of tax year m sets the premiums of year m + 2 (20 CFR 418.1135(a)).

    The tier edge is the premium year's own threshold amount, compared against the tax year's
    MAGI as `tax_federal.mediCosts` compares them. The cost of crossing an edge is one year of
    the added Part B + Part D surcharge for each month of Medicare coverage in the premium year,
    priced by `mediCosts` itself on each side of the edge.

    Both sides are priced outside the slack (`_SLACK`): just below the edge, and at the edge
    plus the gap (at least twice the slack). Priced *at* the edge, the top tier -- which
    includes its edge -- and any gap within the slack read the full surcharge as $0 (step-3
    review 2, Q7: "2,000 over tier 5" and "0.50 over tier 1" both costed $0.00).
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
            medical_n=medical_n, mobs=p.mobs, tobs=p.tobs, slack=_SLACK,
        )

    for m in range(N):
        n_prem = m + 2  # the premium year this tax year's MAGI sets
        if n_prem >= N or not np.any(months[:, n_prem] > 0):
            continue
        thresholds = tx.irmaaThresholds(
            tx.irmaaStatus(p.horizons, n_prem), p.gamma_n, n_prem, thisyear)
        magi = float(p.MAGI_n[m])
        # The year's whole surcharge (QW-2): its premiums at its own MAGI, less those with the
        # MAGI just under tier 1 (the premium year's dollars, deflated as the cost is).
        under_all = np.array(p.MAGI_n[:N], dtype=float)
        under_all[m] = float(thresholds[0]) - 2 * _SLACK
        total = float(premiums(np.array(p.MAGI_n[:N], dtype=float))[n_prem]
                      - premiums(under_all)[n_prem])
        for k, edge in enumerate(thresholds, start=1):
            edge = float(edge)
            distance = magi - edge
            near = _near(distance, edge)
            # QW-2: the near-band rows of every tier, plus the tier the year is actually in
            # (the highest crossed), wherever it sits. A lower tier the year is far over is
            # not a separate thing to look at once a higher one is crossed too.
            if not near:
                if distance <= 0:
                    continue
                if k < len(thresholds) and magi > float(thresholds[k]):
                    continue
            # Review AO1: the tier the year is in is a crossing ("over") wherever it sits, inside
            # the band included; a near row of a lower tier, or of the tier above, is "near".
            top = distance > 0 and not (k < len(thresholds) and magi > float(thresholds[k]))
            below = np.array(p.MAGI_n[:N], dtype=float)
            below[m] = edge - 2 * _SLACK
            across = below.copy()
            across[m] = edge + max(abs(distance), 2 * _SLACK)
            cost = float(premiums(across)[n_prem] - premiums(below)[n_prem])
            entries.append(_entry(
                p.year_n[m], "irmaa", f"IRMAA tier {k}",
                "over" if distance > 0 else "under", abs(distance) / float(p.gamma_n[m]),
                cost / float(p.gamma_n[n_prem]), p.year_n[n_prem],
                # QW-2: the payment year is named explicitly (the two-year lookback).
                f"paid in {int(p.year_n[n_prem])} via the 2-year Medicare lookback: the "
                f"MAGI of {int(p.year_n[m])} sets those premiums",
                boundary=edge / float(p.gamma_n[m]), group="over" if top else "near",
                total=max(total, 0.0) / float(p.gamma_n[n_prem]),
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
            boundary=edge / float(gamma[n]),
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
                boundary=edge / float(gamma[n]),
            ))
    return entries


def _aca_entries(p):
    """Marketplace subsidy limits: the contribution shares of MAGI, against the FPL of the year.

    The cost of a boundary is `tax_federal.acaCosts` priced at the boundary and across it: the
    top edge (400% FPL from 2026) is the subsidy cliff, the Medicaid line hands the household
    over to Medicaid at no premium, and the middle ones are contribution steps.

    Known limit (step-3 review 2, Q6): in a state without the Medicaid expansion
    (`medicaid_n < 1`) the premium tax credit starts at 100% FPL, and that line is not
    reported. NY expanded (138% FPL), so a NY plan is unaffected.
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
            cliff = abs(ratio - 4.0) < 1e-9
            # QW-2: the cliff is a discrete crossing, listed wherever the year sits over it;
            # the steps and the Medicaid line stay near-band rows.
            if not _near(distance, edge) and not (cliff and distance > 0):
                continue
            if cliff:
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
            if cliff and distance > 0:
                # tx.acaCosts: from 2026, no subsidy above 400% FPL (review AN3).
                note = "above 400% FPL no subsidy is paid: the full benchmark premium (SLCSP)"
            else:
                note = "the premium is a share of MAGI (or the SLCSP, whichever is less)"
            entries.append(_entry(
                p.year_n[n], "aca", label,
                "over" if distance > 0 else "under", abs(distance) / float(gamma[n]),
                cost / float(gamma[n]), None, note,
                boundary=edge / float(gamma[n]),
                # Review AO1: the cliff crossed is "over" wherever it sits, inside the band too.
                group="over" if (cliff and distance > 0) else "near",
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
            boundary=edge / float(gamma[n]),
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
        near = _near(distance, edge)
        # QW-2 (decision 2a): the limit is a cliff, listed wherever the year sits over it.
        if not near and distance <= 0:
            continue

        def credit(at_income, b=b, m=m):
            return float(sched.implied_credit(
                np.eye(1, N, m, dtype=float)[0] * at_income, p.prevSTAR)[b])

        # Priced at the enhanced line only: an income over the basic credit's own limit too
        # would also lose the basic credit, which is not this line's cost.
        across = edge + abs(distance)
        if distance > 0 and edge < sched.basic_limit:
            across = min(across, float(sched.basic_limit))
        cost = abs(credit(across) - credit(edge))
        entries.append(_entry(
            p.year_n[m], "star", "Enhanced STAR limit",
            "over" if distance > 0 else "under", abs(distance) / float(gamma[m]),
            cost / float(gamma[b]), p.year_n[b],
            f"the {int(p.year_n[m])} income sets the STAR credit of {int(p.year_n[b])}",
            # Review AO1: over the limit is a crossing wherever it sits, inside the band too.
            boundary=edge / float(gamma[m]), group="over" if distance > 0 else "near",
        ))
    return entries


def _niit_entries(p):
    """The NIIT line: the MAGI threshold (not indexed) above which the 3.8% tax starts.

    `tax_federal.computeNIIT` charges 3.8% of the smaller of the net investment income
    (`I_n + Q_n`: interest, dividends and gains) and the MAGI above the threshold -- a kink,
    not a cliff (step-3 review 3, W7). The exposure gate reads the same income: a year whose
    investment income is gains or qualified dividends alone (a condo-purchase year that sells
    stock) is exposed too (review 2, Q2: the gate read `I_n` only).
    """
    entries = []
    N = p.N_n
    gamma = np.asarray(p.gamma_n[:N], dtype=float)
    status_n = tx.filingStatusIndex_n(p.N_i, p.n_d, N)
    magi = np.asarray(p.MAGI_n[:N], dtype=float)
    nii = np.asarray(p.I_n[:N], dtype=float) + np.asarray(p.Q_n[:N], dtype=float)

    def niit(magi_n):
        return tx.computeNIIT(p.N_i, magi_n, p.I_n, p.Q_n, p.n_d, N)

    for n in range(N):
        if nii[n] <= 0:
            continue
        edge = float(tx.niitThreshold[status_n[n]])
        distance = float(magi[n]) - edge
        if not _near(distance, edge):
            continue
        at_edge = magi.copy()
        at_edge[n] = edge
        across = at_edge.copy()
        across[n] = edge + abs(distance)
        cost = abs(float(niit(across)[n] - niit(at_edge)[n]))
        entries.append(_entry(
            p.year_n[n], "niit", "NIIT threshold",
            "over" if distance > 0 else "under", abs(distance) / float(gamma[n]),
            cost / float(gamma[n]), None,
            "3.8% of the smaller of the investment income and the MAGI above the line",
            boundary=edge / float(gamma[n]),
        ))
    return entries


def _keep(entry):
    """What the report keeps (QW-2, decisions 2b-2d): every ramp (cost None) and every entry
    priced above half a cent, near or over alike. A crossing or near miss that costs nothing
    is not a thing to look at (review 2, Q7). There is no other floor at solve time: the run
    page folds the small items, so its floor can move without a re-solve."""
    cost = entry["cost_today_dollars"]
    return cost is None or cost > 0.005


def threshold_proximity(plan) -> dict:
    """The report of one solved plan: every boundary its income sits just below or just over,
    and every discrete cliff it has crossed (QW-2).

    Returns `{"near_band_fraction": NEAR_BAND, "groups": ["near", "over"], "entries": [...]}`
    with the entries sorted by year. Each entry: year, kind (KINDS), label, side
    ("over"/"under"), amount_today_dollars (the distance), boundary_today_dollars,
    cost_today_dollars (the price of closing the gap, or None at a ramp), affects (the year
    the crossing bites: the IRMAA premium year, the STAR benefit year), a note, group
    ("over" for a cliff crossed, wherever the year sits; "near" for the rest, inside the
    band) and, on IRMAA entries, total_today_dollars (the year's whole surcharge). Today's
    dollars. `_keep` above says which rows make it in.
    """
    entries = []
    for build in (_irmaa_entries, _gains_entries, _ss_entries, _aca_entries,
                  _recapture_entries, _star_entries, _niit_entries):
        entries.extend(build(plan))
    entries = [e for e in entries if _keep(e)]
    entries.sort(key=lambda e: (e["year"], e["kind"], e["label"]))
    return {"near_band_fraction": NEAR_BAND, "groups": list(GROUPS), "entries": entries}

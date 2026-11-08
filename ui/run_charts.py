"""
The Run page's "why" views as figures and words, without Streamlit (UX review Q15-Q17).

- `brackets_figure` / `brackets_table`: income, the Roth conversion layer and MAGI against the
  ordinary bracket tops (faint steps, one per bracket), every IRMAA tier with its premium year,
  and the marketplace's 400% FPL line, in distinct hues and dashes (Q15). The table names the
  active (or next) IRMAA tier and the binding ceiling per year (UX remediation QW-3).
- `taxes_and_premiums_figure`, `income_sources_figure`: the taxes with the Medicare and
  marketplace premiums beside them; the income sources with all-zero series left out and a
  big-ticket purchase year annotated instead of setting the scale (Q16).
- `year_breakdown`, `year_summary`, `sankey_figure`, `flows_table`: one year's sources and
  uses grouped as the paragraph above the Sankey tells them, the Sankey drawn from the same
  groups with the amounts on the nodes and a labelled hub, and the two sides beside each
  other (Q17). One set of words for the paragraph and the nodes; a refunded tax is a tax
  offset, never income (UX remediation QW-1).
- `threshold_parts`: "Things to look at" as the page shows it (QW-2, `ux-qw-handoff-2.md`):
  the crossed cliffs, the near lines, and the small items folded away, with plain columns.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pandas as pd
import plotly.graph_objects as go

NOMINAL_PER_YEAR = "nominal $ per year"
TODAY_PER_YEAR = "$ per year (today's $)"

# Hues (Q15: the IRMAA and ACA lines were two dotted greens).
_IRMAA = "#d62728"
_ACA = "#9467bd"
_EDGE = "rgba(120, 120, 120, 0.45)"


# -- QW-2: "Things to look at" ---------------------------------------------------------------

# An entry priced under this (today's $) -- a crossing or a near line alike -- and every ramp
# (no price) fold into "N smaller items" (decisions 2b-2d). plan.json keeps them all, so this
# floor can move without a re-solve.
SMALL_ITEM = 100.0

THRESHOLD_COLUMNS = ("Year of income", "Line", "Where", "Costs", "Paid in", "Note")

# A note for a row merging several years whose own notes name each year (QW-2's merge).
_MERGED_NOTES = {
    "irmaa": "each year's MAGI sets the Medicare premiums two years later (the lookback)",
    "star": "each year's income sets the STAR credit two years later",
}


def _is_crossing(entry):
    """A year over one of the three discrete cliffs: an IRMAA tier, the 400% FPL line, the
    Enhanced STAR limit (QW-2, decision 2a)."""
    cliff = entry.get("kind") in ("irmaa", "star") or "cliff" in str(entry.get("label") or "")
    return cliff and entry.get("side") == "over"


def _entry_group(entry, band):
    """The entry's group on the page: "over" for a crossing of one of the three cliffs
    wherever it sits, "near" for the rest.

    Review AO1: read from the entry's side and line, not from plan.json's `group` alone. A
    result solved at d64ec67 marked a crossing inside the 5% band "near" (a $12,547
    crossing of the 400% FPL line was listed under *Close to a line*), and one solved before
    QW-2 marked nothing; both are drawn right this way. Every other entry keeps its own mark,
    or, unmarked, is "near" inside its band."""
    if _is_crossing(entry):
        return "over"
    if entry.get("group") in ("near", "over"):
        return entry["group"]
    boundary = entry.get("boundary_today_dollars")
    if boundary is None:
        return "near"
    return "near" if entry["amount_today_dollars"] <= band * abs(boundary) + 0.01 else "over"


def _span(values, fmt):
    lo, hi = min(values), max(values)
    return fmt(lo) if fmt(lo) == fmt(hi) else f"{fmt(lo)}-{fmt(hi)}"


def _dollars(value):
    return f"${value:,.0f}"


def _years(values):
    values = sorted(values)
    return str(values[0]) if values[0] == values[-1] else f"{values[0]}-{values[-1]}"


def _threshold_row(entries):
    """One table row for consecutive years over (or near) the same line."""
    first = entries[0]
    side = first["side"]
    where = f"{_span([e['amount_today_dollars'] for e in entries], _dollars)} {side}"
    costs = [e["cost_today_dollars"] for e in entries]
    if any(c is None for c in costs):
        cost_text = "-"
    else:
        cost_text = _span(costs, _dollars)
        totals = [e.get("total_today_dollars") for e in entries]
        if first["kind"] == "irmaa" and side == "over" and None not in totals:
            cost_text += f" (whole year {_span(totals, _dollars)})"
    paid = [e.get("affects") or e["year"] for e in entries]
    notes = {e.get("note") or "" for e in entries}
    note = notes.pop() if len(notes) == 1 else _MERGED_NOTES.get(first["kind"], first.get("note") or "")
    return {"Year of income": _years([e["year"] for e in entries]), "Line": first["label"],
            "Where": where, "Costs": cost_text, "Paid in": _years(paid), "Note": note,
            "_cost": sum(c or 0.0 for c in costs), "_year": first["year"]}


def _merged_rows(entries):
    """Consecutive years on the same side of the same line, as one row each."""
    runs = []
    for e in sorted(entries, key=lambda e: (e["kind"], e["label"], e["side"], e["year"])):
        last = runs[-1][-1] if runs else None
        if (last is not None and (last["kind"], last["label"], last["side"]) == (e["kind"], e["label"], e["side"])
                and e["year"] == last["year"] + 1):
            runs[-1].append(e)
        else:
            runs.append([e])
    return [_threshold_row(run) for run in runs]


def _table(rows):
    return pd.DataFrame([{k: r[k] for k in THRESHOLD_COLUMNS} for r in rows], columns=list(THRESHOLD_COLUMNS))


def threshold_parts(entries, band, has_groups=True) -> dict:
    """plan.json's threshold entries as the page shows them (QW-2):

    - "over": the cliffs crossed beyond the band (an IRMAA tier, the 400% FPL line, the
      Enhanced STAR limit), consecutive years over the same line merged into one row, the
      largest cost first;
    - "near": the lines the year sits within the band of, by year;
    - "small": everything priced under `SMALL_ITEM`, and the ramps, folded away;
    - "older": True for a result solved before the groups were marked (`has_groups` False).

    Each part is a DataFrame with `THRESHOLD_COLUMNS` (today's dollars).
    """
    over, near, small = [], [], []
    for e in entries:
        cost = e.get("cost_today_dollars")
        if cost is None or cost < SMALL_ITEM:
            small.append(e)
        elif _entry_group(e, band) == "over":
            over.append(e)
        else:
            near.append(e)
    over_rows = sorted(_merged_rows(over), key=lambda r: (-r["_cost"], r["_year"]))
    near_rows = sorted((_threshold_row([e]) for e in near), key=lambda r: (r["_year"], r["Line"]))
    small_rows = sorted((_threshold_row([e]) for e in small), key=lambda r: (r["_year"], r["Line"]))
    return {"over": _table(over_rows), "near": _table(near_rows), "small": _table(small_rows),
            "older": not has_groups}


# -- Q15: conversions and brackets ------------------------------------------------------------


def _taxable_conversions(years):
    income = [row.get("ordinary_taxable_income") or 0.0 for row in years]
    conv = [row.get("conversion") or 0.0 for row in years]
    # A plan.json written before review AI1 has no taxable share: the same rule here.
    return [row["conversion_taxable"] if row.get("conversion_taxable") is not None
            else min(c, max(i, 0.0)) for row, i, c in zip(years, income, conv, strict=True)]


def _cliff(row):
    return next((line["amount"] for line in row.get("aca_lines") or [] if "cliff" in line["label"]), None)


def brackets_figure(years):
    """(figure, note) for plan.json's `brackets.years`; *note* names the lines left above
    the chart (an IRMAA tier no year comes near). Rows without some keys (older results)
    draw what they have."""
    xs = [row["year"] for row in years]
    income = [row.get("ordinary_taxable_income") or 0.0 for row in years]
    taxable_conv = _taxable_conversions(years)
    magi = [row.get("magi") for row in years]
    data_top = max([0.0] + [v for v in income + magi if v is not None])
    upper = 1.2 * data_top if data_top > 0 else None

    fig = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=[max(0.0, i - c) for i, c in zip(income, taxable_conv, strict=True)],
                         name="taxable income, ex conversions", marker_color="#4c78a8"))
    fig.add_trace(go.Bar(x=xs, y=taxable_conv, name="Roth conversions (their taxable part)",
                         marker_color="#72b7b2"))
    fig.add_trace(go.Scatter(x=xs, y=magi, name="MAGI (what IRMAA and the cliff read)",
                             mode="lines+markers", line=dict(color="#222222", width=2)))

    # The ordinary bracket tops: faint steps, labelled at the right (Q15: the old line followed
    # whichever bracket the year was in, and zigzagged).
    labels = []
    for row in years:
        for edge in row.get("ordinary_edges") or []:
            if edge["label"] not in labels:
                labels.append(edge["label"])
    for label in labels:
        ys = [next((e["amount"] for e in row.get("ordinary_edges") or [] if e["label"] == label), None)
              for row in years]
        shown = [y for y in ys if y is not None]
        if not shown or (upper is not None and min(shown) > upper):
            continue
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=_EDGE, width=1, shape="hv"),
                                 name=f"top of the {label} bracket", legendgroup="brackets",
                                 showlegend=False, hovertemplate=f"top of the {label} bracket: "
                                 "%{y:,.0f}<extra></extra>"))
        fig.add_annotation(x=xs[-1], y=shown[-1], text=f"{label} top", showarrow=False, xanchor="left",
                           font=dict(size=10, color="#777777"), xshift=4)

    # Every IRMAA tier, with the premium year each tax year's MAGI sets.
    tiers = []
    for row in years:
        for k, edge in enumerate(row.get("irmaa_edges") or [], start=1):
            if k > len(tiers):
                tiers.append(edge["label"])
    above = []
    dashes = ["dash", "dash", "longdash", "longdash", "longdashdot"]
    for k, label in enumerate(tiers):
        ys, prem = [], []
        for row in years:
            edges = row.get("irmaa_edges") or []
            ys.append(edges[k]["amount"] if k < len(edges) else None)
            prem.append(edges[k].get("premium_year") if k < len(edges) else None)
        shown = [y for y in ys if y is not None]
        if not shown:
            continue
        if upper is not None and min(shown) > upper:
            above.append(f"{label} (from {min(shown):,.0f})")
            continue
        fig.add_trace(go.Scatter(
            x=xs, y=ys, customdata=prem, mode="lines",
            line=dict(color=_IRMAA, width=1.5 if k else 2, dash=dashes[min(k, len(dashes) - 1)], shape="hv"),
            opacity=max(0.45, 1.0 - 0.15 * k), name=f"{label} (MAGI; premiums two years later)",
            hovertemplate="%{x} income → %{customdata} Medicare: " + label + " at %{y:,.0f}<extra></extra>"))

    cliff = [_cliff(row) for row in years]
    if any(c is not None for c in cliff):
        fig.add_trace(go.Scatter(x=xs, y=cliff, mode="lines",
                                 line=dict(color=_ACA, width=2, dash="dashdot", shape="hv"),
                                 name="400% FPL, the marketplace cliff (MAGI)",
                                 hovertemplate="%{x}: 400% FPL at %{y:,.0f}<extra></extra>"))
    fig.update_layout(barmode="stack", yaxis_title=TODAY_PER_YEAR, xaxis_title="Year", height=460,
                      legend=dict(orientation="h", y=-0.2), margin=dict(r=70))
    if upper is not None:
        fig.update_yaxes(range=[0, upper])
    note = ("Above the chart, never reached: " + "; ".join(above) + ".") if above else ""
    return fig, note


def brackets_table(years, window=None, names=()) -> pd.DataFrame:
    """The table under the chart: numbers as numbers (the page formats them), no index.

    QW-3: one IRMAA text column, the tier the year's MAGI is in or its room below tier 1,
    with the premium year (`_irmaa_tier_text`), and *Next limit* (`_next_limit`): the case's
    limits on the year's conversions (plan.json's `conversion_window` is `window`, the
    people's names `names`), then the closest line above the income.
    """
    taxable_conv = _taxable_conversions(years)
    rows = []
    for row, part in zip(years, taxable_conv, strict=True):
        rows.append({
            "Year": row["year"],
            "Taxable income": row.get("ordinary_taxable_income"),
            "Conversions": row.get("conversion"),
            "Of which taxable": part,
            "MAGI": row.get("magi"),
            "Bracket": row.get("fills_bracket") or "-",
            "Room to its top": row.get("room_to_next_edge"),
            "IRMAA tier": _irmaa_tier_text(row),
            "400% FPL": _cliff(row),
            "Next limit": _next_limit(row, window, names),
        })
    table = pd.DataFrame(rows)
    # Years as nullable integers and amounts as whole-dollar floats: a None left in a column
    # made it an object column, and years as floats.
    table["Year"] = pd.to_numeric(table["Year"], errors="coerce").round().astype("Int64")
    for column in table.columns:
        if column not in TEXT_COLUMNS:
            table[column] = pd.to_numeric(table[column], errors="coerce").astype(float).round(0)
    # N2 (review AN10): Streamlit 1.66 draws a missing number as a grey "None" -- a float NaN,
    # a nullable Float64's pd.NA and an object None alike (checked with Playwright) -- and only
    # an empty text cell blank. The 400% FPL line is missing in every year without the
    # marketplace, so it is text: the amount with its separators, or nothing.
    table["400% FPL"] = [f"{v:,.0f}" if pd.notna(v) else "" for v in table["400% FPL"]]
    return table


# The brackets table's text columns (the rest are numbers the page formats).
TEXT_COLUMNS = ("Year", "Bracket", "IRMAA tier", "Next limit", "400% FPL")


def _medicare_in_premium_year(row):
    """Whether anyone has Medicare in the premium year the row's MAGI sets: the row's own flag
    (new solves), else judged from its ages two years on (65 or more), else unknown (None)."""
    flag = row.get("medicare_in_premium_year")
    if flag is not None:
        return bool(flag)
    ages = row.get("ages")
    if ages:
        return any(int(age) + 2 >= 65 for age in ages)
    return None


def _irmaa_tier_text(row) -> str:
    """The IRMAA tier the year's MAGI is in, or how far below tier 1 it is, with the premium
    year (QW-3; review AN5's words): "tier 2 ($38,466 over its $289,559 edge): 2031
    premiums", "below tier 1 by $97,333: 2029 premiums", "no Medicare premiums in 2028". The
    overshoot is never put where a premium is expected. "-" with nothing to say."""
    edges = row.get("irmaa_edges") or []
    magi = row.get("magi")
    prem = (edges[0].get("premium_year") if edges else None) or (row["year"] + 2 if "year" in row else None)
    if _medicare_in_premium_year(row) is False:
        return f"no Medicare premiums in {prem}" if prem is not None else "-"
    if not edges or magi is None:
        return "-"
    crossed = [k for k, edge in enumerate(edges, start=1) if magi > edge["amount"]]
    when = f": {prem} premiums" if prem is not None else ""
    if crossed:
        k = max(crossed)
        edge = edges[k - 1]["amount"]
        return f"tier {k} (${magi - edge:,.0f} over its ${edge:,.0f} edge){when}"
    return f"below tier 1 by ${edges[0]['amount'] - magi:,.0f}{when}"


def _joined(names):
    return ", ".join(names)


def _conversion_limit_text(row, window, names) -> list:
    """The case's own limits on this year's conversions (QW-3), one phrase per kind, the
    people it holds named: "conversion cap reached (Ari)", "no conversions before 2028 (the
    case's window)". [] for a row written before the limits were recorded."""
    limits = row.get("conversion_limit")
    if not limits:
        return []
    window = window or {}
    year = row.get("year")
    who = {}
    for i, limit in enumerate(limits):
        if limit not in (None, "not alive"):
            who.setdefault(limit, []).append(names[i] if i < len(names) else f"person {i + 1}")
    out = []
    for kind in ("cap", "window", "swap", "last years", "pinned", "excluded"):
        people = who.get(kind)
        if not people:
            continue
        if kind == "cap":
            out.append(f"conversion cap reached ({_joined(people)})")
        elif kind == "window":
            start, stop = window.get("start"), window.get("stop")
            if start and year is not None and year < start:
                out.append(f"no conversions before {start} (the case's window)")
            elif stop and year is not None and year >= stop:
                out.append(f"no conversions from {stop} on (the case's window)")
            else:
                out.append("no conversions this year (the case's window)")
        elif kind == "swap":
            out.append(f"no conversions for {_joined(people)} this year (the case's swap"
                       + (f" in {window['swap']}" if window.get("swap") else "") + ")")
        elif kind == "last years":
            out.append(f"no conversions in the last two years of life ({_joined(people)})")
        elif kind == "pinned":
            out.append(f"conversion held at the case's amount ({_joined(people)}, Roth conv fixed)")
        else:
            out.append(f"no conversions for {_joined(people)} (the case excludes them)")
    return out


def _nearest_line(row) -> str | None:
    """The closest line above the year's income, each read on its own measure (a bracket top
    against taxable income; an IRMAA tier, where someone has Medicare in its premium year,
    and the 400% FPL line against MAGI), as "IRMAA tier 2: $38,000 away (2031 premiums)"."""
    magi = row.get("magi")
    income = row.get("ordinary_taxable_income") or 0.0
    candidates = []
    for edge in row.get("ordinary_edges") or []:
        if edge["amount"] > income:
            candidates.append((edge["amount"] - income, f"{edge['label']} bracket top"))
    if _medicare_in_premium_year(row) is not False:
        for k, edge in enumerate(row.get("irmaa_edges") or [], start=1):
            if magi is not None and edge["amount"] > magi:
                prem = edge.get("premium_year")
                candidates.append((edge["amount"] - magi, f"IRMAA tier {k}", prem))
    cliff = _cliff(row)
    if cliff is not None and magi is not None and cliff > magi:
        candidates.append((cliff - magi, "400% FPL line"))
    if not candidates:
        return None
    room, label, *prem = min(candidates, key=lambda c: c[0])
    tail = f" ({prem[0]} premiums)" if prem and prem[0] is not None else ""
    return f"{label}: ${room:,.0f} away{tail}"


def _next_limit(row, window=None, names=()) -> str:
    """QW-3's *Next limit*, as a sentence: the case's own limits on the year's conversions,
    then -- while anyone may still convert -- the closest line above the income. Named "next",
    not "binding": the table cannot know which constraint holds the plan (the caption says
    the plan may stop short for another reason). A row written before the limits were
    recorded gets the lines only."""
    parts = _conversion_limit_text(row, window, list(names))
    limits = row.get("conversion_limit")
    free = not limits or any(limit is None for limit in limits)
    if free:
        line = _nearest_line(row)
        if line:
            parts.append(line)
    return "; ".join(parts) if parts else "-"


_LINE = "\u2003"  # an em space: a line under its group in the table


def _side_cells(groups, titles, star):
    cells = []
    for group, title in titles:
        rows = groups[group]
        if not rows:
            continue
        cells.append(f"{title}  ${sum(rows.values()):,.0f}")
        if len(rows) == 1 and flow_label(next(iter(rows)), star) == title:
            continue  # "Big-ticket purchases" under "Big-ticket purchases" says nothing new
        for name, v in sorted(rows.items(), key=lambda kv: -kv[1]):
            cells.append(f"{_LINE}{flow_label(name, star)}  ${v:,.0f}")
    return cells


def flows_table(sources: dict, uses: dict, star: bool = False) -> pd.DataFrame:
    """Sources beside Uses under the Sankey (QW-1, S6's table): each side's groups with their
    subtotals and their lines under them (`year_breakdown`, the paragraph's groups and words),
    then a totals line equal to the caption's in and out."""
    b = year_breakdown(sources, uses)
    left = _side_cells(b["sources"], _SOURCE_GROUPS, star)
    right = _side_cells(b["uses"], _USE_GROUPS, star)
    rows = max(len(left), len(right))
    left += [""] * (rows - len(left))
    right += [""] * (rows - len(right))
    left.append(f"Total in  ${sum(sources.values()):,.0f}")
    right.append(f"Total out  ${sum(uses.values()):,.0f}")
    return pd.DataFrame({"Sources": left, "Uses": right})


# -- Q16: taxes and premiums, income sources ---------------------------------------------------

# QW-1 (ux-qw-handoff-2.md): one map of words for the paragraph, the Sankey's nodes, the
# table under it and the *Taxes and premiums* chart. Each cash-flow row name (plan.json's,
# unchanged: older results and Compare read them) has a label (nodes, legends, the table) and
# the same words for prose (inside a sentence). A row not listed (a budget's own lines) keeps
# its name in both.
FLOW_LABELS = {
    "Federal income tax": ("Federal income tax", "federal income tax"),
    "Gains tax": ("Capital gains tax", "capital gains tax"),
    "NIIT": ("NIIT (3.8%)", "NIIT (3.8%)"),
    "Payroll tax": ("Payroll tax", "payroll tax"),
    "State and local tax": ("State and local tax", "state and local tax"),
    # The parts of "State and local tax" on the taxes chart (S-4; plan.json's by_year parts).
    "State tax": ("State tax", "state tax"),
    "Local tax": ("Local income tax (NYC / Yonkers)", "local income tax"),
    "STAR credit": ("NY STAR credit", "the NY STAR credit"),
    "Medicare premiums": ("Medicare premiums (with IRMAA)", "Medicare premiums (with IRMAA)"),
    "ACA premiums": ("Marketplace (ACA) premiums", "marketplace (ACA) premiums"),
    "Taxable-account withdrawals": ("Taxable (brokerage) accounts", "the taxable (brokerage) accounts"),
    "Tax-deferred withdrawals": ("Tax-deferred accounts (IRAs)", "the tax-deferred accounts (IRAs)"),
    "Roth withdrawals": ("Roth accounts", "the Roth accounts"),
    "HSA withdrawals": ("HSAs", "the HSAs"),
    "Wages": ("Wages", "wages"),
    "Social Security": ("Social Security", "Social Security"),
    "Pensions": ("Pensions", "pensions"),
    "SPIAs": ("SPIAs", "SPIAs"),
    "Other income": ("Other income", "other income"),
    "Net investment income": ("Net investment income", "net investment income"),
    "Fixed-asset income": ("Fixed-asset income", "fixed-asset income"),
    "Fixed-asset sale": ("Fixed-asset sale", "a fixed-asset sale"),
    "Big-ticket inflows": ("Big-ticket inflows", "big-ticket inflows"),
    "Net spending": ("Net spending", "net spending"),
    "Big-ticket purchases": ("Big-ticket purchases", "big-ticket purchases"),
    "Debt payments": ("Debt payments", "debt payments"),
    "Roth conversions": ("Roth conversions", "Roth conversions"),
    "Savings (surplus)": ("Back into savings", "back into savings"),
}
TAX_USES = ("Federal income tax", "Gains tax", "NIIT", "Payroll tax", "State and local tax")
PREMIUM_USES = ("Medicare premiums", "ACA premiums")
SAVINGS_SOURCES = ("Taxable-account withdrawals", "Tax-deferred withdrawals", "Roth withdrawals",
                   "HSA withdrawals")
CONVERSION_SOURCE = "Roth conversions (from the tax-deferred accounts)"
# A tax that came out negative (a refundable credit larger than the tax) lands on the sources
# side as "<row>, net refund" (`view.cash_flow_year`). In the fork only the NY STAR credit is
# refundable (`Plan._finalize_state_tax`: personal credits stop at zero, STAR comes off after).
REFUND = ", net refund"
STAR_REFUND = "State and local tax" + REFUND


def flow_label(name: str, star: bool = False) -> str:
    """One cash-flow row's label (QW-1): a node, a legend, the table under the Sankey. A
    refunded state tax reads "State tax refund (STAR)" when the run has STAR (`star`)."""
    if name == STAR_REFUND:
        return "State tax refund (STAR)" if star else "State tax refund"
    if name.endswith(REFUND):
        return flow_label(name[:-len(REFUND)]) + " refund"
    return FLOW_LABELS.get(name, (name, name))[0]


def flow_words(name: str) -> str:
    """The same row in prose, inside a sentence (QW-1: no capitals mid-sentence)."""
    return FLOW_LABELS.get(name, (name, name))[1]


def _chart_series(pairs):
    return tuple((key, flow_label(row)) for key, row in pairs)


TAX_SERIES = _chart_series((("federal_income_tax", "Federal income tax"), ("ltcg_tax", "Gains tax"),
                            ("niit", "NIIT"), ("payroll_tax", "Payroll tax"),
                            ("state_tax", "State and local tax")))
PREMIUM_SERIES = _chart_series((("medicare_premiums", "Medicare premiums"), ("aca_premiums", "ACA premiums")))
INCOME_SERIES = (("wages", flow_label("Wages")), ("ss", flow_label("Social Security")),
                 ("pension_income", flow_label("Pensions")), ("spia_income", flow_label("SPIAs")),
                 ("portfolio_withdrawals", "Withdrawals from savings"))


def _series(by_year, key):
    if key == "ss":
        return [sum(row.get("ss_income") or []) for row in by_year]
    return [row.get(key) or 0.0 for row in by_year]


# -- S-4: today's dollars, the state tax's parts, the event markers ---------------------------

UNITS = ("today", "nominal")
UNIT_LABELS = {"today": "Today's \\$", "nominal": "Nominal \\$"}
# by_year keys that are not amounts: never divided by the deflator.
_NOT_MONEY = {"year", "ages", "deflator"}


def units_control(key):
    """S-4: "Today's $ | Nominal $" for the by-year charts, kept for the session (shared by the
    Run and Compare pages: `library_units`), today's dollars by default (decision 7)."""
    import streamlit as st

    current = st.session_state.get("library_units", "today")
    choice = st.segmented_control("Amounts", list(UNITS), default=current, format_func=UNIT_LABELS.get, key=key)
    choice = choice or current
    st.session_state["library_units"] = choice
    return choice


def has_deflator(by_year) -> bool:
    """Whether every row carries its deflator (results solved since S-4)."""
    return bool(by_year) and all(isinstance(row.get("deflator"), (int, float)) and row["deflator"] > 0
                                 for row in by_year)


def effective_units(by_year, units: str) -> str:
    """The units a chart can be drawn in: today's dollars need the deflator (an older result
    draws nominal)."""
    return "today" if units == "today" and has_deflator(by_year) else "nominal"


def in_units(by_year, units: str):
    """The rows with every amount in `units`: today's dollars divide each year's amounts by
    that year's deflator (S-4); nominal returns the rows as they are."""
    if effective_units(by_year, units) == "nominal":
        return list(by_year)
    out = []
    for row in by_year:
        d = float(row["deflator"])
        new = {}
        for k, v in row.items():
            if k in _NOT_MONEY:
                new[k] = v
            elif isinstance(v, list):
                new[k] = [x / d if isinstance(x, (int, float)) else x for x in v]
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                new[k] = v / d
            else:
                new[k] = v
        out.append(new)
    return out


def axis_title(by_year, units: str, per_year: bool = True) -> str:
    if effective_units(by_year, units) == "today":
        return TODAY_PER_YEAR if per_year else "today's $"
    return NOMINAL_PER_YEAR if per_year else "nominal $"


def has_state_parts(by_year) -> bool:
    return bool(by_year) and all("local_tax" in row and "star_credit" in row for row in by_year)


def state_tax_parts(by_year) -> dict:
    """The state tax's parts per year (plan.json since S-4):
    state = state_tax - local_tax + star_credit (the state's own tax, NY recapture inside),
    local = local_tax, star = -star_credit (negative: a credit). They add up to `state_tax`
    in every year, a net STAR refund included."""
    return {
        "state": [(r.get("state_tax") or 0.0) - (r.get("local_tax") or 0.0) + (r.get("star_credit") or 0.0)
                  for r in by_year],
        "local": [r.get("local_tax") or 0.0 for r in by_year],
        "star": [-(r.get("star_credit") or 0.0) for r in by_year],
        "recapture": [r.get("state_recapture") or 0.0 for r in by_year],
    }


def _state_traces(by_year, years):
    """The state tax as one series (an older result) or as its parts, each drawn where it is
    not zero (the STAR credit below the axis, the Sankey's W1 rule for a refund)."""
    if not has_state_parts(by_year):
        return [go.Bar(x=years, y=_series(by_year, "state_tax"), name=flow_label("State and local tax"))]
    parts = state_tax_parts(by_year)
    state = go.Bar(x=years, y=parts["state"], name=flow_label("State tax"))
    if any(abs(v) >= 0.5 for v in parts["recapture"]):
        state.update(customdata=parts["recapture"],
                     hovertemplate="%{x}: %{y:,.0f}<br>NY benefit recapture inside: %{customdata:,.0f}"
                                   "<extra>" + flow_label("State tax") + "</extra>")
    traces = [state]
    if any(abs(v) >= 0.5 for v in parts["local"]):
        traces.append(go.Bar(x=years, y=parts["local"], name=flow_label("Local tax")))
    if any(abs(v) >= 0.5 for v in parts["star"]):
        traces.append(go.Bar(x=years, y=parts["star"], name=flow_label("STAR credit"),
                             marker_pattern_shape="x"))
    return traces


def event_markers(by_year, individuals=(), purchases=None) -> list:
    """(year, label) of the marked events, from plan.json alone (S-4): each person's last work
    year (`wages_by_person`; the household's last wage year on an older result), the purchase
    years (`big_ticket_years`), each person's Medicare start (the year they turn 65) and the
    last year with a debt (the year before `debt` falls to 0)."""
    years = [row["year"] for row in by_year]
    if not years:
        return []
    marks = []
    names = list(individuals or [])
    if all("wages_by_person" in row for row in by_year):
        for i, name in enumerate(names):
            worked = [row["year"] for row in by_year if (row["wages_by_person"][i] or 0) > 0.5]
            if worked and worked[-1] < years[-1]:
                marks.append((worked[-1], f"{name}'s last work year"))
    else:
        worked = [row["year"] for row in by_year if (row.get("wages") or 0) > 0.5]
        if worked and worked[-1] < years[-1]:
            marks.append((worked[-1], "Last wages"))
    for n in sorted(purchases or {}):
        if 0 <= n < len(years):
            marks.append((years[n], "Purchase"))
    for i, name in enumerate(names):
        for row in by_year:
            ages = row.get("ages") or []
            if i < len(ages) and ages[i] == 65:
                marks.append((row["year"], f"{name}: Medicare"))
                break
    debts = [row.get("debt") or 0.0 for row in by_year]
    for n in range(1, len(debts)):
        if debts[n - 1] > 0.5 and debts[n] <= 0.5:
            marks.append((years[n - 1], "Last loan year"))
    return sorted(marks)


def add_markers(fig, marks):
    """Vertical dotted lines with a short label; labels of the same year are joined."""
    by_year = {}
    for year, label in marks:
        by_year.setdefault(year, []).append(label)
    for k, (year, labels) in enumerate(sorted(by_year.items())):
        fig.add_vline(x=year, line_dash="dot", line_color=_EDGE, line_width=1)
        fig.add_annotation(x=year, y=1.0, yref="paper", yanchor="bottom" if k % 2 == 0 else "top",
                           text="<br>".join(labels), showarrow=False, font=dict(size=9),
                           bgcolor="rgba(255,255,255,0.7)")
    return fig


def taxes_and_premiums_figure(by_year, units="nominal", marks=()):
    """Taxes stacked, the health premiums as their own (hatched) series on the same stack. The
    state tax is split into the state's own tax, the local tax and the STAR credit where the
    result carries the parts (S-4); amounts in `units`."""
    rows = in_units(by_year, units)
    years = [row["year"] for row in rows]
    fig = go.Figure()
    for key, label in TAX_SERIES:
        if key == "state_tax":
            for trace in _state_traces(rows, years):
                fig.add_trace(trace)
            continue
        fig.add_trace(go.Bar(x=years, y=_series(rows, key), name=label))
    for key, label in PREMIUM_SERIES:
        values = _series(rows, key)
        if any(values):
            fig.add_trace(go.Bar(x=years, y=values, name=label, marker_pattern_shape="/"))
    # "relative": a negative bar (the STAR credit) stacks below the axis.
    fig.update_layout(barmode="relative", yaxis_title=axis_title(by_year, units), xaxis_title="Year",
                      height=360)
    return add_markers(fig, marks)


def big_ticket_years(cash_flow: dict) -> dict:
    """{year index: amount} of the big-ticket purchases (plan.json's `cash_flow` uses)."""
    values = ((cash_flow or {}).get("uses") or {}).get("Big-ticket purchases") or []
    return {n: float(v) for n, v in enumerate(values) if v and float(v) > 0.5}


def income_sources_figure(by_year, purchases=None, units="nominal", marks=()):
    """Income sources stacked, all-zero series left out. A big-ticket purchase year whose bar
    would set the scale (twice the other years' highest or more) runs off the top of the chart
    with its amount written on it (Q16). Amounts in `units` (S-4)."""
    rows = in_units(by_year, units)
    years = [row["year"] for row in rows]
    fig = go.Figure()
    totals = [0.0] * len(years)
    for key, label in INCOME_SERIES:
        values = _series(rows, key)
        if not any(values):
            continue
        totals = [t + (v or 0.0) for t, v in zip(totals, values, strict=True)]
        fig.add_trace(go.Bar(x=years, y=values, name=label))
    fig.update_layout(barmode="stack", yaxis_title=axis_title(by_year, units), xaxis_title="Year", height=360)
    add_markers(fig, marks)
    purchases = purchases or {}
    if effective_units(by_year, units) == "today":  # the cash flow's amounts are nominal
        purchases = {n: a / float(by_year[n]["deflator"]) for n, a in purchases.items() if n < len(by_year)}
    others = [t for n, t in enumerate(totals) if n not in purchases]
    rest = max(others) if others else 0.0
    if purchases and rest > 0 and max(totals[n] for n in purchases) >= 2 * rest:
        top = 1.3 * rest
        fig.update_yaxes(range=[0, top])
        for n, amount in purchases.items():
            fig.add_annotation(x=years[n], y=top, yanchor="top", showarrow=False,
                               text=f"↑ {totals[n]:,.0f}<br>incl. a {amount:,.0f}<br>purchase",
                               font=dict(size=10), bgcolor="rgba(255,255,255,0.8)")
    return fig


# -- Q17: one year's cash flow ------------------------------------------------------------------

_USE_GROUPS = (("spending", "Spending"), ("big_ticket", "Big-ticket purchases"),
               ("debt", "Debt payments"), ("taxes", "Taxes"), ("premiums", "Health premiums"),
               ("conversions", "Roth conversions"), ("surplus", "Back into savings"),
               ("other", "Other outflows"))
_SOURCE_GROUPS = (("savings", "From savings"), ("income", "Income"),
                  ("conversions", "Roth conversions"), ("tax_offsets", "Tax refunds"))
# Groups that always carry their total in a node of their own, even with one line (QW-1: the
# Health premiums node disappeared whenever a year had a single premium line). Spending gets
# one only for a budget's lines: "Net spending" alone is its own node (`_spending_node`).
_NAMED_USE_GROUPS = ("taxes", "premiums")


def _spending_node(rows):
    return bool(rows) and set(rows) != {"Net spending"}


def _use_group(name):
    if name in TAX_USES:
        return "taxes"
    if name in PREMIUM_USES:
        return "premiums"
    if name == "Big-ticket purchases":
        return "big_ticket"
    if name == "Debt payments":
        return "debt"
    if name == "Roth conversions":
        return "conversions"
    if name == "Savings (surplus)":
        return "surplus"
    if name.endswith(", net outflow"):
        return "other"
    return "spending"  # the budget's lines, or "Net spending" without a budget


def _source_group(name):
    if name in SAVINGS_SOURCES:
        return "savings"
    if name == CONVERSION_SOURCE:
        return "conversions"
    if name.endswith(REFUND):  # QW-1: a refunded tax is a tax offset, not income
        return "tax_offsets"
    return "income"


def year_breakdown(sources: dict, uses: dict) -> dict:
    """One year's rows (`view.cash_flow_year`) in groups that partition each side:
    {"uses": {group: {name: $}}, "sources": {group: {name: $}}} -- every row in exactly one
    group, so the groups add up to the side's total."""
    out = {"uses": {g: {} for g, _ in _USE_GROUPS}, "sources": {g: {} for g, _ in _SOURCE_GROUPS}}
    for name, value in uses.items():
        out["uses"][_use_group(name)][name] = value
    for name, value in sources.items():
        out["sources"][_source_group(name)][name] = value
    return out


def _usd(value):
    return f"\\${value:,.0f}"


def _parts(rows: dict) -> str:
    items = sorted(rows.items(), key=lambda kv: -kv[1])
    return ", ".join(f"{flow_words(k)} {_usd(v)}" for k, v in items)


def _refund_clause(name, value, star):
    """"state and local, a net refund of \\$2,934 (the STAR credit is larger than the tax)"
    (decision 6): the refund in its own clause, beside the taxes, never netted into them."""
    base = name[:-len(REFUND)]
    where = flow_words(base).removesuffix(" tax")
    credit = "the STAR credit" if (star and name == STAR_REFUND) else "a refundable credit"
    return f"{where}, a net refund of {_usd(value)} ({credit} is larger than the tax)"


def year_summary(year: int, sources: dict, uses: dict, star: bool = False) -> str:
    """The paragraph above the Sankey (UX review section 3), in nominal dollars of *year*,
    from the same rows the Sankey draws, in the same words (`flow_words`, QW-1).

    Decision 6 (ux-qw-handoff-2.md): the taxes sentence names the Sankey's figures -- the
    Taxes node's total and its lines -- and a refunded tax (the "..., net refund" rows) is its
    own clause: "Taxes \\$5,111: federal income tax \\$5,111; state and local, a net refund
    of \\$2,934 (the STAR credit is larger than the tax)." STAR is named only when the run has
    it (`star`); otherwise "a refundable credit".
    """
    b = year_breakdown(sources, uses)
    u, s = b["uses"], b["sources"]
    total = lambda rows: sum(rows.values())  # noqa: E731
    text = [f"**{year}**: spending {_usd(total(u['spending']))}"]
    extra = [f"big-ticket purchases {_usd(total(u['big_ticket']))}" if u["big_ticket"] else "",
             f"debt payments {_usd(total(u['debt']))}" if u["debt"] else ""]
    extra = [e for e in extra if e]
    text[0] += (" plus " + " and ".join(extra) if extra else "") + "."
    savings, income = total(s["savings"]), total(s["income"])
    if savings and income:
        text.append(f"The money comes from savings, {_usd(savings)} ({_parts(s['savings'])}), "
                    f"and from income, {_usd(income)} ({_parts(s['income'])}).")
    elif savings:
        if s["conversions"] or s["tax_offsets"]:  # not "all of it": the rest is named below
            text.append(f"The money comes from savings, {_usd(savings)} ({_parts(s['savings'])}).")
        else:
            text.append(f"All of it comes from savings: {_parts(s['savings'])}.")
    elif income:
        if s["conversions"] or s["tax_offsets"]:  # not "all of it": the rest is named below
            text.append(f"The money comes from income, {_usd(income)} ({_parts(s['income'])}).")
        else:
            text.append(f"All of it comes from income: {_parts(s['income'])}.")
    taxes = dict(u["taxes"])
    taxes.setdefault("Federal income tax", 0.0)  # "federal income tax $0" is worth saying
    refunds = s["tax_offsets"]
    if total(taxes) or refunds:
        clauses = [f"Taxes {_usd(total(taxes))}: {_parts(taxes)}"]
        clauses += [_refund_clause(k, v, star) for k, v in sorted(refunds.items(), key=lambda kv: -kv[1])]
        text.append("; ".join(clauses) + ".")
    else:
        text.append("No taxes.")
    if u["premiums"]:
        text.append(f"Health premiums {_usd(total(u['premiums']))} ({_parts(u['premiums'])}).")
    if u["conversions"]:
        text.append(f"A Roth conversion of {_usd(total(u['conversions']))} moves money from the tax-deferred "
                    "accounts to the Roth accounts: it is on both sides.")
    if u["surplus"]:
        text.append(f"{_usd(total(u['surplus']))} goes back into savings.")
    if u["other"]:
        text.append(f"Other outflows {_usd(total(u['other']))} ({_parts(u['other'])}).")
    return " ".join(text)


def sankey_figure(year: int, sources: dict, uses: dict, star: bool = False):
    """Sources (grouped where a group has two or more lines and is not the only group) → the
    year's hub → the use groups → their lines, amounts on every node.

    Taxes and Health premiums always get a node of their own carrying the group's total, even
    with one line (QW-1: the Health premiums node disappeared whenever a year had a single
    premium line); Spending gets one for a budget's lines, while "Net spending" alone goes
    straight from the hub, as does any other group of one line. Every node carries
    `flow_label`'s words, the paragraph's (QW-1); a refunded state tax is the source node
    "State tax refund (STAR)" when the run has STAR."""
    b = year_breakdown(sources, uses)
    labels, colors = [], []
    src, tgt, val = [], [], []

    def node(label, value, color):
        labels.append(f"{label}: ${value:,.0f}")
        colors.append(color)
        return len(labels) - 1

    total = sum(sources.values())
    # Review AO2: a source group of two or more rows (several accounts drawn from, several
    # incomes) gets a node of its own carrying the group's total, as the uses side does: the
    # paragraph names that total ("from savings, $158,708"), and it was on no node. Not when it
    # is the only source group: the hub then carries the same number, and the paragraph says
    # "All of it comes from savings: ..." with no total of its own.
    in_links = []
    several = sum(1 for g, _ in _SOURCE_GROUPS if b["sources"][g]) > 1
    for group, title in _SOURCE_GROUPS:
        rows = b["sources"][group]
        if not rows:
            continue
        if len(rows) == 1 or not several:
            in_links += [(node(flow_label(name, star), v, "#4c78a8"), v) for name, v in rows.items()]
            continue
        g = node(title, sum(rows.values()), "#2f5b8a")
        for name, v in sorted(rows.items(), key=lambda kv: -kv[1]):
            src.append(node(flow_label(name, star), v, "#4c78a8"))
            tgt.append(g)
            val.append(v)
        in_links.append((g, sum(rows.values())))
    hub = node(f"{year} cash flow", total, "#555555")
    for i, v in in_links:
        src.append(i)
        tgt.append(hub)
        val.append(v)
    for group, title in _USE_GROUPS:
        rows = b["uses"][group]
        if not rows:
            continue
        named = group in _NAMED_USE_GROUPS or (group == "spending" and _spending_node(rows))
        if len(rows) == 1 and not named:
            (name, v), = rows.items()
            src.append(hub)
            tgt.append(node(flow_label(name), v, "#f58518"))
            val.append(v)
            continue
        g = node(title, sum(rows.values()), "#e45756" if group == "taxes" else "#f58518")
        src.append(hub)
        tgt.append(g)
        val.append(sum(rows.values()))
        for name, v in sorted(rows.items(), key=lambda kv: -kv[1]):
            src.append(g)
            tgt.append(node(flow_label(name), v, "#ffbb78"))
            val.append(v)
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=colors, pad=14, thickness=14),
        link=dict(source=src, target=tgt, value=val, color="rgba(160, 160, 160, 0.35)",
                  hovertemplate="%{source.label} → %{target.label}<extra></extra>"),
    ))
    fig.update_layout(height=max(460, 24 * len(labels)), font=dict(size=11))
    return fig


# -- S-5: Compare's side-by-side charts ---------------------------------------------------------

TAXES_AND_PREMIUMS_KEYS = ("federal_income_tax", "ltcg_tax", "niit", "payroll_tax", "state_tax",
                           "medicare_premiums", "aca_premiums")
COMPARE_CHARTS = ("Spending", "Liquid net worth", "Taxes and health premiums, cumulative", "MAGI")


def _by_calendar_year(by_year, values):
    return {int(row["year"]): v for row, v in zip(by_year, values, strict=True)}


def compare_series(by_year, units: str) -> dict:
    """{chart: {year: value}} for one result, in `units` (`in_units`; MAGI from the brackets
    rows comes separately, `magi_series`)."""
    rows = in_units(by_year, units)
    running, cumulative = 0.0, []
    for row in rows:
        running += sum(float(row.get(k) or 0.0) for k in TAXES_AND_PREMIUMS_KEYS)
        cumulative.append(running)
    return {
        "Spending": _by_calendar_year(rows, [float(r.get("spending") or 0.0) for r in rows]),
        "Liquid net worth": _by_calendar_year(rows, [float(r.get("liquid_net_worth") or 0.0) for r in rows]),
        "Taxes and health premiums, cumulative": _by_calendar_year(rows, cumulative),
    }


def magi_series(brackets_years, by_year, units: str) -> tuple:
    """({year: MAGI}, {year: IRMAA tier 1}, {year: 400% FPL}) from the brackets rows, which are
    in today's dollars; nominal multiplies by the year's deflator where the result has it."""
    deflators = {int(r["year"]): float(r["deflator"]) for r in by_year if r.get("deflator")}
    nominal = units == "nominal" and has_deflator(by_year)
    magi, irmaa, fpl = {}, {}, {}
    for row in brackets_years or []:
        year = int(row["year"])
        k = deflators.get(year, 1.0) if nominal else 1.0
        if row.get("magi") is not None:
            magi[year] = float(row["magi"]) * k
        tiers = [e for e in row.get("irmaa_edges") or [] if e.get("amount") is not None]
        if tiers:
            irmaa[year] = float(min(e["amount"] for e in tiers)) * k
        lines = [e for e in row.get("aca_lines") or [] if "400%" in str(e.get("label")) and e.get("amount")]
        if lines:
            fpl[year] = float(lines[0]["amount"]) * k
    return magi, irmaa, fpl


def magi_units(by_year, units: str) -> str:
    """The MAGI chart's units: the brackets rows are in today's dollars, so nominal needs the
    deflator."""
    return "nominal" if units == "nominal" and has_deflator(by_year) else "today"


def compare_figure(chart: str, a: dict, b: dict, names=("A", "B"), diff: bool = False, axis: str = "",
                   lines_a=(), lines_b=()):
    """One side-by-side chart: A and B overlaid by calendar year, or B - A (`diff`) over the
    years both have. `lines_*` are (label, {year: value}) threshold lines drawn under A / B."""
    fig = go.Figure()
    years = sorted(set(a) | set(b))
    if diff:
        both = [y for y in years if y in a and y in b]
        fig.add_trace(go.Bar(x=both, y=[b[y] - a[y] for y in both], name=f"{names[1]} - {names[0]}"))
    else:
        for series, name, dash in ((a, names[0], "solid"), (b, names[1], "dash")):
            fig.add_trace(go.Scatter(x=years, y=[series.get(y) for y in years], name=name,
                                     line=dict(width=2.5, dash=dash)))
        for lines, dash in ((lines_a, "dot"), (lines_b, "dashdot")):
            for label, values in lines:
                if values:
                    fig.add_trace(go.Scatter(x=years, y=[values.get(y) for y in years], name=label,
                                             line=dict(width=1, dash=dash, shape="hv",
                                                       color=_IRMAA if "IRMAA" in label else _ACA)))
    fig.update_layout(yaxis_title=axis, xaxis_title="Year", height=340, title=chart)
    return fig

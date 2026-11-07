"""
The Run page's "why" views as figures and words, without Streamlit (UX review Q15-Q17).

- `brackets_figure` / `brackets_table`: income, the Roth conversion layer and MAGI against the
  ordinary bracket tops (faint steps, one per bracket), every IRMAA tier with its premium year,
  and the marketplace's 400% FPL line, in distinct hues and dashes (Q15).
- `taxes_and_premiums_figure`, `income_sources_figure`: the taxes with the Medicare and
  marketplace premiums beside them; the income sources with all-zero series left out and a
  big-ticket purchase year annotated instead of setting the scale (Q16).
- `year_breakdown`, `year_summary`, `sankey_figure`: one year's sources and uses grouped as
  the paragraph above the Sankey tells them, and the Sankey drawn from the same groups, with
  the amounts on the nodes, a labelled hub and a taxes total (Q17).

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


def brackets_table(years) -> pd.DataFrame:
    """The table under the chart: numbers as numbers (the page formats them), no index."""
    taxable_conv = _taxable_conversions(years)
    rows = []
    for row, part in zip(years, taxable_conv, strict=True):
        tier1 = (row.get("irmaa_edges") or [{}])[0]
        rows.append({
            "Year": row["year"],
            "Taxable income": row.get("ordinary_taxable_income"),
            "Conversions": row.get("conversion"),
            "Of which taxable": part,
            "MAGI": row.get("magi"),
            "Bracket": row.get("fills_bracket") or "-",
            "Room to its top": row.get("room_to_next_edge"),
            "IRMAA tier 1": tier1.get("amount"),
            "Sets premiums of": tier1.get("premium_year"),
            "400% FPL": _cliff(row),
        })
    table = pd.DataFrame(rows)
    # Years as nullable integers and amounts as whole-dollar floats: a None left in a column
    # made it an object column that the page showed as "None", and years as floats.
    for column in ("Year", "Sets premiums of"):
        table[column] = pd.to_numeric(table[column], errors="coerce").round().astype("Int64")
    for column in table.columns:
        if column not in ("Year", "Sets premiums of", "Bracket"):
            table[column] = pd.to_numeric(table[column], errors="coerce").astype(float).round(0)
    return table


# -- Q16: taxes and premiums, income sources ---------------------------------------------------

TAX_SERIES = (("federal_income_tax", "Federal income tax"), ("ltcg_tax", "Gains tax"), ("niit", "NIIT"),
              ("payroll_tax", "Payroll tax"), ("state_tax", "State + local"))
PREMIUM_SERIES = (("medicare_premiums", "Medicare premiums (with IRMAA)"),
                  ("aca_premiums", "Marketplace premiums"))
INCOME_SERIES = (("wages", "Wages"), ("ss", "Social Security"), ("pension_income", "Pensions"),
                 ("spia_income", "SPIAs"), ("portfolio_withdrawals", "Withdrawals from savings"))


def _series(by_year, key):
    if key == "ss":
        return [sum(row.get("ss_income") or []) for row in by_year]
    return [row.get(key) or 0.0 for row in by_year]


def taxes_and_premiums_figure(by_year):
    """Taxes stacked, the health premiums as their own (hatched) series on the same stack."""
    years = [row["year"] for row in by_year]
    fig = go.Figure()
    for key, label in TAX_SERIES:
        fig.add_trace(go.Bar(x=years, y=_series(by_year, key), name=label))
    for key, label in PREMIUM_SERIES:
        values = _series(by_year, key)
        if any(values):
            fig.add_trace(go.Bar(x=years, y=values, name=label, marker_pattern_shape="/"))
    fig.update_layout(barmode="stack", yaxis_title=NOMINAL_PER_YEAR, xaxis_title="Year", height=340)
    return fig


def big_ticket_years(cash_flow: dict) -> dict:
    """{year index: amount} of the big-ticket purchases (plan.json's `cash_flow` uses)."""
    values = ((cash_flow or {}).get("uses") or {}).get("Big-ticket purchases") or []
    return {n: float(v) for n, v in enumerate(values) if v and float(v) > 0.5}


def income_sources_figure(by_year, purchases=None):
    """Income sources stacked, all-zero series left out. A big-ticket purchase year whose bar
    would set the scale (twice the other years' highest or more) runs off the top of the chart
    with its amount written on it (Q16)."""
    years = [row["year"] for row in by_year]
    fig = go.Figure()
    totals = [0.0] * len(years)
    for key, label in INCOME_SERIES:
        values = _series(by_year, key)
        if not any(values):
            continue
        totals = [t + (v or 0.0) for t, v in zip(totals, values, strict=True)]
        fig.add_trace(go.Bar(x=years, y=values, name=label))
    fig.update_layout(barmode="stack", yaxis_title=NOMINAL_PER_YEAR, xaxis_title="Year", height=340)
    purchases = purchases or {}
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

TAX_USES = {"Federal income tax": "federal income tax", "Gains tax": "capital gains",
            "NIIT": "NIIT", "Payroll tax": "payroll tax", "State and local tax": "state and local"}
PREMIUM_USES = {"ACA premiums": "marketplace", "Medicare premiums": "Medicare"}
SAVINGS_SOURCES = {"Taxable-account withdrawals": "the taxable (brokerage) accounts",
                   "Tax-deferred withdrawals": "the tax-deferred accounts (IRAs)",
                   "Roth withdrawals": "the Roth accounts", "HSA withdrawals": "the HSAs"}
INCOME_WORDS = {"Wages": "wages", "Pensions": "pensions", "Other income": "other income",
                "Fixed-asset income": "fixed-asset income", "Fixed-asset sale": "a fixed-asset sale",
                "Big-ticket inflows": "big-ticket inflows", "Net investment income": "net investment income"}
CONVERSION_SOURCE = "Roth conversions (from the tax-deferred accounts)"
_USE_GROUPS = (("spending", "Spending"), ("big_ticket", "Big-ticket purchases"),
               ("debt", "Debt payments"), ("taxes", "Taxes"), ("premiums", "Health premiums"),
               ("conversions", "Roth conversions"), ("surplus", "Back into savings"),
               ("other", "Other outflows"))
_SOURCE_GROUPS = (("savings", "From savings"), ("income", "Income"), ("conversions", "Roth conversions"))


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


def _parts(rows: dict, words: dict | None = None) -> str:
    items = sorted(rows.items(), key=lambda kv: -kv[1])
    return ", ".join(f"{(words or {}).get(k, k)} {_usd(v)}" for k, v in items)


def year_summary(year: int, sources: dict, uses: dict) -> str:
    """The paragraph above the Sankey (UX review section 3), in nominal dollars of *year*,
    from the same rows the Sankey draws."""
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
        text.append(f"The money comes from savings, {_usd(savings)} ({_parts(s['savings'], SAVINGS_SOURCES)}), "
                    f"and from income, {_usd(income)} ({_parts(s['income'], INCOME_WORDS)}).")
    elif savings:
        text.append(f"All of it comes from savings: {_parts(s['savings'], SAVINGS_SOURCES)}.")
    elif income:
        text.append(f"All of it comes from income: {_parts(s['income'], INCOME_WORDS)}.")
    taxes = dict(u["taxes"])
    taxes.setdefault("Federal income tax", 0.0)  # "federal income tax $0" is worth saying
    if total(taxes):
        text.append(f"Taxes {_usd(total(taxes))}: {_parts(taxes, TAX_USES)}.")
    else:
        text.append("No taxes.")
    if u["premiums"]:
        text.append(f"Health premiums {_usd(total(u['premiums']))} ({_parts(u['premiums'], PREMIUM_USES)}).")
    if u["conversions"]:
        text.append(f"A Roth conversion of {_usd(total(u['conversions']))} moves money from the tax-deferred "
                    "accounts to the Roth accounts: it is on both sides.")
    if u["surplus"]:
        text.append(f"{_usd(total(u['surplus']))} goes back into savings.")
    if u["other"]:
        text.append(f"Other outflows {_usd(total(u['other']))} ({_parts(u['other'])}).")
    return " ".join(text)


def sankey_figure(year: int, sources: dict, uses: dict):
    """Sources → the year's hub → the use groups → their lines, amounts on every node.

    A group of one line goes straight from the hub; Spending, Taxes and Health premiums with
    several lines get a node of their own carrying the group's total (Q17: the taxes were five
    nodes with no total)."""
    b = year_breakdown(sources, uses)
    labels, colors = [], []
    src, tgt, val = [], [], []

    def node(label, value, color):
        labels.append(f"{label}: ${value:,.0f}")
        colors.append(color)
        return len(labels) - 1

    total = sum(sources.values())
    in_nodes = [(node(name, v, "#4c78a8"), v) for name, v in sources.items()]
    hub = node(f"{year} cash flow", total, "#555555")
    for i, v in in_nodes:
        src.append(i)
        tgt.append(hub)
        val.append(v)
    for group, title in _USE_GROUPS:
        rows = b["uses"][group]
        if not rows:
            continue
        if len(rows) == 1:
            (name, v), = rows.items()
            src.append(hub)
            tgt.append(node(name, v, "#f58518"))
            val.append(v)
            continue
        g = node(title, sum(rows.values()), "#e45756" if group == "taxes" else "#f58518")
        src.append(hub)
        tgt.append(g)
        val.append(sum(rows.values()))
        for name, v in sorted(rows.items(), key=lambda kv: -kv[1]):
            src.append(g)
            tgt.append(node(name, v, "#ffbb78"))
            val.append(v)
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=colors, pad=14, thickness=14),
        link=dict(source=src, target=tgt, value=val, color="rgba(160, 160, 160, 0.35)",
                  hovertemplate="%{source.label} → %{target.label}<extra></extra>"),
    ))
    fig.update_layout(height=max(460, 24 * len(labels)), font=dict(size=11))
    return fig

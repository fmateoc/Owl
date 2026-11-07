"""
Run page for the run library (run-library-design.md, section 9.1).

One run, one of its solves at a time: the header (name, change summary, parent, solve date
and method, status, and a plain-language quality line), the headline numbers (the score as
`run_suite.py` computes it, the home at the end and the savings left -- two numbers, never
added, R3 -- total taxes, the claiming ages, SS withheld), "Things to look at" (the years
whose income sits just below or just over a threshold, design 14.1 I3), charts drawn from
`plan.json` (durable; D7) including the one-year cash-flow Sankey (I6), the Results
workbook's sheets, the conversion and bracket view (I8: taxable income, the Roth
conversion layer and the bracket, IRMAA and ACA lines, with the per-request regret
sweep), the sensitivity tornado (I9: one child per key input moved by a set
step, solved under the exact LP -- the medical-inflation child with Medicare priced exactly,
review AJ1 -- the effects sorted into bars with their tolerances), the
claiming-age map over a work_sweep scores file (I7), and the
buttons: "Open in Owl" (the existing pages from the cached `plan.pkl`, no solve),
"Download everything" (a zip of the run), "Edit as new run" (the run's frozen files into
the case pages; saving makes a child run) and "Edit the scenario" (the run's events on the
Scenario page; step 4).

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

from io import BytesIO, StringIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import libraryjobs
import librarypresets
import run_charts
import sskeys as kz
from owlplanner.library import JobsError, ScenarioError, agemap, load_plan, preset_solves
from owlplanner.library import results as R
from owlplanner.library import grid, tornado, view

st.markdown("# :material/monitoring: Run")
kz.divider("orange")
libraryjobs.show_flashes()  # what the last action said before its rerun (review 3, W3)

# The four by-year charts read plan.json's `by_year`, which is in nominal dollars (each year's
# own); plan.json carries no deflator, so the axes say so (UX review Q6).
NOMINAL_PER_YEAR = "nominal $ per year"


def _frozen_solver_options(run) -> dict:
    """The `[solver_options]` of the run's frozen Case.toml (what its events generated
    included), or {} when it cannot be read."""
    import tomllib

    try:
        with open(run.path / "inputs" / "Case.toml", "rb") as fh:
            return tomllib.load(fh).get("solver_options") or {}
    except (OSError, ValueError):
        return {}


def _usd(value):
    """A metric's value: plain text (st.metric is not markdown), "-" when there is none."""
    return "-" if value is None else f"{value:,.0f}"


def _things_to_look_at(result):
    """I3: the years just below or just over a threshold the model knows (plan.json)."""
    entries = view.thresholds(result)
    if not entries:
        return
    st.markdown("### Things to look at")
    band = view.threshold_band(result)
    st.caption(
        f"Years whose income sits within {100 * band:.0f}% of a threshold the model knows "
        "(today's dollars). *Cost* is what closing that gap costs where the model prices the "
        "crossing; empty where the boundary is a ramp. The plan may be parked at a boundary on "
        "purpose (the optimizer fills a bracket to its edge): read this as a list of margins, "
        "not of errors."
    )
    rows = [{
        "Year": e["year"],
        "Threshold": e["label"],
        "Side": e["side"],
        "Amount ($)": round(e["amount_today_dollars"]),
        "Cost ($)": None if e.get("cost_today_dollars") is None else round(e["cost_today_dollars"]),
        "Affects": e.get("affects") or "-",
        "Note": e.get("note") or "",
    } for e in entries]
    money = st.column_config.NumberColumn(format="localized")  # thousands separators (Q6)
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True,
                 # "%d", not "plain": Streamlit 1.66 shows 2028 as 2027.9999999999998 in "plain".
                 column_config={"Year": st.column_config.NumberColumn(format="%d"),
                                "Amount ($)": money, "Cost ($)": money,
                                "Affects": st.column_config.TextColumn()})


def _cash_flow_sankey(result, by_year):
    """I6: one year's sources and uses as a paragraph and a Sankey (plan.json's `cash_flow`,
    nominal $; `run_charts.year_summary` / `sankey_figure`, UX review Q17)."""
    cf = view.cash_flow(result)
    if not (cf.get("sources") and cf.get("uses")) or not by_year:
        st.caption("This solve's files carry no cash-flow detail (solved before this build).")
        return
    years = [row["year"] for row in by_year]

    # Default to the purchase year, then the first Medicare year (the design's two uses).
    default = 0
    for n in range(len(years)):
        if view.cash_flow_year(result, n)[1].get("Big-ticket purchases", 0) > 0:
            default = n
            break
    else:
        for n in range(len(years)):
            if view.cash_flow_year(result, n)[1].get("Medicare premiums", 0) > 0:
                default = n
                break
    n = st.selectbox("Year", list(range(len(years))), index=default,
                     format_func=lambda i: str(years[i]), key="run_page_cash_flow_year")
    # Signed rows land on the side they flow to (a STAR refund is money in, review 3 W1).
    sources, uses = view.cash_flow_year(result, n)
    if not sources or not uses:
        st.caption(f"{years[n]}: nothing to show.")
        return

    # UX review Q17: the year in words first, from the very rows the Sankey draws; then the
    # Sankey with the amounts on its nodes, a labelled hub and the taxes' total.
    st.markdown(run_charts.year_summary(years[n], sources, uses))
    st.plotly_chart(run_charts.sankey_figure(years[n], sources, uses), width="stretch")
    st.caption(
        f"{years[n]}: \\${sum(sources.values()):,.0f} in, \\${sum(uses.values()):,.0f} out (nominal "
        "dollars of that year; the two differ only by rounding). A Roth conversion is a move between "
        "accounts: it appears on both sides. A tax that comes out negative (a refundable "
        "credit larger than the tax, such as STAR) is money in: it is drawn as a source. "
        "Spending is split along the budget's lines when the case has a budget sheet."
    )


def _age_map_chart(amap):
    """I7: the objective over the free claiming ages, ties within tolerance shaded together."""
    if amap.dimensions == 0:
        # A work_sweep row with fixed claiming ages scores the decided plan and sweeps
        # nothing (its cells carry no age tuples): there is no axis to draw (review 2, Q3).
        st.caption("This work variant swept no claiming ages (they are fixed): nothing to draw.")
        return
    groups = amap.tie_groups()
    shades = amap.group_of()
    best = amap.best()
    tied = len(groups[0]) if groups else 0
    st.caption(
        f"{len(amap.cells)} scored plan(s); {len(groups)} shade(s); the best "
        f"{best.value:,.0f} is tied (within {max(c.tolerance for c in groups[0]):,.0f}) with "
        f"{tied} cell(s). Cells this sweep did not score are blank."
    )
    if amap.dimensions > 1:
        xs, ys = amap.x_ages(), amap.y_ages()
        xi = {m: i for i, m in enumerate(xs)}
        yi = {m: i for i, m in enumerate(ys)}
        z = [[float("nan")] * len(xs) for _ in ys]
        text = [[""] * len(xs) for _ in ys]
        for cell in amap.cells:
            j, i = yi.get(cell.ages[1]), xi.get(cell.ages[0])
            if i is None or j is None:
                continue
            z[j][i] = shades[cell.ages]
            text[j][i] = f"{cell.value:,.0f}"
        fig = go.Figure(go.Heatmap(
            z=z, text=text, texttemplate="%{text}", x=[view.age_text(m / 12) for m in xs],
            y=[view.age_text(m / 12) for m in ys], colorscale="Greens_r", showscale=False,
            xgap=2, ygap=2,
            hovertemplate="%{x} · %{y}<br>objective %{text}<extra></extra>",
        ))
        if amap.decided and len(amap.decided) > 1:
            fig.add_trace(go.Scatter(
                x=[view.age_text(amap.decided[0] / 12)], y=[view.age_text(amap.decided[1] / 12)],
                mode="markers", name="decided",
                marker=dict(size=14, color="#d62728", symbol="circle-open", line=dict(width=3)),
            ))
        fig.update_layout(height=380, xaxis_title=amap.free[0], yaxis_title=amap.free[1])
        st.plotly_chart(fig, width="stretch")
    else:
        pts = sorted(amap.cells, key=lambda c: c.ages)
        fig = go.Figure(go.Scatter(x=[view.age_text(c.ages[0] / 12) for c in pts],
                                   y=[c.value for c in pts], mode="lines+markers",
                                   name="objective"))
        fig.update_layout(height=320, xaxis_title=amap.free[0], yaxis_title="objective")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(pd.DataFrame([{"Age": view.age_text(c.ages[0] / 12), "Objective": round(c.value),
                                    "Tolerance": round(c.tolerance)} for c in pts]),
                     width="stretch", hide_index=True)


def _claiming_age_map(run):
    """I7: the heat map over a work_sweep scores file (the run's, or one the user picks)."""
    st.markdown("### Claiming-age map")
    st.caption(
        "What each pair of claiming ages is worth for one work variant: cells tied within the "
        "solves' tolerance share a shade, the darkest being the best. The scores come from the "
        "*Claiming ages, every pair tried* preset (an expert preset), which keeps them with its "
        "solve; *Let Owl choose the claiming ages* tries only its pick and the neighbouring "
        "years, so it gives no map."
    )
    maps = None
    found = None
    note = ""
    scores_path = run.path / "scores.json"
    if scores_path.exists():
        found, note = scores_path, "Reading the claiming-age scores kept in the run's folder."
    else:
        # "Ages, thorough" writes its sweep with the solve (its results folder; I7).
        results = run.path / "results"
        # Only a folder whose solve finished (review AH6: a folder's sweep must be its record's).
        mine = sorted((p for p in results.glob(f"*/{R.SCORES_JSON}")
                       if ((R.read_record(p.parent) or {}).get("status")) == "solved"),
                      reverse=True) if results.is_dir() else []
        if mine:
            found = mine[0]
            note = (f"Reading the claiming-age scores of the solve of {found.parent.name} (the "
                    "newest *Claiming ages, every pair tried* solve).")
    if found is not None:
        try:
            maps = agemap.load_scores(found)
            st.caption(note)
        except Exception as exc:  # noqa: BLE001 - shown, not raised
            st.warning(f"{found.name} could not be read: {exc}")
    if maps is None:
        up = st.file_uploader("A claiming-age scores file", type=["json"], key="run_page_scores",
                              help="The scores file the claiming-age sweep writes (`scores.json`, "
                                   "or `work_sweep.py --json` from the command line).")
        if up is not None:
            try:
                maps = agemap.load_scores(up.getvalue())
            except Exception as exc:  # noqa: BLE001 - shown, not raised
                st.error(f"Not a claiming-age scores file: {exc}")
    if not maps:
        return
    names = {}
    for amap in maps:  # variant names repeat across suites; keep the first, label duplicates
        name = amap.name if amap.name not in names else f"{amap.name} ({len(names)})"
        names[name] = amap
    amap = names[st.selectbox("Work variant", list(names), key="run_page_age_variant")]
    if not amap.cells:
        st.caption("This variant has no scored claiming ages.")
        return
    _age_map_chart(amap)


manager = libraryjobs.get_manager()
lib = manager.library

runs = list(reversed(lib.runs()))
if not runs:
    st.info("The library has no runs yet.")
    st.stop()

# -- the conversion and bracket view (design 14.1, I8) -----------------


def _conversions_and_brackets(run, result):
    """Per year: taxable income, the Roth conversion layer, and the lines it fills (I8).

    Reads `plan.json`'s `brackets` block (`owlplanner.brackets`, durable: D7). The chart
    (`run_charts.brackets_figure`) stacks the conversion on the ordinary taxable income and
    steps the lines the year is measured against: the ordinary bracket tops (income), every
    IRMAA tier and the marketplace's 400% FPL cliff (both against MAGI; UX review Q15: tier 1
    alone, a zigzag "top of the bracket" and two dotted greens before). Below it, the per-request regret
    sweep: what a different first-year conversion would have cost
    (`stresstests.run_conversion_regret_sweep`, one "regret" job per request).
    """
    doc = result.plan.get("brackets") or {}
    years = doc.get("years") or []
    if not years:
        return
    st.markdown("### Conversions and brackets")
    st.caption(
        "Ordinary taxable income per year (after the deduction), with the Roth conversion's "
        "taxable part as its top layer (today's \\$): a conversion the deduction absorbs is not "
        "taxable income, so the table gives the gross conversion beside its taxable part. The "
        "faint grey steps are the tops of the federal brackets, read against taxable income. "
        "The red dashed lines are the IRMAA tiers and the purple dash-dot line the marketplace's "
        "400% FPL cliff: both are read against **MAGI**, the black line, and a year's MAGI sets "
        "the Medicare premiums two years later (hover a tier for the year it sets). The "
        "conversions are optimized in the model -- IRMAA, ACA, SS taxability and state tax "
        "priced together -- so this view explains them.")
    fig, note = run_charts.brackets_figure(years)
    st.plotly_chart(fig, width="stretch")
    if note:
        st.caption(note)
    money = st.column_config.NumberColumn(format="localized")  # thousands separators (Q15)
    table = run_charts.brackets_table(years)
    st.dataframe(table, width="stretch", hide_index=True,
                 column_config={c: money for c in table.columns
                                if c not in ("Year", "Bracket", "Sets premiums of")}
                 | {"Year": st.column_config.NumberColumn(format="%d"),
                    "Sets premiums of": st.column_config.NumberColumn(format="%d")})

    # -- the regret sweep (I8: "what a different conversion would have cost") -----
    regret = result.record.get("regret")
    if regret is None:
        first = ((result.plan.get("individuals") or [None])[0])
        st.markdown("**What would a different conversion have cost?** A regret sweep "
                    "re-solves historical scenarios with this year's "
                    "conversion pinned on a grid and reports the regret of each commitment"
                    + (f" -- {first}'s conversion, the first person of the case"
                       if first else "") + ".")
        if st.button("Run the regret sweep", key="run_page_regret",
                     help="One solve per request (a background job, its own results): "
                          "\"Quick look\" size -- 18 historical scenarios, a 7-point grid."):
            try:
                manager.enqueue(run, preset="regret")
            except (ScenarioError, JobsError) as exc:  # another plan year (R1)
                libraryjobs.flash("error", f"Not queued: {exc}")
            else:
                libraryjobs.flash("success", "The regret sweep is queued (one solve per request).")
            st.rerun()
    elif regret.get("error"):
        st.warning(f"The regret sweep did not finish: {regret['error']}", icon=":material/warning:")
    else:
        st.markdown("**What a different conversion would have cost** "
                    + (f"-- {regret['person']}'s first-year conversion " if regret.get("person") else "")
                    + f"({regret.get('n_scenarios')} historical scenario(s))")
        # The summarizer's key is `regret_by_grid` (review AH4: `by_grid` drew nothing).
        by_grid = regret.get("regret_by_grid") or []
        if by_grid:
            fig = go.Figure(go.Scatter(
                x=[g["x"] / 1000.0 for g in by_grid],
                y=[g.get("mean") for g in by_grid],
                name="mean regret", line=dict(width=3)))
            fig.update_layout(xaxis_title="committed first-year conversion ($k)",
                              yaxis_title="mean regret (today's $)", height=320)
            st.plotly_chart(fig, width="stretch")
        valley = regret.get("valley") or {}
        whose = regret.get("person")
        if valley:
            # The summary's key is `mean_regret` (review AG7: `mean` always read 0).
            st.caption(f"Least regret: commit {valley.get('x', 0):,.0f} "
                       f"(mean regret {valley.get('mean_regret') or 0:,.0f})"
                       + (f", {whose}'s first-year conversion" if whose else "")
                       + "; the curves and the per-scenario spread are in the full summary "
                       "below (kept with this solve).")
        with st.expander("The full summary"):
            st.json(regret)


# -- pick a run and one of its solves ----------------------------------

labels = {f"{r.name}  ({r.folder_name})": r for r in runs}
# "Open" on the Library page names the run through the session. Consume it here and drive
# the selector explicitly: the widget's own key (`run_page_run`) otherwise keeps its old
# value and overrides `index`, and "Open" stops switching runs after the first render
# (step-3 review P2).
wanted = st.session_state.pop("library_selected_run", None)
if wanted is not None:
    for label, r in labels.items():
        if r.id == wanted:
            st.session_state["run_page_run"] = label
            break
run = labels[st.selectbox("Run", list(labels), key="run_page_run")]

entries = []  # newest solve first: (label, job, result)
for job in reversed(manager.jobs(run)):
    record = R.read_record(job.results_dir)
    if record is None:
        continue
    when = (record.get("solve_date") or {}).get("finished") or job.doc.get("queued") or ""
    label = (f"{job.id} · {librarypresets.name(record.get('preset') or job.doc.get('preset'))} · "
             f"{when[:10] or 'no solve'} · {record.get('status') or job.state}")
    entries.append((label, job, view.load_result(job.results_dir)))
if not entries:
    st.info("This run has no results yet: solve it below.")

# -- header -----------------------------------------------------------

st.markdown(f"## {run.name}")
st.caption(f"`{run.folder_name}` · plan year {run.plan_year or '?'} · "
           f"created {run.created[:10]}" + (f" · {', '.join(run.tags)}" if run.tags else ""))
if run.parent:
    parent = None
    try:
        parent = lib.get(run.parent).name
    except Exception:  # noqa: BLE001 - a deleted parent shows as deleted (section 7)
        parent = "a deleted run"
    st.markdown(f"From **{parent}**: {'; '.join(run.change_summary) or 'same inputs'}")
if run.notes:
    st.markdown(run.notes)

if entries:
    # A model companion (the exact LP, or the tornado's Medicare model, review AJ1) is a
    # check, not the headline (R2): default to the newest main solve, not to it.
    default_idx = next((i for i, e in enumerate(entries) if not view.is_companion(e[2])), 0)
    chosen = st.selectbox("Result", [e[0] for e in entries], index=default_idx,
                          key="run_page_result")
    job, result = next((e[1], e[2]) for e in entries if e[0] == chosen)
    record = result.record
    finished = (record.get("solve_date") or {}).get("finished") or ""
    st.markdown(f"**Solved** {finished[:16].replace('T', ' ') or job.state} · "
                f"{view.method_text(result)}")
    search = record.get("age_search")
    if search:
        decided = search.get("decided")
        if decided:
            # "Ages, thorough" (review AH1): the sweep's scorer, and the published plan re-solved
            # the same way; both values shown, so a gap between them is visible.
            how = ("local search" if decided.get("used") == "local search"
                   else "branch-and-bound at gap 1e-5")
            published = search.get("published_value")
            st.caption("Claiming ages searched (every pair tried): picked "
                       f"{view.claiming_ages_text(result)} from "
                       f"{len(search.get('candidates') or [])} whole-year pair(s), each scored "
                       f"at fixed ages by {how}; this plan is the decided cell "
                       "re-solved the same way"
                       + (f" (objective {published:,.2f}; the sweep's cell {decided['value']:,.2f})"
                          if published is not None and decided.get("value") is not None else "")
                       + ".")
        else:
            st.caption("Claiming ages chosen by Owl: picked "
                       f"{view.claiming_ages_text(result)} from "
                       f"{len(search.get('candidates') or [])} candidate(s), scored at fixed ages "
                       "under the case's own model.")
    if record.get("status") != "solved":
        st.error(f"This solve did not finish: {record.get('status') or job.state}"
                 + (f" ({record.get('error')})" if record.get("error") else ""),
                 icon=":material/error:")
    else:
        # Design 9.1's plain-language line. With problems, the caption only points at them:
        # echoing the first note there showed it twice (review 2, Q4).
        notes = view.quality_notes(result)
        st.caption("Quality: settled" if not notes
                   else f"Quality: {len(notes)} problem(s), below")
        for note in notes:
            st.warning(note, icon=":material/warning:")

    # -- headline numbers (design 9.1; run_suite.py's score rule) -------
    value = view.score(result)
    case_options = _frozen_solver_options(run)
    cols = st.columns(6)
    # The score's own words as its label (UX review Q7); under maxBequest it is the final
    # bequest, and the savings left is the number differences are read on (view.first_number).
    _score_words = view.score_label(result)
    cols[0].metric(_score_words[:1].upper() + _score_words[1:], _usd(value),
                   help="The score: the number the solve maximizes, today's dollars.")
    cols[1].metric("Home at the end", _usd(view.home_at_end(result)),
                   help="The home net of commission and of any loan still owed: the reserve "
                        "for care, today's dollars. Never added to the savings.")
    _spent = view.spent_down_by_design(result, case_options.get("bequest"))
    cols[2].metric("Savings left", _usd(view.savings_left(result)),
                   delta="spent down by design" if _spent else None, delta_color="off",
                   delta_arrow="off",
                   help="After the heirs' tax, today's dollars."
                        + (" The case asks for no bequest, so the plan spends its savings by the "
                           "end: zero here is the goal." if _spent else ""))
    cols[3].metric("Total taxes", _usd(view.total_taxes_today(result)),
                   help="Income, gains, NIIT, payroll and state, over the plan (today's $).")
    cols[4].markdown("**Claiming ages**  \n"
                     + (view.claiming_ages_phrase(result, case_options.get("withSSAges")) or "-"))
    withheld = view.ss_withheld_today(result)
    cols[5].markdown("**SS withheld by the earnings test**  \n"
                     + (f"\\${withheld:,.0f}" if withheld is not None else "-"))
    st.caption(view.score_label(result)
               + " is the score; the two end-of-plan numbers are reported side by side and "
                 "never added together.")

    # -- "Things to look at" (design 14.1, I3) --------------------------
    _things_to_look_at(result)

    # -- charts from plan.json (D7) ------------------------------------
    by_year = result.plan.get("by_year") or []
    if by_year:
        years = [row["year"] for row in by_year]
        tabs = st.tabs(["Spending", "Account balances", "Taxes and premiums", "Income sources",
                        "Cash flow (one year)"])
        with tabs[0]:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=[row.get("spending") for row in by_year],
                                     name="Spending", line=dict(width=3)))
            fig.update_layout(yaxis_title=NOMINAL_PER_YEAR, xaxis_title="Year", height=320)
            st.plotly_chart(fig, width="stretch")
        with tabs[1]:
            fig = go.Figure()
            for key, label in (("portfolio_total", "Savings accounts"),
                               ("fixed_assets", "Fixed assets"), ("debt", "Debt"),
                               ("net_worth", "Net worth")):
                fig.add_trace(go.Scatter(x=years, y=[row.get(key) for row in by_year], name=label))
            fig.update_layout(yaxis_title="nominal $", xaxis_title="Year", height=320)
            st.plotly_chart(fig, width="stretch")
        with tabs[2]:
            # UX review Q16: the Medicare (IRMAA included) and marketplace premiums beside the
            # taxes; they were in plan.json and on no chart.
            st.plotly_chart(run_charts.taxes_and_premiums_figure(by_year), width="stretch")
        with tabs[3]:
            # Q16: all-zero series left out; a purchase year runs off the top, annotated.
            purchases = run_charts.big_ticket_years(view.cash_flow(result))
            st.plotly_chart(run_charts.income_sources_figure(by_year, purchases), width="stretch")
            if purchases:
                st.caption("A year with a big-ticket purchase (from the cash flow's uses) is drawn "
                           "off the top of the chart, its total written on it, so that it does not "
                           "set the scale for the other years.")
        with tabs[4]:
            _cash_flow_sankey(result, by_year)

    # -- conversions and brackets (design 14.1, I8) ----------------------
    _conversions_and_brackets(run, result)

    # -- the workbook's sheets -----------------------------------------
    xlsx = job.results_dir / R.RESULTS_XLSX
    if xlsx.exists():
        with st.expander("Results workbook"):
            sheets = pd.read_excel(BytesIO(xlsx.read_bytes()), sheet_name=None)
            sheet = st.selectbox("Sheet", list(sheets), key="run_page_sheet")
            st.dataframe(sheets[sheet], width="stretch")
    else:
        st.caption("The Results workbook is gone from this folder; solve again to get it.")

    # -- buttons -------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Open in Owl", type="primary", use_container_width=True,
                     help="The existing pages (Graphs, Worksheets, Reports) from the cached "
                          "plan, with no solve."):
            plan = load_plan(job.results_dir, record)
            if plan is None:
                st.info("The cached plan of this solve is gone (or the code changed since it "
                        "was written): solve the run again to open it in the pages.")
            else:
                name = kz.openCaseFromPlan(plan, name=f"{run.name} {job.id[:16]}")
                if name:
                    st.toast(f"Opened as case *{name}*; see the Results section.")
    with col2:
        try:
            blob = libraryjobs.run_zip_bytes(run)
        except Exception as exc:  # noqa: BLE001 - shown, not raised (a run being re-queued, P5)
            st.caption(f"zip unavailable: {exc}")
        else:
            st.download_button("Download everything", data=blob,
                               file_name=f"{run.folder_name}.zip", use_container_width=True,
                               help="A zip of the run folder: inputs, results, records and logs.")
    with col3:
        if st.button("Edit as new run", use_container_width=True,
                     help="Opens the run's frozen files in the case pages. Edit there and "
                          "save on the Library page: a new run, with this one as its parent."):
            case_path = run.path / "inputs" / "Case.toml"
            if kz.createCaseFromFile(StringIO(case_path.read_text(encoding="utf-8"))):
                hfp = run.path / "inputs" / "HFP.xlsx"
                if hfp.exists():
                    import owlbridge as owb

                    owb.readHFP(BytesIO(hfp.read_bytes()), file="HFP.xlsx")
                kz.setRunBase(run.id)  # saved on the Library page as its child
                # Review AL2: a run's case is complete, as after "Open in Owl" (Q12); the
                # progress strip on Run Options read "(25%) - Step 2 of 8".
                import case_progress

                kz.storeCaseKey("case_setup_visited_pages", case_progress.all_setup_pages())
                # UX review Q13: go where the what-if is made. A toast does not survive the
                # page switch; the flash is drawn under Run Options' title bar (sskeys.titleBar).
                libraryjobs.flash(
                    "info",
                    f"The inputs of *{run.name}* are open as the case **{kz.currentCaseName()}**. "
                    "Change them here or on any Case Setup page, then save them on the Library "
                    f"page (*Save the current case*): a new run, with *{run.name}* as its parent.")
                st.switch_page("Run_Options.py")
    with col4:
        if st.button("Edit the scenario", use_container_width=True,
                     help="The run's events (work, claiming, rent, a home purchase, care) on "
                          "the Scenario page, with what each one puts into the case."):
            st.session_state["library_selected_run"] = run.id
            st.switch_page("Scenario.py")

# -- solve this run ----------------------------------------------------

with st.expander("Solve this run"):
    preset = librarypresets.select("Preset", "run_page_preset")
    if st.button("Solve", type="primary"):
        for solve in preset_solves(preset):
            try:
                job = manager.enqueue(run, preset=solve)
            except (ScenarioError, JobsError) as exc:  # a run from another plan year (R1)
                # Shown after the rerun below (review 3, W3: an st.error here vanished).
                libraryjobs.flash("error", f"Not queued: {exc}")
                break
            st.toast(f"Queued {job.id} ({solve})")
        st.rerun()

# -- the sensitivity tornado (design 14.1, I9) --------------------------


def _tornado_collection(run):
    """The collection the sensitivity runs live in (created on first use): one child per
    mover, queued under the exact LP, "run the collection again" re-solves them all. The run
    itself is a member and the reference (review AG5: the grid's cells are differences from
    it, as the bars are). Found by the run's id, never by its name (review AI3)."""
    coll = tornado.collection_of(lib, run.id)
    if coll is None:
        coll = lib.create_collection(
            f"Sensitivity: {run.name}",
            question=f"What moves {run.name}'s score? (one key input at a time)",
            rule="each child re-solved under the exact LP, against this run's own exact-LP "
                 "solve; bars sorted by effect, each with its tolerance",
            tornado_of=run.id)
    if coll.member(run.id) is None:
        lib.add_member(coll.id, run, {"mover": tornado.BASE_LABEL})
    if coll.reference is None:
        lib.set_reference(coll.id, run)
    return lib.collection(coll.id)


def _live_companion_solves():
    """(run id, preset) of every model-companion solve waiting or running (review AI3: not
    queued twice; review AJ1: the medical-inflation pair solves under its own preset)."""
    return {(str(j.doc.get("run_id")), str(j.doc.get("preset"))) for j in manager.jobs()
            if j.state in (R.WAITING, R.RUNNING)
            and j.doc.get("preset") in (tornado.EXACT_PRESET, tornado.MEDICARE_PRESET)}


def _queue_unless_current(target, preset, live):
    """Queue `target` under `preset` unless that solve is queued, running, or was solved today
    by the code running now (review AI3). Returns "queued", "current" or an error message."""
    if (target.id, preset) in live or tornado.is_current(target.path, preset=preset):
        return "current"
    try:
        manager.enqueue(target, preset=preset)
    except (ScenarioError, JobsError) as exc:  # another plan year (R1)
        return str(exc)
    return "queued"


with st.expander("Sensitivity (tornado)"):
    st.caption(
        "One child run per key input moved by a set step: " +
        "; ".join(f"**{m.label}** ({m.note})" for m in tornado.movers(lib.scenario(run.id))) +
        ". Each child is solved under the exact LP (for speed) -- the medical-inflation child "
        "with Medicare priced exactly, since the exact LP has no Medicare premiums -- and "
        "measured against this run's own solve under the same model, which the button queues "
        "when the run has none; the bars below are sorted by the size of the effect, each with "
        "its tolerance (the noise rule), the home at the end beside it (the other number, never "
        "added). A mover that does not fit this scenario, or that no plan "
        "year would see, is skipped and says why. A solve already made today by this code, or "
        "queued, is not queued again. The runs land in the collection "
        f"*{getattr(tornado.collection_of(lib, run.id), 'name', None) or 'Sensitivity: ' + run.name}*."
    )
    if st.button("Make the sensitivity runs", type="primary", key="run_page_tornado"):
        made, skipped = tornado.tornado_variants(lib.scenario(run.id))
        for note in skipped:
            libraryjobs.flash("caption", f"Skipped {note}.")
        if not made:
            libraryjobs.flash("error", "No sensitivity run fits this scenario.")
            st.rerun()
        coll = _tornado_collection(run)
        queued, current = 0, 0
        live = _live_companion_solves()
        # The bars measure from this run's own result under each mover's model only (reviews
        # AG2, AJ1), queued unless it is already queued or was solved today by this code
        # (review AI3): the bars then compare solves of one day, the children's rule too.
        for preset in tornado.presets_needed(made):
            outcome = _queue_unless_current(run, preset, live)
            if outcome == "queued":
                queued += 1
            elif outcome != "current":
                libraryjobs.flash("error", f"{run.name}: its {preset} solve not queued ({outcome})")
        for variant in made:
            try:
                saved = lib.save_run(name=f"{run.name} {variant.label}",
                                     scenario=variant.scenario, parent=run.id)
            except Exception as exc:  # noqa: BLE001 - shown, not raised (a bad value, a locked library)
                libraryjobs.flash("error", f"{variant.label}: not saved ({exc})")
                continue
            child = saved.run if saved.created else saved.identical_to
            lib.add_member(coll.id, child, variant.values)
            outcome = _queue_unless_current(child, tornado.preset_of(variant), live)
            if outcome == "queued":
                queued += 1
            elif outcome == "current":
                current += 1  # solved today by this code, or queued (review AI3)
            else:
                libraryjobs.flash("error", f"{child.name}: not queued ({outcome})")
        libraryjobs.flash("success", f"{queued} sensitivity solve(s) queued"
                          + (f"; {current} already solved today or queued, not queued again."
                             if current else "."))
        st.rerun()
    _coll = tornado.collection_of(lib, run.id)  # by the run's id (review AI3)
    if _coll is not None:
        _bases = {p: tornado.base_result(run.path, p)
                  for p in (tornado.EXACT_PRESET, tornado.MEDICARE_PRESET)}
        _base = _bases[tornado.EXACT_PRESET]
        _rows = []
        for _member in _coll.members:
            if _member.run == run.id:
                continue  # the run itself: the base, not a bar
            _label = (_member.values or {}).get("mover") or "(no label)"
            try:
                _child = lib.get(_member.run)
            except Exception:  # noqa: BLE001 - a deleted child is shown, not fatal
                _rows.append((_label, None))
                continue
            _rows.append((_label, tornado.result_of(_child.path, tornado.preset_of(_label))))
        if all(b is None for b in _bases.values()):
            st.caption("The bars wait for this run's own exact-LP solve (the children's model; "
                       "\"Make the sensitivity runs\" queues it): another model's result would "
                       "put the model change into every bar.")
        elif any(result is not None for _label, result in _rows):
            _ref = _base or _bases[tornado.MEDICARE_PRESET]
            _what = view.first_number_label(_ref)
            _measured = [f"{'this run' if p == tornado.EXACT_PRESET else 'the medical-inflation bar'}"
                         f"'s {'exact-LP' if p == tornado.EXACT_PRESET else 'Medicare-priced'} solve, "
                         f"{view.first_number(b):,.0f}" for p, b in _bases.items() if b is not None]
            st.caption(f"Measured from {'; '.join(_measured)} ({_what}); claiming ages "
                       f"{view.claiming_ages_text(_ref)}.")
            _plain = grid.latest_result(run.path)
            if (_plain is not None and _plain.record.get("age_search")
                    and view.claiming_ages(_plain) != view.claiming_ages(_ref)):
                _last = librarypresets.name(_plain.record.get("preset"))
                st.warning(f"This run's last '{_last}' solve picked the claiming "
                           f"ages {view.claiming_ages_text(_plain)}; the sensitivity solves hold the "
                           f"case's own ({view.claiming_ages_text(_ref)}), so the bars do too.",
                           icon=":material/flag:")
            for _flag in tornado.bar_flags(_bases, _rows):
                st.warning(_flag, icon=":material/flag:")
            _bars = tornado.bars(_bases, _rows)
            _shown = [b for b in _bars if b["delta"] is not None]
            if _shown:
                fig = go.Figure(go.Bar(
                    y=[b["label"] for b in _shown][::-1],
                    x=[b["delta"] for b in _shown][::-1],
                    orientation="h",
                    error_x=dict(type="data", array=[b["tolerance"] or 0.0 for b in _shown][::-1],
                                 visible=True),
                    marker_color=["#c62828" if b["delta"] < 0 else "#2e7d32" for b in _shown][::-1],
                    customdata=[b.get("home_delta") or 0.0 for b in _shown][::-1],
                    hovertemplate="%{y}: %{x:+,.0f}; home at the end %{customdata:+,.0f}"
                                  "<extra></extra>",
                ))
                fig.update_layout(height=max(240, 40 * len(_shown) + 120),
                                  # Plotly shows text as is: no Markdown escape.
                                  xaxis_title="difference from this run: " + _what.replace("\\$", "$"),
                                  showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            # The home at the end beside the first number (review AI4: R3's other number,
            # never added; "condo price +10%" moves it by about the price change). Under
            # maxBequest the first number is the savings left (review AJ3).
            lines = ["| mover | difference | tolerance | verdict | home at the end | model |",
                     "|---|---:|---:|---|---:|---|"]
            for b in _bars:
                delta = f"{b['delta']:+,.0f}" if b["delta"] is not None else "-"
                tol = f"{b['tolerance']:,.0f}" if b["tolerance"] is not None else "-"
                home = b.get("home_delta")
                home = "-" if home is None else ("±0" if b.get("home_verdict") == "no difference"
                                                 else f"{home:+,.0f}")
                model = ("exact LP" if tornado.preset_of(b["label"]) == tornado.EXACT_PRESET
                         else "exact LP, Medicare priced exactly")
                lines.append(f"| {b['label']} | {delta} | ±{tol} | {b['verdict']}"
                             + (f" ({b['note']})" if b["note"] else "") + f" | {home} | {model} |")
            st.markdown("\n".join(lines))
        else:
            st.caption("No sensitivity result yet: the Queue page shows their progress "
                       "(each is one solve under the exact LP, the medical-inflation pair with "
                       "Medicare priced exactly).")

# -- the claiming-age map (design 14.1, I7) -----------------------------

_claiming_age_map(run)

st.caption(
    "A results folder is one solve of the run's frozen inputs. Plans start today: results "
    "from different days are flagged when compared."
)

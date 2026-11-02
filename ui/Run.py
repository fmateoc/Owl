"""
Run page for the run library (run-library-design.md, section 9.1).

One run, one of its solves at a time: the header (name, change summary, parent, solve date
and method, status, and a plain-language quality line), the headline numbers (the score as
`run_suite.py` computes it, the home at the end and the savings left -- two numbers, never
added, R3 -- total taxes, the claiming ages, SS withheld), "Things to look at" (the years
whose income sits just below or just over a threshold, design 14.1 I3), charts drawn from
`plan.json` (durable; D7) including the one-year cash-flow Sankey (I6), the Results
workbook's sheets, the claiming-age map over a work_sweep scores file (I7), and the
buttons: "Open in Owl" (the existing pages from the cached `plan.pkl`, no solve),
"Download everything" (a zip of the run) and "Edit as new run" (the run's frozen files into
the case pages; saving makes a child run).

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
import sskeys as kz
from owlplanner.library import PRESETS, ScenarioError, agemap, load_plan, preset_solves
from owlplanner.library import results as R
from owlplanner.library import view

st.markdown("# :material/monitoring: Run")
kz.divider("orange")

_PRESET_HELP = (
    "quick: the self-consistent loop for every tax family (no MIP, no local search), "
    "claiming ages held at the scenario's values. decision: local search with the ages held, "
    "plus its exact-model companion as a second result (the comparison's agreement check). "
    "custom: the case's own options."
)


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
        "crossing; '-' where the boundary is a ramp. The plan may be parked at a boundary on "
        "purpose (the optimizer fills a bracket to its edge): read this as a list of margins, "
        "not of errors."
    )
    rows = [{
        "Year": e["year"],
        "Threshold": e["label"],
        "Side": e["side"],
        "Amount ($)": round(e["amount_today_dollars"]),
        "Cost ($)": "-" if e.get("cost_today_dollars") is None else round(e["cost_today_dollars"]),
        "Affects": e.get("affects") or "-",
        "Note": e.get("note") or "",
    } for e in entries]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _cash_flow_sankey(result, by_year):
    """I6: one year's sources and uses as a Sankey (plan.json's `cash_flow`, nominal $)."""
    cf = view.cash_flow(result)
    sources_all = cf.get("sources") or {}
    uses_all = cf.get("uses") or {}
    if not sources_all or not by_year:
        st.caption("This solve's files carry no cash-flow detail (solved before this build).")
        return
    years = [row["year"] for row in by_year]

    def _at(rows, n):
        return {name: float(values[n]) for name, values in rows.items()
                if n < len(values) and values[n] > 0.5}

    # Default to the purchase year, then the first Medicare year (the design's two uses).
    default = 0
    for n in range(len(years)):
        if _at(uses_all, n).get("Big-ticket purchases", 0) > 0:
            default = n
            break
    else:
        for n in range(len(years)):
            if _at(uses_all, n).get("Medicare premiums", 0) > 0:
                default = n
                break
    n = st.selectbox("Year", list(range(len(years))), index=default,
                     format_func=lambda i: str(years[i]), key="run_page_cash_flow_year")
    sources = _at(sources_all, n)
    uses = _at(uses_all, n)
    if not sources or not uses:
        st.caption(f"{years[n]}: nothing to show.")
        return

    total = sum(sources.values())
    labels = list(sources) + [""] + list(uses)
    hub = len(sources)
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, pad=12, thickness=14,
                  color=["#4c78a8"] * len(sources) + ["#999999"] + ["#f58518"] * len(uses)),
        link=dict(
            source=list(range(len(sources))) + [hub] * len(uses),
            target=[hub] * len(sources) + [len(sources) + 1 + j for j in range(len(uses))],
            value=[sources[k] for k in sources] + [uses[k] for k in uses],
            label=[f"{k}: ${v:,.0f}" for k, v in sources.items()] + [f"{k}: ${v:,.0f}" for k, v in uses.items()],
            color=["#aec7e8"] * len(sources) + ["#ffbb78"] * len(uses),
        ),
    ))
    fig.update_layout(height=430, font=dict(size=11))
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"{years[n]}: ${total:,.0f} in, the same ${total:,.0f} out (nominal dollars of that "
        "year). A Roth conversion is a move between accounts: it appears on both sides. "
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
        "The objective over the free claiming ages of one work variant (work_sweep.py output, "
        "its --json file); cells tied within tolerance share a shade, the darkest being the "
        "best. `fork-notes/phase5/work_sweep.py` writes this file; the Ages presets come with "
        "step 6."
    )
    maps = None
    scores_path = run.path / "scores.json"
    if scores_path.exists():
        try:
            maps = agemap.load_scores(scores_path)
            st.caption("Reading `scores.json` from the run folder.")
        except Exception as exc:  # noqa: BLE001 - shown, not raised
            st.warning(f"scores.json in the run folder could not be read: {exc}")
    if maps is None:
        up = st.file_uploader("A work_sweep scores file", type=["json"], key="run_page_scores")
        if up is not None:
            try:
                maps = agemap.load_scores(up.getvalue())
            except Exception as exc:  # noqa: BLE001 - shown, not raised
                st.error(f"Not a work_sweep scores file: {exc}")
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
    label = (f"{job.id} · {record.get('preset') or job.doc.get('preset')} · "
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
    # The exact-model companion is a check, not the headline (R2): default to the newest
    # main solve, not to it.
    default_idx = next((i for i, e in enumerate(entries) if not view.is_exact_lp(e[2])), 0)
    chosen = st.selectbox("Result", [e[0] for e in entries], index=default_idx,
                          key="run_page_result")
    job, result = next((e[1], e[2]) for e in entries if e[0] == chosen)
    record = result.record
    finished = (record.get("solve_date") or {}).get("finished") or ""
    st.markdown(f"**Solved** {finished[:16].replace('T', ' ') or job.state} · "
                f"{view.method_text(result)}")
    if record.get("status") != "solved":
        st.error(f"This solve did not finish: {record.get('status') or job.state}"
                 + (f" ({record.get('error')})" if record.get("error") else ""),
                 icon=":material/error:")
    else:
        st.caption(f"Quality: {view.quality_line(result)}")  # design 9.1's plain-language line
        for note in view.quality_notes(result):
            st.warning(note, icon=":material/warning:")

    # -- headline numbers (design 9.1; run_suite.py's score rule) -------
    value = view.score(result)
    cols = st.columns(6)
    cols[0].metric("Score", _usd(value), help=view.score_label(result) + ", today's dollars.")
    cols[1].metric("Home at the end", _usd(view.home_at_end(result)),
                   help="The home net of commission and of any loan still owed: the reserve "
                        "for care, today's dollars. Never added to the savings (R3).")
    cols[2].metric("Savings left", _usd(view.savings_left(result)),
                   help="After the heirs' tax, today's dollars.")
    cols[3].metric("Total taxes", _usd(view.total_taxes_today(result)),
                   help="Income, gains, NIIT, payroll and state, over the plan (today's $).")
    cols[4].markdown(f"**Claiming ages**  \n{view.claiming_ages_text(result) or '-'}")
    withheld = view.ss_withheld_today(result)
    cols[5].markdown("**SS withheld by the earnings test**  \n"
                     + (f"\\${withheld:,.0f}" if withheld is not None else "-"))
    st.caption(view.score_label(result)
               + " is the score; the two end-of-plan numbers are reported side by side and "
                 "never added (R3).")

    # -- "Things to look at" (design 14.1, I3) --------------------------
    _things_to_look_at(result)

    # -- charts from plan.json (D7) ------------------------------------
    by_year = result.plan.get("by_year") or []
    if by_year:
        years = [row["year"] for row in by_year]
        tabs = st.tabs(["Spending", "Account balances", "Taxes by kind", "Income sources",
                        "Cash flow (one year)"])
        with tabs[0]:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=[row.get("spending") for row in by_year],
                                     name="Spending", line=dict(width=3)))
            fig.update_layout(yaxis_title="$ per year", xaxis_title="Year", height=320)
            st.plotly_chart(fig, width="stretch")
        with tabs[1]:
            fig = go.Figure()
            for key, label in (("portfolio_total", "Savings accounts"),
                               ("fixed_assets", "Fixed assets"), ("debt", "Debt"),
                               ("net_worth", "Net worth")):
                fig.add_trace(go.Scatter(x=years, y=[row.get(key) for row in by_year], name=label))
            fig.update_layout(yaxis_title="$", xaxis_title="Year", height=320)
            st.plotly_chart(fig, width="stretch")
        with tabs[2]:
            fig = go.Figure()
            for key, label in (("federal_income_tax", "Federal income tax"),
                               ("ltcg_tax", "Gains tax"), ("niit", "NIIT"),
                               ("payroll_tax", "Payroll tax"), ("state_tax", "State + local")):
                fig.add_trace(go.Bar(x=years, y=[row.get(key) for row in by_year], name=label))
            fig.update_layout(barmode="stack", yaxis_title="$ per year", xaxis_title="Year",
                              height=320)
            st.plotly_chart(fig, width="stretch")
        with tabs[3]:
            fig = go.Figure()
            for key, label in (("wages", "Wages"), ("ss", "Social Security"),
                               ("pension_income", "Pensions"), ("spia_income", "SPIAs"),
                               ("portfolio_withdrawals", "Withdrawals from savings")):
                values = ([sum(row.get("ss_income") or []) for row in by_year] if key == "ss"
                          else [row.get(key) for row in by_year])
                fig.add_trace(go.Bar(x=years, y=values, name=label))
            fig.update_layout(barmode="stack", yaxis_title="$ per year", xaxis_title="Year",
                              height=320)
            st.plotly_chart(fig, width="stretch")
        with tabs[4]:
            _cash_flow_sankey(result, by_year)

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
    col1, col2, col3 = st.columns(3)
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
                st.session_state["library_base_run_id"] = run.id
                st.toast("The run's inputs are open in the case pages (Create Case). "
                         "Save them as a new run on the Library page.")

# -- solve this run ----------------------------------------------------

with st.expander("Solve this run"):
    preset = st.selectbox("Preset", list(PRESETS), key="run_page_preset", help=_PRESET_HELP)
    if st.button("Solve", type="primary"):
        for solve in preset_solves(preset):
            try:
                job = manager.enqueue(run, preset=solve)
            except ScenarioError as exc:  # a run from another plan year (R1)
                st.error(str(exc), icon=":material/event_busy:")
                break
            st.toast(f"Queued {job.id} ({solve})")
        st.rerun()

# -- the claiming-age map (design 14.1, I7) -----------------------------

_claiming_age_map(run)

st.caption(
    "A results folder is one solve of the run's frozen inputs. Plans start today: results "
    "from different days are flagged when compared (design 8.3)."
)

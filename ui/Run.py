"""
Run page for the run library (run-library-design.md, section 9.1).

One run, one of its solves at a time: the header (name, change summary, parent, solve date
and method, status, and a plain-language quality line), the headline numbers (the score as
`run_suite.py` computes it, the home at the end and the savings left -- two numbers, never
added, R3 -- total taxes, the claiming ages, SS withheld), charts drawn from `plan.json`
(durable; D7), the Results workbook's sheets, and the buttons: "Open in Owl" (the existing
pages from the cached `plan.pkl`, no solve), "Download everything" (a zip of the run) and
"Edit as new run" (the run's frozen files into the case pages; saving makes a child run).

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
from owlplanner.library import PRESETS, ScenarioError, load_plan, preset_solves, run_zip
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


manager = libraryjobs.get_manager()
lib = manager.library

runs = list(reversed(lib.runs()))
if not runs:
    st.info("The library has no runs yet.")
    st.stop()

# -- pick a run and one of its solves ----------------------------------

labels = {f"{r.name}  ({r.folder_name})": r for r in runs}
wanted = st.session_state.get("library_selected_run")
default = next((label for label, r in labels.items() if r.id == wanted), next(iter(labels)))
run = labels[st.selectbox("Run", list(labels), index=list(labels).index(default),
                          key="run_page_run")]

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
    st.caption(f"Quality: {view.quality_line(result)}")  # design 9.1's plain-language line
    quality = view.quality_notes(result)
    if quality:
        for note in quality:
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

    # -- charts from plan.json (D7) ------------------------------------
    by_year = result.plan.get("by_year") or []
    if by_year:
        years = [row["year"] for row in by_year]
        tabs = st.tabs(["Spending", "Account balances", "Taxes by kind", "Income sources"])
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
        st.download_button("Download everything", data=run_zip(run),
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

st.caption(
    "A results folder is one solve of the run's frozen inputs. Plans start today: results "
    "from different days are flagged when compared (design 8.3)."
)

"""
Library page for the run library: the runs, and how new ones get in (design sections 5-7).

Every saved scenario is an immutable run folder (save-as only; D3). Runs come in here by
"Import a case" (an existing TOML + workbook, section 6.4) or by saving the case that is
open in the session's pages ("Save the current case as a new run"; the pages' own Save flow
lands here too, section 7). A solved run is never overwritten: editing opens the case pages
against the run ("Edit as new run" on the run page) and saving again is a new run whose
parent is the one opened.

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

import tempfile
from pathlib import Path

import streamlit as st

import libraryjobs
import sskeys as kz
from owlplanner.library import import_case, scenario_from_ui

st.markdown("# :material/database: Library")
kz.divider("orange")

manager = libraryjobs.get_manager()
lib = manager.library


def _run_name(rid):
    """A run's name, or None when it is gone (a deleted parent shows as deleted, section 7)."""
    try:
        return lib.get(rid).name
    except Exception:  # noqa: BLE001 - a deleted run is simply not there any more
        return None


def _report_saved(result):
    """Say what save_run did, including "identical to an existing run" (V8)."""
    if result.created:
        st.toast(f"Saved as **{result.run.name}** ({result.run.folder_name})")
    else:
        other = result.identical_to
        st.info(
            f"Identical to *{other.name}* ({other.folder_name}): not saved again. "
            "The run keeps its own inputs; the requested name, notes and tags were not applied."
            if other else "Not saved: identical inputs already in the library."
        )
        if result.dropped:
            st.caption(f"Not applied: {result.dropped}")


def _save_uploaded_run(name, notes, tags, uploaded):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        paths = {}
        for key, up in uploaded.items():
            if up is None:
                continue
            path = tmp / up.name
            path.write_bytes(up.getvalue())
            paths[key] = path
        try:
            scenario = import_case(paths["case"], hfp_path=paths.get("hfp"),
                                   budget_path=paths.get("budget"))
            result = lib.save_run(name=name or Path(paths["case"]).stem, scenario=scenario,
                                  notes=notes, tags=tuple(t for t in tags if t.strip()))
        except Exception as exc:  # noqa: BLE001 - shown to the user, not raised
            st.error(f"Cannot import this case: {exc}", icon=":material/error:")
            return
        _report_saved(result)


def _save_current_case(name, notes, tags):
    dic = kz.currentCaseDic()
    plan = dic.get("plan")
    base_run_id = st.session_state.get("library_base_run_id")
    base = None
    if base_run_id:
        try:
            base = lib.scenario(base_run_id)
        except Exception:  # noqa: BLE001 - a deleted run is simply not the base any more
            base = None
    try:
        scenario = scenario_from_ui(dic, plan, base=base)
        result = lib.save_run(name=name or kz.currentCaseName(), scenario=scenario,
                              parent=base_run_id, notes=notes,
                              tags=tuple(t for t in tags if t.strip()))
    except Exception as exc:  # noqa: BLE001 - an incomplete case is shown, not raised
        st.error(f"Cannot save this case yet: {exc}", icon=":material/error:")
        return
    _report_saved(result)


# -- getting a run in -------------------------------------------------

with st.expander("Add a run to the library", expanded=not lib.runs()):
    tab1, tab2 = st.tabs(["_Import a case_", "_Save the current case_"])
    with tab1:
        col1, col2 = st.columns([3, 2], gap="large")
        with col1:
            case_up = st.file_uploader("Case file (TOML)", type=["toml"], key="lib_case_up")
            hfp_up = st.file_uploader("Household workbook (optional)", type=["xlsx"],
                                      key="lib_hfp_up")
            budget_up = st.file_uploader("Budget file (optional)", type=["json"],
                                         key="lib_budget_up")
        with col2:
            name = st.text_input("Run name", key="lib_import_name",
                                 placeholder="from the file name when empty")
            notes = st.text_area("Notes (optional)", key="lib_import_notes")
            tags = st.text_input("Tags (optional, comma separated)", key="lib_import_tags")
        if st.button("Import as a new run", type="primary", disabled=case_up is None):
            _save_uploaded_run(name.strip(), notes.strip(), tags.split(","),
                               {"case": case_up, "hfp": hfp_up, "budget": budget_up})
            st.rerun()
    with tab2:
        if not kz.has_current_case():
            st.caption(
                "No case is open in the session. Open one on the Create Case page (or "
                '"Edit as new run" on a run\'s page) and come back here.'
            )
        else:
            base_run_id = st.session_state.get("library_base_run_id")
            base_name = _run_name(base_run_id) if base_run_id else None
            base_note = f" against *{base_name}*" if base_name else ""
            st.caption(f"The case **{kz.currentCaseName()}** will be saved as a new run{base_note}.")
            col1, col2 = st.columns([3, 2], gap="large")
            with col1:
                name = st.text_input("Run name", key="lib_save_name",
                                     value=kz.currentCaseName() or "")
                notes = st.text_area("Notes (optional)", key="lib_save_notes")
                tags = st.text_input("Tags (optional, comma separated)", key="lib_save_tags")
            if st.button("Save as a new run", type="primary"):
                _save_current_case(name.strip(), notes.strip(), tags.split(","))
                st.rerun()


# -- the runs ---------------------------------------------------------

runs = list(reversed(lib.runs()))
if not runs:
    st.info("The library has no runs yet: import a case above.")
    st.stop()

st.markdown("#### Runs")
for run in runs:
    jobs = manager.jobs(run)
    latest = jobs[-1].state if jobs else None
    line = f"**{run.name}**"
    if run.plan_year:
        line += f"  \n`{run.folder_name}` · plan year {run.plan_year}"
    if run.parent:
        parent = _run_name(run.parent) or "a deleted run"
        changes = "; ".join(run.change_summary[:2]) if run.change_summary else "same inputs"
        line += f"  \nfrom *{parent}*: {changes}"
    elif run.change_summary:
        line += f"  \n{'; '.join(run.change_summary[:2])}"
    if run.notes:
        line += f"  \n{run.notes}"
    if run.tags:
        line += f"  \n{', '.join(run.tags)}"
    if jobs:
        line += f"  \n{len(jobs)} solve(s), latest: {latest}"
    cols = st.columns([6, 1, 1, 1, 1])
    cols[0].markdown(line)
    if cols[1].button("Open", key=f"open_{run.id}",
                      help="The run's page: numbers, charts, tables and its solves."):
        st.session_state["library_selected_run"] = run.id
        st.switch_page("Run.py")
    try:
        blob = libraryjobs.run_zip_bytes(run)
    except Exception as exc:  # noqa: BLE001 - shown, not raised (a run being re-queued, P5)
        cols[2].caption(f"zip unavailable: {exc}")
    else:
        cols[2].download_button("Zip", data=blob, file_name=f"{run.folder_name}.zip",
                                key=f"zip_{run.id}", help="Download everything (a zip of the run).")
    with cols[3].popover("Rename"):
        new = st.text_input("Name", value=run.name, key=f"rename_{run.id}")
        if st.button("Rename", key=f"renameb_{run.id}"):
            lib.rename_run(run, new.strip() or run.name)
            st.rerun()
    with cols[4].popover("Delete"):
        st.caption("Moves the run to `library/trash/` (emptied by hand). Children keep "
                   "their parent id and show it as deleted.")
        if st.button("Delete", type="primary", key=f"delb_{run.id}"):
            lib.delete_run(run)
            st.rerun()
    st.divider()

damaged = lib.damaged()
if damaged:
    st.warning(f"{len(damaged)} folder(s) in `runs/` have an unreadable run.json and are "
               "shown as damaged, never listed: " + ", ".join(p.name for p in damaged))

st.caption(
    "A run is immutable: its inputs and every solve stay as they were saved (save-as only, "
    "D3). Deleting moves the folder to `library/trash/`; backing up is copying the library "
    "folder, and `owlcli run runs/<run>/inputs/Case.toml` reproduces a solve outside the "
    "interface."
)

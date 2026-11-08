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

import streamlit as st

import library_import
import libraryjobs
import owlbridge as owb
import sskeys as kz
from owlplanner.library import scenario_from_ui

st.markdown("# :material/database: Library")
kz.divider("orange")
libraryjobs.show_flashes()  # what the last action said before its rerun (review 3, W3)

manager = libraryjobs.get_manager()
lib = manager.library


def _run_name(rid):
    """A run's name, or None when it is gone (a deleted parent shows as deleted, section 7)."""
    try:
        return lib.get(rid).name
    except Exception:  # noqa: BLE001 - a deleted run is simply not there any more
        return None


def _report_saved(result):
    """Say what save_run did, including "identical to an existing run" (V8).

    The callers rerun the page right after, so everything but the toast goes through
    `libraryjobs.flash` (review 3, W3).
    """
    if result.created:
        st.toast(f"Saved as **{result.run.name}** ({result.run.folder_name})")
    else:
        other = result.identical_to
        libraryjobs.flash(
            "info",
            f"Identical to *{other.name}* ({other.folder_name}): not saved again. "
            "The run keeps its own inputs; the requested name, notes and tags were not applied."
            if other else "Not saved: identical inputs already in the library.",
        )
        if result.dropped:
            libraryjobs.flash("caption", f"Not applied: {result.dropped}")


def _add_to_collection(collection, result):
    """The save dialog's "Collection" field (design section 7): the saved run joins the
    collection as it is -- no variant values, so the grid lists it beside the cells until
    they are set (the Members section, "Values"). An identical save joins the run it is,
    which keeps its values when it is already a member (review AG6)."""
    if collection is None:
        return
    run = result.run if result.created else result.identical_to
    if run is not None:
        # A run already in the collection keeps its variant values (review AG6).
        lib.join_collection(collection.id, run)


def _save_uploaded_run(name, notes, tags, uploaded, collection=None):
    """Import the uploaded case as a new run. Returns whether it was saved; on False the
    reason is flashed and the form stays open with its files (UX review Q10)."""
    result, reason = library_import.import_uploaded(lib, name=name, notes=notes, tags=tags,
                                                    uploaded=uploaded)
    if reason:
        libraryjobs.flash("error", reason)
        return False
    _report_saved(result)
    _add_to_collection(collection, result)
    return True


def _save_current_case(name, notes, tags, collection=None):
    dic = kz.currentCaseDic()
    plan = dic.get("plan")
    base_run_id = kz.runBase()
    base = None
    if base_run_id:
        try:
            base = lib.scenario(base_run_id)
        except Exception:  # noqa: BLE001 - a deleted run is simply not the base any more
            base = None
    try:
        # The tables come from the plan (`scenario_from_ui`), not from the case keys: sync the
        # page-edited ones in first, or a table edited and not yet run or downloaded would be
        # missing from the run.
        if plan is not None and owb.syncContributions() is False:
            # Review Y4: the plan refused the pages' tables; saving now would store its previous
            # ones without a word (the rerun after the button clears the page's own error).
            libraryjobs.flash(
                "error",
                "Cannot save this case yet: the Wages and Contributions tables were not accepted. "
                "Fix them on the Financial Profile page.",
            )
            return
        dropped = []
        scenario = scenario_from_ui(dic, plan, base=base, dropped=dropped)
        result = lib.save_run(name=name or kz.currentCaseName(), scenario=scenario,
                              parent=base_run_id, notes=notes,
                              tags=tuple(t for t in tags if t.strip()))
    except Exception as exc:  # noqa: BLE001 - an incomplete case is shown, not raised
        libraryjobs.flash("error", f"Cannot save this case yet: {exc}")
        return
    _report_saved(result)
    _add_to_collection(collection, result)
    if dropped:
        # Review W1: a value the run's events generate is regenerated from its event (section
        # 6.3, markers first), so an edit to one in the case pages does not survive the save.
        shown = "; ".join(dropped[:5]) + (f"; and {len(dropped) - 5} more" if len(dropped) > 5 else "")
        libraryjobs.flash(
            "warning",
            f"Not kept in this run: {shown}. These values are regenerated by the run's events — "
            "edit the event on the Scenario page instead.",
        )


# -- getting a run in -------------------------------------------------

# Open while the library is empty, and after an import that failed (UX review Q10: it closed
# again, and the error was the only thing left on screen).
_import_open = not lib.runs() or bool(st.session_state.get("lib_import_failed"))
with st.expander("Add a run to the library", expanded=_import_open):
    tab1, tab2 = st.tabs(["_Import a case_", "_Save the current case_"])
    with tab1:
        col1, col2 = st.columns([3, 2], gap="large")
        with col1:
            # The uploaders' keys carry a counter that a successful import bumps: the next
            # import starts from an empty form; a failed one keeps the files chosen.
            _n = st.session_state.get("lib_import_round", 0)
            case_up = st.file_uploader("Case file (TOML)", type=["toml"], key=f"lib_case_up{_n}")
            _refs = library_import.case_refs(case_up)
            hfp_up = st.file_uploader("Household workbook (xlsx)", type=["xlsx"], key=f"lib_hfp_up{_n}")
            st.caption(library_import.companion_caption("hfp", _refs, case_up))
            budget_up = st.file_uploader("Budget file (JSON)", type=["json"], key=f"lib_budget_up{_n}")
            st.caption(library_import.companion_caption("budget", _refs, case_up))
            rates_up = st.file_uploader("Rates table (CSV)", type=["csv"], key=f"lib_rates_up{_n}")
            st.caption(library_import.companion_caption("rates", _refs, case_up))
        with col2:
            name = st.text_input("Run name", key=f"lib_import_name{_n}",
                                 placeholder="from the file name when empty")
            notes = st.text_area("Notes (optional)", key=f"lib_import_notes{_n}")
            tags = st.text_input("Tags (optional, comma separated)", key=f"lib_import_tags{_n}")
            collection = st.selectbox(
                "Collection (optional)", [None] + list(lib.collections()),
                format_func=lambda c: "(none)" if c is None else c.name,
                key=f"lib_import_collection{_n}",
                help="The run joins this collection as it is; its variant values are set "
                     "on the Collections page.")
        if st.button("Import as a new run", type="primary", disabled=case_up is None):
            if _save_uploaded_run(name.strip(), notes.strip(), tags.split(","),
                                  {"case": case_up, "hfp": hfp_up, "budget": budget_up,
                                   "rates": rates_up}, collection):
                st.session_state.pop("lib_import_failed", None)
                st.session_state["lib_import_round"] = _n + 1
            else:
                st.session_state["lib_import_failed"] = True
            st.rerun()
    with tab2:
        if not kz.has_current_case():
            st.caption(
                "No case is open in the session. Open one on the Create Case page (or "
                '"Edit as new run" on a run\'s page) and come back here.'
            )
        else:
            base_run_id = kz.runBase()
            base_name = _run_name(base_run_id) if base_run_id else None
            base_note = f" against *{base_name}*" if base_name else ""
            st.caption(f"The case **{kz.currentCaseName()}** will be saved as a new run{base_note}.")
            col1, col2 = st.columns([3, 2], gap="large")
            with col1:
                # UX remediation QW-8: a save of a run's modified inputs is a run of its own,
                # so the default name says so. Second pass (review AN4): "<base run's name>
                # variant" -- the import's case name read "ari+noa variant" for "ari+noa
                # condo baseline" -- and the widget is keyed by the case, so the default
                # follows a switch of case (Streamlit keeps a drawn widget's value).
                _case = kz.currentCaseName() or ""
                _name = f"{base_name} variant" if base_name else _case
                name = st.text_input("Run name", key=f"lib_save_name|{_case}", value=_name)
                if name.strip() and name.strip() in {r.name for r in lib.runs()}:
                    st.warning(f"A run is already called *{name.strip()}*: saving makes another "
                               "one with the same name.", icon=":material/flag:")
                notes = st.text_area("Notes (optional)", key="lib_save_notes")
                tags = st.text_input("Tags (optional, comma separated)", key="lib_save_tags")
            collection = st.selectbox(
                "Collection (optional)", [None] + list(lib.collections()),
                format_func=lambda c: "(none)" if c is None else c.name,
                key="lib_save_collection",
                help="The run joins this collection as it is; its variant values are set "
                     "on the Collections page.")
            if st.button("Save as a new run", type="primary"):
                _save_current_case(name.strip(), notes.strip(), tags.split(","), collection)
                st.rerun()


# -- the runs ---------------------------------------------------------

runs = list(reversed(lib.runs()))
if not runs:
    st.info("The library has no runs yet: import a case above.")
    st.stop()

st.markdown("#### Runs")
_baseline = lib.baseline()
for run in runs:
    jobs = manager.jobs(run)
    latest = jobs[-1].state if jobs else None
    line = f"**{run.name}**"
    if _baseline is not None and run.id == _baseline.id:
        line += "  :material/push_pin: *baseline*"
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
    cols = st.columns([6, 1, 1, 1, 1, 1])
    cols[0].markdown(line)
    # S-1: the baseline is the run the app opens on (the Run page, library mode's landing page).
    if _baseline is not None and run.id == _baseline.id:
        if cols[5].button("Baseline ✓", key=f"unpin_{run.id}",
                          help="The app opens on this run. Click to unpin it."):
            lib.unpin(run)
            st.rerun()
    elif cols[5].button("Make this the baseline", key=f"pin_{run.id}",
                        help="The app opens on the baseline (the Run page)."):
        lib.pin(run)
        libraryjobs.flash("info", f"*{run.name}* is the baseline: the app opens on it.")
        st.rerun()
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
        st.caption("Moves the run to the library's trash folder (emptied by hand). Runs made "
                   "from it keep their link to it and show it as deleted.",
                   help="The folder is `trash/` inside the library folder.")
        if st.button("Delete", type="primary", key=f"delb_{run.id}"):
            # Through the manager: a run with a waiting or running solve is refused (review
            # 3, W4: the folder used to move to trash/ under a live worker, untracked).
            try:
                manager.delete_run(run)
            except Exception as exc:  # noqa: BLE001 - shown after the rerun, not raised
                libraryjobs.flash("error", f"Not deleted: {exc}")
            st.rerun()
    st.divider()

damaged = lib.damaged()
if damaged:
    st.warning(f"{len(damaged)} folder(s) in `runs/` have an unreadable run.json and are "
               "shown as damaged, never listed: " + ", ".join(p.name for p in damaged))

st.caption(
    "A saved run never changes: its inputs and every solve stay as they were saved, and an "
    "edit is saved as a new run. Deleting moves a run to the library's trash folder; backing "
    "up is copying the library folder. Each run's inputs are an ordinary Owl case, so a solve "
    "can be reproduced outside the interface with Owl's command line."
)

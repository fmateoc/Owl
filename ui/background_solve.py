"""
Fork: the classic results pages in library mode (ergonomics review S-6, decision 9).

Graphs, Worksheets and Reports solve the case in the foreground when it changed since its last
solve (`owb.runPlan()` on open). A Careful solve of the synthetic household takes about five
minutes, a claiming-age search half an hour or more, and the page is blocked meanwhile. In
library mode the pages skip that solve and offer *Save as a new run and solve it in the
background* instead: the Library page's save of the current case (`library_save`), then a
Careful enqueue through `preset_solves`, with a link to the Queue. Outside library mode the
pages keep upstream's code path.

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

import library_save
import libraryjobs
import librarypresets
import sskeys as kz

PRESET = "decision"  # "Careful": local search and its exact companion
LABEL = "Save as a new run and solve it in the background"


def _save_and_queue():
    manager = libraryjobs.get_manager()
    lib = manager.library
    base_id = kz.runBase()
    base_name = None
    if base_id:
        try:
            base_name = lib.get(base_id).name
        except Exception:  # noqa: BLE001 - a deleted base run names nothing
            base_name = None
    name = f"{base_name} variant" if base_name else (kz.currentCaseName() or "case")
    saved = library_save.save_current_case(lib, name)
    if saved is None:
        return
    result, dropped = saved
    run = result.run if result.created else result.identical_to
    if run is None:
        libraryjobs.flash("error", "Not saved: identical inputs already in the library.")
        return
    queued = []
    failed = False
    from owlplanner.library import preset_solves
    from owlplanner.library import results as R

    existing = getattr(manager, "jobs", None)
    live = ({str(j.doc.get("preset")) for j in existing(run)
             if j.state in (R.WAITING, R.RUNNING)} if callable(existing) else set())
    for solve in preset_solves(PRESET):
        if solve in live:
            continue
        try:
            queued.append(manager.enqueue(run, preset=solve).id)
        except Exception as exc:  # noqa: BLE001 - a run from another plan year, say (R1)
            libraryjobs.flash("error", f"Not queued: {exc}")
            failed = True
            break
    what = f"Saved as *{run.name}*" if result.created else f"Identical to *{run.name}* (not saved again)"
    if queued:
        libraryjobs.flash("info", f"{what}; its {librarypresets.name(PRESET)} solve is queued "
                                  "(the Queue page shows it; the Run page shows the result).")
    elif not failed:
        libraryjobs.flash("info", f"{what}; its {librarypresets.name(PRESET)} solve is already in the queue "
                                  "(the Queue page shows it; the Run page shows the result).")
    if not failed:
        kz.storeCaseKey("library_queued_run", run.name)
    library_save.flash_dropped(dropped)
    st.session_state["library_selected_run"] = run.id


def button(page_key: str, primary: bool = False, container=None) -> None:
    """The button alone (it stands in for *Re-run* on Graphs). The messages it queues are drawn
    by the title bar after the rerun (`sskeys.titleBar`)."""
    (container or st).button(LABEL, key=f"bg_solve_{page_key}", type="primary" if primary else "secondary",
                             on_click=_save_and_queue,
                             help="The Library page's save of the current case, then a Careful solve in the "
                                  "queue (the Queue page).")


def offer(page_key: str) -> None:
    """The notice and the button that stand in for the foreground solve (library mode)."""
    queued_run = kz.getCaseKey("library_queued_run")
    if queued_run:
        st.info(f"Saved as *{queued_run}* for a background *Careful* solve (the Queue page shows "
                "its progress; the Run page shows the result when it finishes).",
                icon=":material/schedule:")
        if st.button("Open the Queue", key=f"bg_queue_{page_key}", icon=":material/schedule:"):
            st.switch_page("Queue.py")
        return
    st.info("The case changed since its last solve. In the run library it is solved in the background: "
            "save it as a new run and queue its *Careful* solve; this page is not blocked meanwhile.",
            icon=":material/schedule:")
    c1, c2 = st.columns([3, 1])
    button(page_key, primary=True, container=c1)
    if c2.button("Open the Queue", key=f"bg_queue_{page_key}", icon=":material/schedule:"):
        st.switch_page("Queue.py")

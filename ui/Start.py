"""
Fork: where a session starts in library mode (the "operate it alone" request, 2026-11-10).

The page asks what the reader wants to do, among the things the program does, and shows the
steps to it with what is already done: the first step still open carries the one button.
Nothing is locked: every page stays in the menu. With no plan in the folder the only things
to do are to make one (the Setup page) or to bring in files made earlier (the Library page's
import), and the app opens here; once a plan exists the app opens on it (the Run page, S-1)
and this page is one click away.

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

from datetime import date

import streamlit as st

import disclaimer
import libraryjobs
import librarypresets
import sskeys as kz
import whatif
from owlplanner.library import household as H
from owlplanner.library.casefiles import has_housing_rows

st.markdown("# :material/flag: Start")
kz.divider("orange")
libraryjobs.show_flashes()

manager = libraryjobs.get_manager()
lib = manager.library
home = H.home_dir(lib.root)
# A file to double-click next time (written once; none for a library the launcher's folder
# argument would not open).
starter = H.write_starter(home, library_root=lib.root)


# The reminder, once per library (S-1, decision 2): with no plan yet this is the landing page.
@st.dialog(disclaimer.TITLE)
def _library_reminder():
    st.markdown(disclaimer.reminder_markdown())
    st.caption("Shown once for this library: OK is remembered in its `library.json`.")
    if st.button("OK"):
        lib.accept_disclaimer()
        kz.storeGlobalKey(disclaimer.DISMISSED_KEY, True)
        st.rerun()


if disclaimer.show_disclaimer() and not kz.getGlobalKey(disclaimer.DISMISSED_KEY) \
        and not lib.disclaimer_accepted():
    _library_reminder()


def _go(page, run=None, **state):
    if run is not None:
        st.session_state["library_selected_run"] = run.id
    for key, value in state.items():
        st.session_state[key] = value
    st.switch_page(page)


def _steps(steps):
    """Numbered steps: (done, text). The first one not done is the one to do now."""
    todo = next((i for i, (done, _text) in enumerate(steps) if not done), None)
    lines = []
    for i, (done, text) in enumerate(steps):
        mark = ":material/check_circle:" if done else (":material/arrow_circle_right:" if i == todo
                                                       else ":material/radio_button_unchecked:")
        lines.append(f"{mark} **{i + 1}.** {text}")
    st.markdown("  \n".join(lines))


runs = lib.runs()
st.caption(f"Your folder: `{home}`. Everything the program makes or keeps is in it"
           + (f"; next time, start it with `{starter.name}` there." if starter is not None else "."))

# -- no plan yet -----------------------------------------------------------
if not runs:
    st.markdown("### This folder has no plan yet")
    c1, c2 = st.columns(2, gap="large")
    with c1.container(border=True):
        st.markdown("#### Set up our plan")
        st.markdown("Answer a few questions: who the plan is for, where you live, your savings, Social "
                    "Security, and what the plan should aim for. Wages, a budget and a home go in an Excel "
                    "workbook, which the program can hand you empty. About fifteen minutes with your "
                    "statements at hand; it is kept as you go.")
        if st.button("Set up our plan", type="primary", key="start_setup"):
            _go("Setup.py")
    with c2.container(border=True):
        st.markdown("#### Bring in files made earlier")
        st.markdown("A case file (`.toml`) and its workbook from an earlier use of Owl. The Library page "
                    "reads them as they are.")
        if st.button("Bring in files", key="start_import"):
            _go("Library.py")
    st.stop()

# -- a plan exists ----------------------------------------------------------
plan = lib.baseline() or runs[-1]
this_year = date.today().year
results = whatif.main_results(manager, plan)
solving = libraryjobs.live_jobs(manager, plan)
old_year = plan.plan_year is not None and plan.plan_year < this_year
careful = librarypresets.name(whatif.PRESET)

st.markdown(f"### What do you want to do with *{libraryjobs.plain(plan.name)}*?")
if lib.baseline() is None:
    st.caption("This is the newest plan in the folder. *Make this the baseline* on the Library page picks "
               "the one the program opens on.")
wishes = {
    "see": "See where our plan stands",
    "whatif": "Try a change (retire later, buy another year, another price ...)",
    "options": "Compare several options side by side",
    "update": "Bring our numbers up to date" + (f", or start {this_year}" if old_year else ""),
    "files": "Find my files, back them up, or add a plan",
}
wish = st.radio("I want to", list(wishes), format_func=wishes.get, key="start_wish",
                index=list(wishes).index("update") if old_year else 0, label_visibility="collapsed")

in_year = (not old_year, f"The plan is for {plan.plan_year}." if not old_year else
           f"The plan was made for {plan.plan_year}: start {this_year} from it first (its page says how).")
solved = (bool(results), "It is solved." if results else
          ("It is being solved now." if solving else "Solve it: the program works out the plan."))

with st.container(border=True):
    if wish == "see":
        _steps([(True, "Your figures are in."), in_year, solved,
                (False, "Read it: spending, taxes, what is left, and the years to look at.")])
        if old_year:
            if st.button(f"Open the plan to start {this_year}", type="primary", key="start_see_year"):
                _go("Run.py", plan)
        elif not results and not solving:
            if st.button(f"Solve it ({careful})", type="primary", key="start_see_solve"):
                try:
                    whatif.queue_careful(manager, plan)
                except Exception as exc:  # noqa: BLE001 - shown on the page it opens
                    libraryjobs.flash("error", f"Not queued: {libraryjobs.plain(exc)}")
                _go("Run.py", plan, **{libraryjobs.SHOW_NEWEST_KEY: True})
        elif st.button("Open our plan", type="primary", key="start_see_open"):
            _go("Run.py", plan)
    elif wish == "whatif":
        rows = False
        try:
            rows = has_housing_rows(lib.scenario(plan))
        except Exception:  # noqa: BLE001 - a damaged run offers nothing
            rows = False
        _steps([in_year, solved,
                (not rows, "The home in your workbook can be changed on the what-if page." if not rows else
                 "Your home is in the workbook as rows. To try another year or price, turn it into an "
                 "event first: *Turn the home rows into a purchase event* on the plan's page."),
                (False, "On the what-if page: change one thing, press *Save and solve*, then *Compare with "
                        "its parent* on the page it opens.")])
        if old_year or rows:
            if st.button("Open the plan's page", type="primary", key="start_whatif_run"):
                _go("Run.py", plan)
        elif st.button("Open the what-if page", type="primary", key="start_whatif"):
            _go("Scenario.py", plan)
    elif wish == "options":
        _steps([in_year, solved,
                (False, "On the Collections page, *Make variants*: pick what varies (the place, the purchase "
                        "year, cash or a loan, the last work year, the claiming ages) and its values; the "
                        "program makes one plan per combination and solves them."),
                (False, "Read the grid: each cell is the difference from the plan you started from.")])
        if st.button("Open the Collections page", type="primary", key="start_options", disabled=old_year):
            _go("Collections.py")
    elif wish == "update":
        if old_year:
            _steps([(False, f"On the plan's page, *Start {this_year} from this run* opens last year's figures "
                            f"for {this_year}."),
                    (False, "Put in this year's account balances, and what the page lists."),
                    (False, "Save on the Library page: the plan for the new year.")])
        else:
            _steps([(False, "On the plan's page, *Edit as new run* opens its figures in the Case Setup pages."),
                    (False, "Change what is new: balances, Social Security estimates, the workbook's tables."),
                    (False, "Save on the Library page: a new plan, with this one kept as it was.")])
        if st.button("Open the plan's page", type="primary", key="start_update"):
            _go("Run.py", plan)
    else:
        st.markdown(
            f"- **Your files** are in `{home}`: the workbook you filled, and `library`, where every plan "
            "and its results are kept.\n"
            "- **To back up**, copy that whole folder. Nothing is stored anywhere else.\n"
            "- **A plan you deleted** is in `library/trash` until you empty it yourself.\n"
            + (f"- **To start the program**, double-click `{starter.name}` in that folder.\n" if starter else ""))
        c1, c2 = st.columns(2)
        if c1.button("See all the plans (Library)", key="start_files_library"):
            _go("Library.py")
        if c2.button("Set up another plan", key="start_files_setup"):
            _go("Setup.py")

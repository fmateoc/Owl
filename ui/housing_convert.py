"""
Fork: "Turn the home rows into a purchase event" (ergonomics review S-3), on the Run and
Library pages.

An imported case holds its home as hand workbook rows. `casefiles.convert_housing` proposes
rent / purchase / care events and accepts them only when they rebuild the run's tables and case
cell for cell; on success the events are saved as a child run (the parent never changes), on
failure the differing cells are shown and nothing is saved. Offered, never automatic
(decision 5).

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

import pandas as pd
import streamlit as st

import libraryjobs
from owlplanner.library.casefiles import convert_housing, has_housing_rows

LABEL = "Turn the home rows into a purchase event"
HELP = ("Reads the home in this run's workbook (Fixed Assets, its loan, the purchase outflow, the "
        "owner's budget lines, the rent before) as rent and purchase events, so that make variants "
        "and the Scenario page can move them. Saved as a new run only when the events rebuild the "
        "same tables exactly; otherwise the cells that differ are shown.")


def offered(lib, run) -> bool:
    try:
        return has_housing_rows(lib.scenario(run))
    except Exception:  # noqa: BLE001 - a damaged run offers nothing
        return False


def convert_button(lib, run, key, container=None):
    """The button and what a click does; True when a child run was saved (then rerun)."""
    box = container or st
    if not box.button(LABEL, key=key, help=HELP):
        return False
    converted, problems = convert_housing(lib.scenario(run))
    if converted is None:
        st.warning("Not converted: the events would not rebuild this run's tables exactly, so nothing was "
                   "saved. What differs:", icon=":material/warning:")
        st.dataframe(pd.DataFrame({"difference": problems}), hide_index=True, width="stretch")
        return False
    result = lib.save_run(name=f"{run.name}, home as events", scenario=converted, parent=run.id,
                          notes="The home rows turned into rent / purchase events (same tables).")
    if result.created:
        libraryjobs.flash("info", f"Saved *{result.run.name}*: the same tables, now made by rent and purchase "
                                  "events (Scenario page).")
    else:
        other = result.identical_to
        libraryjobs.flash("info", f"Identical to *{other.name}*: not saved again." if other
                          else "Not saved: identical inputs already in the library.")
    st.rerun()
    return True

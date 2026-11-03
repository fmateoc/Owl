"""
Create Case page for Owl retirement planner Streamlit UI.

This module provides the interface for creating new retirement planning cases
or uploading existing case files.

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
from io import StringIO
import streamlit as st

import sskeys as kz
import owlbridge as owb
import tomlexamples as tomlex
import case_progress as cp


@st.cache_data
def _state_choices():
    from owlplanner import tax_state as _ts

    return [""] + _ts.valid_states()


@st.cache_data
def _locality_choices(state):
    from owlplanner import tax_local as _tl

    return [""] + _tl.valid_localities(state) if state else [""]


@st.cache_data
def _district_choices(state):
    from owlplanner import star as _star

    return [""] + _star.valid_districts(state) if state else [""]


_district_help = (
    "Fork: municipality and school district of the home, for the NY STAR credit (Basic, or Enhanced from 65 "
    "under the income limit). It applies in years with a budget 'property tax' line. Blank for none."
)


def _district_select(label, district_key, state):
    """Selectbox for the school district of a residence, when the state has STAR data."""
    choices = _district_choices(state or "")
    if kz.getCaseKey(district_key) not in choices:
        kz.setCaseKey(district_key, "")
        st.session_state.pop(kz.genCaseKey(district_key), None)
    if len(choices) > 1:
        kz.getSelectbox(label, choices, district_key, help=_district_help)


# --- moves after the first (fork: the case file carries them; run-library step 5 edits them) ---


def _moreMoveKey(idx, field):
    return kz.genCaseKey(f"mvMore{idx}_{field}")


def _onMoreMove(idx, field):
    """Copy one widget of further move *idx* into stateMovesMore."""
    more = [dict(m) for m in kz.getCaseKey("stateMovesMore") or []]
    if idx >= len(more):
        return
    val = st.session_state.get(_moreMoveKey(idx, field))
    if field == "year":
        more[idx]["year"] = int(val)
    elif val:
        more[idx][field] = val
    else:
        more[idx].pop(field, None)
    kz.setCaseKey("stateMovesMore", more)


def _dropMoreMoveField(idx, field):
    """Drop a further move's field (its state no longer has that city or district)."""
    more = [dict(m) for m in kz.getCaseKey("stateMovesMore") or []]
    if idx < len(more):
        more[idx].pop(field, None)
        kz.setCaseKey("stateMovesMore", more)
    st.session_state.pop(_moreMoveKey(idx, field), None)


def _setMovesMore(more):
    """Replace the further moves. The rows' widget state goes with the old rows: removing one
    shifts the rest onto its keys (#194's half-typed row problem, for whole rows)."""
    kz.setCaseKey("stateMovesMore", more)
    for i in range(len(more) + 2):
        for field in ("year", "state", "locality", "school_district"):
            st.session_state.pop(_moreMoveKey(i, field), None)


def _addMove():
    more = [dict(m) for m in kz.getCaseKey("stateMovesMore") or []]
    last = more[-1] if more else {}
    more.append(
        {
            "year": int(last.get("year") or kz.getCaseKey("stateMoveYear") or date.today().year) + 2,
            "state": last.get("state") or kz.getCaseKey("stateMoveState") or "",
        }
    )
    _setMovesMore(more)


def _removeMove(idx):
    more = [dict(m) for m in kz.getCaseKey("stateMovesMore") or []]
    if idx < len(more):
        del more[idx]
    _setMovesMore(more)


def _normResidence(state, locality, district):
    """A residence as residency compares them: canonical spellings where it knows them.

    A move can come from the case file with a short form ("Yonkers") while the pages'
    selects hold the canonical name ("City of Yonkers / Yonkers"); residency canonicalizes
    before comparing, so the warnings here must too (review W3). An unknown spelling is
    compared as written rather than raising in the page.
    """
    from owlplanner import residency as _res

    try:
        return _res.normalize(state or "", locality or "", district or "")
    except ValueError:
        return (state or "", locality or "", district or "")


def _moreMoveWarnings(moves, first, bounds=None):
    """The moves residency refuses at solve time, reported as the rows are edited.

    Every move -- the first included -- is checked against the residence it leaves, walked in
    year order as `residency._homes_by_year` applies them (it sorts the moves and refuses one
    that does not change the residence in force). The first move's "goes to the starting
    residence" case is the page's own warning beside its fields, so it is not repeated here
    (review W3: a further move dated before the first can make the first move the refused one).
    `bounds` is (first plan year, N_n) when the case has a plan: a move outside
    first_year < year < first_year + N_n is refused at solve time too (review W4).
    """
    msgs = []
    tagged = [(False, first)] + [(True, m) for m in moves]
    tagged.sort(key=lambda pair: int(pair[1].get("year") or 0))
    seen = set()
    prev = _normResidence(
        kz.getCaseKey("state") or "", kz.getCaseKey("locality") or "", kz.getCaseKey("schoolDistrict") or ""
    )
    prev_label = "the starting residence"
    for is_more, move in tagged:
        year = int(move.get("year") or 0)
        dest = _normResidence(move.get("state") or "", move.get("locality") or "", move.get("school_district") or "")
        label = f"the move in {year}" if year else "a move"
        if year in seen:
            msgs.append(f"Two moves in {year}.")
        seen.add(year)
        if bounds is not None:
            first_year, n_n = bounds
            if not first_year < year < first_year + n_n:
                msgs.append(
                    f"{label.capitalize()} must fall after the first plan year and within the plan "
                    f"({first_year + 1}-{first_year + n_n - 1}); got {year}."
                )
        if dest == prev and (is_more or prev_label != "the starting residence"):
            where = " / ".join(filter(None, dest)) or "no state"
            msgs.append(f"{label.capitalize()} goes to {prev_label} ('{where}').")
        prev, prev_label = dest, label
    return msgs


def _renderMoreMoves():
    """The moves after the first, one block of cascading selects each."""
    thisyear = date.today().year
    more = [dict(m) for m in kz.getCaseKey("stateMovesMore") or []]
    st.markdown("##### :orange[Further moves]")
    for idx, move in enumerate(more):
        st.markdown(f"**Move {idx + 2}**")
        cols = st.columns([2, 3, 3, 1], gap="small", vertical_alignment="top")
        with cols[0]:
            st.number_input(
                f"Year of move {idx + 2}",
                value=int(move.get("year") or thisyear + 5),
                min_value=thisyear + 1,
                max_value=thisyear + 100,
                step=1,
                key=_moreMoveKey(idx, "year"),
                on_change=_onMoreMove,
                args=[idx, "year"],
                help="First calendar year taxed by the new state. It must fall within the plan.",
            )
        with cols[1]:
            states = _state_choices()
            state = move.get("state") or ""
            st.selectbox(
                f"State of move {idx + 2}",
                states,
                index=states.index(state) if state in states else 0,
                key=_moreMoveKey(idx, "state"),
                on_change=_onMoreMove,
                args=[idx, "state"],
                help="State of residence from that year on. Leave blank to stop modeling state taxes.",
            )
            localities = _locality_choices(state)
            if move.get("locality") and move["locality"] not in localities:
                _dropMoreMoveField(idx, "locality")
            if len(localities) > 1:
                loc = move.get("locality") or ""
                st.selectbox(
                    f"City income tax of move {idx + 2} (optional)",
                    localities,
                    index=localities.index(loc) if loc in localities else 0,
                    key=_moreMoveKey(idx, "locality"),
                    on_change=_onMoreMove,
                    args=[idx, "locality"],
                    help="City income tax from that year on. Blank means the rest of the state.",
                )
        with cols[2]:
            districts = _district_choices(state)
            if move.get("school_district") and move["school_district"] not in districts:
                _dropMoreMoveField(idx, "school_district")
            if len(districts) > 1:
                district = move.get("school_district") or ""
                st.selectbox(
                    f"School district of move {idx + 2} (optional)",
                    districts,
                    index=districts.index(district) if district in districts else 0,
                    key=_moreMoveKey(idx, "school_district"),
                    on_change=_onMoreMove,
                    args=[idx, "school_district"],
                    help=_district_help,
                )
        with cols[3]:
            st.button(
                ":material/delete:",
                key=kz.genCaseKey(f"mvMoreRemove{idx}"),
                on_click=_removeMove,
                args=[idx],
                help=f"Remove move {idx + 2}.",
            )
    st.button("Add a move :material/add:", on_click=_addMove)
    first = {
        "year": kz.getCaseKey("stateMoveYear"),
        "state": kz.getCaseKey("stateMoveState") or "",
        "locality": kz.getCaseKey("stateMoveLocality") or "",
        "school_district": kz.getCaseKey("stateMoveSchoolDistrict") or "",
    }
    plan = kz.getCaseKey("plan")
    bounds = (int(plan.year_n[0]), plan.N_n) if plan is not None else None
    for msg in _moreMoveWarnings(more, first, bounds=bounds):
        st.warning(msg, icon=":material/warning:")


def _loadHFPExample(file):
    if file:
        hfp_name = tomlex.getHFPName(file)
        mybytesio = tomlex.loadWagesExample(file)
        if mybytesio is not None:
            owb.readHFP(mybytesio, file=hfp_name)


def _deleteCase():
    kz.deleteCurrentCase()
    # Close the popover so a second click cannot delete the next case.
    st.session_state["delete_case_popover"] = False


def _render_case_loader():
    st.markdown(
        "##### Select a tab below to load one of the available case examples,"
        " create a new case, or upload an existing TOML case file."
    )
    st.caption("Consult the :material/help: [Documentation](Documentation) for more details.")
    tab1, tab2, tab3 = st.tabs(["_Load a Case Example_", "_Create a New Case_", "_Upload Your Own Case File_"])
    with tab1:
        col, hint = st.columns([2, 3], gap="large", vertical_alignment="bottom")
        with col:
            kz.initGlobalKey("_example_case_idx", 0)
            case = st.selectbox(
                "Examples available from GitHub",
                tomlex.CASES,
                index=None,
                key="_example_case" + str(kz.getGlobalKey("_example_case_idx")),
                placeholder="Select an example case",
            )
        with hint:
            st.caption("Load a pre-built case from GitHub. Most parameters can be adjusted after loading.")
        if case:
            owb.ui_log(f"Loading example: '{case}'")
            mystringio = tomlex.loadCaseExample(case)
            if kz.createCaseFromFile(mystringio):
                kz.storeGlobalKey("_example_case_idx", kz.getGlobalKey("_example_case_idx") + 1)
                kz.initCaseKey("tomlexcase", case)
                st.rerun()
    with tab2:
        col, hint = st.columns([2, 3], gap="large", vertical_alignment="bottom")
        with col:
            st.text_input(
                "Case name",
                key="_newcase",
                on_change=kz.createNewCase,
                args=["newcase"],
                placeholder="Enter a short case name...",
            )
        with hint:
            st.caption("Enter a short name to start a blank case. Life parameters and financials are filled in next.")
    with tab3:
        col, hint = st.columns([2, 3], gap="large", vertical_alignment="bottom")
        with col:
            kz.initGlobalKey("_confile_idx", 0)
            file = st.file_uploader(
                "Upload *case* parameter file...",
                key="_confile" + str(kz.getGlobalKey("_confile_idx")),
                type=["toml"],
            )
        with hint:
            st.caption("Upload a TOML case file previously saved from Owl.")
        if file is not None:
            owb.ui_log(f"Loading case file: '{file.name}'")
            mystringio = StringIO(file.read().decode("utf-8"))
            if kz.createCaseFromFile(mystringio):
                # Bump uploader key to avoid re-import on rerun.
                kz.storeGlobalKey("_confile_idx", kz.getGlobalKey("_confile_idx") + 1)
                st.rerun()


ret = kz.titleBar(":material/person_add: Create Case")

if ret is None:
    _render_case_loader()
else:
    with st.expander("_Create or load another case_"):
        _render_case_loader()

    st.markdown("#### :orange[Description and Life Parameters]")
    casemsg = "Case name can be changed by editing it directly."
    col1, col2, col3 = st.columns((2, 1, 1), gap="large")
    with col1:
        kz.storeGlobalKey("caseNewName", kz.currentCaseName())
        name = st.text_input(
            "Case name",
            on_change=kz.renameCase,
            args=["caseNewName"],
            key="caseNewName",
            help=casemsg,
        )

    diz1 = kz.getCaseKey("plan") is not None
    diz2 = diz1
    with col2:
        statusChoices = ["single", "married"]
        kz.initCaseKey("status", statusChoices[0])
        st.radio(
            "Marital status",
            statusChoices,
            disabled=diz2,
            index=statusChoices.index(kz.getCaseKey("status")),
            key=kz.genCaseKey("status"),
            on_change=kz.setpull,
            args=["status"],
            horizontal=True,
        )
    kz.initCaseKey("state", "")
    _state_help = (
        "Select your state to include state income taxes in the plan. "
        "Leave blank to model federal taxes only. "
        "No-income-tax states (AK, FL, NV, NH, SD, TN, TX, WA, WY) are listed too and produce zero state tax. "
        "See the documentation for the details and limitations of state-tax modeling."
    )
    with col3:
        kz.getSelectbox("State of residence (for state taxes)", _state_choices(), "state", help=_state_help)
        kz.initCaseKey("locality", "")
        localities = _locality_choices(kz.getCaseKey("state") or "")
        if kz.getCaseKey("locality") not in localities:
            kz.setCaseKey("locality", "")  # the state changed to one without that city
            st.session_state.pop(kz.genCaseKey("locality"), None)
        if len(localities) > 1:
            kz.getSelectbox(
                "City income tax (optional)",
                localities,
                "locality",
                help="Adds the city's resident income tax on top of the state's. Blank means the rest of the state.",
            )
        kz.initCaseKey("schoolDistrict", "")
        _district_select("School district (NY STAR credit, optional)", "schoolDistrict", kz.getCaseKey("state"))
        thisyear = date.today().year
        kz.initCaseKey("stateMoveEnabled", False)
        kz.initCaseKey("stateMoveYear", thisyear + 5)
        kz.initCaseKey("stateMoveState", "")
        kz.initCaseKey("stateMoveLocality", "")
        kz.initCaseKey("stateMoveSchoolDistrict", "")
        kz.initCaseKey("stateMovesMore", [])
        _move_help = (
            "Model a change of residence during the plan. "
            "The residence on December 31 taxes the whole year, "
            "so the year of the move is taxed by the new state and city."
        )
        kz.getToggle("Move to another state during the plan", "stateMoveEnabled", help=_move_help)
        if kz.getCaseKey("stateMoveEnabled"):
            mcol1, mcol2 = st.columns(2, gap="small", vertical_alignment="top")
            with mcol1:
                kz.getIntNum(
                    "Year of the move",
                    "stateMoveYear",
                    min_value=thisyear + 1,
                    max_value=thisyear + 100,
                    help="First calendar year taxed by the new state. It must fall within the plan.",
                )
            with mcol2:
                kz.getSelectbox(
                    "New state",
                    _state_choices(),
                    "stateMoveState",
                    help="State of residence from that year on. Leave blank to stop modeling state taxes.",
                )
                move_localities = _locality_choices(kz.getCaseKey("stateMoveState") or "")
                if kz.getCaseKey("stateMoveLocality") not in move_localities:
                    kz.setCaseKey("stateMoveLocality", "")
                    st.session_state.pop(kz.genCaseKey("stateMoveLocality"), None)
                if len(move_localities) > 1:
                    kz.getSelectbox(
                        "New city income tax (optional)",
                        move_localities,
                        "stateMoveLocality",
                        help="City income tax from that year on. Blank means the rest of the state.",
                    )
                _district_select("New school district (optional)", "stateMoveSchoolDistrict",
                                 kz.getCaseKey("stateMoveState"))
            if (
                kz.getCaseKey("stateMoveState"),
                kz.getCaseKey("stateMoveLocality"),
                kz.getCaseKey("stateMoveSchoolDistrict"),
            ) == (
                kz.getCaseKey("state"),
                kz.getCaseKey("locality"),
                kz.getCaseKey("schoolDistrict"),
            ):
                st.warning("The new residence is the starting one.", icon=":material/warning:")
        elif kz.getCaseKey("stateMovesMore"):
            # Review W8: with the toggle off the further moves are invisible here and
            # ui_to_config writes no moves at all -- they stay in the case but are neither
            # solved nor saved until the toggle is on again (or they are removed).
            st.caption(
                f"{len(kz.getCaseKey('stateMovesMore'))} further move(s) stay in the case but are "
                "neither solved nor saved while this is off. Turn it on to edit or remove them."
            )

    if kz.getCaseKey("stateMoveEnabled"):
        # Fork: moves after the first, which the case file carries and the pages edit here.
        _renderMoreMoves()

    kz.initCaseKey("description", "")
    helpmsg = "Provide a short distinguishing description for the case."
    description = kz.getLongText(
        "Brief description", "description", help=helpmsg, placeholder="Enter a brief description..."
    )

    namehelp = "Use first name or just a nickname."
    col1, col2 = st.columns(2, gap="large", vertical_alignment="top")
    with col1:
        kz.initCaseKey("iname0", "")
        if kz.getCaseKey("iname0") == "":
            st.info("First name must be provided.")

        iname0 = kz.getText("Your first name", "iname0", help=namehelp, disabled=diz2, placeholder="Enter name...")

        datemsg = """
Calculations are the same if you were born on any day after the 2nd of the month.
Social Security has special rules for those born on the 1st or 2nd.
See SSA documentation for details.
"""
        longmsg = "See the documentation for suggested resources on estimating longevity."
        sexmsg = "Sex is a required input for stochastic lifespan modeling."
        if iname0:
            incol1, incol2, incol3 = st.columns((1, 1, 0.7), gap="large", vertical_alignment="top")
            with incol1:
                kz.initCaseKey("dob0", "1965-01-15")
                ret = kz.getDate(
                    f"{iname0}'s date of birth",
                    "dob0",
                    min_value="1945-01-01",
                    max_value="2000-12-31",
                    help=datemsg,
                    disabled=diz2,
                )

            with incol2:
                kz.initCaseKey("life0", 89)
                ret = kz.getIntNum(
                    f"{iname0}'s expected longevity", "life0", max_value=120, help=longmsg, disabled=diz1
                )

            with incol3:
                kz.initCaseKey("sex0", "F")
                kz.getSelectbox(f"{iname0}'s sex", ["M", "F"], "sex0", help=sexmsg, disabled=diz2)

    with col2:
        if kz.getCaseKey("status") == "married":
            kz.initCaseKey("iname1", "")
            if kz.getCaseKey("iname1") == "":
                st.info("First name must be provided.")

            iname1 = kz.getText(
                "Your spouse's first name", "iname1", help=namehelp, disabled=diz2, placeholder="Enter a name..."
            )

            if iname1:
                incol1, incol2, incol3 = st.columns((1, 1, 0.7), gap="large", vertical_alignment="top")
                with incol1:
                    kz.initCaseKey("dob1", "1965-01-15")
                    ret = kz.getDate(
                        f"{iname1}'s date of birth",
                        "dob1",
                        min_value="1945-01-01",
                        max_value="2000-12-31",
                        help=datemsg,
                        disabled=diz2,
                    )

                with incol2:
                    kz.initCaseKey("life1", 89)
                    ret = kz.getIntNum(
                        f"{iname1}'s expected longevity", "life1", max_value=120, help=longmsg, disabled=diz1
                    )

                with incol3:
                    kz.initCaseKey("sex1", "M")
                    kz.getSelectbox(f"{iname1}'s sex", ["M", "F"], "sex1", help=sexmsg, disabled=diz2)

    st.divider()
    cantcreate = kz.isIncomplete() or diz1
    if not cantcreate and kz.getCaseKey("plan") is None:
        st.info("""Any parameter on this page can now be changed, including the case name.
Once changes are complete, click the `Create case` button.""")

    cantcopy = kz.caseHasNoPlan()

    # HFP uploader section: shown when plan exists but no HFP has been loaded yet.
    if kz.caseHasPlan() and kz.getCaseKey("stHFP") is None:
        st.markdown("#### :orange[Upload Financial Profile (Optional)]")
        hfp_col1, hfp_col2 = st.columns(2, gap="large")
        with hfp_col1:
            st.markdown("##### :orange[Upload *Household Financial Profile* Workbook]")
            kz.initCaseKey("_xlsx", 0)
            stHFP = st.file_uploader(
                "Upload values from a Household Financial Profile (HFP) workbook...",
                key="_stHFP" + str(kz.getCaseKey("_xlsx")),
                type=["xlsx", "ods"],
                help=(
                    "An Excel (.xlsx) or OpenDocument (.ods) workbook with one sheet per individual "
                    "containing year-by-year wages, retirement contributions, Roth conversions, and large expenses, "
                    "plus optional household sheets for debts, fixed assets and budget."
                ),
            )
            if stHFP is not None:
                if owb.readHFP(stHFP):
                    kz.setCaseKey("stHFP", stHFP)
                    kz.storeCaseKey("_xlsx", kz.getCaseKey("_xlsx") + 1)
                    st.rerun()
        with hfp_col2:
            tomlexcase = kz.getCaseKey("tomlexcase")
            if tomlexcase is not None and tomlex.hasHFPExample(tomlexcase):
                st.markdown("##### :orange[Load Example HFP Workbook]")
                st.markdown("Read associated HFP workbook.")
                helpmsg = "Load associated *Household Financial Profile* workbook from GitHub."
                st.button(
                    "Load example workbook",
                    help=helpmsg,
                    type="primary",
                    key="create_hfp_example_btn",
                    on_click=_loadHFPExample,
                    args=[tomlexcase],
                )
        st.divider()

    col1, col2, col3 = st.columns(3, gap="small", vertical_alignment="top")
    with col1:
        helpmsg = """`Copy parameters` carries over all parameters to a new case.
Then, click on the `Create case` button once all parameters on this page are set."""
        st.button("Copy parameters :material/content_copy:", on_click=kz.copyCase, disabled=cantcopy, help=helpmsg)
    with col2:
        helpmsg = "`Create case` opens up all other pages in the **Case Setup** section."
        st.button(
            "Create case :material/add:", on_click=owb.createPlan, disabled=cantcreate, type="primary", help=helpmsg
        )

    with col3:
        helpmsg = "`Delete case` removes all parameters associated with the case."
        with st.popover("Delete case :material/delete:", help=helpmsg, key="delete_case_popover", on_change="rerun"):
            st.warning("This cannot be undone.", icon=":material/warning:")
            st.button("Confirm delete", type="primary", on_click=_deleteCase)

# Show progress bar at bottom (only when a case is selected)
if ret is not None:
    cp.show_progress_bar()

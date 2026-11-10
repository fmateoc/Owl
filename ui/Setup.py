"""
Fork: the first-time setup of a household's plan (the "operate it alone" request, 2026-11-10).

A run needs a case file and, for anything year by year, a workbook; writing the case file by
hand is developer work. This page asks for the household's figures in a form -- who, where,
savings, Social Security and pensions, the workbook, the goal -- and makes the first run from
them (`owlplanner.library.household`): no TOML, amounts in dollars, every refusal in words.

Not a wizard: the sections are all on the page and can be filled in any order; what is still
missing is listed above the one button that makes the plan. The answers are kept in the
library folder as they are typed (`setup-draft.json`), so a closed tab loses nothing. The
year-by-year tables stay in Excel: the page reads a workbook the folder already holds, takes
one from elsewhere, or writes an empty one to fill.

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

import copy
from datetime import date

import streamlit as st

import libraryjobs
import sskeys as kz
from owlplanner import tax_local, tax_state
from owlplanner.library import household as H

st.markdown("# :material/assignment: Set up our plan")
kz.divider("orange")
libraryjobs.show_flashes()

manager = libraryjobs.get_manager()
lib = manager.library
home = H.home_dir(lib.root)
today = date.today()

if "setup_answers" not in st.session_state:
    st.session_state["setup_answers"] = H.load_draft(lib.root)
answers = st.session_state["setup_answers"]
before = copy.deepcopy(answers)

if lib.runs():
    st.info("This folder already has a plan. A second household's plan can be made here too, but to "
            "change the one you have, open it and use *Edit as new run*, or the Scenario page for a "
            "what-if.", icon=":material/info:")
st.caption(f"What you type stays on this computer, in `{home}`. It is kept as you go: you can stop "
           "and come back. Amounts are in dollars. Have your latest account statements and Social "
           "Security statements at hand.")


def _money(label, value, key, help=None, container=st):
    """A dollar amount: whole dollars, never negative."""
    return float(container.number_input(label, min_value=0, value=int(round(float(value or 0))), step=1000,
                                        format="%d", key=key, help=help))


# -- 1. who ---------------------------------------------------------------
with st.container(border=True):
    st.markdown("#### 1. Who the plan is for")
    answers["couple"] = st.radio("The plan is for", [True, False], horizontal=True,
                                 index=0 if answers["couple"] else 1, key="setup_couple",
                                 format_func=lambda couple: "A couple" if couple else "One person") is True
    who = H.people(answers)
    for person, col in zip(who, st.columns(len(who), gap="large"), strict=True):
        i = who.index(person)
        person["name"] = col.text_input("First name", value=person["name"], key=f"setup_name{i}", max_chars=31).strip()
        born = H._date(person["born"])
        picked = col.date_input("Date of birth", value=born, min_value=date(today.year - 110, 1, 1),
                                max_value=date(today.year - 18, 12, 31), key=f"setup_born{i}",
                                format="YYYY-MM-DD")
        person["born"] = picked.isoformat() if picked else ""
        c1, c2 = col.columns(2)
        person["sex"] = c1.radio("Sex", ["F", "M"], horizontal=True, index=0 if person["sex"] == "F" else 1,
                                 key=f"setup_sex{i}", help="Read by the survival statistics some of Owl's "
                                                           "stress tests use; the plan itself runs to the age "
                                                           "beside it.")
        person["plan_to_age"] = int(c2.number_input(
            "Plan to age", min_value=60, max_value=120, value=int(person["plan_to_age"]), key=f"setup_age{i}",
            help="The plan runs to the end of the year this person reaches that age. A later age is the "
                 "safer choice: the money has to last longer."))
names = [p["name"] or f"Person {i + 1}" for i, p in enumerate(who)]

# -- 2. where -------------------------------------------------------------
with st.container(border=True):
    st.markdown("#### 2. Where you live")
    states = [""] + tax_state.valid_states()
    c1, c2 = st.columns(2, gap="large")
    answers["state"] = c1.selectbox(
        "State", states, index=states.index(answers["state"]) if answers["state"] in states else 0,
        format_func=lambda s: s or "Not listed (no state income tax is counted)", key="setup_state")
    cities = [""] + (tax_local.valid_localities(answers["state"]) if answers["state"] else [])
    if len(cities) > 1:
        answers["locality"] = c2.selectbox(
            "City with its own income tax", cities,
            index=cities.index(answers["locality"]) if answers["locality"] in cities else 0,
            format_func=lambda c: c or "None of these", key="setup_city")
    else:
        answers["locality"] = ""

# -- 3. savings -----------------------------------------------------------
with st.container(border=True):
    st.markdown("#### 3. Savings today")
    picked = st.date_input("The balances below are as of", value=H._date(answers["balance_date"]),
                           min_value=date(today.year, 1, 1), max_value=date(today.year, 12, 31),
                           key="setup_balance_date", format="YYYY-MM-DD",
                           help="1 January (the year-end statements) is the simplest. For a later date, "
                                "the Documentation's section on the start date says what to adjust.")
    answers["balance_date"] = picked.isoformat() if picked else ""
    if len(who) == 2:
        st.caption("An account in both names: put half under each of you.")
    for person, col in zip(who, st.columns(len(who), gap="large"), strict=True):
        i = who.index(person)
        col.markdown(f"**{names[i]}**")
        person["taxable"] = _money("Taxable (brokerage, bank savings)", person["taxable"], f"setup_txbl{i}",
                                   container=col)
        person["tax_deferred"] = _money("Tax-deferred (IRA, 401k, 403b)", person["tax_deferred"],
                                        f"setup_txdef{i}", container=col)
        person["roth"] = _money("Roth (Roth IRA, Roth 401k)", person["roth"], f"setup_roth{i}", container=col)
        person["hsa"] = _money("Health savings account (HSA)", person["hsa"], f"setup_hsa{i}", container=col)
        known = col.checkbox("I know what was paid for the taxable investments", key=f"setup_basis_on{i}",
                             value=person["cost_basis"] not in (None, ""),
                             help="The cost basis, on the brokerage statement. With it the plan taxes only "
                                  "the gain when it sells; without it Owl estimates the gain.")
        person["cost_basis"] = (_money("Paid for them (cost basis)", person["cost_basis"] or person["taxable"],
                                       f"setup_basis{i}", container=col) if known else None)
    total = sum(float(p[k] or 0) for p in who for k in ("taxable", "tax_deferred", "roth", "hsa"))
    st.markdown(f"Savings entered: **\\${total:,.0f}** in all.")

# -- 4. Social Security and pensions --------------------------------------
with st.container(border=True):
    st.markdown("#### 4. Social Security and pensions")
    ages = [None] + [float(a) for a in range(62, 71)]
    for person, col in zip(who, st.columns(len(who), gap="large"), strict=True):
        i = who.index(person)
        col.markdown(f"**{names[i]}**")
        person["ss_monthly"] = float(col.number_input(
            "Social Security: monthly benefit at full retirement age", min_value=0, step=50, format="%d",
            value=int(round(float(person["ss_monthly"] or 0))), key=f"setup_ss{i}",
            help="On your Social Security statement (ssa.gov/myaccount): the monthly amount at full "
                 "retirement age, in today's dollars. 0 if none."))
        person["ss_age"] = col.selectbox(
            "Starting at age", ages, key=f"setup_ss_age{i}",
            index=ages.index(person["ss_age"]) if person["ss_age"] in ages else 0,
            format_func=lambda a: "Let Owl choose" if a is None else f"{a:.0f}",
            help="Let Owl choose: the claiming-age solve (*Let Owl choose the claiming ages*) tries the "
                 "ages; the other solves hold 67 meanwhile.")
        with col.expander("A pension"):
            person["pension_monthly"] = _money("Monthly pension", person["pension_monthly"], f"setup_pen{i}")
            person["pension_age"] = float(st.number_input(
                "From age", min_value=50, max_value=80, value=int(person["pension_age"]), key=f"setup_pen_age{i}"))
            person["pension_indexed"] = st.checkbox("It rises with inflation", value=bool(person["pension_indexed"]),
                                                    key=f"setup_pen_idx{i}")

# -- 5. the workbook ------------------------------------------------------
with st.container(border=True):
    st.markdown("#### 5. Year by year: wages, budget, a home (an Excel workbook)")
    st.caption("Wages and contributions while someone still works, your budget lines (rent, property "
               "tax, everything else), a home and its loan are tables, and they stay in Excel. Without a "
               "workbook the plan has no wages and spends the same amount every year.")
    found = H.workbooks(home)
    choices = ["none", "existing", "new"]
    words = {"none": "Nothing to add for now",
             "existing": "Use a workbook I have",
             "new": "Give me an empty workbook to fill in Excel"}
    mode = st.radio("The workbook", choices, format_func=words.get, key="setup_book_mode",
                    index=choices.index("existing" if found else "none"))
    workbook = None
    if mode == "existing":
        c1, c2 = st.columns(2, gap="large")
        if found:
            workbook = c1.selectbox(f"In `{home.name}`", found, format_func=lambda p: p.name, key="setup_book_pick")
        else:
            c1.caption(f"No workbook in `{home}` yet.")
        up = c2.file_uploader("Or one from elsewhere (it is copied into the folder)", type=["xlsx"],
                              key="setup_book_up")
        if up is not None:
            workbook = H.keep_upload(home, up.name, up.getvalue())
    elif mode == "new":
        target = home / H.WORKBOOK_NAME
        if target.exists():
            workbook = target
            st.markdown(f"`{target}` is ready. Open it in Excel, fill what applies (its first sheet says "
                        "how), **save and close it**, then read it below.")
        elif st.button(f"Make {H.WORKBOOK_NAME} in this folder", key="setup_book_make"):
            try:
                H.write_workbook(target, answers)
            except Exception as exc:  # noqa: BLE001 - shown, not raised (names missing, a locked folder)
                st.warning(libraryjobs.plain(exc), icon=":material/warning:")
            else:
                st.rerun()
        else:
            st.caption(f"It gets a sheet for {' and '.join(names)} with a row per year of the plan, so fill "
                       "sections 1 and 3 first.")
    summary = None
    if workbook is not None and not H.problems(answers):
        try:
            summary = H.read_workbook(workbook, answers)
        except Exception as exc:  # noqa: BLE001 - the reader's own words name the sheet and column
            st.error(f"`{workbook.name}` cannot be read as it is: {libraryjobs.plain(exc)} Correct it in "
                     "Excel, save, and this page reads it again.", icon=":material/error:")
            workbook = None
        else:
            st.markdown(f"Read from `{workbook.name}`:\n\n" + "\n".join(f"- {libraryjobs.plain(line)}"
                                                                        for line in summary["lines"]))
            st.button("Read it again", key="setup_book_again", help="After saving a change in Excel.")
    elif workbook is not None:
        st.caption(f"`{workbook.name}` is read once the sections above are complete.")

# -- 6. the goal ----------------------------------------------------------
with st.container(border=True):
    st.markdown("#### 6. What the plan should aim for")
    goals = ["spend", "leave"]
    answers["goal"] = st.radio(
        "Goal", goals, index=goals.index(answers["goal"]) if answers["goal"] in goals else 0, key="setup_goal",
        format_func={"spend": "Spend as much as we safely can",
                     "leave": "Leave as much as possible, spending a set amount"}.get)
    if answers["goal"] == "spend":
        answers["bequest"] = _money("Leaving at least (today's dollars; 0 = spend it all by the end)",
                                    answers["bequest"], "setup_bequest",
                                    help="Savings left at the end of the plan. A home is not counted in it.")
    else:
        answers["spending"] = _money("Spending a year (today's dollars, after tax)", answers["spending"],
                                     "setup_spending")
    with st.expander("Two assumptions you can leave as they are"):
        answers["stocks_percent"] = st.slider("Share of the savings in stocks (the rest in bonds), percent",
                                              0, 100, int(answers["stocks_percent"]), step=5,
                                              key="setup_stocks")
        answers["marketplace"] = st.checkbox(
            "Health insurance from the marketplace (healthcare.gov or the state's) before 65",
            value=bool(answers["marketplace"]), key="setup_aca")
        if answers["marketplace"]:
            c1, c2 = st.columns(2)
            answers["marketplace_year"] = int(c1.number_input(
                "From the year", min_value=today.year, max_value=today.year + 40,
                value=max(today.year, int(answers["marketplace_year"] or today.year)), key="setup_aca_year"))
            answers["marketplace_premium"] = _money(
                "Benchmark premium for the household, a year", answers["marketplace_premium"],
                "setup_aca_premium", container=c2,
                help="The second-cheapest Silver plan's yearly premium for the household, before any "
                     "subsidy: the marketplace shows it; the subsidy is worked out from it.")
        st.caption("Everything else (returns, inflation, tax law, how the money is invested over time) "
                   "starts from Owl's standard assumptions and can be changed afterwards with *Edit as new "
                   "run* on the plan's page.")

if answers != before:
    H.save_draft(lib.root, answers)

# -- make the plan --------------------------------------------------------
st.markdown("#### Make the plan")
missing = H.problems(answers)
if missing:
    st.markdown("Still needed:\n\n" + "\n".join(f"- {libraryjobs.plain(m)}" for m in missing))
c1, c2 = st.columns([2, 3], vertical_alignment="bottom")
plan_name = c1.text_input("Name of the plan", value="Our plan", key="setup_plan_name").strip() or "Our plan"
# Enabled whatever is missing (review AL1's lesson: a disabled button swallows the click that
# leaves the last corrected field); a click with something missing says what.
if c2.button("Make our plan and solve it", type="primary", key="setup_make"):
    if missing:
        st.warning("Not yet: see what is still needed, above.", icon=":material/warning:")
    else:
        try:
            scenario = summary["scenario"] if summary is not None else H.first_scenario(answers, None)
            scenario["case"]["case_name"] = plan_name
            saved = lib.save_run(name=plan_name, scenario=scenario,
                                 notes="Made by the first-time setup." + (
                                     f" Workbook: {workbook.name}." if workbook is not None else ""))
        except Exception as exc:  # noqa: BLE001 - shown, not raised
            st.error(f"The plan could not be made: {libraryjobs.plain(exc)}", icon=":material/error:")
        else:
            run = saved.run if saved.created else saved.identical_to
            if lib.baseline() is None:
                lib.pin(run.id)  # the plan the app opens on
            try:
                libraryjobs.watch_jobs(run.id, [manager.enqueue(run, preset="quick")])
            except Exception as exc:  # noqa: BLE001 - saved; the Run page offers Solve
                libraryjobs.flash("warning", f"Saved, not solved yet: {libraryjobs.plain(exc)}")
            H.drop_draft(lib.root)
            st.session_state.pop("setup_answers", None)
            libraryjobs.flash(
                "success",
                f"*{libraryjobs.plain(run.name)}* is made. A first, quick solve is on its way; for "
                "decisions, solve it again with *Careful* (below, under *Solve this run*).")
            st.session_state["library_selected_run"] = run.id
            st.session_state[libraryjobs.SHOW_NEWEST_KEY] = True
            st.switch_page("Run.py")

"""
Scenario page: a run's events and what they generate (design sections 6.1-6.3, step 4).

The scenario is the source of truth of a run (D2): events in plain terms -- work, claiming,
rent, a home purchase, care (D6), a named downturn sequence (step 5b, I11) and the death
ages (I2's longevity) -- beside the hand rows. A year field may name a calendar
year or anchor to another event: "the year after Noa's last work year" (`after:Noa`), "at age
86" (`age:Ari:86`), "the purchase year" (`purchase`), or another event's year (`event:care`,
`event:care+2`) (I1). The builder (library.builder) turns the events into Owl's coupled edits
(section 6.2): the move and school district from the purchase, the marketplace year from the
last work year, the Fixed Assets and Debts rows, the big-ticket outflow, the owner's Budget
lines and the rent rows that end the year before the purchase.

Every generated row, cell and case field is **marked** with the event that produced it
(section 6.3). Markers first (S11): a generated row is regenerated wholesale when the events
change, hand rows are untouched, and an edit to a generated value does not survive a
regeneration -- per-cell overrides with a "back to computed" button are the later increment of
section 6.3. The generated files of a run (Case.toml, HFP.xlsx) are written from this at save
time and frozen (section 5).

What the events do not cover -- balances, PIAs, the assumptions and the Owl settings (section
6.1's People, Accounts and Advanced rows) -- stays in the case dictionary and is edited in the
existing pages ("Edit as new run" on the Run page). The goal and the Roth conversion limits are
case fields too, but this page edits them in its "Goal and conversions" box (ergonomics review
S-2, decision 3), so that one page and one save make a what-if run. Edits on this page are kept
in a session draft per run across page visits (S-2), with a Reset. Saving there keeps the run's
events; what they generate is regenerated from them, and the hand values they replaced are
kept (section 6.3; review X1/X2).

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
import math
from datetime import date

import pandas as pd
import streamlit as st

import libraryjobs
import sskeys as kz
from owlplanner.library import SCHEMA_VERSION, ScenarioError, canonicalize, diff_summaries
from owlplanner.library import builder
from owlplanner.library.sequences import sequences as _sequences
from year_ref_input import year_ref_input

st.markdown("# :material/edit_note: Scenario")
kz.divider("orange")
libraryjobs.show_flashes()  # what the last action said before its rerun (review 3, W3)

manager = libraryjobs.get_manager()
lib = manager.library

runs = list(reversed(lib.runs()))
if not runs:
    st.info("The library has no runs yet: import a case on the Library page.")
    st.stop()

# The run to edit: the one another page asked for ("Edit the scenario" on the Run page), else
# the one edited last in this session (S-2: the selector's own state is dropped with the page,
# and the page used to come back on the newest run, away from the draft), else the newest.
_by_id = {r.id: r for r in runs}
_wanted = st.session_state.pop("library_selected_run", None)
if _wanted in _by_id:
    st.session_state["scenario_page_run"] = _wanted
elif st.session_state.get("scenario_page_run") not in _by_id:
    st.session_state.pop("scenario_page_run", None)
_last = st.session_state.get("scenario_last_run")
# index 0 where the session names the choice: a default beside it draws Streamlit's warning.
_index = list(_by_id).index(_last) if _last in _by_id and _wanted not in _by_id else 0
run = _by_id[st.selectbox("Run to edit", list(_by_id), index=_index, key="scenario_page_run",
                          format_func=lambda i: f"{_by_id[i].name} ({_by_id[i].folder_name})")]
st.session_state["scenario_last_run"] = run.id
scenario = lib.scenario(run.id)
if run.plan_year is not None and run.plan_year != date.today().year:
    # Local-use review D2: a child keeps its parent's plan year, and a run is solved only in
    # its plan year. Said before the edits are typed, not at the refused solve.
    _c1, _c2 = st.columns([4, 1], vertical_alignment="center")
    _c1.warning(f"This run is for {run.plan_year}. A what-if saved from it is for {run.plan_year} too, "
                f"and is not solved in {date.today().year}: start {date.today().year} from it on its "
                "page first, then ask the what-if of that run.", icon=":material/event_repeat:")
    if _c2.button("Open its page", key="scenario_to_run_page"):
        st.session_state["library_selected_run"] = run.id
        st.switch_page("Run.py")

# -- the draft (ergonomics review S-2) -----------------------------------
# Streamlit drops a widget's state when its page is not drawn, so an edit typed here was lost
# on a visit to another page (UX review F3). The page keeps one plain dict per run in the
# session, `scn_draft_<run id>`: every box's value and the three tables as records, written
# after each render and read back as the widgets' `value=` / `data=` when they mount again.
# The editors' `data=` is the base they were mounted with for as long as they stay mounted: a
# data_editor replays its recorded deltas (added rows, edited cells) on whatever `data=` it is
# given, so feeding it the edited rows back would apply the edits twice. Reset drops the draft
# and bumps the version, which is part of every widget key: the widgets mount afresh from the
# run. The draft lasts for the browser session (design section 4's drafts on disk are later).
_VERSION_KEY = f"scn_version_{run.id}"
_DRAFT_KEY = f"scn_draft_{run.id}"
version = int(st.session_state.get(_VERSION_KEY, 0))
# Widget keys follow the run (editing two runs keeps their states apart) and the version.
key = run.id if not version else f"{run.id}_v{version}"
draft = st.session_state.get(_DRAFT_KEY) or {}
if draft.get("version") != version:
    draft = {}
_seen = draft.get("values") or {}
new_draft = {"version": version, "values": {}, "tables": {}, "base": {}, "changes": []}


def _seed(name, default):
    """A box's starting value: the draft's, else the run's (`default`)."""
    return _seen.get(name, default)


def _keep(name, value):
    """Record a box's value in the draft; returns it."""
    new_draft["values"][name] = value
    return value


banner = st.container()  # "Unsaved changes against ...", filled once the edits are assembled

# -- the events --------------------------------------------------------

st.markdown("#### Events")
st.caption(
    "One row or box per event. A year field of the rent, home purchase and care events (work "
    "spans take plain years) takes a calendar year or an anchor: "
    "`age:Ari:86` (the year Ari turns 86), `work:Noa` (Noa's last work year), `after:Noa` "
    "(the year after it), `purchase` (the home purchase's year), or `event:care` / "
    "`event:care+2` (another event's year -- a work span's end, a rent's start -- shifted). "
    "The rent ends the year before the purchase unless it names its own end. "
    "*Months worked* is written for every year of its span (the year work stops is the one "
    "that matters; blank means 12 in a year with wages) -- split the span to give one year "
    "its own value."
)

events = scenario.get("events") or []
names = list((scenario.get("case", {}).get("basic_info") or {}).get("names") or [])
plan_year = scenario.get("plan_year") or date.today().year
# Defaults for an event the run does not have yet: years from the plan year, not the
# household's (review X8). An event the run has shows its own values, and a key it leaves out
# shows the builder's default for it, so an unedited save changes nothing (review X4).
work_rows = [{
    "id": e.get("id"), "person": e.get("person"), "level": e.get("level", "full"),
    "start": e.get("start"), "end": e.get("end"),
    "wages": e.get("wages"), "401k": e.get("k401k"), "employer": e.get("employer"),
    "IRA": e.get("ira"), "months worked": e.get("months_worked"),
} for e in events if e.get("kind") == "work"]
claim_rows = [{"id": e.get("id"), "person": e.get("person"), "age": e.get("age")}
              for e in events if e.get("kind") == "claim"]
death_rows = [{"id": e.get("id"), "person": e.get("person"), "age": e.get("age")}
              for e in events if e.get("kind") == "death"]
rent = next((e for e in events if e.get("kind") == "rent"), None)
buy = next((e for e in events if e.get("kind") == "purchase"), None)
care = next((e for e in events if e.get("kind") == "care"), None)
down = next((e for e in events if e.get("kind") == "downturn"), None)


@st.cache_data
def _locality_choices(state):
    from owlplanner import tax_local

    return [""] + tax_local.valid_localities(state) if state else [""]


@st.cache_data
def _district_choices(state):
    from owlplanner import star

    try:
        return [""] + star.valid_districts(state) if state else [""]
    except (KeyError, ValueError):  # a state with no STAR data
        return [""]


def _choices(options, value):
    """The dropdown's options, with the event's own value kept when the data lacks it."""
    return list(options) + ([value] if value and value not in options else [])


def _none_label(value):
    return value or "(none)"


def _place_to_store(locality, district, move, case_district, original):
    """The place's locality and district as the event stores them.

    A district picked as none is "-" on a purchase without a move where the case has a
    district (a blank keeps the case's, UX review B2). Where the picked value builds the same
    as the event's own spelling, the event keeps its spelling: an unedited save changes
    nothing (review X4)."""
    if not move and not district and case_district:
        district = builder.NO_PLACE

    def built_district(value):
        if move or str(value or "").strip():
            return builder.place_text(value)
        return case_district

    if original is not None:
        if built_district(original.get("school_district")) == built_district(district):
            district = original.get("school_district", "")
        if not move or builder.place_text(original.get("locality")) == builder.place_text(locality):
            locality = original.get("locality", "")
    return locality, district


def _bound(value, low, high):
    """(min, max) for a number box, or None where the stored value is already outside it: a
    Streamlit box refuses a value outside its bounds, and the builder's own range check names
    the problem instead (QW-4)."""
    v = float(value)
    return (low if low is None or v >= low else None, high if high is None or v <= high else None)


def _share_from_percent(shown, original):
    """A share the page shows in percent (UX review Q19), as the event stores it: the event's
    own value while the shown percent is unchanged, so an unedited save changes nothing (X4)."""
    if math.isclose(float(shown), float(original) * 100.0, rel_tol=0.0, abs_tol=1e-9):
        return original
    return float(shown) / 100.0


def _event_id(column, default, current, widget_key):
    """The event's id, behind "Advanced" (UX review Q19): other events anchor on it
    (`event:care+2`) and the generated rows are marked with it, so it stays editable."""
    with column.popover("Advanced"):
        value = st.text_input("Event id", value=current, key=widget_key,
                              help="Other events can refer to this one by its id "
                                   f"(a year as `event:{current or default}+2`), and the rows it "
                                   "generates are marked with it.")
    return value


def _payer_label(value):
    return value if value else (f"default ({names[0]})" if names else "default")


def _present(value):
    return value is not None and not (isinstance(value, float) and pd.isna(value)) and value != ""


def _filled(rows):
    return [r for r in rows if any(_present(v) for k, v in r.items() if k != "id")]


def _blank_rows(rows, columns):
    """A table to edit: the events' rows, and one empty row to type into."""
    return pd.DataFrame([*rows, {c: None for c in columns}], columns=columns)


LEVEL_LABELS = {"full": "full time", "part": "part time"}


def _person_column(label="person"):
    return st.column_config.SelectboxColumn(label, options=names)


def _table(name, rows, columns, column_config):
    """One events table, through the draft (see "the draft" above).

    Mounted (its widget state is in the session), the editor gets the base it was mounted
    with; mounting, it gets the draft's rows (else the run's) and one empty row. The event id
    stays in the records, hidden: other events anchor on it and the generated rows carry it."""
    widget = f"scn_{name}_{key}"
    if widget in st.session_state and name in (draft.get("base") or {}):
        base = draft["base"][name]
    else:
        source = (draft.get("tables") or {}).get(name, rows)
        base = _blank_rows(_filled(source), columns).to_dict("records")
    new_draft["base"][name] = base
    frame = st.data_editor(pd.DataFrame(base, columns=columns), num_rows="dynamic", hide_index=True,
                           key=widget, column_config={"id": None, **column_config})
    new_draft["tables"][name] = frame.to_dict("records")
    return frame


work_df = _table(
    "work", work_rows, ["id", "person", "level", "start", "end", "wages", "401k",
                        "employer", "IRA", "months worked"],
    {"person": _person_column(),
     "level": st.column_config.SelectboxColumn("level", options=list(LEVEL_LABELS), default="full",
                                               help="Blank: full time.",
                                               format_func=LEVEL_LABELS.get),
     "start": st.column_config.NumberColumn("start (year)", format="%d", step=1),
     "end": st.column_config.NumberColumn("end (last work year)", format="%d", step=1),
     "wages": st.column_config.NumberColumn("wages ($/yr, in AGI)"),
     "401k": st.column_config.NumberColumn("401k deferral"),
     "employer": st.column_config.NumberColumn("employer contribution"),
     "IRA": st.column_config.NumberColumn("IRA contribution"),
     "months worked": st.column_config.NumberColumn("months worked (0-12)")},
)
st.markdown("*Claiming* (an empty age lets Owl choose)")
claim_df = _table("claim", claim_rows, ["id", "person", "age"], {"person": _person_column()})
st.markdown("*Death* (a person's life horizon in whole years of age: \"first death at 75\"; "
            "Owl's own death mechanics -- the survivor's share, single filing -- do the rest)")
death_df = _table("death", death_rows, ["id", "person", "age"], {"person": _person_column()})


def _slug(text):
    return "-".join(str(text or "").lower().split()) or "x"


def _with_ids(rows, kind):
    """The table's filled rows, each with its event id: a row's own, else one made from its
    person (and a work span's start year, as the synthetic suite's `work-ari-2026`), unique."""
    rows = [dict(r) for r in _filled(rows)]
    taken = {r["id"] for r in rows if _present(r.get("id"))}
    for row in rows:
        if _present(row.get("id")):
            continue
        stem = f"{kind}-{_slug(row.get('person'))}"
        if kind == "work" and _present(row.get("start")):
            stem += f"-{int(row['start'])}"
        eid, n = stem, 2
        while eid in taken:
            eid, n = f"{stem}-{n}", n + 1
        row["id"] = eid
        taken.add(eid)
    return rows


_table_rows = {"work": _with_ids(work_df.to_dict("records"), "work"),
               "claim": _with_ids(claim_df.to_dict("records"), "claim"),
               "death": _with_ids(death_df.to_dict("records"), "death")}


def _box_id(name, event, default):
    """A box's event id as it stands now (its widget, else the draft, else the run's)."""
    return (st.session_state.get(f"scn_{name}_id_{key}") or _seen.get(f"{name}_id")
            or (event or {}).get("id") or default)


def _describe(row, kind):
    if kind == "work":
        return f"{row.get('person')}'s work, {int(row['start']) if _present(row.get('start')) else '?'}" \
               f"-{int(row['end']) if _present(row.get('end')) else '?'}"
    return f"{row.get('person')}'s {kind}"


# The events another year field can anchor on ("Another event's year"), with a description.
_anchor_ids = [(r["id"], _describe(r, kind)) for kind in ("work", "claim", "death") for r in _table_rows[kind]]


def _box_on(name, event):
    """Whether a box's event is on as it stands now (its checkbox, else the draft, else the run)."""
    widget = f"scn_{name}_on_{key}"
    if widget in st.session_state:
        return bool(st.session_state[widget])
    return bool(_seen.get(f"{name}_on", event is not None))


_anchor_ids += [(_box_id(name, event, default), label) for name, event, default, label in (
    ("rent", rent, "rent", "the rent"), ("buy", buy, "buy", "the home purchase"),
    ("care", care, "care", "the care span"), ("down", down, "downturn", "the downturn"))
    if _box_on(name, event)]


def _year_box(column, label, name, stored, *, blank=None, own=None, default_year=None):
    """A year field through the structured picker (S-2, decision 4) and the draft."""
    text = _seed(name, stored)
    return _keep(name, year_ref_input(column, label, text, f"scn_{name}_{key}", names=names, ids=_anchor_ids,
                                      default_year=default_year or plan_year, blank=blank, own_id=own))


with st.expander("Rent", expanded=rent is not None):
    rent_on = _keep("rent_on", st.checkbox("The household rents", value=_seed("rent_on", rent is not None),
                                           key=f"scn_rent_on_{key}"))
    r1, r2, r3, r4 = st.columns(4)
    rent_monthly = _keep("rent_monthly", r1.number_input(
        "Monthly rent ($)", value=_seed("rent_monthly", float((rent or {}).get("monthly", 4000))),
        key=f"scn_rent_monthly_{key}"))
    rent_id = _keep("rent_id", _event_id(r4, "rent", _seed("rent_id", (rent or {}).get("id", "rent")),
                                         f"scn_rent_id_{key}"))
    rent_start = _year_box(r2, "From", "rent_start", builder.year_ref_text((rent or {}).get("start", plan_year)),
                           own=rent_id)
    rent_flat = _year_box(r3, "Flat through", "rent_flat",
                          builder.year_ref_text((rent or {}).get("flat_until", plan_year + 1)), own=rent_id,
                          default_year=plan_year + 1)
    rent_end = _year_box(r4, "To", "rent_end",
                         "" if not rent or "end" not in rent else builder.year_ref_text(rent["end"]),
                         blank="the year before the purchase, or the plan end", own=rent_id)

with st.expander("Home purchase", expanded=buy is not None):
    buy_on = _keep("buy_on", st.checkbox("Buy a home", value=_seed("buy_on", buy is not None),
                                         key=f"scn_buy_on_{key}"))
    financing = (buy or {}).get("financing") or {"kind": "cash"}
    if buy is not None:  # the event's own terms, the builder's defaults for what it leaves out
        terms = {**builder.FINANCING_DEFAULTS["loan"], **builder.FINANCING_DEFAULTS["cash"], **financing}
    else:  # suggestions for a new purchase, shown in the fields and saved as typed
        terms = {"down": 0.20, "closing": 0.03, "extra": 0.02}
    b1, b2, b3, b4 = st.columns(4)
    buy_name = _keep("buy_name", b1.text_input("Home (the rows' name)",
                                               value=_seed("buy_name", (buy or {}).get("name", "home")),
                                               key=f"scn_buy_name_{key}"))
    buy_price = _keep("buy_price", b2.number_input(
        "Price (today's \\$)", value=_seed("buy_price", float((buy or {}).get("price", 700000))),
        key=f"scn_buy_price_{key}"))
    buy_id = _keep("buy_id", _event_id(b4, "buy", _seed("buy_id", (buy or {}).get("id", "buy")),
                                       f"scn_buy_id_{key}"))
    # A new purchase defaults to the year after the plan year (review X8: "purchase" anchored
    # the purchase to itself).
    buy_year = _year_box(b3, "Year", "buy_year", builder.year_ref_text((buy or {}).get("year") or plan_year + 1),
                         own=buy_id, default_year=plan_year + 1)
    s1, s2, s3, s4 = st.columns(4)
    buy_sale = _year_box(s1, "Sold", "buy_sale",
                         "" if not buy or "sale" not in buy else builder.year_ref_text(buy["sale"]),
                         blank="kept", own=buy_id)
    # A dropdown of the case's people (UX review Q19); no choice is the builder's default, the
    # first person, and stays no choice so that an unedited save changes nothing.
    _payer = _seed("buy_pay_on", (buy or {}).get("pay_on"))
    _payers = _choices([None, *names], _payer)
    buy_pay_on = _keep("buy_pay_on", s2.selectbox(
        "Paid from (person)", _payers, index=_payers.index(_payer), format_func=_payer_label,
        key=f"scn_buy_pay_on_{key}", help="Whose savings pay the price and the closing costs."))
    _kind = _seed("buy_kind", "loan" if financing.get("kind") == "loan" else "cash")
    buy_kind = _keep("buy_kind", s3.selectbox("Financing", ["cash", "loan"], index=["cash", "loan"].index(_kind),
                                              key=f"scn_buy_kind_{key}"))
    buy_debt_name = _keep("buy_debt", s4.text_input("Loan's name", value=_seed("buy_debt", financing.get("name", "")),
                                                    key=f"scn_buy_debt_{key}"))
    f1, f2, f3, f4, f5 = st.columns(5)
    buy_term = _keep("buy_term", f1.number_input(
        "Term (years)", value=_seed("buy_term", float(financing.get("term", 30))),
        min_value=_bound(financing.get("term", 30), 1.0, None)[0], key=f"scn_buy_term_{key}"))
    buy_rate = _keep("buy_rate", f2.number_input(
        "Rate (%)", value=_seed("buy_rate", float(financing.get("rate", 6.25))),
        min_value=_bound(financing.get("rate", 6.25), 0.0, None)[0], key=f"scn_buy_rate_{key}"))

    def _percent_box(column, label, share, step, name):
        # Shares shown in percent (UX review Q19: 0.2 read as a fifth of a percent); the event
        # keeps shares, converted here only. Bounded 0-100 (QW-4), unless a stored value is
        # already outside: the builder's range check then says why it does not build.
        shown = float(share) * 100.0
        low, high = _bound(shown, 0.0, 100.0)
        typed = _keep(name, column.number_input(label, value=_seed(name, shown), step=step, format="%.2f",
                                                min_value=low, max_value=high, key=f"scn_{name}_{key}"))
        return _share_from_percent(typed, share)

    buy_down = _percent_box(f3, "Down payment (%)", terms["down"], 1.0, "buy_down")
    buy_closing = _percent_box(f4, "Closing costs (% of the price)", terms["closing"], 0.5, "buy_closing")
    buy_extra = _percent_box(f5, "Loan closing (% of the loan)", terms["extra"], 0.5, "buy_extra")
    if buy_kind == "loan":
        _shown = {"kind": "loan", "term": buy_term, "rate": buy_rate, "down": buy_down,
                  "closing": buy_closing, "extra": buy_extra}
        _problem = builder.financing_range_error(_shown)
        if _problem:
            st.error(f"This purchase does not build: {_problem}.", icon=":material/error:")
        for _note in builder.financing_warnings(_shown):  # QW-4: a slip of units, not refused
            st.warning(_note, icon=":material/flag:")
    # The place starts from the case's own residence (UX review B2): a new purchase shows the
    # case's state, locality and district, and a purchase without a move that leaves its
    # district blank builds with the case's, so it shows that one. A district picked as none
    # is saved as "-" where the case has one (a blank would keep it).
    hand_info = (scenario.get("case") or {}).get("basic_info") or {}
    case_place = {"state": hand_info.get("state") or builder.PLACE_DEFAULTS["state"],
                  "locality": hand_info.get("locality") or "",
                  "school_district": hand_info.get("school_district") or ""}
    event_place = dict((buy or {}).get("place") or {})
    if buy is None:
        place = {**builder.PLACE_DEFAULTS, **case_place}
    else:
        place = {**builder.PLACE_DEFAULTS, **event_place}
        if not place["move"] and not str(place["school_district"] or "").strip():
            place["school_district"] = case_place["school_district"]
    for field in ("locality", "school_district"):
        if place[field] == builder.NO_PLACE:
            place[field] = ""
    # The draft's place (the widgets' values when the page was last drawn) wins on mount.
    place = {**place, **{f: _seen[f"place_{f}"] for f in ("state", "locality", "school_district", "move")
                         if f"place_{f}" in _seen}}
    costs = (buy or {}).get("costs") or {}
    p1, p2, p3, p4 = st.columns(4)
    _state_typed = _keep("place_state", p1.text_input("State", value=place["state"], key=f"scn_place_state_{key}"))
    place_state = _state_typed.strip().upper()
    if buy is not None and str(event_place.get("state") or "").strip().upper() == place_state:
        place_state = event_place["state"]  # the event's own spelling: no phantom edit (AK6)
    # The pre-filled locality and district belong to the state they came from: another state
    # starts both pickers at "(none)" (independent review AK2: the case's Yonkers stayed under
    # CT, and the run failed only at solve time).
    if place_state.upper() != str(place["state"] or "").strip().upper():
        place = {**place, "locality": "", "school_district": ""}
    place_move = _keep("place_move", p4.checkbox(
        "Move there", value=bool(place.get("move")), key=f"scn_place_move_{key}",
        help="The household moves to the new home in the purchase year (a "
             "move in the case). Without it, the home is where the case "
             "already lives: its locality stays, its school district is the one "
             "picked here."))
    _localities = _choices(_locality_choices(place_state.upper()), place["locality"])
    _districts = _choices(_district_choices(place_state.upper()), place["school_district"])
    for _k, _opts in ((f"scn_place_locality_{key}", _localities), (f"scn_place_district_{key}", _districts)):
        if _k in st.session_state and st.session_state[_k] not in _opts:
            st.session_state.pop(_k)  # another state's value: start over from the default
    _shown_locality = _keep("place_locality", p2.selectbox(
        "Locality (with a move)", _localities, index=_localities.index(place["locality"]),
        format_func=_none_label, key=f"scn_place_locality_{key}", disabled=not place_move,
        help="Local income tax at the new home. Without a move the case's own locality stays."))
    _shown_district = _keep("place_school_district", p3.selectbox(
        "School district", _districts, index=_districts.index(place["school_district"]),
        format_func=_none_label, key=f"scn_place_district_{key}",
        help="For the NY STAR credit, in the years with a property tax line. Starts from the "
             "case's own district."))
    place_locality, place_district = _place_to_store(
        _shown_locality, _shown_district, bool(place_move), case_place["school_district"],
        event_place if buy is not None else None)
    c1, c2, c3, c4, c5 = st.columns(5)
    cost_tax = _keep("cost_tax", c1.number_input("Property tax (\\$/yr, today's \\$)",
                                                 value=_seed("cost_tax", float(costs.get("property tax", 0))),
                                                 key=f"scn_cost_tax_{key}"))
    cost_hoa = _keep("cost_hoa", c2.number_input("HOA / common charges ($/yr)",
                                                 value=_seed("cost_hoa", float(costs.get("hoa", 0))),
                                                 key=f"scn_cost_hoa_{key}"))
    cost_ins = _keep("cost_ins", c3.number_input("Insurance ($/yr)",
                                                 value=_seed("cost_ins", float(costs.get("insurance", 0))),
                                                 key=f"scn_cost_ins_{key}"))
    buy_growth = _keep("buy_growth", c4.number_input(
        "Value growth (% real)", value=_seed("buy_growth", float((buy or {}).get("growth", 0.0))),
        key=f"scn_buy_growth_{key}"))
    buy_commission = _keep("buy_commission", c5.number_input(
        "Selling cost (%)", value=_seed("buy_commission", float((buy or {}).get("commission", 0.0))),
        key=f"scn_buy_commission_{key}"))
    if buy_on and not (cost_tax or cost_hoa or cost_ins):
        st.warning("Property tax, HOA and insurance are all 0: owning the home costs nothing in "
                   "this run. Enter them, unless that is what you mean.", icon=":material/warning:")

with st.expander("Care", expanded=care is not None):
    care_on = _keep("care_on", st.checkbox("A care span", value=_seed("care_on", care is not None),
                                           key=f"scn_care_on_{key}"))
    c1, c2, c3, c4 = st.columns(4)
    care_name = _keep("care_name", c1.text_input("Line name",
                                                 value=_seed("care_name", (care or {}).get("name", "care")),
                                                 key=f"scn_care_name_{key}"))
    care_amount = _keep("care_amount", c2.number_input(
        "Cost (\\$/yr, today's \\$)", value=_seed("care_amount", float((care or {}).get("amount", 110000))),
        key=f"scn_care_amount_{key}"))
    care_id = _keep("care_id", _event_id(c4, "care", _seed("care_id", (care or {}).get("id", "care")),
                                         f"scn_care_id_{key}"))
    _care_default = {"anchor": "age", "person": names[0], "age": 86} if names else plan_year
    care_year = _year_box(c3, "From", "care_year", builder.year_ref_text((care or {}).get("year") or _care_default),
                          own=care_id)
    care_end = _year_box(c4, "To", "care_end",
                         "" if not care or "end" not in care else builder.year_ref_text(care["end"]),
                         blank="the plan end", own=care_id)
    care_essential = _keep("care_ess", st.checkbox(
        "Essential (paid whatever the spending level)",
        value=_seed("care_ess", bool((care or {}).get("essential", True))), key=f"scn_care_ess_{key}"))

with st.expander("Downturn sequence", expanded=down is not None):
    st.caption(
        "A named stress sequence overlaid on the run's own rate method at a chosen year: the "
        "years inside the window take the sequence's returns, the years outside keep the "
        "case's own method. The overlay becomes the run's table of yearly rates; a run that "
        "already reads a rates table cannot take one."
    )
    down_on = _keep("down_on", st.checkbox("Overlay a named downturn sequence",
                                           value=_seed("down_on", down is not None),
                                           key=f"scn_down_on_{key}"))
    _seq_names = sorted(_sequences())
    d1, d2, d3 = st.columns(3)
    _chosen = _seed("down_seq", (down or {}).get("sequence", _seq_names[0]) if _seq_names else None)
    down_seq = _keep("down_seq", d1.selectbox(
        "Sequence", _seq_names, index=max(0, _seq_names.index(_chosen)) if _chosen in _seq_names else 0,
        key=f"scn_down_seq_{key}"))
    down_id = _keep("down_id", _event_id(d3, "downturn", _seed("down_id", (down or {}).get("id", "downturn")),
                                         f"scn_down_id_{key}"))
    down_start = _year_box(d2, "From", "down_start", builder.year_ref_text((down or {}).get("start") or plan_year),
                           own=down_id)
    if down_seq:
        _meta = _sequences()[down_seq]
        st.caption(f"{_meta['description']} *(source: {_meta['source']})*")


# The keys each box edits; any other key of the run's event (a purchase's `type` or `basis`,
# say) is carried through a save unchanged (review X4: they were dropped).
_MANAGED = {
    "work": {"id", "kind", "person", "level", "start", "end", "wages", "k401k", "employer", "ira",
             "months_worked"},
    "rent": {"id", "kind", "monthly", "start", "flat_until", "end"},
    "purchase": {"id", "kind", "name", "price", "year", "pay_on", "growth", "commission", "place",
                 "costs", "sale", "financing"},
    "care": {"id", "kind", "name", "amount", "year", "end", "essential"},
    "downturn": {"id", "kind", "sequence", "start"},
    "death": {"id", "kind", "person", "age"},
}


def _kept(event, kind):
    """The run's event's keys that no widget edits."""
    return {k: copy.deepcopy(v) for k, v in (event or {}).items() if k not in _MANAGED[kind]}


_work_by_id = {e.get("id"): e for e in events if e.get("kind") == "work"}


def _work_events(rows):
    out = []
    for row in rows:
        if not any(_present(v) for v in row.values()):
            continue  # the empty row the editor adds
        event = {**_kept(_work_by_id.get(row["id"]), "work"),
                 "id": row["id"], "kind": "work", "person": row["person"],
                 "level": row["level"] if _present(row.get("level")) else "full",
                 "start": int(row["start"]), "end": int(row["end"])}  # a table cell is a float
        for column, field in (("wages", "wages"), ("401k", "k401k"), ("employer", "employer"),
                              ("IRA", "ira"), ("months worked", "months_worked")):
            if _present(row.get(column)):
                event[field] = int(row[column]) if field == "months_worked" else row[column]
        out.append(event)
    return out


def _claim_events(rows):
    out = []
    for row in rows:
        if not any(_present(v) for v in row.values()):
            continue
        age = row.get("age")
        out.append({"id": row["id"], "kind": "claim", "person": row["person"],
                    "age": float(age) if _present(age) else None})
    return out


def _death_events(rows):
    out = []
    for row in rows:
        if not any(_present(v) for v in row.values()):
            continue
        age = row.get("age")
        if not _present(age):
            raise ScenarioError(f"death {row.get('id')!r}: give the age (whole years) at death")
        try:
            years = float(age)
        except (TypeError, ValueError):
            raise ScenarioError(f"death {row.get('id')!r}: the age is not a number: {age!r}") from None
        if years != int(years):
            raise ScenarioError(f"death {row.get('id')!r}: the age must be whole years, got {age!r}")
        out.append({"id": row["id"], "kind": "death", "person": row["person"], "age": int(years)})
    return out


def _year_ref(text, where, ids=()):
    # The scenario's ids settle `event:<id>-<n>` for an id that ends in -<digits> (review X5).
    return builder.parse_year_ref(text, where, ids=ids) if _present(text) else None


def _assemble():
    """The events list from the widgets above (ScenarioError with the field that is wrong)."""
    events = _work_events(_table_rows["work"])
    events += _claim_events(_table_rows["claim"])
    events += _death_events(_table_rows["death"])
    ids = [e["id"] for e in events]
    ids += [i.strip() or d for on, i, d in ((rent_on, rent_id, "rent"), (buy_on, buy_id, "buy"),
                                            (care_on, care_id, "care"), (down_on, down_id, "downturn")) if on]

    def _year(text, where):
        return _year_ref(text, where, ids)

    if rent_on:
        event = {**_kept(rent, "rent"),
                 "id": rent_id.strip() or "rent", "kind": "rent", "monthly": rent_monthly,
                 "start": _year(rent_start, "rent.from"), "flat_until": _year(rent_flat, "rent.flat through")}
        if _present(rent_end):
            event["end"] = _year(rent_end, "rent.to")
        events.append(event)
    if buy_on:
        event = {**_kept(buy, "purchase"),
                 "id": buy_id.strip() or "buy", "kind": "purchase", "name": buy_name.strip() or "home",
                 "price": buy_price, "year": _year(buy_year, "purchase.year"),
                 "pay_on": buy_pay_on or None,
                 "growth": buy_growth, "commission": buy_commission,
                 "place": {"state": place_state, "locality": place_locality,
                           "school_district": place_district, "move": bool(place_move)},
                 "costs": {"property tax": cost_tax, "hoa": cost_hoa, "insurance": cost_ins}}
        if _present(buy_sale):
            event["sale"] = _year(buy_sale, "purchase.sold")
        if buy_kind == "loan":
            event["financing"] = {"kind": "loan", "term": int(buy_term), "rate": buy_rate,
                                  "down": buy_down, "closing": buy_closing, "extra": buy_extra}
            if _present(buy_debt_name):
                event["financing"]["name"] = buy_debt_name.strip()
        else:
            event["financing"] = {"kind": "cash", "closing": buy_closing}
        events.append(event)
    if care_on:
        event = {**_kept(care, "care"),
                 "id": care_id.strip() or "care", "kind": "care", "name": care_name.strip() or "care",
                 "amount": care_amount, "year": _year(care_year, "care.from"),
                 "essential": bool(care_essential)}
        if _present(care_end):
            event["end"] = _year(care_end, "care.to")
        events.append(event)
    if down_on:
        events.append({**_kept(down, "downturn"),
                       "id": down_id.strip() or "downturn", "kind": "downturn",
                       "sequence": down_seq, "start": _year(down_start, "downturn.from")})
    return events


# -- the goal and the Roth conversions (S-2, decision 3) ----------------
# Hand case fields, not events: no event generates them (`builder.build`'s case fields are the
# residence, the life horizon, the marketplace year, the claiming ages and the rates table), so
# they are saved as typed and read in words by the change summary (`scenario.PATH_LABELS`). A
# field the case leaves out stays out unless its box is changed: an unedited save changes
# nothing. Amounts are in the case's own `units` (thousands of dollars by default), as stored.
_hand_case = scenario.get("case") or {}
_so = dict(_hand_case.get("solver_options") or {})
_op = dict(_hand_case.get("optimization_parameters") or {})
try:
    from owlplanner import utils as _u

    _unit = {1: "\\$", 1000: "\\$k", 1_000_000: "\\$M"}.get(_u.getUnits(_so.get("units", "k")), "units")
except ValueError:
    _unit = "units"
_last_year = _u.last_year_entered(plan_year)
_OBJECTIVES = {"maxSpending": "Spend as much as possible (keep a bequest target)",
               "maxBequest": "Leave as much as possible (spend a set amount)"}
_settings = {}  # path -> (the value as the case holds it, the value the box shows now, present before)
_clamped = []


def _year_shown(name, value, low, high, label):
    """A stored year inside the box's bounds (#250's last_year_entered), the move named on the page."""
    year = int(value)
    if low <= year <= high:
        return year
    moved = min(max(year, low), high)
    where = f"past the last year accepted, {high}" if year > high else f"before {low}"
    _clamped.append(f"{label}: {year} is {where}; shown as {moved} (kept unless you change it)")
    return moved


with st.expander("Goal and conversions", expanded=False):
    st.caption("The objective and the Roth conversion limits of this run, as on the case pages' Goals and "
               "Run Options. Changing one here saves a new run like any other edit on this page.")
    g1, g2 = st.columns(2)
    _obj0 = _op.get("objective", "maxSpending")
    _objs = _choices(list(_OBJECTIVES), _obj0)
    _obj = _keep("goal_objective", g1.selectbox(
        "Objective", _objs, index=_objs.index(_seed("goal_objective", _obj0)),
        format_func=lambda o: _OBJECTIVES.get(o, o), key=f"scn_goal_objective_{key}"))
    _settings["optimization_parameters.objective"] = (_obj0, _obj, "objective" in _op)
    if _obj == "maxSpending":
        _b0 = float(_so.get("bequest", 0) or 0)
        _b = _keep("goal_bequest", g2.number_input(
            f"Bequest target (today's {_unit})", min_value=0.0 if _b0 >= 0 else None,
            value=_seed("goal_bequest", _b0), key=f"scn_goal_bequest_{key}",
            help="What the plan must leave at the end, in today's dollars."))
        _settings["solver_options.bequest"] = (_so.get("bequest"), _b if _b != _b0 else _so.get("bequest"),
                                               "bequest" in _so)
    else:
        _n0 = float(_so.get("netSpending", 0) or 0)
        _n = _keep("goal_spending", g2.number_input(
            f"Net spending, first year (today's {_unit}/yr)", min_value=0.0 if _n0 >= 0 else None,
            value=_seed("goal_spending", _n0), key=f"scn_goal_spending_{key}",
            help="The spending the plan keeps while it maximizes what is left at the end."))
        _settings["solver_options.netSpending"] = (_so.get("netSpending"),
                                                   _n if _n != _n0 else _so.get("netSpending"),
                                                   "netSpending" in _so)
    k1, k2, k3 = st.columns(3)
    _cap_present = "maxRothConversion" in _so
    _cap_on = _keep("roth_cap_on", k1.checkbox("Cap annual Roth conversions", value=_seed("roth_cap_on", _cap_present),
                                               key=f"scn_roth_cap_on_{key}",
                                               help="Off: no cap (any conversion the plan finds worth it)."))
    _cap0 = float(_so.get("maxRothConversion", 50) or 0)
    _cap = _keep("roth_cap", k1.number_input(
        f"Maximum annual Roth conversion (nominal {_unit})", min_value=0.0 if _cap0 >= 0 else None,
        value=_seed("roth_cap", _cap0), disabled=not _cap_on, key=f"scn_roth_cap_{key}",
        help="0 means no conversions. A year held fixed in the workbook is not bound by it."))
    if not _cap_on:
        _settings["solver_options.maxRothConversion"] = (_so.get("maxRothConversion"), None, _cap_present)
    else:
        _settings["solver_options.maxRothConversion"] = (
            _so.get("maxRothConversion"), _so.get("maxRothConversion") if _cap_present and _cap == _cap0 else _cap,
            _cap_present)
    _start0 = _so.get("startRothConversions")
    _start_shown = _year_shown("roth_start", _start0 if _start0 is not None else plan_year, plan_year, _last_year,
                               "Roth conversions start")
    _start = int(_keep("roth_start", k2.number_input(
        "Year to start considering Roth conversions", value=_seed("roth_start", _start_shown), step=1,
        min_value=plan_year, max_value=_last_year, format="%d", key=f"scn_roth_start_{key}")))
    _settings["solver_options.startRothConversions"] = (
        _start0, _start0 if _start == _start_shown else _start, _start0 is not None)
    _stop0 = _so.get("stopRothConversions")
    _stop_on = _keep("roth_stop_on", k3.checkbox("Stop Roth conversions mid-plan",
                                                 value=_seed("roth_stop_on", _stop0 is not None),
                                                 key=f"scn_roth_stop_on_{key}",
                                                 help="Off: conversions are considered to the plan's end."))
    _stop_low = max(_start, plan_year)
    _stop_default = min(max(plan_year + 10, _stop_low), _last_year)
    _stop_shown = _year_shown("roth_stop", _stop0 if _stop0 is not None else _stop_default,
                              max(_start_shown, plan_year), _last_year, "Roth conversions stop")
    _stop_key = f"scn_roth_stop_{key}"
    if isinstance(st.session_state.get(_stop_key), (int, float)) and st.session_state[_stop_key] < _stop_low:
        st.session_state[_stop_key] = _stop_low
    _stop = int(_keep("roth_stop", k3.number_input(
        "Year to stop considering Roth conversions", value=min(max(int(_seed("roth_stop", _stop_shown)), _stop_low),
                                                               _last_year),
        step=1, min_value=_stop_low, max_value=_last_year, format="%d", disabled=not _stop_on,
        key=_stop_key, help="No conversions in this year or later.")))
    _settings["solver_options.stopRothConversions"] = (
        _stop0, (_stop0 if _stop0 is not None and _stop == _stop_shown else _stop) if _stop_on else None,
        _stop0 is not None)
    if _clamped:
        st.caption("; ".join(_clamped) + ".")


def _apply_settings(case):
    """The case with the box's values: a field written only when it changes what the case
    holds, removed when switched off."""
    case = copy.deepcopy(case)
    for path, (old, new, present) in _settings.items():
        section, field = path.split(".")
        if new is None:
            if present:
                case[section].pop(field, None)
        elif new != old:
            case.setdefault(section, {})[field] = new
    return case


edited = copy.deepcopy(scenario)
built = None
try:
    edited["case"] = _apply_settings(edited.get("case") or {})
    edited["events"] = _assemble()
    # Canonical cells (T1/V3): the widgets re-type ints as floats, which must not move the
    # inputs hash or the change summary (review U2).
    edited = canonicalize(edited)
    built = builder.build(edited)
except ScenarioError as exc:
    st.error(f"Not buildable yet: {exc}")
except Exception as exc:  # noqa: BLE001 - shown to the user, not raised
    st.error(f"Cannot build this scenario yet: {exc}")

# -- what the events generate (marked) ---------------------------------

st.markdown("#### What the events generate (marked)")
st.caption(
    "Every generated row, cell and case field records which event produced it. A generated "
    "row is regenerated whole when the events change and rows typed by hand are untouched; an "
    "edit to a generated value does not survive a regeneration (keeping such an edit is not "
    "built yet)."
)
if built is not None:
    _case, tables, provenance = built

    def _cell(row, columns, column):
        return row[columns.index(column)] if column in columns else None

    rows = []
    for mark, event_id in sorted(provenance["rows"].items()):
        table, name = mark.split("|", 1)
        sheet = tables.get(table) or {}
        columns = sheet.get("columns") or []
        found = (next((r for r in sheet.get("rows") or [] if _cell(r, columns, "name") == name), None)
                 if columns else None)
        row = {"sheet": table, "name": name, "from event": event_id}
        if found is not None:
            row["type"] = _cell(found, columns, "type")
            if table == "Debts":  # a loan: one year and a term, not a span (review U9)
                row["years"] = f"{_cell(found, columns, 'year')}, {_cell(found, columns, 'term')}-year loan"
                row["amount / value ($)"] = _cell(found, columns, "amount")
            elif table == "Fixed Assets":
                sale = _cell(found, columns, "yod")
                row["years"] = (f"{_cell(found, columns, 'year')}, sold {sale}" if sale
                                else f"{_cell(found, columns, 'year')}, kept")
                row["amount / value ($)"] = _cell(found, columns, "value")
            else:
                row["years"] = f"{_cell(found, columns, 'year')}-{_cell(found, columns, 'end') or 'end'}"
                row["amount / value ($)"] = _cell(found, columns, "amount")
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    cells = [{"sheet": sheet, "cell": f"{column}, {year}", "from event": event_id}
             for sheet, column, year, event_id in provenance["cells"]]
    if cells:
        st.markdown("*Person-sheet cells*")
        st.dataframe(pd.DataFrame(cells), width="stretch", hide_index=True)
    fields = [{"case field": path, "from event": event_id}
              for path, event_id in sorted(provenance["case_fields"].items())]
    if fields:
        st.markdown("*Case fields*")
        st.dataframe(pd.DataFrame(fields), width="stretch", hide_index=True)
    if not rows and not cells and not fields:
        st.caption("Nothing yet: add an event above.")

# -- save ---------------------------------------------------------------

st.markdown("#### Save")
# Against the run's own document in the current schema: a run saved before events existed
# (schema 1) is migrated, which is not a change of its inputs (review X8).
try:
    current = canonicalize(scenario)
except ScenarioError:
    current = scenario
changes = diff_summaries(current, edited) if built is not None else []
st.caption("Changes against this run: " + (libraryjobs.plain("; ".join(changes)) if changes else "none yet"))
new_draft["changes"] = list(changes)
st.session_state[_DRAFT_KEY] = new_draft


def _reset():
    """Drop the draft and mount every widget afresh from the run (the version is in the keys)."""
    st.session_state.pop(_DRAFT_KEY, None)
    st.session_state[_VERSION_KEY] = version + 1


if changes or built is None:
    with banner:
        if changes:
            st.warning(f"Unsaved changes against *{run.name}*: " + libraryjobs.plain("; ".join(changes)),
                       icon=":material/edit_note:")
        else:
            st.warning(f"The events on this page cannot be built yet (see below); *{run.name}* itself is "
                       "unchanged.", icon=":material/edit_note:")
        st.button("Reset to the run", key=f"scn_reset_{key}", on_click=_reset,
                  help="Drop the edits on this page and show the run as it was saved.")
if scenario.get("schema_version") != SCHEMA_VERSION:
    st.caption(f"This run was saved in scenario schema {scenario.get('schema_version')} (before events); "
               f"saving it here stores a schema-{SCHEMA_VERSION} copy as a new run, even with no edit "
               "(its case files are generated by the current builder).")
st.caption(
    "Saving makes a new run whose parent is this one (a saved run never changes); its case "
    "file, its financial-profile workbook and (with a downturn sequence) its table of yearly "
    "rates are generated from these events and kept with it. Balances, PIAs and the "
    "assumptions are edited in the case pages ('Edit as new run' on the Run page)."
)
n1, n2, n3 = st.columns([2, 3, 2])
name = n1.text_input("Name", value=f"{run.name} variant", key="scenario_page_name")
notes = n2.text_area("Notes (optional)", key="scenario_page_notes")
collection = n3.selectbox(
    "Collection (optional)", [None] + list(lib.collections()),
    format_func=lambda c: "(none)" if c is None else c.name,
    key="scenario_page_collection",
    help="The new run joins this collection as it is; its variant values "
         "are set on the Collections page.")
# Enabled whatever the events say (review AL1, as Q18): disabled while the page could not
# build, the button was still disabled when the click that leaves the corrected field landed
# (a field commits on blur), so that first click did nothing.
save_clicked = st.button("Save as a new run", type="primary")
if save_clicked and built is None:
    st.warning("Not saved: the events above cannot be built yet (see the message above).",
               icon=":material/warning:")
elif save_clicked:
    try:
        result = lib.save_run(name=name.strip() or f"{run.name} variant", scenario=edited,
                              parent=run.id, notes=notes.strip())
    except Exception as exc:  # noqa: BLE001 - shown to the user, not raised
        libraryjobs.flash("error", f"Not saved: {exc}")
    else:
        if result.created:
            libraryjobs.flash("info", f"Saved as *{result.run.name}* ({result.run.folder_name}); "
                                      "the page now shows it.")
            # The edits are the new run now: drop the draft and open the page on it (S-2).
            st.session_state.pop(_DRAFT_KEY, None)
            st.session_state[_VERSION_KEY] = version + 1
            st.session_state["library_selected_run"] = result.run.id
        else:
            other = result.identical_to
            libraryjobs.flash(
                "info",
                f"Identical to *{other.name}* ({other.folder_name}): not saved again."
                if other else "Not saved: identical inputs already in the library.",
            )
        if collection is not None:
            saved = result.run if result.created else result.identical_to
            if saved is not None:  # a member already keeps its values (review AG6)
                lib.join_collection(collection.id, saved)
    st.rerun()

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

What the events do not cover -- balances, PIAs, the goal, the assumptions and the Owl settings
(section 6.1's People, Accounts, Goal and Advanced rows) -- stays in the case dictionary and is
edited in the existing pages ("Edit as new run" on the Run page). Saving there keeps the run's
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

st.markdown("# :material/edit_note: Scenario")
kz.divider("orange")
libraryjobs.show_flashes()  # what the last action said before its rerun (review 3, W3)

manager = libraryjobs.get_manager()
lib = manager.library

runs = list(reversed(lib.runs()))
if not runs:
    st.info("The library has no runs yet: import a case on the Library page.")
    st.stop()

_default = st.session_state.get("library_selected_run")
_index = next((i for i, r in enumerate(runs) if r.id == _default), 0)
run = st.selectbox("Run to edit", runs, index=_index, key="scenario_page_run",
                   format_func=lambda r: f"{r.name} ({r.folder_name})")
scenario = lib.scenario(run.id)
key = run.id  # widget keys follow the run: editing two runs keeps their states apart

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


def _blank_rows(rows, columns):
    """A table to edit: the events' rows, and one empty row to type into."""
    return pd.DataFrame([*rows, {c: None for c in columns}], columns=columns)


work_df = st.data_editor(
    _blank_rows(work_rows, ["id", "person", "level", "start", "end", "wages", "401k",
                            "employer", "IRA", "months worked"]),
    num_rows="dynamic", hide_index=True, key=f"scn_work_{key}",
    column_config={"wages": st.column_config.NumberColumn("wages ($/yr, in AGI)"),
                   "401k": st.column_config.NumberColumn("401k deferral"),
                   "employer": st.column_config.NumberColumn("employer contribution"),
                   "IRA": st.column_config.NumberColumn("IRA contribution"),
                   "months worked": st.column_config.NumberColumn("months worked (0-12)")},
)
st.markdown("*Claiming* (an empty age lets Owl choose)")
claim_df = st.data_editor(
    _blank_rows(claim_rows, ["id", "person", "age"]),
    num_rows="dynamic", hide_index=True, key=f"scn_claim_{key}",
)
st.markdown("*Death* (a person's life horizon in whole years of age: \"first death at 75\"; "
            "Owl's own death mechanics -- the survivor's share, single filing -- do the rest)")
death_df = st.data_editor(
    _blank_rows(death_rows, ["id", "person", "age"]),
    num_rows="dynamic", hide_index=True, key=f"scn_death_{key}",
)

with st.expander("Rent", expanded=rent is not None):
    rent_on = st.checkbox("The household rents", value=rent is not None, key=f"scn_rent_on_{key}")
    r1, r2, r3, r4 = st.columns(4)
    rent_monthly = r1.number_input("Monthly rent ($)", value=float((rent or {}).get("monthly", 4000)),
                                   key=f"scn_rent_monthly_{key}")
    rent_start = r2.text_input("From", value=builder.year_ref_text((rent or {}).get("start", plan_year)),
                               key=f"scn_rent_start_{key}")
    rent_flat = r3.text_input("Flat through",
                              value=builder.year_ref_text((rent or {}).get("flat_until", plan_year + 1)),
                              key=f"scn_rent_flat_{key}")
    rent_end = st.text_input(
        "To (blank: the year before the purchase, or the plan end)",
        value=("" if not rent or "end" not in rent else builder.year_ref_text(rent["end"])),
        key=f"scn_rent_end_{key}")
    rent_id = _event_id(r4, "rent", (rent or {}).get("id", "rent"), f"scn_rent_id_{key}")

with st.expander("Home purchase", expanded=buy is not None):
    buy_on = st.checkbox("Buy a home", value=buy is not None, key=f"scn_buy_on_{key}")
    financing = (buy or {}).get("financing") or {"kind": "cash"}
    if buy is not None:  # the event's own terms, the builder's defaults for what it leaves out
        terms = {**builder.FINANCING_DEFAULTS["loan"], **builder.FINANCING_DEFAULTS["cash"], **financing}
    else:  # suggestions for a new purchase, shown in the fields and saved as typed
        terms = {"down": 0.20, "closing": 0.03, "extra": 0.02}
    b1, b2, b3, b4 = st.columns(4)
    buy_name = b1.text_input("Home (the rows' name)", value=(buy or {}).get("name", "home"),
                             key=f"scn_buy_name_{key}")
    buy_price = b2.number_input("Price (today's \\$)", value=float((buy or {}).get("price", 700000)),
                                key=f"scn_buy_price_{key}")
    # A new purchase defaults to the year after the plan year (review X8: "purchase" anchored
    # the purchase to itself).
    buy_year = b3.text_input("Year", value=builder.year_ref_text((buy or {}).get("year") or plan_year + 1),
                             key=f"scn_buy_year_{key}")
    buy_id = _event_id(b4, "buy", (buy or {}).get("id", "buy"), f"scn_buy_id_{key}")
    s1, s2, s3, s4 = st.columns(4)
    buy_sale = s1.text_input("Sold (blank: kept)",
                             value=("" if not buy or "sale" not in buy else builder.year_ref_text(buy["sale"])),
                             key=f"scn_buy_sale_{key}")
    # A dropdown of the case's people (UX review Q19); no choice is the builder's default, the
    # first person, and stays no choice so that an unedited save changes nothing.
    _payers = _choices([None, *names], (buy or {}).get("pay_on"))
    buy_pay_on = s2.selectbox("Paid from (person)", _payers,
                              index=_payers.index((buy or {}).get("pay_on")),
                              format_func=_payer_label, key=f"scn_buy_pay_on_{key}",
                              help="Whose savings pay the price and the closing costs.")
    buy_kind = s3.selectbox("Financing", ["cash", "loan"],
                            index=0 if financing.get("kind") != "loan" else 1,
                            key=f"scn_buy_kind_{key}")
    buy_debt_name = s4.text_input("Loan's name", value=financing.get("name", ""),
                                  key=f"scn_buy_debt_{key}")
    f1, f2, f3, f4, f5 = st.columns(5)
    buy_term = f1.number_input("Term (years)", value=float(financing.get("term", 30)),
                               key=f"scn_buy_term_{key}")
    buy_rate = f2.number_input("Rate (%)", value=float(financing.get("rate", 6.25)),
                               key=f"scn_buy_rate_{key}")
    # Shares shown in percent (UX review Q19: 0.2 read as a fifth of a percent); the event
    # keeps shares, converted here only.
    buy_down = _share_from_percent(
        f3.number_input("Down payment (%)", value=float(terms["down"]) * 100.0, step=1.0,
                        format="%.2f", key=f"scn_buy_down_{key}"), terms["down"])
    buy_closing = _share_from_percent(
        f4.number_input("Closing costs (% of the price)", value=float(terms["closing"]) * 100.0,
                        step=0.5, format="%.2f", key=f"scn_buy_closing_{key}"), terms["closing"])
    buy_extra = _share_from_percent(
        f5.number_input("Loan closing (% of the loan)", value=float(terms["extra"]) * 100.0,
                        step=0.5, format="%.2f", key=f"scn_buy_extra_{key}"), terms["extra"])
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
    costs = (buy or {}).get("costs") or {}
    p1, p2, p3, p4 = st.columns(4)
    place_state = p1.text_input("State", value=place["state"], key=f"scn_place_state_{key}").strip().upper()
    if buy is not None and str(event_place.get("state") or "").strip().upper() == place_state:
        place_state = event_place["state"]  # the event's own spelling: no phantom edit (AK6)
    # The pre-filled locality and district belong to the state they came from: another state
    # starts both pickers at "(none)" (independent review AK2: the case's Yonkers stayed under
    # CT, and the run failed only at solve time).
    if place_state.upper() != str(place["state"] or "").strip().upper():
        place = {**place, "locality": "", "school_district": ""}
    place_move = p4.checkbox("Move there", value=bool(place.get("move")), key=f"scn_place_move_{key}",
                             help="The household moves to the new home in the purchase year (a "
                                  "move in the case). Without it, the home is where the case "
                                  "already lives: its locality stays, its school district is the one "
                                  "picked here.")
    _localities = _choices(_locality_choices(place_state.upper()), place["locality"])
    _districts = _choices(_district_choices(place_state.upper()), place["school_district"])
    for _k, _opts in ((f"scn_place_locality_{key}", _localities), (f"scn_place_district_{key}", _districts)):
        if _k in st.session_state and st.session_state[_k] not in _opts:
            st.session_state.pop(_k)  # another state's value: start over from the default
    place_locality = p2.selectbox(
        "Locality (with a move)", _localities, index=_localities.index(place["locality"]),
        format_func=_none_label, key=f"scn_place_locality_{key}", disabled=not place_move,
        help="Local income tax at the new home. Without a move the case's own locality stays.")
    place_district = p3.selectbox(
        "School district", _districts, index=_districts.index(place["school_district"]),
        format_func=_none_label, key=f"scn_place_district_{key}",
        help="For the NY STAR credit, in the years with a property tax line. Starts from the "
             "case's own district.")
    place_locality, place_district = _place_to_store(
        place_locality, place_district, bool(place_move), case_place["school_district"],
        event_place if buy is not None else None)
    c1, c2, c3, c4, c5 = st.columns(5)
    cost_tax = c1.number_input("Property tax (\\$/yr, today's \\$)",
                               value=float(costs.get("property tax", 0)), key=f"scn_cost_tax_{key}")
    cost_hoa = c2.number_input("HOA / common charges ($/yr)", value=float(costs.get("hoa", 0)),
                               key=f"scn_cost_hoa_{key}")
    cost_ins = c3.number_input("Insurance ($/yr)", value=float(costs.get("insurance", 0)),
                               key=f"scn_cost_ins_{key}")
    buy_growth = c4.number_input("Value growth (% real)", value=float((buy or {}).get("growth", 0.0)),
                                 key=f"scn_buy_growth_{key}")
    buy_commission = c5.number_input("Selling cost (%)", value=float((buy or {}).get("commission", 0.0)),
                                     key=f"scn_buy_commission_{key}")
    if buy_on and not (cost_tax or cost_hoa or cost_ins):
        st.warning("Property tax, HOA and insurance are all 0: owning the home costs nothing in "
                   "this run. Enter them, unless that is what you mean.", icon=":material/warning:")

with st.expander("Care", expanded=care is not None):
    care_on = st.checkbox("A care span", value=care is not None, key=f"scn_care_on_{key}")
    c1, c2, c3, c4 = st.columns(4)
    care_name = c1.text_input("Line name", value=(care or {}).get("name", "care"),
                              key=f"scn_care_name_{key}")
    care_amount = c2.number_input("Cost (\\$/yr, today's \\$)", value=float((care or {}).get("amount", 110000)),
                                  key=f"scn_care_amount_{key}")
    _care_default = {"anchor": "age", "person": names[0], "age": 86} if names else plan_year
    care_year = c3.text_input("From", value=builder.year_ref_text((care or {}).get("year") or _care_default),
                              key=f"scn_care_year_{key}")
    care_id = _event_id(c4, "care", (care or {}).get("id", "care"), f"scn_care_id_{key}")
    care_end = st.text_input("To (blank: the plan end)",
                             value=("" if not care or "end" not in care else builder.year_ref_text(care["end"])),
                             key=f"scn_care_end_{key}")
    care_essential = st.checkbox("Essential (paid whatever the spending level)",
                                 value=bool((care or {}).get("essential", True)), key=f"scn_care_ess_{key}")

with st.expander("Downturn sequence", expanded=down is not None):
    st.caption(
        "A named stress sequence overlaid on the run's own rate method at a chosen year: the "
        "years inside the window take the sequence's returns, the years outside keep the "
        "case's own method. The overlay becomes the run's table of yearly rates; a run that "
        "already reads a rates table cannot take one."
    )
    down_on = st.checkbox("Overlay a named downturn sequence", value=down is not None,
                          key=f"scn_down_on_{key}")
    _seq_names = sorted(_sequences())
    d1, d2, d3 = st.columns(3)
    _chosen = (down or {}).get("sequence", _seq_names[0]) if _seq_names else None
    down_seq = d1.selectbox("Sequence", _seq_names,
                            index=max(0, _seq_names.index(_chosen)) if _chosen in _seq_names else 0,
                            key=f"scn_down_seq_{key}")
    down_start = d2.text_input("From", value=builder.year_ref_text((down or {}).get("start") or plan_year),
                               key=f"scn_down_start_{key}")
    down_id = _event_id(d3, "downturn", (down or {}).get("id", "downturn"), f"scn_down_id_{key}")
    if down_seq:
        _meta = _sequences()[down_seq]
        st.caption(f"{_meta['description']} *(source: {_meta['source']})*")


def _present(value):
    return value is not None and not (isinstance(value, float) and pd.isna(value)) and value != ""


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
                 "level": row["level"] or "full",
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
    events = _work_events(work_df.to_dict("records"))
    events += _claim_events(claim_df.to_dict("records"))
    events += _death_events(death_df.to_dict("records"))
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


edited = copy.deepcopy(scenario)
built = None
try:
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
st.caption("Changes against this run: " + ("; ".join(changes) if changes else "none yet"))
if scenario.get("schema_version") != SCHEMA_VERSION:
    st.caption(f"This run was saved in scenario schema {scenario.get('schema_version')} (before events); "
               f"saving it here stores a schema-{SCHEMA_VERSION} copy as a new run, even with no edit "
               "(its case files are generated by the current builder).")
st.caption(
    "Saving makes a new run whose parent is this one (a saved run never changes); its case "
    "file, its financial-profile workbook and (with a downturn sequence) its table of yearly "
    "rates are generated from these events and kept with it. Balances, PIAs, the "
    "goal and the assumptions are edited in the case pages ('Edit as new run' on the Run page)."
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
if st.button("Save as a new run", type="primary", disabled=built is None):
    try:
        result = lib.save_run(name=name.strip() or f"{run.name} variant", scenario=edited,
                              parent=run.id, notes=notes.strip())
    except Exception as exc:  # noqa: BLE001 - shown to the user, not raised
        libraryjobs.flash("error", f"Not saved: {exc}")
    else:
        if result.created:
            libraryjobs.flash("info", f"Saved as *{result.run.name}* ({result.run.folder_name}).")
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

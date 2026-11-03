"""
Scenario page: a run's events and what they generate (design sections 6.1-6.3, step 4).

The scenario is the source of truth of a run (D2): events in plain terms -- work, claiming,
rent, a home purchase and care (D6) -- beside the hand rows. A year field may name a calendar
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
edited in the existing pages ("Edit as new run" on the Run page; saving there keeps the events'
generated values, section 6.3).

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

import pandas as pd
import streamlit as st

import libraryjobs
import sskeys as kz
from owlplanner.library import ScenarioError, diff_summaries
from owlplanner.library import builder

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
    "One row or box per event. A year field takes a calendar year or an anchor: "
    "`age:Ari:86` (the year Ari turns 86), `work:Noa` (Noa's last work year), `after:Noa` "
    "(the year after it), `purchase` (the home purchase's year), or `event:care` / "
    "`event:care+2` (another event's year, shifted). The rent ends the year before the "
    "purchase unless it names its own end (section 6.2)."
)

events = scenario.get("events") or []
work_rows = [{
    "id": e.get("id"), "person": e.get("person"), "level": e.get("level", "full"),
    "start": e.get("start"), "end": e.get("end"),
    "wages": e.get("wages"), "401k": e.get("k401k"), "employer": e.get("employer"),
    "IRA": e.get("ira"), "months worked": e.get("months_worked"),
} for e in events if e.get("kind") == "work"]
claim_rows = [{"id": e.get("id"), "person": e.get("person"), "age": e.get("age")}
              for e in events if e.get("kind") == "claim"]
rent = next((e for e in events if e.get("kind") == "rent"), None)
buy = next((e for e in events if e.get("kind") == "purchase"), None)
care = next((e for e in events if e.get("kind") == "care"), None)


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

with st.expander("Rent", expanded=rent is not None):
    rent_on = st.checkbox("The household rents", value=rent is not None, key=f"scn_rent_on_{key}")
    r1, r2, r3, r4 = st.columns(4)
    rent_id = r1.text_input("Event id", value=(rent or {}).get("id", "rent"), key=f"scn_rent_id_{key}")
    rent_monthly = r2.number_input("Monthly rent ($)", value=float((rent or {}).get("monthly", 4000)),
                                   key=f"scn_rent_monthly_{key}")
    rent_start = r3.text_input("From", value=builder.year_ref_text((rent or {}).get("start", 2026)),
                               key=f"scn_rent_start_{key}")
    rent_flat = r4.text_input("Flat through", value=builder.year_ref_text((rent or {}).get("flat_until", 2027)),
                              key=f"scn_rent_flat_{key}")
    rent_end = st.text_input(
        "To (blank: the year before the purchase, or the plan end)",
        value=("" if not rent or "end" not in rent else builder.year_ref_text(rent["end"])),
        key=f"scn_rent_end_{key}")

with st.expander("Home purchase", expanded=buy is not None):
    buy_on = st.checkbox("Buy a home", value=buy is not None, key=f"scn_buy_on_{key}")
    financing = (buy or {}).get("financing") or {"kind": "cash"}
    b1, b2, b3, b4 = st.columns(4)
    buy_id = b1.text_input("Event id", value=(buy or {}).get("id", "buy"), key=f"scn_buy_id_{key}")
    buy_name = b2.text_input("Home (the rows' name)", value=(buy or {}).get("name", "home"),
                             key=f"scn_buy_name_{key}")
    buy_price = b3.number_input("Price (today's $)", value=float((buy or {}).get("price", 700000)),
                                key=f"scn_buy_price_{key}")
    buy_year = b4.text_input("Year", value=builder.year_ref_text((buy or {}).get("year") or {"anchor": "purchase"}),
                             key=f"scn_buy_year_{key}")
    s1, s2, s3, s4 = st.columns(4)
    buy_sale = s1.text_input("Sold (blank: kept)",
                             value=("" if not buy or "sale" not in buy else builder.year_ref_text(buy["sale"])),
                             key=f"scn_buy_sale_{key}")
    buy_pay_on = s2.text_input("Paid from (person)",
                               value=(buy or {}).get("pay_on") or "", key=f"scn_buy_pay_on_{key}")
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
    buy_down = f3.number_input("Down payment (share)", value=float(financing.get("down", 0.20)),
                               key=f"scn_buy_down_{key}")
    buy_closing = f4.number_input("Closing costs (share)", value=float(financing.get("closing", 0.03)),
                                  key=f"scn_buy_closing_{key}")
    buy_extra = f5.number_input("Loan closing (share)", value=float(financing.get("extra", 0.02)),
                                key=f"scn_buy_extra_{key}")
    place = (buy or {}).get("place") or {}
    costs = (buy or {}).get("costs") or {}
    p1, p2, p3, p4 = st.columns(4)
    place_state = p1.text_input("State", value=place.get("state", "NY"), key=f"scn_place_state_{key}")
    place_locality = p2.text_input("Locality", value=place.get("locality", ""),
                                   key=f"scn_place_locality_{key}")
    place_district = p3.text_input("School district", value=place.get("school_district", ""),
                                   key=f"scn_place_district_{key}")
    place_move = p4.checkbox("Move there", value=bool(place.get("move")), key=f"scn_place_move_{key}")
    c1, c2, c3, c4, c5 = st.columns(5)
    cost_tax = c1.number_input("Property tax ($/yr, today's $)",
                               value=float(costs.get("property tax", 0)), key=f"scn_cost_tax_{key}")
    cost_hoa = c2.number_input("HOA / common charges ($/yr)", value=float(costs.get("hoa", 0)),
                               key=f"scn_cost_hoa_{key}")
    cost_ins = c3.number_input("Insurance ($/yr)", value=float(costs.get("insurance", 0)),
                               key=f"scn_cost_ins_{key}")
    buy_growth = c4.number_input("Value growth (% real)", value=float((buy or {}).get("growth", 0.0)),
                                 key=f"scn_buy_growth_{key}")
    buy_commission = c5.number_input("Selling cost (%)", value=float((buy or {}).get("commission", 0.0)),
                                     key=f"scn_buy_commission_{key}")

with st.expander("Care", expanded=care is not None):
    care_on = st.checkbox("A care span", value=care is not None, key=f"scn_care_on_{key}")
    c1, c2, c3, c4 = st.columns(4)
    care_id = c1.text_input("Event id", value=(care or {}).get("id", "care"), key=f"scn_care_id_{key}")
    care_name = c2.text_input("Line name", value=(care or {}).get("name", "care"),
                              key=f"scn_care_name_{key}")
    care_amount = c3.number_input("Cost ($/yr, today's $)", value=float((care or {}).get("amount", 110000)),
                                  key=f"scn_care_amount_{key}")
    care_year = c4.text_input("From", value=builder.year_ref_text((care or {}).get("year") or {"anchor": "purchase"}),
                              key=f"scn_care_year_{key}")
    care_end = st.text_input("To (blank: the plan end)",
                             value=("" if not care or "end" not in care else builder.year_ref_text(care["end"])),
                             key=f"scn_care_end_{key}")
    care_essential = st.checkbox("Essential (paid whatever the spending level)",
                                 value=bool((care or {}).get("essential", True)), key=f"scn_care_ess_{key}")


def _present(value):
    return value is not None and not (isinstance(value, float) and pd.isna(value)) and value != ""


def _work_events(rows):
    out = []
    for row in rows:
        if not any(_present(v) for v in row.values()):
            continue  # the empty row the editor adds
        event = {"id": row["id"], "kind": "work", "person": row["person"],
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


def _year(text, where):
    return builder.parse_year_ref(text, where) if _present(text) else None


def _assemble():
    """The events list from the widgets above (ScenarioError with the field that is wrong)."""
    events = _work_events(work_df.to_dict("records"))
    events += _claim_events(claim_df.to_dict("records"))
    if rent_on:
        event = {"id": rent_id.strip() or "rent", "kind": "rent", "monthly": rent_monthly,
                 "start": _year(rent_start, "rent.from"), "flat_until": _year(rent_flat, "rent.flat through")}
        if _present(rent_end):
            event["end"] = _year(rent_end, "rent.to")
        events.append(event)
    if buy_on:
        event = {"id": buy_id.strip() or "buy", "kind": "purchase", "name": buy_name.strip() or "home",
                 "price": buy_price, "year": _year(buy_year, "purchase.year"),
                 "pay_on": buy_pay_on.strip() or None,
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
        event = {"id": care_id.strip() or "care", "kind": "care", "name": care_name.strip() or "care",
                 "amount": care_amount, "year": _year(care_year, "care.from"),
                 "essential": bool(care_essential)}
        if _present(care_end):
            event["end"] = _year(care_end, "care.to")
        events.append(event)
    return events


edited = copy.deepcopy(scenario)
built = None
try:
    edited["events"] = _assemble()
    built = builder.build(edited)
except ScenarioError as exc:
    st.error(f"Not buildable yet: {exc}")
except Exception as exc:  # noqa: BLE001 - shown to the user, not raised
    st.error(f"Cannot build this scenario yet: {exc}")

# -- what the events generate (marked) ---------------------------------

st.markdown("#### What the events generate (marked)")
st.caption(
    "Every generated row, cell and case field records which event produced it (section 6.3). "
    "A generated row is regenerated wholesale when the events change and hand rows are "
    "untouched; an edit to a generated value does not survive a regeneration. Per-cell "
    "overrides with a \"back to computed\" button are the later increment of section 6.3."
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
            row["years"] = f"{_cell(found, columns, 'year')}-{_cell(found, columns, 'end') or 'end'}"
            row["amount ($/yr, today's $)"] = _cell(found, columns, "amount")
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
changes = diff_summaries(scenario, edited) if built is not None else []
st.caption("Changes against this run: " + ("; ".join(changes) if changes else "none yet"))
st.caption(
    "Saving makes a new run whose parent is this one (a run is immutable, D3); its Case.toml "
    "and HFP.xlsx are generated from these events and frozen (section 5). Balances, PIAs, the "
    "goal and the assumptions are edited in the case pages ('Edit as new run' on the Run page)."
)
n1, n2 = st.columns([2, 3])
name = n1.text_input("Name", value=f"{run.name} variant", key="scenario_page_name")
notes = n2.text_area("Notes (optional)", key="scenario_page_notes")
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
    st.rerun()

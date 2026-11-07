"""
Collections page for the run library (run-library-design.md, section 9.3, step 6).

A collection is a named set of runs answering one question, with a comparison rule written
on it ("Maximize first-year discretionary spending, condo kept; reference: Yonkers 2027
cash"). This page creates and edits collections, makes variants ("choose a dimension ...
and get one child draft per value, all in one collection, queued together": place, purchase
year, financing, last work year, claiming ages, first death (I2) and the named downturn
sequence (I11)), and shows the grid: the score's difference from the reference and the home
at the end per cell, coloured by the comparison rule (R3), and the variants no other variant
beats on both numbers, with whether each lead is resolved.

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

import libraryjobs
import librarypresets
import sskeys as kz
import variant_tables as vt
from owlplanner.library import JobsError, ScenarioError, grid, preset_solves, variants
from owlplanner.library import view
from owlplanner.library.sequences import sequences as _sequences

st.markdown("# :material/grid_view: Collections")
kz.divider("orange")
libraryjobs.show_flashes()  # what the last action said before its rerun (review 3, W3)

manager = libraryjobs.get_manager()
lib = manager.library

_DIMENSIONS = variants.DIMENSIONS


# -- pick a collection, or make one -----------------------------------


def _open_collection(cid):
    """Open a collection on the next render (reviews AC2-AC3).

    The picker's own key (`col_page_collection`) cannot be written from a button handler:
    it is a widget key, already instantiated mid-run, so writing it raises Streamlit's
    `StreamlitWidgetAlreadyInstantiatedError` (AC2), and it holds the picker's *labels*,
    not ids (AC3). `library_selected_collection` is a plain key; the block below translates
    it to the label before the picker is instantiated -- the route a jump from another
    page already takes.
    """
    st.session_state["library_selected_collection"] = cid


with st.expander("New collection", expanded=not lib.collections()):
    name = st.text_input("Name", key="col_new_name", placeholder="Where and when to buy?")
    question = st.text_input("Question", key="col_new_question",
                             placeholder="Maximize first-year discretionary spending, condo kept")
    rule_hint = ("reference: Yonkers 2027 cash; a variant leads only when it is at least as "
                 "good on the discretionary spending and the home at the end")
    rule = st.text_input("Comparison rule", key="col_new_rule", placeholder=rule_hint)
    # Enabled whatever the name says (UX review Q18): gated on the field, the button was still
    # disabled when the click that blurs the field landed, so that first click did nothing.
    if st.button("Create collection", type="primary"):
        if not name.strip():
            st.warning("Give the collection a name.", icon=":material/warning:")
        elif name.strip() in [c.name for c in lib.collections()]:
            # The field keeps its text after a create: a second click made a twin.
            st.warning(f"A collection named *{name.strip()}* exists already.", icon=":material/warning:")
        else:
            coll = lib.create_collection(name.strip(), question=question.strip(), rule=rule.strip())
            _open_collection(coll.id)
            libraryjobs.flash("success", f"Collection *{coll.name}* created.")
            st.rerun()

colls = lib.collections()
if not colls:
    st.info("The library has no collections yet: create one above. A collection is a named "
            "set of runs answering one question, with a comparison rule.")
    st.stop()

labels = {f"{c.name}  ({len(c.members)} run(s))": c for c in colls}
wanted = st.session_state.pop("library_selected_collection", None)
if wanted is not None:
    for label, c in labels.items():
        if c.id == wanted:
            st.session_state["col_page_collection"] = label
            break
coll = labels[st.selectbox("Collection", list(labels), key="col_page_collection")]


# -- the collection's own fields (section 9.3) -------------------------

st.markdown(f"## {coll.name}")
if coll.question or coll.rule:
    st.markdown(f"*{coll.question or 'no question written'}*")
    if coll.rule:
        st.caption(f"Rule: {coll.rule}")

with st.expander("Question, rule and layout"):
    c1, c2 = st.columns(2)
    name = c1.text_input("Name", value=coll.name, key=f"col_name_{coll.id}")
    question = c2.text_area("Question", value=coll.question, key=f"col_question_{coll.id}",
                            help="What this collection answers, in one sentence.")
    rule = st.text_area("Comparison rule", value=coll.rule, key=f"col_rule_{coll.id}",
                        help="How the variants are judged: a variant leads only when it is at "
                             "least as good on the spending (the savings left, when the bequest is "
                             "maximized) and the home at the end, and better on one beyond the "
                             "noise rule; the two numbers are never added together.")
    dims = sorted({key for m in coll.members for key in (m.values or {})})
    shown_rows, shown_cols = vt.grid_layout(dims, coll.grid)  # AD2: the layout the grid uses
    c3, c4 = st.columns(2)
    rows = c3.multiselect("Grid rows", dims, default=shown_rows, key=f"col_rows_{coll.id}",
                          help="Empty: one row. A dimension in neither list puts its members in "
                               "one cell (the others listed beside the grid).")
    columns = c4.multiselect("Grid columns", dims, default=shown_cols, key=f"col_cols_{coll.id}",
                             help="Empty: the default layout (the purchase year as columns, "
                                  "every other dimension as rows).")
    c5, c6 = st.columns(2)
    if c5.button("Save", key=f"col_save_{coll.id}"):
        lib.update_collection(coll.id, name=name.strip() or coll.name,
                              question=question.strip(), rule=rule.strip(),
                              grid={"rows": rows, "columns": columns})
        libraryjobs.flash("success", "Saved.")
        st.rerun()
    if c6.button("Delete collection", key=f"col_delete_{coll.id}"):
        lib.delete_collection(coll.id)
        st.session_state.pop("col_page_collection", None)
        libraryjobs.flash("info", "The collection is gone; its runs are untouched.")
        st.rerun()


# -- make variants (section 9.3) --------------------------------------


def _fill_claim_ages(parent, names):
    """Fill the claiming boxes from the run's last solve (review AC1).

    An `on_click` callback: it runs before the boxes are instantiated, so writing their
    keys is legal -- an inline handler raised `StreamlitWidgetAlreadyInstantiatedError`
    on every click (the boxes sit above the button).
    """
    result = grid.latest_result(parent.path) if parent is not None else None
    ages = dict(view.claiming_ages(result)) if result is not None else {}
    for person in names:
        st.session_state[f"col_variant_claim_{person}"] = (
            "" if person not in ages else f"{ages[person]:g}")


runs = lib.runs()
if not runs:  # review AC7: `lib.scenario(None)` used to end the page here
    st.caption("The library has no runs yet: save one first (the Run page), then make "
               "variants of it here.")
if runs:
    with st.expander("Make variants", expanded=False):
        parent = st.selectbox("From run", runs, format_func=lambda r: f"{r.name}  ({r.folder_name})",
                              key="col_variant_parent",
                              help="One child draft per value of the dimensions below; several "
                                   "dimensions give their product -- the grid.")
        names = list(((lib.scenario(parent).get("case") or {}).get("basic_info") or {}).get("names") or [])
        st.caption("Each table is one dimension: **one row per value**. Leave a table or field "
                   "empty to keep the parent's; in a table, an empty cell keeps the parent's value "
                   f"and `{vt.CLEAR}` clears a text cell (a place with no local income tax: "
                   "locality `-`).")
        years_text = st.text_input("Purchase year(s)", key="col_variant_years", placeholder="2027, 2029, 2031")
        st.markdown("**Place(s)**")
        places = st.data_editor(
            vt.places_table(), num_rows="dynamic", key="col_variant_places",
            column_config={"move": st.column_config.CheckboxColumn(
                "move", help="A move at the purchase (the place's locality and district from that "
                             "year); unchecked: the district only")})
        st.markdown("**Financing**: cash, or a loan with its term and rate. The down payment and "
                    "the closing costs are **percentages**, as on the Scenario page: type 20 for 20%.")
        money = st.column_config.NumberColumn
        fins = st.data_editor(
            vt.financing_table(), num_rows="dynamic", key="col_variant_fins",
            column_config={
                "kind": st.column_config.SelectboxColumn("cash or loan", options=["cash", "loan"]),
                "term": money("term (years)", min_value=1, max_value=50, step=1, format="%d"),
                "rate": money("rate (%)", min_value=0.0, max_value=25.0, format="%.3f%%",
                              help="Percent a year: 6.25 for 6.25%."),
                # Percentages shown and typed as such, stored as shares (QW-4).
                **{field: money(label, min_value=0.0, max_value=100.0, format="%.2f%%")
                   for field, label in (("down", "down (% of the price)"),
                                        ("closing", "closing (% of the price)"),
                                        ("extra", "loan closing (% of the loan)"))},
                "name": st.column_config.TextColumn(
                    "loan name", help="The Debts row's name; write {place} where the place's label goes."),
            })
        _fin_errors, _fin_warnings = vt.financing_notes(fins)
        for _note in _fin_errors:
            st.error(f"Does not build: {_note}.", icon=":material/error:")
        for _note in _fin_warnings:
            st.warning(_note, icon=":material/flag:")
        c1, c2 = st.columns(2)
        work_person = c1.selectbox("Last work year, for", ["(none)"] + names, key="col_variant_work_person")
        work_years = c2.text_input("their last year(s)", key="col_variant_work_years", placeholder="2026, 2027")
        st.markdown("**Claiming ages** (comma separated per person; empty: let Owl choose)")
        claim_texts = {person: st.text_input(f"{person}", key=f"col_variant_claim_{person}")
                       for person in names}
        st.button("Fill the ages from the run's last solve", key="col_variant_fill",
                  on_click=_fill_claim_ages, args=(parent, names))  # AC1: a callback, not an inline handler
        parent_result = grid.latest_result(parent.path)
        if (parent_result is not None and parent_result.record.get("age_search")
                and not any((text or "").strip() for text in claim_texts.values())):
            # AD5: the children of an "ages" run solve at the case's own ages under the other
            # presets, so the grid would compare claiming ages as well as the housing.
            st.warning("This run's last solve searched the claiming ages "
                       f"({view.claiming_ages_text(parent_result)}). With the boxes empty the "
                       "variants keep the case's own ages under quick/decision: fill the boxes from "
                       "its last solve to hold the whole grid at those ages.", icon=":material/flag:")
        st.markdown("**First death** (one person's life horizon, comma separated ages)")
        d1, d2 = st.columns(2)
        death_person = d1.selectbox("dies early, for", ["(none)"] + names, key="col_variant_death_person",
                                    help="One child per age: 'Ari dies at 75'. Owl's own death "
                                         "mechanics (the survivor's share, single filing) do the rest.")
        death_ages = d2.text_input("their death age(s)", key="col_variant_death_ages",
                                   placeholder="75, 80, 85")
        st.markdown("**Downturn sequence** (one row per value; `start` a year or an anchor "
                    "like `purchase`; `-` removes the overlay)")
        seqs = st.data_editor(
            vt.sequences_table(), num_rows="dynamic", key="col_variant_seqs",
            column_config={"sequence": st.column_config.SelectboxColumn(
                "sequence", options=[vt.CLEAR] + sorted(_sequences()), required=False),
                "start": st.column_config.TextColumn("start")})
        coll_target = st.selectbox("Into collection", colls, format_func=lambda c: c.name,
                                   index=list(c.id for c in colls).index(coll.id),
                                   key="col_variant_collection")
        c3, c4 = st.columns(2)
        run_now = c3.checkbox("Queue them when created", key="col_variant_run",
                              help="Each child is solved with the preset beside it, in a "
                                   "background job of its own.")
        preset = librarypresets.select("Preset", "col_variant_preset", container=c4)
        if st.button("Create the variants", type="primary", key="col_variant_go"):
            try:
                dimensions, notes = vt.dimensions(names, years_text, places, fins,
                                                  work_person, work_years, claim_texts,
                                                  death_person, death_ages, seqs)
            except ScenarioError as exc:  # a bad cell: flash it and make nothing (AC6)
                libraryjobs.flash("error", f"No variants: {exc}")
                st.rerun()
            for note in notes:
                libraryjobs.flash("caption", f"Skipped {note}.")
            if not dimensions:
                libraryjobs.flash("error", "No dimension given: fill a table or a field above.")
                st.rerun()
            try:
                made = variants.plan_variants(lib.scenario(parent), dimensions)
            except ScenarioError as exc:  # a value that does not fit the scenario
                libraryjobs.flash("error", f"No variants: {exc}")
                st.rerun()
            created, skipped = 0, 0
            for variant in made:
                try:
                    saved = lib.save_run(name=f"{parent.name} {variant.label}",
                                         scenario=variant.scenario, parent=parent.id)
                except Exception as exc:  # noqa: BLE001 - shown, not raised (a bad value, a locked library)
                    libraryjobs.flash("error", f"{variant.label}: not saved ({exc})")
                    skipped += 1
                    continue
                run = saved.run if saved.created else saved.identical_to
                lib.add_member(coll_target.id, run, variant.values)
                if saved.created:
                    created += 1
                else:
                    skipped += 1
                    libraryjobs.flash("caption", f"{variant.label}: identical to *{run.name}* "
                                                 "(same inputs): added to the collection as it is.")
                if run_now:
                    for solve in preset_solves(preset):
                        try:
                            manager.enqueue(run, preset=solve)
                        except (ScenarioError, JobsError) as exc:
                            libraryjobs.flash("error", f"{run.name}: not queued ({exc})")
                            break
            if not (coll_target.grid or {}).get("columns"):
                # AD2: give the collection a layout with every varied dimension placed (the
                # page's fallback used to drop one).
                varied = sorted({key for variant in made for key in variant.values})
                rows_, cols_ = vt.grid_layout(varied)
                lib.update_collection(coll_target.id, grid={"rows": rows_, "columns": cols_})
            message = (f"{created} variant(s) created in *{coll_target.name}*"
                       + (f", {skipped} skipped" if skipped else "")
                       + (", queued" if run_now else "."))
            libraryjobs.flash("success", message)
            _open_collection(coll_target.id)  # AC2-AC3: the plain key, translated below
            st.rerun()


# -- the grid and the leads -------------------------------------------


def _member_runs(members):
    out = {}
    for member in members:
        try:
            out[member.run] = lib.get(member.run)
        except Exception:  # noqa: BLE001 - a deleted member is shown, not fatal
            out[member.run] = None
    return out


_RUNS = _member_runs(coll.members)
# One model for the whole collection (review AG5): the exact-LP results when a member has
# nothing else (the sensitivity runs), the headline results otherwise.
_RESULTS, _EXACT = grid.member_results([r.path for r in _RUNS.values() if r is not None])


def _entry(member):
    run = _RUNS.get(member.run)
    if run is None:
        return grid.Entry(run_id=member.run, name="a deleted run", values=member.values)
    return grid.Entry(run_id=run.id, name=run.name, values=member.values,
                      result=_RESULTS.get(run.path))


_LEAD_COLORS = {
    "the second result leads": "#2e7d32",   # the variant leads the reference
    "the first result leads": "#c62828",    # the reference leads the variant
    "trade-off": "#1565c0",
}


def _key_label(key):
    return ", ".join(str(x) for x in key if x is not None) or "(all)"


def _cell_md(cell):
    if cell is None:
        return ""
    home = f"{cell.home:,.0f}" if cell.home is not None else "-"
    if cell.delta is None:
        return home
    # AD4: the colour is R3's verdict on the two numbers (a variant whose score is inside the
    # noise band but whose home is larger leads); "~" marks a score difference inside the band.
    color = _LEAD_COLORS.get(cell.lead.get("verdict", ""), "#757575")
    tilde = "~" if cell.verdict == "within noise" else ""
    star = " &#9733;" if cell.best else ""
    return (f"<span style='color:{color}'><b>{tilde}{cell.delta:+,.0f}{star}</b></span><br>"
            f"<span style='color:#757575'>{home}</span>")


st.markdown("### The grid")
entries = [_entry(m) for m in coll.members]
solved = [e for e in entries if e.result is not None and e.result.solved]
ref_entry = next((e for e in entries if e.run_id == coll.reference), None)
dims = sorted({key for e in entries for key in (e.values or {})})
rows, columns = vt.grid_layout(dims, coll.grid)  # AD2: no dimension dropped by default

if _EXACT:
    st.caption("Every member is read through its **exact-LP** result: some members are solved "
               "under the exact LP alone (the sensitivity runs), and the grid judges one model "
               "at a time.")
if not solved:
    st.info("No member of this collection has a solved result yet: queue them below (or on "
            "the Run page) and come back.")
elif ref_entry is None or ref_entry.result is None or not ref_entry.result.solved:
    st.info("Choose a reference below: the grid's cells are differences from it.")
else:
    g = grid.grid_view(entries, reference=ref_entry.run_id, row_dims=rows, col_dims=columns)
    # R3's first number (review AJ3): the score, or under maxBequest the savings left (the
    # score there is the final bequest, which holds the home shown below it).
    first_name = view.first_number_label(ref_entry.result)
    st.caption(f"Each cell: the difference from the reference (**{ref_entry.name}**, "
               f"{view.first_number(ref_entry.result):,.0f}) in {first_name}, and below it the home "
               "at the end (today's \\$). &#9733; is the best in its row on that number alone. "
               "Colour, the "
               "verdict on the two numbers together: green leads the reference, red the reference leads, "
               "blue a trade-off (more spending against more home), grey no difference beyond the "
               f"noise rule; ~ marks a {view.first_number_name(ref_entry.result)} difference "
               "inside the noise band.")
    lines = [f"| {_key_label(rows) if rows else 'variant'} | "
             + " | ".join(_key_label(col) for col in g.col_keys) + " |",
             "|---|" + "---:|" * len(g.col_keys)]
    for key, row in g.rows:
        lines.append("| " + _key_label(key) + " | "
                     + " | ".join(_cell_md(row[col]) for col in g.col_keys) + " |")
    st.markdown("\n".join(lines), unsafe_allow_html=True)
    for flag in g.flags:
        st.warning(flag, icon=":material/flag:")
    leaders = grid.front(entries, reference=ref_entry.run_id)
    if leaders:
        st.markdown("#### What nothing beats")
        _first = view.first_number_name(ref_entry.result)
        st.caption(f"The variants no other variant beats on both numbers -- the {_first} and the "
                   f"home at the end, never added. *vs the reference* is the verdict on the "
                   f"{_first} difference against the noise rule.")
        for item in leaders:
            entry = item["entry"]
            judgment = item["vs_reference"]
            beat = f"; leads {', '.join(item['leads'])}" if item["leads"] else ""
            home = f"{item['home']:,.0f}" if item["home"] is not None else "-"
            # R3's two numbers (review AJ3): under maxBequest the savings left, not the score,
            # which there holds the home.
            first = view.first_number_name(entry.result)
            st.markdown(
                f"- **{entry.name}**: {first} {item['first']:,.0f}, home {home}{beat}  \n"
                f"  vs *{ref_entry.name}*: {judgment.verdict}"
                + (f" ({judgment.delta:+,.0f})" if judgment.delta is not None else "")
                + (f" -- {judgment.note}" if judgment.note else ""))
    for entry in g.unplaced:
        st.caption(f"Beside the grid (no variant values): **{entry.name}**"
                   + (f", {view.score_name(entry.result)} {entry.score:,.0f}"
                      if entry.score is not None else ""))
    for entry, shares in g.collided:  # AC4: two runs in one cell, both shown
        star = " &#9733; (the best in its row)" if entry.run_id in g.best_beside else ""
        st.caption(f"Beside the grid (its cell shows **{shares.name}**, the same row and column): "
                   f"**{entry.name}**"
                   + (f", {view.score_name(entry.result)} {entry.score:,.0f}"
                      if entry.score is not None else "") + star)


# -- the members -------------------------------------------------------

st.markdown("### Members")
st.caption("A member with variant values is placed in the grid; one without is listed beside "
           "it. *Values* sets them by hand for a run added here -- the same "
           "{dimension: label} pairs \"make variants\" fills, for example "
           "`year: 2027; place: yonkers`.")
member_runs = []
for member in coll.members:
    try:
        member_runs.append(lib.get(member.run))
    except Exception:  # noqa: BLE001 - a deleted member is shown as deleted, not fatal
        pass
c1, c2, c3 = st.columns([3, 2, 2])
add_run = c1.selectbox("Add a run", [None] + list(lib.runs()),
                       format_func=lambda r: "(choose)" if r is None else r.name,
                       key="col_add_run")
if c2.button("Add to the collection", disabled=add_run is None):
    # A run already in the collection keeps the values it has (store.join_collection, AG6).
    lib.join_collection(coll.id, add_run)
    st.rerun()
ref_options = [None] + member_runs
ref_index = next((i for i, r in enumerate(ref_options) if r is not None and r.id == coll.reference), 0)
ref_choice = c3.selectbox("Reference", ref_options,
                          format_func=lambda r: "(none)" if r is None else r.name,
                          index=ref_index,
                          help="The run the grid's cells are differences from.",
                          key=f"col_ref_{coll.id}")
if c3.button("Set the reference"):
    lib.set_reference(coll.id, ref_choice)
    st.rerun()

for member in coll.members:
    entry = _entry(member)
    line = f"**{entry.name}**"
    if member.values:
        line += "  \n" + ", ".join(f"{k}: {v}" for k, v in member.values.items())
    if entry.result is not None and entry.result.solved:
        home = f"{entry.home:,.0f}" if entry.home is not None else "-"
        line += (f"  \n{view.score_name(entry.result)} {entry.score:,.0f} · home {home} · "
                 f"{view.method_text(entry.result)}")
    elif (_EXACT and _RUNS.get(member.run) is not None
          and grid.latest_result(_RUNS[member.run].path, companion="exact_medicare") is not None):
        # The tornado's medical-inflation child solves with Medicare priced exactly (review
        # AJ1): it has no exact-LP result to place in this read; its bar is on the run's page.
        line += ("  \nsolved with Medicare priced exactly (the tornado's medical-inflation "
                 "mover): not in the exact-LP grid; its bar, against the run's own solve under "
                 "the same model, is on the run's page")
    else:
        line += "  \nno solved result yet"
    cols = st.columns([7, 1, 1, 1])
    cols[0].markdown(line)
    if cols[1].button("Open", key=f"col_open_{coll.id}_{member.run}",
                      help="The run's page (numbers, charts, its solves)."):
        st.session_state["library_selected_run"] = member.run
        st.switch_page("Run.py")
    with cols[2].popover("Values"):
        text = st.text_area("Values", value=vt.values_text(member.values),
                            key=f"col_values_{coll.id}_{member.run}",
                            help="dimension: label pairs, separated by ';' or newlines.")
        if st.button("Save", key=f"col_values_save_{coll.id}_{member.run}"):
            try:
                values = vt.member_values(text)
            except ScenarioError as exc:  # a bad pair: flash it, keep the old values
                libraryjobs.flash("error", f"Values not saved: {exc}")
            else:
                lib.add_member(coll.id, member.run, values=values)
            st.rerun()
    if cols[3].button("Remove", key=f"col_rm_{coll.id}_{member.run}"):
        lib.remove_member(coll.id, member.run)
        st.rerun()
    st.divider()


# -- run the collection again -----------------------------------------

with st.expander("Run the collection again"):
    st.caption("Every member is queued again with the preset below. Plans start today: compare "
               "only runs solved the same day, and only within the run's plan year (the year "
               "its balances were entered for).")
    preset = librarypresets.select("Preset", "col_run_preset")
    if st.button("Queue every member", type="primary"):
        queued = 0
        for member in coll.members:
            try:
                run = lib.get(member.run)
            except Exception:  # noqa: BLE001 - a deleted member is not queued
                continue
            for solve in preset_solves(preset):
                try:
                    manager.enqueue(run, preset=solve)
                    queued += 1
                except (ScenarioError, JobsError) as exc:  # another plan year (R1)
                    libraryjobs.flash("error", f"{run.name}: not queued ({exc})")
                    break
        libraryjobs.flash("success", f"{queued} solve(s) queued.")
        st.rerun()

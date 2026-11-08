"""
Fork: a structured picker for a scenario's year fields (ergonomics review S-2, decision 4).

A year field of the rent, home purchase, care and downturn events takes a calendar year or an
anchor (`builder.parse_year_ref`'s six forms): a calendar year, `age:<person>:<age>`,
`work:<person>` (that person's last work year), `after:<person>` (the year after it),
`purchase` (the home purchase's year) and `event:<id>` with an optional `+n` / `-n`. The page
used to take the text form only. This helper shows the forms as a "When" dropdown with the
fields each one needs, and keeps the text form as a fallback ("Type it").

The helper returns the **text form** (`builder.year_ref_text`'s output), not the parsed dict:
the page parses every year field once, with the scenario's event ids and the field's name in
its error message (`Scenario._year_ref`), and the page's draft keeps the text. `split_ref` and
`join_ref` are the pure halves, round-tripped against `parse_year_ref` / `year_ref_text` in
`tests/ui/test_year_ref_input.py`.

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

from owlplanner.library import ScenarioError
from owlplanner.library import builder

BLANK = "blank"
MODES = ("year", "age", "work", "after", "purchase", "event", "text")
MODE_LABELS = {
    "year": "Calendar year",
    "age": "At an age",
    "work": "Last work year",
    "after": "Year after last work",
    "purchase": "Home purchase year",
    "event": "Another event's year",
    "text": "Type it",
}


def split_ref(text, ids=()):
    """(mode, parts) of a year field's text form; "text" with the raw text when it does not
    parse, BLANK for an empty field."""
    raw = "" if text is None else str(text)
    if not raw.strip():
        return BLANK, {}
    try:
        ref = builder.parse_year_ref(raw, ids=list(ids))
    except ScenarioError:
        return "text", {"text": raw}
    if "year" in ref:
        return "year", {"year": int(ref["year"])}
    anchor = ref.get("anchor")
    if anchor == "age":
        return "age", {"person": ref["person"], "age": float(ref["age"])}
    if anchor == "work_end":
        return ("after" if ref.get("after") else "work"), {"person": ref["person"]}
    if anchor == "purchase":
        return "purchase", {}
    if anchor == "event":
        return "event", {"id": ref["id"], "offset": int(ref.get("offset") or 0)}
    return "text", {"text": raw}


def join_ref(mode, parts):
    """The text form of (mode, parts); "" for BLANK."""
    if mode == BLANK:
        return ""
    if mode == "text":
        return str(parts.get("text") or "")
    if mode == "year":
        return builder.year_ref_text(int(parts["year"]))
    if mode == "age":
        return builder.year_ref_text({"anchor": "age", "person": parts["person"], "age": float(parts["age"])})
    if mode in ("work", "after"):
        return builder.year_ref_text({"anchor": "work_end", "person": parts["person"], "after": mode == "after"})
    if mode == "purchase":
        return "purchase"
    if mode == "event":
        return builder.year_ref_text({"anchor": "event", "id": parts["id"], "offset": int(parts.get("offset") or 0)})
    raise ValueError(f"unknown year mode {mode!r}")


def _with(options, value):
    """The options, with a stored value the options lack kept (a person renamed since)."""
    options = list(options)
    return options + ([value] if value is not None and value not in options else [])


def year_ref_input(container, label, text, key, *, names, ids, default_year, blank=None, own_id=None,
                   help=None):
    """A year field: "When" plus the fields its form needs; returns the text form.

    `ids` is a list of (event id, description) the "Another event's year" form offers (the
    event's own id, `own_id`, left out); `blank`, when given, is the meaning of an empty field
    ("the plan end") and adds it as the first choice. Widget keys start with `key`.
    """
    known = [i for i, _ in ids]
    mode, parts = split_ref(text, known)
    if mode == BLANK and blank is None:
        mode, parts = "year", {"year": int(default_year)}
    modes = ([BLANK] if blank is not None else []) + list(MODES)
    labels = {**MODE_LABELS, BLANK: f"Blank: {blank}" if blank else "Blank"}
    chosen = container.selectbox(label, modes, index=modes.index(mode), format_func=labels.get,
                                 key=f"{key}_mode", help=help)
    seed = parts if chosen == mode else {}
    first = names[0] if names else None
    if chosen == BLANK:
        return ""
    if chosen == "purchase":
        return "purchase"
    if chosen == "year":
        year = container.number_input("Year", value=int(seed.get("year", default_year)), step=1,
                                      min_value=1900, max_value=2200, format="%d", key=f"{key}_year")
        return join_ref("year", {"year": int(year)})
    if chosen in ("age", "work", "after"):
        people = _with(names, seed.get("person"))
        person = container.selectbox("Person", people, index=people.index(seed.get("person", first))
                                     if seed.get("person", first) in people else 0,
                                     key=f"{key}_person")
        if chosen != "age":
            return join_ref(chosen, {"person": person})
        age = container.number_input("Age", value=float(seed.get("age", 65.0)), step=1.0, min_value=0.0,
                                     max_value=120.0, format="%g", key=f"{key}_age")
        return join_ref("age", {"person": person, "age": age})
    if chosen == "event":
        described = dict(ids)
        choices = _with([i for i in known if i != own_id], seed.get("id"))
        if not choices:
            container.caption("No other event to anchor to yet.")
            return ""
        current = seed.get("id", choices[0])
        event = container.selectbox("Event", choices, index=choices.index(current) if current in choices else 0,
                                    format_func=lambda i: f"{i} ({described[i]})" if described.get(i) else i,
                                    key=f"{key}_event")
        offset = container.number_input("Years after it (negative: before)", value=int(seed.get("offset", 0)),
                                        step=1, format="%d", key=f"{key}_offset")
        return join_ref("event", {"id": event, "offset": int(offset)})
    shown = seed.get("text") if chosen == mode else (text or "")
    return container.text_input("Year (text form)", value=shown or "", key=f"{key}_text",
                                help="A calendar year, `age:<person>:<age>`, `work:<person>`, "
                                     "`after:<person>`, `purchase`, or `event:<id>` (with `+n` / `-n`).")

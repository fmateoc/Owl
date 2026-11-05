"""
The Collections page's "make variants" editors, read into `library.variants` dimensions.

Pure functions (no Streamlit calls), so the tests can feed them what `st.data_editor`
really returns (review AD1). The editor hands back `None` for a cell nobody typed in, but
`DataFrame.iterrows()` turns that `None` into NaN, which passed every `None` / `""` guard:
empty costs reached the plan as \\$0, an empty name became "nan", a loan without its default
terms failed in the builder. `records` reads each row with every missing cell as `None`.

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

import itertools
import math

import pandas as pd

from owlplanner.library import ScenarioError
from owlplanner.library.variants import DIMENSIONS

PLACE_COLUMNS = ["label", "name", "price", "state", "locality", "school_district", "move",
                 "property tax", "hoa", "insurance"]
FINANCING_COLUMNS = ["label", "kind", "term", "rate", "down", "closing", "extra", "name"]
SEQUENCE_COLUMNS = ["label", "sequence", "start"]
# A place's text fields: an empty cell keeps the parent's; "-" clears it (a place with no
# local income tax, from a parent that has one: White Plains from Yonkers).
CLEAR = "-"
# A sequence cell that clears the downturn overlay instead of naming one ("no downturn"):
# empty, or typed as none.
NO_SEQUENCE = ("", "-", "none", "no", "no downturn")


def places_table():
    return pd.DataFrame(columns=PLACE_COLUMNS)


def financing_table():
    return pd.DataFrame(columns=FINANCING_COLUMNS)


def sequences_table():
    """The downturn-sequence dimension (I11): one row per value, `start` a year or an anchor
    ("purchase", "after:Ari"); a sequence of `-` is the "no downturn" value."""
    return pd.DataFrame(columns=SEQUENCE_COLUMNS)


def _missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def records(df) -> list:
    """The editor's rows as dicts, a missing cell (None, NaN, blank text) as None."""
    out = []
    for row in df.to_dict("records"):
        out.append({k: (None if _missing(v) else (v.strip() if isinstance(v, str) else v))
                    for k, v in row.items()})
    return out


def number(value, what):
    """One editor cell as a number; a bad cell raises ScenarioError (flashed, AC6)."""
    if isinstance(value, bool):
        raise ScenarioError(f"{what} is not a number: {value!r}")
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ScenarioError(f"{what} is not a number: {value!r}") from None
    if not math.isfinite(x):
        raise ScenarioError(f"{what} is not a number: {value!r}")
    return x


_TRUE = {"true", "yes", "y", "1"}
_FALSE = {"false", "no", "n", "0"}


def flag(value, what) -> bool:
    """A true/false cell (review AD6: `bool("False")` is True). A checkbox gives a bool;
    typed text must be one of true/false, yes/no, 1/0."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise ScenarioError(f"{what} must be true or false, got {value!r}")


def claim_combos(names, texts):
    """[{person: age or None}, ...] over the per-person age lists (the claim dimension)."""
    per_person = []
    for person in names:
        text = (texts.get(person) or "").strip()
        if not text:
            per_person.append([None])
        else:
            per_person.append([number(part, f"{person}'s claiming age")
                               for part in text.replace(";", ",").split(",") if part.strip()])
    combos = [dict(zip(names, ages, strict=True)) for ages in itertools.product(*per_person)]
    if all(age is None for combo in combos for age in combo.values()):
        return []
    return combos


def _years(text, what):
    try:
        return [int(part) for part in text.replace(";", ",").split(",") if part.strip()]
    except ValueError:
        raise ScenarioError(f"not a list of years ({what}): {text!r}") from None


def death_values(person, text):
    """[{"person", "age"}, ...] for one person's death ages (the I2 dimension)."""
    return [{"person": person, "age": age} for age in _years(text, "death ages")]


def _sequence_value(row) -> dict:
    label = row.get("label")
    raw = row.get("sequence")
    text = "" if raw is None else str(raw).strip().lower()
    if text in NO_SEQUENCE:  # "" is the empty cell: the "no downturn" value
        if row.get("start") is not None:
            raise ScenarioError(
                f"sequence row {label!r} names no sequence but a placement: name a sequence, "
                f"or use {CLEAR!r} for no downturn")
        return {"label": label, "sequence": None} if label is not None else {"sequence": None}
    value = {"sequence": str(raw).strip()}
    if label is not None:
        value["label"] = str(label)
    if row.get("start") is None:
        raise ScenarioError(
            f"sequence {value['sequence']!r}: give its placement (a year, or an anchor "
            "like 'purchase')")
    value["start"] = str(row["start"]).strip()
    return value


def _place_value(row) -> dict:
    label = row["label"]
    value = {"label": label}
    if row.get("name") is not None:
        value["name"] = str(row["name"])
    if row.get("price") is not None:
        value["price"] = number(row["price"], f"place {label}: price")
    place = {}
    for field in ("state", "locality", "school_district"):
        if row.get(field) is not None:
            text = str(row[field])
            place[field] = "" if text == CLEAR else text
    if row.get("move") is not None:
        place["move"] = flag(row["move"], f"place {label}: move")
    if place:
        value["place"] = place
    costs = {}
    for field in ("property tax", "hoa", "insurance"):
        if row.get(field) is not None:
            costs[field] = number(row[field], f"place {label}: {field}")
    if costs:
        value["costs"] = costs
    return value


def _financing_value(row) -> dict:
    label = row["label"]
    kind = str(row.get("kind") or "cash").strip().lower()
    if kind in ("loan", "mortgage"):
        financing = {"kind": "loan"}
    elif kind == "cash":
        financing = {"kind": "cash"}
    else:
        raise ScenarioError(f"financing {label}: kind must be cash or loan, got {row.get('kind')!r}")
    for field in ("term", "rate", "down", "closing", "extra"):
        if row.get(field) is not None:
            financing[field] = number(row[field], f"financing {label}: {field}")
    if row.get("name") is not None:
        financing["name"] = str(row["name"])
    return {"label": label, "financing": financing}


def dimensions(names, years_text, places, fins, work_person, work_years, claim_texts,
               death_person="(none)", death_ages="", seqs=None):
    """The make-variants dimensions from the editors' raw values (reviews AC6, AD1, AD6).

    Returns ``(dimensions, skipped)``. Raises ScenarioError on a cell that is not a number,
    a move that is not true/false, a kind that is not cash/loan, or a year field that is not
    a list of years (the page flashes it and makes nothing). An empty cell keeps the
    parent's value; a table row with data but no label is skipped and named in `skipped`.
    """
    out = {}
    skipped = []
    if years_text.strip():
        out["year"] = _years(years_text, "purchase years")
    for kind, table, build in (("place", places, _place_value), ("financing", fins, _financing_value)):
        for row in records(table):
            if row.get("label") is None:
                if any(v is not None for v in row.values()):
                    skipped.append(f"a {kind} row with no label")
                continue
            row["label"] = str(row["label"])
            out.setdefault(kind, []).append(build(row))
    if work_person != "(none)" and work_years.strip():
        out["work"] = [{"person": work_person, "end": end} for end in _years(work_years, "last work years")]
    combos = claim_combos(names, claim_texts)
    if combos:
        out["claim"] = combos
    if death_person != "(none)" and (death_ages or "").strip():
        out["death"] = death_values(death_person, death_ages)
    for row in records(seqs) if seqs is not None else []:
        if not any(v is not None for v in row.values()):
            continue  # the empty row the editor adds
        out.setdefault("sequence", []).append(_sequence_value(row))
    return out, skipped


def member_values(text):
    """A hand-added member's variant values from "dimension: label" pairs (section 9.3: a
    member with no values is listed beside the grid; values place it).

    Pairs are separated by `;` or newlines ("year: 2027; place: yonkers"). The year's label
    is stored as a calendar year (int, what "make variants" stores, so one grid cell holds
    both routes); every other label stays text. A dimension that is not one of `DIMENSIONS`
    is refused (AD6's rule: a typo is refused). Raises ScenarioError on a part that is not a
    pair or on a year that is not one calendar year.
    """
    out = {}
    for part in (text or "").replace("\n", ";").split(";"):
        part = part.strip()
        if not part:
            continue
        dim, _, label = part.partition(":")
        dim, label = dim.strip(), label.strip()
        if not dim or not label:
            raise ScenarioError(f"not a 'dimension: label' pair: {part!r}")
        if dim not in DIMENSIONS:
            raise ScenarioError(f"not one of the dimensions {list(DIMENSIONS)}: {part!r}")
        if dim == "year":
            years = _years(label, "the year's label")
            if len(years) != 1:
                raise ScenarioError(f"year: give one calendar year, got {label!r}")
            out[dim] = years[0]
        else:
            out[dim] = label
    return out


def values_text(values) -> str:
    """A member's values as `member_values`' editable text ("year: 2027; place: yonkers")."""
    return "; ".join(f"{dim}: {label}" for dim, label in (values or {}).items())


def grid_layout(dims, saved=None):
    """(rows, columns) for a collection's grid (review AD2).

    A saved layout with at least one column is used as saved (its rows may be empty: one
    row). Otherwise the columns are the purchase year when the members vary it (else the
    last dimension), and the rows are every other dimension, in the variant order (place,
    financing, work, claim, death, sequence) -- section 9.3's pivot, with no dimension
    dropped.
    """
    dims = list(dims)
    saved = saved or {}
    columns = [d for d in saved.get("columns") or [] if d in dims]
    if columns:
        rows = [d for d in saved.get("rows") or [] if d in dims and d not in columns]
        return rows, columns
    order = [d for d in DIMENSIONS if d in dims] + sorted(d for d in dims if d not in DIMENSIONS)
    if not order:
        return [], []
    columns = ["year"] if "year" in order else [order[-1]]
    return [d for d in order if d not in columns], columns

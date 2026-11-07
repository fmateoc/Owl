""""Make variants" (design section 9.3, step 6): one child scenario per value of a chosen
dimension, for a collection.

From a run: "choose a dimension (purchase year 2027, 2029, 2031, 2034, 2038; place;
financing; last work year; claiming ages) and get one child draft per value, all in one
collection, queued together." `plan_variants` takes the run's scenario and a mapping
``{dimension: [value, ...]}`` and returns one `Variant` per **combination** of values
(`itertools.product` over the dimensions, in the mapping's order): one dimension is the
design's case, and several are the grid of section 4 ("place x year x financing"). Each
value is a small edit to the scenario's events:

- ``place``: {"label", "name", "price", "place", "costs"} -- the purchase event's home
  name, price, place (state, locality, school district, move) and yearly costs (property
  tax, HOA, insurance); only the keys given change.
- ``year``: a calendar year -- the purchase event's year (the rent end and the owner's
  lines follow by construction, section 6.2).
- ``financing``: {"label", "financing"} -- the purchase event's financing (cash, or a loan
  with term, rate, down, closing, extra, name); its ``name`` may hold ``{place}``, filled
  from the place value's label.
- ``work``: {"person", "end", "label"?} -- the person's full-time work event's last year.
- ``claim``: {person: age or None} -- each named person's claiming age (None: let Owl
  choose); a person with no claim event gets one.
- ``death`` (I2): {"person", "age", "label"?} -- when that person dies (their life horizon;
  Owl's own death mechanics do the rest). A person with no death event gets one.
- ``sequence`` (I11): {"label"?, "sequence", "start"} -- the named downturn sequence overlaid
  on the run's own rate path from a year or anchor ("the purchase year", `after:Ari`), the
  single `downturn` event of the scenario (step 5b); ``sequence: None`` drops the overlay
  (a "no downturn" cell in a grid).

The variant's `values` ({dimension: label}) is what a collection member stores and the grid
view keys its rows and columns on (`store.Member`). The children are scenarios like any
other: `Library.save_run` freezes them (canonicalized; the change summary against the
parent is computed there).

A purchase is at most one per scenario (D6), so a "place" value that implies a different home
is an edit of the same event, never a second purchase; the same holds for the downturn event
(one overlay per scenario) and one death per person.
"""

from __future__ import annotations

import copy
import itertools
import math
from dataclasses import dataclass
from typing import Any

from . import builder
from .scenario import ScenarioError, validate

DIMENSIONS = ("place", "year", "financing", "work", "claim", "death", "sequence")

# The dimensions that edit the one purchase event (D6: one purchase per scenario).
_PURCHASE_DIMENSIONS = ("place", "year", "financing")

# What a collection member's `values` may key on: the make-variants dimensions plus the
# sensitivity tornado's mover label (`tornado` stores {"mover": <label>} and the grid keys
# on it like a dimension). `ui/variant_tables.member_values` accepts exactly these (AF2).
VALUE_KEYS = tuple(DIMENSIONS) + ("mover",)


@dataclass(frozen=True)
class Variant:
    """One child: its name label, its dimension values, and its scenario."""

    label: str
    values: dict
    scenario: dict


def _names(scenario: dict) -> list:
    return list(((scenario.get("case") or {}).get("basic_info") or {}).get("names") or [])


def _events(scenario: dict) -> list:
    events = scenario.get("events") or []
    return [e for e in events if isinstance(e, dict)]


def _event_ids(scenario: dict) -> list:
    """The scenario's event ids (`builder.parse_year_ref` settles `event:<id>-<n>` against
    an id that itself ends in `-<digits>`, review X5/AF3)."""
    return [e.get("id") for e in _events(scenario)]


def _start_ref(value: Any, where: str, ids=None) -> dict:
    """A downturn's placement: a year field ({"year"/anchor}), a bare year, or its editable
    text form ("purchase", "after:Ari", "age:Ari:86"; `builder.parse_year_ref`). `ids` (the
    scenario's event ids) settles `event:<id>-<n>` (review AF3)."""
    if isinstance(value, str):
        return builder.parse_year_ref(value, where, ids=ids)
    return builder._year_ref(value, where)


def _one_event(scenario: dict, kind: str, dimension: str, person: str = None) -> dict:
    found = [e for e in _events(scenario) if e.get("kind") == kind
             and (person is None or e.get("person") == person)]
    if not found:
        who = f" for {person!r}" if person else ""
        # How to get one (UX review B2): an imported case holds its purchase as hand rows,
        # which no dimension can vary.
        how = {
            "purchase": " An imported case holds its home as Fixed Assets rows, not as an event: "
                        "start from a run without the home (the rent-only baseline) and add the "
                        "purchase on the Scenario page (\"Edit the scenario\" on the Run page).",
        }.get(kind, " Add one on the Scenario page (\"Edit the scenario\" on the Run page).")
        raise ScenarioError(
            f"the {dimension!r} dimension needs a {kind} event{who} in the scenario: "
            f"nothing to vary.{how}"
        )
    if len(found) > 1:
        who = "" if person is None else f" for {person!r}"
        raise ScenarioError(
            f"the {dimension!r} dimension found {len(found)} {kind} events{who}: it varies one"
        )
    return found[0]


def _label_text(value: Any) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _age_text(age: float) -> str:
    from .view import age_text

    return age_text(float(age))


def _value_label(dimension: str, value: Any, ids=None) -> str:
    """The grid label of one value ("yonkers", 2027, "cash", "Ari 67y0m / Noa 70y0m")."""
    if dimension == "year":
        return int(value)
    if dimension == "claim":
        return " / ".join(
            f"{person} {_age_text(age)}" if age is not None else f"{person}: let Owl choose"
            for person, age in value.items())
    if isinstance(value, dict) and value.get("label") is not None:
        return _label_text(value["label"])
    if dimension == "work":
        return f"{value.get('person')} to {value.get('end')}"
    if dimension == "death":
        return f"{value.get('person')} dies at {int(value.get('age'))}"
    if dimension == "sequence":
        if value.get("sequence") is None:
            return "no downturn"
        where = builder.year_ref_text(_start_ref(value.get("start"), "sequence.start", ids))
        return f"{value.get('sequence')} at {where}"
    raise ScenarioError(f"{dimension}: value {value!r} needs a 'label'")


def _non_finite(obj: Any, where: str) -> None:
    """Refuse NaN or infinity anywhere in a value (review AD1): a NaN from an editor cell
    passes `<= 0` and type checks alike, and `normalize` then stores it as None."""
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ScenarioError(f"{where} is not a number ({obj!r}): an empty or unreadable cell?")
    if isinstance(obj, dict):
        for key, item in obj.items():
            _non_finite(item, f"{where}.{key}")
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _non_finite(item, f"{where}[{i}]")


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_value(dimension: str, value: Any, scenario: dict) -> None:
    _non_finite(value, dimension)
    if dimension == "year":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ScenarioError(f"year: a value must be a calendar year, got {value!r}")
        return
    if not isinstance(value, dict):
        raise ScenarioError(f"{dimension}: a value must be a dict, got {value!r}")
    if dimension == "place":
        if value.get("label") is None:
            raise ScenarioError("place: each value needs a 'label'")
        for field in ("name", "place", "costs"):
            if field not in value:
                continue
            ok = (isinstance(value[field], dict) if field in ("place", "costs")
                  else isinstance(value[field], (str, int, float)) and not isinstance(value[field], bool))
            if not ok:
                what = "a dict" if field in ("place", "costs") else "a number or a string"
                raise ScenarioError(f"place: {field!r} of a value must be {what}, got {value[field]!r}")
        # The price is typed here too (review AC5): the shape check above takes a string,
        # and comparing one with `<= 0` raised TypeError where every other refusal is a
        # ScenarioError (what `ui/Collections.py` flashes).
        price = value.get("price")
        if price is not None and (not isinstance(price, (int, float))
                                  or isinstance(price, bool) or price <= 0):
            raise ScenarioError(f"place: price must be a positive number (today's dollars), got {price!r}")
        for field, amount in (value.get("costs") or {}).items():
            if not _number(amount) or amount < 0:
                raise ScenarioError(f"place: cost {field!r} must be a yearly amount of 0 or more, got {amount!r}")
        for field, item in (value.get("place") or {}).items():
            ok = isinstance(item, bool) if field == "move" else isinstance(item, str)
            if not ok:
                what = "true or false" if field == "move" else "text"
                raise ScenarioError(f"place: {field!r} must be {what}, got {item!r}")
    elif dimension == "financing":
        if value.get("label") is None:
            raise ScenarioError("financing: each value needs a 'label'")
        fin = value.get("financing")
        if not isinstance(fin, dict) or fin.get("kind") not in ("cash", "loan"):
            raise ScenarioError("financing: each value needs a 'financing' of kind 'cash' or 'loan'")
        if fin.get("kind") == "loan" and ("term" not in fin or "rate" not in fin):
            raise ScenarioError("financing: a loan value needs 'term' and 'rate'")
        for field in ("term", "rate", "down", "closing", "extra"):
            if field in fin and not _number(fin[field]):
                raise ScenarioError(f"financing: {field!r} must be a number, got {fin[field]!r}")
        if "name" in fin and not isinstance(fin["name"], str):
            raise ScenarioError(f"financing: 'name' must be text, got {fin['name']!r}")
    elif dimension == "work":
        person, end = value.get("person"), value.get("end")
        if not isinstance(person, str) or not isinstance(end, int) or isinstance(end, bool):
            raise ScenarioError("work: each value needs 'person' and a calendar year 'end'")
    elif dimension == "claim":
        if not value:
            raise ScenarioError("claim: each value must name at least one person")
        names = _names(scenario)
        for person, age in value.items():
            if person not in names:
                raise ScenarioError(f"claim: {person!r} is not one of the case's people {names}")
            if age is not None and (not isinstance(age, (int, float)) or isinstance(age, bool) or age <= 0):
                raise ScenarioError(f"claim: {person!r}'s age must be a positive number or None")
    elif dimension == "death":
        names = _names(scenario)
        person, age = value.get("person"), value.get("age")
        if not isinstance(person, str) or person not in names:
            raise ScenarioError(f"death: {person!r} is not one of the case's people {names}")
        if not isinstance(age, int) or isinstance(age, bool) or not 1 <= age <= builder.DEATH_AGE_MAX:
            raise ScenarioError(
                f"death: {person!r}'s age must be a whole number of years "
                f"1-{builder.DEATH_AGE_MAX}, got {age!r}")
        builder.check_death_age(person, age, scenario.get("case") or {}, scenario,
                                where=f"death: {person!r}")
        builder.check_death_window(scenario, person, age, where=f"death: {person!r}")
        builder.check_death_after_work(scenario, person, age, where=f"death: {person!r}")
    elif dimension == "sequence":
        sequence = value.get("sequence")
        if sequence is None:
            return
        from .sequences import SequenceError, sequences  # lazy: reads the data file

        try:
            known = sequences()
        except SequenceError as exc:
            raise ScenarioError(str(exc)) from exc
        if sequence not in known:
            raise ScenarioError(f"sequence: {sequence!r} is not one of {sorted(known)}")
        if "start" not in value:
            raise ScenarioError("sequence: each value needs a 'start' (a year or an anchor)")
        _start_ref(value["start"], "sequence: start", _event_ids(scenario))
        # A downturn generates the run's rates table (step 5b); one that already reads a table
        # cannot take an overlay (`builder._check_table_events` says the same at build time).
        if scenario.get("rates_table") is not None:
            raise ScenarioError(
                "sequence: this run holds a hand-entered rates table, and a downturn sequence "
                "generates its own: edit the table instead")
        if ((scenario.get("case") or {}).get("rates_selection") or {}).get("method") == "table":
            raise ScenarioError(
                "sequence: this case reads a rates table (rates_selection.method = 'table') "
                "and a downturn overlays the case's own rate method: edit the table instead")


def _apply_value(dimension: str, value: Any, scenario: dict, place_label) -> None:
    """Edit one value into the scenario's events (in place; the scenario is a fresh copy)."""
    if dimension == "year":
        _one_event(scenario, "purchase", "year")["year"] = {"year": int(value)}
        return
    if dimension == "place":
        event = _one_event(scenario, "purchase", "place")
        for field in ("name", "price"):
            if field in value:
                event[field] = value[field]
        for field in ("place", "costs"):
            if field in value:
                event[field] = {**dict(event.get(field) or {}), **dict(value[field])}
        return
    if dimension == "financing":
        event = _one_event(scenario, "purchase", "financing")
        financing = dict(value["financing"])
        name = financing.get("name")
        if isinstance(name, str) and "{place}" in name:
            if place_label is None:
                raise ScenarioError(
                    "financing: the loan's name holds '{place}' but this call varies no place "
                    "value (give the name explicitly, or vary 'place' too)"
                )
            financing["name"] = name.replace("{place}", _label_text(place_label))
        event["financing"] = financing
        return
    if dimension == "work":
        person, end = value["person"], int(value["end"])
        found = [e for e in _events(scenario)
                 if e.get("kind") == "work" and e.get("person") == person
                 and e.get("level", "full") == "full"]
        if len(found) != 1:
            raise ScenarioError(
                f"work: {person!r} has {len(found)} full-time work events; the dimension "
                "varies the last work year of one")
        found[0]["end"] = end
        return
    if dimension == "claim":
        for person, age in value.items():
            event = next((e for e in _events(scenario)
                          if e.get("kind") == "claim" and e.get("person") == person), None)
            if event is None:
                event = {"id": f"claim-{person.lower()}", "kind": "claim", "person": person}
                scenario.setdefault("events", []).append(event)
            event["age"] = None if age is None else float(age)
        return
    if dimension == "death":
        person, age = value["person"], int(value["age"])
        event = next((e for e in _events(scenario)
                      if e.get("kind") == "death" and e.get("person") == person), None)
        if event is None:
            event = {"id": f"death-{person.lower()}", "kind": "death", "person": person}
            scenario.setdefault("events", []).append(event)
        event["age"] = age
        return
    if dimension == "sequence":
        downs = [e for e in _events(scenario) if e.get("kind") == "downturn"]
        if value.get("sequence") is None:  # "no downturn": the overlay is taken off
            if downs:
                scenario["events"] = [e for e in scenario.get("events") or []
                                      if not (isinstance(e, dict) and e.get("kind") == "downturn")]
            return
        event = downs[0] if downs else None
        if event is None:
            event = {"id": "downturn", "kind": "downturn"}
            scenario.setdefault("events", []).append(event)
        event["sequence"] = value["sequence"]
        event["start"] = _start_ref(value["start"], "sequence: start", _event_ids(scenario))
        return


def _slug(text: str) -> str:
    """A name fragment: lowercased, non-alphanumerics collapsed to dashes ("Ari 67y0m" ->
    "ari-67y0m"), as `store.Library._slugify` names folders."""
    out = "".join(c if c.isalnum() else "-" for c in str(text).lower())
    return "-".join(part for part in out.split("-") if part) or "variant"


def plan_variants(scenario: dict, dimensions: dict) -> list:
    """One `Variant` per combination of the dimensions' values (section 9.3).

    ``dimensions`` is ``{dimension: [value, ...]}``, in the order the labels join ("place",
    "year", "financing" gives "yonkers-2027-mortgage"); the product is over the values in
    the order given. The input scenario is never edited (every child is a deep copy).
    Raises ScenarioError for an unknown dimension, an empty value list, or a value that does
    not fit the scenario.
    """
    if not dimensions:
        raise ScenarioError(f"no dimension given: choose one of {list(DIMENSIONS)}")
    for dimension, values in dimensions.items():
        if dimension not in DIMENSIONS:
            raise ScenarioError(f"unknown dimension {dimension!r}: choose one of {list(DIMENSIONS)}")
        if not isinstance(values, (list, tuple)) or not values:
            raise ScenarioError(f"{dimension}: give at least one value")
        if dimension in _PURCHASE_DIMENSIONS:
            _one_event(scenario, "purchase", dimension)
        for value in values:
            _check_value(dimension, value, scenario)

    keys = list(dimensions)
    ids = _event_ids(scenario)
    variants = []
    for combo in itertools.product(*(dimensions[key] for key in keys)):
        child = copy.deepcopy(scenario)
        labels = {key: _value_label(key, value, ids) for key, value in zip(keys, combo, strict=True)}
        place_label = labels.get("place")
        for key, value in zip(keys, combo, strict=True):
            _apply_value(key, value, child, place_label)
        label = "-".join(_slug(labels[key]) for key in keys)
        # A death and a work end varied together must still agree (review AI6): each is
        # checked against the parent at the door, the pair only here.
        builder.check_death_after_work(child, where=label)
        validate(child)  # the child is a scenario like any other
        variants.append(Variant(label=label, values=labels, scenario=child))
    return variants

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

The variant's `values` ({dimension: label}) is what a collection member stores and the grid
view keys its rows and columns on (`store.Member`). The children are scenarios like any
other: `Library.save_run` freezes them (canonicalized; the change summary against the
parent is computed there).

Not covered here (the design's later increments): the downturn-sequence dimension (I11) and
the longevity dimension (I2, first death at 75 / 80 / 85). A purchase is at most one per
scenario (D6), so a "place" value that implies a different home is an edit of the same
event, never a second purchase.
"""

from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass
from typing import Any

from .scenario import ScenarioError, validate

DIMENSIONS = ("place", "year", "financing", "work", "claim")

# The dimensions that edit the one purchase event (D6: one purchase per scenario).
_PURCHASE_DIMENSIONS = ("place", "year", "financing")


@dataclass(frozen=True)
class Variant:
    """One child: its name label, its dimension values, and its scenario."""

    label: str
    values: dict
    scenario: dict


def _names(scenario: dict) -> list:
    return list(((scenario.get("case") or {}).get("basic_info") or {}).get("names") or [])


def _events(scenario: dict) -> list:
    events = scenario.get("events")
    return [e for e in events if isinstance(e, dict)]


def _one_event(scenario: dict, kind: str, dimension: str, person: str = None) -> dict:
    found = [e for e in _events(scenario) if e.get("kind") == kind
             and (person is None or e.get("person") == person)]
    if not found:
        who = f" for {person!r}" if person else ""
        raise ScenarioError(
            f"the {dimension!r} dimension needs a {kind} event{who} in the scenario: "
            "nothing to vary"
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


def _value_label(dimension: str, value: Any) -> str:
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
    raise ScenarioError(f"{dimension}: value {value!r} needs a 'label'")


def _check_value(dimension: str, value: Any, scenario: dict) -> None:
    if dimension == "year":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ScenarioError(f"year: a value must be a calendar year, got {value!r}")
        return
    if not isinstance(value, dict):
        raise ScenarioError(f"{dimension}: a value must be a dict, got {value!r}")
    if dimension == "place":
        if value.get("label") is None:
            raise ScenarioError("place: each value needs a 'label'")
        for field in ("name", "price", "place", "costs"):
            if field not in value:
                continue
            ok = (isinstance(value[field], dict) if field in ("place", "costs")
                  else isinstance(value[field], (str, int, float)) and not isinstance(value[field], bool))
            if not ok:
                what = "a dict" if field in ("place", "costs") else "a number or a string"
                raise ScenarioError(f"place: {field!r} of a value must be {what}, got {value[field]!r}")
        price = value.get("price")
        if price is not None and price <= 0:
            raise ScenarioError(f"place: price must be a positive number (today's dollars), got {price!r}")
    elif dimension == "financing":
        if value.get("label") is None:
            raise ScenarioError("financing: each value needs a 'label'")
        fin = value.get("financing")
        if not isinstance(fin, dict) or fin.get("kind") not in ("cash", "loan"):
            raise ScenarioError("financing: each value needs a 'financing' of kind 'cash' or 'loan'")
        if fin.get("kind") == "loan" and ("term" not in fin or "rate" not in fin):
            raise ScenarioError("financing: a loan value needs 'term' and 'rate'")
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
    variants = []
    for combo in itertools.product(*(dimensions[key] for key in keys)):
        child = copy.deepcopy(scenario)
        labels = {key: _value_label(key, value) for key, value in zip(keys, combo, strict=True)}
        place_label = labels.get("place")
        for key, value in zip(keys, combo, strict=True):
            _apply_value(key, value, child, place_label)
        label = "-".join(_slug(labels[key]) for key in keys)
        validate(child)  # the child is a scenario like any other
        variants.append(Variant(label=label, values=labels, scenario=child))
    return variants

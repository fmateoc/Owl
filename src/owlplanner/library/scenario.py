"""Scenario schema v1 for the run library: hand rows only.

A scenario is the source of truth of a run (`fork-notes/run-library-design.md`, section 6).
Schema version 1 holds Owl's case dictionary (`case`) and the HFP workbook tables (`hfp`)
as JSON and nothing else: every row is a row the user entered or imported ("hand rows"),
plus the run's own dates: `plan_year` (the calendar year the balances and year rows were
entered for, R1) and `as_of` (the balances' date -- `basic_info.start_date`, the Account
Balances page's "Account balance date" -- which every solve of the run freezes Owl's "today"
to, section 8.3 b).  Events and the builder arrive in a later schema version (section 6.3a);
each format change ships a migration (`migrate`).

Canonical form (the inputs hash, section 5, S10): keys sorted, compact separators, and every
number kept as entered: an int stays an int and a float stays a float (V3), because the generated
TOML keeps them apart (`toml_io._clean_float` writes near-integer floats as `N.0` deliberately),
so they are not equal documents. Two byte-different documents that differ only in key order or
whitespace hash the same. Non-finite floats (NaN, inf) are stored as null in tables; `validate`
rejects them, and `None`, inside the case dictionary (V4: TOML cannot store either).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

SCHEMA_VERSION = 1

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Version of the generation code that turns a scenario into Case.toml / HFP.xlsx
# (library.casefiles). Part of the inputs hash: a change here makes old runs "built with
# an older builder" instead of aliasing two different outputs (section 5, R9).
BUILDER_VERSION = 1


class ScenarioError(ValueError):
    """A scenario document is not valid for this schema version."""


def normalize(obj: Any) -> Any:
    """Recursively prepare a JSON value for canonical serialization (types preserved)."""
    if obj is None or isinstance(obj, (bool, str, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (list, tuple)):
        return [normalize(x) for x in obj]
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                raise ScenarioError(f"non-string key in scenario: {key!r}")
            out[key] = normalize(value)
        return out
    raise ScenarioError(f"value of type {type(obj).__name__} cannot be stored: {obj!r}")


def canonical_json(obj: Any) -> str:
    """Canonical JSON text: sorted keys, compact separators, normalized numbers."""
    return json.dumps(normalize(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def pretty_json(obj: Any) -> str:
    """Human-editable JSON text (the user may open scenario.json in an editor)."""
    return json.dumps(normalize(obj), sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def scenario_hash(scenario: dict) -> str:
    """The inputs hash: canonical scenario plus the builder version (section 5)."""
    text = canonical_json({"builder_version": BUILDER_VERSION, "scenario": scenario})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check_case_values(obj: Any, where: str) -> None:
    """Reject what TOML cannot store (V4): None values and non-finite floats, anywhere in case."""
    if obj is None:
        raise ScenarioError(
            f"None value at {where}: the generated TOML would silently drop it"
        )
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ScenarioError(f"non-finite float at {where}: the generated TOML cannot store it")
        return
    if isinstance(obj, (bool, str, int)):
        return
    if isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            _check_case_values(value, f"{where}[{i}]")
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            _check_case_values(value, f"{where}.{key}")
        return
    raise ScenarioError(f"value of type {type(obj).__name__} at {where} cannot be stored")


def validate(scenario: Any) -> dict:
    """Check a scenario document against schema version 1 and return it."""
    if not isinstance(scenario, dict):
        raise ScenarioError(f"scenario must be a dict, got {type(scenario).__name__}")
    version = scenario.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ScenarioError(
            f"schema_version {version!r} cannot be read (this build handles {SCHEMA_VERSION}); "
            "the run stays readable from its generated files (design section 6.3a)"
        )
    case = scenario.get("case")
    if not isinstance(case, dict):
        raise ScenarioError("scenario.case must be a dict (the Owl case dictionary)")
    _check_case_values(case, "case")
    hfp = scenario.get("hfp")
    if not isinstance(hfp, dict):
        raise ScenarioError("scenario.hfp must be a dict of tables")
    for name, table in hfp.items():
        if not isinstance(name, str):
            raise ScenarioError(f"hfp table name must be a string: {name!r}")
        if not isinstance(table, dict) or not isinstance(table.get("columns"), list) \
                or not isinstance(table.get("rows"), list):
            raise ScenarioError(f"hfp table {name!r} must be {{'columns': [...], 'rows': [[...]]}}")
        width = len(table["columns"])
        for i, row in enumerate(table["rows"]):
            if not isinstance(row, list) or len(row) != width:
                raise ScenarioError(f"hfp table {name!r}, row {i}: expected {width} values")
    plan_year = scenario.get("plan_year")
    if plan_year is not None and not isinstance(plan_year, int):
        raise ScenarioError(f"plan_year must be an int, got {plan_year!r}")
    as_of = scenario.get("as_of")
    if as_of is not None:
        if not isinstance(as_of, str) or not ISO_DATE_RE.match(as_of):
            raise ScenarioError(f"as_of must be an ISO date string ('YYYY-MM-DD'), got {as_of!r}")
        if plan_year is not None and int(as_of[:4]) != plan_year:
            raise ScenarioError(
                f"as_of {as_of} does not fall in the run's plan year {plan_year}: a run is "
                "solved at its own balances' date (design section 8.3 b)"
            )
    return scenario


def migrate(scenario: dict) -> dict:
    """Bring a scenario up to SCHEMA_VERSION. Version 1 is the first: nothing to migrate."""
    version = scenario.get("schema_version")
    if version == SCHEMA_VERSION:
        return scenario
    raise ScenarioError(f"no migration from schema_version {version!r}")


def _short(value: Any, limit: int = 40) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def diff_summaries(old: Any, new: Any, prefix: str = "", limit: int = 20) -> list[str]:
    """A field-by-field diff of two scenarios in words (design section 7).

    Hand rows (schema v1) are diffed structurally; worded-per-event summaries arrive with
    the scenario model (step 4). At most `limit` lines; the last line counts the rest.
    """
    changes: list[str] = []
    _diff_into(old, new, prefix, changes)
    if len(changes) > limit:
        rest = len(changes) - limit
        changes = changes[:limit] + [f"... and {rest} more change(s)"]
    return changes


def _diff_into(old: Any, new: Any, where: str, out: list[str]) -> None:
    # Canonical text, not Python equality: 1 == 1.0 == True in Python, but the hash and the
    # generated TOML tell them apart (T4).
    if canonical_json(old) == canonical_json(new):
        return
    label = where or "scenario"
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new)):
            path = f"{label}.{key}" if where else str(key)
            if key not in old:
                out.append(f"{path}: added ({_short(new[key])})")
            elif key not in new:
                out.append(f"{path}: removed (was {_short(old[key])})")
            else:
                _diff_into(old[key], new[key], path, out)
        return
    if isinstance(old, list) and isinstance(new, list):
        if len(old) == len(new):
            for i, (a, b) in enumerate(zip(old, new, strict=True)):
                _diff_into(a, b, f"{label}[{i}]", out)
        else:
            out.append(f"{label}: {len(old)} -> {len(new)} rows")
        return
    out.append(f"{label}: {_short(old)} -> {_short(new)}")

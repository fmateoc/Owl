"""Scenario schema for the run library: hand rows, and (since v2) events and their builder.

A scenario is the source of truth of a run (`fork-notes/run-library-design.md`, section 6).
Schema version 1 holds Owl's case dictionary (`case`) and the HFP workbook tables (`hfp`)
as JSON and nothing else: every row is a row the user entered or imported ("hand rows").
Version 2 (build step 4) adds `events` (work, claiming, rent, a home purchase, care; D6) whose
coupled edits the builder generates (`library.builder.build`), with provenance markers: a
generated row or cell is marked with the event that produced it and regenerated wholesale,
hand rows are untouched (section 6.3, markers first per S11). Version 3 (build step 5b, D11)
adds the optional `rates_table` (a year-by-year rates table the run's `rates.csv` is written
from) and the `downturn` event kind (a named sequence placed at a year, I11); an older reader
would silently drop the table and reject the event, so they get their own version. Each
format change ships a migration (`migrate`).

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
from typing import Any

SCHEMA_VERSION = 3

# Version of the generation code that turns a scenario into Case.toml / HFP.xlsx / rates.csv
# (library.casefiles and library.builder). Part of the inputs hash: a change here makes old runs
# "built with an older builder" instead of aliasing two different outputs (section 5, R9).
# 3 (step 4, second review): a person with no claim event keeps the hand case's withSSAges
# choice (X7), and a purchase's keys at the builder's defaults leave the canonical form (X4).
# 4 (step 5b): the run's rates.csv (a downturn sequence generates it; D11).
# 5 (step 5b, third review AB1): a downturn run's case resets the hand case's reverse_sequence /
# roll_sequence, which its generated table already carries.
# 6 (UX review B2): a purchase without a move whose school district is blank keeps the case's
# district (it used to set it to ""; "-" now states none), and a purchase over a hand home
# still owned is refused.
# Not bumped (local-use review D2): a purchase with a move in the plan's first year now sets the
# starting residence instead of `moves = [{year = <first year>}]`. Owl refuses that move, so no
# run built the old way could be solved, and a bump would move every run's inputs hash.
BUILDER_VERSION = 6


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
    """The inputs hash: canonical scenario plus the builder version (section 5).

    Plus a hash of the named downturn sequences the scenario's events use (name + window,
    review Z7): the windows are builder input (`data/downturn_sequences.toml`), the generated
    `rates.csv` changes with them, and two runs with different frozen files must not share a
    hash. Only a scenario with a downturn event gains this term; runs without one keep the
    hash they had (the builder version covers builder *code*, not this data file).
    """
    payload: dict[str, Any] = {"builder_version": BUILDER_VERSION, "scenario": scenario}
    windows = _sequence_windows(scenario)
    if windows:
        payload["sequence_windows"] = windows
    text = canonical_json(payload)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sequence_windows(scenario: dict) -> dict:
    """{sequence name: its window} for the scenario's downturn events (review Z7), or {} when
    it has none. Read through `library.sequences` at call time (lazy import: `builder` imports
    this module, and a live server must see an edited data file)."""
    from .sequences import sequences

    downs = [e for e in scenario.get("events") or []
             if isinstance(e, dict) and e.get("kind") == "downturn"]
    if not downs:
        return {}
    known = sequences()
    out = {}
    for event in downs:
        name = str(event.get("sequence"))
        out[name] = [list(row) for row in known.get(name, {}).get("window", [])]
    return out


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
    """Check a scenario against its schema version (1: hand rows; 2: + events; 3: + rates table)."""
    if not isinstance(scenario, dict):
        raise ScenarioError(f"scenario must be a dict, got {type(scenario).__name__}")
    version = scenario.get("schema_version")
    if version not in (1, 2, SCHEMA_VERSION):
        raise ScenarioError(
            f"schema_version {version!r} cannot be read (this build handles 1-{SCHEMA_VERSION}); "
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
    _check_rates_table(scenario, case)
    plan_year = scenario.get("plan_year")
    if plan_year is not None and not isinstance(plan_year, int):
        raise ScenarioError(f"plan_year must be an int, got {plan_year!r}")
    if version >= 2:
        events = scenario.get("events", [])
        if not isinstance(events, list):
            raise ScenarioError("scenario.events must be a list of events")
        from . import builder  # lazy: builder imports this module

        builder.validate_events(events, list((case.get("basic_info") or {}).get("names") or []))
    return scenario


def _check_rates_table(scenario: dict, case: dict) -> None:
    """The optional `rates_table` (step 5b): its shape, and the two ways it can contradict the
    case dictionary (the generated `Case.toml` must name the table it is written with)."""
    table = scenario.get("rates_table")
    method = (case.get("rates_selection") or {}).get("method")
    if table is None:
        if method == "table":
            raise ScenarioError(
                "the case names a rate table (rates_selection.method = 'table') but the scenario "
                "holds none: import the CSV beside the case file"
            )
        return
    if not isinstance(table, dict) or not isinstance(table.get("columns"), list) \
            or not isinstance(table.get("rows"), list):
        raise ScenarioError("scenario.rates_table must be {'columns': [...], 'rows': [[...]]}")
    width = len(table["columns"])
    for i, row in enumerate(table["rows"]):
        if not isinstance(row, list) or len(row) != width:
            raise ScenarioError(f"rates_table row {i}: expected {width} values")
        for value in row:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ScenarioError(f"rates_table row {i}: not a number: {value!r}")
    if method != "table":
        raise ScenarioError(
            f"the scenario holds a rate table but the case's rates_selection.method is {method!r}: "
            "a table run's case must name method = 'table'"
        )


def migrate(scenario: dict) -> dict:
    """Bring a scenario up to SCHEMA_VERSION and return it (a copy; the input is untouched).

    Version 1 (hand rows) and version 2 (events) become version 3 with what they had: every
    row stays a hand row, and an old scenario may hold no rates table (step 5b).
    """
    version = scenario.get("schema_version")
    if version == SCHEMA_VERSION:
        out = dict(scenario)
        out.setdefault("events", [])
        return out
    if version in (1, 2):
        out = ({k: v for k, v in scenario.items() if k not in ("events", "provenance")}
               if version == 1 else dict(scenario))
        out["schema_version"] = SCHEMA_VERSION
        out.setdefault("events", [])
        return out
    raise ScenarioError(f"no migration from schema_version {version!r}")


def _short(value: Any, limit: int = 40) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


# The case fields a person meets, in words (UX review Q9); any other path is shown as is.
PATH_LABELS = {
    "case.basic_info.names": "names",
    "case.basic_info.date_of_birth": "dates of birth",
    "case.basic_info.life_expectancy": "life expectancy",
    "case.basic_info.start_date": "plan start",
    "case.basic_info.state": "state",
    "case.basic_info.locality": "locality",
    "case.basic_info.school_district": "school district",
    "case.basic_info.moves": "moves",
    "case.savings_assets.taxable_savings_balances": "taxable savings balances",
    "case.savings_assets.tax_deferred_savings_balances": "tax-deferred savings balances",
    "case.savings_assets.tax_free_savings_balances": "tax-free (Roth) savings balances",
    "case.savings_assets.hsa_savings_balances": "HSA balances",
    "case.savings_assets.taxable_cost_basis": "taxable cost basis",
    "case.fixed_income.social_security_pia_amounts": "Social Security PIAs",
    "case.fixed_income.social_security_ages": "Social Security claiming ages",
    "case.fixed_income.pension_monthly_amounts": "pensions (monthly)",
    "case.fixed_income.pension_ages": "pension ages",
    "case.optimization_parameters.objective": "objective",
    "case.optimization_parameters.spending_profile": "spending profile",
    "case.optimization_parameters.surviving_spouse_spending_percent": "survivor's spending (%)",
    "case.optimization_parameters.other_medical_expenses": "other medical expenses",
    "case.aca_settings.slcsp_annual": "marketplace benchmark premium",
    "case.aca_settings.aca_start_year": "marketplace coverage starts",
    "case.rates_selection.method": "rates method",
    "case.rates_selection.heirs_rate_on_tax_deferred_estate": "heirs' tax rate on tax-deferred savings",
    "case.rates_selection.obbba_expiration_year": "federal tax law reverts in",
    "case.solver_options.maxRothConversion": "Roth conversion cap",
    "case.solver_options.noRothConversions": "no Roth conversions for",
    "case.solver_options.startRothConversions": "Roth conversions start",
    "case.solver_options.stopRothConversions": "Roth conversions stop",
    "case.solver_options.netSpending": "net spending",
    "case.solver_options.bequest": "bequest target",
    "case.solver_options.withSSAges": "claiming ages searched",
    "case.solver_options.withMedicare": "Medicare premiums",
    "case.solver_options.withACA": "marketplace premiums",
    "case.solver_options.breakpointMethod": "solution method",
    "case.solver_options.timePreference": "time preference",
    "case.solver_options.noLateSurplus": "no cash-flow surplus in the last two years",
    "case.solver_options.spendingSlack": "spending profile slack",
    "case.solver_options.withItemized": "itemized deductions",
    "case.solver_options.withSTAR": "NY STAR credit",
}

# Case fields whose value at the model's own default is the same as no value (UX review Q9):
# the case pages write them when saving (Goals initializes `timePreference` to 0.0, Run
# Options `noLateSurplus` to False), so a save that adds or drops one changes nothing the
# solve reads. Each default is the one Plan.solve reads with (`plan.py`: noLateSurplus False,
# timePreference 0.0, spendingSlack 0). The inputs hash still sees the key: this is the
# summary's reading only.
NO_OP_DEFAULTS = {
    "case.solver_options.noLateSurplus": False,
    "case.solver_options.timePreference": 0.0,
    "case.solver_options.spendingSlack": 0,
}


def _is_no_op(path: str, value: Any) -> bool:
    if path not in NO_OP_DEFAULTS:
        return False
    default = NO_OP_DEFAULTS[path]
    if isinstance(default, bool) or isinstance(value, bool):
        return value is default
    try:
        return float(value) == float(default)
    except (TypeError, ValueError):
        return False


def _path_words(path: str) -> str:
    """A path in words where `PATH_LABELS` names it; a list index stays ("life expectancy[1]")."""
    base = path.split("[", 1)[0]
    return PATH_LABELS[base] + path[len(base):] if base in PATH_LABELS else path


def diff_summaries(old: Any, new: Any, prefix: str = "", limit: int = 20) -> list[str]:
    """A field-by-field diff of two scenarios in words (design section 7).

    Events are worded per event ("purchase: ... 2029 ... -> ... 2031 ...") and matched by id;
    hand rows are diffed structurally. Case fields a person meets are named in words
    (`PATH_LABELS`), the raw path otherwise; a field added or removed at the model's own
    default is not a change (`NO_OP_DEFAULTS`). At most `limit` lines; the last line counts
    the rest.
    """
    changes: list[str] = []
    if isinstance(old, dict) and isinstance(new, dict):
        _events_into(old, new, changes)
        old = {k: v for k, v in old.items() if k not in ("events", "provenance")}
        new = {k: v for k, v in new.items() if k not in ("events", "provenance")}
    _diff_into(old, new, prefix, changes)
    if len(changes) > limit:
        rest = len(changes) - limit
        changes = changes[:limit] + [f"... and {rest} more change(s)"]
    return changes


def _events_into(old: dict, new: dict, out: list[str]) -> None:
    """The events diff, worded per event (section 7), matched by id."""
    old_events = {e.get("id"): e for e in old.get("events") or [] if isinstance(e, dict)}
    new_events = {e.get("id"): e for e in new.get("events") or [] if isinstance(e, dict)}
    for eid in sorted(set(old_events) | set(new_events)):
        before, after = old_events.get(eid), new_events.get(eid)
        if before is None:
            out.append(f"{after.get('kind', 'event')}: {_event_words(after)} (added)")
        elif after is None:
            out.append(f"{before.get('kind', 'event')}: {_event_words(before)} (removed)")
        elif canonical_json(before) != canonical_json(after):
            words = (_event_words(before), _event_words(after))
            line = f"{before.get('kind', 'event')}: {words[0]} -> {words[1]}"
            if words[0] == words[1]:
                # The words do not show this change (a closing cost, a district, ...): name the
                # fields that moved (review X4).
                fields: list[str] = []
                _diff_into(before, after, "", fields)
                line += " (" + "; ".join(fields) + ")"
            out.append(line)


def _event_words(event: dict) -> str:
    """One event in words ("buy in Yonkers (10701) in 2027, cash")."""
    kind = event.get("kind")
    if kind == "work":
        level = "full time" if event.get("level", "full") == "full" else "part time"
        pay = f", wages {event['wages']}" if event.get("wages") is not None else ""
        return f"{event.get('person')} {level} {event.get('start')}-{event.get('end')}{pay}"
    if kind == "claim":
        age = event.get("age")
        return (f"{event.get('person')} claims at {age}" if age is not None
                else f"{event.get('person')}: let Owl choose")
    if kind == "death":
        return f"{event.get('person')} dies at {event.get('age')}"
    if kind == "rent":
        end = f" to {_ref_words(event['end'])}" if "end" in event else ""
        return (f"{event.get('monthly')}/mo from {_ref_words(event.get('start'))}, "
                f"flat through {_ref_words(event.get('flat_until'))}{end}")
    if kind == "purchase":
        financing = event.get("financing") or {"kind": "cash"}
        how = ("cash" if financing.get("kind") != "loan"
               else f"{financing.get('term')}-year loan at {financing.get('rate')}%")
        price = f" at {event['price']} (today's $)" if event.get("price") is not None else ""
        sale = f", sold {_ref_words(event['sale'])}" if "sale" in event else ""
        return f"{event.get('name')}{price} in {_ref_words(event.get('year'))}, {how}{sale}"
    if kind == "care":
        end = f" to {_ref_words(event['end'])}" if "end" in event else ""
        return f"{event.get('amount')}/yr from {_ref_words(event.get('year'))}{end}"
    return repr(event)


def _ref_words(ref: Any) -> str:
    """A year field in words: a calendar year or its anchor ("the year after Noa's work")."""
    if isinstance(ref, int) and not isinstance(ref, bool):
        return str(ref)
    if isinstance(ref, dict):
        if "year" in ref:
            return str(ref["year"])
        anchor = ref.get("anchor")
        if anchor == "age":
            return f"{ref.get('person')} at {ref.get('age')}"
        if anchor == "work_end":
            which = "the year after" if ref.get("after") else "the last year of"
            return f"{which} {ref.get('person')}'s work"
        if anchor == "purchase":
            return "the purchase year"
        if anchor == "event":
            offset = ref.get("offset") or 0
            return f"{ref.get('id')}" + (f" +{offset}" if offset else "")
    return repr(ref)


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
                if not _is_no_op(path, new[key]):
                    out.append(f"{_path_words(path)}: added ({_short(new[key])})")
            elif key not in new:
                if not _is_no_op(path, old[key]):
                    out.append(f"{_path_words(path)}: removed (was {_short(old[key])})")
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
    if _is_no_op(label, old) and _is_no_op(label, new):
        return  # 0 -> 0.0 at the default: the solve reads the same
    out.append(f"{_path_words(label)}: {_short(old)} -> {_short(new)}")

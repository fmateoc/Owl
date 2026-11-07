"""Scenario model and builder: events to Owl's case dictionary and HFP tables (step 4).

Design `fork-notes/run-library-design.md` sections 6.1-6.3, build step 4 and D6/I1. A scenario
carries **events** (work, claiming, rent, a home purchase, care) beside its hand rows (`case`,
`hfp`: rows the user entered or imported). `build()` turns the events into the coupled edits of
section 6.2 in one place:

- the place gives the state, locality, school district and a move in the purchase year;
- the purchase gives a Fixed Assets row in purchase-year dollars (grown by the case's own
  inflation path, as `make_cases.py` does), a Debts row linked to it by name, the big-ticket
  outflow, the owner's Budget lines from that year, and rent lines ending the year before;
- the last work year gives the marketplace start year, `months worked`, and the wages and
  contributions in the person sheets;
- the claiming events give `social_security_ages` and the `withSSAges` switch;
- the death events give `basic_info.life_expectancy` (I2's longevity variants: "first death at
  75, 80, 85, each spouse in turn", one horizon per person; Owl already models the death
  mechanics).

`build(scenario) -> (case, hfp, provenance)` is deterministic and has no side effects; a case
whose rate model draws a new inflation path at every build (a stochastic method without a fixed
seed) is refused where an event needs that path (review X3). The row
builders (`budget_row`, `rent_rows`, `owner_rows`) are shared with
`fork-notes/synthetic/make_cases.py`, and `check_library_builder.py` checks the builder's
placement against that script's 39 workbooks cell for cell.

Provenance (section 6.3, markers first per S11): every generated row and cell records which
event produced it -- Budget, Debts and Fixed Assets rows by their `name`, person-sheet cells by
event and year, case fields by path. A generated row is regenerated wholesale when the events
change; hand rows are untouched. Per-cell overrides on generated values ("closing costs 2029:
24,000 instead of 21,700") are the next increment of section 6.3 and are not built yet: an edit
to a generated value does not survive a regeneration.

Anchors (I1): the year fields of the rent, purchase and care events (work spans take plain
calendar years) may name a calendar year or anchor to another event -- "the year after Noa's
last work year" (`{"anchor": "work_end", "person": "Noa", "after": true}`), "at age 86"
(`{"anchor": "age", "person": "Ari", "age": 86}`), "the purchase year" (`{"anchor":
"purchase"}`), or another event's year (`{"anchor": "event", "id": "care"}`: its year field,
or a work span's end / a rent's start where it has none). The rent end and the owner lines
follow from the purchase by construction (section 6.2).
"""

from __future__ import annotations

import copy
import io
import math
from typing import Any

from .scenario import ScenarioError

# The person-sheet columns (upstream's order, hfp_io._timeHorizonItems). The house tables follow
# hfp_io's own lists; Budget is budget.SHEET_COLUMNS (the 14-column format gen_hfp_us's writer
# predates, make_cases.py rewrites it in).
PERSON_COLUMNS = (
    "year",
    "anticipated wages",
    "months worked",
    "other inc",
    "net inv",
    "taxable ctrb",
    "401k ctrb",
    "employer ctrb",
    "Roth 401k ctrb",
    "IRA ctrb",
    "Roth IRA ctrb",
    "HSA ctrb",
    "Roth conv",
    "Roth conv fixed",
    "QCD",
    "big-ticket items",
)
DEBT_COLUMNS = ("active", "name", "type", "year", "term", "amount", "rate", "property")
ASSET_COLUMNS = ("active", "name", "type", "year", "basis", "value", "rate", "yod", "commission")
BUDGET_COLUMNS = (
    "active",
    "name",
    "type",
    "year",
    "end",
    "amount",
    "rate",
    "survivor",
    "essential",
    "clock",
    "start_age",
    "end_age",
    "index",
    "kind",
)
HOUSE_TABLES = ("Debts", "Fixed Assets", "Budget")

# The run's rates table file (design section 5): the case names it (`rates_selection.rates_file`)
# and `casefiles.export_case` writes it beside Case.toml.
RATES_CSV = "rates.csv"

EVENT_KINDS = ("work", "claim", "rent", "purchase", "care", "downturn", "death")

# Plain event fields to person-sheet columns (the rest of the sheet stays hand cells).
PAY_COLUMNS = {
    "wages": "anticipated wages",
    "k401k": "401k ctrb",
    "employer": "employer ctrb",
    "ira": "IRA ctrb",
    "months_worked": "months worked",
}

# The builder's defaults for a purchase's optional fields: one place, read by build(), by the
# canonical form (a key at its default is dropped, casefiles._canonical_events) and by the
# Scenario page's widgets (review X4: the page had its own, larger closing-cost defaults).
FINANCING_DEFAULTS = {
    "cash": {"closing": 0.0},
    "loan": {"down": 0.20, "closing": 0.0, "extra": 0.0},
}
PLACE_DEFAULTS = {"state": "NY", "locality": "", "school_district": "", "move": False}
# A place's text field that states "none" (no local income tax, no STAR district): the
# variants tables' spelling (`ui/variant_tables.CLEAR`). A blank district on a purchase
# without a move keeps the case's own district (UX review B2: blank used to wipe it).
NO_PLACE = "-"


def place_text(value) -> str:
    """A place's locality or district as the case stores it ("-" stated as none)."""
    text = "" if value is None else str(value).strip()
    return "" if text == NO_PLACE else text


# "That event's year" for an `event:` anchor, by the target's kind (review X6): a work span's
# end, a rent's start, a purchase's or care span's year, a downturn's placement. A claim or a
# death has no year.
EVENT_YEAR_FIELD = {"work": "end", "rent": "start", "purchase": "year", "care": "year", "downturn": "start"}

# A death age (I2's longevity dimension): whole years of age at death, at least 1 and at most
# what Owl's own tables handle (`tax_federal`: "Unsupported life expectancy over 120 years").
DEATH_AGE_MAX = 120


# ---------------------------------------------------------------------------
# Budget, Debts and Fixed Assets rows (shared with make_cases.py)
# ---------------------------------------------------------------------------


def budget_row(name, typ, year, end, amount, rate=0.0, survivor=None, essential=False, **age):
    """One Budget sheet row (the 14 columns of budget.SHEET_COLUMNS)."""
    row = {
        "active": True,
        "name": name,
        "type": typ,
        "year": year,
        "end": end,
        "amount": amount,
        "rate": rate,
        "survivor": survivor,
        "essential": essential,
        "clock": None,
        "start_age": None,
        "end_age": None,
        "index": None,
        "kind": None,
    }
    row.update(age)
    return [row[c] for c in BUDGET_COLUMNS]


def rent_rows(annual, start, flat_until, end, gamma, base):
    """Rent rows: `annual` in today's dollars from `start`, nominal-flat through `flat_until`,
    then growing with inflation (real growth 0), to `end` (0: the plan end).

    The flat years are one-year rows (a flat nominal amount declines in real terms, which one
    constant-rate row cannot express); the tail row is named "rent from <flat_until>" as
    make_cases.py named it. `gamma[k]` is the case's price level at `base + k` relative to
    `base`, so a flat nominal amount in today's dollars is `annual * gamma[start-base] /
    gamma[year-base]` (make_cases.py: `round(RENT / gamma[1])` for a rent flat through 2027).
    """
    if flat_until <= start:
        return [] if (end and end < start) else [budget_row("rent", "rent", start, end, annual, essential=True)]
    rows = []
    for year in range(start, flat_until):
        if end and year > end:
            return rows
        amount = annual if year == start else round(annual * float(gamma[start - base]) / float(gamma[year - base]))
        rows.append(budget_row("rent" if year == start else f"rent in {year}", "rent", year, year,
                               amount, essential=True))
    if not end or flat_until <= end:
        amount = round(annual * float(gamma[start - base]) / float(gamma[flat_until - base]))
        rows.append(budget_row(f"rent from {flat_until}", "rent", flat_until, end, amount, essential=True))
    return rows


def owner_rows(property_tax, hoa, insurance, first_year, last_year=0):
    """The owner's Budget rows from the purchase year (`last_year` 0: the plan end)."""
    return [
        budget_row("property tax", "property tax", first_year, last_year, property_tax, rate=1.0, essential=True),
        budget_row("HOA", "maintenance", first_year, last_year, hoa, essential=True),
        budget_row("condo insurance", "insurance", first_year, last_year, insurance, essential=True),
    ]


def care_row(amount, year, end=0, name="care", essential=True):
    return [budget_row(name, "care", year, end, amount, essential=essential)]


def asset_row(name, year, value, rate, yod, commission, typ="residence", basis=None):
    """One Fixed Assets row: value and basis in the purchase year's dollars."""
    return [True, name, typ, year, value if basis is None else basis, value, rate, yod or 0, commission]


def debt_row(name, year, term, amount, rate, property_name, typ="mortgage"):
    """One Debts row; `property` is the residence whose sale pays the loan off."""
    return [True, name, typ, year, term, amount, rate, property_name]


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def _year_ref(value, where: str) -> dict:
    """A year field normalized to {"year": n} or {"anchor": ...} (a bare int is a year)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return {"year": int(value)}
    if not isinstance(value, dict):
        raise ScenarioError(f"{where}: a year must be a calendar year or an anchor, got {value!r}")
    if "year" in value:
        if not isinstance(value["year"], int) or isinstance(value["year"], bool):
            raise ScenarioError(f"{where}.year must be a calendar year, got {value['year']!r}")
        return {"year": int(value["year"])}
    anchor = value.get("anchor")
    if anchor == "age":
        if not isinstance(value.get("person"), str) or not isinstance(value.get("age"), (int, float)) \
                or isinstance(value.get("age"), bool):
            raise ScenarioError(f"{where}: an age anchor needs 'person' and 'age'")
        if float(value["age"]) != int(value["age"]):
            raise ScenarioError(f"{where}: an age anchor takes whole years (got {value['age']!r})")
        return {"anchor": "age", "person": value["person"], "age": int(value["age"])}
    if anchor == "work_end":
        if not isinstance(value.get("person"), str):
            raise ScenarioError(f"{where}: a work_end anchor needs 'person'")
        return {"anchor": "work_end", "person": value["person"], "after": bool(value.get("after", False))}
    if anchor == "purchase":
        return {"anchor": "purchase"}
    if anchor == "event":
        if not isinstance(value.get("id"), str):
            raise ScenarioError(f"{where}: an event anchor needs 'id'")
        offset = value.get("offset", 0)
        if not isinstance(offset, int) or isinstance(offset, bool):
            raise ScenarioError(f"{where}: the event anchor's offset must be an integer")
        return {"anchor": "event", "id": value["id"], "offset": offset}
    raise ScenarioError(f"{where}: unknown year anchor {anchor!r}")


def _finite_number(value: Any) -> bool:
    """A real number: not a bool, not None, not NaN or infinite (review AD1)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _year_fields(event: dict) -> list[str]:
    """The names of the event's year fields."""
    kind = event["kind"]
    if kind == "work":
        return ["start", "end"]
    if kind == "rent":
        return ["start", "flat_until"] + (["end"] if "end" in event else [])
    if kind == "purchase":
        return ["year"] + (["sale"] if "sale" in event else [])
    if kind == "care":
        return ["year"] + (["end"] if "end" in event else [])
    if kind == "downturn":
        return ["start"]
    return []


# The editable text form of a year field (the scenario editor's inputs): a calendar year,
# "age:<person>:<age>", "work:<person>" (their last work year), "after:<person>" (the year
# after it), "purchase" (the home purchase's year), or "event:<id>" with an optional "+<n>" /
# "-<n>" (that event's year, shifted).
def year_ref_text(ref) -> str:
    """A year field as editable text (the inverse of `parse_year_ref`)."""
    if isinstance(ref, int) and not isinstance(ref, bool):
        return str(ref)
    if not isinstance(ref, dict):
        return repr(ref)
    if "year" in ref:
        return str(ref["year"])
    anchor = ref.get("anchor")
    if anchor == "age":
        return f"age:{ref.get('person')}:{ref.get('age'):g}"
    if anchor == "work_end":
        return ("after:" if ref.get("after") else "work:") + str(ref.get("person"))
    if anchor == "purchase":
        return "purchase"
    if anchor == "event":
        offset = int(ref.get("offset") or 0)
        return f"event:{ref.get('id')}" + (f"{offset:+d}" if offset else "")
    return repr(ref)


def parse_year_ref(text, where="year", ids=None) -> dict:
    """A year field from its editable text form (ScenarioError with the grammar on bad text).

    `ids` (the scenario's event ids, when known) settles `event:<id>-<n>` against an id that
    itself ends in `-<digits>`, as the synthetic suite's `work-ari-2026` does (review X5): a
    known id wins, else the trailing `+<n>` / `-<n>` is the offset.
    """
    grammar = ("a calendar year, 'age:<person>:<age>', 'work:<person>', 'after:<person>', "
               "'purchase', or 'event:<id>' (with '+<n>' / '-<n>')")
    if not isinstance(text, str):
        raise ScenarioError(f"{where}: expected the text form of a year ({grammar})")
    value = text.strip()
    if value.lstrip("-").isdigit():
        return {"year": int(value)}
    if value.startswith("age:"):
        parts = value.split(":")
        if len(parts) == 3:
            try:
                return {"anchor": "age", "person": parts[1], "age": float(parts[2])}
            except ValueError:
                pass
    elif value.startswith("work:") and len(value) > len("work:"):
        return {"anchor": "work_end", "person": value[len("work:"):], "after": False}
    elif value.startswith("after:") and len(value) > len("after:"):
        return {"anchor": "work_end", "person": value[len("after:"):], "after": True}
    elif value == "purchase":
        return {"anchor": "purchase"}
    elif value.startswith("event:"):
        body = value[len("event:"):]
        known = set(ids or ())
        if body and body in known:
            return {"anchor": "event", "id": body, "offset": 0}
        at = max(body.rfind("+"), body.rfind("-"))
        if at > 0 and body[at + 1:].isdigit() and (not known or body[:at] in known):
            return {"anchor": "event", "id": body[:at], "offset": int(body[at:])}
        if body:
            return {"anchor": "event", "id": body, "offset": 0}
    raise ScenarioError(f"{where}: {text!r} is not a year ({grammar})")


def validate_events(events: Any, names: list[str]) -> list[dict]:
    """Check a scenario's events and return them normalized (year fields as refs)."""
    if events is None:
        return []
    if not isinstance(events, list):
        raise ScenarioError("scenario.events must be a list of events")
    seen: set[str] = set()
    death_persons: set[str] = set()
    out: list[dict] = []
    for i, event in enumerate(events):
        where = f"events[{i}]"
        if not isinstance(event, dict):
            raise ScenarioError(f"{where} must be a dict")
        kind = event.get("kind")
        if kind not in EVENT_KINDS:
            raise ScenarioError(f"{where}.kind must be one of {list(EVENT_KINDS)}, got {kind!r}")
        eid = event.get("id")
        if not isinstance(eid, str) or not eid:
            raise ScenarioError(f"{where}.id must be a non-empty string (the provenance marker)")
        if eid in seen:
            raise ScenarioError(f"{where}.id {eid!r} is used twice")
        seen.add(eid)
        event = dict(event)
        if kind in ("work", "claim", "death"):
            person = event.get("person")
            if person not in names:
                raise ScenarioError(f"{where}.person {person!r} is not one of the case's people {names}")
        if kind == "work":
            for field in ("start", "end"):
                value = event.get(field)
                if not isinstance(value, int) or isinstance(value, bool):
                    raise ScenarioError(f"{where}.{field} must be a calendar year")
            if event["end"] < event["start"]:
                raise ScenarioError(f"{where}: ends before it starts")
            level = event.get("level", "full")
            if level not in ("full", "part"):
                raise ScenarioError(f"{where}.level must be 'full' or 'part', got {level!r}")
            for field in PAY_COLUMNS:
                if field in event and field != "months_worked":
                    value = event[field]
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        raise ScenarioError(f"{where}.{field} must be a number")
            months = event.get("months_worked")
            if months is not None and (not isinstance(months, int) or not 0 <= months <= 12):
                raise ScenarioError(f"{where}.months_worked must be 0-12")
        elif kind == "claim":
            if "age" not in event:
                raise ScenarioError(f"{where}: 'age' is required (None lets Owl choose)")
            age = event["age"]
            if age is not None and (not isinstance(age, (int, float)) or isinstance(age, bool) or age <= 0):
                raise ScenarioError(f"{where}.age must be a positive number or None (let Owl choose)")
        elif kind == "death":
            age = event.get("age")
            if not isinstance(age, (int, float)) or isinstance(age, bool) \
                    or not 1 <= float(age) <= DEATH_AGE_MAX or float(age) != int(age):
                raise ScenarioError(
                    f"{where}.age must be a whole number of years 1-{DEATH_AGE_MAX}, got {age!r}")
            if event["person"] in death_persons:
                raise ScenarioError(
                    f"{where}: {event['person']!r} already has a death event (one per person)")
            death_persons.add(event["person"])
        elif kind == "rent":
            monthly = event.get("monthly")
            if not isinstance(monthly, (int, float)) or isinstance(monthly, bool) or monthly <= 0:
                raise ScenarioError(f"{where}.monthly must be a positive number")
        elif kind == "purchase":
            price = event.get("price")
            if not _finite_number(price) or price <= 0:
                raise ScenarioError(f"{where}.price must be a positive number (today's dollars)")
            if not isinstance(event.get("name"), str) or not event["name"]:
                raise ScenarioError(f"{where}.name must name the home (rows are marked by name)")
            pay_on = event.get("pay_on")
            if pay_on is not None and pay_on not in names:
                raise ScenarioError(f"{where}.pay_on {pay_on!r} is not one of the case's people {names}")
            financing = event.get("financing")
            if not isinstance(financing, dict) or financing.get("kind") not in ("cash", "loan"):
                raise ScenarioError(f"{where}.financing must be 'cash' or a loan")
            if financing.get("kind") == "loan":
                for field in ("term", "rate"):
                    if field not in financing:
                        raise ScenarioError(f"{where}.financing needs {field!r} for a loan")
            # A number the builder computes with must be one (review AD1): a NaN from an editor
            # cell is stored as None by `normalize`, and a None cost became a $0 Budget line
            # while a None loan term failed in `build` with a bare ValueError.
            for field in ("term", "rate", "down", "closing", "extra"):
                if field in financing and not _finite_number(financing[field]):
                    raise ScenarioError(f"{where}.financing.{field} must be a number, got {financing[field]!r}")
            costs = event.get("costs")
            if costs is not None:
                if not isinstance(costs, dict):
                    raise ScenarioError(f"{where}.costs must be a dict of yearly amounts")
                for field, value in costs.items():
                    if not _finite_number(value) or value < 0:
                        raise ScenarioError(
                            f"{where}.costs.{field} must be a yearly amount of 0 or more (today's dollars), "
                            f"got {value!r}")
        elif kind == "care":
            amount = event.get("amount")
            if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
                raise ScenarioError(f"{where}.amount must be a positive number (today's dollars)")
        elif kind == "downturn":
            from .sequences import SequenceError, sequences  # lazy: reads the data file

            sequence = event.get("sequence")
            try:
                known = sequences()
            except SequenceError as e:
                raise ScenarioError(str(e)) from e
            if sequence not in known:
                raise ScenarioError(f"{where}.sequence {sequence!r} is not one of {sorted(known)}")
        if kind != "work":  # work takes plain calendar years (checked above), the rest anchors
            for field in _year_fields(event):
                if field not in event:
                    raise ScenarioError(f"{where}.{field} is required")
                event[field] = _year_ref(event[field], f"{where}.{field}")
        out.append(event)
    # An `event:` anchor must name an event that has a year (review X6: a claim has none, and
    # an anchor to one used to raise a raw TypeError).
    kinds = {e["id"]: e["kind"] for e in out}
    for i, event in enumerate(out):
        for field in _year_fields(event) if event["kind"] != "work" else ():
            ref = event[field]
            if ref.get("anchor") != "event":
                continue
            target = kinds.get(ref["id"])
            if target is None:
                raise ScenarioError(f"events[{i}].{field}: no event has the id {ref['id']!r}")
            if target not in EVENT_YEAR_FIELD:
                raise ScenarioError(
                    f"events[{i}].{field}: {ref['id']!r} is a {target} event, which has no year to anchor to"
                )
    # One home purchase, one rent and one care span for now (design D6: "moves without a
    # purchase, sale and re-buy later" is a later increment; their rows carry fixed names), and
    # one downturn sequence (step 5b: the variant dimension of I11 comes with step 6).
    for kind in ("purchase", "rent", "care", "downturn"):
        if sum(1 for e in out if e["kind"] == kind) > 1:
            raise ScenarioError(f"at most one {kind} event per scenario (a sale and re-buy later)")
    return out


def check_death_age(person: str, age, case: dict, scenario: dict, where: str = "death") -> None:
    """A death age against the person's age at the plan start (I2): a death in the past would
    give the plan a horizon of zero years (or fewer) for that person."""
    info = case.get("basic_info") or {}
    names = list(info.get("names") or [])
    births = [int(str(d)[:4]) for d in info.get("date_of_birth") or []]
    start = _plan_start(case, scenario)
    try:
        birth = births[names.index(person)]
    except (ValueError, IndexError):
        raise ScenarioError(
            f"{where}: no date of birth for {person!r}: its death age cannot be placed"
        ) from None
    if int(age) < start - birth:
        raise ScenarioError(
            f"{where}: {person!r} is {start - birth} in {start} and would die at "
            f"{int(age)}: a death before the plan starts"
        )


def plan_window(scenario: dict, person: str = None, age=None) -> tuple:
    """(first plan year, last plan year) of a scenario: the start year and the last life
    horizon, with the scenario's death events applied (and `person` dying at `age`, a death
    not in the events yet). The last year is None when no date of birth is known.
    """
    case = scenario.get("case") or {}
    info = case.get("basic_info") or {}
    names = list(info.get("names") or [])
    births = [int(str(d)[:4]) for d in info.get("date_of_birth") or []]
    start = _plan_start(case, scenario)
    from owlplanner.config.defaults import DEFAULT_LIFE_EXPECTANCY

    life = [int(expect) for expect in info.get("life_expectancy") or []]
    life += [DEFAULT_LIFE_EXPECTANCY] * (len(names) - len(life))
    for event in scenario.get("events") or []:
        if isinstance(event, dict) and event.get("kind") == "death" \
                and event.get("person") in names and event.get("age") is not None:
            life[names.index(event["person"])] = int(event["age"])
    if person is not None and person in names:
        life[names.index(person)] = int(age)
    end_year = max((b + e for b, e in zip(births, life, strict=False)), default=None)
    return start, end_year


def check_death_window(scenario: dict, person: str = None, age=None, where: str = "") -> None:
    """The plan window the deaths leave (I2, U7's door check; review AE1).

    A death at the age one is now is fine for that person (one year of horizon), but
    `Plan` refuses to build a plan of one year ("Plan needs more than 1 years"), so the
    *last* death must leave the plan more than one year past its start. `person`/`age` is
    a death not in the events yet -- a variant value or a mover, checked at the door
    before it applies (the events' own deaths are applied here too, so a combination that
    collapses the window is refused where it is entered).
    """
    start, end_year = plan_window(scenario, person, age)
    if end_year is not None and end_year <= start:
        prefix = f"{where}: " if where else ""
        raise ScenarioError(
            f"{prefix}the plan would run {start}-{end_year}: not more than one year, and a "
            "plan needs more than one (the last life horizon is at the plan start)")


def check_death_after_work(scenario: dict, person: str = None, age=None, where: str = "") -> None:
    """No one works past their own death (review AI6).

    The plan's years are checked against the *last* life horizon, so a work year after the
    person's own death passed; Owl then dropped the wages after the horizon without a word,
    while the marketplace start the work events generate still followed the dead person's
    work (the widowed survivor paid no premium in the gap). A death year is the year of birth
    plus the age (the last year of the person's horizon). The scenario's own death events
    are checked, with `person` dying at `age` in their place when given (a variant value or
    a mover, checked at the door before it applies)."""
    case = scenario.get("case") or {}
    info = case.get("basic_info") or {}
    names = list(info.get("names") or [])
    births = {}
    for name, dob in zip(names, info.get("date_of_birth") or [], strict=False):
        try:
            births[name] = int(str(dob)[:4])
        except ValueError:
            continue
    deaths = {}
    for event in scenario.get("events") or []:
        if isinstance(event, dict) and event.get("kind") == "death" and event.get("age") is not None:
            deaths[event.get("person")] = (int(event["age"]), event.get("id"))
    if person is not None:
        deaths[person] = (int(age), None)
    prefix = f"{where}: " if where else ""
    for event in scenario.get("events") or []:
        if not (isinstance(event, dict) and event.get("kind") == "work"):
            continue
        who = event.get("person")
        if who not in deaths or who not in births:
            continue
        try:
            end = int(event.get("end"))
        except (TypeError, ValueError):
            continue
        died, did = deaths[who]
        if end > births[who] + died:
            name = f" ({did})" if did else ""
            raise ScenarioError(
                f"{prefix}{who!r} would die at {died}{name}, in {births[who] + died}, but works "
                f"to {end} ({event.get('id')}): end the work by the death year, or move the death"
            )


def resolve_years(events: list[dict], case: dict) -> dict[str, dict[str, int]]:
    """The calendar year of every event's year field (the I1 anchors resolved).

    Raises ScenarioError on an anchor that cannot be resolved: a missing person or event, or a
    cycle between events.
    """
    info = case.get("basic_info") or {}
    names = list(info.get("names") or [])
    birth_years: dict[str, int] = {}
    for name, dob in zip(names, info.get("date_of_birth") or [], strict=False):
        try:
            birth_years[name] = int(str(dob)[:4])
        except ValueError:
            raise ScenarioError(f"basic_info.date_of_birth for {name!r} is not a date: {dob!r}") from None
    work_ends: dict[str, int] = {}
    for event in events:
        if event["kind"] == "work":
            work_ends[event["person"]] = max(work_ends.get(event["person"], -10**9), int(event["end"]))

    resolved: dict[str, dict[str, int]] = {}
    purchase_year: list[int | None] = [None]
    kinds = {e["id"]: e["kind"] for e in events}

    def resolve(ref: dict) -> int | None:
        if "year" in ref:
            return int(ref["year"])
        anchor = ref["anchor"]
        if anchor == "age":
            return birth_years.get(ref["person"], 0) + int(ref["age"]) if ref["person"] in birth_years else None
        if anchor == "work_end":
            return work_ends[ref["person"]] + (1 if ref["after"] else 0) if ref["person"] in work_ends else None
        if anchor == "purchase":
            return purchase_year[0]
        if anchor == "event":
            other = resolved.get(ref["id"])
            if other is None:
                return None
            # "That event's year" by the target's kind (U3, X6): a work span's end, a rent's
            # start (even when the rent names its own end), a purchase's or care span's year.
            main = other.get(EVENT_YEAR_FIELD.get(kinds.get(ref["id"]), "year"))
            return None if main is None else main + ref["offset"]
        return None

    pending = {e["id"]: e for e in events}
    for _ in range(len(events) + 2):
        progress = False
        for eid, event in list(pending.items()):
            years = {}
            for field in _year_fields(event):
                if event["kind"] == "work":
                    years[field] = int(event[field])
                    continue
                value = resolve(event[field])
                if value is not None:
                    years[field] = value
            if len(years) == len(_year_fields(event)):
                resolved[eid] = years
                if event["kind"] == "purchase":
                    purchase_year[0] = years["year"]
                del pending[eid]
                progress = True
        if not pending:
            return resolved
        if not progress:
            break
    stuck = [
        f"{eid}.{field}"
        for eid, event in pending.items()
        for field in _year_fields(event)
    ]
    raise ScenarioError(
        "event years that cannot be resolved (a missing person or event, or a cycle): " + "; ".join(stuck)
    )


# ---------------------------------------------------------------------------
# build()
# ---------------------------------------------------------------------------


def _set_path(case: dict, path: str, value) -> None:
    keys = path.split(".")
    node = case
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def _throwaway_plan(case: dict, rates_rows=None):
    """A plan built from the case with no HFP and no solve; the logs go to a string.

    A stochastic rate model draws a new inflation path at every plan build unless the case
    fixes its seed: the purchase price and the rent's flat rows would then be a random draw,
    frozen into the run and unrelated to the path the solve draws (review X3), and a generated
    rates table would describe a market that the run does not use. So the case must fix its
    seed (`reproducible_rates` **and** `rate_seed`): `setReproducible(True, None)` mints a
    fresh time-based seed per plan build, so `reproducible_rates` alone is no seed at all and
    one export would freeze two different tables (review Z2). The check reads the case, which
    is what a run stores; the plan cannot tell a minted seed from a fixed one.
    `rates_rows` carries a rate table held in memory (method 'table' only; `config_to_plan`'s
    parameter).
    """
    import tempfile

    from owlplanner.config import config_to_plan

    plan = config_to_plan(copy.deepcopy(case), tempfile.gettempdir(), logstreams=[io.StringIO()],
                          loadHFP=False, rates_rows=rates_rows)
    model = getattr(plan, "rateModel", None)
    if model is not None and not getattr(model, "deterministic", False):
        selection = case.get("rates_selection") or {}
        if not selection.get("reproducible_rates") or selection.get("rate_seed") is None:
            method = selection.get("method")
            raise ScenarioError(
                f"the case's rates ({method!r}) draw a new inflation path at every build, so a purchase "
                "price or a rent in nominal dollars cannot be built from it: the case must fix its "
                "seed (rates_selection.reproducible_rates = true and rate_seed = <an integer>), or "
                "the rates must use a deterministic rate method"
            )
    return plan


def _gamma(case: dict, rates_rows=None) -> list[float]:
    """The case's own inflation path (gamma_n): the price level of each plan year relative to
    the plan's first year (gamma[0] == 1). Read through a plan build with no HFP and no solve;
    the logs go to a string (make_cases.py reads the same array for nominal amounts)."""
    plan = _throwaway_plan(case, rates_rows)
    gamma = [float(g) for g in plan.gamma_n]
    if gamma and gamma[0] != 1.0:
        raise ScenarioError(f"the case's inflation path does not start at 1: gamma[0] = {gamma[0]}")
    return gamma


def rates_table(scenario: dict, events=None) -> dict | None:
    """The run's rates table ({'columns': [...], 'rows': [[year, S&P 500, Bonds Baa, T-Notes,
    Inflation], ...]} in percent), or None when the run uses no table (step 5b, D11).

    The hand table (`scenario["rates_table"]`) when there is one. Otherwise generated from the
    scenario's downturn events (I11): the case's own rate path with each named sequence's window
    overlaid at its placement year, so the years outside the window keep the run's own rate
    method and the stress question is "the same plan, but the market does this". `events` is
    the validated events, when the caller already has them.
    """
    return _rates_table(scenario, events=events)


def _check_table_events(scenario: dict, downs: list[dict]) -> None:
    """The two ways a rates table contradicts a downturn event (the recorded decisions),
    enforced however the table reaches `build` (review AA3): the event generates the table,
    so a hand table and a downturn refuse to coexist ("drop one"), and a downturn over a
    `table` case has no baseline to overlay."""
    if not downs:
        return
    case = scenario.get("case") or {}
    if scenario.get("rates_table") is not None:
        raise ScenarioError(
            "the run has both a hand-entered rates table and a downturn event, and the event "
            "generates the table: drop one of them"
        )
    if (case.get("rates_selection") or {}).get("method") == "table":
        raise ScenarioError(
            "a downturn sequence overlays the case's own rate method, and this case reads a "
            "rates table (rates_selection.method = 'table'): edit the table itself instead"
        )


def _rates_table(scenario: dict, events=None) -> dict | None:
    """`rates_table`'s implementation (the name `build`'s `rates_table=` keyword shadows)."""
    case = scenario.get("case") or {}
    hand = scenario.get("rates_table")
    if events is None:
        events = validate_events(scenario.get("events"), list((case.get("basic_info") or {}).get("names") or []))
    downs = [e for e in events if e["kind"] == "downturn"]
    _check_table_events(scenario, downs)
    if not downs:
        if hand is None:
            return None
        return {"columns": list(hand["columns"]), "rows": [list(row) for row in hand["rows"]]}
    return _generated_rates(scenario, events, downs)


def plan_rates_table(scenario: dict) -> dict:
    """The run's rate path as a rates table, however the run names it (I9's rate movers).

    A hand table or a downturn overlay comes back as `rates_table` builds it; a run on its
    own rate method gets that method's path as rows (`_generated_rates` with no overlay --
    the plan's own method with its own window and seed, reversed or rolled already).
    """
    case = scenario.get("case") or {}
    events = validate_events(scenario.get("events"), list((case.get("basic_info") or {}).get("names") or []))
    table = _rates_table(scenario, events=events)
    if table is not None:
        return table
    return _generated_rates(scenario, events, [])


def _generated_rates(scenario: dict, events: list[dict], downs: list[dict]) -> dict:
    """The rates table the downturn events generate: the case's own rate path, overlaid.

    The path is read through a plan build (as `_gamma` reads the inflation path), so it is the
    run's own method with its own window and seed; the overlay replaces the window's years. A
    window that reaches past the plan's end is simply not used there (documented); a window
    that lands in no plan year, or that starts before the plan and would be cut, is refused --
    a placement outside the plan must not look applied (review Z4).
    """
    from owlplanner.rate_models.table import RATE_TABLE_COLUMNS
    from .sequences import sequences

    case = scenario.get("case") or {}
    _check_table_events(scenario, downs)
    plan = _throwaway_plan(case)
    rows = [
        [int(year)] + [round(100.0 * float(plan.tau_kn[k][n]), 4) for k in range(4)]
        for n, year in enumerate(plan.year_n)
    ]
    years = resolve_years(events, case)
    by_year = {row[0]: row for row in rows}
    first, last = min(by_year), max(by_year)
    known = sequences()
    for event in downs:
        window = known[event["sequence"]]["window"]
        start = years[event["id"]]["start"]
        if not any(start + i in by_year for i in range(len(window))):
            raise ScenarioError(
                f"{event['id']}: no year of the {event['sequence']!r} window "
                f"({start}-{start + len(window) - 1}) lands in the plan ({first}-{last}): "
                "the downturn would not be applied"
            )
        if start < first:
            raise ScenarioError(
                f"{event['id']}: the {event['sequence']!r} window starts at {start}, before the "
                f"plan ({first}-{last}), and would be cut: place it inside the plan"
            )
        for i, values in enumerate(window):
            row = by_year.get(start + i)
            if row is not None:  # a window reaching past the plan's end is simply not used
                row[1:5] = [round(float(v), 4) for v in values]
    return {"columns": list(RATE_TABLE_COLUMNS), "rows": rows}


# `build`'s `rates_table=` keyword: its "the caller did not pass one" value (None is a real
# value -- a run with no table; review Z2).
_TABLE_UNSET = object()


def build(scenario: dict, *, rates_table=_TABLE_UNSET) -> tuple[dict, dict, dict]:
    """(case, hfp tables, provenance) for a scenario: its hand rows plus what its events generate.

    Deterministic and without side effects (design section 6.2). With no events this is the
    hand document unchanged (the plan window is still checked: a plan needs more than one
    year). `hfp` maps a sheet name to {"columns": [...], "rows": [[...]]};
    the provenance marks every generated row, cell and case field with the id of the event
    that produced it (section 6.3).

    `rates_table` is the run's rates table when the caller has computed it already
    (`export_case` computes the table once and passes it in, so one export builds and writes
    one and the same table, review Z2); by default it is computed here. Whatever the caller
    passes, the consistency rules between the table and the events are enforced here (review
    AA3): a hand table and a downturn refuse to coexist, a downturn over a `table` case is
    refused, and a downturn run must have a table (`rates_table=None` is refused).
    """
    hand_case = copy.deepcopy(scenario.get("case") or {})
    hand_hfp = copy.deepcopy(scenario.get("hfp") or {})
    events = validate_events(scenario.get("events"), list((hand_case.get("basic_info") or {}).get("names") or []))
    provenance: dict[str, Any] = {"case_fields": {}, "rows": {}, "cells": []}
    # The run's rates table (step 5b): hand rows, or generated by the downturn events (I11).
    # Either way the generated case names it (rates_selection.method 'table' and the file name),
    # marked with the event when one generates it, so a pages save keeps the hand case's values.
    table = _rates_table(scenario, events=events) if rates_table is _TABLE_UNSET else rates_table
    downs = [e for e in events if e["kind"] == "downturn"]
    _check_table_events(scenario, downs)  # however the table arrived (review AA3)
    if downs and table is None:
        raise ScenarioError(
            "the run's downturn event generates its rates table, so there must be one: call "
            "build() with no rates_table= (it is computed here) or pass builder.rates_table(scenario)"
        )
    if table is not None:
        _set_path(hand_case, "rates_selection.method", "table")
        _set_path(hand_case, "rates_selection.rates_file", RATES_CSV)
        if downs:
            generated = ["rates_selection.method", "rates_selection.rates_file"]
            # The generated table is the hand case's rate path as the plan uses it, reversed or
            # rolled already (`Plan.setRates` transforms every non-constant model, `table`
            # included): the frozen case must not transform it again, or the window leaves its
            # placement and every other year leaves the parent's path (review AB1). The keys
            # are reset only where the hand case sets them, so other runs' cases are unchanged.
            selection = hand_case.get("rates_selection") or {}
            if selection.get("reverse_sequence"):
                selection["reverse_sequence"] = False
                generated.append("rates_selection.reverse_sequence")
            if int(selection.get("roll_sequence") or 0) != 0:
                selection["roll_sequence"] = 0
                generated.append("rates_selection.roll_sequence")
            for field in generated:
                provenance["case_fields"][field] = downs[0]["id"]
    # The plan window must be more than one year even with no events (review AF1: the
    # no-events return used to skip the check, leaving the model's own "Plan needs more
    # than 1 years." at solve time).
    if not events:
        check_death_window(scenario)
        return hand_case, hand_hfp, provenance

    info = hand_case.get("basic_info") or {}
    names = list(info.get("names") or [])
    plan_start = _plan_start(hand_case, scenario)
    years = resolve_years(events, hand_case)
    case = hand_case

    # The plan's window (the person sheets run from the plan start to the year the last person
    # reaches their life horizon): every resolved year must sit inside it (U7).
    births = [int(str(d)[:4]) for d in info.get("date_of_birth") or []]
    life = [int(expect) for expect in info.get("life_expectancy") or []]
    # Death events (I2) give their person's horizon (`basic_info.life_expectancy`, a generated
    # case field like the claiming ages): "first death at 75, each spouse in turn" as a variant
    # dimension, with Owl's own death mechanics below. The horizon a death sets must cover the
    # plan's start, or the plan would run zero years for that person.
    deaths = [e for e in events if e["kind"] == "death"]
    if deaths:
        from owlplanner.config.defaults import DEFAULT_LIFE_EXPECTANCY

        life += [DEFAULT_LIFE_EXPECTANCY] * (len(names) - len(life))
        for event in deaths:
            check_death_age(event["person"], event["age"], case, scenario, where=event["id"])
            life[names.index(event["person"])] = int(event["age"])
        _set_path(case, "basic_info.life_expectancy", list(life))
        provenance["case_fields"]["basic_info.life_expectancy"] = deaths[0]["id"]
    end_year = max((b + e for b, e in zip(births, life, strict=False)), default=None)
    check_death_window(scenario)
    check_death_after_work(scenario)
    for eid, fields in years.items():
        for field, year in fields.items():
            if year < plan_start or (end_year is not None and year > end_year):
                window = f"{plan_start}-{end_year}" if end_year is not None else f"from {plan_start}"
                raise ScenarioError(f"{eid}.{field} = {year} is outside the plan ({window})")
    by_id = {e["id"]: e for e in events}
    for eid, fields in years.items():
        event = by_id[eid]
        pairs = {"rent": ("end", "start"), "care": ("end", "year"), "purchase": ("sale", "year")}
        first, second = pairs.get(event["kind"], (None, None))
        if first in fields and fields[first] < fields[second]:
            raise ScenarioError(f"{eid}: {first} = {fields[first]} is before {second} = {fields[second]}")

    # Generated rows paired with their event, generated cells likewise. Rows are generated in
    # event order (the row order of the Budget sheet is part of the generated document).
    rows: dict[str, list[tuple[list, str]]] = {"Debts": [], "Fixed Assets": [], "Budget": []}
    cells: list[tuple[str, str, int, Any, str]] = []  # (sheet, column, year, value, event id)

    purchase = next((e for e in events if e["kind"] == "purchase"), None)
    purchase_year = years[purchase["id"]]["year"] if purchase else None
    # The inflation path the nominal amounts are built from is the one the solve will use: the
    # run's rates table when there is one (a downturn overlay moves the plan's own prices), else
    # the case's own method (step 5b).
    gamma = (_gamma(case, rates_rows=table["rows"] if table is not None else None)
             if purchase or any(e["kind"] == "rent" for e in events) else None)

    def nominal(amount, year):
        k = year - plan_start
        if gamma is None or not 0 <= k < len(gamma):
            raise ScenarioError(f"{year} is outside the case's inflation path")
        return round(amount * float(gamma[k]))

    work_ids = [e["id"] for e in events if e["kind"] == "work"]
    last_full = None
    for event in events:
        kind = event["kind"]
        where = years[event["id"]]
        if kind == "work":
            # Wages and contributions in the person sheets (section 6.2).
            if event.get("level", "full") == "full":
                last_full = event["end"] if last_full is None else max(last_full, event["end"])
            for year in range(event["start"], event["end"] + 1):
                for field, column in PAY_COLUMNS.items():
                    if event.get(field) is not None:
                        cells.append((event["person"], column, year, event[field], event["id"]))
        elif kind == "purchase":
            # The home: a Fixed Assets row in purchase-year dollars, a Debts row linked to it by
            # name, the big-ticket outflow, the owner's Budget lines, and the move (section 6.2).
            year = where["year"]
            sale = where.get("sale") or 0
            price = nominal(purchase["price"], year)
            financing = purchase.get("financing") or {"kind": "cash"}
            terms = {**FINANCING_DEFAULTS[financing.get("kind", "cash")], **financing}
            rows["Fixed Assets"].append((asset_row(
                purchase["name"], year, price, purchase.get("growth", 0.0), sale,
                purchase.get("commission", 0.0), purchase.get("type", "residence"),
                purchase.get("basis")), purchase["id"]))
            if financing.get("kind") == "loan":
                down, closing, extra = terms["down"], terms["closing"], terms["extra"]
                loan = round(price * (1 - down))
                rows["Debts"].append((debt_row(
                    financing.get("name", f"{purchase['name']} mortgage"), year, financing["term"],
                    loan, financing["rate"], purchase["name"]), purchase["id"]))
                outflow = -round(price * (down + closing) + loan * extra)
            else:
                outflow = -round(price * (1 + terms["closing"]))
            cells.append((purchase.get("pay_on") or (names[0] if names else ""), "big-ticket items", year,
                          outflow, purchase["id"]))
            costs = purchase.get("costs") or {}
            for row in owner_rows(costs.get("property tax", 0), costs.get("hoa", 0), costs.get("insurance", 0),
                                  year, (sale - 1) if sale else 0):
                rows["Budget"].append((row, purchase["id"]))
            place = {**PLACE_DEFAULTS, **(purchase.get("place") or {})}
            if place["move"]:
                # A move states its new place: a blank or "-" field there is none.
                _set_path(case, "basic_info.moves", [{
                    "year": year,
                    "state": place["state"],
                    "locality": place_text(place["locality"]),
                    "school_district": place_text(place["school_district"]),
                }])
                provenance["case_fields"]["basic_info.moves"] = purchase["id"]
            elif str(place["school_district"] or "").strip():
                # Stated ("-" for none); a blank field keeps the case's district (B2).
                _set_path(case, "basic_info.school_district", place_text(place["school_district"]))
                provenance["case_fields"]["basic_info.school_district"] = purchase["id"]
        elif kind == "rent":
            # Rent to the year before the purchase (section 6.2, I1).
            if "end" in event:
                end = where["end"]
            elif purchase_year is not None:
                end = purchase_year - 1
            else:
                end = 0
            for row in rent_rows(event["monthly"] * 12, where["start"], where["flat_until"], end, gamma, plan_start):
                rows["Budget"].append((row, event["id"]))
        elif kind == "care":
            for row in care_row(event["amount"], where["year"], where.get("end") or 0,
                                event.get("name", "care"), event.get("essential", True)):
                rows["Budget"].append((row, event["id"]))

    if work_ids:
        # The last work year gives the marketplace start year (section 6.2): employer coverage
        # runs while either spouse works full time (make_cases.py's rule).
        _set_path(case, "aca_settings.aca_start_year", (last_full + 1) if last_full is not None else plan_start)
        provenance["case_fields"]["aca_settings.aca_start_year"] = work_ids[0]

    # -- claiming: the ages and the switch ----------------------------------------------------
    claims = [e for e in events if e["kind"] == "claim"]
    if claims:
        current = list((hand_case.get("fixed_income") or {}).get("social_security_ages") or [])
        ages = []
        for i, name in enumerate(names):
            claim = next((c for c in claims if c["person"] == name), None)
            if claim is not None and claim["age"] is not None:
                ages.append(float(claim["age"]))  # the generated age is a float (the case's type)
            elif i < len(current):
                ages.append(current[i])  # a kept hand age keeps its own type (U8, V3)
            else:
                raise ScenarioError(
                    f"claim: no age for {name!r} and the case holds none (an age or a fixed case value)"
                )
        # Owl's withSSAges takes "optimize", "fixed", or a name / list of names to search
        # (plan._parseSSAgesOption): a mixed scenario searches only the free ones and holds
        # the others' ages (U4). A person with no claim event keeps the hand case's choice,
        # searched or held, as they keep its age (review X7).
        hand_free = _searched_names(
            (hand_case.get("solver_options") or {}).get("withSSAges", "fixed"), names)
        claimed = {c["person"] for c in claims}
        free = [name for name in names
                if (name in claimed and any(c["person"] == name and c["age"] is None for c in claims))
                or (name not in claimed and name in hand_free)]
        if not free:
            mode = "fixed"
        elif set(free) == set(names):
            mode = "optimize"
        else:
            mode = free
        _set_path(case, "fixed_income.social_security_ages", ages)
        _set_path(case, "solver_options.withSSAges", mode)
        for field in ("fixed_income.social_security_ages", "solver_options.withSSAges"):
            provenance["case_fields"][field] = claims[0]["id"]

    for table in HOUSE_TABLES:
        for row, eid in rows[table]:
            provenance["rows"][f"{table}|{row[1]}"] = eid
    for sheet, column, year, _value, eid in cells:
        provenance["cells"].append([sheet, column, year, eid])

    if purchase is not None:
        _check_one_home(hand_hfp, purchase, years[purchase["id"]], end_year)
    hfp = _merge_tables(hand_hfp, rows, cells, names, plan_start, births, life)
    return case, hfp, provenance


def _check_one_home(hand_hfp: dict, purchase: dict, where: dict, end_year) -> None:
    """Refuse a purchase event over a hand Fixed Assets home still owned while the event's
    home is (UX review B2): an imported case whose workbook holds its own purchase got a
    second residence, with no warning. A hand home sold (`yod`, disposed at the start of
    that year) by the event's year, an inactive row and the event's own row (kept by name
    from a pages save, regenerated) are not a second home."""
    table = hand_hfp.get("Fixed Assets") or {}
    columns = list(table.get("columns") or ASSET_COLUMNS)
    if not all(c in columns for c in ("name", "type", "year", "yod")):
        return
    at = {c: columns.index(c) for c in ("active", "name", "type", "year", "yod") if c in columns}
    start = where["year"]
    stop = where.get("sale") or None  # the event's home is gone from its sale year
    for row in table.get("rows") or []:
        if "active" in at and row[at["active"]] is False:
            continue
        if row[at["name"]] == purchase["name"] or str(row[at["type"]]).strip().lower() != "residence":
            continue
        try:
            bought, yod = int(row[at["year"]]), int(row[at["yod"]] or 0)
        except (TypeError, ValueError):
            continue
        if yod <= 0:  # zero or negative: counted from the plan's end (fixedassets' rule)
            yod = (end_year + yod + 1) if end_year is not None else None
        if (yod is None or start < yod) and (stop is None or bought < stop):
            sold = f"sold in {yod}" if yod is not None and yod <= (end_year or yod) else "kept to the end"
            raise ScenarioError(
                f"the case already holds a home, {row[at['name']]!r} (Fixed Assets, from {bought}, "
                f"{sold}), owned while the purchase event's {purchase['name']!r} is (from {start}): "
                "the plan would hold two homes. Drop the purchase event, or start from a run with "
                "no home in its workbook (a rent-only case: no home in Fixed Assets, no loan for "
                "it, no owner's budget lines or purchase outflow) and add the purchase here."
            )


def _searched_names(option, names) -> set:
    """The people a withSSAges value searches (plan._parseSSAgesOption's reading)."""
    if isinstance(option, str):
        if option.strip().lower() == "optimize":
            return set(names)
        return {option} & set(names)
    if isinstance(option, (list, tuple)):
        return set(option) & set(names)
    return set()


def _merge_tables(hand_hfp, rows, cells, names, plan_start, births, life) -> dict:
    """Hand rows with the generated ones: generated rows by name (regenerated wholesale),
    generated cells by position (section 6.3's markers). Sheets come in workbook order:
    the person sheets first, then Debts, Fixed Assets and Budget."""
    generated_names = {table: {row[1] for row, _eid in rows[table]} for table in HOUSE_TABLES}
    hfp: dict[str, dict] = {}

    # Person sheets: hand rows with the generated cells set; a generated cell year gets a row.
    by_sheet: dict[str, dict[int, dict[str, Any]]] = {}
    for sheet, column, year, value, _eid in cells:
        by_sheet.setdefault(sheet, {}).setdefault(year, {})[column] = value
    sheet_names = list(dict.fromkeys([*names, *[s for s in hand_hfp if s not in HOUSE_TABLES]]))
    end_year = max((birth + expect for birth, expect in zip(births, life, strict=False)), default=plan_start)
    for sheet in sheet_names:
        hand = hand_hfp.get(sheet) or {}
        columns = list(hand.get("columns") or PERSON_COLUMNS)
        year_at = columns.index("year")
        rows_by_year: dict[int, list] = {}
        for row in hand.get("rows") or []:
            rows_by_year[int(row[year_at])] = list(row)
        if not rows_by_year:
            for year in range(plan_start, end_year + 1):
                row = [0] * len(columns)
                row[year_at] = year
                rows_by_year[year] = row
        for year, values in by_sheet.get(sheet, {}).items():
            if year not in rows_by_year:
                row = [0] * len(columns)
                row[year_at] = year
                rows_by_year[year] = row
            for column, value in values.items():
                rows_by_year[year][columns.index(column)] = value
        hfp[sheet] = {"columns": columns, "rows": [rows_by_year[y] for y in sorted(rows_by_year)]}

    for table in HOUSE_TABLES:
        hand = hand_hfp.get(table) or {}
        columns = list(hand.get("columns") or _table_columns(table))
        name_at = columns.index("name") if "name" in columns else None
        names_here = generated_names[table]  # the name is the identity within one table (U5)
        kept = [
            list(row) for row in hand.get("rows") or []
            if not (name_at is not None and len(row) > name_at and row[name_at] in names_here)
        ]
        kept.extend(_place_row(columns, row) for row, _eid in rows[table])
        hfp[table] = {"columns": columns, "rows": kept}
    return hfp


def _table_columns(table: str) -> list[str]:
    return {
        "Debts": list(DEBT_COLUMNS),
        "Fixed Assets": list(ASSET_COLUMNS),
        "Budget": list(BUDGET_COLUMNS),
    }[table]


def _place_row(columns: list[str], row: list) -> list:
    """A generated row (built in the canonical column order) placed in the table's columns."""
    source = {
        len(BUDGET_COLUMNS): BUDGET_COLUMNS,
        len(ASSET_COLUMNS): ASSET_COLUMNS,
        len(DEBT_COLUMNS): DEBT_COLUMNS,
    }.get(len(row))
    if source is None or list(columns) == list(source):
        return list(row)
    out = [None] * len(columns)
    for value, column in zip(row, source, strict=True):
        if column in columns:
            out[columns.index(column)] = value
    return out


def _plan_start(case: dict, scenario: dict) -> int:
    start = (case.get("basic_info") or {}).get("start_date")
    if isinstance(start, str) and len(start) >= 4 and start[:4].isdigit():
        return int(start[:4])
    plan_year = scenario.get("plan_year")
    if isinstance(plan_year, int):
        return int(plan_year)
    raise ScenarioError(
        "the plan's start year is unknown: set basic_info.start_date or the scenario's plan_year"
    )

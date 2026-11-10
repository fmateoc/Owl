"""A run for a new plan year, from last year's run (design 8.3; local-use review D2).

A run is solved only in its plan year (`casefiles.check_plan_year`): Owl's plan starts in the
calendar year of the solve, so January's balances of one year would be read as the next
January's. From 1 January every run of the library is refused, and the way on is a run for
the new year: this year's balances, a new plan year, the old run as its parent.

`start_year(scenario, year)` makes that run's scenario from last year's. It moves the plan
year and the balance date's year, and it carries the events over -- which moving the year
alone does not: an event that starts in the old plan year is "outside the plan" for the
builder (`rent.start = 2026 is outside the plan (2027-2053)`). The rules, with Y the new year:

- **An event that is over** (a work span, a rent or a care span ending before Y; a home bought
  and sold before Y) is dropped: what it did is in the balances. So is **a downturn placed
  before Y**, whether or not its window still runs: its years behind the plan are in the
  balances, and the run follows the case's own rates again.
- **A home bought before Y and still owned** stops being an event and becomes hand rows: the
  Fixed Assets row, the loan, the owner's budget lines and the move or school district the
  event generated, taken from the run's own build. The rows hold the price and the loan in
  the dollars of the year it was bought in, which a purchase *event* (today's dollars, grown
  by the plan's inflation from the plan start) could not express once that year is past. The
  loan is exact from there (Owl amortizes it from its start year). The home's *value* is not:
  Owl's reader resets a Fixed Assets year in the past to the plan's first year and reads the
  value as the worth at its start, so the price left as it is loses a year of growth and
  inflation at every roll (700,000 at 0.5% real and 2.8% inflation: 25,089 less home at the
  end, in the new year's dollars, review AQ2). No amount is re-priced here, so the notes say
  it, for the home just frozen and for every property a run already held as rows
  (`_note_owned_assets`). This step is accepted only on an exact rebuild at the old plan year
  (`convert_housing`'s rule, the other way round).
- **An event under way** (work, rent or care that started before Y and goes on) starts at Y.
  A rent's monthly amount is not changed: within its flat years that is exact (the nominal
  rent is the same), after them it is last year's rent read in Y's dollars, like every other
  amount in today's dollars -- the caller says so (`TODAYS_DOLLARS_NOTE`).
- **A year anchored to an event that left or moved** (`event:care+2`, `purchase`,
  `after:Noa`) becomes the calendar year it resolved to.
- **The years before Y in the person sheets** become hand rows holding what the run's build
  held (the wages a work event generated, the purchase's outflow): history, which no event
  generates any more and which the earnings test reads for someone already claiming (#235).
- **Case fields counted from the plan start**: `previousMAGIs` / `previousSTARIncomes` (the
  two years before the plan) shift by the years moved, the year now needed left at 0; a move
  (`basic_info.moves`) dated in Y or before becomes the residence the plan starts in (Owl
  refuses a move in the plan's first year); the marketplace start year the work events
  generated is kept once they are all over.

The balances are *not* changed: they are last year's, and the new run must not be saved with
them. The interface opens the rolled inputs in the case pages (Account Balances first) and
saves against them (`ui/library_save.py`); nothing is stored until then. The plan-against-
actual comparison of the design's yearly check-in (I4's drift chart) is not built.
"""

from __future__ import annotations

import copy
from typing import Any

from . import builder
from .casefiles import _differences, _table_differences, _with_year, canonicalize
from .scenario import ScenarioError

# What the caller tells the user beside the notes: no amount is re-priced here.
TODAYS_DOLLARS_NOTE = (
    "Amounts in today's dollars (budget lines, the rent, a home's price, care costs) are "
    "unchanged and are now read in {year}'s dollars: raise the ones that should have kept up "
    "with prices."
)

_PREVIOUS_YEARS = ("previousMAGIs", "previousSTARIncomes")  # the two years before the plan


def start_year(scenario: dict, year: int) -> tuple[dict, list[str]]:
    """(the scenario for plan year `year`, notes on what was carried over and how).

    Raises ScenarioError when the run is already for `year` or a later one, when a bought home
    cannot be carried over exactly, or when the result does not build (a death event already
    reached, say): what is returned has been through the builder.
    """
    try:
        return _start_year(scenario, int(year))
    except ScenarioError:
        raise
    except ValueError as exc:  # the plan the builder reads the inflation path from refused the case
        raise ScenarioError(f"the run cannot be carried over to {year}: {exc}") from exc


def _start_year(scenario: dict, year: int) -> tuple[dict, list[str]]:
    base = canonicalize(copy.deepcopy(scenario))
    old = base.get("plan_year")
    if old is None:
        raise ScenarioError("the run has no plan year: the library cannot tell which year it was made for")
    if year <= int(old):
        raise ScenarioError(f"the run is already for {old}: a new plan year must be later (asked: {year})")
    notes: list[str] = []
    # First, so that every build below reads a case Owl accepts: it refuses a move dated in
    # the plan's first year or before, and the builder's inflation path comes from a plan.
    _fold_moves(base["case"].setdefault("basic_info", {}), year, notes)
    owned = _owned_assets(base.get("hfp") or {}, year)  # before a purchase event joins them
    if base.get("events"):
        base["events"] = _roll_events(base, year, notes)
    notes.extend(owned)
    _roll_case(base["case"], int(old), year, notes)
    base["plan_year"] = year
    rolled = canonicalize(base)
    try:
        builder.build(rolled)
    except ScenarioError as exc:
        raise ScenarioError(f"the run cannot be carried over to {year}: {exc}") from exc
    return rolled, notes


# ---------------------------------------------------------------------------
# The events
# ---------------------------------------------------------------------------


def _roll_events(base: dict, new_year: int, notes: list[str]) -> list[dict]:
    """The events for the new plan year; `base`'s hand case and tables take what leaves them."""
    case, hfp = base["case"], base["hfp"]
    events = copy.deepcopy(base["events"])
    years = builder.resolve_years(events, case)
    # A downturn placed before the new year goes first, before anything is built: the builder
    # reads the rate path from a plan that starts in the clock's year, and refuses a window
    # that starts before it. Dropped after the build below, as first written, it was never
    # reached: the roll of such a run stopped at "the window starts at 2026, before the plan
    # (2027-2053), and would be cut" (review AQ8).
    for event in [e for e in events if e["kind"] == "downturn" and years[e["id"]]["start"] < new_year]:
        events.remove(event)
        notes.append(f"The {event['sequence']} downturn was placed at {years[event['id']]['start']}, "
                     f"before {new_year}: it is dropped, and the plan follows the case's own rates "
                     "again (place one on the Scenario page to stress the new year's plan).")
    base["events"] = copy.deepcopy(events)
    built_case, built_tables, provenance = builder.build(base)

    purchase = next((e for e in events if e["kind"] == "purchase"), None)
    purchase_year = years[purchase["id"]]["year"] if purchase else None

    over: set[str] = set()      # dropped: nothing of them is left in the plan
    frozen: set[str] = set()    # dropped as events, kept as hand rows (a home still owned)
    for event in events:
        kind, where = event["kind"], years[event["id"]]
        if kind == "work":
            if int(event["end"]) < new_year:
                over.add(event["id"])
                notes.append(f"{event['person']}'s work to {event['end']} is over: what the run held for "
                             "those years is now in the workbook's rows, as history.")
        elif kind == "purchase":
            if where["year"] < new_year:
                if where.get("sale") and where["sale"] < new_year:
                    over.add(event["id"])
                    notes.append(f"{event['name']} was bought in {where['year']} and sold in "
                                 f"{where['sale']}: both are behind the plan, the event is dropped.")
                else:
                    frozen.add(event["id"])
                    notes.append(f"{event['name']} was bought in {where['year']}: it is now a home the "
                                 "plan starts with (Fixed Assets, its loan and the owner's budget lines "
                                 "as rows), no longer a purchase event. In Fixed Assets its *value* is the "
                                 f"planned price, which the plan reads as what the home is worth in January "
                                 f"{new_year}: put in what it is worth now, and in *basis* what was paid. "
                                 "Check the loan against what was borrowed.")
        elif kind == "rent":
            end = where.get("end") or ((purchase_year - 1) if purchase_year is not None else 0)
            if end and end < new_year:
                over.add(event["id"])
                notes.append(f"The rent ended in {end}: the event is dropped.")
        elif kind == "care":
            end = where.get("end") or 0
            if end and end < new_year:
                over.add(event["id"])
                notes.append(f"{event.get('name', 'care')} ended in {end}: the event is dropped.")

    # History first, from the build every event still takes part in.
    _freeze_history(hfp, built_tables, new_year)
    if frozen:
        _freeze_home(base, events, years, built_case, built_tables, provenance, frozen)

    # The marketplace start year the work events generate (the year after the last full-time
    # one) outlives them: once they are all over it is the case's own value.
    work = [e for e in events if e["kind"] == "work"]
    if work and all(e["id"] in over for e in work):
        generated = ((built_case.get("aca_settings") or {}).get("aca_start_year"))
        if generated is not None:
            builder._set_path(case, "aca_settings.aca_start_year", max(int(generated), new_year))

    gone = over | frozen
    working = {e["person"] for e in work if e["id"] not in gone}
    # An event under way starts at the new year; its own year then no longer is the year
    # another event's anchor meant.
    moved = {
        e["id"] for e in events
        if e["id"] not in gone and e["kind"] in ("rent", "care")
        and years[e["id"]][builder.EVENT_YEAR_FIELD[e["kind"]]] < new_year
    }

    def loose(ref: dict) -> bool:
        anchor = ref.get("anchor")
        return ((anchor == "event" and ref["id"] in (gone | moved))
                or (anchor == "purchase" and purchase is not None and purchase["id"] in gone)
                or (anchor == "work_end" and ref["person"] not in working))

    kept = []
    for event in events:
        if event["id"] in gone:
            continue
        where = years[event["id"]]
        if event["kind"] == "work":
            if int(event["start"]) < new_year:
                event["start"] = new_year
        else:
            for field in builder._year_fields(event):
                if where[field] < new_year:
                    event[field] = {"year": new_year}
                elif loose(event[field]):
                    event[field] = {"year": where[field]}
            if event["id"] in moved:
                what = "The rent" if event["kind"] == "rent" else event.get("name", "care")
                notes.append(f"{what} started in {where[builder.EVENT_YEAR_FIELD[event['kind']]]} and "
                             f"goes on: its event now starts in {new_year}.")
        kept.append(event)
    return kept


def _freeze_history(hfp: dict, built_tables: dict, new_year: int) -> None:
    """The person sheets' rows before `new_year` as the run's build held them (hand rows)."""
    for sheet, built in built_tables.items():
        if sheet in builder.HOUSE_TABLES:
            continue
        columns = list(built["columns"])
        year_at = columns.index("year")
        past = [list(row) for row in built["rows"] if int(row[year_at]) < new_year]
        hand = hfp.get(sheet) or {}
        hand_rows = [list(row) for row in hand.get("rows") or []]
        if not hand_rows:
            if not any(value for row in past for i, value in enumerate(row) if i != year_at):
                continue  # nothing was held for those years: the sheet stays generated
            # A sheet with no hand rows is generated whole (zero rows for every plan year,
            # `_merge_tables`); with history rows in it, it must hold those years itself.
            later = sorted({int(row[year_at]) for row in built["rows"]} - {int(row[year_at]) for row in past})
            for y in later:
                row = [0] * len(columns)
                row[year_at] = y
                hand_rows.append(row)
        elif list(hand.get("columns") or columns) != columns:
            continue  # not the builder's layout: left as the hand table has it
        by_year = {int(row[year_at]): row for row in hand_rows}
        for row in past:
            by_year[int(row[year_at])] = row
        hfp[sheet] = {"columns": columns, "rows": [by_year[y] for y in sorted(by_year)]}


def _freeze_home(base, events, years, built_case, built_tables, provenance, frozen) -> None:
    """A bought home's generated rows and case fields into the hand document, on an exact rebuild.

    The check is made at the old plan year, before anything else moves: the scenario without
    the purchase event (a rent that ended "the year before the purchase" given that year)
    must build the tables the run builds today, and the same case apart from the fields the
    purchase generated -- which then become the hand case's own, a move as the residence the
    plan starts in (it is dated before the new plan year).
    """
    case, hfp = base["case"], base["hfp"]
    for key, eid in provenance["rows"].items():
        if eid not in frozen:
            continue
        table, name = key.split("|", 1)
        built = built_tables[table]
        name_at = built["columns"].index("name")
        rows = [list(row) for row in built["rows"] if row[name_at] == name]
        hand = hfp.get(table) or {"columns": list(built["columns"]), "rows": []}
        if list(hand.get("columns") or built["columns"]) != list(built["columns"]):
            raise ScenarioError(f"the {table} sheet is not in the builder's layout: the bought home's "
                                "rows cannot be written into it")
        hand_name_at = hand["columns"].index("name")
        hand["rows"] = [list(row) for row in hand["rows"] if row[hand_name_at] != name] + rows
        hfp[table] = hand
    paths = [path for path, eid in provenance["case_fields"].items() if eid in frozen]

    purchase_year = next(years[e["id"]]["year"] for e in events if e["kind"] == "purchase")
    check = copy.deepcopy(base)
    check["events"] = []
    for event in events:
        if event["id"] in frozen:
            continue
        event = copy.deepcopy(event)
        if event["kind"] == "rent" and "end" not in event:
            event["end"] = {"year": purchase_year - 1}
        for field in builder._year_fields(event):
            ref = event[field]
            anchored = isinstance(ref, dict) and (
                ref.get("anchor") == "purchase" or (ref.get("anchor") == "event" and ref.get("id") in frozen))
            if anchored:  # a year that leaned on the purchase: the year it resolved to
                event[field] = {"year": years[event["id"]][field]}
        check["events"].append(event)
    try:
        case_b, tables_b, _ = builder.build(check)
    except ScenarioError as exc:
        raise ScenarioError(f"the bought home cannot be carried over as rows: {exc}") from exc
    problems = (_table_differences(_sorted_tables(built_tables), _sorted_tables(tables_b))
                + _differences(_without(built_case, paths), _without(case_b, paths), "case."))
    if problems:
        raise ScenarioError(
            "the bought home cannot be carried over as rows: the plan would not be the same ("
            + "; ".join(problems[:6]) + ")"
        )

    info = case.setdefault("basic_info", {})
    for path in paths:
        value = _get_path(built_case, path)
        if path != "basic_info.moves":
            if value is None:
                _without(case, [path], copy_first=False)
            else:
                builder._set_path(case, path, copy.deepcopy(value))
            continue
        info.pop("moves", None)  # the event's move replaced the case's own (the builder's rule)
        if value:
            move = value[-1]
            info["state"] = move.get("state", info.get("state", ""))
            info["locality"] = move.get("locality", "") or ""
            info["school_district"] = move.get("school_district", "") or ""


def _owned_assets(hfp: dict, new_year: int) -> list[str]:
    """Notes for the properties the run holds as Fixed Assets rows valued before `new_year`.

    Owl reads such a row's value as the worth at the start of the plan's first year (its
    reader resets a year in the past to it), so a value carried over unchanged stands still
    while prices move: the note asks for today's value, every year."""
    table = hfp.get("Fixed Assets") or {}
    columns = list(table.get("columns") or [])
    if not {"name", "year", "value"} <= set(columns):
        return []
    at = {c: columns.index(c) for c in columns}
    out = []
    for row in table.get("rows") or []:
        try:
            valued, value = int(row[at["year"]]), float(row[at["value"]])
            sold = int(row[at["yod"]] or 0) if "yod" in at else 0
        except (TypeError, ValueError):
            continue  # a blank year is read as the plan's first year: nothing is behind
        if "active" in at and row[at["active"]] in (False, 0, "FALSE", "false"):
            continue
        if valued >= new_year or 0 < sold < new_year:
            continue
        out.append(f"Fixed Assets: *{row[at['name']]}* is valued at {value:,.0f}, as of {valued}. The plan "
                   f"reads that as what it is worth in January {new_year}: put in what it is worth now.")
    return out


def _without(doc: dict, paths, copy_first: bool = True) -> dict:
    """`doc` with the dotted `paths` removed."""
    doc = copy.deepcopy(doc) if copy_first else doc
    for path in paths:
        node = doc
        *sections, leaf = path.split(".")
        for key in sections:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict):
            node.pop(leaf, None)
    return doc


def _sorted_tables(tables: dict) -> dict:
    """Tables as the rebuild check compares them: what the plan reads, not how it is laid out.

    The rows in one order (a frozen row sits among the hand rows, a generated one after them:
    the same plan, another row order). And nothing for what holds nothing: a table without
    rows, and a person-sheet row that is zero apart from its year. A build with events lays
    out every house table and a zero row per plan year; one with no events left is the hand
    document as it is. Comparing the layouts refused every cash purchase the year after it,
    in the yearly use (2026 -> 2027 drops the rent and the work that are over, 2027 -> 2028
    checks the home with no other event: "Debts: columns differ", review AQ1)."""
    out = {}
    for sheet, table in tables.items():
        columns = list(table["columns"])
        rows = [list(r) for r in table["rows"]]
        if sheet not in builder.HOUSE_TABLES and "year" in columns:
            year_at = columns.index("year")
            rows = [r for r in rows if any(v for i, v in enumerate(r) if i != year_at)]
        if not rows:
            continue
        keys = [columns.index(c) for c in ("name", "year") if c in columns]
        out[sheet] = {"columns": columns, "rows": sorted(rows, key=lambda r: [str(r[k]) for k in keys])}
    return out


def _get_path(doc: dict, path: str) -> Any:
    """The value at a dotted path, None where the document has none."""
    for part in path.split("."):
        if not isinstance(doc, dict) or part not in doc:
            return None
        doc = doc[part]
    return doc


# ---------------------------------------------------------------------------
# The case
# ---------------------------------------------------------------------------


def _roll_case(case: dict, old: int, new_year: int, notes: list[str]) -> None:
    info = case.setdefault("basic_info", {})
    info["start_date"] = _with_year(info.get("start_date"), new_year)

    # The two years before the plan, oldest first: moved by the years the plan moved.
    shift = new_year - old
    options = case.get("solver_options") or {}
    for key in _PREVIOUS_YEARS:
        values = options.get(key)
        if isinstance(values, list) and len(values) == 2:
            options[key] = (list(values) + [0.0] * shift)[shift:][:2]
            if any(values):
                what = "The MAGI" if key == "previousMAGIs" else "The STAR income"
                unknown = ", ".join(str(y) for y in range(max(old, new_year - 2), new_year))
                notes.append(f"{what} of the two years before the plan moved with it: {unknown} is "
                             "not known here and reads 0 until it is entered"
                             + (" (Run Options)." if key == "previousMAGIs" else "."))


def _fold_moves(info: dict, new_year: int, notes: list[str]) -> None:
    """A move dated in the new plan's first year or before is where the plan starts.

    The residence in force on December 31 taxes the whole year, so a move in the first year is
    the starting residence too, and Owl refuses one there (`residency`: "A move must fall
    after the first plan year")."""
    moves = [m for m in info.get("moves") or [] if isinstance(m, dict)]
    past = sorted((m for m in moves if int(m.get("year", new_year + 1)) <= new_year), key=lambda m: int(m["year"]))
    if not past:
        return
    last = past[-1]
    info["state"] = last.get("state", info.get("state", ""))
    info["locality"] = last.get("locality", "") or ""
    info["school_district"] = last.get("school_district", "") or ""
    info["moves"] = [m for m in moves if m not in past]
    if not info["moves"]:
        info.pop("moves")
    where = ", ".join(x for x in (info["locality"], info["state"]) if x)
    notes.append(f"The move of {last['year']} is not ahead of the plan any more: it now starts in {where}.")

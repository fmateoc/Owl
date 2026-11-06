"""The grid view and the leads (design section 9.3, step 6).

A collection's members carry their variant values ({dimension: label}, `store.Member`).
`grid_view` lays them out as `run_suite.py`'s `condo_pivot` does -- the row dimensions (for
example place and financing) against the column dimension (the purchase year) -- with each
cell showing the **score's difference from the reference** and below it the **home at the
end**, coloured by the comparison rule (R3, `compare`): *leads the reference* (at least as
good on both numbers, better on one beyond the noise rule), *trade-off*, *the reference
leads*, or grey when the difference is inside the noise band. The best score in each row is
marked, by score only (run_suite bolds the same way). Under maxBequest the cell's number, the
star and the front's "vs the reference" read the savings left instead of the score, which
there is the final bequest and holds the home, R3's other number (`view.first_number`,
review AJ3).

`front` answers the question the collection is written for (section 9.3): the variants that
**no other variant beats on both numbers** (the score and the home at the end, never added
-- R3), each with whether it leads the reference and whether that difference is resolved
against the noise rule.

Both read results, not runs (section 5: "Comparisons pick results"): an `Entry` pairs one
member with the solve its numbers come from, so the caller can take the newest solve, a
chosen one, or the exact-model companion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import compare as C
from . import view
from .view import Result


@dataclass(frozen=True)
class Entry:
    """One collection member with the result its numbers come from."""

    run_id: str
    name: str
    values: dict
    result: Optional[Result] = None

    @property
    def score(self) -> Optional[float]:
        return view.score(self.result) if self.result is not None else None

    @property
    def home(self) -> Optional[float]:
        return view.home_at_end(self.result) if self.result is not None else None

    @property
    def first(self) -> Optional[float]:
        """R3's first number (`view.first_number`): the score, or under maxBequest the savings
        left -- what the cells, the star and the front read (review AJ3)."""
        return view.first_number(self.result) if self.result is not None else None


@dataclass(frozen=True)
class Cell:
    """One grid cell: the difference from the reference, judged (section 9.3)."""

    entry: Entry
    delta: Optional[float] = None        # the first number - the reference's (AJ3: the score,
    #                                      or under maxBequest the savings left)
    verdict: str = "-"                   # "resolved" | "within noise" | "no difference" | "-"
    note: str = ""
    home: Optional[float] = None
    home_delta: Optional[float] = None
    lead: dict = field(default_factory=lambda: {"verdict": "-", "note": ""})
    best: bool = False                   # best score in its row (by score only)


@dataclass(frozen=True)
class Grid:
    """The pivot: rows of the row dimensions against the column dimension's keys."""

    reference: Entry
    col_dims: tuple
    row_dims: tuple
    col_keys: tuple       # each a tuple of the column dimensions' values
    rows: tuple           # (row key tuple, {col key: Cell or None})
    unplaced: tuple       # entries with no value for a row or column dimension
    collided: tuple       # (entry, shown) pairs: two members with the same cell key (AC4)
    flags: tuple          # the reference's and the cells' caveats (S13), deduplicated
    best_beside: tuple = ()  # run ids of collided members that hold their row's best score (AD3)


def _key(values: dict, dims) -> tuple:
    return tuple(values.get(dim) for dim in dims)


def _sorted_keys(keys) -> list:
    """Sorted for reading (years first, then labels); None (a missing value) sorts last."""
    return sorted(set(keys), key=lambda k: (any(x is None for x in k), tuple(str(x) for x in k)))


def grid_view(entries, *, reference: "Entry | str", row_dims=("place", "financing"),
              col_dims=("year",)) -> Grid:
    """Lay the entries out by their values (section 9.3's grid view).

    `reference` is the entry (or run id) the cells are differences from. A member with no
    values at all is listed in `unplaced` (it has no grid position); a value a placed member
    lacks is its dimension's None bucket. One cell holds one member: another member with
    the very same values keeps its own Cell beside the grid (`collided`, review AC4: two
    runs of one question cell never silently vanish from the pivot). Cells are judged
    against the reference's own result (`compare.difference` for the score, the home by the
    fifty-cent rule alone -- it is set by the inputs), and the lead verdict is R3's two
    numbers.
    """
    by_id = {e.run_id: e for e in entries}
    ref = by_id.get(reference) if isinstance(reference, str) else reference
    if ref is None:
        raise ValueError(f"the reference {reference!r} is not one of the entries")
    row_dims, col_dims = tuple(row_dims), tuple(col_dims)

    placed, unplaced = [], []
    for entry in entries:
        values = entry.values or {}
        if not values:
            # A member added by hand with no variant values carries no grid position: it is
            # listed beside the grid, not placed. A value a placed member lacks is its
            # dimension's None bucket (a variant that varies only the year sits in one row).
            unplaced.append(entry)
        else:
            placed.append(entry)

    col_keys = _sorted_keys({_key(e.values, col_dims) for e in placed})
    row_keys = _sorted_keys({_key(e.values, row_dims) for e in placed})
    cells = {}
    for entry in placed:
        if entry is ref or entry.result is None or ref.result is None:
            cells[entry.run_id] = Cell(entry=entry, home=entry.home)
            continue
        judgment = C.difference(view.first_number_name(ref.result), ref.first, entry.first,
                                ta=ref.result, tb=entry.result)
        home = entry.home
        home_delta = None if home is None or ref.home is None else home - ref.home
        cells[entry.run_id] = Cell(
            entry=entry,
            delta=judgment.delta,
            verdict=judgment.verdict,
            note=judgment.note,
            home=home,
            home_delta=home_delta,
            lead=lead_between(ref, entry),
        )

    # One cell per (row key, column key): the first member whose values fit it; another
    # member with the very same values keeps its own Cell beside the grid (review AC4).
    shown = {}
    collided = []
    for entry in placed:
        key = (_key(entry.values, row_dims), _key(entry.values, col_dims))
        if key in shown:
            collided.append((entry, shown[key]))
        else:
            shown[key] = entry

    # Best score in each row, by score only (run_suite's `condo_pivot` bolds the same way) --
    # R3's first number, so under maxBequest the savings left, not savings + home (AJ3).
    # The mark goes to the best member itself (review AD3): a cell is starred only when it
    # shows that member, and a best member listed beside the grid (collided) is named in
    # `best_beside` -- the star never sits on a number that is not the row's best.
    best_beside = []
    for key in row_keys:
        here = [e for e in placed if _key(e.values, row_dims) == key]
        scored = [e for e in here if e.first is not None]
        if scored:
            best = max(scored, key=lambda e: e.first)
            if shown[(key, _key(best.values, col_dims))] is not best:
                best_beside.append(best.run_id)
                continue
            cell = cells[best.run_id]
            cells[best.run_id] = Cell(
                entry=cell.entry, delta=cell.delta, verdict=cell.verdict, note=cell.note,
                home=cell.home, home_delta=cell.home_delta, lead=cell.lead, best=True,
            )

    rows = []
    for key in row_keys:
        row = {}
        for col in col_keys:
            entry = shown.get((key, col))
            row[col] = cells.get(entry.run_id) if entry is not None else None
        rows.append((key, row))

    flags = []
    for entry in placed:
        if entry is not ref and entry.result is not None and ref.result is not None:
            flags.extend(C.flags(ref.result, entry.result))
    ages_flag = claiming_ages_flag(ref, placed)
    if ages_flag:
        flags.append(ages_flag)
    return Grid(
        reference=ref,
        col_dims=col_dims,
        row_dims=row_dims,
        col_keys=tuple(col_keys),
        rows=tuple(rows),
        unplaced=tuple(unplaced),
        collided=tuple(collided),
        flags=tuple(dict.fromkeys(flags)),
        best_beside=tuple(best_beside),
    )


def _exact_only(run_path) -> bool:
    """Is every solve of the run -- solved, failed, running or queued -- a model companion's?

    The tornado's children are queued under `decision_exact` alone (its medical-inflation
    child under `exact_medicare`, review AJ1). A "decision" member is not: its local-search
    solve sits beside its exact companion even while it runs or after it failed (review AH5).
    A folder's model comes from its record when there is one, else from its job record's
    preset (`status.json`), else from its name (`<stamp>_<preset>`).
    """
    from .presets import COMPANION_PRESETS

    results = Path(run_path) / "results"
    if not results.is_dir():
        return False
    found = False
    for folder in results.iterdir():
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        record = view.load_result(folder).record
        if record:
            exact = (record.get("preset") in COMPANION_PRESETS
                     or view.record_companion(record) is not None)
        else:
            try:
                with open(folder / "status.json", encoding="utf-8") as f:
                    preset = (json.load(f) or {}).get("preset")
            except (OSError, ValueError, AttributeError):
                preset = folder.name.split("_", 1)[1] if "_" in folder.name else None
            exact = preset in COMPANION_PRESETS
        if not exact:
            return False
        found = True
    return found


def member_results(run_paths) -> tuple:
    """({path: Result or None}, exact): one model for every member of a collection.

    The grid reads each member's newest result that is not the exact-LP companion (R2's
    agreement check, not the headline). A member whose solves are all exact-LP ones -- the
    sensitivity tornado's children, which solve under the exact LP alone -- used to show as
    "no solved result yet" however many had solved (review AG5). When any member is in that
    state, every member is read through its exact-LP result instead (None where it has
    none), so the grid never judges two models against each other; `exact` says which.
    A member whose headline solve is still running or failed beside a solved exact companion
    (a "decision" member) does not switch the collection: it shows as unsolved (review AH5).
    The tornado's medical-inflation child solves under its own companion model alone
    (`exact_medicare`, review AJ1): it has no exact-LP result, so it shows as unsolved in the
    exact read (its bar, against the run's own solve under that model, is on the Run page).
    """
    paths = list(run_paths)
    plain = {path: latest_result(path) for path in paths}
    exact = {path: latest_result(path, prefer_exact=True) for path in paths}
    if any(plain[path] is None and exact[path] is not None and _exact_only(path) for path in paths):
        return exact, True
    return plain, False


def _months(result: Result) -> Optional[tuple]:
    """The claiming ages a solve used, as (name, months) pairs; None when unknown."""
    ages = view.claiming_ages(result)
    return tuple((name, int(round(float(age) * 12))) for name, age in ages) if ages else None


def claiming_ages_flag(reference: Entry, entries) -> str:
    """A caveat for the cells solved at claiming ages other than the reference's (AD5).

    The usual grid solves the reference with the "ages" preset and the variants with
    "decision", which holds each case's own ages: unless a single-valued claim dimension pins
    the grid at the reference's pick, every such cell's difference includes the claiming
    ages. A member whose values vary the claiming ages (a "claim" value) is left out: there
    the ages are the question. Returns "" when nothing differs or the ages are unknown.
    """
    if reference.result is None:
        return ""
    ref_ages = _months(reference.result)
    if ref_ages is None:
        return ""
    off = []
    for entry in entries:
        if entry is reference or entry.result is None or "claim" in (entry.values or {}):
            continue
        ages = _months(entry.result)
        if ages is not None and ages != ref_ages:
            off.append(f"{entry.name} ({view.claiming_ages_text(entry.result)})")
    if not off:
        return ""
    return (f"{len(off)} cell(s) solved at claiming ages other than the reference's "
            f"({view.claiming_ages_text(reference.result)}): {'; '.join(off)}. Their differences "
            "include the claiming ages; pin the grid at the reference's ages (a single claim "
            "value) to compare the housing alone")


def lead_between(a: Entry, b: Entry) -> dict:
    """R3's verdict on the pair: does b lead a, or is it a trade-off (`compare.lead_verdict`)?

    The two numbers are judged side by side (the score and the home at the end; under
    maxBequest, the savings left and the home) without the year-by-year "what moved" pass
    `compare.compare` also runs -- the grid judges every pair against the reference.
    """
    objective = C.objective_of(a.result) if a.result is not None else ""
    if a.result is None or b.result is None or not a.result.solved or not b.result.solved:
        return {"verdict": "not comparable", "note": "one of the two results has no numbers"}
    if objective != C.objective_of(b.result):
        return {"verdict": "not comparable",
                "note": f"different objectives ({objective} vs {C.objective_of(b.result)})"}
    rows = (
        C.difference("score", a.score, b.score, ta=a.result, tb=b.result),
        C.difference("home at the end", a.home, b.home, ta=a.result, tb=b.result,
                     from_inputs=True),
        C.difference("savings left at the end", view.savings_left(a.result),
                     view.savings_left(b.result), ta=a.result, tb=b.result),
    )
    return C.lead_verdict(rows, objective)


def front(entries, reference=None) -> list:
    """The variants no other variant beats on both numbers (section 9.3, R3).

    One entry leads another when `compare` says so -- at least as good on the score and on
    the home at the end (under maxBequest, the savings left and the home), better on one
    beyond the noise rule. Entries with no solved result, or with a different objective than
    the first solved one, are not comparable and are left out. Each front member comes with
    the entries it leads and its score judged against `reference` (default: the first solved
    member): "whether each lead is resolved" is that judgment's verdict.
    """
    solved = [e for e in entries if e.result is not None and e.result.solved]
    if not solved:
        return []
    objective = C.objective_of(solved[0].result)
    solved = [e for e in solved if C.objective_of(e.result) == objective]
    leads_over = {e.run_id: [] for e in solved}
    beaten = set()
    for a in solved:
        for b in solved:
            if a is b:
                continue
            if lead_between(b, a).get("verdict") == "the second result leads":  # a leads b
                leads_over[a.run_id].append(b.name)
                beaten.add(b.run_id)
    ref = next((e for e in solved if e.run_id == getattr(reference, "run_id", reference)), solved[0])
    out = []
    for entry in solved:
        if entry.run_id in beaten:
            continue
        # R3's first number (review AJ3): under maxBequest the score holds the home.
        judgment = C.difference(view.first_number_name(ref.result), ref.first, entry.first,
                                ta=ref.result, tb=entry.result)
        out.append({
            "entry": entry,
            "leads": tuple(leads_over[entry.run_id]),
            "score": entry.score,
            "first": entry.first,
            "home": entry.home,
            "vs_reference": judgment,
        })
    return out


def latest_result(run_path, *, prefer_exact: bool = False,
                  companion: Optional[str] = None) -> Optional[Result]:
    """The result to show for a run: its newest solved one under the case's own model (a
    model companion only when asked, as `ui/Run.py` defaults away from it -- R2's agreement
    check, not the headline).

    `prefer_exact` asks for the exact-LP companion ("decision_exact"); `companion` names any
    companion (`view.record_companion`: "decision_exact" or "exact_medicare", the tornado's
    Medicare model, review AJ1). Without either, no companion is a headline result: the
    tornado's "exact_medicare" base solve was the newest non-exact-LP result of its run, and
    a collection or the Run page read it as the run's own.

    Returns None for a run with no such solved result yet (a draft, or a failed solve).
    """
    wanted = companion if companion is not None else ("decision_exact" if prefer_exact else None)
    results = Path(run_path) / "results"
    if not results.is_dir():
        return None
    best = None
    for folder in sorted(results.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        result = view.load_result(folder)
        if not result.solved or view.record_companion(result.record) != wanted:
            continue
        best = result
        break
    return best

"""The grid view and the leads (design section 9.3, step 6).

A collection's members carry their variant values ({dimension: label}, `store.Member`).
`grid_view` lays them out as `run_suite.py`'s `condo_pivot` does -- the row dimensions (for
example place and financing) against the column dimension (the purchase year) -- with each
cell showing the **score's difference from the reference** and below it the **home at the
end**, coloured by the comparison rule (R3, `compare`): *leads the reference* (at least as
good on both numbers, better on one beyond the noise rule), *trade-off*, *the reference
leads*, or grey when the difference is inside the noise band. The best score in each row is
marked, by score only (run_suite bolds the same way).

`front` answers the question the collection is written for (section 9.3): the variants that
**no other variant beats on both numbers** (the score and the home at the end, never added
-- R3), each with whether it leads the reference and whether that difference is resolved
against the noise rule.

Both read results, not runs (section 5: "Comparisons pick results"): an `Entry` pairs one
member with the solve its numbers come from, so the caller can take the newest solve, a
chosen one, or the exact-model companion.
"""

from __future__ import annotations

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


@dataclass(frozen=True)
class Cell:
    """One grid cell: the difference from the reference, judged (section 9.3)."""

    entry: Entry
    delta: Optional[float] = None        # score - the reference's score
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
        judgment = C.difference("score", ref.score, entry.score, ta=ref.result, tb=entry.result)
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

    # Best score in each row, by score only (run_suite's `condo_pivot` bolds the same way):
    # the mark goes to the cell that holds the row's best score, even when that is a
    # collided member listed beside the grid.
    for key in row_keys:
        here = [e for e in placed if _key(e.values, row_dims) == key]
        scored = [e for e in here if e.score is not None]
        if scored:
            best = max(scored, key=lambda e: e.score)
            holder = shown[(key, _key(best.values, col_dims))]
            cell = cells[holder.run_id]
            cells[holder.run_id] = Cell(
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
    return Grid(
        reference=ref,
        col_dims=col_dims,
        row_dims=row_dims,
        col_keys=tuple(col_keys),
        rows=tuple(rows),
        unplaced=tuple(unplaced),
        collided=tuple(collided),
        flags=tuple(dict.fromkeys(flags)),
    )


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
        judgment = C.difference("score", ref.score, entry.score, ta=ref.result, tb=entry.result)
        out.append({
            "entry": entry,
            "leads": tuple(leads_over[entry.run_id]),
            "score": entry.score,
            "home": entry.home,
            "vs_reference": judgment,
        })
    return out


def latest_result(run_path, *, prefer_exact: bool = False) -> Optional[Result]:
    """The result to show for a run: its newest solved one (the exact companion only when
    asked, as `ui/Run.py` defaults away from it -- R2's agreement check, not the headline).

    Returns None for a run with no solved result yet (a draft, or a failed solve).
    """
    results = Path(run_path) / "results"
    if not results.is_dir():
        return None
    best = None
    for folder in sorted(results.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        result = view.load_result(folder)
        if not result.solved or bool(view.is_exact_lp(result)) != prefer_exact:
            continue
        best = result
        break
    return best

"""The claiming-age map over `work_sweep.py`'s scores output (run-library-design.md, 14.1, I7).

`fork-notes/phase5/work_sweep.py --json scores.json` scores a case at fixed claiming ages and
writes one row per work variant: the ages it swept, the decided ages and every scored plan
(`results`, keyed by the ages in "68y3m/63y0m" form, each cell with `value`, `tolerance` and
`proved`). This module reads that file and turns one variant into an `AgeMap` for the run
page's heat map: the objective over the free claiming ages, ties within tolerance shaded
together.

The scores file does not exist yet inside a results folder (the Ages presets come with step
6), so the run page looks for `scores.json` in the run folder and accepts a file the user
picks. Nothing here solves anything.

Tolerances (the rule R2 uses for pairs, applied to each cell): a proved cell (branch-and-bound)
reports its own `gap x objective`; any other solve has no certificate and takes the loop-noise
band, 1% of its own value (`view.NOISE_FRACTION`). Two cells tie when they are within the
larger of the two tolerances of each other.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .view import NOISE_FRACTION


@dataclass(frozen=True)
class AgeCell:
    """One scored plan: the free persons' claiming ages in months and the objective."""

    ages: tuple
    value: float
    tolerance: float


@dataclass
class AgeMap:
    """One work variant's scored claiming ages."""

    name: str
    free: list = field(default_factory=list)  # person names, in the order of `ages` tuples
    decided: tuple = ()  # the variant's decided ages, months per free person
    cells: list = field(default_factory=list)

    @property
    def dimensions(self) -> int:
        return len(self.free)

    def x_ages(self) -> list:
        """Swept ages of the first free person, ascending (months)."""
        return sorted({c.ages[0] for c in self.cells if c.ages}) if self.cells else []

    def y_ages(self) -> list:
        """Swept ages of the second free person, ascending (months); empty with one free."""
        return (sorted({c.ages[1] for c in self.cells if len(c.ages) > 1})
                if self.dimensions > 1 else [])

    def at(self, *ages) -> AgeCell | None:
        for cell in self.cells:
            if cell.ages == tuple(ages):
                return cell
        return None

    def best(self) -> AgeCell | None:
        return max(self.cells, key=lambda c: c.value) if self.cells else None

    def tie_groups(self) -> list:
        """The cells shaded together (I7): greedy groups, best leader first.

        A cell joins a group when the leader and the cell are within tolerance of each other
        (the larger of the two). The first group is the best plan and everything tied with it;
        the second is the best of the rest, and so on.
        """
        groups = []
        for cell in sorted(self.cells, key=lambda c: -c.value):
            for group in groups:
                lead = group[0]
                if lead.value - cell.value <= max(lead.tolerance, cell.tolerance):
                    group.append(cell)
                    break
            else:
                groups.append([cell])
        return groups

    def group_of(self) -> dict:
        """{(ages tuple): group index}, 0 = the best group (`tie_groups`' order)."""
        return {cell.ages: i for i, group in enumerate(self.tie_groups()) for cell in group}


def _age_months(text):
    """"68y3m" -> 819. Returns None for anything else (a key segment this build cannot read)."""
    try:
        years, _, months = str(text).strip().lower().partition("y")
        months = months.removesuffix("m") or "0"
        return int(years) * 12 + int(months)
    except (TypeError, ValueError):
        return None


def parse_scores(doc) -> list:
    """`work_sweep.py --json` output (a list of variant rows) -> [AgeMap], one per variant."""
    maps = []
    for row in doc if isinstance(doc, list) else []:
        if not isinstance(row, dict):
            continue
        results = row.get("results") or {}
        # The free persons' indices: the sweeps name each searched person and its index.
        indices = []
        for sweep in row.get("sweeps") or []:
            i = sweep.get("index")
            if isinstance(i, int) and i not in indices:
                indices.append(i)
        names = list(row.get("free") or [])
        if not indices:
            indices = list(range(len(names)))
        best = row.get("best") or []
        decided = tuple(int(best[i]) for i in indices if i < len(best))
        cells = []
        for key, cell in results.items():
            if not isinstance(cell, dict) or cell.get("status") not in (None, "solved"):
                continue
            value = cell.get("value")
            if not isinstance(value, (int, float)):
                continue  # a solve that failed: nothing scored
            ages_all = cell.get("ages")
            if not ages_all:  # older output: the key carries the ages
                ages_all = [_age_months(part) for part in str(key).split("/")]
            try:
                ages = tuple(int(ages_all[i]) for i in indices)
            except (IndexError, TypeError, ValueError):
                continue
            tol = cell.get("tolerance")
            tolerance = float(tol) if isinstance(tol, (int, float)) else NOISE_FRACTION * abs(float(value))
            cells.append(AgeCell(ages=ages, value=float(value), tolerance=max(0.0, tolerance)))
        cells.sort(key=lambda c: c.ages)
        free = names if len(names) == len(indices) else [f"person {i}" for i in indices]
        maps.append(AgeMap(name=str(row.get("name") or "variant"),
                           free=free, decided=decided, cells=cells))
    return maps


def load_scores(source) -> list:
    """Read a work_sweep scores file: a path, bytes, or a file-like object -> [AgeMap]."""
    if isinstance(source, (str, Path)):
        doc = json.loads(Path(source).read_text(encoding="utf-8"))
    elif isinstance(source, bytes):
        doc = json.loads(source.decode("utf-8"))
    else:
        doc = json.load(source)
    return parse_scores(doc)

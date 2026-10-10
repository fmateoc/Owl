"""
Budget: build the spending profile from line items.

Budgeting is not optimized. An optional HFP "Budget" sheet holds one row per budget line (core
spending, rent, property tax, a car, travel, care, ...), each with its years, an amount in today's
dollars, a real growth rate and the share a survivor keeps. This module turns the lines into the
spending profile's amounts per plan year; the optimizer consumes them as an external spending
profile (``Plan.setSpendingProfile("budget")``), normalized to its first year. Nothing in the LP
changes: the budget only sets the shape of net spending, and under ``maxSpending`` the whole budget
scales together.

Essential lines (fork, after #175): a line marked ``essential`` is a floor, not a share. Net spending
is then the essential lines at their amounts plus the other (discretionary) lines times one scale,
which ``maxSpending`` maximizes; ``Plan._add_income_profile`` writes that as affine profile rows.
Without essential lines the plan is the one above.

A line's survivor share defaults to the case's survivor percentage, except for household housing
costs (rent, property tax, insurance, maintenance), which a survivor keeps paying in full.

A line follows either the calendar (``year`` / ``end``) or an age (``clock = "age"``,
``start_age`` / ``end_age`` against ``index``: "younger" (default), "older", or a person's name).
An age clock is what a longer life needs: travel "while we are able" and care "from 80" stay tied
to the age that causes them, so extra years still include them.

The same lines can arrive as JSON (``load_json``) instead of the workbook sheet: one evaluator,
the sheet's DataFrame. Unknown fields and an unknown ``schema_version`` are refusals.

The fork's New Jersey property tax deduction reads the "property tax" and "rent" lines.

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

######################################################################
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import utils as u


BUDGET_TYPES = ("core", "rent", "property tax", "insurance", "maintenance", "car", "travel", "care", "other")

# Costs of the home: a survivor keeps paying them in full unless the line says otherwise.
HOUSEHOLD_TYPES = frozenset({"rent", "property tax", "insurance", "maintenance"})

PROPERTY_TAX = "property tax"
RENT = "rent"

CALENDAR = "calendar"
AGE = "age"
CLOCKS = (CALENDAR, AGE)
# Age index for a household line: the younger (default) or older spouse, or a person by name.
AGE_INDEXES = ("younger", "older")

JSON_SCHEMA_VERSION = 1

# JSON line fields. `kind` is free text for reporting and maps to the sheet's `type` when `type`
# is absent. `start_year` / `end_year` are accepted as aliases of `year` / `end`.
_JSON_LINE_FIELDS = frozenset(
    {
        "active",
        "name",
        "type",
        "kind",
        "clock",
        "year",
        "end",
        "start_year",
        "end_year",
        "start_age",
        "end_age",
        "index",
        "amount",
        "rate",
        "survivor",
        "essential",
    }
)

# Columns of the Budget sheet (and of the DataFrame evaluate() takes).
SHEET_COLUMNS = (
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
)


@dataclass(frozen=True)
class Budget:
    """Budget lines evaluated over the plan, in today's dollars.

    names, types -- one entry per active line
    amounts_ln   -- shape (lines, N_n): each line's amount by plan year
    total_n      -- shape (N_n,): the sum, the spending profile before normalization
    essential    -- one bool per active line: paid at its amount, not scaled by maxSpending
    """

    names: tuple
    types: tuple
    amounts_ln: np.ndarray
    total_n: np.ndarray
    essential: tuple = ()

    @property
    def has_essentials(self):
        return any(self.essential)

    @property
    def essential_n(self):
        """Sum of the essential lines, by plan year (today's dollars)."""
        rows = [k for k, e in enumerate(self.essential) if e]
        if not rows:
            return np.zeros(self.total_n.shape[0])
        return self.amounts_ln[rows].sum(axis=0)

    @property
    def discretionary_n(self):
        """Sum of the other lines, by plan year (today's dollars)."""
        return self.total_n - self.essential_n

    def by_type(self, *types):
        """Sum of the lines of the given types, by plan year (today's dollars)."""
        rows = [k for k, t in enumerate(self.types) if t in types]
        if not rows:
            return np.zeros(self.total_n.shape[0])
        return self.amounts_ln[rows].sum(axis=0)


def _is_blank(val):
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    try:
        return bool(np.isnan(val))
    except (TypeError, ValueError):
        return False


def _row_clock(row):
    """'calendar' (default) or 'age'. Anything else is a refusal."""
    val = row.get("clock", CALENDAR)
    if _is_blank(val):
        return CALENDAR
    clock = str(val).strip().lower()
    if clock not in CLOCKS:
        raise ValueError(f"Budget line {row.get('name')!r}: unknown clock {val!r}; use 'calendar' or 'age'.")
    return clock


def _row_index(row):
    """Which person's age an age-clock line follows: 'younger' (default), 'older', or a name."""
    val = row.get("index", "younger")
    if _is_blank(val):
        return "younger"
    return str(val).strip().lower()


def _ages_for_index(row, ages_in, inames):
    """Age series (length N_n) for the line's index. None when ages were not provided."""
    if ages_in is None:
        return None
    ages_in = np.asarray(ages_in, dtype=float)
    if ages_in.ndim != 2:
        raise ValueError("ages_in must have shape (N_i, N_n).")
    idx = _row_index(row)
    if idx == "younger":
        # Youngest: the smallest age at the plan's end (ties: first).
        return ages_in[np.argmin(ages_in[:, -1])]
    if idx == "older":
        return ages_in[np.argmax(ages_in[:, -1])]
    if inames is None:
        raise ValueError(f"Budget line {row.get('name')!r}: index {idx!r} needs person names to resolve.")
    lowered = [str(n).strip().lower() for n in inames]
    if idx not in lowered:
        raise ValueError(f"Budget line {row.get('name')!r}: unknown index {row.get('index')!r}.")
    return ages_in[lowered.index(idx)]


def _last_year(end, thisyear, N_n):
    """Last calendar year of a line. end <= 0 counts back from the plan's last year (0 = that year)."""
    plan_end = thisyear + N_n - 1
    return plan_end + end if end <= 0 else end


def _line_window(row, N_n, thisyear, ages_in=None, inames=None):
    """
    Calendar years the line pays, and the year its growth counts from.

    Returns (first_cal, last_cal, ref_cal), or None when the line never applies (or its age
    range is empty). first_cal may be before the plan start; the caller clips to the plan.
    """
    if _row_clock(row) == AGE:
        age_n = _ages_for_index(row, ages_in, inames)
        if age_n is None:
            raise ValueError(
                f"Budget line {row.get('name')!r}: an age clock needs the plan's ages; "
                "evaluate() was not given ages_in."
            )
        sa, ea = row.get("start_age"), row.get("end_age")
        if _is_blank(sa) or _is_blank(ea):
            raise ValueError(f"Budget line {row.get('name')!r}: clock 'age' needs start_age and end_age.")
        start_age, end_age = float(sa), float(ea)
        if end_age < start_age:
            return None
        hits = np.nonzero((age_n >= start_age) & (age_n <= end_age))[0]
        if hits.size == 0:
            return None
        first_n, last_n = int(hits[0]), int(hits[-1])
        first_cal = thisyear + first_n
        return first_cal, thisyear + last_n, max(first_cal, thisyear)

    year = row.get("year", 0)
    end = row.get("end", 0)
    start = int(0 if _is_blank(year) else year)
    last = _last_year(int(0 if _is_blank(end) else end), thisyear, N_n)
    ref = max(start, thisyear)
    return start, last, ref


def _survivor_share(row, default_pct):
    """Share of the line kept after the first death, as a fraction."""
    val = row.get("survivor", np.nan)
    try:
        val = float(val)
    except (TypeError, ValueError):
        val = np.nan
    if np.isnan(val):
        return 1.0 if str(row["type"]).lower() in HOUSEHOLD_TYPES else default_pct / 100.0
    if not 0 <= val <= 100:
        raise ValueError(f"Budget line {row['name']!r}: survivor {val} outside 0-100%.")
    return val / 100.0


def is_essential(row):
    """A line's essential flag: blank or missing means no."""
    val = row.get("essential", False)
    try:
        if val is None or (not isinstance(val, str) and np.isnan(val)):
            return False
    except TypeError:
        pass
    if isinstance(val, str) and val.strip() == "":
        return False
    return bool(u.convert_to_bool(val))


def evaluate(budget_df, N_n, n_d, survivor_pct, thisyear, ages_in=None, inames=None):
    """
    Evaluate the active budget lines over the plan.

    Parameters
    ----------
    budget_df : pd.DataFrame
        Columns: active, name, type, year, end, amount, rate, survivor, essential, and
        optionally clock, start_age, end_age, index. `amount` is annual, in today's dollars, as
        of the first year the line pays (a year before the plan start counts from the plan start);
        `rate` is real growth above inflation (%); `survivor` is the percent kept after the first
        death (blank: the case's percentage, or 100 for housing costs); `essential` (optional,
        blank = no) marks a line paid at its amount whatever the spending level.
        `clock` is "calendar" (default; `year` / `end`) or "age" (`start_age` / `end_age` against
        `index`: "younger" (default), "older", or a name in `inames`).
    N_n : int
        Plan length in years.
    n_d : int
        Index of the first year after the first death (N_n for a single person, or when nobody
        dies within the plan).
    survivor_pct : float
        The case's survivor percentage (default for personal lines).
    thisyear : int
        Calendar year of plan index 0.
    ages_in : array-like, optional
        Shape (N_i, N_n): each person's age in each plan year. Required for age clocks.
    inames : list of str, optional
        Person names, for an age index that names someone.

    Returns
    -------
    Budget
    """
    names, types, rows, essential = [], [], [], []
    if not u.is_dataframe_empty(budget_df):
        for _, row in budget_df.iterrows():
            if not u.is_row_active(row):
                continue
            window = _line_window(row, N_n, thisyear, ages_in=ages_in, inames=inames)
            if window is None:
                continue
            first_cal, last_cal, ref = window
            amount, rate = float(row["amount"]), float(row["rate"])
            share = _survivor_share(row, survivor_pct)
            line = np.zeros(N_n)
            for n in range(N_n):
                cal = thisyear + n
                if max(ref, first_cal) <= cal <= last_cal:
                    line[n] = amount * (1.0 + rate / 100.0) ** (cal - ref)
            if n_d < N_n:
                line[n_d:] *= share
            names.append(str(row["name"]))
            types.append(str(row["type"]).lower())
            rows.append(line)
            essential.append(is_essential(row))
    amounts = np.array(rows) if rows else np.zeros((0, N_n))
    total = amounts.sum(axis=0) if rows else np.zeros(N_n)
    return Budget(tuple(names), tuple(types), amounts, total, tuple(essential))


def lines_left_out(budget_df, N_n, thisyear, ages_in=None, inames=None):
    """(name, reason) for each active line that adds nothing within the plan.

    A positive `end` is a calendar year: one before the line starts (a term such as 10 typed as
    `end`, say) leaves the line out, as does a `year` after the plan's last year. An age line is
    left out when its range never meets the index person's ages inside the plan.
    """
    out = []
    if u.is_dataframe_empty(budget_df):
        return out
    plan_end = thisyear + N_n - 1
    for _, row in budget_df.iterrows():
        if not u.is_row_active(row):
            continue
        name = str(row.get("name"))
        try:
            window = _line_window(row, N_n, thisyear, ages_in=ages_in, inames=inames)
        except ValueError as e:
            out.append((name, str(e).split(": ", 1)[-1]))
            continue
        if window is None:
            if _row_clock(row) == AGE:
                out.append((name, f"age range {row.get('start_age')}-{row.get('end_age')} never applies to the plan"))
            else:
                out.append((name, "ends before it starts"))
            continue
        first_cal, last_cal, ref = window
        if _row_clock(row) == AGE:
            if first_cal > plan_end:
                out.append((name, f"starts at age {row.get('start_age')}, after the plan ends in {plan_end}"))
            elif last_cal < thisyear:
                out.append((name, f"ends at age {row.get('end_age')}, before the plan starts in {thisyear}"))
            continue
        start, end = int(row["year"]), int(row["end"])
        last = _last_year(end, thisyear, N_n)
        if start > plan_end:
            out.append((name, f"starts in {start}, after the plan ends in {plan_end}"))
        elif last < max(start, thisyear):
            out.append((name, f"ends in {last}, before it starts in {max(start, thisyear)}"))
    return out


def profile(budget):
    """The spending profile xi_n: the budget normalized to its first year.

    The first year sets the scale (net spending's first year is the basis), so it must not be zero.
    """
    total0 = float(budget.total_n[0])
    if total0 <= 0:
        raise ValueError(
            "The budget has no spending in the plan's first year: the spending profile is scaled by "
            "its first year. Add a line covering the first year (for instance core spending)."
        )
    return budget.total_n / total0


# ---------------------------------------------------------------------------
# JSON interchange (Owl-budget / MCP). Same lines as the sheet, one evaluator.
# ---------------------------------------------------------------------------


def _json_line_to_row(line, i):
    """One JSON line object as a sheet row dict. Raises on unknown fields or missing amounts."""
    if not isinstance(line, dict):
        raise ValueError(f"Budget line {i}: expected an object, got {type(line).__name__}.")
    unknown = set(line) - _JSON_LINE_FIELDS
    if unknown:
        raise ValueError(f"Budget line {i}: unknown fields {sorted(unknown)}. Allowed: {sorted(_JSON_LINE_FIELDS)}.")
    name = line.get("name", f"line {i}")
    typ = line.get("type", line.get("kind"))
    if typ is None or (isinstance(typ, str) and not typ.strip()):
        raise ValueError(f"Budget line {name!r}: needs 'type' (or 'kind').")
    if "amount" not in line:
        raise ValueError(f"Budget line {name!r}: needs 'amount' (today's dollars, $k).")
    clock = line.get("clock", CALENDAR)
    if _is_blank(clock):
        clock = CALENDAR
    clock = str(clock).strip().lower()
    year = line.get("year", line.get("start_year", 0))
    end = line.get("end", line.get("end_year", 0))
    if clock == AGE:
        if line.get("start_age") is None or line.get("end_age") is None:
            raise ValueError(f"Budget line {name!r}: clock 'age' needs start_age and end_age.")
    return {
        "active": bool(line.get("active", True)),
        "name": str(name),
        "type": str(typ).strip().lower(),
        "year": 0 if _is_blank(year) else int(year),
        "end": 0 if _is_blank(end) else int(end),
        "amount": float(line["amount"]),
        "rate": float(line.get("rate", 0.0) or 0.0),
        "survivor": np.nan if _is_blank(line.get("survivor")) else float(line["survivor"]),
        "essential": bool(line.get("essential", False)),
        "clock": clock,
        "start_age": np.nan if line.get("start_age") is None else float(line["start_age"]),
        "end_age": np.nan if line.get("end_age") is None else float(line["end_age"]),
        "index": "" if _is_blank(line.get("index")) else str(line["index"]).strip().lower(),
    }


def df_from_json_obj(obj):
    """
    A budget file object as the Budget sheet's DataFrame.

    Unknown top-level keys, unknown line fields and an unknown schema_version are errors, not
    silent drops: Owl refuses a file it cannot honor (as for a bad Debts property link).
    """
    if not isinstance(obj, dict):
        raise ValueError(f"Budget file: expected a JSON object, got {type(obj).__name__}.")
    ver = obj.get("schema_version")
    if ver != JSON_SCHEMA_VERSION:
        raise ValueError(f"Budget file schema_version {ver!r} is not supported; this Owl reads {JSON_SCHEMA_VERSION}.")
    unknown = set(obj) - {"schema_version", "lines"}
    if unknown:
        raise ValueError(f"Budget file: unknown fields {sorted(unknown)}.")
    lines = obj.get("lines")
    if not isinstance(lines, list):
        raise ValueError("Budget file: 'lines' must be a list.")
    rows = [_json_line_to_row(line, i) for i, line in enumerate(lines)]
    df = pd.DataFrame(rows, columns=list(SHEET_COLUMNS))
    return df


def load_json(path):
    """Read a budget profile JSON file into the Budget sheet's DataFrame."""
    path = Path(path)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Budget file {path.name}: not valid JSON ({e}).") from e
    return df_from_json_obj(obj)

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
``start_age`` / ``end_age`` against ``index``). An age clock is what a longer life needs: travel
"while we are able" and care "from 80" stay tied to the age that causes them, so extra years still
include them. ``index`` "younger" (default) or "older" is a household line, read against that
spouse's age while both are alive and the survivor's after the first death; a person's name makes a
personal line, which ends at that person's death.

The same lines can arrive as JSON (``load_json``) instead of the workbook sheet: one evaluator,
the sheet's DataFrame, amounts in today's dollars like the sheet. Unknown fields, an unknown
``schema_version`` or ``type``, and loosely typed values are refusals. ``kind`` is free text.

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
    "kind",
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


def _age_series(row, ages_in, inames, n_d, i_d):
    """
    Ages (length N_n) an age-clock line is read against, NaN in the years it cannot apply.

    A line indexed by a person's name follows that person and stops at their death. "younger"
    and "older" are household lines: they follow the younger (older) spouse while both are
    alive and the survivor after the first death. n_d is the first plan year after the first
    death (N_n when nobody dies within the plan) and i_d the person who dies then.
    """
    if ages_in is None:
        raise ValueError(
            f"Budget line {row.get('name')!r}: an age clock needs the plan's ages; evaluate() was not given ages_in."
        )
    ages_in = np.asarray(ages_in, dtype=float)
    if ages_in.ndim != 2:
        raise ValueError("ages_in must have shape (N_i, N_n).")
    N_i, N_n = ages_in.shape
    death = N_i == 2 and n_d < N_n
    if death and i_d not in (0, 1):
        raise ValueError(f"Budget line {row.get('name')!r}: an age clock needs who dies first (i_d).")
    idx = _row_index(row)
    if idx in AGE_INDEXES:
        k = int(np.argmin(ages_in[:, 0]) if idx == "younger" else np.argmax(ages_in[:, 0]))
        age_n = ages_in[k].copy()
        if death:
            age_n[n_d:] = ages_in[1 - i_d, n_d:]
        return age_n
    if inames is None:
        raise ValueError(f"Budget line {row.get('name')!r}: index {idx!r} needs person names to resolve.")
    lowered = [str(n).strip().lower() for n in inames]
    if idx not in lowered:
        raise ValueError(f"Budget line {row.get('name')!r}: unknown index {row.get('index')!r}.")
    k = lowered.index(idx)
    age_n = ages_in[k].copy()
    if death and k == i_d:
        age_n[n_d:] = np.nan
    return age_n


def _last_year(end, thisyear, N_n):
    """Last calendar year of a line. end <= 0 counts back from the plan's last year (0 = that year)."""
    plan_end = thisyear + N_n - 1
    return plan_end + end if end <= 0 else end


def _line_years(row, N_n, thisyear, ages_in=None, inames=None, n_d=None, i_d=None):
    """
    Plan years the line pays, and the calendar year its growth counts from.

    Returns (mask, ref_cal): mask is a bool array of length N_n. An age-clock line can pay in
    years that are not contiguous (an "older" line resumes when the survivor reaches its range).
    """
    cal_n = thisyear + np.arange(N_n)
    if _row_clock(row) == AGE:
        sa, ea = row.get("start_age"), row.get("end_age")
        if _is_blank(sa) or _is_blank(ea):
            raise ValueError(f"Budget line {row.get('name')!r}: clock 'age' needs start_age and end_age.")
        age_n = _age_series(row, ages_in, inames, N_n if n_d is None else n_d, i_d)
        with np.errstate(invalid="ignore"):
            mask = (age_n >= float(sa)) & (age_n <= float(ea))
        ref = int(cal_n[np.argmax(mask)]) if mask.any() else thisyear
        return mask, ref

    year = row.get("year", 0)
    end = row.get("end", 0)
    start = int(0 if _is_blank(year) else year)
    last = _last_year(int(0 if _is_blank(end) else end), thisyear, N_n)
    ref = max(start, thisyear)
    return (cal_n >= ref) & (cal_n <= last), ref


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


def evaluate(budget_df, N_n, n_d, survivor_pct, thisyear, ages_in=None, inames=None, i_d=None):
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
        `index`: "younger" (default) or "older", household lines that follow the survivor's age
        after the first death; or a name in `inames`, a personal line that ends with that person).
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
    i_d : int, optional
        Index of the person who dies first. Required for age clocks when n_d < N_n for a couple.

    Returns
    -------
    Budget
    """
    names, types, rows, essential = [], [], [], []
    if not u.is_dataframe_empty(budget_df):
        for _, row in budget_df.iterrows():
            if not u.is_row_active(row):
                continue
            mask, ref = _line_years(row, N_n, thisyear, ages_in=ages_in, inames=inames, n_d=n_d, i_d=i_d)
            if not mask.any():
                continue
            amount, rate = float(row["amount"]), float(row["rate"])
            share = _survivor_share(row, survivor_pct)
            cal_n = thisyear + np.arange(N_n)
            line = np.where(mask, amount * (1.0 + rate / 100.0) ** (cal_n - ref), 0.0)
            if n_d < N_n:
                line[n_d:] *= share
            names.append(str(row["name"]))
            types.append(str(row["type"]).lower())
            rows.append(line)
            essential.append(is_essential(row))
    amounts = np.array(rows) if rows else np.zeros((0, N_n))
    total = amounts.sum(axis=0) if rows else np.zeros(N_n)
    return Budget(tuple(names), tuple(types), amounts, total, tuple(essential))


def lines_left_out(budget_df, N_n, thisyear, ages_in=None, inames=None, n_d=None, i_d=None):
    """(name, reason) for each active line that adds nothing within the plan.

    A positive `end` is a calendar year: one before the line starts (a term such as 10 typed as
    `end`, say) leaves the line out, as does a `year` after the plan's last year. An age line is
    left out when its range never meets, inside the plan, the ages it follows (a named person's
    while they are alive).
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
            mask, _ = _line_years(row, N_n, thisyear, ages_in=ages_in, inames=inames, n_d=n_d, i_d=i_d)
        except ValueError as e:
            out.append((name, str(e).split(": ", 1)[-1]))
            continue
        if _row_clock(row) == AGE:
            if not mask.any():
                out.append((name, f"age range {row.get('start_age')}-{row.get('end_age')} never applies to the plan"))
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


def _json_number(line, key, name, default=None, integer=False):
    """A numeric field: a JSON number (not a boolean or a string); null or absent gives default."""
    val = line.get(key)
    if val is None:
        return default
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"Budget line {name!r}: {key} must be a number, got {val!r}.")
    if integer:
        if float(val) != int(val):
            raise ValueError(f"Budget line {name!r}: {key} must be a whole year, got {val!r}.")
        return int(val)
    return float(val)


def _json_flag(line, key, name, default):
    """A flag: JSON true or false; absent or null gives default. Strings such as "false" are refused."""
    val = line.get(key)
    if val is None:
        return default
    if not isinstance(val, bool):
        raise ValueError(f"Budget line {name!r}: {key} must be true or false, got {val!r}.")
    return val


def _json_text(line, key, name):
    val = line.get(key)
    if val is None:
        return ""
    if not isinstance(val, str):
        raise ValueError(f"Budget line {name!r}: {key} must be text, got {val!r}.")
    return val.strip()


def _json_line_to_row(line, i):
    """
    One JSON line object as a sheet row dict.

    Refused rather than read loosely: unknown fields, a `type` outside BUDGET_TYPES, a missing
    amount, numbers given as text, flags other than true / false, fractional years. `type` is the
    category Owl acts on (survivor default, the NJ deduction's lines); `kind` is free text kept
    for reporting, and serves as the type when `type` is absent and `kind` is one of the types.
    """
    if not isinstance(line, dict):
        raise ValueError(f"Budget line {i}: expected an object, got {type(line).__name__}.")
    unknown = set(line) - _JSON_LINE_FIELDS
    if unknown:
        raise ValueError(f"Budget line {i}: unknown fields {sorted(unknown)}. Allowed: {sorted(_JSON_LINE_FIELDS)}.")
    name = line.get("name", f"line {i}")
    if not isinstance(name, str):
        raise ValueError(f"Budget line {i}: name must be text, got {name!r}.")
    kind = _json_text(line, "kind", name)
    typ = _json_text(line, "type", name).lower()
    if not typ:
        if kind.lower() not in BUDGET_TYPES:
            raise ValueError(
                f"Budget line {name!r}: needs 'type', one of {list(BUDGET_TYPES)} "
                f"('kind' {kind!r} is free text and is not one of them)."
            )
        typ = kind.lower()
    if typ not in BUDGET_TYPES:
        raise ValueError(f"Budget line {name!r}: unknown type {typ!r}; use one of {list(BUDGET_TYPES)}.")
    amount = _json_number(line, "amount", name)
    if amount is None:
        raise ValueError(f"Budget line {name!r}: needs 'amount' (annual, today's dollars).")
    clock = _json_text(line, "clock", name).lower() or CALENDAR
    if clock not in CLOCKS:
        raise ValueError(f"Budget line {name!r}: unknown clock {clock!r}; use 'calendar' or 'age'.")
    for key, alias in (("year", "start_year"), ("end", "end_year")):
        if key in line and alias in line:
            raise ValueError(f"Budget line {name!r}: give {key!r} or {alias!r}, not both.")
    year = _json_number(line, "year" if "year" in line else "start_year", name, default=0, integer=True)
    end = _json_number(line, "end" if "end" in line else "end_year", name, default=0, integer=True)
    start_age = _json_number(line, "start_age", name, default=np.nan)
    end_age = _json_number(line, "end_age", name, default=np.nan)
    if clock == AGE and (np.isnan(start_age) or np.isnan(end_age)):
        raise ValueError(f"Budget line {name!r}: clock 'age' needs start_age and end_age.")
    return {
        "active": _json_flag(line, "active", name, True),
        "name": name,
        "type": typ,
        "year": year,
        "end": end,
        "amount": amount,
        "rate": _json_number(line, "rate", name, default=0.0),
        "survivor": _json_number(line, "survivor", name, default=np.nan),
        "essential": _json_flag(line, "essential", name, False),
        "clock": clock,
        "start_age": start_age,
        "end_age": end_age,
        "index": _json_text(line, "index", name).lower(),
        "kind": kind,
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

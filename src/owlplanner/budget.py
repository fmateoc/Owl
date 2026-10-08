"""
Budget: build the spending profile from line items.

Budgeting is not optimized. An optional HFP "Budget" sheet holds one row per budget line (core
spending, rent, property tax, a car, travel, care, ...), each with its years, an amount in today's
dollars, a real growth rate and the share a survivor keeps. This module turns the lines into the
spending profile's amounts per plan year; the optimizer consumes them as an external spending
profile (``Plan.setSpendingProfile("budget")``), normalized to its first year. Nothing in the LP
changes: the budget only sets the shape of net spending, and under ``maxSpending`` the whole budget
scales together.

A line's survivor share defaults to the case's survivor percentage, except for household housing
costs (rent, property tax, insurance, maintenance), which a survivor keeps paying in full.

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
from dataclasses import dataclass

import numpy as np

from . import utils as u


BUDGET_TYPES = ("core", "rent", "property tax", "insurance", "maintenance", "car", "travel", "care", "other")

# Costs of the home: a survivor keeps paying them in full unless the line says otherwise.
HOUSEHOLD_TYPES = frozenset({"rent", "property tax", "insurance", "maintenance"})

PROPERTY_TAX = "property tax"
RENT = "rent"


@dataclass(frozen=True)
class Budget:
    """Budget lines evaluated over the plan, in today's dollars.

    names, types -- one entry per active line
    amounts_ln   -- shape (lines, N_n): each line's amount by plan year
    total_n      -- shape (N_n,): the sum, the spending profile before normalization
    """

    names: tuple
    types: tuple
    amounts_ln: np.ndarray
    total_n: np.ndarray

    def by_type(self, *types):
        """Sum of the lines of the given types, by plan year (today's dollars)."""
        rows = [k for k, t in enumerate(self.types) if t in types]
        if not rows:
            return np.zeros(self.total_n.shape[0])
        return self.amounts_ln[rows].sum(axis=0)


def _last_year(end, thisyear, N_n):
    """Last calendar year of a line. end <= 0 counts back from the plan's last year (0 = that year)."""
    plan_end = thisyear + N_n - 1
    return plan_end + end if end <= 0 else end


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


def evaluate(budget_df, N_n, n_d, survivor_pct, thisyear):
    """
    Evaluate the active budget lines over the plan.

    Parameters
    ----------
    budget_df : pd.DataFrame
        Columns: active, name, type, year, end, amount, rate, survivor. `amount` is annual, in
        today's dollars, as of `year` (a year before the plan start counts from the plan start);
        `rate` is real growth above inflation (%); `survivor` is the percent kept after the first
        death (blank: the case's percentage, or 100 for housing costs).
    N_n : int
        Plan length in years.
    n_d : int
        Index of the first year after the first death (N_n for a single person, or when nobody
        dies within the plan).
    survivor_pct : float
        The case's survivor percentage (default for personal lines).
    thisyear : int
        Calendar year of plan index 0.

    Returns
    -------
    Budget
    """
    names, types, rows = [], [], []
    if not u.is_dataframe_empty(budget_df):
        for _, row in budget_df.iterrows():
            if not u.is_row_active(row):
                continue
            start = int(row["year"])
            last = _last_year(int(row["end"]), thisyear, N_n)
            ref = max(start, thisyear)
            amount, rate = float(row["amount"]), float(row["rate"])
            share = _survivor_share(row, survivor_pct)
            line = np.zeros(N_n)
            for n in range(N_n):
                cal = thisyear + n
                if ref <= cal <= last:
                    line[n] = amount * (1.0 + rate / 100.0) ** (cal - ref)
            if n_d < N_n:
                line[n_d:] *= share
            names.append(str(row["name"]))
            types.append(str(row["type"]).lower())
            rows.append(line)
    amounts = np.array(rows) if rows else np.zeros((0, N_n))
    return Budget(tuple(names), tuple(types), amounts, amounts.sum(axis=0) if rows else np.zeros(N_n))


def lines_left_out(budget_df, N_n, thisyear):
    """(name, reason) for each active line that adds nothing within the plan.

    A positive `end` is a calendar year: one before the line starts (a term such as 10 typed as
    `end`, say) leaves the line out, as does a `year` after the plan's last year.
    """
    out = []
    if u.is_dataframe_empty(budget_df):
        return out
    plan_end = thisyear + N_n - 1
    for _, row in budget_df.iterrows():
        if not u.is_row_active(row):
            continue
        start, end = int(row["year"]), int(row["end"])
        last = _last_year(end, thisyear, N_n)
        if start > plan_end:
            out.append((str(row["name"]), f"starts in {start}, after the plan ends in {plan_end}"))
        elif last < max(start, thisyear):
            out.append((str(row["name"]), f"ends in {last}, before it starts in {max(start, thisyear)}"))
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

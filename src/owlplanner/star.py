"""
New York School Tax Relief (STAR) credit for Owl retirement planner (fork).

The STAR credit (Tax Law sec. 606(eee)) is a refundable New York personal income tax credit,
paid in advance as a check or direct deposit around the time school taxes are due. A NY resident
who owns and lives in the home on July 1 of the year gets the Basic credit if the household's
income two years earlier was at most $500,000, or the larger Enhanced credit if an owner is 65 or
older on December 31 and that income is at most the Enhanced income standard. Amounts are set per
municipality and school district. Data and sources: data/property_tax_relief.toml.

This module turns the data into per-year amounts for a plan (``star_schedule``) and the credit a
given income path implies (``StarSchedule.implied_credit``). The Plan charges the credit against
the state income tax, which is what it is in law: the cash flow and the federal SALT deduction
follow from that, and the NY itemized deduction subtracts it from the real estate taxes paid
(IT-196 line 6; tax.ny.gov, "How to report your property tax credit").

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

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import toml

_TOML_PATH = Path(__file__).parent / "data" / "property_tax_relief.toml"

# Separator between municipality and school district in a district key.
_SEP = " / "


@lru_cache(maxsize=1)
def _load(toml_path: str = None) -> dict:
    with open(toml_path or str(_TOML_PATH), "r", encoding="utf-8") as f:
        return toml.load(f)


def program(state: str) -> dict:
    """The STAR table of *state* (an empty dict where the state has none)."""
    return _load().get(state or "", {})


def district_key(row: dict) -> str:
    """'City of Yonkers / Yonkers': the canonical name of a district row."""
    return f"{row['municipality']}{_SEP}{row['school_district']}"


def valid_districts(state: str) -> list:
    """Canonical district names defined for *state*, sorted."""
    return sorted(district_key(r) for r in program(state).get("districts", []))


def canonical_district(state: str, name: str) -> str:
    """Return the canonical spelling of district *name* in *state* ("" for none).

    *name* is "Municipality / School district" or, where it names one row only, the school
    district alone ("Yonkers"); case and surrounding spaces do not matter.
    """
    name = (name or "").strip()
    if not name:
        return ""
    rows = program(state).get("districts", [])
    if not rows:
        raise ValueError(f"School district '{name}' given, but no STAR data for state '{state or 'none'}'.")
    want = name.lower()
    exact = [r for r in rows if district_key(r).lower() == want]
    if exact:
        return district_key(exact[0])
    by_district = [r for r in rows if r["school_district"].lower() == want]
    if len(by_district) == 1:
        return district_key(by_district[0])
    if by_district:
        options = ", ".join(f"'{district_key(r)}'" for r in by_district)
        raise ValueError(f"School district '{name}' lies in several municipalities: name one of {options}.")
    raise ValueError(
        f"Unknown school district '{name}' for {state}. Use 'Municipality / School district' as listed in "
        "data/property_tax_relief.toml (Westchester and New York City so far)."
    )


def _district_row(state: str, key: str) -> dict:
    for r in program(state).get("districts", []):
        if district_key(r) == key:
            return r
    raise ValueError(f"Unknown school district '{key}' for {state}.")


@dataclass(frozen=True)
class StarSchedule:
    """Per-year STAR amounts for a plan (nominal $).

    Attributes
    ----------
    basic_n     -- Basic credit where the household could receive STAR (NY resident owner in a
                   district with data), else 0
    enhanced_n  -- Enhanced credit in those years where an owner meets the age test, else 0
    limit_n     -- Enhanced income standard of the benefit year
    basic_limit -- Basic credit income limit
    lag         -- years between the income tested and the benefit year
    """

    basic_n: np.ndarray
    enhanced_n: np.ndarray
    limit_n: np.ndarray
    basic_limit: float
    lag: int

    @property
    def active(self) -> bool:
        return bool(np.any(self.basic_n > 0))

    def tested_income(self, income_n, prior) -> np.ndarray:
        """Income each benefit year is tested on: income_n shifted by lag, prior before the plan."""
        income_n = np.asarray(income_n, dtype=float)
        N_n = len(self.basic_n)
        out = np.zeros(N_n)
        prior = list(prior) + [0.0] * self.lag
        for n in range(N_n):
            m = n - self.lag
            out[n] = income_n[m] if m >= 0 else float(prior[n])
        return out

    def implied_credit(self, income_n, prior) -> np.ndarray:
        """The credit per year (nominal $) that an income path implies.

        income_n: STAR income of each plan year; prior: income of the *lag* years before the plan,
        oldest first.
        """
        inc = self.tested_income(income_n, prior)
        basic_ok = (self.basic_n > 0) & (inc <= self.basic_limit)
        enh_ok = basic_ok & (self.enhanced_n > 0) & (inc <= self.limit_n)
        return np.where(enh_ok, self.enhanced_n, np.where(basic_ok, self.basic_n, 0.0))


def empty_schedule(N_n: int) -> StarSchedule:
    z = np.zeros(N_n)
    return StarSchedule(z, z.copy(), z.copy(), 0.0, 2)


def _income_limits(data: dict, year_n, gamma_n) -> np.ndarray:
    """Enhanced income standard per plan year: the data years as given, later years indexed."""
    years = [int(y) for y in data["enhanced_limit_years"]]
    amounts = [float(a) for a in data["enhanced_limit_amounts"]]
    last_year, last = years[-1], amounts[-1]
    year0 = int(year_n[0])
    # Inflation from the last data year, read off the plan's own path (from year 0 when that year
    # lies before the plan: the data then needs an update, and the plan starts from its last amount).
    n_last = min(max(last_year - year0, 0), len(year_n) - 1)
    out = np.zeros(len(year_n))
    for n, y in enumerate(year_n):
        y = int(y)
        if y in years:
            out[n] = amounts[years.index(y)]
        elif y < years[0]:
            out[n] = amounts[0]
        else:
            out[n] = last * float(gamma_n[n]) / float(gamma_n[n_last])
    # The standard never decreases (RPTL sec. 425(4)(b)(i)(D)).
    return np.maximum.accumulate(out)


def _enhanced_age_ok(year_n, yobs, horizons, n_d, i_d, age, survivor_age) -> np.ndarray:
    """Years where an owner meets the Enhanced age test (December 31 of the year).

    Both spouses are taken as owners living in the home. After the first death, a survivor at
    least *survivor_age* on December 31 of the year of the death keeps an Enhanced credit the
    deceased spouse's age had allowed; a younger one waits for their own 65 (tax.ny.gov, STAR
    eligibility, "Surviving spouse eligibility"; Tax Law sec. 606(eee)(4)(A)(i)).
    """
    N_n = len(year_n)
    N_i = len(yobs)
    year_n = np.asarray(year_n, dtype=int)
    ok = np.zeros(N_n, dtype=bool)
    for n in range(N_n):
        for i in range(N_i):
            if n < horizons[i] and year_n[n] - yobs[i] >= age:
                ok[n] = True
    if N_i == 2 and 0 < n_d < N_n:
        i_s = 1 - i_d
        # The deceased's last plan year is the year of the death.
        death_year = year_n[n_d - 1]
        keeps = death_year - yobs[i_d] >= age and death_year - yobs[i_s] >= survivor_age
        for n in range(n_d, N_n):
            if keeps and n < horizons[i_s]:
                ok[n] = True
    return ok


def star_schedule(states_n, districts_n, owner_n, property_tax_n, year_n, gamma_n, yobs, horizons, n_d, i_d):
    """Per-year STAR amounts for a plan.

    states_n, districts_n -- state and canonical school district of each plan year
    owner_n         -- years in which the household owns its home (it pays property tax)
    property_tax_n  -- property tax paid per year (nominal $): the credit cannot exceed the school
                       taxes, of which it is an upper bound
    year_n, gamma_n -- calendar years and cumulative inflation of the plan
    yobs, horizons, n_d, i_d -- birth years, years alive, first death year and who dies first
    """
    N_n = len(year_n)
    basic = np.zeros(N_n)
    enhanced = np.zeros(N_n)
    limit = np.zeros(N_n)
    basic_limit, lag = 0.0, 2
    year_n = np.asarray(year_n)
    for state in sorted(set(s for s, d in zip(states_n, districts_n, strict=True) if d)):
        data = program(state)
        basic_limit = float(data["basic_income_limit"])
        lag = int(data.get("income_lag_years", 2))
        growth = 1.0 + float(data.get("credit_growth_pct", 0.0)) / 100.0
        base_year = int(data["amounts_year"])
        age_ok = _enhanced_age_ok(year_n, yobs, horizons, n_d, i_d, int(data["enhanced_age"]),
                                  int(data["surviving_spouse_age"]))
        lim = _income_limits(data, year_n, gamma_n)
        for n in range(N_n):
            if states_n[n] != state or not districts_n[n] or not owner_n[n]:
                continue
            row = _district_row(state, districts_n[n])
            grow = growth ** max(0, int(year_n[n]) - base_year)
            cap = max(0.0, float(property_tax_n[n]))
            basic[n] = min(float(row["basic"]) * grow, cap)
            if age_ok[n]:
                enhanced[n] = max(min(float(row["enhanced"]) * grow, cap), basic[n])
            limit[n] = lim[n]
    return StarSchedule(basic, enhanced, limit, basic_limit, lag)

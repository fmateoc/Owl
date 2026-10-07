"""
Recurring housing costs: rent, property tax, insurance, maintenance, HOA fees.

An optional HFP "Housing" sheet holds one row per recurring cost. The amounts are
household-level and are not scaled at the first death (as for debts). Nothing about
housing is optimized here: the ledger is exogenous data, subtracted in the cash flow
like debt payments, and the only tax rule that reads it is the NJ property tax
deduction (tax_state / plan).

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
from datetime import date

import numpy as np

from . import utils as u


# Row types. Only "property tax" and "rent" feed the NJ property tax deduction;
# every type is a cash outflow.
HOUSING_TYPES = ("rent", "property tax", "insurance", "maintenance", "other")

PROPERTY_TAX = "property tax"
RENT = "rent"


def _active_rows(housing_df):
    """Yield (start_year, end_year, amount, rate, type) for each active housing row."""
    for _, row in housing_df.iterrows():
        if not u.is_row_active(row):
            continue
        start_year = int(row["year"])
        end_year = int(row["end"])
        yield start_year, end_year, float(row["amount"]), float(row["rate"]), str(row["type"]).lower()


def _end_year_paid(end, thisyear, N_n):
    """Last calendar year the cost is paid. end<=0 counts from the plan end (0 = last year)."""
    plan_end = thisyear + N_n - 1
    return plan_end + end if end <= 0 else end


def get_housing_arrays(housing_df, N_n, gamma_n, thisyear=None):
    """
    Process housing_df into nominal per-year cost arrays.

    Parameters:
    -----------
    housing_df : pd.DataFrame
        DataFrame with columns: active, name, type, year, end, amount, rate.
        `amount` is the annual cost in `year` dollars; `rate` is real growth above
        inflation (%). A `year` before the plan start is read as plan-start dollars
        (as for Fixed Assets); inflation is then applied only from the plan start.
    N_n : int
        Number of years in the plan (length of output arrays)
    gamma_n : ndarray or None
        Cumulative inflation multiplier array (length N_n+1) from gen_gamma_n().
    thisyear : int, optional
        Starting year of the plan (defaults to date.today().year).

    Returns:
    --------
    tuple of np.ndarray
        Three arrays of length N_n (nominal $):
        - total_n: all housing costs
        - property_tax_n: rows of type "property tax"
        - rent_n: rows of type "rent"
    """
    if thisyear is None:
        thisyear = date.today().year

    total_n = np.zeros(N_n)
    property_tax_n = np.zeros(N_n)
    rent_n = np.zeros(N_n)

    if u.is_dataframe_empty(housing_df):
        return total_n, property_tax_n, rent_n

    for start_year, end_raw, amount, rate, htype in _active_rows(housing_df):
        last_paid = _end_year_paid(end_raw, thisyear, N_n)
        # Amount is in `year` dollars; a past `year` is read as plan-start dollars.
        ref_year = max(thisyear, start_year)
        ref_n = ref_year - thisyear
        if ref_n >= N_n or last_paid < thisyear:
            continue
        for n in range(N_n):
            cal = thisyear + n
            if cal < start_year or cal > last_paid:
                continue
            years_from_ref = cal - ref_year
            nominal = amount * (1.0 + rate / 100.0) ** years_from_ref
            if gamma_n is not None:
                nominal *= gamma_n[n] / gamma_n[ref_n]
            total_n[n] += nominal
            if htype == PROPERTY_TAX:
                property_tax_n[n] += nominal
            elif htype == RENT:
                rent_n[n] += nominal

    return total_n, property_tax_n, rent_n

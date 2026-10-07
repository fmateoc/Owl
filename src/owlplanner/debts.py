"""
Debt management and calculation module.

This module provides functions for handling debts including mortgage calculations,
loan amortization, and debt-related financial planning.

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
import numpy as np
from datetime import date

from . import utils as u


def _payoff_year(debt, start_year, term):
    """Year the remaining balance is paid in full, or None.

    The optional `payoff` column (0 or absent = none) ends a loan before its term, e.g. in the
    year the house it finances is sold. A year at or after the end of the term changes nothing.
    """
    if "payoff" not in debt.index:
        return None
    try:
        payoff = int(debt["payoff"])
    except (TypeError, ValueError):
        return None
    if payoff <= 0 or not start_year <= payoff < start_year + term:
        return None
    return payoff


def _active_loans(debts_df):
    """Yield (start_year, term, end_year, principal, rate, payoff) for each active loan row.

    Regular payments run for start_year <= year < end_year. With a payoff year, end_year is that
    year, in which the balance left after the regular payments is paid instead (payoff_amount).
    """
    for _, debt in debts_df.iterrows():
        if not u.is_row_active(debt):
            continue
        start_year = int(debt["year"])
        term = int(debt["term"])
        payoff = _payoff_year(debt, start_year, term)
        end_year = payoff if payoff is not None else start_year + term
        yield start_year, term, end_year, float(debt["amount"]), float(debt["rate"]), payoff


def payoff_amount(principal, annual_rate, term_years, start_year, payoff):
    """Balance paid in the payoff year: what is left after the regular payments before it."""
    return calculate_remaining_balance(principal, annual_rate, term_years, payoff - start_year)


def calculate_monthly_payment(principal, annual_rate, term_years):
    """
    Calculate monthly payment for an amortizing loan. This is a constant payment amount for a fixed-rate loan.
    monthly payment = principal * (monthly_rate * (1 + monthly_rate)**num_payments) /
                      ((1 + monthly_rate)**num_payments - 1)
    where monthly_rate = annual_rate / 100.0 / 12.0 and num_payments = term_years * 12.0.

    This formula is derived from the formula for the present value of an annuity.

    Parameters:
    -----------
    principal : float
        Original loan amount
    annual_rate : float
        Annual interest rate as a percentage (e.g., 4.5 for 4.5%)
    term_years : int
        Loan term in years

    Returns:
    --------
    float
        Monthly payment amount
    """
    if term_years <= 0 or annual_rate < 0 or principal <= 0:
        return 0.0

    monthly_rate = annual_rate / 100.0 / 12.0
    num_payments = term_years * 12
    fac = (1 + monthly_rate) ** num_payments

    if monthly_rate == 0:
        return principal / num_payments

    payment = principal * (monthly_rate * fac) / (fac - 1)

    return payment


def calculate_annual_payment(principal, annual_rate, term_years):
    """
    Calculate annual payment for an amortizing loan.

    Parameters:
    -----------
    principal : float
        Original loan amount
    annual_rate : float
        Annual interest rate as a percentage
    term_years : int
        Loan term in years

    Returns:
    --------
    float
        Annual payment amount
    """
    return 12 * calculate_monthly_payment(principal, annual_rate, term_years)


def calculate_remaining_balance(principal, annual_rate, term_years, years_elapsed):
    """
    Calculate remaining balance on a loan after a given number of years.

    Parameters:
    -----------
    principal : float
        Original loan amount
    annual_rate : float
        Annual interest rate as a percentage
    term_years : int
        Original loan term in years
    years_elapsed : float
        Number of years since loan origination

    Returns:
    --------
    float
        Remaining balance
    """
    if years_elapsed <= 0:
        return principal

    if term_years <= 0 or years_elapsed >= term_years:
        return 0.0

    monthly_rate = annual_rate / 100.0 / 12.0
    fac = 1 + monthly_rate
    num_payments = term_years * 12
    payments_made = int(years_elapsed * 12)
    if num_payments <= 0:
        return 0.0

    if monthly_rate == 0:
        return principal * (1 - payments_made / num_payments)

    remaining = principal * (fac**num_payments - fac**payments_made) / (fac**num_payments - 1)

    return max(0.0, remaining)


def get_debt_payments_for_year(debts_df, year):
    """
    Calculate total debt payments (principal + interest) for a given year.

    Parameters:
    -----------
    debts_df : pd.DataFrame
        DataFrame with columns: name, type, year, term, amount, rate (and optional payoff)
    year : int
        Year for which to calculate payments

    Returns:
    --------
    float
        Total annual debt payments for the year
    """
    if u.is_dataframe_empty(debts_df):
        return 0.0

    total_payments = 0.0

    for start_year, term, end_year, principal, rate, payoff in _active_loans(debts_df):
        if start_year <= year < end_year:
            total_payments += calculate_annual_payment(principal, rate, term)
        elif year == payoff:
            total_payments += payoff_amount(principal, rate, term, start_year, payoff)

    return total_payments


def get_debt_balances_for_year(debts_df, year):
    """
    Calculate total remaining debt balances at the end of a given year.

    Parameters:
    -----------
    debts_df : pd.DataFrame
        DataFrame with columns: name, type, year, term, amount, rate (and optional payoff)
    year : int
        Year for which to calculate balances

    Returns:
    --------
    float
        Total remaining debt balances at end of year
    """
    if u.is_dataframe_empty(debts_df):
        return 0.0

    total_balance = 0.0

    for start_year, term, end_year, principal, rate, _payoff in _active_loans(debts_df):
        if start_year <= year < end_year:
            years_elapsed = year - start_year + 1
            total_balance += calculate_remaining_balance(principal, rate, term, years_elapsed)

    return total_balance


def get_debt_payments_array(debts_df, N_n, thisyear=None):
    """
    Process debts_df to provide a single array of length N_n containing
    all annual payments made for each year of the plan.

    Parameters:
    -----------
    debts_df : pd.DataFrame
        DataFrame with columns: name, type, year, term, amount, rate (and optional payoff)
    N_n : int
        Number of years in the plan (length of output array)
    thisyear : int, optional
        Starting year of the plan (defaults to date.today().year).
        Array index 0 corresponds to thisyear, index 1 to thisyear+1, etc.

    Returns:
    --------
    np.ndarray
        Array of length N_n with annual debt payments for each year.
        payments_n[0] = payments for thisyear,
        payments_n[1] = payments for thisyear+1, etc.
    """
    if thisyear is None:
        thisyear = date.today().year

    if u.is_dataframe_empty(debts_df):
        return np.zeros(N_n)

    payments_n = np.zeros(N_n)

    for start_year, term, end_year, principal, rate, payoff in _active_loans(debts_df):
        annual_payment = calculate_annual_payment(principal, rate, term)
        for n in range(N_n):
            if start_year <= thisyear + n < end_year:
                payments_n[n] += annual_payment
            elif thisyear + n == payoff:
                payments_n[n] += payoff_amount(principal, rate, term, start_year, payoff)

    return payments_n


def get_debt_balances_array(debts_df, N_n, thisyear=None):
    """
    Process debts_df to provide a single array of length N_n containing
    the remaining debt balance at the start of each year of the plan.

    Parameters:
    -----------
    debts_df : pd.DataFrame
        DataFrame with columns: name, type, year, term, amount, rate (and optional payoff)
    N_n : int
        Number of years in the plan (length of output array)
    thisyear : int, optional
        Starting year of the plan (defaults to date.today().year).
        Array index 0 corresponds to thisyear, index 1 to thisyear+1, etc.

    Returns:
    --------
    np.ndarray
        Array of length N_n with the remaining debt balance at the start
        of each year. balances_n[0] = balance at the start of thisyear,
        balances_n[1] = balance at the start of thisyear+1, etc.
    """
    if thisyear is None:
        thisyear = date.today().year

    if u.is_dataframe_empty(debts_df):
        return np.zeros(N_n)

    balances_n = np.zeros(N_n)

    for start_year, term, end_year, principal, rate, payoff in _active_loans(debts_df):
        for n in range(N_n):
            year = thisyear + n
            # The balance is still owed at the start of the payoff year.
            if start_year <= year < end_year or year == payoff:
                years_elapsed = year - start_year
                balances_n[n] += calculate_remaining_balance(principal, rate, term, years_elapsed)

    return balances_n


def get_remaining_debt_balance(debts_df, N_n, thisyear=None):
    """
    Calculate total remaining debt balance at the end of the plan horizon.
    Returns the sum of all remaining balances for loans that haven't been
    fully paid off by the end of the plan.

    Parameters:
    -----------
    debts_df : pd.DataFrame
        DataFrame with columns: name, type, year, term, amount, rate (and optional payoff)
    N_n : int
        Number of years in the plan
    thisyear : int, optional
        Starting year of the plan (defaults to date.today().year)

    Returns:
    --------
    float
        Total remaining debt balance at the end of the plan horizon.
        Returns 0.0 if all loans are paid off or if no loans are active.
    """
    if thisyear is None:
        thisyear = date.today().year

    if u.is_dataframe_empty(debts_df):
        return 0.0

    end_year = thisyear + N_n - 1
    total_balance = 0.0

    for start_year, term, loan_end_year, principal, rate, _payoff in _active_loans(debts_df):
        if start_year <= end_year < loan_end_year:
            years_elapsed = end_year - start_year + 1
            total_balance += calculate_remaining_balance(principal, rate, term, years_elapsed)

    return total_balance

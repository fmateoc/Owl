"""
Spending profile generation utilities.

This module implements spending profile time series: flat and smile (retirement
spending) profiles, with survivor fraction and normalization.

One cosine period of the smile covers a fixed number of years (``SMILE_SPAN``) from
the start of the smile, not the length of the plan. A longer life therefore appends the
late-life rise instead of stretching the go-go years and moving the dip later. Here the
start is ``delay`` years after the plan's first year (negative: the smile started before
the plan), or ``t`` gives the years into the smile directly. ``Plan.setSpendingProfile``
reads them from an age (``smile_start_age``): the younger spouse's, then the survivor's after
the first death, so the curve stays at the same ages when the plan is run again in a later
year.

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

# One cosine period of the smile, in years, measured from the start of the smile.
# Independent of the plan's length: at N_n = SMILE_SPAN + 1 and delay = 0 the curve
# is exactly the old plan-stretched one (span = N_n - 1); on a longer horizon the
# early years are unchanged and the extra years take the late-life rise.
SMILE_SPAN = 30


def gen_spending_profile(profile, fraction, n_d, N_n, dip=15, increase=12, delay=0, span=None, t=None):
    """
    Generate spending profile time series.

    Value is reduced to fraction starting in year n_d (after passing of
    shortest-lived spouse). Series is unadjusted for inflation.

    Parameters
    ----------
    profile : str
        'flat' or 'smile'
    fraction : float
        Survivor fraction (0–1) applied from year n_d onward
    n_d : int
        Year index when survivor reduction begins
    N_n : int
        Plan horizon (number of years)
    dip : float
        Percent dip for smile profile (cosine amplitude)
    increase : float
        Percent linear increase for smile profile (over one ``span``)
    delay : int
        Years from the plan's first year to the start of the smile; negative when the smile
        started before the plan (its earlier part is then not in the plan)
    span : float, optional
        Length of one cosine period in years. Default ``SMILE_SPAN``. Pass
        ``N_n - 1 - delay`` to recover the old plan-stretched curve.
    t : array-like, optional
        Years into the smile for each plan year (length N_n; 0 before it starts). Replaces
        ``delay`` when given: ``Plan.setSpendingProfile`` reads it from an age, the younger
        spouse's and, after the first death, the survivor's.

    Returns
    -------
    xi : ndarray
        Length N_n, spending profile unadjusted for inflation
    """
    xi = np.ones(N_n)
    if profile == "flat":
        if n_d < N_n:
            xi[n_d:] *= fraction
    elif profile == "smile":
        S = float(SMILE_SPAN if span is None else span)
        if S <= 0:
            raise ValueError(f"Smile span {S} must be positive.")
        a = dip / 100
        b = increase / 100
        # Years since the smile starts. Before ``delay`` the profile is held at the
        # smile's opening value (the go-go level).
        if t is None:
            t = np.maximum(np.arange(N_n, dtype=float) - delay, 0.0)
        else:
            t = np.maximum(np.asarray(t, dtype=float), 0.0)
            if t.shape != (N_n,):
                raise ValueError(f"Smile years t must have length {N_n}.")
        # One cosine period over [0, S]; after that freeze at the period's end
        # (cos = +1) and keep the linear rise, which is the late-life part.
        cos_term = np.where(t <= S, np.cos((2 * np.pi / S) * t), 1.0)
        xi = 1.0 + a * cos_term + (b / S) * t
        neutralSum = N_n
        if n_d < N_n:
            neutralSum -= (1 - fraction) * (N_n - n_d)
            xi[n_d:] *= fraction
        xi *= neutralSum / xi.sum()
    else:
        raise ValueError(f"Unknown profile type '{profile}'.")

    return xi

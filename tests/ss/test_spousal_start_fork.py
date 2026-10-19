"""
Fork fixes to ``compute_social_security_benefits``'s spousal add-on, found by the
earnings-test no-op grid (Phase 5 steps 1-2 review, 2026-10-18). Both are on stock
upstream ``dev`` too (draft issue ``fork-notes/issue-spousal-start.md``); when upstream
fixes them, take theirs and drop these tests if they duplicate upstream's.

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

import numpy as np
import pytest

from owlplanner import socialsecurity as ss

THISYEAR = 2026


def _run(pias, ages, yobs, mobs, horizons=(25, 25)):
    zeta, _ = ss.compute_social_security_benefits(
        np.array(pias, dtype=np.int32),
        np.array(ages, dtype=np.float64),
        np.array(yobs, dtype=np.int64),
        np.array(mobs, dtype=np.int64),
        np.array([15, 15], dtype=np.int64),
        np.array(horizons, dtype=np.int64),
        2,
        int(max(horizons)),
        thisyear=THISYEAR,
    )
    return zeta


def test_spousal_paid_all_year_when_both_claimed_before_the_plan():
    """Both spouses collecting before 2026: 2026 has twelve spousal checks, not a
    fraction of them (the partial first year applied to a start before the plan).

    Person 1, born 1962-05-15, claims at 62 → 62y1m (June 2024, the later claim):
      own      800 x 0.704167 x 12  = 6,760.00
      spousal  700 x 0.654167 x 12  = 5,495.00   (0.5 x 3,000 - 800 = 700)
    """
    zeta = _run([3000, 800], [62.0, 62.0], [1961, 1962], [1, 5])
    own = 800 * (0.8 - 0.05 * 23 / 12)
    spousal = 700 * (0.75 - 0.05 * 23 / 12)
    assert zeta[1, 0] == pytest.approx(12 * (own + spousal))


@pytest.mark.parametrize("swap", [False, True])
def test_spousal_start_does_not_depend_on_person_order(swap):
    """The later claimer's age is reset (62.0 → 62y1m) before the spousal start is read.

    Auxiliary: PIA $1,000, born 1964-03-15, claims 62y1m (April 2026). Worker: PIA
    $3,000, born 1966-05-15, enters 62.0 → 62y1m (June 2028). The spousal add-on
    ($500) starts June 2028 at the auxiliary's 64y3m: factor 1 - (1/12) x 2.75 =
    0.770833; checks July-December. 2028:
      own      1,000 x 0.704167 x 12  = 8,450.00
      spousal    500 x 0.770833 x 6   = 2,312.50
    """
    pias, ages, yobs, mobs = [1000, 3000], [62.0 + 1 / 12, 62.0], [1964, 1966], [3, 5]
    aux = 0
    if swap:
        pias, ages, yobs, mobs = pias[::-1], ages[::-1], yobs[::-1], mobs[::-1]
        aux = 1
    zeta = _run(pias, ages, yobs, mobs)
    assert zeta[aux, 2] == pytest.approx(8450.0 + 500 * (1 - 2.75 / 12) * 6)

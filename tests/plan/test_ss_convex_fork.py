"""
Fork: withSSTaxability="convex" (upstream #193, branch ss-convex) and the fork's loop parameters.

The SS cap probe re-solves the plan once per year it tries, warm-started from the best plan's loop
quantities. Upstream's list covers its own quantities; the fork adds its _SC_PARAMS (NJ exclusion
free set, NY recapture, itemizing branches and floors), which otherwise restart cold in every probe
(on the fork's NJ probe couple: 25-37% of the solve time, same plans).

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

from unittest.mock import patch

from owlplanner import Plan


def _ny_couple():
    p = Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "ss-convex-fork", verbose=False)
    p.setSpendingProfile("flat")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=[[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2)
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    p.setStateTax("NY")
    return p


def test_cap_probe_warm_starts_the_fork_loop_parameters():
    warms = []
    orig = Plan._ssCapProbe

    def spy(self, objective, myoptions, run):
        def wrapped(seed, warm=None):
            if warm is not None:
                warms.append(set(warm))
            return run(seed, warm)

        return orig(self, objective, myoptions, wrapped)

    p = _ny_couple()
    with patch.object(Plan, "_ssCapProbe", spy):
        p.solve("maxBequest", options={"noRothConversions": "None", "netSpending": 90,
                                       "withSSTaxability": "convex"})
    assert p.caseStatus == "solved"
    assert warms, "the cap probe ran no probe"
    fork_params = set(Plan._SC_PARAMS) - {"Psi_n"}
    for keys in warms:
        assert fork_params <= keys, sorted(fork_params - keys)
        assert "Psi_n" not in keys  # "convex" sets SS by region, not from a carried Psi_n

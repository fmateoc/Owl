"""
Repro for the 2026 QCD limit (fork-notes/issue-qcd-limit.md), on stock upstream `dev`.

IRS Notice 2025-67 sets the 2026 limit under IRC 408(d)(8)(A) at $111,000;
tax_federal.qcdLimit has $115,000. Owl therefore accepts a 2026 QCD between the
two, through the same HFP path a user takes (the `QCD` column, read by
setContributions), and excludes it from income.

Run in 2026 (the plan starts in the current year):
    PYTHONPATH=<checkout>/src python issue-qcd-limit-repro.py
"""

from datetime import date

import owlplanner as owl
from owlplanner import tax_federal as tx

print("owlplanner from", owl.__file__)
thisyear = date.today().year
assert thisyear == 2026, "the repro checks the 2026 figure; run it in 2026"

print("tx.qcdLimit:", tx.qcdLimit)
print("tx.qcdLimitForYear(2026):", f"{tx.qcdLimitForYear(2026):,.0f}")

# A single retiree well past 70 1/2 (the plan of tests/plan/test_qcd.py).
p = owl.Plan(["Alice"], ["1950-01-15"], [96], "QCD limit repro", verbose=False)
p.zeroWagesAndContributions()
p.setAccountBalances(taxable=[300], taxDeferred=[1_500], taxFree=[200])
p.setAllocationRatios("individual", generic=[[[60, 20, 20, 0], [60, 20, 20, 0]]])
p.setRates("user", values=[6.0, 4.0, 3.0, 2.5])
p.setSpendingProfile("flat", 60)
p.setSocialSecurity([2_000], [70])

for amount in (111_000, 113_000, 115_000, 115_001):
    df = p.timeLists["Alice"]
    df.loc[df["year"] == 2026, "QCD"] = amount
    try:
        p.setContributions()
        print(f"QCD of ${amount:,} in 2026: accepted (qcd_in[0, 0] = {p.qcd_in[0, 0]:,.0f})")
    except ValueError as e:
        print(f"QCD of ${amount:,} in 2026: refused: {e}")

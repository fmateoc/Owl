"""A mortgage outlives the sale of the home it financed.

Usage (repository root): python fork-notes/model-review/debt_payoff_repro.py [payoff]
With `payoff`, the loan row gets payoff = the sale year (needs the Debts `payoff` column).
Output for the draft issue fork-notes/issue-debt-payoff.md.
"""
import sys

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond

p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "sale", verbose=False)
Y = int(p.year_n[0])
SALE = 10  # plan year of the sale
p.setSpendingProfile("flat")
p.setAccountBalances(taxable=[600, 600], taxDeferred=[750, 750], taxFree=[75, 75])
p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
p.setRates("conservative")
p.setSocialSecurity([3000, 2400], [70, 70])
home = dict(active=True, name="home", type="residence", year=Y, basis=800000.0, value=800000.0,
            rate=0.5, yod=Y + SALE, commission=6.0)
loan = dict(active=True, name="mtg", type="mortgage", year=Y, term=30, amount=640000.0, rate=6.5)
if len(sys.argv) > 1 and sys.argv[1] == "payoff":
    loan["payoff"] = Y + SALE
p.houseLists["Fixed Assets"] = cond(pd.DataFrame([home]), "Fixed Assets")
p.houseLists["Debts"] = cond(pd.DataFrame([loan]), "Debts")
p.solve("maxSpending", options={"bequest": 0, "withMedicare": "None", "withSSTaxability": 0.85})

after = p.debt_payments_n[SALE:]
print("status", p.caseStatus, f"spending basis {p.basis:,.0f}")
proceeds = p.fixed_assets_tax_free_n[SALE] + p.fixed_assets_capital_gains_n[SALE]
print(f"home sold in {Y + SALE}; proceeds {proceeds:,.0f}")
print(f"balance owed at the start of {Y + SALE}: {p.fixed_assets_debt_balances_remaining_n[SALE]:,.0f}")
print(f"debt payments from {Y + SALE} on: {after.sum():,.0f} nominal, in {np.count_nonzero(after)} year(s)")

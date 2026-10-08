# Draft upstream issue (mdlacasse/Owl): a mortgage outlives the sale of the home it financed

Status: **filed as #173 and implemented upstream with a different design** (`431aee0`, merged into
the fork 2026-10-08; the fork's `payoff` column is dropped). Debts gain an optional `property` column
naming a residence or real estate in Fixed Assets; the loan is paid off in the year that property is
sold (balance owed at the start of the sale year, paid that year), and a link that can't be honored
is a configuration error. The maintainer's reason: a typed year drifts out of step with a `yod`
counted back from the plan end when the horizon changes. Our payoff mechanics were kept. With the
link, this repro gives the same numbers as our `payoff` did (on 2026-10-08: spending basis 158,637
to 161,220, $542,567 paid in 2036; $16/yr lower than below because the plan starts "today").
The text below is the issue as filed; the patch is kept for the record only.

**Title:** Debts: optional `payoff` year, so that a loan can end when the home it finances is sold

---

A `Debts` row pays its amortized payment every year from `year` to `year + term`, whatever happens
to the asset it financed. When a `residence` in `Fixed Assets` is sold within the plan (`yod`), the
mortgage keeps being paid for the rest of its term, after the sale proceeds have reached savings.
In reality the balance is paid off at closing. Nothing in the `Debts` sheet can express that: a
shorter `term` changes the payment, and the payments can't be stopped.

It matters for the cases where a sale is planned: downsizing, a move to another state (now that
`moves` exist), selling before entering care. Any plan that sells a mortgaged home before the end of
the loan is affected.

**Repro** (stock `dev` `004c840`, from the repository root): couple born 1964, $800k home bought in
the plan's first year with a $640k 30-year mortgage at 6.5%, sold in plan year 10 (`yod` = 2036).
Script: `fork-notes/model-review/debt_payoff_repro.py` in our fork; condensed here (the full script
also prints the first two lines of the output below).

```python
import numpy as np, pandas as pd, owlplanner as owl
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond

p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "sale", verbose=False)
Y, SALE = int(p.year_n[0]), 10
p.setSpendingProfile("flat")
p.setAccountBalances(taxable=[600, 600], taxDeferred=[750, 750], taxFree=[75, 75])
p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
p.setRates("conservative")
p.setSocialSecurity([3000, 2400], [70, 70])
p.houseLists["Fixed Assets"] = cond(pd.DataFrame([dict(active=True, name="home", type="residence", year=Y,
    basis=800000.0, value=800000.0, rate=0.5, yod=Y + SALE, commission=6.0)]), "Fixed Assets")
p.houseLists["Debts"] = cond(pd.DataFrame([dict(active=True, name="mtg", type="mortgage", year=Y, term=30,
    amount=640000.0, rate=6.5)]), "Debts")
p.solve("maxSpending", options={"bequest": 0, "withMedicare": "None", "withSSTaxability": 0.85})
after = p.debt_payments_n[SALE:]
print(f"balance owed at the start of {Y + SALE}: {p.fixed_assets_debt_balances_remaining_n[SALE]:,.0f}")
print(f"debt payments from {Y + SALE} on: {after.sum():,.0f} nominal, in {np.count_nonzero(after)} year(s)")
```

Output on `dev`:

```
status solved spending basis 158,653
home sold in 2036; proceeds 1,041,861
balance owed at the start of 2036: 542,567
debt payments from 2036 on: 970,856 nominal, in 20 year(s)
```

The house is gone in 2036, but $48,543 a year is paid for 20 more years ($970,856 nominal) instead
of the $542,567 owed at the sale.

**Proposal:** an optional `payoff` column on `Debts`: the calendar year the remaining balance is paid
in full. That year the balance left after the regular payments (`calculate_remaining_balance` at
`payoff - year` years) is paid instead of the regular payment; nothing is paid after it, and the
balance is zero from then on (so the balance sheet and `remaining_debt_balance` follow). 0 or blank
means no payoff, and a year at or after the end of the term changes nothing, so every existing
workbook gives the same plan. For a sale, `payoff` = `yod`: the balance is owed at the start of the
sale year and paid that year, the year the proceeds arrive.

With the patch, the same plan with `payoff` = 2036:

```
status solved spending basis 161,236
home sold in 2036; proceeds 1,041,861
balance owed at the start of 2036: 542,567
debt payments from 2036 on: 542,567 nominal, in 1 year(s)
```

and without the column (or `payoff` = 0) the output is identical to `dev` (spending basis 158,653).
Here the payoff raises the spending basis by $2,583/yr: the loan's 6.5% is above the conservative
rates the savings earn after the sale.

**Patch** (`issue-debt-payoff.patch`, 9 files, +209/-30):

- `debts.py`: `_active_loans` yields the payoff year; regular payments stop at it; the payoff year
  pays `payoff_amount()`; the start-of-year balance array keeps the balance in the payoff year
  (it is still owed that January) and is zero after.
- `hfp_io.py`: `payoff` added to the Debts columns as an optional one (`_optionalHouseItems`), so a
  workbook without it loads (read as 0); integer column.
- `export.py` (sheet format), `ui/Financial_Profile.py` (editor column), `cli/cmd_explain.py`
  (`payoff_year` in the debts list when set), `ui/Documentation.py`, `info/PARAMETERS.md`,
  `info/modeling-capabilities.md`.
- `tests/assets/test_debt_payoff.py`: 12 tests (no column = unchanged; 0 = none; the payoff pays the
  balance and stops; the payoff equals the start-of-year balance; no balance left at the plan end;
  payoff at or after the term changes nothing; payoff in the start year pays the principal; a plan
  that pays off; HFP round trip with the column; an HFP without the column loads).

Verification on `dev` `004c840` with the patch alone: full suite 2721 passed, 1 skipped
(`dev` alone: 2709 passed, 1 skipped; the 12 new tests are the difference); flake8 clean on the changed files.

Not in the patch: linking the loan to the asset automatically (a `payoff` of "at the asset's `yod`").
The explicit year keeps `Debts` independent of `Fixed Assets`, as it is now.

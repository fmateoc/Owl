# Draft upstream issue (mdlacasse/Owl): rates below 1% are read back from an HFP workbook as 100x

Status: draft, 2026-10-08, ready to file. Repro run on stock `dev` `156d812`; patch
`fork-notes/issue-hfp-percent-rates.patch` verified on the same commit (see the end).

**Title:** HFP: a Debts or Fixed Assets rate below 1 (e.g. 0.5% real growth) is read as 50% after a save and reload

---

When `readHFP` reads the Debts and Fixed Assets sheets, `conditionDebtsAndFixedAssetsDF(...,
convert_decimal_pct=True)` multiplies every `rate` and `commission` between 0 and 1 by 100, on the
assumption that such a value is an Excel fraction (0.045 shown as 4.5%). But the sheets hold
percent numbers (every example workbook stores rates as plain numbers in General format: 4.5, 0,
5), and the documentation suggests exactly such small values for a residence: "real house price
appreciation of roughly 0–0.5%/year". A 0.5 typed there, or a 0.9% loan, becomes 50% or 90%.
`saveHFP` writes the value as entered, so a plan saved and reloaded changes.

**Repro** (stock `dev` `156d812`):

```python
import numpy as np, pandas as pd, owlplanner as owl
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond

p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "rate", verbose=False)
Y = int(p.year_n[0])
p.houseLists["Fixed Assets"] = cond(pd.DataFrame([dict(active=True, name="home", type="residence", year=Y,
    basis=500000.0, value=800000.0, rate=0.5, yod=0, commission=6.0)]), "Fixed Assets")
p.houseLists["Debts"] = cond(pd.DataFrame([dict(active=True, name="mtg", type="mortgage", year=Y, term=30,
    amount=400000.0, rate=0.9)]), "Debts")
p.saveHFP("HFP_rate.xlsx", overwrite=True)
q = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "rate", verbose=False)
q.readHFP("HFP_rate.xlsx")
for label, plan in (("as entered", p), ("after save/read", q)):
    plan.setRates("conservative")
    plan.processDebtsAndFixedAssets()
    print(label, plan.houseLists["Fixed Assets"]["rate"].iloc[0], plan.houseLists["Debts"]["rate"].iloc[0],
          f"{plan.fixed_assets_bequest_value:,.0f}", f"{plan.debt_payments_n[0]:,.0f}")
```

Output (home rate, loan rate, home value at the end of the plan, annual loan payment):

```
as entered 0.5 0.9 2,066,105 15,219
after save/read 50.0 90.0 509,135,553,961 360,000
```

**Proposal:** convert only what is a fraction: cells that the workbook formats as a percentage.
`openpyxl` gives each cell's `number_format`; a cell shown as 4.50% holds 0.045 and has a `%` in
its format. Any other cell is read as typed, whatever its size.

**Patch** (`issue-hfp-percent-rates.patch`, 2 files):

- `hfp_io.py`: `_percentFormattedCells(finput, _pctCols)` lists, per sheet and column, the rows
  whose cell format contains `%` (read-only openpyxl; a file openpyxl cannot read, such as xls or
  ods, gives none, so its values are read as typed; an in-memory upload is rewound after).
  `_conditionHouseTables` multiplies those cells by 100 and no others, and no longer asks
  `conditionDebtsAndFixedAssetsDF` for the size-based conversion (the parameter stays, unused by
  the reader).
- `tests/config/test_hfp_percent_rates.py`: 4 tests (a 0.5 and a 0.9 survive a round trip;
  percent-formatted cells 4.50% and 6.00% read as 4.5 and 6; an in-memory upload, rewound;
  tables given as DataFrames read as typed). All four fail on `dev` and pass with the patch.

Verification on `dev` `156d812`: full suite 2763 passed, 1 skipped (2760 collected on `dev` alone, plus the 4 new tests); flake8 clean on the changed files.

Not handled: a percent-formatted cell in a workbook with blank rows inside a table, where pandas
and openpyxl could number rows differently (not checked). The person sheets have no rate columns.

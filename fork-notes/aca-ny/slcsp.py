"""Second-lowest-cost silver plan (SLCSP) in NY Rating Area 4, 2027, per county.

Inputs: rates2027.csv (rates.py) and attrs2027.csv (attrs.py). Writes silver_region4_2027.csv.

Service areas inside Rating Area 4 come from each carrier's rate application (README.md, table);
Aetna Life and UHIC file off-exchange plans only and are left out by the On filter.

Two readings of which plans count (README.md, "Which plans count"):
  all     every exchange silver plan ID, so an age-29 twin of a plan is a plan of its own;
  dep26   plans with dependent coverage to 26 only (Exhibit 23 "Limiting Child Age" 26).
"""
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

SERVES = {
    "Westchester": {"Anthem_HP", "HIP", "Healthfirst_PHSP", "MVP_HP", "NYQHC", "Oscar", "UHC"},
    "Queens": {"Anthem_HP", "HIP", "Healthfirst_PHSP", "MetroPlus", "NYQHC", "Oscar", "UHC"},
}

r = pd.read_csv("rates2027.csv")
a = pd.read_csv("attrs2027.csv")
r = r[(r.method == "Family-Tier Rates") & (r.area == "Rating Area 4")]
a["on"] = a.xchg.astype(str).str.strip() == "On"
p = (a.groupby(["carrier", "plan"])
     .agg(metal=("metal", "first"), on=("on", "any"), std=("std", "first"), child_age=("child_age", "first"),
          child_only=("child_only", "first"), non_ehb=("non_ehb", "first"))
     .reset_index())
m = r.merge(p, on=["carrier", "plan"], how="left")
assert not m.metal.isna().any(), "rated plan without an Exhibit 23 row"
s = m[(m.metal == "Silver") & m.on & (m.child_only == "No")].sort_values("single")
s[["carrier", "plan", "single", "couple", "std", "child_age", "non_ehb"]].to_csv("silver_region4_2027.csv",
                                                                               index=False)

for county, carriers in SERVES.items():
    x = s[s.carrier.isin(carriers)]
    print(f"\n== {county}: exchange silver plans, approved 2027 monthly rates")
    print(x[["carrier", "plan", "single", "couple", "std", "child_age", "non_ehb"]].head(8).to_string(index=False))
    for name, y in (("all", x), ("dep26", x[x.child_age == 26])):
        b = y.iloc[1]
        print(f"   SLCSP [{name}]: {b.carrier} {b.plan}  single {b.single:,.2f}/mo  couple {b.couple:,.2f}/mo"
              f"  = {12 * b.couple:,.0f}/yr")

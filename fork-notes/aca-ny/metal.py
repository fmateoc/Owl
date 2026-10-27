"""Rating Area 4 plans of one metal level per county, approved 2027 rates, on and off the exchange.

Usage: python metal.py Gold   (run where rates2027.csv and attrs2027.csv are; see README.md)
Writes <metal>_region4_2027.csv. Service areas as in slcsp.py (keep the two in step), plus the
two off-exchange-only filings (Aetna Life, UHIC), whose rate applications list both counties.
"""
import sys
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

SERVES = {
    "Westchester": {"Anthem_HP", "HIP", "Healthfirst_PHSP", "MVP_HP", "NYQHC", "Oscar", "UHC"},
    "Queens": {"Anthem_HP", "HIP", "Healthfirst_PHSP", "MetroPlus", "NYQHC", "Oscar", "UHC"},
}
metal = sys.argv[1]
OFF_ONLY = {"Aetna_Life", "UHIC"}
r = pd.read_csv("rates2027.csv")
a = pd.read_csv("attrs2027.csv")
r = r[(r.method == "Family-Tier Rates") & (r.area == "Rating Area 4")]
a["on"] = a.xchg.astype(str).str.strip() == "On"
p = (a.groupby(["carrier", "plan"])
     .agg(metal=("metal", "first"), on=("on", "any"), std=("std", "first"), child_age=("child_age", "first"),
          child_only=("child_only", "first"), hsa=("hsa", "first"), non_ehb=("non_ehb", "first"))
     .reset_index())
m = r.merge(p, on=["carrier", "plan"], how="left")
x = m[(m.metal == metal) & (m.child_only == "No")].sort_values("single")
x[["carrier", "plan", "single", "couple", "on", "std", "child_age", "hsa", "non_ehb"]].to_csv(
    f"{metal.lower()}_region4_2027.csv", index=False)
for county, carriers in SERVES.items():
    y = x[x.carrier.isin(carriers | OFF_ONLY) & (x.child_age == 26)]
    print(f"\n== {county}: {metal} plans, dependents to 26, approved 2027 monthly rates")
    print(y[["carrier", "plan", "single", "couple", "on", "std", "hsa", "non_ehb"]].to_string(index=False))

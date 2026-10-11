"""One-shot: zmed as a local-search family (shipped ALWAYS_FREE run is in the step-6 .txt)."""
import io
import time

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner import localsearch
from owlplanner.export import _compute_estate
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]


def line(name, htype, amount):
    return {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0,
            "amount": amount, "rate": 0.0, "survivor": np.nan}


localsearch.ALWAYS_FREE = tuple(f for f in localsearch.ALWAYS_FREE if f != "zmed")
localsearch.FAMILIES = localsearch.FAMILIES + ("zmed",)
localsearch.FAMILY_LABEL = {**localsearch.FAMILY_LABEL, "zmed": "medical floor"}

p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "zmed-family",
             verbose=False, logstreams=[io.StringIO()])
p.setSpendingProfile("budget")
p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75], hsa=[60, 60])
p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
p.setRates("conservative")
p.setSocialSecurity([3000, 2400], [70, 70])
p.houseLists["Budget"] = cond(pd.DataFrame([
    line("core", "core", 80000.0), line("pt", "property tax", 25000.0),
    line("med", "medical", 3000.0)]), "Budget")
p.setStateTax("NY", locality="Yonkers")
p.setExpirationYearOBBBA(2099)
t = time.time()
p.solve("maxBequest", options={"noRothConversions": "None", "breakpointMethod": "local-search",
                               "withItemized": "optimize"})
dt = time.time() - t
print("status", p.caseStatus)
print("bequest %.0f" % (_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]))
print("time", round(dt, 1))
print("zmed", p.vm["zmed"].size if "zmed" in p.vm else 0,
      "zmedf", p.vm["zmedf"].size if "zmedf" in p.vm else 0)
print("bins", {k: int(v.size) for k, v in p.vm._blocks.items() if v.start >= p.vm.nconts})
print("nodes", p.solverNodesTotal, "hits", p.solverNodeLimitHits)

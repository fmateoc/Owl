"""Does local search's step (b) (SS moves) lose STAR plans by pinning zst? Date frozen at 2026-10-15.

NY Yonkers owner couple as in tests/tax/test_star.py (budget: core $80k + property tax $25k), maxBequest,
statutory law. Usage: zst_step_b.py VARIANT TAXABLE_K DOB_A DOB_B SS_A SS_B
VARIANT: ls (fork as is), ls-zst (step (b) also leaves zst free), bb (branch-and-bound preset, maxTime 600).
"""
import datetime, io, sys, time
from unittest.mock import patch
import numpy as np
import pandas as pd
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import owlplanner as owl
from owlplanner import localsearch
from owlplanner.export import _compute_estate
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
var, tk, dob_a, dob_b, ss_a, ss_b = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4], float(sys.argv[5]), float(sys.argv[6])
if var == "ls-zst":
    orig = localsearch.LocalSearch._pin
    def _pin(self, x, families):
        # Step (b) is the only call that pins the families without SS: leave zst free there too.
        if "zs" not in families and "zst" in families and "zs" in self._families():
            families = [f for f in families if f != "zst"]
        return orig(self, x, families)
    localsearch.LocalSearch._pin = _pin
p = owl.Plan(["Joe", "Jane"], [dob_a, dob_b], [89, 92], "star", verbose=False, logstreams=[io.StringIO()])
p.setSpendingProfile("budget")
p.setAccountBalances(taxable=[tk, tk], taxDeferred=[900, 600], taxFree=[75, 75])
p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
p.setRates("conservative")
p.setSocialSecurity([ss_a, ss_b], [67, 67])
year = int(p.year_n[0])
line = lambda name, htype, amount: {"active": True, "name": name, "type": htype, "year": year, "end": 0,
                                    "amount": amount, "rate": 0.0, "survivor": np.nan}
p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(
    pd.DataFrame([line("core", "core", 80000.0), line("pt", "property tax", 25000.0)]), "Budget")
p.setStateTax("NY", locality="Yonkers", school_district="Yonkers")
p.setExpirationYearOBBBA(2099)
opts = {"breakpointMethod": "branch-and-bound" if var == "bb" else "local-search"}
if var == "bb":
    opts["maxTime"] = 600
t = time.time(); p.solve("maxBequest", options=opts); dt = time.time() - t
if p.caseStatus != "solved":
    print(f"{var:7s} {tk:5.0f} {dob_a}/{dob_b} {ss_a:.0f}/{ss_b:.0f} {p.caseStatus}"); sys.exit()
g = p.gamma_n[: p.N_n]
enh = int(np.sum(np.isclose(p.st_star_n, p._star.enhanced_n) & (p._star.enhanced_n > p._star.basic_n)))
cand = int(np.sum(p._star.enhanced_n > p._star.basic_n))
res = p.fixedPointResidual or {}
tot = sum(v.get("abs_sum", 0.0) for v in res.values() if isinstance(v, dict))
parts = " ".join(f"{k}={v['abs_sum']:,.0f}" for k, v in res.items() if isinstance(v, dict) and v.get("abs_sum", 0) >= 1)
print(f"{var:7s} taxable {tk:5.0f} dob {dob_a[:4]}/{dob_b[:4]} ss {ss_a:.0f}/{ss_b:.0f} | bequest "
      f"{_compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]:>11,.0f} | Enhanced {enh:2d}/{cand:2d} yrs | STAR "
      f"{np.sum(p.st_star_n / g):>7,.0f} | {dt:6.1f} s | res {tot:,.0f} [{parts}] | gap {p.solverGap:.1e} | {p.breakpointMethodUsed}",
      flush=True)

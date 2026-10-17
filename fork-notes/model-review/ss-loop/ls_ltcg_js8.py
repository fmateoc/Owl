"""john+sally: local-search preset variants. Date frozen 2026-10-15.
Usage: js8.py ROOT base|radius|joint"""
import datetime, sys, time
from unittest.mock import patch
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import owlplanner as owl
from owlplanner import localsearch
from owlplanner.export import _compute_estate
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
root, var = sys.argv[1], sys.argv[2]
case = sys.argv[3] if len(sys.argv) > 3 else "Case_john+sally"
o_extra = {"breakpointMethod": "local-search"}
if var == "radius":
    o_extra["localSearchRadius"] = 200
if var == "joint":
    # Step (b) frees LTCG with SS: pin only the families other than SS and LTCG.
    orig = localsearch.LocalSearch._pin
    def _pin(self, x, families):
        import inspect
        caller = inspect.stack()[1]
        if caller.function == "solve" and "others" in caller.frame.f_locals and families is caller.frame.f_locals["others"]:
            families = [f for f in families if f != "zl"]
        return orig(self, x, families)
    localsearch.LocalSearch._pin = _pin
p = owl.readConfig(f"{root}/examples/{case}.toml", verbose=False)
o = dict(p.solverOptions); o.update(o_extra)
t = time.time(); p.solve(p.objective, o); dt = time.time() - t
obj = float(p.basis) if p.objective == "maxSpending" else _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]
print(f"{case:22s} {var:7s} {obj:>12,.0f} {dt:6.1f}s {p.breakpointMethodUsed}")

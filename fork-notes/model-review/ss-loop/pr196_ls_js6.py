import datetime, sys, io
from unittest.mock import patch
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 15)
import owlplanner as owl
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
root = sys.argv[1]
log = io.StringIO()
p = owl.readConfig(f"{root}/examples/Case_john+sally.toml", verbose=True, logstreams=[log])
o = dict(p.solverOptions); o.update(withSSTaxability="optimize", withMedicare="optimize", withLTCG="optimize", mipStrategy="local-search")
p.solve(p.objective, o)
print(log.getvalue())

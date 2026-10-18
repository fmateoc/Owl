"""gain_basis.py rerun on today's fork: withItemized 'loop' (the 'optimize' mode was removed in R1),
date frozen at 2026-10-11 (the original run's day)."""
import datetime, sys
from unittest.mock import patch
_REAL = datetime.date
class _Day(_REAL):
    @classmethod
    def today(cls):
        return _REAL(2026, 10, 11)
import owlplanner as owl  # noqa
for mod in list(sys.modules.values()):
    if mod is not None and getattr(mod, "date", None) is _REAL:
        patch.object(mod, "date", _Day).start()
src = open(__file__.replace("gain_basis_loop.py", "gain_basis.py")).read()
src = src.replace('("none", "optimize")', '("none", "loop")').replace('res["optimize"]', 'res["loop"]')
exec(compile(src, "gain_basis_loop", "exec"))

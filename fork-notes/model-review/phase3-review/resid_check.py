import sys
sys.path.insert(0, "tests/tax")
import numpy as np
from test_itemized import _plan, OPTS
for name, kw, extra in (
    ("NY mtg exact optimize", dict(state="NY", mortgage=(600_000.0, 6.5, 30)), dict(OPTS, withItemized="optimize")),
    ("NY mtg exact loop", dict(state="NY", mortgage=(600_000.0, 6.5, 30)), dict(OPTS, withItemized="loop")),
    ("NJ med loop full", dict(state="NJ", medical=6000.0), {"noRothConversions": "None"}),
    ("FL mtg560 full loop", dict(state="FL", property_tax=0.0, mortgage=(560_000.0, 6.5, 30)), {"noRothConversions": "None"}),
):
    p = _plan(**kw); p.solve("maxBequest", options=extra)
    r = p._fixedPointResidualByYear(True)
    out = {k: round(float(np.sum(np.abs(v))), 1) for k, v in r.items() if k in ("itemized", "state medical", "state itemized", "deduction")}
    print(name, p.caseStatus, p.convergenceType, out, "total resid", getattr(p, "fixedPointResidual", None))

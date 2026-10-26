# Comment draft for upstream #231 (exempt amounts after the table)

Status: draft, for the user to post (2026-10-26). Numbers from a run on stock `dev` `4dcfabb`:
`fork-notes/issue-231-repro.py`, output `fork-notes/issue-231-repro-output.txt`; the test
below was run on stock `dev` too (fails at 2.5%, 6,900.30 vs 7,220.00; passes at 0%).

What the comment adds beyond #231: (1) a regression test for the fix, (2) the payroll wage
base, which has the same shape. Not in it: the 2027 amounts themselves (not verified here:
federalregister.gov and ssa.gov are not reachable from our container).

---

Two additions, run on stock `dev` `4dcfabb`.

**1. A test for the fix.** For a year the table covers, the amount withheld depends only on
that year's nominal earnings and nominal exempt amount. So a plan starting in 2026 and one
starting in 2027 should withhold the same nominal amount for 2027's work. Today, with 2027
added to the table as above and $40,000 of 2027 wages:

| Inflation | Plan from 2026 | Plan from 2027 | Difference |
|---|---|---|---|
| 0% | 7,220.00 | 7,220.00 | 0.00 |
| 2.5% | 6,900.30 | 7,220.00 | -319.70 |

The 0% row is a check of the harness, since there the two dollar bases coincide. $40,000 keeps
the excess below the year's benefit, so the amount withheld is the excess itself, and the PIA
(entered in each plan's own today's dollars) does not enter. The test, which fails today at 2.5%:

```python
import datetime
import io
import sys

import numpy as np
import pytest

import owlplanner as owl
from owlplanner import socialsecurity as ss


def _withheld_for_2027(monkeypatch, start, inflation):
    """Nominal amount withheld for $40,000 of 2027 wages by a plan starting in `start`
    (the excess is below the year's benefit, so the PIA's dollar base does not enter)."""

    class Day(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(start, 1, 1)

    with monkeypatch.context() as mp:
        for name, mod in list(sys.modules.items()):
            d = getattr(mod, "date", None) if name.startswith("owlplanner") and mod else None
            if isinstance(d, type) and issubclass(d, datetime.date):
                mp.setattr(mod, "date", Day)
        p = owl.Plan(["W"], ["1963-08-15"], [89], "t", verbose=False, logstreams=[io.StringIO()])
        p.setSocialSecurity([2000], [62 + 1 / 12])  # entitled before either plan
        p.omega_in[0, 2027 - start] = 40_000
        gamma = (1 + inflation) ** np.arange(p.N_n + 1)
        res = p._earningsTestResult(gamma_n=gamma)
    return float(np.sum(res.withheld_in[0] * gamma[: p.N_n]))


@pytest.mark.parametrize("inflation", [0.0, 0.025])
def test_withholding_in_a_tabled_year_does_not_depend_on_the_start_year(monkeypatch, inflation):
    monkeypatch.setitem(ss._EXEMPT_TABLE, 2027, (25_560.0, 67_920.0))
    early = _withheld_for_2027(monkeypatch, 2026, inflation)
    late = _withheld_for_2027(monkeypatch, 2027, inflation)
    assert early == pytest.approx(late, abs=1.0)  # 7,220 = (40,000 - 25,560) / 2
```

**2. The payroll wage base has the same shape.** `payrollWageBase` (from #227/#228, my code) is
one value, "held at its 2026 level in today's dollars", and read as the plan's first-year
dollars. That is the convention the federal brackets follow, and the year-end checklist lists
it, so between releases it is no worse than they are. On $250,000 of 2027 wages:

| Inflation | Plan from 2026 | Plan from 2027 | Difference |
|---|---|---|---|
| 0% | 15,514.00 | 15,514.00 | 0.00 |
| 2.5% | 15,799.97 | 15,514.00 | 285.97 |

The difference is 6.2% of the base's 2.5% growth.

Once the fix makes `_EXEMPT_TABLE` nominal and year-keyed, though, the wage base would be the
only amount SSA indexes to wages each year left on the other convention. Adding next year's
base before the year starts would then inflate it twice, the same way #231 shows for the exempt
amounts. It could go in a year-keyed nominal table with the same lookup. If the 2027 base was
published with the exempt amounts, it can go in now.

# Draft upstream design issue: the employee payroll tax on wages, for the user to post

Status: **posted by the user as #227 (2026-10-25)**, with the PR offer kept. Answered the same day: PR requested; built as `payroll-tax-pr` (`fork-notes/pr-227-body.md`). Drafted 2026-10-24, reviewed 2026-10-25 on `claude/phase5-step1` (pushed as `claude/eager-hawking-scp4gw`),
after merging upstream `dev` `4e55b36`. Not posted. Concept level, as #220 was: the gap, the rule,
a shape and measured stakes on upstream's own examples, not the fork's code. The fork charges the
tax with no option since 2026-10-24 (PROGRESS.md "Payroll tax always on; upstream issue drafted"),
and has no `withPayrollTax` key since 2026-10-25.

## What the text rests on

**Verified on stock upstream `dev` `4e55b36`** (`git show upstream/dev:...`, 2026-10-24):

- `ui/Documentation.py:446-453`: *anticipated wages* is pay as it enters AGI, and "**Owl** uses this
  single amount both as cash available to the plan and as taxable employment income". The same in
  `papers/owl.tex:260-266` ("This single amount serves both as cash available to the plan ...") and
  `info/PARAMETERS.md:81` ("as they enter AGI").
- No payroll tax anywhere: a case-insensitive search of the 296 `.md`, `.py`, `.tex` and `.toml`
  files for `\bfica\b`, `payroll tax`, `0.0765`, `wage base`, `medicare tax` (not preceded by
  "additional"), `social security tax\b` and `self-employment tax` finds one hit, the digits
  `0.076560` in `data/mortality_tables.py:370`. Nothing in `modeling-capabilities.md` lists it as a
  limitation.
- `Plan._earnings_test_inputs` (since #221, `ccc4d46`): earnings are wages plus that year's
  tax-deferred contributions, which is W-2 box 5 under the #221 convention.

**Real run on stock `dev` `4e55b36`** (`fork-notes/issue-payroll-tax-repro.py`, output `issue-payroll-tax-repro-output.txt`, run 2026-10-24 from
a worktree of `upstream/dev` with its own `src` on the path, inside pytest for the frozen date;
`owlplanner from .../stock/src/owlplanner/__init__.py` in the output): the table below. Method: the
employee's FICA is a non-deductible cash outflow, which is exactly what a negative big-ticket item is
in Owl, so each example with wages is solved as shipped and again with its FICA entered that way;
no code change.

**Cross-check in the fork** (which charges the tax in the cash-flow row, 2026-10-24, HiGHS, frozen
date): the fork's payroll totals equal the repro's hand FICA (43,987.50, 25,245.00, 8,797.50,
100,138.50), and for the four examples where the fork's model otherwise equals upstream's
(alex+jamie, joe, john+sally, jon+jane) the fork's objective equals the repro's "with FICA" column
within \$0.16 (225,076.85, 91,275.84, 21.00, 155,455.03). jack+jill differs by the fork's smile.

**Rules, verified earlier in the primary text** (PROGRESS.md "Phase 5 step 5", irs.gov read
2026-10-18 and 2026-10-22, not re-read today): IRS Pub. 15 (2026), "What's New": 6.2% social
security tax each for employer and employee up to \$184,500, Medicare 1.45% each with no base;
Instructions for Form 8959: Additional Medicare Tax 0.9% above \$250,000 MFJ / \$200,000 single,
"aren't indexed for inflation", on combined Medicare wages.

**Verified at the review (2026-10-25; both texts saved in `fork-notes/phase5/sources/`):** 20 CFR 404.1048 (eCFR versioner API, 2026-10-15 text): the
contribution and benefit base is refigured in each year with a benefit cost-of-living increase, by
the ratio of average W-2 wages, rounded to \$300, and is never lower than the base in effect. IRS Tax
Topic 554 (irs.gov, "Page Last Reviewed or Updated: 24-Sep-2026"): self-employment tax is 12.4% +
2.9% on 92.35% of net earnings from self-employment, and one-half of it is deducted in figuring
AGI. `info/PARAMETERS.md:83` on `4e55b36`: `other inc` is "Not read by the SSA earnings test: enter
net SE earnings in `anticipated wages` for them to count". `computeNIIT` switches to single in the
year after the first death (`n == n_d`); `irmaaStatus` follows the lookback return since #213, so
the text cites `computeNIIT`.

**Recalled, kept out of the text's claims:** W-2 box 3/5 treatment of 401(k) deferrals (in) and
section 125 HSA (out).

**Not in the text on purpose:** the fork's other additions; MOSEK (no license here).

## Where to post, and when (user's call)

- **A new issue.** Nothing upstream tracks it.
- **Timing.** Right after #220/#222 and #221, which defined the wage input this rests on and the
  derived earnings it would reuse; the maintainer has that code in mind. The evidence is his own
  examples under the frozen test date, so it moves only when upstream's code does.
- **Offer a PR?** #222 was squashed and landed with one change; the same could work here (pure
  function in `tax_federal`, a constant in the cash-flow row, outputs). The text offers it.

---

## Issue text

**Title:** Wages are counted as cash with no payroll tax: FICA is never paid

**Body:**

Since #221, *anticipated wages* are the wages as they enter AGI, and Owl "uses this single amount
both as cash available to the plan and as taxable employment income" (`ui/Documentation.py`). The
employee's payroll tax is not charged anywhere: no FICA, no Additional Medicare Tax (I searched the
`.md`, `.py`, `.tex` and `.toml` files on `dev` `4e55b36` and found none, and
`modeling-capabilities.md` does not list it as a limitation). So every working year's cash is
overstated by 7.65% of earnings up to the wage base, 1.45% above it, plus 0.9% of household
Medicare wages above \$250,000 (MFJ) or \$200,000 (single).

A household cannot enter wages net of it: that would understate AGI and income tax. The only way to
get it right today is a negative big-ticket item of the same amount each year, which nothing tells
the user to do.

**Stakes on the examples** (stock `dev` `4e55b36`, frozen test date, HiGHS; each case as shipped,
then with each person's FICA entered as a negative big-ticket item, the same non-deductible cash
outflow; script below):

| case | objective | wage years | earnings | FICA | as shipped | with FICA | difference |
|---|---|---|---:|---:|---:|---:|---:|
| alex+jamie | maxSpending | 2026-2028 | 575,000 | 43,988 | 228,077 | 225,077 | -3,000 (-1.32%) |
| chris+pat | maxSpending | 2026-2028 | 626,900 | 48,084 | 116,837 | 114,043 | -2,794 (-2.39%) |
| jack+jill | maxSpending | 2026-2028 | 575,000 | 43,988 | 102,572 | 100,669 | -1,903 (-1.86%) |
| joe | maxSpending | 2026-2028 | 330,000 | 25,245 | 92,574 | 91,276 | -1,298 (-1.40%) |
| john+sally | maxBequest | 2026 | 115,000 | 8,798 | 16,803 | 21 | -16,782 |
| jon+jane | maxSpending | 2026-2033 | 1,309,000 | 100,138 | 160,611 | 155,455 | -5,156 (-3.21%) |

Earnings are what the earnings test already derives (wages plus that year's tax-deferred
contributions); spending in \$/yr, bequest in today's dollars. Six of the 18 examples have wages;
all six are overstated: the spending plans by 1.3-3.2% a year, and john+sally's bequest falls
from \$16,803 to \$21.

**Why it fits your guideline** ("model a tax rule exactly when it changes a decision the household
faces soon, and when we can do that without making the planner harder to use or slower to
solve"):

- *A near-term decision.* Every work variant pays it: retiring a year later, part time, or
  stopping now. Without it, each working year brings in 7.65% more cash than it does, in the same
  comparisons the earnings test now gets right.
- *No input.* The earnings are the ones the earnings test already derives; the rates are statutory.
- *Nothing to solve.* The tax is not deductible, so it is a constant of each year's cash-flow row:
  no column, no row, no binary, and no term in any tax computation.

**A shape** (what the fork has charged since 2026-10-22, with no option since 2026-10-24):

- a pure function: per person, 6.2% of earnings up to the wage base plus 1.45% of all earnings;
  per household, 0.9% of the combined earnings above the threshold, joint through the year of the
  first death and single after, as `computeNIIT` does;
- the year's total subtracted from that year's cash-flow right-hand side, like debt payments;
- outputs: a *payroll tax* column in the Cash Flow sheet (which must still balance), inside the
  taxes of the lifetime allocation, a Summary line for households with earnings, and the plan
  metrics that `owlcli compare` reports.

Choices I would leave to you:

1. **The wage base after 2026.** By statute it follows average wages (20 CFR 404.1048: refigured in
   each year with a benefit COLA, never lower than before); the fork holds the 2026 \$184,500
   constant in today's dollars, as the earnings test does with its exempt amounts. The threshold of
   the 0.9% is not indexed (Form 8959).
2. **Self-employment tax.** `info/PARAMETERS.md` asks for net SE earnings in *anticipated wages*
   so that the earnings test counts them. They would then pay the employee's 7.65%, about half of
   the 14.1% that SE tax takes (12.4% + 2.9% on 92.35% of net earnings, half of it deducted from
   AGI; IRS Tax Topic 554). Taxing them right needs an input saying which wages are SE earnings:
   probably a documented limitation for now. `other inc` stays untaxed, as it
   stays out of the earnings test.
3. **Default.** On for every case, with no option, as the earnings test is: the six examples above
   move; the other twelve are unchanged to the cent (no earnings, so nothing is charged).

If it helps, I can open a PR on `dev` as with #222.

<details><summary>Repro script</summary>

```python
"""Stock-dev repro for the payroll-tax issue (fork-notes/issue-payroll-tax.md).

Owl counts `anticipated wages` (the wages in AGI since #221) as cash, and charges no payroll tax
on them. The employee's FICA is a cash outflow that no income tax computation deducts, which is
exactly how Owl treats a negative big-ticket item. So this script measures what the missing tax
is worth on stock Owl, with no code change: each example with wages is solved as shipped, then
again with each person's FICA entered as a negative big-ticket item in each year.

FICA by hand (IRS Pub. 15 (2026): 6.2% up to the $184,500 wage base, 1.45% on all; Form 8959:
0.9% on the household's Medicare wages above $250,000 MFJ / $200,000 single, not indexed),
on the earnings Owl's earnings test already derives: wages plus that year's tax-deferred
contributions (Plan._earnings_test_inputs; W-2 boxes 3 and 5). The wage base is held at its
2026 level in today's dollars (it follows the wage index by statute).

Run from a checkout of stock `dev`, inside pytest so tests/conftest.py freezes the date:
    cp fork-notes/issue-payroll-tax-repro.py <stock>/tests/test_zz_payroll_repro.py
    cd <stock> && PYTHONPATH=src python -m pytest tests/test_zz_payroll_repro.py -s -q -p no:cacheprovider
"""
import io
import os

import numpy as np

import owlplanner as owl

CASES = ("alex+jamie", "chris+pat", "jack+jill", "joe", "john+sally", "jon+jane")
BASE_2026 = 184_500.0


def _fica(p):
    earnings = np.where(p.omega_in > 0, p.omega_in + p.kappa_ijn[:, 1, : p.N_n], 0.0)
    ss = 0.062 * np.minimum(earnings, BASE_2026 * p.gamma_n[: p.N_n])
    med = 0.0145 * earnings
    thr = np.where(np.arange(p.N_n) < p.n_d, 250_000.0 if p.N_i == 2 else 200_000.0, 200_000.0)
    addl = 0.009 * np.maximum(0.0, np.sum(earnings, axis=0) - thr)
    per_person = ss + med
    if p.N_i == 2:  # Additional Medicare Tax split by share of earnings, for the big-ticket entry
        share = np.divide(earnings, np.sum(earnings, axis=0), out=np.zeros_like(earnings), where=earnings > 0)
        per_person = per_person + share * addl
    else:
        per_person = per_person + addl
    return earnings, per_person


def _solve(case, fica=False):
    root = os.path.join(os.path.dirname(owl.__file__), "..", "..", "examples")
    p = owl.readConfig(os.path.join(root, f"Case_{case}.toml"), verbose=False, logstreams=[io.StringIO()])
    earnings, tax = _fica(p)
    if fica:
        p.Lambda_in[:, : p.N_n] -= tax
    p.solve(p.objective, dict(p.solverOptions or {}))
    assert p.caseStatus == "solved", (case, p.caseStatus)
    return p, earnings, tax


def test_repro():
    print("\nowlplanner from", owl.__file__)
    print(f"{'case':12} {'objective':11} {'wage years':10} {'earnings':>10} {'FICA':>8} "
          f"{'as shipped':>12} {'with FICA':>12} {'difference':>11}")
    for case in CASES:
        p, earnings, tax = _solve(case)
        q, _, _ = _solve(case, fica=True)
        key = "basis" if p.objective == "maxSpending" else "bequest"
        a, b = getattr(p, key), getattr(q, key)
        yrs = [int(p.year_n[n]) for n in range(p.N_n) if earnings[:, n].sum() > 0]
        span = f"{yrs[0]}-{yrs[-1]}" if len(yrs) > 1 else str(yrs[0])
        print(f"{case:12} {p.objective:11} {span:10} {earnings.sum():>10,.0f} {tax.sum():>8,.0f} "
              f"{a:>12,.0f} {b:>12,.0f} {b - a:>+11,.0f} ({100 * (b - a) / a:+.2f}%)")
```

</details>

---

## Before posting (user)

- The script in the `<details>` block is `fork-notes/issue-payroll-tax-repro.py` as run (its
  docstring's `\\$` escapes shown as `$`); its run instructions name a `<stock>` checkout.
- Decide on the PR offer.
- Rerun the script if upstream `dev` has moved past `4e55b36` (the run uses the frozen test date,
  so only code changes move it).

"""First-order stakes of itemizing (Phase 3 probe), post hoc on a solved plan.

Not a model of itemizing: the plan is solved with the standard deduction (as Owl does today),
then each year's deduction is recomputed as max(standard, itemized) with income held fixed, and
the tax saved is read off the solved plan's own brackets. The LP does not respond (no change in
conversions or withdrawals), so this is a lower bound on what the plan could gain, and it
ignores the LTCG stacking, recapture and IRMAA/SS feedback of a lower taxable income.

Synthetic couple from Phase 1 (born 1964-03-15 / 1964-09-15, LE 89/92, SS $3,000/$2,400 at 70,
$150k taxable each, $75k Roth each, $900k + $600k tax-deferred, conservative rates, 60/40),
maxBequest at a fixed budget: core $80k + property tax (a survivor keeps paying it).
Exact LP (Medicare off, SS taxability 0.85), so no Medicare premiums and no medical deduction.

Federal (verified 2026-10-10 against P.L. 119-21 sec. 70120 and the 2025 Schedule A
instructions): SALT cap $40,400 in 2026, +1%/yr through 2029, $10,000 from 2030; the MAGI
phase-down above $505,000 is not reached here and is ignored. The senior bonus is kept by
itemizers (2025 Form 1040 instructions, line 13b), the 65+ additional amount is not.
Mortgage interest on up to $750,000 of acquisition debt (Pub. 936, 2025).
New York (IT-196-I 2025): itemizing is allowed whatever was done federally; state and local
income taxes are not deductible; no SALT cap; mortgage limit $1M; above NYAGI $200,000 (MFJ)
the itemized deduction is cut by up to 25% over the next $50,000 (Worksheet 3). Standard
deduction $16,050 MFJ (taxes_state.toml).

Owl reverts to pre-TCJA brackets and standard deduction in `yOBBBA` (default 2032, a
speculation: P.L. 119-21 made them permanent). From that year the probe applies pre-TCJA
itemizing too: no SALT cap and a $1M mortgage limit (the Pease limitation is ignored).

Mortgage cases: the loan proceeds come in as a positive big-ticket item in the first year and
stay invested (the borrow-instead-of-paying-cash counterfactual); payments come from Debts.

Usage: itemized_probe.py [case;case...] [yOBBBA]   case keys: ny, nymort, nj, njmort
"""
import io
import sys

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner import tax_federal as tx
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]
PT = 25000.0  # property tax, first year, today's $ (made up; Westchester-like)
MORTGAGE = (600000.0, 6.5, 30)  # principal, rate %, term; taken out in THISYEAR
opts = {"noRothConversions": "None", "withMedicare": "None", "withSSTaxability": 0.85}
YOBBBA = int(sys.argv[2]) if len(sys.argv) > 2 else 2032


def salt_cap(year):
    if year >= YOBBBA:
        return np.inf
    if year >= 2030:
        return 10000.0
    return 40400.0 * 1.01 ** max(0, year - 2026) if year >= 2026 else 40000.0


def mortgage_interest(year):
    """Interest paid in a calendar year on the probe's mortgage (annual payments, as debts.py)."""
    P, r, T = MORTGAGE
    k = year - THISYEAR
    if k < 0 or k >= T:
        return 0.0, 0.0
    i = r / 100
    pay = P * i / (1 - (1 + i) ** -T)
    bal = P * (1 + i) ** k - pay * ((1 + i) ** k - 1) / i
    return bal * i, bal


def bracket_tax(ti, rates, widths):
    tax, left = 0.0, max(0.0, ti)
    for r, w in zip(rates, widths):
        take = min(left, w)
        tax += r * take
        left -= take
    return tax


def run(state, locality, mortgage):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], "itemized probe",
                 verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75])
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])

    def line(name, htype, amount):
        return {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0,
                "amount": amount, "rate": 0.0, "survivor": np.nan}
    p.houseLists["Budget"] = conditionDebtsAndFixedAssetsDF(
        pd.DataFrame([line("core", "core", 80000.0), line("pt", "property tax", PT)]), "Budget")
    if mortgage:
        P, r, T = MORTGAGE
        p.houseLists["Debts"] = conditionDebtsAndFixedAssetsDF(pd.DataFrame([{
            "active": True, "name": "m", "type": "mortgage", "year": THISYEAR, "term": T,
            "amount": P, "rate": r}]), "Debts")
    p.setStateTax(state, locality=locality)
    p.setExpirationYearOBBBA(YOBBBA)
    if mortgage:
        p.Lambda_in[0, 0] = MORTGAGE[0]
    p.solve("maxBequest", options=dict(opts))
    assert p.caseStatus == "solved", p.caseStatus

    # Standard deduction without the senior bonus (the bonus is kept by itemizers).
    base = tx.taxParams(p.yobs, p.i_d, p.n_d, p.N_n, p.gamma_n, np.full(p.N_n, np.inf), p.yOBBBA)[0]
    bonus = p.sigmaBar_n - base
    std_core = base.copy()  # the 2026 standard amount + 65+ additions
    g = p.gamma_n[:-1]
    pt_n = PT * g  # the budget's property tax line in nominal $ (real growth 0)
    rows, fed_save, ny_save, fed_years, ny_years = [], 0.0, 0.0, 0, 0
    for n in range(p.N_n):
        year = THISYEAR + n
        mi, bal = mortgage_interest(year) if mortgage else (0.0, 0.0)
        limit = 750000.0 if year < YOBBBA else 1e6
        mi_fed = mi * min(1.0, limit / bal) if bal > 0 else 0.0
        salt = min(salt_cap(year), pt_n[n] + p.st_T_n[n])  # SALT cap is nominal, not indexed
        item = salt + mi_fed
        ti = float(np.sum(p.f_tn[:, n]))  # ordinary taxable income in the solved plan
        delta = max(0.0, item - std_core[n])
        fed = 0.0
        if delta > 0:
            fed_years += 1
            rates, widths = p.theta_tn[:, n], p.DeltaBar_tn[:, n]
            fed = bracket_tax(ti, rates, widths) - bracket_tax(ti - delta, rates, widths)
        fed_save += fed / g[n]
        ny = 0.0
        if state == "NY":
            agi = p.st_agi_n[n]
            ny_item = pt_n[n] + mi * min(1.0, 1e6 / bal if bal > 0 else 1.0)
            ny_item *= 1 - 0.25 * min(max(agi - 200000.0, 0.0), 50000.0) / 50000.0
            ny_std = p.st_sigmaBar_n[n]
            d = max(0.0, ny_item - ny_std)
            if d > 0:
                ny_years += 1
                sti = p.st_ti_n[n]
                rates, widths = p.st_theta_tn[:, n], p.st_DeltaBar_tn[:, n]
                ny = (bracket_tax(sti, rates, widths) - bracket_tax(sti - d, rates, widths))
                ny *= 1 + (p.lt_surcharge_n[n] if np.ndim(p.lt_surcharge_n) else 0.0)
            ny_save += ny / g[n]
        rows.append((year, ti, std_core[n] + bonus[n], item + bonus[n], fed, ny))
    return p, rows, fed_save, ny_save, fed_years, ny_years


cases = {
    "ny": ("NY Yonkers owner, $25k property tax", "NY", "Yonkers", False),
    "nymort": ("NY Yonkers owner, $25k property tax, $600k mortgage", "NY", "Yonkers", True),
    "nj": ("NJ owner, $25k property tax", "NJ", "", False),
    "njmort": ("NJ owner, $25k property tax, $600k mortgage", "NJ", "", True),
}
only = sys.argv[1].split(";") if len(sys.argv) > 1 else list(cases)
for key in only:
    name, state, loc, mort = cases[key]
    p, rows, fed, ny, fy, nyy = run(state, loc, mort)
    print(f"## {name} (run {pd.Timestamp.today().date()}, plan starts {THISYEAR}, yOBBBA {YOBBBA})")
    print(f"federal: itemizing wins in {fy} years, first-order tax saved {fed:,.0f} (today's $)")
    if state == "NY":
        print(f"NY+local: itemizing wins in {nyy} years, first-order tax saved {ny:,.0f} (today's $)")
    print("| year | fed ordinary TI | std (+bonus) | itemized (+bonus) | fed saved | NY saved |")
    for r in rows[:8] + rows[-2:]:
        print(f"| {r[0]} | {r[1]:,.0f} | {r[2]:,.0f} | {r[3]:,.0f} | {r[4]:,.0f} | {r[5]:,.0f} |")
    print()
    sys.stdout.flush()

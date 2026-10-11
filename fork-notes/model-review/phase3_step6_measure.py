"""Phase 3 step 6 measurement: itemizing stakes in-model, binaries, solve times.

Same synthetic couple as itemized_probe.py / housing_stakes.py (born 1964, LE 89/92, SS
$3,000/$2,400 at 70, $150k taxable / $75k Roth each, conservative 60/40). Plans start today;
compare variants run the same day.

Groups (CLI: phase3_step6_measure.py [group;group...] [yOBBBA]):
  probe     itemized_probe cases in-model: none / loop / optimize, exact LP
  probe-ls  the same under local search (statutory law)
  nynj      NY vs NJ owner at $20k and $25k property tax, none vs optimize
  housing   Scenario 5 rent / buy cash / buy mortgage with the deduction
  hsa       HSA plan: zmed / zmedf counts, and zmed as ALWAYS_FREE vs family
  med       discretionary medical under maxSpending: zmed family vs ALWAYS_FREE

yOBBBA: 2099 (statutory, D1) or 2032 (Owl's default reversion). Default 2099.
"""
import io
import sys
import time

import numpy as np
import pandas as pd

import owlplanner as owl
from owlplanner import localsearch
from owlplanner.export import _compute_estate
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF as cond

THISYEAR = owl.Plan(["A"], ["1960-01-01"], [80], "t", verbose=False).year_n[0]
PT25 = 25000.0
MORTGAGE = (600000.0, 6.5, 30)  # principal, rate %, term
EXACT = {"noRothConversions": "None", "withMedicare": "None", "withSSTaxability": 0.85}
LS = {"noRothConversions": "None", "breakpointMethod": "local-search"}
YOBBBA = int(sys.argv[2]) if len(sys.argv) > 2 else 2099
OUT = open(f"fork-notes/model-review/phase3_step6_{pd.Timestamp.today().date()}.txt", "a")


def say(msg):
    print(msg)
    OUT.write(msg + "\n")
    OUT.flush()


def line(name, htype, amount, **kw):
    row = {"active": True, "name": name, "type": htype, "year": THISYEAR, "end": 0,
           "amount": amount, "rate": 0.0, "survivor": np.nan}
    row.update(kw)
    return row


def bins(p):
    nconts = p.vm.nconts
    return {k: v.size for k, v in p.vm._blocks.items() if v.start >= nconts}


def estate(p):
    return _compute_estate(p, p.N_n)[3] / p.gamma_n[p.N_n]


def report(tag, p, dt, opts):
    if p.caseStatus != "solved":
        say(f"| {tag} | {opts.get('withItemized', 'loop')} | - | INFEASIBLE | | | | {dt:.1f}s | | |")
        return
    b = bins(p)
    item = getattr(p, "itemizing_n", None)
    st_item = getattr(p, "st_itemizing_n", None)
    item_yrs = int(np.count_nonzero(item)) if item is not None else 0
    st_yrs = int(np.count_nonzero(st_item)) if st_item is not None else 0
    item_tot = float(np.sum(getattr(p, "item_n", np.zeros(1)) / p.gamma_n[:-1]))
    st_tot = float(np.sum(getattr(p, "st_item_n", np.zeros(1)) / p.gamma_n[:-1]))
    st_tax = float(np.sum(p.st_T_n / p.gamma_n[:-1]))
    nodes = getattr(p, "solverNodesTotal", -1)
    hits = getattr(p, "solverNodeLimitHits", None)
    hit_txt = ""
    if hits is not None:
        capped, runs, scap, sruns = hits
        hit_txt = f"; node-limit {capped}/{runs}" + (f" (LS {scap}/{sruns})" if sruns else "")
    mode = opts.get("withItemized", "loop")
    method = "LS" if opts.get("breakpointMethod") == "local-search" else "exact"
    obj = estate(p) if p.objective != "maxSpending" else float(p.basis)
    obj_name = "bequest" if p.objective != "maxSpending" else "spending"
    say(f"| {tag} | {mode} | {method} | {obj_name} {obj:,.0f} | {st_tax:,.0f} |"
        f" {item_yrs} / {item_tot:,.0f} | {st_yrs} / {st_tot:,.0f} |"
        f" {dt:.1f}s | bins {b} | nodes {nodes}{hit_txt} |")


def build(state, locality, *, pt=PT25, core=80000.0, mortgage=False, medical=0.0, charity=0.0,
          hsa=None, deferred=(900, 600), name="step6"):
    p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], name,
                 verbose=False, logstreams=[io.StringIO()])
    p.setSpendingProfile("budget")
    p.setAccountBalances(taxable=[150, 150], taxDeferred=list(deferred), taxFree=[75, 75],
                         hsa=list(hsa) if hsa else None)
    p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
    p.setRates("conservative")
    p.setSocialSecurity([3000, 2400], [70, 70])
    lines = [line("core", "core", core)]
    if pt:
        lines.append(line("pt", "property tax", pt))
    if medical:
        lines.append(line("med", "medical", medical))
    if charity:
        lines.append(line("ch", "charity", charity))
    p.houseLists["Budget"] = cond(pd.DataFrame(lines), "Budget")
    if mortgage:
        P, r, T = MORTGAGE
        p.houseLists["Debts"] = cond(pd.DataFrame([{
            "active": True, "name": "m", "type": "mortgage", "year": THISYEAR, "term": T,
            "amount": P, "rate": r}]), "Debts")
        p.Lambda_in[0, 0] = P
    if state:
        p.setStateTax(state, locality=locality)
    p.setExpirationYearOBBBA(YOBBBA)
    return p


def solve(p, objective, opts, **extra):
    my = dict(opts)
    my.update(extra)
    t = time.time()
    p.solve(objective, options=my)
    dt = time.time() - t
    if p.caseStatus != "solved":
        say(f"   !! {p._name}: {p.caseStatus} {p.solverMessage}")
    return dt


# ---------------------------------------------------------------------------
# Group: probe cases in-model
# ---------------------------------------------------------------------------
PROBE = [
    ("ny", "NY Yonkers owner $25k", "NY", "Yonkers", False),
    ("nymort", "NY Yonkers owner $25k + $600k mtg", "NY", "Yonkers", True),
    ("nj", "NJ owner $25k", "NJ", "", False),
    ("njmort", "NJ owner $25k + $600k mtg", "NJ", "", True),
]


def run_probe(ls=False):
    modes = ["none", "loop", "optimize"] if not ls else ["none", "optimize"]
    base = LS if ls else EXACT
    say(f"\n## probe{'-ls' if ls else ''} yOBBBA={YOBBBA} ({pd.Timestamp.today()})"
        f"  couple: $150k/$150k taxable, $900k/$600k deferred, core $80k + PT $25k")
    say("| case | withItemized | method | bequest | state tax | fed item yrs/tot | st item yrs/tot"
        " | time | binaries | nodes |")
    for key, name, state, loc, mort in PROBE:
        for mode in modes:
            p = build(state, loc, mortgage=mort, name=key)
            opts = dict(base)
            opts["withItemized"] = mode
            dt = solve(p, "maxBequest", opts)
            report(f"{key} {name}", p, dt, opts)


# ---------------------------------------------------------------------------
# Group: NY vs NJ owner at $20k and $25k (the 2026-10-07 table, with NY itemizing)
# ---------------------------------------------------------------------------
def run_nynj(ls=False):
    base = LS if ls else EXACT
    modes = ["none", "optimize"]
    say(f"\n## nynj{'-ls' if ls else ''} yOBBBA={YOBBBA} ({pd.Timestamp.today()})"
        "  NY vs NJ owner, maxBequest at netSpending 80 (housing_stakes recipe)")
    say("| case | withItemized | method | bequest | state tax | fed item yrs/tot | st item yrs/tot"
        " | time | binaries | nodes |")
    for pt in (20000.0, 25000.0):
        for state, loc in (("NY", "Yonkers"), ("NJ", "")):
            for mode in modes:
                p = build(state, loc, pt=pt, name=f"{state}-pt{int(pt/1000)}k")
                opts = dict(base)
                opts["withItemized"] = mode
                # housing_stakes recipe: budget profile, no netSpending (each plan spends its
                # own first-year total: core $80k + the property-tax line).
                dt = solve(p, "maxBequest", opts)
                report(f"{state} pt ${pt/1000:.0f}k", p, dt, opts)


# ---------------------------------------------------------------------------
# Group: Scenario 5 rent / buy cash / buy mortgage (budget profile, maxBequest)
# ---------------------------------------------------------------------------
HOME = 600000.0
RENT = 36000.0
PT_HOME = 15000.0
INS = 2500.0
MAINT = 6000.0
CLOSING = 0.02  # of price, as a negative big-ticket item
DOWN = 0.20


def run_housing(ls=False):
    base = LS if ls else EXACT
    modes = ["none", "optimize"]
    say(f"\n## housing{'-ls' if ls else ''} yOBBBA={YOBBBA} ({pd.Timestamp.today()})"
        f"  Scenario 5: rent ${RENT:,.0f} / cash ${HOME:,.0f} / mortgage"
        f" {100*DOWN:.0f}% down at {MORTGAGE[1]}%; core $80k; owner PT ${PT_HOME:,.0f}"
        f" + ins ${INS:,.0f} + maint ${MAINT:,.0f}; maxBequest, budget profile")
    say("| case | withItemized | method | bequest | state tax | fed item yrs/tot | st item yrs/tot"
        " | time | binaries | nodes |")

    def variant(kind, mode):
        p = owl.Plan(["Joe", "Jane"], ["1964-03-15", "1964-09-15"], [89, 92], f"housing-{kind}",
                     verbose=False, logstreams=[io.StringIO()])
        p.setSpendingProfile("budget")
        p.setAccountBalances(taxable=[500, 300], taxDeferred=[900, 600], taxFree=[75, 75])
        p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
        p.setRates("conservative")
        p.setSocialSecurity([3000, 2400], [70, 70])
        lines = [line("core", "core", 80000.0)]
        if kind == "rent":
            lines.append(line("rent", "rent", RENT))
        else:
            lines.append(line("pt", "property tax", PT_HOME))
            lines.append(line("ins", "insurance", INS))
            lines.append(line("maint", "maintenance", MAINT))
        p.houseLists["Budget"] = cond(pd.DataFrame(lines), "Budget")
        closing = HOME * CLOSING
        if kind == "cash":
            p.houseLists["Fixed Assets"] = cond(pd.DataFrame([{
                "active": True, "name": "home", "type": "residence", "year": THISYEAR,
                "basis": HOME, "value": HOME, "rate": 0.5, "yod": 0, "commission": 6.0}]),
                "Fixed Assets")
            p.Lambda_in[0, 0] = -(HOME + closing)
        elif kind == "mortgage":
            loan = HOME * (1 - DOWN)
            p.houseLists["Fixed Assets"] = cond(pd.DataFrame([{
                "active": True, "name": "home", "type": "residence", "year": THISYEAR,
                "basis": HOME, "value": HOME, "rate": 0.5, "yod": 0, "commission": 6.0}]),
                "Fixed Assets")
            p.houseLists["Debts"] = cond(pd.DataFrame([{
                "active": True, "name": "m", "type": "mortgage", "year": THISYEAR,
                "term": 30, "amount": loan, "rate": MORTGAGE[1], "property": "home"}]), "Debts")
            p.Lambda_in[0, 0] = -(HOME * DOWN + closing)
        p.setStateTax("NY", locality="Yonkers")
        p.setExpirationYearOBBBA(YOBBBA)
        opts = dict(base)
        opts["withItemized"] = mode
        dt = solve(p, "maxBequest", opts)
        report(kind, p, dt, opts)

    for kind in ("rent", "cash", "mortgage"):
        for mode in modes:
            variant(kind, mode)


# ---------------------------------------------------------------------------
# Group: HSA zmed/zmedf counts, and zmed ALWAYS_FREE vs family
# ---------------------------------------------------------------------------
def run_hsa():
    say(f"\n## hsa yOBBBA={YOBBBA} ({pd.Timestamp.today()})"
        "  test_hsa recipe: FL couple born 1958, core $40k + PT $20k + medical $30k, HSA $60k each")
    say("| case | withItemized | method | bequest | state tax | fed item yrs/tot | st item yrs/tot"
        " | time | binaries | nodes |")

    def hsa_plan(tag, **kw):
        p = owl.Plan(["Joe", "Jane"], ["1958-03-15", "1958-09-15"], [89, 92], tag,
                     verbose=False, logstreams=[io.StringIO()])
        p.setSpendingProfile("budget")
        p.setAccountBalances(taxable=[150, 150], taxDeferred=[900, 600], taxFree=[75, 75],
                             hsa=[60, 60])
        p.setAllocationRatios("individual", generic=np.array([[[60, 40, 0, 0], [60, 40, 0, 0]]] * 2))
        p.setRates("conservative")
        p.setSocialSecurity([3000, 2400], [70, 70])
        lines = [line("core", "core", kw.get("core", 40000.0)),
                 line("pt", "property tax", kw.get("pt", 20000.0)),
                 line("med", "medical", kw.get("medical", 30000.0))]
        p.houseLists["Budget"] = cond(pd.DataFrame(lines), "Budget")
        p.setStateTax("FL")
        p.setExpirationYearOBBBA(YOBBBA)
        return p

    for label, extra in (
        ("withMedicare=loop (test recipe)", {"withMedicare": "loop"}),
        ("withMedicare=optimize", {"withMedicare": "optimize"}),
    ):
        p = hsa_plan("hsa")
        opts = dict(EXACT)
        opts.update(withItemized="optimize", **extra)
        dt = solve(p, "maxBequest", opts)
        report(f"hsa {label}", p, dt, opts)
        say(f"   zmed {p.vm['zmed'].size if 'zmed' in p.vm else 0},"
            f" zmedf {p.vm['zmedf'].size if 'zmedf' in p.vm else 0},"
            f" zi {p.vm['zi'].size if 'zi' in p.vm else 0}")

    # zmed is the NY medical-floor switch: needs NY itemizing + medical. FL above has zmedf only.
    say("\n   zmed (NY) local-search placement: NY Yonkers, PT $25k, medical $3k, HSA $60k each,"
        " maxBequest, LS, withItemized=optimize:")
    for label, patch in (
        ("ALWAYS_FREE (as shipped)", None),
        ("family zmed", ("zmed",)),
    ):
        old_free, old_fam = localsearch.ALWAYS_FREE, localsearch.FAMILIES
        old_label = dict(localsearch.FAMILY_LABEL)
        if patch:
            localsearch.ALWAYS_FREE = tuple(f for f in old_free if f != "zmed")
            localsearch.FAMILIES = old_fam + ("zmed",)
            localsearch.FAMILY_LABEL = {**old_label, "zmed": "medical floor"}
        try:
            q = build("NY", "Yonkers", pt=25000.0, medical=3000.0, hsa=[60, 60], name="zmed-ls")
            opts = dict(LS)
            opts.update(withItemized="optimize")
            dt = solve(q, "maxBequest", opts)
            report(f"zmed NY LS zmed={label}", q, dt, opts)
            say(f"   zmed {q.vm['zmed'].size if 'zmed' in q.vm else 0},"
                f" zmedf {q.vm['zmedf'].size if 'zmedf' in q.vm else 0}")
        finally:
            localsearch.ALWAYS_FREE = old_free
            localsearch.FAMILIES = old_fam
            localsearch.FAMILY_LABEL = old_label


# ---------------------------------------------------------------------------
# Group: discretionary medical under maxSpending (the ~100 s loop case)
# ---------------------------------------------------------------------------
def run_med():
    say(f"\n## med yOBBBA={YOBBBA} ({pd.Timestamp.today()})"
        "  NY Yonkers owner $25k PT + medical $3k, maxSpending; zsi/zmed free under loop")
    say("| case | withItemized | method | bequest | state tax | fed item yrs/tot | st item yrs/tot"
        " | time | binaries | nodes |")
    for mode in ("none", "loop", "optimize"):
        for method, base in (("exact", EXACT), ("loop", {"noRothConversions": "None"})):
            if method == "loop" and mode == "none":
                continue
            p = build("NY", "Yonkers", pt=25000.0, medical=3000.0, name="med")
            opts = dict(base)
            opts["withItemized"] = mode
            if method == "loop":
                opts.pop("withSSTaxability", None)
            dt = solve(p, "maxSpending", opts)
            report(f"med maxSpending {mode}", p, dt, opts)

    say("\n   zmed as family vs ALWAYS_FREE (medical $3k, maxSpending, loop, withItemized=loop):")
    for label, patch in (
        ("ALWAYS_FREE (as shipped)", None),
        ("family zmed", ("zmed",)),
    ):
        old_free, old_fam = localsearch.ALWAYS_FREE, localsearch.FAMILIES
        if patch:
            localsearch.ALWAYS_FREE = tuple(f for f in old_free if f != "zmed")
            localsearch.FAMILIES = old_fam + ("zmed",)
        try:
            p = build("NY", "Yonkers", pt=25000.0, medical=3000.0, name="med-fam")
            opts = {"noRothConversions": "None", "withItemized": "loop"}
            dt = solve(p, "maxSpending", opts)
            report(f"med loop zmed={label}", p, dt, opts)
        finally:
            localsearch.ALWAYS_FREE = old_free
            localsearch.FAMILIES = old_fam


GROUPS = {
    "probe": lambda: run_probe(ls=False),
    "probe-ls": lambda: run_probe(ls=True),
    "nynj": lambda: run_nynj(ls=False),
    "nynj-ls": lambda: run_nynj(ls=True),
    "housing": lambda: run_housing(ls=False),
    "housing-ls": lambda: run_housing(ls=True),
    "hsa": run_hsa,
    "med": run_med,
}

only = sys.argv[1].split(";") if len(sys.argv) > 1 and sys.argv[1] != "all" else list(GROUPS)
say(f"=== Phase 3 step 6 measure, yOBBBA={YOBBBA}, plan starts {THISYEAR},"
    f" run {pd.Timestamp.today()} ===")
for key in only:
    GROUPS[key]()
say("=== done ===")
OUT.close()

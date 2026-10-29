"""
Run the household's scenario set on one case and write one readable report.

The scenarios are those of fork-notes/phase0/phase0-scenarios.md: when to stop working (full or
part time), when to claim SS, the deductions, the 2032 reversion, the marketplace benchmark, and
where, when and how to buy a condo (renting to the end is not an option: user, 2026-10-29), and
what a late-life care cost does to keeping it. Each scenario is solved the way `owlcli run` solves
a case (load_toml, the --set overrides, config_to_plan, the case's own [solver_options]), so a run
that works here works with owlcli too. The work sweep (claiming ages decided by branch-and-bound
at fixed ages, hours per variant) stays fork-notes/phase5/work_sweep.py.

Two uses, the same command:

- on the synthetic household (fork-notes/synthetic/make_cases.py), in the cloud or anywhere, to
  check that every scenario solves and that each modeled rule shows up where it should;
- on the real case, offline only, by the user (CLAUDE.md "Household data"), with the real case
  files and a scenario file of the same format in otherFiles/.

    .venv/bin/python fork-notes/synthetic/run_suite.py CASE.toml CONDO_CASE.toml SCENARIOS.json
        [--out-dir DIR] [--jobs N] [--only GROUP ...] [--report-from results.json]

CASE.toml is the baseline: the Phase 0 template filled in (maxSpending, bequest 0, budget profile,
claiming ages searched), whose workbook holds a reference purchase (rent until it, own after).
CONDO_CASE.toml is the same household with breakpointMethod = "local-search". SCENARIOS.json
holds "work" ({name, what, set, hfp}: `set` items are `--set` specs; `hfp` edits the case's
workbook per person and year, the format of work_sweep.py), "extra" (more main scenarios in the
same format, such as one that claims before FRA while working, for the earnings test), "grid"
({name, what, set, place, year, financing}: each its own workbook, named relative to the case),
"ltc" (the first is the base of its group) and "reference" (the grid entry that equals the
baseline).

Groups, each against its own base (its first row):

- "main": the baseline (claiming ages searched in two stages, two_stage_ages: under the exact LP,
  then the pick and its +-1-year neighbours at fixed ages under the case's model), the work
  variants, both claiming at 62, 67 or 70, no itemizing, the 2032 reversion, the 2027 benchmark,
  Roth conversions from 2027 or none. Differences under 1% are marked `~`: loop noise can make
  them, with either sign (CLAUDE.md "Loop noise").
- "condo" (local search) and "condo-exact" (exact LP: Medicare off, SS taxability 0.85): the
  reference purchase, then every grid variant, at the claiming ages the baseline chose. A pivot
  shows the purchase year against place and financing; a table puts local search and the exact LP
  side by side: a difference counts when both give it the same sign and it exceeds their spread.
- "ltc": a care cost late in life with the condo kept or sold to pay for it.

Scores. With essential budget lines under maxSpending, net spending is the essential lines at
their amounts plus k x the discretionary lines, so the comparable score is the first year's
discretionary spending, k x D_0 ($/yr; the same discretionary lines in every variant), not the
spending basis (which also holds the first year's essential lines). Without essential lines the
score is the spending basis; under maxBequest, the final bequest. Beside it, what is left at the
end in today's dollars: savings (bequest 0 spends them) and the home net of commission and of any
loan still owed ("home at the end", the reserve for care). A cheaper or later purchase can buy
more spending with less home at the end: the report shows both and does not add them.

Out-dir (default: suite/ next to CASE.toml): per run, the workbook `owlcli run` writes
(<group>_<scenario>.xlsx), its Summary as text (.txt) and its log (.log); edited workbooks
(HFP_<group>_<scenario>.xlsx); results.json (every metric of every run; --report-from reprints
the report from it); report.md.

Plans start today: compare only runs made the same day.
"""

import argparse
import copy
import importlib.util
import io
import json
import multiprocessing as mp
import os
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from owlplanner import __version__  # noqa: E402
from owlplanner.cli.set_override import apply_overrides  # noqa: E402
from owlplanner.config import config_to_plan, load_toml  # noqa: E402
from owlplanner.config.schema import parse_solver_options  # noqa: E402
from owlplanner.export import build_summary_string, plan_metrics  # noqa: E402

_spec = importlib.util.spec_from_file_location("work_sweep", ROOT / "fork-notes" / "phase5" / "work_sweep.py")
work_sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(work_sweep)

_NUM = re.compile(r"\$?\d[\d,]*(?:\.\d+)?(?![\d.,%])")  # amounts and counts; a percentage stays
EXACT = ["solver_options.breakpointMethod=loop", "solver_options.withMedicare=none",
         "solver_options.withSSTaxability=0.85"]

# Lifetime amounts in the cost tables, today's dollars (plan_metrics keys, plus the fork's state-tax
# parts and the STAR credit added in solve_one()).
COSTS = [
    ("wages_today", "Wages"),
    ("ss_income_today", "SS"),
    ("federal_income_tax_today", "Fed. ordinary"),
    ("ltcg_tax_today", "Fed. gains"),
    ("niit_today", "NIIT"),
    ("payroll_tax_today", "Payroll"),
    ("state_tax_today", "State+local"),
    ("state_recapture_today", "of which recapture"),
    ("local_tax_today", "of which local"),
    ("star_credit_today", "STAR"),
    ("medicare_today", "Medicare"),
    ("aca_today", "ACA"),
    ("ss_withheld_today", "SS withheld"),
    ("roth_conversions_year1", "Roth conv. 2026"),
    ("roth_conversions_today", "Roth conv."),
    ("itemized_deductions_today", "Fed. itemized"),
    ("state_itemized_today", "NY itemized"),
    ("debt_payments_today", "Debt paid"),
    ("housing_costs_today", "Housing"),
]


def fixed_ages(ages):
    return ["solver_options.withSSAges=fixed", f"fixed_income.social_security_ages={json.dumps(ages)}"]


def scenario_groups(case, condo, scen):
    """Return [(group, case_file, group_sets, rows, ages_from_base)]; rows = [(name, what, sets, hfp, extra)]."""
    main = [("base", "the case as written", [], None, {})]
    # A work entry without workbook edits repeats the baseline (a check that a rerun gives the same plan).
    main += [(w["name"], w["what"], w["set"], w.get("hfp"), {}) for w in scen.get("work", [])]
    main += [(w["name"], w["what"], w["set"], w.get("hfp"), {}) for w in scen.get("extra", [])]
    main += [
        ("ss-62", "both claim at 62", fixed_ages([62.0, 62.0]), None, {}),
        ("ss-67", "both claim at 67 (FRA)", fixed_ages([67.0, 67.0]), None, {}),
        ("ss-70", "both claim at 70", fixed_ages([70.0, 70.0]), None, {}),
        ("no-itemizing", "standard deduction only (federal and NY)", ["solver_options.withItemized=none"], None, {}),
        ("obbba-2032", "pre-TCJA federal law from 2032 (Owl's default)",
         ["rates_selection.obbba_expiration_year=2032"], None, {}),
        ("slcsp-2027", "2027 marketplace benchmark (25.29 $k)", ["aca_settings.slcsp_annual=25.29"], None, {}),
        ("roth-from-2027", "no Roth conversion in 2026 (conversions from 2027)",
         ["solver_options.startRothConversions=2027"], None, {}),
        ("no-roth", "no Roth conversions at all", ["solver_options.maxRothConversion=0"], None, {}),
    ]
    ref = scen.get("reference")
    grid = [(g["name"], g["what"], g["set"], None, {k: g[k] for k in ("place", "year", "financing") if k in g})
            for g in scen.get("grid", [])]
    ref_row = [("reference", f"the baseline's purchase ({ref})", [], None,
                next((r[4] for r in grid if r[0] == ref), {}))]
    grid = [r for r in grid if r[0] != ref]
    # The Roth questions again under local search and the exact LP: the main group's method (branch-
    # and-bound on IRMAA, loop on the rest) converted nothing in 2026 where local search converted
    # $40,000 on the same case and ages (synthetic run 2026-10-29-c), so one method does not settle it.
    roth = [("roth-from-2027", "the reference, no Roth conversion in 2026 (conversions from 2027)",
             ["solver_options.startRothConversions=2027"], None, {}),
            ("no-roth", "the reference, no Roth conversions at all", ["solver_options.maxRothConversion=0"], None, {})]
    ltc = [(t["name"], t["what"], t["set"], None, {}) for t in scen.get("ltc", [])]
    groups = [("main", case, [], main, False),
              ("condo", condo, [], ref_row + roth + grid, True),
              ("condo-exact", condo, EXACT, ref_row + roth + grid, True)]
    if ltc:
        groups.append(("ltc", condo, [], ltc, True))
    return groups


def _hfp_of(sets):
    for s in sets:
        if s.startswith("household_financial_profile.HFP_file_name="):
            return s.split("=", 1)[1]
    return None


def build(spec, base_ages, out_dir):
    """Turn the groups into jobs (group, name, what, case_file, overrides, extra), writing edited workbooks."""
    jobs, skipped = [], []
    for group, case_file, gsets, rows, from_base in spec:
        diconf, dirname, _ = load_toml(str(case_file))
        ages = fixed_ages(base_ages) if from_base and base_ages is not None else []
        for name, what, sets, hfp_edits, extra in rows:
            sets = gsets + ages + list(sets)
            hfp = _hfp_of(sets) or diconf["household_financial_profile"]["HFP_file_name"]
            src = hfp if os.path.isabs(hfp) else os.path.join(dirname, hfp)
            if not os.path.exists(src):
                skipped.append((group, name, f"workbook {hfp} not found next to {case_file}"))
                continue
            if hfp_edits:
                dst = os.path.join(out_dir, f"HFP_{group}_{name}.xlsx")
                work_sweep.edit_hfp(src, dst, hfp_edits)
                sets.append(f"household_financial_profile.HFP_file_name={dst}")
                extra = {**extra, "hfp_edits": hfp_edits}
            jobs.append((group, name, what, str(case_file), sets, extra))
    return jobs, skipped


def _plan(diconf, dirname, buf, sets=()):
    d = apply_overrides(diconf, list(sets)) if sets else copy.deepcopy(diconf)
    return config_to_plan(d, dirname, verbose=True, logstreams=[buf], loadHFP=True)


def _solve(p):
    p.solve(p.objective, parse_solver_options(dict(p.solverOptions)))
    return p


def two_stage_ages(diconf, dirname, buf):
    """Claiming ages for a case that searches them, without Owl's own search on the full model.

    Stage 1: the case's own withSSAges search under the exact LP (Medicare off, SS taxability 0.85),
    a pure LP per candidate (about 0.5 s on the synthetic case). Unlike work_sweep.py stage (a), ACA
    stays on the loop: withACA="optimize" makes each candidate a MIP (9 s there, so about 10 minutes
    for the search's ~270 candidates), and the exact LP mis-prices the ACA years even then
    (plan-review-2026-10-22.md §3.2). Stage 2: the pick and each searched person's pick +-1 year (clipped
    to 62-70, one person at a time), each solved at fixed ages under the case's own model; the best
    score wins. Owl's search on the full model makes every candidate a branch-and-bound MIP: on the
    synthetic case with brokerage-heavy balances one search ran past 20 minutes (2026-10-29).
    Returns (ages, candidates) with candidates = [(ages, score or None)].
    """
    p = _solve(_plan(diconf, dirname, buf, EXACT))
    if p.caseStatus != "solved":
        raise RuntimeError(f"stage 1 (exact LP age search) did not solve: {p.caseStatus}")
    pick = [float(a) for a in p.ssecAges]
    sel = diconf.get("solver_options", {}).get("withSSAges", "optimize")
    names = list(p.inames)
    free = range(len(names)) if str(sel).lower() == "optimize" else [names.index(n) for n in sel]
    trials = [pick]
    for i in free:
        for d in (-1.0, 1.0):
            a = min(70.0, max(62.0, pick[i] + d))  # clipped: a 69y10m pick still tries 70
            if abs(a - pick[i]) > 1e-6:
                t = list(pick)
                t[i] = a
                trials.append(t)
    cands = []
    for t in trials:
        q = _solve(_plan(diconf, dirname, buf, fixed_ages(t)))
        cands.append(([round(float(a), 4) for a in q.ssecAges],
                      _score_plan(q) if q.caseStatus == "solved" else None))
    good = [c for c in cands if c[1] is not None]
    if not good:
        raise RuntimeError("stage 2: no candidate ages solved")
    return max(good, key=lambda c: c[1])[0], cands


def _score_plan(p):
    m = plan_metrics(p)
    if p.objective != "maxSpending":
        return m["final_bequest_today"]
    k = m.get("discretionary_scale")
    return k * float(p.budget.discretionary_n[0]) if k is not None else m["spending_basis"]


def _arr(p, attr):
    return np.asarray(getattr(p, attr, np.zeros(p.N_n)))[: p.N_n]


def solve_one(job, out_dir):
    group, name, what, case_file, sets, extra = job
    stem = f"{group}_{name}"
    t0 = time.time()
    rec = {"group": group, "name": name, "what": what, "overrides": sets, "case": case_file, **extra}
    buf, sbuf = io.StringIO(), io.StringIO()  # the final solve's log; the age stages' log
    try:
        diconf, dirname, _ = load_toml(case_file)
        diconf = apply_overrides(diconf, sets)
        if str(diconf.get("solver_options", {}).get("withSSAges", "fixed")).lower() != "fixed":
            ages, cands = two_stage_ages(diconf, dirname, sbuf)
            rec["age_candidates"] = cands
            diconf = apply_overrides(diconf, fixed_ages(ages))
        p = _solve(_plan(diconf, dirname, buf))
        rec["status"] = p.caseStatus
        rec["objective"] = p.objective
        if p.caseStatus == "solved":
            m = plan_metrics(p)
            inv_g = 1.0 / p.gamma_n[: p.N_n]
            m["state_recapture_today"] = float(np.sum(_arr(p, "st_recap_n") * inv_g))
            m["local_tax_today"] = float(np.sum(_arr(p, "lt_T_n") * inv_g))
            m["star_credit_today"] = float(np.sum(_arr(p, "st_star_n") * inv_g))
            m["home_at_end_today"] = m["final_bequest_today"] - m["final_bequest_savings_today"]
            m["roth_conversions_year1"] = float(np.sum(p.x_in[:, 0]))
            k = m.get("discretionary_scale")
            if k is not None:
                m["discretionary_year1"] = k * float(p.budget.discretionary_n[0])
                m["essential_year1"] = float(p.budget.essential_n[0])
            rec["metrics"] = m
            rec["ages"] = [round(float(a), 4) for a in p.ssecAges]
            rec["names"] = list(p.inames)
            rec["convergence"] = p.convergenceType
            rec["method"] = getattr(p, "breakpointMethodUsed", "loop")
            rec["error_bar"] = float(p.oscillationAbs) / 2.0
            p.saveWorkbook(basename=os.path.join(out_dir, stem + ".xlsx"), overwrite=True, with_config="first")
            with open(os.path.join(out_dir, stem + ".txt"), "w", encoding="utf-8") as f:
                f.write(f"{group} / {name}: {what}\nOverrides: {sets}\n\n")
                f.write(build_summary_string(p))
                f.write("\n")
        else:
            rec["error"] = p.solverMessage
    except Exception as e:  # a scenario that breaks is a finding: record it and go on
        rec["status"] = "exception"
        rec["error"] = f"{type(e).__name__}: {e}"
        buf.write(traceback.format_exc())
    log = buf.getvalue()
    with open(os.path.join(out_dir, stem + ".log"), "w", encoding="utf-8") as f:
        if sbuf.getvalue():
            f.write("===== claiming-age stages (their warnings are not in the report) =====\n")
            f.write(sbuf.getvalue())
            f.write("===== final solve =====\n")
        f.write(log)
    rec["warnings"] = sorted({ln.split("|", 3)[-1].strip() if "|" in ln else ln.strip()
                              for ln in log.splitlines() if "WARNING" in ln or "ERROR" in ln})
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def _run(args):
    return solve_one(*args)


# ----- report -----------------------------------------------------------------------------------
def score(rec):
    m = rec["metrics"]
    if rec["objective"] != "maxSpending":
        return m["final_bequest_today"]
    return m.get("discretionary_year1", m["spending_basis"])


def score_label(rec):
    if rec["objective"] != "maxSpending":
        return "final bequest ($, today's)"
    if "discretionary_year1" in rec["metrics"]:
        return "first year's discretionary spending ($/yr, today's)"
    return "spending basis ($/yr, today's)"


def money(x):
    return f"{x:,.0f}"


def signed(x):
    return f"{x:+,.0f}"


def ym(a):
    mo = int(round(a * 12))
    return f"{mo // 12}y{mo % 12}m"


def ages_text(rec):
    return ", ".join(f"{n} {ym(a)}" for n, a in zip(rec["names"], rec["ages"], strict=True))


def solved(r):
    return r is not None and r.get("status") == "solved"


def group_table(g, rows):
    base = rows[0]
    out = [f"## {g}", ""]
    if solved(base):
        out += [f"Objective {base['objective']}; score = {score_label(base)}. Base: `{base['name']}`"
                + (f", overrides `{' '.join(base['overrides'])}`" if base["overrides"] else "") + ". "
                "*Savings left* (after heirs' tax): bequest 0 is a floor, so this is what repays a loan still owed "
                "at the end, or money the budget's shape cannot spend (a sale late in the plan), else 0. *Home at "
                "the end*: the home net of commission and of any loan left.", ""]
    out += ["| scenario | what changes | score | vs base | % | savings left | home at the end | claiming ages | "
            "method / convergence | s |", "|---|---|---:|---:|---:|---:|---:|---|---|---:|"]
    for r in rows:
        if not solved(r):
            err = r.get("error", "")[:120]
            out.append(f"| {r['name']} | {r['what']} | **{r.get('status')}** | | | | | | {err} | {r['seconds']} |")
            continue
        s, m = score(r), r["metrics"]
        d = pct = ""
        if solved(base) and r is not base:
            s0 = score(base)
            d = signed(s - s0)
            pc = 100 * (s - s0) / abs(s0) if s0 else 0.0
            pct = f"{pc:+.2f}{' ~' if g == 'main' and abs(pc) < 1 and abs(s - s0) > 0.5 else ''}"
        left = money(m["final_bequest_savings_today"])
        out.append(f"| {r['name']} | {r['what']} | {money(s)} | {d} | {pct} | {left} "
                   f"| {money(m['home_at_end_today'])} | {ages_text(r)} | {r['method']} / {r['convergence']} | "
                   f"{r['seconds']} |")
    ok = [r for r in rows if solved(r)]
    if solved(base) and len(ok) > 1:
        shown = [(k, lab) for k, lab in COSTS if any(abs(r["metrics"].get(k, 0.0)) > 0.5 for r in ok)]
        out += ["", "Lifetime amounts, today's $: the base's, then each variant's difference.", "",
                "| " + " | ".join(["scenario"] + [lab for _, lab in shown]) + " |", "|---|" + "---:|" * len(shown)]
        for r in ok:
            cells = [money(base["metrics"].get(k, 0.0)) if r is base else
                     signed(r["metrics"].get(k, 0.0) - base["metrics"].get(k, 0.0)) for k, _ in shown]
            out.append("| " + " | ".join([r["name"]] + cells) + " |")
    return out + [""]


def condo_pivot(rows, group):
    """Place x financing rows, purchase years as columns: score difference from the reference, home at the end."""
    ref = rows[0]
    cells = [r for r in rows if "year" in r]
    if not solved(ref) or not cells:
        return []
    years = sorted({r["year"] for r in cells})
    keys = []
    for r in cells:
        if (r["place"], r["financing"]) not in keys:
            keys.append((r["place"], r["financing"]))
    out = [f"### {group}: where, when, how", "",
           f"Each cell: the score's difference from the reference purchase ({ref['what']}: "
           f"{money(score(ref))}), and below it the home at the end (today's $). The best year per row in bold, "
           "by score only.", "",
           "| place, financing | " + " | ".join(str(y) for y in years) + " |", "|---|" + "---:|" * len(years)]
    for place, fin in keys:
        row = {r["year"]: r for r in cells if r["place"] == place and r["financing"] == fin}
        good = {y: r for y, r in row.items() if solved(r)}
        best = max(good, key=lambda y: score(good[y])) if good else None
        vals = []
        for y in years:
            r = row.get(y)
            if r is None:
                vals.append("")
            elif not solved(r):
                vals.append(f"**{r.get('status')}**")
            else:
                d = signed(score(r) - score(ref))
                vals.append(f"{'**' + d + '**' if y == best else d}<br>{money(r['metrics']['home_at_end_today'])}")
        out.append(f"| {place}, {fin} | " + " | ".join(vals) + " |")
    return out + [""]


def agreement(by, ls, ex, base_name):
    """The same variant under local search and under the exact LP: the decision rule of CLAUDE.md "Loop noise"."""
    rows = []
    for (g, n), r in by.items():
        if g != ls or n == base_name or (ex, n) not in by:
            continue
        quad = [by.get((ls, base_name)), r, by.get((ex, base_name)), by.get((ex, n))]
        if not all(solved(x) for x in quad):
            continue
        d_ls, d_ex = score(quad[1]) - score(quad[0]), score(quad[3]) - score(quad[2])
        spread = abs(d_ls - d_ex)
        bars = sum(x["error_bar"] for x in quad)
        if (d_ls > 0) != (d_ex > 0):
            verdict = "unresolved: the two disagree on the sign"
        elif min(abs(d_ls), abs(d_ex)) <= spread + bars:
            verdict = "unresolved: smaller than the spread" + (" and error bars" if bars > 0.5 else "")
        else:
            verdict = "resolved: " + ("ahead of" if d_ls > 0 else "behind") + f" the {base_name}"
        rows.append(f"| {n} | {signed(d_ls)} | {signed(d_ex)} | {money(spread)} | {money(bars)} | {verdict} |")
    if not rows:
        return []
    return [f"### {ls} vs {ex}", "",
            "Score difference from the reference under local search and under the exact LP (Medicare off, SS "
            "taxability 0.85: a different model, so only its differences compare). A difference counts when both "
            "give it the same sign and it is larger than their spread plus the error bars of the four runs (a loop "
            "that did not settle).", "",
            "| scenario | local search | exact LP | spread | error bars | reading |", "|---|---:|---:|---:|---:|---|",
            *rows, ""]


def age_decisions(recs):
    """The two-stage claiming-age decisions: each candidate's score under the case's own model."""
    rows = [r for r in recs if r.get("age_candidates")]
    if not rows:
        return []
    out = ["## Claiming ages: two-stage decisions", "",
           "Stage 1 searched the ages under the exact LP; its pick is the first candidate. Stage 2 scored it and "
           "its +-1-year neighbours at fixed ages under the case's model; the chosen ages are in bold. Candidates "
           "within loop noise of each other (under about 1%, CLAUDE.md \"Loop noise\") are a tie, not a pick: "
           "read the bold ages as the neighbourhood the model prefers.", "",
           "| scenario | candidates (ages: score) |", "|---|---|"]
    for r in rows:
        best = max((c for c in r["age_candidates"] if c[1] is not None), key=lambda c: c[1], default=None)
        cells = []
        for ages, sc in r["age_candidates"]:
            txt = " / ".join(ym(a) for a in ages) + ": " + (money(sc) if sc is not None else "not solved")
            cells.append(f"**{txt}**" if best is not None and list(ages) == list(best[0]) else txt)
        out.append(f"| {r['group']}/{r['name']} | {'; '.join(cells)} |")
    return out + [""]


def feature_checks(by):
    """Each modeled rule shows up where the scenario says it should: (label, ok, detail)."""
    out = []

    def val(g, n, k):
        r = by.get((g, n))
        return r["metrics"].get(k) if solved(r) else None

    def check(label, g, n, k, pred, ref=None):
        v = val(g, n, k)
        rv = val(*ref, k) if ref else None
        if v is None or (ref and rv is None):
            out.append((label, None, f"{g}/{n}" + (f" or {ref[0]}/{ref[1]}" if ref else "") + " not solved or absent"))
            return
        ok = pred(v) if ref is None else pred(v, rv)
        out.append((label, ok, f"{k} = {money(v)}" + (f" vs {money(rv)} in {ref[0]}/{ref[1]}" if ref else "")))

    pos = lambda v: v > 0  # noqa: E731
    zero = lambda v: abs(v) < 0.5  # noqa: E731
    more = lambda v, r: v > r  # noqa: E731
    less = lambda v, r: v < r  # noqa: E731
    check("Payroll tax on the 2026 wages", "main", "base", "payroll_tax_today", pos)
    check("Marketplace premiums before 65", "main", "base", "aca_today", pos)
    check("Medicare premiums from 65", "main", "base", "medicare_today", pos)
    check("Yonkers surcharge (living in Yonkers)", "main", "base", "local_tax_today", pos)
    check("STAR credit for the owner (from the purchase)", "main", "base", "star_credit_today", pos)
    check("Savings spent by the end (bequest 0)", "main", "base", "final_bequest_savings_today", lambda v: v < 1000)
    check("The condo kept to the end", "main", "base", "home_at_end_today", pos)
    for n in [n for (g, n) in by if g == "main" and n.startswith(("ari-", "noa-", "both-")) and n != "both-stop-2026"]:
        check(f"{n}: more wages than stopping in 2026", "main", n, "wages_today", more, ("main", "base"))
    check("Full-time work in 2027 adds payroll tax", "main", "both-full-2027", "payroll_tax_today", more,
          ("main", "base"))
    check("Earnings test withholds SS: claim at 62 while working part time", "main", "noa-part-claim-62",
          "ss_withheld_today", pos)
    check("Claiming at 62 pays less SS over the plan than at 70", "main", "ss-62", "ss_income_today", less,
          ("main", "ss-70"))
    check("No itemizing: no federal itemized deduction", "main", "no-itemizing", "itemized_deductions_today", zero)
    check("No itemizing: no NY itemized deduction", "main", "no-itemizing", "state_itemized_today", zero)
    check("2032 reversion changes the federal tax", "main", "obbba-2032", "federal_income_tax_today",
          lambda v, r: abs(v - r) > 1, ("main", "base"))
    check("Roth conversions in the baseline", "main", "base", "roth_conversions_today", pos)
    check("No Roth conversion in 2026 when they start in 2027", "main", "roth-from-2027", "roth_conversions_year1",
          zero)
    check("No Roth conversions at all", "main", "no-roth", "roth_conversions_today", zero)
    check("No Roth conversion in 2026 under local search either", "condo", "roth-from-2027", "roth_conversions_year1",
          zero)
    check("Higher benchmark raises marketplace premiums", "main", "slcsp-2027", "aca_today", more, ("main", "base"))
    for place in ("yonkers", "whiteplains", "queens"):
        if place != "yonkers":
            check(f"{place} 2027 cash: STAR credit for the owner", "condo", f"{place}-2027-cash", "star_credit_today",
                  pos)
            check(f"{place} 2027 cash: home at the end", "condo", f"{place}-2027-cash", "home_at_end_today", pos)
            check(f"{place} 2027 cash: NY itemizes the property tax", "condo", f"{place}-2027-cash",
                  "state_itemized_today", pos)
        check(f"{place} 2027 mortgage: loan payments", "condo", f"{place}-2027-mortgage", "debt_payments_today", pos)
        check(f"{place} 2027 mortgage: interest itemized federally", "condo", f"{place}-2027-mortgage",
              "itemized_deductions_today", pos)
    check("White Plains: no Yonkers surcharge after the move", "condo", "whiteplains-2027-cash", "local_tax_today",
          less, ("condo", "reference"))
    check("Queens: NYC tax above the Yonkers surcharge", "condo", "queens-2027-cash", "local_tax_today", more,
          ("condo", "reference"))
    check("A later purchase pays more rent first", "condo", "yonkers-2038-cash", "housing_costs_today", more,
          ("condo", "reference"))
    check("Care, condo sold: no home at the end", "ltc", "ltc-sell", "home_at_end_today", zero)
    check("Care, condo kept: home at the end", "ltc", "ltc-keep", "home_at_end_today", pos)
    check("Care, condo kept: the care lowers discretionary spending", "ltc", "ltc-keep", "discretionary_year1", less,
          ("condo", "reference"))
    return out


def run_checks(rec):
    """Problems with one run, whatever the scenario."""
    if not solved(rec):
        return [f"not solved: {rec.get('status')} ({rec.get('error', '')})"]
    issues = []
    if rec["convergence"] in ("max iteration", "unsolvable iterate", "undefined"):
        issues.append(f"convergence: {rec['convergence']}")
    if rec["error_bar"] > 0.5:
        issues.append(f"loop did not settle: objective error bar ±{money(rec['error_bar'])} ({rec['convergence']})")
    for w in rec["warnings"]:
        if "Cash flow balance" in w or "infeasible" in w.lower() or "maximum iterations" in w:
            issues.append(w)
    return issues


def report(recs, skipped, out_dir, header):
    by = {(r["group"], r["name"]): r for r in recs}
    lines = [f"# Scenario suite: {os.path.basename(header['case'])}", "",
             f"Run {header['when']} with Owl {header['version']}, {header['jobs']} jobs, {header['seconds']:.0f} s. "
             "Plans start today: compare only runs from the same day. Amounts in today's dollars.", "",
             f"Claiming ages chosen by the baseline: {header.get('base_ages_text', 'n/a')}; every group but main runs "
             "at those ages.", ""]
    groups = []
    for r in recs:
        if r["group"] not in groups:
            groups.append(r["group"])
    for g in groups:
        rows = [r for r in recs if r["group"] == g]
        lines += group_table(g, rows)
        if g.startswith("condo"):
            lines += condo_pivot(rows, g)
    lines += agreement(by, "condo", "condo-exact", "reference")
    lines += age_decisions(recs)
    lines += ["## Run checks", ""]
    bad = [(r, i) for r in recs for i in run_checks(r)]
    if not bad:
        lines += ["Every run solved, its loop settled (error bar 0) and its log has no cash-flow or infeasibility "
                  "warning.", ""]
    lines += [f"- {r['group']}/{r['name']}: {i}" for r, i in bad]
    if skipped:
        lines += ["", "Skipped:", ""] + [f"- {g}/{n}: {why}" for g, n, why in skipped]
    lines += ["", "## Feature checks", "",
              "Each line checks that a modeled rule shows up in the scenario that should trigger it, not that its "
              "amount is right.", "", "| check | result | detail |", "|---|---|---|"]
    for label, ok, detail in feature_checks(by):
        lines.append(f"| {label} | {'ok' if ok else ('n/a' if ok is None else '**FAIL**')} | {detail} |")
    lines += ["", "## Warnings in the logs", "",
              "Owl's warnings from each run's final solve, grouped by message (amounts as #, with their range).", ""]
    groups = {}
    for r in recs:
        for w in r.get("warnings", []):
            key = _NUM.sub("#", w)
            g = groups.setdefault(key, {"runs": [], "nums": []})
            if f"{r['group']}/{r['name']}" not in g["runs"]:
                g["runs"].append(f"{r['group']}/{r['name']}")
            first = _NUM.search(w)
            if first:
                g["nums"].append(first.group(0))
    if not groups:
        lines.append("None.")
    for key, g in sorted(groups.items(), key=lambda kv: -len(kv[1]["runs"])):
        nums = sorted({n for n in g["nums"]}, key=lambda n: float(n.lstrip("$").replace(",", "") or 0))
        rng = f"; first amount {nums[0]}" + (f" to {nums[-1]}" if len(nums) > 1 else "") if nums else ""
        where = g["runs"]
        lines.append(f"- {key}  \n  ({len(where)} run(s){rng}: {', '.join(where[:6])}"
                     f"{' ...' if len(where) > 6 else ''})")
    lines += ["", f"Per run: `<group>_<scenario>.xlsx` (the workbook `owlcli run` writes), `.txt` (its Summary as "
              f"text), `.log`. All in `{out_dir}`.", ""]
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case", nargs="?")
    ap.add_argument("condo", nargs="?")
    ap.add_argument("scenarios", nargs="?")
    ap.add_argument("--out-dir")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2,
                    help="parallel runs (spawned processes); a run that searches claiming ages does its "
                         "two stages in its own process")
    ap.add_argument("--only", nargs="*",
                    help="groups or group/scenario names to run besides main/base (e.g. condo ltc main/ss-62)")
    ap.add_argument("--report-from", help="results.json of an earlier run: reprint its report without solving")
    args = ap.parse_args()

    if args.report_from:
        with open(args.report_from, encoding="utf-8") as f:
            saved = json.load(f)
        print(report(saved["runs"], saved["skipped"], os.path.dirname(os.path.abspath(args.report_from)),
                     saved["header"]))
        return
    if not (args.case and args.condo and args.scenarios):
        ap.error("CASE.toml, CONDO_CASE.toml and SCENARIOS.json are required (or --report-from).")
    case, condo = Path(args.case).resolve(), Path(args.condo).resolve()
    with open(args.scenarios, encoding="utf-8") as f:
        scen = json.load(f)
    out_dir = Path(args.out_dir or case.parent / "suite").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = scenario_groups(case, condo, scen)
    t0 = time.time()

    # The baseline first: the other groups run at the claiming ages it chose.
    jobs, _ = build(spec[:1], None, str(out_dir))
    base = solve_one(jobs[0], str(out_dir))
    print(f"main/base: {base['status']} in {base['seconds']} s", flush=True)
    base_ages = base.get("ages")
    jobs, skipped = build(spec, base_ages, str(out_dir))
    order = {(j[0], j[1]): i for i, j in enumerate(jobs)}
    jobs = jobs[1:]
    if args.only:
        jobs = [j for j in jobs if j[0] in set(args.only) or f"{j[0]}/{j[1]}" in set(args.only)]
    recs = [base]
    with ProcessPoolExecutor(max_workers=args.jobs, mp_context=mp.get_context("spawn")) as pool:
        for rec in pool.map(_run, [(j, str(out_dir)) for j in jobs]):
            print(f"{rec['group']}/{rec['name']}: {rec['status']} in {rec['seconds']} s", flush=True)
            recs.append(rec)
    recs.sort(key=lambda r: order.get((r["group"], r["name"]), -1))
    header = {"case": str(case), "condo": str(condo), "scenarios": str(Path(args.scenarios).resolve()),
              "when": datetime.now().strftime("%Y-%m-%d %H:%M"), "version": __version__, "jobs": args.jobs,
              "seconds": time.time() - t0,
              "base_ages_text": ages_text(base) if solved(base) else "baseline not solved"}
    with open(out_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump({"header": header, "skipped": skipped, "runs": recs}, f, indent=1, default=float)
    print(report(recs, skipped, str(out_dir), header))


if __name__ == "__main__":
    main()

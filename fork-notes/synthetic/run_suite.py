"""
Run the household's scenario set on one case and write one readable report.

The scenarios are those of fork-notes/phase0/phase0-scenarios.md, sections 1-6 (section 4's work
sweep is fork-notes/phase5/work_sweep.py, run separately: it takes hours). Each scenario is solved
the way `owlcli run` solves a case (load_toml, the --set overrides, config_to_plan, the case's own
[solver_options]), so a run that works here works with owlcli too.

Two uses, the same scenarios:

- On the synthetic household (fork-notes/synthetic/make_cases.py), in the cloud or anywhere: to
  check that every scenario solves and that each modeled feature shows up where it should (the
  feature checks at the end of the report).
- On the real case, offline only, by the user (CLAUDE.md "Household data"): the same command with
  the real case files, which stay in otherFiles/.

    .venv/bin/python fork-notes/synthetic/run_suite.py CASE.toml HOUSING_CASE.toml [--out-dir DIR]
        [--jobs N] [--only NAME ...] [--report-from results.json]

CASE.toml is the baseline (the Phase 0 template filled in: maxSpending, budget profile, claiming
ages searched). HOUSING_CASE.toml is the rent base of section 5 (maxBequest, local search, no
netSpending). The other workbooks are found next to each case by suffix, from the case's own
HFP_file_name: for HFP_x.xlsx, HFP_x_2027.xlsx (work one more year), HFP_x_oneworks.xlsx (one keeps
working), and next to the housing case, for HFP_y_rent.xlsx, HFP_y_buy_cash.xlsx,
HFP_y_buy_mortgage.xlsx and HFP_y_move.xlsx. A scenario whose workbook is missing is skipped and
listed as such. `--move-district` names the NY school district of the move scenario.

How the groups are compared:

- "main": each scenario against the baseline, with every option as the case sets it (claiming ages
  searched where the case says so). Under the default loop, differences under about 1% can be loop
  noise with either sign (CLAUDE.md "Loop noise"): the report marks them.
- "residency-ls" and "residency-exact": the residency variants again, at the claiming ages the
  baseline chose, under local search and under the exact LP (Medicare off, SS taxability 0.85).
  Read a residency difference as resolved only when both agree on its sign and it is larger than
  their spread.
- "housing" (local search) and "housing-exact": the buy variants against renting, maxBequest, read
  as final_bequest_today (savings after heirs' tax plus the home net of commission, less debt), at
  the baseline's claiming ages.

Out-dir (default: next to CASE.toml, in suite/): one workbook (<group>_<scenario>.xlsx) and one
synopsis (.txt, the workbook's Summary sheet as text) per run, the run's log (.log), results.json
(every metric of every run, so --report-from reprints without solving) and report.md.

Plans start today: results move from one day to the next, so compare only runs from the same day.
"""

import argparse
import copy
import io
import json
import os
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

LS = ["solver_options.breakpointMethod=local-search"]
EXACT = ["solver_options.breakpointMethod=loop", "solver_options.withMedicare=none",
         "solver_options.withSSTaxability=0.85"]

# Metrics shown in the cost table, in today's dollars over the plan (plan_metrics keys, plus the
# fork's state-tax parts and the STAR credit computed in solve_one()).
COSTS = [
    ("federal_income_tax_today", "Federal ordinary"),
    ("ltcg_tax_today", "Federal gains"),
    ("niit_today", "NIIT"),
    ("payroll_tax_today", "Payroll"),
    ("state_tax_today", "State+local"),
    ("state_recapture_today", "of which NY recapture"),
    ("local_tax_today", "of which local"),
    ("star_credit_today", "STAR credit"),
    ("medicare_today", "Medicare"),
    ("aca_today", "ACA"),
    ("ss_withheld_today", "SS withheld"),
    ("roth_conversions_today", "Roth conversions"),
    ("itemized_deductions_today", "Federal itemized"),
    ("state_itemized_today", "NY itemized"),
    ("debt_payments_today", "Debt payments"),
    ("housing_costs_today", "Housing costs"),
]


def scenario_groups(case, housing, names, move_district):
    """Return [(group, case_file, group_sets, [(name, what, sets)], ages_from_base)]."""
    a, b = (names + [names[0]])[:2]

    def hfp(suffix):  # the workbook next to the case, by suffix (resolved in build())
        return {"hfp_suffix": suffix}

    def fixed(age):
        return ["solver_options.withSSAges=fixed", f"fixed_income.social_security_ages=[{age:.1f}, {age:.1f}]"]

    residency = [
        ("yonkers", "Yonkers (city surcharge on NY tax)", ["basic_info.locality=Yonkers"]),
        ("nyc", "New York City (city income tax)", ["basic_info.locality=NYC"]),
    ]
    main = [
        ("retire-2027", "both work one more year (HFP _2027), marketplace from 2028",
         [hfp("_2027"), "aca_settings.aca_start_year=2028"]),
        ("ss-62", "both claim at 62", fixed(62)),
        ("ss-67", "both claim at 67 (FRA)", fixed(67)),
        ("ss-70", "both claim at 70", fixed(70)),
        *residency,
        ("no-itemizing", "standard deduction only (federal and NY)", ["solver_options.withItemized=none"]),
        ("one-works", f"{a} stops in 2026, {b} keeps working (HFP _oneworks), marketplace from 2029, "
                      f"{a}'s age searched, {b} at 67",
         [hfp("_oneworks"), "aca_settings.aca_start_year=2029", f'solver_options.withSSAges=["{a}"]',
          "fixed_income.social_security_ages=[62.0, 67.0]"]),
        ("obbba-2032", "pre-TCJA federal law from 2032 (Owl's default)",
         ["rates_selection.obbba_expiration_year=2032"]),
        ("slcsp-2027", "2027 marketplace benchmark (25.29 $k)", ["aca_settings.slcsp_annual=25.29"]),
    ]
    move = [{"year": 2032, "state": "NY", "locality": "", "school_district": move_district}]
    housing_v = [
        ("buy-cash", "buy with cash (HFP _buy_cash)", [hfp("_buy_cash")]),
        ("buy-mortgage", "buy with a mortgage (HFP _buy_mortgage)", [hfp("_buy_mortgage")]),
        ("buy-mortgage-no-itemizing", "buy with a mortgage, standard deduction only",
         [hfp("_buy_mortgage"), "solver_options.withItemized=none"]),
        ("buy-cash-no-star", "buy with cash, STAR credit off",
         [hfp("_buy_cash"), "solver_options.withSTAR=none"]),
        ("move-2032", f"rent, then buy in {move_district} in 2032 (HFP _move, a move within NY)",
         [hfp("_move"), "basic_info.moves=" + json.dumps(move)]),
    ]
    housing_x = [v for v in housing_v if v[0] in ("buy-cash", "buy-mortgage")]
    return [
        ("main", case, [], main, False),
        ("residency-ls", case, LS, residency, True),
        ("residency-exact", case, EXACT, residency, True),
        ("housing", housing, [], housing_v, True),
        ("housing-exact", housing, EXACT, housing_x, True),
    ]


def hfp_name(diconf, suffix):
    name = diconf["household_financial_profile"]["HFP_file_name"]
    stem, ext = os.path.splitext(name)
    for known in ("_rent",):
        if stem.endswith(known):
            stem = stem[: -len(known)]
    return stem + suffix + ext


def build(spec, base_ages):
    """Turn the groups into jobs: (group, name, what, case_file, overrides, base_name)."""
    jobs, skipped = [], []
    for group, case_file, gsets, variants, from_base in spec:
        diconf, dirname, _ = load_toml(str(case_file))
        extra = []
        if from_base and base_ages is not None:
            extra = ["solver_options.withSSAges=fixed", f"fixed_income.social_security_ages={json.dumps(base_ages)}"]
        rows = [("base", "the case as written" if not (gsets or extra) else "the case, group settings", [])]
        for name, what, sets in variants:
            resolved, missing = [], None
            for s in sets:
                if isinstance(s, dict):
                    f = hfp_name(diconf, s["hfp_suffix"])
                    if not os.path.exists(os.path.join(dirname, f)):
                        missing = f
                    resolved.append(f"household_financial_profile.HFP_file_name={f}")
                else:
                    resolved.append(s)
            if missing:
                skipped.append((group, name, f"workbook {missing} not found next to {case_file}"))
                continue
            rows.append((name, what, resolved))
        for name, what, sets in rows:
            jobs.append((group, name, what, str(case_file), gsets + extra + sets))
    return jobs, skipped


def _arr(p, attr):
    return np.asarray(getattr(p, attr, np.zeros(p.N_n)))[: p.N_n]


def solve_one(job, out_dir):
    group, name, what, case_file, sets = job
    stem = f"{group}_{name}"
    t0 = time.time()
    rec = {"group": group, "name": name, "what": what, "overrides": sets, "case": case_file}
    buf = io.StringIO()
    try:
        diconf, dirname, _ = load_toml(case_file)
        diconf = apply_overrides(diconf, sets)
        p = config_to_plan(copy.deepcopy(diconf), dirname, verbose=True, logstreams=[buf], loadHFP=True)
        opts = parse_solver_options(dict(p.solverOptions))
        p.solve(p.objective, opts)
        rec["status"] = p.caseStatus
        rec["objective"] = p.objective
        if p.caseStatus == "solved":
            m = plan_metrics(p)
            inv_g = 1.0 / p.gamma_n[: p.N_n]
            m["state_recapture_today"] = float(np.sum(_arr(p, "st_recap_n") * inv_g))
            m["local_tax_today"] = float(np.sum(_arr(p, "lt_T_n") * inv_g))
            m["star_credit_today"] = float(np.sum(_arr(p, "st_star_n") * inv_g))
            m["home_in_bequest_today"] = m["final_bequest_today"] - m["final_bequest_savings_today"]
            rec["metrics"] = m
            rec["ages"] = [round(float(a), 4) for a in p.ssecAges]
            rec["names"] = list(p.inames)
            rec["convergence"] = p.convergenceType
            rec["method"] = getattr(p, "breakpointMethodUsed", "loop")
            rec["error_bar"] = float(p.oscillationAbs) / 2.0
            rec["gap"] = float(p.solverGap)
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
    return m["spending_basis"] if rec["objective"] == "maxSpending" else m["final_bequest_today"]


def money(x):
    return f"{x:,.0f}"


def signed(x):
    return f"{x:+,.0f}"


def ages_text(rec):
    def ym(a):
        mo = int(round(a * 12))
        return f"{mo // 12}y{mo % 12}m"
    return ", ".join(f"{n} {ym(a)}" for n, a in zip(rec["names"], rec["ages"], strict=True))


def feature_checks(by):
    """Each modeled feature shows up where the scenario says it should. (label, ok, detail)."""
    out = []

    def m(g, n, k):
        r = by.get((g, n))
        return None if r is None or "metrics" not in r else r["metrics"].get(k)

    def check(label, g, n, k, pred, ref=None):
        v = m(g, n, k)
        if v is None:
            out.append((label, None, f"{g}/{n} not solved"))
            return
        rv = m(*ref, k) if ref else None
        if ref and rv is None:
            out.append((label, None, f"{ref[0]}/{ref[1]} not solved"))
            return
        ok = pred(v) if ref is None else pred(v, rv)
        out.append((label, ok, f"{k} = {money(v)}" + (f" vs {money(rv)} in {ref[0]}/{ref[1]}" if ref else "")))

    pos = lambda v: v > 0  # noqa: E731
    zero = lambda v: abs(v) < 0.5  # noqa: E731
    check("Payroll tax charged on the wages", "main", "base", "payroll_tax_today", pos)
    check("Marketplace premiums before 65", "main", "base", "aca_today", pos)
    check("Medicare premiums from 65", "main", "base", "medicare_today", pos)
    check("No local tax outside Yonkers/NYC", "main", "base", "local_tax_today", zero)
    check("No STAR credit while renting", "main", "base", "star_credit_today", zero)
    check("Yonkers surcharge charged", "main", "yonkers", "local_tax_today", pos)
    check("NYC income tax charged", "main", "nyc", "local_tax_today", pos)
    check("NYC tax above the Yonkers surcharge", "main", "nyc", "local_tax_today", lambda v, r: v > r,
          ("main", "yonkers"))
    check("One more work year adds wages", "main", "retire-2027", "wages_today", lambda v, r: v > r, ("main", "base"))
    check("One more work year adds payroll tax", "main", "retire-2027", "payroll_tax_today", lambda v, r: v > r,
          ("main", "base"))
    check("Part-time work adds wages", "main", "one-works", "wages_today", lambda v, r: v > r, ("main", "base"))
    check("No itemizing: no federal itemized deduction", "main", "no-itemizing", "itemized_deductions_today", zero)
    check("No itemizing: no NY itemized deduction", "main", "no-itemizing", "state_itemized_today", zero)
    check("2032 reversion changes the federal tax", "main", "obbba-2032", "federal_income_tax_today",
          lambda v, r: abs(v - r) > 1, ("main", "base"))
    check("Higher benchmark raises marketplace premiums", "main", "slcsp-2027", "aca_today", lambda v, r: v > r,
          ("main", "base"))
    check("Rent counted as housing", "housing", "base", "housing_costs_today", pos)
    check("STAR credit for an owner in Yonkers", "housing", "buy-cash", "star_credit_today", pos)
    check("STAR off: no credit", "housing", "buy-cash-no-star", "star_credit_today", zero)
    check("NY itemizes the property tax", "housing", "buy-cash", "state_itemized_today", pos)
    check("Mortgage payments charged", "housing", "buy-mortgage", "debt_payments_today", pos)
    check("Mortgage interest itemized federally", "housing", "buy-mortgage", "itemized_deductions_today", pos)
    check("Home counted in the bequest (cash buy)", "housing", "buy-cash", "home_in_bequest_today", pos)
    check("Home counted in the bequest, less the loan left (mortgage)", "housing", "buy-mortgage",
          "home_in_bequest_today", pos)
    check("STAR credit after the move", "housing", "move-2032", "star_credit_today", pos)
    check("No Yonkers surcharge after leaving Yonkers", "housing", "move-2032", "local_tax_today", lambda v, r: v < r,
          ("housing", "base"))
    return out


def agreement(by):
    """Local search against the exact LP for the same variant: the decision rule of CLAUDE.md "Loop noise"."""
    out = []
    for ls, ex in (("residency-ls", "residency-exact"), ("housing", "housing-exact")):
        names = [n for (g, n) in by if g == ls and n != "base" and (ex, n) in by]
        rows = []
        for n in names:
            r = [by.get((ls, "base")), by.get((ls, n)), by.get((ex, "base")), by.get((ex, n))]
            if any(x is None or x.get("status") != "solved" for x in r):
                continue
            d_ls, d_ex = score(r[1]) - score(r[0]), score(r[3]) - score(r[2])
            spread = abs(d_ls - d_ex)
            if (d_ls > 0) != (d_ex > 0):
                verdict = "unresolved: the two disagree on the sign"
            elif min(abs(d_ls), abs(d_ex)) <= spread:
                verdict = "unresolved: smaller than the spread"
            else:
                verdict = "resolved: " + ("variant ahead" if d_ls > 0 else "base ahead")
            rows.append(f"| {n} | {signed(d_ls)} | {signed(d_ex)} | {money(spread)} | {verdict} |")
        if rows:
            out += [f"## {ls} vs {ex}", "",
                    "The same variant under local search and under the exact LP (Medicare off, SS taxability 0.85). "
                    "A difference counts only when both give it the same sign and it is larger than their spread.", "",
                    "| scenario | local search | exact LP | spread | reading |", "|---|---:|---:|---:|---|", *rows, ""]
    return out


def run_checks(rec):
    """Problems with one run, whatever the scenario."""
    issues = []
    if rec.get("status") != "solved":
        return [f"not solved: {rec.get('status')} ({rec.get('error', '')})"]
    if rec["convergence"] not in ("monotonic",) and not rec["convergence"].startswith("oscillatory"):
        issues.append(f"convergence: {rec['convergence']}")
    if rec["convergence"].startswith("oscillatory"):
        issues.append(f"loop did not settle ({rec['convergence']}; error bar ±{money(rec['error_bar'])})")
    for w in rec["warnings"]:
        if "Cash flow balance" in w or "infeasible" in w.lower():
            issues.append(w)
    return issues


def report(recs, skipped, out_dir, header):
    by = {(r["group"], r["name"]): r for r in recs}
    lines = [f"# Scenario suite: {header['case']}", "",
             f"Run {header['when']} with Owl {header['version']}, {header['jobs']} jobs, "
             f"{header['seconds']:.0f} s. Plans start today: compare only runs from the same day.", "",
             "Each group compares its scenarios with its own base (the first row). Amounts are in today's dollars; "
             "*score* is the net yearly spending basis under maxSpending and the final bequest (after heirs' tax, home "
             "net of commission, less debt) under maxBequest. Differences under 1% in a loop-mode group are marked "
             "with `~` (can be loop noise, either sign).", ""]
    groups = []
    for r in recs:
        if r["group"] not in groups:
            groups.append(r["group"])
    for g in groups:
        rows = [r for r in recs if r["group"] == g]
        base = by.get((g, "base"))
        lines += [f"## {g}", ""]
        if base and base.get("status") == "solved":
            obj = "spending basis ($/yr)" if base["objective"] == "maxSpending" else "final bequest ($)"
            lines += [f"Objective: {base['objective']}, score = {obj}. Base overrides: "
                      f"`{' '.join(base['overrides']) or 'none'}`.", ""]
        lines += ["| scenario | what changes | score | vs base | % | claiming ages | method / convergence | s |",
                  "|---|---|---:|---:|---:|---|---|---:|"]
        for r in rows:
            if r.get("status") != "solved":
                err = r.get("error", "")[:120]
                lines.append(f"| {r['name']} | {r['what']} | **{r.get('status')}** | | | | {err} | {r['seconds']} |")
                continue
            s = score(r)
            d = pct = ""
            if base and base.get("status") == "solved" and r is not base:
                s0 = score(base)
                d = signed(s - s0)
                pc = 100 * (s - s0) / abs(s0) if s0 else 0.0
                noisy = g == "main" and abs(pc) < 1 and abs(s - s0) > 0.5
                pct = f"{pc:+.2f}{' ~' if noisy else ''}"
            lines.append(f"| {r['name']} | {r['what']} | {money(s)} | {d} | {pct} | {ages_text(r)} | "
                         f"{r['method']} / {r['convergence']} | {r['seconds']} |")
        solved = [r for r in rows if r.get("status") == "solved"]
        if base and base.get("status") == "solved" and len(solved) > 1:
            shown = [(k, lab) for k, lab in COSTS
                     if any(abs(r["metrics"].get(k, 0.0)) > 0.5 for r in solved)]
            lines += ["", "Lifetime amounts (base) and differences (variants), today's $:", "",
                      "| " + " | ".join(["scenario"] + [lab for _, lab in shown]) + " |",
                      "|---|" + "---:|" * len(shown)]
            for r in solved:
                cells = [money(base["metrics"].get(k, 0.0)) if r is base else
                         signed(r["metrics"].get(k, 0.0) - base["metrics"].get(k, 0.0)) for k, _ in shown]
                lines.append("| " + " | ".join([r["name"]] + cells) + " |")
        lines.append("")

    lines += agreement(by)
    lines += ["## Run checks", ""]
    bad = [(r, run_checks(r)) for r in recs]
    bad = [(r, i) for r, i in bad if i]
    if not bad:
        lines += ["Every run solved, converged (no oscillating loop) and has no cash-flow or infeasibility "
                  "warning.", ""]
    for r, issues in bad:
        for i in issues:
            lines.append(f"- {r['group']}/{r['name']}: {i}")
    if skipped:
        lines += ["", "Skipped:", ""] + [f"- {g}/{n}: {why}" for g, n, why in skipped]
    lines += ["", "## Feature checks", "",
              "Each line checks that a modeled rule shows up in the scenario that should trigger it (not that its "
              "amount is right).", "", "| check | result | detail |", "|---|---|---|"]
    for label, ok, detail in feature_checks(by):
        lines.append(f"| {label} | {'ok' if ok else ('n/a' if ok is None else '**FAIL**')} | {detail} |")
    warns = {}
    for r in recs:
        for w in r.get("warnings", []):
            warns.setdefault(w, []).append(f"{r['group']}/{r['name']}")
    lines += ["", "## Warnings in the logs", ""]
    if not warns:
        lines.append("None.")
    for w, where in sorted(warns.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"- {w}  \n  ({len(where)} run(s): {', '.join(where[:6])}{' ...' if len(where) > 6 else ''})")
    lines += ["", f"Per run: `<group>_<scenario>.xlsx` (the workbook `owlcli run` writes), `.txt` (its Summary as "
              f"text), `.log`. All in `{out_dir}`.", ""]
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case", nargs="?")
    ap.add_argument("housing", nargs="?")
    ap.add_argument("--out-dir")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 0))
    ap.add_argument("--only", nargs="*", help="group or group/scenario names to run (the bases always run)")
    ap.add_argument("--move-district", default="City of New Rochelle / New Rochelle")
    ap.add_argument("--report-from", help="results.json of an earlier run: reprint its report without solving")
    args = ap.parse_args()

    if args.report_from:
        with open(args.report_from, encoding="utf-8") as f:
            saved = json.load(f)
        print(report(saved["runs"], saved["skipped"], os.path.dirname(os.path.abspath(args.report_from)),
                     saved["header"]))
        return
    if not (args.case and args.housing):
        ap.error("CASE.toml and HOUSING_CASE.toml are required (or --report-from).")
    case, housing = Path(args.case).resolve(), Path(args.housing).resolve()
    out_dir = Path(args.out_dir or case.parent / "suite").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    names = load_toml(str(case))[0]["basic_info"]["names"]
    spec = scenario_groups(case, housing, names, args.move_district)
    t0 = time.time()

    # The baseline first: the later groups run at the claiming ages it chose.
    jobs, _ = build(spec[:1], None)
    base = solve_one(jobs[0], str(out_dir))
    print(f"main/base: {base['status']} in {base['seconds']} s", flush=True)
    base_ages = base.get("ages")
    jobs, skipped = build(spec, base_ages)
    jobs = jobs[1:]
    if args.only:
        keep = set(args.only)
        jobs = [j for j in jobs if j[1] == "base" or j[0] in keep or f"{j[0]}/{j[1]}" in keep]
    recs = [base]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for rec in pool.map(_run, [(j, str(out_dir)) for j in jobs]):
            print(f"{rec['group']}/{rec['name']}: {rec['status']} in {rec['seconds']} s", flush=True)
            recs.append(rec)
    header = {"case": str(case), "housing": str(housing), "when": datetime.now().strftime("%Y-%m-%d %H:%M"),
              "version": __version__, "jobs": args.jobs, "seconds": time.time() - t0}
    with open(out_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump({"header": header, "skipped": skipped, "runs": recs}, f, indent=1, default=float)
    print(report(recs, skipped, str(out_dir), header))


if __name__ == "__main__":
    main()

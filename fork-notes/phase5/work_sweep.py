"""
Phase 5 step 6: sweep work (and other) variants of one case, deciding claiming ages by the
two-stage method of `fork-notes/plan-review-2026-10-22.md` §3.2 (decision R1, 2026-10-22).

For each variant:

(a) reference search: `withSSAges` under the exact LP (`withMedicare="none"`,
    `withSSTaxability=0.85`), with `withACA="optimize"` added when the case has a benchmark
    premium (the same rule as the local-search preset), so the ACA cliff is priced;
(b) loop search: `withSSAges` with every breakpoint family on the loop (skip with --no-loop);
(c) decision: local search at fixed ages. For each searched person in turn, with the others held
    at the current best: the whole years 62-70 (each mapped to the first open month at or after
    it), the picks of (a) and (b) and the current best. The best under local search becomes that
    person's age; passes repeat while someone moves (--passes, default 2).

Spread: local search is not a proven optimum, so its scores carry noise. Assuming the true value
is unimodal in each person's claiming age, every interior dip in a sweep (a score below both
neighbours) is noise; its depth, min(neighbours) - score, is a lower bound on that noise. A
variant's spread is its deepest dip. A difference between two variants is "resolved" only when it
is larger than both variants' spreads; with no dip seen, the spread is unknown, not zero. Cliffs
(ACA, IRMAA, SS taxability) can make the true value dip too: a dip that recurs at the same age in
every variant may be the model's, and then the spread overstates the noise (it errs toward
"unresolved"). The per-plan scores in --json show which costs move at a dip.

Variants are generic case and HFP overrides, so the script also serves the locality and rent/buy
comparisons (Phase 6 folded in, decision R5). A JSON file describes them:

    {
      "set": ["aca_settings.slcsp_annual=20", "solver_options.withSSAges=optimize"],
      "variants": [
        {"name": "base", "set": ["aca_settings.aca_start_year=2029"]},
        {"name": "stops-2027",
         "set": ["aca_settings.aca_start_year=2028"],
         "hfp": {"Pat": [{"years": [2028, 2028], "anticipated wages": 0, "401k ctrb": 0}]}}
      ]
    }

- "set": `owlcli --set` specs (KEY.PATH=VALUE, the same parser), the top-level list applied to
  every variant first, then the variant's own. A PIA per variant goes here
  (`fixed_income.social_security_pia_amounts=[...]`, decision D4).
- "hfp": per person (sheet name), edits of that person's sheet: "years" [first, last] and any
  recognized column with its value in dollars, as typed in the workbook. Applied with openpyxl to
  a copy of the variant's workbook, so every other cell keeps its value and format (the fork reads
  Debts/Fixed Assets rates by their percent format). Wages follow upstream #221: the wages in
  AGI, pay less pre-tax deferrals.
- The first variant is the reference for the differences.

Each variant's workbook and case file are written to --out-dir, so any run can be repeated with
`owlcli run`. Real numbers stay in `otherFiles/` (the default --out-dir is `otherFiles/sweep`).

Local search runs here with its time caps raised (--ls-time, --ls-step-time), so its node limits
decide and the scores do not depend on machine load or on --jobs. The report says, per scored
plan, whether the default caps (300 s per solve, 60 s per restricted solve) would have bound.

Plans start today: compare variants run the same day. Run from the repository root:

    .venv/bin/python fork-notes/phase5/work_sweep.py CASE.toml VARIANTS.json [--out-dir DIR]
        [--jobs N] [--json FILE]
"""

import argparse
import copy
import io
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date
import multiprocessing as mp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import openpyxl  # noqa: E402

import owlplanner as owl  # noqa: E402
from owlplanner import hfp_io, localsearch  # noqa: E402
from owlplanner.cli.set_override import apply_overrides  # noqa: E402
from owlplanner.config import load_toml, save_toml  # noqa: E402
from owlplanner.config.plan_bridge import config_to_plan  # noqa: E402
from owlplanner.export import plan_metrics  # noqa: E402

EXACT = {"withMedicare": "none", "withSSTaxability": 0.85}
FAMILIES = ("withSSTaxability", "withLTCG", "withNIIT", "withACA", "withSeniorBonus", "withMedicare")
PRESET_KEYS = ("breakpointMethod", "mipStrategy", "localSearchTime", "localSearchStepTime",
               "localSearchRadius", "localSearchStepNodes")
METRICS = ("federal_income_tax_today", "ltcg_tax_today", "niit_today", "state_tax_today", "payroll_tax_today",
           "medicare_today", "aca_today", "ss_withheld_today", "ss_income_today", "final_bequest_today")


def ym(age):
    m = int(round(age * 12))
    return f"{m // 12}y{m % 12}m"


def months(ages):
    return tuple(int(round(a * 12)) for a in ages)


# ----- building a variant -------------------------------------------------------------------------
def _hfp_path(diconf, dirname):
    name = diconf.get("household_financial_profile", {}).get("HFP_file_name", "None")
    if not name or name == "None":
        return None
    if os.path.exists(name):
        return os.path.abspath(name)
    path = os.path.join(dirname, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"HFP '{name}' not found.")
    return os.path.abspath(path)


def edit_hfp(src, dst, edits):
    """Copy workbook src to dst with the per-person edits applied cell by cell."""
    known = set(hfp_io.timeHorizonItems()) - {"year"}
    wb = openpyxl.load_workbook(src)
    for person, items in edits.items():
        if person not in wb.sheetnames:
            raise ValueError(f"HFP edit: no sheet '{person}' in {src}.")
        ws = wb[person]
        header = {c.value: c.column for c in ws[1] if c.value is not None}
        if "year" not in header:
            raise ValueError(f"HFP edit: sheet '{person}' has no 'year' column.")
        rows = {ws.cell(row=r, column=header["year"]).value: r for r in range(2, ws.max_row + 1)}
        for item in items:
            first, last = item["years"]
            cols = {k: v for k, v in item.items() if k != "years"}
            bad = [k for k in cols if k not in known]
            if bad:
                raise ValueError(f"HFP edit for {person}: unknown column(s) {bad}; known: {sorted(known)}.")
            for col in cols:
                if col not in header:
                    header[col] = max(header.values()) + 1
                    ws.cell(row=1, column=header[col], value=col)
            for year in range(int(first), int(last) + 1):
                if year not in rows:
                    rows[year] = ws.max_row + 1
                    ws.cell(row=rows[year], column=header["year"], value=year)
                for col, value in cols.items():
                    ws.cell(row=rows[year], column=header[col], value=value)
    wb.save(dst)


def build_variants(case_file, spec, out_dir):
    """Return [(name, diconf, dirname, overrides)] with each variant's workbook written."""
    base, dirname, _ = load_toml(case_file)
    os.makedirs(out_dir, exist_ok=True)
    out = []
    names = set()
    for v in spec["variants"]:
        name = v["name"]
        if name in names:
            raise ValueError(f"Duplicate variant name '{name}'.")
        names.add(name)
        sets = list(spec.get("set", [])) + list(v.get("set", []))
        d = apply_overrides(base, sets)
        stem = f"{d.get('case_name', 'case')}_{name}"
        hfp = _hfp_path(d, dirname)
        if v.get("hfp"):
            if hfp is None:
                raise ValueError(f"Variant '{name}' edits the HFP but the case has none.")
            dst = os.path.abspath(os.path.join(out_dir, f"HFP_{stem}.xlsx"))
            edit_hfp(hfp, dst, v["hfp"])
            hfp = dst
        if hfp is not None:
            d.setdefault("household_financial_profile", {})["HFP_file_name"] = hfp
        save_toml(d, os.path.join(out_dir, f"Case_{stem}.toml"))
        out.append((name, d, dirname, sets + ([f"hfp: {json.dumps(v['hfp'])}"] if v.get("hfp") else [])))
    return out


def make_plan(diconf, dirname, ages=None):
    d = copy.deepcopy(diconf)
    if ages is not None:
        d.setdefault("fixed_income", {})["social_security_ages"] = [m / 12 for m in months(ages)]
    buf = io.StringIO()
    p = config_to_plan(d, dirname, verbose=True, logstreams=[buf])
    return p, buf


def base_options(p, **extra):
    opts = {k: v for k, v in dict(p.solverOptions or {}).items() if k not in PRESET_KEYS}
    opts.update(extra)
    return opts


# ----- stages (a) and (b): age searches -----------------------------------------------------------
def age_search(diconf, dirname, mode):
    p, _ = make_plan(diconf, dirname)
    sel = (p.solverOptions or {}).get("withSSAges", "fixed")
    if mode == "exact":
        extra = dict(EXACT, withACA="optimize") if p.slcsp_annual > 0 else dict(EXACT)
    else:
        extra = {f: "loop" for f in FAMILIES}
        if (p.solverOptions or {}).get("withMedicare") == "none":
            extra["withMedicare"] = "none"
    t0 = time.time()
    p.solve(p.objective, base_options(p, withSSAges=sel, **extra))
    dt = time.time() - t0
    ok = p.caseStatus == "solved"
    return {"ages": [float(a) for a in p.ssecAges], "value": p._objectiveValue(p.objective) if ok else None,
            "status": p.caseStatus, "seconds": dt}


# ----- stage (c): local search at fixed ages ------------------------------------------------------
def score(args):
    """Worker: local search at fixed ages. Picklable arguments, a plain dict back."""
    diconf, dirname, ages, ls_time, ls_step = args
    p, buf = make_plan(diconf, dirname, ages)
    opts = base_options(p, withSSAges="fixed", breakpointMethod="local-search",
                        localSearchTime=ls_time, localSearchStepTime=ls_step)
    t0 = time.time()
    p.solve(p.objective, opts)
    dt = time.time() - t0
    out = {"ages": list(months(ages)), "status": p.caseStatus, "seconds": dt,
           "method": getattr(p, "breakpointMethodUsed", None)}
    if p.caseStatus != "solved":
        return out
    log = getattr(p, "localSearchLog", None) or []
    steps = [s["seconds"] for it in log for s in it.get("steps", [])]
    out.update({
        "value": p._objectiveValue(p.objective),
        "search_seconds": sum(it.get("time", 0.0) for it in log),
        "max_step_seconds": max(steps) if steps else 0.0,
        "budget_spent": "time budget spent" in buf.getvalue(),
        "metrics": {k: v for k, v in plan_metrics(p).items() if k in METRICS},
    })
    out["default_caps_bind"] = (out["search_seconds"] > localsearch.TOTAL_TIME
                                or out["max_step_seconds"] > localsearch.STEP_TIME)
    return out


def whole_year_candidates(p, i):
    """First open claiming month at or after each whole year 62..70 for person i."""
    open_m = [int(round(a * 12)) for a in p._ssaOpenAges(i)]
    picks = []
    for y in range(62, 71):
        later = [m for m in open_m if m >= 12 * y]
        if later and later[0] not in picks:
            picks.append(later[0])
    return picks


def dips(points):
    """Interior dips of [(months, value)] sorted by age: [(months, depth)]."""
    pts = sorted(points)
    out = []
    for (_, a), (m, b), (_, c) in zip(pts, pts[1:], pts[2:], strict=False):
        if b < a and b < c:
            out.append((m, min(a, c) - b))
    return out


def decide(diconf, dirname, ref, loop, pool, ls_time, ls_step, passes, log):
    p, _ = make_plan(diconf, dirname)
    p._ssa_optimize_set = p._parseSSAgesOption(p.solverOptions or {})
    free = [i for i in sorted(p._ssa_optimize_set) if not p._ssaAgeIsFixed(i)]
    best = list(months(ref["ages"] if ref else p.ssecAges))
    cache = {}

    def run(trials):
        todo = [t for t in dict.fromkeys(trials) if t not in cache]
        jobs = [(diconf, dirname, [m / 12 for m in t], ls_time, ls_step) for t in todo]
        for t, r in zip(todo, pool.map(score, jobs), strict=True):
            cache[t] = r

    def val(t):
        return cache[t].get("value")

    run([tuple(best)])
    sweeps = []
    seen = set()
    for k in range(passes if free else 0):
        moved = False
        for i in free:
            if (i, tuple(best)) in seen:  # the same sweep again: same scores, no move
                continue
            seen.add((i, tuple(best)))
            opts = set(whole_year_candidates(p, i)) | {best[i]}
            for pick in (ref, loop):
                if pick and pick["status"] == "solved":
                    opts.add(months(pick["ages"])[i])
            trials = []
            for m in sorted(opts):
                t = list(best)
                t[i] = m
                trials.append(tuple(t))
            t0 = time.time()
            run(trials)
            pts = [(t[i], val(t)) for t in trials if val(t) is not None]
            winner = max(trials, key=lambda t: -float("inf") if val(t) is None else val(t))
            sweeps.append({"pass": k, "person": p.inames[i], "held": list(best), "points": pts, "dips": dips(pts)})
            log(f"    pass {k}, {p.inames[i]} swept ({len(trials)} ages, {time.time() - t0:.0f}s): "
                f"best {ym(winner[i] / 12)} at {val(winner):,.2f}")
            vb = val(tuple(best))
            if winner[i] != best[i] and val(winner) is not None and (vb is None or val(winner) > vb):
                best[i] = winner[i]
                moved = True
        if not moved:
            log(f"    pass {k}: no age moved")
            break
    return tuple(best), cache, sweeps, [p.inames[i] for i in free]


# ----- report -------------------------------------------------------------------------------------
def run_variant(name, diconf, dirname, args, pool, log):
    log(f"\n== {name}")
    ref = age_search(diconf, dirname, "exact")
    log(f"  (a) exact-LP search: {ref['status']}, ages {'/'.join(ym(a) for a in ref['ages'])} "
        f"({ref['seconds']:.0f}s)")
    loop = None
    if not args.no_loop:
        loop = age_search(diconf, dirname, "loop")
        log(f"  (b) loop search:     {loop['status']}, ages {'/'.join(ym(a) for a in loop['ages'])} "
            f"({loop['seconds']:.0f}s)")
    log("  (c) local search at fixed ages:")
    best, cache, sweeps, free = decide(diconf, dirname, ref if ref["status"] == "solved" else None, loop, pool,
                                       args.ls_time, args.ls_step_time, args.passes, log)
    spread = max((d for s in sweeps for _, d in s["dips"]), default=None)
    res = cache[best]

    def at(pick):
        if not pick or pick["status"] != "solved":
            return None
        return cache.get(months(pick["ages"]), {}).get("value")

    return {"name": name, "free": free, "best": list(best), "result": res, "spread": spread,
            "ref": ref, "loop": loop, "ref_value": at(ref), "loop_value": at(loop), "sweeps": sweeps,
            "results": {"/".join(ym(m / 12) for m in k): v for k, v in cache.items()}}


def report(rows, objective, log):
    unit = "annual spending, today's $/yr" if objective == "maxSpending" else "after-tax bequest, today's $"
    log(f"\nDecided by local search; objective = {unit}. Taxes and premiums: lifetime, today's $.")
    base = rows[0]["result"].get("value")
    hdr = (f"{'variant':<24}{'ages':>14}{'objective':>13}{'vs first':>11}{'spread':>9}  {'':<11}"
           f"{'(a) cost':>9}{'(b) cost':>9}")
    log(hdr)
    for r in rows:
        v = r["result"].get("value")
        if v is None:
            log(f"{r['name']:<24}{'':>14}{r['result']['status']:>13}")
            continue
        sp = r["spread"]
        sp0 = rows[0]["spread"]
        d = v - base if base is not None else None
        if r is rows[0]:
            verdict = ""
        elif sp is None or sp0 is None:
            verdict = "no spread"
        else:
            verdict = "resolved" if abs(d) > max(sp, sp0) else "unresolved"
        costs = [f"{v - x:>9,.0f}" if x is not None else f"{'-':>9}" for x in (r["ref_value"], r["loop_value"])]
        log(f"{r['name']:<24}{'/'.join(ym(m / 12) for m in r['best']):>14}{v:>13,.2f}"
            f"{d:>11,.2f}{'?' if sp is None else f'{sp:,.0f}':>9}  {verdict:<11}{costs[0]}{costs[1]}")
    log("\n(a)/(b) cost: decided objective less local search's score at that search's pick.")
    log(f"\n{'variant':<24}{'federal':>10}{'state':>10}{'payroll':>10}{'Medicare':>10}{'ACA':>10}"
        f"{'SS withheld':>12}{'SS paid':>11}{'bequest':>11}")
    for r in rows:
        m = r["result"].get("metrics")
        if not m:
            continue
        fed = m["federal_income_tax_today"] + m["ltcg_tax_today"] + m["niit_today"]
        log(f"{r['name']:<24}{fed:>10,.0f}{m['state_tax_today']:>10,.0f}{m['payroll_tax_today']:>10,.0f}"
            f"{m['medicare_today']:>10,.0f}{m['aca_today']:>10,.0f}{m['ss_withheld_today']:>12,.0f}"
            f"{m['ss_income_today']:>11,.0f}{m['final_bequest_today']:>11,.0f}")
    log("\nLocal search per scored plan:")
    for r in rows:
        deepest = "none seen" if r["spread"] is None else f"{r['spread']:,.2f}"
        log(f"  {r['name']}: {len(r['results'])} plans scored; deepest dip {deepest}")
        for s in r["sweeps"]:
            pts = ", ".join(f"{ym(m / 12)} {v:,.2f}" for m, v in sorted(s["points"]))
            log(f"    pass {s['pass']} {s['person']} (held {'/'.join(ym(m / 12) for m in s['held'])}): {pts}")
            for m, dd in s["dips"]:
                log(f"      dip at {ym(m / 12)}: {dd:,.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("case")
    ap.add_argument("variants")
    ap.add_argument("--out-dir", default="otherFiles/sweep")
    ap.add_argument("--jobs", type=int, default=1, help="parallel local-search solves (processes)")
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--ls-time", type=float, default=7200.0, help="localSearchTime (s); default lifts the cap")
    ap.add_argument("--ls-step-time", type=float, default=1800.0, help="localSearchStepTime (s)")
    ap.add_argument("--no-loop", action="store_true", help="skip stage (b)")
    ap.add_argument("--only", nargs="*", help="run only these variants (the first listed is the reference)")
    ap.add_argument("--json", help="write every score to this file")
    args = ap.parse_args()

    def log(msg):
        print(msg, flush=True)

    with open(args.variants, encoding="utf-8") as f:
        spec = json.load(f)
    variants = build_variants(args.case, spec, args.out_dir)
    if args.only:
        by = {v[0]: v for v in variants}
        variants = [by[n] for n in args.only]
    log(f"work_sweep.py, {date.today().isoformat()}, owlplanner {owl.__version__} from {owl.__file__}")
    log(f"case {args.case}, variants {args.variants}, jobs {args.jobs}, passes {args.passes}, "
        f"localSearchTime {args.ls_time:.0f}s, localSearchStepTime {args.ls_step_time:.0f}s")
    for name, _, _, sets in variants:
        log(f"  {name}: {'; '.join(sets) or '(no overrides)'}")
    objective = None
    rows = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.jobs, mp_context=mp.get_context("spawn")) as pool:
        for name, d, dirname, _ in variants:
            if objective is None:
                objective = make_plan(d, dirname)[0].objective
            rows.append(run_variant(name, d, dirname, args, pool, log))
    report(rows, objective, log)
    caps = [(r["name"], k) for r in rows for k, c in r["results"].items() if c.get("default_caps_bind")]
    spent = [(r["name"], k) for r in rows for k, c in r["results"].items() if c.get("budget_spent")]
    failed = [(r["name"], k, c["status"]) for r in rows for k, c in r["results"].items() if c["status"] != "solved"]
    log(f"\nScored plans where the default caps (300 s / 60 s) would have bound: "
        f"{', '.join(f'{n} {k}' for n, k in caps) or 'none'}")
    log(f"Scored plans that spent the raised time budget: {', '.join(f'{n} {k}' for n, k in spent) or 'none'}")
    log(f"Scored plans not solved: {', '.join(f'{n} {k} ({st})' for n, k, st in failed) or 'none'}")
    log(f"Total {time.time() - t0:.0f}s.")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1, default=str)


if __name__ == "__main__":
    main()

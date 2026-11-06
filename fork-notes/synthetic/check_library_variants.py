"""Check build step 6's acceptance on the synthetic household.

`run-library-design.md` section 11, step 6, Check column: "the synthetic condo grid through
the interface matches `run_suite.py`'s report". The user's call (2026-11-04): a reduced grid
now -- one place x three purchase years x cash/mortgage -- and the full 36-cell grid
(six of them the 2027 ARM rows, below) as an
offline/overnight run (below). Both sides solve the **same day** (plans start today) from
the same synthetic inputs:

- **run_suite.py** (the suite's own route) is run on the reduced condo grid
  (`--only condo/reference condo/<variant> ...`), which writes `report.md` and
  `results.json` to a temp folder. Its baseline (`main/base`, the case as written) runs
  first and picks the claiming ages every other group is held at.
- **the interface's route** is a fresh library in a temp folder: the reference scenario
  from `scenarios.json` is saved as a run and solved with the **`ages` preset** (the same
  two-stage search, through the worker); "make variants" (`library.variants`) then makes
  the grid's children from it -- place x year x financing, with the claiming ages held at
  the baseline's pick (the suite's rule: the grid runs at the baseline's ages) -- and each
  child is solved through the worker with the `decision` preset (local search, ages held),
  like `run_suite.py`'s condo group. The numbers come back through `library.grid`'s grid
  view (durable files only) and are compared with the report's own cells.

Checks:

1. the children's events are `make_cases.py`'s grid scenarios (the variants' edits produce
   exactly the purchase events the suite runs, T1 at the events level; the builder's
   cell-for-cell parity is `check_library_builder.py`'s);
2. the `ages` preset picks the claiming ages `run_suite.py`'s baseline picked (the same
   two-stage search, one implementation);
3. the reference's score matches the report's;
4. every grid cell matches the report's -- the score's difference from the reference and
   the home at the end -- within the noise rule (1% of the reference's score; the home
   within a dollar: the inputs fix it, no solve moves it);
5. the report's cells are its own `results.json` rounded (the parse is faithful).

Run after `make_cases.py` (which this script runs itself), from anywhere:

    uv run python fork-notes/synthetic/check_library_variants.py [--full]

Prints one line per check and a summary; exits 1 if any check fails. `--full` runs the
whole 36-cell condo grid through both routes (3 places x 5 purchase years x cash/mortgage
plus the six ARM rows `make_cases.py` writes for 2027; the design's literal check: hours of local-
search solves on this machine, an overnight run; the reduced grid is the recorded one).

Notes: the synthetic cases are plan-year 2026, so the check only runs in 2026 (R1: a run is
solved only in its plan year). The run_suite side runs as a subprocess with its own process
pool; the interface side solves in this process through `library.worker.run_job` (the same
code a detached worker runs), as `check_library_rates.py` does.
"""

import argparse
import copy
import importlib.util
import itertools
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from owlplanner.library import Library  # noqa: E402
from owlplanner.library import grid as gridmod  # noqa: E402
from owlplanner.library import results as R  # noqa: E402
from owlplanner.library import variants  # noqa: E402
from owlplanner.library.presets import preset_options  # noqa: E402
from owlplanner.library.worker import run_job  # noqa: E402

CASES = Path(__file__).parent / "cases"
CASE = CASES / "Case_ari+noa.toml"
CONDO_CASE = CASES / "Case_ari+noa_condo.toml"
GRID_JSON = CASES / "condo_grid.json"
SCENARIOS = CASES / "scenarios.json"
RUN_SUITE = Path(__file__).parent / "run_suite.py"

# The reduced grid (the user's call, 2026-11-04): one place, three purchase years, two
# financings -- 6 cells. The full grid is make_cases.py's: 3 places x 5 years x cash and
# mortgage (30 cells) plus the ARM rows (2027 only, below) = 36 cells.
REDUCED = {"place": ["yonkers"], "years": [2027, 2029, 2031], "financing": ["cash", "mortgage"]}
FULL = {"place": ["yonkers", "whiteplains", "queens"],
        "years": [2027, 2029, 2031, 2034, 2038],
        "financing": ["cash", "mortgage"]}
# The ARM rows (make_cases.py: ARM_YEARS = (2027,)): arm5 (paid down within the fixed 5
# years) and arm30 (refinanced at no higher rate), for the "now or soon" purchase only --
# later rates are unknown. They are their own make-variants pass (one purchase year cannot
# ride the dimensions' product), added to the same grid by --full (the user's call,
# 2026-11-05: --full includes the ARM rows).
ARM = {"years": [2027], "financing": ["arm5", "arm30"]}

# The suite's own pool (its --jobs). Unbounded it is `os.cpu_count()` -- 16 concurrent
# local-search solves here -- and the full grid's run died with BrokenProcessPool ~15 min
# in (2026-11-05, 32 GB machine with ~12 GB free: a worker terminated abruptly mid-solve).
# Six concurrent solves is the proven count (the reduced grid's); scores do not depend on
# --jobs (time-capped local search within the noise rule).
SUITE_JOBS = 6

NOISE = 0.01  # the loop-noise band (view.NOISE_FRACTION, R2)
HOME_TOL = 1.0  # the home at the end is set by the inputs (compare's fifty-cent rule)


def _load_make_cases():
    spec = importlib.util.spec_from_file_location("make_cases", Path(__file__).parent / "make_cases.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_the_cases() -> None:
    """Write the synthetic household (make_cases.py), as its own checks require."""
    import sys as _sys

    saved = _sys.argv
    _sys.argv = ["make_cases.py", "--out-dir", str(CASES)]
    try:
        _load_make_cases().main()
    finally:
        _sys.argv = saved


class Checks:
    def __init__(self):
        self.rows = []

    def run(self, label, fn):
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001 - a broken check is a finding, not a crash
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        self.rows.append((label, ok, detail))
        print(f"{'ok  ' if ok else 'FAIL'}  {label}" + (f" -- {detail}" if detail else ""), flush=True)
        return ok

    @property
    def passed(self):
        return sum(1 for _label, ok, _detail in self.rows if ok)

    @property
    def total(self):
        return len(self.rows)


# -- the report's cells ------------------------------------------------

_CELL = re.compile(r"(?:\*\*)?([+-][\d,]+)(?:\*\*)?<br>([\d,]+)")
_ROW = re.compile(r"^\| ([^|]+?) \| (.*) \|$")


def parse_pivot(text):
    """{(place, financing): {year: (score difference, home at the end)}} from report.md's
    `condo: where, when, how` table, plus the reference's score from its caption."""
    section = text.split("### condo: where, when, how", 1)
    if len(section) < 2:
        raise ValueError("no condo pivot in report.md")
    section = section[1].split("\n#", 1)[0]
    caption = re.search(r"the reference purchase \([^:]*: ([\d,]+)\)", section)
    if not caption:
        raise ValueError("no reference score in the pivot's caption")
    ref_score = float(caption.group(1).replace(",", ""))
    years, cells = None, {}
    for line in section.splitlines():
        match = _ROW.match(line.strip())
        if not match:
            continue
        head, body = match.group(1).strip(), match.group(2)
        if head == "place, financing":
            years = [int(y) for y in body.split("|") if y.strip()]
            continue
        if years is None:
            continue
        parts = [p.strip() for p in body.split("|")]
        values = {}
        for year, part in zip(years, parts, strict=True):
            if not part:
                continue
            m = _CELL.search(part)
            if m:
                values[year] = (float(m.group(1).replace(",", "")),
                                float(m.group(2).replace(",", "")))
        cells[tuple(head.split(", "))] = values
    return cells, ref_score


# -- the interface's side ---------------------------------------------


def _solve(run, preset, library, tag):
    """One solve of one run through the worker (`run_job`), as check_library_rates does."""
    from datetime import datetime

    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    folder = run.path / "results" / f"{stamp}_{preset}_{tag}"
    job = R.JobRecord.create(folder, run_id=run.id, run_name=run.name, preset=preset,
                             options=preset_options(preset), plan_year=run.plan_year)
    state = run_job(job.results_dir, job.token)
    return state, gridmod.latest_result(run.path)


def _values_for(make_cases, place, year, fin):
    """The variant values that reproduce make_cases.py's grid scenario for (place, year, fin)."""
    c = make_cases.PLACES[place]
    place_value = {
        "label": place,
        "name": f"{place} condo",
        "price": c["price"],
        "place": {"state": "NY", "locality": c["locality"], "school_district": c["district"],
                  "move": c["move"]},
        "costs": {"property tax": c["property tax"], "hoa": c["maintenance"],
                  "insurance": c["insurance"]},
    }
    if fin == "cash":
        financing = {"kind": "cash", "closing": make_cases.CLOSING}
    else:
        term, rate, suffix = {"mortgage": (30, make_cases.MORTGAGE_RATE, "mortgage"),
                              "arm5": (5, make_cases.ARM_RATE, "ARM"),
                              "arm30": (30, make_cases.ARM_RATE, "ARM")}[fin]
        financing = {"kind": "loan", "term": term, "rate": rate, "down": make_cases.DOWN,
                     "closing": make_cases.CLOSING, "extra": make_cases.MORTGAGE_EXTRA,
                     "name": "{place} " + suffix}
    return place_value, year, {"label": fin, "financing": financing}


def _norm_events(events, names):
    from owlplanner.library import builder, casefiles

    return casefiles._canonical_events(builder.validate_events(events, names))


def _drop_hfp_name(case):
    """The hand case without `household_financial_profile.HFP_file_name` (one dictionary
    per family: `make_cases.py` gives every grid variant its own workbook file, the library
    writes one `HFP.xlsx` per run from the generated tables -- inert in the stored case)."""
    out = {key: copy.deepcopy(value) for key, value in case.items()}
    profile = dict(out.get("household_financial_profile") or {})
    profile.pop("HFP_file_name", None)
    if profile:
        out["household_financial_profile"] = profile
    else:
        out.pop("household_financial_profile", None)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="the whole condo grid (hours; overnight)")
    args = ap.parse_args()
    selection = FULL if args.full else REDUCED

    print("writing the synthetic household (make_cases.py) ...", flush=True)
    _make_the_cases()
    make_cases = _load_make_cases()
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))["scenarios"]
    by_name = {e["name"]: e for e in scenarios}
    reference = json.loads(GRID_JSON.read_text(encoding="utf-8"))["reference"]
    blocks = [(selection["years"], selection["financing"])]
    if args.full:
        blocks.append((ARM["years"], ARM["financing"]))
    combos = [(year, fin) for years, fins in blocks for year in years for fin in fins]
    grid_names = [f"{place}-{year}-{fin}"
                  for place, (year, fin) in itertools.product(selection["place"], combos)]
    suite_only = ["condo/reference"] + [f"condo/{name}" for name in grid_names if name != reference]

    checks = Checks()
    with tempfile.TemporaryDirectory(prefix="check_library_variants_") as tmp:
        tmp = Path(tmp)
        suite_dir = tmp / "suite"

        # -- the suite's route ------------------------------------------
        print(f"run_suite.py on {len(suite_only)} condo row(s) ...", flush=True)
        proc = subprocess.run(
            [sys.executable, str(RUN_SUITE), str(CASE), str(CONDO_CASE), str(GRID_JSON),
             "--out-dir", str(suite_dir), "--only", *suite_only,
             "--jobs", str(SUITE_JOBS)],
            capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stdout[-4000:])
            print(proc.stderr[-4000:], file=sys.stderr)
            print("run_suite.py failed; nothing to compare")
            return 1
        report_text = (suite_dir / "report.md").read_text(encoding="utf-8")
        results_doc = json.loads((suite_dir / "results.json").read_text(encoding="utf-8"))
        report_cells, report_ref_score = parse_pivot(report_text)
        base_rec = results_doc["runs"][0]
        base_ages = [float(a) for a in base_rec.get("ages") or []]

        # -- the interface's route -------------------------------------
        print("the interface: the reference run, the ages preset, make variants ...", flush=True)
        lib = Library.open(tmp / "library")
        reference_entry = by_name[reference]
        parent = lib.save_run(name="reference", scenario=reference_entry["scenario"]).run
        state, parent_result = _solve(parent, "ages", lib, "parent")
        chosen = ((parent_result.record.get("age_search") or {}).get("chosen")
                  if parent_result is not None else None)

        made = []
        for years, fins in blocks:
            dimensions = {}
            place_values, fin_values = [], []
            for place in selection["place"]:
                for fin in fins:
                    place_value, _year, fin_value = _values_for(make_cases, place, 2027, fin)
                    if place_value not in place_values:
                        place_values.append(place_value)
                    if fin_value not in fin_values:
                        fin_values.append(fin_value)
            dimensions["place"] = place_values
            dimensions["year"] = list(years)
            dimensions["financing"] = fin_values
            if chosen:
                names = list((reference_entry["scenario"]["case"].get("basic_info") or {}).get("names") or [])
                dimensions["claim"] = [dict(zip(names, [float(a) for a in chosen], strict=True))]
            made += variants.plan_variants(reference_entry["scenario"], dimensions)
        coll = lib.create_collection("Condo grid (check)",
                                     question="Maximize first-year discretionary spending, condo kept",
                                     rule="reference: " + reference + " (the baseline's claiming ages)")
        runs = {}
        for variant in made:
            saved = lib.save_run(name=f"reference {variant.label}", scenario=variant.scenario,
                                 parent=parent.id)
            run = saved.run if saved.created else saved.identical_to
            lib.add_member(coll.id, run, variant.values)
            runs[variant.label] = run

        def _matches(v):
            return (v.values.get("place"), v.values.get("year"), v.values.get("financing")) == \
                (make_cases.REFERENCE[0], make_cases.REFERENCE[1], make_cases.REFERENCE[2])

        ref_variant = next((v for v in made if _matches(v)), None)
        if ref_variant is None:
            print(f"the reduced grid holds no {make_cases.REFERENCE} cell; nothing to compare")
            return 1
        ref_run = runs[ref_variant.label]
        coll = lib.set_reference(coll.id, ref_run)

        print(f"solving {len(made)} variant(s) with the decision preset ...", flush=True)
        for run in runs.values():
            _solve(run, "decision", lib, "grid")

        entries = [gridmod.Entry(run_id=run.id, name=run.name, values=lib.collection(coll.id)
                                 .member(run.id).values, result=gridmod.latest_result(run.path))
                   for run in runs.values()]
        g = gridmod.grid_view(entries, reference=ref_run.id, row_dims=("place", "financing"),
                              col_dims=("year",))
        interface = {}
        for key, row in g.rows:
            for col, cell in row.items():
                if cell is None:
                    continue
                delta = cell.delta
                if delta is None and cell.entry.run_id == ref_run.id:
                    delta = 0.0  # the reference's own cell: the report shows its +0
                interface[(key, col)] = (delta, cell.home)

        # -- the checks -------------------------------------------------
        def check_children():
            names = list((reference_entry["scenario"]["case"].get("basic_info") or {}).get("names") or [])
            bad = []
            checked = 0
            for variant in made:
                place, year, fin = (variant.values.get("place"), variant.values.get("year"),
                                    variant.values.get("financing"))
                if not args.full and place != "yonkers":
                    continue
                checked += 1
                entry = by_name.get(f"{place}-{year}-{fin}")
                if entry is None:
                    bad.append(f"{variant.label}: no scenarios.json entry")
                    continue
                mine = [e for e in variant.scenario["events"] if e.get("kind") != "claim"]
                theirs = [e for e in entry["scenario"]["events"] if e.get("kind") != "claim"]
                if _norm_events(mine, names) != _norm_events(theirs, names):
                    bad.append(f"{variant.label}: its events are not {entry['name']}'s")
                if variant.scenario["hfp"] != entry["scenario"]["hfp"]:
                    bad.append(f"{variant.label}: its hand rows are not {entry['name']}'s")
                # The hand case is the same but for HFP_file_name (see `_drop_hfp_name`).
                if _drop_hfp_name(variant.scenario["case"]) != _drop_hfp_name(entry["scenario"]["case"]):
                    bad.append(f"{variant.label}: its hand case is not {entry['name']}'s")
            return (checked > 0 and not bad,
                    f"{checked - len(bad)}/{checked} children are make_cases' grid scenarios"
                    if not bad else "; ".join(bad))

        def check_ages():
            detail = f"the ages preset picked {chosen}, the suite's baseline {base_ages}"
            return (chosen is not None and list(chosen) == base_ages, detail)

        def check_reference_score():
            ours = gridmod.Entry(run_id=ref_run.id, name=ref_run.name, values={},
                                 result=gridmod.latest_result(ref_run.path)).score
            tol = NOISE * abs(report_ref_score)
            return (ours is not None and abs(ours - report_ref_score) <= tol,
                    f"interface {ours:,.0f} vs report {report_ref_score:,.0f} "
                    f"(tolerance {tol:,.0f})")

        def check_cells():
            bad, compared = [], 0
            for (key, col), (delta, home) in sorted(interface.items(), key=lambda kv: str(kv[0])):
                row_key = key if isinstance(key, tuple) else (key,)
                year = col[0] if isinstance(col, tuple) else col
                want = report_cells.get(row_key, {}).get(year)
                if want is None:
                    continue  # a cell the suite's reduced run did not include
                compared += 1
                d_report, h_report = want
                tol = NOISE * abs(report_ref_score)
                if delta is None or abs(delta - d_report) > tol:
                    bad.append(f"{row_key} {year}: delta {delta} vs report {d_report:+,.0f}")
                elif home is None or abs(home - h_report) > HOME_TOL:
                    bad.append(f"{row_key} {year}: home {home} vs report {h_report:,.0f}")
            return (compared > 0 and not bad,
                    f"{compared - len(bad)}/{compared} cells within the noise rule"
                    if not bad else "; ".join(bad))

        def check_parse():
            good = 0
            total = 0
            for values in report_cells.values():
                for d_report, _h in values.values():
                    total += 1
                    if d_report == round(d_report):
                        good += 1
            return (total > 0 and good == total,
                    f"{good}/{total} report cells are whole dollars (the parse reads them)")

        checks.run("the children are make_cases.py's grid scenarios", check_children)
        checks.run("the ages preset picks the suite's baseline ages", check_ages)
        checks.run("the reference's score matches the report", check_reference_score)
        checks.run("the grid cells match the report", check_cells)
        checks.run("the report's cells parse as whole dollars", check_parse)

    print(f"\n{checks.passed}/{checks.total} checks passed")
    return 0 if checks.passed == checks.total else 1


if __name__ == "__main__":
    raise SystemExit(main())

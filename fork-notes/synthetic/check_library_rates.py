"""Check build step 5b's acceptance on the synthetic household.

`run-library-design.md` section 11, step 5b, Check column:

1. "`owlcli run` of a case with a table reproduces the interface's result" -- a run whose
   downturn event generates its `inputs/rates.csv` is solved through the library's worker
   (the interface's solve) and again from its frozen `inputs/Case.toml` by `owlcli run`,
   called from a different working directory: the two agree on the plan's every field
   (`plan.json`, which carries the summary metrics among its fields; the solve's own timing
   aside), and the run's `summary.json` is checked to hold its metrics (one key's existence
   and shape, not a comparison -- review Z8);
2. the run's inputs carry the table: `inputs/rates.csv` is written, the generated
   `Case.toml` names it (`rates_selection.method = "table"`, `rates_file = "rates.csv"`),
   and the sequence's window sits at its placement year while the years outside it keep
   the case's own method (the case is `conservative`: one constant baseline row);
3. `record.json` records the rate method as `table` (its `rates` block);
4. the same acceptance for a **hand** table: a case whose `rates.csv` is imported with it
   solves identically both ways, and re-imports of the frozen files give the same inputs
   hash (T1) -- the table is stored in the scenario, so it is in the hash (R13). T1 is the
   hand table's alone by design: every re-import drops the events (step 4), so a downturn
   run re-imports as a hand-table scenario.

Run after `make_cases.py`, from anywhere:

    uv run python fork-notes/synthetic/check_library_rates.py

Prints one line per check and a summary; exits 1 if any check fails. Both solves of a pair
run in this process on the same day: the plan year is the year of capture (section 8.3), and
the preset is `custom` (the case's own solver options) on both sides, so the only difference
is the entry point. The synthetic case's claiming ages are held and Medicare is put on the
loop first (its own `withSSAges = "optimize"` x `withMedicare = "optimize"` makes every age
candidate a branch-and-bound MIP, design section 8.1): the check is about the rate table, not
about the search, and both solves read the same frozen case.
"""

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "ui"))

import click.testing  # noqa: E402

from owlplanner.cli._main import cli  # noqa: E402
from owlplanner.config.toml_io import load_toml, save_toml  # noqa: E402
from owlplanner.library import Library, export_case, import_case, scenario_hash  # noqa: E402
from owlplanner.library import results as R  # noqa: E402
from owlplanner.library.sequences import sequences  # noqa: E402
from owlplanner.library.worker import run_job  # noqa: E402

CASES = Path(__file__).parent / "cases"
CASE = CASES / "Case_ari+noa.toml"
WORKBOOK = CASES / "HFP_ari+noa.xlsx"
SEQUENCE = "three-negative-years"
PLACED_AT = 2030

# The plan's logger writes DEBUG to stdout/stderr; keep the script's own output readable.
_quiet = contextlib.redirect_stdout(io.StringIO())
_quiet_err = contextlib.redirect_stderr(io.StringIO())
_real_out = sys.stdout


def _lighten(scenario):
    """Both solves run the plain loop: ages held and Medicare on the loop (design section 8.1).

    The synthetic case's own `withSSAges = "optimize"` x `withMedicare = "optimize"` makes every
    claiming-age candidate a branch-and-bound MIP. The check is about the rate table and the
    entry point, not about the search, and both solves read the same frozen case.
    """
    options = scenario["case"].setdefault("solver_options", {})
    options["withSSAges"] = "fixed"
    options["withMedicare"] = "loop"


def _job_for(run, name):
    scenario = json.loads((run.path / "inputs" / "scenario.json").read_text(encoding="utf-8"))
    return R.JobRecord.create(run.path / "results" / name, run_id=run.id, run_name=run.name,
                              preset="custom", options={}, plan_year=scenario["plan_year"])


def _interface_solve(run):
    """The interface's result: the worker's solve of the run's frozen inputs."""
    job = _job_for(run, "custom")
    run_job(job.results_dir, job.token)
    record = json.loads((job.results_dir / "record.json").read_text(encoding="utf-8"))
    return job.results_dir, record


def _owlcli(case_file, elsewhere):
    """`owlcli run <case> --output-format json`, called from a different working directory."""
    runner = click.testing.CliRunner()
    old = os.getcwd()
    os.chdir(elsewhere)
    try:
        result = runner.invoke(cli, ["run", str(case_file), "--output-format", "json"],
                               catch_exceptions=False)
    finally:
        os.chdir(old)
    if result.exit_code != 0:
        raise RuntimeError(f"owlcli run failed ({result.exit_code}): {result.stdout[-2000:]}")
    return json.loads(result.stdout)


def _plan_doc(results_dir):
    return json.loads((results_dir / "plan.json").read_text(encoding="utf-8"))


def _same_plan(worker_plan, cli_plan):
    """The two plan documents agree field for field, except the solve's own timing."""
    worker_plan = dict(worker_plan)
    cli_plan = dict(cli_plan)
    for doc in (worker_plan, cli_plan):
        doc.pop("solve_time_seconds", None)
    return worker_plan == cli_plan


def _table_case(tmp: Path, table):
    """Ari+noa as a hand-table case: rates.csv beside the case, named by it."""
    case, _, _ = load_toml(str(CASE))
    case["rates_selection"] = {"method": "table", "rates_file": "rates.csv"}
    path = tmp / "Case_table.toml"
    save_toml(case, str(path))
    with open(tmp / "rates.csv", "w", encoding="utf-8") as f:
        f.write(",".join(table["columns"]) + "\n")
        for row in table["rows"]:
            f.write(",".join(str(v) for v in row) + "\n")
    return path


def main() -> int:
    if not CASE.exists() or not WORKBOOK.exists():
        print(f"missing {CASE.name} / {WORKBOOK.name} (run make_cases.py first)")
        return 2

    failures = 0
    checks = 0

    def check(name, ok, detail=""):
        nonlocal failures, checks
        checks += 1
        failures += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""),
              file=_real_out, flush=True)

    with tempfile.TemporaryDirectory() as tmp, _quiet, _quiet_err:
        tmp = Path(tmp)
        library = Library.open(tmp / "library")

        # -- the downturn run: a named sequence at its placement -----------------
        scenario = import_case(CASE, hfp_path=WORKBOOK)
        _lighten(scenario)
        scenario["events"] = [{"id": "stress", "kind": "downturn", "sequence": SEQUENCE,
                               "start": PLACED_AT}]
        run = library.save_run(name="ari+noa downturn", scenario=scenario).run
        inputs = run.path / "inputs"
        csv_rows = {int(line.split(",")[0]): line.split(",")[1:]
                    for line in (inputs / "rates.csv").read_text(encoding="utf-8").splitlines()[1:]}
        window = sequences()[SEQUENCE]["window"]

        check("the run's inputs carry rates.csv",
              (inputs / "rates.csv").exists() and (inputs / "Case.toml").exists())
        case, _, _ = load_toml(str(inputs / "Case.toml"))
        check("the generated Case.toml names the table",
              case["rates_selection"].get("method") == "table"
              and case["rates_selection"].get("rates_file") == "rates.csv",
              f"method={case['rates_selection'].get('method')!r}, file={case['rates_selection'].get('rates_file')!r}")
        placed = all([float(v) for v in csv_rows[PLACED_AT + i]] == [float(x) for x in values]
                     for i, values in enumerate(window))
        # The case is `conservative` (one constant baseline row): the years outside the window
        # must still read it, before and after the window alike.
        outside = csv_rows[PLACED_AT - 1] == csv_rows[PLACED_AT + len(window)] == csv_rows[2026]
        check(f"the {SEQUENCE!r} window sits at {PLACED_AT} and the baseline holds elsewhere",
              placed and outside,
              f"row {PLACED_AT} = {csv_rows[PLACED_AT]}, row {PLACED_AT - 1} = {csv_rows[PLACED_AT - 1]}")

        results_dir, record = _interface_solve(run)
        check("record.json records the rate method", record["rates"]["method"] == "table",
              f"rates = {record['rates']}")
        cli_plan = _owlcli(inputs / "Case.toml", tmp)
        worker_plan = _plan_doc(results_dir)
        check("owlcli run reproduces the interface's plan.json (timing aside)",
              _same_plan(worker_plan, cli_plan))
        summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
        check("the solve wrote summary.json metrics",
              isinstance(summary.get("final_bequest_today"), (int, float))
              or isinstance(summary.get("discretionary_year1"), (int, float)),
              f"{len(summary)} metrics")

        # -- a hand table: imported with the case, frozen, solved the same way ---
        table = {"columns": ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"],
                 "rows": [[year] + ([-30, 2, 1, 2] if year == 2027 else [6, 4.5, 3, 2.5])
                          for year in range(2026, 2071)]}  # canonical cells (integral floats become ints)
        hand = import_case(_table_case(tmp, table), hfp_path=WORKBOOK)
        _lighten(hand)
        check("the imported hand table is stored in the scenario", hand.get("rates_table") == table)
        hand_run = library.save_run(name="ari+noa hand table", scenario=hand).run
        hand_results, hand_record = _interface_solve(hand_run)
        check("a hand-table run's record.json records the rate method",
              hand_record["rates"]["method"] == "table")
        cli_hand = _owlcli(hand_run.path / "inputs" / "Case.toml", tmp)
        worker_hand = _plan_doc(hand_results)
        check("owlcli run reproduces the interface's plan.json (hand table)",
              _same_plan(worker_hand, cli_hand))

        again = import_case(hand_run.path / "inputs" / "Case.toml")
        check("re-importing the frozen files gives the same inputs hash (T1)",
              scenario_hash(again) == hand_run.inputs_hash)
        rebuilt = export_case(copy.deepcopy(hand), tmp / "rebuilt")
        check("exporting the scenario again writes the same rates.csv",
              (tmp / "rebuilt" / "rates.csv").read_text(encoding="utf-8")
              == (hand_run.path / "inputs" / "rates.csv").read_text(encoding="utf-8"),
              f"{len(rebuilt)} files")

    print(f"{checks - failures}/{checks} step-5b checks pass", file=_real_out, flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

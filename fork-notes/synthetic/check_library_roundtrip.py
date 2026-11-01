"""Check build step 1's acceptance: the synthetic cases import and export unchanged.

`run-library-design.md` step 1: "the synthetic cases import and export with the same case
dictionary and HFP tables". For every case file in `cases/` and every workbook that belongs
to it (the workbook variants `run_suite.py` runs), this script imports the pair into a
scenario, exports the generated files to a temporary folder, imports those again, and
compares the case dictionary (less the workbook name, our own bookkeeping) and the HFP
tables.

Run after `make_cases.py`, from anywhere:

    uv run python fork-notes/synthetic/check_library_roundtrip.py

Prints one line per pair and a summary; exits 1 if any pair differs.
"""

import contextlib
import copy
import io
import sys
import tempfile
from pathlib import Path

from owlplanner.library import export_case, import_case

CASES = Path(__file__).parent / "cases"

# The plan's logger writes DEBUG to stdout/stderr; keep the script's own output readable.
_quiet = contextlib.redirect_stdout(io.StringIO())
_real_out = sys.stdout


def normalized(case):
    case = copy.deepcopy(case)
    case.setdefault("household_financial_profile", {})["HFP_file_name"] = "HFP.xlsx"
    return case


def case_for(workbook):
    """The case file a workbook belongs to: the longest case stem it starts with."""
    stem = workbook.stem[len("HFP_"):]
    best = None
    for case_file in sorted(CASES.glob("Case_*.toml")):
        prefix = case_file.stem[len("Case_"):]
        if stem == prefix or stem.startswith(prefix + "_"):
            if best is None or len(prefix) > len(best.stem[len("Case_"):]):
                best = case_file
    return best


def main() -> int:
    if not CASES.is_dir():
        print(f"missing {CASES} (run make_cases.py first)")
        return 2
    failures = 0
    checks = 0
    with tempfile.TemporaryDirectory() as tmp, _quiet:
        for workbook in sorted(CASES.glob("HFP_*.xlsx")):
            case_file = case_for(workbook)
            if case_file is None:
                print(f"? no case file for {workbook.name}", file=_real_out)
                failures += 1
                continue
            scenario = import_case(case_file, hfp_path=workbook)
            out = Path(tmp) / workbook.stem
            export_case(scenario, out)
            again = import_case(out / "Case.toml")
            ok_case = normalized(again["case"]) == normalized(scenario["case"])
            ok_hfp = again["hfp"] == scenario["hfp"]
            ok_year = again["plan_year"] == scenario["plan_year"]
            ok_budget = again.get("budget_file") == scenario.get("budget_file")
            checks += 1
            where = f"{case_file.name} + {workbook.name}"
            if ok_case and ok_hfp and ok_year and ok_budget:
                print(f"ok   {where} ({len(scenario['hfp'])} tables)", file=_real_out)
            else:
                failures += 1
                print(f"FAIL {where}: case={ok_case} hfp={ok_hfp} "
                      f"plan_year={ok_year} budget={ok_budget}", file=_real_out)
    print(f"{checks - failures}/{checks} pairs round-trip unchanged", file=_real_out)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

"""Step-4 acceptance: the builder reproduces make_cases.py's 39 workbooks cell for cell.

Run from the repository root:

    uv run python fork-notes/synthetic/check_library_builder.py

`make_cases.py` writes the synthetic household into a temporary folder (its 39 workbooks, the
case TOMLs and the JSONs) and `scenarios.json`: the same cases as schema-v2 scenarios for
`owlplanner.library.builder` -- events (work, claiming, rent, a home purchase, care) plus the
hand rows. For every scenario this check runs the builder and compares:

1. the built case against "expected_case" (the case the scenario's `set` builds): the coupled
   edits of run-library-design.md section 6.2 -- the move or school district from the purchase,
   the marketplace start year from the last work year, the claiming ages from the claim events;
2. the builder's tables written out as `HFP.xlsx` (through `export_case`, the run's own path)
   against make_cases.py's workbook of the same name, **cell for cell**: sheet names, sizes and
   every value, person sheets and Budget, Debts and Fixed Assets rows included (the row order
   too);
3. for a work-variant scenario (no workbook of its own: an edit of the baseline workbook), the
   generated person cells against the `hfp` edits its `set` applies.

Every line reports one scenario; the last line reports the totals. Exit 0 when everything
matches, 1 on a difference, 2 when the synthetic cases cannot be built.
"""

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from owlplanner.library import export_case  # noqa: E402
from owlplanner.library import builder  # noqa: E402


def load_workbook_values(path):
    """{sheet: [[cell, ...], ...]} for every sheet of the workbook."""
    wb = openpyxl.load_workbook(path)
    return {
        sheet: [[cell.value for cell in row] for row in wb[sheet].iter_rows()]
        for sheet in wb.sheetnames
    }


def compare_workbook(name, expected_path, built_path):
    """[] when the two workbooks hold the same values, else the differences (capped)."""
    expected = load_workbook_values(expected_path)
    built = load_workbook_values(built_path)
    problems = []
    if set(expected) != set(built):
        problems.append(f"sheets: {sorted(expected)} != {sorted(built)}")
        return problems
    for sheet, rows in expected.items():
        other = built[sheet]
        if len(rows) != len(other):
            problems.append(f"{sheet}: {len(rows)} rows != {len(other)}")
            continue
        for i, (a, b) in enumerate(zip(rows, other, strict=True)):
            if len(a) != len(b):
                problems.append(f"{sheet} row {i + 1}: {len(a)} cells != {len(b)}")
                continue
            for j, (va, vb) in enumerate(zip(a, b, strict=True)):
                if va != vb:
                    problems.append(f"{sheet} row {i + 1}, column {j + 1}: {va!r} != {vb!r}")
                    if len(problems) >= 8:
                        return problems + ["..."]
    return problems


def compare_case(expected, built):
    """[] when the two case dictionaries hold the same values, else the differences (capped)."""
    problems = []

    def walk(a, b, where):
        if len(problems) >= 8:
            return
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                if key not in a:
                    problems.append(f"{where}{key}: added ({b[key]!r})")
                elif key not in b:
                    problems.append(f"{where}{key}: removed (was {a[key]!r})")
                else:
                    walk(a[key], b[key], f"{where}{key}.")
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                problems.append(f"{where[:-1]}: {len(a)} != {len(b)} values")
            else:
                for i, (x, y) in enumerate(zip(a, b, strict=True)):
                    walk(x, y, f"{where}{i}.")
        elif a != b or isinstance(a, bool) != isinstance(b, bool):
            problems.append(f"{where[:-1]}: {a!r} != {b!r}")

    walk(expected, built, "")
    return problems


def compare_hfp_edits(edits, tables):
    """[] when the builder's person cells equal the scenario's `hfp` edits, else the differences."""
    problems = []
    for person, spans in edits.items():
        table = tables.get(person)
        if table is None:
            problems.append(f"{person}: no person sheet")
            continue
        columns = table["columns"]
        by_year = {int(row[columns.index("year")]): row for row in table["rows"]}
        for span in spans:
            for year in range(span["years"][0], span["years"][-1] + 1):
                row = by_year.get(year)
                if row is None:
                    problems.append(f"{person} {year}: no row")
                    continue
                for column, value in span.items():
                    if column == "years":
                        continue
                    got = row[columns.index(column)]
                    if got != value:
                        problems.append(f"{person} {year} {column}: {value!r} != {got!r}")
    return problems


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        made = tmp / "cases"
        print(f"Building the synthetic household (make_cases.py -> {made}) ...")
        run = subprocess.run(
            [sys.executable, str(ROOT / "fork-notes" / "synthetic" / "make_cases.py"),
             "--out-dir", str(made)],
            capture_output=True, text=True,
        )
        if run.returncode != 0:
            print(run.stdout)
            print(run.stderr)
            print("make_cases.py failed")
            return 2
        scenarios = json.loads((made / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]

        ok = 0
        failures = []
        for entry in scenarios:
            name = entry["name"]
            scenario = copy.deepcopy(entry["scenario"])
            case, tables, provenance = builder.build(scenario)
            problems = compare_case(entry["expected_case"], case)
            kind = "workbook" if "workbooks" in entry else "hfp edits"
            if "workbooks" in entry:
                built_dir = tmp / "built" / name
                export_case(scenario, built_dir)
                for workbook in entry["workbooks"]:
                    problems += compare_workbook(workbook, made / workbook, built_dir / "HFP.xlsx")
            else:
                problems += compare_hfp_edits(entry.get("hfp") or {}, tables)
            if problems:
                failures.append((name, kind, problems))
                print(f"{name}: {len(problems)} difference(s) ({kind})")
                for problem in problems[:8]:
                    print(f"    {problem}")
            else:
                ok += 1
        workbooks = sum(len(e.get("workbooks") or []) for e in scenarios)
        print(f"{ok}/{len(scenarios)} scenarios match make_cases.py "
              f"({workbooks} workbooks cell for cell; case fields and hfp edits included).")
        return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

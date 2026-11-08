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
   whole built workbook against the baseline workbook with its `hfp` edits overlaid -- so the
   generated rows and cells outside the edits are checked too (review U8).

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
from owlplanner.library import export_case, import_case  # noqa: E402
from owlplanner.library.casefiles import convert_housing  # noqa: E402
from owlplanner.library import builder  # noqa: E402

BASE_WORKBOOK = "HFP_ari+noa.xlsx"  # the baseline workbook a work variant's edits apply to


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
    """[] when the two case dictionaries hold the same values, else the differences (capped).

    Leaves compare with their types (review U8): per T1/V3 the generated TOML keeps an int and
    a float apart, so `1` and `1.0` are not the same case field.
    """
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
        elif type(a) is not type(b) or a != b:
            problems.append(f"{where[:-1]}: {a!r} != {b!r}")

    walk(expected, built, "")
    return problems


def expected_workbook(made, entry):
    """A work variant's expected workbook: the baseline's with its `hfp` edits overlaid.

    A work variant has no workbook of its own (its `set` is an edit of the baseline workbook),
    but its events generate the baseline's rows too -- the home, the rent -- and those must
    match the baseline workbook cell for cell (review U8: comparing the edit cells alone let a
    wrong generated value through).
    """
    wb = openpyxl.load_workbook(made / BASE_WORKBOOK)
    for person, spans in (entry.get("hfp") or {}).items():
        ws = wb[person]
        header = [c.value for c in ws[1]]
        year_at = header.index("year") + 1
        for span in spans:
            for r in range(2, ws.max_row + 1):
                if span["years"][0] <= ws.cell(r, year_at).value <= span["years"][-1]:
                    for column, value in span.items():
                        if column != "years":
                            ws.cell(r, header.index(column) + 1).value = value
    path = made.parent / f"_expected_{entry['name']}.xlsx"
    wb.save(path)
    return path


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
            case, _tables, _provenance = builder.build(scenario)
            problems = compare_case(entry["expected_case"], case)
            kind = "workbook" if "workbooks" in entry else "workbook (baseline + edits)"
            built_dir = tmp / "built" / name
            export_case(scenario, built_dir)
            if "workbooks" in entry:
                for workbook in entry["workbooks"]:
                    problems += compare_workbook(workbook, made / workbook, built_dir / "HFP.xlsx")
            else:
                problems += compare_workbook(f"{name} (baseline + edits)", expected_workbook(made, entry),
                                             built_dir / "HFP.xlsx")
            if problems:
                failures.append((name, kind, problems))
                print(f"{name}: {len(problems)} difference(s) ({kind})")
                for problem in problems[:8]:
                    print(f"    {problem}")
            else:
                ok += 1
        workbooks = sum(len(e.get("workbooks") or []) for e in scenarios)
        print(f"{ok}/{len(scenarios)} scenarios match make_cases.py "
              f"({workbooks} workbooks cell for cell; the work variants against the baseline "
              "plus their edits; case fields and every cell included).")

        # Ergonomics review S-3: each workbook imported as a hand case (its case file as the
        # scenario's events generate it, the workbook as make_cases.py wrote it) turns into
        # rent / purchase / care events that rebuild its tables and case cell for cell.
        converted = 0
        conversion_failures = []
        for entry in scenarios:
            for workbook in entry.get("workbooks") or []:
                case_dir = tmp / "imported" / entry["name"]
                export_case(copy.deepcopy(entry["scenario"]), case_dir)
                hand = import_case(case_dir / "Case.toml", hfp_path=made / workbook)
                result, problems = convert_housing(hand)
                if result is None:
                    conversion_failures.append(workbook)
                    print(f"{workbook}: not converted")
                    for problem in problems[:8]:
                        print(f"    {problem}")
                else:
                    converted += 1
        print(f"{converted}/{workbooks} imported workbooks convert to events that rebuild them exactly "
              "(S-3).")
        return 1 if failures or conversion_failures else 0


if __name__ == "__main__":
    sys.exit(main())

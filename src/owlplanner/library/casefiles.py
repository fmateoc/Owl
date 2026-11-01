"""Scenario <-> Owl files: Case.toml, HFP.xlsx and the budget sidecar (build step 1).

Import reads a case dictionary (TOML) and an HFP workbook into a schema-v1 scenario; export
writes them back as a run's generated files (frozen per run, run-library-design.md section 5).
Both directions go through Owl's own code: `config.toml_io.load_toml` / `save_toml` for the
case dictionary and `hfp_io.read`'s conditioning for the workbook tables, so an imported run
re-loads exactly as Owl would load it, and `owlcli run` on the generated `Case.toml` sees the
same inputs.

Budget sidecar: `optimization_parameters.budget_file` (Owl-budget's JSON) is kept beside the
generated files and its reference in the case dictionary is preserved. Owl's own rule stands:
the Budget sheet wins when both are present (`config.plan_bridge._load_budget_file`), and
`plan.saveContributions` keeps file-sourced lines out of the workbook.

Not here: `rates.csv` (the downturn rate table, D11) arrives with build step 5b; events and
the builder with step 4 (scenario schema version 2).
"""

from __future__ import annotations

import copy
import io
import tempfile
from pathlib import Path

from .scenario import SCHEMA_VERSION, ScenarioError, validate

CASE_TOML = "Case.toml"
HFP_XLSX = "HFP.xlsx"
HOUSE_TABLES = ("Debts", "Fixed Assets", "Budget")
BUDGET_SIDECAR_DEFAULT = "budget.json"


def _json_safe(value):
    """A JSON-storable copy of one value (numpy unwrapped, non-finite floats to None)."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        import math

        return value if math.isfinite(value) else None
    if value.__class__.__name__ in ("NAType", "NaTType"):
        return None
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (ValueError, AttributeError):
            pass
    if hasattr(value, "tolist"):
        try:
            return _json_safe(value.tolist())
        except (ValueError, TypeError, AttributeError):
            pass
    return value


def df_to_table(df) -> dict:
    """A DataFrame in the scenario's JSON table form: {columns, rows}."""
    import pandas as pd

    if not isinstance(df, pd.DataFrame):
        raise ScenarioError(f"expected a DataFrame, got {type(df).__name__}")
    columns = [str(c) for c in df.columns]
    rows = [[_json_safe(v) for v in row] for row in df.itertuples(index=False, name=None)]
    return {"columns": columns, "rows": rows}


def table_to_df(table: dict):
    """The scenario's JSON table form back as a DataFrame."""
    import pandas as pd

    return pd.DataFrame(table["rows"], columns=table["columns"])


def _as_table(value) -> dict:
    if isinstance(value, dict) and "columns" in value and "rows" in value:
        return {"columns": list(value["columns"]), "rows": [list(r) for r in value["rows"]]}
    return df_to_table(value)


def _plan_year_of(case: dict):
    start = (case.get("basic_info") or {}).get("start_date")
    if isinstance(start, str) and len(start) >= 4 and start[:4].isdigit():
        return int(start[:4])
    return None


def scenario_from_case(case, time_lists=None, house_lists=None, *, plan_year=None, budget_file=None) -> dict:
    """A schema-v1 scenario from a case dictionary and the HFP tables (hand rows).

    `time_lists` maps a person's name to their year table (DataFrame or {columns, rows});
    `house_lists` holds "Debts", "Fixed Assets" and "Budget". `budget_file` is
    {"ref": <the case dict's name>, "text": <the JSON file's text>} for a budget_file case.
    """
    hfp = {}
    for name, table in (time_lists or {}).items():
        hfp[str(name)] = _as_table(table)
    for name in HOUSE_TABLES:
        if house_lists and name in house_lists:
            hfp[name] = _as_table(house_lists[name])
    scenario = {
        "schema_version": SCHEMA_VERSION,
        "plan_year": plan_year if plan_year is not None else _plan_year_of(case),
        "case": _json_safe(case),
        "hfp": hfp,
    }
    if budget_file:
        scenario["budget_file"] = {"ref": str(budget_file["ref"]), "text": str(budget_file["text"])}
    validate(scenario)
    return scenario


def scenario_from_ui(uidic: dict, plan) -> dict:
    """A scenario straight from the app's pages, before any solve (build step 1, R6).

    The case dictionary comes through `config.ui_bridge.ui_to_config` (never
    `owlbridge.getCaseString`, which is empty before the first run); the tables come from
    `plan.saveContributions()`, the workbook the Download button writes, read back through
    `hfp_io.read` so they are conditioned exactly as on a reload. The caller syncs the UI's
    edited tables into the plan first (`ui.owlbridge.saveContributions` does it with
    `_setContributions`).
    """
    from owlplanner.config.ui_bridge import ui_to_config

    case = ui_to_config(dict(uidic))
    with tempfile.TemporaryDirectory() as tmp:
        time_lists, house_lists = _tables_from_plan(plan, Path(tmp))
    budget_file = None
    if getattr(plan, "budgetFromFile", False):
        budget_file = _read_budget_text(str(getattr(plan, "budgetFileName", "") or ""), None)
    return scenario_from_case(case, time_lists, house_lists, budget_file=budget_file)


def _tables_from_plan(plan, tmpdir: Path):
    """The HFP tables exactly as the Download button's workbook carries them."""
    from owlplanner import hfp_io

    workbook = tmpdir / HFP_XLSX
    plan.saveContributions().save(workbook)
    _, time_lists, house_lists, _, _ = hfp_io.read(str(workbook), plan.inames, plan.horizons, plan.mylog)
    return time_lists, house_lists


def _hfp_reference(case: dict):
    """The case dict's workbook name, normalized as plan_bridge normalizes it, or None."""
    from owlplanner.config.plan_bridge import _normalize_hfp_file_name

    value = (case.get("household_financial_profile") or {}).get("HFP_file_name")
    if not isinstance(value, str):
        return None
    name = _normalize_hfp_file_name(value)
    return None if name == "None" else name


def _resolve_sibling(ref: str, case_path, explicit=None):
    """CWD first, then next to the case file (plan_bridge's own order)."""
    if explicit is not None:
        path = Path(explicit)
        if not path.exists():
            raise ScenarioError(f"{path} not found")
        return path
    candidates = [Path(ref)]
    if case_path is not None:
        candidates.append(Path(case_path).parent / ref)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _read_budget_text(ref: str, case_path, budget_path=None):
    """The budget sidecar {"ref", "text"} for a budget_file case, or None."""
    if not ref or str(ref).strip().lower() in ("", "none"):
        return None
    ref = str(ref).strip()
    path = _resolve_sibling(ref, case_path, budget_path)
    if path is None:
        raise ScenarioError(f"budget file {ref!r} not found")
    return {"ref": ref, "text": path.read_text(encoding="utf-8")}


def import_case(case_path, hfp_path=None, budget_path=None) -> dict:
    """Read a case file and its HFP workbook into a scenario (section 6.4: hand rows only)."""
    from owlplanner import hfp_io
    from owlplanner.config.plan_bridge import config_to_plan
    from owlplanner.config.toml_io import load_toml

    case_path = Path(case_path)
    case, dirname, _ = load_toml(str(case_path))

    time_lists, house_lists = {}, {}
    ref = _hfp_reference(case)
    workbook = Path(hfp_path) if hfp_path is not None else None
    if workbook is None and ref is not None:
        workbook = _resolve_sibling(ref, case_path)
        if workbook is None:
            raise ScenarioError(f"HFP workbook {ref!r} not found for {case_path}")
    if workbook is not None:
        if not workbook.exists():
            raise ScenarioError(f"{workbook} not found")
        # The plan supplies inames and horizons (life expectancy), the two inputs
        # hfp_io.read needs to condition the tables; nothing is solved.
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=False)
        _, time_lists, house_lists, _, _ = hfp_io.read(
            str(workbook), plan.inames, plan.horizons, plan.mylog
        )

    budget_ref = (case.get("optimization_parameters") or {}).get("budget_file") or ""
    budget_file = _read_budget_text(str(budget_ref), case_path, budget_path)
    return scenario_from_case(case, time_lists, house_lists, budget_file=budget_file)


def _sidecar_target(ref: str):
    """Where the sidecar goes under inputs/, and the reference to record (None: unchanged)."""
    name = Path(str(ref).strip()) if str(ref).strip() else Path(BUDGET_SIDECAR_DEFAULT)
    if not name.is_absolute() and ".." not in name.parts:
        return name, None
    flat = Path(name.name or BUDGET_SIDECAR_DEFAULT)
    return flat, str(flat)


def export_case(scenario: dict, out_dir) -> list:
    """Write the generated files (Case.toml, HFP.xlsx, the budget sidecar) into out_dir.

    This is the step-1 builder for hand rows: the generated files of a run are written once
    and frozen (section 5, R9). Returns the paths written.
    """
    import pandas as pd
    from owlplanner.config.toml_io import save_toml

    validate(scenario)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    case = copy.deepcopy(scenario["case"])
    written = []

    sidecar = scenario.get("budget_file")
    if sidecar:
        target, new_ref = _sidecar_target(sidecar.get("ref", ""))
        path = out / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sidecar["text"], encoding="utf-8")
        written.append(path)
        if new_ref is not None:
            case.setdefault("optimization_parameters", {})["budget_file"] = new_ref

    workbook = out / HFP_XLSX
    tables = scenario["hfp"]
    if tables:
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            for sheet, table in tables.items():
                table_to_df(table).to_excel(writer, sheet_name=sheet, index=False)
        written.append(workbook)
        case.setdefault("household_financial_profile", {})["HFP_file_name"] = HFP_XLSX
    else:
        # No tables, no workbook: Owl's canonical no-HFP sentinel (plan_bridge).
        case.setdefault("household_financial_profile", {})["HFP_file_name"] = "None"

    buf = io.StringIO()
    save_toml(case, buf)
    case_file = out / CASE_TOML
    case_file.write_text(buf.getvalue(), encoding="utf-8")
    written.append(case_file)
    return written

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
`plan.saveContributions` keeps file-sourced lines out of the workbook. Whenever the case names
a `budget_file` the sidecar is captured and written (V2: a frozen pair must never reference a
file it does not carry), and its file is resolved CWD-then-beside-the-case exactly as
`_load_budget_file` resolves it (V1; pass `case_dir=` or `budget_path=` where that is not enough).

Canonical case dictionary (T1, `fork-notes/run-library-step1-review-2.md`): the scenario holds
the case exactly as its generated `Case.toml` reads back. `canonical_case` writes the library's
own file names (`HFP.xlsx` or Owl's `"None"`, the sidecar's name under `inputs/`) and passes the
dictionary through `save_toml`'s encoder and back (8 significant figures, V10), so re-importing a
run's own files gives the same scenario and the same inputs hash. It does not use `load_toml`,
whose `sanitize_config` is date-dependent (a past `startRothConversions` is clamped to this year).

Saving from the pages (T1, T3): `ui_to_config` fills Owl's UI defaults and turns the start date's
year into the current year, so it cannot serve as the canonical form (it is also lossy: on the
synthetic condo case it drops `asset_allocation.interpolation_*`). `scenario_from_ui(base=...)`
therefore applies to the opened run's case only the fields the pages changed (the difference
between `ui_to_config` of the base and of the pages' state), and keeps the base's plan year.

Known limits of this step (from `fork-notes/run-library-step1-review.md`):

- The tables are `hfp_io.read`'s **conditioned** tables (V5): every year to the horizon is
  filled with zeros, rows outside `today-5 .. today+horizon` are dropped, and a past Fixed Assets
  year is clamped to today. Import is therefore date-dependent, but only through the year:
  a run is captured in its plan year and solved only in it (`check_plan_year`, R1; design
  section 8.3, revised 2026-11-02: no frozen "as of" date), so its tables are conditioned to
  the year they are solved in.
- `load_toml` (import) applies `sanitize_config`, which clamps a past `startRothConversions` to
  this year: another date dependence of import, through the year only, like V5's.
- `start_date = "today"` is stored as the capture date (an absolute date), so a run's first-year
  fraction does not move with the day it is solved on, and re-importing its own files gives the
  same hash.
- `save_toml`'s encoder writes floats with 8 significant figures (V10); the scenario stores the
  truncated values (T1), so it matches its frozen `Case.toml`.
- For a case with no workbook both entry paths record the plan's zero-filled tables and export
  an `HFP.xlsx` (V9); with `base=` the two paths give the same scenario for an unedited case.

Not here: `rates.csv` (the downturn rate table, D11) arrives with build step 5b. Events and the
builder (scenario schema version 2) are `library.builder` (step 4): export runs `build()`, so
the generated rows and case fields of a scenario's events land in the frozen files with
provenance markers, and hand rows are untouched.
"""

from __future__ import annotations

import copy
import io
import tempfile
from datetime import date
from pathlib import Path

from .scenario import SCHEMA_VERSION, ScenarioError, canonical_json, migrate, normalize, validate

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
    """A scenario of hand rows from a case dictionary and the HFP tables (section 6.4).

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
    # Normalized and canonicalized before hashing and before generating, so scenario.json is
    # exactly the document the frozen files are built from and read back as (V3, T1).
    return canonicalize(scenario)


def canonicalize(scenario: dict) -> dict:
    """The scenario with its case dictionary in canonical form (T1); validated.

    Idempotent. The case gets the library's own file names and goes through `save_toml`'s
    encoder and back, so it equals what the generated `Case.toml` reads back as.
    """
    scenario = normalize(scenario)
    scenario = migrate(scenario)  # stored scenarios are current-version (2, with events)
    validate(scenario)  # rejects None and non-finite values before the encoder sees them (V4)
    scenario["hfp"] = {name: _canonical_table(table) for name, table in scenario["hfp"].items()}
    scenario["case"], sidecar = canonical_case(
        scenario["case"], has_tables=bool(scenario["hfp"]), sidecar=scenario.get("budget_file")
    )
    if sidecar is not None:
        scenario["budget_file"] = sidecar
    # 'today' as the balances' date means the day of capture: stored as an absolute date, so
    # the plan's first-year fraction (`Plan._setStartingDate`) does not move with the day a run
    # is solved on, and re-importing a run's own files gives the same hash.
    info = scenario["case"].get("basic_info")
    if isinstance(info, dict) and str(info.get("start_date", "")).strip().lower() == "today":
        info["start_date"] = date.today().isoformat()
    if scenario.get("plan_year") is None:
        # The year the balances and year rows were entered for (R1): the start date's year,
        # else the year of capture.
        scenario["plan_year"] = _plan_year_of(scenario["case"]) or date.today().year
    validate(scenario)
    return scenario


def check_plan_year(scenario: dict) -> int:
    """The run's plan year, refused unless it is the current year (R1; design section 8.3).

    Owl's plan starts in the calendar year of the solve whatever the case says, so a run's
    balances and year rows are valid only in the year they were entered for: solved a year
    later, January's balances would be read as the new January's. Within the plan year a run
    solves the same on any day (with fixed claiming ages); the claiming-age search reads the
    current month on purpose, since a month already past cannot be claimed. A run for a new
    year is made by the yearly check-in (I4): new balances, a new plan year.
    """
    plan_year = scenario.get("plan_year")
    this_year = date.today().year
    if plan_year is None:
        raise ScenarioError("the run has no plan year: the library cannot tell when its inputs are valid")
    if int(plan_year) != this_year:
        raise ScenarioError(
            f"the run's plan year is {plan_year} but this is {this_year}: its balances and year rows "
            f"were entered for {plan_year}, and Owl would read them as {this_year}'s. Make a run for "
            f"{this_year} with this year's balances (save it as a new run from the pages)."
        )
    return int(plan_year)


def _canonical_cell(value):
    # A workbook cell is a double: 0 and 0.0 are one value there, and which one a table holds
    # depends only on how it was read (the source workbook's cells, or Owl's saveContributions
    # read back). Integral floats become ints so that incidental typing never changes the hash.
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _canonical_table(table: dict) -> dict:
    return {
        "columns": list(table["columns"]),
        "rows": [[_canonical_cell(v) for v in row] for row in table["rows"]],
    }


def canonical_case(case: dict, *, has_tables: bool, sidecar=None):
    """(case, sidecar) with the library's file names, read back through the TOML encoder."""
    import toml
    from owlplanner.config.toml_io import _CleanFloatEncoder

    case = copy.deepcopy(case)
    case.setdefault("household_financial_profile", {})["HFP_file_name"] = HFP_XLSX if has_tables else "None"
    if sidecar:
        target, _ = _sidecar_target(sidecar.get("ref", ""))
        sidecar = {"ref": target.as_posix(), "text": str(sidecar["text"])}
        case.setdefault("optimization_parameters", {})["budget_file"] = sidecar["ref"]
    case = toml.loads(toml.dumps(case, encoder=_CleanFloatEncoder()))
    return case, (sidecar or None)


def _apply_page_edits(base: dict, before: dict, after: dict) -> dict:
    """`base` with the fields that differ between `before` and `after` (the pages' edits).

    Dictionaries are walked key by key; anything else (lists included) is one field. A field
    the pages added is added, one they dropped is dropped, an unchanged one keeps base's value.
    """
    result = copy.deepcopy(base)
    _merge_edits(result, before, after)
    return result


def _merge_edits(target: dict, before: dict, after: dict) -> None:
    for key in set(before) | set(after):
        if key not in after:
            target.pop(key, None)
        elif key not in before:
            target[key] = copy.deepcopy(after[key])
        elif isinstance(before[key], dict) and isinstance(after[key], dict):
            if isinstance(target.get(key), dict):
                _merge_edits(target[key], before[key], after[key])
            else:
                # A section the base does not have: add it only if the pages changed something
                # in it (an empty section would be a spurious change, T1).
                section: dict = {}
                _merge_edits(section, before[key], after[key])
                if section:
                    target[key] = section
        elif canonical_json(before[key]) != canonical_json(after[key]):
            target[key] = copy.deepcopy(after[key])


def _with_year(start_date, year):
    """`start_date` ('YYYY-MM-DD' or 'MM-DD') moved to `year`; other values unchanged."""
    if year is None or not isinstance(start_date, str):
        return start_date
    parts = start_date.replace("/", "-").split("-")
    if len(parts) == 3 and parts[0].isdigit():
        return f"{int(year):04d}-{parts[1]}-{parts[2]}"
    if len(parts) == 2:
        return f"{int(year):04d}-{parts[0]}-{parts[1]}"
    return start_date


def scenario_from_ui(uidic: dict, plan, *, base=None, plan_year=None, case_dir=None, budget_path=None) -> dict:
    """A scenario straight from the app's pages, before any solve (build step 1, R6).

    The case dictionary comes through `config.ui_bridge.ui_to_config` (never
    `owlbridge.getCaseString`, which is empty before the first run); the tables come from
    `plan.saveContributions()`, the workbook the Download button writes, read back through
    `hfp_io.read` so they are conditioned exactly as on a reload. The caller syncs the UI's
    edited tables into the plan first (`ui.owlbridge.saveContributions` does it with
    `_setContributions`).

    `base` is the scenario of the run the pages were opened from (T1, T3). With it, only the
    fields the pages changed are applied to the base's case (`ui_to_config` of the base against
    `ui_to_config` of the pages), so an unedited save is identical to the base, the change
    summary lists the edits alone, and the base's plan year is kept. Without it (a case typed
    in the pages), the case is `ui_to_config`'s as is, with the current year as its plan year.
    `plan_year` overrides either; the start date's year follows the plan year (the pages always
    show the current year, and Owl ignores the start date's year). A case file from outside the
    library comes in through `import_case`, which keeps the file's own fields and year.

    The budget sidecar is captured whenever the case names a `budget_file` (V2): the base's,
    when the reference is unchanged and no `budget_path=` is given; else resolved
    CWD-then-`case_dir` like `plan_bridge._load_budget_file` (V1).

    With a base that has events (schema v2), the rows and cells the events generate are dropped
    from the saved hand rows (`_drop_generated`): they are regenerated wholesale from the events
    (markers first, S11), so an edit to a generated value does not survive a save.
    """
    from owlplanner.config.ui_bridge import config_to_ui, ui_to_config

    case = ui_to_config(dict(uidic))
    year = plan_year
    if base is not None:
        base = canonicalize(base)
        before = ui_to_config(config_to_ui(copy.deepcopy(base["case"])))
        case = _apply_page_edits(base["case"], before, case)
        if year is None:
            year = base.get("plan_year")
    if year is not None:
        info = case.setdefault("basic_info", {})
        info["start_date"] = _with_year(info.get("start_date"), year)
    with tempfile.TemporaryDirectory() as tmp:
        time_lists, house_lists = _tables_from_plan(plan, Path(tmp))
    if base is not None and base.get("events"):
        time_lists, house_lists = _drop_generated(time_lists, house_lists, base)
    ref = _budget_reference(case)
    base_sidecar = base.get("budget_file") if base is not None else None
    if ref and base_sidecar and budget_path is None and ref == base_sidecar["ref"]:
        budget_file = dict(base_sidecar)
    else:
        budget_file = _read_budget_text(
            ref,
            base=Path(case_dir) if case_dir is not None else None,
            explicit=budget_path,
        )
    return scenario_from_case(case, time_lists, house_lists, plan_year=year, budget_file=budget_file)


def _tables_from_plan(plan, tmpdir: Path):
    """The HFP tables exactly as the Download button's workbook carries them."""
    from owlplanner import hfp_io

    workbook = tmpdir / HFP_XLSX
    plan.saveContributions().save(workbook)
    _, time_lists, house_lists, _, _ = hfp_io.read(str(workbook), plan.inames, plan.horizons, plan.mylog)
    return time_lists, house_lists


def _drop_generated(time_lists, house_lists, base):
    """The plan's tables without the rows and cells the base's events generate.

    The pages hold the generated values too (they load the run's frozen files). A generated row
    is regenerated wholesale when the scenario is built (section 6.3, markers first, S11), so
    the saved hand rows keep only what the events do not generate. Section 6.3's per-cell
    overrides are the later increment; here an edit to a generated value is dropped.
    """
    from . import builder

    _case, _tables, provenance = builder.build(base)
    row_names: dict[str, set] = {}
    for key in provenance["rows"]:
        table, name = key.split("|", 1)
        row_names.setdefault(table, set()).add(name)
    cells: dict[str, dict[int, set]] = {}
    for sheet, column, year, _eid in provenance["cells"]:
        cells.setdefault(sheet, {}).setdefault(int(year), set()).add(column)

    clean_time = {}
    for name, table in (time_lists or {}).items():
        table = _as_table(table)
        by_year = cells.get(name, {})
        if by_year:
            columns = list(table["columns"])
            year_at = columns.index("year")
            rows = []
            for row in table["rows"]:
                row = list(row)
                for column in by_year.get(int(row[year_at]), ()):
                    if column in columns:
                        row[columns.index(column)] = 0
                rows.append(row)
            table = {"columns": columns, "rows": rows}
        clean_time[name] = table
    clean_house = {}
    for name, table in (house_lists or {}).items():
        table = _as_table(table)
        drop = row_names.get(name, set())
        if drop and "name" in table["columns"]:
            at = table["columns"].index("name")
            table = {"columns": list(table["columns"]),
                     "rows": [row for row in table["rows"] if row[at] not in drop]}
        clean_house[name] = table
    return clean_time, clean_house


def _hfp_reference(case: dict):
    """The case dict's workbook name, normalized as plan_bridge normalizes it, or None."""
    from owlplanner.config.plan_bridge import _normalize_hfp_file_name

    value = (case.get("household_financial_profile") or {}).get("HFP_file_name")
    if not isinstance(value, str):
        return None
    name = _normalize_hfp_file_name(value)
    return None if name == "None" else name


def _budget_reference(case: dict) -> str:
    """The case dict's budget_file name ('' when there is none; 'None' is the sentinel)."""
    ref = str((case.get("optimization_parameters") or {}).get("budget_file") or "").strip()
    return "" if ref.lower() == "none" else ref


def _resolve_ref(ref: str, *, explicit=None, base=None):
    """Explicit path first, then CWD, then beside the case file (`_load_budget_file`'s order)."""
    if explicit is not None:
        path = Path(explicit)
        if not path.exists():
            raise ScenarioError(f"{path} not found")
        return path
    candidates = [Path(ref)]
    if base is not None:
        candidates.append(Path(base) / ref)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _read_budget_text(ref: str, *, base=None, explicit=None):
    """The budget sidecar {"ref", "text"} for a budget_file case, or None."""
    if not ref:
        return None
    ref = str(ref).strip()
    path = _resolve_ref(ref, explicit=explicit, base=base)
    if path is None:
        where = f" (sought in {base})" if base is not None else ""
        raise ScenarioError(
            f"budget file {ref!r} not found{where}; pass budget_path= or case_dir= to the caller"
        )
    return {"ref": ref, "text": path.read_text(encoding="utf-8")}


def import_case(case_path, hfp_path=None, budget_path=None) -> dict:
    """Read a case file and its HFP workbook into a scenario (section 6.4: hand rows only).

    Without a workbook the scenario holds the plan's zero-filled tables (the same route
    `scenario_from_ui` takes), so both entry paths agree (V9).
    """
    from owlplanner import hfp_io
    from owlplanner.config.plan_bridge import config_to_plan
    from owlplanner.config.toml_io import load_toml

    case_path = Path(case_path)
    case, dirname, _ = load_toml(str(case_path))
    # The plan supplies inames and horizons (life expectancy), the two inputs hfp_io.read
    # needs to condition the tables; nothing is solved.
    plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=False)

    ref = _hfp_reference(case)
    workbook = Path(hfp_path) if hfp_path is not None else None
    if workbook is None and ref is not None:
        workbook = _resolve_ref(ref, base=case_path.parent)
        if workbook is None:
            raise ScenarioError(f"HFP workbook {ref!r} not found for {case_path}")
    if workbook is not None:
        if not workbook.exists():
            raise ScenarioError(f"{workbook} not found")
        _, time_lists, house_lists, _, _ = hfp_io.read(
            str(workbook), plan.inames, plan.horizons, plan.mylog
        )
    else:
        with tempfile.TemporaryDirectory() as tmp:
            time_lists, house_lists = _tables_from_plan(plan, Path(tmp))

    budget_file = _read_budget_text(_budget_reference(case), base=case_path.parent, explicit=budget_path)
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

    The frozen files of a run (section 5, R9): the hand rows plus what the scenario's events
    generate (`library.builder.build`, step 4). Returns the paths written.
    """
    import pandas as pd
    from owlplanner.config.toml_io import save_toml

    from . import builder

    validate(scenario)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    case, tables, _provenance = builder.build(scenario)
    written = []

    sidecar = scenario.get("budget_file")
    if _budget_reference(case) and not sidecar:
        raise ScenarioError(
            f"the case names budget_file {_budget_reference(case)!r} but the scenario holds no "
            "sidecar; the generated files would not load (V2)"
        )
    if sidecar:
        target, new_ref = _sidecar_target(sidecar.get("ref", ""))
        path = out / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sidecar["text"], encoding="utf-8")
        written.append(path)
        if new_ref is not None or not _budget_reference(case):
            case.setdefault("optimization_parameters", {})["budget_file"] = target.as_posix()

    workbook = out / HFP_XLSX
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

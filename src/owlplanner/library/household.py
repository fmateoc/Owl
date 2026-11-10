"""A household's first inputs, without a case file (the "operate it alone" request, 2026-11-10).

A run needs a case file (TOML) and, for anything year by year, a workbook. Writing the first
by hand is developer work (`fork-notes/running-locally.md`: a template with `TODO`s, amounts
in thousands, list-per-person fields). This module takes a short set of **answers** -- who,
where, savings, Social Security and pensions, the goal -- and makes the case from them, so
that the interface can ask for them in a form:

- `blank_answers()` / `problems(answers)`: the answers and what is still wrong with them, in
  plain words. Amounts are in **dollars** (the case file's thousands are a trap: balances
  typed in dollars came back "infeasible" with no other hint, CLAUDE.md);
- `case_from_answers(answers)`: the Owl case dictionary, the assumptions nobody was asked
  about set to documented defaults (`ASSUMPTIONS`), every one of them editable afterwards in
  the case pages;
- `write_workbook(path, answers)`: an empty workbook to fill in Excel -- one sheet per person
  with a row per plan year, the Budget, Debts and Fixed Assets sheets with their headers, and
  a first sheet of instructions (the reader takes the sheets it knows by name and leaves the
  rest); it never overwrites a file;
- `read_workbook(path, answers)`: a filled workbook read as the plan will read it, and what
  was found in it in words, so that a wrong column or a missing zero is seen before a solve;
- `first_scenario(answers, workbook)`: the library scenario for the first run.

Nothing here is specific to one household: the defaults are Owl's own or stated below.
"""

from __future__ import annotations

import copy
import io
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Optional

from . import builder
from .casefiles import HOUSE_TABLES, canonicalize, import_case
from .scenario import ScenarioError

DRAFT_JSON = "setup-draft.json"   # the answers typed so far, kept in the library folder
WORKBOOK_NAME = "Household.xlsx"  # the empty workbook written into the household folder

# What nobody is asked at the start, and why. All of it is in the case pages afterwards.
ASSUMPTIONS = {
    # A fixed, deterministic rate path: the library's builder prices a purchase or a rent
    # from the case's inflation path and refuses one that is redrawn at every build.
    "rates_method": "conservative",
    # Federal law as enacted: no reversion of the 2025 brackets (the fork's decision D1). The
    # interface caps the year at this year + 40.
    "obbba_years_ahead": 40,
    "heirs_rate": 30.0,
    "dividend_rate": 2.0,
    "survivor_percent": 60,
    "pension_age": 65.0,
}

SS_AGE_MIN, SS_AGE_MAX = 62.0, 70.0
_SHEET_FORBIDDEN = re.compile(r"[\[\]:*?/\\]")
_PERSON = {
    "name": "", "born": "", "sex": "F", "plan_to_age": 89,
    "taxable": 0.0, "tax_deferred": 0.0, "roth": 0.0, "hsa": 0.0, "cost_basis": None,
    "ss_monthly": 0.0, "ss_age": 67.0,
    "pension_monthly": 0.0, "pension_age": ASSUMPTIONS["pension_age"], "pension_indexed": False,
}


def blank_answers(today: Optional[date] = None) -> dict:
    """The answers before anything is typed: a couple, balances as of 1 January this year."""
    today = today or date.today()
    return {
        "couple": True,
        "people": [copy.deepcopy(_PERSON), dict(copy.deepcopy(_PERSON), sex="M")],
        "state": "",
        "locality": "",
        "balance_date": date(today.year, 1, 1).isoformat(),
        "goal": "spend",          # "spend": as much as is safe, leaving `bequest`; "leave": spend
        "bequest": 0.0,           # `spending` a year and leave as much as possible
        "spending": None,
        "stocks_percent": 60,
        "marketplace": False,     # health insurance bought on the marketplace before 65
        "marketplace_year": today.year,
        "marketplace_premium": None,
    }


def people(answers: dict) -> list:
    """The one or two people the answers are about."""
    return list(answers.get("people") or [])[: 2 if answers.get("couple") else 1]


def _date(text) -> Optional[date]:
    try:
        return date.fromisoformat(str(text))
    except ValueError:
        return None


def _amount(value) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return float("nan")


def problems(answers: dict, today: Optional[date] = None) -> list[str]:
    """What stops a plan from being made of these answers, in plain words (empty: nothing)."""
    today = today or date.today()
    out: list[str] = []
    who = people(answers)
    names = [str(p.get("name") or "").strip() for p in who]
    for i, (person, name) in enumerate(zip(who, names, strict=True)):
        label = name or f"person {i + 1}"
        if not name:
            out.append(f"Person {i + 1} has no name yet.")
        elif _SHEET_FORBIDDEN.search(name) or len(name) > 31 or name in HOUSE_TABLES or name == "Instructions":
            out.append(f"The name {name!r} cannot name a workbook sheet: at most 31 characters, none of "
                       "[ ] : * ? / \\, and not Budget, Debts, Fixed Assets or Instructions.")
        born = _date(person.get("born"))
        if born is None:
            out.append(f"{label}: the date of birth is missing.")
        else:
            age = today.year - born.year
            if not 18 <= age <= 110:
                out.append(f"{label}: born in {born.year} would be {age} this year. Check the date of birth.")
            elif int(person.get("plan_to_age") or 0) < age + 2:
                out.append(f"{label}: the plan runs to age {person.get('plan_to_age')}, but {label} is "
                           f"{age} this year. Plan at least two years ahead.")
            elif int(person.get("plan_to_age") or 0) > 120:
                out.append(f"{label}: the plan cannot run past age 120.")
        for field, what in (("taxable", "taxable savings"), ("tax_deferred", "tax-deferred savings"),
                            ("roth", "Roth savings"), ("hsa", "HSA savings"),
                            ("ss_monthly", "Social Security benefit"), ("pension_monthly", "pension")):
            value = _amount(person.get(field))
            if not value >= 0:  # NaN too
                out.append(f"{label}: the {what} must be an amount of zero or more.")
        basis = person.get("cost_basis")
        if basis not in (None, "") and not 0 <= _amount(basis) <= _amount(person.get("taxable")):
            out.append(f"{label}: what was paid for the taxable investments cannot be more than they are "
                       "worth today (leave it empty when it is not known).")
        ss_age = person.get("ss_age")
        if ss_age is not None and not SS_AGE_MIN <= _amount(ss_age) <= SS_AGE_MAX:
            out.append(f"{label}: Social Security starts between 62 and 70.")
        if _amount(person.get("ss_monthly")) > 6000:
            out.append(f"{label}: a Social Security benefit of ${_amount(person['ss_monthly']):,.0f} a "
                       "month is above the program's maximum. Enter the monthly amount at full "
                       "retirement age, not a yearly one.")
    if len(set(names)) < len(names) and all(names):
        out.append("The two people need different names (each has a sheet of their own in the workbook).")
    if not any(_amount(p.get(k)) > 0 for p in who for k in ("taxable", "tax_deferred", "roth", "hsa")):
        out.append("No savings are entered: a plan needs at least one account with money in it.")
    when = _date(answers.get("balance_date"))
    if when is None or when.year != today.year:
        out.append(f"The savings must be as of a date in {today.year}: a plan starts in the year it is "
                   "made in.")
    if answers.get("goal") == "leave" and not _amount(answers.get("spending")) > 0:
        out.append("To leave as much as possible, say how much you spend a year.")
    if not _amount(answers.get("bequest")) >= 0:
        out.append("The amount to leave must be zero or more.")
    if not 0 <= _amount(answers.get("stocks_percent")) <= 100:
        out.append("The share in stocks is between 0 and 100 percent.")
    if answers.get("marketplace"):
        if not _amount(answers.get("marketplace_premium")) > 0:
            out.append("Marketplace coverage needs the yearly benchmark premium (the second-cheapest "
                       "Silver plan for the household).")
        if int(answers.get("marketplace_year") or 0) < today.year:
            out.append(f"Marketplace coverage starts in {today.year} or later.")
    return out


def case_from_answers(answers: dict, *, workbook_name: Optional[str] = None, name: str = "our plan",
                      today: Optional[date] = None) -> dict:
    """The Owl case dictionary for these answers (amounts converted to the case's thousands)."""
    today = today or date.today()
    who = people(answers)
    n = len(who)
    stocks = float(answers.get("stocks_percent", 60))
    mix = [stocks, 100.0 - stocks, 0.0, 0.0]  # stocks, corporate bonds, Treasury notes, cash
    free = [p["name"] for p in who if p.get("ss_age") is None]  # ages left to Owl
    case: dict[str, Any] = {
        "case_name": name,
        "description": "Made from the answers of the first-time setup.",
        "basic_info": {
            "status": "married" if n == 2 else "single",
            "names": [str(p["name"]).strip() for p in who],
            "sexes": [p.get("sex") or "F" for p in who],
            "date_of_birth": [str(p["born"]) for p in who],
            "life_expectancy": [int(p["plan_to_age"]) for p in who],
            "start_date": str(answers["balance_date"]),
            "state": answers.get("state") or "",
            "locality": answers.get("locality") or "",
        },
        "savings_assets": {
            "taxable_savings_balances": [_amount(p.get("taxable")) / 1000.0 for p in who],
            "tax_deferred_savings_balances": [_amount(p.get("tax_deferred")) / 1000.0 for p in who],
            "tax_free_savings_balances": [_amount(p.get("roth")) / 1000.0 for p in who],
            "hsa_savings_balances": [_amount(p.get("hsa")) / 1000.0 for p in who],
        },
        "household_financial_profile": {"HFP_file_name": workbook_name or "None"},
        "fixed_income": {
            "pension_monthly_amounts": [_amount(p.get("pension_monthly")) for p in who],
            "pension_ages": [float(p.get("pension_age") or ASSUMPTIONS["pension_age"]) for p in who],
            "pension_indexed": [bool(p.get("pension_indexed")) for p in who],
            "social_security_pia_amounts": [_amount(p.get("ss_monthly")) for p in who],
            # An age left to Owl still needs a starting value: full retirement age.
            "social_security_ages": [float(p["ss_age"]) if p.get("ss_age") is not None else 67.0 for p in who],
        },
        "rates_selection": {
            "method": ASSUMPTIONS["rates_method"],
            "heirs_rate_on_tax_deferred_estate": ASSUMPTIONS["heirs_rate"],
            "dividend_rate": ASSUMPTIONS["dividend_rate"],
            "obbba_expiration_year": today.year + ASSUMPTIONS["obbba_years_ahead"],
        },
        "asset_allocation": {
            "interpolation_method": "linear",
            "type": "individual",
            "generic": [[list(mix), list(mix)] for _ in who],
        },
        "optimization_parameters": {
            "spending_profile": "flat",  # `first_scenario` makes it "budget" for a workbook with lines
            "surviving_spouse_spending_percent": ASSUMPTIONS["survivor_percent"],
            "objective": "maxBequest" if answers.get("goal") == "leave" else "maxSpending",
        },
        "solver_options": {
            "withSSAges": ("fixed" if not free else "optimize" if len(free) == n else free),
            "startRothConversions": today.year,
        },
        "results": {"default_plots": "today"},
    }
    if any(p.get("cost_basis") not in (None, "") for p in who):
        # Unknown for one of two: taken as the account's value (no gain), the neutral reading.
        case["savings_assets"]["taxable_cost_basis"] = [
            _amount(p["cost_basis"] if p.get("cost_basis") not in (None, "") else p.get("taxable")) / 1000.0
            for p in who]
    if answers.get("goal") == "leave":
        case["solver_options"]["netSpending"] = _amount(answers.get("spending")) / 1000.0
    else:
        case["solver_options"]["bequest"] = _amount(answers.get("bequest")) / 1000.0
    if answers.get("marketplace"):
        case["aca_settings"] = {
            "slcsp_annual": _amount(answers.get("marketplace_premium")) / 1000.0,
            "aca_start_year": int(answers.get("marketplace_year") or today.year),
        }
    return case


# ---------------------------------------------------------------------------
# The workbook
# ---------------------------------------------------------------------------

_PERSON_HELP = {
    "year": "One row per year of the plan. Do not change this column.",
    "anticipated wages": "Wages for the year as they appear on the tax return: pay minus what goes "
                         "into a pre-tax 401k, a deductible IRA or an HSA from pay. 0 once retired.",
    "months worked": "Months worked in the year (0-12). Only needed in a year someone stops working "
                     "while already receiving Social Security; leave 0 otherwise.",
    "other inc": "Other taxable income of the year (consulting, royalties). Negative for a deduction.",
    "net inv": "Net investment income from outside the accounts in the plan (usually 0).",
    "taxable ctrb": "Money added to the taxable (brokerage) account.",
    "401k ctrb": "The employee's own pre-tax 401k contribution.",
    "employer ctrb": "The employer's 401k contribution (match or other).",
    "Roth 401k ctrb": "Roth 401k contribution.",
    "IRA ctrb": "Deductible IRA contribution.",
    "Roth IRA ctrb": "Roth IRA contribution.",
    "HSA ctrb": "HSA contribution.",
    "Roth conv": "Leave empty: the plan chooses Roth conversions.",
    "Roth conv fixed": "Leave empty unless a conversion of that year is already decided.",
    "QCD": "Charitable distribution from an IRA (from age 70 1/2).",
    "big-ticket items": "One-time amounts: negative for a large expense (a car, a roof), positive "
                        "for money coming in (an inheritance, a sale).",
}
_INSTRUCTIONS = [
    "How to fill this workbook",
    "",
    "Amounts are in dollars a year, in today's money unless a line says otherwise. Empty cells are zero.",
    "Fill only what applies; a sheet left as it is adds nothing to the plan.",
    "",
    "A sheet per person: wages, contributions and one-time amounts, year by year. Every column's",
    "meaning is in a note on its heading (rest the pointer on it).",
    "",
    "Budget: what you spend, one line each (rent, food and everything else, property tax, insurance,",
    "medical). name: your words. type: rent, property tax, maintenance, insurance, medical, charity,",
    "care, or core for everything else. year and end: first and last year (end 0 = to the end of the",
    "plan). amount: dollars a year in today's money. rate: yearly growth above inflation, in percent.",
    "essential: TRUE for a line that cannot shrink (rent, taxes); the plan then finds how much is left",
    "for the others. With no Budget line, the plan spends as much as is safe, the same every year.",
    "",
    "Fixed Assets: a home or other property you own. year: when bought. basis: what was paid. value:",
    "what it is worth in the dollars of that year. rate: yearly growth in percent. yod: the year it is",
    "sold (0 = kept). commission: selling costs in percent. type: residence for the home you live in.",
    "",
    "Debts: loans. year: when it started. term: years. amount: borrowed. rate: percent. property: the",
    "Fixed Assets name of the home it is on (the loan is paid off when the home is sold).",
    "",
    "Do not rename the sheets or the headings. When done: save, close, and read the workbook in Owl.",
]


def plan_years(answers: dict, today: Optional[date] = None) -> list[int]:
    """The plan's years: this year to the year the last person reaches their age."""
    today = today or date.today()
    ends = [(_date(p.get("born")) or today).year + int(p.get("plan_to_age") or 0) for p in people(answers)]
    return list(range(today.year, max([today.year, *ends]) + 1))


def write_workbook(path, answers: dict, today: Optional[date] = None) -> Path:
    """Write the empty workbook for these people; refuses to replace an existing file."""
    import openpyxl
    from openpyxl.comments import Comment
    from openpyxl.styles import Font

    from owlplanner import hfp_io

    path = Path(path)
    if path.exists():
        raise ScenarioError(f"{path.name} is already in the folder and is not replaced: it may hold "
                            "your figures. Use it, or move it away first.")
    names = [str(p.get("name") or "").strip() for p in people(answers)]
    if not all(names):
        raise ScenarioError("The workbook has a sheet per person: give each person a name first.")
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Instructions"
    for row, text in enumerate(_INSTRUCTIONS, start=1):
        sheet.cell(row=row, column=1, value=text)
    sheet["A1"].font = Font(bold=True, size=14)
    sheet.column_dimensions["A"].width = 110
    bold = Font(bold=True)
    columns = hfp_io.timeHorizonItems()
    for name in names:
        sheet = book.create_sheet(name)
        for col, header in enumerate(columns, start=1):
            cell = sheet.cell(row=1, column=col, value=header)
            cell.font = bold
            cell.comment = Comment(_PERSON_HELP.get(header, header), "Owl")
            sheet.column_dimensions[cell.column_letter].width = max(12, len(header) + 2)
        for row, year in enumerate(plan_years(answers, today), start=2):
            sheet.cell(row=row, column=1, value=year)
            for col in range(2, len(columns) + 1):
                sheet.cell(row=row, column=col, value=0)
        sheet.freeze_panes = "B2"
    for title, headers in (("Budget", builder.BUDGET_COLUMNS), ("Debts", builder.DEBT_COLUMNS),
                           ("Fixed Assets", builder.ASSET_COLUMNS)):
        sheet = book.create_sheet(title)
        for col, header in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=col, value=header)
            cell.font = bold
            sheet.column_dimensions[cell.column_letter].width = max(12, len(header) + 2)
        sheet.freeze_panes = "A2"
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)
    return path


def first_scenario(answers: dict, workbook=None, *, name: str = "our plan",
                   today: Optional[date] = None) -> dict:
    """The library scenario for the first run: the case from the answers, the workbook's tables.

    A workbook with Budget lines makes the plan spend by them (`spending_profile = "budget"`);
    without one the spending is flat in today's money. Raises ScenarioError (or the reader's
    own error) when the workbook cannot be read as the plan needs it.
    """
    from owlplanner.config.toml_io import save_toml

    found = problems(answers, today)
    if found:
        raise ScenarioError("; ".join(found))
    workbook = Path(workbook) if workbook else None
    case = case_from_answers(answers, workbook_name=workbook.name if workbook else None, name=name, today=today)
    with tempfile.TemporaryDirectory() as tmp:
        case_file = Path(tmp) / "Case.toml"
        text = io.StringIO()
        save_toml(case, text)
        case_file.write_text(text.getvalue(), encoding="utf-8")
        scenario = import_case(case_file, workbook)
    if (scenario["hfp"].get("Budget") or {}).get("rows"):
        scenario["case"]["optimization_parameters"]["spending_profile"] = "budget"
        scenario = canonicalize(scenario)
    return scenario


def read_workbook(path, answers: dict, today: Optional[date] = None) -> dict:
    """A filled workbook as the plan reads it: {"lines": what was found, in words; "scenario"}.

    The reader's refusals (a heading mistyped, a sheet missing for a person) are raised as they
    are: they name the sheet and the column.
    """
    scenario = first_scenario(answers, path, today=today)
    hfp = scenario["hfp"]
    lines = []
    for person in scenario["case"]["basic_info"]["names"]:
        table = hfp.get(person) or {"columns": [], "rows": []}
        at = {c: i for i, c in enumerate(table["columns"])}

        def column(name, table=table, at=at):
            return [(int(r[at["year"]]), _amount(r[at[name]])) for r in table["rows"]] if name in at else []

        wages = [(y, v) for y, v in column("anticipated wages") if v]
        said = (f"wages from {wages[0][0]} to {wages[-1][0]} (the largest year ${max(v for _, v in wages):,.0f})"
                if wages else "no wages")
        saved = sum(v for name in at if name.endswith("ctrb") for _, v in column(name))
        if saved:
            said += f"; ${saved:,.0f} of contributions in all"
        once = [(y, v) for y, v in column("big-ticket items") if v]
        if once:
            said += "; one-time amounts: " + ", ".join(f"{y}: {v:+,.0f}" for y, v in once[:4]) + (
                ", ..." if len(once) > 4 else "")
        lines.append(f"**{person}**: {said}.")
    for sheet, what in (("Budget", "budget line"), ("Fixed Assets", "property"), ("Debts", "loan")):
        table = hfp.get(sheet) or {"columns": [], "rows": []}
        names = [str(r[table["columns"].index("name")]) for r in table["rows"]] if "name" in table["columns"] else []
        if names:
            lines.append(f"**{sheet}**: {len(names)} {what}{'s' if len(names) != 1 else ''} "
                         f"({', '.join(names[:8])}{', ...' if len(names) > 8 else ''}).")
        else:
            lines.append(f"**{sheet}**: none" + (
                " (the plan spends as much as is safe, the same every year in today's money)."
                if sheet == "Budget" else "."))
    return {"lines": lines, "scenario": scenario}


# ---------------------------------------------------------------------------
# The household folder
# ---------------------------------------------------------------------------


def home_dir(library_root) -> Path:
    """The household folder: $OWL_HOME_DIR (the launcher's folder argument), else the folder
    the library is in. The workbook the setup writes and the starter file live there."""
    import os

    env = os.environ.get("OWL_HOME_DIR")
    return Path(env) if env else Path(library_root).resolve().parent


def workbooks(home) -> list[Path]:
    """The Excel workbooks in the household folder (not Excel's own lock files), by name."""
    home = Path(home)
    if not home.is_dir():
        return []
    return sorted(p for p in home.glob("*.xlsx") if not p.name.startswith("~$"))


def keep_upload(home, name: str, data: bytes) -> Path:
    """A workbook chosen from elsewhere, copied into the household folder under its own name
    (the same bytes are not written twice; another file of that name is kept, the new one
    numbered)."""
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    target = home / Path(name).name
    k = 2
    while target.exists() and target.read_bytes() != data:
        target = home / f"{Path(name).stem} ({k}){Path(name).suffix}"
        k += 1
    if not target.exists():
        target.write_bytes(data)
    return target


def load_draft(library_root, today: Optional[date] = None) -> dict:
    """The answers typed so far (`setup-draft.json` in the library folder), else blank ones.
    A draft from another year or an unreadable one starts over."""
    import json

    blank = blank_answers(today)
    path = Path(library_root) / DRAFT_JSON
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return blank
    if not isinstance(saved, dict) or not isinstance(saved.get("people"), list):
        return blank
    answers = {**blank, **{k: v for k, v in saved.items() if k in blank}}
    answers["people"] = [{**copy.deepcopy(_PERSON), **(p if isinstance(p, dict) else {})}
                         for p in (list(saved["people"]) + blank["people"])[:2]]
    when = _date(answers.get("balance_date"))
    if when is None or when.year != (today or date.today()).year:
        answers["balance_date"] = blank["balance_date"]
    return answers


def save_draft(library_root, answers: dict) -> None:
    import json

    root = Path(library_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / DRAFT_JSON).write_text(json.dumps(answers, indent=1, sort_keys=True), encoding="utf-8")


def drop_draft(library_root) -> None:
    (Path(library_root) / DRAFT_JSON).unlink(missing_ok=True)


def write_starter(home, platform: Optional[str] = None) -> Optional[Path]:
    """A file in the household folder that starts the app on this folder with a double click
    ("Start Owl.cmd" on Windows, "Start Owl.command" on macOS, "start-owl.sh" elsewhere).

    Written once (an existing one is left alone) and only from a checkout (the launcher it
    calls, `owlplanner-library.cmd` / `.sh`, is at the repository's root). Returns its path,
    or None when there is no launcher to call.
    """
    import sys

    platform = platform or sys.platform
    repo = Path(__file__).resolve().parents[3]
    home = Path(home)
    if platform.startswith("win"):
        launcher, starter = repo / "owlplanner-library.cmd", home / "Start Owl.cmd"
        text = f'@echo off\r\ncall "{launcher}" "%~dp0."\r\n'
    else:
        launcher = repo / "owlplanner-library.sh"
        starter = home / ("Start Owl.command" if platform == "darwin" else "start-owl.sh")
        text = f'#!/bin/bash\nexec bash "{launcher}" "$(cd "$(dirname "$0")" && pwd)"\n'
    if not launcher.exists():
        return None
    if not starter.exists():
        home.mkdir(parents=True, exist_ok=True)
        starter.write_text(text, encoding="utf-8", newline="")
        if not platform.startswith("win"):
            starter.chmod(0o755)
    return starter

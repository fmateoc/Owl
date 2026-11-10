"""
Fork: saving the session's current case as a library run (run-library design section 7).

The Library page's *Save the current case* and the classic pages' background solve in library
mode (ergonomics review S-6) save the same way: the pages' tables synced into the plan, the
scenario built against the run the case was opened from (`sskeys.runBase`), a child of that
run when there is one.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import re
from datetime import date

import libraryjobs
import owlbridge as owb
import sskeys as kz
from owlplanner.library import newyear, scenario_from_ui

_BALANCES = ("taxable_savings_balances", "tax_deferred_savings_balances", "tax_free_savings_balances",
             "hsa_savings_balances")


def new_year_name(base_name, year):
    """"<base run> - <year>": a run started for a new plan year. A year the base's own name
    ends with is replaced, so the name stays put from one year to the next."""
    return f"{re.sub(r' - (19|20)[0-9]{2}$', '', str(base_name))} - {year}"


def default_name(base_name, case_name=None):
    """The save form's default run name: "<base run> variant" for a run's edited inputs (QW-8),
    `new_year_name` for a run started for a new plan year, else the case's own name."""
    year = kz.runNewYear()
    if base_name and year:
        return new_year_name(base_name, year)
    return f"{base_name} variant" if base_name else (case_name or "")


def _balances(scenario):
    assets = (scenario.get("case") or {}).get("savings_assets") or {}
    return [assets.get(key) for key in _BALANCES]


def save_current_case(lib, name, notes="", tags=()):
    """(save result, dropped values) for the current case, or None after flashing why not."""
    dic = kz.currentCaseDic()
    plan = dic.get("plan")
    base_run_id = kz.runBase()
    base = None
    if base_run_id:
        try:
            base = lib.scenario(base_run_id)
        except Exception:  # noqa: BLE001 - a deleted run is simply not the base any more
            base = None
    new_year = kz.runNewYear()
    stored = base
    try:
        if base is not None and new_year and base.get("plan_year") != new_year:
            # The case was opened from the base carried over to `new_year` ("Start <year> from
            # this run"): the pages' edits are applied to that document, whose plan year the
            # save keeps -- against the stored base it would keep the old year (review A1).
            base, _notes = newyear.start_year(base, new_year)
    except Exception as exc:  # noqa: BLE001 - shown, not raised
        libraryjobs.flash("error", f"Cannot save this case yet: {exc}")
        return None
    try:
        # The tables come from the plan (`scenario_from_ui`), not from the case keys: sync the
        # page-edited ones in first, or a table edited and not yet run or downloaded would be
        # missing from the run.
        if plan is not None and owb.syncContributions() is False:
            # Review Y4: the plan refused the pages' tables; saving now would store its previous
            # ones without a word (the rerun after the button clears the page's own error).
            libraryjobs.flash(
                "error",
                "Cannot save this case yet: the Wages and Contributions tables were not accepted. "
                "Fix them on the Financial Profile page.",
            )
            return None
        dropped = []
        scenario = scenario_from_ui(dic, plan, base=base, dropped=dropped)
        result = lib.save_run(name=name or kz.currentCaseName(), scenario=scenario,
                              parent=base_run_id, notes=notes,
                              tags=tuple(t for t in tags if str(t).strip()))
    except Exception as exc:  # noqa: BLE001 - an incomplete case is shown, not raised
        libraryjobs.flash("error", f"Cannot save this case yet: {exc}")
        return None
    saved_year = scenario.get("plan_year")
    this_year = date.today().year
    rolled = bool(new_year and stored is not None and stored.get("plan_year") != new_year)
    if rolled and _balances(scenario) == _balances(stored):
        # The reason a run has a plan year at all: last January's balances read as this one's.
        # The case stays marked as started for the new year, its steps on the pages: the next
        # save is again the run for that year, from the same parent.
        libraryjobs.flash(
            "warning",
            f"Saved for {new_year} with the account balances of {stored.get('plan_year')}: they were "
            f"not changed. Enter this year's on the Account Balances page and save again, or the "
            f"plan for {new_year} starts from last year's money.",
        )
    elif rolled:
        # The run for the new year exists: the case is its inputs from here on. Left marked, the
        # pages went on saying "Nothing is saved yet" above the list of steps, and every later
        # save made another "<name> - <year>" beside it from last year's run (review AQ5).
        run = result.run if result.created else result.identical_to
        if run is not None and run.plan_year == new_year:
            kz.setRunBase(run.id, run.name)
            kz.clearRunNewYear()
    elif saved_year is not None and saved_year != this_year:
        libraryjobs.flash(
            "warning",
            f"This run is for plan year {saved_year}, like the run it was edited from, and cannot "
            f"be solved in {this_year}. Use *Start {this_year} from this run* on its Run page.",
        )
    return result, dropped


def flash_dropped(dropped):
    if dropped:
        # Review W1: a value the run's events generate is regenerated from its event (section
        # 6.3, markers first), so an edit to one in the case pages does not survive the save.
        shown = "; ".join(dropped[:5]) + (f"; and {len(dropped) - 5} more" if len(dropped) > 5 else "")
        libraryjobs.flash(
            "warning",
            f"Not kept in this run: {shown}. These values are regenerated by the run's events — "
            "edit the event on the Scenario page instead.",
        )

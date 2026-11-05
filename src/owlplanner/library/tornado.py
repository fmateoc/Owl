"""Sensitivity "tornado" (run-library-design.md 14.1, I9; step 6's second increment).

One button on a run: one child run per key input moved by a set step, and their effects
sorted into bars, each with its tolerance (R2). The movers, as the design lists them plus
the two the user called for (2026-11-05):

- ``returns -1 point`` and ``inflation +1 point``: the run's own rate path, written out as
  a rates table with the shift in it (step 5b's `rates_table`; `builder.plan_rates_table`
  reads the path however the run names it, and a downturn overlay is baked into it);
- ``medical inflation +2 points``: `optimization_parameters.medical_inflation_excess`;
- ``condo price +10%``: the purchase event's price (today's $);
- ``benchmark premium +10%`` / ``-10%``: `aca_settings.slcsp_annual`, the marketplace's
  benchmark Silver plan;
- ``the 2027 marketplace rules``: `aca_settings.aca_table_year` = 2027, the 2027
  applicable-percentages table in every plan year (the knob's own sensitivity);
- ``the 2032 reversion`` and ``no 2032 reversion``: `rates_selection.obbba_expiration_year`
  at 2032 (as scheduled) and pushed out (the OBBBA provisions made permanent);
- ``<person> dies at 80``: the `death` event (I2), one bar per person.

A child is an ordinary run (`variants.Variant`, saved under the run and queued with its
collection); a mover that does not fit the scenario is skipped with its reason (no home
purchase, no benchmark premium, a death already past). The bars measure against the run's
newest **exact-LP** result when it has one (the children solve under the exact LP "for
speed"), else its newest result. Nothing here solves anything and nothing here changes the
model: every mover is a scenario edit.

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

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable, Optional

from . import builder, compare, grid, view
from .scenario import ScenarioError, validate
from .variants import Variant, _slug

# The steps (the design's I9 list; "the first death at 80" is DEATH_AGE below).
RETURNS_STEP = -1.0
INFLATION_STEP = 1.0
MEDICAL_STEP = 2.0
PRICE_STEP = 0.10
SLCSP_STEP = 0.10
MARKETPLACE_TABLE_YEAR = 2027
REVERSION_YEAR = 2032
NO_REVERSION_YEAR = 2100
DEATH_AGE = 80


@dataclass(frozen=True)
class Mover:
    """One key input moved by its set step."""

    key: str  # the collection member's values key ("returns-1")
    label: str  # "returns -1 point" (the bar's and the run name's label)
    note: str  # what moves, in plain terms (the page's caption)
    edit: Callable[[dict], None]  # the scenario edit; ScenarioError when it cannot apply


def _section(scenario: dict, name: str) -> dict:
    return scenario.setdefault("case", {}).setdefault(name, {})


def _shift_rates(scenario: dict, shifts: dict) -> None:
    """Move the run's rate path by `shifts` (percentage points per table column) and make
    the child a table run: the shifted path is its `rates_table`, so `owlcli run` reproduces
    it (step 5b). A downturn overlay is inside the rows already (they are the path as the
    plan uses it), so its event goes; so do `reverse_sequence` / `roll_sequence`, which the
    generated rows carry (builder AB1). A hand table keeps its case's transforms: shifting
    commutes with reversing and rolling."""
    generated = scenario.get("rates_table") is None
    table = builder.plan_rates_table(scenario)
    columns = list(table["columns"])
    rows = []
    for row in table["rows"]:
        moved = list(row)
        for i, column in enumerate(columns):
            if i and column in shifts:
                moved[i] = round(float(moved[i]) + float(shifts[column]), 4)
        rows.append(moved)
    scenario["rates_table"] = {"columns": columns, "rows": rows}
    scenario["events"] = [e for e in scenario.get("events") or []
                          if not (isinstance(e, dict) and e.get("kind") == "downturn")]
    selection = _section(scenario, "rates_selection")
    selection["method"] = "table"
    selection["rates_file"] = builder.RATES_CSV
    if generated:
        if selection.get("reverse_sequence"):
            selection["reverse_sequence"] = False
        if int(selection.get("roll_sequence") or 0) != 0:
            selection["roll_sequence"] = 0


def _returns_minus_1(scenario: dict) -> None:
    from owlplanner.rate_models.table import RATE_TABLE_COLUMNS

    returns = [c for c in RATE_TABLE_COLUMNS if c not in ("year", "Inflation")]
    _shift_rates(scenario, {c: RETURNS_STEP for c in returns})


def _inflation_plus_1(scenario: dict) -> None:
    _shift_rates(scenario, {"Inflation": INFLATION_STEP})


def _medical_plus_2(scenario: dict) -> None:
    params = _section(scenario, "optimization_parameters")
    current = float(params.get("medical_inflation_excess", 0.0) or 0.0)
    if current + MEDICAL_STEP > 10.0:  # the schema's cap (config.schema.OptimizationParameters)
        raise ScenarioError(
            f"medical inflation is already {current:g}% and the model caps it at 10%: "
            f"+{MEDICAL_STEP:g} does not fit")
    params["medical_inflation_excess"] = round(current + MEDICAL_STEP, 4)


def _condo_plus_10(scenario: dict) -> None:
    found = [e for e in (scenario.get("events") or [])
             if isinstance(e, dict) and e.get("kind") == "purchase"]
    if not found:
        raise ScenarioError("this run buys no home: there is no condo price to move")
    found[0]["price"] = round(float(found[0]["price"]) * (1.0 + PRICE_STEP), 2)


def _slcsp(factor: float) -> Callable[[dict], None]:
    def edit(scenario: dict) -> None:
        aca = _section(scenario, "aca_settings")
        current = float(aca.get("slcsp_annual", 0.0) or 0.0)
        if current <= 0:
            raise ScenarioError(
                "this case sets no benchmark Silver premium (aca_settings.slcsp_annual): "
                "the marketplace is not in the plan")
        aca["slcsp_annual"] = round(current * factor, 4)

    return edit


def _marketplace_rules(scenario: dict) -> None:
    aca = _section(scenario, "aca_settings")
    if float(aca.get("slcsp_annual", 0.0) or 0.0) <= 0:
        raise ScenarioError(
            "this case sets no benchmark Silver premium (aca_settings.slcsp_annual): "
            "the marketplace is not in the plan")
    if int(aca.get("aca_table_year", 0) or 0) == MARKETPLACE_TABLE_YEAR:
        raise ScenarioError(f"this case already pins the {MARKETPLACE_TABLE_YEAR} table")
    aca["aca_table_year"] = MARKETPLACE_TABLE_YEAR


def _obbba(year: int) -> Callable[[dict], None]:
    def edit(scenario: dict) -> None:
        selection = _section(scenario, "rates_selection")
        value = selection.get("obbba_expiration_year", REVERSION_YEAR)
        current = REVERSION_YEAR if value is None else int(value)
        if current == year:
            raise ScenarioError(f"this case already assumes it (obbba_expiration_year = {current})")
        selection["obbba_expiration_year"] = year

    return edit


def _death(person: str, scenario: dict) -> None:
    builder.check_death_age(person, DEATH_AGE, scenario.get("case") or {}, scenario,
                            where=f"{person!r} dies at {DEATH_AGE}")
    event = next((e for e in (scenario.get("events") or [])
                  if isinstance(e, dict) and e.get("kind") == "death" and e.get("person") == person),
                 None)
    if event is None:
        event = {"id": f"death-{person.lower()}", "kind": "death", "person": person}
        scenario.setdefault("events", []).append(event)
    event["age"] = DEATH_AGE


def movers(scenario: dict) -> list:
    """One `Mover` per key input moved by its set step, this run's own people included."""
    out = [
        Mover("returns-1", "returns -1 point",
              "every return of the run's own rate path, 1 point lower",
              _returns_minus_1),
        Mover("inflation+1", "inflation +1 point",
              "the rate path's inflation column, 1 point higher (prices and the deflator)",
              _inflation_plus_1),
        Mover("medical+2", "medical inflation +2 points",
              "medical_inflation_excess, 2 points higher",
              _medical_plus_2),
        Mover("condo+10", "condo price +10%",
              "the home purchase's price, 10% higher (today's $)",
              _condo_plus_10),
        Mover("slcsp+10", "benchmark premium +10%",
              "aca_settings.slcsp_annual, 10% higher (the marketplace's benchmark Silver plan)",
              _slcsp(1.0 + SLCSP_STEP)),
        Mover("slcsp-10", "benchmark premium -10%",
              "aca_settings.slcsp_annual, 10% lower",
              _slcsp(1.0 - SLCSP_STEP)),
        Mover("marketplace-2027", f"the {MARKETPLACE_TABLE_YEAR} marketplace rules",
              f"aca_settings.aca_table_year = {MARKETPLACE_TABLE_YEAR}: the "
              f"{MARKETPLACE_TABLE_YEAR} applicable percentages in every plan year",
              _marketplace_rules),
        Mover("reversion-2032", "the 2032 reversion",
              f"rates_selection.obbba_expiration_year = {REVERSION_YEAR} (as scheduled)",
              _obbba(REVERSION_YEAR)),
        Mover("no-reversion", "no 2032 reversion",
              f"rates_selection.obbba_expiration_year = {NO_REVERSION_YEAR} (made permanent)",
              _obbba(NO_REVERSION_YEAR)),
    ]
    names = list(((scenario.get("case") or {}).get("basic_info") or {}).get("names") or [])
    for person in names:
        out.append(Mover(
            f"death-{_slug(person)}", f"{person} dies at {DEATH_AGE}",
            f"the first death at {DEATH_AGE}: {person}'s life horizon ({person} only)",
            lambda scenario, person=person: _death(person, scenario)))
    return out


def tornado_variants(scenario: dict) -> tuple:
    """(variants, skipped): one `Variant` per mover that fits this scenario.

    Each child is a deep copy with the mover's edit applied and validated like any scenario
    (`validate`); `values` is {"mover": label}, what the collection member stores and the
    bars label themselves with. `skipped` names a mover that does not fit and why (no home
    purchase, no benchmark premium, a death already past, a case that already assumes the
    value). The input scenario is never edited.
    """
    made, skipped = [], []
    for mover in movers(scenario):
        child = copy.deepcopy(scenario)
        try:
            mover.edit(child)
        except ScenarioError as exc:
            skipped.append(f"{mover.label}: {exc}")
            continue
        validate(child)
        made.append(Variant(label=_slug(mover.label),
                            values={"mover": mover.label}, scenario=child))
    return made, skipped


def bars(parent_result, rows) -> list:
    """The tornado's bars: each mover's score against the parent's, judged (R2), sorted by
    the size of the effect (largest first; a bar with no solved result last).

    `rows` is [(label, result or None)] over the movers' runs. Each bar carries the
    difference's tolerance in dollars (`compare.pair_tolerance`) beside the verdict, so the
    chart can draw both ("bars sorted by effect, each with its tolerance").
    """
    base = view.score(parent_result) if parent_result is not None else None
    out = []
    for label, result in rows:
        got = view.score(result) if result is not None and result.solved else None
        if base is None or got is None:
            out.append({"label": label, "delta": None, "tolerance": None, "verdict": "-",
                        "note": "no solved result yet", "result": result})
            continue
        judgment = compare.difference("score", base, got, ta=parent_result, tb=result)
        tolerance, why = compare.pair_tolerance(parent_result, result, base)
        out.append({"label": label, "delta": judgment.delta, "tolerance": tolerance,
                    "verdict": judgment.verdict,
                    "note": judgment.note or (why if judgment.resolved else ""),
                    "result": result})
    out.sort(key=lambda row: (row["delta"] is None,
                              -abs(row["delta"]) if row["delta"] is not None else 0.0))
    return out


def result_of(run_path) -> Optional[view.Result]:
    """A run's own result for the tornado: its newest exact-LP one when it has one (the
    children solve under the exact LP, "for speed"), else its newest (R2)."""
    return grid.latest_result(run_path, prefer_exact=True) or grid.latest_result(run_path)

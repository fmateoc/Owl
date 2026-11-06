"""Sensitivity "tornado" (run-library-design.md 14.1, I9; step 6's second increment).

One button on a run: one child run per key input moved by a set step, and their effects
sorted into bars, each with its tolerance (R2). The movers, as the design lists them plus
the two the user called for (2026-11-05):

- ``returns -1 point`` and ``inflation +1 point``: the run's own rate path, written out as
  a rates table with the shift in it (step 5b's `rates_table`; `builder.plan_rates_table`
  reads the path however the run names it, and a downturn overlay is baked into it). The
  inflation mover raises every return column by the same point, so the real returns hold
  and the bar is inflation's own effect (indexing, basis, fixed nominal amounts), not a
  second copy of the returns bar (review AG3); the shift is in the table's own units
  (`in_percent`, review AG1);
- ``medical inflation +2 points``: `optimization_parameters.medical_inflation_excess`;
- ``condo price +10%``: the purchase event's price (today's $);
- ``benchmark premium +10%`` / ``-10%``: `aca_settings.slcsp_annual`, the marketplace's
  benchmark Silver plan;
- ``the <year> benchmark jump``: the published benchmark Silver premium of a later year
  (`aca_settings.slcsp_published_year` / `slcsp_published_annual`, the marketplace's
  approved rates -- for the household's region the 2027 benchmark is 21.4% over 2026 against
  the market's 6.0%, `fork-notes/aca-ny/README.md`). Owl grows `slcsp_annual` with (medical)
  inflation, so the jump above it is not in the plan; the mover sets `slcsp_annual` so that
  the plan's benchmark in that year is the published one, growing with (medical) inflation
  after it (the user's call, 2026-11-06: this bar replaces "the 2027 marketplace rules",
  which no plan year of the household could see -- review AG4);
- ``the 2032 reversion`` and ``no 2032 reversion``: `rates_selection.obbba_expiration_year`
  at 2032 (as scheduled) and pushed out (the OBBBA provisions made permanent); each is
  skipped when no plan year changes side of the expiration (review AG4: the template's
  2066 and 2100 are both past a plan that ends in 2053);
- ``<person> dies at 80``: the `death` event (I2), one bar per person.

A child is an ordinary run (`variants.Variant`, saved under the run and queued with its
collection; named after the mover's key, which keeps its sign: `slcsp+10`, `slcsp-10`,
review AG9); a mover that does not fit the scenario, or whose edit no plan year can see, is
skipped with its reason (no home purchase, no benchmark premium, a death already past, a
policy year outside the plan). The bars measure the children's **exact-LP** results against
the run's own exact-LP result and nothing else (review AG2: another model's result would
put the model change into every bar); without one, the bars wait for it. Nothing here
solves anything and nothing here changes the model: every mover is a scenario edit.

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
REVERSION_YEAR = 2032
NO_REVERSION_YEAR = 2100
DEATH_AGE = 80

# The run itself in its "Sensitivity" collection (the reference, review AG5): its `mover` value.
BASE_LABEL = "none (this run)"


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
    selection = _section(scenario, "rates_selection")
    # The shifts are percentage points. A hand table is stored as its file holds it and
    # `in_percent` says what the cells mean (review AA1): in decimals one point is 0.01, not
    # 1.0 (review AG1: -1.0 on a decimal table was -94% returns). A generated path is in
    # percent (`builder._generated_rates`).
    in_percent = generated or bool(selection.get("in_percent", True))
    scale, digits = (1.0, 4) if in_percent else (0.01, 6)
    table = builder.plan_rates_table(scenario)
    columns = list(table["columns"])
    rows = []
    for row in table["rows"]:
        moved = list(row)
        for i, column in enumerate(columns):
            if i and column in shifts:
                moved[i] = round(float(moved[i]) + scale * float(shifts[column]), digits)
        rows.append(moved)
    scenario["rates_table"] = {"columns": columns, "rows": rows}
    scenario["events"] = [e for e in scenario.get("events") or []
                          if not (isinstance(e, dict) and e.get("kind") == "downturn")]
    selection["method"] = "table"
    selection["rates_file"] = builder.RATES_CSV
    if generated:
        selection.pop("in_percent", None)  # the generated rows are in percent
        if selection.get("reverse_sequence"):
            selection["reverse_sequence"] = False
        if int(selection.get("roll_sequence") or 0) != 0:
            selection["roll_sequence"] = 0


def _return_columns() -> list:
    from owlplanner.rate_models.table import RATE_TABLE_COLUMNS

    return [c for c in RATE_TABLE_COLUMNS if c not in ("year", "Inflation")]


def _returns_minus_1(scenario: dict) -> None:
    _shift_rates(scenario, {c: RETURNS_STEP for c in _return_columns()})


def _inflation_plus_1(scenario: dict) -> None:
    """Inflation one point higher at the same real returns (review AG3): the return columns
    move with it. Held at the same *nominal* returns, the real returns of stocks and bonds
    fell by the point the returns mover already takes away, and the two bars measured nearly
    the same thing (-7,814 and -7,064 on the synthetic household)."""
    shifts = {c: INFLATION_STEP for c in _return_columns()}
    shifts["Inflation"] = INFLATION_STEP
    _shift_rates(scenario, shifts)


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


def _benchmark_growth(scenario: dict, year: int) -> float:
    """The factor the model grows `slcsp_annual` by from the plan's first year to `year`:
    the run's own inflation path compounded with `medical_inflation_excess` (`Plan._medical_n`,
    which `tax_federal.acaCosts` / `acaVals` multiply the benchmark by). The path is the one
    the solve uses: the run's rates table when it has one, else the case's own method."""
    case = scenario.get("case") or {}
    start = builder.plan_window(scenario)[0]
    table = builder.rates_table(scenario)
    gamma = builder._gamma(case, rates_rows=table["rows"] if table is not None else None)
    k = year - start
    if not 0 <= k < len(gamma):
        raise ScenarioError(f"{year} is outside the case's inflation path")
    excess = float((case.get("optimization_parameters") or {}).get("medical_inflation_excess", 0.0) or 0.0)
    return float(gamma[k]) * (1.0 + excess / 100.0) ** k


def _benchmark_jump(scenario: dict) -> None:
    aca = _section(scenario, "aca_settings")
    current = float(aca.get("slcsp_annual", 0.0) or 0.0)
    if current <= 0:
        raise ScenarioError(
            "this case sets no benchmark Silver premium (aca_settings.slcsp_annual): "
            "the marketplace is not in the plan")
    year, published = aca.get("slcsp_published_year"), aca.get("slcsp_published_annual")
    if not year or published is None:
        raise ScenarioError(
            "this case states no published benchmark (aca_settings.slcsp_published_year and "
            "slcsp_published_annual: a later year's approved benchmark, nominal $k)")
    year, published = int(year), float(published)
    start, end = builder.plan_window(scenario)
    if year < start or (end is not None and year > end):
        raise ScenarioError(f"the published benchmark's year {year} is outside the plan ({start}-{end})")
    first = max(start, int(aca.get("aca_start_year", 0) or 0) or start)
    if first < year:
        raise ScenarioError(
            f"the case's marketplace years start in {first}, before the published {year} "
            f"benchmark: scaling slcsp_annual would move {first} too")
    moved = round(published / _benchmark_growth(scenario, year), 4)
    if abs(moved - current) < 5e-4:
        raise ScenarioError(f"this case already prices the published {year} benchmark")
    aca["slcsp_annual"] = moved


def _obbba(year: int) -> Callable[[dict], None]:
    def edit(scenario: dict) -> None:
        selection = _section(scenario, "rates_selection")
        value = selection.get("obbba_expiration_year", REVERSION_YEAR)
        current = REVERSION_YEAR if value is None else int(value)
        if current == year:
            raise ScenarioError(f"this case already assumes it (obbba_expiration_year = {current})")
        # A plan year is under OBBBA when it is before the expiration year (`tax_federal.
        # taxParams`): the move reaches the plan only if some year changes side (review AG4).
        start, end = builder.plan_window(scenario)
        end = end if end is not None else start
        if not any((y < current) != (y < year) for y in range(start, end + 1)):
            raise ScenarioError(
                f"this case already assumes it: the plan ({start}-{end}) is the same under "
                f"obbba_expiration_year = {current} and {year}")
        selection["obbba_expiration_year"] = year

    return edit


def _death(person: str, scenario: dict) -> None:
    builder.check_death_age(person, DEATH_AGE, scenario.get("case") or {}, scenario,
                            where=f"{person!r} dies at {DEATH_AGE}")
    if _life_of(scenario, person) == DEATH_AGE:  # a child equal to its parent (review AG4)
        raise ScenarioError(f"this case already has {person} die at {DEATH_AGE}")
    builder.check_death_window(scenario, person, DEATH_AGE,
                               where=f"{person!r} dies at {DEATH_AGE}")
    event = next((e for e in (scenario.get("events") or [])
                  if isinstance(e, dict) and e.get("kind") == "death" and e.get("person") == person),
                 None)
    if event is None:
        event = {"id": f"death-{person.lower()}", "kind": "death", "person": person}
        scenario.setdefault("events", []).append(event)
    event["age"] = DEATH_AGE


def _life_of(scenario: dict, person: str):
    """The person's life horizon (age) as the scenario sets it: a death event, else the case."""
    for event in scenario.get("events") or []:
        if isinstance(event, dict) and event.get("kind") == "death" and event.get("person") == person:
            return int(event["age"])
    info = (scenario.get("case") or {}).get("basic_info") or {}
    names = list(info.get("names") or [])
    life = list(info.get("life_expectancy") or [])
    i = names.index(person) if person in names else None
    return int(life[i]) if i is not None and i < len(life) else None


def _benchmark_label(scenario: dict) -> str:
    year = ((scenario.get("case") or {}).get("aca_settings") or {}).get("slcsp_published_year")
    return f"the {int(year)} benchmark jump" if year else "the published benchmark"


def movers(scenario: dict) -> list:
    """One `Mover` per key input moved by its set step, this run's own people included."""
    out = [
        Mover("returns-1", "returns -1 point",
              "every return of the run's own rate path, 1 point lower",
              _returns_minus_1),
        Mover("inflation+1", "inflation +1 point",
              "the rate path's inflation, 1 point higher, with every return 1 point higher "
              "too (the same real returns: inflation's own effect)",
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
        Mover("slcsp-published", _benchmark_label(scenario),
              "aca_settings.slcsp_annual set so the plan's benchmark in the published year is "
              "the published one (slcsp_published_annual), growing with (medical) inflation "
              "after it",
              _benchmark_jump),
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
        # The child's name takes the mover's key, which keeps its sign ("slcsp+10" and
        # "slcsp-10" were both "benchmark-premium-10", review AG9).
        made.append(Variant(label=mover.key, values={"mover": mover.label}, scenario=child))
    return made, skipped


WAITING_FOR_BASE = "waiting for this run's own exact-LP solve"


def bars(parent_result, rows) -> list:
    """The tornado's bars: each mover's score against the parent's, judged (R2), sorted by
    the size of the effect (largest first; a bar with no result to judge last).

    `rows` is [(label, result or None)] over the movers' runs. Each bar carries the
    difference's tolerance in dollars (`compare.pair_tolerance`) beside the verdict, so the
    chart can draw both ("bars sorted by effect, each with its tolerance"). Both sides must
    be exact-LP results (review AG2): the children solve under the exact LP, and a parent
    result under another model put the model change -- +4,381 to +4,534 on the synthetic
    household, four times the noise band -- into every bar. Without the parent's own
    exact-LP result every bar waits (`WAITING_FOR_BASE`).
    """
    usable = parent_result is not None and parent_result.solved and view.is_exact_lp(parent_result)
    base = view.score(parent_result) if usable else None
    out = []
    for label, result in rows:
        exact = result is not None and result.solved and view.is_exact_lp(result)
        got = view.score(result) if exact else None
        if base is None or got is None:
            note = (WAITING_FOR_BASE if base is None
                    else "no exact-LP result yet" if result is None or not exact
                    else "no score")
            out.append({"label": label, "delta": None, "tolerance": None, "verdict": "-",
                        "note": note, "result": result})
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


def bar_flags(parent_result, rows) -> list:
    """The caveats the bars carry (S13's `compare.flags`, deduplicated) and the claiming
    ages they hold (review AG2: `decision_exact` fixes the ages, so a case that searches them
    solves every bar at its own hand ages, which the page must say). Empty without a base."""
    if parent_result is None or not parent_result.solved:
        return []
    out = []
    entries = []
    for label, result in rows:
        if result is not None and result.solved:
            out.extend(compare.flags(parent_result, result))
            entries.append(grid.Entry(run_id=label, name=label, values={}, result=result))
    ref = grid.Entry(run_id="(this run)", name="this run", values={}, result=parent_result)
    ages = grid.claiming_ages_flag(ref, [ref, *entries])
    if ages:
        out.append(ages)
    return list(dict.fromkeys(out))


def base_result(run_path) -> Optional[view.Result]:
    """The run's own exact-LP result, the only base the bars measure from (review AG2)."""
    return grid.latest_result(run_path, prefer_exact=True)


def result_of(run_path) -> Optional[view.Result]:
    """A mover run's result for the tornado: its newest exact-LP one (the children solve
    under the exact LP, "for speed"); None when it has none (review AG2: no other model's
    result enters a bar)."""
    return grid.latest_result(run_path, prefer_exact=True)

"""Comparing two results (run-library-design.md, section 9.2): the noise rule (R2), the two
numbers (R3), the flags (S13) and "what moved".

The judgment of one difference follows section 9.2 and CLAUDE.md's "Loop noise":

- a **proved** plan (branch-and-bound) reports a MIP gap, and is proven only to gap x
  objective: a difference counts when it is larger than *both* results' tolerances;
- a loop or local-search solve reports no gap: under 1% of the reference's value the
  difference is *unresolved* (grey, "~") -- the loop settling on a different fixed point can
  make it, with either sign -- and at or above 1% it counts (local search decides; the exact
  model is only an agreement check, never a tolerance);
- a difference of fifty cents or less is no difference at all (TIE_DOLLARS, run_suite.py's
  `|delta| > 0.5` guard on the "~" marker);
- a number no solve can move -- the home at the end, `fixed_assets_bequest_value` less the
  loan left, both set from the Debts and Fixed Assets tables before any solve
  (`Plan.processDebtsAndFixedAssets`) -- is judged by the fifty-cent rule alone: the loop
  noise and the MIP gap are properties of a solve, and applying them there let a real home
  difference read "within noise" and R3 call a trade-off a lead (step-3 review 3, W2).

A variant **leads** only when it is at least as good on both numbers -- the score and the
home at the end, never added together (R3); under maxBequest, whose score already holds the
home, the savings left and the home -- and better on one beyond the noise rule; otherwise
the verdict is "trade-off" (or "no difference"). Two results with different objectives are
not comparable.

When each run also has an exact-model companion (`view.is_exact_lp`), the pair gets the
agreement check (run_suite.agreement): the exact model is a *different model* (Medicare off,
SS taxability 0.85, LTCG exact), so only its differences compare. A disagreement in a plan
year with marketplace coverage goes to the local-search result, not to a tie (the exact LP
mis-prices the ACA trade).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .view import (
    NOISE_FRACTION,
    Result,
    error_bar,
    home_at_end,
    is_exact_lp,
    method_kind,
    savings_left,
    score,
    score_name,
    tolerance,
    total_taxes_today,
)

# Differences at or below this many dollars are no difference (run_suite: |delta| > 0.5).
TIE_DOLLARS = 0.5


@dataclass(frozen=True)
class Judgment:
    """One number, side by side, with the difference judged against the noise rule."""

    label: str
    a: Optional[float]
    b: Optional[float]
    delta: Optional[float]  # b - a
    verdict: str  # "resolved" | "within noise" | "no difference" | "-"
    note: str = ""

    @property
    def resolved(self) -> bool:
        return self.verdict == "resolved"


@dataclass(frozen=True)
class Comparison:
    """The comparison screen's content for two results (design 9.2)."""

    rows: tuple  # headline Judgments: score, home at the end, savings left, total taxes
    flags: tuple  # S13's comparison flags
    lead: dict  # {"verdict": ..., "note": ...} -- R3
    agreement: Optional[dict]  # the exact-model check, when both companions were found
    what_moved: tuple  # year-by-year differences (design 9.2's "What moved")
    what_moved_totals: tuple  # lifetime differences of the same items
    # The units of the rows ("today" | "nominal", the page's choice when both results carry
    # the deflator) and of the lifetime totals (today's dollars when both carry it: S-5).
    what_moved_units: str = "nominal"
    what_moved_totals_units: str = "nominal"


def pair_tolerance(a: Result, b: Result, reference: float) -> tuple:
    """(tolerance in dollars, why) for a difference measured against `reference` (R2)."""
    kinds = {method_kind(a), method_kind(b)}
    tol = max(tolerance(a), tolerance(b))
    reasons = []
    if "proved" in kinds:
        reasons.append("the reported gap x objective")
    if kinds - {"proved"}:
        tol = max(tol, NOISE_FRACTION * abs(reference))
        reasons.append("the 1% loop-noise band")
    return tol, " and ".join(reasons)


def difference(label: str, a: Optional[float], b: Optional[float], *, ta: Result, tb: Result,
               from_inputs: bool = False) -> Judgment:
    """Judge b - a for one number, against the pair's noise tolerance.

    `reference` is a's value (the first result is the reference, as `run_suite.group_table`
    reads "vs base"). `from_inputs` marks a number the inputs fix before any solve (the home
    at the end): no solve noise applies to it, only the fifty-cent rule (review 3, W2).
    """
    if a is None or b is None:
        return Judgment(label, a, b, None, "-")
    delta = b - a
    if abs(delta) <= TIE_DOLLARS:
        return Judgment(label, a, b, delta, "no difference")
    if from_inputs:
        return Judgment(label, a, b, delta, "resolved",
                        "set by the inputs (no solve moves it): no noise band applies")
    tol, why = pair_tolerance(ta, tb, a)
    if abs(delta) <= tol:
        kind = "within noise"
        if "gap" in why:
            note = f"within {why}"
        else:
            note = f"~ {why}: the loop can make it, with either sign"
        return Judgment(label, a, b, delta, kind, note)
    return Judgment(label, a, b, delta, "resolved")


# -- flags (S13) -------------------------------------------------------


def flags(a: Result, b: Result) -> tuple:
    """Comparisons that need a caveat: different days, presets or Owl commits (S13)."""
    out = []
    recs = (a.record, b.record)

    def _finished(rec):
        return (rec.get("solve_date") or {}).get("finished") or ""

    day_a, day_b = _finished(recs[0])[:10], _finished(recs[1])[:10]
    if day_a and day_b and day_a != day_b:
        out.append(
            f"solved on different days ({day_a} vs {day_b}): plans start today, so the "
            "difference includes the day -- run both again before deciding"
        )
    objectives = [objective_of(a), objective_of(b)]
    if objectives[0] != objectives[1]:
        out.append(f"solved with different objectives ({objectives[0]} vs {objectives[1]}): "
                   "one maximizes spending, the other the bequest, so their headline "
                   "numbers are not the same quantity")
    presets = [str(rec.get("preset") or "?") for rec in recs]
    if presets[0] != presets[1]:
        out.append(f"solved with different presets ({presets[0]} vs {presets[1]})")
    commits = [str((rec.get("engine") or {}).get("commit") or "?") for rec in recs]
    if commits[0] != commits[1]:
        out.append(f"solved under different Owl commits ({commits[0]} vs {commits[1]})")
    return tuple(out)


# -- the two numbers (R3) ---------------------------------------------


def _lead_one(judgment: Judgment) -> str:
    """"b better" / "a better" / "even" for one number (higher is better)."""
    if judgment.resolved:
        return "b better" if (judgment.delta or 0.0) > 0 else "a better"
    return "even"


def objective_of(result: Result) -> str:
    """The result's objective ("maxSpending" / "maxBequest"), from plan.json or the record."""
    return str(result.plan.get("objective")
               or (result.record.get("method") or {}).get("objective") or "")


def lead_verdict(rows, objective: str = "maxSpending") -> dict:
    """R3: a variant leads only when it is at least as good on both and better on one.

    The two numbers are the score and the home at the end under maxSpending. Under
    maxBequest the score *is* the final bequest, which already holds the home, so judging it
    beside the home counted the home twice: more home and less savings read as a lead on
    both (step-3 review 3, W5). There the two numbers are the savings left and the home.
    """
    by_label = {r.label: r for r in rows}
    spending = objective == "maxSpending"
    # The score row comes first and carries the score's own words (QW-5, `view.score_name`).
    first = (rows[0] if rows else None) if spending else by_label.get("savings left at the end")
    pair = (first, by_label.get("home at the end"))
    if any(r is None or r.delta is None for r in pair):
        return {"verdict": "not comparable", "note": "one of the two results has no numbers"}
    stances = [_lead_one(r) for r in pair]
    both = (f"the {first.label} and the home at the end" if spending
            else "the savings left and the home at the end")
    if stances == ["even", "even"]:
        return {"verdict": "no difference beyond the noise rule", "note": ""}
    if "b better" in stances and "a better" not in stances:
        return {"verdict": "the second result leads", "note": f"at least as good on {both}, better on one"}
    if "a better" in stances and "b better" not in stances:
        return {"verdict": "the first result leads", "note": f"at least as good on {both}, better on one"}
    return {
        "verdict": "trade-off",
        "note": (("one buys more spending, the other keeps more home at the end" if spending
                  else "one leaves more savings, the other more home at the end")
                 + "; the two numbers are never added together"),  # R3
    }


# -- the agreement check (run_suite.agreement, R2) ---------------------


def _has_aca_years(result: Result) -> bool:
    return any(abs(int(row.get("aca_premiums") or 0)) > 0 for row in result.plan.get("by_year") or [])


def agreement(a: Result, b: Result, a_exact: Result, b_exact: Result) -> dict:
    """The pair as selected and under the exact model: does it order them the same?

    A difference counts when both models give it the same sign and it is larger than their
    spread plus the four runs' error bars (a loop that did not settle).
    """
    d_pair = (score(b) or 0.0) - (score(a) or 0.0)
    d_ex = (score(b_exact) or 0.0) - (score(a_exact) or 0.0)
    spread = abs(d_pair - d_ex)
    bars = error_bar(a) + error_bar(b) + error_bar(a_exact) + error_bar(b_exact)
    aca = _has_aca_years(a) or _has_aca_years(b)
    if (d_pair > 0) != (d_ex > 0):
        verdict = "unresolved: the two models disagree on the sign"
    elif min(abs(d_pair), abs(d_ex)) <= spread + bars:
        verdict = "unresolved: smaller than the spread" + (" and error bars" if bars > 0.5 else "")
    else:
        verdict = "resolved: the second result is " + ("ahead of" if d_pair > 0 else "behind") + " the first"
    note = ""
    if aca and not verdict.startswith("resolved"):
        # Design 9.2: "a disagreement there goes to the local-search result, not to a tie".
        # So the reading defers to the pair's own numbers (the table above) instead of
        # leaving "unresolved" on the screen next to a note that denies the tie (review P7).
        verdict = ("not settled by the exact model: the pair's own difference decides "
                   f"({d_pair:+,.0f} today's $)")
        note = ("Plan years with marketplace coverage: the exact model mis-prices the ACA "
                "trade, so a disagreement goes to the local-search result, not to a tie.")  # design 9.2
    return {
        "delta_pair": d_pair,
        "delta_exact": d_ex,
        "spread": spread,
        "error_bars": bars,
        "verdict": verdict,
        "note": note,
    }


# -- "what moved" (design 9.2) ----------------------------------------

# The year-by-year items whose differences explain a verdict (plan.json's by_year; SS income
# is summed over the individuals). Label order is the table's.
WHAT_MOVED = (
    ("taxes", "Taxes (income, gains, NIIT, payroll, state)"),
    ("medicare_premiums", "Medicare premiums (IRMAA)"),
    ("aca_premiums", "ACA premiums"),
    ("roth_conversions", "Roth conversions"),
    ("portfolio_withdrawals", "Withdrawals from savings"),
    ("ss_income", "SS income (claiming)"),
    ("spending", "Spending"),
)


def has_deflator(result: Result) -> bool:
    """Whether every by_year row of the result carries its deflator (plan.json since S-4)."""
    rows = result.plan.get("by_year") or []
    return bool(rows) and all(isinstance(r.get("deflator"), (int, float)) and r["deflator"] > 0 for r in rows)


def _by_year_sums(result: Result, units: str = "nominal") -> dict:
    """{year: {item: total}} for the WHAT_MOVED items, nominal or in today's dollars (each
    year's amounts divided by that year's own deflator: S-5)."""
    today = units == "today"
    out = {}
    for row in result.plan.get("by_year") or []:
        try:
            year = int(row.get("year"))
        except (TypeError, ValueError):
            continue
        sums = {
            "taxes": sum(int(row.get(k) or 0) for k in
                         ("federal_income_tax", "ltcg_tax", "niit", "payroll_tax", "state_tax")),
            "medicare_premiums": int(row.get("medicare_premiums") or 0),
            "aca_premiums": int(row.get("aca_premiums") or 0),
            "roth_conversions": int(row.get("roth_conversions") or 0),
            "portfolio_withdrawals": int(row.get("portfolio_withdrawals") or 0),
            "ss_income": sum(int(v or 0) for v in (row.get("ss_income") or [])),
            "spending": int(row.get("spending") or 0),
        }
        if today:
            sums = {k: v / float(row["deflator"]) for k, v in sums.items()}
        out[year] = sums
    return out


def what_moved_units(a: Result, b: Result, units: str = "nominal") -> tuple:
    """(rows' units, totals' units): the rows in `units` when both results carry the deflator,
    else nominal; the lifetime totals in today's dollars whenever both carry it (S-5)."""
    both = has_deflator(a) and has_deflator(b)
    return ("today" if units == "today" and both else "nominal"), ("today" if both else "nominal")


def what_moved(a: Result, b: Result, units: str = "nominal") -> tuple:
    """Year-by-year differences (b - a): the rows the comparison shows, in `units`.

    The two plans are matched by calendar year, not by position (step-3 review 3, W6: two
    results of different plan years compared A's 2027 with B's 2028 under the label 2027); a
    year only one plan has counts the other's items as 0. A row is included when any item
    moved by more than a dollar in any year; the items with no movement anywhere are left out
    of the table's columns.

    The lifetime totals are sums over years, so they are in today's dollars whenever both
    results carry the deflator (S-5: a sum of nominal dollars of different years mixes
    dollars of different worth, and two plans with different inflation paths then differ
    in the sum where they spend the same). Units: `what_moved_units`.
    """
    row_units, total_units = what_moved_units(a, b, units)

    def _deltas(units_):
        sa, sb = _by_year_sums(a, units_), _by_year_sums(b, units_)
        years = sorted(set(sa) | set(sb))

        def _delta(key, year):
            return (sb.get(year) or {}).get(key, 0) - (sa.get(year) or {}).get(key, 0)

        return years, _delta

    years, delta = _deltas(row_units)
    moving = [key for key, _ in WHAT_MOVED
              if any(abs(delta(key, year)) > 1 for year in years)]
    rows = []
    for year in years:
        changes = {key: round(delta(key, year)) for key in moving}
        if any(changes.values()):
            rows.append({"year": year, "changes": changes})
    t_years, t_delta = _deltas(total_units)
    totals = tuple(
        (label, round(sum(t_delta(key, year) for year in t_years)))
        for key, label in WHAT_MOVED if key in moving
    )
    columns = tuple((key, label) for key, label in WHAT_MOVED if key in moving)
    return tuple(rows), totals, columns


# -- the verdict in words (S-5) ---------------------------------------


def _money(value) -> str:
    return f"\\${abs(value):,.0f}"


def where_it_shows_up(totals, limit: int = 3) -> list:
    """The largest lifetime lines of "what moved" (label, B - A), largest first: where a
    difference shows up, not what caused it (S-5, decision 8)."""
    lines = [(label, value) for label, value in totals if abs(value) >= 1]
    return sorted(lines, key=lambda lv: -abs(lv[1]))[:limit]


def verdict_sentence(comparison: Comparison, name_a: str, name_b: str, score_words: str,
                     objective: str = "maxSpending") -> str:
    """The lead verdict (R3) as one sentence naming the runs and the amounts (S-5).

    The amounts are the rows' differences in today's dollars: the first number per year under
    maxSpending, the savings left under maxBequest, and the home at the end. "Too close to
    call" names the noise rule that makes it so."""
    rows = comparison.rows
    spending = objective == "maxSpending"
    first = rows[0] if spending else next((r for r in rows if r.label == "savings left at the end"), None)
    home = next((r for r in rows if r.label == "home at the end"), None)
    verdict = comparison.lead.get("verdict")
    note = comparison.lead.get("note") or ""
    if verdict == "not comparable":
        return f"Not comparable: {note or 'one result has no numbers'}."

    def _first_words(r, more=True):
        word = "more" if more else "less"
        if spending:
            return f"{_money(r.delta)}/yr {word} {score_words}"
        return f"{_money(r.delta)} {word} savings left at the end"

    if verdict in ("the second result leads", "the first result leads"):
        winner, sign = (name_b, 1) if verdict == "the second result leads" else (name_a, -1)
        better = [r for r in (first, home) if r is not None and r.resolved and sign * (r.delta or 0) > 0]
        parts = [(_first_words(r) if r is first else f"{_money(r.delta)} more home at the end") for r in better]
        if len(better) == 1:
            parts.append("as much home at the end or more" if home not in better
                         else (f"as much {score_words} or more" if spending else "as much savings or more"))
        return f"*{winner}* comes out ahead: {' and '.join(parts)}."
    if verdict == "trade-off":
        if first is None or home is None:
            return "A trade-off."
        more_first = name_b if (first.delta or 0) > 0 else name_a
        more_home = name_b if (home.delta or 0) > 0 else name_a
        what = f"spends {_money(first.delta)}/yr more" if spending else f"leaves {_money(first.delta)} more savings"
        return (f"A trade-off: *{more_first}* {what}, *{more_home}* keeps {_money(home.delta)} more home at "
                "the end (the two are never added together).")
    # No difference beyond the noise rule.
    if first is not None and first.verdict == "within noise":
        why = "the solver's proved gap" if "gap" in (first.note or "") else "1% of the plan"
        amount = f"{_money(first.delta)}/yr" if spending else _money(first.delta)
        return f"Too close to call: {amount}, within this method's noise ({why})."
    return "No difference."


# -- the whole screen --------------------------------------------------


def compare(a: Result, b: Result, *, a_exact: Optional[Result] = None,
            b_exact: Optional[Result] = None, units: str = "nominal") -> Comparison:
    """The comparison screen's content for two results (design 9.2); "what moved" in `units`
    where both results allow it (`what_moved_units`)."""
    rows = (
        difference(score_name(a), score(a), score(b), ta=a, tb=b),
        difference("home at the end", home_at_end(a), home_at_end(b), ta=a, tb=b,
                   from_inputs=True),
        difference("savings left at the end", savings_left(a), savings_left(b), ta=a, tb=b),
        difference("total taxes (lifetime)", total_taxes_today(a), total_taxes_today(b), ta=a, tb=b),
    )
    objectives = (objective_of(a), objective_of(b))
    if objectives[0] != objectives[1]:
        lead = {"verdict": "not comparable",
                "note": f"different objectives ({objectives[0]} vs {objectives[1]}): the two "
                        "headline numbers measure different things"}
    else:
        lead = lead_verdict(rows, objectives[0])
    moved_rows, moved_totals, _columns = what_moved(a, b, units)
    row_units, total_units = what_moved_units(a, b, units)
    agree = None
    if a_exact is not None and b_exact is not None and a_exact.solved and b_exact.solved:
        # Four distinct results (review P4): a result is never its own companion, and one
        # exact solve cannot stand in for both runs (the exact difference would be zero and
        # read as a sign disagreement).
        if len({a.results_id, b.results_id, a_exact.results_id, b_exact.results_id}) == 4:
            agree = agreement(a, b, a_exact, b_exact)
    return Comparison(
        rows=rows,
        flags=flags(a, b),
        lead=lead,
        agreement=agree,
        what_moved=moved_rows,
        what_moved_totals=moved_totals,
        what_moved_units=row_units,
        what_moved_totals_units=total_units,
    )


def exact_companion(results, exclude=(), near=None) -> Optional[Result]:
    """The exact-model result among a run's results, if any (`view.is_exact_lp`).

    `exclude` holds the results already selected on the comparison screen: the companion of
    a pair is one of its *other* solves, and never the pair's own other side either
    (step-3 review P4). Of the candidates the newest solve wins (the results folder's stamp
    names its time), preferring one solved on the same day as `near` (the pair's own solve):
    a companion from another day confounds the check (S13).
    """

    def _day(result):
        return str((result.record.get("solve_date") or {}).get("finished") or "")[:10]

    cands = [r for r in results if r.results_id not in exclude and r.solved and is_exact_lp(r)]
    cands.sort(key=lambda r: r.results_id, reverse=True)
    if near is not None:
        cands.sort(key=lambda r: 0 if _day(r) == _day(near) else 1)  # stable: newest first
    return cands[0] if cands else None


# -- the Compare page's default pair (UX review Q4) -------------------


def default_pair(entries) -> tuple:
    """The indices (a, b) the Compare page selects first.

    `entries` holds one tuple per result, in the page's order: (run id, parent run id,
    finish time in seconds or None, main) -- `main` true for a solved headline result (not a
    model companion, R2). B is the newest main result; A is the newest main result of B's
    parent run, else the newest main result of another run, never B itself. With fewer than
    two main results, the first two entries. With a pinned baseline (S-1) and no parent result,
    A is the baseline's newest main result (`entries` may carry a fifth item, true for the
    baseline's results).
    """
    mains = [i for i, e in enumerate(entries) if e[3]]
    if len(mains) < 2:
        return 0, min(1, len(entries) - 1)

    def newest(indices):
        # The newest finish; the page order (newest run first) breaks ties and missing times.
        return max(indices, key=lambda i: (entries[i][2] if entries[i][2] is not None else float("-inf"), -i))

    b = newest(mains)
    run_b, parent_b = entries[b][0], entries[b][1]
    of_parent = [i for i in mains if parent_b is not None and entries[i][0] == parent_b]
    others = [i for i in mains if entries[i][0] != run_b]
    of_baseline = [i for i in others if len(entries[i]) > 4 and entries[i][4]]
    a = newest(of_parent or of_baseline or others or [i for i in mains if i != b])
    return a, b

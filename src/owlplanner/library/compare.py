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


def _pair_tolerance(a: Result, b: Result, reference: float) -> tuple:
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
    tol, why = _pair_tolerance(ta, tb, a)
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
                   "the scores are not the same quantity")
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
    first = "score" if spending else "savings left at the end"
    pair = (by_label.get(first), by_label.get("home at the end"))
    if any(r is None or r.delta is None for r in pair):
        return {"verdict": "not comparable", "note": "one of the two results has no numbers"}
    stances = [_lead_one(r) for r in pair]
    both = ("the score and the home at the end" if spending
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
                 + "; the two numbers are never added (R3)"),
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
                "trade, so a disagreement goes to the local-search result, not to a tie "
                "(design 9.2).")
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


def _by_year_sums(result: Result) -> dict:
    """{year: {item: nominal total}} for the WHAT_MOVED items."""
    out = {}
    for row in result.plan.get("by_year") or []:
        try:
            year = int(row.get("year"))
        except (TypeError, ValueError):
            continue
        out[year] = {
            "taxes": sum(int(row.get(k) or 0) for k in
                         ("federal_income_tax", "ltcg_tax", "niit", "payroll_tax", "state_tax")),
            "medicare_premiums": int(row.get("medicare_premiums") or 0),
            "aca_premiums": int(row.get("aca_premiums") or 0),
            "roth_conversions": int(row.get("roth_conversions") or 0),
            "portfolio_withdrawals": int(row.get("portfolio_withdrawals") or 0),
            "ss_income": sum(int(v or 0) for v in (row.get("ss_income") or [])),
            "spending": int(row.get("spending") or 0),
        }
    return out


def what_moved(a: Result, b: Result) -> tuple:
    """Year-by-year differences (b - a), nominal $: the rows the comparison shows.

    The two plans are matched by calendar year, not by position (step-3 review 3, W6: two
    results of different plan years compared A's 2027 with B's 2028 under the label 2027); a
    year only one plan has counts the other's items as 0. A row is included when any item
    moved by more than a dollar in any year; the items with no movement anywhere are left out
    of the table's columns.
    """
    sa, sb = _by_year_sums(a), _by_year_sums(b)
    years = sorted(set(sa) | set(sb))

    def _delta(key, year):
        return (sb.get(year) or {}).get(key, 0) - (sa.get(year) or {}).get(key, 0)

    moving = [key for key, _ in WHAT_MOVED
              if any(abs(_delta(key, year)) > 1 for year in years)]
    rows = []
    for year in years:
        changes = {key: _delta(key, year) for key in moving}
        if any(changes.values()):
            rows.append({"year": year, "changes": changes})
    totals = tuple(
        (label, sum(_delta(key, year) for year in years))
        for key, label in WHAT_MOVED if key in moving
    )
    columns = tuple((key, label) for key, label in WHAT_MOVED if key in moving)
    return tuple(rows), totals, columns


# -- the whole screen --------------------------------------------------


def compare(a: Result, b: Result, *, a_exact: Optional[Result] = None,
            b_exact: Optional[Result] = None) -> Comparison:
    """The comparison screen's content for two results (design 9.2)."""
    rows = (
        difference("score", score(a), score(b), ta=a, tb=b),
        difference("home at the end", home_at_end(a), home_at_end(b), ta=a, tb=b,
                   from_inputs=True),
        difference("savings left at the end", savings_left(a), savings_left(b), ta=a, tb=b),
        difference("total taxes (lifetime)", total_taxes_today(a), total_taxes_today(b), ta=a, tb=b),
    )
    objectives = (objective_of(a), objective_of(b))
    if objectives[0] != objectives[1]:
        lead = {"verdict": "not comparable",
                "note": f"different objectives ({objectives[0]} vs {objectives[1]}): the two "
                        "scores measure different things"}
    else:
        lead = lead_verdict(rows, objectives[0])
    moved_rows, moved_totals, _columns = what_moved(a, b)
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

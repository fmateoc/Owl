"""Comparing two results (run-library-design.md, section 9.2): the noise rule (R2), the two
numbers (R3), the flags (S13) and "what moved".

The judgment of one difference follows section 9.2 and CLAUDE.md's "Loop noise":

- a **proved** plan (branch-and-bound) reports a MIP gap, and is proven only to gap x
  objective: a difference counts when it is larger than *both* results' tolerances;
- a loop or local-search solve reports no gap: under 1% of the reference's score the
  difference is *unresolved* (grey, "~") -- the loop settling on a different fixed point can
  make it, with either sign -- and at or above 1% it counts (local search decides; the exact
  model is only an agreement check, never a tolerance);
- a difference of a dollar or less is no difference at all (run_suite.py's `|delta| > 0.5`
  guard on the "~" marker).

A variant **leads** only when it is at least as good on both numbers -- the score and the
home at the end, never added together (R3) -- and better on one beyond the noise rule;
otherwise the verdict is "trade-off" (or "no difference").

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


def difference(label: str, a: Optional[float], b: Optional[float], *, ta: Result, tb: Result) -> Judgment:
    """Judge b - a for one number, against the pair's noise tolerance.

    `reference` is a's value (the first result is the reference, as `run_suite.group_table`
    reads "vs base").
    """
    if a is None or b is None:
        return Judgment(label, a, b, None, "-")
    delta = b - a
    if abs(delta) <= TIE_DOLLARS:
        return Judgment(label, a, b, delta, "no difference")
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


def lead_verdict(rows) -> dict:
    """R3: a variant leads only when it is at least as good on both and better on one."""
    by_label = {r.label: r for r in rows}
    pair = (by_label.get("score"), by_label.get("home at the end"))
    if any(r is None or r.delta is None for r in pair):
        return {"verdict": "not comparable", "note": "one of the two results has no numbers"}
    stances = [_lead_one(r) for r in pair]
    if stances == ["even", "even"]:
        return {"verdict": "no difference beyond the noise rule", "note": ""}
    if "b better" in stances and "a better" not in stances:
        return {"verdict": "the second result leads", "note": "at least as good on both numbers, better on one"}
    if "a better" in stances and "b better" not in stances:
        return {"verdict": "the first result leads", "note": "at least as good on both numbers, better on one"}
    return {
        "verdict": "trade-off",
        "note": "one buys more spending, the other keeps more home at the end; the two numbers "
                "are never added (R3)",
    }


# -- the agreement check (run_suite.agreement, R2) ---------------------


def _has_aca_years(result: Result) -> bool:
    return any(abs(int(row.get("aca_premiums") or 0)) > 0 for row in result.plan.get("by_year") or [])


def agreement(a: Result, b: Result, a_exact: Result, b_exact: Result) -> dict:
    """The same pair under local search and under the exact model: does it order them the same?

    A difference counts when both models give it the same sign and it is larger than their
    spread plus the four runs' error bars (a loop that did not settle).
    """
    d_ls = (score(b) or 0.0) - (score(a) or 0.0)
    d_ex = (score(b_exact) or 0.0) - (score(a_exact) or 0.0)
    spread = abs(d_ls - d_ex)
    bars = error_bar(a) + error_bar(b) + error_bar(a_exact) + error_bar(b_exact)
    aca = _has_aca_years(a) or _has_aca_years(b)
    if (d_ls > 0) != (d_ex > 0):
        verdict = "unresolved: the two models disagree on the sign"
    elif min(abs(d_ls), abs(d_ex)) <= spread + bars:
        verdict = "unresolved: smaller than the spread" + (" and error bars" if bars > 0.5 else "")
    else:
        verdict = "resolved: the second result is " + ("ahead of" if d_ls > 0 else "behind") + " the first"
    note = ""
    if aca and not verdict.startswith("resolved"):
        note = ("plan years with marketplace coverage: the exact model mis-prices the ACA trade, "
                "so this disagreement goes to the local-search result, not to a tie")
    return {
        "delta_local_search": d_ls,
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
    """{item: [per-year nominal totals]} for the WHAT_MOVED items."""
    out = {key: [] for key, _ in WHAT_MOVED}
    for row in result.plan.get("by_year") or []:
        taxes = sum(int(row.get(k) or 0) for k in
                    ("federal_income_tax", "ltcg_tax", "niit", "payroll_tax", "state_tax"))
        out["taxes"].append(taxes)
        out["medicare_premiums"].append(int(row.get("medicare_premiums") or 0))
        out["aca_premiums"].append(int(row.get("aca_premiums") or 0))
        out["roth_conversions"].append(int(row.get("roth_conversions") or 0))
        out["portfolio_withdrawals"].append(int(row.get("portfolio_withdrawals") or 0))
        out["ss_income"].append(sum(int(v or 0) for v in (row.get("ss_income") or [])))
        out["spending"].append(int(row.get("spending") or 0))
    return out


def what_moved(a: Result, b: Result) -> tuple:
    """Year-by-year differences (b - a), nominal $: the rows the comparison shows.

    A row is included when any item moved by more than a dollar in any year; the items with
    no movement anywhere are left out of the table's columns.
    """
    years = [int(row.get("year") or 0) for row in b.plan.get("by_year") or a.plan.get("by_year") or []]
    sa, sb = _by_year_sums(a), _by_year_sums(b)

    def _delta(key, i):
        return _at(sb[key], i) - _at(sa[key], i)

    moving = [key for key, _ in WHAT_MOVED
              if any(abs(_delta(key, i)) > 1 for i in range(len(years)))]
    rows = []
    for i, year in enumerate(years):
        changes = {key: _delta(key, i) for key in moving}
        if any(changes.values()):
            rows.append({"year": year, "changes": changes})
    totals = tuple(
        (label, sum(_delta(key, i) for i in range(len(years))))
        for key, label in WHAT_MOVED if key in moving
    )
    columns = tuple((key, label) for key, label in WHAT_MOVED if key in moving)
    return tuple(rows), totals, columns


def _at(values, i):
    return values[i] if i < len(values) else 0


# -- the whole screen --------------------------------------------------


def compare(a: Result, b: Result, *, a_exact: Optional[Result] = None,
            b_exact: Optional[Result] = None) -> Comparison:
    """The comparison screen's content for two results (design 9.2)."""
    rows = (
        difference("score", score(a), score(b), ta=a, tb=b),
        difference("home at the end", home_at_end(a), home_at_end(b), ta=a, tb=b),
        difference("savings left at the end", savings_left(a), savings_left(b), ta=a, tb=b),
        difference("total taxes (lifetime)", total_taxes_today(a), total_taxes_today(b), ta=a, tb=b),
    )
    moved_rows, moved_totals, _columns = what_moved(a, b)
    agree = None
    if a_exact is not None and b_exact is not None and a_exact.solved and b_exact.solved:
        if a_exact is not a and b_exact is not b:
            agree = agreement(a, b, a_exact, b_exact)
    return Comparison(
        rows=rows,
        flags=flags(a, b),
        lead=lead_verdict(rows),
        agreement=agree,
        what_moved=moved_rows,
        what_moved_totals=moved_totals,
    )


def exact_companion(results) -> Optional[Result]:
    """The exact-model result among a run's results, if any (`view.is_exact_lp`)."""
    for result in results:
        if result.solved and is_exact_lp(result):
            return result
    return None

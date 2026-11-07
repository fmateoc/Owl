"""One result as the library pages show it (run-library-design.md, section 9.1).

A results folder holds the durable artifacts of one solve: `record.json` (how it was
obtained), `summary.json` (`export.plan_metrics`), `plan.json`
(`cli.formatters.plan_to_dict`, the per-year arrays) and the workbook. Everything the run
page and the comparison show is derived from those files alone, so a result whose
`plan.pkl` cache has been dropped reads exactly the same (D7: charts from `plan.json`,
Owl's own plots through "Open in Owl").

The scoring rule is `fork-notes/synthetic/run_suite.py`'s (its docstring): with essential
budget lines under maxSpending the score is the first year's discretionary spending
(`discretionary_year1`, k x D_0); without them, the spending basis; under maxBequest, the
final bequest. Beside it, what is left at the end in today's dollars is reported as two
numbers that are never added (R3): *savings* (after the heirs' tax) and the *home* at the
end (the final bequest minus the savings part: the home net of commission and of any loan
still owed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import results as R

# The loop noise band (CLAUDE.md, "Loop noise"; design 9.2, R2): under the self-consistent
# loop and under local search a difference below 1% of the reference can come from the loop
# settling on a different fixed point, and can have the wrong sign.
NOISE_FRACTION = 0.01


@dataclass(frozen=True)
class Result:
    """One solve's durable artifacts. Each file may be missing (a solve that never got there)."""

    results_id: str
    results_dir: Path
    record: dict
    summary: dict
    plan: dict

    @property
    def solved(self) -> bool:
        """A result with numbers: the record says solved and both durable files are there.

        A reader can see a record beside an empty summary/plan (a hand-deleted file, or the
        moment `JobRecord.publish` renames the artifacts one by one): that is not $0 of
        everything (step-3 review P3), it is "no numbers" -- the derivations return None and
        the quality line says which file is missing.
        """
        return self.record.get("status") == "solved" and bool(self.plan) and bool(self.summary)


def load_result(results_dir) -> Result:
    """Read record.json, summary.json and plan.json of one results folder (missing files: empty)."""
    results_dir = Path(results_dir)

    def _read(name):
        path = results_dir / name
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            return doc if isinstance(doc, dict) else {}
        except (OSError, ValueError):
            return {}

    return Result(
        results_id=results_dir.name,
        results_dir=results_dir,
        record=_read(R.RECORD_JSON) or {},
        summary=_read(R.SUMMARY_JSON),
        plan=_read(R.PLAN_JSON),
    )


# -- headline numbers (design 9.1) -------------------------------------


def score(result: Result) -> Optional[float]:
    """The number two variants are compared on (run_suite.score), or None when unsolved."""
    if not result.solved:
        return None
    m = result.summary
    if result.plan.get("objective") != "maxSpending":
        return float(m.get("final_bequest_today", 0.0))
    if "discretionary_year1" in m:
        return float(m["discretionary_year1"])
    return float(m.get("spending_basis", 0.0))


def score_label(result: Result) -> str:
    """What the score is, in words (run_suite.score_label)."""
    if result.plan.get("objective") != "maxSpending":
        return r"final bequest (today's \$)"
    if "discretionary_year1" in result.summary:
        return r"first year's discretionary spending (\$/yr, today's)"
    return r"spending basis (\$/yr, today's)"


def score_name(result: Result) -> str:
    """The score in a few words (QW-5, decision 3: the pages say what the number is, never
    "score"): "discretionary spending" with essential budget lines, "spending" without, the
    "final bequest" under maxBequest."""
    if result is not None and result.plan.get("objective") != "maxSpending":
        return "final bequest"
    if result is not None and "discretionary_year1" in result.summary:
        return "discretionary spending"
    return "spending"


def first_number(result: Result) -> Optional[float]:
    """R3's first number, what a variant's difference is read on beside the home at the end:
    the score under maxSpending; under maxBequest the savings left, since the score there is
    the final bequest, which holds the home (step-3 review 3, W5, for the lead rule; review
    AJ3 for the tornado's bars, the grid's cells and star and the front: "condo price +10%"
    read -97,822 = -173,908 savings + 76,086 home, with the home shown again beside it).
    None when unsolved."""
    if result is None or not result.solved:
        return None
    if result.plan.get("objective") != "maxSpending":
        return savings_left(result)
    return score(result)


def first_number_name(result: Result) -> str:
    """`first_number`'s name, as `compare`'s rows name it (`score_name` under maxSpending,
    "savings left at the end" under maxBequest)."""
    if result is not None and result.plan.get("objective") != "maxSpending":
        return "savings left at the end"
    return score_name(result)


def first_number_label(result: Result) -> str:
    """`first_number` in words, for a page's caption or axis."""
    if result is not None and result.plan.get("objective") != "maxSpending":
        return r"savings left at the end (today's \$, after the heirs' tax)"
    return score_label(result) if result is not None else "spending"


def savings_left(result: Result) -> Optional[float]:
    """Savings left at the end, today's $, after the heirs' tax (run_suite: "savings left")."""
    if not result.solved:
        return None
    return float(result.summary.get("final_bequest_savings_today", 0.0))


def home_at_end(result: Result) -> Optional[float]:
    """The home at the end (net of commission and of any loan left): the bequest's home part.

    `final_bequest_today` is the estate (home plus savings) less the heirs' tax, which is
    charged on the savings part (`final_bequest_savings_today`); the difference is the home
    (run_suite's `home_at_end_today`).
    """
    if not result.solved:
        return None
    return float(result.summary.get("final_bequest_today", 0.0)) - float(
        result.summary.get("final_bequest_savings_today", 0.0)
    )


def total_taxes_today(result: Result) -> Optional[float]:
    """Every lifetime tax the model charges, today's $ (income, gains, NIIT, payroll, state)."""
    if not result.solved:
        return None
    m = result.summary
    return float(sum(m.get(k, 0.0) for k in (
        "federal_income_tax_today", "ltcg_tax_today", "niit_today",
        "payroll_tax_today", "state_tax_today",
    )))


def ss_withheld_today(result: Result) -> Optional[float]:
    """SS withheld by the earnings test over the plan, today's $."""
    if not result.solved:
        return None
    return float(result.summary.get("ss_withheld_today", 0.0))


def claiming_ages(result: Result) -> list:
    """[(name, age in years)] as the solve used them (66y2m = 66.1667; plan.json)."""
    names = list(result.plan.get("individuals") or [])
    ages = list(result.plan.get("claiming_ages") or [])
    return list(zip(names, ages, strict=False))


def age_text(age: float) -> str:
    """66.1667 -> "66y2m" (run_suite.ym)."""
    months = int(round(float(age) * 12))
    return f"{months // 12}y{months % 12}m"


def claiming_ages_text(result: Result) -> str:
    return ", ".join(f"{name} {age_text(age)}" for name, age in claiming_ages(result))


def claiming_ages_how(result: Result, case_ss_ages=None) -> str:
    """How the solve got its claiming ages, in words (UX review Q7): "chosen by Owl" when an
    Ages preset searched them (`record.json` `age_search`); "held" when the solve fixed them
    (`withSSAges = "fixed"` in its options) while the run's case asks Owl to search them
    (`case_ss_ages`, the case's own `withSSAges`); "" otherwise (the case fixes them itself)."""
    record = result.record or {}
    if record.get("age_search"):
        return "chosen by Owl"
    solved = str(((record.get("method") or {}).get("options") or {}).get("withSSAges", "")).lower()
    asked = case_ss_ages if isinstance(case_ss_ages, list) else str(case_ss_ages or "fixed").lower()
    if solved == "fixed" and asked not in ("fixed", "", []):
        return "held"
    return ""


def claiming_ages_phrase(result: Result, case_ss_ages=None) -> str:
    """`claiming_ages_text` with how they were set: "Ari 67y0m, Noa 67y0m (held at these:
    this solve does not search them)" or "(chosen by Owl)"."""
    text = claiming_ages_text(result)
    how = claiming_ages_how(result, case_ss_ages)
    if not text or not how:
        return text
    if how == "held":
        return f"{text} (held at these: this solve does not search them)"
    return f"{text} ({how})"


def spent_down_by_design(result: Result, case_bequest=None) -> bool:
    """Savings left at zero on purpose (UX review Q7): a maxSpending plan whose bequest
    target (the case's `solver_options.bequest`, 0 when absent) is zero spends the savings
    by the end; a zero then is the goal, not a shortfall."""
    left = savings_left(result) if result is not None else None
    if left is None or result.plan.get("objective") != "maxSpending":
        return False
    try:
        target = float(case_bequest or 0.0)
    except (TypeError, ValueError):
        return False
    return target == 0.0 and abs(left) < 0.5


# -- "Things to look at" (I3) and the one-year cash flow (I6) ------------
# Both blocks are written into plan.json at solve time (`thresholds.threshold_proximity`,
# `export.cash_flow_split` via `plan_to_dict`), so a result reads the same without plan.pkl.


def thresholds(result: Result) -> list:
    """"Things to look at" (design 14.1, I3): plan.json's `thresholds` entries (today's $)."""
    return list((result.plan.get("thresholds") or {}).get("entries") or [])


def threshold_groups_marked(result: Result) -> bool:
    """Whether the report names its groups (QW-2): False for a result solved before crossings
    were reported, whose list holds near lines only (or the build's partial crossings)."""
    return bool((result.plan.get("thresholds") or {}).get("groups"))


def threshold_band(result: Result) -> float:
    """The proximity band the report used (a fraction of each boundary; 0.05 when absent)."""
    band = (result.plan.get("thresholds") or {}).get("near_band_fraction")
    try:
        return float(band) if band is not None else 0.05
    except (TypeError, ValueError):
        return 0.05


def cash_flow(result: Result) -> dict:
    """One year's sources and uses, per year (design 14.1, I6): plan.json's `cash_flow` block.

    {"sources": {name: [per year]}, "uses": {name: [per year]}}, nominal $ of each year;
    the two sides are equal in every year (the cash flow identity).
    """
    return result.plan.get("cash_flow") or {}


# A flow under this many dollars is not drawn (each row is rounded to whole dollars).
FLOW_DOLLARS = 0.5


def cash_flow_year(result: Result, n: int) -> tuple:
    """Year n's sources and uses as the Sankey draws them: ({name: $}, {name: $}), all positive.

    `cash_flow` holds signed rows: a negative use is money coming in (NY's refundable STAR
    credit makes "State and local tax" negative once it exceeds the tax, `st_T_n`), and a
    negative source is money going out (a negative `other inc`, #225). Dropping them broke
    the balance the chart claims -- in 23 of the synthetic baseline's 28 years the drawn uses
    exceeded the sources by up to $3,492 (step-3 review 3, W1). Each one moves to the other
    side under its own name ("..., net refund" / "..., net outflow"), so the two sides stay
    equal to the dollar of rounding; flows of fifty cents or less are left out on both sides.
    """
    cf = cash_flow(result)
    sources, uses = {}, {}

    def _value(values):
        try:
            return float(values[n]) if n < len(values) else 0.0
        except (TypeError, ValueError):
            return 0.0

    for name, values in (cf.get("sources") or {}).items():
        v = _value(values)
        if v > FLOW_DOLLARS:
            sources[name] = v
        elif v < -FLOW_DOLLARS:
            uses[f"{name}, net outflow"] = -v
    for name, values in (cf.get("uses") or {}).items():
        v = _value(values)
        if v > FLOW_DOLLARS:
            uses[name] = v
        elif v < -FLOW_DOLLARS:
            sources[f"{name}, net refund"] = -v
    return sources, uses


# -- how good is this result (design 9.1's quality line, run_suite.run_checks) ------


def error_bar(result: Result) -> float:
    """Half the objective's oscillation band (today's $) on an unsettled loop; 0 when settled."""
    conv = result.record.get("convergence") or {}
    bar = conv.get("objective_error_bar_today_dollars", 0.0)
    try:
        return max(0.0, float(bar or 0.0))
    except (TypeError, ValueError):
        return 0.0


def quality_notes(result: Result) -> list:
    """Problems with one result, whatever the scenario (run_suite.run_checks)."""
    if not result.solved:
        status = result.record.get("status") or "no record"
        if status == "solved":
            missing = [name for name, doc in (("summary.json", result.summary),
                                              ("plan.json", result.plan)) if not doc]
            return [f"the solve's files are incomplete ({', '.join(missing)} missing): "
                    "no numbers to show"]
        note = result.record.get("error") or result.plan.get("status") or ""
        return [f"not solved: {status}" + (f" ({note})" if note else "")]
    issues = []
    conv = result.record.get("convergence") or {}
    if conv.get("convergence") in ("max iteration", "unsolvable iterate", "undefined"):
        issues.append(f"the loop stopped early ({conv['convergence']})")
    if error_bar(result) > 0.5:
        issues.append(
            f"the loop did not settle (objective error bar \u00b1{error_bar(result):,.0f}); "
            "differences under 1% are not meaningful"
        )
    for w in result.record.get("warnings") or []:
        if "Cash flow balance" in w or "infeasible" in w.lower() or "maximum iterations" in w:
            issues.append(w)
    return issues


def quality_line(result: Result) -> str:
    """One plain-language line: "settled", or what did not settle (design 9.1)."""
    notes = quality_notes(result)
    return notes[0] if notes else "settled"


# -- method and the noise tolerance (design 9.2, R2, S13) -------------

def method_text(result: Result) -> str:
    """"How the solve was made", in plain English (UX remediation QW-6): the preset as people
    know it (`presets.PRESET_NAMES`, the one list) and what the method promises, no more --
    "Careful — taxes and premiums priced exactly, the plan found by a local search". Review
    AN8: "exact ... optimization" claimed more for a local search than the comparison grants
    it (its 1% band). The raw codes (the preset id, the binary families, "branch-and-bound at
    gap 1e-5", the version and commit) are `method_details`, shown in a collapsed expander."""
    from .presets import preset_name

    rec = result.record
    method = rec.get("method") or {}
    raw = str(method.get("breakpoint_method") or "loop")
    preset = str(rec.get("preset") or "?")
    head = preset_name(preset)
    companion = record_companion(rec)
    if companion == "decision_exact":  # by its options, whatever preset it was recorded under
        return (f"{preset_name(companion)} (a simpler model solved beside the Careful one, to "
                "check the order of the variants)")
    if companion == "exact_medicare":
        return preset_name(companion)  # review AM4: its name says it all
    kind = method_kind(result)
    if kind == "no solve":
        return head
    if kind == "loop":
        tail = ("the fast approximate method" if "-> loop" not in raw
                else "the fast approximate method (the local search found nothing better)")
    else:
        what = "taxes and premiums" if ("IRMAA" in raw or "Medicare" in raw) else "taxes"
        tail = (f"{what} priced exactly, proved optimal within its gap" if kind == "proved"
                else f"{what} priced exactly, the plan found by a local search")
    return f"{head} — {tail}"


def method_details(result: Result) -> str:
    """The solve's technical details, markdown for a collapsed expander (QW-6): the raw
    preset id and breakpoint method (with the binary families), the branch-and-bound gap,
    the engine's version and commit, and what an exact-model companion is."""
    rec = result.record
    method = rec.get("method") or {}
    engine = rec.get("engine") or {}
    lines = [f"- Preset (its code): `{rec.get('preset') or '?'}`",
             f"- Breakpoint method (the binary families): `{method.get('breakpoint_method') or 'loop'}`"]
    try:
        gap = float(rec.get("gap"))
    except (TypeError, ValueError):
        gap = None
    if gap is not None and gap >= 0:
        lines.append(f"- Proved by branch-and-bound at gap {gap:g} (the plan is proven only "
                     "to gap x objective)")
    version = str(engine.get("version") or "")
    commit = str(engine.get("commit") or "")
    if version or commit:
        lines.append(f"- Engine: Owl {version}" + (f" (`{commit}`)" if commit else ""))
    if method.get("options"):
        lines.append(f"- Solver options: `{method['options']}`")
    companion = record_companion(rec)
    if companion == "decision_exact":
        lines.append("- Solved under the exact LP (a check on the headline solve: Medicare "
                     "off, the Social Security taxable fraction pinned at 0.85, capital gains "
                     "priced exactly)")
    elif companion == "exact_medicare":
        lines.append("- Solved under the exact LP with Medicare premiums priced exactly "
                     "(the sensitivity's medical-inflation model)")
    return "\n".join(lines)


def method_kind(result: Result) -> str:
    """"proved" (branch-and-bound), "local search", "loop", or "no solve".

    "local search -> loop" (the search kept the loop's plan) is not proved: nothing was
    proven about the plan the loop left.
    """
    if not result.solved:
        return "no solve"
    method = (result.record.get("method") or {}).get("breakpoint_method") or "loop"
    text = str(method).lower()
    if "branch-and-bound" in text:
        return "proved"
    if "local search" in text and "-> loop" not in text:
        return "local search"
    return "loop"


def is_exact_lp(result: Result) -> bool:
    """Is this the exact-model companion of a "decision" solve (run_suite's EXACT_GROUP)?

    The comparison's agreement check reads it (R2): "does the exact model order the two the
    same way?". The model is the loop with Medicare off, the SS taxable fraction pinned at
    0.85 and capital gains priced exactly.
    """
    return record_is_exact_lp(result.record)


def record_is_exact_lp(record: dict) -> bool:
    """`is_exact_lp` on a record.json alone (the pages pick a default result with it)."""
    options = (record.get("method") or {}).get("options") or {}

    def _norm(value):
        return str(value).strip().lower()

    try:
        ss_taxable = float(options.get("withSSTaxability"))
    except (TypeError, ValueError):
        return False
    return (
        _norm(options.get("breakpointMethod")) == "loop"
        and _norm(options.get("withMedicare")) == "none"
        and abs(ss_taxable - 0.85) < 1e-9
        and _norm(options.get("withLTCG")) == "optimize"
    )


def record_companion(record: dict) -> Optional[str]:
    """Which model companion a record.json is: "exact_medicare" (by its solve preset: the
    exact model with Medicare priced exactly, the tornado's medical-inflation mover and its
    base, review AJ1), "decision_exact" (the exact LP, by its options, `record_is_exact_lp`),
    or None -- a solve under the case's own model, which the pages may show as the run's
    headline.

    The pages pick a run's default result, and the collections their headline result, among
    the records this says None for: a companion's model is not the case's (no Medicare, or
    the SS taxable fraction pinned at 0.85), so it is read beside the headline, never as it.
    """
    if str(record.get("preset") or "") == "exact_medicare":
        return "exact_medicare"
    if record_is_exact_lp(record):
        return "decision_exact"
    return None


def is_companion(result: Result) -> bool:
    """Is this a model companion's result (`record_companion`), not a headline one?"""
    return record_companion(result.record) is not None


def objective_value(result: Result) -> Optional[float]:
    """The value the solver's reported gap is relative to (R2's "gap x objective"), today's $.

    maxSpending: the LP maximizes the (discounted) real spending of every year, which scales
    with the first year's (`g_n[0]`, `spending_year1`; exactly so without essential lines,
    approximately with them), so a relative gap bounds `spending_year1` by the same fraction.
    maxBequest: the LP maximizes the accounts left at the end after the heirs' tax
    (`Plan._build_objective_vector`: taxable and Roth at 1, tax-deferred and HSA at 1 - nu),
    which is `final_bequest_savings_today` -- not the final bequest, which adds the home and
    subtracts any loan, neither of which the solve moves (step-3 review 2, Q8: the docstring
    said `Plan._objectiveValue`, whose maxBequest value is `max(0, accounts - debt)`, and the
    code used the final bequest).

    Not the *score*: under essential lines the score is only the discretionary part of the
    objective (step-3 review P9: essential 400k + discretionary 50k would understate the
    tolerance 9x).
    """
    if not result.solved:
        return None
    m = result.summary
    if (result.plan.get("objective") or (result.record.get("method") or {}).get("objective")) == "maxSpending":
        value = m.get("spending_year1")
    else:
        value = m.get("final_bequest_savings_today", m.get("final_bequest_today"))
    return None if value is None else float(value)


def tolerance(result: Result) -> float:
    """How far a difference must move before this result calls it real (R2), today's $.

    A proved plan (branch-and-bound) reports a MIP gap, and the plan is proven only to gap x
    objective: that is its tolerance (read the *reported* gap, CLAUDE.md's "Loop noise"
    bullet, its "Branch-and-bound gap" paragraph). A loop or local-search solve reports no
    gap: its tolerance is the loop-noise band, 1% of the reference's value (the caller
    applies the fraction to the pair's reference). Here the fractional case returns 0, and
    the caller adds `NOISE_FRACTION * |reference|`.
    """
    if method_kind(result) != "proved":
        return 0.0
    gap = result.record.get("gap")
    try:
        gap = float(gap)
    except (TypeError, ValueError):
        return 0.0
    if gap < 0:
        return 0.0
    value = objective_value(result)
    if value is None:
        value = score(result) or 0.0
    return gap * abs(value)

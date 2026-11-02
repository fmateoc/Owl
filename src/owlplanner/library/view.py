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
        return self.record.get("status") == "solved" and bool(self.plan)


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
    """"preset · breakpoint method · Owl version+commit" for the run page's header."""
    rec = result.record
    method = rec.get("method") or {}
    parts = [str(rec.get("preset") or "?"), str(method.get("breakpoint_method") or "loop")]
    engine = rec.get("engine") or {}
    version = str(engine.get("version") or "")
    commit = str(engine.get("commit") or "")
    if version:
        parts.append(f"Owl {version}" + (f" ({commit})" if commit else ""))
    return " \u00b7 ".join(parts)


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
    options = (result.record.get("method") or {}).get("options") or {}

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


def tolerance(result: Result) -> float:
    """How far a difference must move before this result calls it real (R2), today's $.

    A proved plan (branch-and-bound) reports a MIP gap, and the plan is proven only to gap x
    objective: that is its tolerance (read the *reported* gap, CLAUDE.md, "Branch-and-bound
    gap"). A loop or local-search solve reports no gap: its tolerance is the loop-noise band,
    1% of the reference's score (the caller applies the fraction to the pair's reference).
    Here the fractional case returns 0, and the caller adds `NOISE_FRACTION * |reference|`.
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
    value = score(result) or 0.0
    return gap * abs(value)

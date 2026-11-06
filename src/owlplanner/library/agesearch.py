"""The "Ages" preset's two-stage claiming-age search (design section 8.1; run_suite.py's).

When the scenario says "let Owl choose" (``withSSAges`` not ``fixed``), solving on the full
model makes every candidate age a branch-and-bound MIP: on the synthetic case with
brokerage-heavy balances one search ran past 20 minutes (2026-10-29). So the search runs in
two stages, as `fork-notes/synthetic/run_suite.py` runs it:

- **Stage 1** is the case's own ``withSSAges`` search under the **exact LP** (the loop with
  Medicare off and the SS taxable fraction pinned at 0.85 -- `EXACT_MODEL`): a pure LP per
  candidate (about 0.5 s on the synthetic case). ACA stays on the loop, unlike
  `owlplanner.work_sweep`'s stage (a): ``withACA = "optimize"`` makes each
  candidate a MIP (9 s there, about 10 minutes for the search's ~270 candidates), and the
  exact LP mis-prices the ACA years even then (`plan-review-2026-10-22.md` 3.2).
- **Stage 2** solves the pick and each searched person's pick +-1 year (clipped to 62-70
  and to the person's first open claiming age, review AJ4; one person at a time) at **fixed
  ages** under **the case's own model**, scoring each with `score_plan` (run_suite's score
  rule, the library's `view.score` over a plan). The best score wins.

The search is one implementation, shared by the suite and the interface (the fork's rule,
run-library-design.md section 6.2): `run_suite.py` imports it, and the worker runs it for
the ``ages`` preset before the final solve at the chosen ages.

``check`` (optional) is called between steps and may raise to stop the search (the worker's
cancellation hook, S8); ``log`` is a stream for the stages' own solve logs (their warnings
are not part of the record).
"""

from __future__ import annotations

import copy
import io
import json
from typing import Any, Callable, Optional

# The exact model of the stage-1 search and of "decision"'s exact companion (run_suite.py's
# EXACT / EXACT_GROUP; `presets._FORCED["decision_exact"]` and `run_suite.EXACT_GROUP` read
# these): the loop with Medicare off, the SS taxable fraction pinned at 0.85, and (the
# group's model only) capital gains priced exactly. The exact groups (run_suite's
# condo-exact, rates-exact) price capital gains exactly for a measured reason: with a large
# brokerage account the LTCG loop did not settle in 138 of 153 unsettled rates-exact runs
# (error bars up to +-12,856, median +-2,782; synthetic run 2026-10-29-d), and
# withLTCG="optimize" settled the four probed (error bar 0) at 11-15 s per run instead of
# 0.5-1 s. Stage 1 of the age search keeps the pure LP (a candidate solve must stay fast).
EXACT_MODEL = {"breakpointMethod": "loop", "withMedicare": "none", "withSSTaxability": 0.85}
EXACT_GROUP = {**EXACT_MODEL, "withLTCG": "optimize"}


def set_strings(options: dict) -> list:
    """A solver-option dict as `owlcli --set` specs (run_suite's `EXACT` list).

    Strings stay bare (`breakpointMethod=loop`): `set_override._parse_value` keeps a bare
    word as-is, and every option value here is a word that is not a JSON literal.
    """
    return [f"solver_options.{key}={value if isinstance(value, str) else json.dumps(value)}"
            for key, value in options.items()]


EXACT_SETS = set_strings(EXACT_MODEL)
EXACT_GROUP_SETS = set_strings(EXACT_GROUP)


def fixed_ages(ages) -> list:
    """Pin the claiming ages (`owlcli --set` specs, run_suite's `fixed_ages`)."""
    return ["solver_options.withSSAges=fixed",
            f"fixed_income.social_security_ages={json.dumps([float(a) for a in ages])}"]


def score_plan(plan) -> float:
    """The number an age candidate is scored on (run_suite's `_score_plan`, its docstring).

    With essential budget lines under maxSpending the score is the first year's discretionary
    spending (k x D_0); without them, the spending basis; under maxBequest, the final bequest.
    """
    from owlplanner.export import plan_metrics

    m = plan_metrics(plan)
    if plan.objective != "maxSpending":
        return m["final_bequest_today"]
    k = m.get("discretionary_scale")
    return k * float(plan.budget.discretionary_n[0]) if k is not None else m["spending_basis"]


def _plan(diconf, dirname, log, sets=()):
    from owlplanner.config import config_to_plan

    d = _overrides(diconf, list(sets)) if sets else copy.deepcopy(diconf)
    return config_to_plan(d, dirname, verbose=True, logstreams=[log], loadHFP=True)


def _overrides(diconf, sets):
    from owlplanner.cli.set_override import apply_overrides

    return apply_overrides(diconf, sets)


def _solve(plan, options=None):
    from owlplanner.config.schema import parse_solver_options

    opts = parse_solver_options(dict(plan.solverOptions) if options is None else options)
    plan.solve(plan.objective, opts)
    return plan


def searched_names(option, names) -> list:
    """The people a ``withSSAges`` value searches (plan._parseSSAgesOption's reading)."""
    if isinstance(option, str):
        if option.strip().lower() == "optimize":
            return list(names)
        return [n for n in names if n == option]
    if isinstance(option, (list, tuple)):
        return [n for n in names if n in option]
    return []


def _trials(pick, free, first=None) -> list:
    """The age tuples stage 2 scores: the pick, then each searched person's pick +-1 year.

    Each neighbour is clipped to 62-70 and, when `first` is given (each person's first open
    claiming age, `Plan._ssaOpenAges`: eligibility or this month, whichever is later), to
    that age from below (review AJ4): a fixed age already past is solved without a word as
    benefits already being collected, so stage 2 could score -- and pick -- a month that can
    no longer be claimed (Ari, 62y7m on 2026-11-06, was tried at 62y0m).
    """
    trials = [list(pick)]
    for i in free:
        low = 62.0 if first is None else max(62.0, float(first[i]))
        for d in (-1.0, 1.0):
            a = min(70.0, max(low, pick[i] + d))  # clipped: a 69y10m pick still tries 70
            if abs(a - pick[i]) > 1e-6:
                t = list(pick)
                t[i] = a
                trials.append(t)
    return trials


def two_stage_ages(diconf, dirname, log=None, *, check: Optional[Callable[[], Any]] = None):
    """Claiming ages for a case that searches them (run_suite's `two_stage_ages`).

    Returns ``(ages, candidates)`` with ``candidates = [(ages, score or None)]``. ``ages`` is
    the best-scoring candidate's (the stage-1 pick when its neighbours do not beat it).
    Raises RuntimeError when a stage does not solve.
    """
    log = log if log is not None else io.StringIO()
    if check is not None:
        check()
    p = _solve(_plan(diconf, dirname, log, EXACT_SETS))
    if p.caseStatus != "solved":
        raise RuntimeError(f"stage 1 (exact LP age search) did not solve: {p.caseStatus}")
    pick = [float(a) for a in p.ssecAges]
    sel = diconf.get("solver_options", {}).get("withSSAges", "optimize")
    names = list(p.inames)
    free = [names.index(n) for n in searched_names(sel, names)]
    # Each person's first open claiming age (review AJ4); 70 for someone with none left.
    first = [(p._ssaOpenAges(i) or [70.0])[0] for i in range(len(names))]
    scored = []
    for t in _trials(pick, free, first):
        if check is not None:
            check()
        q = _solve(_plan(diconf, dirname, log, fixed_ages(t)))
        scored.append(([round(float(a), 4) for a in q.ssecAges],
                       score_plan(q) if q.caseStatus == "solved" else None))
    good = [c for c in scored if c[1] is not None]
    if not good:
        raise RuntimeError("stage 2: no candidate ages solved")
    return max(good, key=lambda c: c[1])[0], scored

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
the ``ages`` preset and publishes the winning candidate's own plan (``keep``).

``check`` (optional) is called between steps and may raise to stop the search (the worker's
cancellation hook, S8); ``log`` is a stream for the stages' own solve logs (their warnings
are not part of the record).

``effort`` (optional) is local search's effort for stage 2, where the case's own model is
local search (`search_effort`; the library passes `presets.LOCAL_SEARCH_EFFORT`): stage 2
picks by the raw score, so a candidate whose search a wall-clock cap cut short can lose to
its neighbour by a dollar (performance review, 2026-11-11).

``overrides`` (optional) are options given for the one job (the worker's job record), put
over the case's own in every stage-2 solve, as the worker's published solve puts them
(`candidate_options`).

``pool`` (optional) scores stage 2's candidates side by side: an object with
``map(fn, items) -> list`` whose `fn` runs in another process (`score_trial`, the worker's
pool on the cores the queue gave the job). The candidates are independent solves, so the
scores are the serial ones; each candidate's log reaches ``log`` when it ends.

``keep`` (optional) returns the winning candidate's solved plan with the ages and scores
(`Winner`; performance review P4a, 2026-11-11). The worker used to build the plan again at
the chosen ages and solve it with the same options: one of the four to six solves of the
search, done twice. A plan solved on the pool comes back pickled (a solved Plan pickles, its
logger without its streams: `Logger.__getstate__`, the plan cache's route); the others are
dropped where they were solved.
"""

from __future__ import annotations

import copy
import io
import json
import pickle
from typing import Any, Callable, NamedTuple, Optional

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


def is_local_search(options) -> bool:
    """True when these solver options solve by local search (the option is normalized)."""
    return str((options or {}).get("breakpointMethod", "")).strip().lower() == "local-search"


class Winner(NamedTuple):
    """The winning stage-2 candidate, kept (``two_stage_ages(keep=True)``, P4a)."""

    plan: Any  # the solved Plan, logging to the search's `log` stream
    log: str  # its own solve log, as the search wrote it to `log` among the others
    options: dict  # the solver options it was solved with (`candidate_options`)


def search_effort(options, effort) -> dict:
    """`options` with local search's effort settings filled in, where it is the method.

    The settings the options already state are kept (the Ages presets force nothing, R4):
    `effort` supplies only what is missing, in place of upstream's defaults. Options that do
    not solve by local search come back as they are.
    """
    options = dict(options or {})
    if effort and is_local_search(options):
        for key, value in effort.items():
            options.setdefault(key, value)
    return options


def candidate_options(case_options, overrides=None, effort=None) -> dict:
    """The options a stage-2 candidate solves with: the case's own (the candidate plan's, its
    ages fixed), the job's `overrides` on top, then local search's `effort` where it is the
    method (`search_effort`).

    `presets.resolve_options` reads this for the ``ages`` preset, so the candidate stage 2
    picks is solved exactly as the plan the worker publishes, which is that candidate's own
    plan (P4a).
    """
    return search_effort({**dict(case_options or {}), **dict(overrides or {})}, effort)


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


def score_trial(job) -> tuple:
    """One stage-2 candidate, start to finish: `(ages, score or None, its solve log, kept)`.

    `job` is `(diconf, dirname, ages, effort, overrides, keep)`, all plain data: this is what
    a pool runs in another process, where the caller's log stream does not exist -- the log
    comes back as text for the caller to write. With `keep`, a solved plan comes back too, as
    `kept = (its pickle, the options it was solved with)` (P4a); else `kept` is None.
    """
    diconf, dirname, ages, effort, overrides, keep = job
    buf = io.StringIO()
    q = _plan(diconf, dirname, buf, fixed_ages(ages))
    options = candidate_options(q.solverOptions, overrides, effort)
    q = _solve(q, options)
    value = score_plan(q) if q.caseStatus == "solved" else None
    kept = None
    if keep and value is not None:
        q.setLogger(None)  # its log is the text returned; its stream is this process's
        kept = (pickle.dumps(q), options)
    return [round(float(a), 4) for a in q.ssecAges], value, buf.getvalue(), kept


class _Copy:
    """A log stream that writes through to another and keeps a copy (a kept candidate's log)."""

    def __init__(self, stream):
        self._stream = stream
        self._copy = io.StringIO()

    def write(self, text):
        self._copy.write(text)
        return self._stream.write(text)

    def flush(self):
        flush = getattr(self._stream, "flush", None)
        if flush is not None:
            flush()

    def text(self) -> str:
        return self._copy.getvalue()


def _winner(scored) -> Optional[int]:
    """The index of the best score (the first of equal ones), None when none solved."""
    good = [i for i, (_, value) in enumerate(scored) if value is not None]
    return max(good, key=lambda i: scored[i][1]) if good else None


def two_stage_ages(diconf, dirname, log=None, *, check: Optional[Callable[[], Any]] = None,
                   effort: Optional[dict] = None, overrides: Optional[dict] = None, pool=None,
                   keep: bool = False):
    """Claiming ages for a case that searches them (run_suite's `two_stage_ages`).

    Returns ``(ages, candidates)`` with ``candidates = [(ages, score or None)]``. ``ages`` is
    the best-scoring candidate's (the stage-1 pick when its neighbours do not beat it; the
    first of equal scores). With ``keep``, ``(ages, candidates, Winner)``: that candidate's
    solved plan, its log and its options. Raises RuntimeError when a stage does not solve.
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
    best = None  # with `keep`: the best candidate so far, (index, plan or pickle, log, options)
    trials = _trials(pick, free, first)
    if pool is not None:
        if check is not None:
            check()
        jobs = [(diconf, dirname, t, effort, overrides, keep) for t in trials]
        for ages, value, text, kept in pool.map(score_trial, jobs):
            log.write(text)
            scored.append((ages, value))
            if kept is not None and _winner(scored) == len(scored) - 1:
                best = (len(scored) - 1, kept[0], text, kept[1])
        trials = []  # all scored
    for t in trials:
        if check is not None:
            check()
        stream = _Copy(log) if keep else log
        q = _plan(diconf, dirname, stream, fixed_ages(t))
        options = candidate_options(q.solverOptions, overrides, effort)
        q = _solve(q, options)
        scored.append(([round(float(a), 4) for a in q.ssecAges],
                       score_plan(q) if q.caseStatus == "solved" else None))
        if keep and scored[-1][1] is not None and _winner(scored) == len(scored) - 1:
            best = (len(scored) - 1, q, stream.text(), options)  # the plan it beat is dropped
    chosen = _winner(scored)
    if chosen is None:
        raise RuntimeError("stage 2: no candidate ages solved")
    ages = scored[chosen][0]
    if not keep:
        return ages, scored
    index, plan, text, options = best
    assert index == chosen, (index, chosen)  # one rule picks both (`_winner`)
    if isinstance(plan, bytes):
        plan = pickle.loads(plan)  # the pool's own pickle (`score_trial`), never one read from disk
    plan.setLogstreams(True, [log])
    return ages, scored, Winner(plan, text, options)

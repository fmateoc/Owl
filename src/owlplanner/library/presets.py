"""Run presets (run-library-design.md, section 8.1).

A preset is part of the scenario: it names how a run is solved, so it lands in the inputs
hash and in `record.json`. Every preset but the two Ages ones fixes the claiming ages (R4):
the template's `withSSAges = "optimize"` would make every quick run a claiming-age search.

Two levels, because "Decision" is one choice but two solves (section 8.1: "local search,
ages held fixed; the exact LP as a second result, read as an agreement check (does it order
the variants the same way?), not as a tolerance (R2)"):

- ``PRESETS`` is what the interface offers: ``quick``, ``decision``, ``ages``, ``custom``.
- ``SOLVE_PRESETS`` is what one results folder records. ``preset_solves`` expands a choice
  into the solves it queues: "decision" runs ``decision`` (local search) and
  ``decision_exact`` (the exact model companion the comparison's agreement check reads).

Built in step 2: ``quick`` and ``custom``. ``decision`` / ``decision_exact`` come with the
comparison (step 3). ``ages`` (section 8.1's "Ages": `run_suite.py`'s two-stage claiming-age
search, `library.agesearch`) and ``ages_thorough`` (its "Ages, thorough":
`owlplanner.work_sweep`'s every whole-year pair by branch-and-bound) come with
step 6.

- ``quick`` is section 8.1's "the default loop, claiming ages held": every tax family that
  can be solved exactly (`"optimize"`) is solved by the self-consistent loop instead, the
  breakpoint method is the loop and no MIP strategy is set, and the claiming ages are fixed
  (review N5: before, it forced the ages only, so on the template, `withMedicare =
  "optimize"`, every loop iteration was still a branch-and-bound MIP, and a case naming
  `breakpointMethod = "local-search"` ran local search). Model choices stay the case's own:
  `"none"` (no Medicare, no STAR) and a pinned SS taxable fraction are not solution methods.
  These settings are final: the caller's options cannot undo them (use ``custom``).
- ``decision`` is local search with the ages held fixed. Model choices stay the case's own;
  local search solves each tax family exactly itself (it also overrides a pinned SS taxable
  fraction and sets Medicare, SS taxability, LTCG, NIIT, senior bonus and ACA to "optimize";
  CLAUDE.md, "Loop noise"). Anything keyed on loop-mode Medicare does not hold under it.
  Its search runs at the library's own effort (`LOCAL_SEARCH_EFFORT`: 1,000 nodes a step,
  both wall-clock caps lifted), whatever the case says; the job's own options can change
  it.
- ``decision_exact`` is the exact model of `run_suite.py`'s condo-exact group (CLAUDE.md,
  "Loop noise"): the loop with Medicare off, the SS taxable fraction pinned at 0.85 and
  capital gains priced exactly (`withLTCG = "optimize"`). A different *model*, so only its
  differences compare (it mis-prices the ACA trade in marketplace years): it is read as
  "does it order the variants the same way?", never as a tolerance (R2).
- ``ages`` runs `library.agesearch`'s two-stage search when the case searches claiming ages
  (`withSSAges` not ``fixed``), then solves at the ages it picked: the exact LP searches,
  and the pick and its +-1-year neighbours are scored at fixed ages under the case's own
  model (section 8.1). It forces nothing (R4's exception): a case with ``withSSAges =
  "fixed"`` just solves, under its own model. Where that model is local search, the effort
  settings the case does not state are the library's (`LOCAL_SEARCH_EFFORT`), in stage 2
  and in the final solve alike: stage 2 picks by the raw score, so its candidates must not
  be cut short by the clock.
- ``ages_thorough`` (section 8.1's "Ages, thorough") runs `owlplanner.work_sweep`'s
  own sweep -- every whole-year pair of the searched people scored by branch-and-bound at
  gap 1e-5 (`run_variant`, stage (a)'s exact-LP search plus stage (c); the loop search is
  skipped) -- writes its `scores.json` (the claiming-age map reads it, I7) and solves at the
  ages it decided **the way the decided cell was scored** (`work_sweep.scorer_options`:
  branch-and-bound at the sweep's gap, or the local search it fell back to), so the published
  plan is the one the map's best cell shows (review AH1: the case's own options, with no gap,
  published a plan 1,208 below it on the synthetic household). That final solve repeats one
  scored plan's time. The same implementation `fork-notes/synthetic/run_suite.py` runs
  (`owlplanner.work_sweep`, moved into `src/owlplanner` 2026-11-05). A slow job (29-51 min
  per variant on the chris+pat dry run), one per request.
- ``regret`` (I8, one per request from the run page) solves as ``custom`` with the ages
  fixed, then runs the conversion regret sweep (`stresstests.run_conversion_regret_sweep`,
  its "Quick look" size) and writes `regret.json`: what a different first-year Roth
  conversion would have cost. It is a solve preset, not a queue-time choice (as
  ``decision_exact``); the interface offers it through the run page's own button.
- ``exact_medicare`` is ``decision_exact``'s model with Medicare priced exactly
  (`withMedicare = "optimize"`, IRMAA binaries; `EXACT_MEDICARE`): the sensitivity tornado
  solves its medical-inflation mover, and the run's own base for that bar, under it (review
  AJ1: the exact LP has no Medicare premiums, which are what medical inflation grows, so the
  bar read -83 where local search moved -1,813 on the synthetic household; this model gives
  -1,842 at +-198). A model companion like ``decision_exact`` (`view.record_companion`): never
  a run's headline result. A solve preset, not a queue-time choice.
- ``custom`` runs the case's own `[solver_options]`, with the caller's options on top (as
  `owlcli --solver-opt` does).
"""

from __future__ import annotations

from .agesearch import EXACT_GROUP, search_effort

# The tornado's medical-inflation model (review AJ1): the exact model with Medicare priced
# exactly. The other movers stay on `decision_exact` (EXACT_GROUP), which has Medicare off.
EXACT_MEDICARE = {**EXACT_GROUP, "withMedicare": "optimize"}

# What the interface offers (section 8.1's rows).
PRESETS = ("quick", "decision", "ages", "ages_thorough", "custom")

# What one solve is recorded as (its results folder is <stamp>_<solve preset>).
SOLVE_PRESETS = ("quick", "decision", "decision_exact", "exact_medicare", "ages", "ages_thorough",
                 "regret", "custom")

# Every solve preset as people know it (UX remediation QW-6, review AN8: one list; the run
# page's method line, `view.method_text`, reads it, and the picker, `ui/librarypresets.NAMES`,
# adds the time hints). The ids above stay what is stored.
PRESET_NAMES = {
    "quick": "Quick look",
    "decision": "Careful",
    "decision_exact": "Careful: the exact-model check",
    "exact_medicare": "Exact model with Medicare priced",
    "ages": "Let Owl choose the claiming ages",
    "ages_thorough": "Claiming ages, every pair tried",
    "custom": "The case's own solver options",
    "regret": "Roth conversion regret sweep",
}


def preset_name(preset) -> str:
    """A preset id in people's words (the id itself when it has no name)."""
    return PRESET_NAMES.get(preset, str(preset))


# The solve presets of a model companion: a model other than the case's own, read beside a
# run's headline result and never as it (`view.record_companion`).
COMPANION_PRESETS = ("decision_exact", "exact_medicare")

# The families whose "optimize" mode makes the solve a MIP (or a local search); "quick" puts
# each on the loop.
LOOP_FAMILIES = ("withMedicare", "withACA", "withLTCG", "withNIIT", "withSSTaxability",
                 "withSeniorBonus", "withSTAR")

# Local search's effort where the library runs it (performance review, 2026-11-11; the
# figures are `fork-notes/performance-review.md`'s, on the synthetic household).
#
# Upstream caps each restricted solve by branch-and-bound nodes "so that the answer does not
# depend on machine speed or load" (`localsearch.py`), with two wall-clock backstops behind
# the cap: 300 s for the whole search (`TOTAL_TIME`) and 60 s a step (`STEP_TIME`). On the
# synthetic household both backstops bind: 4 of 6 Careful solves ran into the 300 s when
# four ran at once, and a step took 81 s at 3,000 nodes under load. A result then depends on
# how busy the computer is (by dollars: +2.81/yr on one variant), the same run solved twice
# on one day can show two numbers, and nothing marks it. So the two caps are lifted to
# `work_sweep.py`'s values (they stay as backstops; `record.json` counts a search they cut,
# `search_budget_cuts`), and the node cap goes from upstream's 3,000 to 1,000, which pays
# for the lift: the identical plan on three of four variants measured and 1.06/yr less on
# the fourth, 37% less time where the search settles, about 18% and 53% more on the two
# variants where it keeps moving.
LOCAL_SEARCH_EFFORT = {
    "localSearchStepNodes": 1000,
    "localSearchTime": 7200.0,
    "localSearchStepTime": 1800.0,
}

# What each solve forces whatever the case says (R4: ages fixed, except the Ages presets).
_FORCED = {
    "quick": {"withSSAges": "fixed", "breakpointMethod": "loop"},
    "decision": {"withSSAges": "fixed", "breakpointMethod": "local-search"},
    # run_suite.py's EXACT_GROUP: the exact model companion of "decision" (R2's agreement
    # check). Ages fixed like the local-search solve it accompanies.
    "decision_exact": {"withSSAges": "fixed", **EXACT_GROUP},
    # The tornado's medical-inflation mover and its base (review AJ1): Medicare priced exactly.
    "exact_medicare": {"withSSAges": "fixed", **EXACT_MEDICARE},
    # The Ages presets force nothing: the case's own model, its own ages choice (section 8.1).
    # (The "Ages, thorough" worker re-solves its decided cell with the sweep's own scorer
    # options when the sweep ran, review AH1; a case with fixed ages just solves.)
    "ages": {},
    "ages_thorough": {},
    # I8's "regret" job: the case's own model with the ages fixed (R4), then the conversion
    # regret sweep over its historical scenarios ("what would a different conversion have
    # cost?"). One per request, from the run page; not one of section 8.1's rows.
    "regret": {"withSSAges": "fixed"},
    "custom": {},
}


# How many solves a job of each preset runs at once when the queue has the cores (the
# queue counts them, `JobManager.tick`; the worker sizes its pool by what it was given).
# Every other preset is one solve: about one core (1.1 measured on a Careful solve).
# 0 means "as many as the queue has".
# - ``ages``: stage 2 scores the pick and each searched person's two neighbours, five solves
#   for a couple; stage 1's thread pool runs inside the same share.
# - ``ages_thorough``: 81 whole-year pairs for a couple, each a branch-and-bound solve.
# - ``regret``: upstream's sweep solves its scenarios on a thread pool of every core, of which
#   the Python share holds the interpreter lock: 1.6 cores' worth measured on four threads
#   (`fork-notes/performance-review.md`, section 3b), counted as 2.
CORES_WANTED = {"ages": 5, "ages_thorough": 0, "regret": 2}


def cores_wanted(preset: str) -> int:
    """The solves a job of `preset` runs at once when it can (0: as many as the queue has)."""
    _check(preset)
    return CORES_WANTED.get(preset, 1)


def _check(preset: str) -> None:
    if preset not in _FORCED:
        raise ValueError(f"unknown preset {preset!r}: this build runs {SOLVE_PRESETS}")


def preset_solves(preset: str) -> tuple:
    """The solves one queue-time preset runs: (itself,), except "decision" (+ its exact companion)."""
    if preset == "decision":
        return ("decision", "decision_exact")
    _check(preset)
    return (preset,)


def preset_options(preset: str, options=None) -> dict:
    """The solver-option overrides a job of `preset` is queued with (stored in status.json).

    The caller's options, then the preset's forced ones on top. `resolve_options` applies the
    rest of the preset against the case's own options when the job runs.
    """
    _check(preset)
    merged = dict(options or {})
    merged.update(_FORCED[preset])
    return merged


def resolve_options(preset: str, case_options=None, overrides=None) -> dict:
    """The solver options a job of `preset` solves with, from the case's own options.

    The case's `[solver_options]`, the job's overrides on top, then the preset: for
    ``quick``, every `"optimize"` family on the loop, no MIP strategy, the loop as the
    breakpoint method and the ages fixed (N5); for ``decision``, ``decision_exact`` and
    ``ages``, the forced options only (solve presets, not queue-time choices; ``ages``
    forces nothing and keeps the case's own model).

    Local search's effort (`LOCAL_SEARCH_EFFORT`): ``decision`` sets it over the case's own
    settings and under the job's overrides (the preset is the method; an override is a
    choice made for one job). ``ages`` fills in only what neither states, where the model is
    local search (it forces nothing).
    """
    _check(preset)
    options = dict(case_options or {})
    if preset == "decision":
        options.update(LOCAL_SEARCH_EFFORT)
    options.update(dict(overrides or {}))
    if preset == "ages":
        options = search_effort(options, LOCAL_SEARCH_EFFORT)
    if preset == "quick":
        for key in LOOP_FAMILIES:
            if str(options.get(key, "")).strip().lower() == "optimize":
                options[key] = "loop"
        options.pop("mipStrategy", None)
        options.update(_FORCED["quick"])
    else:
        options.update(_FORCED[preset])
    return options

"""Run presets (run-library-design.md, section 8.1).

A preset is part of the scenario: it names how a run is solved, so it lands in the inputs
hash and in `record.json`. Every preset but the two Ages ones fixes the claiming ages (R4):
the template's `withSSAges = "optimize"` would make every quick run a claiming-age search.

Two levels, because "Decision" is one choice but two solves (section 8.1: "local search,
ages held fixed; the exact LP as a second result, read as an agreement check (does it order
the variants the same way?), not as a tolerance (R2)"):

- ``PRESETS`` is what the interface offers: ``quick``, ``decision``, ``custom``.
- ``SOLVE_PRESETS`` is what one results folder records. ``preset_solves`` expands a choice
  into the solves it queues: "decision" runs ``decision`` (local search) and
  ``decision_exact`` (the exact model companion the comparison's agreement check reads).

Built in step 2: ``quick`` and ``custom``. ``decision`` / ``decision_exact`` come with the
comparison (step 3). The two Ages presets (``run_suite.py``'s two-stage search) follow with
step 6 and bring their own machinery.

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
- ``decision_exact`` is the exact model of `run_suite.py`'s condo-exact group (CLAUDE.md,
  "Loop noise"): the loop with Medicare off, the SS taxable fraction pinned at 0.85 and
  capital gains priced exactly (`withLTCG = "optimize"`). A different *model*, so only its
  differences compare (it mis-prices the ACA trade in marketplace years): it is read as
  "does it order the variants the same way?", never as a tolerance (R2).
- ``custom`` runs the case's own `[solver_options]`, with the caller's options on top (as
  `owlcli --solver-opt` does).
"""

from __future__ import annotations

# What the interface offers (section 8.1's rows, minus the two Ages presets).
PRESETS = ("quick", "decision", "custom")

# What one solve is recorded as (its results folder is <stamp>_<solve preset>).
SOLVE_PRESETS = ("quick", "decision", "decision_exact", "custom")

# The families whose "optimize" mode makes the solve a MIP (or a local search); "quick" puts
# each on the loop.
LOOP_FAMILIES = ("withMedicare", "withACA", "withLTCG", "withNIIT", "withSSTaxability",
                 "withSeniorBonus", "withSTAR")

# What each solve forces whatever the case says (R4: ages fixed).
_FORCED = {
    "quick": {"withSSAges": "fixed", "breakpointMethod": "loop"},
    "decision": {"withSSAges": "fixed", "breakpointMethod": "local-search"},
    # run_suite.py's EXACT_GROUP: the exact model companion of "decision" (R2's agreement
    # check). Ages fixed like the local-search solve it accompanies.
    "decision_exact": {"withSSAges": "fixed", "breakpointMethod": "loop",
                       "withMedicare": "none", "withSSTaxability": 0.85, "withLTCG": "optimize"},
    "custom": {},
}


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
    breakpoint method and the ages fixed (N5); for ``decision`` and ``decision_exact``, the
    forced options only (a solve preset, not a queue-time choice).
    """
    _check(preset)
    options = dict(case_options or {})
    options.update(dict(overrides or {}))
    if preset == "quick":
        for key in LOOP_FAMILIES:
            if str(options.get(key, "")).strip().lower() == "optimize":
                options[key] = "loop"
        options.pop("mipStrategy", None)
        options.update(_FORCED["quick"])
    else:
        options.update(_FORCED[preset])
    return options

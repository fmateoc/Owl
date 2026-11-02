"""Run presets (run-library-design.md, section 8.1).

A preset is part of the scenario: it names how a run is solved, so it lands in the inputs
hash and in `record.json`. Every preset but the two Ages ones fixes the claiming ages (R4):
the template's `withSSAges = "optimize"` would make every quick run a claiming-age search.

Built in step 2: ``quick`` and ``custom``. ``decision`` (local search, ages fixed) and the two
Ages presets (``run_suite.py``'s two-stage search) follow with the comparison and presets
steps (3 and 6) and bring their own machinery.

- ``quick`` is section 8.1's "the default loop, claiming ages held": every tax family that
  can be solved exactly (`"optimize"`) is solved by the self-consistent loop instead, the
  breakpoint method is the loop and no MIP strategy is set, and the claiming ages are fixed
  (review N5: before, it forced the ages only, so on the template, `withMedicare =
  "optimize"`, every loop iteration was still a branch-and-bound MIP, and a case naming
  `breakpointMethod = "local-search"` ran local search). Model choices stay the case's own:
  `"none"` (no Medicare, no STAR) and a pinned SS taxable fraction are not solution methods.
  These settings are final: the caller's options cannot undo them (use ``custom``).
- ``custom`` runs the case's own `[solver_options]`, with the caller's options on top (as
  `owlcli --solver-opt` does).
"""

from __future__ import annotations

PRESETS = ("quick", "custom")

# The families whose "optimize" mode makes the solve a MIP (or a local search); "quick" puts
# each on the loop.
LOOP_FAMILIES = ("withMedicare", "withACA", "withLTCG", "withNIIT", "withSSTaxability",
                 "withSeniorBonus", "withSTAR")

# What each preset forces whatever the case says (R4: ages fixed).
_FORCED = {
    "quick": {"withSSAges": "fixed", "breakpointMethod": "loop"},
    "custom": {},
}


def _check(preset: str) -> None:
    if preset not in _FORCED:
        raise ValueError(f"unknown preset {preset!r}: this build runs {PRESETS}")


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
    breakpoint method and the ages fixed (N5).
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
    return options

"""Run presets (run-library-design.md, section 8.1).

A preset is part of the scenario: it names how a run is solved, so it lands in the inputs
hash and in `record.json`. Every preset but the two Ages ones fixes the claiming ages (R4):
the template's `withSSAges = "optimize"` would make every quick run a claiming-age search.

Built in step 2: ``quick`` (the default self-consistent loop, ages held at the scenario's
values) and ``custom`` (the case's own options, untouched). ``decision`` (local search, ages
fixed) and the two Ages presets (``run_suite.py``'s two-stage search) follow with the
comparison and presets steps (3 and 6) and bring their own machinery.

Option order: the preset's forced options first, the caller's `options` on top, and the
job's own result over the case's `[solver_options]` (as `owlcli --solver-opt` does).
"""

from __future__ import annotations

PRESETS = ("quick", "custom")

# What each preset forces on top of the case's own solver options (R4: ages fixed).
_FORCED = {
    "quick": {"withSSAges": "fixed"},
    "custom": {},
}


def preset_options(preset: str, options=None) -> dict:
    """The solver-option overrides a job of `preset` runs with (caller's options win)."""
    if preset not in _FORCED:
        raise ValueError(f"unknown preset {preset!r}: this build runs {PRESETS}")
    merged = dict(_FORCED[preset])
    for key, value in dict(options or {}).items():
        merged[key] = value
    return merged

"""Run presets (design section 8.1; review N5): what each preset solves with."""

import pytest

from owlplanner.library.presets import LOOP_FAMILIES, PRESETS, preset_options, resolve_options

TEMPLATE_LIKE = {
    "withSSAges": "optimize",
    "withMedicare": "optimize",
    "withACA": "loop",
    "withLTCG": "optimize",
    "withNIIT": "optimize",
    "withSSTaxability": "optimize",
    "withSeniorBonus": "optimize",
    "withSTAR": "optimize",
    "breakpointMethod": "local-search",
    "mipStrategy": "local-search",
    "gap": 1e-5,
    "maxIter": 29,
}


def test_quick_is_the_loop_with_the_ages_held():
    """Section 8.1's "the default loop": no family left on "optimize", no MIP strategy."""
    options = resolve_options("quick", TEMPLATE_LIKE)
    assert all(options[key] == "loop" for key in LOOP_FAMILIES)
    assert options["breakpointMethod"] == "loop" and "mipStrategy" not in options
    assert options["withSSAges"] == "fixed"
    assert options["gap"] == 1e-5 and options["maxIter"] == 29  # the rest is the case's


def test_quick_keeps_model_choices():
    """"none" and a pinned taxable fraction are what is modelled, not how it is solved."""
    options = resolve_options("quick", {"withMedicare": "none", "withSTAR": "none", "withSSTaxability": 0.85})
    assert options["withMedicare"] == "none" and options["withSTAR"] == "none"
    assert options["withSSTaxability"] == 0.85


def test_quick_cannot_be_undone_by_the_caller():
    options = resolve_options("quick", {}, {"withSSAges": "optimize", "withMedicare": "optimize",
                                            "breakpointMethod": "branch-and-bound"})
    assert options["withSSAges"] == "fixed" and options["withMedicare"] == "loop"
    assert options["breakpointMethod"] == "loop"
    assert preset_options("quick", {"withSSAges": "optimize"})["withSSAges"] == "fixed"


def test_custom_is_the_case_with_the_caller_on_top():
    options = resolve_options("custom", TEMPLATE_LIKE, {"withMedicare": "loop"})
    assert options == dict(TEMPLATE_LIKE, withMedicare="loop")


def test_an_unknown_preset_is_refused():
    assert PRESETS == ("quick", "custom")
    with pytest.raises(ValueError):
        resolve_options("decision", {})
    with pytest.raises(ValueError):
        preset_options("decision")

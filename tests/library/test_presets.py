"""Run presets (design section 8.1; review N5): what each preset solves with.

Step 3 adds "Decision": one queue-time choice, two solves -- local search and its exact-model
companion (`decision_exact`, the comparison's agreement check, R2). Step 6 adds "Ages":
`library.agesearch`'s two-stage claiming-age search, which forces nothing (R4's exception).
"""

import pytest

from owlplanner.library.presets import (
    LOOP_FAMILIES,
    PRESETS,
    SOLVE_PRESETS,
    preset_options,
    preset_solves,
    resolve_options,
)

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


def test_decision_is_local_search_with_the_ages_held():
    """Section 8.1: "local search, ages held fixed". Model choices stay the case's own."""
    options = resolve_options("decision", TEMPLATE_LIKE)
    assert options["breakpointMethod"] == "local-search" and options["withSSAges"] == "fixed"
    assert options["withMedicare"] == "optimize"  # local search solves the family exactly
    assert options["withSTAR"] == "optimize" and options["mipStrategy"] == "local-search"
    assert resolve_options("decision", {"withMedicare": "none"})["withMedicare"] == "none"


def test_decision_exact_is_run_suite_s_exact_model():
    """The EXACT_GROUP of run_suite.py: loop, Medicare off, SS taxability 0.85, LTCG exact."""
    options = resolve_options("decision_exact", TEMPLATE_LIKE)
    assert options["breakpointMethod"] == "loop" and options["withSSAges"] == "fixed"
    assert options["withMedicare"] == "none"
    assert options["withSSTaxability"] == 0.85
    assert options["withLTCG"] == "optimize"
    # It cannot be undone by the case or the caller (it is a model, not a default).
    assert resolve_options("decision_exact", {"withMedicare": "optimize"},
                           {"withSSTaxability": "optimize"})["withMedicare"] == "none"


def test_decision_queues_two_solves_and_the_others_one():
    assert preset_solves("decision") == ("decision", "decision_exact")
    assert preset_solves("quick") == ("quick",)
    assert preset_solves("ages") == ("ages",)
    assert preset_solves("custom") == ("custom",)


def test_ages_is_the_case_s_own_model_with_its_own_ages_choice():
    """Section 8.1's "Ages": the search and the candidates run under the case's own options
    (R4's exception: this preset does not fix the claiming ages)."""
    assert resolve_options("ages", TEMPLATE_LIKE) == TEMPLATE_LIKE
    assert resolve_options("ages", TEMPLATE_LIKE, {"mipStrategy": None}) == dict(
        TEMPLATE_LIKE, mipStrategy=None)
    assert preset_options("ages", {"withSSAges": "optimize"}) == {"withSSAges": "optimize"}
    assert resolve_options("ages", {"withSSAges": "fixed"})["withSSAges"] == "fixed"


def test_the_presets_the_interface_offers_and_the_solves_it_records():
    assert PRESETS == ("quick", "decision", "ages", "custom")
    # "decision_exact" and "regret" are solve presets, not queue-time choices: one is the
    # decision's exact companion, the other I8's per-request sweep (its button queues it).
    assert SOLVE_PRESETS == ("quick", "decision", "decision_exact", "ages", "regret", "custom")
    for preset in PRESETS:
        for solve in preset_solves(preset):
            assert solve in SOLVE_PRESETS
            assert isinstance(preset_options(solve), dict)  # every solve has its forced options
    assert preset_options("regret") == {"withSSAges": "fixed"}  # R4: the ages are fixed


def test_an_unknown_preset_is_refused():
    with pytest.raises(ValueError):
        resolve_options("ages_thorough", {})
    with pytest.raises(ValueError):
        preset_options("decision_exact_typo")
    with pytest.raises(ValueError):
        preset_solves("thorough")

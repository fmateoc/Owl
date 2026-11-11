"""Run presets (design section 8.1; review N5): what each preset solves with.

Step 3 adds "Decision": one queue-time choice, two solves -- local search and its exact-model
companion (`decision_exact`, the comparison's agreement check, R2). Step 6 adds "Ages":
`library.agesearch`'s two-stage claiming-age search, which forces nothing (R4's exception).
"""

import pytest

from owlplanner.library.presets import (
    LOCAL_SEARCH_EFFORT,
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


def test_decision_searches_at_the_library_s_effort():
    """Performance review, 2026-11-11: upstream's two wall-clock backstops (300 s a search,
    60 s a step) bind on the synthetic household, so a Careful result depended on how busy
    the computer was. The preset lifts both and caps a step at 1,000 nodes, whatever the
    case's own settings; an option given for the one job still wins."""
    assert LOCAL_SEARCH_EFFORT == {"localSearchStepNodes": 1000, "localSearchTime": 7200.0,
                                   "localSearchStepTime": 1800.0}
    options = resolve_options("decision", dict(TEMPLATE_LIKE, localSearchTime=300, localSearchStepNodes=3000))
    assert {key: options[key] for key in LOCAL_SEARCH_EFFORT} == LOCAL_SEARCH_EFFORT
    options = resolve_options("decision", TEMPLATE_LIKE, {"localSearchStepNodes": 300})
    assert options["localSearchStepNodes"] == 300 and options["localSearchTime"] == 7200.0
    # The job record's own options stay what was asked for: the effort is resolved at the solve.
    assert preset_options("decision") == {"withSSAges": "fixed", "breakpointMethod": "local-search"}


def test_ages_fills_in_the_effort_where_the_case_searches_locally():
    """The Ages preset forces nothing (R4): the settings the case states are kept, the ones
    it does not state are the library's -- and only where its model is local search."""
    options = resolve_options("ages", dict(TEMPLATE_LIKE, localSearchTime=600))
    assert options["localSearchTime"] == 600
    assert options["localSearchStepNodes"] == 1000 and options["localSearchStepTime"] == 1800.0
    loop_case = dict(TEMPLATE_LIKE, breakpointMethod="loop")
    assert resolve_options("ages", loop_case) == loop_case
    # A job's own option that makes it a local search brings the effort with it.
    assert resolve_options("ages", loop_case, {"breakpointMethod": "local-search"})["localSearchStepNodes"] == 1000


@pytest.mark.parametrize("preset", ["quick", "custom", "regret", "decision_exact", "exact_medicare", "ages_thorough"])
def test_the_other_presets_carry_no_search_effort(preset):
    options = resolve_options(preset, TEMPLATE_LIKE)
    assert not set(LOCAL_SEARCH_EFFORT) & set(options)


def test_what_each_preset_runs_at_once():
    """The queue counts cores (performance review, 2026-11-11): a single solve is one, the
    claiming-age presets score several plans side by side, the regret sweep is a thread pool."""
    from owlplanner.library.presets import cores_wanted

    assert {preset: cores_wanted(preset) for preset in SOLVE_PRESETS} == {
        "quick": 1, "decision": 1, "decision_exact": 1, "exact_medicare": 1, "custom": 1,
        "regret": 2, "ages": 5, "ages_thorough": 0}
    with pytest.raises(ValueError):
        cores_wanted("nonsense")


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


@pytest.mark.parametrize("case, overrides", [
    (TEMPLATE_LIKE, None),
    ({"breakpointMethod": "loop"}, None),
    ({"breakpointMethod": "loop"}, {"breakpointMethod": "local-search"}),
    (dict(TEMPLATE_LIKE, localSearchTime=600), {"localSearchStepNodes": 500}),
])
def test_ages_solves_as_its_stage_2_candidates(case, overrides):
    """P4a: "ages" publishes the winning stage-2 candidate's plan, so its options are the
    rule the candidates solve by (`agesearch.candidate_options`), whatever the job adds."""
    from owlplanner.library.agesearch import candidate_options

    assert resolve_options("ages", case, overrides) == candidate_options(case, overrides, LOCAL_SEARCH_EFFORT)


def test_ages_is_the_case_s_own_model_with_its_own_ages_choice():
    """Section 8.1's "Ages": the search and the candidates run under the case's own options
    (R4's exception: this preset does not fix the claiming ages)."""
    # Nothing the case states is changed; where its model is local search, the effort
    # settings it does not state are the library's (performance review, 2026-11-11).
    assert resolve_options("ages", TEMPLATE_LIKE) == dict(TEMPLATE_LIKE, **LOCAL_SEARCH_EFFORT)
    assert resolve_options("ages", TEMPLATE_LIKE, {"mipStrategy": None}) == dict(
        TEMPLATE_LIKE, mipStrategy=None, **LOCAL_SEARCH_EFFORT)
    assert preset_options("ages", {"withSSAges": "optimize"}) == {"withSSAges": "optimize"}
    assert resolve_options("ages", {"withSSAges": "fixed"})["withSSAges"] == "fixed"


def test_the_presets_the_interface_offers_and_the_solves_it_records():
    assert PRESETS == ("quick", "decision", "ages", "ages_thorough", "custom")
    # "decision_exact", "exact_medicare" and "regret" are solve presets, not queue-time
    # choices: the decision's exact companion, the tornado's medical-inflation model (review
    # AJ1), and I8's per-request sweep (their buttons queue them).
    assert SOLVE_PRESETS == ("quick", "decision", "decision_exact", "exact_medicare", "ages",
                             "ages_thorough", "regret", "custom")
    for preset in PRESETS:
        for solve in preset_solves(preset):
            assert solve in SOLVE_PRESETS
            assert isinstance(preset_options(solve), dict)  # every solve has its forced options
    assert preset_options("regret") == {"withSSAges": "fixed"}  # R4: the ages are fixed
    # R4's exception: both Ages presets force nothing (the case's own model and ages).
    assert preset_options("ages") == {} and preset_options("ages_thorough") == {}


def test_an_unknown_preset_is_refused():
    with pytest.raises(ValueError):
        resolve_options("thorough", {})
    with pytest.raises(ValueError):
        preset_options("decision_exact_typo")
    with pytest.raises(ValueError):
        preset_solves("quick_thorough")


def test_aj1_the_medicare_companion_is_the_exact_model_with_medicare_priced_exactly():
    """Review AJ1: the tornado's medical-inflation mover solves with Medicare (the exact LP has
    it off); a solve preset and a model companion, never a queue-time choice."""
    from owlplanner.library.agesearch import EXACT_GROUP
    from owlplanner.library.presets import COMPANION_PRESETS, EXACT_MEDICARE

    assert EXACT_MEDICARE == {**EXACT_GROUP, "withMedicare": "optimize"}
    assert preset_options("exact_medicare") == {"withSSAges": "fixed", **EXACT_MEDICARE}
    assert COMPANION_PRESETS == ("decision_exact", "exact_medicare")
    assert "exact_medicare" not in PRESETS

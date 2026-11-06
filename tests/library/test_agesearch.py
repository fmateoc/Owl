"""The "Ages" preset's two-stage claiming-age search (design section 8.1, step 6).

`library.agesearch` is `run_suite.py`'s two-stage search, one implementation shared by the
suite and the interface. The search itself needs solves, so the acceptance check runs it
(`fork-notes/synthetic/check_library_variants.py`); these tests pin the pieces: the trial
set stage 2 scores, the option sets, the score rule, and the worker's wiring (the chosen
ages reach the final solve and the record's `age_search` block).
"""

import json

import pytest

from owlplanner.library import results as R
from owlplanner.library import agesearch
from owlplanner.library.worker import run_job

BILL = "examples/Case_bill.toml"


class TestTrials:
    def test_the_pick_and_each_free_person_s_neighbours(self):
        # 62+ and 70- still add a neighbour; 62- and 70+ are clipped away (run_suite's rule).
        assert agesearch._trials([67.0, 66.0], [0, 1]) == [
            [67.0, 66.0], [66.0, 66.0], [68.0, 66.0], [67.0, 65.0], [67.0, 67.0]]
        assert agesearch._trials([62.0, 70.0], [0, 1]) == [
            [62.0, 70.0], [63.0, 70.0], [62.0, 69.0]]

    def test_only_the_free_people_move(self):
        assert agesearch._trials([66.0, 67.0], [1]) == [
            [66.0, 67.0], [66.0, 66.0], [66.0, 68.0]]

    def test_a_month_based_pick_still_tries_the_whole_year(self):
        # run_suite's comment: "a 69y10m pick still tries 70" (the +1 year clips to 70).
        trials = agesearch._trials([69.8333], [0])
        assert [t[0] for t in trials] == pytest.approx([69.8333, 68.8333, 70.0])

    def test_aj4_a_neighbour_below_the_first_open_month_is_clipped_to_it(self):
        """Review AJ4: Ari, born April 1964, is 62y7m in November 2026; the pick 62y9m's
        -1 year neighbour was 62y0m, a month already past, which Owl solves at fixed ages
        without a word as benefits already being collected."""
        first = [62 + 7 / 12, 62 + 1 / 12]
        trials = agesearch._trials([62.75, 70.0], [0, 1], first)
        assert [round(t[0], 4) for t in trials] == [62.75, 62.5833, 63.75, 62.75]
        # A pick at the first open month has no neighbour below it.
        trials = agesearch._trials([62 + 7 / 12, 70.0], [0], first)
        assert [round(t[0], 4) for t in trials] == [62.5833, 63.5833]
        # Without `first` the 62-70 clip alone (run_suite's rule before the fold).
        assert agesearch._trials([62.75, 70.0], [0])[1] == [62.0, 70.0]

    def test_aj4_the_search_clips_at_each_person_s_first_open_month(self, monkeypatch):
        """`two_stage_ages` reads each person's first open claiming age from the stage-1 plan
        (`Plan._ssaOpenAges`) and no stage-2 trial goes below it."""
        import types

        open_ages = {0: [62 + 7 / 12 + m / 12 for m in range(0, 90)], 1: [62 + 1 / 12]}
        tried = []

        def plan(diconf, dirname, log, sets=()):
            ages = next((json.loads(x.split("=", 1)[1]) for x in sets
                         if x.startswith("fixed_income.social_security_ages=")), [62.75, 70.0])
            tried.append(ages)
            return types.SimpleNamespace(ssecAges=ages, caseStatus="solved", inames=["Ari", "Noa"],
                                         _ssaOpenAges=lambda i: open_ages[i], objective="maxSpending")

        monkeypatch.setattr(agesearch, "_plan", plan)
        monkeypatch.setattr(agesearch, "_solve", lambda p, options=None: p)
        monkeypatch.setattr(agesearch, "score_plan", lambda p: -abs(p.ssecAges[0] - 62.0))
        ages, scored = agesearch.two_stage_ages({"solver_options": {"withSSAges": "Ari"}}, ".")
        assert [round(a[0], 4) for a, _ in scored] == [62.75, 62.5833, 63.75]
        assert round(ages[0], 4) == 62.5833  # the closest open month, never 62y0m


class TestOptions:
    def test_the_exact_model_is_run_suite_s(self):
        assert agesearch.EXACT_MODEL == {"breakpointMethod": "loop", "withMedicare": "none",
                                         "withSSTaxability": 0.85}
        assert agesearch.EXACT_GROUP == {**agesearch.EXACT_MODEL, "withLTCG": "optimize"}
        assert agesearch.EXACT_SETS == ["solver_options.breakpointMethod=loop",
                                        "solver_options.withMedicare=none",
                                        "solver_options.withSSTaxability=0.85"]
        assert agesearch.EXACT_GROUP_SETS == agesearch.EXACT_SETS + \
            ["solver_options.withLTCG=optimize"]

    def test_fixed_ages_is_the_set_form(self):
        assert agesearch.fixed_ages([62, 70]) == [
            "solver_options.withSSAges=fixed",
            "fixed_income.social_security_ages=[62.0, 70.0]"]


class TestSearchedNames:
    def test_optimize_searches_everyone_and_a_name_only_that_person(self):
        assert agesearch.searched_names("optimize", ["Ari", "Noa"]) == ["Ari", "Noa"]
        assert agesearch.searched_names("Noa", ["Ari", "Noa"]) == ["Noa"]
        assert agesearch.searched_names(["Noa"], ["Ari", "Noa"]) == ["Noa"]
        assert agesearch.searched_names("fixed", ["Ari", "Noa"]) == []


def test_score_plan_reads_the_suite_s_rule(monkeypatch):
    """maxSpending scores the first year's discretionary spending when the budget has
    essential lines (k x D_0), else the spending basis; maxBequest scores the final
    bequest (run_suite's `_score_plan`)."""
    import owlplanner.export as export

    class _Budget:
        discretionary_n = [100.0]

    class _Plan:
        objective = "maxSpending"
        budget = _Budget()

    metrics = {"final_bequest_today": 5.0, "spending_basis": 7.0, "discretionary_scale": 3.0}
    monkeypatch.setattr(export, "plan_metrics", lambda plan: dict(metrics))
    assert agesearch.score_plan(_Plan()) == 300.0
    metrics.pop("discretionary_scale")
    assert agesearch.score_plan(_Plan()) == 7.0
    _Plan.objective = "maxBequest"
    assert agesearch.score_plan(_Plan()) == 5.0


class TestWorkerWiring:
    """The "Ages" preset through the worker: the search's pick is what solves (step 6)."""

    @pytest.fixture
    def library(self, tmp_path):
        from owlplanner.library import Library

        return Library.open(tmp_path / "library")

    @pytest.fixture
    def searched_case(self, library):
        from owlplanner.library import import_case

        scenario = import_case(BILL)
        scenario["case"]["solver_options"]["withSSAges"] = "optimize"  # the case searches
        return library.save_run(name="bill", scenario=scenario).run

    def _job(self, run, name="2026-01-01T00-00-00_ages"):
        return R.JobRecord.create(run.path / "results" / name, run_id=run.id, run_name=run.name,
                                  preset="ages", options={}, plan_year=2026)

    def test_the_search_picks_and_the_final_solve_uses_them(self, searched_case, monkeypatch):
        calls = {}

        def fake_search(diconf, dirname, log=None, *, check=None):
            calls["withSSAges"] = diconf.get("solver_options", {}).get("withSSAges")
            return [66.0], [([66.0], 123.0), ([67.0], 100.0)]

        monkeypatch.setattr("owlplanner.library.worker.two_stage_ages", fake_search)
        job = self._job(searched_case)
        assert run_job(job.results_dir, job.token) == R.DONE
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["preset"] == "ages"
        assert record["age_search"] == {"chosen": [66.0],
                                        "candidates": [[[66.0], 123.0], [[67.0], 100.0]]}
        # The search saw the case's own ages choice; the final solve pinned the pick.
        assert calls["withSSAges"] == "optimize"
        assert record["method"]["options"]["withSSAges"] == "fixed"
        plan_doc = json.loads((job.results_dir / R.PLAN_JSON).read_text(encoding="utf-8"))
        assert plan_doc["claiming_ages"] == [66.0]

    def test_a_fixed_ages_case_skips_the_search(self, library, monkeypatch):
        from owlplanner.library import import_case

        scenario = import_case(BILL)  # Case_bill: withSSAges = "fixed"
        run = library.save_run(name="bill fixed", scenario=scenario).run

        def boom(*args, **kwargs):
            raise AssertionError("the search must not run when the ages are fixed")

        monkeypatch.setattr("owlplanner.library.worker.two_stage_ages", boom)
        job = self._job(run)
        assert run_job(job.results_dir, job.token) == R.DONE
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["age_search"] is None

    def test_the_other_presets_record_no_search(self, searched_case, monkeypatch):
        def boom(*args, **kwargs):
            raise AssertionError("quick must not search the ages")

        monkeypatch.setattr("owlplanner.library.worker.two_stage_ages", boom)
        job = R.JobRecord.create(searched_case.path / "results" / "2026-01-01T00-00-00_quick",
                                 run_id=searched_case.id, run_name=searched_case.name,
                                 preset="quick", options={"withSSAges": "fixed"}, plan_year=2026)
        assert run_job(job.results_dir, job.token) == R.DONE
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["age_search"] is None

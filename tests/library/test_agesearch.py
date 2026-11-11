"""The "Ages" preset's two-stage claiming-age search (design section 8.1, step 6).

`library.agesearch` is `run_suite.py`'s two-stage search, one implementation shared by the
suite and the interface. The search itself needs solves, so the acceptance check runs it
(`fork-notes/synthetic/check_library_variants.py`); these tests pin the pieces: the trial
set stage 2 scores, the option sets, the score rule, and the worker's wiring (the winning
candidate's plan is the one published, and the record's `age_search` block).
"""

import io
import json

import pytest

from owlplanner.library import results as R
from owlplanner.library import agesearch
from owlplanner.library.presets import LOCAL_SEARCH_EFFORT
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
                                         _ssaOpenAges=lambda i: open_ages[i], objective="maxSpending",
                                         solverOptions={})

        monkeypatch.setattr(agesearch, "_plan", plan)
        monkeypatch.setattr(agesearch, "_solve", lambda p, options=None: p)
        monkeypatch.setattr(agesearch, "score_plan", lambda p: -abs(p.ssecAges[0] - 62.0))
        ages, scored = agesearch.two_stage_ages({"solver_options": {"withSSAges": "Ari"}}, ".")
        assert [round(a[0], 4) for a, _ in scored] == [62.75, 62.5833, 63.75]
        assert round(ages[0], 4) == 62.5833  # the closest open month, never 62y0m

    def _stage2_options(self, monkeypatch, case_options, effort, overrides=None):
        import types

        seen = []

        def plan(diconf, dirname, log, sets=()):
            fixed = any(x == "solver_options.withSSAges=fixed" for x in sets)
            return types.SimpleNamespace(ssecAges=[66.0], caseStatus="solved", inames=["Ari"], fixed=fixed,
                                         _ssaOpenAges=lambda i: [62.0], solverOptions=dict(case_options))

        def solve(p, options=None):
            if p.fixed:
                seen.append(options)
            return p

        monkeypatch.setattr(agesearch, "_plan", plan)
        monkeypatch.setattr(agesearch, "_solve", solve)
        monkeypatch.setattr(agesearch, "score_plan", lambda p: 1.0)
        agesearch.two_stage_ages({"solver_options": {"withSSAges": "Ari"}}, ".", effort=effort,
                                 overrides=overrides)
        return seen

    def test_stage_2_searches_at_the_effort_given(self, monkeypatch):
        """Stage 2 picks by the raw score, so where the case's model is local search its
        candidates run at the caller's effort (the library's: wall-clock caps lifted), and the
        settings the case states itself are kept (the Ages presets force nothing, R4)."""
        case = {"breakpointMethod": "local-search", "localSearchTime": 600}
        seen = self._stage2_options(monkeypatch, case, LOCAL_SEARCH_EFFORT)
        assert len(seen) == 3 and all(o == seen[0] for o in seen)  # the pick and its two neighbours
        assert seen[0]["localSearchTime"] == 600
        assert seen[0]["localSearchStepNodes"] == LOCAL_SEARCH_EFFORT["localSearchStepNodes"]
        assert seen[0]["localSearchStepTime"] == LOCAL_SEARCH_EFFORT["localSearchStepTime"]

    def test_stage_2_leaves_another_method_alone(self, monkeypatch):
        seen = self._stage2_options(monkeypatch, {"breakpointMethod": "loop"}, LOCAL_SEARCH_EFFORT)
        assert seen == [{"breakpointMethod": "loop"}] * 3

    def test_without_an_effort_stage_2_is_the_case_s_own(self, monkeypatch):
        """`run_suite.py` calls it so: the plan's own options."""
        case = {"breakpointMethod": "local-search"}
        assert self._stage2_options(monkeypatch, case, None) == [case] * 3

    def test_stage_2_puts_the_job_s_options_over_the_case_s(self, monkeypatch):
        """P4a: the plan published is the winning candidate's, so every candidate solves as
        the published solve would, the job's own options included (`candidate_options`,
        which `presets.resolve_options` reads for "ages")."""
        from owlplanner.library.presets import resolve_options

        case = {"breakpointMethod": "loop", "withMedicare": "loop"}
        overrides = {"breakpointMethod": "local-search", "localSearchStepNodes": 500}
        seen = self._stage2_options(monkeypatch, case, LOCAL_SEARCH_EFFORT, overrides)
        assert seen == [resolve_options("ages", case, overrides)] * 3
        assert seen[0]["localSearchStepNodes"] == 500  # the job's own setting is kept
        assert seen[0]["localSearchTime"] == LOCAL_SEARCH_EFFORT["localSearchTime"]


class TestKeep:
    """Performance review P4a (2026-11-11): the search returns the winning candidate's own
    plan, which the worker publishes instead of solving it again."""

    def test_the_first_of_equal_scores_wins(self):
        assert agesearch._winner([([1.0], None), ([2.0], 5.0), ([3.0], 5.0), ([4.0], 4.0)]) == 1
        assert agesearch._winner([([1.0], None)]) is None

    def _stubbed(self, monkeypatch, scores):
        """Stage 2 on stubs: candidate ages [66, 65, 67] score `scores[age]`."""
        import types

        def plan(diconf, dirname, log, sets=()):
            ages = [66.0]
            for spec in sets:
                if spec.startswith("fixed_income.social_security_ages="):
                    ages = json.loads(spec.split("=", 1)[1])
            log.write(f"solving at {ages}\n")
            return types.SimpleNamespace(ssecAges=ages, caseStatus="solved", inames=["Ari"],
                                         _ssaOpenAges=lambda i: [62.0], solverOptions={"x": 1},
                                         streams=None, setLogstreams=None)

        def solve(p, options=None):
            p.setLogstreams = lambda verbose, streams, p=p: setattr(p, "streams", streams)
            return p

        monkeypatch.setattr(agesearch, "_plan", plan)
        monkeypatch.setattr(agesearch, "_solve", solve)
        monkeypatch.setattr(agesearch, "score_plan", lambda p: scores[p.ssecAges[0]])

    def test_the_winner_is_the_best_candidate_s_own_plan(self, monkeypatch):
        self._stubbed(monkeypatch, {66.0: 1.0, 65.0: 3.0, 67.0: 3.0})
        log = io.StringIO()
        ages, scored, winner = agesearch.two_stage_ages(
            {"solver_options": {"withSSAges": "Ari"}}, ".", log, overrides={"y": 2}, keep=True)
        assert ages == [65.0] and [a for a, _ in scored] == [[66.0], [65.0], [67.0]]
        assert winner.plan.ssecAges == [65.0]  # the first of the two best, as `ages` says
        assert winner.log == "solving at [65.0]\n" and winner.log in log.getvalue()
        assert winner.options == {"x": 1, "y": 2}
        assert winner.plan.streams == [log]  # it logs to the caller's stream from now on

    def test_without_keep_the_result_is_as_before(self, monkeypatch):
        self._stubbed(monkeypatch, {66.0: 1.0, 65.0: 3.0, 67.0: 2.0})
        result = agesearch.two_stage_ages({"solver_options": {"withSSAges": "Ari"}}, ".")
        assert result == ([65.0], [([66.0], 1.0), ([65.0], 3.0), ([67.0], 2.0)])


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

    def test_the_search_s_plan_is_the_one_published(self, searched_case, monkeypatch):
        """P4a: the winning candidate's plan is published as it is; nothing is solved again."""
        from owlplanner.plan import Plan

        calls = {}
        solves = []
        real_solve = Plan.solve

        def counted(self, *args, **kwargs):
            solves.append(self)
            return real_solve(self, *args, **kwargs)

        monkeypatch.setattr(Plan, "solve", counted)

        def fake_search(diconf, dirname, log=None, *, check=None, effort=None, overrides=None,
                        pool=None, keep=False):
            calls.update(effort=effort, pool=pool, overrides=overrides, keep=keep,
                         withSSAges=diconf.get("solver_options", {}).get("withSSAges"))
            own = io.StringIO()
            plan = agesearch._plan(diconf, dirname, own, agesearch.fixed_ages([66.0]))
            options = agesearch.candidate_options(plan.solverOptions, overrides, effort)
            agesearch._solve(plan, options)
            own.write("12:00 | WARNING | the kept solve's own warning\n")
            log.write(own.getvalue())
            plan.setLogstreams(True, [log])
            calls["plan"] = plan
            return ([66.0], [([66.0], 123.0), ([67.0], 100.0)],
                    agesearch.Winner(plan, own.getvalue(), options))

        monkeypatch.setattr("owlplanner.library.worker.two_stage_ages", fake_search)
        job = self._job(searched_case)
        assert run_job(job.results_dir, job.token) == R.DONE
        record = json.loads((job.results_dir / R.RECORD_JSON).read_text(encoding="utf-8"))
        assert record["preset"] == "ages"
        assert record["age_search"] == {"chosen": [66.0], "stage_2_plan": True,
                                        "candidates": [[[66.0], 123.0], [[67.0], 100.0]]}
        assert solves == [calls["plan"]]  # the stage's own solve, and no other
        # The search saw the case's own ages choice and the job's options (none here).
        assert calls["withSSAges"] == "optimize"
        assert calls["overrides"] == {} and calls["keep"] is True
        # Stage 2 runs at the library's search effort (performance review, 2026-11-11).
        assert calls["effort"] == LOCAL_SEARCH_EFFORT
        assert calls["pool"] is None  # a job with one core scores its candidates in a row
        assert record["method"]["options"]["withSSAges"] == "fixed"
        # The kept solve's log is read as the published solve's; it is in solve.log once.
        assert "the kept solve's own warning" in record["warnings"]
        log = (job.results_dir / R.SOLVE_LOG).read_text(encoding="utf-8")
        assert log.count("the kept solve's own warning") == 1
        assert "published as solved there (not solved again)" in log
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


class TestStageTwoOnAPool:
    """Performance review, 2026-11-11 (P4b): stage 2's candidates are independent solves; with
    a pool they are scored side by side and decided exactly as in a row."""

    class Pool:
        """`map` in this process: the scoring's logic, without the processes (the worker's
        pool is tested with them in test_worker.py)."""

        def __init__(self):
            self.jobs = []

        def map(self, fn, items):
            self.jobs = list(items)
            return [fn(item) for item in self.jobs]

    @pytest.fixture
    def searched(self):
        from owlplanner.cli.set_override import apply_overrides
        from owlplanner.config import load_toml

        diconf, dirname, _ = load_toml(BILL)
        return apply_overrides(diconf, ["solver_options.withSSAges=optimize"]), dirname

    def test_the_pool_scores_what_the_row_scores(self, searched):
        diconf, dirname = searched
        log_a, log_b = io.StringIO(), io.StringIO()
        pool = self.Pool()
        in_a_row = agesearch.two_stage_ages(diconf, dirname, log_a)
        on_a_pool = agesearch.two_stage_ages(diconf, dirname, log_b, pool=pool)
        assert on_a_pool == in_a_row
        assert len(pool.jobs) == len(in_a_row[1]) >= 2  # every candidate went to the pool
        # Each candidate's solve log reaches the caller's stream, as it does in a row.
        assert log_b.getvalue().count("Objective:") == log_a.getvalue().count("Objective:") > 0

    def test_a_candidate_is_plain_data(self, searched):
        """What crosses to another process pickles, and comes back as (ages, score, log, kept):
        with `keep`, the solved plan's pickle and its options (P4a)."""
        import pickle

        diconf, dirname = searched
        for keep in (False, True):
            job = (diconf, dirname, [67.0], LOCAL_SEARCH_EFFORT, None, keep)
            ages, value, text, kept = agesearch.score_trial(pickle.loads(pickle.dumps(job)))
            assert ages == [67.0] and value > 0 and isinstance(text, str) and text
            pickle.dumps((ages, value, text, kept))
            if not keep:
                assert kept is None
                continue
            blob, options = kept
            plan = pickle.loads(blob)
            assert plan.caseStatus == "solved" and list(plan.ssecAges) == [67.0]
            assert options["withSSAges"] == "fixed"
            assert agesearch.score_plan(plan) == value

    class PicklingPool(Pool):
        """`map` in this process, every item and result through a pickle, as a process pool
        sends them."""

        def map(self, fn, items):
            import pickle

            self.jobs = list(items)
            return [pickle.loads(pickle.dumps(fn(pickle.loads(pickle.dumps(item))))) for item in self.jobs]

    @pytest.mark.parametrize("on_a_pool", [False, True])
    def test_the_kept_plan_is_what_solving_again_gives(self, searched, on_a_pool):
        """P4a: the plan kept is the plan the worker used to build again at the chosen ages and
        solve with `resolve_options("ages", ...)`: the same results, to the last figure."""
        from owlplanner.cli.formatters import plan_to_dict
        from owlplanner.config.schema import parse_solver_options
        from owlplanner.export import plan_metrics
        from owlplanner.library.presets import resolve_options

        diconf, dirname = searched
        log = io.StringIO()
        pool = self.PicklingPool() if on_a_pool else None
        ages, scored, winner = agesearch.two_stage_ages(diconf, dirname, log, effort=LOCAL_SEARCH_EFFORT,
                                                        pool=pool, keep=True)
        assert (ages, scored) == agesearch.two_stage_ages(diconf, dirname, effort=LOCAL_SEARCH_EFFORT)
        again = agesearch._plan(diconf, dirname, io.StringIO(), agesearch.fixed_ages(ages))
        options = resolve_options("ages", again.solverOptions, None)
        again.solve(again.objective, parse_solver_options(options))
        assert winner.options == options

        def doc(plan):
            out = plan_to_dict(plan)
            out.pop("solve_time_seconds", None)  # load-dependent
            return json.dumps(out, sort_keys=True, default=str)

        assert doc(winner.plan) == doc(again)
        assert json.dumps(plan_metrics(winner.plan), sort_keys=True, default=str) == \
            json.dumps(plan_metrics(again), sort_keys=True, default=str)
        # Its own log is among the candidates' in the caller's stream, and it logs there now.
        assert winner.log and winner.log in log.getvalue()
        before = len(log.getvalue())
        winner.plan.mylog.vprint("after the search")
        assert "after the search" in log.getvalue()[before:]

    def test_the_check_still_runs_before_the_pool(self, searched):
        diconf, dirname = searched

        def stop():
            raise RuntimeError("cancelled")

        pool = self.Pool()
        with pytest.raises(RuntimeError, match="cancelled"):
            agesearch.two_stage_ages(diconf, dirname, check=stop, pool=pool)
        assert pool.jobs == []

"""`work_sweep.score` keeps the plans it scores, for the run library's "Ages, thorough".

The library publishes the decided cell's own plan instead of solving it again (performance
review P4a, as for "ages"): `score` pickles the plan whose value a cell records into the
folder the caller names (`cfg["keep_dir"]`), and `load_kept_plan` reads the decided cell's.
The command (`python -m owlplanner.work_sweep`) names no folder and keeps nothing. The job's
own options reach every scored plan (`scorer_options`), between the case's and the scorer's.
"""

import copy
import io
import json
import os
import types
from pathlib import Path

import pytest

from owlplanner import work_sweep as ws
from owlplanner.config import load_toml


def _cfg(**extra):
    args = types.SimpleNamespace(decider="bb", gap=1e-5, max_time=900.0, ls_time=7200.0,
                                 ls_step_time=1800.0, **extra)
    return ws.scorer_config(args)


class _Serial:
    def map(self, fn, items):
        return [fn(item) for item in items]


class _Stand:
    """A picklable stand-in for a scored plan (the fallback rule's tests)."""

    def __init__(self, name):
        self.name = name

    def setLogger(self, logger):
        self.logger = logger


def _drop_clock(doc) -> int:
    """Remove `plan_to_dict`'s `solve_time_seconds` wherever it is; how many were removed."""
    n = 0
    if isinstance(doc, dict):
        n += doc.pop("solve_time_seconds", None) is not None
        n += sum(_drop_clock(v) for v in doc.values())
    elif isinstance(doc, list):
        n += sum(_drop_clock(v) for v in doc)
    return n


def _searching(case):
    diconf, dirname, _ = load_toml(str(Path(case).resolve()))
    diconf = copy.deepcopy(diconf)
    diconf["solver_options"]["withSSAges"] = "optimize"
    return diconf, dirname


class TestTheConfig:
    def test_the_command_s_config_keeps_nothing(self):
        """The command's arguments have neither setting: its config is what it was."""
        assert _cfg() == {"decider": "bb", "gap": 1e-5, "max_time": 900.0, "ls_time": 7200.0,
                          "ls_step": 1800.0}

    def test_the_library_s_settings(self, tmp_path):
        cfg = _cfg(keep_dir=tmp_path, overrides={"spendingSlack": 3})
        assert cfg["keep_dir"] == str(tmp_path) and cfg["overrides"] == {"spendingSlack": 3}

    def test_the_job_s_options_go_between_the_case_s_and_the_scorer_s(self):
        p = types.SimpleNamespace(solverOptions={"withMedicare": "optimize", "spendingSlack": 0,
                                                 "breakpointMethod": "loop", "withSSAges": "optimize"})
        cfg = _cfg(overrides={"spendingSlack": 3, "withSSAges": "optimize", "localSearchTime": 5.0,
                              "gap": 0.1, "noLateSurplus": True})
        bb = ws.scorer_options(p, cfg)
        # The job's option wins over the case's; the method keys (PRESET_KEYS) are the
        # scorer's alone; the scorer's own settings win over the job's.
        assert bb == {"withMedicare": "optimize", "spendingSlack": 3, "noLateSurplus": True,
                      "withSSAges": "fixed", "breakpointMethod": "branch-and-bound", "gap": 1e-5,
                      "maxTime": 900.0}
        ls = ws.scorer_options(p, cfg, "local search")
        assert ls == {"withMedicare": "optimize", "spendingSlack": 3, "noLateSurplus": True, "gap": 0.1,
                      "withSSAges": "fixed", "breakpointMethod": "local-search",
                      "localSearchTime": 7200.0, "localSearchStepTime": 1800.0}


class TestTheRule:
    """Which plan a cell keeps: the one whose value it records."""

    def _patch(self, monkeypatch, bb, ls):
        calls = []

        def score_bb(diconf, dirname, ages, cfg):
            calls.append("bb")
            return dict(bb, _kept=(_Stand("bb"), io.StringIO("bb log"), {"breakpointMethod": "branch-and-bound"}))

        def score_ls(diconf, dirname, ages, cfg):
            calls.append("ls")
            return dict(ls, _kept=(_Stand("ls"), io.StringIO("ls log"), {"breakpointMethod": "local-search"}))

        monkeypatch.setattr(ws, "_score_bb", score_bb)
        monkeypatch.setattr(ws, "_score_ls", score_ls)
        return calls

    def test_a_proved_plan_is_kept(self, monkeypatch, tmp_path):
        calls = self._patch(monkeypatch, {"status": "solved", "value": 10.0, "proved": True}, {})
        out = ws.score((None, None, [67.0], _cfg(keep_dir=tmp_path)))
        assert calls == ["bb"] and "_kept" not in out
        kept = ws.load_kept_plan(tmp_path, [804])
        assert kept.plan.name == "bb" and kept.log == "bb log" and kept.plan.logger is None
        assert kept.options == {"breakpointMethod": "branch-and-bound"}
        assert [f.name for f in tmp_path.iterdir()] == ["804.pkl"]  # nothing half-written left

    def test_local_search_s_plan_where_its_value_is_kept(self, monkeypatch, tmp_path):
        self._patch(monkeypatch, {"status": "solved", "value": 10.0, "proved": False},
                    {"status": "solved", "value": 12.0, "used": "local search"})
        out = ws.score((None, None, [67.0], _cfg(keep_dir=tmp_path)))
        assert out["used"] == "local search" and out["value"] == 12.0
        assert "_kept" not in out and "_kept" not in out["bb"]["fallback"]
        assert ws.load_kept_plan(tmp_path, [804]).plan.name == "ls"

    def test_branch_and_bound_s_plan_where_its_value_is_kept(self, monkeypatch, tmp_path):
        self._patch(monkeypatch, {"status": "solved", "value": 10.0, "proved": False},
                    {"status": "solved", "value": 9.0, "used": "local search"})
        out = ws.score((None, None, [67.0], _cfg(keep_dir=tmp_path)))
        assert out["value"] == 10.0 and "_kept" not in out["fallback"]
        assert ws.load_kept_plan(tmp_path, [804]).plan.name == "bb"

    def test_a_cell_that_did_not_solve_keeps_nothing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ws, "_score_bb", lambda *a: {"status": "infeasible", "proved": False})
        monkeypatch.setattr(ws, "_score_ls", lambda *a: {"status": "infeasible"})
        ws.score((None, None, [67.0], _cfg(keep_dir=tmp_path)))
        assert ws.load_kept_plan(tmp_path, [804]) is None and not list(tmp_path.iterdir())

    def test_the_deposit_split_s_cells_are_not_kept(self, monkeypatch, tmp_path):
        """They share the decided cell's ages, so its file name; the check runs without the
        folder, and `score` keeps nothing for a cell with a split given."""
        self._patch(monkeypatch, {"status": "solved", "value": 10.0, "proved": True}, {})
        ws.score((None, None, [67.0], dict(_cfg(keep_dir=tmp_path), eta=1.0)))
        assert not list(tmp_path.iterdir())
        seen = []

        class Pool:
            def map(self, fn, items):
                seen.extend(cfg for *_, cfg in items)
                return [{"value": 1.0} for _ in items]

        monkeypatch.setattr(ws, "make_plan", lambda *a, **k: (types.SimpleNamespace(
            etaOptimize=False, eta=0.5, N_i=2), None))
        ws.eta_check(None, None, [804, 804], Pool(), _cfg(keep_dir=tmp_path), [0.0, 1.0], lambda m: None)
        assert len(seen) == 2 and all("keep_dir" not in cfg for cfg in seen)

    def test_without_a_folder_nothing_is_kept_and_the_cell_is_plain_data(self, monkeypatch, tmp_path):
        """The command's route: `_kept` is never set, and the cell goes to --json as before."""
        bill = _searching("examples/Case_bill.toml")
        monkeypatch.chdir(tmp_path)
        out = ws.score((*bill, [67.0], _cfg()))
        assert out["status"] == "solved" and "_kept" not in out
        json.dumps(out)
        assert not list(tmp_path.iterdir())


class TestARealSweep:
    """Case_cameron's sweep (six whole-year cells, a few seconds): every scored plan is in its
    own file, under its own ages, and is the plan its cell records."""

    @pytest.fixture(scope="class")
    @classmethod
    def swept(cls, tmp_path_factory):
        keep = tmp_path_factory.mktemp("kept")
        diconf, dirname = _searching("examples/Case_cameron.toml")
        args = types.SimpleNamespace(no_loop=True, decider="bb", gap=1e-5, max_time=ws.TIME_LIMIT,
                                     ls_time=7200.0, ls_step_time=1800.0, passes=2, eta=[], keep_dir=keep)
        row = ws.run_variant("base", diconf, dirname, args, _Serial(), lambda m: None)
        return keep, row, ws.scorer_config(args), (diconf, dirname)

    def test_one_file_per_scored_plan(self, swept):
        keep, row, _, _ = swept
        cells = row["results"].values()
        assert len(cells) > 1 and all(c["status"] == "solved" for c in cells)
        assert sorted(f.name for f in keep.iterdir()) == sorted(
            os.path.basename(ws.kept_plan_path(keep, c["ages"])) for c in cells)

    def test_each_file_holds_its_cell_s_plan(self, swept):
        keep, row, cfg, (diconf, dirname) = swept
        for cell in row["results"].values():
            kept = ws.load_kept_plan(keep, cell["ages"])
            assert list(ws.months(kept.plan.ssecAges)) == cell["ages"]
            assert kept.plan.caseStatus == "solved"
            assert kept.plan._objectiveValue(kept.plan.objective) == cell["value"]
            built, _ = ws.make_plan(diconf, dirname, [m / 12 for m in cell["ages"]])
            assert kept.options == ws.scorer_options(built, cfg, cell["used"])
            assert kept.plan.solverOptions["gap"] == 1e-5  # solved with them
            assert "SS benefits claimed at age(s)" in kept.log  # its own build and solve

    def test_the_decided_cell_s_plan_is_a_solve_again_s(self, swept):
        """What the worker used to do at the decided ages (review AH1's solve again) gives the
        plan kept there, to the cent in every exported number."""
        from owlplanner.cli.formatters import plan_to_dict
        from owlplanner.config import config_to_plan
        from owlplanner.config.schema import parse_solver_options
        from owlplanner.export import plan_metrics
        from owlplanner.library.agesearch import fixed_ages
        from owlplanner.cli.set_override import apply_overrides

        keep, row, cfg, _ = swept
        kept = ws.load_kept_plan(keep, row["best"])
        diconf, dirname = _searching("examples/Case_cameron.toml")
        again = config_to_plan(apply_overrides(diconf, fixed_ages([m / 12 for m in row["best"]])), dirname,
                               verbose=True, logstreams=[io.StringIO()], loadHFP=True)
        options = {k: v for k, v in again.solverOptions.items() if k not in ws.PRESET_KEYS}
        options.update(ws.scorer_options(again, cfg, row["result"]["used"]))
        again.solve(again.objective, parse_solver_options(options))
        assert again.caseStatus == "solved"
        assert plan_metrics(again) == plan_metrics(kept.plan)
        a, b = plan_to_dict(again), plan_to_dict(kept.plan)
        assert a.keys() == b.keys()
        assert _drop_clock(a) == 1 and _drop_clock(b) == 1  # the solve's clock (machine and load)
        assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)

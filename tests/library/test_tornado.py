"""The sensitivity tornado (design 14.1, I9): one child per key input moved by a set step,
and the effects sorted into bars with their tolerances -- `library.tornado`.

The children are ordinary runs (`variants.Variant`); these tests pin each mover's edit, the
skips ("this run buys no home", "the case already assumes it"), and `bars`' ordering and
tolerances on crafted results. The button on the Run page is checked by
`tests/ui/test_library_pages.py`."""

import types
from pathlib import Path

import numpy as np
import pytest

from owlplanner.library import ScenarioError, tornado, view
from owlplanner.library import builder as b

WORK_ARI = {"id": "work-ari", "kind": "work", "person": "Ari", "start": 2026, "end": 2026,
            "wages": 168000}
WORK_NOA = {"id": "work-noa", "kind": "work", "person": "Noa", "start": 2026, "end": 2026,
            "wages": 121000}
BUY = {"id": "buy", "kind": "purchase", "name": "yonkers condo", "price": 700000,
       "year": 2027, "pay_on": "Ari",
       "place": {"state": "NY", "locality": "Yonkers", "school_district": "City of Yonkers / Yonkers",
                 "move": False},
       "costs": {"property tax": 9500, "hoa": 9600, "insurance": 900},
       "financing": {"kind": "cash", "closing": 0.03}}


def _scenario(events=None, *, slcsp=12.0, aca_start=2027):
    return {
        "schema_version": 3, "plan_year": 2026,
        "case": {
            "basic_info": {"names": ["Ari", "Noa"], "date_of_birth": ["1964-04-17", "1964-12-09"],
                           "life_expectancy": [89, 89], "start_date": "2026-01-01"},
            "fixed_income": {"social_security_ages": [67.0, 67.0]},
            "aca_settings": {"aca_start_year": aca_start, "slcsp_annual": slcsp},
            "optimization_parameters": {"medical_inflation_excess": 1.0},
            "rates_selection": {"method": "trailing_30", "obbba_expiration_year": 2034},
            "solver_options": {"withSSAges": "fixed"},
        },
        "hfp": {},
        "events": events if events is not None else [WORK_ARI, WORK_NOA, BUY],
    }


@pytest.fixture
def stub_plan(monkeypatch):
    """The case's own rate path (`_generated_rates`): constant rates, known years."""
    monkeypatch.setattr(b, "_throwaway_plan", lambda case, rates_rows=None: types.SimpleNamespace(
        year_n=list(range(2026, 2056)),
        tau_kn=np.array([[0.06] * 30, [0.045] * 30, [0.03] * 30, [0.02] * 30])))


def _made(scenario, key):
    made, skipped = tornado.tornado_variants(scenario)
    variant = next(v for v in made if v.values.get("mover") == key)
    return variant, skipped


class TestTheMovers:
    def test_the_design_s_movers_are_all_there(self, stub_plan):
        labels = [m.label for m in tornado.movers(_scenario())]
        assert labels == [
            "returns -1 point", "inflation +1 point", "medical inflation +2 points",
            "condo price +10%", "benchmark premium +10%", "benchmark premium -10%",
            "the 2027 marketplace rules", "the 2032 reversion", "no 2032 reversion",
            "Ari dies at 80", "Noa dies at 80"]

    def test_returns_minus_one_shifts_the_run_s_own_path(self, stub_plan):
        variant, skipped = _made(_scenario(aca_start=2026), "returns -1 point")
        assert skipped == []
        assert variant.values == {"mover": "returns -1 point"}
        table = variant.scenario["rates_table"]
        assert [row[:4] for row in table["rows"][:2]] == [
            [2026, 5.0, 3.5, 2.0], [2027, 5.0, 3.5, 2.0]]  # returns down 1, inflation kept
        assert variant.scenario["case"]["rates_selection"] == {
            "method": "table", "rates_file": "rates.csv", "obbba_expiration_year": 2034}

    def test_inflation_plus_one_holds_the_real_returns(self, stub_plan):
        """Review AG3: the returns move with inflation (the same real returns), so the bar
        is inflation's own effect and not a second copy of "returns -1 point"."""
        variant, _ = _made(_scenario(), "inflation +1 point")
        assert variant.scenario["rates_table"]["rows"][0] == [2026, 7.0, 5.5, 4.0, 3.0]

    def test_the_rate_movers_bake_a_downturn_overlay_in(self, stub_plan):
        events = [WORK_ARI, WORK_NOA, BUY,
                  {"id": "stress", "kind": "downturn", "sequence": "crash-30", "start": 2030}]
        variant, _ = _made(_scenario(events), "returns -1 point")
        assert not [e for e in variant.scenario["events"] if e["kind"] == "downturn"]
        rows = {row[0]: row for row in variant.scenario["rates_table"]["rows"]}
        assert rows[2030][1] == -31.0  # crash-30's -30% year, shifted down 1 point

    def test_a_hand_table_is_shifted_and_keeps_its_case_s_transforms(self, stub_plan):
        scenario = _scenario()
        scenario["case"]["rates_selection"] = {"method": "table", "reverse_sequence": True}
        scenario["rates_table"] = {"columns": ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"],
                                   "rows": [[2026, 6.0, 4.5, 3.0, 2.0]]}
        variant, _ = _made(scenario, "returns -1 point")
        assert variant.scenario["rates_table"]["rows"] == [[2026, 5.0, 3.5, 2.0, 2.0]]
        assert variant.scenario["case"]["rates_selection"]["reverse_sequence"] is True

    def test_medical_condo_and_benchmark_premium_move_by_their_steps(self, stub_plan):
        medical, _ = _made(_scenario(), "medical inflation +2 points")
        assert medical.scenario["case"]["optimization_parameters"]["medical_inflation_excess"] == 3.0
        condo, _ = _made(_scenario(), "condo price +10%")
        buy = next(e for e in condo.scenario["events"] if e["kind"] == "purchase")
        assert buy["price"] == 770000.0
        up, _ = _made(_scenario(), "benchmark premium +10%")
        assert up.scenario["case"]["aca_settings"]["slcsp_annual"] == 13.2
        down, _ = _made(_scenario(), "benchmark premium -10%")
        assert down.scenario["case"]["aca_settings"]["slcsp_annual"] == 10.8

    def test_the_marketplace_mover_pins_the_2027_table(self, stub_plan):
        variant, _ = _made(_scenario(aca_start=2026), "the 2027 marketplace rules")
        assert variant.scenario["case"]["aca_settings"]["aca_table_year"] == 2027

    def test_the_reversion_movers_move_the_expiration_year(self, stub_plan):
        on, _ = _made(_scenario(), "the 2032 reversion")
        assert on.scenario["case"]["rates_selection"]["obbba_expiration_year"] == 2032
        off, _ = _made(_scenario(), "no 2032 reversion")
        assert off.scenario["case"]["rates_selection"]["obbba_expiration_year"] == 2100

    def test_a_reversion_the_case_already_assumes_is_skipped(self, stub_plan):
        scenario = _scenario()
        scenario["case"]["rates_selection"]["obbba_expiration_year"] = 2032
        made, skipped = tornado.tornado_variants(scenario)
        assert any("the 2032 reversion" in s and "already assumes" in s for s in skipped)
        assert any(v.values.get("mover") == "no 2032 reversion" for v in made)  # the other direction still runs

    def test_the_first_death_movers_set_the_death_event(self, stub_plan):
        variant, _ = _made(_scenario(), "Ari dies at 80")
        assert variant.values == {"mover": "Ari dies at 80"}
        assert [e for e in variant.scenario["events"] if e["kind"] == "death"] == [
            {"id": "death-ari", "kind": "death", "person": "Ari", "age": 80}]

    def test_a_death_already_past_is_skipped(self, stub_plan):
        scenario = _scenario()
        scenario["case"]["basic_info"]["date_of_birth"] = ["1944-04-17", "1964-12-09"]
        made, skipped = tornado.tornado_variants(scenario)
        assert any("Ari dies at 80" in s and "before the plan" in s for s in skipped)
        assert not any(v.values.get("mover") == "Ari dies at 80" for v in made)

    def test_a_death_that_leaves_the_plan_one_year_is_skipped(self, stub_plan):
        # Ari is 80 at the plan start (born 1946) and Noa's death event already sets her
        # horizon to the start (born 1964, dies at 62): "Ari dies at 80" would leave the
        # plan one year, so the mover is skipped with the reason (review AE1).
        scenario = _scenario([WORK_ARI, WORK_NOA,
                              {"id": "d1", "kind": "death", "person": "Noa", "age": 62}])
        scenario["case"]["basic_info"]["date_of_birth"] = ["1946-04-17", "1964-12-09"]
        made, skipped = tornado.tornado_variants(scenario)
        assert any("Ari dies at 80" in s and "one year" in s for s in skipped)
        assert not any(v.values.get("mover") == "Ari dies at 80" for v in made)

    def test_a_scenario_without_a_home_or_a_marketplace_says_why(self, stub_plan):
        scenario = _scenario([WORK_ARI, WORK_NOA], slcsp=0.0)
        made, skipped = tornado.tornado_variants(scenario)
        assert not any(v.values.get("mover") == "condo price +10%" for v in made)
        assert any("buys no home" in s for s in skipped)
        assert sum("marketplace is not in the plan" in s for s in skipped) == 3

    def test_the_children_are_scenarios_like_any_other(self, stub_plan):
        scenario = _scenario(aca_start=2026)
        made, skipped = tornado.tornado_variants(scenario)
        assert skipped == []
        for variant in made:
            assert variant.scenario is not scenario  # deep copies, the parent untouched
        from owlplanner.library import validate

        for variant in made:
            validate(variant.scenario)

    def test_a_medical_step_past_the_model_s_cap_is_refused(self, stub_plan):
        scenario = _scenario()
        scenario["case"]["optimization_parameters"]["medical_inflation_excess"] = 9.5
        with pytest.raises(ScenarioError, match="caps it at 10"):
            next(m for m in tornado.movers(scenario) if m.key == "medical+2").edit(scenario)


class TestBars:
    EXACT = {"breakpointMethod": "loop", "withMedicare": "none", "withSSTaxability": 0.85,
             "withLTCG": "optimize", "withSSAges": "fixed"}

    def _result(self, score_value, gap=None, method="loop", exact=True):
        options = dict(self.EXACT) if exact else {"breakpointMethod": "local-search"}
        record = {"status": "solved", "preset": "decision_exact" if exact else "decision",
                  "gap": gap,
                  "method": {"breakpoint_method": method, "options": options,
                             "objective": "maxSpending"},
                  "convergence": {"objective_error_bar_today_dollars": 0.0},
                  "solve_date": {"finished": "2026-01-01T00:00:00"}}
        summary = {"discretionary_year1": score_value,
                   "final_bequest_today": 400_000.0, "final_bequest_savings_today": 0.0}
        plan = {"objective": "maxSpending", "by_year": []}
        return view.Result(results_id="r", results_dir=Path("."), record=record,
                           summary=summary, plan=plan)

    def test_bars_are_sorted_by_the_size_of_the_effect(self):
        base = self._result(100_000.0)
        rows = [("small", self._result(99_000.0)), ("big", self._result(80_000.0)),
                ("none", None), ("other", self._result(112_000.0))]
        bars = tornado.bars(base, rows)
        assert [b["label"] for b in bars] == ["big", "other", "small", "none"]
        assert bars[0]["delta"] == -20_000.0 and bars[-1]["delta"] is None

    def test_each_bar_carries_its_tolerance_and_verdict(self):
        base = self._result(100_000.0)
        bars = tornado.bars(base, [("in the band", self._result(99_500.0)),
                                   ("resolved", self._result(80_000.0))])
        noise = next(b for b in bars if b["label"] == "in the band")
        assert noise["verdict"] == "within noise" and noise["tolerance"] == pytest.approx(1_000.0)
        resolved = next(b for b in bars if b["label"] == "resolved")
        assert resolved["verdict"] == "resolved" and resolved["tolerance"] == pytest.approx(1_000.0)

    def test_a_bar_without_a_result_is_listed_last(self):
        bars = tornado.bars(self._result(100_000.0), [("gone", None)])
        assert bars == [{"label": "gone", "delta": None, "tolerance": None, "verdict": "-",
                         "note": "no exact-LP result yet", "result": None}]


class TestReview3Fixes:
    """`fork-notes/run-library-step6-review-3.md` AG1-AG4 and AG9 (AG8 not folded). Each test
    was checked to fail before the fix it names."""

    DECIMAL = {"method": "table", "rates_file": "rates.csv", "in_percent": False}
    COLUMNS = ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"]

    def _decimal(self):
        scenario = _scenario()
        scenario["case"]["rates_selection"] = dict(self.DECIMAL)
        scenario["rates_table"] = {"columns": list(self.COLUMNS),
                                   "rows": [[2026, 0.06, 0.045, 0.03, 0.02]]}
        return scenario

    def test_ag1_a_decimal_table_moves_by_one_point_not_one_hundred(self, stub_plan):
        down, _ = _made(self._decimal(), "returns -1 point")
        assert down.scenario["rates_table"]["rows"] == [[2026, 0.05, 0.035, 0.02, 0.02]]
        assert down.scenario["case"]["rates_selection"]["in_percent"] is False
        up, _ = _made(self._decimal(), "inflation +1 point")
        assert up.scenario["rates_table"]["rows"] == [[2026, 0.07, 0.055, 0.04, 0.03]]

    def test_ag1_a_generated_path_is_written_in_percent(self, stub_plan):
        scenario = _scenario()
        scenario["case"]["rates_selection"]["in_percent"] = False  # a stray key, no table
        variant, _ = _made(scenario, "returns -1 point")
        assert variant.scenario["rates_table"]["rows"][0][:4] == [2026, 5.0, 3.5, 2.0]
        assert "in_percent" not in variant.scenario["case"]["rates_selection"]

    def test_ag4_the_marketplace_rules_are_skipped_when_coverage_starts_in_2027(self, stub_plan):
        made, skipped = tornado.tornado_variants(_scenario(aca_start=2027))
        assert not any(v.values["mover"] == "the 2027 marketplace rules" for v in made)
        assert any(s.startswith("the 2027 marketplace rules") and "no plan year would change" in s
                   for s in skipped)

    def test_ag4_a_reversion_year_past_the_plan_s_end_is_skipped(self, stub_plan):
        scenario = _scenario()
        scenario["case"]["rates_selection"]["obbba_expiration_year"] = 2066  # the template's
        made, skipped = tornado.tornado_variants(scenario)
        movers = [v.values["mover"] for v in made]
        assert "no 2032 reversion" not in movers  # 2066 -> 2100: the plan ends in 2053
        assert "the 2032 reversion" in movers
        assert any(s.startswith("no 2032 reversion") and "2026-2053" in s for s in skipped)

    def test_ag4_a_death_the_case_already_has_is_skipped(self, stub_plan):
        scenario = _scenario()
        scenario["case"]["basic_info"]["life_expectancy"] = [80, 89]
        made, skipped = tornado.tornado_variants(scenario)
        assert not any(v.values["mover"] == "Ari dies at 80" for v in made)
        assert any("already has Ari die at 80" in s for s in skipped)

    def test_ag9_the_children_s_names_keep_the_mover_s_sign(self, stub_plan):
        made, _ = tornado.tornado_variants(_scenario(aca_start=2026))
        labels = [v.label for v in made]
        assert len(labels) == len(set(labels))
        assert {"slcsp+10", "slcsp-10", "inflation+1", "returns-1"} <= set(labels)


class TestReview3Bars:
    """Review AG2: the bars measure exact-LP results against the run's own exact-LP result."""

    _result = TestBars._result
    EXACT = TestBars.EXACT

    def test_ag2_a_base_from_another_model_makes_every_bar_wait(self):
        base = self._result(111_500.0, exact=False)  # a quick/custom/ages result
        bars = tornado.bars(base, [("returns -1 point", self._result(108_970.0))])
        assert bars[0]["delta"] is None and bars[0]["note"] == tornado.WAITING_FOR_BASE

    def test_ag2_a_child_from_another_model_is_not_a_bar(self):
        bars = tornado.bars(self._result(116_034.0),
                            [("re-run by hand", self._result(108_000.0, exact=False)),
                             ("returns -1 point", self._result(108_970.0))])
        by = {b["label"]: b for b in bars}
        assert by["returns -1 point"]["delta"] == pytest.approx(-7_064.0)
        assert by["re-run by hand"]["delta"] is None
        assert by["re-run by hand"]["note"] == "no exact-LP result yet"

    def test_ag2_the_flags_name_children_at_other_claiming_ages(self):
        base = self._result(116_034.0)
        base.plan.update({"individuals": ["Ari", "Noa"], "claiming_ages": [67.0, 67.0]})
        child = self._result(108_970.0)
        child.plan.update({"individuals": ["Ari", "Noa"], "claiming_ages": [70.0, 67.0]})
        flags = tornado.bar_flags(base, [("returns -1 point", child)])
        assert any("claiming ages other than the reference's" in f for f in flags)
        assert tornado.bar_flags(None, [("x", child)]) == []

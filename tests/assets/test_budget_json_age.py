"""Age clocks on budget lines and the JSON budget-file interchange."""

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from owlplanner import budget
from owlplanner.hfp_io import conditionDebtsAndFixedAssetsDF

THISYEAR = 2026
COLS = list(budget.SHEET_COLUMNS)


def _line(**kw):
    base = {
        "active": True,
        "name": "l",
        "type": "core",
        "year": THISYEAR,
        "end": 0,
        "amount": 12000.0,
        "rate": 0.0,
        "survivor": np.nan,
        "essential": False,
        "clock": "",
        "start_age": np.nan,
        "end_age": np.nan,
        "index": "",
    }
    base.update(kw)
    return base


def _df(*lines):
    return conditionDebtsAndFixedAssetsDF(pd.DataFrame(list(lines), columns=COLS), "Budget")


def _ages(younger0=60.0, older0=62.0, N_n=8):
    # Row 0 is the younger spouse (born later): age at the plan's end is larger.
    younger = younger0 + np.arange(N_n)
    older = older0 + np.arange(N_n)
    return np.vstack([younger, older])


# ---------------------------------------------------------------------------
# age clocks
# ---------------------------------------------------------------------------


class TestAgeClock:
    def test_age_window_is_inclusive(self):
        line = _line(clock="age", start_age=62, end_age=64, amount=1000.0, year=0, end=0)
        ages = _ages(younger0=60.0, N_n=8)  # ages 60..67
        b = budget.evaluate(_df(line), 8, 8, 60, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert list(b.total_n) == [0, 0, 1000.0, 1000.0, 1000.0, 0, 0, 0]

    def test_index_older_uses_the_other_spouse(self):
        line = _line(clock="age", start_age=62, end_age=63, amount=1000.0, index="older", year=0, end=0)
        # younger 60..67, older 62..69 -> older is 62,63 in plan years 0,1
        ages = _ages(younger0=60.0, older0=62.0, N_n=8)
        b = budget.evaluate(_df(line), 8, 8, 60, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert list(b.total_n) == [1000.0, 1000.0, 0, 0, 0, 0, 0, 0]

    def test_index_by_name(self):
        line = _line(clock="age", start_age=64, end_age=64, amount=1000.0, index="b", year=0, end=0)
        ages = _ages(younger0=60.0, older0=62.0, N_n=8)  # B is row 1: 62..69, age 64 in year 2
        b = budget.evaluate(_df(line), 8, 8, 60, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert list(b.total_n) == [0, 0, 1000.0, 0, 0, 0, 0, 0]

    def test_growth_counts_from_the_first_active_year(self):
        line = _line(clock="age", start_age=62, end_age=63, amount=1000.0, rate=10.0, year=0, end=0)
        ages = _ages(younger0=61.0, N_n=4)  # 61,62,63,64 -> active years 1,2
        b = budget.evaluate(_df(line), 4, 4, 60, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert list(b.total_n) == [0, 1000.0, 1100.0, 0]

    def test_age_before_plan_starts_clips_and_grows_from_plan_start(self):
        # Already past start_age at plan start: pays from year 0, growth from year 0.
        line = _line(clock="age", start_age=50, end_age=62, amount=1000.0, rate=5.0, year=0, end=0)
        ages = _ages(younger0=60.0, N_n=3)  # 60,61,62
        b = budget.evaluate(_df(line), 3, 3, 60, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert list(b.total_n) == pytest.approx([1000.0, 1050.0, 1102.5])

    def test_never_applies_is_left_out(self):
        line = _line(clock="age", start_age=80, end_age=85, year=0, end=0)
        ages = _ages(younger0=60.0, N_n=5)
        b = budget.evaluate(_df(line), 5, 5, 60, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert np.all(b.total_n == 0)
        left = budget.lines_left_out(_df(line), 5, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert left and "age range" in left[0][1]

    def test_unknown_clock_is_a_refusal(self):
        line = _line(clock="phase of the moon", year=0, end=0)
        ages = _ages(N_n=4)
        with pytest.raises(ValueError, match="clock"):
            budget.evaluate(_df(line), 4, 4, 60, THISYEAR, ages_in=ages, inames=["A", "B"])

    def test_age_clock_without_ages_is_a_refusal(self):
        line = _line(clock="age", start_age=62, end_age=64, year=0, end=0)
        with pytest.raises(ValueError, match="ages"):
            budget.evaluate(_df(line), 4, 4, 60, THISYEAR)

    def test_unknown_index_is_a_refusal(self):
        line = _line(clock="age", start_age=62, end_age=64, index="nobody", year=0, end=0)
        ages = _ages(N_n=4)
        with pytest.raises(ValueError, match="index"):
            budget.evaluate(_df(line), 4, 4, 60, THISYEAR, ages_in=ages, inames=["A", "B"])

    def test_survivor_still_applies_to_age_lines(self):
        line = _line(clock="age", start_age=60, end_age=65, amount=1000.0, survivor=50.0, year=0, end=0)
        ages = _ages(younger0=60.0, N_n=6)
        b = budget.evaluate(_df(line), 6, 3, 60, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert list(b.total_n) == [1000.0, 1000.0, 1000.0, 500.0, 500.0, 500.0]

    def test_calendar_lines_ignore_the_age_clock(self):
        line = _line(amount=1000.0, clock="", start_age=1, end_age=2)
        b = budget.evaluate(_df(line), 3, 3, 60, THISYEAR, ages_in=_ages(N_n=3), inames=["A", "B"])
        assert list(b.total_n) == [1000.0, 1000.0, 1000.0]


# ---------------------------------------------------------------------------
# JSON interchange
# ---------------------------------------------------------------------------


class TestJson:
    def test_round_trip_matches_the_sheet(self):
        obj = {
            "schema_version": 1,
            "lines": [
                {"name": "core", "type": "core", "year": THISYEAR, "end": 0, "amount": 50.0,
                 "rate": 0.0, "survivor": 60, "essential": True},
                {"name": "travel", "kind": "travel", "clock": "age", "start_age": 62, "end_age": 64,
                 "amount": 12.0, "rate": -1.0, "survivor": 30},
            ],
        }
        df = budget.df_from_json_obj(obj)
        ages = _ages(younger0=60.0, N_n=6)
        b = budget.evaluate(df, 6, 6, 60, THISYEAR, ages_in=ages, inames=["A", "B"])
        assert b.names == ("core", "travel")
        assert b.types == ("core", "travel")
        # core 50 every year; travel at ages 62-64 (years 2-4), 12 growing at -1%/yr
        assert list(b.total_n) == pytest.approx([50.0, 50.0, 62.0, 50.0 + 12 * 0.99, 50.0 + 12 * 0.99**2, 50.0])
        assert b.essential == (True, False)

    def test_start_year_end_year_aliases(self):
        obj = {
            "schema_version": 1,
            "lines": [{"name": "x", "type": "core", "start_year": THISYEAR, "end_year": THISYEAR,
                       "amount": 1.0}],
        }
        df = budget.df_from_json_obj(obj)
        b = budget.evaluate(df, 3, 3, 60, THISYEAR)
        assert list(b.total_n) == [1.0, 0, 0]

    def test_kind_maps_to_type(self):
        df = budget.df_from_json_obj(
            {"schema_version": 1, "lines": [{"name": "r", "kind": "rent", "amount": 1.0}]}
        )
        assert df.loc[0, "type"] == "rent"

    def test_unknown_schema_version_refused(self):
        with pytest.raises(ValueError, match="schema_version"):
            budget.df_from_json_obj({"schema_version": 99, "lines": []})

    def test_unknown_top_level_field_refused(self):
        with pytest.raises(ValueError, match="unknown fields"):
            budget.df_from_json_obj({"schema_version": 1, "lines": [], "oops": 1})

    def test_unknown_line_field_refused(self):
        with pytest.raises(ValueError, match="unknown fields"):
            budget.df_from_json_obj(
                {"schema_version": 1, "lines": [{"name": "x", "type": "core", "amount": 1.0, "colour": "red"}]}
            )

    def test_missing_amount_refused(self):
        with pytest.raises(ValueError, match="amount"):
            budget.df_from_json_obj({"schema_version": 1, "lines": [{"name": "x", "type": "core"}]})

    def test_age_line_without_ages_refused(self):
        with pytest.raises(ValueError, match="start_age"):
            budget.df_from_json_obj(
                {"schema_version": 1,
                 "lines": [{"name": "x", "type": "care", "amount": 1.0, "clock": "age"}]}
            )

    def test_load_json_from_file(self, tmp_path: Path):
        path = tmp_path / "profile.json"
        path.write_text(
            json.dumps({"schema_version": 1, "lines": [{"name": "c", "type": "core", "amount": 3.0}]}),
            encoding="utf-8",
        )
        df = budget.load_json(path)
        assert df.loc[0, "amount"] == 3.0

    def test_bad_json_is_a_clear_error(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ValueError, match="not valid JSON"):
            budget.load_json(path)


# ---------------------------------------------------------------------------
# Plan / config wiring
# ---------------------------------------------------------------------------


def _budget_file(tmp_path: Path) -> Path:
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lines": [
                    {"name": "core", "type": "core", "amount": 50.0, "survivor": 60},
                    {"name": "travel", "type": "travel", "clock": "age", "start_age": 62, "end_age": 64,
                     "amount": 10.0},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_config_budget_file_feeds_the_plan(tmp_path: Path):
    from owlplanner.config import config_to_plan, default_config, plan_to_config

    path = _budget_file(tmp_path)
    diconf = default_config(ni=2)
    diconf["case_name"] = "json-budget"
    diconf["basic_info"]["names"] = ["A", "B"]
    diconf["basic_info"]["date_of_birth"] = ["1964-01-01", "1962-01-01"]
    diconf["basic_info"]["life_expectancy"] = [90, 92]
    diconf["optimization_parameters"]["spending_profile"] = "budget"
    diconf["optimization_parameters"]["budget_file"] = str(path)
    p = config_to_plan(diconf, dirname=str(tmp_path), verbose=False, logstreams=[io.StringIO()])
    assert p.budgetFileName == str(path)
    assert p.houseLists["Budget"] is not None
    p._evaluateBudget()
    assert p.budget.names == ("core", "travel")
    # A is younger (born 1964): at THISYEAR=plan start they are ~62, so travel is active early.
    assert p.budget.total_n[0] == pytest.approx(60.0)
    # Round-trip keeps the path.
    out = plan_to_config(p)
    assert out["optimization_parameters"]["budget_file"] == str(path)


def test_budget_sheet_wins_over_the_json_file(tmp_path: Path):
    from owlplanner.config import config_to_plan, default_config
    from owlplanner.config.plan_bridge import _load_budget_file

    path = _budget_file(tmp_path)
    diconf = default_config(ni=1)
    diconf["case_name"] = "both"
    diconf["basic_info"]["names"] = ["A"]
    diconf["optimization_parameters"]["spending_profile"] = "budget"
    diconf["optimization_parameters"]["budget_file"] = str(path)
    p = config_to_plan(diconf, dirname=str(tmp_path), verbose=False, logstreams=[io.StringIO()])
    p.houseLists["Budget"] = _df(_line(name="from-sheet", type="core", amount=99.0))
    # Re-apply: the sheet already has lines, so the file must not overwrite them.
    _load_budget_file(p, diconf, str(tmp_path))
    assert list(p.houseLists["Budget"]["name"]) == ["from-sheet"]


def test_age_lines_survive_clone_with_a_longer_horizon(tmp_path: Path):
    from owlplanner import clone
    from owlplanner.config import config_to_plan, default_config

    path = _budget_file(tmp_path)
    diconf = default_config(ni=2)
    diconf["case_name"] = "clone-age"
    diconf["basic_info"]["names"] = ["A", "B"]
    diconf["basic_info"]["date_of_birth"] = ["1964-01-01", "1962-01-01"]
    diconf["basic_info"]["life_expectancy"] = [85, 87]
    diconf["optimization_parameters"]["spending_profile"] = "budget"
    diconf["optimization_parameters"]["budget_file"] = str(path)
    p = config_to_plan(diconf, dirname=str(tmp_path), verbose=False, logstreams=[io.StringIO()])
    p._evaluateBudget()
    n_short = int(np.sum(p.budget.by_type("travel") > 0))
    c = clone(p, expectancy=[95, 97], verbose=False, logstreams=[io.StringIO()])
    c._evaluateBudget()
    # A longer life cannot drop age-tied lines that were already active.
    assert c.budget.names == p.budget.names
    assert np.sum(c.budget.by_type("travel") > 0) >= n_short

"""The `table` rate method (step 5b, D11): a year-by-year rates CSV the case file names.

Covers:
- reading rows by the `year` column (any order), percent units, extra columns ignored;
- the errors a bad or short table gives (missing years named, duplicates, missing columns);
- `rows` in memory in place of the file, and the file resolved beside the case (`base_dir`);
- the TOML round trip: only `rates_file` (and `in_percent`) reach the case file;
- `Plan.setRates("table", ...)`: the plan's own years, the `_config_dir` resolution and the
  in-memory fallback when the file cannot be re-read (its twin: a changed file is re-read);
- hostile input (review Z5/Z6): no `rates_file` names what is missing, an Excel byte-order
  mark is read, and `nan` / `inf` cells are refused by year and column.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

###########################################################################
import numpy as np
import pytest

from owlplanner.rate_models.loader import load_rate_model
from owlplanner.rate_models.table import TableRateModel, read_rates_csv

CSV_TEXT = (
    "year,S&P 500,Bonds Baa,T-Notes,Inflation\n"
    "2026,7.0,4.5,3.0,2.5\n"
    "2027,-30.0,2.0,1.0,2.0\n"
    "2028,5.5,4.0,2.8,2.2\n"
)

ROWS = [[2026, 7.0, 4.5, 3.0, 2.5], [2027, -30.0, 2.0, 1.0, 2.0], [2028, 5.5, 4.0, 2.8, 2.2]]


def _write(tmp_path, text=CSV_TEXT, name="rates.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _model(tmp_path=None, **params):
    config = {"method": "table", "start_year": 2026, "rates_file": "rates.csv"}
    config.update(params)
    if tmp_path is not None:
        config.setdefault("base_dir", str(tmp_path))
    return TableRateModel(config=config)


# ---- identity and discovery -------------------------------------------


def test_registered_under_table():
    assert load_rate_model("table") is TableRateModel


def test_deterministic_but_not_constant():
    model = _model(rows=ROWS)
    assert model.deterministic is True
    assert model.constant is False


# ---- reading the table -------------------------------------------------


def test_rows_are_matched_to_years():
    data = _model(rows=ROWS).generate(3)
    assert data.shape == (3, 4)
    assert data[1][0] == pytest.approx(-0.30)  # percent in, decimal out
    assert data[0][3] == pytest.approx(0.025)


def test_rows_may_come_in_any_order():
    data = _model(rows=list(reversed(ROWS))).generate(3)
    assert data[1][0] == pytest.approx(-0.30)


def test_in_percent_false_keeps_the_values():
    data = _model(rows=ROWS, in_percent=False).generate(3)
    assert data[0][0] == pytest.approx(7.0)


def test_the_file_is_read_when_no_rows_are_given(tmp_path):
    _write(tmp_path)
    data = _model(tmp_path).generate(3)
    assert data[1][0] == pytest.approx(-0.30)


def test_the_file_is_resolved_beside_the_case(tmp_path):
    _write(tmp_path)
    model = TableRateModel(config={"method": "table", "rates_file": "rates.csv",
                                   "base_dir": str(tmp_path), "start_year": 2026})
    assert model.generate(3)[0][0] == pytest.approx(0.07)


def test_extra_columns_are_ignored(tmp_path):
    _write(tmp_path, (
        "year,S&P 500,Bonds Baa,real estate,T-Bills,T-Notes,Inflation\n"
        "2026,7.0,4.5,1.0,3.0,3.0,2.5\n"
        "2027,-30.0,2.0,1.0,3.0,1.0,2.0\n"
        "2028,5.5,4.0,1.0,3.0,2.8,2.2\n"
    ))
    assert _model(tmp_path).generate(3)[1][0] == pytest.approx(-0.30)


def test_read_rates_csv_gives_numbers(tmp_path):
    assert read_rates_csv(_write(tmp_path)) == ROWS


# ---- errors ------------------------------------------------------------


def test_missing_years_are_named(tmp_path):
    _write(tmp_path, CSV_TEXT + "2029,1.0,1.0,1.0,1.0\n")
    with pytest.raises(ValueError, match="no row for 2030, 2031"):
        _model(tmp_path, start_year=2029).generate(4)


def test_a_duplicate_year_is_an_error():
    with pytest.raises(ValueError, match="two rows for 2027"):
        _model(rows=ROWS + [[2027, 1.0, 1.0, 1.0, 1.0]]).generate(3)


def test_missing_columns_are_an_error(tmp_path):
    _write(tmp_path, "year,S&P 500,Inflation\n2026,7.0,2.5\n")
    with pytest.raises(ValueError, match="missing the column"):
        _model(tmp_path).generate(1)


def test_a_missing_file_names_where_it_looked(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        _model(tmp_path).generate(1)


def test_start_year_is_required():
    model = TableRateModel(config={"method": "table", "rates_file": "rates.csv", "rows": ROWS})
    with pytest.raises(ValueError, match="start_year"):
        model.generate(1)


def test_a_bad_row_is_named():
    with pytest.raises(ValueError, match="row 2"):
        _model(rows=[ROWS[0], [2027, "x", 1.0, 1.0, 1.0]]).generate(2)


# ---- hostile input (review Z5/Z6) -------------------------------------


def test_no_rates_file_names_what_is_missing():
    with pytest.raises(ValueError, match="needs a 'rates_file'"):
        TableRateModel.from_config({"method": "table"})


def test_a_blank_rates_file_names_what_is_missing():
    with pytest.raises(ValueError, match="needs a 'rates_file'"):
        TableRateModel.from_config({"method": "table", "rates_file": "   "})


def test_the_case_path_names_a_missing_rates_file():
    """Review Z5: `config_to_plan` refuses by name, not with a bare `KeyError: 'rates_file'`."""
    from owlplanner.config import config_to_plan, load_toml

    case, dirname, _ = load_toml(CASE)
    case["rates_selection"] = {"method": "table"}
    with pytest.raises(ValueError, match="needs a 'rates_file'"):
        config_to_plan(case, dirname, verbose=False, loadHFP=False)


def test_a_byte_order_mark_is_read(tmp_path):
    """Excel's "CSV UTF-8" writes a BOM; the header still reads `year` (review Z6)."""
    assert read_rates_csv(_write(tmp_path, "\ufeff" + CSV_TEXT)) == ROWS


@pytest.mark.parametrize("bad", ["nan", "inf", "1e999"])
def test_a_non_finite_cell_is_named(tmp_path, bad):
    with pytest.raises(ValueError, match="row 2029, column 'S&P 500' is not a finite number"):
        read_rates_csv(_write(tmp_path, CSV_TEXT + f"2029,{bad},1.0,1.0,1.0\n"))


def test_a_non_finite_cell_somewhere_else_is_named(tmp_path):
    with pytest.raises(ValueError, match="row 2029, column 'T-Notes' is not a finite number"):
        read_rates_csv(_write(tmp_path, CSV_TEXT + "2029,1.0,1.0,inf,1.0\n"))


def test_unknown_parameters_are_rejected():
    with pytest.raises(ValueError, match="Unknown parameter"):
        TableRateModel(config={"method": "table", "rates_file": "r.csv", "seeds": 1})


# ---- the TOML round trip ----------------------------------------------


def test_config_round_trip_keeps_only_the_file_name():
    model = _model(rows=ROWS, base_dir="somewhere", in_percent=False)
    section = TableRateModel.to_config(**model.params)
    assert section == {"rates_file": "rates.csv", "in_percent": False}
    back = TableRateModel.from_config({**section, "method": "table", "base_dir": "other",
                                       "start_year": 2030, "rows": ROWS})
    assert back == {"rates_file": "rates.csv", "in_percent": False}


# ---- through Plan.setRates --------------------------------------------


CASE = str(__import__("pathlib").Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml")


def _long_csv(tmp_path, first=2026, last=2070, crash=-30.0):
    """A table that covers any plan horizon this file's plans can ask for."""
    lines = ["year,S&P 500,Bonds Baa,T-Notes,Inflation"]
    for year in range(first, last + 1):
        rates = [crash, 2.0, 1.0, 2.0] if year == 2027 else [7.0, 4.5, 3.0, 2.5]
        lines.append(",".join(str(v) for v in [year, *rates]))
    _write(tmp_path, "\n".join(lines) + "\n")


def _plan():
    from owlplanner.config import config_to_plan, load_toml

    case, dirname, _ = load_toml(CASE)
    return config_to_plan(case, dirname, verbose=False, loadHFP=False)


def test_the_plan_reads_its_own_years(tmp_path):
    _long_csv(tmp_path)
    plan = _plan()
    plan._config_dir = str(tmp_path)
    plan.setRates("table", rates_file="rates.csv")
    assert plan.rateMethod == "table"
    assert plan.tau_kn[0, 1] == pytest.approx(-0.30)
    assert int(plan.year_n[0]) == 2026


def test_a_plan_that_cannot_re_read_the_file_reuses_its_rows(tmp_path):
    _long_csv(tmp_path)
    plan = _plan()
    plan._config_dir = str(tmp_path)
    plan.setRates("table", rates_file="rates.csv")
    plan._config_dir = str(tmp_path / "gone")  # the run folder moved away
    plan.setRates("table", rates_file="rates.csv")
    assert plan.tau_kn[0, 1] == pytest.approx(-0.30)


def test_a_changed_file_is_re_read(tmp_path):
    """That test's twin (review Z1): the file wins whenever it can be read, so a hand-edited
    `rates.csv` reaches a plan that has already read the table (the interface's re-solve)."""
    _long_csv(tmp_path)
    plan = _plan()
    plan._config_dir = str(tmp_path)
    plan.setRates("table", rates_file="rates.csv")
    assert plan.tau_kn[0, 1] == pytest.approx(-0.30)
    _long_csv(tmp_path, crash=-55.0)  # the user edits rates.csv
    plan.setRates("table", rates_file="rates.csv")
    assert plan.tau_kn[0, 1] == pytest.approx(-0.55)


def test_a_clone_with_a_new_expectancy_keeps_the_table(tmp_path):
    from owlplanner.config.plan_bridge import clone

    _long_csv(tmp_path)
    plan = _plan()
    plan._config_dir = str(tmp_path)
    plan.setRates("table", rates_file="rates.csv")
    longer = clone(plan, expectancy=[83, 83])
    assert np.allclose(longer.tau_kn[:, :3], plan.tau_kn[:, :3])

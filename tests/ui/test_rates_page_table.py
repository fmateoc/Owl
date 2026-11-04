"""The pages on a rates-table case (run-library step 5b, third review AB2 and AB4).

- AB2: the Rates page re-applies the table once per case (`initRates` -> `owlbridge._setRates`);
  it must use the case's own units (`in_percent`) and sequence options, as a solve does, or a
  decimal table is shown and held 100x too small until the next solve.
- AB4: an uploaded case file cannot bring its rates CSV along; the Create Case error must say
  where the case can be opened instead.
"""

import copy
import io
from pathlib import Path

import pytest

import owlbridge  # the bare module name the pages bind

from owlplanner.config import config_to_plan, load_toml
from owlplanner.config.toml_io import save_toml
from owlplanner.config.ui_bridge import config_to_ui

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
CASE = str(Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml")


def _table_case(tmp_path, *, value, selection):
    """A jack+jill case whose rates come from a rates.csv beside it (constant rows)."""
    case, _, _ = load_toml(CASE)
    case["rates_selection"] = {"method": "table", "rates_file": "rates.csv", **selection}
    case["household_financial_profile"]["HFP_file_name"] = "None"
    path = tmp_path / "Case_table.toml"
    save_toml(case, str(path))
    rows = "".join(f"{y},{value(y)},0.045,0.03,0.025\n" for y in range(2020, 2080))
    (tmp_path / "rates.csv").write_text("year,S&P 500,Bonds Baa,T-Notes,Inflation\n" + rows,
                                        encoding="utf-8")
    return path


def _visit(case_path):
    """Render the Rates page on the case; (the page, the session plan after the visit)."""
    from streamlit.testing.v1 import AppTest

    case, dirname, _ = load_toml(str(case_path))
    plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=False)
    dic = config_to_ui(copy.deepcopy(case))
    dic.update({"plan": plan, "name": "t", "caseStatus": "modified", "logs": io.StringIO()})
    at = AppTest.from_file(str(UI_DIR / "Rates.py"), default_timeout=60)
    at.session_state["cases"] = {"t": dic}
    at.session_state["currentCase"] = "t"
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at, at.session_state["cases"]["t"]["plan"]


def test_ab2_a_decimal_table_keeps_its_units_on_the_rates_page(tmp_path):
    """Without the fix: shown 0.06 (percent) and held 0.0006 after the visit."""
    at, plan = _visit(_table_case(tmp_path, value=lambda y: 0.06, selection={"in_percent": False}))
    assert float(plan.tau_kn[0, 0]) == pytest.approx(0.06)
    assert at.dataframe[0].value.iloc[0]["S&P 500"] == pytest.approx(6.0)


def test_ab2_the_sequence_options_survive_the_rates_page(tmp_path):
    """A reversed table is held and shown reversed, as a solve applies it."""
    at, plan = _visit(_table_case(tmp_path, value=lambda y: float(y - 2000),
                                  selection={"reverse_sequence": True}))
    last = int(plan.year_n[-1])  # reversed: the plan's first year holds the last year's row
    assert 100 * float(plan.tau_kn[0, 0]) == pytest.approx(float(last - 2000))
    assert at.dataframe[0].value.iloc[0]["S&P 500"] == pytest.approx(float(last - 2000))


def test_ab4_an_uploaded_table_case_says_where_to_open_it(tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(owlbridge.st, "error", lambda msg, **kw: errors.append(msg))
    text = _table_case(tmp_path, value=lambda y: 6.0, selection={}).read_text(encoding="utf-8")
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)  # no rates.csv in the working directory
    name, dic = owlbridge.createCaseFromFile(io.StringIO(text))
    assert (name, dic) == ("", {})
    assert len(errors) == 1 and "not found" in errors[0]
    assert "Import a case" in errors[0] and "owlcli run" in errors[0]


def test_ab4_other_upload_errors_carry_no_rates_hint(monkeypatch):
    errors = []
    monkeypatch.setattr(owlbridge.st, "error", lambda msg, **kw: errors.append(msg))
    owlbridge.createCaseFromFile(io.StringIO("this is not toml = = ="))
    assert len(errors) == 1 and "Import a case" not in errors[0]

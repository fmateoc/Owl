"""
The Budget editor on the Financial Profile page (run-library step 5).

Until here the Budget lines arrived only in an uploaded workbook: `Financial_Profile.py` had
editors for Debts and Fixed Assets and none for the Budget sheet. AppTest does not surface
`st.data_editor` elements, so the edit loop itself is not driven from a test; what is tested
is everything around it: the column help covers the sheet's columns, the model's own "adds
nothing" checks are reported next to the table, a restored run keeps its tables instead of
zeroing them, and a table edited in the pages reaches the plan, the workbook and a run saved
to the library.

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

import ast
import copy
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from owlplanner import readConfig
from owlplanner.hfp_io import _budgetItems
from owlplanner.config import config_to_plan, config_to_ui, load_toml

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
JACK = EXAMPLES / "Case_jack+jill.toml"
THISYEAR = date.today().year


def _rows(*rows):
    """A Budget table as the editor holds it: the sheet's columns in order."""
    return pd.DataFrame([list(r) for r in rows], columns=_budgetItems)


def _render(monkeypatch, case):
    """Render Financial_Profile.py around a prepared case dictionary."""
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
    at = AppTest.from_file(str(UI_DIR / "Financial_Profile.py"), default_timeout=120)
    at.session_state["cases"] = {"t": case}
    at.session_state["currentCase"] = "t"
    at.run()
    return at


def _case_with_plan(monkeypatch, case_file=JACK):
    """A case dict as "Open in Owl" leaves it: the plan carries the tables, the keys do not."""
    import owlbridge as owb

    plan = readConfig(str(case_file), verbose=False)
    _, dic = owb.openCaseFromPlan(plan)
    dic["name"] = "t"
    dic["id"] = "t1"
    return plan, dic


class TestBudgetHelp:
    def _help_dict(self):
        tree = ast.parse((UI_DIR / "Financial_Profile.py").read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "budgetHelp":
                return ast.literal_eval(node.value)
        raise AssertionError("budgetHelp not found in Financial_Profile.py")

    def test_every_budget_column_has_bubble_help(self):
        """As for the timetables: a column without a tooltip would render bare, and nothing
        else in the suite would notice."""
        from owlplanner.budget import SHEET_COLUMNS

        helpdic = self._help_dict()
        assert set(helpdic) == set(SHEET_COLUMNS)
        assert all(helpdic.values()), helpdic


class TestBudgetWarnings:
    """`checkBudgetRows`: the model's own `budget.lines_left_out`, next to the table."""

    @pytest.fixture
    def rows(self, monkeypatch):
        plan = readConfig(str(JACK), verbose=False)
        import owlbridge as owb
        import sskeys as kz

        monkeypatch.setattr(kz, "getCaseKey", {"plan": plan}.get)
        return owb.checkBudgetRows

    def test_a_line_that_ends_before_it_starts(self, rows):
        df = _rows((True, "short", "core", 2031, 2030, 10_000.0, 0.0, None, False, None, None, None, None, None))
        msgs = rows(df)
        assert len(msgs) == 1 and "Budget line 'short'" in msgs[0] and "before it starts" in msgs[0]

    def test_an_age_clock_without_its_ages(self, rows):
        df = _rows((True, "aged", "travel", 0, 0, 10_000.0, 0.0, None, False, "age", 62.0, None, "younger", None))
        msgs = rows(df)
        assert len(msgs) == 1 and "Budget line 'aged'" in msgs[0] and "start_age" in msgs[0]

    def test_an_index_that_names_nobody(self, rows):
        df = _rows((True, "personal", "care", 0, 0, 10_000.0, 0.0, None, True, "age", 80.0, 90.0, "nobody", None))
        msgs = rows(df)
        assert len(msgs) == 1 and "unknown index" in msgs[0]

    def test_a_line_that_pays_is_not_reported(self, rows):
        df = _rows((True, "core", "core", THISYEAR, 0, 72_000.0, 0.0, None, True, None, None, None, None, None))
        assert rows(df) == []


class TestThePageShowsTheTable:
    def test_the_section_renders_with_lines_and_warns(self, monkeypatch):
        plan, dic = _case_with_plan(monkeypatch)
        dic["houseListBudget"] = _rows(
            (True, "core", "core", THISYEAR, 0, 72_000.0, 0.0, None, True, None, None, None, None, None),
            (True, "short", "core", 2031, 2030, 1.0, 0.0, None, False, None, None, None, None, None),
        )
        at = _render(monkeypatch, dic)
        assert not at.exception, [str(e.message) for e in at.exception]
        heads = [str(m.value) for m in at.markdown if str(m.value).startswith("### ")]
        assert any("Budget" in h for h in heads), heads
        warns = [str(w.value) for w in at.warning]
        assert any("Budget line 'short'" in w for w in warns), warns

    def test_the_budget_file_is_noted(self, monkeypatch):
        plan, dic = _case_with_plan(monkeypatch)
        dic["budgetFile"] = "budget.json"
        at = _render(monkeypatch, dic)
        assert not at.exception, [str(e.message) for e in at.exception]
        text = "\n".join(str(c.value) for c in at.caption)
        assert "budget.json" in text and "does not read it" in text


class TestARestoredRunKeepsItsTables:
    """"Open in Owl" (design 9.1) restores the run's Plan into the pages. The page used to
    zero the plan's Wages and Contributions on arrival (resetTimeLists), which is what the
    seeding now replaces."""

    def test_the_plan_and_the_case_keys_keep_the_run_tables(self, monkeypatch):
        plan, dic = _case_with_plan(monkeypatch)
        before = {name: df.copy() for name, df in plan.timeLists.items()}
        assert before["Jack"].to_numpy().any()  # there is something to lose
        budget = _rows((True, "core", "core", THISYEAR, 0, 72_000.0, 0.0, None, True, None, None, None, None, None))
        plan.houseLists["Budget"] = budget
        assert "timeList0" not in dic  # the tables live in the plan only, as genDic leaves them
        dic["caseStatus"] = "solved"

        at = _render(monkeypatch, dic)
        assert not at.exception, [str(e.message) for e in at.exception]
        for name, df in before.items():
            assert plan.timeLists[name].equals(df), name
        case = at.session_state["cases"]["t"]
        assert case["timeList0"].equals(plan.timeLists["Jack"])
        assert case["houseListBudget"].equals(budget)
        # Seeding the page is not an edit: a solved run keeps its status.
        assert case["caseStatus"] == "solved"


class TestTheTablesReachThePlanAndTheWorkbook:
    def test_a_budget_edit_reaches_the_workbook(self, monkeypatch):
        import owlbridge as owb
        import sskeys as kz

        case, dirname, _ = load_toml(str(JACK))
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        edited = _rows((True, "travel while able", "travel", THISYEAR, 0, 9_000.0, 0.0, None, False,
                        "age", 62.0, 80.0, "younger", None))
        uidic = {
            "plan": plan,
            "timeList0": plan.timeLists["Jack"],
            "timeList1": plan.timeLists["Jill"],
            "iname0": "Jack",
            "iname1": "Jill",
            "status": "married",
            "hfpFileName": "HFP_jack+jill.xlsx",
            "houseListDebts": plan.houseLists["Debts"],
            "houseListFixedAssets": plan.houseLists["Fixed Assets"],
            "houseListBudget": edited,
        }
        monkeypatch.setattr(kz, "getCaseKey", uidic.get)
        monkeypatch.setattr(kz, "setCaseKey", lambda k, v: uidic.update({k: v}))
        monkeypatch.setattr(kz, "storeCaseKey", lambda k, v: uidic.update({k: v}))

        owb.syncContributions()
        assert plan.houseLists["Budget"]["name"].tolist() == ["travel while able"]

        buffer = plan.saveContributions()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HFP.xlsx"
            buffer.save(path)
            budget = pd.read_excel(path, sheet_name="Budget")
        assert budget["name"].tolist() == ["travel while able"]
        assert budget["clock"].tolist() == ["age"]


class TestSavingTheCurrentCaseCarriesTheEdit:
    """The library's save takes the tables from the plan (`scenario_from_ui`), so the pages'
    edits have to be synced in first (`owlbridge.syncContributions`, called by the page)."""

    def test_the_saved_run_has_the_edited_budget_line(self, monkeypatch, tmp_path):
        from streamlit.testing.v1 import AppTest
        from owlplanner.library import Library

        root = tmp_path / "library"
        monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
        monkeypatch.syspath_prepend(str(UI_DIR))
        lib = Library.open(root)

        case, dirname, _ = load_toml(str(JACK))
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        dic = config_to_ui(copy.deepcopy(case))
        dic.update({"plan": plan, "id": plan._id, "caseStatus": "new", "summaryDf": None,
                    "casetoml": "", "logs": None})
        dic["timeList0"] = plan.timeLists[plan.inames[0]]
        if len(plan.inames) > 1:
            dic["timeList1"] = plan.timeLists[plan.inames[1]]
        dic["houseListDebts"] = plan.houseLists["Debts"]
        dic["houseListFixedAssets"] = plan.houseLists["Fixed Assets"]
        # The edit, in the pages' tables only: the plan still holds the workbook's rows.
        dic["houseListBudget"] = _rows((True, "edited line", "core", THISYEAR, 0, 72_000.0, 0.0,
                                        None, True, None, None, None, None, None))
        assert plan.houseLists["Budget"]["name"].tolist() != ["edited line"]

        import streamlit as st

        monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
        at = AppTest.from_file(str(UI_DIR / "Library.py"), default_timeout=120)
        at.session_state["cases"] = {"t": dic}
        at.session_state["currentCase"] = "t"
        at.run()
        assert not at.exception, [str(e.message) for e in at.exception]
        next(b for b in at.button if b.label == "Save as a new run").click().run()
        assert not at.exception, [str(e.message) for e in at.exception]

        runs = list(lib.runs())
        assert len(runs) == 1, [r.name for r in runs]
        workbook = runs[0].path / "inputs" / "HFP.xlsx"
        budget = pd.read_excel(workbook, sheet_name="Budget")
        assert "edited line" in budget["name"].tolist()

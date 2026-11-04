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
        assert "budget.json" in text and "never opens the file" in text


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

    def test_a_refused_table_is_not_saved_with_the_old_one(self, monkeypatch, tmp_path):
        """Review Y4: when the plan refuses the pages' tables the save stops and says so; it
        used to go ahead with the plan's previous tables, and the rerun hid the page's error."""
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
        jack = plan.timeLists[plan.inames[0]].copy()
        row = jack.index[jack["year"] == THISYEAR][0]
        jack.loc[row, "anticipated wages"] = 123_456.0  # the edit
        jack.loc[row, "months worked"] = 13  # refused by hfp_io.read
        dic["timeList0"] = jack
        dic["timeList1"] = plan.timeLists[plan.inames[1]]
        for key, table in (("houseListDebts", "Debts"), ("houseListFixedAssets", "Fixed Assets"),
                           ("houseListBudget", "Budget")):
            dic[key] = plan.houseLists[table]

        import streamlit as st

        monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
        at = AppTest.from_file(str(UI_DIR / "Library.py"), default_timeout=120)
        at.session_state["cases"] = {"t": dic}
        at.session_state["currentCase"] = "t"
        at.run()
        next(b for b in at.button if b.label == "Save as a new run").click().run()
        assert not at.exception, [str(e.message) for e in at.exception]
        assert list(lib.runs()) == []
        errors = [str(e.value) for e in at.error]
        assert any("were not accepted" in e for e in errors), errors


class TestAnEditMakesTheTableTheSource:
    """Review W2: for a case naming `budget_file`, an edit to the Budget table makes it the
    source everywhere (the model's own rule: a Budget sheet with lines wins over the file),
    so the solve, the Download workbook and a saved run all carry the same lines."""

    def _plan_with_budget_file(self, tmp_path):
        from owlplanner.config import config_to_plan, load_toml

        (tmp_path / "budget.json").write_text(
            '{"schema_version": 1, "lines": [{"name": "from the file", "type": "core", "amount": 50000.0}]}',
            encoding="utf-8",
        )
        case, _, _ = load_toml(str(JACK))
        case["optimization_parameters"]["budget_file"] = "budget.json"
        case["household_financial_profile"]["HFP_file_name"] = "None"
        plan = config_to_plan(copy.deepcopy(case), str(tmp_path), verbose=False, loadHFP=True)
        assert plan.budgetFromFile is True  # the file's lines are the plan's table
        return plan

    def test_an_edit_clears_budget_from_file_and_reaches_the_workbook(self, monkeypatch, tmp_path):
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        import owlbridge as owb

        plan = self._plan_with_budget_file(tmp_path)
        _, dic = owb.openCaseFromPlan(plan)
        dic["name"] = "t"
        dic["id"] = "t1"

        real_editor = st.data_editor

        def edited_budget(data, *args, **kwargs):
            # AppTest cannot drive st.data_editor; stand in for the user's edit (review W2).
            out = real_editor(data, *args, **kwargs)
            if str(kwargs.get("key", "")).endswith("_budget") and len(out):
                out = out.copy()
                out.loc[out.index[0], "amount"] = 4321.0
            return out

        monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
        monkeypatch.setattr(st, "data_editor", edited_budget)
        at = AppTest.from_file(str(UI_DIR / "Financial_Profile.py"), default_timeout=120)
        at.session_state["cases"] = {"t": dic}
        at.session_state["currentCase"] = "t"
        at.run()
        assert not at.exception, [str(e.message) for e in at.exception]
        assert plan.budgetFromFile is False
        assert at.session_state["cases"]["t"]["houseListBudget"]["amount"].tolist() == [4321.0]

        # A fresh render syncs the tables into the plan (the Download button's call). Keep the
        # sidebar's case selector on its decorated option first (AppTest cannot re-serialize it).
        for box in at.selectbox:
            if box.label == "Case selector":
                box.set_value(box.options[0])
        at.run()
        buffer = plan.saveContributions()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HFP.xlsx"
            buffer.save(path)
            budget = pd.read_excel(path, sheet_name="Budget")
        assert budget["name"].tolist() == ["from the file"]
        assert budget["amount"].tolist() == [4321.0]


class TestSavingSaysWhatItDidNotKeep:
    """Review W1: a value the run's events generate is regenerated from its event on save
    (design section 6.3, markers first), so an edit to one in the case pages is not kept.
    The save names those edits instead of losing them silently."""

    def test_the_save_names_the_edits_it_does_not_keep(self, monkeypatch, tmp_path):
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        from owlplanner.config import config_to_plan, config_to_ui, load_toml
        from owlplanner.library import Library, import_case
        import sskeys as kz

        root = tmp_path / "library"
        monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
        monkeypatch.syspath_prepend(str(UI_DIR))
        lib = Library.open(root)

        events = [{"id": "rent", "kind": "rent", "monthly": 4000,
                   "start": THISYEAR, "flat_until": THISYEAR + 1}]
        run = lib.save_run(name="base", scenario=dict(import_case(str(JACK)), events=events)).run

        case, dirname, _ = load_toml(str(run.path / "inputs" / "Case.toml"))
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False)
        dic = config_to_ui(copy.deepcopy(case))
        dic.update({"plan": plan, "id": plan._id, "caseStatus": "new", "summaryDf": None,
                    "casetoml": "", "logs": None})
        dic[kz.RUN_BASE_KEY] = run.id
        dic["timeList0"] = plan.timeLists[plan.inames[0]]
        if len(plan.inames) > 1:
            dic["timeList1"] = plan.timeLists[plan.inames[1]]
        dic["houseListDebts"] = plan.houseLists["Debts"]
        dic["houseListFixedAssets"] = plan.houseLists["Fixed Assets"]
        # The pages edit a generated row: the rent lines come from the "rent" event.
        budget = plan.houseLists["Budget"].copy()
        assert "rent" in list(budget["name"])
        budget.loc[budget["name"] == "rent", "amount"] = 12345.0
        dic["houseListBudget"] = budget

        monkeypatch.setattr(st, "page_link", lambda *a, **k: None)
        at = AppTest.from_file(str(UI_DIR / "Library.py"), default_timeout=120)
        at.session_state["cases"] = {"t": dic}
        at.session_state["currentCase"] = "t"
        at.run()
        assert not at.exception, [str(e.message) for e in at.exception]
        next(b for b in at.button if b.label == "Save as a new run").click().run()
        assert not at.exception, [str(e.message) for e in at.exception]
        warns = [str(w.value) for w in at.warning]
        assert any("Not kept in this run" in w and "Budget row 'rent'" in w for w in warns), warns

    def test_the_generated_row_note_shows_only_for_a_case_edited_from_a_run(self, monkeypatch):
        plan, dic = _case_with_plan(monkeypatch)
        at = _render(monkeypatch, dic)
        assert not [c for c in at.caption if "regenerated from its event" in str(c.value)]

        import sskeys as kz

        plan, dic = _case_with_plan(monkeypatch)
        dic[kz.RUN_BASE_KEY] = "run-1"
        at = _render(monkeypatch, dic)
        assert [c for c in at.caption if "regenerated from its event" in str(c.value)]

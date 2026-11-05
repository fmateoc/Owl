"""The Collections page (design section 9.3, step 6), rendered by Streamlit's AppTest.

The numbers' derivations are unit-tested in `tests/library/test_grid.py`; this checks the
page renders, the grid shows the differences from the reference, the leads are listed, and
a collection can be created and deleted. `make variants` is exercised at scale by
`fork-notes/synthetic/check_library_variants.py`.
"""

import json
from pathlib import Path

import pytest

from owlplanner.library import Library, import_case
from owlplanner.library import results as R

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"


def _write_result(run, name, *, score=82_000.0, home=150_000.0, savings=350_000.0,
                  finished="2026-11-03T10:05:00+01:00"):
    folder = run.path / "results" / name
    job = R.JobRecord.create(folder, run_id=run.id, run_name=run.name, preset="decision",
                             options={}, plan_year=run.plan_year)
    job.finish(R.DONE)  # as the worker leaves it: a solved result is no longer a live job
    record = {
        "record_format": R.RECORD_FORMAT, "status": "solved", "preset": "decision",
        "method": {"objective": "maxSpending", "breakpoint_method": "local search (5 rounds)",
                   "options": {"breakpointMethod": "local-search", "withSSAges": "fixed"}},
        "engine": {"version": "2026.11.3", "commit": "abcdef1"},
        "solve_date": {"started": finished, "finished": finished},
        "gap": -1.0,
        "convergence": {"convergence": "monotonic", "objective_error_bar_today_dollars": 0.0},
        "warnings": [],
        "plan_pkl_sha256": None,
    }
    summary = {
        "spending_basis": score, "discretionary_year1": score,
        "final_bequest_today": home + savings, "final_bequest_savings_today": savings,
    }
    plan = {"objective": "maxSpending", "individuals": ["Noa", "Avi"],
            "claiming_ages": [67.0, 70.0], "by_year": []}
    (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")
    (folder / R.SUMMARY_JSON).write_text(json.dumps(summary), encoding="utf-8")
    (folder / R.PLAN_JSON).write_text(json.dumps(plan), encoding="utf-8")
    return folder


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    lib = Library.open(root)
    base = lib.save_run(name="bill", scenario=import_case(BILL)).run
    scenario = import_case(BILL)
    scenario["case"]["case_name"] = "bill later"
    variant = lib.save_run(name="bill later", scenario=scenario, parent=base.id).run
    _write_result(base, "2026-11-03T10-00-00_decision")
    _write_result(variant, "2026-11-03T11-00-00_decision", score=84_000.0, home=120_000.0,
                  finished="2026-11-03T11:05:00+01:00")
    coll = lib.create_collection("Where and when to buy",
                                 question="Maximize spending, condo kept",
                                 rule="reference: bill; a variant leads on both numbers")
    lib.add_member(coll.id, base, {"year": 2027})
    lib.add_member(coll.id, variant, {"year": 2029})
    lib.set_reference(coll.id, base)
    lib.update_collection(coll.id, grid={"rows": [], "columns": ["year"]})
    return lib


def _page(name="Collections.py"):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / name), default_timeout=90)
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    return at.run()


def _text(at):
    parts = [m.value for m in at.markdown]
    parts += [c.value for c in at.caption]
    parts += [i.value for i in at.info]
    parts += [w.value for w in at.warning]
    parts += [e.value for e in at.error]
    return "\n".join(str(p) for p in parts)


class TestTheGrid:
    def test_the_page_shows_the_question_the_grid_and_the_leads(self, library):
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "Where and when to buy" in text
        assert "Maximize spending, condo kept" in text
        assert "The grid" in text and "What nothing beats (R3)" in text

    def test_the_cells_are_differences_from_the_reference(self, library):
        at = _page()
        text = _text(at)
        # bill later scores 2,000 more and keeps 30,000 less home than the reference: a
        # trade-off (R3), the cell's difference against the reference's own score.
        assert "+2,000" in text
        assert "vs *bill*" in text

    def test_the_members_are_listed_with_their_values(self, library):
        at = _page()
        text = _text(at)
        assert "**bill**" in text and "**bill later**" in text
        assert "year: 2027" in text and "year: 2029" in text


class TestCollections:
    def test_a_collection_can_be_created(self, library):
        at = _page()
        at.text_input(key="col_new_name").set_value("A second question")
        at.text_input(key="col_new_question").set_value("Where to live at 85?")
        at.run()
        next(b for b in at.button if b.label == "Create collection").click().run()
        assert not at.exception, [e.value for e in at.exception]
        names = [c.name for c in library.collections()]
        assert "A second question" in names

    def test_the_collection_is_deleted_and_its_runs_kept(self, library):
        at = _page()
        at.button(key=f"col_delete_{library.collections()[0].id}").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert library.collections() == []
        assert len(library.runs()) == 2

    def test_make_variants_offers_the_dimensions(self, library):
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        labels = [b.label for b in at.button]
        assert "Create the variants" in labels and "Queue every member" in labels
        assert any(t.label == "Purchase year(s)" for t in at.text_input)
        assert "Claiming ages" in _text(at)

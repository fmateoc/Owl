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
    plan = {"objective": "maxSpending", "individuals": ["Bill"],
            "claiming_ages": [67.0], "by_year": []}
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
        assert "The grid" in text and "What nothing beats" in text

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

    def test_create_collection_is_enabled_before_the_name_and_asks_for_it(self, library):
        """UX review Q18: gated on the name, the button was still disabled when the click that
        blurs the name field landed, so that click did nothing (reproduced with Playwright; a
        blur cannot be driven from AppTest). It is enabled now and a blank name is refused."""
        at = _page()
        button = next(b for b in at.button if b.label == "Create collection")
        assert not button.disabled
        before = len(library.collections())
        button.click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert any(w.value == "Give the collection a name." for w in at.warning)
        assert len(library.collections()) == before

    def test_a_second_click_does_not_make_a_twin(self, library):
        """Found in the Q18 re-drive: the name stays in the field after a create, and a
        second click made a second collection with the same name."""
        at = _page()
        at.text_input(key="col_new_name").set_value("A second question")
        at.run()
        next(b for b in at.button if b.label == "Create collection").click().run()
        next(b for b in at.button if b.label == "Create collection").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert [c.name for c in library.collections()].count("A second question") == 1
        assert any("exists already" in w.value for w in at.warning)

    def test_ac3_create_collection_opens_the_new_collection(self, library):
        # Review AC3: `_open_collection` stored the collection's id where the picker holds
        # labels, so the rerun fell back to the first collection instead of opening the new
        # one (and dropped the previous selection).
        at = _page()
        at.text_input(key="col_new_name").set_value("A second question")
        at.run()
        next(b for b in at.button if b.label == "Create collection").click().run()
        assert not at.exception, [e.value for e in at.exception]
        heads = [m.value for m in at.markdown if str(m.value).startswith("## ")]
        assert heads == ["## A second question"]

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


class TestMakeVariants:
    """The make-variants editors end to end (reviews AC1-AC2, AC6)."""

    def test_ac1_fill_the_ages_fills_the_boxes(self, library):
        # The fill button used to write the claim boxes' widget keys from an inline
        # handler -- StreamlitWidgetAlreadyInstantiatedError on every click (AC1).
        at = _page()
        at.text_input(key="col_variant_claim_Bill").set_value("70")
        at.run()
        next(b for b in at.button if b.label == "Fill the ages from the run's last solve").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert at.text_input(key="col_variant_claim_Bill").value == "67"

    def test_ac2_create_the_variants_ends_without_an_exception(self, library):
        # The handler's tail wrote the collection picker's widget key (AC2): the children
        # were saved but the page ended in StreamlitWidgetAlreadyInstantiatedError. A claim
        # value makes one child of the bill run (its scenario has no purchase to vary).
        at = _page()
        at.text_input(key="col_variant_claim_Bill").set_value("67")
        at.run()
        next(b for b in at.button if b.label == "Create the variants").click().run()
        assert not at.exception, [e.value for e in at.exception]
        coll = library.collections()[0]
        assert [m.values for m in coll.members] == [{"year": 2027}, {"year": 2029},
                                                    {"claim": "Bill 67y0m"}]
        assert sorted(r.name for r in library.runs()) == ["bill", "bill bill-67y0m", "bill later"]

    def test_ac6_a_bad_cell_flashes_an_error_and_makes_nothing(self, library):
        # `float()` on the claiming box (and on the places/financing cells) used to end the
        # page with a raw ValueError (AC6): a bad cell is a flash now, and nothing is made.
        at = _page()
        at.text_input(key="col_variant_claim_Bill").set_value("67x")
        at.run()
        next(b for b in at.button if b.label == "Create the variants").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert "67x" in _text(at)
        assert sorted(r.name for r in library.runs()) == ["bill", "bill later"]


class TestTheNewDimensions:
    """The I2 first-death dimension and the I11 downturn-sequence table on the page (the
    table's parsing is unit-tested in test_variant_tables.py; AppTest cannot drive it)."""

    def test_the_editors_are_on_the_form(self, library):
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "First death" in text and "Downturn sequence" in text
        assert at.text_input(key="col_variant_death_ages") is not None

    def test_the_first_death_fields_make_a_death_variant(self, library):
        at = _page()
        at.selectbox(key="col_variant_death_person").select("Bill")
        at.text_input(key="col_variant_death_ages").set_value("80")
        at.run()
        next(b for b in at.button if b.label == "Create the variants").click().run()
        assert not at.exception, [e.value for e in at.exception]
        child = next(r for r in library.runs() if "dies-at-80" in r.name)
        events = library.scenario(child.id)["events"]
        assert [e for e in events if e["kind"] == "death"] == [
            {"id": "death-bill", "kind": "death", "person": "Bill", "age": 80}]
        coll = library.collections()[0]
        assert coll.member(child.id).values == {"death": "Bill dies at 80"}


class TestMemberValues:
    """The hand-added member's values (the grid places a member through them)."""

    def _hand_added(self, tmp_path, monkeypatch):
        members = [({"year": 2027}, 80_000.0, 150_000.0), ({"year": 2029}, 82_000.0, 150_000.0)]
        lib = _grid_library(tmp_path, monkeypatch, members)
        coll = lib.collections()[0]
        scenario = import_case(BILL)
        scenario["case"]["case_name"] = "v2b"
        run = lib.save_run(name="v2b", scenario=scenario).run
        _write_result(run, "2026-11-03T10-00-02_decision", score=90_000.0, home=200_000.0)
        lib.add_member(coll.id, run)  # no values: listed beside the grid
        return lib, coll, run

    def test_values_set_by_hand_place_the_member(self, tmp_path, monkeypatch):
        lib, coll, run = self._hand_added(tmp_path, monkeypatch)
        at = _page()
        assert "Beside the grid" in _text(at)
        at.text_area(key=f"col_values_{coll.id}_{run.id}").set_value("year: 2031")
        at.run()
        at.button(key=f"col_values_save_{coll.id}_{run.id}").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert lib.collection(coll.id).member(run.id).values == {"year": 2031}
        assert "Beside the grid" not in _text(at)  # a cell of its own now

    def test_a_pair_that_is_not_a_pair_is_flashed_and_keeps_the_values(self, tmp_path, monkeypatch):
        lib, coll, run = self._hand_added(tmp_path, monkeypatch)
        at = _page()
        at.text_area(key=f"col_values_{coll.id}_{run.id}").set_value("yonkers")
        at.run()
        at.button(key=f"col_values_save_{coll.id}_{run.id}").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert "not a 'dimension: label' pair" in _text(at)
        assert lib.collection(coll.id).member(run.id).values == {}

    def test_re_adding_a_member_keeps_its_values(self, library):
        # `add_member` replaces the values (store): the Add button must not wipe them.
        coll = library.collections()[0]
        bill = next(r for r in library.runs() if r.name == "bill")
        at = _page()
        at.selectbox(key="col_add_run").select("bill")
        at.run()
        next(b for b in at.button if b.label == "Add to the collection").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert library.collection(coll.id).member(bill.id).values == {"year": 2027}


class TestNoRuns:
    def test_ac7_a_collection_with_no_runs_renders(self, tmp_path, monkeypatch):
        # Make variants used to read `lib.scenario(None)` ("no run with id None") on every
        # render of a collection with no runs (AC7).
        root = tmp_path / "empty"
        monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
        Library.open(root).create_collection("Lonely question")
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        assert "Lonely question" in _text(at)


def _grid_library(tmp_path, monkeypatch, members, layout=None):
    """A library with one collection: each member (values, score, home) a bill run with a
    solved result; the first is the reference."""
    root = tmp_path / "grid"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    lib = Library.open(root)
    coll = lib.create_collection("Q")
    for i, (values, score, home) in enumerate(members):
        scenario = import_case(BILL)
        scenario["case"]["case_name"] = f"v{i}"
        run = lib.save_run(name=f"v{i}", scenario=scenario).run
        _write_result(run, f"2026-11-03T10-00-0{i}_decision", score=score, home=home)
        lib.add_member(coll.id, run, values)
        if i == 0:
            lib.set_reference(coll.id, run)
    if layout is not None:
        lib.update_collection(coll.id, grid=layout)
    return lib


def _grid_md(at):
    return next(str(m.value) for m in at.markdown if str(m.value).startswith("| "))


class TestTheGridLayoutAndMarks:
    """Review AD2-AD4 on the real page."""

    def test_ad2_the_condo_grid_places_every_member(self, tmp_path, monkeypatch):
        # 2 places x 2 years x 2 financings, no saved layout: the page used to take the
        # alphabetically first and last dimensions (financing x year), dropping place and
        # listing four members "beside the grid".
        members, score = [], 80_000.0
        for place in ("yonkers", "white-plains"):
            for year in (2027, 2029):
                for fin in ("cash", "mortgage"):
                    members.append(({"place": place, "year": year, "financing": fin}, score, 150_000.0))
                    score += 3_000
        _grid_library(tmp_path, monkeypatch, members)
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        table = _grid_md(at)
        assert table.startswith("| place, financing | 2027 | 2029 |")
        assert "white-plains, mortgage" in table and "yonkers, cash" in table
        assert "Beside the grid" not in _text(at)

    def test_ad2_one_dimension_is_one_row(self, tmp_path, monkeypatch):
        members = [({"year": y}, 80_000.0 + 3_000 * i, 150_000.0) for i, y in enumerate((2027, 2029, 2031))]
        _grid_library(tmp_path, monkeypatch, members)
        at = _page()
        lines = _grid_md(at).splitlines()
        assert len(lines) == 3  # header, rule, one row (it was a 3 x 3 diagonal)

    def test_ad3_the_star_is_never_on_a_number_that_is_not_the_best(self, tmp_path, monkeypatch):
        # Two members in one cell (a layout with columns only); the second scores more.
        members = [({"place": "yonkers", "year": 2027}, 80_000.0, 150_000.0),
                   ({"place": "yonkers", "year": 2029}, 82_000.0, 150_000.0),
                   ({"place": "queens", "year": 2029}, 95_000.0, 150_000.0)]
        _grid_library(tmp_path, monkeypatch, members, layout={"rows": [], "columns": ["year"]})
        at = _page()
        assert not at.exception, [e.value for e in at.exception]
        assert "&#9733;" not in _grid_md(at)  # the +2,000 cell used to carry the row's star
        [beside] = [c.value for c in at.caption if "Beside the grid" in c.value]
        assert "**v2**" in beside and "the best score in its row" in beside

    def test_ad4_a_lead_on_the_home_inside_the_score_band_is_green(self, tmp_path, monkeypatch):
        # +400 on 80,000 is inside the 1% band; +100,000 of home is resolved: R3 says the
        # variant leads, and the cell used to be grey.
        members = [({"place": "yonkers"}, 80_000.0, 150_000.0),
                   ({"place": "queens"}, 80_400.0, 250_000.0)]
        _grid_library(tmp_path, monkeypatch, members)
        at = _page()
        assert "color:#2e7d32'><b>~+400" in _grid_md(at)


class TestTheClaimingAgesWarnings:
    """Review AD5 on the real page: the grid flags cells at other claiming ages, and Make
    variants warns when the parent's last solve searched them and the boxes are empty."""

    def test_ad5_a_cell_at_other_ages_is_flagged(self, tmp_path, monkeypatch):
        members = [({"year": 2027}, 80_000.0, 150_000.0), ({"year": 2029}, 81_000.0, 150_000.0)]
        lib = _grid_library(tmp_path, monkeypatch, members)
        coll = lib.collections()[0]
        other = lib.get(coll.members[1].run)
        plan_json = next((other.path / "results").iterdir()) / R.PLAN_JSON
        doc = json.loads(plan_json.read_text(encoding="utf-8"))
        doc["claiming_ages"] = [70.0]
        plan_json.write_text(json.dumps(doc), encoding="utf-8")
        at = _page()
        warnings = [w.value for w in at.warning]
        assert any("claiming ages other than the reference's" in w and "v1 (Bill 70y0m)" in w
                   for w in warnings)

    def test_ad5_make_variants_warns_after_an_ages_solve(self, library):
        bill = next(r for r in library.runs() if r.name == "bill")
        record_path = next((bill.path / "results").iterdir()) / R.RECORD_JSON
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["age_search"] = {"chosen": [67.0], "candidates": [[[67.0], 82_000.0]]}
        record_path.write_text(json.dumps(record), encoding="utf-8")
        at = _page()
        at.selectbox(key="col_variant_parent").set_value(bill).run()
        assert any("searched the claiming ages" in w.value for w in at.warning)
        at.text_input(key="col_variant_claim_Bill").set_value("67").run()
        assert not any("searched the claiming ages" in w.value for w in at.warning)

    def test_ad2_make_variants_stores_a_layout(self, tmp_path, monkeypatch):
        root = tmp_path / "fresh"
        monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
        monkeypatch.syspath_prepend(str(UI_DIR))
        lib = Library.open(root)
        lib.save_run(name="bill", scenario=import_case(BILL))
        lib.create_collection("Claims")
        at = _page()
        at.text_input(key="col_variant_claim_Bill").set_value("67, 70").run()
        next(b for b in at.button if b.label == "Create the variants").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert lib.collections()[0].grid == {"rows": [], "columns": ["claim"]}


class TestASensitivityCollection:
    """Review AG5: the tornado's children have exact-LP results only; the page reads the
    whole collection through them instead of calling every member unsolved."""

    EXACT = {"breakpointMethod": "loop", "withMedicare": "none", "withSSTaxability": 0.85,
             "withLTCG": "optimize", "withSSAges": "fixed"}

    def _exact(self, run, name, score):
        folder = _write_result(run, name, score=score)
        record = json.loads((folder / R.RECORD_JSON).read_text(encoding="utf-8"))
        record["preset"] = "decision_exact"
        record["method"] = {"objective": "maxSpending", "breakpoint_method": "loop",
                            "options": dict(self.EXACT)}
        (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")

    def test_ag5_the_members_show_their_exact_lp_numbers(self, library):
        from owlplanner.library import tornado

        base = next(r for r in library.runs() if r.name == "bill")
        self._exact(base, "2026-11-03T09-00-00_decision_exact", 80_000.0)
        made, _ = tornado.tornado_variants(library.scenario(base.id))
        coll = library.create_collection(f"Sensitivity: {base.name}")
        library.add_member(coll.id, base, {"mover": tornado.BASE_LABEL})
        library.set_reference(coll.id, base)
        for i, variant in enumerate(made[:2]):
            child = library.save_run(name=f"bill {variant.label}", scenario=variant.scenario,
                                     parent=base.id).run
            library.add_member(coll.id, child, variant.values)
            self._exact(child, f"2026-11-03T1{i}-00-00_decision_exact", 78_000.0 - 1_000 * i)
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(UI_DIR / "Collections.py"), default_timeout=90)
        at.session_state["cases"] = {}
        at.session_state["currentCase"] = None
        at.session_state["library_selected_collection"] = coll.id
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "No member of this collection has a solved result yet" not in text
        assert "no solved result yet" not in text
        assert "exact-LP" in text
        assert "-2,000" in text  # the first mover's cell: 78,000 against the reference's 80,000

    def test_aj1_the_medical_child_says_where_its_bar_is(self, library):
        """Review AJ1: the medical-inflation child solves with Medicare priced exactly and has
        no exact-LP result to place; the member list says so instead of "no solved result"."""
        from owlplanner.library import tornado

        base = next(r for r in library.runs() if r.name == "bill")
        self._exact(base, "2026-11-03T09-00-00_decision_exact", 80_000.0)
        made, _ = tornado.tornado_variants(library.scenario(base.id))
        coll = library.create_collection(f"Sensitivity: {base.name}", tornado_of=base.id)
        library.add_member(coll.id, base, {"mover": tornado.BASE_LABEL})
        library.set_reference(coll.id, base)
        returns = next(v for v in made if v.label == "returns-1")
        medical = next(v for v in made if v.label == "medical+2")
        for variant in (returns, medical):
            child = library.save_run(name=f"bill {variant.label}", scenario=variant.scenario,
                                     parent=base.id).run
            library.add_member(coll.id, child, variant.values)
            if variant is returns:
                self._exact(child, "2026-11-03T10-00-00_decision_exact", 78_000.0)
            else:
                folder = _write_result(child, "2026-11-03T11-00-00_exact_medicare", score=77_000.0)
                record = json.loads((folder / R.RECORD_JSON).read_text(encoding="utf-8"))
                record["preset"] = "exact_medicare"
                record["method"] = {"objective": "maxSpending", "breakpoint_method": "loop",
                                    "options": {**self.EXACT, "withMedicare": "optimize"}}
                (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(UI_DIR / "Collections.py"), default_timeout=90)
        at.session_state["cases"] = {}
        at.session_state["currentCase"] = None
        at.session_state["library_selected_collection"] = coll.id
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "exact-LP" in text and "-2,000" in text  # the grid stays on the exact LP
        assert "solved with Medicare priced exactly" in text

"""The step-3 pages (run-library step 3), rendered for real by Streamlit's AppTest.

`ui/Library.py` lists the runs and gets new ones in; `ui/Run.py` shows one run's result (the
headline numbers of design 9.1, charts from plan.json, the workbook, the buttons);
`ui/Compare.py` shows two results judged against the noise rule (design 9.2, R2/R3). The
records here are written by hand: the numbers' derivations are unit-tested in
`tests/library/test_view.py` and `test_compare.py`; this checks the pages render and say
what they should.
"""

import json
from pathlib import Path

import pytest

from owlplanner.library import Library, import_case
from owlplanner.library import results as R

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"


def _write_result(run, name, *, preset="decision", score=82_000.0, home=150_000.0,
                  savings=350_000.0, finished="2026-11-02T10:05:00+01:00", exact=False,
                  tax_shift=0):
    """One results folder with its record.json, summary.json and plan.json."""
    folder = run.path / "results" / name
    job = R.JobRecord.create(folder, run_id=run.id, run_name=run.name, preset=preset, options={},
                             plan_year=run.plan_year)
    job.finish(R.DONE)  # as the worker leaves it: a solved result is no longer a live job
    options = ({"breakpointMethod": "loop", "withMedicare": "none",
                "withSSTaxability": 0.85, "withLTCG": "optimize"} if exact
               else {"breakpointMethod": "local-search", "withSSAges": "fixed"})
    if preset == "exact_medicare":  # the tornado's medical-inflation model (review AJ1)
        options = {**options, "withMedicare": "optimize"}
    record = {
        "record_format": R.RECORD_FORMAT, "status": "solved", "preset": preset,
        "method": {"objective": "maxSpending",
                   "breakpoint_method": "loop" if exact else "local search (5 rounds)",
                   "options": options},
        "engine": {"version": "2026.11.2", "commit": "abcdef1"},
        "solve_date": {"started": finished, "finished": finished},
        "gap": -1.0,
        "convergence": {"convergence": "monotonic", "objective_error_bar_today_dollars": 0.0},
        "warnings": [],
        "plan_pkl_sha256": None,
    }
    summary = {
        "spending_basis": score, "discretionary_year1": score, "essential_year1": 18_000.0,
        "final_bequest_today": home + savings, "final_bequest_savings_today": savings,
        "federal_income_tax_today": 120_000.0, "ltcg_tax_today": 10_000.0,
        "niit_today": 2_000.0, "payroll_tax_today": 3_000.0, "state_tax_today": 45_000.0,
        "ss_withheld_today": 7_000.0,
    }
    plan = {
        "objective": "maxSpending", "individuals": ["Noa", "Avi"],
        "claiming_ages": [66.1667, 70.0],
        "brackets": {
            "units": "today's dollars",
            "years": [{"year": y, "ages": [60, 62], "ordinary_taxable_income": 90_000.0,
                       "conversion": 15_000.0, "magi": 110_000.0, "fills_bracket": "22/25%",
                       "room_to_next_edge": 25_000.0,
                       "ordinary_edges": [{"label": "22/25%", "amount": 115_000.0}],
                       "gains_edge_0": 49_450.0,
                       "irmaa_edges": [{"label": "IRMAA tier 1", "amount": 110_000.0,
                                        "premium_year": y + 2}],
                       "aca_lines": [{"label": "400% FPL (the subsidy cliff)",
                                      "amount": 100_000.0}]}
                      for y in (2027, 2028)],
        },
        "thresholds": {
            "near_band_fraction": 0.05,
            "entries": [{"year": 2027, "kind": "irmaa", "label": "IRMAA tier 1", "side": "over",
                         "amount_today_dollars": 1_200.0, "cost_today_dollars": 1_900.0,
                         "affects": 2029, "note": "the MAGI of 2027 sets the premiums of 2029"}],
        },
        "cash_flow": {
            "sources": {"Wages": [60_000, 30_000], "Taxable-account withdrawals": [30_000, 61_000]},
            "uses": {"Net spending": [90_000, 91_000]},
        },
        "by_year": [
            {"year": 2027, "spending": 90_000, "federal_income_tax": 20_000 + tax_shift,
             "ltcg_tax": 2_000,
             "niit": 500, "payroll_tax": 0, "state_tax": 5_000, "medicare_premiums": 0,
             "aca_premiums": 0, "roth_conversions": 0, "portfolio_withdrawals": 55_000,
             "ss_income": [0, 0], "wages": 10_000, "pension_income": 0, "spia_income": 0,
             "portfolio_total": 1_400_000, "fixed_assets": 0, "debt": 0, "net_worth": 1_400_000},
            {"year": 2028, "spending": 91_000, "federal_income_tax": 21_000 + tax_shift,
             "ltcg_tax": 2_100,
             "niit": 510, "payroll_tax": 0, "state_tax": 5_100, "medicare_premiums": 0,
             "aca_premiums": 0, "roth_conversions": 0, "portfolio_withdrawals": 57_000,
             "ss_income": [0, 0], "wages": 0, "pension_income": 0, "spia_income": 0,
             "portfolio_total": 1_350_000, "fixed_assets": 0, "debt": 0, "net_worth": 1_350_000},
        ],
    }
    (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")
    (folder / R.SUMMARY_JSON).write_text(json.dumps(summary), encoding="utf-8")
    (folder / R.PLAN_JSON).write_text(json.dumps(plan), encoding="utf-8")
    return folder


def _set_created(run, iso):
    """Pin run.json's created stamp: the fixture saves its runs within one second."""
    path = run.path / "run.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["created"] = iso
    path.write_text(json.dumps(doc), encoding="utf-8")


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
    _set_created(base, "2026-11-01T09:00:00+01:00")
    _set_created(variant, "2026-11-01T10:00:00+01:00")
    _write_result(base, "2026-11-02T10-00-00_decision")
    _write_result(base, "2026-11-02T10-30-00_decision_exact", preset="decision_exact",
                  score=70_000.0, exact=True)
    _write_result(variant, "2026-11-02T11-00-00_decision", score=84_000.0, home=120_000.0,
                  savings=350_000.0, finished="2026-11-02T11:05:00+01:00", tax_shift=2_000)
    _write_result(variant, "2026-11-02T11-30-00_decision_exact", preset="decision_exact",
                  score=72_500.0, exact=True, finished="2026-11-02T11:35:00+01:00")
    return lib


def _page(name):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(UI_DIR / name), default_timeout=90)
    # sskeys.init() runs once per process at import time (main.py normally does it per
    # session): seed what the pages read from the session (as test_open_in_owl does).
    at.session_state["cases"] = {}
    at.session_state["currentCase"] = None
    return at.run()


def _text(at):
    """Everything the page says: markdown, captions and messages."""
    parts = [m.value for m in at.markdown]
    parts += [c.value for c in at.caption]
    parts += [i.value for i in at.info]
    parts += [w.value for w in at.warning]
    parts += [e.value for e in at.error]
    return "\n".join(parts)


class TestLibraryPage:
    def test_the_runs_are_listed_with_their_lineage(self, library):
        at = _page("Library.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "**bill**" in text and "**bill later**" in text
        assert "from *bill*" in text  # the child's change summary (section 7)
        assert "2 solve(s)" in text

    def test_a_new_run_can_be_imported_and_the_current_case_saved(self, library):
        at = _page("Library.py")
        assert any(u.label.startswith("Case file") for u in at.get("file_uploader"))
        text = _text(at)
        assert "No case is open in the session" in text

    def test_the_save_dialogs_offer_the_collections(self, library):
        # Design section 7's "Collection" field, in both save dialogs (the run joins with no
        # variant values; the Collections page sets them).
        from streamlit.testing.v1 import AppTest

        library.create_collection("Where to live")
        at = AppTest.from_file(str(UI_DIR / "Library.py"), default_timeout=90)
        at.session_state["cases"] = {"draft": {"name": "draft"}}  # an open case: tab 2 shows
        at.session_state["currentCase"] = "draft"
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        boxes = [s for s in at.selectbox if s.label == "Collection (optional)"]
        assert len(boxes) == 2  # the import tab and "save the current case"
        assert all(b.options[0] == "(none)" and "Where to live" in b.options for b in boxes)

    def test_open_switches_to_the_run_page(self, library, monkeypatch):
        opened = []
        monkeypatch.setattr("streamlit.switch_page", lambda page: opened.append(page))
        at = _page("Library.py")
        at.button(key=f"open_{library.runs()[0].id}").click().run()
        assert opened == ["Run.py"]

    def test_zip_downloads_are_offered_for_every_run(self, library):
        at = _page("Library.py")
        assert not at.exception, [e.value for e in at.exception]
        zips = [d for d in at.get("download_button") if d.label == "Zip"]
        assert len(zips) == len(library.runs())


class TestMessagesSurviveTheRerun:
    """Review 3, W3: a message written just before `st.rerun()` was cleared by the rerun; the
    pages now queue it (`libraryjobs.flash`) and draw it on the next render. W4: Delete is
    refused while the run has a live solve."""

    def test_a_failed_save_of_the_current_case_is_shown(self, library):
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(UI_DIR / "Library.py"), default_timeout=90)
        at.session_state["cases"] = {"draft": {"name": "draft"}}  # no plan: cannot be saved
        at.session_state["currentCase"] = "draft"
        at.run()
        next(b for b in at.button if b.label == "Save as a new run").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert any(e.value.startswith("Cannot save this case yet") for e in at.error)
        at.run()  # shown once, not on every render after
        assert not any(e.value.startswith("Cannot save this case yet") for e in at.error)

    def test_delete_is_refused_while_a_solve_waits(self, library, monkeypatch):
        from owlplanner.library import JobManager

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # stays waiting
        run = library.runs()[0]
        JobManager(library).enqueue(run)
        at = _page("Library.py")
        at.button(key=f"delb_{run.id}").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert any("Not deleted" in e.value and "Cancel it on the Queue page" in e.value
                   for e in at.error)
        assert run.path.is_dir() and run.id in [r.id for r in library.runs()]

    def test_delete_without_a_live_solve_moves_the_run_to_the_trash(self, library):
        run = library.runs()[0]
        at = _page("Library.py")
        at.button(key=f"delb_{run.id}").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert not at.error, [e.value for e in at.error]
        assert not run.path.exists()

    def test_a_refused_solve_says_why(self, library, monkeypatch):
        from owlplanner.library import ScenarioError

        def refuse(scenario):
            raise ScenarioError("the run's plan year is 2025 but this is 2026")

        monkeypatch.setattr("owlplanner.library.jobs.check_plan_year", refuse)
        at = _page("Run.py")
        next(b for b in at.button if b.label == "Solve").click().run()
        assert not at.exception, [e.value for e in at.exception]
        assert any("Not queued" in e.value and "plan year is 2025" in e.value for e in at.error)


class _Session(dict):
    """A stand-in for st.session_state: item and attribute access to one dict."""

    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class TestTheRunBaseFollowsItsCase:
    """Review 2, Q9: the "edited from run X" mark was session-wide and cleared route by route;
    `switchToCaseName` (Run All Cases), `copyCase` and `deleteCurrentCase` left it in place,
    so the next save claimed the wrong parent and base. It now lives in the case's dict."""

    @pytest.fixture
    def kz(self, monkeypatch):
        import sskeys

        session = _Session(cases={"edited": {}, "other": {}}, currentCase="edited")
        monkeypatch.setattr(sskeys, "ss", session)
        return sskeys

    def test_switching_by_name_does_not_carry_the_mark(self, kz):
        kz.setRunBase("run-1")
        assert kz.runBase() == "run-1"
        kz.switchToCaseName("other")  # what owlbridge.runAllCases does, case by case
        assert kz.runBase() is None
        kz.switchToCaseName("edited")
        assert kz.runBase() == "run-1"  # back on the edited case: still its base

    def test_deleting_the_edited_case_drops_the_mark(self, kz):
        kz.setRunBase("run-1")
        kz.deleteCurrentCase()
        assert kz.currentCaseName() == "other" and kz.runBase() is None

    def test_no_current_case_has_no_base(self, kz):
        kz.ss.currentCase = None
        assert kz.runBase() is None


class TestRunPage:
    def test_the_headline_numbers_come_from_the_result(self, library):
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        metrics = {m.label: m.value for m in at.metric}
        # The newest run's main solve (its exact-model companion is not the headline, R2).
        assert metrics["Score"] == "84,000"
        assert metrics["Home at the end"] == "120,000"
        assert metrics["Savings left"] == "350,000"
        assert metrics["Total taxes"] == "180,000"
        text = _text(at)
        assert "Noa 66y2m, Avi 70y0m" in text
        assert "settled" in text
        assert "local search" in text and "abcdef1" in text

    def test_charts_and_the_solve_expander_render(self, library):
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        assert at.get("plotly_chart"), "the charts from plan.json did not render"
        assert any("Solve this run" in e.label for e in at.expander)

    def test_the_quality_line_warns_when_the_loop_did_not_settle(self, library):
        run = library.runs()[-1]  # "bill later": the run page's default
        folder = run.path / "results" / "2026-11-02T11-00-00_decision"
        record = json.loads((folder / R.RECORD_JSON).read_text(encoding="utf-8"))
        record["convergence"]["objective_error_bar_today_dollars"] = 2782.0
        (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")
        at = _page("Run.py")
        assert any("did not settle" in w.value for w in at.warning)
        assert any("under 1%" in w.value for w in at.warning)
        # Shown once, as a warning; the caption points at it (review 2, Q4).
        assert _text(at).count("did not settle") == 1
        assert any(c.value == "Quality: 1 problem(s), below" for c in at.caption)

    def test_edit_as_new_run_opens_the_frozen_files(self, library):
        at = _page("Run.py")
        button = next(b for b in at.button if b.label == "Edit as new run")
        button.click().run()
        assert not at.exception, [e.value for e in at.exception]
        # The case pages hold the run's inputs, and saving will make a child of *this* run.
        case = at.session_state["cases"][at.session_state["currentCase"]]
        assert case["library_base_run_id"] == library.runs()[-1].id

    def test_open_switches_runs_after_the_first_render(self, library):
        """Review P2: the selector's widget state used to override "Open" after run one."""
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        assert any(m.value == "## bill later" for m in at.markdown)  # the newest run first
        at.session_state["library_selected_run"] = library.runs()[0].id  # what Open sets
        at.run()
        assert any(m.value == "## bill" for m in at.markdown)
        assert not any(m.value == "## bill later" for m in at.markdown)

    def test_the_solve_button_queues_both_decision_solves(self, library, monkeypatch):
        """Review P12: "decision" is one choice, two results (design 8.1)."""
        from owlplanner.library import JobManager

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # no real worker
        before = {j.id for j in JobManager(library).jobs()}
        at = _page("Run.py")
        at.selectbox(key="run_page_preset").select("decision").run()
        next(b for b in at.button if b.label == "Solve").click().run()
        assert not at.exception, [e.value for e in at.exception]
        queued = [j for j in JobManager(library).jobs() if j.id not in before]
        assert sorted(j.doc["preset"] for j in queued) == ["decision", "decision_exact"]

    def test_the_run_zip_download_is_offered(self, library):
        at = _page("Run.py")
        assert any(d.label == "Download everything" for d in at.get("download_button"))


class TestRunPageDetails:
    """The second increment of step 3: I3 (threshold proximity), I6 (the one-year Sankey)
    and I7 (the claiming-age map), run-library-design.md 14.1."""

    def test_things_to_look_at_shows_the_years_near_a_threshold(self, library):
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "Things to look at" in text
        assert "within 5% of a threshold" in text
        assert any("IRMAA tier 1" in str(d.value) for d in at.dataframe)

    def test_the_one_year_cash_flow_sankey_has_its_year_and_caption(self, library):
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        assert at.selectbox(key="run_page_cash_flow_year"), "the year picker did not render"
        text = _text(at)
        # Both sides as drawn (review 3, W1): the fixture's 2027 is 90,000 in and out.
        assert "90,000 in" in text and "90,000 out" in text
        assert "Roth conversion is a move between accounts" in text
        assert "drawn as a source" in text  # a negative tax (STAR refund) is money in

    def test_the_claiming_age_map_reads_scores_json_from_the_run_folder(self, library):
        run = library.runs()[-1]  # the page's default run
        scores = [{"name": "base", "free": ["Noa", "Avi"], "best": [804, 804], "sweeps": [],
                   "results": {
                       "67y0m/67y0m": {"status": "solved", "value": 84_000.0,
                                       "tolerance": 8.4, "proved": True, "ages": [804, 804]},
                       "66y0m/67y0m": {"status": "solved", "value": 83_997.0,
                                       "tolerance": 8.4, "proved": True, "ages": [792, 804]},
                       "70y0m/67y0m": {"status": "solved", "value": 83_500.0,
                                       "tolerance": 8.4, "proved": True, "ages": [840, 804]},
                   }}]
        (run.path / "scores.json").write_text(json.dumps(scores), encoding="utf-8")
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "Claiming-age map" in text
        assert "Reading `scores.json` from the run folder" in text
        assert "3 scored plan(s)" in text and "2 shade(s)" in text
        assert at.selectbox(key="run_page_age_variant"), "the variant picker did not render"

    def test_without_a_scores_file_the_map_asks_for_one(self, library):
        at = _page("Run.py")
        assert "Claiming-age map" in _text(at)
        assert any(u.label.startswith("A work_sweep scores file") for u in at.get("file_uploader"))

    def test_the_map_reads_the_scores_an_ages_thorough_solve_wrote(self, library):
        """The `ages_thorough` preset writes `scores.json` with its solve (its results
        folder); the map finds the newest one there (I7)."""
        run = library.runs()[-1]
        scores = [{"name": "base", "free": ["Noa", "Avi"], "best": [804, 804], "sweeps": [],
                   "results": {
                       "67y0m/67y0m": {"status": "solved", "value": 84_000.0,
                                       "tolerance": 8.4, "proved": True, "ages": [804, 804]}}}]
        folder = next((run.path / "results").iterdir())
        (folder / R.SCORES_JSON).write_text(json.dumps(scores), encoding="utf-8")
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert f"Reading `scores.json` from `{folder.name}`" in text
        assert "Claiming-age map" in text

    def test_ah6_the_map_skips_a_folder_whose_solve_did_not_finish(self, library):
        """Review AH6: a sweep is read only from a folder whose record says solved (a newer
        folder holding an old attempt's scores.json beside a failed record is skipped)."""
        run = library.runs()[-1]
        scores = [{"name": "base", "free": ["Noa", "Avi"], "best": [804, 804], "sweeps": [],
                   "results": {
                       "67y0m/67y0m": {"status": "solved", "value": 84_000.0,
                                       "tolerance": 8.4, "proved": True, "ages": [804, 804]}}}]
        solved = next(p for p in (run.path / "results").iterdir()
                      if (R.read_record(p) or {}).get("status") == "solved")
        (solved / R.SCORES_JSON).write_text(json.dumps(scores), encoding="utf-8")
        failed = run.path / "results" / "2099-01-01T00-00-00_ages_thorough"
        failed.mkdir()
        (failed / R.RECORD_JSON).write_text(json.dumps({"status": "failed"}), encoding="utf-8")
        (failed / R.SCORES_JSON).write_text(json.dumps(scores), encoding="utf-8")
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert f"Reading `scores.json` from `{solved.name}`" in text
        assert failed.name not in text

    def test_a_work_variant_with_fixed_ages_draws_nothing_and_does_not_crash(self, library):
        """A work_sweep row with no free person (the claiming ages are fixed) has nothing to
        sweep: its cells carry no age tuples, and the page must say so, not raise (the
        zero-free crash, step-3 review 2, Q3)."""
        run = library.runs()[-1]  # the page's default run
        scores = [{"name": "fixed", "free": [], "best": [804, 804], "sweeps": [],
                   "results": {
                       "67y0m/67y0m": {"status": "solved", "value": 84_000.0,
                                       "tolerance": 8.4, "proved": True, "ages": [804, 804]}}}]
        (run.path / "scores.json").write_text(json.dumps(scores), encoding="utf-8")
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        assert "swept no claiming ages" in _text(at)


class TestComparePage:
    def test_two_results_are_judged_against_the_noise_rule(self, library):
        at = _page("Compare.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "difference is B - A" in text
        assert "resolved" in text  # 82,000 -> 84,000 is beyond the 1% band
        assert "~ unresolved" in text or "no difference" in text

    def test_the_two_numbers_say_leads_or_trade_off(self, library):
        at = _page("Compare.py")
        text = _text(at)
        # More spending (82,000 -> 84,000) with less home at the end (150,000 -> 120,000).
        assert "trade-off" in text

    def test_the_exact_model_agreement_check_is_shown(self, library):
        at = _page("Compare.py")
        text = _text(at)
        assert "The exact model, as a check" in text
        assert "difference in the selected pair" in text

    def test_the_inputs_difference_is_in_words(self, library):
        at = _page("Compare.py")
        text = _text(at)
        assert "case_name" in text  # diff_summaries: "case.case_name: bill -> bill later"

    def test_the_what_moved_table_is_rendered(self, library):
        at = _page("Compare.py")
        assert at.dataframe, "the 'what moved' table did not render"

    def test_the_s13_flags_are_shown(self, library):
        """Review P12: different days and commits must be flagged on the page itself."""
        folder = library.runs()[0].path / "results" / "2026-11-02T10-00-00_decision"
        record = json.loads((folder / R.RECORD_JSON).read_text(encoding="utf-8"))
        record["solve_date"]["finished"] = "2026-11-05T10:05:00+01:00"
        record["engine"]["commit"] = "1234567"
        (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")
        at = _page("Compare.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "solved on different days" in text and "run both again" in text
        assert "different Owl commits" in text


class TestTheLocalhostGuard:
    def test_library_mode_is_refused_off_localhost(self, monkeypatch):
        import streamlit as st

        import libraryjobs

        monkeypatch.setattr(st, "get_option", lambda key: "0.0.0.0")
        assert not libraryjobs.library_address_ok()
        monkeypatch.setattr(st, "get_option", lambda key: "localhost")
        assert libraryjobs.library_address_ok()
        monkeypatch.setattr(st, "get_option", lambda key: "127.0.0.1")
        assert libraryjobs.library_address_ok()


class TestTheSensitivityTornado:
    """I9 on the Run page: one child per key input moved by a set step, queued under the
    exact LP into a "Sensitivity: <run>" collection, and the effects as bars with their
    tolerances (`library.tornado` is unit-tested in tests/library/test_tornado.py)."""

    def test_the_button_makes_the_children_and_queues_them(self, library, monkeypatch):
        from owlplanner.library import JobManager

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # no real worker
        before = {j.id for j in JobManager(library).jobs()}
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        assert any(x.label == "Sensitivity (tornado)" for x in at.expander)
        assert "returns -1 point" in _text(at)  # the movers' steps, spelled out
        next(b for b in at.button if b.label == "Make the sensitivity runs").click().run()
        assert not at.exception, [e.value for e in at.exception]
        coll = next(c for c in library.collections() if c.name.startswith("Sensitivity:"))
        values = [m.values for m in coll.members]
        assert {"mover": "returns -1 point"} in values
        assert {"mover": "Bill dies at 80"} in values
        child = next(r for r in library.runs() if r.name.startswith("bill later "))
        assert child.parent == next(r for r in library.runs() if r.name == "bill later").id
        queued = [j for j in JobManager(library).jobs() if j.id not in before]
        # The exact LP for every child but medical inflation's, which solves with Medicare
        # priced exactly, as does the run's own base for that bar (review AJ1).
        assert queued and {j.doc["preset"] for j in queued} == {"decision_exact", "exact_medicare"}
        medical = next(r for r in library.runs() if r.name.endswith(" medical+2"))
        parent = next(r for r in library.runs() if r.name == "bill later")
        medicare = {(j.doc["run_id"], j.doc["preset"]) for j in queued
                    if j.doc["preset"] == "exact_medicare"}
        assert medicare == {(medical.id, "exact_medicare"), (parent.id, "exact_medicare")}

    def test_the_bars_come_with_their_tolerances(self, library, monkeypatch):
        from owlplanner.library import JobManager
        from streamlit.testing.v1 import AppTest

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)
        at = _page("Run.py")
        next(b for b in at.button if b.label == "Make the sensitivity runs").click().run()
        assert not at.exception, [e.value for e in at.exception]
        coll = next(c for c in library.collections() if c.name.startswith("Sensitivity:"))
        for i, member in enumerate(coll.members):
            child = library.get(member.run)
            _write_result(child, f"2026-11-04T10-00-0{i}_decision_exact", preset="decision_exact",
                          exact=True, score=82_000.0 - 3_000 * i)
        # A fresh render defaults to the newest run (a tornado child now): open the parent.
        parent = next(r for r in library.runs() if r.name == "bill later")
        at = AppTest.from_file(str(UI_DIR / "Run.py"), default_timeout=90)
        at.session_state["cases"] = {}
        at.session_state["currentCase"] = None
        at.session_state["library_selected_run"] = parent.id
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        table = next(str(m.value) for m in at.markdown
                     if str(m.value).startswith("| mover | difference |"))
        assert "returns -1 point" in table and "±" in table


class TestTheTornadoReview3:
    """`fork-notes/run-library-step6-review-3.md` AG2 and AG5 on the Run page."""

    @staticmethod
    def _open(run):
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(UI_DIR / "Run.py"), default_timeout=90)
        at.session_state["cases"] = {}
        at.session_state["currentCase"] = None
        at.session_state["library_selected_run"] = run.id
        return at.run()

    def test_ag2_a_run_with_no_exact_result_gets_one_queued_and_the_bars_wait(self, library, monkeypatch):
        from owlplanner.library import JobManager, import_case

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)
        scenario = import_case(BILL)
        scenario["case"]["case_name"] = "bill quick"
        run = library.save_run(name="bill quick", scenario=scenario).run
        _write_result(run, "2026-11-02T12-00-00_quick", preset="quick")  # no exact-LP result
        before = {j.id for j in JobManager(library).jobs()}
        at = self._open(run)
        next(b for b in at.button if b.label == "Make the sensitivity runs").click().run()
        assert not at.exception, [e.value for e in at.exception]
        queued = [j for j in JobManager(library).jobs() if j.id not in before]
        assert any(j.doc["run_id"] == run.id and j.doc["preset"] == "decision_exact" for j in queued)
        coll = next(c for c in library.collections() if c.name == "Sensitivity: bill quick")
        for i, member in enumerate(m for m in coll.members if m.run != run.id):
            _write_result(library.get(member.run), f"2026-11-04T10-00-0{i}_decision_exact",
                          preset="decision_exact", exact=True, score=82_000.0 - 1_000 * i)
        at = self._open(run)
        assert not at.exception, [e.value for e in at.exception]
        assert "wait for this run's own exact-LP solve" in _text(at)
        assert not any(str(m.value).startswith("| mover | difference |") for m in at.markdown)

    def test_ag5_the_run_is_the_collection_s_reference(self, library, monkeypatch):
        from owlplanner.library import JobManager, tornado

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)
        parent = next(r for r in library.runs() if r.name == "bill later")
        at = self._open(parent)
        next(b for b in at.button if b.label == "Make the sensitivity runs").click().run()
        coll = next(c for c in library.collections() if c.name == "Sensitivity: bill later")
        assert coll.reference == parent.id
        assert coll.member(parent.id).values == {"mover": tornado.BASE_LABEL}


class TestTheTornadoReview4:
    """`fork-notes/run-library-step6-review-4.md` AI3 and AI4 on the Run page."""

    _open = staticmethod(TestTheTornadoReview3._open)

    @staticmethod
    def _make(run):
        at = TestTheTornadoReview3._open(run)
        next(b for b in at.button if b.label == "Make the sensitivity runs").click().run()
        assert not at.exception, [e.value for e in at.exception]
        return at

    @staticmethod
    def _table(at):
        return next((str(m.value) for m in at.markdown
                     if str(m.value).startswith("| mover | difference |")), None)

    @staticmethod
    def _solve_children(library, coll, parent, *, current=False):
        """Hand-written results for the children under their movers' presets (scores 69,000,
        68,000, ...; the homes 150,000 + 1,000 x i); `current` stamps them today, by the code
        running now."""
        from datetime import date

        from owlplanner.library import tornado
        from owlplanner.version import engine_provenance

        for i, member in enumerate(m for m in coll.members if m.run != parent.id):
            child = library.get(member.run)
            preset = tornado.preset_of(member.values["mover"])  # review AJ1: its own model
            folder = _write_result(child, f"2026-11-04T10-00-0{i}_{preset}",
                                   preset=preset, exact=True, score=69_000.0 - 1_000 * i,
                                   home=150_000.0 + 1_000 * i,
                                   finished=(f"{date.today().isoformat()}T10:00:00+00:00" if current
                                             else "2026-11-04T10:00:00+00:00"))
            if current:
                record = json.loads((folder / R.RECORD_JSON).read_text(encoding="utf-8"))
                record["engine"] = engine_provenance()
                (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")

    def test_ai3_a_second_run_of_the_same_name_has_no_bars_of_the_first(self, library, monkeypatch):
        from owlplanner.library import JobManager, import_case, tornado

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)
        first = next(r for r in library.runs() if r.name == "bill later")
        self._make(first)
        coll = tornado.collection_of(library, first.id)
        assert coll.tornado_of == first.id
        self._solve_children(library, coll, first)
        scenario = import_case(BILL)
        scenario["case"]["case_name"] = "bill later, another case"
        second = library.save_run(name="bill later", scenario=scenario).run
        _write_result(second, "2026-11-02T12-30-00_decision_exact", preset="decision_exact",
                      score=90_000.0, exact=True)
        at = self._open(second)
        assert not at.exception, [e.value for e in at.exception]
        assert self._table(at) is None  # it used to draw the first run's children
        assert tornado.collection_of(library, second.id) is None

    def test_ai3_a_rename_keeps_the_bars_and_a_second_click_queues_no_current_child(
            self, library, monkeypatch):
        from owlplanner.library import JobManager, tornado

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)
        run = next(r for r in library.runs() if r.name == "bill later")
        self._make(run)
        coll = tornado.collection_of(library, run.id)
        self._solve_children(library, coll, run, current=True)
        run = library.rename_run(run, "bill baseline")
        assert self._table(self._open(run)) is not None  # the bars survive the rename
        before = {j.id for j in JobManager(library).jobs()}
        self._make(run)
        queued = [j for j in JobManager(library).jobs() if j.id not in before]
        children = {m.run for m in coll.members if m.run != run.id}
        assert not [j for j in queued if j.doc["run_id"] in children]
        assert len([c for c in library.collections() if c.tornado_of == run.id]) == 1

    def test_ai4_the_table_shows_the_home_at_the_end(self, library, monkeypatch):
        from owlplanner.library import JobManager, tornado

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)
        run = next(r for r in library.runs() if r.name == "bill later")
        self._make(run)
        self._solve_children(library, tornado.collection_of(library, run.id), run)
        table = self._table(self._open(run))
        assert "| home at the end |" in table.splitlines()[0]
        # The base's exact-LP home is the fixture's 150,000; the children's 150,000 + 1,000 x i.
        assert "| ±0 |" in table and "| +1,000 |" in table


class TestTheTornadoReview5:
    """`fork-notes/run-library-step6-review-5.md` AJ1 on the Run page: the medical-inflation
    bar is measured against the run's own solve with Medicare priced exactly, and that solve
    never becomes the run's headline result."""

    _open = staticmethod(TestTheTornadoReview3._open)
    _make = staticmethod(TestTheTornadoReview4._make)
    _table = staticmethod(TestTheTornadoReview4._table)

    def test_aj1_the_medical_bar_reads_the_medicare_base(self, library, monkeypatch):
        from owlplanner.library import JobManager, tornado

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)
        run = next(r for r in library.runs() if r.name == "bill later")
        self._make(run)
        coll = tornado.collection_of(library, run.id)
        TestTheTornadoReview4._solve_children(library, coll, run)
        # The run's own exact-LP base is the fixture's (72,500); its Medicare-priced base:
        _write_result(run, "2026-11-04T12-00-00_exact_medicare", preset="exact_medicare",
                      exact=True, score=70_000.0, finished="2026-11-04T10:00:00+00:00")
        at = self._open(run)
        assert not at.exception, [e.value for e in at.exception]
        rows = {line.split("|")[1].strip(): line for line in self._table(at).splitlines()[2:]}
        medical = rows[tornado.MEDICAL_LABEL]
        # Its child is the third mover (69,000 - 2 x 1,000 = 67,000), against 70,000, not 72,500.
        assert "| -3,000 |" in medical and "Medicare priced exactly" in medical
        assert "| exact LP |" in rows["returns -1 point"]
        # The headline stays the case's own model: the newest solve is the companion's.
        assert "decision" in str(at.selectbox(key="run_page_result").value)
        assert "exact_medicare" not in str(at.selectbox(key="run_page_result").value)


class TestConversionsAndBrackets:
    """I8 on the run page: the income, the conversion layer and the lines it fills
    (plan.json's `brackets` block), and the per-request regret sweep button."""

    def test_the_view_shows_the_income_the_conversions_and_the_lines(self, library):
        at = _page("Run.py")
        assert not at.exception, [e.value for e in at.exception]
        text = _text(at)
        assert "Conversions and brackets" in text
        assert "of which taxable" in text  # the table's column (review AI1)
        assert "Run the regret sweep" in [b.label for b in at.button]

    def test_ai1_the_chart_stacks_the_taxable_part_and_draws_magi(self, library):
        """Review AI1: a conversion larger than the year's taxable income (the deduction
        absorbs the rest) is stacked at its taxable part, not gross, and MAGI is drawn for the
        IRMAA and cliff lines to be read against (in 2028 on the synthetic household the bar
        sat 33k under the cliff while MAGI was 37k over it). A plan.json from before the fold
        (no `conversion_taxable`) gets the same cap."""
        from streamlit.testing.v1 import AppTest

        run = next(r for r in library.runs() if r.name == "bill later")
        folder = next(p for p in (run.path / "results").iterdir() if p.name.endswith("_decision"))
        plan = json.loads((folder / R.PLAN_JSON).read_text(encoding="utf-8"))
        rows = plan["brackets"]["years"]
        for row in rows:
            row.update({"ordinary_taxable_income": 24_800.0, "conversion": 51_455.0,
                        "magi": 121_355.0, "room_to_next_edge": 76_000.0,
                        "fills_bracket": "10% (full)",
                        "aca_lines": [{"label": "400% FPL (the subsidy cliff)", "amount": 84_202.0}]})
        rows[0]["conversion_taxable"] = 24_800.0  # the second row is a pre-fold one
        (folder / R.PLAN_JSON).write_text(json.dumps(plan), encoding="utf-8")
        at = AppTest.from_file(str(UI_DIR / "Run.py"), default_timeout=90)
        at.session_state["cases"] = {}
        at.session_state["currentCase"] = None
        at.session_state["library_selected_run"] = run.id
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        charts = [json.loads(c.proto.spec) for c in at.get("plotly_chart")]
        chart = next(c for c in charts if any(t.get("name", "").startswith("Roth conversions")
                                              for t in c.get("data") or []))
        traces = {t["name"]: t for t in chart["data"]}
        conv = traces["Roth conversions (their taxable part)"]["y"]
        ex = traces["taxable income, ex conversions"]["y"]
        assert list(conv) == [24_800.0, 24_800.0] and list(ex) == [0.0, 0.0]
        magi = next(t for name, t in traces.items() if name.startswith("MAGI"))
        assert list(magi["y"]) == [121_355.0, 121_355.0]
        table = next(str(m.value) for m in at.markdown if "| of which taxable |" in str(m.value))
        assert "| 51,455 | 24,800 | 121,355 | 10% (full) |" in table

    def test_ag7_ag10_the_caption_reads_the_valley_and_names_the_person(self, library):
        """Review AG7: the summary's key is `mean_regret` (the caption always said 0);
        AG10: whose first-year conversion the sweep pinned."""
        import numpy as np
        from streamlit.testing.v1 import AppTest
        from owlplanner import summarize_conversion_regret

        grid = np.array([0.0, 25_000.0, 50_000.0])
        v_at = np.array([[1000.0, 1200.0, 1100.0], [900.0, 1300.0, 1000.0]])
        summary = summarize_conversion_regret({
            "grid": grid, "v_at": v_at, "v_star": v_at.max(axis=1) + 150.0,
            "x_star": grid[v_at.argmax(axis=1)], "v_noconv": v_at[:, 0]})
        summary = json.loads(json.dumps(summary, default=float))
        summary["person"] = "Noa"
        assert summary["valley"]["mean_regret"] == 150.0
        run = next(r for r in library.runs() if r.name == "bill later")
        folder = next(p for p in (run.path / "results").iterdir() if p.name.endswith("_decision"))
        record = json.loads((folder / R.RECORD_JSON).read_text(encoding="utf-8"))
        record["regret"] = summary
        (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")
        at = AppTest.from_file(str(UI_DIR / "Run.py"), default_timeout=90)
        at.session_state["cases"] = {}
        at.session_state["currentCase"] = None
        at.session_state["library_selected_run"] = run.id
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        least = next(c.value for c in at.caption if "Least regret" in c.value)
        assert "mean regret 150" in least and "Noa's first-year conversion" in least
        # Review AH4: the curve is drawn from the summarizer's own key, `regret_by_grid`.
        charts = [json.loads(c.proto.spec) for c in at.get("plotly_chart")]
        assert any("mean regret" in json.dumps(((c.get("layout") or {}).get("yaxis") or {}).get("title"))
                   for c in charts), "the regret curve was not drawn"

    def test_ah1_the_ages_thorough_caption_names_the_sweep_s_scorer(self, library):
        """Review AH1: an "Ages, thorough" result says the candidates were scored by
        branch-and-bound and that the plan is the decided cell re-solved the same way, with
        both values."""
        from streamlit.testing.v1 import AppTest

        run = next(r for r in library.runs() if r.name == "bill later")
        folder = next(p for p in (run.path / "results").iterdir() if p.name.endswith("_decision"))
        record = json.loads((folder / R.RECORD_JSON).read_text(encoding="utf-8"))
        record["preset"] = "ages_thorough"
        record["age_search"] = {"chosen": [66.1667, 70.0], "candidates": [[[66.0, 70.0], 1.0]],
                                "decided": {"used": "branch-and-bound", "value": 165_361.78,
                                            "proved": True, "gap": 1e-5},
                                "published_value": 165_361.78}
        (folder / R.RECORD_JSON).write_text(json.dumps(record), encoding="utf-8")
        at = AppTest.from_file(str(UI_DIR / "Run.py"), default_timeout=90)
        at.session_state["cases"] = {}
        at.session_state["currentCase"] = None
        at.session_state["library_selected_run"] = run.id
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        caption = next(c.value for c in at.caption if "Claiming ages searched" in c.value)
        assert "'Ages, thorough'" in caption and "branch-and-bound at gap 1e-5" in caption
        assert "re-solved the same way" in caption and "165,361.78" in caption
        assert "under the case's own model" not in caption

    def test_the_regret_button_queues_one_job(self, library, monkeypatch):
        from owlplanner.library import JobManager

        monkeypatch.setattr(JobManager, "_spawn", lambda self, job: False)  # no real worker
        before = {j.id for j in JobManager(library).jobs()}
        at = _page("Run.py")
        next(b for b in at.button if b.label == "Run the regret sweep").click().run()
        assert not at.exception, [e.value for e in at.exception]
        queued = [j for j in JobManager(library).jobs() if j.id not in before]
        assert [j.doc["preset"] for j in queued] == ["regret"]

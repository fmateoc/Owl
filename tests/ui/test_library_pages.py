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
    R.JobRecord.create(folder, run_id=run.id, run_name=run.name, preset=preset, options={},
                       plan_year=run.plan_year)
    options = ({"breakpointMethod": "loop", "withMedicare": "none",
                "withSSTaxability": 0.85, "withLTCG": "optimize"} if exact
               else {"breakpointMethod": "local-search", "withSSAges": "fixed"})
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

    def test_edit_as_new_run_opens_the_frozen_files(self, library):
        at = _page("Run.py")
        button = next(b for b in at.button if b.label == "Edit as new run")
        button.click().run()
        assert not at.exception, [e.value for e in at.exception]
        # The case pages hold the run's inputs, and saving will make a child of *this* run.
        assert at.session_state["library_base_run_id"] == library.runs()[-1].id

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
        assert "in, the same" in text and "Roth conversion is a move between accounts" in text

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

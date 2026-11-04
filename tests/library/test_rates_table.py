"""The run's rates table (step 5b, D11): a hand table, the downturn event that generates one
(I11), and what the frozen files carry.

Covers:
- a hand table: stored in the scenario, written as `rates.csv`, named by the generated
  `Case.toml`, and re-imported to the same inputs hash (T1);
- the downturn event: the sequence's window overlaid at its placement (plain years and
  anchors), the baseline kept outside it, the generated case fields marked with the event,
  and the refusal to mix a sequence with a hand table;
- the schema's two consistency rules between the table and the case dictionary;
- a pages save: the table and the events survive it untouched (the pages edit neither);
- the review's fixes (Z2-Z7, `run-library-step5b-review.md`): one table per export, a seedless
  stochastic baseline refused, the two workflows the pages recommend, a placement outside the
  plan refused, hostile CSV input, and the sequence windows in the inputs hash.
"""

import copy
from pathlib import Path

import numpy as np
import pytest

from owlplanner.config import config_to_plan, load_toml
from owlplanner.config.toml_io import save_toml
from owlplanner.config.ui_bridge import config_to_ui
from owlplanner.library import ScenarioError, canonicalize, export_case, import_case, scenario_hash
from owlplanner.library import builder as b
from owlplanner.library import scenario as sc
from owlplanner.library.casefiles import scenario_from_case, scenario_from_ui
from owlplanner.library.sequences import sequences

CASE = str(Path(__file__).resolve().parents[2] / "examples" / "Case_jack+jill.toml")
HFP = str(Path(__file__).resolve().parents[2] / "examples" / "HFP_jack+jill.xlsx")
CRASH = [-30.0, 2.0, 1.0, 2.0]  # sequences()["crash-30"]["window"][0]


def _rows(first=2026, last=2070):
    """A hand table that covers any plan horizon these tests can ask for."""
    return {
        "columns": ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"],
        "rows": [[year] + (CRASH if year == 2030 else [6.0, 4.5, 3.0, 2.0])
                 for year in range(first, last + 1)],
    }


def _table_case(tmp_path, table=None, selection=None):
    """A case file whose rates come from a rates.csv beside it (as a run's inputs hold it)."""
    import shutil

    table = _rows() if table is None else table
    case, _, _ = load_toml(CASE)
    case["rates_selection"] = selection or {"method": "table", "rates_file": "rates.csv"}
    shutil.copy(HFP, tmp_path / "HFP_jack+jill.xlsx")
    path = tmp_path / "Case_table.toml"
    save_toml(case, str(path))
    with open(tmp_path / "rates.csv", "w", encoding="utf-8") as f:
        f.write(",".join(table["columns"]) + "\n")
        for row in table["rows"]:
            f.write(",".join(str(v) for v in row) + "\n")
    return path


def _stub_plan(first=2026, years=45, stocks=6.0, cpi=2.0):
    """The baseline rate path `_generated_rates` overlays on: constant rates, known years."""
    import types

    return types.SimpleNamespace(
        year_n=list(range(first, first + years)),
        tau_kn=np.array([[stocks / 100] * years, [0.045] * years, [0.03] * years, [cpi / 100] * years]),
    )


def _downturn(start, sequence="three-negative-years"):
    """A scenario with one downturn event at a plain year (no other case content)."""
    return {"schema_version": 3, "plan_year": 2026, "case": {"case_name": "x"}, "hfp": {},
            "events": [{"id": "s", "kind": "downturn", "sequence": sequence, "start": start}]}


def _sequence_file(path, window):
    """A downturn_sequences.toml with one named sequence at `window` (a one-row table)."""
    rows = "".join(f"[{', '.join(str(v) for v in row)}],\n" for row in window)
    path.write_text(
        "[sequences.test-seq]\n"
        'description = "a test sequence"\n'
        'source = "invented for the test"\n'
        f"window = [\n{rows}]\n",
        encoding="utf-8",
    )


@pytest.fixture
def stub_baseline(monkeypatch):
    monkeypatch.setattr(b, "_throwaway_plan", lambda case, rates_rows=None: _stub_plan())


class TestHandTable:
    def test_the_import_stores_the_table_and_the_files_carry_it(self, tmp_path):
        scenario = import_case(_table_case(tmp_path), hfp_path=HFP)
        assert scenario["rates_table"]["columns"] == ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"]
        assert scenario["rates_table"]["rows"][4] == [2030] + CRASH

        out = tmp_path / "inputs"
        written = {p.name for p in export_case(scenario, out)}
        assert written == {"Case.toml", "HFP.xlsx", "rates.csv"}
        case, _, _ = load_toml(str(out / "Case.toml"))
        assert case["rates_selection"]["method"] == "table"
        assert case["rates_selection"]["rates_file"] == "rates.csv"
        assert (out / "rates.csv").read_text(encoding="utf-8").splitlines()[5] == "2030,-30,2,1,2"

    def test_a_round_trip_reimports_identically(self, tmp_path):
        scenario = import_case(_table_case(tmp_path), hfp_path=HFP)
        out = tmp_path / "inputs"
        export_case(scenario, out)
        again = import_case(out / "Case.toml")
        assert scenario_hash(again) == scenario_hash(scenario)

    def test_owlcli_reads_the_same_rates(self, tmp_path):
        """The step's acceptance in small: `owlcli run` loads the frozen files the same way."""
        scenario = import_case(_table_case(tmp_path), hfp_path=HFP)
        out = tmp_path / "inputs"
        export_case(scenario, out)
        case, dirname, _ = load_toml(str(out / "Case.toml"))
        plan = config_to_plan(case, dirname, verbose=False, loadHFP=True)
        assert plan.rateMethod == "table"
        table = {row[0]: row[1:] for row in scenario["rates_table"]["rows"]}
        for k, year in enumerate(plan.year_n):
            assert list(np.round(100 * plan.tau_kn[:, k], 4)) == table[int(year)]

    def test_a_name_outside_the_run_is_normalized(self, tmp_path):
        case, _, _ = load_toml(CASE)
        case["rates_selection"] = {"method": "table", "rates_file": "my rates.csv"}
        path = tmp_path / "Case_table.toml"
        save_toml(case, str(path))
        table = _rows()
        with open(tmp_path / "my rates.csv", "w", encoding="utf-8") as f:
            f.write(",".join(table["columns"]) + "\n")
            for row in table["rows"]:
                f.write(",".join(str(v) for v in row) + "\n")
        scenario = import_case(path, hfp_path=HFP)
        assert scenario["case"]["rates_selection"]["rates_file"] == "rates.csv"


class TestValidate:
    def test_a_table_needs_the_case_to_name_it(self):
        doc = {"schema_version": 3, "plan_year": 2026,
               "case": {"case_name": "x", "rates_selection": {"method": "historical_average"}},
               "hfp": {}, "rates_table": _rows(first=2026, last=2027)}
        with pytest.raises(ScenarioError, match="must name method = 'table'"):
            sc.validate(doc)

    def test_a_named_table_must_be_present(self):
        doc = {"schema_version": 3, "plan_year": 2026,
               "case": {"case_name": "x", "rates_selection": {"method": "table", "rates_file": "rates.csv"}},
               "hfp": {}}
        with pytest.raises(ScenarioError, match="holds none"):
            sc.validate(doc)

    def test_the_table_is_shape_checked(self):
        doc = {"schema_version": 3, "plan_year": 2026,
               "case": {"case_name": "x", "rates_selection": {"method": "table"}}, "hfp": {},
               "rates_table": {"columns": ["year", "S&P 500"], "rows": [[2026]]}}
        with pytest.raises(ScenarioError, match="rates_table row"):
            sc.validate(doc)


class TestDownturn:
    def test_the_window_sits_at_the_placement_and_the_baseline_elsewhere(self, stub_baseline):
        scenario = {"schema_version": 3, "plan_year": 2026,
                    "case": {"case_name": "x", "rates_selection": {"method": "historical_average"}},
                    "hfp": {},
                    "events": [{"id": "stress", "kind": "downturn", "sequence": "crash-30", "start": 2030}]}
        table = b.rates_table(scenario)
        rows = {row[0]: row[1:] for row in table["rows"]}
        assert rows[2030] == CRASH
        assert rows[2029] == [6.0, 4.5, 3.0, 2.0] and rows[2031] == [6.0, 4.5, 3.0, 2.0]
        assert table["columns"] == ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"]

    def test_the_window_reaches_as_far_as_the_sequence(self, stub_baseline):
        scenario = {"schema_version": 3, "plan_year": 2026,
                    "case": {"case_name": "x"}, "hfp": {},
                    "events": [{"id": "s", "kind": "downturn", "sequence": "three-negative-years",
                                "start": 2040}]}
        rows = {row[0]: row[1:] for row in b.rates_table(scenario)["rows"]}
        window = sequences()["three-negative-years"]["window"]
        for i, values in enumerate(window):
            assert rows[2040 + i] == values

    def test_a_window_past_the_plan_end_is_ignored(self, stub_baseline):
        short = {"schema_version": 3, "plan_year": 2026, "case": {"case_name": "x"}, "hfp": {},
                 "events": [{"id": "s", "kind": "downturn", "sequence": "three-negative-years",
                             "start": 2069}]}
        rows = {row[0]: row[1:] for row in b.rates_table(short)["rows"]}
        window = sequences()["three-negative-years"]["window"]
        assert rows[2069] == window[0] and rows[2070] == window[1]
        assert 2071 not in rows  # the stub's plan ends at 2070; the third window year is unused

    def test_an_anchor_places_it(self, stub_baseline):
        scenario = import_case(CASE)
        scenario["events"] = [{"id": "s", "kind": "downturn", "sequence": "crash-30",
                               "start": {"anchor": "age", "person": "Jack", "age": 70}}]
        born = int(str(scenario["case"]["basic_info"]["date_of_birth"][0])[:4])
        rows = {row[0]: row[1:] for row in b.rates_table(scenario)["rows"]}
        assert rows[born + 70] == CRASH

    def test_the_generated_case_fields_are_marked_with_the_event(self, stub_baseline):
        scenario = import_case(CASE)
        scenario["events"] = [{"id": "stress", "kind": "downturn", "sequence": "crash-30", "start": 2030}]
        case, _tables, provenance = b.build(scenario)
        assert case["rates_selection"]["method"] == "table"
        assert case["rates_selection"]["rates_file"] == "rates.csv"
        assert provenance["case_fields"] == {"rates_selection.method": "stress",
                                             "rates_selection.rates_file": "stress"}

    def test_build_is_deterministic(self, stub_baseline):
        scenario = import_case(CASE)
        scenario["events"] = [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]
        assert b.rates_table(scenario) == b.rates_table(scenario)

    def test_a_hand_table_and_a_sequence_refuse_to_coexist(self, stub_baseline):
        scenario = {"schema_version": 3, "plan_year": 2026, "case": {"case_name": "x",
                    "rates_selection": {"method": "table"}}, "hfp": {}, "rates_table": _rows(2026, 2027),
                    "events": [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]}
        with pytest.raises(ScenarioError, match="drop one"):
            b.rates_table(scenario)

    def test_a_sequence_on_a_table_case_is_refused(self, stub_baseline):
        scenario = {"schema_version": 3, "plan_year": 2026,
                    "case": {"case_name": "x", "rates_selection": {"method": "table"}}, "hfp": {},
                    "events": [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]}
        with pytest.raises(ScenarioError, match="edit the table itself"):
            b.rates_table(scenario)

    def test_an_unknown_sequence_is_refused(self):
        with pytest.raises(ScenarioError, match="sequence"):
            b.validate_events([{"id": "s", "kind": "downturn", "sequence": "nope", "start": 2030}], [])

    def test_the_names_are_the_data_files(self):
        names = sorted(sequences())
        assert ["crash-30", "poor-decade", "three-negative-years"] == names
        for entry in sequences().values():
            assert entry["source"] and entry["description"]
            assert all(len(row) == 4 for row in entry["window"])


class TestRealBaseline:
    def test_the_overlay_sits_on_the_cases_own_rates(self):
        """The real path (no stub): the baseline is the case's own method, as the solve sees it."""
        scenario = import_case(CASE)
        baseline = b._throwaway_plan(scenario["case"])
        scenario["events"] = [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]
        rows = {row[0]: row[1:] for row in b.rates_table(scenario)["rows"]}
        for k, year in enumerate(baseline.year_n):
            expected = CRASH if int(year) == 2030 else list(np.round(100 * baseline.tau_kn[:, k], 4))
            assert rows[int(year)] == expected

    def test_the_gamma_of_a_table_run_is_the_tables_inflation(self):
        """A downturn overlay moves the plan's prices, so it moves the nominal amounts (step 5b)."""
        scenario = import_case(CASE)
        case = copy.deepcopy(scenario["case"])
        case["rates_selection"] = {"method": "table", "rates_file": "rates.csv"}
        rows = [[year, 6.0, 4.5, 3.0, 5.0] for year in range(2026, 2071)]
        gamma = b._gamma(case, rates_rows=rows)
        assert gamma[1] == pytest.approx(1.05)
        assert gamma[2] == pytest.approx(1.05**2, rel=1e-9)


class TestPagesSave:
    def test_a_pages_save_keeps_the_table(self, tmp_path):
        base = import_case(_table_case(tmp_path), hfp_path=HFP)
        case, dirname, _ = load_toml(str(tmp_path / "Case_table.toml"))
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        uidic = config_to_ui(copy.deepcopy(case))
        assert uidic["rateType"] == "table" and uidic["ratesFile"] == "rates.csv"

        scenario = scenario_from_ui(uidic, plan, base=base)
        assert scenario["rates_table"] == base["rates_table"]
        assert scenario_hash(scenario) == scenario_hash(base)

    def test_a_pages_save_keeps_the_downturn_events(self, monkeypatch):
        from owlplanner.library import builder

        monkeypatch.setattr(builder, "_throwaway_plan", lambda case, rates_rows=None: _stub_plan())
        base = import_case(CASE)
        base = dict(base, events=[{"id": "stress", "kind": "downturn", "sequence": "crash-30",
                                   "start": 2030}])
        base = canonicalize(base)
        case, dirname, _ = load_toml(CASE)
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        uidic = config_to_ui(copy.deepcopy(base["case"]))
        scenario = scenario_from_ui(uidic, plan, base=base)
        assert scenario["events"] == base["events"]
        assert "rates_table" not in scenario  # generated from the event, not stored (section 6.3)
        assert scenario_hash(scenario) == scenario_hash(base)


class TestScenarioFromCase:
    def test_a_table_needs_the_case_to_agree(self):
        with pytest.raises(ScenarioError, match="must name method = 'table'"):
            scenario_from_case({"case_name": "x", "rates_selection": {"method": "user"}}, {},
                               rates_table=_rows(2026, 2027))


class TestReviewFixesZ:
    """`fork-notes/run-library-step5b-review.md` Z2-Z4, Z6-Z7 (Z1's twin, Z5 and Z6's reader
    live in `tests/rate_models/test_rate_model_table.py`). Each test was checked to fail
    before the fix it names."""

    @staticmethod
    def _stochastic(**extra):
        """A downturn run whose baseline rate method draws at every build (the case
        `test_builder.py`'s `_histochastic` makes, with this file's downturn event)."""
        scenario = import_case(CASE)
        rates = scenario["case"]["rates_selection"]
        rates.clear()
        rates.update({"method": "histochastic", "from": 1970, "to": 2000, **extra})
        return canonicalize(dict(scenario, events=[{"id": "s", "kind": "downturn",
                                                    "sequence": "crash-30", "start": 2030}]))

    # -- Z2: one export freezes one table --------------------------------

    def test_z2_a_seeded_baseline_exports_byte_identical_rates(self, tmp_path):
        scenario = self._stochastic(reproducible_rates=True, rate_seed=1234)
        export_case(scenario, tmp_path / "one")
        export_case(scenario, tmp_path / "two")
        assert ((tmp_path / "one" / "rates.csv").read_bytes()
                == (tmp_path / "two" / "rates.csv").read_bytes())

    def test_z2_a_seedless_baseline_is_refused(self):
        scenario = self._stochastic(reproducible_rates=True)  # `rate_seed` absent
        with pytest.raises(ScenarioError, match="the case must fix its seed"):
            b.build(scenario)

    def test_z2_one_export_computes_one_table(self, tmp_path, monkeypatch):
        """The `probe_review_z2.py` scenario: the written rates.csv is the very table build()
        priced the nominal amounts with (one `rates_table()` call per export)."""
        import csv

        scenario = self._stochastic(reproducible_rates=True, rate_seed=1234)
        calls = []
        real = b.rates_table

        def spy(doc, events=None):
            out = real(doc, events=events)
            calls.append(out)
            return out

        monkeypatch.setattr(b, "rates_table", spy)
        export_case(scenario, tmp_path / "out")
        assert len(calls) == 1
        with open(tmp_path / "out" / "rates.csv", newline="", encoding="utf-8") as f:
            written = [[float(x) for x in row] for row in list(csv.reader(f))[1:]]
        assert written == [[float(x) for x in row] for row in calls[0]["rows"]]

    # -- Z3: the two workflows the pages recommend ------------------------

    def test_z3_a_no_base_save_stores_the_table_the_plan_holds(self, tmp_path):
        _table_case(tmp_path)
        case, dirname, _ = load_toml(str(tmp_path / "Case_table.toml"))
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        uidic = config_to_ui(copy.deepcopy(case))
        scenario = scenario_from_ui(uidic, plan, case_dir=str(tmp_path))
        assert scenario["rates_table"]["rows"][4] == [2030] + CRASH
        out = tmp_path / "inputs"
        export_case(scenario, out)  # the old "holds none" refusal is gone
        assert (out / "rates.csv").read_text(encoding="utf-8").splitlines()[5] == "2030,-30,2,1,2"

    def test_z3_an_explicit_rates_path_feeds_the_import(self, tmp_path):
        """The Import page's uploader: the CSV arrives with the case, not beside it."""
        case_file = _table_case(tmp_path)
        uploaded = tmp_path / "uploaded.csv"
        (tmp_path / "rates.csv").rename(uploaded)
        scenario = import_case(case_file, hfp_path=HFP, rates_path=uploaded)
        assert scenario["rates_table"]["rows"][4] == [2030] + CRASH

    # -- Z4: a placement that misses the plan must not look applied -------

    def test_z4_a_placement_in_no_plan_year_is_refused(self, stub_baseline):
        for start in (2020, 2075):  # the window before the plan, and one after it
            with pytest.raises(ScenarioError, match="lands in the plan") as exc:
                b.rates_table(_downturn(start))
            assert f"({start}-" in str(exc.value) and "(2026-2070)" in str(exc.value)

    def test_z4_a_window_cut_by_the_plan_start_is_refused(self, stub_baseline):
        with pytest.raises(ScenarioError, match="before the plan") as exc:
            b.rates_table(_downturn(2024))  # a three-year window, one year in the plan
        assert "2024" in str(exc.value) and "(2026-2070)" in str(exc.value)

    def test_z4_an_anchor_before_the_plan_is_refused(self, stub_baseline):
        scenario = import_case(CASE)
        scenario["events"] = [{"id": "s", "kind": "downturn", "sequence": "crash-30",
                               "start": {"anchor": "age", "person": "Jack", "age": 60}}]
        with pytest.raises(ScenarioError, match="lands in the plan"):
            b.rates_table(scenario)

    # -- Z6: hostile CSV input on the library path ------------------------

    def test_z6_an_excel_bom_is_read(self, tmp_path):
        case_file = _table_case(tmp_path)
        text = (tmp_path / "rates.csv").read_text(encoding="utf-8")
        (tmp_path / "rates.csv").write_text("\ufeff" + text, encoding="utf-8")
        scenario = import_case(case_file, hfp_path=HFP)
        assert scenario["rates_table"]["rows"][4] == [2030] + CRASH

    def test_z6_a_non_finite_cell_is_refused_on_import(self, tmp_path):
        case_file = _table_case(tmp_path)
        text = (tmp_path / "rates.csv").read_text(encoding="utf-8")
        (tmp_path / "rates.csv").write_text(text.replace("2027,6.0,4.5,3.0,2.0",
                                                         "2027,nan,4.5,3.0,2.0"), encoding="utf-8")
        with pytest.raises(ValueError, match="row 2027, column 'S&P 500' is not a finite number"):
            import_case(case_file, hfp_path=HFP)

    # -- Z7: the sequence window is builder input -------------------------

    def test_z7_an_edited_window_changes_the_hash_of_a_downturn_run_only(self, tmp_path, monkeypatch):
        from owlplanner.library import sequences as seq

        data = tmp_path / "downturn_sequences.toml"
        monkeypatch.setattr(seq, "SEQUENCES_FILE", data)
        _sequence_file(data, [[-30.0, 2.0, 1.0, 2.0]])
        downturn = import_case(CASE)
        downturn = canonicalize(dict(downturn, events=[{"id": "s", "kind": "downturn",
                                                        "sequence": "test-seq", "start": 2030}]))
        plain = import_case(CASE)
        before = scenario_hash(downturn), scenario_hash(plain)

        _sequence_file(data, [[-45.0, 2.0, 1.0, 2.0]])  # the window edited in place
        after = scenario_hash(downturn), scenario_hash(plain)
        assert after[0] != before[0]  # the hash sees the window the frozen rates.csv comes from
        assert after[1] == before[1]  # a run without a downturn keeps its hash

    def test_z7_sequences_see_an_edited_file_without_a_restart(self, tmp_path):
        from owlplanner.library.sequences import load_sequences

        data = tmp_path / "downturn_sequences.toml"
        _sequence_file(data, [[-30.0, 2.0, 1.0, 2.0]])
        assert load_sequences(path=data)["test-seq"]["window"] == [[-30.0, 2.0, 1.0, 2.0]]
        _sequence_file(data, [[-45.0, 2.0, 1.0, 2.0]])
        assert load_sequences(path=data)["test-seq"]["window"] == [[-45.0, 2.0, 1.0, 2.0]]


class TestReview2Fixes:
    """`fork-notes/run-library-step5b-review-2.md` AA1-AA3 (AA4-AA6 not folded). Each test was
    checked to fail before the fix it names."""

    DECIMALS = {"method": "table", "rates_file": "rates.csv", "in_percent": False}

    @staticmethod
    def _decimal_table(first=2026, last=2070):
        """A table in decimals (`in_percent = false`): -0.30 is one year's -30%."""
        return {
            "columns": ["year", "S&P 500", "Bonds Baa", "T-Notes", "Inflation"],
            "rows": [[year, -0.30 if year == 2027 else 0.06, 0.045, 0.03, 0.025]
                     for year in range(first, last + 1)],
        }

    # -- AA1: the table's units must not drift 100x ------------------------

    def test_aa1_a_no_base_save_keeps_the_table_units(self, tmp_path):
        """The review's probe2_f_import.py (f3): without the fix the frozen run re-reads the
        decimal rows as percent and its solve runs on rates 100x smaller."""
        case_file = _table_case(tmp_path, table=self._decimal_table(), selection=self.DECIMALS)
        case, dirname, _ = load_toml(str(case_file))
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        assert float(plan.tau_kn[0, 1]) == pytest.approx(-0.30)  # decimals in, decimals out

        uidic = config_to_ui(copy.deepcopy(case))
        uidic.pop("inPercent", None)  # a case-key builder that never learned the key
        scenario = scenario_from_ui(uidic, plan, case_dir=str(tmp_path))
        assert scenario["case"]["rates_selection"]["in_percent"] is False
        assert scenario["rates_table"]["rows"][1] == [2027, -0.30, 0.045, 0.03, 0.025]

        out = tmp_path / "inputs"
        export_case(scenario, out)
        frozen, frozen_dir, _ = load_toml(str(out / "Case.toml"))
        assert frozen["rates_selection"]["in_percent"] is False
        again = config_to_plan(copy.deepcopy(frozen), frozen_dir, verbose=False, loadHFP=True)
        assert float(again.tau_kn[0, 1]) == pytest.approx(-0.30)  # what the solve would use

    def test_aa1_the_pages_round_trip_keeps_the_table_units(self, tmp_path):
        """The ui keys carry `in_percent`, so the pages' pre-solve `apply_config_to_plan`
        re-prices the table in its own units (every solve re-applies the rates)."""
        from owlplanner.config.plan_bridge import apply_config_to_plan
        from owlplanner.config.ui_bridge import ui_to_config

        case_file = _table_case(tmp_path, table=self._decimal_table(), selection=self.DECIMALS)
        case, dirname, _ = load_toml(str(case_file))
        plan = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=True)
        uidic = config_to_ui(copy.deepcopy(case))
        assert uidic["inPercent"] is False  # the key crosses config_to_ui
        apply_config_to_plan(plan, ui_to_config(dict(uidic)))
        assert float(plan.tau_kn[0, 1]) == pytest.approx(-0.30)

    # -- AA3: the refusals hold however build() gets the table ------------

    def test_aa3_build_enforces_the_refusals_however_it_gets_the_table(self):
        table = _rows(2026, 2070)
        events = [{"id": "s", "kind": "downturn", "sequence": "crash-30", "start": 2030}]
        hand = {"schema_version": 3, "plan_year": 2026, "case": {"case_name": "x",
                "rates_selection": {"method": "table"}}, "hfp": {}, "rates_table": _rows(2026, 2027),
                "events": copy.deepcopy(events)}
        with pytest.raises(ScenarioError, match="drop one"):
            b.build(hand, rates_table=table)
        over_table = {"schema_version": 3, "plan_year": 2026,
                      "case": {"case_name": "x", "rates_selection": {"method": "table"}}, "hfp": {},
                      "events": copy.deepcopy(events)}
        with pytest.raises(ScenarioError, match="edit the table itself"):
            b.build(over_table, rates_table=table)

    def test_aa3_build_refuses_no_table_for_a_downturn_run(self):
        with pytest.raises(ScenarioError, match="generates its rates table"):
            b.build(_downturn(2030), rates_table=None)


class TestThirdReview:
    """The third review's AB1 and AB3 (`run-library-step5b-review-3.md`); AB2 and AB4 are page
    tests (`tests/ui/test_rates_page_table.py`)."""

    # -- AB1: a downturn over a reversed or rolled baseline -----------------

    @staticmethod
    def _transformed(extra):
        """jack+jill's `historical` case with a sequence option, its plan, and a crash at 2030."""
        case, dirname, _ = load_toml(CASE)
        case["rates_selection"].update(extra)
        parent = config_to_plan(copy.deepcopy(case), dirname, verbose=False, loadHFP=False)
        scenario = canonicalize({"schema_version": 3, "plan_year": 2026, "case": case, "hfp": {},
                                 "events": [{"id": "dn", "kind": "downturn", "sequence": "crash-30",
                                             "start": 2030}]})
        return case, parent, scenario

    @pytest.mark.parametrize("extra", [{"reverse_sequence": True}, {"roll_sequence": 5}])
    def test_ab1_the_frozen_run_sees_the_window_at_its_placement(self, tmp_path, extra):
        """Without the fix the frozen case transforms the table again: the reversed crash lands
        in 2054 and 31 of the 32 other years leave the parent's path."""
        _case, parent, scenario = self._transformed(extra)
        export_case(scenario, tmp_path)
        frozen, frozen_dir, _ = load_toml(str(tmp_path / "Case.toml"))
        run = config_to_plan(copy.deepcopy(frozen), frozen_dir, verbose=False, loadHFP=False)
        n = list(run.year_n).index(2030)
        assert float(run.tau_kn[0][n]) == pytest.approx(-0.30)
        others = [k for k in range(run.N_n) if k != n]
        assert np.allclose(run.tau_kn[:, others], parent.tau_kn[:, others], atol=1e-6)

    def test_ab1_the_reset_is_generated_and_a_pages_save_puts_the_hand_value_back(self):
        from owlplanner.library.casefiles import _drop_generated_case

        case, _parent, scenario = self._transformed({"reverse_sequence": True, "roll_sequence": 3})
        built, _tables, provenance = b.build(scenario)
        assert built["rates_selection"]["reverse_sequence"] is False
        assert built["rates_selection"]["roll_sequence"] == 0
        for field in ("rates_selection.reverse_sequence", "rates_selection.roll_sequence"):
            assert provenance["case_fields"][field] == "dn"
        saved = _drop_generated_case(built, provenance, scenario["case"])
        assert saved["rates_selection"]["reverse_sequence"] is True
        assert saved["rates_selection"]["roll_sequence"] == 3

    def test_ab1_a_case_without_the_options_is_built_as_before(self):
        _case, _parent, scenario = self._transformed({})
        built, _tables, provenance = b.build(scenario)
        assert "reverse_sequence" not in built["rates_selection"]
        assert "roll_sequence" not in built["rates_selection"]
        assert set(provenance["case_fields"]) == {"rates_selection.method", "rates_selection.rates_file"}

    # -- AB3: a stray rates.csv in the working directory --------------------

    def test_ab3_a_frozen_run_reads_its_own_table_from_any_working_directory(self, tmp_path, monkeypatch):
        """The third review's probe: a run's inputs loaded as the worker loads them, from a
        directory holding another rates.csv."""
        _case, _parent, scenario = self._transformed({})
        inputs = tmp_path / "inputs"
        export_case(scenario, inputs)
        cwd = tmp_path / "elsewhere"
        cwd.mkdir()
        (cwd / "rates.csv").write_text(
            "year,S&P 500,Bonds Baa,T-Notes,Inflation\n"
            + "".join(f"{y},99.0,0,0,0\n" for y in range(2000, 2100)), encoding="utf-8")
        monkeypatch.chdir(cwd)
        frozen, frozen_dir, _ = load_toml(str(inputs / "Case.toml"))
        run = config_to_plan(copy.deepcopy(frozen), frozen_dir, verbose=False, loadHFP=False)
        assert float(run.tau_kn[0][list(run.year_n).index(2030)]) == pytest.approx(-0.30)
        # The import reads the same file the plan reads.
        again = import_case(inputs / "Case.toml")
        assert again["rates_table"]["rows"] == scenario_from_case(
            frozen, rates_table=b.rates_table(scenario))["rates_table"]["rows"]

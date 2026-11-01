"""Scenario schema v1: canonical form, the inputs hash, validation, the change diff."""

import pytest

from owlplanner.library import scenario as sc


def _minimal(**extra):
    doc = {"schema_version": 1, "plan_year": 2026, "case": {"case_name": "x"}, "hfp": {}}
    doc.update(extra)
    return doc


class TestCanonicalJson:
    def test_key_order_does_not_change_the_text(self):
        assert sc.canonical_json({"a": 1, "b": 2}) == sc.canonical_json({"b": 2, "a": 1})

    def test_int_and_float_of_one_value_hash_the_same(self):
        as_int = _minimal(case={"case_name": "x", "n": 24000})
        as_float = _minimal(case={"case_name": "x", "n": 24000.0})
        assert sc.scenario_hash(as_int) == sc.scenario_hash(as_float)

    def test_non_finite_floats_become_null(self):
        assert sc.canonical_json({"x": float("nan")}) == '{"x":null}'
        assert sc.canonical_json({"x": float("inf")}) == '{"x":null}'

    def test_compact_separators_and_stable_text(self):
        assert sc.canonical_json({"b": [1, 2], "a": None}) == '{"a":null,"b":[1,2]}'


class TestHash:
    def test_stable_across_calls_and_key_order(self):
        one = _minimal()
        two = {"hfp": {}, "case": {"case_name": "x"}, "plan_year": 2026, "schema_version": 1}
        assert sc.scenario_hash(one) == sc.scenario_hash(two)

    def test_changes_when_a_value_changes(self):
        assert sc.scenario_hash(_minimal()) != sc.scenario_hash(_minimal(plan_year=2027))

    def test_builder_version_is_part_of_the_hash(self, monkeypatch):
        base = sc.scenario_hash(_minimal())
        monkeypatch.setattr(sc, "BUILDER_VERSION", sc.BUILDER_VERSION + 1)
        assert sc.scenario_hash(_minimal()) != base


class TestValidate:
    def test_minimal_is_valid(self):
        assert sc.validate(_minimal()) is not None

    @pytest.mark.parametrize("version", [0, 2, None, "1"])
    def test_other_schema_versions_are_rejected(self, version):
        with pytest.raises(sc.ScenarioError, match="schema_version"):
            sc.validate(_minimal(schema_version=version))

    def test_case_must_be_a_dict(self):
        with pytest.raises(sc.ScenarioError, match="case"):
            sc.validate({"schema_version": 1, "case": [], "hfp": {}})

    def test_hfp_table_shape(self):
        with pytest.raises(sc.ScenarioError, match="hfp table"):
            sc.validate(_minimal(hfp={"Joe": {"columns": ["year"], "rows": [[2026, 1]]}}))

    def test_plan_year_type(self):
        with pytest.raises(sc.ScenarioError, match="plan_year"):
            sc.validate(_minimal(plan_year="2026"))


class TestMigrate:
    def test_v1_passes_through(self):
        doc = _minimal()
        assert sc.migrate(doc) is doc

    def test_unknown_versions_raise(self):
        with pytest.raises(sc.ScenarioError, match="migration"):
            sc.migrate({"schema_version": 99})


class TestDiffSummaries:
    def test_changed_leaf(self):
        changes = sc.diff_summaries(
            {"case": {"objective": "maxSpending"}},
            {"case": {"objective": "maxBequest"}},
        )
        assert changes == ["case.objective: 'maxSpending' -> 'maxBequest'"]

    def test_added_and_removed_keys(self):
        changes = sc.diff_summaries({"case": {"a": 1, "old": 2}}, {"case": {"a": 1, "new": 3}})
        assert changes == ["case.new: added (3)", "case.old: removed (was 2)"]

    def test_list_length_is_counted_not_dumped(self):
        changes = sc.diff_summaries({"hfp": {"rows": [1, 2]}}, {"hfp": {"rows": [1, 2, 3]}})
        assert changes == ["hfp.rows: 2 -> 3 rows"]

    def test_equal_lists_are_silent(self):
        assert sc.diff_summaries({"a": [1, 2]}, {"a": [1, 2]}) == []

    def test_changes_are_capped(self):
        old = {"case": {f"k{i}": i for i in range(30)}}
        new = {"case": {f"k{i}": i + 1 for i in range(30)}}
        changes = sc.diff_summaries(old, new, limit=5)
        assert len(changes) == 6
        assert changes[-1] == "... and 25 more change(s)"

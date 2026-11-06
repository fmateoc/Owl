"""Collections (design sections 4 and 9.3, step 6): a named set of runs answering one
question, with a comparison rule -- in `library.json`, kept under `library.lock`."""

import json

import pytest

from owlplanner.library import Collection, Library, LibraryError, Member


def _scenario(marker="a"):
    return {"schema_version": 1, "plan_year": 2026, "case": {"case_name": marker}, "hfp": {}}


def _generate(scenario, inputs_dir):
    (inputs_dir / "Case.toml").write_text("generated", encoding="utf-8")


@pytest.fixture()
def lib(tmp_path):
    return Library.open(tmp_path / "library")


@pytest.fixture()
def runs(lib):
    out = []
    for marker in ("a", "b"):
        out.append(lib.save_run(name=f"run {marker}", scenario=_scenario(marker),
                                generate=_generate).run)
    return out


class TestCreate:
    def test_a_new_collection_is_empty_and_named(self, lib):
        coll = lib.create_collection("Where and when to buy",
                                     question="Maximize spending, condo kept",
                                     rule="reference: Yonkers 2027 cash")
        assert isinstance(coll, Collection) and coll.members == ()
        assert coll.name == "Where and when to buy"
        assert coll.question == "Maximize spending, condo kept"
        assert coll.rule == "reference: Yonkers 2027 cash"
        assert coll.reference is None and coll.grid == {}
        assert lib.collections() == [coll]

    def test_the_name_is_required(self, lib):
        with pytest.raises(LibraryError, match="name"):
            lib.create_collection("  ")

    def test_collections_come_back_in_the_order_created(self, lib):
        first = lib.create_collection("one")
        second = lib.create_collection("two")
        assert [c.id for c in lib.collections()] == [first.id, second.id]

    def test_an_unknown_id_is_refused(self, lib):
        with pytest.raises(LibraryError, match="no collection"):
            lib.collection("nope")


class TestMembers:
    def test_add_is_idempotent_and_keeps_values(self, lib, runs):
        coll = lib.create_collection("grid")
        coll = lib.add_member(coll.id, runs[0], {"place": "yonkers", "year": 2027})
        coll = lib.add_member(coll.id, runs[0], {"place": "yonkers", "year": 2029})
        assert len(coll.members) == 1
        assert coll.members[0] == Member(run=runs[0].id, values={"place": "yonkers", "year": 2029})
        coll = lib.add_member(coll.id, runs[1])
        assert [m.run for m in coll.members] == [runs[0].id, runs[1].id]

    def test_remove_clears_the_reference_when_it_leaves(self, lib, runs):
        coll = lib.create_collection("grid")
        lib.add_member(coll.id, runs[0])
        lib.add_member(coll.id, runs[1])
        lib.set_reference(coll.id, runs[0])
        coll = lib.remove_member(coll.id, runs[0])
        assert coll.reference is None
        assert [m.run for m in coll.members] == [runs[1].id]

    def test_the_reference_is_a_run_of_the_library(self, lib, runs):
        coll = lib.create_collection("grid")
        with pytest.raises(LibraryError, match="no run"):
            lib.set_reference(coll.id, "nope")
        coll = lib.set_reference(coll.id, runs[1])
        assert coll.reference == runs[1].id
        coll = lib.set_reference(coll.id, None)
        assert coll.reference is None

    def test_deleting_a_run_drops_it_from_every_collection(self, lib, runs):
        coll = lib.create_collection("grid")
        lib.add_member(coll.id, runs[0], {"year": 2027})
        lib.add_member(coll.id, runs[1])
        lib.set_reference(coll.id, runs[0])
        lib.delete_run(runs[0])
        coll = lib.collection(coll.id)
        assert [m.run for m in coll.members] == [runs[1].id]
        assert coll.reference is None


class TestUpdate:
    def test_the_question_rule_and_grid_are_written_on_it(self, lib):
        coll = lib.create_collection("grid")
        coll = lib.update_collection(coll.id, question="Where to buy?", rule="the score leads",
                                     grid={"rows": ["place", "financing"], "columns": ["year"]})
        assert coll.question == "Where to buy?" and coll.rule == "the score leads"
        assert coll.grid == {"rows": ["place", "financing"], "columns": ["year"]}

    def test_a_blank_name_is_refused(self, lib):
        coll = lib.create_collection("grid")
        with pytest.raises(LibraryError, match="name"):
            lib.update_collection(coll.id, name=" ")

    def test_delete_drops_the_collection_and_keeps_the_runs(self, lib, runs):
        coll = lib.create_collection("grid")
        lib.add_member(coll.id, runs[0])
        lib.delete_collection(coll.id)
        assert lib.collections() == []
        assert [r.id for r in lib.runs()] == [runs[0].id, runs[1].id]
        with pytest.raises(LibraryError, match="no collection"):
            lib.delete_collection(coll.id)


class TestOnDisk:
    def test_a_malformed_entry_is_skipped_not_fatal(self, lib):
        lib.create_collection("good")
        path = lib.root / "library.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["collections"]["broken"] = ["not", "a", "dict"]
        path.write_text(json.dumps(doc), encoding="utf-8")
        assert [c.name for c in lib.collections()] == ["good"]

    def test_the_file_is_one_plain_document(self, lib, runs):
        coll = lib.create_collection("grid", question="q", rule="r")
        lib.add_member(coll.id, runs[0], {"year": 2027})
        lib.set_reference(coll.id, runs[0])
        doc = json.loads((lib.root / "library.json").read_text(encoding="utf-8"))
        entry = doc["collections"][coll.id]
        assert entry["question"] == "q" and entry["rule"] == "r"
        assert entry["members"] == [{"run": runs[0].id, "values": {"year": 2027}}]
        assert entry["reference"] == runs[0].id
        assert doc["collection_order"] == [coll.id]


class TestJoinCollection:
    """Review AG6: the save dialogs' "Collection" field joins a run without wiping the
    variant values it already has as a member (`add_member` replaces them)."""

    def test_a_member_keeps_its_values(self, lib, runs):
        coll = lib.create_collection("grid")
        lib.add_member(coll.id, runs[0], {"place": "yonkers", "year": 2027})
        coll = lib.join_collection(coll.id, runs[0])
        assert list(coll.members) == [Member(run=runs[0].id, values={"place": "yonkers", "year": 2027})]

    def test_a_new_run_joins_with_no_values(self, lib, runs):
        coll = lib.create_collection("grid")
        coll = lib.join_collection(coll.id, runs[1])
        assert [(m.run, m.values) for m in coll.members] == [(runs[1].id, {})]

    def test_an_unknown_collection_is_refused(self, lib, runs):
        with pytest.raises(LibraryError, match="no collection"):
            lib.join_collection("nope", runs[0])

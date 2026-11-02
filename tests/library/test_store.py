"""Library storage: run folders, the inputs hash dedupe, save-as, lineage, the lock."""

import json
import os
import subprocess
import sys
import threading
import time

import pytest

from owlplanner.library import Library, LibraryError, LibraryLocked
from owlplanner.library.store import STAGING_STALE_SECONDS


def _scenario(marker="a"):
    return {"schema_version": 1, "plan_year": 2026, "case": {"case_name": marker}, "hfp": {}}


def _generate(scenario, inputs_dir):
    (inputs_dir / "Case.toml").write_text("generated", encoding="utf-8")


@pytest.fixture()
def lib(tmp_path):
    return Library.open(tmp_path / "library")


class TestLayout:
    def test_open_creates_the_layout(self, tmp_path):
        Library.open(tmp_path / "library")
        assert (tmp_path / "library" / "library.json").exists()
        assert (tmp_path / "library" / "runs").is_dir()
        assert (tmp_path / "library" / "trash").is_dir()

    def test_open_without_create_rejects_a_plain_folder(self, tmp_path):
        (tmp_path / "plain").mkdir()
        with pytest.raises(LibraryError, match="not a library"):
            Library.open(tmp_path / "plain", create=False)

    def test_corrupt_library_json_is_reported(self, tmp_path):
        root = tmp_path / "library"
        root.mkdir()
        (root / "library.json").write_text("{", encoding="utf-8")
        with pytest.raises(LibraryError, match="cannot read"):
            Library.open(root, create=False)


class TestSaveRun:
    def test_save_writes_run_and_inputs(self, lib):
        result = lib.save_run(name="wp 2029 mortgage", scenario=_scenario(), generate=_generate)
        assert result.created and result.identical_to is None
        assert result.run.name == "wp 2029 mortgage"
        assert result.run.parent is None
        assert result.run.plan_year == 2026
        assert result.run.inputs_hash
        inputs = result.run.path / "inputs"
        assert (inputs / "scenario.json").exists()
        assert (inputs / "Case.toml").exists()
        assert lib.get(result.run.id) == result.run

    def test_folder_name_is_slug_and_date(self, lib):
        result = lib.save_run(name="WP 2029 — Mortgage!", scenario=_scenario(), generate=_generate)
        assert result.run.folder_name == f"{result.run.created[:10]}_wp-2029-mortgage"

    def test_folder_names_never_collide(self, lib):
        one = lib.save_run(name="same", scenario=_scenario("a"), generate=_generate)
        two = lib.save_run(name="same", scenario=_scenario("b"), generate=_generate)
        assert one.run.folder_name != two.run.folder_name

    def test_identical_inputs_are_not_duplicated(self, lib):
        first = lib.save_run(name="one", scenario=_scenario(), generate=_generate)
        second = lib.save_run(name="two", scenario=_scenario(), generate=_generate)
        assert not second.created
        assert second.identical_to.id == first.run.id
        assert [r.id for r in lib.runs()] == [first.run.id]

    def test_empty_name_is_rejected(self, lib):
        with pytest.raises(LibraryError, match="name"):
            lib.save_run(name="  ", scenario=_scenario(), generate=_generate)

    def test_a_failed_generate_leaves_no_partial_run(self, lib):
        def boom(scenario, inputs_dir):
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            lib.save_run(name="x", scenario=_scenario(), generate=boom)
        assert list((lib.root / "runs").iterdir()) == []
        assert list((lib.root / ".staging").iterdir()) == []

    def test_open_clears_stale_staging(self, tmp_path):
        root = tmp_path / "library"
        Library.open(root)
        leftover = root / ".staging" / "leftover"
        (leftover / "inputs").mkdir(parents=True)
        old = time.time() - STAGING_STALE_SECONDS - 60
        for path in (leftover / "inputs", leftover):
            os.utime(path, (old, old))
        Library.open(root)
        assert list((root / ".staging").iterdir()) == []

    def test_open_keeps_a_fresh_staging_folder(self, tmp_path):
        """T2: another session may be saving; only stale folders go."""
        root = tmp_path / "library"
        Library.open(root)
        (root / ".staging" / "in-progress" / "inputs").mkdir(parents=True)
        Library.open(root)
        assert [p.name for p in (root / ".staging").iterdir()] == ["in-progress"]

    def test_a_second_open_does_not_break_a_save_in_progress(self, tmp_path):
        """T2: Library.open while another session's generate runs (two tabs, S5)."""
        lib = Library.open(tmp_path / "library")
        started = threading.Event()
        errors = []

        def slow(scenario, inputs_dir):
            started.set()
            time.sleep(0.5)
            (inputs_dir / "Case.toml").write_text("generated", encoding="utf-8")

        def save():
            try:
                lib.save_run(name="tab A", scenario=_scenario(), generate=slow)
            except BaseException as exc:  # noqa: BLE001 - reported below
                errors.append(exc)

        worker = threading.Thread(target=save)
        worker.start()
        assert started.wait(5)
        Library.open(tmp_path / "library")
        worker.join()
        assert errors == []
        assert [r.name for r in lib.runs()] == ["tab A"]

    def test_the_stored_scenario_is_the_generated_document(self, lib):
        seen = {}

        def generate(scenario, inputs_dir):
            seen["scenario"] = scenario

        result = lib.save_run(
            name="x",
            scenario={"schema_version": 1, "case": {"n": 24000.0}, "hfp": {}},
            generate=generate,
        )
        stored = json.loads((result.run.path / "inputs" / "scenario.json").read_text(encoding="utf-8"))
        assert stored == seen["scenario"]  # V3: one document, hashed and generated and stored
        assert isinstance(stored["case"]["n"], float)

    def test_a_damaged_run_json_does_not_break_the_library(self, lib):
        good = lib.save_run(name="good", scenario=_scenario("a"), generate=_generate)
        bad = lib.save_run(name="bad", scenario=_scenario("b"), generate=_generate)
        (bad.run.path / "run.json").write_text("{", encoding="utf-8")

        assert [r.id for r in lib.runs()] == [good.run.id]
        assert [d.name for d in lib.damaged()] == [bad.run.folder_name]
        # and the library keeps working around it
        more = lib.save_run(name="more", scenario=_scenario("c"), generate=_generate)
        assert more.created

    def test_dedupe_reports_dropped_metadata(self, lib):
        first = lib.save_run(name="one", scenario=_scenario(), generate=_generate)
        second = lib.save_run(
            name="two",
            scenario=_scenario(),
            generate=_generate,
            notes="typed notes",
            tags=("candidate",),
            plan_year=2027,
        )
        assert not second.created and second.identical_to.id == first.run.id
        assert second.dropped == {
            "name": "two",
            "notes": "typed notes",
            "tags": ["candidate"],
            "parent": None,
            "plan_year": 2027,
        }

    def test_plan_year_defaults_to_the_scenario(self, lib):
        result = lib.save_run(name="x", scenario=_scenario(), generate=_generate)
        assert result.run.plan_year == 2026


class TestLineage:
    def test_parent_and_change_summary(self, lib):
        parent = lib.save_run(name="parent", scenario=_scenario("a"), generate=_generate)
        child = lib.save_run(
            name="child", scenario=_scenario("b"), generate=_generate, parent=parent.run
        )
        assert child.run.parent == parent.run.id
        assert child.changes == ["case.case_name: 'a' -> 'b'"]
        assert child.run.change_summary == ("case.case_name: 'a' -> 'b'",)

    def test_children_survive_the_parent(self, lib):
        parent = lib.save_run(name="parent", scenario=_scenario("a"), generate=_generate)
        child = lib.save_run(
            name="child", scenario=_scenario("b"), generate=_generate, parent=parent.run.id
        )
        lib.delete_run(parent.run)
        assert lib.get(child.run.id).parent == parent.run.id
        assert [r.id for r in lib.runs()] == [child.run.id]


class TestRenameAndDelete:
    def test_rename_changes_the_name_not_the_folder(self, lib):
        result = lib.save_run(name="old", scenario=_scenario(), generate=_generate)
        renamed = lib.rename_run(result.run, "new name")
        assert renamed.name == "new name"
        assert renamed.path == result.run.path
        assert renamed.folder_name == result.run.folder_name

    def test_delete_moves_to_trash(self, lib):
        result = lib.save_run(name="gone", scenario=_scenario(), generate=_generate)
        trash = lib.delete_run(result.run)
        assert trash.exists() and trash.parent.name == "trash"
        assert lib.runs() == []

    def test_delete_clears_order_and_pins(self, lib):
        result = lib.save_run(name="gone", scenario=_scenario(), generate=_generate)

        doc = json.loads((lib.root / "library.json").read_text(encoding="utf-8"))
        doc["order"] = [result.run.id]
        doc["pins"] = [result.run.id]
        (lib.root / "library.json").write_text(json.dumps(doc), encoding="utf-8")
        lib.delete_run(result.run)
        doc = json.loads((lib.root / "library.json").read_text(encoding="utf-8"))
        assert doc["order"] == [] and doc["pins"] == []


class TestLock:
    def test_a_held_lock_raises(self, lib):
        other = Library(lib.root)
        other.lock_wait = 0.1
        with lib._lock():
            with pytest.raises(LibraryLocked):
                other.save_run(name="x", scenario=_scenario(), generate=_generate)
        assert list((lib.root / ".staging").iterdir()) == []

    def test_a_leftover_lock_file_does_not_block(self, lib):
        """T5: the file is only where the lock lives; its presence or age means nothing."""
        lock = lib.root / "library.lock"
        lock.write_text("", encoding="utf-8")
        old = time.time() - 3600
        os.utime(lock, (old, old))
        lib.lock_wait = 0.1
        assert lib.save_run(name="x", scenario=_scenario(), generate=_generate).created

    def test_a_crashed_holder_releases_the_lock(self, lib):
        """T5: a holder that dies without unlocking leaves no stale lock (the kernel frees it)."""
        code = (
            "import os, sys\n"
            "from owlplanner.library import Library\n"
            "lib = Library(sys.argv[1])\n"
            "cm = lib._lock(); cm.__enter__()\n"
            "print('held', flush=True)\n"
            "os._exit(0)\n"
        )
        out = subprocess.run(
            [sys.executable, "-c", code, str(lib.root)], capture_output=True, text=True, timeout=60
        )
        assert out.stdout.strip() == "held"
        lib.lock_wait = 0.5
        assert lib.save_run(name="x", scenario=_scenario(), generate=_generate).created

    def test_concurrent_saves_lose_no_update(self, lib):
        """S5/T5: every save's read-modify-write of library.json survives the others."""
        errors = []

        def save(i):
            try:
                lib.save_run(name=f"run {i}", scenario=_scenario(f"m{i}"), generate=_generate)
            except BaseException as exc:  # noqa: BLE001 - reported below
                errors.append(exc)

        threads = [threading.Thread(target=save, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        doc = json.loads((lib.root / "library.json").read_text(encoding="utf-8"))
        assert sorted(doc["order"]) == sorted(r.id for r in lib.runs())
        assert len(doc["order"]) == 12

    def test_the_lock_is_released_after_save(self, lib):
        lib.save_run(name="x", scenario=_scenario(), generate=_generate)
        other = Library(lib.root)
        other.lock_wait = 0.0
        with other._lock():
            pass

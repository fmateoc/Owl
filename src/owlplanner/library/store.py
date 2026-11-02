"""Library storage: one folder per run, plain files (run-library-design.md, section 5).

Layout (all paths relative to the library root):

    library.json            collections, pins, the order shown (build step 6 fills them)
    library.lock            an OS file lock held around every read-modify-write (S5, T5)
    runs/<date>_<slug>/     one folder per run; the folder name is fixed at creation (S4)
        run.json            id, name, parent, created, notes, tags, plan year, inputs hash,
                            change summary against the parent
        inputs/             scenario.json (the source of truth) plus the generated files
    trash/                  deleted runs (section 10)

Rules implemented here: atomic writes (a run's whole folder is staged outside `runs/` and
published with one rename, so a save never appears half-written), the inputs hash dedupe,
save-as only (a run is never edited in place), and lineage. The lock (`library.lock`) is held
only for the fast metadata work (V6): `generate` runs before it, into the staging folder.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import time
import uuid
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Sequence

from .scenario import diff_summaries, normalize, pretty_json, scenario_hash, validate

LIBRARY_JSON = "library.json"
LOCK_NAME = "library.lock"
RUNS_DIR = "runs"
TRASH_DIR = "trash"
STAGING_DIR = ".staging"
RUN_JSON = "run.json"
INPUTS_DIR = "inputs"
SCENARIO_JSON = "scenario.json"
LIBRARY_FORMAT = 1
RUN_FORMAT = 1
# A staging folder untouched for this long belongs to a save that never published (a crash):
# `Library.open` drops it. A live save touches its folder within seconds (T2).
STAGING_STALE_SECONDS = 3600.0


def default_library_root():
    """The library folder: $OWL_LIBRARY_DIR, else <checkout>/otherFiles/library (section 3, 10).

    The env var both names the folder and switches the UI's Library section on (the way
    `OWL_ASSISTANT=1` does the assistant). `otherFiles/` is gitignored by upstream itself, so
    a household's runs never land in a public tree. The checkout assumption is the codebase's
    own (`ui/tomlexamples.py` reads `examples/` the same way).
    """
    import os

    env = os.environ.get("OWL_LIBRARY_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "otherFiles" / "library"


def _git_ignored(root: Path) -> Optional[bool]:
    """True when git ignores `root`, False when it does not, None when git cannot tell.

    Section 10: the interface refuses a library folder inside a repository that git does not
    ignore -- a household's runs must never land in a public tree. `git check-ignore` exits
    0 for an ignored path, 1 for a path in the work tree that is not ignored, and 128 when
    the folder is not in a repository at all (the rule is about repositories only). It
    classifies by pattern whether the path exists or not, so a library folder that is about
    to be created is checked too; `git -C` needs an existing folder, hence the walk up.
    """
    probe = Path(root)
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            return None
        probe = parent
    try:
        # Forward slashes and a trailing "/" so a directory-only pattern (`.gitignore`'s
        # "library/") matches a folder that does not exist yet.
        target = str(Path(root)).replace(os.sep, "/").rstrip("/") + "/"
        proc = subprocess.run(
            ["git", "-C", str(probe), "check-ignore", "-q", "--", target],
            capture_output=True,
        )
    except OSError:  # no git installed: cannot tell, and likely no repository either
        return None
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def _newest_mtime(path: Path) -> Optional[float]:
    """The newest mtime in a tree, or None if it vanished meanwhile (published or removed)."""
    try:
        newest = path.stat().st_mtime
        if path.is_dir():
            for dirpath, dirnames, filenames in os.walk(path):
                for name in dirnames + filenames:
                    try:
                        newest = max(newest, os.stat(os.path.join(dirpath, name)).st_mtime)
                    except OSError:
                        pass
        return newest
    except OSError:
        return None


def _try_lock(fd: int) -> bool:
    """Take the exclusive lock on an open file without waiting; False if another holds it."""
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)  # one byte; beyond EOF is allowed
        except OSError:
            return False
        return True
    import fcntl

    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


def _unlock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_UN)


class LibraryError(RuntimeError):
    """The library folder or a run is missing or malformed."""


class LibraryLocked(LibraryError):
    """Another writer holds library.lock."""


@dataclass(frozen=True)
class RunInfo:
    """One run's run.json, plus its folder."""

    id: str
    name: str
    parent: Optional[str]
    created: str
    notes: str
    tags: tuple
    plan_year: Optional[int]
    inputs_hash: str
    change_summary: tuple
    path: Path

    @property
    def folder_name(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class SaveResult:
    """The outcome of save_run: created, or identical to an existing run (section 5).

    When the inputs were identical to an existing run, `dropped` lists the requested
    metadata (name, notes, tags, parent, plan_year) that was *not* applied (V8), so the
    interface can say what was discarded instead of losing it silently.
    """

    created: bool
    run: RunInfo
    identical_to: Optional[RunInfo]
    changes: list
    dropped: Optional[dict] = None


class Library:
    """The library folder: runs, collections, and the rules around them."""

    def __init__(self, root):
        self.root = Path(root)
        # Lock timings are instance attributes so tests can shorten them.
        self.lock_wait = 5.0

    # -- layout ---------------------------------------------------------

    @classmethod
    def open(cls, root, *, create: bool = True) -> "Library":
        lib = cls(root)
        # Section 10 (M2): a library holds household data. Inside a git repository it must be
        # ignored (`git check-ignore`), or a commit could publish the runs.
        if _git_ignored(lib.root) is False:
            raise LibraryError(
                f"{lib.root} is inside a git repository that does not ignore it: a library holds "
                "household data and must not be committable (section 10). Point OWL_LIBRARY_DIR "
                "at a gitignored folder (for example otherFiles/library) or at one outside the "
                "repository."
            )
        marker = lib.root / LIBRARY_JSON
        if not marker.exists():
            if not create:
                raise LibraryError(f"{lib.root} is not a library (no {LIBRARY_JSON})")
            lib._init_layout()
        lib._library_doc()  # validates the file
        # A stale staging folder belongs to a save that never published (a crash). Only stale
        # ones go: another session may be saving right now (T2: two tabs, S5).
        staging = lib.root / STAGING_DIR
        staging.mkdir(parents=True, exist_ok=True)
        now = time.time()
        for entry in staging.iterdir():
            newest = _newest_mtime(entry)
            if newest is not None and now - newest > STAGING_STALE_SECONDS:
                shutil.rmtree(entry, ignore_errors=True)
        return lib

    def _init_layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / RUNS_DIR).mkdir(exist_ok=True)
        (self.root / TRASH_DIR).mkdir(exist_ok=True)
        self._write_json(
            self.root / LIBRARY_JSON,
            {"library_format": LIBRARY_FORMAT, "collections": {}, "pins": [], "order": []},
        )

    def _library_doc(self) -> dict:
        try:
            doc = self._read_json(self.root / LIBRARY_JSON)
        except (OSError, json.JSONDecodeError) as exc:
            raise LibraryError(f"cannot read {self.root / LIBRARY_JSON}: {exc}") from exc
        if not isinstance(doc, dict) or doc.get("library_format") != LIBRARY_FORMAT:
            raise LibraryError(f"{self.root / LIBRARY_JSON} is not library format {LIBRARY_FORMAT}")
        doc.setdefault("collections", {})
        doc.setdefault("pins", [])
        doc.setdefault("order", [])
        return doc

    # -- small file helpers --------------------------------------------

    @staticmethod
    def _read_json(path: Path) -> Any:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_json(path: Path, doc: Any) -> None:
        Library._atomic_write(path, pretty_json(doc))

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)

    @contextmanager
    def _lock(self) -> Iterator[None]:
        """Hold library.lock for one read-modify-write (S5).

        An OS file lock (`flock` on POSIX, `msvcrt.locking` on Windows), not a create-exclusive
        file (T5): the kernel releases it when the holder's process ends, so a crash leaves no
        stale lock to take over, and two waiters can never both take one over. Separate opens
        conflict even within one process (two Streamlit sessions are threads of one server).
        The file itself stays on disk; deleting it would let two holders lock two files.
        """
        path = self.root / LOCK_NAME
        deadline = time.monotonic() + self.lock_wait
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            while not _try_lock(fd):
                if time.monotonic() > deadline:
                    raise LibraryLocked(f"{path} is held by another writer")
                time.sleep(0.05)
            try:
                yield
            finally:
                _unlock(fd)
        finally:
            os.close(fd)

    # -- runs -----------------------------------------------------------

    def _run_dirs(self) -> list:
        runs = self.root / RUNS_DIR
        return sorted(d for d in runs.iterdir() if d.is_dir())

    def _info_from_dir(self, folder: Path) -> Optional[RunInfo]:
        """Read a run folder's run.json. None for a partial write (no run.json yet).

        A run.json that exists but cannot be read (hand-edited, truncated) is a damaged
        run: `damaged()` reports it and every listing skips it (V7).
        """
        path = folder / RUN_JSON
        if not path.exists():
            return None
        try:
            doc = self._read_json(path)
            return RunInfo(
                id=doc["id"],
                name=doc["name"],
                parent=doc.get("parent"),
                created=doc["created"],
                notes=doc.get("notes", ""),
                tags=tuple(doc.get("tags", ())),
                plan_year=doc.get("plan_year"),
                inputs_hash=doc["inputs_hash"],
                change_summary=tuple(doc.get("change_summary", ())),
                path=folder,
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _scan(self):
        """(runs, damaged folders). Folders without run.json are partial writes: skipped."""
        good, damaged = [], []
        for folder in self._run_dirs():
            if not (folder / RUN_JSON).exists():
                continue
            info = self._info_from_dir(folder)
            if info is None:
                damaged.append(folder)
            else:
                good.append(info)
        return good, damaged

    def runs(self) -> list:
        """Every run, oldest first (damaged folders are skipped, see damaged())."""
        good, _ = self._scan()
        return sorted(good, key=lambda r: (r.created, r.id))

    def damaged(self) -> list:
        """Run folders whose run.json cannot be read (V7). Their files may still be useful."""
        _, damaged = self._scan()
        return damaged

    def get(self, run_id: str) -> RunInfo:
        for info in self.runs():
            if info.id == run_id:
                return info
        raise LibraryError(f"no run with id {run_id!r}")

    def scenario(self, run: "RunInfo | str") -> dict:
        info = run if isinstance(run, RunInfo) else self.get(run)
        return self._read_json(info.path / INPUTS_DIR / SCENARIO_JSON)

    def find_by_hash(self, inputs_hash: str) -> Optional[RunInfo]:
        for info in self.runs():
            if info.inputs_hash == inputs_hash:
                return info
        return None

    @staticmethod
    def _slugify(name: str) -> str:
        slug = "".join(c if c.isalnum() else "-" for c in name.lower())
        slug = "-".join(part for part in slug.split("-") if part)
        return slug or "run"

    def _new_folder(self, name: str, created: datetime) -> Path:
        base = f"{created:%Y-%m-%d}_{self._slugify(name)}"
        folder = self.root / RUNS_DIR / base
        n = 1
        while folder.exists():
            n += 1
            folder = self.root / RUNS_DIR / f"{base}-{n}"
        return folder

    def save_run(
        self,
        *,
        name: str,
        scenario: dict,
        plan_year: Optional[int] = None,
        parent: "RunInfo | str | None" = None,
        notes: str = "",
        tags: Sequence[str] = (),
        generate: Optional[Callable[[dict, Path], None]] = None,
    ) -> SaveResult:
        """Save a scenario as a new run (save-as; never in place, section 7).

        Returns created=False with identical_to set when the inputs hash matches an
        existing run (section 5: "identical to X" instead of a duplicate); the requested
        name, notes, tags, parent and plan_year then arrive in ``dropped`` (V8).
        ``generate`` writes the generated files (Case.toml, HFP.xlsx) into inputs/; it
        defaults to library.casefiles.export_case, and the scenario is then canonicalized
        first (`casefiles.canonicalize`, T1), so a hand-built scenario.json is stored as the
        document its Case.toml reads back as.

        The slow work (``generate``) runs outside the lock into a staging folder (V6); the
        run is published under the lock with one rename, complete or not at all.
        """
        if not name.strip():
            raise LibraryError("a run needs a name")
        if generate is None:
            from . import casefiles

            generate = casefiles.export_case
            scenario = casefiles.canonicalize(scenario)
        else:
            scenario = normalize(scenario)
            validate(scenario)
        inputs_hash = scenario_hash(scenario)
        parent_info = parent if isinstance(parent, RunInfo) else (self.get(parent) if parent else None)
        changes: list = []
        if parent_info is not None:
            changes = diff_summaries(self.scenario(parent_info), scenario)

        created_dt = datetime.now()
        rid = uuid.uuid4().hex
        staging = self.root / STAGING_DIR / rid
        folder = None
        try:
            inputs = staging / INPUTS_DIR
            inputs.mkdir(parents=True)
            self._write_json(inputs / SCENARIO_JSON, scenario)
            generate(scenario, inputs)  # slow; outside the lock (V6)
            self._write_json(
                staging / RUN_JSON,
                {
                    "run_format": RUN_FORMAT,
                    "id": rid,
                    "name": name,
                    "parent": parent_info.id if parent_info else None,
                    "created": created_dt.isoformat(timespec="seconds"),
                    "notes": notes,
                    "tags": list(tags),
                    "plan_year": plan_year if plan_year is not None else scenario.get("plan_year"),
                    "inputs_hash": inputs_hash,
                    "change_summary": changes,
                },
            )
            with self._lock():
                existing = self.find_by_hash(inputs_hash)
                if existing is not None:
                    shutil.rmtree(staging, ignore_errors=True)
                    return SaveResult(
                        created=False,
                        run=existing,
                        identical_to=existing,
                        changes=[],
                        dropped={
                            "name": name,
                            "notes": notes,
                            "tags": list(tags),
                            "parent": parent_info.id if parent_info else None,
                            "plan_year": plan_year,
                        },
                    )
                folder = self._new_folder(name, created_dt)
                os.replace(staging, folder)  # the publish: one rename
                doc = self._library_doc()
                doc["order"].append(rid)
                self._write_json(self.root / LIBRARY_JSON, doc)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

        return SaveResult(created=True, run=self._info_from_dir(folder), identical_to=None, changes=changes)

    def rename_run(self, run: "RunInfo | str", name: str) -> RunInfo:
        """Rename a run: the name in run.json only, never the folder (S4)."""
        if not name.strip():
            raise LibraryError("a run needs a name")
        info = run if isinstance(run, RunInfo) else self.get(run)
        with self._lock():
            doc = self._read_json(info.path / RUN_JSON)
            doc["name"] = name
            self._write_json(info.path / RUN_JSON, doc)
        return self._info_from_dir(info.path)

    def delete_run(self, run: "RunInfo | str") -> Path:
        """Move a run to trash/ (section 10). Children keep their parent id."""
        info = run if isinstance(run, RunInfo) else self.get(run)
        with self._lock():
            trash = self.root / TRASH_DIR
            trash.mkdir(exist_ok=True)
            target = trash / info.folder_name
            n = 1
            while target.exists():
                n += 1
                target = trash / f"{info.folder_name}-{n}"
            os.replace(info.path, target)
            doc = self._library_doc()
            doc["order"] = [rid for rid in doc["order"] if rid != info.id]
            doc["pins"] = [rid for rid in doc["pins"] if rid != info.id]
            self._write_json(self.root / LIBRARY_JSON, doc)
        return target


def run_zip(run: "RunInfo | Path") -> bytes:
    """The run folder as a zip ("Download everything", design section 9.1).

    Everything a run holds -- its inputs, its results and their records -- except the OS
    lock files (`library.lock`, `status.lock`) and any staging folder a killed attempt left
    (`results/.attempt-*`). `plan.pkl` travels too: it is only ever loaded against the hash
    and code stamp in its own record.json (section 10), so a copy opened elsewhere is simply
    read without it.
    """
    root = run.path if isinstance(run, RunInfo) else Path(run)
    if not root.is_dir():
        raise LibraryError(f"{root} is not a run folder")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if any(part.startswith(".attempt-") for part in rel.parts) or path.name.endswith(".lock"):
                continue
            zf.write(path, arcname=str(Path(root.name) / rel))
    return buf.getvalue()

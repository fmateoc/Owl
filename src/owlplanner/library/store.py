"""Library storage: one folder per run, plain files (run-library-design.md, section 5).

Layout (all paths relative to the library root):

    library.json            collections, pins, the order shown (collections since step 6)
    library.lock            an OS file lock held around every read-modify-write (S5, T5)
    runs/<date>_<slug>/     one folder per run; the folder name is fixed at creation (S4)
        run.json            id, name, parent, created, notes, tags, plan year, inputs hash,
                            change summary against the parent
        inputs/             scenario.json (the source of truth) plus the generated files
    trash/                  deleted runs (section 10)

Rules implemented here: atomic writes (a run's whole folder is staged outside `runs/` and
published with one rename, so a save never appears half-written), the inputs hash dedupe,
save-as only (a run is never edited in place), lineage, and the collections (section 4: a
named set of runs answering one question, with a comparison rule; section 9.3). The lock
(`library.lock`) is held only for the fast metadata work (V6): `generate` runs before it,
into the staging folder.
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

from .results import PLAN_PKL
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
    to be created is checked too.

    The probe is a sentinel *file* inside the folder, not the folder itself (step-3 review
    P1): a trailing-slash path is matched against directory-only patterns, and on this git
    (2.52, Windows) with a CRLF `.gitignore` containing a blank line, the blank pattern
    matches every not-yet-existing trailing-slash path -- `check-ignore` then says "ignored"
    for a library dropped anywhere in the repository. A sentinel file path is classified
    correctly (the blank pattern matches nothing), and a directory pattern such as
    `otherFiles/` still matches paths inside it. If the sentinel name itself were ignored
    the answer is "ignored": refusing is the safe direction.
    """
    probe = Path(root)
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            return None
        probe = parent
    try:
        target = str(Path(root) / ".owl-library-probe").replace(os.sep, "/")
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


@dataclass(frozen=True)
class Member:
    """One collection member: a run and the variant values its grid reads (section 9.3).

    `values` maps a variant dimension (`library.variants`: "place", "year", "financing",
    "work", "claim") to its label for this run ("yonkers", 2027, "cash"): the grid's row and
    column keys. A member added by hand may hold no values: it is listed with the others but
    sits in no grid cell.
    """

    run: str
    values: dict


@dataclass(frozen=True)
class Collection:
    """A named set of runs answering one question, with a comparison rule (section 4).

    The question and the rule are written on it (section 9.3, for example "Maximize
    first-year discretionary spending, condo kept; reference: Yonkers 2027 cash"). The
    grid's cells are differences from `reference` (a run id; None until one is chosen), laid
    out by `grid` -- {"rows": [dimension, ...], "columns": [dimension]} of the members'
    values (section 9.3's grid view).
    """

    id: str
    name: str
    question: str
    rule: str
    created: str
    reference: Optional[str]
    members: tuple
    grid: dict
    # The run whose sensitivity tornado this collection holds (I9), by id: the Run page finds
    # its tornado through it, never by the collection's name, which a second run of the same
    # name or a rename would break (review AI3). None for every other collection.
    tornado_of: Optional[str] = None

    def member(self, run_id: str) -> Optional[Member]:
        for member in self.members:
            if member.run == run_id:
                return member
        return None


class Library:
    """The library folder: runs, collections, and the rules around them."""

    def __init__(self, root):
        self.root = Path(root)
        # Lock timings are instance attributes so tests can shorten them.
        self.lock_wait = 5.0
        # Where each run was last seen (id -> folder), refreshed by every listing. `get` reads
        # only that folder's run.json and checks its id (performance review P6): a page that
        # names one run per row used to read the whole library once per row.
        self._folder_of = {}

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
            {"library_format": LIBRARY_FORMAT, "collections": {}, "collection_order": [],
             "pins": [], "order": []},
        )

    def _library_doc(self) -> dict:
        try:
            doc = self._read_json(self.root / LIBRARY_JSON)
        except (OSError, json.JSONDecodeError) as exc:
            raise LibraryError(f"cannot read {self.root / LIBRARY_JSON}: {exc}") from exc
        if not isinstance(doc, dict) or doc.get("library_format") != LIBRARY_FORMAT:
            raise LibraryError(f"{self.root / LIBRARY_JSON} is not library format {LIBRARY_FORMAT}")
        doc.setdefault("collections", {})
        doc.setdefault("collection_order", [])
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
        """Every run, oldest first (damaged folders are skipped, see damaged()).

        The order is `library.json`'s `order` -- the save order, "the order shown" (section
        5), which resolves the same-second ties a uuid4 id cannot (step-3 review P11). A run
        missing from the list (a folder copied in by hand) sorts by (created, id) behind
        them.
        """
        good, _ = self._scan()
        rank = {rid: i for i, rid in enumerate(self._library_doc().get("order", []))}
        ordered = sorted(good, key=lambda r: (rank.get(r.id, len(rank)), r.created, r.id))
        folder_of = {}
        for info in ordered:
            folder_of.setdefault(info.id, info.path)  # two folders with one id: the first listed
        self._folder_of = folder_of
        return ordered

    def damaged(self) -> list:
        """Run folders whose run.json cannot be read (V7). Their files may still be useful."""
        _, damaged = self._scan()
        return damaged

    def get(self, run_id: str) -> RunInfo:
        """The run with this id, read from its own run.json (never a stale copy).

        The folder where the last listing saw it is read first; a run it does not hold any more
        (deleted, damaged, never listed by this instance) costs one listing, as every call did.
        """
        folder = self._folder_of.get(run_id)
        if folder is not None:
            info = self._info_from_dir(folder)
            if info is not None and info.id == run_id:
                return info
        for info in self.runs():
            if info.id == run_id:
                return info
        raise LibraryError(f"no run with id {run_id!r}")

    def scenario(self, run: "RunInfo | str") -> dict:
        info = run if isinstance(run, RunInfo) else self.get(run)
        return self._read_json(info.path / INPUTS_DIR / SCENARIO_JSON)

    # -- pins: the baseline (ergonomics review S-1) ---------------------

    def pins(self) -> list:
        """The pinned run ids, first pinned first (ids of deleted runs are dropped at delete)."""
        return list(self._library_doc().get("pins") or [])

    def pin(self, run: "RunInfo | str") -> None:
        """Make the run the baseline: it goes to the front of `pins` (idempotent)."""
        info = run if isinstance(run, RunInfo) else self.get(run)
        with self._lock():
            doc = self._library_doc()
            doc["pins"] = [info.id] + [rid for rid in doc["pins"] if rid != info.id]
            self._write_json(self.root / LIBRARY_JSON, doc)

    def unpin(self, run: "RunInfo | str") -> None:
        rid = run.id if isinstance(run, RunInfo) else str(run)
        with self._lock():
            doc = self._library_doc()
            doc["pins"] = [p for p in doc["pins"] if p != rid]
            self._write_json(self.root / LIBRARY_JSON, doc)

    def baseline(self) -> Optional[RunInfo]:
        """The first pin that is still a run, else None (the landing page's run)."""
        by_id = {r.id: r for r in self.runs()}
        return next((by_id[rid] for rid in self.pins() if rid in by_id), None)

    # -- the disclaimer, once per library (S-1, decision 2) --------------

    def disclaimer_accepted(self) -> Optional[str]:
        """When the disclaimer was accepted for this library (an ISO stamp), else None."""
        value = self._library_doc().get("disclaimer_accepted")
        return value if isinstance(value, str) and value else None

    def accept_disclaimer(self) -> str:
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._lock():
            doc = self._library_doc()
            doc["disclaimer_accepted"] = stamp
            self._write_json(self.root / LIBRARY_JSON, doc)
        return stamp

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
        """Move a run to trash/ (section 10). Children keep their parent id.

        A deleted run leaves every collection it was a member of (a collection keeps no
        reference to a folder that is gone; the runs keep their own lineage).
        """
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
            for coll in (doc.get("collections") or {}).values():
                if not isinstance(coll, dict):
                    continue
                coll["members"] = [m for m in coll.get("members") or []
                                   if isinstance(m, dict) and m.get("run") != info.id]
                if coll.get("reference") == info.id:
                    coll["reference"] = None
            self._write_json(self.root / LIBRARY_JSON, doc)
        return target

    # -- collections ---------------------------------------------------

    @staticmethod
    def _collection_from(cid: str, doc: Any) -> Optional[Collection]:
        """One collection from its library.json entry; None for a malformed one (V7's rule:
        shown as damaged, never fatal)."""
        if not isinstance(doc, dict):
            return None
        members = []
        for member in doc.get("members") or []:
            if isinstance(member, dict) and isinstance(member.get("run"), str):
                values = member.get("values")
                members.append(Member(run=member["run"],
                                      values=dict(values) if isinstance(values, dict) else {}))
        grid = doc.get("grid")
        return Collection(
            id=cid,
            name=str(doc.get("name") or "untitled"),
            question=str(doc.get("question") or ""),
            rule=str(doc.get("rule") or ""),
            created=str(doc.get("created") or ""),
            reference=doc.get("reference") if isinstance(doc.get("reference"), str) else None,
            members=tuple(members),
            grid=dict(grid) if isinstance(grid, dict) else {},
            tornado_of=doc.get("tornado_of") if isinstance(doc.get("tornado_of"), str) else None,
        )

    def collections(self) -> list:
        """Every collection, in the order shown (`library.json`'s `collection_order`)."""
        doc = self._library_doc()
        known = doc.get("collections") or {}
        rank = {cid: i for i, cid in enumerate(doc.get("collection_order") or [])}
        out = []
        for cid in sorted(known, key=lambda c: (rank.get(c, len(rank)), c)):
            coll = self._collection_from(cid, known[cid])
            if coll is not None:
                out.append(coll)
        return out

    def collection(self, cid: str) -> Collection:
        doc = self._library_doc()
        entry = (doc.get("collections") or {}).get(cid)
        coll = self._collection_from(cid, entry) if entry is not None else None
        if coll is None:
            raise LibraryError(f"no collection with id {cid!r}")
        return coll

    def create_collection(self, name: str, *, question: str = "", rule: str = "",
                          tornado_of: Optional[str] = None) -> Collection:
        """A new, empty collection (section 4). The id is its folder-free identity.

        `tornado_of` (a run id) marks the collection as that run's sensitivity tornado (I9,
        review AI3)."""
        if not name.strip():
            raise LibraryError("a collection needs a name")
        cid = uuid.uuid4().hex
        with self._lock():
            doc = self._library_doc()
            doc["collections"][cid] = {
                "id": cid,
                "name": name,
                "question": question,
                "rule": rule,
                "created": datetime.now().isoformat(timespec="seconds"),
                "reference": None,
                "members": [],
                "grid": {},
            }
            if tornado_of is not None:
                doc["collections"][cid]["tornado_of"] = str(tornado_of)
            doc["collection_order"].append(cid)
            self._write_json(self.root / LIBRARY_JSON, doc)
        return self.collection(cid)

    def update_collection(self, cid: str, *, name: Optional[str] = None,
                          question: Optional[str] = None, rule: Optional[str] = None,
                          grid: Optional[dict] = None) -> Collection:
        """Edit a collection's own fields (name, question, rule, grid layout). The
        reference is set with `set_reference`, the members with add/remove_member."""
        with self._lock():
            doc = self._library_doc()
            entry = (doc.get("collections") or {}).get(cid)
            if not isinstance(entry, dict):
                raise LibraryError(f"no collection with id {cid!r}")
            if name is not None:
                if not name.strip():
                    raise LibraryError("a collection needs a name")
                entry["name"] = name
            if question is not None:
                entry["question"] = question
            if rule is not None:
                entry["rule"] = rule
            if grid is not None:
                entry["grid"] = dict(grid)
            self._write_json(self.root / LIBRARY_JSON, doc)
        return self.collection(cid)

    def set_reference(self, cid: str, run: "RunInfo | str | None") -> Collection:
        """The run the collection's grid measures from (None: no reference yet)."""
        with self._lock():
            doc = self._library_doc()
            entry = (doc.get("collections") or {}).get(cid)
            if not isinstance(entry, dict):
                raise LibraryError(f"no collection with id {cid!r}")
            if run is None:
                entry["reference"] = None
            else:
                info = run if isinstance(run, RunInfo) else self.get(run)
                entry["reference"] = info.id
            self._write_json(self.root / LIBRARY_JSON, doc)
        return self.collection(cid)

    def delete_collection(self, cid: str) -> None:
        """Drop the collection. The runs stay (deleting a question deletes no answers)."""
        with self._lock():
            doc = self._library_doc()
            if cid not in (doc.get("collections") or {}):
                raise LibraryError(f"no collection with id {cid!r}")
            del doc["collections"][cid]
            doc["collection_order"] = [c for c in doc["collection_order"] if c != cid]
            self._write_json(self.root / LIBRARY_JSON, doc)

    def add_member(self, cid: str, run: "RunInfo | str", values: Optional[dict] = None) -> Collection:
        """Put a run in a collection (idempotent: a second add updates its values).

        `values` is the run's variant labels ({dimension: label}, `library.variants`); it
        replaces the member's previous values, so "make variants" can fill them in one pass.
        """
        info = run if isinstance(run, RunInfo) else self.get(run)
        with self._lock():
            doc = self._library_doc()
            entry = (doc.get("collections") or {}).get(cid)
            if not isinstance(entry, dict):
                raise LibraryError(f"no collection with id {cid!r}")
            members = [m for m in entry.get("members") or []
                       if isinstance(m, dict) and m.get("run") != info.id]
            members.append({"run": info.id, "values": dict(values or {})})
            entry["members"] = members
            self._write_json(self.root / LIBRARY_JSON, doc)
        return self.collection(cid)

    def join_collection(self, cid: str, run: "RunInfo | str") -> Collection:
        """Put a run in a collection as it is: a run already in it keeps its values.

        The save dialogs' "Collection" field (design section 7) and the Collections page's
        Add button use this: a save identical to a member joins that member's run, and
        `add_member`'s replace semantics would wipe its variant values and take it out of
        the grid (review AG6). Read and write under one lock.
        """
        info = run if isinstance(run, RunInfo) else self.get(run)
        with self._lock():
            doc = self._library_doc()
            entry = (doc.get("collections") or {}).get(cid)
            if not isinstance(entry, dict):
                raise LibraryError(f"no collection with id {cid!r}")
            members = [m for m in entry.get("members") or [] if isinstance(m, dict)]
            if not any(m.get("run") == info.id for m in members):
                members.append({"run": info.id, "values": {}})
                entry["members"] = members
                self._write_json(self.root / LIBRARY_JSON, doc)
        return self.collection(cid)

    def remove_member(self, cid: str, run: "RunInfo | str") -> Collection:
        info = run if isinstance(run, RunInfo) else self.get(run)
        with self._lock():
            doc = self._library_doc()
            entry = (doc.get("collections") or {}).get(cid)
            if not isinstance(entry, dict):
                raise LibraryError(f"no collection with id {cid!r}")
            entry["members"] = [m for m in entry.get("members") or []
                                if not (isinstance(m, dict) and m.get("run") == info.id)]
            if entry.get("reference") == info.id:
                entry["reference"] = None
            self._write_json(self.root / LIBRARY_JSON, doc)
        return self.collection(cid)


def run_zip(run: "RunInfo | Path") -> bytes:
    """The run folder as a zip ("Download everything", design section 9.1).

    Everything a run holds -- its inputs, its results and their records -- except the OS
    lock files (`library.lock`, `status.lock`), the transient folders of live machinery
    (`results/.attempt-*` staging, `results/.requeue-*` trash) and the `plan.pkl` caches.
    Section 10 (R10): "A run brought in from a zip comes without its pickles." The hash that
    guards a pickle is in the `record.json` beside it, so for a folder unzipped and copied
    into a library the check would compare the pickle with a hash it brought along (step-3
    review 3, W8). Nothing is lost: the durable files carry every number, and "Open in Owl"
    on a result without its cache says "solve the run again".

    A file that vanishes between the listing and the write (a "run again" cleaning the
    folder, step-3 review P5) is not silently dropped from "everything": the zip says which
    one and the caller retries.
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
            if any(part.startswith((".attempt-", ".requeue-")) for part in rel.parts) \
                    or path.name.endswith(".lock") or path.name == PLAN_PKL:
                continue
            try:
                zf.write(path, arcname=str(Path(root.name) / rel))
            except OSError as exc:
                raise LibraryError(
                    f"{rel} disappeared while {root.name} was being zipped (a solve being "
                    "re-queued?): try again"
                ) from exc
    return buf.getvalue()

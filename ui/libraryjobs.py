"""
The run library's job manager for the interface: one per server process (design section 8.2).

`get_manager()` is the `st.cache_resource` singleton every page shares (R5: two tabs see one
queue), and it starts the manager's ticker thread (review H5): the queue dispatches waiting
jobs and adopts or interrupts running ones whether or not a Queue page is open. `main.py`
calls it on every page load when the library is on (`OWL_LIBRARY_DIR`), so the ticker runs
from the first page a browser opens after a server restart.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import re
from pathlib import Path

import streamlit as st

from owlplanner.library import JobManager, Library, run_zip
from owlplanner.library.store import default_library_root


def library_address_ok() -> bool:
    """Section 10, R11: library mode is localhost only.

    A running app cannot rebind its own server, so the check is on the configured bind
    address: the library pages are refused unless the server listens on localhost. The
    library-mode launcher (`owlplanner-library.cmd` / `.sh`) passes `--server.address=localhost`.
    """
    return str(st.get_option("server.address")).strip().lower() in ("localhost", "127.0.0.1")


# Messages a page shows across its own `st.rerun()` (step-3 review 3, W3). A rerun ends the
# script run, and the next run clears every element it does not draw again (toasts excepted),
# so an error or notice written just before `st.rerun()` was never seen: the user clicked
# "Import" and nothing appeared to happen. A page queues them here and draws them first.
_FLASH_KEY = "library_flash"
_FLASH_KINDS = ("error", "warning", "info", "success", "caption")


def flash(kind: str, text: str) -> None:
    """Queue one message for the next render of the page (`show_flashes`)."""
    if kind not in _FLASH_KINDS:
        raise ValueError(f"unknown message kind {kind!r}")
    st.session_state.setdefault(_FLASH_KEY, []).append((kind, str(text)))


def show_flashes() -> None:
    """Draw (once) the messages queued before the last rerun."""
    for kind, text in st.session_state.pop(_FLASH_KEY, None) or []:
        getattr(st, kind)(text)


@st.cache_data(show_spinner=False)
def _run_zip_cached(path: str, fingerprint: tuple) -> bytes:
    return run_zip(Path(path))


def run_zip_bytes(run) -> bytes:
    """`store.run_zip` for the download buttons, cached until the run folder changes.

    Without the cache every render of every zip button rebuilt the whole archive (step-3
    review P5). The fingerprint is a walk of the folder's metadata (a cheap cache key); a
    file vanishing mid-zip (`run_zip` names it) propagates as `LibraryError`, which the
    pages show instead of crashing.
    """
    root = Path(run.path)
    count, newest = 0, 0.0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                count += 1
                newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue  # a file in flight: the fingerprint only has to change
    return _run_zip_cached(str(root), (count, newest))


@st.cache_resource
def _manager(root: str):
    manager = JobManager(Library.open(root))
    manager.start_ticker()
    return manager


def get_manager():
    """The server's job manager over the library folder (`OWL_LIBRARY_DIR`), ticking."""
    return _manager(str(default_library_root()))


_LS_STEP = re.compile(r"Local search, iteration\s+(\d+)")


def job_phase(doc: dict, *, another_running: bool = False) -> str:
    """What a queued job is doing, in words, for the Queue page (UX review Q8).

    The raw log line (`last_log`, e.g. "... | DEBUG | localsearch:_step:263 | ...") stays
    available beside it; this is the worker's own step ("solving", "searching the claiming
    ages"), with the local search's step or the loop's iteration when the log names one.
    A failed or interrupted job leads with its error text.
    """
    state = doc.get("state")
    if state == "waiting":
        return "Waiting for another solve to finish" if another_running else "Waiting to start"
    if state in ("failed", "interrupted"):
        error = doc.get("error") or ""
        head = "Failed" if state == "failed" else "Interrupted"
        return f"{head}: {error}" if error else head
    if state == "done":
        return "Finished"
    step = str(doc.get("step") or "solving").strip()
    text = step[:1].upper() + step[1:]
    match = _LS_STEP.search(doc.get("last_log") or "")
    if match:
        return f"{text}: searching the tax breakpoints, step {match.group(1)}"
    if doc.get("iteration") is not None:
        return f"{text}, loop iteration {doc['iteration']}"
    return text

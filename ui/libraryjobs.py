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
from datetime import datetime
from pathlib import Path

import streamlit as st

from owlplanner.library import JobManager, Library, run_zip
from owlplanner.library import results as R
from owlplanner.library.presets import COMPANION_PRESETS, preset_name
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


def plain(text) -> str:
    """Plain text (a change summary, a run's name) for a Markdown element: each `$` escaped, so
    that two of them ("700000 (today's $) ... (today's $)") do not start LaTeX math, which
    swallowed the text between them in the browser (ergonomics review S-2's re-drive)."""
    return str(text).replace("\\$", "$").replace("$", "\\$")


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


def job_key(job) -> str:
    """A widget-key part naming one job among all the library's: its run's folder and its own.

    `job.id` is the results folder's name, "<second>_<preset>", unique inside one run only
    (`JobManager.enqueue` claims it with a `mkdir` there). Two runs queued in the same second
    under one preset share it (*Make variants* with "Queue them when created"), so the Queue
    page keys its rows by the path's two folder names, fixed when each was created.
    """
    results_dir = Path(job.results_dir)
    return f"{results_dir.parent.parent.name}/{results_dir.name}"


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


def since(iso, now=None) -> str:
    """The time from a job stamp to `now` (seconds since the epoch; default: this instant) as
    "12s", "3m" or "1.5h"; "-" for an unreadable stamp (M6). Stamps are offset-aware (H3)."""
    then = R.stamp_seconds(iso)
    if then is None:
        return "-"
    seconds = max(0.0, (now or datetime.now().timestamp()) - then)
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.1f}h"


# -- a run's live solves, for its own page (local-use review D3) --------------------------
# The Run page stayed on "This run has no results yet" after *Solve*: only the Queue page
# refreshed itself. The pages that queue a solve name its jobs here, the Run page's fragment
# shows the live ones and, when one of them ends, says so and redraws the whole page on the
# newest result.

_WATCH_KEY = "run_page_live_{run_id}"
SHOW_NEWEST_KEY = "run_page_show_newest"


def watch_jobs(run_id, jobs) -> None:
    """Name jobs just queued for a run, so its page notices their end even when they finish
    before it is drawn (a Quick look takes two seconds)."""
    key = _WATCH_KEY.format(run_id=run_id)
    st.session_state[key] = sorted(set(st.session_state.get(key) or ()) | {job_key(j) for j in jobs})


def live_jobs(manager, run) -> list:
    """The run's jobs still waiting or running, oldest first."""
    return [job for job in manager.jobs(run) if job.state in (R.WAITING, R.RUNNING)]


def ended_jobs(manager, run) -> tuple:
    """(the run's live jobs, those that were live at the last look and are not any more).

    The session keeps the live set between looks (`watch_jobs` seeds it at queue time); every
    call replaces it, so an ended job is reported once."""
    jobs = manager.jobs(run)
    live = [job for job in jobs if job.state in (R.WAITING, R.RUNNING)]
    key = _WATCH_KEY.format(run_id=run.id)
    seen = set(st.session_state.get(key) or ())
    now = {job_key(job) for job in live}
    ended = [job for job in jobs if job_key(job) in seen - now]
    st.session_state[key] = sorted(now)
    return live, ended


def solving_lines(live, *, another_running=False, now=None) -> list:
    """One line per live job of a run: the preset's name, what it is doing, for how long."""
    lines = []
    for job in live:
        doc = job.doc
        waiting = doc.get("state") == R.WAITING
        phase = job_phase(doc, another_running=another_running and waiting)
        clock = "" if waiting else f", {since(doc.get('started') or doc.get('queued'), now)} so far"
        lines.append(f"**{preset_name(doc.get('preset'))}**: {phase[:1].lower() + phase[1:]}{clock}")
    return lines


def ended_message(job) -> tuple:
    """(message kind, text) for a job that just ended, for `flash`."""
    doc = job.doc
    words = preset_name(doc.get("preset"))
    if doc.get("state") == R.DONE:
        if doc.get("preset") in COMPANION_PRESETS:
            return "caption", f"{words} finished (comparisons read it; the result shown is the main solve's)."
        return "success", f"{words} finished: its result is shown below."
    return "error", f"{words} did not finish. {plain(job_phase(doc))}"

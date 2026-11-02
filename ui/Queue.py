"""
Queue page for the run library: background solves (run-library-design.md, section 8.2).

Shows every job of the library's runs -- waiting, running (elapsed time, the last log line,
the loop iteration), done, failed or interrupted -- and keeps showing it across tab closes
and server restarts: the queue is on disk (status.json in each results folder, S2), the
worker is a detached process, and the manager is one per server (`st.cache_resource`, R5).
Jobs can be cancelled (the worker's per-job token first, a verified kill second, S9) and
re-run ("run again" never leaves two workers on one run, S8).

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from datetime import datetime

import streamlit as st

import libraryjobs
import sskeys as kz
from owlplanner.library import PRESETS
from owlplanner.library import results as R

st.markdown("# :material/schedule: Queue")
kz.divider("orange")

_ICON = {"waiting": ":material/hourglass_top:", "running": ":material/autorenew:",
         "done": ":material/check_circle:", "failed": ":material/error:",
         "interrupted": ":material/warning:"}


def _since(iso, now=None):
    then = R.stamp_seconds(iso)  # offset-aware (H3); an unreadable stamp shows "-" (M6)
    if then is None:
        return "-"
    seconds = max(0.0, (now or datetime.now().timestamp()) - then)
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.1f}h"


manager = libraryjobs.get_manager()  # one per server (R5); it ticks on its own (H5)

# -- queue a solve -----------------------------------------------------
runs = manager.library.runs()
with st.expander("Solve a run", expanded=not manager.jobs()):
    if not runs:
        st.caption("The library has no runs yet.")
    else:
        labels = {f"{r.name} ({r.folder_name})": r for r in runs}
        col1, col2, col3 = st.columns([4, 2, 2], vertical_alignment="bottom")
        choice = col1.selectbox("Run", list(labels), key="queue_run")
        preset = col2.selectbox("Preset", list(PRESETS), key="queue_preset",
                                help="quick: the default loop, claiming ages held at the "
                                     "scenario's values. custom: the case's own options.")
        if col3.button("Solve", type="primary", use_container_width=True):
            job = manager.enqueue(labels[choice], preset=preset)
            st.toast(f"Queued {job.id}")
            st.rerun()


@st.fragment(run_every=2.0)
def queue_fragment():
    manager.tick()  # the ticker thread does this too; ticking here shows a click's effect at once
    jobs = manager.jobs()
    if not jobs:
        st.info("No jobs yet. A queued solve shows up here and keeps running if the tab closes.")
        return

    now = datetime.now().timestamp()
    header = st.columns([4, 2, 2, 4, 2])
    header[0].markdown("**Run**")
    header[1].markdown("**State**")
    header[2].markdown("**Elapsed**")
    header[3].markdown("**Last log line**")
    for job in reversed(jobs):
        doc = job.doc
        row = st.columns([4, 2, 2, 4, 2])
        row[0].markdown(f"**{doc.get('run')}**  \n`{job.id}` · {doc.get('preset')}")
        beat_note = "" if doc.get("state") != R.RUNNING else f"  \nbeat {_since(doc.get('heartbeat'), now)} ago"
        row[1].markdown(f"{_ICON.get(doc.get('state'), '')} {doc.get('state')}{beat_note}")
        started = doc.get("started") or doc.get("queued")
        finished = doc.get("finished")
        row[2].markdown(_since(started, R.stamp_seconds(finished) or now))
        logline = doc.get("last_log") or ""
        if doc.get("iteration") is not None:
            logline = f"iter {doc['iteration']}  \n{logline}"
        if doc.get("error"):
            logline = f"{doc['error']}  \n{logline}"
        row[3].markdown(logline[-300:] if logline else "-")
        with row[4]:
            if doc.get("state") in (R.WAITING, R.RUNNING):
                if st.button("Cancel", key=f"cancel_{job.id}", help="Cancels the job: the worker "
                             "stops at its next step, or is killed when it is the recorded process."):
                    manager.cancel(job, force=True)
                    st.rerun()
            elif doc.get("state") in (R.INTERRUPTED, R.FAILED):
                if st.button("Run again", key=f"again_{job.id}",
                             help="Re-runs the job in the same results folder (a fresh token)."):
                    manager.run_again(job)
                    st.rerun()


queue_fragment()

if any(j.state in (R.WAITING, R.RUNNING) for j in manager.jobs()):
    if st.button("Stop all jobs"):
        manager.stop_all()
        st.rerun()

st.caption(
    "Jobs are detached processes: closing this tab or stopping the server does not stop them. "
    "Elapsed is measured from queue time; the state and the log line refresh every two seconds."
)

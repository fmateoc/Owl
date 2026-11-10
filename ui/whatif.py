"""
Fork: a what-if from the Scenario page to its comparison (local-use review D4).

Buying in 2031 instead of 2029 took 13 actions over 4 pages and ended on the wrong
comparison: saving did not offer to solve, the Run page opened on the baseline, and Compare's
default pair was not the what-if against the run it was made from. *Save and solve* on the
Scenario page saves the child run, queues its *Careful* solve and opens its page;
*Compare with its parent* there opens Compare on that pair.

A comparison is like for like only when both sides were solved the same way on the same day
(plans start today; Compare flags the rest). So the parent's *Careful* solve is queued too
when it has none from today: without it the pair would be a Careful result against a Quick
look, or against last week's plan.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from datetime import date

import streamlit as st

import libraryjobs
from owlplanner.library import preset_solves
from owlplanner.library import results as R
from owlplanner.library import view

PRESET = "decision"  # "Careful": local search and its exact-model companion
PAIR_KEY = "compare_pair"  # {"a": (run id, results folder), "b": (...)}: Compare opens on it


def main_results(manager, run) -> list:
    """The run's solved headline results, newest first: [(job, Result)]. A model companion
    (the exact-model check) is not one (R2)."""
    out = []
    for job in reversed(manager.jobs(run)):
        if not (job.results_dir / R.RECORD_JSON).exists():
            continue
        result = view.load_result(job.results_dir)
        if result.solved and not view.is_companion(result):
            out.append((job, result))
    return out


def _live_presets(manager, run) -> set:
    return {str(job.doc.get("preset")) for job in libraryjobs.live_jobs(manager, run)}


def is_current(manager, run, preset=PRESET, today=None) -> bool:
    """Does the run have a solve under `preset` that a new one would only repeat: a solved
    result of today, or a job waiting or running?"""
    if preset in _live_presets(manager, run):
        return True
    today = (today or date.today()).isoformat()
    for _job, result in main_results(manager, run):
        if result.record.get("preset") == preset:
            return ((result.record.get("solve_date") or {}).get("finished") or "")[:10] == today
    return False


def queue_careful(manager, run) -> list:
    """Queue the run's *Careful* solves (the solve and its companion) unless it has a current
    one; a solve of the pair already waiting or running is not queued twice. Returns the jobs
    queued. Raises what `enqueue` raises (a run from another plan year)."""
    if is_current(manager, run):
        return []
    live = _live_presets(manager, run)
    jobs = [manager.enqueue(run, preset=solve) for solve in preset_solves(PRESET) if solve not in live]
    libraryjobs.watch_jobs(run.id, jobs)  # the Run page notices their end (D3)
    return jobs


def queue_what_if(manager, run, parent) -> tuple:
    """(the run's jobs queued, the parent's): the what-if's solve first, then its parent's
    when the parent has no *Careful* result from today to compare it with."""
    mine = queue_careful(manager, run)
    theirs = []
    if parent is not None:
        try:
            theirs = queue_careful(manager, parent)
        except Exception as exc:  # noqa: BLE001 - the what-if is queued; say why its pair is not
            libraryjobs.flash("warning", f"*{libraryjobs.plain(parent.name)}* was not queued for the "
                                         f"comparison: {libraryjobs.plain(exc)}")
    return mine, theirs


def parent_pair(manager, run, parent, shown=None):
    """((parent job, Result), (run job, Result)) to compare, or None while either side has no
    solved headline result. B is the result the Run page shows (`shown`, a job) when it is a
    solved headline one, else the run's newest; A is the parent's newest result solved the
    same way, else its newest."""
    mine, theirs = main_results(manager, run), main_results(manager, parent)
    if not mine or not theirs:
        return None
    b = next((entry for entry in mine if shown is not None and entry[0].id == shown.id), mine[0])
    preset = b[1].record.get("preset")
    a = next((entry for entry in theirs if entry[1].record.get("preset") == preset), theirs[0])
    return a, b


def open_compare(parent, run, pair) -> None:
    """Send the reader to Compare on that pair (A the parent's result, B the run's)."""
    (job_a, _result_a), (job_b, _result_b) = pair
    st.session_state[PAIR_KEY] = {"a": (parent.id, job_a.id), "b": (run.id, job_b.id)}
    st.switch_page("Compare.py")

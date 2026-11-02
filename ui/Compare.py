"""
Comparison page for the run library (run-library-design.md, section 9.2): the decision screen.

Two results, side by side: the inputs' difference in words, the outputs with each difference
judged against the noise rule (R2; CLAUDE.md, "Loop noise") -- proved plans by their reported
gap x objective, loop and local-search solves by the 1% band -- the flags of S13 (solved on
different days, different presets, different Owl commits), R3's two numbers (the score and
the home at the end, never added: "leads" or "trade-off"), the agreement check against the
exact model when each run has one, and "what moved" year by year.

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

import pandas as pd
import streamlit as st

import libraryjobs
import sskeys as kz
from owlplanner.library import compare as C
from owlplanner.library import results as R
from owlplanner.library import view
from owlplanner.library.scenario import diff_summaries

st.markdown("# :material/compare_arrows: Compare two results")
kz.divider("orange")

manager = libraryjobs.get_manager()
lib = manager.library


def _catalog():
    """Every results folder that has a record: [(label, run, job, record)]."""
    out = []
    for run in reversed(lib.runs()):
        for job in reversed(manager.jobs(run)):
            record = R.read_record(job.results_dir)
            if record is None:
                continue
            when = (record.get("solve_date") or {}).get("finished") or job.doc.get("queued") or ""
            label = (f"{run.name} ({run.folder_name}) · {job.id} · "
                     f"{record.get('preset') or job.doc.get('preset')} · "
                     f"{when[:10] or 'no solve'} · {record.get('status') or job.state}")
            out.append((label, run, job, record))
    return out


def _companion(run, exclude):
    """The run's exact-model solve, if it has one (R2's agreement check)."""
    results = [view.load_result(job.results_dir)
               for job in manager.jobs(run) if (job.results_dir / R.RECORD_JSON).exists()]
    return C.exact_companion(results, exclude=exclude)


def _signed(value):
    return "-" if value is None else f"{value:+,.0f}"


def _number(value):
    return "-" if value is None else f"{value:,.0f}"


catalog = _catalog()
if len(catalog) < 2:
    st.info("Two results are needed: solve at least two runs (or the same run twice).")
    st.stop()

labels = [label for label, _, _, _ in catalog]
# The default pair is two main solves from two different runs (a run's exact-model
# companion is a check, not a headline, R2).
a_idx = next((i for i, e in enumerate(catalog) if not view.record_is_exact_lp(e[3])), 0)
b_idx = next((i for i, e in enumerate(catalog)
              if i != a_idx and not view.record_is_exact_lp(e[3]) and e[1].id != catalog[a_idx][1].id),
             min(1, len(catalog) - 1))
col1, col2 = st.columns(2)
a_label = col1.selectbox("Result A (the reference)", labels, key="cmp_a", index=a_idx)
b_label = col2.selectbox("Result B", labels, key="cmp_b", index=b_idx)

(_, run_a, job_a, _), (_, run_b, job_b, _) = (
    next(entry for entry in catalog if entry[0] == a_label),
    next(entry for entry in catalog if entry[0] == b_label),
)
a = view.load_result(job_a.results_dir)
b = view.load_result(job_b.results_dir)
if not (a.solved and b.solved):
    st.warning("Both results must be solved before they can be compared: "
               f"A is {a.record.get('status') or 'unsolved'}, B is {b.record.get('status') or 'unsolved'}.")
    st.stop()

# -- inputs (design 9.2) ----------------------------------------------

st.markdown("#### Inputs")
if run_a.id == run_b.id:
    st.caption("The same run, solved twice: no input changes.")
else:
    try:
        changes = diff_summaries(lib.scenario(run_a), lib.scenario(run_b))
    except Exception as exc:  # noqa: BLE001 - a damaged scenario is shown, not raised
        changes = [f"(cannot read one of the scenarios: {exc})"]
    if changes:
        for change in changes:
            st.markdown(f"- {change}")
    else:
        st.caption("Identical inputs.")

# -- outputs (design 9.2, R2, R3) -------------------------------------

st.markdown("#### Outputs")
st.caption(f"A = *{run_a.name}* ({job_a.id}); B = *{run_b.name}* ({job_b.id}). "
           "Amounts in today's dollars; the difference is B - A.")
header = st.columns([3, 2, 2, 2, 3])
for cell, text in zip(header, ("number", "A", "B", "difference", "reading"), strict=True):
    cell.markdown(f"**{text}**")

comparison = C.compare(a, b,
                       a_exact=_companion(run_a, exclude={job_a.id}),
                       b_exact=_companion(run_b, exclude={job_b.id}))
for row in comparison.rows:
    cells = st.columns([3, 2, 2, 2, 3])
    cells[0].markdown(f"**{row.label}**")
    cells[1].markdown(_number(row.a))
    cells[2].markdown(_number(row.b))
    cells[3].markdown(_signed(row.delta))
    reading = {"resolved": "resolved", "within noise": "~ unresolved",
               "no difference": "no difference", "-": "-"}[row.verdict]
    if row.note:
        reading += f"  \n{row.note}"
    cells[4].markdown(reading)

verdict = comparison.lead["verdict"]
st.markdown(f"### {verdict}")
if comparison.lead.get("note"):
    st.caption(comparison.lead["note"])

for flag in comparison.flags:
    st.warning(flag, icon=":material/flag:")

# -- the exact model's agreement check (R2) ---------------------------

agree = comparison.agreement
if agree:
    st.markdown("#### The exact model, as a check")
    st.caption(
        "The same pair under local search and under the exact model (the loop with Medicare "
        "off, SS taxability 0.85 and capital gains priced exactly: a different model, so only "
        "its differences compare). A difference counts when both models give it the same sign "
        "and it is larger than their spread plus the error bars of unsettled loops (R2)."
    )
    st.markdown(
        f"- difference under local search: **{_signed(agree['delta_local_search'])}**\n"
        f"- difference under the exact model: **{_signed(agree['delta_exact'])}**\n"
        f"- spread between the two: {_number(agree['spread'])}; "
        f"error bars: {_number(agree['error_bars'])}\n"
        f"- reading: **{agree['verdict']}**"
    )
    if agree.get("note"):
        st.caption(agree["note"])
elif a.solved and b.solved:
    st.caption("No exact-model companion on both sides: the agreement check needs the exact "
               "result of each run (solve both with the Decision preset).")

# -- what moved (design 9.2) ------------------------------------------

st.markdown("#### What moved")
if comparison.what_moved:
    labels_by_key = dict(C.WHAT_MOVED)
    keys = list(comparison.what_moved[0]["changes"])
    frame = pd.DataFrame(
        [{"year": row["year"],
          **{labels_by_key[key]: row["changes"][key] for key in keys}}
         for row in comparison.what_moved]
    )
    totals = {"year": "lifetime"}
    totals.update(dict(comparison.what_moved_totals))
    st.dataframe(pd.concat([frame, pd.DataFrame([totals])], ignore_index=True),
                 width="stretch")
    st.caption("Year-by-year differences (B - A), nominal dollars. This is why one result "
               "leads, not only that it leads.")
else:
    st.caption("Nothing moved by more than a dollar in any year.")

st.caption(
    "Noise rule (R2): a proved plan (branch-and-bound) is judged by its reported gap x "
    "objective; a loop or local-search solve has no gap, so a difference under 1% of the "
    "reference is unresolved (grey, ~) -- the loop settling on another fixed point can make "
    "it, with either sign -- and at or above 1% it counts. When in doubt, run both again "
    "today with the Decision preset."
)

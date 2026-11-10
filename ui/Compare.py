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
import librarypresets
import run_charts
import sskeys as kz
import whatif
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
                     f"{librarypresets.name(record.get('preset') or job.doc.get('preset'))} · "
                     f"{when[:10] or 'no solve'} · {record.get('status') or job.state}")
            out.append((label, run, job, record))
    return out


def _companion(run, exclude, near):
    """The run's exact-model solve, if it has one (R2's agreement check)."""
    results = [view.load_result(job.results_dir)
               for job in manager.jobs(run) if (job.results_dir / R.RECORD_JSON).exists()]
    return C.exact_companion(results, exclude=exclude, near=near)


def _signed(value):
    return "-" if value is None else f"{value:+,.0f}"


def _number(value):
    return "-" if value is None else f"{value:,.0f}"


catalog = _catalog()
if len(catalog) < 2:
    st.info("Two results are needed: solve at least two runs (or the same run twice).")
    st.stop()

labels = [label for label, _, _, _ in catalog]
# The default pair (UX review Q4): B the newest main solve, A the newest main solve of B's
# parent run (what B was edited from), else of another run. A run's model companion -- the
# exact LP, or the tornado's Medicare model, review AJ1 -- is a check, not a headline (R2).
_baseline = lib.baseline()  # S-1: A defaults to the pinned baseline when B has no parent result
a_idx, b_idx = C.default_pair([
    (run.id, run.parent, R.stamp_seconds((record.get("solve_date") or {}).get("finished")),
     record.get("status") == "solved" and view.record_companion(record) is None,
     _baseline is not None and run.id == _baseline.id)
    for _label, run, _job, record in catalog])
# A pair another page asked for (local-use review D4: the Run page's *Compare with its
# parent*). The selectors are driven through the session, as "Open" drives the Run page's
# (P2): a drawn widget keeps its value and would override `index`.
_asked = st.session_state.pop(whatif.PAIR_KEY, None)
_default = {"cmp_a": a_idx, "cmp_b": b_idx}
if _asked:
    for _side, _widget in (("a", "cmp_a"), ("b", "cmp_b")):
        _label = next((label for label, run, job, _record in catalog
                       if (run.id, job.id) == tuple(_asked.get(_side) or ())), None)
        if _label is not None:
            st.session_state[_widget] = _label
            _default[_widget] = 0  # no default beside a session-set value (Streamlit warns)
col1, col2 = st.columns(2)
a_label = col1.selectbox("Result A (the reference)", labels, key="cmp_a", index=_default["cmp_a"])
b_label = col2.selectbox("Result B", labels, key="cmp_b", index=_default["cmp_b"])

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

units = run_charts.units_control("cmp_units")
comparison = C.compare(a, b,
                       a_exact=_companion(run_a, exclude={job_a.id, job_b.id}, near=a),
                       b_exact=_companion(run_b, exclude={job_a.id, job_b.id}, near=b),
                       units=units)
if run_a.id == run_b.id:
    changes = []
else:
    try:
        changes = diff_summaries(lib.scenario(run_a), lib.scenario(run_b))
    except Exception as exc:  # noqa: BLE001 - a damaged scenario is shown, not raised
        changes = [f"(cannot read one of the scenarios: {exc})"]

# -- the verdict in words (S-5) -----------------------------------------
# The lead verdict (R3) as a sentence with the runs' names and the amounts; under it where
# the difference shows up (the largest lifetime lines of "what moved") and, apart, the inputs
# that differ. No "driven by": in an optimized plan taxes, conversions and spending move
# together, and "what moved" says where a difference shows up, not what caused it (decision 8).
_objective = C.objective_of(a)
_name_a = run_a.name if run_a.id != run_b.id else f"{run_a.name} ({job_a.id})"
_name_b = run_b.name if run_a.id != run_b.id else f"{run_b.name} ({job_b.id})"
st.info(C.verdict_sentence(comparison, _name_a, _name_b, view.score_name(a), _objective),
        icon=":material/balance:")
_where = C.where_it_shows_up(comparison.what_moved_totals)
if _where:
    _tot_units = "today's \\$" if comparison.what_moved_totals_units == "today" else "nominal \\$"
    st.markdown("**Where the difference shows up** (lifetime, B - A, " + _tot_units + "): "
                + "; ".join(f"{label} {value:+,.0f}" for label, value in _where) + ".")
if run_a.id == run_b.id:
    st.markdown("**Inputs that differ:** none (the same run, solved twice).")
elif changes:
    st.markdown("**Inputs that differ:** " + libraryjobs.plain("; ".join(changes[:4]))
                + ("; ..." if len(changes) > 4 else ""))
else:
    st.markdown("**Inputs that differ:** none (identical inputs).")
for flag in comparison.flags:
    st.warning(flag, icon=":material/flag:")

# -- inputs (design 9.2) ----------------------------------------------

if len(changes) > 4:
    with st.expander(f"All {len(changes)} input changes"):
        for change in changes:
            st.markdown(f"- {libraryjobs.plain(change)}")

# -- outputs (design 9.2, R2, R3) -------------------------------------

st.markdown("#### Outputs")
st.caption(f"A = *{run_a.name}* ({job_a.id}); B = *{run_b.name}* ({job_b.id}). "
           "Amounts in today's dollars; the difference is B - A.")
header = st.columns([3, 2, 2, 2, 3])
for cell, text in zip(header, ("number", "A", "B", "difference", "reading"), strict=True):
    cell.markdown(f"**{text}**")

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

# -- how sure is this? (R2, the agreement check) -------------------------

agree = comparison.agreement
with st.expander("How sure is this?"):
    st.markdown(f"The rule's reading: **{comparison.lead['verdict']}**"
                + (f" ({comparison.lead['note']})." if comparison.lead.get("note") else "."))
    st.caption(
        "Noise rule: a proved plan (branch-and-bound) is judged by its reported gap x "
        "objective; a loop or local-search solve has no gap, so a difference under 1% of the "
        "reference is unresolved (grey, ~) -- the loop settling on another fixed point can make "
        "it, with either sign -- and at or above 1% it counts. When in doubt, run both again "
        "today with the *Careful* preset."
    )
    if agree:
        _v = agree["verdict"]
        _says = ("a second method agrees" if _v.startswith("resolved")
                 else "a second method disagrees" if "disagree" in _v
                 else "a second method does not settle it")
        st.markdown(f"**The exact model, as a check:** {_says}.")
        st.caption(
            "The pair as selected and under the exact model (the loop with Medicare "
            "off, SS taxability 0.85 and capital gains priced exactly: a different model, so only "
            "its differences compare). A difference counts when both models give it the same sign "
            "and it is larger than their spread plus the error bars of unsettled loops."
        )
        st.markdown(
            f"- difference in the selected pair: **{_signed(agree['delta_pair'])}**\n"
            f"- difference under the exact model: **{_signed(agree['delta_exact'])}**\n"
            f"- spread between the two: {_number(agree['spread'])}; "
            f"error bars: {_number(agree['error_bars'])}\n"
            f"- reading: **{agree['verdict']}**"
        )
        if agree.get("note"):
            st.caption(agree["note"])
    else:
        st.caption("No exact-model companion on both sides: the agreement check needs an exact "
                   "result of its own for each run (solve both with the *Careful* preset).")

# -- side by side (S-5) -------------------------------------------------

st.markdown("#### Side by side")
_rows_a = a.plan.get("by_year") or []
_rows_b = b.plan.get("by_year") or []
if _rows_a and _rows_b:
    _diff = st.toggle("Show the difference (B - A)", key="cmp_diff")
    if units == "today" and not (run_charts.has_deflator(_rows_a) and run_charts.has_deflator(_rows_b)):
        st.caption("One result was solved before the charts could show today's dollars: both are drawn in "
                   "nominal dollars. A new solve can show today's dollars.")
        _units = "nominal"
    else:
        _units = units
    _sa, _sb = run_charts.compare_series(_rows_a, _units), run_charts.compare_series(_rows_b, _units)
    # MAGI comes from the brackets rows (today's dollars): nominal only when both carry the deflator.
    _mu = "nominal" if all(run_charts.magi_units(r, _units) == "nominal" for r in (_rows_a, _rows_b)) else "today"
    _ma = run_charts.magi_series((a.plan.get("brackets") or {}).get("years"), _rows_a, _mu)
    _mb = run_charts.magi_series((b.plan.get("brackets") or {}).get("years"), _rows_b, _mu)
    _tabs = st.tabs(list(run_charts.COMPARE_CHARTS))
    for _tab, _chart in zip(_tabs, run_charts.COMPARE_CHARTS, strict=True):
        with _tab:
            if _chart == "MAGI":
                if not (_ma[0] and _mb[0]):
                    st.caption("MAGI by year needs both results' conversion and bracket view (a newer solve).")
                    continue
                _fig = run_charts.compare_figure(
                    _chart, _ma[0], _mb[0], ("A", "B"), _diff,
                    run_charts.TODAY_PER_YEAR if _mu == "today" else run_charts.NOMINAL_PER_YEAR,
                    lines_a=(("A: IRMAA tier 1", _ma[1]), ("A: 400% FPL", _ma[2])),
                    lines_b=(("B: IRMAA tier 1", _mb[1]), ("B: 400% FPL", _mb[2])))
            else:
                _per_year = _chart == "Spending"
                _axis = (run_charts.axis_title(_rows_a, _units, per_year=_per_year))
                _fig = run_charts.compare_figure(_chart, _sa[_chart], _sb[_chart], ("A", "B"), _diff, _axis)
            st.plotly_chart(_fig, width="stretch")
    st.caption(f"A = *{run_a.name}*, B = *{run_b.name}*, matched by calendar year.")

# -- what moved (design 9.2) ------------------------------------------

_row_units = "today's \\$" if comparison.what_moved_units == "today" else "nominal \\$"
_tot_units = "today's \\$" if comparison.what_moved_totals_units == "today" else "nominal \\$"
st.markdown(f"#### What moved ({_row_units})")
if comparison.what_moved:
    labels_by_key = dict(C.WHAT_MOVED)
    keys = list(comparison.what_moved[0]["changes"])
    frame = pd.DataFrame(
        [{"year": str(row["year"]),
          **{labels_by_key[key]: row["changes"][key] for key in keys}}
         for row in comparison.what_moved]
    )
    # The lifetime row sums years, so it is in today's dollars whenever both results allow it
    # (S-5: a sum of nominal dollars of different years was a defect).
    shown = {labels_by_key[key] for key in keys}
    totals = {"year": f"lifetime ({_tot_units.replace(chr(92), '')})"}
    totals.update({k: v for k, v in comparison.what_moved_totals if k in shown})
    st.dataframe(pd.concat([frame, pd.DataFrame([totals])], ignore_index=True),
                 width="stretch", hide_index=True,
                 column_config={label: st.column_config.NumberColumn(format="localized")
                                for label in labels_by_key.values()})
    st.caption(f"Year-by-year differences (B - A), {_row_units}; the lifetime row in {_tot_units}. Where "
               "a difference shows up, not what caused it: in an optimized plan these move together.")
else:
    st.caption("Nothing moved by more than a dollar in any year.")

"""
Spec tests for the Phase 5 step 2 HFP columns: ``gross earnings`` and ``months worked``.

Plan: ``fork-notes/phase5-plan.md`` §4.2 (inputs), §5 step 2 (round trip, defaults,
refusals). Expected behaviour is from that plan and the existing optional-column
conventions in ``hfp_io.py`` — not from the code under test.

Committed test-first (plan §5b); the markers were removed when the implementation landed.

Month / money conventions:
  ``gross earnings``   nominal $, W-2 box 5 + net SE (D1). Absent → ``anticipated wages``
                       plus a warning naming years where a deferral column is non-zero.
  ``months worked``    0-12, months of work at the start of the year (D2). Absent →
                       12 when that year's earnings are positive, else 0.

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

import os
import tempfile
from datetime import date

import pytest

import owlplanner as owl
from owlplanner import hfp_io

thisyear = date.today().year


def _plan(name="Alice", birth="1970-01-15", remaining=30):
    birth_year = int(birth[:4])
    expectancy = (thisyear - birth_year) + remaining
    return owl.Plan([name], [birth], [expectancy], "Step 2", verbose=False)


def _write_and_reload(p, name="Alice", birth="1970-01-15", remaining=30, drop=None):
    """Save the plan's HFP table to a temp xlsx (optionally dropping columns) and reload."""
    df = p.timeLists[name].copy()
    if drop:
        df = df.drop(columns=drop)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        df.to_excel(tmp.name, sheet_name=name, index=False)
        p2 = _plan(name=name, birth=birth, remaining=remaining)
        p2.readHFP(tmp.name)
        return p2, tmp.name
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


# --------------------------------------------------------------------------------------
# Schema surface
# --------------------------------------------------------------------------------------


def test_columns_are_recognized_hfp_headers():
    """§4.2: two optional per-person columns in the Wages and Contributions table."""
    cols = hfp_io.timeHorizonItems()
    assert "gross earnings" in cols
    assert "months worked" in cols
    # Only 'year' is required; these two are optional like the rest.
    assert "year" in cols
    assert cols.index("gross earnings") > cols.index("year")


def test_typo_near_new_names_is_still_rejected():
    """A header that folds to a recognized one is a typo, not a helper column."""
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"].rename(columns={"gross earnings": "gross earnings "})
    # The trailing-space variant folds to 'gross earnings' and must be refused, not dropped.
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        df.to_excel(tmp.name, sheet_name="Alice", index=False)
        p2 = _plan()
        with pytest.raises(Exception, match="typo|Gross|gross"):
            p2.readHFP(tmp.name)
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


# --------------------------------------------------------------------------------------
# Load into plan arrays
# --------------------------------------------------------------------------------------


def test_present_columns_land_in_et_arrays():
    """``setContributions`` maps the two columns to ``etEarnings_in`` / ``etMonths_in``."""
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    # Plan-year 0 is row 5 (five lead-in years).
    df.loc[df.index[5], "gross earnings"] = 120_000.0
    df.loc[df.index[5], "months worked"] = 6
    df.loc[df.index[6], "gross earnings"] = 40_000.0
    df.loc[df.index[6], "months worked"] = 12
    p.setContributions()

    assert hasattr(p, "etEarnings_in")
    assert hasattr(p, "etMonths_in")
    assert p.etEarnings_in.shape == (p.N_i, p.N_n)
    assert p.etMonths_in.shape == (p.N_i, p.N_n)
    assert p.etEarnings_in[0, 0] == pytest.approx(120_000.0)
    assert p.etMonths_in[0, 0] == 6
    assert p.etEarnings_in[0, 1] == pytest.approx(40_000.0)
    assert p.etMonths_in[0, 1] == 12
    assert p.etEarnings_in[0, 2] == 0
    assert p.etMonths_in[0, 2] == 0


def test_absent_gross_earnings_falls_back_to_anticipated_wages():
    """D1 (a): absent ``gross earnings`` → ``anticipated wages``, not zero (unlike other
    optional columns). The column is still recorded as absent."""
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "anticipated wages"] = 90_000.0
    df.loc[df.index[6], "anticipated wages"] = 50_000.0
    p.setContributions()

    p2, tmp = _write_and_reload(p, drop=["gross earnings"])
    try:
        assert "gross earnings" in p2.hfpAbsentCols["Alice"]
        # Fallback: countable earnings track anticipated wages when the column is absent.
        assert p2.etEarnings_in[0, 0] == pytest.approx(90_000.0)
        assert p2.etEarnings_in[0, 1] == pytest.approx(50_000.0)
        # ... but the raw column in timeLists is zero-filled like any other absent column.
        assert p2.timeLists["Alice"]["gross earnings"].iloc[5] == 0
    finally:
        os.unlink(tmp)


def test_absent_months_worked_defaults_by_earnings():
    """D2: absent ``months worked`` → 12 when that year's earnings are positive, else 0.

    The default keys off the *effective* countable earnings (``gross earnings`` if the
    column is present, else the ``anticipated wages`` fallback) — not off wages alone.
    """
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "gross earnings"] = 95_000.0  # present and positive
    df.loc[df.index[6], "gross earnings"] = 0.0  # present, explicit zero
    df.loc[df.index[6], "anticipated wages"] = 90_000.0  # wages alone do not count
    p.setContributions()

    p2, tmp = _write_and_reload(p, drop=["months worked"])
    try:
        assert "months worked" in p2.hfpAbsentCols["Alice"]
        assert p2.etMonths_in[0, 0] == 12  # gross earnings > 0
        assert p2.etMonths_in[0, 1] == 0  # gross present and 0: default is 0, not 12
    finally:
        os.unlink(tmp)


def test_present_zero_months_worked_is_not_replaced_by_default():
    """An explicit ``months worked`` of 0 is not a missing column (symmetry with gross)."""
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "gross earnings"] = 90_000.0
    df.loc[df.index[5], "months worked"] = 0
    p.setContributions()
    assert p.etMonths_in[0, 0] == 0  # user wins over the 12-when-earning default


def test_present_zero_gross_earnings_is_not_replaced_by_wages():
    """An explicit zero is not a missing column: the user's value wins over the fallback.

    Jointly with ``test_present_zero_months_worked_is_not_replaced_by_default``: both
    columns are literal when present.
    """
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "anticipated wages"] = 90_000.0
    df.loc[df.index[5], "gross earnings"] = 0.0
    df.loc[df.index[5], "months worked"] = 0
    p.setContributions()
    assert p.etEarnings_in[0, 0] == 0
    assert p.etMonths_in[0, 0] == 0


def test_fallback_warning_names_deferral_years():
    """§4.2: a warning names the years where a deferral column is non-zero in a test year.

    Fires when ``setContributions`` applies the ``anticipated wages`` fallback (the
    array-build path), naming calendar years in which any payroll/tax-advantaged
    contribution column is non-zero. Those columns are *401k ctrb*, *Roth 401k ctrb*,
    *IRA ctrb*, *Roth IRA ctrb*, and *HSA ctrb*.
    """
    log_lines = []

    class _Log:
        def print(self, msg, tag=None):
            log_lines.append(f"{tag}: {msg}")

        def vprint(self, msg):
            log_lines.append(msg)

    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "anticipated wages"] = 90_000.0
    df.loc[df.index[5], "401k ctrb"] = 10_000.0
    df.loc[df.index[6], "anticipated wages"] = 50_000.0  # no deferral this year
    p.setContributions()

    p2, tmp = _write_and_reload(p, drop=["gross earnings"])
    try:
        p2.mylog = _Log()
        p2.setContributions()
        text = "\n".join(log_lines)
        assert "gross earnings" in text
        assert str(thisyear) in text  # the deferral year is named
    finally:
        os.unlink(tmp)


# --------------------------------------------------------------------------------------
# Round trip
# --------------------------------------------------------------------------------------


def test_round_trip_workbook_plan_workbook():
    """§5 step 2: workbook → plan → workbook keeps both columns (values, not just headers)."""
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "gross earnings"] = 111_000.0
    df.loc[df.index[5], "months worked"] = 7
    p.setContributions()

    p2, tmp = _write_and_reload(p)
    try:
        assert p2.etEarnings_in[0, 0] == pytest.approx(111_000.0)
        assert p2.etMonths_in[0, 0] == 7
        # Write-back carries the column *values*, not just the headers.
        wb = p2.saveContributions()
        sheet = wb["Alice"]
        headers = [c.value for c in sheet[1]]
        i_gross = headers.index("gross earnings") + 1
        i_months = headers.index("months worked") + 1
        # Row 1 is the header; plan year 0 is Excel row 7 (five lead-in rows + header).
        assert sheet.cell(row=7, column=i_gross).value == pytest.approx(111_000.0)
        assert sheet.cell(row=7, column=i_months).value == 7
    finally:
        os.unlink(tmp)


def test_clone_with_new_expectancy_keeps_columns():
    """§5 step 2: ``clone`` with a new horizon keeps the two columns.

    ``clone`` re-applies HFP from ``rawHFP``, so the plan must have been through
    ``readHFP`` (the same way the UI syncs the per-person tables). Account balances
    are required because clone serializes the full plan.
    """
    p = _plan(remaining=30)
    p.setAccountBalances(taxable=[100], taxDeferred=[500], taxFree=[100])
    p.setAllocationRatios("individual", generic=[[[60, 40, 0, 0], [60, 40, 0, 0]]])
    p.setRates("conservative")
    p.setSpendingProfile("flat")
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "gross earnings"] = 77_000.0
    df.loc[df.index[5], "months worked"] = 4
    df.loc[df.index[6], "gross earnings"] = 88_000.0
    df.loc[df.index[6], "months worked"] = 12
    p.setContributions()
    # Populate rawHFP the way the UI sync does, so clone can rebuild from it.
    p.readHFP({n: p.timeLists[n] for n in p.inames}, houseTables=False)

    c = owl.clone(p, expectancy=[(thisyear - 1970) + 25], verbose=False)
    assert c.etEarnings_in[0, 0] == pytest.approx(77_000.0)
    assert c.etMonths_in[0, 0] == 4
    assert c.etEarnings_in[0, 1] == pytest.approx(88_000.0)
    assert c.etMonths_in[0, 1] == 12


# --------------------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad_months", [-1, 13, 12.5, 6.5])
def test_months_worked_outside_0_12_refused(bad_months):
    """§5 step 2: bad values refused like other columns. Months must be an integer in [0, 12].

    12.5 is outside [0, 12] on the reals; 6.5 is inside the interval but is not a whole
    month. ``months worked`` is a count (plan §4.2; ``earnings_test`` takes ``int``).
    """
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"].copy()
    # The live table may hold an integer dtype; allow a bad entry into the sheet itself.
    df["months worked"] = df["months worked"].astype(float)
    df.loc[df.index[5], "months worked"] = bad_months
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        df.to_excel(tmp.name, sheet_name="Alice", index=False)
        p2 = _plan()
        with pytest.raises(Exception, match="months worked"):
            p2.readHFP(tmp.name)
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


def test_negative_gross_earnings_refused():
    """§5 step 2: negative earnings refused (like other amounts)."""
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "gross earnings"] = -1.0
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        df.to_excel(tmp.name, sheet_name="Alice", index=False)
        p2 = _plan()
        with pytest.raises(Exception, match="gross earnings"):
            p2.readHFP(tmp.name)
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


def test_zero_wages_reset_clears_et_arrays_and_columns():
    """``zeroWagesAndContributions`` rebuilds the tables with both columns present."""
    p = _plan()
    p.zeroWagesAndContributions()
    df = p.timeLists["Alice"]
    df.loc[df.index[5], "gross earnings"] = 10_000.0
    df.loc[df.index[5], "months worked"] = 3
    p.setContributions()
    p.zeroWagesAndContributions()
    p.setContributions()
    assert (p.etEarnings_in == 0).all()
    assert (p.etMonths_in == 0).all()
    assert "gross earnings" in p.timeLists["Alice"].columns
    assert "months worked" in p.timeLists["Alice"].columns
    assert p.hfpAbsentCols["Alice"] == []


def test_fresh_plan_has_zero_et_arrays():
    """A new Plan starts with zero earnings-test inputs (like omega_in)."""
    p = _plan()
    assert (p.etEarnings_in == 0).all()
    assert (p.etMonths_in == 0).all()
    assert p.etEarnings_in.shape == (p.N_i, p.N_n)
    assert p.etMonths_in.shape == (p.N_i, p.N_n)

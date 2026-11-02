"""The "as of" date input: the date a case's inputs are valid at (run-library step 2).

Owl's plan starts in the calendar year of the solve whatever the case file says, and the
current month bounds the claiming ages ``withSSAges`` may choose (`Plan._ssaOpenAges` /
`Plan._ssaCheckPastAges` read `_ssaCurrentAgeMonths`), so results move with the day the
code happens to run on (`fork-notes/run-library-design.md` section 8.3; R1, S1, S7).  A run
must reproduce, so the "today" Owl reads is a first-class input: set once per process, and
every `date.today()` in the package goes through `today()` here.

Set it before anything that reads the calendar (import conditioning in `hfp_io.read`,
`toml_io.sanitize_config`, `Plan._setStartingDate`, the SSA open-ages check):

    from owlplanner import asof
    asof.set_as_of("2026-11-03")   # or a datetime.date; None restores the real today

`owlcli --as-of YYYY-MM-DD` sets it for a command; the run-library worker sets it to the
run's own "as of" date (the balances' date, validated to fall in the run's plan year) and
records it in `record.json`.  Tests pin it instead of monkeypatching `datetime.date`.

With no override set, `today()` is `datetime.date.today()`: the UI and every other caller
outside the library behave exactly as before.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator, Optional, Union

DateLike = Union[date, datetime, str]

_AS_OF: Optional[date] = None
# The `as_of(...)` context manager is thread-local: Streamlit sessions are threads of one
# process, and one session capturing a scenario must not date another session's solve. The
# process-wide `set_as_of` (owlcli, the worker, the test suite) is seen by every thread.
_LOCAL = threading.local()


def _parse(value: Optional[DateLike]) -> Optional[date]:
    """A DateLike as a date; None clears the override. Strings are 'YYYY-MM-DD'.

    Tests patch `date` itself, in every module including the `datetime` module
    (tests/conftest.py's freeze_year rebinds `datetime.date` to a subclass), so the input is
    duck-typed on year/month/day and the stored date is rebuilt from its fields.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.strptime(value.strip(), "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"as_of must be YYYY-MM-DD, got {value!r}") from exc
    if all(hasattr(value, attr) for attr in ("year", "month", "day")):
        # date, datetime, or a test's date subclass: one constructor, fields only.
        return date(value.year, value.month, value.day)
    raise TypeError(f"as_of must be a date, datetime or 'YYYY-MM-DD' string, got {type(value).__name__}")


def set_as_of(value: Optional[DateLike]) -> Optional[date]:
    """Freeze `today()` to `value` process-wide (or clear the freeze with None). Returns the date set."""
    global _AS_OF
    _AS_OF = _parse(value)
    return _AS_OF


def clear_as_of() -> None:
    """Remove the override: `today()` reads the real date again."""
    set_as_of(None)


def get_as_of() -> Optional[date]:
    """The frozen date in this thread's context, or None when `today()` reads the real one."""
    return getattr(_LOCAL, "as_of", None) or _AS_OF


def today() -> date:
    """Today: the frozen "as of" date when one is set, else the real date."""
    frozen = getattr(_LOCAL, "as_of", None) or _AS_OF
    return frozen if frozen is not None else date.today()


@contextmanager
def as_of(value: Optional[DateLike]) -> Iterator[Optional[date]]:
    """Context manager: freeze `today()` to `value` for a block, restore afterwards.

    Thread-local: sessions of a threaded server (Streamlit) do not see each other's freeze.
    """
    previous = getattr(_LOCAL, "as_of", None)
    _LOCAL.as_of = _parse(value)
    try:
        yield _LOCAL.as_of
    finally:
        _LOCAL.as_of = previous

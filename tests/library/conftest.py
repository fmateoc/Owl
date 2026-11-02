"""Shared fixtures for the run-library tests.

`pretend_today` moves the wall clock everywhere a module reads `date.today()` directly
(the `as_of` input must dominate it: two solves on different days give identical results,
step 2's check). The session's date pin itself is the `as_of` input (tests/conftest.py).
"""

import datetime
import sys
from contextlib import contextmanager

import pytest

_REAL_DATE = datetime.date


@contextmanager
def pretend_real_today(iso: str):
    """Pretend the wall clock reads `iso` ('YYYY-MM-DD') for every direct `date.today()`.

    Patches the `date` name of the `datetime` module and of every loaded module whose `date`
    is a `datetime.date` class, so lazily imported code sees the pretend day too.
    """
    day = _REAL_DATE.fromisoformat(iso)

    class _Pretend(_REAL_DATE):
        @classmethod
        def today(cls):
            return day

    def _targets():
        seen = set()
        for mod in list(sys.modules.values()):
            if mod is None:
                continue
            cls = getattr(mod, "date", None)
            if isinstance(cls, type) and issubclass(cls, _REAL_DATE) and id(mod) not in seen:
                seen.add(id(mod))
                yield mod
        dt = sys.modules.get("datetime")
        if dt is not None and id(dt) not in seen:
            yield dt

    saved = [(mod, mod.date) for mod in _targets()]
    try:
        for mod, _ in saved:
            mod.date = _Pretend
        yield day
    finally:
        for mod, old in saved:
            mod.date = old


@pytest.fixture
def pretend_today():
    """`with pretend_today("2026-01-10"):` pretends the wall clock reads that day."""
    return pretend_real_today

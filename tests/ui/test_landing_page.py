"""Library mode's landing page, the baseline pin and the reminder (ergonomics review S-1).

In library mode the Run Library comes first and the app opens on the Run page, on the pinned
baseline; the reminder dialog is shown once per library (its OK is stamped in `library.json`).
Outside library mode nothing changes: Welcome is the default page and draws the reminder.
"""

from pathlib import Path

import pytest

from owlplanner.library import Library, import_case

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
BILL = "examples/Case_bill.toml"


# -- the pin API -----------------------------------------------------------


def _two_runs(root):
    lib = Library.open(root)
    a = lib.save_run(name="a", scenario=import_case(BILL)).run
    b = lib.save_run(name="b", scenario=dict(import_case(BILL), events=[
        {"id": "w", "kind": "work", "person": "Bill", "start": 2026, "end": 2026, "wages": 1000}])).run
    return lib, a, b


def test_pin_unpin_and_baseline(tmp_path):
    lib, a, b = _two_runs(tmp_path / "lib")
    assert lib.baseline() is None and lib.pins() == []
    lib.pin(a)
    assert lib.baseline().id == a.id
    lib.pin(b.id)  # the latest pin is the baseline
    assert lib.pins() == [b.id, a.id] and lib.baseline().id == b.id
    lib.pin(b)  # idempotent
    assert lib.pins() == [b.id, a.id]
    lib.unpin(b)
    assert lib.baseline().id == a.id
    lib.delete_run(a)  # a deleted run leaves the pins
    assert lib.pins() == [] and lib.baseline() is None


def test_the_disclaimer_stamp(tmp_path):
    lib, _a, _b = _two_runs(tmp_path / "lib")
    assert lib.disclaimer_accepted() is None
    stamp = lib.accept_disclaimer()
    assert Library.open(tmp_path / "lib").disclaimer_accepted() == stamp


# -- the app ---------------------------------------------------------------


@pytest.fixture
def library_app(tmp_path, monkeypatch):
    from streamlit import config

    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.delenv("OWL_SKIP_DISCLAIMER", raising=False)
    monkeypatch.syspath_prepend(str(UI_DIR))
    previous = config.get_option("server.address")
    config.set_option("server.address", "localhost")
    lib, a, b = _two_runs(root)
    yield lib, a, b
    config.set_option("server.address", previous)


def _app():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(UI_DIR / "main.py"), default_timeout=90)


def _ok(at):
    return [b for b in at.button if b.label == "OK"]


def test_library_mode_opens_on_the_pinned_baseline(library_app):
    lib, a, _b = library_app
    lib.pin(a)
    lib.accept_disclaimer()
    at = _app().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any(m.value.startswith("# :material/monitoring: Run") for m in at.markdown)  # the Run page
    assert at.selectbox(key="run_page_run").value.startswith("a  (")  # not the newest, b
    assert any("The baseline" in c.value for c in at.caption)


def test_without_a_pin_the_newest_run_and_a_hint(library_app):
    lib, _a, _b = library_app
    lib.accept_disclaimer()
    at = _app().run()
    assert at.selectbox(key="run_page_run").value.startswith("b  (")
    assert any("Pin a run on the Library page" in c.value for c in at.caption)


def test_the_reminder_is_shown_once_per_library(library_app):
    lib, _a, _b = library_app
    at = _app().run()
    assert _ok(at), "the reminder was not drawn on the landing page"
    _ok(at)[0].click().run()
    assert lib.disclaimer_accepted() is not None
    at2 = _app().run()  # a new session on the same library
    assert not _ok(at2)


def test_outside_library_mode_welcome_is_still_the_default(monkeypatch):
    monkeypatch.delenv("OWL_LIBRARY_DIR", raising=False)
    monkeypatch.delenv("OWL_SKIP_DISCLAIMER", raising=False)
    monkeypatch.syspath_prepend(str(UI_DIR))
    at = _app().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Plan your retirement with confidence" in m.value for m in at.markdown)
    assert _ok(at)  # upstream's once-per-session reminder


def test_the_library_page_pins(library_app):
    lib, a, _b = library_app
    lib.accept_disclaimer()
    at = _app().run()
    at.switch_page("Library.py").run()
    assert not at.exception, [e.value for e in at.exception]
    at.button(key=f"pin_{a.id}").click().run()
    assert lib.baseline().id == a.id
    assert at.button(key=f"unpin_{a.id}").label == "Baseline ✓"
    at.button(key=f"unpin_{a.id}").click().run()
    assert lib.baseline() is None

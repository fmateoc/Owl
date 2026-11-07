"""The Library page's import form (UX review Q10, 2026-11-07), through `ui/library_import.py`.

AppTest cannot upload a file, so the form's logic is tested here with stand-in uploads, and
the page itself only for the expander that stays open after a failed import.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from pathlib import Path

import pytest

from owlplanner.config import load_toml
from owlplanner.library import Library, case_references

ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "ui"
JACK_JILL = ROOT / "examples" / "Case_jack+jill.toml"
WORKBOOK = ROOT / "examples" / "HFP_jack+jill.xlsx"
BILL = ROOT / "examples" / "Case_bill.toml"


class Upload:
    """What st.file_uploader returns, as far as the form reads it."""

    def __init__(self, path, name=None, data=None):
        self.name = name or Path(path).name
        self._data = Path(path).read_bytes() if data is None else data

    def getvalue(self):
        return self._data


@pytest.fixture
def library_import(monkeypatch):
    monkeypatch.syspath_prepend(str(UI_DIR))
    import library_import

    return library_import


def test_case_references_name_the_companion_files():
    assert case_references(load_toml(str(JACK_JILL))[0]) == {"hfp": "HFP_jack+jill.xlsx",
                                                             "budget": "", "rates": ""}
    assert case_references(load_toml(str(BILL))[0]) == {"hfp": "", "budget": "", "rates": ""}


def test_the_captions_say_what_the_chosen_case_needs(library_import):
    case = Upload(JACK_JILL)
    refs = library_import.case_refs(case)
    assert library_import.companion_caption("hfp", refs, case) == \
        "Required: this case names *HFP_jack+jill.xlsx*."
    assert library_import.companion_caption("budget", refs, case) == "Not needed: this case names none."
    assert library_import.companion_caption("hfp", {}, None) == "Needed only when the case names one."
    assert library_import.case_refs(Upload(JACK_JILL, data=b"not = [toml")) == {}


@pytest.mark.toml
def test_an_import_without_the_named_workbook_is_refused_by_name(library_import, tmp_path):
    lib = Library.open(tmp_path / "library")
    uploaded = {"case": Upload(JACK_JILL), "hfp": None, "budget": None, "rates": None}
    result, reason = library_import.import_uploaded(lib, name="", notes="", tags=[], uploaded=uploaded)
    assert result is None
    assert reason == ("Not imported: this case names *HFP_jack+jill.xlsx* (choose it under "
                      "*Household workbook*). Add it and import again.")
    assert lib.runs() == []


@pytest.mark.toml
def test_an_import_with_the_workbook_is_saved(library_import, tmp_path):
    lib = Library.open(tmp_path / "library")
    uploaded = {"case": Upload(JACK_JILL), "hfp": Upload(WORKBOOK), "budget": None, "rates": None}
    result, reason = library_import.import_uploaded(lib, name="", notes="", tags=[], uploaded=uploaded)
    assert reason is None and result.created
    assert [r.name for r in lib.runs()] == ["Case_jack+jill"]


@pytest.mark.toml
def test_an_import_error_does_not_show_the_temporary_folder(library_import, tmp_path):
    """Q10: the error named /tmp/tmp.../Case_ari+noa_condo.toml."""
    lib = Library.open(tmp_path / "library")
    broken = Upload(WORKBOOK, data=b"not a workbook")
    uploaded = {"case": Upload(JACK_JILL), "hfp": broken, "budget": None, "rates": None}
    result, reason = library_import.import_uploaded(lib, name="", notes="", tags=[], uploaded=uploaded)
    import tempfile

    assert result is None
    assert reason.startswith("Cannot import this case: Could not read file HFP_jack+jill.xlsx:"), reason
    assert tempfile.gettempdir() not in reason


def test_without_folder_strips_the_folder(library_import, tmp_path):
    folder = tmp_path / "tmpabc"
    message = f"HFP workbook 'HFP_x.xlsx' not found for {folder}/Case_x.toml"
    assert library_import.without_folder(message, folder) == \
        "HFP workbook 'HFP_x.xlsx' not found for Case_x.toml"


def test_the_form_stays_open_after_a_failed_import(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    from owlplanner.library import import_case

    root = tmp_path / "library"
    monkeypatch.setenv("OWL_LIBRARY_DIR", str(root))
    monkeypatch.syspath_prepend(str(UI_DIR))
    Library.open(root).save_run(name="bill", scenario=import_case(str(BILL)))  # not empty: closed

    def page(failed):
        at = AppTest.from_file(str(UI_DIR / "Library.py"), default_timeout=90)
        at.session_state["cases"] = {}
        at.session_state["currentCase"] = None
        if failed:
            at.session_state["lib_import_failed"] = True
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        return next(e for e in at.expander if e.label == "Add a run to the library")

    assert page(failed=False).proto.expanded is False
    assert page(failed=True).proto.expanded is True

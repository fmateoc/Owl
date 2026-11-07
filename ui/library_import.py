"""
The Library page's "Import a case" form, without Streamlit (UX review Q10, 2026-11-07).

The form takes a case file and the files it names (its workbook, budget file and rates
table). It now says which of those the chosen case needs, refuses an import that lacks one
before reading anything (the case's own references would otherwise be sought in the server's
working directory), and keeps the temporary folder the uploads are written to out of its
errors (one read "HFP workbook 'HFP_ari+noa.xlsx' not found for /tmp/tmpp242byv5/...").

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
import tempfile
from io import BytesIO
from pathlib import Path

from owlplanner.library import case_references, import_case

# The companion files: their key in `case_references`, and the uploader's label.
COMPANIONS = {"hfp": "Household workbook", "budget": "Budget file", "rates": "Rates table"}


def case_refs(case_up) -> dict:
    """The files the chosen case file names ({} before one is chosen, or when it cannot be
    read: the import then says why). *case_up* is an uploaded file (`name`, `getvalue()`)."""
    if case_up is None:
        return {}
    try:
        from owlplanner.config import load_toml

        case, _, _ = load_toml(BytesIO(case_up.getvalue()))
        return case_references(case)
    except Exception:  # noqa: BLE001 - the import reports a broken case file itself
        return {}


def companion_caption(key: str, refs: dict, case_up) -> str:
    """The line under a companion's uploader."""
    if refs.get(key):
        return f"Required: this case names *{refs[key]}*."
    if case_up is not None:
        return "Not needed: this case names none."
    return "Needed only when the case names one."


def missing_companions(refs: dict, uploaded: dict) -> str | None:
    """Why the import cannot start (a named file not chosen), or None."""
    missing = [f"*{refs[key]}* (choose it under *{label}*)" for key, label in COMPANIONS.items()
               if refs.get(key) and uploaded.get(key) is None]
    if not missing:
        return None
    return "Not imported: this case names " + " and ".join(missing) + ". Add it and import again."


def without_folder(message: str, folder) -> str:
    """*message* without the temporary folder the uploads were written to (either separator:
    a message may name the folder with "/" on Windows too)."""
    for form in {str(folder), str(Path(folder).resolve())}:
        for sep in {os.sep, "/"}:
            message = message.replace(form + sep, "")
        message = message.replace(form, "the uploaded files")
    return message


def import_uploaded(lib, *, name, notes, tags, uploaded):
    """Import the uploaded case as a new run: (save_run's result, None) or (None, the reason).

    *uploaded* maps "case", "hfp", "budget" and "rates" to uploaded files or None.
    """
    reason = missing_companions(case_refs(uploaded["case"]), uploaded)
    if reason:
        return None, reason
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        paths = {}
        for key, up in uploaded.items():
            if up is None:
                continue
            path = tmp / up.name
            path.write_bytes(up.getvalue())
            paths[key] = path
        try:
            scenario = import_case(paths["case"], hfp_path=paths.get("hfp"),
                                   budget_path=paths.get("budget"), rates_path=paths.get("rates"))
            result = lib.save_run(name=name or Path(paths["case"]).stem, scenario=scenario,
                                  notes=notes, tags=tuple(t for t in tags if t.strip()))
        except Exception as exc:  # noqa: BLE001 - shown to the user, not raised
            return None, f"Cannot import this case: {without_folder(str(exc), tmp)}"
    return result, None

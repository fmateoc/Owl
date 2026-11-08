"""
The reminder dialog's text, shared by the Welcome page and the run library's landing page.

Fork (ergonomics review S-1, decision 2): in library mode the landing page is the Run page, and
the reminder is shown once per library (`Library.accept_disclaimer` writes the stamp in
`library.json`). The text is upstream's, moved here unchanged so both pages draw the same words.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os

GPLV3_URL = "https://www.gnu.org/licenses/gpl-3.0.html#license-text"
DISMISSED_KEY = "welcome_disclaimer_dismissed"
TITLE = ":material/policy: :orange[Reminder]"


def show_disclaimer() -> bool:
    """False when OWL_SKIP_DISCLAIMER says not to show it."""
    return os.environ.get("OWL_SKIP_DISCLAIMER", "0") not in ("1", "true", "True", "yes")


def reminder_markdown() -> str:
    return f"""
**Owl** – *Optimal wealth lab* is for **educational and research purposes** only. Nothing in this session constitutes
**financial, tax, or investment advice**—consult a qualified professional for decisions specific to your situation.

This software is released under the [GNU General Public License v3]({GPLV3_URL}).
"""

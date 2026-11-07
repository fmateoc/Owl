"""
Preset names for people, and the preset picker the run library's pages share (UX review Q2).

The stored ids (`owlplanner.library.PRESETS`, `record.json`, the queue) do not change: the
pages show these names through `format_func`. The times are the ones measured on the
synthetic household in this project's container (`fork-notes/ux-fixes-handoff.md`): quick
0.8 s, decision 304-323 s plus 9 s for its exact companion. The Ages preset was not timed;
"Ages, thorough" took 29-51 minutes per variant on a stand-in couple (presets.py).

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import streamlit as st

from owlplanner.library import PRESETS
from owlplanner.library.presets import PRESET_NAMES

# The picker's time hints on top of the one list of names (QW-6, review AN8: two lists used
# to be kept in step by hand). Solves a choice queues, or a page's own button does, have none.
TIME_HINTS = {
    "quick": "about a second",
    "decision": "about 5 minutes",
    "ages": "slow",
    "ages_thorough": "very slow",
}
NAMES = {preset: f"{words} ({TIME_HINTS[preset]})" if preset in TIME_HINTS else words
         for preset, words in PRESET_NAMES.items()}

# Behind the "Expert" toggle: the slowest search and the case's own options.
EXPERT = ("ages_thorough", "custom")

HELP = (
    "**Quick look**: Owl's fast approximate method, with the claiming ages held at the "
    "scenario's values. Good for a first look; differences under about 1% between two quick "
    "looks can be noise.\n\n"
    "**Careful**: a slower, more exact search for the tax rules that make the plan jumpy "
    "(Medicare premiums, Social Security taxation, capital gains), ages held. It also solves "
    "a simpler exact model beside it, so a comparison can check that both put the variants "
    "in the same order. Use it before deciding between two runs.\n\n"
    "**Let Owl choose the claiming ages**: searches the claiming ages the scenario leaves "
    "open, then solves at the ages it picked.\n\n"
    "Expert: **Claiming ages, every pair tried** scores every whole-year pair of claiming "
    "ages exactly (29-51 minutes per variant on a test couple) and keeps the scores for the "
    "claiming-age map; **The case's own solver options** solves exactly as the case file says."
)


def name(preset) -> str:
    """A preset id as the pages show it (the id itself when it has no name)."""
    return NAMES.get(preset, str(preset))


def select(label, key, *, container=None, help=HELP) -> str:
    """The preset picker: the everyday presets, the expert ones behind a toggle."""
    box = container if container is not None else st
    expert = st.session_state.get(f"{key}_expert", False)
    options = [p for p in PRESETS if expert or p not in EXPERT]
    if st.session_state.get(key) not in options:
        st.session_state.pop(key, None)  # an expert preset with the toggle turned off
    choice = box.selectbox(label, options, key=key, format_func=name, help=help)
    box.toggle("Expert presets", key=f"{key}_expert",
               help="Also offer the exhaustive claiming-age sweep and the case's own options.")
    return choice

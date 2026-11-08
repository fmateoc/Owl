"""The Scenario page's structured year picker (ergonomics review S-2, decision 4).

`ui/year_ref_input.py` splits a year field's text form into a "When" choice and its parts and
joins them back. Every one of `builder.parse_year_ref`'s six forms must round-trip, so the
picker never changes what a stored anchor means.
"""

import sys
from pathlib import Path

import pytest

from owlplanner.library import builder

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
sys.path.insert(0, str(UI_DIR))

import year_ref_input as yr  # noqa: E402

IDS = ["work-ari-2026", "buy", "care"]

FORMS = [
    ("2031", "year"),
    ("age:Ari:86", "age"),
    ("age:Noa:62.5", "age"),
    ("work:Noa", "work"),
    ("after:Ari", "after"),
    ("purchase", "purchase"),
    ("event:care", "event"),
    ("event:buy+20", "event"),
    ("event:work-ari-2026-1", "event"),  # an id ending in -<digits>, with an offset (review X5)
]


@pytest.mark.parametrize("text,mode", FORMS)
def test_every_form_round_trips(text, mode):
    got_mode, parts = yr.split_ref(text, IDS)
    assert got_mode == mode
    joined = yr.join_ref(got_mode, parts)
    assert builder.parse_year_ref(joined, ids=IDS) == builder.parse_year_ref(text, ids=IDS)
    assert joined == builder.year_ref_text(builder.parse_year_ref(text, ids=IDS))


def test_the_modes_cover_the_grammar():
    assert set(yr.MODES) == {"year", "age", "work", "after", "purchase", "event", "text"}
    assert {m for _, m in FORMS} == set(yr.MODES) - {"text"}


def test_unparsable_text_stays_text_and_blank_is_blank():
    assert yr.split_ref("bogus", IDS) == ("text", {"text": "bogus"})
    assert yr.join_ref("text", {"text": "bogus"}) == "bogus"
    assert yr.split_ref("", IDS) == (yr.BLANK, {})
    assert yr.split_ref(None, IDS) == (yr.BLANK, {})
    assert yr.join_ref(yr.BLANK, {}) == ""

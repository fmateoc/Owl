"""No page names a number "score" (UX remediation QW-5, decision 3, ux-qw-handoff-2.md).

The score is the number a solve maximizes; the household reads it in its own words: the
first year's "discretionary spending" (with essential budget lines), "spending", or the
"final bequest" (`view.score_name`). A source check over every string a page renders, as
`test_ui_dollar_math.py` does; the claiming-age map's *scores file* (`scores.json`, which
`work_sweep` writes) keeps its word, as do "scored" and "scores", and so does upstream's
*Retirement Efficiency Score*, a proper name on its Spending Optimization page.
"""

import ast
import re

from test_ui_dollar_math import KEYWORDS, RENDERED, UI_DIR, _text

SCORE = re.compile(r"\bscore\b", re.IGNORECASE)
PROPER_NAMES = re.compile(r"Efficiency Score")


def _offenders():
    found = []
    for path in sorted(UI_DIR.glob("*.py")):
        if path.name == "Documentation.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            args = list(node.args) if name in RENDERED else []
            args += [k.value for k in node.keywords if k.arg in KEYWORDS + ("question", "rule")]
            for arg in args:
                text = _text(arg)
                if text is not None and SCORE.search(PROPER_NAMES.sub("", text)):
                    found.append(f"{path.name}:{arg.lineno}: {text[:90]!r}")
    return found


def test_no_page_names_a_number_score():
    assert _offenders() == []

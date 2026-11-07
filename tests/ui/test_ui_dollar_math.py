"""No interface label renders as math by accident (UX review B4).

Streamlit reads a `$...$` pair in a label, caption or message as LaTeX: the Scenario page
showed "Property tax (/yr, today's )" with a math fragment. Upstream escapes every dollar in
UI strings (`\\$`, 2026-10-11). This is a source check, chosen over rendering each label: it
covers every page without building the state each needs, and does not break when a label's
wording changes. It flags a string constant passed to a Streamlit element or a widget's
`help=` (and `label=`, `placeholder=`, and `st.metric`'s `value=`, `delta=` and
`delta_description=`, which Streamlit 1.66 also reads as Markdown: review AN1, the headline's
split drawn as math and cut) that holds two unescaped dollar signs, unless the pair wraps a
short math token (`$N$`, used on purpose). `Documentation.py` is all math on purpose and is
left out.
"""

import ast
import re
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
DOLLAR = re.compile(r"(?<!\\)\$")
MATH = re.compile(r"(?<!\\)\$[A-Za-z\\][^$\s]{0,20}(?<!\\)\$")  # $N$, $\bar{x}$, $g_s$
RENDERED = {
    "markdown", "caption", "info", "warning", "error", "success", "write", "toast", "title",
    "header", "subheader", "button", "download_button", "checkbox", "toggle", "radio",
    "selectbox", "multiselect", "number_input", "text_input", "text_area", "slider",
    "select_slider", "date_input", "file_uploader", "metric", "expander", "popover", "tabs",
    "page_link", "link_button", "flash",
}


# Keyword arguments Streamlit renders as Markdown (review AN1 added the metric's three).
KEYWORDS = ("help", "label", "placeholder", "value", "delta", "delta_description")


def _text(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in node.values)
    if isinstance(node, ast.BinOp):  # "a" "b" is one constant; "a" + "b" is not
        left, right = _text(node.left), _text(node.right)
        return None if left is None or right is None else left + right
    return None


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
            args += [k.value for k in node.keywords if k.arg in KEYWORDS]
            for arg in args:
                text = _text(arg)
                if text is not None and len(DOLLAR.findall(MATH.sub("", text))) >= 2:
                    found.append(f"{path.name}:{arg.lineno}: {text[:80]!r}")
    return found


def test_no_label_has_two_unescaped_dollars():
    assert _offenders() == []

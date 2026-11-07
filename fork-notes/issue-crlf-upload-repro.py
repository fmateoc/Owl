"""CRLF case file through load_toml and Create Case's upload path (stock dev)."""
import io
import sys
from pathlib import Path

import owlplanner
from owlplanner.config import load_toml

case = Path(sys.argv[1])
text = case.read_text(encoding="utf-8")
crlf = text.replace("\n", "\r\n")
print("owlplanner from:", Path(owlplanner.__file__).parent)
print("from a path (LF file):    ", sorted(load_toml(str(case))[0]))
print("from StringIO, LF text:   ", sorted(load_toml(io.StringIO(text))[0]))
print("from StringIO, CRLF text: ", sorted(load_toml(io.StringIO(crlf))[0]))
print("from BytesIO, CRLF bytes: ", sorted(load_toml(io.BytesIO(crlf.encode()))[0]))

# Create Case's upload: ui/Create_Case.py builds StringIO(file.read().decode("utf-8")) and
# calls sskeys.createCaseFromFile -> owlbridge.createCaseFromFile, which shows st.error.
sys.path.insert(0, "ui")
import streamlit as st  # noqa: E402

shown = []
st.error = lambda msg, **kw: shown.append(msg)
import owlbridge  # noqa: E402

name, dic = owlbridge.createCaseFromFile(io.StringIO(crlf.encode("utf-8").decode("utf-8")))
print("Create Case, CRLF upload: name =", repr(name), "| st.error:", shown)

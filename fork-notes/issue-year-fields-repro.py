"""Run Options' year fields on stock dev: their bounds, and what a typo does to the plan."""
import io
import sys
from pathlib import Path

import numpy as np

import owlplanner
from owlplanner.config import config_to_plan, config_to_ui, load_toml

case = sys.argv[1]
print("owlplanner from:", Path(owlplanner.__file__).parents[2].name)

# 1. The fields as the page draws them (AppTest), and a five-digit year typed in.
sys.path.insert(0, str(Path.cwd() / "ui"))
import streamlit as st  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

st.page_link = lambda *a, **k: None  # AppTest has no multipage context
diconf, dirname, _ = load_toml(case)
plan = config_to_plan(diconf, dirname, verbose=False, logstreams=[io.StringIO()])
dic = config_to_ui(diconf)
dic.update({"plan": plan, "id": "t1", "name": "c", "caseStatus": "new", "summaryDf": None})
at = AppTest.from_file(str(Path.cwd() / "ui" / "Run_Options.py"), default_timeout=60)
at.session_state["cases"] = {"c": dic}
at.session_state["currentCase"] = "c"
at.run()
for w in at.number_input:
    if "Year" in w.label or "ACA" in w.label:
        print(f"field {w.label!r}: min {w.min}, max {w.max}")
start = next(w for w in at.number_input if w.label.startswith("Year to start"))
start.set_value(20300)
for box in at.selectbox:  # keep the decorated case option across the rerun (AppTest quirk)
    if box.label == "Case selector":
        box.set_value(box.options[0])
at.run()
print("after typing 20300 in 'Year to start ...': the case holds", dic["startRothConversions"],
      "| exceptions:", [str(e.value)[:60] for e in at.exception])

# 2. The plan with that typo for 2030.
for year in (2030, 20300):
    diconf, dirname, _ = load_toml(case)
    opts = dict(diconf["solver_options"], startRothConversions=year)
    p = config_to_plan(diconf, dirname, verbose=False, logstreams=[io.StringIO()])
    p.solve(diconf["optimization_parameters"]["objective"], opts)
    print(f"startRothConversions = {year}: {p.caseStatus}, Roth conversions over the plan "
          f"${float(np.sum(p.x_in)):,.0f} (nominal)")

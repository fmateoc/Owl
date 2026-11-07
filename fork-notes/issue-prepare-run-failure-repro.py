"""Stock-dev repro: an ACA start year of 1999 on Reports (AppTest), and setACA's hint."""
import io
import sys
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

import owlplanner as owl
from owlplanner import readConfig
from owlplanner.config import config_to_ui, load_toml

root = Path(sys.argv[1])
try:
    owl.Plan(["Joe"], ["1961-01-15"], [80], "t", verbose=False).setACA(slcsp=10, start_year=1999)
except ValueError as e:
    print("setACA:", e)

st.page_link = lambda *a, **k: None
case_file = root / "examples" / "Case_jack+jill.toml"
plan = readConfig(str(case_file), verbose=False, logstreams=[io.StringIO()])
solves = []
_solve = owl.Plan.solve
owl.Plan.solve = lambda self, *a, **k: (solves.append(1), _solve(self, *a, **k))[1]
diconf, _, _ = load_toml(str(case_file))
case = config_to_ui(diconf)
case.update({"plan": plan, "id": "t1", "name": "t", "caseStatus": "modified", "summaryDf": None,
             "timeList0": plan.timeLists["Jack"], "timeList1": plan.timeLists["Jill"],
             "houseListDebts": plan.houseLists["Debts"], "houseListFixedAssets": plan.houseLists["Fixed Assets"],
             "hfpAbsentCols": dict(getattr(plan, "hfpAbsentCols", {})), "logs": io.StringIO(),
             "slcspAnnual": 20.0, "acaStartYear": 1999})
at = AppTest.from_file(str(root / "ui" / "Reports.py"), default_timeout=300)
at.session_state["cases"] = {"t": case}
at.session_state["currentCase"] = "t"
at.run()
print("solves:", len(solves))
print("caseStatus:", at.session_state["cases"]["t"]["caseStatus"])
for kind in ("error", "warning", "info"):
    for el in getattr(at, kind):
        print(f"{kind}: {el.value}")

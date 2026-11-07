"""Stock-dev repro: Reports solves a case whose move could not be applied (AppTest).

Case_dana (CA). On Create Case: *Move to another state during the plan* on, new state FL in
2031, then *State of residence* FL as well (the page warns "The new state is the starting
state."). Then $50,000 of wages added on Financial Profile for the first plan
year. Open Reports.

Run from anywhere: python issue-prepare-run-failure-repro.py <repo root>
"""
import io
import sys
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

import owlplanner as owl
from owlplanner import readConfig
from owlplanner.config import config_to_ui, load_toml

root = Path(sys.argv[1])
st.page_link = lambda *a, **k: None
case_file = root / "examples" / "Case_dana.toml"
plan = readConfig(str(case_file), verbose=False, logstreams=[io.StringIO()])
name = plan.inames[0]
solves = []
_solve = owl.Plan.solve
owl.Plan.solve = lambda self, *a, **k: (solves.append(1), _solve(self, *a, **k))[1]
diconf, _, _ = load_toml(str(case_file))
case = config_to_ui(diconf)
wages = plan.timeLists[name].copy()
year = int(plan.year_n[0])
row = wages.index[wages["year"] == year][0]
wages.loc[row, "anticipated wages"] += 50_000  # the Financial Profile edit, first plan year
case.update({"plan": plan, "id": "t1", "name": "t", "caseStatus": "modified", "summaryDf": None,
             "timeList0": wages, "houseListDebts": plan.houseLists["Debts"],
             "houseListFixedAssets": plan.houseLists["Fixed Assets"],
             "hfpAbsentCols": dict(getattr(plan, "hfpAbsentCols", {})), "logs": io.StringIO(),
             "state": "FL", "stateMoveEnabled": True, "stateMoveYear": 2031, "stateMoveState": "FL"})
at = AppTest.from_file(str(root / "ui" / "Reports.py"), default_timeout=300)
at.session_state["cases"] = {"t": case}
at.session_state["currentCase"] = "t"
at.run()
print("solves:", len(solves))
print("caseStatus:", at.session_state["cases"]["t"]["caseStatus"])
summary = at.session_state["cases"]["t"]["summaryDf"]  # the solve's results, as Reports shows them
print("case: state FL; plan: state", repr(plan.state), "moves", plan.state_moves)
if summary is not None:
    tax = summary["Total state income tax paid (today's $)"].iloc[0]
    paid = summary["»  Wages (today's $)"].iloc[0]
    print(f"results shown: total state income tax {tax}, total wages {paid}")
print(f"{year} wages: case {wages.loc[row, 'anticipated wages']:,.0f}, "
      f"plan's table after the page {plan.timeLists[name].loc[row, 'anticipated wages']:,.0f}")
for kind in ("error", "warning", "info"):
    for el in getattr(at, kind):
        print(f"{kind}: {el.value}")

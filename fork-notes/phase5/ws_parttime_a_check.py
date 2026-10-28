"""Stage (a) of work_sweep on chris+pat pat-part-time-2029-30, plus exact-LP scores at two fixed ages."""
import json
import sys
H = sys.argv[1]
sys.path.insert(0, f"{H}/fork-notes/phase5")
import work_sweep as ws
import owlplanner as owl
spec = json.load(open(f"{H}/fork-notes/phase5/work_sweep_chris+pat.json"))
by = {v[0]: v for v in ws.build_variants(f"{H}/examples/Case_chris+pat.toml", spec, sys.argv[2])}
_, diconf, dirname, _ = by["pat-part-time-2029-30"]
print(owl.__file__, owl.__version__)
a = ws.age_search(diconf, dirname, "exact")
print("(a)", "/".join(ws.ym(x) for x in a["ages"]), f"{a['value']:,.2f}", f"{a['seconds']:.0f}s")
for ages in ([68.25, 64 + 7 / 12], [68.25, 65.0], [68 + 5 / 12, 65.0]):
    p, _ = ws.make_plan(diconf, dirname, ages)
    p.solve(p.objective, ws.base_options(p, withSSAges="fixed", **dict(ws.EXACT, withACA="optimize")))
    print("exact LP at", "/".join(ws.ym(x) for x in ages), f"{p._objectiveValue(p.objective):,.2f}", p.caseStatus)

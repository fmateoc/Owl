"""Re-solve one HiGHS call dumped by `solve_probe.py` (OWL_DUMP), with HiGHS options laid over Owl's own.

    .venv/bin/python fork-notes/performance/mip_probe.py <mip_NNN.pkl> '{"mip_heuristic_effort": 0.0}'

`_verbose` (HiGHS log) and `_nowarm` (no starting plan) are this script's own keys.
"""
import sys, pickle, time, json
import numpy as np, highspy
from owlplanner.plan import _MoneyScaling
d = pickle.load(open(sys.argv[1], "rb"))
extra = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
verbose = extra.pop("_verbose", False)
nowarm = extra.pop("_nowarm", False)
o = d["options"]
h = highspy.Highs()
h.setOptionValue("output_flag", bool(verbose))
h.setOptionValue("mip_rel_gap", float(o.get("gap")))
h.setOptionValue("time_limit", float(o.get("maxTime")))
h.setOptionValue("mip_max_nodes", int(o.get("mipMaxNodes")))
h.setOptionValue("presolve", "on")
for k, v in extra.items():
    h.setOptionValue(k, v)
sc = _MoneyScaling.for_mip(d["integrality"], d["a_start"], d["a_index"], o)
c = sc.objective(np.arange(len(d["c"])), d["c"])
Lb, Ub = sc.col_values(d["Lb"]), sc.col_values(d["Ub"])
lb, ub = sc.row_values(d["lbvec"]), sc.row_values(d["ubvec"])
av = sc.coefficients(d["a_index"], d["a_value"])
inf = highspy.kHighsInf
f = lambda a: np.where(np.isneginf(a), -inf, np.where(np.isposinf(a), inf, a)).astype(np.float64)
h.passModel(len(c), len(lb), len(av), int(highspy.MatrixFormat.kRowwise), int(highspy.ObjSense.kMinimize), 0.0,
            c.astype(np.float64), f(Lb), f(Ub), f(lb), f(ub), d["a_start"].astype(np.int32), d["a_index"].astype(np.int32),
            av.astype(np.float64), d["integrality"].astype(np.int32))
if d["warm_x"] is not None and not nowarm:
    h.setSolution(len(c), np.arange(len(c), dtype=np.int32), sc.col_values(d["warm_x"]).astype(np.float64))
t = time.time(); cpu = time.process_time()
h.run()
print(json.dumps({"file": sys.argv[1].split("/")[-1], "extra": extra, "wall": round(time.time() - t, 2), "cpu": round(time.process_time() - cpu, 2),
      "status": h.modelStatusToString(h.getModelStatus()), "obj": sc.objective_value(float(h.getObjectiveValue())),
      "nodes": h.getInfoValue("mip_node_count")[1], "gap": h.getInfoValue("mip_gap")[1],
      "bound": h.getInfoValue("mip_dual_bound")[1],
      "nfree_int": int(((d["integrality"] > 0) & (d["Ub"] > d["Lb"])).sum()), "ncols": len(c), "nrows": len(lb)}))

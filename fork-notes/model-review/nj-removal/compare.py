"""compare.py BEFORE AFTER: per case, the change in objective, federal tax, state tax and residual."""
import json, sys
b = {d["case"]: d for d in map(json.loads, open(sys.argv[1]))}
a = {d["case"]: d for d in map(json.loads, open(sys.argv[2]))}
worst = {}
for case in sorted(b, key=lambda c: (c.split(":")[0] == "nj", c)):
    if case not in a:
        print(f"{case:34s} MISSING after"); continue
    x, y = b[case], a[case]
    if x["status"] != "solved" or y["status"] != "solved":
        print(f"{case:34s} status {x['status']} -> {y['status']}"); continue
    d = {k: y[k] - x[k] for k in ("obj", "fed", "state", "resid")}
    same = all(abs(v) < 0.005 for v in d.values()) and x["method"] == y["method"]
    if not case.startswith("nj"):
        for k, v in d.items():
            worst[k] = max(worst.get(k, 0.0), abs(v))
    tag = "identical" if same else "CHANGED"
    print(f"{case:34s} {tag:9s} obj {x['obj']:>14,.2f} -> {y['obj']:>14,.2f} ({d['obj']:+,.2f})  state {d['state']:+,.2f}  "
          f"fed {d['fed']:+,.2f}  resid {d['resid']:+,.2f}  t {x['time']:.0f}->{y['time']:.0f}s"
          + ("" if x["method"] == y["method"] else f"  method {x['method']} -> {y['method']}"))
print("max |change| over non-NJ cases:", {k: round(v, 2) for k, v in worst.items()})

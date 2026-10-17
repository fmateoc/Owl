"""Per-probe times of the "convex" SS cap probe on the fork's NJ probe couple (2099, no mortgage). 2026-10-17."""
import io, sys, time, re
sys.argv = ["x", "/dev/null"]
sys.path.insert(0, "fork-notes/model-review/phase3-review")
import itemized_convergence as ic
import numpy as np
log = io.StringIO()
p = ic.couple("NJ", "", None, 2099, log)
t = time.time()
p.solve("maxBequest", options={"noRothConversions": "None", "withSSTaxability": "convex"})
dt = time.time() - t
tr = getattr(p, "_ssProbeTrace", [])
print(f"total {dt:.1f} s; probes {len(tr)}; probe time {sum(x[4] for x in tr):.1f} s; first solve ~{dt - sum(x[4] for x in tr):.1f} s")
for passno in sorted({x[5] for x in tr}):
    xs = [x for x in tr if x[5] == passno]
    print(f" pass {passno}: {len(xs)} probes, {sum(x[4] for x in xs):.1f} s, kept {sum(1 for x in xs if x[3] > 1)}; times {[round(x[4],1) for x in xs]}")
caps = len(re.findall(r"Solution limit reached|node limit", log.getvalue()))
print("node-limit mentions in log:", caps)

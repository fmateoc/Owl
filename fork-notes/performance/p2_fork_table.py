"""Table of `p2_fork_run.sh`'s output: each checkout against `base`, per synthetic variant.

    .venv/bin/python fork-notes/performance/p2_fork_table.py <out dir> base settled confirm

The value is the first year's discretionary spending (`plan_metrics`, the library's score);
"skipped" counts the searches that skipped their capped steps, "confirm" the confirming search.
"""
import glob
import json
import os
import sys

out, tags = sys.argv[1], sys.argv[2:]
ref = tags[0]
total = {t: 0.0 for t in tags}
for f in sorted(glob.glob(f"{out}/{ref}/*.json")):
    name = os.path.basename(f)[:-5]
    runs = {t: json.load(open(f"{out}/{t}/{name}.json")) for t in tags if os.path.exists(f"{out}/{t}/{name}.json")}
    if len(runs) < len(tags):
        print(f"{name:<26s} (a run is missing)")
        continue
    b = runs[ref]
    line = f"{name:<26s} {b['disc']:>12,.2f} searches {len(b['ls'])} CPU {b['cpu']:>6.1f}"
    for t in tags:
        total[t] += runs[t]["cpu"]
    for t in tags[1:]:
        r = runs[t]
        same = "same" if abs(r["disc"] - b["disc"]) < 0.005 else f"{r['disc'] - b['disc']:+.2f}"
        log = r["log"]
        conf = ""
        if "confirming search on the last problem" in log:
            moved = "a better plan." in log.split("confirming search")[-1][:80]
            conf = " confirm: MOVED" if moved else " confirm: no move"
        line += (f" | {t}: {same} skipped {log.count('capped steps skipped')}{conf} CPU {r['cpu']:>6.1f}"
                 f" ({(r['cpu'] - b['cpu']) / b['cpu'] * 100:+.0f}%)")
    print(line)
parts = []
for t, v in total.items():
    parts.append(f"{t} {v:.1f}" + ("" if t == ref else f" ({(v - total[ref]) / total[ref] * 100:+.1f}%)"))
print("total CPU " + ", ".join(parts))

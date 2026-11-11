"""Table of `p2_stock_run.sh`'s output: each checkout against `base`, per example.

    .venv/bin/python fork-notes/performance/p2_stock_table.py <out dir> [tag ...]

Tags default to `settled`. A confirming search (`confirm` checkout) shows in the search log as an
entry without a start step; "confirm" says whether one ran and whether the loop went on after it
(a search after it: it found a better plan).
"""
import glob
import json
import os
import sys

out = sys.argv[1]
tags = sys.argv[2:] or ["settled"]
total = {t: 0.0 for t in ["base", *tags]}
for f in sorted(glob.glob(f"{out}/base/*.json")):
    name = os.path.basename(f)[:-5]
    runs = {"base": json.load(open(f))}
    for t in tags:
        p = f"{out}/{t}/{name}.json"
        if os.path.exists(p):
            runs[t] = json.load(open(p))
    if len(runs) < len(tags) + 1:
        print(f"{name:<24s} (a run is missing)")
        continue
    b = runs["base"]
    line = (f"{name:<24s} {b['objective']:<11s} {b['value']:>14,.2f} searches {len(b['iterations'])}"
            f" CPU {b['cpu']:>6.1f}")
    total["base"] += b["cpu"]
    for t in tags:
        r = runs[t]
        total[t] += r["cpu"]
        same = "same" if abs(r["value"] - b["value"]) < 0.005 else f"{r['value'] - b['value']:+.2f}"
        its = r["iterations"]
        confirms = [k for k, it in enumerate(its) if it["labels"] and not it["labels"][0].startswith("start:")]
        conf = "" if not confirms else (" confirm: no move" if confirms[-1] == len(its) - 1 else " confirm: MOVED")
        line += (f" | {t}: {same} skipped {r['skipped_iterations']}{conf} CPU {r['cpu']:>6.1f}"
                 f" ({(r['cpu'] - b['cpu']) / b['cpu'] * 100:+.0f}%)")
    print(line)
parts = []
for t, v in total.items():
    parts.append(f"{t} {v:.1f}" + ("" if t == "base" else f" ({(v - total['base']) / total['base'] * 100:+.1f}%)"))
print("total CPU " + ", ".join(parts))

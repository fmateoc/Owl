"""Table of `p2_stock_run.sh`'s output: base against the patched checkout, per example.

    .venv/bin/python fork-notes/performance/p2_stock_table.py <out dir>
"""
import glob
import json
import os
import sys

out = sys.argv[1]
tot_b = tot_s = 0.0
for f in sorted(glob.glob(f"{out}/base/*.json")):
    name = os.path.basename(f)[:-5]
    b = json.load(open(f))
    sf = f"{out}/settled/{name}.json"
    if not os.path.exists(sf):
        print(f"{name:<24s} base {b['value']:>14,.2f} cpu {b['cpu']:>6.1f}  (patched run missing)")
        continue
    s = json.load(open(sf))
    tot_b += b["cpu"]
    tot_s += s["cpu"]
    same = "same" if abs(s["value"] - b["value"]) < 0.005 else f"{s['value'] - b['value']:+.2f}"
    print(f"{name:<24s} {b['objective']:<11s} {b['value']:>14,.2f} {same:>6s}  searches {len(b['iterations'])}"
          f"  skipped {s['skipped_iterations']}  CPU {b['cpu']:>6.1f} -> {s['cpu']:>6.1f}"
          f" ({(s['cpu'] - b['cpu']) / b['cpu'] * 100:+.0f}%)  budget cuts {b['budget_spent']}/{s['budget_spent']}")
print(f"total CPU {tot_b:.1f} -> {tot_s:.1f} ({(tot_s - tot_b) / tot_b * 100:+.1f}%)")

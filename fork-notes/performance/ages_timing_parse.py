"""Split an `ages_timing.py` solve log by plan built (performance review P4a, section 6b).

Each plan's build logs "Preparing scenario"; each solve ends with upstream's "CPU time used:
..., Wall time: ..." lines, whose largest value in the block is that solve's own wall time.
The pool's candidates log in their own processes, so their stamps are when they ran.

    .venv/bin/python fork-notes/performance/ages_timing_parse.py OUT_DIR
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

d = Path(sys.argv[1])
stamp = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \|")
wall = re.compile(r"Wall time: (?:(\d+)m)?([\d.]+)s")
blocks = []  # [start stamp, end stamp, longest "Wall time" in the block]
for line in (d / "solve.log").read_text(encoding="utf-8").splitlines():
    m = stamp.match(line)
    t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S") if m else None
    if "Preparing scenario" in line:
        blocks.append([t, None, 0.0])
    w = wall.search(line)
    if w and blocks:
        blocks[-1][1] = t
        blocks[-1][2] = max(blocks[-1][2], 60 * int(w.group(1) or 0) + float(w.group(2)))
rec = json.loads((d / "record.json").read_text())
n = len(rec["age_search"]["candidates"])
print(d.name, "| record wall_time_seconds", round(rec["wall_time_seconds"]), "| plans built", len(blocks),
      "| candidates", n, "| stage_2_plan", rec["age_search"].get("stage_2_plan"))
names = ["stage 1"] + [f"candidate {i}" for i in range(1, n + 1)] + ["final solve"] * (len(blocks) - n - 1)
for name, (s, e, w) in zip(names, blocks, strict=True):
    print(f"  {name:12s} {s:%H:%M:%S} - {e:%H:%M:%S}  solve wall {w:6.0f} s")
cands = blocks[1:1 + n]
print("  stage 2: from", f"{min(b[0] for b in cands):%H:%M:%S}", "to", f"{max(b[1] for b in cands):%H:%M:%S}",
      "=", (max(b[1] for b in cands) - min(b[0] for b in cands)).total_seconds(), "s")
print("  ", [(a, round(v, 2)) for a, v in rec["age_search"]["candidates"]], "chosen", rec["age_search"]["chosen"])

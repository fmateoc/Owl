#!/bin/bash
# The two variants whose search keeps moving, with local search's wall-clock caps lifted
# (localSearchTime 7200, localSearchStepTime 1800, as work_sweep.py): 3,000 nodes, 1,000 nodes, and
# 1,000 nodes with the P2 prototype. All six at once: with the caps lifted the results are node-capped
# and do not depend on the load. Run from the repository root; results in $1 (a folder).
# Performance review, 2026-11-11 (fork-notes/performance-review.md, "P3, measured on 2026-11-11").
out=${1:?output folder}
mkdir -p "$out"
P=fork-notes/performance/solve_probe.py
LIFT='"localSearchTime": 7200, "localSearchStepTime": 1800'
for v in whiteplains_2038_cash whiteplains_2029_mortgage; do
  H=HFP_ari+noa_condo_$v.xlsx
  .venv/bin/python $P decision "$H" "$out/${v}_3000.json" "{$LIFT}" > "$out/${v}_3000.out" 2>&1 &
  .venv/bin/python $P decision "$H" "$out/${v}_1000.json" "{$LIFT, \"localSearchStepNodes\": 1000}" > "$out/${v}_1000.out" 2>&1 &
  OWL_QUIET=1 .venv/bin/python $P decision "$H" "$out/${v}_1000q.json" "{$LIFT, \"localSearchStepNodes\": 1000}" > "$out/${v}_1000q.out" 2>&1 &
done
wait

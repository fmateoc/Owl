#!/usr/bin/env bash
# P2 on the synthetic household: the six condo variants of the performance review, Careful
# (`decision`, so the library's search effort: 1,000 nodes, both wall-clock caps lifted), claiming
# ages 70/70, from several fork checkouts (one per tag), interleaved, N at a time.
#
#   fork-notes/performance/p2_fork_run.sh <out dir> <jobs> tag=<checkout> [tag=<checkout> ...]
#
# Run fork-notes/synthetic/make_cases.py first. Output: <out dir>/<tag>/<variant>.json (solve_probe.py's).
set -u
export OUT=$1; JOBS=$2; shift 2
HERE=$(cd "$(dirname "$0")" && pwd)
export HERE PY=$(cd "$HERE/../.." && pwd)/.venv/bin/python
VARIANTS="yonkers_2027_mortgage queens_2031_cash yonkers_2034_cash queens_2027_arm5 whiteplains_2029_mortgage whiteplains_2038_cash"
for pair in "$@"; do mkdir -p "$OUT/${pair%%=*}"; done
for v in $VARIANTS; do
  for pair in "$@"; do echo "${pair%%=*} ${pair#*=} $v"; done
done | xargs -P "$JOBS" -L 1 bash -c '
  tag=$0; tree=$1; v=$2
  PYTHONPATH=$tree/src "$PY" "$HERE/solve_probe.py" decision "HFP_ari+noa_condo_$v.xlsx" "$OUT/$tag/$v.json" \
    > "$OUT/$tag/$v.out" 2>&1 || echo "FAILED $tag $v"
'

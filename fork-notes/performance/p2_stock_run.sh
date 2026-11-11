#!/usr/bin/env bash
# P2 on stock upstream: every shipped example under local search, from two checkouts of upstream
# `dev` (stock, and with fork-notes/issue-ls-settled-steps.patch applied), interleaved so that both
# run at the same load, three at a time.
#
#   fork-notes/performance/p2_stock_run.sh <stock checkout> <patched checkout> <out dir> [options JSON] [jobs]
#
# Each checkout needs the fork's .venv (symlinked). Output: <out dir>/{base,settled}/<case>.json.
# CASES="Case_joe Case_jack+jill" limits the run to those examples. Options JSON '{}' keeps
# upstream's caps (300 s per search, 60 s per step).
set -u
export STOCK=$1 PATCHED=$2 OUT=$3 OPTS=${4:-'{"localSearchTime": 7200, "localSearchStepTime": 1800}'}
JOBS=${5:-3}
HERE=$(cd "$(dirname "$0")" && pwd)
export HERE PY=$(cd "$HERE/../.." && pwd)/.venv/bin/python
mkdir -p "$OUT/base" "$OUT/settled"
for f in "$STOCK"/examples/Case_*.toml; do
  c=$(basename "$f")
  if [ -n "${CASES:-}" ] && ! [[ " $CASES " == *" ${c%.toml} "* ]]; then continue; fi
  echo "base $STOCK $c"
  echo "settled $PATCHED $c"
done | xargs -P "$JOBS" -L 1 bash -c '
  tag=$0; tree=$1; case=$2; name=${case%.toml}
  PYTHONPATH=$tree/src "$PY" "$HERE/p2_stock_probe.py" "$case" "$OUT/$tag/$name.json" "$OPTS" \
    > "$OUT/$tag/$name.out" 2>&1 || echo "FAILED $tag $case"
'

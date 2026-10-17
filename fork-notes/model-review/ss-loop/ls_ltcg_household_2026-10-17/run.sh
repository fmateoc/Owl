#!/bin/bash
# run.sh old|new SCRIPT ARGS... : one household stand-in script on the unpatched or patched fork
S=${S:?set S to a scratch dir holding fork_old/ (a worktree without the patch)}
which=$1; shift; script=$1; shift
if [ $which = old ]; then root=$S/fork_old; else root=/home/user/Owl; fi
tag=$(basename $script .py)_$(echo "$@" | tr ' ;,' '___')_$which
cd $root && { echo "# $script $* on $which ($(git log --oneline -1 | cut -c1-7)$(git diff --quiet -- src || echo ' + issue-ls-ltcg.patch')), started $(date -u +%FT%TZ)"; PYTHONPATH=$root/src /home/user/Owl/.venv/bin/python -c "import owlplanner;print('# owlplanner from', owlplanner.__file__)"; PYTHONPATH=$root/src /home/user/Owl/.venv/bin/python fork-notes/model-review/$script "$@" 2>/dev/null; echo "# finished $(date -u +%FT%TZ)"; } > $S/hh/$tag.txt 2>&1

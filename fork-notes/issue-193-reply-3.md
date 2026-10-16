# Third comment on #193: the ss-binaries experiment on the repro, for the user to post

Status: **not posted, moot** (2026-10-16): the maintainer had already concluded the experiment and
deleted `ss-binaries` (relayed by the user; `git fetch --prune` shows the branch gone). Kept as the
record of our measurement. Drafted 2026-10-16. Upstream branch `ss-binaries` (`abd39b4`, "[experiment] SS taxability
MIP: one binary per year when the benefit is at least the tier gap", marked not for merge as is)
measured on the #193 repro: `issue-193-binaries-output.txt` (`issue-193-ls.py 600 ss-bb,ss-ls`, run
once per `OWL_SS_VARIANT`, stock code, date frozen at 2026-10-15). Nodes are `solverNodesTotal`,
the whole solve over every loop iteration; the maintainer's "1.5-4x" may count something else, so
the comment says what was counted. Not merged into the fork: it changes `"optimize"` by default
(and so local search), at more nodes.

---

For the record, `ss-binaries` (`abd39b4`) on the seven repro cases, `withSSTaxability="optimize"`,
counting branch-and-bound nodes over the whole solve (`solverNodesTotal`, every loop iteration):

| `OWL_SS_VARIANT` | nodes | time, branch-and-bound | time, `mipStrategy="local-search"` |
|---|---|---|---|
| dev formulation | 700-1,222 | 14-22 s | 24-32 s |
| `drop` (default) | 3,392-4,735 (3.6-6.3x) | 35-60 s | 26-36 s |
| `cuts` | 1,090-2,428 (1.3-2.6x) | 22-32 s | 23-34 s |

All three give the same bequest to the dollar in every case, under branch-and-bound and local
search. So on these cases `drop` costs more than the 1.5-4x in your commit message (unless that
counts nodes differently). Everything here is far slower than `"convex"` on `ss-convex`, which takes
0.8-1.2 s for the same plans.

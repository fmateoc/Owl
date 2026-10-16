# Second reply on #193: the "convex" prototype checked with the repro, for the user to post

Status: draft 2026-10-16, **reassessed** after the maintainer moved the "convex" commits from `dev`
to the branch `ss-convex` (`dev` force-pushed back to `10b9f72`) and added `c22f46d` (cheaper cap
probe). The first version of this draft quoted `83a580b`; the numbers below are from the branch tip
`c22f46d`. Sources, both on stock code, date frozen at 2026-10-15:
`issue-193-convex-c22-output.txt` (`issue-193-ls.py 600 loop,convex,ss-bb`) and
`model-review/ss-loop/examples_convex_c22_stock_2026-10-16.txt` (`ex_ss.py ... convex`). The
`83a580b` runs are kept (`issue-193-convex-output.txt`, `examples_convex_stock_2026-10-16.txt`)
for the before/after line below.

What changed in the reassessment: the fix is now a prototype on a branch, so the reply is evidence
for moving it to `dev`, measured on the branch tip; `c22f46d` made "convex" about 3-4x faster on
the repro (2.2-5.2 s -> 0.8-1.2 s) with the same plans; a few examples moved by -$22 to +$21;
`morgan` is now +2.10% (+2.15% at `83a580b`); the Summary still labels "convex" solves "loop".
Left out, as before: the fork-only results (NJ exclusion under "convex", the fork's LTCG loop gap).

---

Thanks. I ran the repro against `ss-convex` at `c22f46d`.

- **The seven #193 cases:** `withSSTaxability="convex"` gives the same bequest as `"optimize"` to
  the dollar in all seven, with a fixed-point residual of $0. It takes 0.8-1.2 s, the same as the
  loop, against 14-21 s for branch-and-bound. At `83a580b` it took 2.2-5.2 s for the same plans.
- **The 18 examples:** SS residual $0 in all of them. The bequest is at or above the loop's in 17
  (`Case_alex+jamie` -$12, -0.01%). `Case_john+sally` gains +72%, `Case_morgan` +2.10%,
  `Case_kim+sam-bequest` +0.72%. Solve times are under 3 s for every example but `Case_jack+jill`,
  which takes 30.5 s. Against `83a580b`, a few examples moved by -$22 to +$21, consistent with
  the later passes now covering near-ties only.

On these cases it gives the exact SS plan at about the loop's cost, so I see no reason here not
to move it to `dev`.

One small thing, still there at `c22f46d`: the Summary's breakpoint method reads "loop" for a
`"convex"` solve (`_breakpointFamilies` lists SS only under `"optimize"`). A saved workbook
therefore does not show that SS was priced exactly.

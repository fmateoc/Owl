# Reply on #193: local search (mipStrategy="local-search") on the repro cases, for the user to post

Status: draft 2026-10-16. Answers the maintainer's question on #193: "How does that compare with
the local MILP which takes binary families one by one around a local search
(mipStrategy=local-search)?" Numbers: `fork-notes/issue-193-ls.py` on stock `dev` `10b9f72`,
output `issue-193-ls-output.txt` (date frozen at 2026-10-15; one process on a 4-core cloud
container). The 0.3% gap of the presets is upstream's default when Medicare is optimized and no
`gap` is given (30 x GAP, `plan.py:5063-5070` on `dev`). The issue's "a few seconds" for the exact
SS solve was never timed; it is corrected here.

---

Local search closes the gap the same way branch-and-bound does. I ran every case of the repro
five ways on `dev` `10b9f72` (script `issue-193-ls.py`, same couple and frozen date). The
issue's part 5 already used local search, through `breakpointMethod="local-search"`, but only on
one case.

Bequest, today's $:

| case | loop | SS `optimize`, branch-and-bound | SS `optimize`, `mipStrategy="local-search"` | `breakpointMethod="local-search"` | `breakpointMethod="branch-and-bound"` |
|---|---:|---:|---:|---:|---:|
| NY $95k | 948,275 | 988,448 | 988,448 | 988,945 | 988,945 |
| NY $100k | 728,034 | 766,704 | 766,704 | 767,187 | 767,187 |
| NY $105k | 506,651 | 544,961 | 544,961 | 545,434 | 545,434 |
| NY $110k | 283,374 | 323,217 | 323,217 | 323,684 | 323,376 |
| NY $115k | 63,523 | 101,321 | 101,321 | 101,845 | 101,845 |
| NY $105k, Roth 61/39 | 518,267 | 552,010 | 552,010 | 552,481 | 552,481 |
| NJ $105k | 478,708 | 527,310 | 527,310 | 527,580 | 527,580 |
| time per solve | 0.7-1.3 s | 14-21 s | 22-31 s | 29-46 s | 17-39 s |

- With only the SS family set to `optimize`, local search and branch-and-bound return the same
  bequest to the dollar in all seven cases. Starting from the loop's plan does not hold the search
  back here.
- The presets, which also optimize IRMAA, LTCG and NIIT, add $270-524 more. That is 0.6-1.6% of
  what the SS family alone recovers ($33.7k-48.6k).
- `breakpointMethod="branch-and-bound"` matches local search except at $110k, where it gives $308
  less. It stops at the 0.3% gap that the solver sets by default when Medicare is optimized; local
  search's steps are solved to 0.01%.
- Every exact run ends with a fixed-point residual of $0; the loop's runs end with $2.2k-26.4k.

One correction to the issue: I wrote that the exact SS solve took "3 iterations and a few
seconds" here. Three iterations is right, but I had not timed it. It takes 14-21 s against about
1 s for the loop, on a 4-core cloud container.

So local search is the right tool for this couple, and it costs 29-46 s per solve. My question 2 then
becomes a pointer: when the loop ends at the cap or in a cycle with a large SS residual, the
message could recommend `breakpointMethod="local-search"`.

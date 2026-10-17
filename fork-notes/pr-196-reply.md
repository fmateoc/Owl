# Reply to the maintainer on PR #196 (draft, for the user to post)

Maintainer on PR #196 (2026-10-17, relayed by the user): "Are you sure you want to keep the
ss-convex implementation? My tests were mixed. I am not sure this adds much. Your call."

Measured on stock `fb8b10e` (the PR head), date frozen at 2026-10-15:
`model-review/ss-loop/pr196_check_2026-10-17.txt` (scripts `pr196_*.py` beside it). Below, version A
keeps "convex"; version B, if the user drops it, cuts the PR to the warning.

---

## Version A (keep "convex", opt-in)

I'd keep it, as an opt-in for loop users. I think the mixed results come from the other loops, not
from SS. What I measured on `fb8b10e` (date frozen at 2026-10-15):

**Holding everything else exact, "convex" and "optimize" give the same plan.** With IRMAA, LTCG,
NIIT, senior bonus (and ACA for morgan) on `"optimize"` and only SS changed:

| example | SS "convex" | SS "optimize" | MIP gap |
|---|---:|---:|---:|
| john+sally | 31,693 | 31,693 | 0-0.2% |
| helen+ruth | 195,201 | 195,246 | 0.3% |
| joe | 93,109 | 93,057 | 0.3% |
| morgan | 44,212 | 44,201 | 0.3% |
| kim+sam-bequest | 1,961,483 | 1,961,326 (2nd iterate; I stopped it, each MILP was hitting `maxTime`=900 s) | 0.3-0.5% |

The differences are within the gap. The seven #193 cases matched to the dollar earlier.

**With the other families on the loop (the defaults), the two land on different fixed points.**
Under "optimize" the other loops did not settle in three examples: helen+ruth residual $20,820,
joe $20,780, jack+jill $15,506, mostly LTCG. Under "convex" the residual was $0-1 in all eight
examples I ran. The largest gap, john+sally (28,898 under "convex" vs 18,481 under "optimize",
both with $0 residual), is not SS at all: taxable SS equals the IRS formula in every year of both
plans. "Convex" converts less in 2026-2027 and stays out of an IRMAA tier in 2028-2030 (lifetime
Medicare $136.3k vs $143.2k). Seen from one side or the other, that gap is noise from the IRMAA
loop. So it shows up as "mixed" in both directions.

**Where it adds something:** exact SS at about the loop's cost, when the rest stays on the loop:
1.8 s vs 14.7 s for SS "optimize" on john+sally (uncontended), 0.8-1.2 s vs 14-21 s on the #193
cases. On the 18 examples the gain over the plain loop is small: 15 of 18 are under 0.3%, kim+sam-bequest
0.7%, morgan 2.1%, and john+sally +72% (the IRMAA fixed point above). On
#193-type cases, with many SS years in the phase-in, it is $34-49k.

**Where it doesn't:** with other families on "optimize" it is slower than SS "optimize" (helen+ruth
867 s vs 252 s, joe 584 vs 251, morgan 1,208 vs 249, run concurrently), because the cap probe
re-solves a MILP per year. The presets replace it anyway (`breakpointMethod` sets SS to
"optimize"). So it is a loop-mode tool. If you keep it, the docs could say so: use it with the other
families on the loop.

**Side finding, separate from this PR:** on john+sally the local-search preset returns 20,004, while
the branch-and-bound preset returns 31,778 (gap 0.19%, 21 s) and "convex" alone 28,898. I can file
that separately if useful.

If you'd still rather not carry it, I'll cut the PR down to the warning, pointing to
`withSSTaxability="optimize"` and `breakpointMethod="local-search"`, and drop the label change.

---

## Version B (drop "convex")

Fine to drop it. I'll rework the PR to `dev` without `ss-convex`: only the warning when the loop
leaves SS unsettled, pointing to `withSSTaxability="optimize"` and `breakpointMethod="local-search"`.
The Summary label change goes, since without "convex" there is nothing to name.

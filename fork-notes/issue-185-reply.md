# Optional reply on #185 (federal itemized deductions), for the user to post or not

Status: **posted by the user** (relayed 2026-10-16); drafted 2026-10-15. Follow-up: #193. Answers the maintainer's first reply ("Adding more stuff to the
recursion loop is what causes cycling and prevents monotonic convergence. I'll run a few tests
and get back to you.") with the fork's measurement, before his tests come back. Numbers:
`fork-notes/model-review/phase3-review/itemized_convergence_2026-10-15.txt` (script
`itemized_convergence.py` in the same folder; fork `c06b6af`, upstream `dev` `10b9f72` merged,
date frozen at 2026-10-15). Every number below is from that file.

Posting is the user's call. For: he is testing now, and the data covers exactly the concern he
raised. Against: it is a second comment before his answer (lesson 9). The text says it measures
the fork's design, not whatever he builds.

---

Thanks. Since cycling is the concern, here is what I measured on my fork's version (loop only, no
binary: rows on existing columns, with the branch and the floors taken from the previous iterate).
Default self-consistent loop, `withItemized` off vs on, nothing else changed:

- **The 18 examples as shipped**: the same number of iterations and the same ending in all 18.
  Two of them itemize (`Case_devon` 22 years, `Case_jordan+taylor` 1 year); the other 16 give the
  same plan to the dollar.
- **A synthetic NJ couple** ($1.5M tax-deferred, $25k property tax, with and without a $600k
  mortgage, law as enacted and the 2032 reversion, `maxBequest` and `maxSpending`). In the 6 pairs
  where it itemizes: same ending in 5, one "oscillatory" became a 2-cycle; 0 to 4 more iterations;
  the largest fixed-point residual is the SS taxable fraction in both modes ($1.1k-1.6k).
- **The same couple in NY with a mortgage, federal itemizing only**: 18-19 iterations and a
  2-cycle in all 4 cases (residual $2.6k-4.5k). With itemizing off, 2 of those 4 hit the 30-iteration
  cap.

So in these runs federal itemizing did not add cycling that the loop did not already have. Here
the loop rarely converges monotonically either way: among the examples, 4 of 18 end "monotonic",
with or without itemizing. The bad cases come from the loop itself. The NY couple with a mortgage,
under the 2032 reversion, hits the iteration cap at $20k-30k of property tax with itemizing **off**
(SS residual $19k-25k), and returns a bequest 7% below local search ($464k vs $498k). In that
case local search orders the variants the way it should and leaves no residual: off $498k, federal
$670k, federal plus my NY schedule $710k.

One reason it adds little: where the bounds decide the branch (mortgage interest and property tax
are known in advance; under `maxBequest` spending is pinned), itemizing adds rows but no loop
quantity. Elsewhere it adds the branch, the 7.5% medical and 0.5% charity floors, and the SALT
phase-down above $505k of MAGI. Each of these is a kink where the deduction stays continuous, not a
cliff.

This is my implementation. Yours may load the loop differently, so your tests are the ones that
count. I can send the script if that helps.

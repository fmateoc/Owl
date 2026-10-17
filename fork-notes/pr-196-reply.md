# Reply to the maintainer on PR #196 (draft, for the user to post)

Maintainer on PR #196 (2026-10-17, relayed by the user): "Are you sure you want to keep the
ss-convex implementation? My tests were mixed. I am not sure this adds much. Your call."

Measured on stock `fb8b10e` (the PR head), date frozen at 2026-10-15:
`model-review/ss-loop/pr196_check_2026-10-17.txt` (scripts `pr196_*.py` beside it).

Revised 2026-10-17 after the user's review. The first draft recommended keeping "convex" as an
opt-in, in a version A. That is dropped, for these reasons:
- An opt-in adds work for the maintainer (code, docs, tests) and a decision for every user. A
  user can only make that decision with a signal saying when "convex" matters, and there is none.
  The PR's residual warning catches a loop that does not settle. It misses a loop that settles
  short: the #193 couple at $105k ends with $1,167 of SS residual, under the $1,550 bar, while
  the loop is more than $10k short of "convex".
- Where "convex" could be chosen deliberately, it is dominated. With the other families on
  "optimize" it is 2.3-4.9x slower than SS "optimize" for the same plan, and both presets replace it
  with "optimize". Its only edge is exact SS at the loop's speed with everything else on the loop.
  No user can tell when they need that.
- Version A also said "I think the mixed results come from the other loops". That was not
  measured: we never saw his tests. What we measured is the source of the differences in our own
  runs. The reply now says only that.

The one form in which "convex" would add value without a new choice is replacing the SS loop as the
default. On the upstream examples it is >= the loop in 17 of 18 (alex+jamie -$12) with SS residual
$0 in all, and all but jack+jill finish under 3 s (jack+jill 30.5 s vs 1.4 s); the #193 cases gain
$34-49k. A default change also needs measurements we have not made: the full test suite with the
default switched, the stochastic and regret sweeps, and timings on larger plans. It is his call, and
he is skeptical. So it is not proposed here. The user can raise it separately if wanted.

The pointer in the warning: `withSSTaxability="optimize"`, the exact SS model, which has no other
effect on the plan. It replaces "convex or local search" in the first PR text. Local search is no
longer suggested: on john+sally it stops at $20,004 against branch-and-bound's $31,778
(`issue-ls-ltcg.md`, not yet fixed upstream).

Fork consequence: if upstream drops `ss-convex`, the fork drops its merge of it at the next sync,
along with the `warm_keys` edit in `_ssCapProbe` and `tests/plan/test_ss_convex_fork.py`. The
fork's decision runs use the local-search preset and never used "convex", which in NJ took 4-7 min
on the fork.

---

No, drop it. I'll rework the PR onto `dev` without `ss-convex`. It will keep only the warning
when the loop leaves Social Security unsettled, pointing to `withSSTaxability="optimize"`. The
Summary label change goes too, since without "convex" there is nothing for it to name.

For the record, what I measured on the PR head (date frozen at 2026-10-15), since it may help
read your tests:

- **With every other family exact** (IRMAA, LTCG, NIIT, senior bonus, and ACA for morgan on
  "optimize"), "convex" and "optimize" gave the same plan within the MIP gap: john+sally 31,693 /
  31,693, helen+ruth 195,201 / 195,246, joe 93,109 / 93,057, morgan 44,212 / 44,201. "Convex" took
  2.3-4.9x longer there, because its cap probe re-solves a MILP per year.
- **With the other families on the loop**, the two differed in both directions on the examples.
  In my runs the differences came from the other loops, not SS. Under "optimize", the LTCG, NIIT and
  IRMAA loops left $15.5-20.8k of residual in helen+ruth, joe and jack+jill. On john+sally
  ("convex" 28,898, "optimize" 18,481, both with $0 residual), taxable SS equals the IRS formula in
  every year of both plans; the gap is the IRMAA loop settling at another point.

So "convex" bought exact SS at the loop's speed, but only with everything else on the loop. As an
option, that is one more choice with no signal for when to make it. The warning in this PR catches
a loop that does not settle, but not one that settles short.

Separately: on john+sally the local-search preset stops at 20,004 against branch-and-bound's
31,778. It is not SS: step (b) pins the LTCG binaries while SS moves. I'll file it as its own issue
with a repro and a patch.

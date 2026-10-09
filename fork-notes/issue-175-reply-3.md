# Draft reply on #175 (Owl-budget, third round, conceptual), for the user to post

Status: draft, 2026-10-09. Not posted. Answers the maintainer's reply of 2026-10-09 (ownership,
hooks, longevity, JSON vs Excel, sources, cost function), at the level of the discussion: ideas
first, measurements only as support. The earlier, measurement-led version is
`issue-175-reply-3-measured.md` (superseded); the numbers quoted here come from it
(`fork-notes/model-review/essential_stakes.py`, run 2026-10-09 on `5a4a12f`).

What was checked for this draft, against Owl's source on `claude/phase2-housing`:

- `spending.gen_spending_profile`: the smile's cosine has one period over `span = N_n - 1 - delay`,
  and the profile is renormalized to a neutral sum, so the dip and the rise are placed relative
  to the plan's length, not to age. The survivor step multiplies the whole profile by one fraction.
- `clone(expectancy=...)` builds a fresh plan from the configuration (docstring), so the profile is
  regenerated for each sampled lifespan; `runStochasticSpending(with_longevity=True)` draws
  lifespans from the SSA tables.
- `stresstests._stochastic_lp`: one commitment `g` for the whole budget, with shortfall
  `sigma_s >= g - basis_s` and a single risk parameter lambda.
- `spendingSlack`: one percentage for the whole profile.
- No payroll tax: grep for `fica|oasdi|payroll tax|0.062|0.0145` in `src/owlplanner` finds none.

Recalled, not checked here: the literature points (Blanchett's age-indexed spending decline; CE
being cross-sectional and HRS/CAMS longitudinal; CE healthcare including insurance premiums and CE housing including mortgage interest;
floor-and-upside / safety-first as a named approach). They are marked as such in the text.

---

Thanks. Agreed on 1 and 2. Rather than more numbers, here are some ideas on the open questions,
since they seem to hang together: longevity, elasticity and the cost function are mostly one
question about what a budget line is tied to and what gives when money is short.

**What a budget line is tied to (your point 3).** Lines follow different clocks: the calendar (a
lease, a car loan, a move in 2030), age (travel while we are able, care late in life), and
household events (retirement, the first death, a move). Owl has a fourth one today: the length of
the plan. The smile is drawn over the horizon, so a longer life stretches the go-go years and
moves the dip later, rather than adding years at the end. If each line is tied to the clock that
causes it, longevity needs no rule of its own: a longer life appends years, and whatever lines
are active at those ages apply. The literature on the spending decline (Blanchett's "smile", from
memory) is indexed by age, which fits this.

That also lets me revise what we said earlier about specifications versus arrays. Your "outputs
are time series" works, provided there is one series per household state: both alive, and each
spouse as the survivor, by year, out to the longest life we'd ever sample. Owl splices them at
the first death. Each line carries its own survivor share (rent 100%, food perhaps 60%) when the
series are built, so the single survivor fraction becomes a property of lines rather than of the
plan. Three columns are horizon-independent, easy in Excel, and easy to pass over MCP. The only
lines it can't express are ones timed from the death itself ("downsize two years after"), which
seems an acceptable loss.

**Elasticity: an order rather than weights (cost function).** Splitting core from discretionary
is a priority order, and users can state an order even when they can't state utility weights. It
generalizes to a few tiers (essential, important, nice to have), funded in order, and the bequest
can take a place in that order too: for some households a minimum bequest is essential, for
others it is the residual. Your two objectives become the two corners: with everything fixed, the
bequest is the residual; with the bequest fixed, the top tier is. With two tiers it is still one
LP, the core as a floor and the discretionary part scaled; more tiers would be a short sequence of
LPs, each fixing what the previous one reached.

**Elasticity matters mostly under uncertainty.** In a single deterministic plan with ample money
the split hardly changes anything; it matters when a sequence or a long life goes wrong. Owl
already has the machinery for that: stochastic spending trades a commitment against shortfall
risk through lambda, but today the shortfall is shared evenly by the whole budget. A natural
extension is one risk tolerance per tier: the core committed at a high success rate, the
discretionary part closer to risk-neutral. Two numbers then summarize a plan: the probability the
core is funded, and the distribution of the discretionary level. This is the floor-and-upside idea
from the safety-first literature (from memory), expressed with Owl's own tools, and it tells the
user what guaranteed income (Social Security timing, an annuity, a TIPS ladder) should be sized
to cover: the core, not the whole budget. Timing has the same split: discretionary lines are
elastic in time (a trip can move), the core is not, so a slack per tier would be more faithful
than one `spendingSlack`.

We tried the two-tier version in our fork to see whether the distinction is real. On a test couple
with sampled lifespans, scaling the whole budget "funded" every draw by cutting rent by 20-25%
along with everything else, while holding the core fixed showed 9 of 200 draws where it could not
be funded, in 8 of them a survivor who outlived the other spouse by 10 to 30 years on one Social
Security check. Scaling the whole
budget hides exactly the risk the split is meant to show.

**Sweeps (your point 4).** With tiers, the variants people compare (rent or buy, where to live,
when to stop working) mostly change the core. So the natural result of a sweep is the core-funded
probability and the discretionary level per variant, with the bequest alongside, rather than one
maximal spending number.

**Data: own history for the level, the literature for the change (your point 5).** A household's
past five years are the best evidence for the level; the published sources are better at how
spending changes with age and at lines a household has no history for (health at 80, long-term
care). Two cautions, from memory: CE is cross-sectional, so today's 80-year-olds are another
cohort, not us at 80, whereas HRS follows the same people; and survey categories include costs Owl
already computes (Medicare premiums in healthcare, mortgage interest in housing), so benchmarks need mapping to the
budget's boundary before use. Fidelity's 2026 estimate is a case in point: about 45% of its
$185,500 is Medicare Part B and D premiums, which Owl already charges.

**The decade before retirement.** There the budget plays another role: wages minus taxes minus
spending is saving, so the budget sets how much can be contributed, and the retirement date is
the decision linking the two. Work-related lines (commuting, payroll-deducted items) are tied to
that date. One gap on Owl's side: we found no payroll tax in its source, so a working-years budget
would have to carry Social Security and Medicare tax as a line.

Questions back:

1. Should the bequest be one of the tiers (a floor that can be essential), or stay the objective?
2. By "ladders", do you mean a ladder of budget variants to sweep, or bond ladders? If the
   latter, the core tier is the natural target for sizing one.
3. Would anchoring Owl's own smile to age, rather than to the plan's length, be worth doing on its
   own, independent of Owl-budget?

# Draft reply on #175 (housing ledger), for the user to post

Status: **posted** by the user on #175, 2026-10-08. No answer yet. Design details: `phase2b-budget-plan.md`.

---

Thanks, that's a fair line to draw, and it changes the proposal.

**State taxes.** Agreed, we'll keep the New Jersey property tax deduction in our fork, with the
other NJ rules, and not ask you to carry it.

**Budget → spending profile.** We tried your framing against what we built, and it holds up. On a
test couple ($1.5M tax-deferred, $80k/yr of other spending with a 60% survivor step, $30k/yr rent),
putting the rent inside the spending profile instead of a separate outflow gives exactly the same
plan under `maxBequest` at a fixed spending level: same bequest to the dollar ($1,209,697), same
outlay every year. That is how we read rent-vs-buy questions anyway, since home equity can't be
spent. Under `maxSpending` the two differ in meaning, as you'd expect: the envelope scales the whole
budget, rent included (the first-year total was within 0.2%; survivor years up to $2,821/yr apart).

So we'd like to propose the split you describe:

1. **In Owl:** a spending profile can come from outside, as amounts in today's dollars per plan year,
   instead of the flat/smile shape. Owl normalizes it to the existing `xi_n`, so the LP, the
   `spendingSlack` rows and the objectives don't change; under `maxBequest`, `netSpending` can default
   to the profile's first year. One requirement we found: it has to be stored as a specification Owl
   evaluates, not as a fixed array, because the survivor step sits at the first death and
   `clone(expectancy=...)` and lifespan sampling rebuild the plan with a new horizon.
2. **Outside the optimizer:** a small budget module that builds that specification from line items
   (an HFP sheet: name, type, first and last year, amount, real growth, and the share kept by a
   survivor, e.g. 100% for rent, the case's survivor % for personal spending). Today's flat and
   smile profiles are the case of a single "core" line. Cars, long-term care, travel and housing all
   fit the same rows. One-off items stay where they are (big-ticket items, Fixed Assets, Debts with
   the property link from #173).

Would you take (1) on its own, or (1) and (2)? If you'd rather implement it yourself, as with #173,
we'll follow your design. Otherwise we can send a patch on `dev`. Either way we'll build it in our
fork now, since we need it for the rent-vs-buy comparison, and drop our version when yours lands.

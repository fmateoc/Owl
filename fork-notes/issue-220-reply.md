# Reply to the maintainer on #220 (draft, for the user to post)

Maintainer on #220 (relayed by the user 2026-10-23): "That's a good point that was overlooked. What
did you end up doing? This case does not apply to me and therefore I have not given a lot of
thoughts into it. I assume it is closer to your situation and therefore I trust your judgement to
fill the gap that suits you best. The only requirement is that the optimize full MILP is still
affordable on today's computer. Otherwise, we are chasing a moving target."

Drafted 2026-10-23 on `claude/phase5-step1` (fork at upstream `dev` `e3592e7`). Revised the same
day after the user's review: the maintainer asked for an implementation, not a choice, so the test is part of
the model with no switch (the fork removed its `withEarningsTest` switch the same day: its only effect was to
keep wrong cases wrong), and the reply offers the implementation, not an option. The payroll tax
is left out of this reply (still opt-in in the fork). The last paragraph promises a PR on stock
`dev`: the PR is built (branch `fmateoc:earnings-test-pr`, `fork-notes/pr-220-body.md`); open it,
then replace PR_LINK below with its link and post this.

## What the text rests on

- **What the fork does:** `info/PARAMETERS.md` (`gross earnings`, `months worked`),
  `info/modeling-capabilities.md` (Social Security row), PROGRESS.md "Phase 5 step 3" / "step 4" / "The earnings test without an
  option", `phase5-plan.md` §4. Read from the fork's files today, not recalled.
- **Rules:** as cited in #220 (POMS and 20 CFR 404 subpart E, read 2026-10-17/18); unchanged.
- **"Nothing withheld = today's streams":** `tests/ss/test_earnings_test_always.py` (where the test
  withholds nothing the streams are `compute_social_security_benefits`' own output, checked with a
  marker on that function) and `tests/ss/test_earnings_test_plan.py` (the 15 examples without SS
  before FRA in a work year solve to the same objective to the cent as without the test).
- **Full-MILP cost: measured** 2026-10-23, before the switch was removed (off = Owl without the
  test, on = with it; the code path with the test is the one the fork now always runs), `fork-notes/phase5/et_milp_cost.py`, output
  `et_milp_cost_2026-10-23.txt` (today's date; `breakpointMethod="branch-and-bound"`, the fork's
  itemizing off; each case at its own claiming ages; two solves per setting; a container restart interrupted
  the run after alex+jamie's first solve, and it was resumed for the missing solves, noted in the
  file). The row-tag check ran alongside alex+jamie's first test-on solve; that solve's time
  (162.9 s) matches the second (162.2 s)). The row difference: `ss_tax_*` rows, 8 for chris+pat's 2028
  (checked by tag count, loop and SS/LTCG-optimize runs, same day; script not kept).
- **Not claimed:** anything about upstream's own MILP timings on other machines; whether a
  `withSSAges` search under branch-and-bound is affordable at all (97 candidates per person per
  round at 40-250 s each is upstream's cost with or without the test; not run here).

The text answers his question with what was built, then his one condition with numbers, then
points to the PR. It does not re-argue the problem (he accepted it). It answers our own four questions
from #220 as the fork decided them, since he left the design to us.

---

Thanks. Here is what I built in my fork. The test is part of the model, with no option: a case
with no earnings up to someone's FRA year is unchanged, and the cases it changes are the ones
Owl had wrong.

**Where it sits.** In the Social Security streams, before the LP sees them, as proposed in the
issue. For a given claiming age, the amounts withheld each year, the crediting months and the
higher benefit from FRA are fixed numbers, so the LP just receives the net benefit: no new column,
row, binary or loop quantity. Since #195 every `withSSAges` candidate is a fixed-age solve, so
the search sees the test exactly, spousal charging and the ARF included, with no other change.

**Rules.** The withholding is \$1 for \$2 of earnings above the annual exempt amount before the FRA
year, and \$1 for \$3 above the higher amount in the FRA year (months before FRA only). The excess
is charged month by month from entitlement, first against everything paid on the worker's record
(the spouse's benefit included), then the spouse's own excess against the spouse's own benefit,
and it is never carried into the next year. In the grace year, non-service months are paid. At FRA
the reduction factor is recomputed without the withheld months (the ARF), for the worker's own
benefit and for a spousal benefit on the spouse's record. Exempt amounts for 2024-2026 come from
POMS RS 02501.025 D; later years are held at the 2026 amount in today's dollars, since Owl has no
wage index. Survivor benefits are left out: checks from the year of the first death are what Owl
pays today.

**Inputs** (my questions 2 and 3). Two optional per-person columns in Wages and Contributions:
- *gross earnings*: earnings as SS counts them (W-2 box 5 plus net self-employment earnings).
  Where it is 0 or absent, *anticipated wages* is used, with a warning naming the years where a
  taxable, 401(k) or IRA contribution column is non-zero (those wages are net of contributions,
  which the test counts).
- *months worked*: 0-12, months of work at the start of the year. Where it is 0 or absent, it is
  12 in a year with earnings. It decides the grace year and how the FRA-year earnings split
  around the FRA month.

`other inc` is not read by the test.

**Outputs.** Summary rows *SS withheld by the earnings test* and *ARF months* (for a household
with earnings before someone's FRA), a *SS withheld* column next to Social Security in the
per-person worksheets, and a warning when a fixed claiming age pays nothing before FRA.

**What it leaves alone.** Where the test withholds nothing, the streams are the output of
`compute_social_security_benefits` itself, not of the test's own monthly builder. So a case the
test does not touch does not depend on the new code. The 15 examples without benefits before FRA
in a work year give the same objective to the cent. alex+jamie, chris+pat and jack+jill change,
as in the issue.

**Your condition: the full MILP.** I measured the three examples from the issue at their own
claiming ages, with `breakpointMethod="branch-and-bound"`, without and with the test (same machine,
same day, today's date):

| Example | Columns | Binaries | Rows (without / with) | Without: time (nodes) | With: time (nodes) |
|---|---:|---:|---:|---:|---:|
| chris+pat | 1,900 | 352 | 1,968 / 1,960 | 50.7 s, 49.8 s (15) | 43.7 s, 42.7 s (1) |
| alex+jamie | 1,626 | 289 | 1,584 / 1,576 | 248.9 s, 197.8 s (25) | 162.9 s, 162.2 s (143) |
| jack+jill | 1,900 | 352 | 2,001 / 1,993 | 312.6 s, 308.3 s (267) | 200.8 s, 202.0 s (1,077) |

(Two solves of each, HiGHS, gap 0.3% in all, one machine.)

The model has the same columns and binaries. It loses the SS-taxability rows of a year in which
everything is withheld, since Owl writes those rows only for years with benefits. Building the
streams with the test takes about 1 ms per solve. Times and node counts move with the problem's
numbers, as with any change of inputs (here every case solved faster with the test, and two of them
took more nodes), but the test adds nothing for the solver to work on. Under `withSSAges` the
number of candidates does not change, and each candidate is the same fixed-age problem.

The PR is PR_LINK, on `dev`: the test and the two columns, with tests (POMS examples worked by
hand, the no-op property on all examples, the `withSSAges` path) and the recorded results
updated. It's yours to take or not.

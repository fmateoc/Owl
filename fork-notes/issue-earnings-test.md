# Draft upstream design issue: the SSA earnings test (Phase 5 step 9), for the user to post

Status: **posted by the user as #220** (2026-10-22). Drafted 2026-10-22 on `claude/phase5-step1` after
merging upstream `dev` `37afa2a`. Reviewed the same day before posting: units in the table, the grace-year and ARF wording,
the case's own "works through 2028", `other inc` as upstream documents it, the exempt-amount
projection, Jill re-measured with itemizing off, and two claims narrowed to what was checked. Concept level (`phase3-plan.md` §2, lessons 2, 3, 7, 8): the problem, the rules, a shape
and measured stakes, not the fork's code. Federal Social Security only. Decision D8 (plan §6): post
after step 4, with upstream's own examples as the evidence.

## Where to post, and when (user's call)

- **A new issue.** Nothing open upstream covers it: the limitation is documented, not tracked.
- **Timing.** Of #199-#218 (filed by `rationalpiper` and the maintainer, 2026-10-20/21), the
  maintainer fixed all but #204-#206 within two days (merged by `37afa2a`, 2026-10-22). Three of those touched the code this proposal
  sits on (#210 survivor limit, #211 spousal DRCs, #212 born on the 1st), so the SS module is fresh
  in his mind; on the other hand, a design issue right after a batch of 20 may wait. Nothing here
  goes stale quickly: the evidence is upstream's own examples, rerun on `37afa2a`, and moves only
  with the date (plans start today).

## What the text rests on

**Verified on stock upstream `dev` `37afa2a`** (`git show upstream/dev:...`, 2026-10-22):

- `info/modeling-capabilities.md:26`: "Earnings test not modeled; users assumed fully retired
  before FRA." `papers/owl.tex:407` ("users are assumed to be fully retired before their FRA") and
  `:5318`; `socialsecurity.py:19-22` ("This tool assumes users are retired with no earned income
  above the exempt amount").
- `ui/Documentation.py:444`: *anticipated wages* is "entered **net of all contributions** listed
  in the *ctrb* columns".
- `info/USER_GUIDE.md:41` walks through jack+jill, one of the three examples below.
- `withSSAges` solves the plan at each open claiming month and keeps the best (#195,
  `_ssAgeSearch`): every candidate is a fixed-age solve.

**Real run on stock `dev` `37afa2a`** (`fork-notes/issue-earnings-test-repro.py`, output
`issue-earnings-test-repro-output.txt`, 2026-10-22, run from a worktree of `upstream/dev` with its
own `src` on the path): the table and the two picks quoted in the issue text.

**Rules: verified in the primary text** (plan §2.1, POMS read 2026-10-17; §2.1b, 20 CFR 404
subpart E, eCFR 2026-10-15 text, read 2026-10-18): RS 02501.025 D (2026 amounts \$24,480 and
\$65,160), RS 02501.021 (what counts; FRA-year months before FRA only), RS 02501.080 (excess,
1/2 or 1/3), RS 02501.095 and 404.434 (charging against the family benefit on the worker's
record, never carried over), RS 02501.030 and 404.435 (non-service months, grace year,
presumption), RS 00615.480/.482 and 404.412 (ARF at FRA, partial-deduction months count),
404.430(a)(2) (exempt amounts indexed to the AWI with a two-year lag), RS 02505.005 and related
(wages as SS defines them: 401(k) deferrals count, the employer match and §125 amounts do not).
"In practice W-2 box 5 plus net SE earnings" is inferred from those definitions, not read.

**Measured in the fork** (which implements the test; its other additions switched off where they
could apply: `withItemized="none"`, since alex+jamie has a mortgage and jack+jill too; no case has
a budget, and FL, CO and TN have none of the fork's state additions):
`fork-notes/phase5/et_issue_measure_2026-10-22.txt`, `et_issue_crosscheck_2026-10-22.txt`, and
for Jill a run the same day (65y11m with the test off and on, basis \$104,586.81 both; script not
kept). The fork's no-test pick for Pat equals stock `dev`'s (62y6m), so the two runs differ by
the test.

**Read in upstream's docs, used in the text:** `info/PARAMETERS.md:82` describes `other inc` as
"Other ordinary income (e.g. part-time work, consulting, royalties)"; `examples/Case_chris+pat.toml`
says Pat "continues working through 2028, retiring at 62".

**Not verified, kept out of the text:** the 2027 exempt amounts (normally announced in October,
recalled; POMS had only 2024-2026 when read); whether SSA's Statement estimates assume work to the
claiming age (recalled).

---

**Title:** Social Security earnings test: withhold benefits claimed before FRA while working

Owl documents that the SSA earnings test is not modeled and that users are assumed fully retired
before FRA (modeling-capabilities, `socialsecurity.py`, the paper). Three of the shipped examples
break that assumption: each pays a spouse Social Security before FRA in a year with wages well
above the exempt amount, so Owl pays benefits SSA would withhold. On `dev` `37afa2a`, run on
2026-10-22:

| Example | Who | Claims at | Year | Wages (nominal) | SS Owl pays that year (today's \$) | (wages − \$24,480)/2 |
|---|---|---|---|---:|---:|---:|
| alex+jamie | Jamie | 62y1m | 2026 | \$80,000 | \$10,140 | \$27,760 |
| alex+jamie | Jamie | 62y1m | 2027 | \$80,000 | \$10,140 | \$27,760 |
| chris+pat | Pat | 62y1m | 2028 | \$85,000 | \$9,858 | \$30,260 |
| jack+jill | Jill | 62y1m | 2028 | \$85,000 | \$11,562 | \$30,260 |

(The last column is a first-order size: nominal wages against the 2026 exempt amount. In every row
it is larger than the year's benefit, so for someone who works through the year the whole year is
withheld.) jack+jill is the case the user guide walks through.

It also reaches the claiming-age search. With `withSSAges=["Pat"]`, chris+pat picks Pat 62y6m:
entitlement from July 2028, in the year she earns \$85,000. The case says she "continues working
through 2028", and then July-December 2028 would all be withheld; had she stopped by June, it
would all be paid (the grace year, below). The plan has no way to say which.

**The rules** (POMS RS 02501.021-.110, RS 02505.005, RS 00615.480-.490; 20 CFR 404.412-.435):

- Before the FRA year, \$1 is withheld for every \$2 of earnings above the annual exempt amount
  (\$24,480 in 2026); in the FRA year, \$1 for \$3 above \$65,160, counting only the months before
  FRA. Nothing at or after FRA. The amounts follow the national average wage index.
- The worker's excess is charged month by month from the first month of entitlement, against all
  benefits on the worker's record (a spouse's benefit included), and is never carried into the
  next year. A spouse's own excess is charged only to the spouse's benefit.
- In the first year with a "non-service month" (a month of entitlement with wages not above the
  monthly amount, \$2,040 in 2026, and no substantial self-employment), those months are paid
  whatever the annual total: this is what lets someone stop working in June, claim in July and
  lose nothing.
- At FRA the reduction factor is recomputed without the months withheld, fully or partly (the
  ARF), so the withholding comes back as a higher benefit from FRA on; over a long life it can
  return more than was withheld.
- Earnings are wages as Social Security defines them, so 401(k) deferrals count (the employer
  match and cafeteria-plan amounts do not), plus net self-employment earnings.

**Proposed shape: in the SS streams, no LP change.** Earnings are inputs, so for a given claiming
age everything the test does (the dollars withheld each year, the crediting months, the higher
benefit from FRA) is a fixed function of that age. It can be applied where `zeta_in` is built,
before the LP sees it: taxes on SS, IRMAA, ACA and the cash flow then follow the net benefit with
no new variable, row or binary. Since #195 every `withSSAges` candidate is a fixed-age solve, so
the age search sees the test exactly, spousal charging and the ARF included; nothing else in the
optimizer has to know about it. The test needs a monthly entitlement grid for the year's charge
(own, spousal and their start months), which duplicates part of what
`compute_social_security_benefits` does annually; with no earnings it must give exactly today's
streams. Exempt amounts are set year by year from the wage index (20 CFR 404.430); Owl has no
wage index, so a projection at inflation is the simple choice (it overstates withholding a little
by leaving out real wage growth, over the five years at most between 62 and FRA).

**What it needs as input**, beyond what Owl has:

1. Earnings as the test counts them. `anticipated wages` is net of all contributions, so it
   leaves out 401(k) deferrals, which the test counts. And PARAMETERS.md suggests `other inc` for
   "part-time work, consulting, royalties": the first two are earnings for the test, and the same
   column also holds income that is not, so the test cannot read that column as it is.
2. When work stops within the last year: the grace year turns on it (above), and an annual
   wage cannot say it. A *months worked* count on the year's row is one way.
3. A default for existing cases: on, it moves the results of the three examples above.

**Stakes, measured in my fork**, which has the test (2026-10-22; the fork's other additions
switched off or not applicable to these cases; with the test off, the fork picks the same age for
Pat as `dev` does):

- alex+jamie: Jamie's \$20,612 (nominal) of 2026-2027 benefits are withheld, all of them; at FRA
  her benefit rises by 24 crediting months (from 70.4% to 80.6% of PIA, by the ARF). Spending
  basis \$228,619 → \$228,077 (−\$542/yr).
- chris+pat, Pat searched: the pick moves from 62y6m to 63y2m (entitlement from March 2029, after her
  last work year). At 62y6m with the test, \$6,945 is withheld and 6 months come back at FRA. Following the
  no-test pick costs \$50-65/yr of basis (local search \$50, exact LP \$63, loop \$65): small,
  but the no-test pick is a claim the test withholds.
- jack+jill, Jill searched: her best age is 65y11m with or without the test (after her work), so
  nothing changes there.

The dollar stakes on these examples are modest; the point is that Owl's answer to "should I claim
while still working?" is the one the earnings test exists to change. Three of the 18 shipped
examples were written with a spouse who claims at 62 while still working.

**Questions.**

1. Would you take the test in core, given the assumption is documented? If yes, on by default or
   opt-in like the `with*` options?
2. Earnings: a separate optional input (gross earnings as SS counts them, falling back to
   `anticipated wages` with a warning), or derived from `anticipated wages` plus the deferral
   columns (which also carry the employer match, which the test does not count)?
3. The stop month: a per-year *months worked* count, or something else you prefer for "when in
   the year does work end"?
4. Survivor benefits under the test (a survivor under FRA who works) follow the same charging
   rule but need the survivor stream on the monthly grid. In or out of a first version?

I have a working version in my fork (opt-in, with the two inputs above and its outputs in the
Summary and the worksheets); I would rather you design it your way. If a minimal patch on stock
`dev` would help, I can build one.

# Draft upstream design issue: federal itemized deductions (Phase 3 step 8), for the user to post

Status: draft, 2026-10-12; revised the same day after merging upstream `dev` `810a6cd` (MCP
health-care parameters). **Posted by the user as #185** (posting date not recorded here). Maintainer's
first answer, relayed 2026-10-15: more loop quantities cause cycling and prevent monotonic convergence;
he will run tests. Measurement against that: PROGRESS.md "Itemizing and loop convergence"; optional
reply `issue-185-reply.md`. Concept level (`phase3-plan.md` §2, lessons 2, 4, 7, 8;
`phase3-review.md` R5): the contract and the measured stakes, not the fork's code. Federal only;
NY itemizing and NJ line 31 stay in the fork (lesson 3).

## Where to post, and when (user's call)

Checked 2026-10-12 on github.com (pages read with WebFetch, which summarizes them; the issue and
Discussion numbers and dates are from those pages, not from the fork's notes):

- **#158 (NY recapture) is closed**: closed as completed by `fmateoc` on 2026-10-07, with no
  maintainer comment on the thread. The fork's notes still said "open, no reply". Lesson 9's
  "not before #158 has a reply" therefore no longer applies as written.
- **#175 is Discussion #177.** Last comment: ours of 2026-10-09 (`issue-175-reply-3.md`, posted;
  the notes said "user to post"), ending with three questions. No maintainer reply since; his
  2026-10-08 comment said he was nearly out of tokens for the week.
- Upstream `dev` moved to `810a6cd` on 2026-10-11 evening (three commits, MCP and explainer
  only; merged here 2026-10-12). It changes question 2 and the medical bullet (below).

Recommendation: a **new issue**, not a comment on #177. The proposal is a federal tax rule in core;
#177 is about Owl-budget, and our questions there are unanswered, so a comment would stack on
them (lesson 9). The issue links #177 only for the part that is a budget contract question (which
amounts a budget hands Owl). If you would rather wait for his answer on #177 first, nothing here
goes stale: the stakes are measured on synthetic couples and do not depend on today's date beyond
the loop noise already noted.

## What the text rests on

Verified on stock upstream `dev` (`git show upstream/dev:...`, 2026-10-12; `390f02f`, then
`810a6cd`, which touches none of the files cited in this list except as noted):

- `info/modeling-capabilities.md:29`: "Itemized deductions not modeled; standard deduction only."
  `papers/owl.tex:970` and `:1015` say the same for federal and state.
- `ui/Documentation.py:560`: "Mortgage interest is not deducted for income tax purposes, as
  **Owl** assumes taking the standard tax deduction."
- Debts: `type` is `loan` or `mortgage` (`ui/Documentation.py:197`, `hfp_io.py:79`);
  `debts.py` has the amortization (`calculate_annual_payment`, `calculate_remaining_balance`) and
  the payoff rule (`resolve_payoff_years`, #173), so the year's interest is payments minus the fall
  in balance. Upstream has no interest-by-year function; the fork's
  `get_mortgage_interest_array` is 83 lines on top of these.
- State income tax is an LP quantity (`st_T_n`, `_add_state_taxable_income`); Medicare and ACA
  premiums are computed per year; `setMedicalExpenses` only caps HSA withdrawals (its docstring).
- `810a6cd` (`17870e7`, `83ba462`): `other_medical_expenses` (= `setMedicalExpenses`) and
  `medical_inflation_excess` become MCP parameters of every parameter tool; the intake prompt asks
  for "yearly out-of-pocket qualified medical expenses (other_medical_expenses: dental, vision,
  co-pays, deductibles)" **only when anyone has an HSA balance** (`intake.py`); `explain_results`
  gains a `health_care` section (lifetime Medicare premiums with the IRMAA part, ACA net premiums,
  other medical expenses, HSA withdrawals) whose note says: "Other medical expenses sit inside net
  spending; they only cap tax-free HSA withdrawals." No change to the model (`plan.py`,
  `tax_federal.py` untouched).
- IRS Pub. 969 (irs.gov, read 2026-10-12 with WebFetch): HSA qualified medical expenses are
  "medical care (as defined in Code section 213(d))", the Schedule A definition, and expenses paid
  by a tax-free HSA distribution cannot also be deducted on Schedule A. Medicare premiums are
  HSA-qualified at 65+ (not Medigap); ACA premiums are not. So `other_medical_expenses` is, by its
  own description, the Schedule A medical amount, and upstream's HSA cap is the same 213(d) set.
- `withSeniorBonus` is `"loop"` (default) or `"optimize"` (`plan.py:2630`, `:4987`).
- Owl's default reverts to pre-TCJA in 2032 (`yOBBBA = 2032`, `plan.py:477`): MFJ standard
  deduction $17,160 instead of $32,200, today's $ (`tax_federal.py:97`, `:101`).

Measured in the fork (exact LP = `withMedicare="None"`, `withSSTaxability=0.85`; synthetic couple
born 1964, $1.5M tax-deferred, `maxBequest`, budget $80k core + $25k property tax, NY Yonkers or
NJ; plans start 2026-10-11):

- Lifetime federal tax saved, itemizing on minus off, today's $: `phase3-review.md` A.2 item 1
  (`gain_basis.py`). Bequest gains: PROGRESS.md "Phase 3 step 6", table 1. The no-mortgage
  statutory row is 0 in both.
- Rent / cash / mortgage: PROGRESS.md "Phase 3 step 6", table 3 (federal only: NY itemizing was
  on in both columns there). Mortgage path +11,418 (exact, as enacted) and +62,160 (2032); cash
  +0 and +2,160; rent unchanged. Cash minus mortgage under 2032: 1,312,913 − 1,145,286 = 167,627
  without, 1,315,073 − 1,207,446 = 107,627 with.
- Loop vs a binary mode: `phase3-review.md` B.2 R1 (step 6 probes; `near_switch.py`, five cases
  near the switch).
- Rules (P.L. 119-21, IRS instructions, Pub. 936): `phase3-plan.md` §3.1, verified 2026-10-10.

The fork follows the rule question 2 proposes since 2026-10-12: its claims read
`other_medical_expenses` when the budget has no `medical` line, never both (PROGRESS.md).

Inferred, not measured (stated as such in the text): with `medical_inflation_excess` > 0 the
medical amounts grow faster than the 7.5%-of-AGI floor, so the medical part of Schedule A grows
over the plan.

Not verified, and kept out of the text: whether turning the rule on by default would change any
existing upstream example (they have no mortgage and no budget; the fork's 18-example run compared
loop with optimize, not with off).

---

**Title:** Federal itemized deductions: max(standard, itemized) from amounts Owl already computes

Owl takes the standard deduction everywhere (modeling-capabilities: "Itemized deductions not
modeled"; the Debts docs: "Mortgage interest is not deducted ... as Owl assumes taking the
standard tax deduction"). Since OBBBA that is a good default for most retirees, but it fails in
two places that matter for planning: a household with a mortgage, and every plan under Owl's own
default reversion to pre-TCJA law in 2032, where the standard deduction roughly halves and SALT is
uncapped again.

**The idea.** Owl already knows three of the itemizable amounts:

- mortgage interest, from the Debts rows of type `mortgage` (payments minus the fall in balance,
  with the #173 payoff rule);
- the state and local income tax it computes itself, which goes into SALT;
- medical: the Medicare and ACA premiums it computes, plus `other_medical_expenses`, which since
  the health-care MCP work in 2026.10.11 is a household input in its own right. Its description (dental, vision,
  co-pays, deductibles) is the Schedule A medical expense: HSA "qualified medical expenses" are
  medical care as defined in IRC 213(d), the same definition (Pub. 969). What the HSA paid
  tax-free comes off, as Pub. 969 requires; Owl knows that too.

What is left is spending only a budget knows: property tax and cash charity (and medical lines,
if a budget itemizes them). That is a contract question for Owl-budget (#177): next to the
spending series, the budget would hand Owl the deductible part of it by category and year. With core vs discretionary lines, those amounts
have to follow the scale on the discretionary part under `maxSpending` (a deductible amount fixed
as a share of total spending is wrong as soon as the scale moves away from 1).

Owl would then take max(standard, itemized) each year, with the OBBBA details: SALT cap with its
phase-down until 2030 and $10k after, the $750k loan limit, the 7.5% medical floor, the 0.5%
charity floor for itemizers and the $1k/$2k charity deduction for non-itemizers, the senior bonus
kept by itemizers while the 65+ additions are lost. Under the pre-TCJA reversion, no SALT cap.
With `medical_inflation_excess` above zero, medical costs grow faster than a 7.5%-of-AGI floor
that keeps pace with inflation, so the medical part would grow over the plan (I have not measured
that; the stakes below have no medical expenses).

**Shape: loop only, no binary.** I first built it like `withSeniorBonus` (loop, plus an optimize
mode with a binary per year) and then removed the optimize mode, because it bought nothing. The
kink of max(standard, itemized) is continuous, so a branch taken from the previous iterate loses
at most the gap between the two branches, which is small exactly where the choice is close; and
the parts that depend on this year's AGI (medical and charity floors, the SALT phase-down) are
previous-iterate parameters in either mode. Measured: on the exact LP, loop and optimize gave the
same plan to the dollar in every case; on the full loop near the switch, within $260 of a $1.8M
bequest or $145 a year of spending, either way, at up to 23x the solve time. In loop mode the
itemized branch is a pair of upper-bound rows on the deduction column in the years the loop says
itemize (SALT's min(cap, property tax + state tax) is the two rows), and the standard branch is
the LP as it is today (plus the non-itemizer charity cap, in years with charity). No new column, no binary, nothing for local search to know about.

**Stakes** (synthetic couple born 1964, $1.5M tax-deferred, `maxBequest`, $80k core spending
plus $25k property tax, NY or NJ; exact LP; lifetime federal tax saved, today's $):

| | law as enacted | Owl's default (pre-TCJA from 2032) |
|---|---:|---:|
| homeowner, no mortgage | $0 (never itemizes) | $20k (itemizes 25 of 31 years) |
| same + $600k mortgage at 6.5% | $15k (9 years) | $87-89k (every year) |

As bequest at the end of the plan, row by row: $0 and $28-29k; $30k and $141k. In a rent / buy with
cash / buy with a mortgage comparison it adds $11k (as enacted) or $62k (2032 reversion) of
bequest to the mortgage path and almost nothing to the others; it narrows the gap to paying
cash, it does not reverse it (under the 2032 reversion, cash ahead by $168k without the
deduction, $108k with it). So under the law as written the effect is moderate and confined to
mortgages; under Owl's default reversion, leaving it out tilts every mortgage-vs-cash comparison
by tens of thousands of dollars.

**Questions.**

1. Would you take this in core, given the standard-deduction assumption is stated in the docs? If
   yes: on by default, or opt-in like the other `with*` options?
2. Medical: may Schedule A read `other_medical_expenses` (today, per `explain_results`, it "only
   caps tax-free HSA withdrawals"), less the HSA's tax-free withdrawals? If so, the intake would
   ask for it from everyone, not only HSA holders, and a budget's medical lines would have to be
   the same amount, not a second one, or it counts twice.
3. Should property tax and charity be part of the Owl-budget contract in #177, or inputs of
   their own on the Owl side until Owl-budget exists?

I have a working version in my fork (federal plus two state schedules I keep there); I would rather
you design it your way. If a minimal patch on stock `dev` would help, I can build one for the
federal part only.

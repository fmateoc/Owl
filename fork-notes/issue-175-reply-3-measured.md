# Draft reply on #175 (Owl-budget, third round), for the user to post

Status: **superseded, not to be posted** (2026-10-09). The user restarted the third reply at the
conceptual level the maintainer keeps (`issue-175-reply-3.md`); this measured version stays as the
evidence behind it. Answers the maintainer's reply of 2026-10-09 (ownership,
hooks, longevity, JSON vs Excel, sources, cost function). Numbers come from
`fork-notes/model-review/essential_stakes.py` on `claude/phase2-housing` (commit `5a4a12f`), run
2026-10-09; raw output in `fork-notes/model-review/essential_stakes_2026-10-09.txt`.

---

Thanks. Taking your points in order, then the cost function, where we have a prototype and numbers.

**1-2. Ownership and hooks.** Fine with you owning it. For the hooks: upstream's
`gen_spending_profile` builds `flat` and `smile` only, so an external profile needs a third
kind that Owl evaluates per horizon. Our fork's version is about 200 lines with docstrings
(`budget.py` plus `Plan._evaluateBudget`), with no LP change for shape-only profiles. The core/discretionary split
below needs one more small change, to the profile rows.

**3. The profile and longevity.** Two separate effects:

- *Horizon.* The survivor step sits at the first death, and a line can run "to the end of the
  plan", so the profile has to be evaluated for each horizon. That holds for `clone(expectancy=...)`
  and for each sampled lifespan. Evaluating a specification (lines with years, growth and a
  survivor share) does this; a frozen array doesn't.
- *What gives when the money runs short.* This is where the cost function and longevity meet.
  When the whole profile scales, a longer life or a bad sequence cuts every line by the same
  factor, rent included, and the plan always solves. With essential lines held fixed, discretionary
  spending absorbs the shortfall, and when even the essentials can't be paid the plan is
  infeasible. Under lifespan sampling, the share of infeasible draws is then the probability that
  the essentials can't be funded. Owl's stochastic spending already counts an infeasible
  scenario as a full shortfall, so nothing new is needed there. Numbers below.

**4. JSON and Excel.** Agreed that both are needed. We'd keep one schema with two serializations:
JSON as the canonical file and the MCP payload, and an Excel sheet as the view retirees edit,
with a round trip tested between them. Our fork already reads and writes the Excel side (an HFP
`Budget` sheet: name, type, years, amount in today's $, real growth, survivor share, and now an
`essential` flag). On sweeps: with the split, `maxSpending` returns the discretionary level directly,
so a sweep varies the inputs (rent vs buy, location, essentials), not the spending level.

**5. Sources and the years before retirement.** We checked what we could reach from here (the
proxy blocks bls.gov, FRED, ebri.org and fidelity.com, so these come from search results and
reprints, not the primary pages):

- BLS CE 2024, households headed by someone 65+: total $61,432, housing $22,193, transportation
  $9,538, healthcare $7,799. These match FRED's copies of the BLS series, as quoted in search results.
- Fidelity 2026 (released July 21): $185,500 for a single 65-year-old, $371,000 for a couple, up
  7.5% from $172,500. About 45% of it is Medicare Part B and D premiums, 48% other medical costs, 7% drugs.
  It assumes Original Medicare plus Part D and excludes long-term care. The 45% is what Owl already
  charges (`withMedicare`), so only about 55% belongs in a budget, and as a lifetime average it
  needs turning into amounts by age.
- EBRI, 2024 Spending in Retirement Survey: 31% of retirees said they spend more than they can
  afford (27% in 2022, 17% in 2020). The "3[1]%" in the pasted text is a footnote link that broke
  the number. EBRI asks about essential and discretionary spending separately, which supports
  your split.
- From memory, not checked: CE "housing" includes mortgage interest, which Owl takes from Debts,
  and CE "healthcare" includes insurance premiums, Medicare's among them. So CE averages can't be
  added to an Owl plan as they are. HRS's consumption module (CAMS), MEPS for out-of-pocket costs
  by age, and Blanchett's spending "smile" are the other usual references. CE also publishes tables
  for large metro areas.

The ten years before retirement fit as they are: Owl's plan starts today, wages fund spending,
and surpluses go to the taxable account. One gap: we found no payroll tax in Owl's source
(searched for FICA, OASDI and the 6.2% / 1.45% rates). Since *anticipated wages* are net of
contributions only, a pre-retirement budget has to carry Social Security and Medicare tax as a
line, or the working years overstate the cash.

**Cost function.** As you put it: `maxBequest` takes the budget as given and maximizes the
bequest; `maxSpending` fixes the bequest and scales spending. Splitting the budget into essential
and discretionary lines gives a third reading without a new objective:

- net spending each year = essential lines at their amounts + k times the discretionary lines;
- `maxSpending` maximizes k (the discretionary level) with the essentials as a floor;
- `maxBequest` at the budget is k = 1, and at the essentials alone it is k = 0, so the bequest
  there is the reserve above the core;
- the spending-bequest frontier you already have traces k against the bequest, starting from
  that k = 0 point rather than from zero spending.

In the LP this is the profile rows made affine: g_n - E_n = (g_0 - E_0) D_n / D_0, with
`spendingSlack` applied to the discretionary part only, and g_0 >= E_0 under `maxSpending`. No
binaries are added, and a budget with no essential lines gives the same plan as before (a test
checks it). One numerical lesson: written with dollar-sized coefficients (D_0 times g_n), HiGHS
called feasible plans infeasible; normalized to order-1 coefficients like the existing profile
rows, all solve.

Measured on our synthetic couple: born 1964, SS $3,000 and $2,400/month at 70, $300k taxable,
$150k Roth, NY. Exact LP (Medicare off, SS taxability 0.85), conservative rates, no conversions,
bequest 0. Budget in today's $: living $50k and rent $36k (the essentials when flagged; a survivor
keeps rent in full and 60% of living), travel $20k through 2044 and other $10k (discretionary).

| Tax-deferred | Life exp. | Budget scaled as a whole: first year, rent | Essentials fixed: first year, rent, discretionary k |
|---|---|---|---|
| $1.5M | 89 / 92 | $130,091, rent $40,373 | $132,680, rent $36,000, k = 1.56 |
| $1.5M | 95 / 98 | $126,296, rent $39,195 | $128,877, rent $36,000, k = 1.43 |
| $0.8M | 89 / 92 | $103,566, rent $32,141 | $101,256, rent $36,000, k = 0.51 |
| $0.8M | 95 / 98 | $102,320, rent $31,754 | $98,887, rent $36,000, k = 0.43 |

At $1.5M, `maxBequest` at the essentials alone (k = 0) leaves $1,532,151 to the heirs and at the
budget (k = 1) $576,022: those are the two ends of the frontier. At $0.8M the budget itself is
infeasible under `maxBequest`, which the k of 0.51 already says.

Longevity, with 200 Monte Carlo scenarios (`histochastic` from 1928-2024, seed 42) and lifespans
sampled from the SSA tables, `runStochasticSpending` as is:

- $1.5M: no scenario fails under either reading; median first-year spending $157,535 (whole budget)
  vs $163,285 (essentials fixed).
- $0.8M: the whole-budget reading solves all 200, by cutting rent with everything else.
  With essentials fixed, 9 of 200 (4.5%) cannot fund the essentials. In those same draws the
  whole-budget plans spend $86.6-92.9k in the first year, 75-80% of the budget, so rent is
  "cut" to $27-29k. In 8 of the 9 one spouse dies at 67-74 and the other lives to 83-100: a
  survivor still owes the full rent on one Social Security check.

So the split changes the answer exactly where it matters: what has to give, and how likely the
core is to be at risk. It costs nothing where money is ample.

What we'd not do in a first version: per-line elasticities or a utility curve. The weights would
drive the answer and users can't set them. The single discretionary scale, plus the slack you
already have, keeps the objective in dollars.

Our questions back:

1. Is the essential/discretionary split the shape you had in mind, or did you mean something more
   elastic (several priority levels, say)?
2. For the JSON: should the schema live in Owl's repository, since Owl reads it, with Owl-budget
   writing it?

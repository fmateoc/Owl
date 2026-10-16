# Draft upstream issue: the SS-taxability loop on a couple with most SS years in the phase-in

Status: **filed by the user as #193** (2026-10-16). Pointer comment for #185 below, **posted by the
user** (relayed 2026-10-16). Every number comes from stock upstream `dev` `10b9f72`:
`fork-notes/issue-ss-loop-repro.py` (output: `issue-ss-loop-repro-output.txt`, run twice with
identical output) and `fork-notes/model-review/ss-loop/` (`stock_repro_2026-10-16.txt`: Roth
59/41 on stock; `examples_ss_stock_2026-10-16.txt`: the 18 examples). The fork-only analysis
behind it (loop trace, the tie at the loop's own Psi, the NJ comparison) is in PROGRESS.md "Why
the NY + mortgage loop fails" and is not quoted here, because it ran on fork code.

Why file it although the maintainer is running his own tests on #185: user's rule (2026-10-16), a
concrete test case or new information gets filed regardless of the other party's own tests.

---

**Title:** SS taxability loop: plan $34-49k short of `withSSTaxability="optimize"` on a couple with most SS years in the phase-in, and stuck at the iteration cap when the LP has ties

On #185 you mentioned that adding to the loop causes cycling. I went back to the NY couple with a
mortgage whose loop failed in my itemizing runs, and it fails on stock `dev` (`10b9f72`) too, with
no itemizing involved. The cause is the SS taxable fraction, and the loop's plan is also well
short of the exact one. Self-contained repro attached (`issue-ss-loop-repro.py`, plain Python on
stock Owl, date frozen at 2026-10-15 so the numbers do not move).

**Case.** Married couple born 1964 (LE 89/92), $150k taxable, $900k/$600k tax-deferred and $75k
Roth each, SS $3,000/$2,400 a month at 70, a $600k 30-year mortgage at 6.5% taken in 2026 (its
proceeds counted as cash that year), flat net spending, `maxBequest`, NY, `conservative` rates,
the default 2032 reversion, every account 60/40. 22 or 23 of the 23 SS years are in the 50-85%
phase-in, in the loop's plans and the exact ones.

**1. The loop's plan is short by $34-49k of bequest** (today's $):

| case | default loop | `withSSTaxability="optimize"` | loop short by |
|---|---|---|---:|
| NY, spending $95k | 948,275 (24 iterations, 2-cycle, SS residual $13,562) | 988,448 (3 iterations) | 40,173 |
| NY, $100k | 728,034 (30, max iteration, $24,279) | 766,704 (3) | 38,671 |
| NY, $105k | 506,651 (30, max iteration, $26,411) | 544,961 (3) | 38,310 |
| NY, $110k | 283,374 (22, 2-cycle, $14,786) | 323,217 (3) | 39,843 |
| NY, $115k | 63,523 (30, max iteration, $9,599) | 101,321 (3) | 37,798 |
| NY, $105k, Roth 61/39 | 518,267 (20, 2-cycle, $2,779) | 552,010 (3) | 33,743 |
| NJ, $105k | 478,708 (20, 2-cycle, $2,214) | 527,310 (3) | 48,602 |

Where it comes from (NY $105k, Roth 61/39, where the loop settles; lifetime, today's $): the
exact model converts $852,005 instead of $708,796, front-loaded (2026: $232,555 vs $121,468; 2027:
$193,198 vs $123,868). Taxable SS falls from $1,041,214 to $631,966 and federal income tax from
$273,954 to $207,423. With `Psi_n` a constant in the LP, a dollar of income in a phase-in year is
priced at the bracket rate. In fact it also makes up to $0.85 of SS taxable, so the LP
under-prices exactly the income the exact model moves out of those years.

**2. Why it stops at the cap: the LP has ties at a fixed SS fraction.** All accounts have the same
mix at fixed rates, so a withdrawal can often move between years or accounts at no cost. Part 3
of the repro solves the pure LP (`withSSTaxability=0.85`, `withMedicare="none"`, NY $105k) and
then pins Joe's 2036 tax-deferred withdrawal $13k lower. The bequest is the same to the cent
($621,377.74), and the withdrawals move in 21 account-years, by up to $110,143. (Pinned $13k
higher instead, it costs $52.19.) The solver returns one vertex of that face, and the IRS formula
then gives each vertex a different SS fraction. So in the loop, the next `Psi_n` follows the
solver's pick, and the damped update never settles. Giving the Roth 61/39 instead of 60/40 is
enough to turn the cap into a 2-cycle with a $2.8k residual (table above; 59/41: 20 iterations,
$2,411).

**3. What a user sees.** The Summary reports "max iteration" with an objective error bar of
±$358 (0.07%) for the $105k case (±$523 at $100k, ±$404 at $115k). The bar measures the loop's
oscillation, not the distance to a consistent plan, which is $38k there. The SS residual
($26,411 over the horizon) appears only in the verbose log and in `plan.fixedPointResidual`.

**Not general.** On the 18 examples, `optimize` is within ±0.5% of the loop in 16, +10.0% on
`Case_john+sally`, and -0.7% on `Case_morgan`. It is as fast on a few and up to about 1,100 times slower on others
(686 s against 0.6 s on `Case_kim+sam-bequest`). The gap needs many SS years in the phase-in and income
the plan can move, as with large tax-deferred balances and SS claimed late. Local search (which sets `withSSTaxability="optimize"`) gets this case right: $545,434 at
$105k (repro, part 5).

**Questions.**

1. Would you surface the fixed-point residual (or at least the SS one) in the Summary next to the
   error bar? A plan that ends at "max iteration" with a $26k SS residual looks like a ±$358 plan
   now.
2. When the loop ends at the cap or in a cycle with a large SS residual, would a one-time
   re-solve with `withSSTaxability="optimize"` be acceptable, or a recommendation in the message?
   Here it took 3 iterations and a few seconds; on the examples it can take minutes, so maybe
   only as the message.

I can turn either into a patch on `dev` if you want one.

---

## Pointer comment on #185 (posted)

The NY + mortgage cases that hit the cap in my measurements above fail the same way on stock
`dev` with no itemizing: it is the SS taxability loop on an LP with ties, and the loop's plan is
also $34-49k short of `withSSTaxability="optimize"` on that couple. Details and a repro in #193.

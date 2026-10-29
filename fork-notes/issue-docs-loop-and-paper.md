# Draft upstream issue (mdlacasse/Owl): paper and docs, loop mode is self-consistent not optimal, and paper vs code drift

**Not filed yet.** Documentation only. No code change is proposed, except possibly the defaults question at the end.

## Recheck against upstream `dev` `226ff54` (2026-10-29)

**Superseded the same day by a full read of the paper: `fork-notes/paper-review-226ff54.md`** (finds more, corrects item 1 and the Tx2 row below; section D there compares the two).

Read against upstream's `papers/owl.tex` (`git show upstream/dev:papers/owl.tex`, not the fork's copy), `info/*.md` and `ui/Documentation.py`. "Fixed" means the paper now says what this draft says the code does; the code was re-read only where noted. **Most of the draft is obsolete; the text below this section must not be filed as is.** What is left is short enough for a small issue.

| Item | Status on `226ff54` |
|---|---|
| 1. Loop = fixed point, not optimum | **Mostly addressed, not in the paper.** `info/modeling-capabilities.md` (SC-loop row: "can settle on a fixed point that is self-consistent yet not optimal") and `ui/Documentation.py` ("cannot see that a little less income would drop an IRMAA bracket") say it, added 2026-10-24 (`241175c`). The paper's loop section (§"The Self-Consistent Iteration Loop") says a fixed point is required, that branch-and-bound is "not exact", and local search's "never worse than the loop ... improved 17 of 23 cases"; a grep for "not optimal", "not the best", "cannot weigh", "marginal cost", "torpedo" finds no statement that the loop does not price the marginal cost. The measurement table (on `a85ff76`, before local search, `residualTol` and many fixes) is stale and should not be filed. The defaults question is superseded by `breakpointMethod="local-search"`; `withMedicare` still defaults to `"loop"` |
| 2. Taxable bond/cash returns clipped | **Clip documented**: Eq. Tx2 now has `max(0, tau_kn)` and "Only positive returns are taxable: a loss on bonds or cash does not reduce income". Not stated: the consequence under variable rates (`E[max(0,tau)] > E[tau]`; price gains taxed before sale) |
| 3. Plan year is today's year | **Addressed**: §"Planning Horizon" says the horizon "runs from the current calendar year (year 0)"; `PARAMETERS.md` `start_date` too. The reproducibility consequence (same file, other result after Jan 1) is not stated; minor |
| 4. Roth cap combined (Ch. 7) | **Fixed**: "For couples, the cap applies to each individual's conversions"; solver options and constraint text say per individual |
| 4. IRMAA MAGI expansion | **Half fixed.** The `J_3` rows now match the code (no `e` term; "so `e_{n-2}` does not appear"; code re-read: `w`, `x` at -1, comment "Subtracting e here as well would add it a second time"). **Eqs. MedDecomp2/MedDecomp3 are unchanged**: `-e_(n-2)`, `-Σ[w_i1 + x]` and `-Σ(b - w + d)(...)` (signs flipped against Tx2 and `J_3`); they also lack `ā_i` and the `max(0, tau)` clip that `J_3` has |
| 4. Eq. (PI) basis | **Still wrong**: `Π_n = G_n - ½Σζ` with the AGI-basis `G_n`; the intermediate-variables entry says `Π_n = G^aca_n - ½Σζ` (full SS), which is what the code does (`plan.py`: "PI = MAGI_aca - 0.5*SS") |
| 4. AMO binaries | **Fixed**: §"Mutually exclusive transactions" says Owl no longer uses them; `amorepair.py` documented; `amoConstraints` etc. under "Retired" |
| 4. Decomposition / Benders | **Fixed**: no "benders" or "certified global"; `withDecomposition` under "Retired" |
| 4. Big-M 10^8, `3 B20` | **Fixed**: per-year `M` from the income ceiling; `bigM*` keys under "Retired" |
| 4. Survivor claimed in year of death | **Fixed**: chapters renumbered; `survivor_claim_age` described, no "year of death" claim found |
| 4. Lexicographic term incomplete | **Fixed** (§"Lexicographic tie-breaking": `eps(1+n)` on `x`, `eps` on `w_i2n`, `s_n`, the second individual's withdrawals, `f^s`; `1e-4` on `tss` and others); code not re-read |
| 4. Eq. Tx2 omits the clip | **Fixed** (see 2) |
| 4. Scenarios "drawn from the lognormal model" | **Fixed**: "drawn from the plan's stochastic rate model" |
| 4. Longevity: last-survivor horizon | **Still drifts**: §"Longevity risk" says the clone's "life expectancy is set to the drawn last-survivor horizon"; `stresstests.py` passes each person's drawn age (`clone(plan, expectancy=drawn_list[i])`, code re-read). Minor |
| 4. CVaR / efficient frontier framing | **Unchanged** in the commitment-LP section ("equivalent to minimizing CVaR", "Every frontier point is Pareto-optimal"). Perfect foresight is now said for the year-1 robustness view (§"Monte Carlo and stress testing") and implied for SS ages, not for the bases. A framing point, not an error; weakest item |

Also from `fork-review-2026-10-25.md` item 2 (upstream code the upstream paper did not describe): the formulation section now has the federal deduction added back (Eq. StateTI, explained), the SS exclusion through `t^σ`, and personal credits. **Still missing**: Ch. 2 §"State Income Tax" says "bracket widths and deductions are indexed to inflation through `γ_n`", while upstream's `taxes_state.toml` has `brackets_indexed = false` in 70 of 103 entries (#157); and it describes state taxable income from "federal ordinary taxable income" without the add-back; the change of state (#159) is not mentioned (grep for "move", "resid", "relocat", "change of state": nothing on it). The fork's `owl.tex` has its own text for all three (`git diff upstream/dev -- papers/owl.tex`).

**Remaining for a filing**: MedDecomp2/3 signs and `e` term; Eq. (PI) basis; Ch. 2 state indexing, AGI add-back and moves; one sentence in the paper's loop section (the docs already have it); optionally the longevity sentence, the bond-return consequence and the CVaR wording.

---

*Original draft (2026-10-04, on `a85ff76`/`c1e5619`), kept for the record:*

**Title:** Paper: say that loop mode returns a self-consistent plan, not an optimal one; correct places where the text no longer matches the code

---

**1. Loop mode returns a fixed point, not an optimum.** Chapter 3 ("The Self-Consistent Iteration Loop") presents the loop as resolving the nonlinear terms. Each iteration optimizes with the lagged quantities held constant, then recomputes them. At the fixed point the plan charges itself the right IRMAA, SS tax, NIIT, ACA premium and LTCG room, but the LP never sees their **marginal** cost. IRMAA cliffs and the premium-credit phase-out are invisible when choosing conversions. So is the SS "tax torpedo": taxable SS enters `_add_taxable_income` as the constant `Psi_n * zetaBar`, so a dollar of other income is charged its bracket rate and not the 1.5x or 1.85x it really costs. The same holds for the 3.8% NIIT, the OBBBA senior-deduction phase-out and the LTCG stacking room. A fixed point of this map is optimal only where the derivatives of the lagged terms are zero.

Measured on the shipped examples, all loop vs. one family switched to `"optimize"` (`maxTime=60` per MILP). This was run on a fork at upstream `dev` `a85ff76`. The fork's additions are opt-in except its NY benefit recapture, which applies to the two NY examples, cameron and robin. Those two were rerun on stock `dev` `c1e5619` and gave identical figures (cameron +0/+0, robin +0/+96). Objective: spending basis $/yr, or bequest $, today's dollars.

| Case | Objective | All loop | Medicare optimize | SS taxability optimize |
|---|---|---:|---:|---:|
| alex+jamie | spending | 228,574 | +1,229 | +111 |
| chris+pat | spending | 116,916 | +40 | +76 (max iterations) |
| jack+jill | spending | 102,577 | +0 | +208 |
| joe | spending | 93,044 | +374 | +121 (max iterations) |
| jordan+taylor | bequest | 1,530,120 | +19,368 | +0 |
| kim+sam-bequest | bequest | 1,917,624 | +2,504 | +9,124 |
| kim+sam-spending | spending | 185,393 | +27 | +219 |
| morgan | spending | 37,920 | +0 | +866 |
| robin | spending | 44,070 | +0 | +96 |

bill, cameron, dana and john+sally gave +0 in what was run. devon, helen+ruth, jon+jane and jordan+taylor-qcd were not run. No delta was negative. The largest are +1.3% of bequest (jordan+taylor, IRMAA) and +2.3% of spending (morgan, SS taxability). Medicare optimize took 0.1-62 s; SS-taxability optimize took up to 30 minutes, which is too slow for a default.

Suggested text: loop mode returns a self-consistent plan whose own income agrees with the costs it was charged, but it may leave value on the table where a cliff or phase-out sits near the plan's income. The `"optimize"` flags price those marginal costs exactly, at the cost of binaries. Whether `withMedicare` should default to `"optimize"` given these timings is a question for you.

**2. Taxable bond and cash returns.** `_add_taxable_income` taxes `max(0, tau_k)` of bonds and cash held in taxable accounts each year as ordinary income. That is total return, price changes included, so negative years are ignored. Under variable rates (historical, Monte Carlo) this overtaxes: `E[max(0, tau)] > E[tau]`, and price gains are taxed before any sale. Under constant rates the effect is small. Eq. Tx2 in the paper uses `tau_kn` and omits the clip. Worth stating as an assumption.

**3. Plan year is today's calendar year.** `_setStartingDate` ignores the year, and ages, RMD start, FRA and tax-year logic follow `date.today()`. The same case file gives different results after January 1, and a pinned seed reproduces the rates but not the plan. `info/PARAMETERS.md` documents this; the paper's assumptions don't.

**4. Paper vs code drift** (`papers/owl.tex` on `dev`):

| Paper | Code | Note |
|---|---|---|
| Roth cap: Ch. 5 per person; Ch. 7 "applied to the combined conversions" | per person (`_add_roth_conversion_constraints`) | Ch. 7 wrong |
| IRMAA MAGI expansion, Eqs. MedDecomp2/3 and rows `J_3`: `-e_(n-2)` and income terms with flipped signs | income before the exemption, no `e` term ("Subtracting e here as well would add it a second time") | paper wrong, code right |
| Eq. (PI): `Pi = MAGI - SS/2` with the AGI-basis MAGI (taxable SS only) | `MAGI_aca_n - SS/2` (full SS) | the intermediate-variables section is right; Eq. (PI) is not |
| "Adding binary variables z^x ... always contributes 4N_n binaries"; "coupled with binary variables excluding ..." | AMO binaries removed; post-solve repair (`amorepair.py`) | stale |
| MIP decomposition, sequential and Benders, "certified global optimum" (Sec. 3.9; table "benders_cut") | `withDecomposition` retired (`84811f1`, 2026-09-26) | stale |
| Big-M "about 10^8"; `M_n = 3 B20` for LTCG/NIIT | per-year ceilings from the portfolio plus fixed income (`_incomeCeiling`) | stale |
| Ch. 11: "survivor benefit assumed claimed in the year of death" | `survivor_claim_age` setting (Ch. 2 describes it) | Ch. 11 stale |
| Lexicographic term: `+eps` on `x` and spouse-1 withdrawals | `eps*(1+n)` on `x`; also on `w_i2n` and `s_n`; `1e-4` on `tss` | incomplete |
| Eq. Tx2: taxable-account interest uses `tau_kn` | `max(0, tau_kn)` | paper omits the clip |
| Stochastic spending scenarios "drawn from the calibrated multivariate lognormal model" | any configured rate model | imprecise |
| Ch. 10 longevity: "life expectancy set to the drawn last-survivor horizon" | each person's drawn age is passed to `clone` | code more correct than text |
| CVaR relation and "efficient frontier" | the commitment LP's optimum is the empirical quantile of the scenario bases at level `1/Lambda`, and each is a perfect-foresight optimum | the framing overstates |

These were found reading the 2026 `owl.tex` against the code at `a85ff76`, and are cited by equation label.

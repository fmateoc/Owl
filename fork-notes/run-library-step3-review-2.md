# Review of run-library step 3 as a whole (2026-11-02)

A full review of build step 3 of `fork-notes/run-library-design.md` -- both increments --
in two independent passes, as asked:

- **the own pass** (this session): the code read against the design and the model's own
  functions, with its own probes and checks;
- **the independent pass**: a reviewer agent with fresh context (nothing but the design,
  the code and the build's own claims), which ran its own probes, the tests and its own
  reading (`C:\Users\fmate\AppData\Local\Temp\opencode\qprobe*.py`; its full text is
  `step3-indep-review.md` beside the probes).

Scope: branch `claude/run-library-step3`, commits `7366cdee..f08a9250` -- the backend and
the pages (`view.py`, `compare.py`, `presets.py`, `store.py`, `results.py`, `ui/Library.py`,
`ui/Run.py`, `ui/Compare.py`, the launchers, `check_library_compare.py`), the P1-P14 fixes
of the first review (`fork-notes/run-library-step3-review.md`, folded in `4b4c13f1`), and
the second increment (`thresholds.py`, `export.cash_flow_split`, `library/agemap.py`, the
Run page's "Things to look at", Sankey tab and claiming-age map). Checked against design
sections 5, 7, 8.1-8.3, 9 (9.1/9.2), 10, 11, 14.1 (I3/I6/I7) and 14.3, `run_suite.py`'s
rules, PROGRESS.md's two step-3 entries and CLAUDE.md's bullets.

Findings are numbered **Q1-Q9** (Q1-Q6 from the independent pass, Q7-Q8 from the own pass,
Q9 from both). Both passes converged on Q1 and Q2 independently. Every finding carries a
probe or a file:line reference. **Q1 and Q3 were folded in on 2026-11-02 after this review**
(their entries say how); **Q2 and Q4-Q9 on 2026-11-02 too, with review 3's W5-W9**
("Disposition after review 3" at the end).

## How I checked

| What | How |
|---|---|
| The step-3 acceptance check | ran `fork-notes/synthetic/check_library_compare.py` myself: **9/9**, every figure matching PROGRESS (108,959 / 760,861 / 0 / 310,107; 67y0m+67y0m; -13.34%; 2 input changes; 28 years moved; re-solve all +0; d_pair -14,530, d_exact -15,672 resolved; thresholds 1 entry (irmaa); cash flow sources = uses in 28 years, 2027 at 974,971 both sides; age map 4 variants) |
| Test suites and counts | `.venv\Scripts\python -m pytest tests\library tests\ui tests\plan\test_thresholds.py` targeted runs green (own: 29 fast; independent: 265 passed, 1 skipped); `--collect-only` counts: the second increment adds exactly 36 test functions (19/10/3/4 as PROGRESS claims), the first increment 55 + 18 as P10's correction claims |
| I3 `thresholds.py` against the model | own probes `probe_step3_q.py` (gains basis side flip, NIIT gate, IRMAA top edge and sub-$1 gaps) against `tax_federal.mediCosts`/`irmaaTier`/`capitalGainTax`/`computeNIIT`, `tax_state.state_recapture`, `star.StarSchedule`; the independent pass read the same functions and plan.py's call sites and probed on a real solved plan (`qprobe2_gains_basis.py`, `qprobe2b_low_income.py`, `qprobe3_gates.py`) |
| I6 `cash_flow_split` | term-by-term against `Plan._check_cashflow_balance` (own pass) and against `budget_spending`/`_budget_amount_terms` (independent pass); the check script's 28-year identity on the synthetic baseline |
| I7 `agemap.py` | against `fork-notes/phase5/work_sweep.py`'s real `--json` format (`free`, `sweeps[].index`, `best`, `results` cells with `ages`/`value`/`tolerance`/`proved`); `qprobe5_agemap.py` over the real `work_sweep_chris+pat_bb_2026-10-26.json` and crafted rows |
| The P1-P14 fixes | each located and verified by both passes (`qprobe1_gitignore.py` incl. the CRLF + blank-line `.gitignore`, `qprobe4_apptest.py`/`qprobe4b_apptest.py` for the pages, AppTest and store probes for the zip, ordering and companions) |
| Score rule / noise rule / R3 / agreement | `view.py`/`compare.py` walked against `run_suite.py` (`_score_plan`, `score`, `group_table`'s `~` rule and `> 0.5` guard, `agreement`, `run_checks`, `EXACT_GROUP`) and CLAUDE.md's "Loop noise" / "Branch-and-bound gap" bullets |
| The pages | Streamlit AppTest probes (both passes): "Open" switching, result/year selectors across run changes, zip buttons, the claiming-age map section, quality-note rendering |

## Findings

### Should-fix

**Q1 (both passes). The 0%-gains-bracket entry measures `G_n + Q_n`, not the taxable income
the model prices the bracket on -- wrong distances, wrong costs, and entries on the wrong
side whenever ordinary income leaves deduction unused.**
The model's QDCG-worksheet basis is `G_n + e_n + max(Q_n,0) - ded`, `ded = sigmaBar_n` in
widening years and `e_n` in itemizing ones (`Plan._ltcg_tax_implied`, plan.py:8022-8033;
the widening rows plan.py:5488-5499: "a deduction that ordinary income leaves unused,
sigma_n - e_n, takes gains out of tax first (#205)"). `thresholds.py:119` uses `G_n + Q_n`
for the distance and feeds `capitalGainTax` unclamped gains. In a year with unused
deduction -- low ordinary income, gains carrying the year, exactly where the 0% bracket is
decided -- the report overstates taxable income by `sigmaBar_n - e_n`.

Own probe (`probe_step3_q.py`, stub: G 68k + e 10k + Q 32k, sigmaBar 40k, edge 98.9k):
the report lists "over the 0% edge by 1,100, cost 165" while the model's measure is 28,900
*under* the edge and owes $0 gains tax. The independent pass found the same on a real
solved low-income plan (13 of 25 years carry 10k-36k of unused deduction) and on a stub
where the report claims "5k under, cost 714" while the model's edge is 85k away. The tests
cannot catch it: `FakePlan` has no `e_n`/`sigmaBar_n`, and `test_the_0_percent_gains_bracket`
pins the G+Q basis itself. Fix: measure on `_ltcg_tax_implied`'s basis (widen-aware, gains
clipped at taxable), and pin it in a stub that carries the deduction.

**Fixed 2026-11-02.** `_gains_entries` now measures the QDCG line-1 basis
(`G_n + e_n + max(Q_n,0) - ded`, `ded` = `sigmaBar_n` in widening years and `e_n` in
itemizing ones, mirroring `Plan._ltcg_tax_implied`) and prices `capitalGainTax` with gains
clipped at taxable (`np.minimum(gains, income)`); `FakePlan` carries `e_n`, `sigmaBar_n`
and `_ltcg_wide_n`, and `test_the_gains_bracket_measures_the_qdcg_taxable_income` pins the
side flip (unused deduction: no entry; deduction used: "over by 1k"; itemizing year: `e_n`
deducted whatever the ceiling).

**Q3 (independent pass). A `work_sweep.py --json` row with no free person (fixed claiming
ages) crashes the Run page: `IndexError: tuple index out of range`.**
`work_sweep.decide` with every age fixed returns `free = []` and still scores the decided
cell (work_sweep.py:423, 436-439, 470), so real output contains a variant row with no
sweeps and no free names. `parse_scores` then builds `AgeMap(dimensions=0)` with cells whose
`ages` tuples are empty; `_age_map_chart` takes the one-free-person branch and indexes
`c.ages[0]` / `amap.free[0]` (ui/Run.py:180-184, agemap.py:53). Probes: `qprobe5`
("zero-free: dims 0 cells [()]; x_ages raises: IndexError tuple index out of range") and
`qprobe4b` (the page exception). The whole page below the caption dies, on load, whenever
the run folder's `scores.json` (or a picked file) contains such a variant and it is the
selected one. Fix: treat `dimensions == 0` as "nothing to sweep" (a caption, no chart), and
guard `x_ages`/`y_ages`; add a regression test with a crafted zero-free row.

**Fixed 2026-11-02.** `_age_map_chart` treats `dimensions == 0` as "nothing to draw" (a
caption, no chart), and `x_ages`/`y_ages` skip cells with no age tuple. Regression tests:
`test_a_variant_with_no_free_person_sweeps_nothing` (test_agemap.py) and
`test_a_work_variant_with_fixed_ages_draws_nothing_and_does_not_crash`
(test_library_pages.py, the page end to end with a crafted zero-free `scores.json`).

### Minor

**Q2 (both passes). The NIIT line's exposure gate reads `I_n` only, so a year whose net
investment income is gains or qualified dividends alone is never reported.**
`thresholds.py:322-323` skips `I_n[n] <= 0`, but `computeNIIT` charges 3.8% of
`min(MAGI - threshold, I_n + Q_n)` (tax_federal.py:1289). Own probe: MAGI 260k, I=0,
Q=50k -> the model charges $380/yr and the report lists nothing; the independent pass got
the same (MAGI 252k, Q=60k -> $76 charged, no entry). A condo-sale or all-equity year is
exactly this shape. Fix: gate on `I_n[n] + Q_n[n]` (or on the computed cost).

**Q4 (independent pass). A result with quality notes shows the first note twice.**
`quality_line` returns `notes[0]` into the "Quality:" caption and the loop below then shows
every note as a `st.warning` (ui/Run.py:294-296; `qprobe4b` (J) shows identical texts).
P14's fix covered the *unsolved* case only. Fix: caption "settled"/"not settled" without
echoing the first note, or drop the first warning.

**Q5 (independent pass). Three drifts between what is claimed and what is checked or
quoted.**
(a) `check_library_compare.py`'s docstring says check 7 verifies "every entry inside its
band"; the code checks only `near_band_fraction` and the schema (lines 177-179) -- an entry
outside its band would pass. (b) PROGRESS says the threshold tests "pin every boundary,
side, distance and cost against the model's own constants and cost functions": the
recapture *cost* is unpinned (test_thresholds.py:203-218) and the ACA cost is only asserted
`> 0` (:188). (c) PROGRESS's quote of `run_suite.py`'s comment ("did not settle in 138 of
153 runs") drops the qualifier -- the comment says "138 of 153 **unsettled** rates-exact
runs" (run_suite.py:98).

**Q6 (independent pass). I3's marketplace kind omits the 100%-FPL line.** The entries list
the applicable-table breakpoints and the Medicaid line (thresholds.py:209); where the state
has no Medicaid expansion (`medicaid_n < 1`) the premium tax credit starts at 100% FPL and
the gap below it is a priced cliff (`acaCosts`, gap="exact"). The design says "the
marketplace subsidy limits". NY (138%) is unaffected; declare it as a known limit or add
the `1.0` breakpoint where `medicaid_n[n] < 1`.

**Q7 (own pass). I3's IRMAA "cost of closing the gap" is $0 at the top-tier edge, and at
gaps below the $1 slack -- and PROGRESS's "a crossing that costs nothing here is not listed"
holds only for the `aca` and `niit` kinds.**
`premiums()` evaluates with `slack=1.0` (thresholds.py:78), and `irmaaTier`'s top tier
*includes* its edge (tax_federal.py:402-403), so `at_edge` is priced inside the top tier and
`across` with it: the cost of the largest surcharge reads $0.00 on both sides of the top
edge. A gap at or below the slack also prices $0 at the lower edges. Probe
(`probe_step3_q.py`): "2,000 over IRMAA tier 5" -> `('IRMAA tier 5', 'over', 2000, 0.0)`
where the tier step is $581/yr per person; "0.50 over IRMAA tier 1" -> `('IRMAA tier 1',
'over', 0, 0.0)` where the step is $1,148/yr (a $2,000 gap prices correctly at 2,296.80 for
the couple). Only `aca` and `niit` filter zero-cost entries (`_gains_entries`,
`_irmaa_entries`, `_recapture_entries`, `_star_entries` list them at $0). Fix: price
`at_edge` on the lower side of the edge (e.g. `edge - slack`), and either filter $0-cost
entries of every kind or reword PROGRESS.

**Q8 (own pass). `view.objective_value` is not `Plan._objectiveValue` under `maxBequest`,
though its docstring and PROGRESS's P9 note say it is.**
`Plan._objectiveValue("maxBequest")` is `self.bequest` = `max(0, accounts - remaining
debt)/gamma` (plan.py:9409-9416), and the LP objective itself is the accounts only
(`_build_objective_vector`, plan.py:6111-6116); `view.objective_value` returns
`final_bequest_today` = `(accounts - debt + fixed_assets_bequest_value)/gamma`
(export.py:893-902, 1030) -- the home is added and the `max(0, ·)` clamp dropped
(view.py:293-308). For `maxSpending` the two agree exactly (`g_n[0]`), so the P9 fix's real
target (the 9x understatement with essential lines) is solved; for `maxBequest` on a
household with a home the tolerance is `gap x (bequest + home)`, and the claim "the value
the solver proved bounds on: `Plan._objectiveValue`" is wrong. Fix: name the value actually
used (the reported bequest) in the docstring and PROGRESS, or return the LP objective's own
value. (The independent pass verified "gap x objective" against the tests, which stub
summary.json and cannot see this; the two passes disagree here.)

**Q9 (both passes). P13's clearing of `library_base_run_id` misses routes where a case
becomes current.** The fix clears the mark in `createCaseFromFile`, `createNewCase`,
`openCaseFromPlan` and `switchToCase` (sskeys.py), but `switchToCaseName` sets
`currentCase` without clearing (sskeys.py:181-184) -- `owlbridge.runAllCases` switches
through every case with it, so an interrupted run-all leaves a different case current with
the stale mark -- and `copyCase`/`deleteCurrentCase` change the current case without
clearing either (independent pass). The next "Save the current case" then claims the wrong
parent and change summary, which is the exact failure P13 set out to close. Fix: clear in
`setCurrentCase` (or in `switchToCaseName`, `copyCase`, `deleteCurrentCase`).

## P1-P14 disposition (first review's fixes)

Both passes verified every fix; all fourteen are present, correct and tested. P1's
sentinel-file probe was re-run end to end on the real repository and on a scratch repo with
the real `.gitignore` shape (`src/...` refused, `otherFiles/library` allowed); P2 was
re-probed with AppTest; P4's four-distinct same-day companion lookup; P5's cached zip with
`.requeue-*` skipped and a vanished file named; P6 fifty cents; P7's ACA deferral; P9's
gap x objective (see Q8 for the maxBequest nuance); P10's counts re-derived from the diff
(55 + 18; 19/10/3/4); P11's `library.json` order. **P8's rejection is correct**:
`**Branch-and-bound gap:**` exists inside CLAUDE.md line 87's "Loop noise" bullet and the
sharpened citation names it accurately. P13's residual routes are Q9.

## Verified as sound

- **The noise rule (R2) and its direction** (`b - a` throughout): proved pairs judged by
  both results' tolerances (`max`), unproved by the 1% band of the reference, the mixed pair
  by the stricter, the $0.50 guard; matches `run_suite`'s `~` rule.
- **R3's leads/trade-off rule** in every sign combination (the first review brute-forced it;
  unchanged since).
- **The score rule** (`discretionary_year1` -> spending basis -> final bequest) matches
  `_score_plan`/`score`/`score_label` exactly; `home_at_end` = `final_bequest_today -
  final_bequest_savings_today` = run_suite's `home_at_end_today`.
- **The agreement check** term for term (`spread + four error bars`; the zero-difference
  edge is run_suite's own behaviour), with P4's and P7's fixes.
- **The `decision_exact` fingerprint** (`loop` + Medicare off + SS 0.85 + LTCG optimize) =
  `run_suite`'s EXACT_GROUP, and the declared deviation is worded consistently in
  `presets.py`, `view.py`, `compare.py`, the Compare page, PROGRESS and the amended design
  8.1.
- **I3's other kinds**: IRMAA (tax-year MAGI vs the premium year's thresholds exactly as
  `mediCosts`, exposure-gated, right deflators; see Q7 for the cost at the edges), the SS
  bands (PI = `MAGI_aca - 0.5*SS` as `compute_social_security_taxability`), the marketplace
  prices through `acaCosts` in the plan's own gap mode, the NY recapture exactly as
  `_state_recapture_implied`, the Enhanced STAR lag/limit/cost (`implied_credit`'s own
  `<=`), the NIIT math (see Q2 for the gate).
- **I6** mirrors `_check_cashflow_balance` term for term (10 lhs, 9 rhs terms; the Roth
  conversion pair nets to zero; `budget_spending` sums to `g_n`), sources = uses on solved
  plans (28 years on the synthetic baseline; the check's rounding tolerance is right for
  whole-dollar rows).
- **I7** parses the real work_sweep format (4 variants on the real file), drops failed
  solves, falls back to the 1% band for unproved cells, groups ties at the larger of the two
  cells' tolerances (R2 per cell), marks the decided pair; the map shades only the scored
  cells (a declared deviation).
- **The second increment's wiring**: `plan_to_dict` writes `thresholds`/`cash_flow` and the
  new `by_year` fields; `plan_metrics`' `discretionary_year1`/`essential_year1`;
  `plan_convergence`' `objective_error_bar_today_dollars`; the run page reads the durable
  files alone (D7).
- **Section 10**: the localhost guard, the launcher defaults, the `check-ignore` refusal
  (P1's fix), and the pickle policy as built.
- **Counts and claims**: test counts exact (55 + 18; 19/10/3/4); the scope calls (exactly
  two results, `NEAR_BAND` 5%, `scores.json` from the run folder with a picker,
  `decision_exact` = the exact model) match the code; the four declared deviations are real
  and worded as built; "sources = uses", "worst rounding 2.00", "974,971 both sides",
  "1 near a threshold (irmaa)" all reproduced by the acceptance check run here.

## Checks

- `fork-notes/synthetic/check_library_compare.py`: **9/9**, before the fixes and again after
  them (every figure unchanged).
- Targeted suites green in both passes (`tests/library`, `tests/ui`,
  `tests/plan/test_thresholds.py`); after the fixes: 54 passed over the three touched test
  files (the three new regression tests among them); flake8 and ruff clean on the six
  touched files.
- Full suite: `.venv\Scripts\python -m pytest -q -n 4` → **3881 passed, 2 skipped in 760 s**
  before the fixes (matching PROGRESS's claim exactly) and **3884 passed, 2 skipped in 823 s**
  after them -- the three new regression tests. The two skips are the environmental ones:
  the unlicensed MOSEK and the POSIX-only tzset test.

## Disposition after review 3 (2026-11-02)

The open items, fixed on `claude/run-library-step3` together with review 3's W5-W9
(`run-library-step3-review-3.md`). Every code change has a regression test; the threshold
tests were also run against the code as committed before the fix and fail there.

- **Q2** `thresholds._niit_entries` gates on `I_n + Q_n`, the income `computeNIIT` charges;
  its threshold comes from `tx.niitThreshold`, and the note now reads "3.8% of the smaller of
  the investment income and the MAGI above the line" (review 3, W7). Test:
  `test_the_niit_line_counts_gains_only_investment_income` (MAGI 260k, gains 50k, no
  interest: listed, cost 3.8% x 10k).
- **Q4** the Run page's caption reads "Quality: settled" or "Quality: N problem(s), below";
  each note is shown once, as a warning. `test_the_quality_line_warns...` counts it.
- **Q5** (a) every entry now carries `boundary_today_dollars` (same deflator as its
  amount), and check 7 verifies amount <= band x boundary
  (`test_every_entry_carries_its_boundary_and_sits_inside_its_band`); (b) and (c) PROGRESS
  corrected in place (the costs pinned are IRMAA, gains, NIIT and STAR; "138 of 153
  unsettled rates-exact runs", the quote of `run_suite.py:98`). Three garbled "§" signs in
  PROGRESS restored on the way.
- **Q6** declared as a known limit in `_aca_entries`' docstring (NY expanded Medicaid: no
  effect here).
- **Q7** IRMAA crossings are priced outside the \$1 slack (`edge - 2` against
  `edge + max(gap, 2)`), so the top tier and sub-slack gaps cost the full step
  (`test_the_top_tier_and_sub_slack_gaps_are_priced_at_the_full_step`); every priced kind
  now drops a \$0 crossing (`test_a_crossing_that_costs_nothing_is_not_listed`: an enhanced
  STAR credit equal to the basic one).
- **Q8** `view.objective_value` under maxBequest is `final_bequest_savings_today`, which
  is the LP objective (`Plan._build_objective_vector`: the accounts after the heirs' tax),
  not the final bequest with the home; the docstring says what each objective's value is.
  This goes beyond the "docstring only" first proposed: the value itself was wrong.
- **Q9** the "edited from run X" mark lives in the case's own dictionary
  (`sskeys.setRunBase` / `runBase`), so it follows that case through every switch, copy and
  delete; the route-by-route clearing is gone. Tests: `TestTheRunBaseFollowsItsCase`.

# Phase 3 review: step 6, then the whole phase (2026-10-11)

Fork-only note. Review of `e634c81` (step 6, the user's measurement commit) and of everything
Phase 3 added since `066b8d6` (steps 1-5 and their review fixes), asked for before step 7 (docs)
and step 8 (upstream). Measured on this branch the same day as step 6 (plans start 2026-10-11,
so step-6 numbers reproduce to the dollar: NY $20k exact 1,225,376, NJ 1,262,557, NY $25k
1,007,955, NJ 1,033,578). Scripts and raw output: `fork-notes/model-review/phase3-review/`
(`ny_item_off.py`, `gain_basis.py`, `loop_vs_opt.py`, `near_switch.py`, `resid_check.py`;
near_switch ran on `e634c81`'s code, the others on the reviewed tree, where plans are unchanged).

Baseline before any change: full suite on `e634c81`, **3168 passed, 1 skipped** (8:30).

---

## Part A — step 6

### A.1 Checked and correct

Every number in PROGRESS.md "Phase 3 step 6" tables 1-3 was recomputed from
`phase3_step6_2026-10-11.txt` (differences and percentages): all match. The binary-count table
matches the log. The LS "no slowdown" claim holds for the probe cases (65.7/66.6, 47.6/36.8,
93.6/87.6, 116.7/115.2 s none/optimize).

### A.2 Corrections

1. **In-model vs first-order compares two different quantities.** §3.2's first-order numbers are
   lifetime tax saved (sum of today's $); step 6's "in-model gain" is the final bequest, which
   also carries the growth of every dollar saved to the end of the plan. Same day, same cases,
   exact LP, lifetime tax saved in-model (`optimize` minus `none`, sum of `T_n + st_T_n` over
   `gamma_n`):

   | case | first-order (§3.2) | in-model tax saved | in-model bequest gain (step 6) |
   |---|---:|---:|---:|
   | NY + $600k mortgage, statutory | 17,977 | 15,073 | 30,385 |
   | NJ + $600k mortgage, statutory | 15,735 | 15,478 | 30,385 |
   | NY $25k, 2032 reversion | 22,431 | 19,979 | 29,093 |
   | NY + mortgage, 2032 reversion | 93,100 | 87,377 | 140,997 |
   | NJ $25k, 2032 reversion | 21,449 | 20,453 | 27,934 |
   | NJ + mortgage, 2032 reversion | 87,801 | 88,708 | 140,995 |

   So the LP response does **not** multiply the value: on the like-for-like measure the in-model
   saving is 84-101% of the first-order estimate. The 1.5-1.7x ratio behind "the LP response
   multiplies the mortgage cases" compares bequest with tax; the gap between the two measures is
   the growth of the saved tax to the plan's end (inferred: the tax saved itself is lower
   in-model, not higher). "The in-model numbers supersede
   §3.2" holds only with the measure named; both measures are useful (tax saved for "how much
   deduction", bequest for "what it is worth to the plan").

2. **The NY-itemizing attribution in table 2 rests on a different recipe.** The 2026-10-07 table
   (+$62,830 exact / +$46,703 LS) came from `housing_stakes.py`: `maxRothConversion = 0` (no
   conversions), `withMedicare = "None"` even in LS mode, `netSpending = 80`. Step 6's `nynj` has
   conversions, Medicare in LS, and no `netSpending`. The "cuts the NJ advantage by ~$25k exact
   / ~$5k LS" therefore mixes recipe and dates. Same day, same recipe, NY itemizing switched off
   (a test-only patch: `Plan._st_item_candidate_years` returning `[]`; NY itemizing has no
   option of its own, see B.2 R2):

   | property tax | method | NY, itemizing on | NY, itemizing off | NY itemizing worth | NJ − NY on | NJ − NY off |
   |---|---|---:|---:|---:|---:|---:|
   | $20k | exact | 1,225,376 | 1,198,279 | +27,097 | +37,181 | +64,278 |
   | $25k | exact | 1,007,955 | 969,320 | +38,635 | +25,623 | +64,258 |
   | $20k | LS | 1,101,591 | 1,095,736 | +5,855 | +41,083 | +46,938 |
   | $25k | LS | 877,984 | 866,838 | +11,146 | +35,792 | +46,938 |

   Lifetime NY + Yonkers tax (today's $), off -> on: exact 37,978 -> 23,316 at $20k and
   38,051 -> 15,979 at $25k; LS 42,690 -> 39,517 and 42,690 -> 36,680. NJ LS rows are step 6's
   (same day; node caps make them repeatable). The LS "on" rows reproduce step 6 exactly.

   Reading: NY itemizing cuts the NJ owner's edge by $27-39k exact but only $6-11k under local
   search; the two methods disagree on its value by a factor of 3-5, so its size is unresolved by
   the Phase 1 rule. Both agree on its sign, and on NJ staying ahead ($26-41k with NY itemizing).
   The step-6 "~$25k exact / ~$5k LS" lands near the exact and LS values at $20k, but by chance:
   that comparison did not isolate NY itemizing.

3. **The `zmed` family-vs-free comparison in the `med` group is vacuous.** `localsearch.FAMILIES`
   and `ALWAYS_FREE` are read only by `LocalSearch` (`localsearch.py:133`, `:198`); the `med`
   runs use the self-consistent loop, so both rows ran the same solve (both 486 nodes, same state
   tax). Only the NY local-search row (`zmed_family_ls.py`, 1,526 vs 519 nodes, same bequest
   965,406) measures the placement. The conclusion (keep `ALWAYS_FREE`) stands on that one row;
   drop "and 92.3 s vs 91.8 s in the maxSpending loop" and the matching sentence under "Open".
4. **The `med` group recorded no objective.** Its rows come from an earlier `report()` (no
   "bequest"/"spending" prefix in the log) that printed the estate, 0 for a no-bequest plan. So the
   loop-vs-optimize comparison under `maxSpending` with a medical line is unmeasured there
   (B.2 R1 has it).
5. **"`withItemized="optimize"` is cheap"** omits two rows of the same log: the cash variant
   under the 2032 reversion (0.1 -> 3.7 s) and the `maxSpending` medical case (exact 15.1 ->
   19.7 s; full loop 92.2 -> 120.7 s, +31%).
6. **Block sizes are not free counts.** "`zi` free in only 4 years" reads the size of the `zi`
   block, which is the number of candidate years; how many are free is `FIX_n` (not logged).
7. **The raw log keeps superseded runs unlabelled**: a housing block at rent $48k / home $800k,
   one with other balances (rent 465,610, cash infeasible), and an HSA run at property tax $39k
   (infeasible) precede the runs the tables use. The `nynj` header says "maxBequest at
   netSpending 80" while the recipe sets none (the code comment is right). Label or drop them.

---

## Part B — the whole phase

### B.1 Fixed in this commit (no plan changes except where said)

- **Explain registry.** `CONSTRAINT_FAMILIES` is the contract ("adding a constraint family
  requires one entry"); step 3 and step 5 added 15 tag families without entries, so the
  federal big-M gates (`item_salt_gate`, ...) would have surfaced to users as policy
  constraints (unknown families default to policy). Registered: federal itemized rows (policy:
  SALT paid, floors, non-itemizer charity; structural: `item_deduction`; artifacts: gates and
  claims) and NJ `state_medical_deduction`. Upstream's own `senior_bonus_*` and the fork's
  pre-Phase-3 NJ exclusion tags are also unregistered; left as they are (not Phase 3).
- **NJ line 31 in the loop's convergence test.** `NJMF_n` / `_nj_medl_n` are loop parameters,
  but their moves were not in the residual that decides convergence: a plan whose line-31 floor
  still moved could be called converged. Added (floor move where paid clears one of the two
  floors; flag flips by |paid − floor|), as for NY's floor.
- **Federal medical moves counted premiums nowhere.** Step 5 put Owl's premiums (less HSA
  distributions) into the federal claim rows and floor flags, but the loop residual still
  measured medical paid as the budget lines alone. Now the same amount as the rows.
- **Fixed-point residual** (Summary): NY had a "state itemized" entry; federal itemizing and NJ
  line 31 had none, though both carry loop parameters (floors, SALT cap, branch). Added
  "itemized" (deduction taken less max(standard, itemized) at the plan's own AGI, years with
  positive taxable income) and "state medical". Checked on four plans (NY mortgage exact
  loop/optimize, NJ medical full loop, FL mortgage full loop): both read under $0.05.
- **`_fix_dominated_itemizing`** pinned `zmedf` from the budget line alone; the claim rows count
  premiums less HSA distributions since step 5. Where the line alone is below the floor and
  premiums lift it above, the re-solve lost the medical claim, its objective fell, and the fix
  was dropped silently. Read, not run.
- **One helper, not two:** `_state_itemized_terms` was a copy of `_item_terms`; removed.
  `_setup_federal_itemized` re-implemented `tax_federal.standard_without_bonus` inline; it calls
  it now (the function had no caller in `src`).
- **Data keys the code did not honour** (NY `itemized`): `income_taxes` (refused if true),
  `salt_cap` (always 0, its code path untested), `mortgage_limit` (read only as "> 0"; the limit
  was the hard-coded pre-TCJA rule). Removed from the data, `StateItemizedParams` and the
  parser; the TOML header now says the state's total is Schedule A under the IRC as before TCJA
  (property tax uncapped, $1M mortgage rule, income taxes out). An unknown `itemized` key is now
  refused instead of ignored. The per-field year copy (8 lines, twice) is one `_copy_year`.
- **`nch`** was created as an empty block whenever claim columns existed; now only when a year
  has a non-itemizer charity column (the step-6 note).
- **`_scSolve`** (upstream's function) carried 70 inline lines of fork residual code; moved to
  `_itemized_sc_moves`, one call in `_scSolve`. Less merge surface, same arithmetic.
- **Comments that narrate the fork's review history** ("step-5 review: ...", "Phase 3 step 3")
  rewritten to state the behaviour; upstream comments describe code, not its history.

### B.2 Recommendations that need a decision

**R1. Drop `withItemized="optimize"`.** It is the largest part of the phase (claim columns
`isalt`/`ich`/`imed`/`nch`, binaries `zi`/`zch`/`zmedf`, the free set `FIX_n` and `ITEM_WINDOW`,
`_fix_dominated_itemizing`, the "itemizing" local-search family, `_add_federal_itemized_cols`;
`_add_federal_itemized_cols` alone is 96 lines and `_fix_dominated_itemizing` 60, plus the
optimize branches of the setup, aggregation and checks; 18 of the 33 tests in
`test_itemized.py` run it), and I did not find a case where it pays:

- 18 examples, each with its own options, `optimize − loop`: from −$46.80 (`Case_helen+ruth`)
  to +$2.49 (`Case_kim+sam-spending`); 13 identical to the cent. `Case_morgan` 0.3 -> 5.6 s.
- Step 6: loop = optimize to the dollar in every probe case, both laws.
- Near the switch (`near_switch.py`: five synthetic cases with 0-4 itemizing years, FL/NY/NJ,
  mortgages and charity/medical lines, x `maxBequest`/`maxSpending` x exact LP / full loop, each
  under loop, optimize, and optimize at gap 1e-7): exact LP, optimize = loop in all 10. Full
  loop: optimize ahead in two `maxBequest` cases (+$260 of $1.82M, +$45 of $1.29M bequest),
  behind in three `maxSpending` cases (−$43 to −$145 a year of spending), equal in the other
  five; gap 1e-7 changes one of them (−$43 -> −$59). Time: up to 23x slower (`maxSpending` NJ,
  exact 0.2 -> 4.5 s; full loop 1.5 -> 35 s).

Why (inferred, consistent with the runs): the kink of max(standard, itemized) is continuous
(plan §5 step 3), so a branch taken from the previous iterate loses at most the gap between the
two branches, which is small exactly where the choice is close. And `"optimize"` adds only the
branch choice: the MAGI-dependent parts (medical and charity floors, the SALT phase-down) are
loop parameters in both modes (`FEDMF_n`, `FEDCF_n`, `FEDSC_n`). Upstream's `withSeniorBonus`
optimize mode, by contrast, puts this year's MAGI into the LP. Under local search,
`_applyBreakpointOptions` turns `withItemized` to `"optimize"`; without it, the search would
keep the loop's branch and still see the deduction in every restricted solve (not run). Cost of keeping it: the code above, binaries in every
itemizing plan, and a mode that needs its own repair (`_fix_dominated_itemizing`) to be no worse
than the loop. If kept, D4 (household files on `"optimize"`) has no measured benefit to justify
it. **Recommended: remove; keep `"none"` / `"loop"`.**

**R2. Put NY itemizing and NJ line 31 behind the same switch.** Federal itemizing has
`withItemized="none"`; NY itemizing and NJ line 31 are always on, so no run can measure them
(A.2 item 2 needed a code patch) and `"none"` is not "today's plans" for a NY owner. One option,
"itemized deductions: none / loop", covering every schedule, gives the baseline step 6 lacked
and matches upstream's one-switch-per-feature style.

**R3. One mechanism for max(0, paid − floor).** Three exist for the same term: NY uses a binary
`zmed` (28-31 per NY plan under local search, 31 under `maxSpending` with a medical line);
federal loop mode and NJ line 31 use a loop flag from the previous iterate (no binary); federal
optimize mode uses `zmedf`. The flag form needs no binary; its lag now shows in the loop
residual and the fixed-point residual (B.1). With R1, NY's `zsi` could also follow the loop rule (branch from the previous iterate), and
Phase 3 would add no binary in loop mode at all. Not measured yet: NY `zsi`/`zmed` vs a loop
rule on the `maxSpending` medical case (15 s exact with 62 binaries).

**R4. Merge upstream `dev` 2026.10.11 (medical inflation, `390f02f`) before step 7.** It
conflicts only in `CHANGELOG.md`. It lets Medicare, ACA and `setMedicalExpenses` amounts grow
faster than inflation (`Plan._medical_n`); premium tables (`Cbar_nq`, `slcsp_aca_n`) pick it up,
so the claims follow. One fork line must change with it: `_medical_premium_lo` uses
`other_medical_k * gamma_n`, which becomes `other_medical_k * _medical_n(gamma_n)`. Two
consistency questions it raises for Phase 4: budget `medical` lines grow at their own real
`rate`, not at upstream's excess (should a `medical` line default to it?); and upstream's own
medical input (`setMedicalExpenses`) is in no claim and is not charged as spending (only an HSA
cap), which a federal proposal upstream has to address: which medical amount would Schedule A
read?

**R5. Size against upstream's scale before step 8.** Phase 3 adds about 1,240 lines of new
methods to `plan.py` (federal 748, NY 206, NJ 102, shared medical 107, shared budget/spending
77) plus about 300 inline, and 11 loop parameters to `_SC_PARAMS` (upstream has 6). Upstream's
`withSeniorBonus` (a federal deduction with a phase-out, `d6970b2`) added 89 lines to
`plan.py`. Lesson 2 of the plan (he implements his own design) argues for proposing the
contract and the measured stakes, not offering this code; R1 would cut the federal part to
roughly what a loop-only design needs.

### B.3 Read and left as is

- `_medicare_premium_ub_n` (set in `_buildOffsetMap`) and `_premium_ub_build_n` both take the
  top IRMAA premium from `Cbar_nq`; one is a column bound, the other a build-time bound
  including ACA. Could be one; not merged because R1/R3 decide which survives.
- `_gateCeilings(ss_in=...)`: a fork parameter on an upstream function, used by
  `_item_income_ub_n` before the variable map exists. Small, documented.
- The bracket-order repair's restore list in `_scSolve` names ten loop parameters by hand;
  a new one must be added there too (the step-5 review found two missing); nothing enforces it.
- Step 7 (docs) must add CHANGELOG entries for NY itemizing (step 2), NJ line 31 and the premium
  wiring (step 5), and the `medical` / `charity` budget types; only the federal entry exists.

### B.4 Tooling

- **The worktree recipe in CLAUDE.md runs the main checkout's code.** The `.venv` has an
  editable install whose `.pth` points at `/home/user/Owl/src`, so a worktree with `.venv`
  symlinked imports `/home/user/Owl/src/owlplanner` (checked: `owlplanner.__file__` from the
  worktree). Set `PYTHONPATH=$PWD/src` in the worktree to test its own code.

# Plan review after upstream `dev` `37afa2a` (2026-10-22)

Fork-only note. Written on `claude/phase5-step1` after merging upstream `dev` `37afa2a` (fixes for
#199-#203, #207-#218; PROGRESS.md "Upstream `dev` `37afa2a` merged"). Question: is the Phase 5
design still the right one, and do the remaining steps and phases still make sense, now that
upstream has changed a lot since the plan was written (2026-10-17, on `dev` `7abed19`)?

Each claim is marked: **read in code** (this commit), **measured** (script and saved output named),
**verified** (primary source, read earlier and cited where it was recorded), or **recalled**.

## 1. What changed upstream since the plan, and what it does to Phase 5

| Upstream change | Effect on the Phase 5 plan |
|---|---|
| #195 (`0b318e0`, merged 2026-10-20): `withSSAges` solves the plan at every open claiming month and keeps the best; the claiming-month MILP is gone | Already absorbed (plan §4.1, step 4). It made the design simpler (no tables): every candidate is a fixed-age solve, so the test applies through one path. It also makes **the cost of a candidate solve** the cost of an age search (§3 below) |
| #211 spousal DRCs | The fork's earnings-test builder repeats the spousal rule; mirrored in the merge, now pinned by a grid case (PROGRESS.md). Lesson: every upstream change to `_add_spousal_benefit` must be mirrored |
| #210 survivor limit after the age reduction; #212 born on the 1st | Inherited automatically: the builder's survivor fold goes through `compute_survivor_stream` (with the fork's `deceased_factor`) and its ARF through `getSelfFactor` (read in code) |
| #207 January 1 birthday, #208 Medicare/ACA by the month (+ HSA proration), #213, #214, #216 | No design effect. The household's placeholder birth dates are on the 1st, which these rules now treat specially: real dates are needed before decision runs (as noted 2026-10-21) |
| #199 tax-household FPL, #200 prior-year guideline, #201 2027 table and exactly 400%, #202 Medicaid by state | **Raises the weight of the ACA years in Phase 5**: the 400% FPL cliff is now where the law puts it (2027: 4 x \$21,640 = \$86,560 for two, `fork-notes/upstream-199-217/README.md`), and part-time earnings of \$20-60k (the plan's band) sit right around it in 2027-2028. See §3.2 |
| `eed3582` MOSEK bulk calls (claiming-age search 5x faster with MOSEK) | Only with MOSEK; this container solves with HiGHS (the suite's default). No change to the plan |
| `deebe3e`/`ad79391` MCP sweeps and scenario runs hold SS ages | Nothing to do (step 4) |
| Not fixed: #205/#206 (LTCG and the unused deduction) | \$0 on the 18 examples (measured 2026-10-21); no change |

No payroll tax was added upstream (case-insensitive grep of `upstream/dev` `src` for `payroll`,
`fica`: the only `fica` hits are inside "significant"), so step 5 is still needed as planned.

Step 9's evidence is unchanged: `et_examples.py` on stock `dev` `37afa2a` finds the same three
examples with the same numbers as on 2026-10-17 (measured:
`fork-notes/phase5/et_examples_2026-10-22_dev37afa2a.txt`).

## 2. The design (plan §4): still the right one

- **§4.1, a deterministic stream change, no LP piece.** Still right, and #195 made it more so:
  with the age chosen by fixed-age solves, a stream-level test is exact for every candidate,
  spousal charging and the ARF included. Nothing upstream did since points to an LP formulation.
- **§4.2 inputs** (`gross earnings`, `months worked`): unchanged by upstream; upstream still has
  only `anticipated wages`, net of contributions (read in code).
- **§4.3 the builder duplicates upstream's monthly SS rules.** This is the one weak point the
  merge exposed: #211 changed the spousal rule and the builder silently diverged until it was
  mirrored. Options: (a) keep the duplicate and rely on the zero-earnings grid test, which now
  covers the DRC case and failed under the mutation (\$2,880/yr, PROGRESS.md); (b) refactor
  upstream's `_add_spousal_benefit` to expose a monthly amount the builder calls. (b) adds a fork
  hunk inside an upstream function, which is the kind of change that conflicts at every merge.
  **Recommendation: (a)**, plus a line in the step-9 issue saying the builder must follow
  `_add_spousal_benefit` (if upstream adopts the test, the duplication goes away with ours).
- **§4.5 out of scope**: unchanged.

## 3. Remaining Phase 5 steps

### 3.1 Step 9 (upstream issue draft): still next, evidence refreshed

Unchanged in substance. Add: the #211 dependency (above), and that upstream's own #195 search is
what lets the test stay out of the LP. Timing is the user's call: the maintainer is working
through a batch of 18+ issues filed 2026-10-20/21; a design issue may wait behind them.

### 3.2 Step 6 (work-scenario sweep): the method needs changing

The plan says: for each work variant, `withSSAges` on both, run with local search and with the
exact LP. Three problems, two measured:

1. **A local-search age search is out of reach.** Each candidate is a full solve; local search
   took about 120 s per solve on chris+pat (step 4, `et_step4_crosscheck_2026-10-21.txt`), the
   loop about 0.6 s, the exact LP about 0.2 s. A searched spouse has up to 97 open months, and
   with both free the search repeats until neither moves (2-4 rounds in step 4). With 4 threads
   that is roughly 97 x 120 s / 4 ≈ 50 min per spouse per round, so hours per variant (inferred
   arithmetic from those timings).
2. **Loop picks move with loop noise.** chris+pat, Pat searched, test on: the loop picked 63y0m
   on 2026-10-21 and 63y2m today (measured, `et_plan_review_probe_2026-10-22.txt`; plans start
   today and the merge changed several rules, so the cause is not isolated). An argmax over 97
   candidates whose values carry loop noise of up to ~1% selects partly on noise.
3. **The "exact LP" is not exact in ACA years.** The CLAUDE.md recipe (`withMedicare="none"`,
   `withSSTaxability=0.85`) leaves ACA in the loop unless `withACA="optimize"` is added (read in
   code: the local-search preset sets it, in `_applyBreakpointOptions`, when `slcsp_annual > 0`;
   the recipe does not). The household has ACA years
   (`aca_start_year = 2027`, and since #208 the months before each 65th birthday in 2029), and
   part-time earnings put ACA-year MAGI near the 400% cliff, where a loop cannot price the jump.
   chris+pat has no SLCSP, so step 4's cross-check never met this.

**Measured** (`fork-notes/phase5/et_plan_review_probe_2026-10-22.txt`; chris+pat, test on, Chris
held at 70, Pat searched; the first search ran while the full suite was also running, so its
time is high):

| Pat's age | Local search basis (today's $) | |
|---|---:|---|
| 62y1m | 117,063.81 | |
| **63y0m** | **117,272.77** | pick of the exact-LP search (11 s) |
| 63y2m | 117,240.30 | pick of the loop search (58.5 s) |
| 64y0m | 117,141.91 | |
| 65y0m | 117,171.27 | |
| 66y0m | 117,128.01 | |
| 67y0m | 117,008.06 | |
| 68y0m | 116,969.41 | |
| 69y0m | 116,703.19 | |
| 70y0m | 116,441.90 | |

Local search took 67-177 s per solve. Of the ages it scored, it ranks the exact-LP pick best and
the loop's pick \$32/yr lower. The ranking is not smooth (65y0m above 64y0m by \$29): local
search is not a proven optimum, so differences of tens of dollars between neighbouring ages
are within its own noise. One case and one searched spouse; months other than the two picks
were not scored under local search. It supports, but does not prove, the exact LP as the
age-search reference when ACA is not involved.

*(ACA-reference probe `et_aca_reference_probe.py` running when this was committed.)*

**Proposed step 6 method** (replaces "run each with local search and with the exact LP"):
(a) search the ages with a cheap, noiseless reference: the exact LP **plus `withACA="optimize"`**
when the variant has ACA years (one ACA bracket binary block, only in the ACA years; its cost is
not measured yet, measure it first on a stand-in with an SLCSP); (b) evaluate the pick, the
loop's pick and a few neighbours (±6-12 months, whole years) under local search at fixed ages;
(c) decide differences by the CLAUDE.md rule (local search vs the reference, same sign, above
their spread). Cost per variant: one cheap search plus a handful of 2-minute local-search
solves, instead of hours.

Related template change: `Case_us.template.toml` sets `withSSAges = "optimize"` together with
`withMedicare = "optimize"`, so every candidate of a direct `owlcli run` is a MIP solved by
branch-and-bound under HiGHS (upstream's own note: HiGHS 49-238x slower than MOSEK on
branch-and-bound). Leave the template as the "full model" description, but say in its comments
that age searches go through the sweep script's two-stage method.

### 3.3 Inputs the sweep cannot express yet (questions for the user)

- **One household `aca_start_year`.** A variant where one spouse keeps employer coverage that
  covers only that spouse, while the other buys marketplace coverage, cannot be expressed: Owl
  starts ACA for everyone alive and under 65 in the same year (read in code: `_aca_coverage`
  takes no per-person start). Does any work variant have that shape? If yes, it is a small
  per-person start (fork, or an upstream issue: federal, in their scope).
- **`slcsp_annual = 0` in the template** (TODO): until the real benchmark is entered, every
  household run has no ACA cost and no cliff, so the variants that the cliff decides cannot be
  compared at all.

### 3.4 Steps 5, 8, 10

- **Step 5 (payroll tax)**: unchanged (nothing upstream). Size S. It matters only for comparing
  work variants against each other, so it must land before step 6's numbers are read.
- **Step 8 (measure)**: unchanged in purpose; uses step 6's method.
- **Step 10 (docs)**: `modeling-capabilities.md` done 2026-10-22 (`59ea495`); left: the
  `socialsecurity.py` module docstring, `Documentation.py`, template comments (§3.2).

**Revised order**: step 9 draft → step 5 → step 6 (method of §3.2; first measure the cost of the
ACA-optimize reference) → step 8 → step 10. Steps 5 and 9 are independent.

## 4. Remaining phases

From the original roadmap (PROGRESS.md "Later phases"; `phase3-plan.md` §1): 4 healthcare cost
model, 6 sweep and report. 7 (NJ) dropped 2026-10-17.

### Phase 4, healthcare: mostly covered upstream now; what is left is small or data

What the roadmap listed (`phase3-plan.md` §1: "OOP line with medical inflation and age curve;
Medigap vs Advantage; NY community rating; LTC shocks") against what exists now:

| Item | State |
|---|---|
| Medical price growth above inflation | Upstream `setMedicalInflation` (2026-10-11), applied to Medicare, ACA and other medical |
| Out-of-pocket spending | `other_medical_expenses`, or budget `medical` lines with their own rate and age clock (fork Phase 2b/Track B); counted in the itemized medical claims (Phase 3) |
| Medicare/ACA transition at 65, by the month; HSA end | Upstream #208 and `fb1a4a7` (merged today) |
| ACA rules (prior-year guideline, yearly tables, 400% edge, tax household, Medicaid by state) | Upstream #199-#202 (merged today) |
| NY community rating for a lone enrollee | **No effect on this household** (read in code): `couple_to_individual_fraction` clips the age to 64, and both spouses are 64 or 65 in the only year with one enrollee (2029), so both factors are 3.000 and the lone enrollee pays 1/2 of the couple's benchmark, which is also what pure community rating gives (that NY rates this way is recalled, not verified) |
| Medigap vs Medicare Advantage | Not modeled; a premium choice that can be entered as a budget `medical` line (and Part D base premium). A comparison of the two, not a model change |
| LTC shocks | Budget `care` lines with age clocks (fork Track B); deterministic, no probability |
| NY Essential Plan (up to 200% FPL since 2026-07-01, per a search summary, not the source) | Not modeled: Owl prices 138-200% FPL as marketplace coverage. Matters only if a variant holds ACA-year MAGI under 200% FPL (\$43,280 for two in 2026) |

**Recommendation:** no Phase 4 code now. Enter the household's real SLCSP and medical lines
(data); look at the step-6 output for ACA-year MAGI under 200% FPL, and only then decide on the
Essential Plan (a data-driven Medicaid-like band in `tax_federal`, federal-structured but
NY-specific, so fork-only by lesson 3).

### Phase 6, sweep and report: fold into Phase 5 step 6

Upstream still has no general scenario sweep (`owlcli` has `run`, `compare`, `explain`,
`frontier`; the MCP has `compare_cases` / `compare_to_baseline` and the conversion regret sweep;
read in code). Phase 5 step 6 is a sweep script over work variants; the residency and housing
comparisons of Phase 0 (`phase0-scenarios.md` §§3-5) are the same mechanics (a base case plus
overrides, the two-stage method of §3.2, one table per run). **Recommendation:** write step 6's
script with variants as generic case/HFP overrides, so it serves locality (Yonkers / NYC / rest
of Westchester), rent/buy and work at once, and call that Phase 6. A dashboard stays out of
scope.

### The gap that matters most is still Phase 0

As `phase3-plan.md` §1 said on 2026-10-10: the decision engine has never run on the decision.
`otherFiles/` holds only a PROGRESS copy (checked today); the template's balances, PIAs, birth
dates and SLCSP are TODOs. Since today's merge, the birth dates (on the 1st or not) and the
SLCSP change modeled results directly (#207, #208, #212; §3.3). Every remaining step's value
depends on them.

## 5. Decisions for the user

| # | Question | Recommendation |
|---|---|---|
| R1 | Step 6 method: two-stage (cheap noiseless age search, then local search at fixed ages) instead of local search inside the age search | Yes (§3.2); measure the ACA-optimize reference cost first |
| R2 | Does any work variant have one spouse on employer coverage alone while the other is on the marketplace? | Your facts; if yes, add a per-person ACA start before step 6 |
| R3 | Keep the builder's copy of the spousal rule, guarded by the grid test (vs refactoring upstream's function) | Keep (§2) |
| R4 | Phase 4: no code now; decide the NY Essential Plan from step 6's output | Yes |
| R5 | Phase 6 folded into Phase 5 step 6 (generic overrides) | Yes |
| R6 | Fill the real case (`otherFiles/Case_us.toml`, HFP): birth dates, balances, PIAs, SLCSP | Before step 6's runs |

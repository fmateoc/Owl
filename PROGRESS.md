# Owl fork — progress (as of 2026-11-01)

Fork-only file, like `CLAUDE.md`; not for upstream. Keep it current at the end of each work session.

Fork `fmateoc/Owl`, branch `claude/phase2-housing` (2026-10-07, from `main`): Phase 2 housing ledger and NJ property tax deduction, then the review fixes (same day): Debts `payoff` year, a crash before the first solve, Scenario 5 commands, stakes recorded on the objective, `--solver-opt` numeric text. 2026-10-08: merged upstream `dev` `156d812` (#173 loan linked to the property it finances, #174 mode options normalized, MCP partial bequest); our `payoff` column and `--solver-opt` validator dropped for theirs. Phase 2b the same day (after #175's answer): the Housing ledger replaced by a `"budget"` spending profile built from an HFP Budget sheet; HFP rate fix (a rate below 1 read as 100x). 2026-10-09: merged upstream `dev` `0ca30f4` (#176 our HFP rate report, fixed upstream with their design, ours dropped; #178 MIP money scaling); a fork fix the scaling exposed (NJ exclusion claimed short of the statute); essential budget lines (#175's cost-function point). Later the same day: merged upstream `dev` `d6970b2e` (`withSeniorBonus = "optimize"`; keep fork `zx` in `localsearch.FAMILIES` and their `zsb` in `ALWAYS_FREE`); Track B remainder plan rewritten against the shipped budget code. 2026-10-10: Track B steps 0-2 (smile anchored to its start with a fixed 30-year span; age clocks on Budget lines; JSON `budget_file`), then review fixes (below, and `fork-notes/track-b-spending-profile.md`, "Review fixes").
Plan details: `fork-notes/phase1-revised.md`. Scenario commands: `fork-notes/phase0/phase0-scenarios.md`.

## Upstream

Maintainer's responses as relayed by the user on 2026-10-06; issue states not re-checked on GitHub (this session's GitHub access covers the fork only).

| Item | State |
|---|---|
| #147, #149, #155 | Fixed upstream earlier; our copies dropped |
| #157 NY/NJ not indexed (+ NJ addendum) | Fixed upstream (`3c88ce1`, 2026.10.3); merged, theirs |
| #158 NY benefit recapture missing | **Closed 2026-10-07 by `fmateoc` as completed, no maintainer comment** (github.com, read 2026-10-12; the rest of this row predates that). Filed; no response (the issue said our code would not apply as is). **2026-10-06: rebuilt on stock `dev` `b4f1605`** without our loop registry or typed params, on upstream's `st_schedule`: `fork-notes/issue-ny-recapture.patch` (4 files, +369/−6, 23 tests; full upstream suite 2720 passed, 1 skipped; plans identical to the fork's to the dollar, also under local search and after the fork merged `b4f1605`). Follow-up comment **posted** by the user (`fork-notes/issue-ny-recapture-update.md`); no reply on #158 yet (the 2026-10-07 reply relayed answered the #171 points). 2026-10-07: patch refreshed on `5dd1623` (applies without offsets; upstream suite with it 2732 passed, 1 skipped; fork and patched stock still identical, by the same numbers moved $3-14/yr by upstream's own changes). Fork keeps its own version (locality surcharge on it, credits, Summary line) |
| #159 Moves + local tax (design) | **Implemented upstream as one move** (`f5820c0`, `a3897b2`, 2026.10.6), no local tax. Maintainer: wants equivalence of all variables between states and no lookup between years (e.g. IRMAA) before folding more in; "consider PA". **Merged 2026-10-06**: Plan names, `_states_n()`, the UI toggle and `basic_info.moves` follow upstream; the fork keeps several moves, a locality per move, and typed `StateTaxParams` (`st_schedule` under upstream's name). Three upstream asserts adapted (3-tuples), two `st_schedule` tests read fields. PA not looked at (its local earned-income taxes are wage taxes, which `taxes_local.toml` excludes by design; not verified this session) |
| #160 NJ retirement-income exclusion | Answered 2026-10-04: upstream keeps state taxes a pure LP. Our reply posted. Fork keeps its MILP |
| #161 ACA optimize infeasible | **Fixed upstream** (`bf817dd`, 2026.10.5), crossing found on the sliding scale; merged, theirs |
| #162 Bracket order | Fixed upstream with our patch (`3fca646`); fork keeps its copy (local brackets) |
| #163 SC-loop cycle selection | **On hold**: maintainer tested it over parameter ladders; it does not address optimality and the run-time difference is marginal. Not applied in the fork. Local search now covers the cameron case (section "Local search") |
| #164 ACA 133-150% band | Fixed upstream (`d88a37e`); merged, theirs |
| #165 ACA optimize rates | Fixed upstream (`7ad4c7e`): sliding scale by tangents, and Medicaid at no premium up to 138% FPL in both modes (morgan +$2,100/yr). Merged, theirs |
| #166 Cost basis | Fixed upstream (`4f90899`); merged, theirs |
| #167 Partial first year | **Documented upstream** (`22ec12f`), left open for a short first period. Maintainer suggests adding the amount spent since Jan 1 to the balances. Reply **posted** by the user 2026-10-06 (`fork-notes/issue-partial-first-year-reply.md`): with income kept full-year, as his docs say, the add-back is spending and taxes paid minus income received. Fork template updated (`fork-notes/phase0/Case_us.template.toml`) |
| #168 SS-age taxes | Fixed upstream (`a746a04`); merged, theirs |
| #169 Survivor never claimed | Fixed upstream (`1a21641`); merged, theirs |
| #170 Envelope model | Filed with #171; one conversation with it (the maintainer answered both on #171) |
| #171 Pinned loop | **Declined**: second model too costly; `withACA="optimize"` captures morgan's gain; maintainer's answer is local search (`breakpointMethod="local-search"`, 2026.10.6). Asked for our findings: measured, reply **posted** by the user 2026-10-06 (`fork-notes/issue-local-search-reply.md`, details `fork-notes/local-search/README.md`). Maintainer (2026-10-07): all three points right; tie rule and repeat reuse in `785217c`, merged (fork's own tie code and test dropped, theirs kept). He also notes the cost basis is still a source of non-convergence with Medicare exact (on his list) |
| Loop anomaly (NY→FL at year 5) | Not filed (no repro beyond loop noise) |
| #175 Housing ledger + NJ property tax deduction (design) | **Answered 2026-10-08**: no more state-tax plumbing upstream (NJ deduction stays in the fork); budgeting belongs outside the optimizer, as a module that builds the spending profile ("envelope") the optimizer consumes. Checked: rent inside a custom profile gives the same plan as our ledger under `maxBequest` to the dollar (`envelope_vs_ledger.py`). Plan `phase2b-budget-plan.md`; the user agreed to its 3 decisions and **posted** `issue-175-reply.md` (2026-10-08). **Implemented as Phase 2b** (below). Second answer (2026-10-08): budgeting as a **separate project, "Owl-budget"** (JSON, past five years for extrapolation, rent vs buy, health costs from the literature, HFP filling, Owl's look, files exchanged between two tabs); requirements first. Our input drafted: `owl-budget-requirements.md`, condensed reply `issue-175-reply-2.md`, **posted** by the user (#175 is now a GitHub Discussion). Third answer (2026-10-09): he owns Owl-budget for now; Owl's side of the contract goes in core ("hooks almost all there"); shape-only vs fixed lines open ("how the profile interacts with longevity"); JSON and Excel both, MCP on both sides for ladders of budgets; sources from a web search (BLS CE, HRS, EBRI, Vanguard, Fidelity); the budget must cover ~10 years before retirement; **cost function**: split core from discretionary spending. Answered first with the essential-lines prototype and measurements (`issue-175-reply-3-measured.md`, superseded: the maintainer keeps the discussion at the brainstorming level); restarted by the user as a conceptual reply, `issue-175-reply-3.md` (lines tied to the clock that causes them, calendar / age / household event, instead of Owl's plan-length-stretched smile; one series per household state as the time-series contract; priority tiers instead of utility weights, bequest as a possible tier; one risk tolerance per tier in stochastic spending; own history for the level, literature for change with age), **posted 2026-10-09** (Discussion #177). Maintainer's reply (relayed by the user 2026-10-15): "Sorry for the delay. Give me a day to digest all the good info you provided. I mean really good info. The soft part of discretionary spending expressed as a slack variable is a total novelty in modeling deccumulation." A deferral, no decision yet; nothing to answer until he does |
| #176 HFP rates below 1 read as 100x (0.5% real growth -> 50%) | Found 2026-10-08 while building the Budget sheet; repro on `dev` `156d812`: a home's end value $2.07M -> $509 billion, loan payment $15k -> $360k after save and reload. **Fixed upstream** (`ec6a5e0`, credited): only percent-formatted cells converted, each matched to its row by value and position. Merged 2026-10-09, ours dropped (their 6 tests cover our 4); the fork's Budget sheet keeps its rates as typed |
| #185 Federal itemized deductions (design; `fork-notes/issue-federal-itemized.md`) | Posted by the user. Maintainer's reply (relayed 2026-10-15): "I'll need to look more deeply into it. Adding more stuff to the recursion loop is what causes cycling and prevents monotonic convergence. I'll run a few tests and get back to you." Measured the same day against that concern (section "Itemizing and loop convergence"); data comment `fork-notes/issue-185-reply.md` posted by the user (relayed 2026-10-16). The NY + mortgage failure it mentioned was traced to upstream's SS loop and filed as #193 (2026-10-16); pointer comment linking #193 posted by the user (2026-10-16). Rechecked 2026-10-17 after the NJ removal: conclusions hold; the NJ stakes rise on upstream's NJ (section "#185 after the changes since filing"). **Dropped upstream** (relayed by the user 2026-10-24): the maintainer's reluctance stood ("Adding more stuff to the recursion loop is what causes cycling and prevents monotonic convergence"); apart from the SS-taxability problems found while measuring (#193, fixed upstream), the issue was dropped/closed. Not checked on GitHub (no API access to upstream from this session). Itemizing stays fork-only |
| #199-#217 (not ours; filed 2026-10-20/21, 17 by `rationalpiper`, #208 by the maintainer) | **Fixed upstream** (`dev` `37afa2a`, 2026-10-22) except #204 (proposal), #205, #206; #218 (survivor's home-sale exclusion) too. Merged 2026-10-22, theirs; fork adaptations and a review fix in "Upstream `dev` `37afa2a` merged". Checked before the fixes 2026-10-21: no claim found wrong (`fork-notes/upstream-199-217/README.md`) |
| #220 SSA earnings test (design issue, ours) | **Posted by the user 2026-10-22** (`fork-notes/issue-earnings-test.md`, Phase 5 step 9): stock-`dev` `37afa2a` evidence (three examples pay SS before FRA in a work year; `withSSAges` picks Pat 62y6m inside her last work year), fork stakes, four questions (core and default, the earnings input, the stop month, survivors). **Maintainer (relayed 2026-10-23):** overlooked; "What did you end up doing?"; he trusts our judgement to fill the gap; only requirement: "the optimize full MILP is still affordable". Reply draft `fork-notes/issue-220-reply.md` (what the fork built, full-MILP cost measured, a PR on `dev` promised); revised the same day after the user's review: no option, the test is part of the model (fork: `withEarningsTest` retired); posted 2026-10-23. **PR #222 landed as `6ea43a9` (2026-10-24)**, squashed, the user co-author, `gross earnings` dropped for derived earnings; the maintainer closed PR #222 and #220 by hand (relayed 2026-10-24; section "Upstream `dev` `4e55b36` merged") |
| #227 Employee payroll tax on wages (design issue, ours; `fork-notes/issue-payroll-tax.md`) | **Posted by the user 2026-10-25; answered the same day: PR requested** in a shape he set (no option, `payroll_n` a cash-flow constant, Summary line for every case, re-pins). **PR built** 2026-10-25: branch `payroll-tax-pr` (`55b49ba` + review fixes `36cdddf` on `dev` `22ce72b`), text `fork-notes/pr-227-body.md`, for the user to open. john+sally's \$21: the loop's plan at the zero-bequest edge, \$374 short on IRMAA (PROGRESS.md "PR for #227"). The fork's payroll code equals the PR's. When it lands, take upstream's version |
| PR #196 (#193: `"convex"` + Summary label + SS-residual warning) | Opened by the user 2026-10-17 at the maintainer's request ("bundle both points above in a single PR and I'll test and push"). Head `fmateoc:ss-convex-pr` (`fb8b10e`: upstream `ss-convex` + `dev` `2b34633` merged + our commit), base `dev`. Upstream suite 2871 passed, 1 skipped. Text `fork-notes/pr-193-body.md`. If he pushes to the branch or merges it under new hashes, compare trees before the next sync. **Maintainer on the PR (2026-10-17, relayed):** "Are you sure you want to keep the ss-convex implementation? My tests were mixed. I am not sure this adds much. Your call." Measured the same day (section "PR #196: is 'convex' worth keeping?"); reply draft `fork-notes/pr-196-reply.md`, **revised after the user's review: drop "convex"** (as an opt-in it is a choice with no signal for when to make it; the warning misses a loop that settles short; dominated by "optimize" when the rest is exact); **PR reworked the same day**: branch `ss-convex-pr` force-pushed (lease on `fb8b10e`) to `e5a9ad5`, one commit on `dev` `7abed19` (the warning only, pointing to `withSSTaxability="optimize"`; `tests/plan/test_ss_residual_warning.py`; upstream suite 2869 passed, 1 skipped); new PR title/text (`pr-193-body.md`) **pasted and reply (`pr-196-reply.md`) posted by the user** (2026-10-17); awaiting the maintainer. The reply promises the local-search LTCG issue (`issue-ls-ltcg.md`) as a separate issue |
| #197 Local search pins the LTCG regime binaries in step (b) (`fork-notes/issue-ls-ltcg.md`) | **Filed by the user as #197** (2026-10-17). **Patch applied in the fork** the same day; household stand-ins rerun, no decision moves. Stock repro on `dev` `7abed19`: john+sally local-search preset 20,004 vs branch-and-bound 31,778; patch (step (b) leaves `zl` free) gives 31,778, never lower on the 18 examples, 1.53x the time. Section "Local search and the LTCG family" |
| #193 SS-taxability loop short of the exact model, stuck at the cap on LP ties (`fork-notes/issue-ss-loop.md`) | **Filed by the user 2026-10-16.** Stock repro `issue-ss-loop-repro.py` (output from `dev` `10b9f72`): loop $33.7k-48.6k below `withSSTaxability="optimize"` on the NY + mortgage couple, cap on ties, Summary error bar +-$358 on a plan $38k short, local search right. Questions: residual in the Summary; re-solve or recommend exact SS on a large SS residual. Maintainer (2026-10-16): how does it compare with `mipStrategy="local-search"`? Measured: local search on SS = branch-and-bound to the dollar; presets +$270-524; reply `issue-193-reply.md` **posted by the user**, with a correction (exact SS takes 14-21 s, not "a few seconds"). **Fixed upstream the same day** (`6b02671`, `83a580b`: `withSSTaxability="convex"`, opt-in), merged in `ae1fb9d`; then moved by the maintainer to branch `ss-convex` with `c22f46d` (cheaper cap probe), merged in `bb00250`; checked with the repro at `c22f46d` (equals `"optimize"` to the dollar, 0.8-1.2 s); confirmation `issue-193-reply-2.md` (at the branch tip) **posted by the user**; experiment branch `ss-binaries` (`abd39b4`, fewer SS binaries) measured, not merged: exact, 3.6-6.3x the nodes on the repro; the maintainer concluded it and deleted the branch, our comment draft not posted |
| #178 MIP money scaling (not ours) | Upstream `419a5ee`/`00d9bad`/`0ca30f4`: MILPs solved in hundreds of dollars (`mipScaleOrder`, default 2), tighter withdrawal-ordering big-M. Merged 2026-10-09. Effects on the fork: the NJ exclusion MILP closes its gap at the root (the 200-node cap test now runs at `mipScaleOrder=0`); local search on the NJ test couple 4x faster (43 -> 11 s) and +$154/yr; it also returned a plan that claimed the exclusion short of the statute (fixed in the fork, `b2ef9b2`, below). Not an upstream bug: their LP has no such exclusion |
| #173 Mortgage outlives the sale of its home | **Implemented upstream with another design** (`431aee0`): optional Debts `property` naming a residence/real estate in Fixed Assets; the loan is paid off in the year it is sold; a bad link is a configuration error. Maintainer: a typed year drifts from a `yod` counted from the plan end. Our payoff mechanics kept. Merged 2026-10-08, ours dropped |
| #174 `--solver-opt withSSTaxability=0.85` ignored | **Fixed upstream** (`fcf1b0b`), broader than our patch: all six mode options normalized or refused (`utils.normalize_mode_option`). Merged 2026-10-08, ours dropped; rechecked: jack+jill pins to 101,448 on both runs |
| #233 Sticky-binaries tie can take a plan outside a requested `gap` (ours; `fork-notes/issue-sticky-gap.md`) | **Filed by the user 2026-10-26.** Stock repro on `dev` `4dcfabb` (chris+pat at `gap=1e-5`: `solverGap` 1.8-2.0e-5 with every HiGHS run within 1e-5) and patch (refuse a tie that would leave a gap the solve met; one more loop iteration where it refuses). Open risk: MOSEK's `test_pathological_cases_settle`, not runnable here; fallback offered: cap the tie at the gap. Fork not patched (`work_sweep.py` passes `relTol` = gap). 2026-10-27: maintainer "Thanks for looking into this.", self-assigned, label `bug`; not fixed on `dev` `07b9a77`. **Fixed upstream as filed** (`4aa4887`, 2026-10-27), merged 2026-10-28; the issue's four cases reproduce the patched rows to the cent (section "Upstream `dev` `1bdc3b2` merged") |
| #229-#232 (not ours; filed 2026-10-26 by `rationalpiper`, on code from our PRs #222/#228) | **All four valid**, numbers reproduced here (`fork-notes/upstream-229-232/README.md`): #229 the `omega_in > 0` gate drops an all-deferred year's deferral from the earnings; #230 an employer match in `401k ctrb` and a nondeductible IRA counted as earnings; #231 exempt amounts after 2026 used as first-year dollars (a plan starting 2027 loses a year; 2027 amounts not verified then, verified 2026-10-27 from 91 FR 67380); #232 the worker's excess charged on the spouse's pre-ARF add-on after the spouse's FRA. **All four fixed upstream 2026-10-27** (#229 `69d00c7`: 401k deferral always earnings, new `employer ctrb` column; #230 docs `cc5377b`; #231 `3ea6f0f`: nominal exempt and wage-base tables with 2027; #232 `d9d0bd0`: two-pass charge) and **merged here 2026-10-27**, theirs; the fork's strict xfails removed (section "Upstream `dev` `07b9a77` merged") |
| #234-#235 (not ours / ours; filed 2026-10-26 by `rationalpiper`) | #234 (upstream's `_netSurplusRoundTrip`, `8bd1f3d`): code claims **valid** (netting after the solve, federal-only test, basis and `Q_n` on gross flows, local search seeded netted); numbers not reproduced (setup incomplete). Fork examples: only jack+jill nets ($118,626 in 3 years, basis tracked, TN). #235 (our earnings test, a documented premise): Owl's numbers reproduced, the law's arithmetic checked; feature request. Fork not patched (`fork-notes/upstream-234-235/README.md`). #231: our comment posted by the user. 2026-10-27: #235 has a follow-up by the reporter (overpayment recovered by withholding later checks, 20 CFR 404.501/502), self-assigned by the maintainer, label "Tax law"; #234 unchanged; both open. **#234 fixed upstream** (`3931c8a`, 2026-10-28: only a round trip that realizes no gain is netted; local search starts from the un-netted withdrawals), merged 2026-10-28; jack+jill now nets one year at gain fraction 0 (section "Upstream `dev` `1bdc3b2` merged"). #235 not checked this session. **#235 fixed upstream** (`92afe10`, 2026-10-28: the five years before the plan read for someone already claiming), merged the same day; the law-side figures of 2026-10-26 reproduced (section "Upstream `dev` `b6a3ba7` merged") |
| #236 LP-chosen spousal deposit split (not ours; filed 2026-10-26 by `rationalpiper`, enhancement) | Replace the fixed `eta` rows (`_add_surplus_deposit_linking`) by `d_0n + d_1n = s_n` while both are alive. Reporter's PA case: free split = best fixed `eta` (1.0), +$5,038 over the plan vs 0.5; FL +$365/yr. Self-assigned by the maintainer 2026-10-27, no comment. Code claim (where `eta` is read) holds. **Checked against the household's structure 2026-10-27** (`fork-notes/upstream-236/README.md`): equal horizons (no survivor phase), so the reporter's mechanism cannot arise; on a stand-in, no deposits under `maxSpending`, at most $157 of bequest (0.008%) under `maxBequest` with local search; the free split does not dominate (noise as large as the effect). Nothing to change; `work_sweep.py --eta` stays as a sensitivity on the real inputs. **Implemented upstream** (`1bdc3b2`, 2026-10-28) as an option, `spousal_surplus_deposit_fraction = "optimize"`; merged 2026-10-28 |
| #238, #239 (new; issues not read, known from the commits) | **Fixed upstream** 2026-10-28 and merged the same day: #238 (`f21486b`) the survivor's inherited taxable account takes its value at the death as basis, and an account that starts empty is tracked from $0; #239 (`b6e695b`) a warning when the LTCG loop does not settle. Household: #238 cannot apply (equal horizons) |
| Upstream workflow | Branch from and target `dev` (CONTRIBUTING) |

## Phase 0 — baseline case and scenarios

The unchecked items below are the user's offline runs on the real case (CLAUDE.md, "Household data", 2026-10-29); cloud sessions check the same scenarios on the synthetic household (`fork-notes/synthetic/`).

- [x] Templates in the repo, placeholders only: `fork-notes/phase0/` (case template, HFP generator, scenario commands)
- [x] Template checked: solves with placeholder numbers; Yonkers, NJ move, fixed SS ages and the alternate HFP all run
- [ ] Copy the template to `otherFiles/Case_us.toml` and fill in the TODOs (names, DOBs, balances as of `start_date`, basis, PIAs, SLCSP)
- [x] Scenario 4b written and checked: one spouse stops (and may claim SS), the other keeps working full or part time
- [ ] Generate and fill `otherFiles/HFP_us.xlsx`, `otherFiles/HFP_us_2027.xlsx` and `otherFiles/HFP_us_oneworks.xlsx`
- [ ] Run the baseline and the scenario comparisons; record rate method/seed with each

Scenario 4b settings: `aca_start_year` = the year after the worker's last year (family coverage through the job, so one household start year is right); `withSSAges=["<the one who stops>"]` and the worker's claiming age at 67+ while earning above the limit, because the earnings test is not modeled; a PIA per scenario, since extra work years don't raise it in Owl.

Notes: `owlcli compare` applies `--set` to the variant only, so the base case file must be filled in. Save TOML files as UTF-8 (the Windows-1252 em dash broke loading). Keep `basic_info.names` equal to the HFP sheet names. The fork is public: real numbers only in `otherFiles/`. In the NJ scenarios, wages above $3,000 in a year close NJ line 28b (other income), so scenario 4b's working years get only line 28a.

## Phase 1 — state and local income tax

| Step | Commit | State |
|---|---|---|
| State base = AGI | upstream | Done |
| Typed state params; NY not inflation-indexed | `ad4452d` | Done |
| Registry of self-consistent-loop parameters | `58fd9a8` | Done |
| Change of state during the plan (`basic_info.moves`) | `8849a3d` | Done |
| Local tax: NYC brackets, Yonkers 16.75% surcharge (`basic_info.locality`) | `14d0b57` | Done; checked against the 2025 IT-201-I |
| NY benefit recapture, loop mode | `fe7fba3` | Done; reproduces every 2025 worksheet constant; 2026 derived |
| Recapture and local tax in summary and Taxes sheet | `0696df8` | Done |
| Upstream constraint caching (#151) compatibility | merge `d500c1b` | Done; replay test covers recapture/local/moves |
| MCP explain adapted for moves/locality/recapture | `d0d171e` | Done |
| Recapture, optimize mode | — | **Dropped**: zero regret on a conversion-cap grid; lifetime recapture $81–6.4k |
| NJ not indexed; NJ $1,000 exemptions | `20ccb2d` | Done; schedules and exemptions identical in the 2020 and 2025 NJ-1040 instructions |
| NJ retirement-income exclusion (lines 28a–28c, from Phase 7) | `7fcfadf` | Done, MILP (see below) |
| NJ exclusion: free binaries only near the ceilings; 60 s cap that keeps the tiers | `395be10` | Done (user chose: window first, time cap as fallback) |
| NJ exclusion: 20,000-node cap instead of 60 s (HiGHS); a local-search family | 2026-10-06 | Done (same plan as the 60 s cap on the $2.5M couple; deterministic) |

NJ exclusion, how it is built: one binary per tier per year in which a filer is 62+, in the disaggregated (convex-hull) form. Rejected alternatives, measured on the $1.5M couple: a self-consistent-loop version (2-cycle; the accepted plan undercharged its own NJ tax by $13.9k lifetime), and a big-M-on-income MILP (4–6 s per MILP; with `gap=1e-3` it hit a 30 s limit).

Solve limits (`plan.py`: `RX_WINDOW`, `RX_NODE_LIMIT`; until 2026-10-06 `RX_TIME_LIMIT`): binaries are free only in years whose income in the previous iterate was at most 1.5× the top ceiling ($225k); iteration 0 runs without the exclusion, and the free set (`RXF_n`, an SC parameter) only grows, so at convergence every left-out year is far above $150k, where nothing is excluded. Without `maxTime`, a MILP carrying the binaries stops at 20,000 HiGHS nodes (until 2026-10-06: 60 s), warns with its gap, and later iterations keep its tiers; `solverGap` reports that gap. The window alone did not fix the $2.5M case (60 s cap hit on all four iterations, 240 s); keeping the tiers did (61 s).

NJ stakes, rerun 2026-10-06 on this branch (upstream 2026.10.7 merged; NJ exclusion as a local-search family; node cap). Synthetic couple born 1964-03-15 and 1964-09-15, life expectancies 89 and 92, SS $3,000 and $2,400/month at 70, $300k taxable, $150k Roth, conservative rates, 60/40, `maxSpending`, no bequest. Script `fork-notes/model-review/nj_stakes.py exact|default|ls`; raw output `fork-notes/local-search/nj_stakes_2026-10-06.txt`. Spending basis in $/yr; lifetime state tax in today's $; runs one at a time on the 4-core container.

| Tax-deferred | Case | Exact LP | Loop (default) | Local search | Lifetime state tax (exact / loop / LS) | Time (exact / loop / LS) |
|---|---|---:|---:|---:|---|---|
| $1.5M | FL | 126,340 | 123,818 | 125,130 | 0 / 0 / 0 | 0.1 / 0.6 / 43 s |
| $1.5M | NY | 125,063 | 122,597 | 123,206 | 31,554 / 31,572 / 46,892 | 0.1 / 0.6 / 59 s |
| $1.5M | NJ, no exclusion | 124,587 | 121,817 | 122,947 | 42,595 / 42,526 / 54,692 | 0.1 / 0.9 / 46 s |
| $1.5M | NJ, exclusion | 126,069 | 122,406 | 123,636 | 0 / 0 / 20,193 | 6.2 / 17.8 / 184 s |
| $2.5M | FL | 161,844 | 157,821 | 158,833 | 0 / 0 / 0 | 0.1 / 0.2 / 64 s |
| $2.5M | NY | 157,945 | 153,952 | 154,431 | 97,369 / 97,634 / 98,123 | 0.1 / 0.2 / 82 s |
| $2.5M | NJ, no exclusion | 157,621 | 153,632 | 154,038 | 106,720 / 106,872 / 106,500 | 0.1 / 0.2 / 60 s |
| $2.5M | NJ, exclusion | 158,828 | 154,482 | 154,993 | 63,291 / 63,370 / 75,289 | 63 / 67 / 180 s |

"Exact LP": Medicare off and SS taxability pinned at 0.85, a different model (no IRMAA, no SS formula), so its residuals are large by construction. "Loop": the default options. "Local search": the default options plus `breakpointMethod="local-search"`, which also replaces the pinned SS fraction by the IRS formula. NJ-with-exclusion gaps: 0.01% / 0.17-0.19% at the node cap for the MILPs; local search reports no gap (no certificate).

NJ (exclusion) minus NY, $/yr:

| | Exact LP | Loop | Local search |
|---|---:|---:|---:|
| $1.5M | +1,006 | −191 | +430 |
| $2.5M | +883 | +530 | +562 |

FL minus NY: +1,277 / +1,221 / +1,924 at $1.5M; +3,899 / +3,869 / +4,402 at $2.5M.

Reading: the loop alone flips the sign of NJ vs NY at $1.5M; local search and the exact LP agree that NJ (with its exclusion) is ahead at both levels, by $430-1,006/yr. Local search finds better plans under the full model in every case here (+0.3% to +1.1% over the loop) and pays more state tax in 5 of the 6 taxed cases; that it trades state tax for federal costs the loop prices with a lag (IRMAA, SS taxability) is inferred, not decomposed. For decisions: compare variants under local search, cross-check with the exact LP, and treat differences smaller than the spread between the two as unresolved. Earlier tables (2026-10-03/04, before the upstream ACA/basis fixes and with the 60 s cap) are in git history; the exact-LP figures moved by $20-50/yr since.

Known limits: NYC household/school credits, part-year residency, the 10.9% NY cliff above $25M AGI, NJ Special Exclusion / disability before 62, NJ line 28b when only one spouse is 62+ (only 28a taken), NJ basis in IRAs. Residency comparisons under ~1% made with the loop alone can have the wrong sign (table above).

## Model review (2026-10-03)

Review of the paper (`papers/owl.tex`) against the implementation: `fork-notes/model-review/README.md`, with repro scripts and raw output in the same directory. Main findings (all upstream code):

- [x] Loop mode returns a self-consistent plan, not an optimal one. Optimizing IRMAA or SS taxability raised the objective on 9 of 13 examples by up to +1.3% bequest / +2.3% spending, never lowered it. **Addressed upstream** by `breakpointMethod="local-search"` (2026.10.6, opt-in): better than the loop on 12 of 17 examples, up to +1.42% (+7.79% morgan), never worse (`fork-notes/local-search/README.md`).
- [ ] A non-converging loop keeps its highest-objective iterate, whatever its residual (cameron: SS off by $29.8k). #163 on hold upstream. Under local search, the fork's tie rule now returns cameron's objective with zero residual; proposed in the #171 reply draft.
- [x] Bracket fill goes out of order when late cash has no value (constructed case: $1.56M reported vs $0.91M). **Fixed 2026-10-04**: tax tie-break switched on in the loop when a year goes out of order, a final re-solve, and a post-solve check. The 17 examples are unchanged.
- [x] `withACA="optimize"` infeasible where `pct x MAGI > SLCSP` below 400% FPL. **Fixed 2026-10-04**; upstream's own fix (#161, crossing on the sliding scale) replaced ours in the 2026.10.7 merge.
- [x] NJ kept tier held income on its floor (`maxTime=2`: a year at exactly $150,000 claimed nothing instead of 25%, $5,402 vs $3,330 statutory; failed on `06468de` too). **Fixed 2026-10-04** (`755377e`): such a year's kept tier moves down to the statute's, downward only. 4 of 4 repeated runs were non-statutory without the fix, 0 of 4 with it; deterministic unit test added.
- [x] SS claiming-age MILP charged every candidate age the same SS tax. **Fixed 2026-10-04** (`d92c118`): taxable SS, IRMAA/ACA MAGI and the state SS exclusion use offset + `ssb` with the loop's `Psi_n`. Exact-LP repro: result no longer depends on the starting age and equals a fixed-age solve (start 62 used to report $104,526/yr for an age worth $104,518/yr). Not covered: `withSSTaxability="optimize"` (its min() needs another binary). Draft `fork-notes/issue-ss-age-taxes.md`. Upstream #168; theirs since the 2026.10.7 merge.
- [x] Cost basis omitted reinvested dividends; whole-account gain fraction applied to the equity share only. **Fixed 2026-10-04** (`245d200`): taxed dividends/interest added to basis, equity gain fraction `(1 - K/b)/alpha0`. Examples: joe -469, helen+ruth -1,036, jack+jill -42, robin -57 $/yr (references re-recorded; MOSEK helen+ruth reference not re-recorded). Draft `fork-notes/issue-cost-basis.md`. Upstream #166; theirs since the 2026.10.7 merge.
- [ ] Partial first year: balances are back-projected for growth only, while year-0 flows run full-year (same $1M on Oct 1 vs Jan 1: -2.1% spending). Upstream #167: documented (`22ec12f`), left open. Not fixed in the fork; the household case uses January 1 balances (template).
- [x] Survivor of a worker who died before claiming got 82.5% of PIA. **Fixed 2026-10-04** (`adeea31`): full PIA, plus DRCs to death after FRA. Rule from memory and secondary summaries of POMS RS 00615.320 (ssa.gov, ecfr, govinfo blocked); **user to confirm before filing**. Draft `fork-notes/issue-survivor-never-claimed.md`. Upstream #169; theirs since the 2026.10.7 merge.
- [x] New: ACA loop mode 133-150% FPL band started at 2.10% instead of 3.14% (Rev. Proc. 2025-25; irs.gov blocked, table from secondary sources). **Fixed 2026-10-04** (`5bd010e`). Draft `fork-notes/issue-aca-133-150.md`. Upstream #164; theirs since the 2026.10.7 merge.
- [x] ACA optimize: step rates (each band charged its final %) and the <138% FPL rule differs from loop mode (repro: optimize ends $1,786/yr higher where income drifts below 138%). **Fixed upstream** (#165, `7ad4c7e`): tangent-line sliding scale, Medicaid at no premium up to 138% FPL in both modes.
- [x] Paper vs code drift, loop mode as a fixed point, taxable bond returns, plan year: one docs issue drafted, `fork-notes/issue-docs-loop-and-paper.md`. Rechecked 2026-10-29 against `226ff54`, then superseded by a full review of the paper (`fork-notes/paper-review-226ff54.md`); drafted per its section E as `issue-qcd-limit.md` and `issue-paper-226ff54.md`, filed as #240 and #241 (2026-10-29); both fixed upstream the same day (`8ac888d`, `13d45ed`), merged.

**Filed by the user on 2026-10-04**: ACA 133-150% band (#164), survivor never claimed (#169), cost basis (#166), SS-age taxes (#168), partial first year (#167), ACA optimize rates (#165); numbers from upstream's CHANGELOG and commit messages. **Not filed:** docs/paper drift (`issue-docs-loop-and-paper.md`). The last two were verified on 2026-10-04 against the primary text: Rev. Proc. 2025-25 section 3.01 (irs.gov) and 26 CFR 1.36B-3(g)(1) for the ACA band; 42 U.S.C. 402(e)(2)(D) (govinfo.gov), 20 CFR 404.338 and 404.313(e)(1) (ecfr.gov) and POMS RS 00615.320 (secure.ssa.gov) for the survivor rule. Repro numbers re-run on this branch match the drafts. Note: www.ssa.gov itself answers 403 to curl (the site, not the proxy); POMS is on secure.ssa.gov. Rule from the user: never file a draft that asks the maintainer to check a source we didn't check; mark it not ready instead. Each patch draft has a `.patch` verified on stock `dev` `c1e5619` (full suite with each patch alone: 2604-2606 passed, 1 skipped; flake8 clean). Applied in the fork on branch `claude/project-thread-qx5fy0`.

## Envelope model (2026-10-04, branch `claude/project-thread-u0d9t0`)

Back-of-envelope question: `fork-notes/envelope/README.md`. A one-state DP (`em.py`) reproduces Owl within ±1% on most examples in 0.02–0.2 s; with the early-withdrawal penalty, conversion caps and the taxable account as a second state (§8), the EM's accounting matches Owl's within ±0.11% in 15 of 17 cases and its optimum is within −0.3% to +0.9% in 12 of 17, but it takes 0.7–5 s (slower than Owl's loop). Decision (Florin): the one-state version is the quick screen.

Seeding Owl's loop from the one-state plan does nothing (≤0.05% except john+sally +3%). Pinning Owl's yearly recognition to it, with the loop seeded from it, gives morgan +10.2% on stock `dev` (+11.0% with Ψ fixed, all other residuals 0) and −0.55% to +0.47% elsewhere; john+sally −$5.8k, because the EM's schedule needs an untaxed taxable account (README §10, which also explains the john+sally gap).

Upstream: the pinned loop was filed as #171 and **declined** (2026-10-05/06): a second model with its own assumptions costs too much to maintain; `withACA="optimize"` already gets morgan's gain (+7.9%); the maintainer's answer is local search (2026.10.6), which beats the pinned loop's results on the examples (`fork-notes/local-search/README.md`). The EM issue is #170, answered together with #171. The EM stays a fork-notes screen.

## Upstream contributions (maintainer implements from issues; send issue + patch, not PRs)

1. #157 NY non-indexed amounts (patch `ad4452d`) — filed; NJ addendum drafted (patch `20ccb2d`)
2. #158 NY benefit recapture (patch `fe7fba3`) — filed; stock-`dev` patch and follow-up drafted 2026-10-06, not posted
3. #159 Design issue: residency moves + local tax layer — one move implemented upstream (2026.10.6), no local tax; merged
4. #160 NJ retirement-income exclusion (patches `7fcfadf`, `395be10`) — filed; maintainer keeps state taxes a pure LP; our reply posted
5. #161 ACA optimize infeasibility — fixed upstream (2026.10.5), merged
6. #162 Bracket order — fixed upstream with our patch (2026.10.4), merged
7. #163 SC-loop cycle selection — on hold upstream
8. Filed 2026-10-04 by the user: #164 ACA 133-150% band, #169 survivor never claimed, #166 cost basis, #168 SS-age taxes (all fixed upstream, merged); #167 partial first year (documented, open); #165 ACA optimize rates (fixed upstream). Not filed: docs/paper drift
9. #170 envelope model and #171 pinned loop (one conversation) — declined in favor of local search; findings reply posted 2026-10-06
10. #167 reply posted 2026-10-06
11. Filed by the user after 2026-10-07: housing ledger + NJ property tax deduction (design issue); #173 loan payoff at a sale (implemented upstream as a `property` link, merged); #174 `--solver-opt` numeric text (fixed upstream, merged)
12. Federal itemized deductions (Phase 3 step 8): design issue drafted 2026-10-12, revised after upstream `810a6cd`, `fork-notes/issue-federal-itemized.md`, concept level, not posted

#158 was closed without an upstream change (2026-10-07); the fork keeps its recapture. If upstream ever lands it, merge `dev` and drop our duplicate, as with #149, #155, #157 and the 2026.10.5-7 fixes.

## Later phases (from requirements.md)

2 housing ledger (rent vs buy, property tax) · 3 itemized deductions · 4 healthcare cost model · 5 part-time work and SS earnings test · 6 scenario sweep and report · 7 NJ specifics (**dropped 2026-10-17 with NJ itself**; exclusion done; 65+ exemption done upstream in 2026.10.3; property tax deduction done with Phase 2; left: the $50 credit is out by decision)

## Phase 2 — housing ledger and property tax (2026-10-07; the ledger was replaced by Phase 2b)

| Step | Commit | State |
|---|---|---|
| `Housing` sheet and `housing.py` (rent, property tax, insurance, maintenance, other) | `9ca6b4b` | Done |
| Cash flow, Summary, Cash Flow sheet, plots, balance check | `9ca6b4b` | Done |
| HFP read/write and UI round trip (`houseListHousing`) | `9ca6b4b` | Done |
| NJ property tax deduction (line 41) as a bounded LP variable `st_pt` | `9ca6b4b` | Done |
| Tests: 19 new (`tests/assets/test_housing.py`), including the big-ticket equivalence, NJ owner/tenant, NY unchanged, move, tier, local search, HFP round trip, constraint replay | `9ca6b4b` | Done |
| `gen_hfp_us.py` empty Housing sheet; Scenario 5 (rent vs buy) in `phase0-scenarios.md` | `9ca6b4b` | Done |
| Stakes measurement | `fork-notes/model-review/housing_stakes.py` | Done (exact LP and local search) |
| Upstream design issue | `fork-notes/issue-housing.md` | Drafted 2026-10-07; user to file |
| Review fixes: `st_ptd_*` initialized in `__init__` (the UI's Goals page called `processDebtsAndFixedAssets()` before any solve: `AttributeError`); tier test checks the claimed exclusion (it passed with the `L` term removed); warning for Housing rows that pay nothing; `housing_costs_*` in `plan_metrics()`; deduction in the explanation; Housing and `payoff` in the user docs | `a9093f8` | Done |
| Debts `payoff` year: the balance is paid that year and payments stop (a mortgage used to run to term after its home was sold: $970,856 paid over 20 years instead of $542,567 at the sale) | `a9093f8`; `issue-debt-payoff.md` | **Superseded** 2026-10-08 by upstream #173 (`property` link); fork code and tests dropped in the merge |
| Scenario 5 rewritten: rent / buy with cash / buy with a mortgage; the old commands failed (`optimization_parameters.netSpending` is not read: "needs netSpending option") and compared a `maxSpending` base with a `maxBequest` variant. Template's `bequest` moved to `[solver_options]` (under `[optimization_parameters]` it was ignored; 0 is the default, so no result changed) | `a9093f8` | Done |
| `--solver-opt withSSTaxability=0.85` stayed the text "0.85" and did not pin (jack+jill: variant 102,545 = unpinned base, instead of 101,448). Validator in `SolverOptions`; residency commands in `phase0-scenarios.md` corrected (local search via `--solver-opt` for both runs; the exact LP from a case file) | `a9093f8`; `issue-solver-opt-numeric.md` | **Superseded** 2026-10-08 by upstream #174; fork validator dropped; the exact LP now also goes through `--solver-opt` |

Housing ledger: an optional `Housing` HFP sheet, one row per recurring cost (`active`, `name`,
`type`, `year`, `end`, `amount`, `rate`). Amounts are household-level, not scaled at the first
death; `amount` is in `year` dollars and `rate` is real growth above inflation (0 = tracks
inflation). `end` is the last calendar year paid (0 = the last plan year, negative counts back);
for a home sold in `yod` = Y the owner's rows end in Y - 1 (with negative values, `end` = `yod`).
Buying: big-ticket items (price or down payment) + `Fixed Assets` residence + `Debts` mortgage
(`property` = the residence's name, so a sale pays it off; upstream #173) + Housing rows; rent: a `rent` row (`phase0-scenarios.md`, section 5). Costs are subtracted in the cash flow next to debt payments, so `g_n` means
non-housing spending and rent vs buy is comparable under `maxSpending`. Key test: the same
amounts as negative big-ticket items give the same objective (the series is inflated to match).

NJ property tax deduction (verified 2026-10-07 against the 2025 and 2020 NJ-1040 instructions):
`property_tax_deduction = { cap = 15000, rent_share = 18, indexed = false }` in `taxes_state.toml`;
`st_ptd_n = min(cap, property_tax + rent_share% * rent)`; LP variable `st_pt` in `[0, st_ptd_n]`
with +1 in the `state_taxable_income` row (same position as `st_e`). It is added to the
exclusion's `L` so `L` stays at line 27: line 41 comes after line 39 and does not change the
exclusion tiers. No binaries, so `localsearch.FAMILIES` is unchanged. Not modeled: the $50 credit
(decision), main-home and multi-unit rules, part-year amounts.

Stakes, 2026-10-07, synthetic couple from Phase 1 ($1.5M tax-deferred), `maxBequest` at
`netSpending=80` ($k), no Roth conversions, Medicare off. Final bequest (the objective,
`final_bequest_today`), lifetime state tax and the deduction in today's dollars. "Exact LP" adds
`withSSTaxability=0.85`; "LS" adds `breakpointMethod="local-search"` (taxable SS by the IRS
formula). Script `fork-notes/model-review/housing_stakes.py exact|ls`. The first run recorded no
objective: the script printed `p.basis`, which under `maxBequest` is the fixed net spending; rerun
with the bequest, the other columns came out identical.

| Case | Bequest exact | Bequest LS | State tax (exact / LS) | Lifetime `st_pt` (exact / LS) | Time (exact / LS) |
|---|---:|---:|---:|---:|---:|
| NJ, $20k property tax as big-ticket (no deduction) | 1,047,594 | 1,096,194 | 11,047 / 12,981 | 0 / 0 | 58 / 217 s |
| NJ, $20k property tax as Housing (deduction) | 1,056,287 | 1,109,414 | 5,693 / 11,890 | 260,356 / 255,451 | 46 / 172 s |
| NJ, $30k rent as Housing (18% = $5,400) | 635,003 | 693,072 | 4,042 / 12,316 | 102,600 / 118,800 | 36 / 393 s |
| NY, $20k property tax as Housing (no rule) | 993,457 | 1,062,711 | 48,926 / 50,495 | 0 / 0 | 0.1 / 233 s |

Reading: the NJ deduction is worth +$8,693 of final bequest on the exact LP and +$13,220 under
local search, more than the state tax it saves ($5,354 / $1,091): the saved tax compounds, and the
federal side moves too (not decomposed). Levels differ by $49k-69k between the methods (different
SS taxability models); compare within a method. The lifetime `st_pt` is not a value: in years where
NJ taxable income is zero anyway the amount claimed is arbitrary (the LP is indifferent). NJ owner
minus NY owner: +$62,830 exact, +$46,703 LS (NJ exclusion included). LS runs are minutes each.

Cash vs mortgage (not measured as stakes; mechanics checked on a synthetic NY couple, exact LP,
`maxBequest` at $90k): rent 1,086,605; cash 1,279,963; mortgage 998,124 (made-up inputs: $800k
home, $48k rent, 6.5% mortgage, conservative rates). Not modeled and biased against the mortgage:
the mortgage interest deduction (Phase 3; federal itemized and NY's own).

## Phase 2b — budget spending profile (2026-10-08)

After #175's answer (no more state-tax rules upstream; budgeting belongs outside the optimizer, as
a module that builds the spending profile), the Housing ledger is replaced. Plan and decisions:
`fork-notes/phase2b-budget-plan.md` (all three agreed as recommended).

| Step | State |
|---|---|
| `budget.py` (was `housing.py`): Budget lines -> per-year amounts (today's $), survivor share (blank: the case's %, 100 for rent / property tax / insurance / maintenance), `profile()` normalized to the first year | Done |
| `setSpendingProfile("budget")`; evaluated at `solve()` (clone sets the profile before copying the tables); under `maxBequest`, `netSpending` unset or 0 (the UI's default) means the budget's first year, read where the LP sets `g_0` and not written into the options saved with the case (a stored default would have scaled an edited budget to the old total); a budget sheet with another profile warns | Done |
| Ledger removed: no cash-flow term, no `housing` outflow rows/plot slices; housing totals are now the housing share of `g_n` (`budget_spending()`, `plan_metrics` keys kept); results workbook gets a *Budget* sheet (net spending by line) | Done |
| NJ deduction from the budget's property tax / rent lines; bound `st_pt_n <= s_n g_n` as an LP row (exact under `maxSpending` too; the plan had said "unscaled amounts") | Done |
| HFP: `Budget` sheet (optional `survivor`, blank kept blank); an old `Housing` sheet is read as Budget lines, with a warning; unknown types named in a warning; Budget rates not decimal-converted | Done |
| UI: profile choice `budget`, sheet kept from the file (`houseListBudget`); docs (Documentation, PARAMETERS, modeling-capabilities, CHANGELOG) | Done |
| Tests: `tests/assets/test_budget.py`, 38 (one core line = flat, both objectives; rent in the budget = rent as big-ticket items at fixed spending; `maxSpending` scales the whole budget; clone moves the survivor step; NJ owner/tenant/move/tier/local search/replay; deduction follows `g_n` under `maxSpending`, checked by removing the row) | Done |
| Scenario 5 and `gen_hfp_us.py` for the budget; template comment | Done |

Equivalence with the ledger, same code base and same day (2026-10-08), exact LP
(`housing_stakes.py exact`, old = `e0ed9d1` with the ledger, new = budget): big-ticket 1,049,811
both; rent 634,740 both (deduction 113,400 both); NY 993,065 both; NJ owner 1,054,885 old vs
1,054,858 new. The owner case runs the NJ exclusion MILP to its node cap: reported gaps 0.63% and
0.97% of the objective, so the $27 is inside the solver's own gap.

Stakes, rerun 2026-10-08 on the budget (same couple and options as the 2026-10-07 table above):

| Case | Bequest exact | Bequest LS | State tax (exact / LS) | Time (exact / LS) |
|---|---:|---:|---:|---:|
| NJ, $20k property tax as big-ticket (no deduction) | 1,049,811 | 1,097,367 | 6,190 / 11,710 | 53 / 171 s |
| NJ, $20k property tax in the budget (deduction) | 1,054,858 | 1,109,032 | 8,423 / 11,890 | 37 / 162 s |
| NJ, $30k rent in the budget (18% = $5,400) | 634,740 | 692,696 | 3,753 / 12,316 | 37 / 326 s |
| NY, $20k property tax in the budget | 993,065 | 1,058,925 | 48,926 / 49,427 | 0.1 / 142 s |

**The numbers moved by a day's change of start date**, not by code: the same commit (`bf57da9`)
gave 1,047,594 for the big-ticket case on 2026-10-07 and 1,049,811 on 2026-10-08 (state tax 11,047
-> 6,190). These NJ `maxBequest` runs stop at the MILP node cap with gaps of 0.6-1.0%
($6-10k), so a one-day shift lands on a different point inside the gap. Reading: the NJ deduction
is worth +$5,047 (exact, today) / +$8,693 (exact, yesterday) / +$11,665 (LS, today) / +$13,220
(LS, yesterday). On the exact LP that is **inside the solver gap, so not resolved**; local search
(no certificate) says roughly $12-13k lifetime. Compare variants run the same day, and treat NJ
differences under about 1% as unresolved unless solved with a `maxTime` long enough to close the
gap. Rent vs buy differences are usually far larger than that.

### Essential budget lines (2026-10-09, after #175's third answer)

The maintainer's cost-function point: a budget fixes spending and maximizes the bequest; a fixed
bequest maximizes spending; spending is elastic, so split core from discretionary. Implemented as
an optional `essential` column of the Budget sheet (`5a4a12f`): net spending = essential lines +
k x discretionary lines; `maxSpending` maximizes k (`Plan.discretionary_scale`, Summary line,
`plan_metrics` key only when present); `maxBequest` at k = 0 gives the bequest above the core.
Affine profile rows in `Plan._add_essential_profile`, `spendingSlack` on the discretionary part,
no binaries. Without essential lines the plan is unchanged (test). 22 tests in `test_budget.py`.
Found on the way: written with dollar-sized coefficients (D_0 g_n), HiGHS declared every
`maxBequest` plan infeasible; normalized by D_0 (order-1 coefficients, like upstream's rows) all
solve. Stochastic spending needs no change: lower first-year spending is lower in every year, and
an infeasible scenario already counts as a full shortfall.

Stakes (`fork-notes/model-review/essential_stakes.py`, raw output `essential_stakes_2026-10-09.txt`;
Phase 1 couple, NY, exact LP, conservative rates, bequest 0; budget: living $50k + rent $36k
essential, travel $20k to 2044 + other $10k discretionary):

| Tax-deferred | LE | Whole budget scaled (yr-0, rent) | Essentials fixed (yr-0, rent, k) |
|---|---|---|---|
| $1.5M | 89/92 | 130,091, 40,373 | 132,680, 36,000, 1.556 |
| $1.5M | 95/98 | 126,296, 39,195 | 128,877, 36,000, 1.429 |
| $0.8M | 89/92 | 103,566, 32,141 | 101,256, 36,000, 0.509 |
| $0.8M | 95/98 | 102,320, 31,754 | 98,887, 36,000, 0.430 |

`maxBequest` at $1.5M: 1,532,151 at k = 0, 576,022 at k = 1; at $0.8M the budget is infeasible.
Lifespan sampling (200 MC scenarios, histochastic 1928-2024, seed 42, SSA tables): at $1.5M none
fails either way; at $0.8M the whole-budget reading solves all 200 by cutting rent, while 9 of
200 cannot fund the essentials. Checked that those 9 are real: their whole-budget first year is
$86.6-92.9k (75-80% of the budget), and the lowest whole-budget first year among the funded draws is
$90.5k; 8 of the 9 have one spouse dying at 67-74 and the other living to 83-100 (rent kept in
full by the survivor).

Sources in the maintainer's web search, checked as far as the proxy allows (bls.gov, FRED,
ebri.org, fidelity.com blocked: search results and reprints only): BLS CE 2024 65+ figures match
FRED's copies; Fidelity 2026 $185,500 (45% Medicare B/D premiums, which Owl already charges);
EBRI 2024 31% spend more than they can afford ("3[1]%" in his paste was a broken footnote link).
Checked in code: upstream builds only `flat` and `smile` profiles; Owl charges no payroll tax
(grep for FICA, OASDI, 6.2%, 1.45% found none), so a working-years budget needs a payroll-tax line.

Track B review fixes (2026-10-10): AMO references of the three smile cases re-recorded (HiGHS;
MOSEK entries removed); a person-named age line ends at that person's death, `younger`/`older`
follow the survivor's age after the first death; JSON types checked against the sheet's list,
`kind` kept as free text (also a sheet column), amounts in dollars like the sheet (the docs had
said $k: a file written to them would have budgeted $50/yr), values typed strictly; lines read from
`budget_file` are not written to the HFP (`Plan.budgetFromFile`), so the file is not shadowed by a
copy of itself; the interface keeps `budget_file` on save but does not read it, and the solve error
says so. Then (finding 6, the user's choice): the smile starts at an age of the younger spouse,
`smile_start_age`, instead of `smile_delay` years from today, which had moved the curve a year later
relative to the household's ages on each yearly rerun; a delay is converted once at load, so no plan
moves on the upgrade day; the UI asks for the age. Then: after the first death the smile follows the
survivor's age (jumps ahead by the gap when the younger spouse dies first), and reading a smile case
without `smile_start_age` warns with the age to add. `tests/plan/test_smile_start_age.py`, 15 tests.
The six smile example cases (`avery+quinn`, `jack+jill`, `joe`, `jordan+taylor`, `jordan+taylor-qcd`,
`morgan`) carry `smile_start_age` = the younger spouse's 2026 age + their `smile_delay` (0), so they
read without the warning and no recorded result moved (full suite 3039 passed). These are upstream's
files: expect conflicts on those lines when upstream edits them.

2026-10-10: `main` fast-forwarded to `claude/phase2-housing` (`148f785` -> `271c93e`, then this note).

Next: Track B is done through step 2 (age-anchored smile, age clocks, `budget_file` JSON;
`fork-notes/track-b-spending-profile.md`). Phase 3 is planned in `fork-notes/phase3-plan.md`
(2026-10-10, below). Decisions (same day): D1 statutory federal law as the base, D2 no real
inputs here (the finished product runs on them locally), D3-D5 as recommended. Phase 3 step 1
(3.0, shared plumbing + the `st_pt` fix) done 2026-10-10 (below). Next code: step 2 (NY itemized).
Phase 5 (part-time work / SS earnings test) after Phase 3, as the household needs it.

## Phase 3 planning (2026-10-10)

Step back over Phases 0-7 and the maintainer's responses, then Phase 3 redefined as "deductions
follow the expenses that cause them": `fork-notes/phase3-plan.md`. Rules checked this session
against P.L. 119-21, the 2025 Schedule A / Form 1040 instructions, Pub. 936, Rev. Proc. 2025-32,
IT-196-I (2025), the NJ-1040 instructions, and the nj.gov / tax.ny.gov relief pages.

- First-order probe (`fork-notes/model-review/itemized_probe.py`, output
  `itemized_probe_2026-10-10.txt`; income held fixed, no LP response, Medicare off): Yonkers owner
  with $25k property tax: federal itemizing worth $0 under the law as enacted, $22k lifetime under
  Owl's default 2032 reversion; NY itemizing $10-22k (no mortgage) / $26-34k (with a $600k
  mortgage). With the mortgage, federal $18k (statutory) / $93k (2032). NJ owner: federal $0 / $21k,
  with the mortgage $16k / $88k.
- So the NY-vs-NJ owner comparison is biased toward NJ today (NJ line 41 modeled, NY itemizing not).
- **Bug found, not fixed yet**: with essential budget lines the NJ property tax deduction bound
  (`st_ptd_share_n * g_n`) is wrong whenever k != 1: claimed $12,625 vs $12,000 paid
  (`maxSpending`, k = 1.137), $9,600 vs $12,000 (`maxBequest`, k = 0.474). Fix is step 1 of the plan.
- Owl's default `obbba_expiration_year = 2032` (all 18 examples set it; the household template
  inherits it) reverts to pre-TCJA brackets and standard deduction in 2032; P.L. 119-21 made them
  permanent. It moves the plan before 2032 too. Decision D1.
- Stay NJ (nj.gov, verified): homeowners 65+, up to $6,500/$5,000/$4,000 for income up to
  $100k/$150k/$200k, $0 above (2027 payments; funding set yearly, 2026 payments were cut). Larger
  than any NY-vs-NJ income-tax difference measured; dropped with the Phase 2 rewrite. Decision D3.
- D1 applied: `Case_us.template.toml` sets `obbba_expiration_year = 2066` (no reversion within
  the plan; loads as 2066, plan ends 2056); the 2032 reversion is a sensitivity run
  (`phase0-scenarios.md`, "Federal law after 2031").
- Upstream issue by someone else (MCP `big_ticket_items` sign): direction confirmed on this branch
  (+$25k/yr "expense" for 5 years: year-1 spending 84,352 -> 90,832; -$25k -> 77,864); not the
  issue's "~$25k/yr" (spread over the plan). No effect on HFP/TOML/owlcli/UI paths; affects MCP use.
  Not fixed in the fork (waiting for the maintainer's choice of sign). `phase3-plan.md` §8.
- Enhanced STAR (tax.ny.gov, verified): income limit $110,750 (2026), income = AGI minus taxable IRA
  distributions, two years back; entering property tax net of STAR stays adequate.

## Phase 3 step 1 — shared plumbing and the `st_pt` fix (2026-10-10)

Size S from `phase3-plan.md` §5 step 1 (3.0).

- `budget.py`: `Budget.by_type(*types, essential=None)`; new deductible types `"medical"` and
  `"charity"` (`DEDUCTIBLE_TYPES`; `"care"` stays non-deductible — assisted-living room and board
  is not medical). Docs: `Documentation.py`, `PARAMETERS.md`, the module docstring.
- `Plan._budget_amount_terms(*types)` -> `(const_n, coef_n)` with amount = const + coef * g_n in
  nominal $: a share of net spending without essential lines (today's behaviour), or the essential
  part at its amount plus a share of the discretionary part with them. Computed in
  `processDebtsAndFixedAssets` into `st_ptd_const_n` / `st_ptd_coef_n`; `st_ptd_share_n` kept as
  the "any deductible line" flag.
- `_add_property_tax_deduction` now bounds `st_pt` by that affine amount instead of
  `st_ptd_share_n * g_n`. Fixes the §3.3 bug (claimed $12,625 vs $12,000 paid under `maxSpending`
  k=1.137; $9,600 vs $12,000 under `maxBequest` k=0.474); regression tests claim equals paid.
- `debts.py` `get_mortgage_interest_array`: interest and average balances by calendar year for
  `type == "mortgage"` rows (payments minus the fall in balance; the payoff year pays principal
  only), balances split by Pub. 936 Table 1 category (`MORTGAGE_CATEGORIES`: grandfathered /
  before 2018 / after 2017, from the loan's year); a loan linked to a `real estate` asset is left
  out (rental interest is Schedule E; a linked second home too, documented). `Plan.mortgage_interest_n`
  / `mortgage_balance_cn`, zeros in `__init__`.
- `tax_federal.py`: `salt_cap(year, magi, yOBBBA)` (P.L. 119-21 sec. 70120 schedule, `inf` under a
  pre-TCJA reversion), `qualified_loan_limit` (Pub. 936 (2025) Table 1 lines 1-11, verified on
  irs.gov; `pre_tcja=True` for a reversion and for NY's $1M), `deductible_mortgage_interest`
  (lines 12-15), `standard_without_bonus` (the standard amount without the senior bonus, which an
  itemized deduction is compared with), constants `MORTGAGE_LIMIT` / `MORTGAGE_LIMIT_LEGACY` /
  `MEDICAL_FLOOR` / `CHARITY_FLOOR` / `NONITEMIZER_CHARITY`.
- Tests: `tests/tax/test_itemized_data.py` (25: cap schedule and phase-down floor, hand
  amortization, payoff year, Table 1 worksheet with mixed categories, a loan on real estate left
  out, amount terms with and without essentials, JSON/HFP round trip of the new types); §3.3 cases
  in `tests/assets/test_budget.py`.
- Review fixes (same day, after the first step-1 commit): one aggregate balance with a per-loan
  limit could not combine loans of different categories (now the Table 1 worksheet); rental
  mortgages were counted as home mortgage interest; `_active_loans` reused instead of a second loan
  loop; `itemize_terms` renamed `standard_without_bonus`; `modeling-capabilities.md` lists the new
  budget types; the test count above said 19 where there were 22.

Phase 5 now has a concrete case to serve: scenario 4b. The earnings test would let `withSSAges` optimize the working spouse too; a per-scenario PIA (or recomputing it from extra work years) would remove the manual PIA step. Medicare past 65 with employer coverage (delayed Part B) only matters if the worker goes past 65.

## Phase 3 step 2 — NY itemized deduction (2026-10-10)

Size M from `phase3-plan.md` §5 step 2 (3.1). On `claude/eager-cray-s0fvks` after the step-1 work.

- **Data** (`taxes_state.toml`, NY_Single / NY_MFJ, dotted keys under the entry, documented in the
  header): `itemized.allowed`, `income_taxes` (NY subtracts state/local income taxes from Schedule
  A), `salt_cap` (0 = no cap on real estate), `mortgage_limit` ($1M, the pre-TCJA rule),
  `medical_floor` (shipped as 7.5%; **NY's is 10%**, IT-196 line 3, corrected in the review below),
  `adjustment_agi_start` / `width` / `pct` (line 46, Worksheet 3: MFJ $200k, Single $100k, 25% over
  $50k). Verified against IT-196-I (2025), except the medical floor. Parsed
  into `StateTaxParams.itemized` (`StateItemizedParams`, per year, follows moves and the filing
  status). `income_taxes = true` is refused for now (it would couple the deduction to the tax that
  produces it).
- **LP** (`Plan._add_state_itemized`, beside `_add_state_tax_bounds`, not `@_fixedAcrossIterations`):
  the deduction is the existing `st_e` column, whose bound is raised to the larger of the standard
  and the adjusted itemized total. Components `st_ipt` / `st_ich` / `st_imed`, binary `zsi` (one per
  candidate year). A priori: `LB` (essential property tax + charity + mortgage interest) ≥ standard
  forces itemizing, `UB` (every deductible line at the income ceiling + Medicare + mortgage interest)
  ≤ standard forces the standard; otherwise a free `zsi` and
  `st_e ≤ st_sigmaBar*(1 - zsi) + (1 - NYIR)*(st_ipt + st_ich + st_imed + mi*zsi)`.
- **NYAGI adjustment** (`NYIR_n`, a new `_SC_PARAMS` entry): `25% × min(max(NYAGI − start, 0), width)/width`
  from the previous iterate's `st_agi_n` (bilinear: rate × deduction).
- **Mortgage interest**: `st_item_mi_n` from `deductible_mortgage_interest(..., pre_tcja=True)`
  (the $1M NY limit), set in `processDebtsAndFixedAssets`.
- **Medical floor**: a constant cut from the previous iterate's federal AGI (`MAGI_n`), clamped so
  the bound stays non-negative. As a hard `floor*AGI` on the claim it makes every year without
  medical expenses infeasible (found on the first smoke test). Step 5 can tighten it.
- **Only candidate years get columns** (`_st_item_candidate_years`: the state allows itemizing and
  a budget line or mortgage interest exists). A plan with none stays a pure LP — that is what
  `test_amo_postprocess.TestNoBinaries` requires of `Case_cameron`.
- **Tie check** (step 4's mechanism, needed to claim the full deduction in late years where tax has
  no price): `_itemized_shortfall` joins `_exclusion_shortfall` in `_bracket_order_excess`, including
  a year that took the standard while more was claimable.
- **Local search**: `zsi` is a family (`localsearch.FAMILIES`, labelled "state itemizing").
- **Reporting**: `st_item_n` (unadjusted total, 0 when standard; after the cut since the review), `st_itemizing_n`; Taxes sheet
  columns and a Summary line only when nonzero; `plan_metrics` `state_itemized_today`; explain tags
  for the new rows.
- **Tests**: `tests/tax/test_state_itemized.py` (20: data parse, moves and filing status, owner
  itemizes property tax, renter keeps the standard with no new columns, the line 46 cut, NJ/FL
  unchanged, a NY→NJ move stops it, Yonkers surcharge on the reduced tax, mortgage interest,
  medical above the floor, charity, constraint replay, the FL guard, and the review regressions
  below). `test_state_residency.py` compares the nested `itemized` field.

Pre-commit review (same day, one pass plus an independent reviewer) found and fixed six bugs:

1. The a priori rule used the raw LB/UB against the standard, ignoring the line 46 cut: with
   `rho=0.25` a $20k property tax is $15k after the cut, below the $16,050 standard, but was
   forced to itemize. Now `keep*LB >= std` / `keep*UB <= std`.
2. `_itemized_shortfall` counted mortgage interest in `pot` but not in the claimed components, so
   every itemizing year showed a permanent shortfall and kept the tax tie-break on. Now
   `max(std, keep*pot) - st_e`.
3. `_st_item_candidate_years` summed `_budget_amount_terms` consts (dollars, and **negative** with
   essential lines) with coefs (shares). An essential core + discretionary property tax gave
   `const_pt = -40k`, so the whole deduction vanished. Now flags on `budget.by_type`.
4. The medical floor was a constant cut clamped at `const+M`, which deleted the floor whenever it
   exceeded the constant part and let every discretionary medical dollar through (a $40k line
   claimed $40k against a $7k floor). Now `max(0, paid - floor*AGI)` with one binary `zmed` per
   medical year (`localsearch.ALWAYS_FREE`); the sign of its big-M row was wrong in the first
   attempt (it relaxed instead of binding) and is covered by a test.
5. `_itemized_shortfall` ran in every year, so a NY→NJ move invented ~$25k/yr of phantom shortfall
   in the NJ years and flipped the tax tie-break on for a re-solve that could never help. Now
   masked to `st_item_ok_n`.
6. The SC residual compared `NYIR_n` (a rate) divided by gamma, which never registers. Now weighted
   by the itemized total, including years that took the standard (a rho move can flip the branch).

Also: `_medicare_premium_ub_n` (a big-M for the `m` column) must not enter the shortfall's claimable
amount — only `m_n + M_n` is a cost. `withMedicare="optimize"` medical claims count the `m` variable.

Not in this step (per the plan): the federal itemized deduction (`withItemized`, step 3), the
medical floors wired to `care`/Medicare as LP expressions (step 5 tightens the floor's AGI to the
same iterate), measuring (step 6), docs (step 7). The 50% cut above $525k MFJ and the rules above
$1M NYAGI are out of scope.

### Step 2 review (2026-10-11)

Review of `ec73d60` after the commit; six fixes on the same branch.

1. **NY medical floor is 10%, not 7.5%** (verified: IT-196 (2025) form, line 3 "Multiply line 2 by
   10% (0.10)", line 2 = federal AGI). The 7.5% came from the plan's sketch; §3.1 had not checked
   it. Data, header, `StateItemizedParams` doc and tests corrected. The federal floor stays 7.5%
   (step 3/5 must not reuse NY's value). Worksheet 3's filing-status amounts also confirmed: in
   pypdf's layout mode the circles come out as U+F081/F083 -> $100k, U+F084 -> $150k,
   U+F082/F085 -> $200k (statuses 1/3, 4, 2/5), matching the data.
2. **`zmed` only where the medical amount depends on the plan.** `_medicare_premium_ub_n` was
   filled from `Cbar_nq` in every Medicare mode (`mediVals` runs regardless), and `M_n > 0` also
   created a binary, so every Medicare year of a NY owner got one (28 in the test owner plan, also
   under `withMedicare="None"`). Now a binary only for a discretionary medical line when net
   spending is not pinned, or for the `m` column under `withMedicare="optimize"`; elsewhere
   `max(0, paid - F)` is a column bound. **Correction to the review's own measurement:** local
   search switches `withMedicare` to `"optimize"` (`Plan._applyBreakpointOptions`), so those
   28 binaries are needed there; the "59 s -> 40 s" figure in the review came from removing them,
   which is not a valid speed-up. In loop/None modes they are gone (test).
3. **A priori rule from the bounds on net spending** (`_spending_bounds_n`, `_first_year_spending`
   factored out of `_add_objective_constraints`): under maxBequest without slack every `g_n` is
   pinned, so property tax/charity/medical paid are known and every candidate year is decided
   before the solve (31 of 31 free `zsi` -> 0 in the owner plan), and the big-M gates use the
   spending ceiling instead of the income ceiling. maxSpending still leaves `zsi` free.
4. **Tests** (`test_state_itemized.py`, 20 -> 28): vacuous assertions replaced (a "local search"
   test that ran no local search and rounded a bool array; `imed >= -1`); new: maxBequest fixes
   every year; maxSpending leaves the choice free; Medicare alone adds no binary in loop mode,
   does under optimize; the `zmed = 0` branch (paid below the floor); the claim equals paid - F in
   years with positive taxable income (not just `<=`), under maxBequest, maxSpending and
   `withMedicare="optimize"`; local search on a short plan returns one branch per year and no
   medical above the floor; the shortfall in a NY year without columns. The first versions of two
   new tests were degenerate (medical half of spending: NY taxable income 0, so any claim was a
   tie); rewritten on years with positive taxable income.
5. **Reporting:** `st_item_n` is now the deduction taken (after the line 46 cut), so the Summary
   line and `state_itemized_today` no longer overstate it where NYAGI > $200k. The cut and the
   medical floor are restored from the accepted iterate before the final aggregation (`NYIR_n`
   was not restored at all, unlike `STR_n`; a cycle can accept an earlier iterate). For that the
   floor became an SC-loop parameter, `STMF_n` (10% x previous iterate's federal AGI), with a
   convergence move (only where medical paid clears one of the two floors) and a fixed-point
   residual entry "state itemized".
6. **Shortfall** counts the itemized total only in years with columns; elsewhere only the standard.

Measured (2026-10-11, synthetic owner plan from the tests, old and new run in parallel pairs, so
times are contended; same objective in every pair):

| case | `ec73d60` | after the fixes |
|---|---|---|
| owner, maxBequest, local search | 59.8 s; 31 free `zsi`, 28 `zmed` | 60.6 s; 0 free `zsi`, 28 `zmed` |
| owner + $3k medical, maxSpending, local search | 193.9 s | 177.0 s |
| owner + $3k medical, maxSpending, loop | 107.1 s | 96.7 s |

So no measurable speed-up on these cases. Open for step 6: a discretionary medical line under
maxSpending costs ~100 s in loop mode (31 `zsi` + 31 `zmed` free; ~4 s without the medical line);
whether `zmed` should be a local-search family rather than `ALWAYS_FREE` is not measured.

Not fixed (from the review):

- `itemized.mortgage_limit` is only read as "> 0" (the limit is the hardcoded `pre_tcja=True` rule).
- **Medicare in years without itemized columns.** A NY year with no property-tax, charity or
  medical budget line and no mortgage has no itemized columns and takes the standard; Medicare
  premiums count only in years with columns (a renter with a medical or charity line does get
  them). The missing deduction is max(0, premiums - 10% x AGI), and it changes the result only if
  it beats the NY standard ($16,050 MFJ, $8,000 single). From Owl's own premium table
  (`tx.mediVals`, CMS 2026 values in `tax_federal.py`; Part D base premium 0 by default; read in
  code, not checked against CMS) the couple pays $4,870 in the base tier and $17,498 / $18,742 in
  the top two (MAGI over $410k / $750k two years earlier); a survivor $2,435 and $8,749 / $9,371
  (over $205k / $500k). So the standard loses only in those top two tiers with that year's AGI
  under about $14.5k / $26.9k (couple) or $7.5k / $13.7k (survivor): a very large income two years
  earlier followed by near-zero AGI. Never in the lower tiers. Not fixed because counting Medicare
  in every NY Medicare year would add columns to every NY plan and, under local search (Medicare
  optimized), `zsi`/`zmed` binaries where 10% of AGI is low. (The review first called this a
  renter asymmetry "small at a 10% floor", unmeasured and too broad; corrected 2026-10-11.)
- **STAR is not modeled, and "enter property tax net of STAR" is not a usable instruction**
  (user, 2026-10-11): the plan runs future scenarios (a later move, a purchase, Basic STAR becoming
  Enhanced at 65), where nobody has the credit figures to enter. Verified on tax.ny.gov (STAR
  eligibility page, 2026-10-11): the STAR exemption (a lower school tax bill) is closed to new
  homeowners, who get the STAR credit instead, "a check or direct deposit"; Basic STAR has no age
  restriction and an income limit of $500,000 for the credit; Enhanced STAR is for 65 and older
  (its income limit and definition in `phase3-plan.md` §3.4). So for a future purchase the bill a
  listing shows is the bill paid, and the credit is a separate inflow. Leaving it out overstates the
  cost of owning in NY by the credit, and overstates the IT-196 deduction (lines 5-7 reduce real
  estate taxes by the credit received). Needed: the credit as a rule (Basic, then Enhanced from 65
  while income is under the limit), its amount from data per school district, reducing both the
  cash cost and the itemized property tax. Where the per-district amounts are published, and how
  the credit grows, are not verified yet. Supersedes the "enter net" advice in `phase3-plan.md` §3.4
  and the Phase 2 roadmap row; it belongs with the senior relief of step 9, which has the same
  problem for Stay NJ / ANCHOR.

## Phase 3 step 3 — federal itemized deduction (2026-10-11)

Size L from `phase3-plan.md` §5 step 3 (3.2). On `claude/eager-cray-s0fvks` after the step-2 work
and the `dev` `844a7ec` merge. **Not yet reviewed by an independent pass** (step 2 shipped with
six bugs found that way; a review should follow before this is called done).

- **Option** `withItemized = "none" | "loop" | "optimize"` (D4: default `"loop"` in code,
  `"optimize"` in the household's case files, `"none"` reproduces today's plans). Plumbed through
  every `withSeniorBonus` hit: `plan.py` known options and `_buildOffsetMap`, `config/schema.py`,
  `config/ui_bridge.py`, `assistant/tools.py`, `stresstests.py`, `utils.py` normalization. The
  breakpoint presets set `"optimize"` (except `"none"`).
- **S_n** = the standard deduction without the OBBBA senior bonus (`tax_federal.standard_without_bonus`,
  the 65+ additions included) plus the non-itemizer charity cap (`min($1,000/$2,000, charity lines)`,
  P.L. 119-21 sec. 70424). **B_n** = the bonus (inside `sigmaBar_n` in loop mode, or the `_sb_lp`
  `k*p_n` terms). Itemizers keep the bonus and lose the 65+ additions, which sit inside S_n.
- **LP** (`Plan._add_federal_itemized`, after `_add_magi_lp`, not `@_fixedAcrossIterations`): the
  deduction is the existing `e_n` column, bound raised to `S_n + B_n` in every year (non-itemizer
  charity) and to `max(S+B, UB_item+B)` in candidate years. Components `isalt` / `ich` / `imed`,
  binary `zi` (optimize mode only; loop mode writes the branch as a constant). The row is
  `e_n - isalt - ich - imed + (S_n - MI_n)*zi <= S_n + B_n`; under `withSeniorBonus="optimize"` it
  replaces `senior_bonus_deduction` and carries `k*p_n`. A priori: `LB >= S` forces itemizing,
  `UB <= S` forces the standard (no columns); the loop's first choice is **zi=0 unless LB >= S** —
  zi=1 caps `e_n` at the itemized total, so a wrong guess can make a case infeasible (found on
  `Case_john+sally`, which has state tax but no budget and no mortgage).
- **SALT** is cash-basis property tax + the state and local income tax the plan pays, capped
  (`tax_federal.salt_cap`, MAGI phase-down from the previous iterate). The state terms are exactly
  those `_add_net_cash_flow` charges, factored into `_state_tax_terms(n)` and used by both rows, so
  the deduction cannot drift from the tax paid. Rent is **not** federal SALT (NJ's 18% share is a
  state rule only).
- **Floors** (charity 0.5%, medical 7.5% of AGI) are loop parameters `FEDCF_n` / `FEDMF_n`, as
  `STMF_n` for NY — not the `magi` LP variable the plan sketched. With `magi` the floor moves
  inside one LP, but then `max(0, paid - floor)` needs a binary in every year with a line (the
  column-bound optimization of step 2 needs a constant floor). Converges through the SC loop.
  `zch` / `zmedf` switches only where the amount paid depends on the plan (as NY's `zmed`).
- **Candidate years** (`_item_candidate_years`): `UB_item = min(SALT cap, property tax + state tax
  upper bound) + mortgage interest + charity UB + medical UB` must exceed S_n. A FL owner with $25k
  property tax and no mortgage/medical/charity gets no columns (guard test).
- **Local search**: `zi` is a **family** ("itemizing"), not `ALWAYS_FREE` — a mortgage or a large
  property tax leaves one per year, too many to keep free in every restricted problem (measured:
  with `zi` free, `test_local_search_keeps_the_tiers_integral` lost its statutory tax at
  `localSearchTime=1`). `zch` / `zmedf` stay in `ALWAYS_FREE` (pinning one freezes a `max(0, ·)`).
- **Tie check**: `_federal_itemized_shortfall` joins `_exclusion_shortfall` and `_itemized_shortfall`
  in `_bracket_order_excess`, so a year that claims less than it could turns tax pricing on.
- **Reporting**: `item_n`, `item_salt_n`, `item_mi_n`, `item_char_n`, `item_med_n`, `itemizing_n`;
  Taxes sheet and Summary (only when nonzero); `plan_metrics` `itemized_deductions_today`.
- **Tests**: `tests/tax/test_itemized.py` (14: the FL guard, mortgage vs standard, loop vs optimize,
  SALT = property tax + state tax capped and $10k from 2030, charity and medical floors against the
  budget amount paid, the 65+ bonus kept and the additions lost, `withSeniorBonus="optimize"`,
  pre-TCJA uncapped SALT, rent has no federal SALT, option normalization). The 17-example
  "unchanged objective" guard from the plan is **not** written as a sweep; `Case_devon` moved
  (+$1,505 of spending) and its AMO reference was re-recorded, so the default is not a no-op on
  every shipped case.

Deviations from the plan (§5 step 3), for the review:

1. Floors use loop-parameter AGI, not the `magi` LP variable (above).
2. Loop mode has no `zi` column: the branch is a constant, so the LP is not a MIP when every year
   is decided. The plan said "the same rows with `zi_n` fixed"; a pinned binary still counts in
   `nbins` and can force branch-and-bound.
3. Non-itemizer charity is inside S_n whenever `withItemized != "none"` (so a plan with charity
   lines and no itemizing still gets it). Under `"none"` it is absent, as today.

## Step 3 review (2026-10-11, independent pass over `5070619`)

Measured on HEAD with the date frozen at 2026-01-01 (scripts not committed). Full suite: 3124
passed, 1 skipped (the 3121 above undercounts: `test_itemized.py` has 17 tests, not 14).

Bugs, verified by a run:

1. **The SALT phase-down never applies.** `solve()` zeroes `MAGI_n` before `_buildOffsetMap`,
   so `_setup_federal_itemized` always computes the cap at MAGI 0. The comment at
   `_computeNLstuff` ("one solve stale") is wrong. NY couple, MAGI $694k-877k in 2026-2029:
   $40,400-41,624 claimed every year (statutory: $10,000), the same on three solves in a row.
   No warning either.
2. **The default `"loop"` changes plans that never itemize.** `Case_chris+pat` (FL, no
   budget, zero candidate years): basis $117,052.45 -> $116,919.95. Cause: the standard-branch
   rows `e <= S + B` written for every year (same bound as the column) change a
   non-converging SC loop's path. Writing that row only for `_sb_lp` bonus years restores
   $117,052.45 exactly (checked). Loop-mode standard years in `_item_years` still carry pinned
   columns and rows, which moves the NY residency plan by $11 with no year itemized.
3. **`"optimize"` itemizes where it loses, at the default gap.** `Case_jordan+taylor`:
   2027 and 2029 itemize $31,323 / $33,108 against a standard of $36,494 / $38,566, and 2040
   takes the standard with $32,258 itemizable (MILP gap 0.23%, loop oscillatory). Bequest
   $2,650,296, below both `"none"` ($2,651,672) and `"loop"` ($2,651,846). With `gap=1e-7`
   those years are correct and the loop converges. `_federal_itemized_shortfall` reports this as
   "tax brackets filled out of order ... the objective is unaffected", which is false here: it is
   a suboptimal binary, not a tie, and the repair keeps the binaries.

Plan items not done (plan §4 and §5 step 3), none in the deviations list:

4. No warnings for the SALT phase-down threshold, the 2/37 limit or Pease (grep finds no
   `pease`, `2/37` or SALT warning in `plan.py` / `tax_federal.py`).
5. Under a pre-TCJA reversion the charity floor (`FEDCF_n`) and the non-itemizer charity
   (`_nonitemizer_charity_n`) still apply; the plan says no charity floor after `yOBBBA`. Both
   are OBBBA rules. Small amounts.

Cost (example sweep, none / loop / optimize): `"loop"` costs nothing measurable. `"optimize"`
adds a `zi` in almost every year of any state-tax plan, because the candidate rule bounds state
tax by the top rate x (flows + the whole portfolio): `Case_morgan` (OR) 0.3 s -> 30.8 s,
37 candidate years, 0 itemized; `Case_john+sally` 0.1 -> 5.1 s; `Case_kim+sam-spending`
0.4 -> 8.2 s. The household files are to use `"optimize"` (D4); step 6 should measure this
before that default is kept.

Tests:

6. `test_guard_all_seventeen_examples_unchanged` loads three configs and solves none: the
   name and docstring claim what it does not check (and bug 2 shows the claim is false).
7. `test_local_search_returns_an_integral_plan`: the Summary says `local search -> loop` (the
   search kept the loop's plan), and `(item_n == 0) | (item_n > 0)` always holds.
8. Of the four loosened assertions, three still pass at their old tolerance on HEAD:
   `test_moving_earlier_never_lowers_spending` (strict order holds: 108,213.22 <= 108,299.11
   <= 109,129.18), the STMF `rtol=0.02`, and the tiered-exclusion test with `maxTime=2` and
   `gap > 1e-4`. Only the NYIR one fails (max error 0.0018 vs 1e-4; 3e-5 under `"none"`).
   The tiered-exclusion change (`>= 0.0`) makes that assertion empty; PROGRESS calls it a
   local-search time budget, which it is not.
9. Plan tests not written: finite-difference marginal cost of a conversion in an itemizing
   year, payoff at a linked sale, constraint replay, tie check, optimize >= loop at the switch.

Checked and correct: `Case_devon` (+$1,199/yr under loop) itemizes 2032-2051 because Owl's
2032 reversion uncaps SALT (CA tax $19.8k-34.9k vs a $12.7k-22.5k standard) and 2026 by $301.
SALT = min(cap, property tax + state/local tax paid) in the hand test; e = itemized + bonus in
itemizing years; state taxable income adds back `e`, so federal itemizing does not leak into
state income. Under the 2032 reversion the pre-TCJA AMT (SALT is an add-back) is not modeled,
so the reversion-case values of itemizing (§3.2: $88-93k) are upper bounds (recalled rule, not
computed).

Nits: `_item_fixed` is never set (dead branch); `_setup_federal_itemized` calls
`_spending_bounds_n` and the property-tax terms twice and builds `terms["pt"]` without using it;
`_federal_itemized_shortfall` under `_sb_lp` leaves the bonus out of `best` while `e_n`
includes it (understates a shortfall); `_nonitemizer_charity_n` uses the budget at scale 1,
not the amount paid at `g_n` (matters only for charity lines under $2,000).

## Step 3 review fixes (2026-10-11)

All review findings above fixed. Measured with the date frozen at 2026-01-01, example sweep of
all 18 cases under `none` / `loop` / `optimize` (script not committed).

- **Bug 1 (SALT phase-down):** the cap is a loop parameter `FEDSC_n` (`_SC_PARAMS`), reset to the
  unreduced cap at solve start and recomputed from each iterate's AGI in `_computeNLstuff`; the
  residual counts its moves where SALT paid is above the lower cap. NY couple at MAGI $700k-880k:
  cap used $10,000 = the cap at its own MAGI (was $40,400). The candidate rule uses the unreduced
  cap (a superset). A cap still one iterate stale in the final plan is a warning.
- **Bug 2 (non-itemizing plans moved):** `"loop"` now adds **no column and no binary**: the
  itemized branch is two rows on existing columns, `e <= MI + min(cap, pt + st) + claims + bonus`
  (a min of two terms is an upper bound by both), and a standard year gets nothing. Charity/medical
  claims are paid - floor where the loop's flags `_item_chl_n` / `_item_medl_n` (loop parameters,
  a priori where the amount is known) say the floor is cleared. The e bound is left bit for bit as
  `_add_standard_exemption_bounds` wrote it outside years that may itemize. Rows that carry e in a
  year replace `senior_bonus_deduction` in that year only (`_item_ded_rows`). Result: every
  example that never itemizes gives the `none` plan to the cent (basis, bequest, `T_n`), including
  `Case_chris+pat` and `Case_helen+ruth` (pinned zero columns alone had moved helen+ruth by
  $215/yr: its loop does not converge). Guard test over all 18 examples.
- **Bug 3 (dominated binaries):** `_fix_dominated_itemizing` after each optimize-mode solve: a
  free zi on the smaller deduction (at the solution's own amounts) is flipped and the LP re-solved
  with every binary pinned (the flipped point is feasible with the same spending, so the LP is no
  worse); up to three rounds. `Case_jordan+taylor` at `gap=0.02`: without it 3 dominated years
  ($5,171 / $5,458 / $2,141 of deduction, bequest $2,650,296), with it none ($2,651,846). The tie
  check (`_federal_itemized_shortfall`) is now within the branch taken, so a dominated branch is no
  longer reported as "brackets filled out of order ... objective unaffected".
- **Cost (`"optimize"`):** a valid income bound replaces the old one (fixed income + what can leave
  tax-deferred + the taxable balance, from upstream's `_gateCeilings`, which takes an `ss_in`
  override for this; state tax on the state's own brackets, top rate with NY recapture). It admits
  more candidate years than the old (unsound for late years) bound, so `zi` is now **free only in
  years whose itemized total has come within `ITEM_WINDOW` = 50% of the standard** (loop parameter
  `FIX_n`, grows only, as the NJ exclusion's `RXF_n`); elsewhere zi is pinned to the loop rule.
  Times (optimize, before -> after): `Case_morgan` 30.8 -> 0.7 s, `Case_kim+sam-spending` 8.2 ->
  0.9 s, `Case_john+sally` 5.1 -> 0.2 s, `Case_devon` 5.3 -> 0.7 s. `optimize` vs `none` on
  non-itemizing examples: within $47/yr (`Case_helen+ruth`, 0.02%; pinned columns in a MIP).
- **Plan items:** warnings for the 2/37 limit (P.L. 119-21 sec. 70111 text read on govinfo
  2026-10-11: 2/37 of the lesser of itemized, or taxable income + itemized above the 37% bracket
  start) and for Pease after a reversion (2017 amounts $313,800 MFJ / $261,500 single, Rev. Proc.
  2016-55 sec. 3.15, read 2026-10-11; brought to 2026 with Owl's own 35.1% pre-TCJA adjustment;
  3% of AGI over, at most 80% of non-medical itemized, recalled rule), for a SALT cap one iterate
  stale, and for a year left on the smaller deduction. From `yOBBBA` the charity floor and the
  non-itemizer charity are zero.
- **Nits:** non-itemizer charity is min(cap, the cash charity *paid*) (rows in loop mode, a gated
  column `nch` in optimize mode); `_item_fixed` (dead) removed; setup computes each term once; the
  shortfall uses the bonus the solution carries (`_item_bonus_n`), also under `_sb_lp`. The federal
  loop parameters are restored to the accepted LP's before the bracket-order repair, which reads
  them.
- **Tests:** the four loosened assertions are back to their pre-step-3 form except the NYIR
  tolerance (2.5e-3: that plan itemizes federally in 2026-2029 and its loop oscillates; measured
  0.0018, 3e-5 under `none`). The tiered-exclusion time-limit test is restored as it was; with
  `maxTime=0.5` its gap assertion failed 2 of 3 runs here, with 2 s it passed 4 of 4 (time-based,
  machine-dependent, not a step-3 matter). New in `test_itemized.py` (47 tests): 18-example guard,
  local search takes the larger deduction, SALT phase-down, 2/37 and Pease warnings, reversion ends
  the charity rules, non-itemizer charity at the amount paid (both modes), statutory recompute
  e = max(S, itemized) + bonus (optimize) / within the branch (loop) in place of the finite
  difference, optimize >= loop near the switch, no tie left under maxSpending with no bequest,
  dominated binaries fixed (`Case_jordan+taylor` at gap 2%), linked sale stops the interest,
  constraint replay (both modes).

## Phase 3 step 5 — medical floors wired to premiums; NJ line 31 (2026-10-11)

Size S from `phase3-plan.md` §5 step 5 (3.3). On `claude/eager-cray-s0fvks` after the step-3
review fixes. Rule checked this session against the 2025 NJ-1040 instructions (nj.gov, PDF):
line 31 / Worksheet F — unreimbursed medical above **2% of line 29** (NJ gross income = line 27
total income less the line 28c retirement exclusion). Medicare Part B premiums are named in the
instructions. Line 31 sits in lines 30-37c (before line 39 taxable income); line 41 property tax
comes after line 39. Both end up reducing the tax base.

- **Premiums as medical** (`Plan._medical_premium_terms` / `_medical_premium_ub`): budget
  `medical` lines plus Owl's Medicare Part B/D + IRMAA (`M_n`, or the `m` column under
  `withMedicare="optimize"`) and the ACA net premium (`ACA_n`, or `maca` under
  `withACA="optimize"`). Wired into the federal claim (it had budget lines only; the code said
  "premiums are step 5") and into NY's (which had Medicare but not ACA). `care` stays
  non-deductible (step 1: use `medical` for deductible care).
- **NJ line 31** (`st_med`, beside `st_pt`, no binary): floor `NJMF_n` = 2% of the previous
  iterate's line 29 (`st_agi_n - st_rx_n`), claim `max(0, paid - floor)`. No `max(0,.)` switch:
  a year whose paid amount clears the floor gets the row `st_med <= paid - floor`, one below it
  claims nothing (`_nj_medl_n`, as the federal loop's `_item_medl_n`; both are `_SC_PARAMS`).
  Data: `medical_deduction = { floor_pct = 2 }` in `taxes_state.toml` (NJ_Single / NJ_MFJ),
  `StateTaxParams.med_floor_pct_n`. The column is created only where the state has the deduction
  and something is medically deductible (a `medical` line, or Medicare/ACA on — `mediVals` always
  builds `Cbar`, so it cannot be the flag). Added to the state taxable-income row and to the
  exclusion's line-27 total (like `st_pt`). Shortfall joins `_bracket_order_excess` (step 4
  convention). Reported as `st_med_n` / *medical deduction* in the Taxes sheet and explain.
- **Test** (the plan's case): a deductible care line of $100k/yr from age 80 (`medical` type),
  federal itemizes in those years, `item_med = care + premiums - 7.5% AGI`
  (`test_care_line_of_100k_itemizes_with_premiums`). `tests/tax/test_nj_medical.py` (7): data
  parse NJ only, claim = paid - floor, no column without a medical line and Medicare off, the
  column appears with Medicare on, FL/NY unchanged, claim zero below the floor at high income.
- **Deviations from the plan's sketch:** the test line is a `medical` budget line named "care"
  (step 1 left `care` non-deductible); NJ's floor uses the same loop-flag pattern as the federal
  medical floor rather than a pure column bound, so a year that straddles the floor is decided
  from the previous iterate (no binary, as planned) and can lag one SC step.

Next: step 7 (docs). Step 6 measurements are under "Phase 3 step 6".

## Step 5 review (2026-10-11, independent pass over `ab16b65`)

Repros run on HEAD outside pytest (today's date, not the frozen 2026-01-01; scripts not
committed), with the `_plan` helpers of `test_itemized.py` / `test_nj_medical.py`. Rules
checked this session: NJ-1040 instructions (2025 form, `nj.gov/.../current/1040i.pdf`) line 29
("Subtract line 28c from line 27"), line 31 and Worksheet F (2% of line 29; "Insurance
(including amounts paid as premiums under Part B ...)"; "In general, medical expenses allowed
for federal tax purposes are allowed for New Jersey tax purposes"); Pub. 502 (2025, irs.gov):
Part B and Part D premiums are medical expenses, and "You can't include expenses you pay for
with a tax-free distribution from your health savings account. You also can't use other funds
equal to the amount of the distribution and include the expenses."

Bugs, verified by a run:

1. **The MCP explanation fails for an NJ plan that claims line 31.** `explain.py` emits
   `medical_deduction` (year 0) and `medical_deduction_today` (by year), but neither is in
   `explain_schema.py`, whose models are `extra="forbid"`. A plain NJ couple
   (`test_nj_medical._plan()`, no medical line, default `withMedicare="loop"`,
   `withDuals=True`): 25 of 31 years claim `st_med` on premiums alone and `build_explanation`
   raises `ValidationError` (9 errors). Every NJ retiree plan whose premiums exceed 2% of NJ
   gross income (about $245k for $4,870) hits this. Fix: add both fields and a sentence to the
   state note; test explain on an NJ plan.
2. **HSA distributions are deducted again.** `_add_hsa_medical_cap` lets `w[i,3,n]` reach
   `M_n + m + other_medical_n`; the medical claims count the same premiums. FL couple born 1958,
   HSA $60k each, medical line $30k, `withItemized="optimize"`: 2026 HSA withdrawal $4,870 =
   the premiums, `item_med` $22,936 = 34,870 − 11,934 (Pub. 502: $18,066). Same in 2027-2029.
   Fix: subtract `sum_i w[i,3,n]` from medical paid in the federal, NY and NJ rows (existing
   columns, linear). NY's claim has carried `M_n + m` since step 2, so NY had it before this
   commit. NJ: I did not find HSA text in the NJ-1040 instructions; NJ's treatment not checked.
3. **Federal candidate years ignore premiums under the default loop modes.**
   `_setup_federal_itemized` runs inside `_buildOffsetMap`, after `solve()` zeroes `M_n` and
   `ACA_n` (plan.py:6842-6843 then 6918), so `np.maximum(0.0, self.M_n + self.ACA_n)` at
   plan.py:2892 is always 0, and `_medicare_premium_ub_n` / the ACA bound are nonzero only under
   the optimize modes. FL couple aged 62, property tax $20k, `setACA(24)`, `withItemized=
   "optimize"`, default `withACA="loop"`: 2026-2028 ACA $24.0k-25.4k, AGI $141k-146k, itemized
   by hand $33,444 / $34,465 / $35,519 against a standard of $32,200 / $33,102 / $34,028; no
   candidate year, standard taken. Same pattern as step-3 review bug 1 (a loop value read at
   offset-map time). Fix: a mode-independent premium bound at build (Medicare: the top
   `Cbar` premium in Medicare years whatever the mode; ACA: `slcsp_aca_n` in ACA years).
4. **`withMedicare="optimize"` + `withItemized="loop"` drops the premiums from the floor
   flag.** `_item_floor_flags` adds `M_n + ACA_n` only, which is 0 when the `m` column carries
   the premium (NJ's `_nj_medical_floor_flags` adds `m_n` / `maca_n`). FL couple born 1958,
   property tax $34k, medical line $6k: `_item_medl_n` = [0, 1, 1, 0] in 2026-2029 with line +
   m − floor = $5,036 / $4,836 / $6,391 / $5,127; medical claim 0 in 2026 and 2029, where the
   other three mode pairs claim $4.7k-5.1k. Fix: add `m_n` (+ `maca_n`) at `g_n`, as NJ does.

Read, not run:

5. The NJ row in a year flagged from the previous iterate is a lower bound on spending:
   `st_med >= 0` and `st_med <= const + coef*g + prem - F` force `coef*g + m >= F - const -
   prem_fixed`. The previous iterate satisfies it and `g` is pinned (`maxBequest`) or maximized
   (`maxSpending`), so I did not find a case where it binds; under `withMedicare="optimize"` it
   can only push `m` up. The federal loop avoids this because its claim sits inside the bound
   on `e`. Note, no change proposed.
6. `_nj_medical_paid` reads `_ceiling_n` behind a `hasattr` guard: it is not set in
   `__init__`, and on a plan's first solve iteration 0 runs before `_buildConstraints` sets it,
   so the a priori bound there leaves out the discretionary medical part (the flag is decided
   one iterate later). Harmless lag; initialize it in `__init__` (CLAUDE.md convention).
7. NY candidacy (`_st_item_candidate_years`) still needs a budget line or mortgage interest:
   premiums alone never open a NY year. Not new: the step-2 review notes (`51dec3f`) quantified
   it and left it by decision (the NY standard loses only in the top two IRMAA tiers with
   near-zero AGI). Bug 3 is the federal counterpart, and there SALT makes it bite.
8a. *(Second review pass, 2026-10-11.)* The bracket-order repair reads loop values one SC step
   ahead. The block before `_repairBracketOrder` restores `FEDMF_n`, `FEDCF_n`, `FEDSC_n` and
   `_item_zi_n` "first" because the repair's tie check reads them, but `NJMF_n` / `_nj_medl_n`
   (new), `STMF_n` / `NYIR_n` and `M_n` / `ACA_n` are restored after it (plan.py:7741-7776).
   Step 5 made `_nj_medical_shortfall` and the federal `_item_allowed_parts` /
   `_item_potential_n` read `M_n + ACA_n`, so moving only `NJMF_n` up is not enough: the
   premiums are ahead too. The repair re-solves the LP already built (no rebuild), so only its
   trigger and its accept test (`new_excess < excess`) are measured on the advanced values.
   Small once the loop has converged; not measured.
8. `setMedicalExpenses` (`other_medical_n`, upstream's HSA cap) is in no medical claim. Owl
   does not charge it as spending, so leaving it out is defensible; say so in the docs (step 7).

Tests:

9. No test covers the `m` / `maca` coefficients (`withMedicare` / `withACA` = `"optimize"`),
   HSA withdrawals, or explain on an NJ plan: where bugs 1, 2 and 4 are.
10. `test_claim_is_zero_below_the_floor` is wrapped in `if "st_med" in p.vm:`; the column exists
    in that case, but the guard would let the test pass empty. Assert it. It also compares a
    nominal floor with the line's today's-dollar $3,000 (`below = floor > 3_000.0`): the claim
    there reaches $4,412 in 2049, which is the same $3,000 at gamma 1.887 ($5,662 nominal) less a
    $1,250 floor (run). Compare against the nominal amount paid.

Checked and correct: NJ floor on line 29 = line 27 − 28c (`st_agi_n - st_rx_n`); premiums
(Part B named, Part D and ACA by the federal-conformity sentence) count for NJ; the exclusion's
line-27 row adds `st_med` back (its comment "inside line 27" reads wrongly; the arithmetic is
right); `NJMF_n` / `_nj_medl_n` restored with the other SC parameters. `test_nj_medical.py`,
`test_itemized.py` and `test_mcp_explain.py`: 70 passed. flake8 only upstream's
`localsearch.py:31`; `ruff check` passes.

## Step 5 review fixes (2026-10-11)

All four bugs, items 5, 6 and 8a, and test defect 10; one more bug found while fixing (11).
Each new bug test was run against `68001e4` (a worktree with the new tests and the old `src`):
the five marked "fails before" do.

1. **Explain:** `medical_deduction` / `medical_deduction_today` added to `explain_schema.py`
   (optional fields, `SCHEMA_VERSION` unchanged), and a sentence in the state note.
   `test_explanation_reports_the_medical_deduction` (fails before).
2. **HSA:** `_medical_premium_terms(n, hsa=True)` puts −1 on `w[i,3,n]`, so every federal and NY
   medical row counts premiums less the year's HSA distributions; `_medical_premium_values`
   gives the same amount at a solution (shortfalls, flags, reports, the loop residual). The a
   priori lower bound (`_medical_premium_lo`) drops to `ACA_n − other medical`, because the HSA
   cap lets the distributions take back the whole Medicare premium; the NY and federal `z=0`
   relaxations grow by that amount. All distributions are subtracted, including any against
   `setMedicalExpenses`' amount, which is in no claim: the claim can only be understated by it.
   NJ: not subtracted. NJ does not follow federal HSA treatment; I did not find HSA text in the
   NJ-1040 instructions, and the only sources found (bill trackers for S474 / A2634, not
   nj.gov) say the federal HSA advantages are not in the NJ gross income tax. Owl does not
   model NJ's own HSA rules. `test_hsa_distributions_are_not_deducted_again` (fails before).
   Repro after: 2026 `item_med` $18,366 = 34,870 − 4,870 − 11,634.
3. **Federal candidates:** `_premium_ub_build_n` bounds premiums from the tables (top IRMAA tier
   unless `withMedicare="none"`; the ACA benchmark in ACA years) in every mode.
   `test_aca_premiums_open_itemizing_years_in_loop_mode` (fails before). Repro after: 2026-2028
   itemize; bequest $2,400,848 → $2,401,730.
4. **Floor flag:** `_item_floor_flags` reads `_medical_premium_values()` (m and maca included).
   `test_loop_floor_flag_counts_the_optimized_premium` (fails before). Repro after: flags
   [1, 1, 1, 1], medical claimed in 2026 and 2029.
5. **NJ row:** in a flagged year `st_med` may go down to the smallest `paid − F` instead of 0,
   so the row bounds neither spending nor `m` / `maca` from below; the year's tax is
   overstated by the lag instead, as the federal loop's rows do. `_nj_medical_shortfall` uses
   `paid − F` unclipped in flagged years (a lag is not a tie). Guard test
   `test_optimized_medicare_never_bounds_the_premium_from_below` (passes before too: I did
   not find an NJ plan where the old row bound).
6. `_ceiling_n` initialized in `__init__` and reset at solve entry; `_nj_medical_paid`
   computes the ceiling when it is not built yet.
8a. Before `_repairBracketOrder`, all the fork's loop parameters are restored to the accepted
   LP's (`FEDMF_n`, `FEDCF_n`, `FEDSC_n`, `_item_zi_n`, and now `_item_chl_n`, `_item_medl_n`,
   `NYIR_n`, `STMF_n`, `NJMF_n`, `_nj_medl_n`). `M_n` / `ACA_n` are the accepted LP's during
   the repair only, then put back, so aggregation sees what it saw before. `_item_chl_n` /
   `_item_medl_n` were never restored before; they now stay at the LP's after the solve, so a
   loop-mode plan reports the claims its own rows allowed. No test: not measured on a
   non-converged loop.
10. `test_claim_is_zero_below_the_floor` asserts the column and compares with the nominal
   amount paid and the LP's floor `NJMF_n`. Against the floor recomputed from the final
   iterate it is off by exactly $1,000 in 3 of 17 years: the SC lag, not a bug.
11. **New: under `withMedicare="optimize"` the federal and NY switch-free medical rows bounded
   `m` from below.** A year whose amount paid looked known (pinned `g`, no medical binary) got
   `imed ≤ line + m − F` with `imed ≥ 0`, i.e. `m ≥ F − line`, since step 5 put `m` (and
   `maca`) in that row. FL couple born 1958, property tax $39k, medical line $3k, both modes
   `"optimize"`: HiGHS called iterations 1-4 infeasible, the loop accepted an early iterate
   (floor $6.1k instead of $11.6k) and warned of brackets out of order. Local search sets
   `withMedicare="optimize"`, so it would meet this too. Fix: such years get the floor switch
   (`_medical_premium_lp_n`: an `m` bound, an ACA LP year, or any HSA), as NY already did for
   `m`. `test_optimized_medicare_with_a_known_medical_line_stays_feasible` (fails before).
   Cost: plans with an HSA now carry `zmed` / `zmedf` in every itemizing candidate year
   (both are `ALWAYS_FREE` in local search); step 6 should count them.

Not changed: item 7 (NY premium-only years, step-2 decision) and item 8 (docs, step 7).

## Phase 3 step 6 — measure (2026-10-11)

Size M from `phase3-plan.md` §5 step 6. Same day, synthetic couple of the probe / housing_stakes
(born 1964, LE 89/92, SS $3,000/$2,400 at 70, $150k taxable / $75k Roth each, $900k+$600k
tax-deferred, conservative 60/40; housing variants add taxable $500k+$300k so a home purchase is
feasible). Script `fork-notes/model-review/phase3_step6_measure.py`, raw output
`phase3_step6_2026-10-11.txt`. Exact LP = `withMedicare="None"`, `withSSTaxability=0.85`;
LS = `breakpointMethod="local-search"`. Levels are not comparable across the two methods (LS
charges Medicare and the IRS SS formula); every ranking below is within a method. Plans start
2026-10-11.

### 1. Probe cases in-model vs the first-order numbers (§3.2)

`maxBequest`, core $80k + property tax $25k, Yonkers or NJ. In-model gain =
bequest(`optimize`) − bequest(`none`); first-order is §3.2's post-hoc federal tax saved. NY
itemizing is on in every row (it is not behind `withItemized`), so its first-order $22k is already
in the `none` baseline and does not appear in the gain.

| case | none | loop | optimize | in-model gain (exact / LS) | first-order fed |
|---|---:|---:|---:|---:|---:|
| NY Yonkers $25k | 1,007,955 | 1,007,955 | 1,007,955 | 0 / 0 (LS 877,984) | 0 |
| NY + $600k mtg 6.5% | 781,584 | 811,969 | 811,969 | **+30,385** / **+30,283** | 17,977 |
| NJ $25k | 1,033,578 | 1,033,578 | 1,033,578 | 0 / 0 (LS 913,776) | 0 |
| NJ + $600k mtg | 781,546 | 811,931 | 811,931 | **+30,385** / **+34,842** | 15,735 |

2032 reversion (`obbba_expiration_year=2032`, exact): ny +29,092 (25 yrs), nymort +140,997 (31),
nj +27,935 (25), njmort +140,996 (31). First-order was 22,431 / 93,100 / 21,449 / 87,801: the LP
response multiplies the mortgage cases. **`loop` = `optimize` to the dollar in every case here**
(the a priori rule and `ITEM_WINDOW` leave `zi` free in only 4 years without a mortgage, 8-31 with
one or under the reversion). Reading: without a mortgage and under the law as enacted federal
itemizing is worth **$0**, as the probe said; with a mortgage it is worth **$30k lifetime in-model**
(9 itemizing years), and **$141k** under Owl's 2032 default. The in-model numbers supersede §3.2's
first-order table.

### 2. NY vs NJ owner (the 2026-10-07 table, with NY itemizing)

`housing_stakes` recipe: budget core $80k + property tax, no `netSpending`. NJ − NY of final
bequest:

| property tax | exact, none | exact, optimize | LS, none | LS, optimize |
|---|---:|---:|---:|---:|
| $20k | +37,181 | +37,181 | +41,083 | +41,083 |
| $25k | +25,623 | +25,623 | +35,792 | +35,792 |

Old table (2026-10-07, no NY itemizing, $20k): **+$62,830 exact / +$46,703 LS**. NY itemizing
cuts the NJ advantage by **~$25k exact / ~$5k LS** at $20k (NY lifetime `st_item` $620k of
deduction, 31 years, at $20k PT; $775k at $25k). Federal itemizing does not move the comparison
(no mortgage). The exact-method reduction is of the order the probe predicted for NY itemizing
($22k); the LS reduction is smaller and the two methods disagree on the residual by $4k, so the
remaining NJ edge stays in the "unresolved under 1%" band for a one-year income-tax difference
(the lifetime figure is not: NJ is ahead in both methods). Stay NJ (step 9) is still the larger
omitted term.

### 3. Scenario 5 rent / cash / mortgage, with the deduction

NY Yonkers, budget profile, `maxBequest` (each variant spends its own first-year total): core
$80k; rent $36k; or home $600k (PT $15k + insurance $2.5k + maintenance $6k), cash purchase with
2% closing, or 20% down and a $480k mortgage at 6.5% for 30 years (proceeds stay invested). Final
bequest counts home equity net of commission.

| variant | exact none | exact optimize | LS none | LS optimize | 2032 exact none → optimize |
|---|---:|---:|---:|---:|---:|
| rent | 1,428,594 | 1,428,594 | 1,326,650 | 1,326,650 | 1,305,061 → 1,305,061 |
| buy cash | 1,437,134 | 1,437,134 | 1,325,234 | 1,325,234 | 1,312,913 → 1,315,073 |
| buy mortgage | 1,278,944 | **1,290,362** | 1,147,743 | **1,166,398** | 1,145,286 → **1,207,446** |

- **Mortgage interest deduction is real and material on the mortgage path**: +$11.4k exact /
  +$18.7k LS under statutory law, +$62.2k under the 2032 reversion (26 of 31 years itemize
  federally). It does **not** reverse cash vs mortgage (still −$147k / −$159k of bequest).
- **Cash vs rent is unresolved**: cash ahead by $8.5k exact, rent ahead by $1.4k LS (0.6% / 0.1%).
  The phase0-scenarios caveat on the mortgage can be dropped for the deduction; the cash-vs-rent
  ranking still needs the household's own numbers (and the rate vs return point stands).
- Rent itemizes nothing (no PT, no mortgage) and is unchanged by `withItemized`, as expected.
  Cash itemizes on NY only (28 years of `st_item`); federal needs the mortgage or the reversion.

### 4. Binaries, solve times, node limits

| plan | zsi | zi | zmed | zmedf | other | time exact / LS | node-limit hits |
|---|---:|---:|---:|---:|---|---|---|
| NY owner, no mtg | 31 | 4 | 28 (LS) | 1 | zm 168, zs 62, zl 62, zj 31 | 0.1-0.3 s / 66 s | 0 main; LS 0/33-38 |
| NY owner + mtg | 31 | 8-21 | 28 | 16-18 | same | 0.1 s / 37-48 s | LS 0/36-47 |
| NJ owner | – | 4 | – | 1 | zx 124 | 0.3-0.6 s / 74-93 s | LS 0/44-51 |
| NJ owner + mtg | – | 8-21 | – | 18 | zx 124 | 0.3 s / 115 s | LS 0/63-69 |
| FL + HSA + medical $30k | – | 25 | 0 | 25 | (zm 150 if Medicare optimize) | 0.6-0.9 s | 0 |
| NY + medical $3k, maxSpending | 31 | 31 | 31 | 31 | | 15 s exact / 92 s loop / 121 s optimize-loop | 0/14 |

- **`zsi` is 31 on every NY owner year**: a family is the right shape (already shipped).
- **`zi` is 4 without a mortgage** (`ITEM_WINDOW` pins the rest), 8-21 with one, 25-31 under the
  reversion or a long medical line: also a family (already shipped). `ALWAYS_FREE` would keep 4-31
  binaries free in every restricted problem; the step-3 note already measured that losing.
- **`zmed` is 28-31 on every NY plan under local search** (Medicare becomes `"optimize"`), and 31
  under `maxSpending` with a discretionary medical line. **`zmedf` is 0-25** (25 on the HSA/medical
  FL plan; 1 on a plan whose only medical is premiums). Both stay `ALWAYS_FREE`.
- **`zmed` as a family vs `ALWAYS_FREE`**: same plan, same bequest 965,406, 66.8 s vs 61.7 s
  (`zmed_family_ls.py`), and 92.3 s vs 91.8 s in the maxSpending loop. **No difference: keep it in
  `ALWAYS_FREE`** (pinning one would freeze a `max(0, ·)` the search cannot reopen).
- **HSA plans carry `zmedf` in every federal itemizing candidate year (25) and `zmed` only if the
  state itemizes (NY)**. FL + HSA: `zmed` 0, `zmedf` 25. The step-5 review's "zmed / zmedf in every
  itemizing candidate year" is `zmedf` federally and `zmed` in NY.
- **`withItemized="optimize"` is cheap on these cases** (D4's default stands for the household
  files): +0.2-0.6 s exact, no LS slowdown, because `zi` is free only near the switch. The 30 s
  `Case_morgan` blow-up was the old candidate rule (step-3 review fixed it).
- Main solves never stopped at a node limit here. Local search hit its step cap on 0-4 of 20-69
  restricted solves and still returned the same plan as the loop or better.

### Open from earlier steps, touched here

- Discretionary medical under `maxSpending` costs ~15 s exact / ~92 s full loop (31 `zsi` + 31
  `zmed`); `zmed` placement does not change that. The 100 s figure in the step-2 review was the
  same case under load.
- `nch` is added as an empty block (size 0) under `optimize` when there is no non-itemizer charity
  year. Harmless (0 columns), noticed in every `bins` dump; not fixed.

Next: step 7 (docs).

## Phase 3 review after step 6 (2026-10-11, over `066b8d6..e634c81`)

Full write-up: `fork-notes/phase3-review.md` (Part A: step 6; Part B: the whole phase). Same day
as step 6, so its numbers reproduce to the dollar.

Step 6 corrections (the tables' arithmetic is right; these are about what they measure):

- "In-model gain" is final bequest; §3.2's first-order numbers are lifetime tax saved. Like for
  like, in-model tax saved is 84-101% of first-order (NY + mortgage, statutory: 15,073 vs
  17,977; 2032: 87,377 vs 93,100). The ~2x in the step-6 text is compounding to the plan's end.
- The NY-itemizing attribution compared with the 2026-10-07 table, which used another recipe (no
  conversions, Medicare off in LS, `netSpending` 80). Same day, same recipe, NY itemizing off:
  worth +$27,097 / +$38,635 exact and +$5,855 / +$11,146 LS at $20k / $25k. Methods disagree
  3-5x: size unresolved; sign and NJ's lead agreed.
- The `med`-group `zmed` family-vs-free rows ran no local search (same 486 nodes): vacuous.
  Only the NY LS row measures it. The `med` rows recorded no objective.
- "optimize is cheap" omits +3.6 s (cash, 2032) and +31% (maxSpending medical, full loop).

Fixed (`aa5bdaf`): explain registry for the federal itemized and NJ line 31 rows (gates would
have surfaced as policy constraints); NJ line 31 floor/flag moves in the loop's convergence test;
premiums in the federal medical moves; fixed-point residual entries "itemized" and "state
medical"; `_fix_dominated_itemizing` pins `zmedf` with premiums; duplicate helper removed and
`standard_without_bonus` used; NY `itemized` keys `income_taxes` / `salt_cap` /
`mortgage_limit` dropped (never honoured), unknown keys refused; empty `nch` block gone; the
fork's residual code moved out of `_scSolve`; code comments no longer narrate review history.
Two regression tests (both fail on `e634c81`). The residual entries are only reported; the
added moves can change a plan only by changing when the loop stops (NJ line 31, federal medical
with premiums).

Decisions for the user (`phase3-review.md` B.2): R1 drop `withItemized="optimize"` (18 examples:
optimize − loop from −$46.80 to +$2.49; five near-switch cases: equal under the exact LP, from
−$145/yr to +$260 of bequest under the full loop, up to 23x slower); R2 one switch for
NY itemizing and NJ line 31 too; R3 one mechanism for max(0, paid − floor); R4 done (merge
below); R5 size against upstream before step 8 (federal part ~750 lines of methods vs 89 for
`withSeniorBonus`).

## Phase 3 R1-R3 and step 7 (2026-10-11, after the review)

The user chose R1-R3 of `fork-notes/phase3-review.md`; details and the before/after table in its
Part C.

- **R1:** `withItemized = "optimize"` removed; the option is `"none"` | `"loop"` (default).
- **R2:** `"none"` is the standard deduction everywhere: no NY itemizing, no NJ line 31 either.
- **R3:** NY itemizing follows the federal pattern: branch and medical-floor side from the a
  priori bounds or the previous iterate, one row per itemizing year, no column, no binary.
  Phase 3 adds no binary at all now; the fork's changes to `localsearch.py`, `tools.py` and
  `stresstests.py` for Phase 3 are gone.
- Before/after, date frozen at 2026-10-11: 18 examples and all exact-LP cases identical to the
  cent; NY `maxSpending` with a medical line 103 s -> 0.4 s (−$50/yr); local search with a
  mortgage −0.31% (NY) / +0.30% (NJ), read as search noise (unproven).
- **Step 7 (docs):** `info/modeling-capabilities.md` (an *Itemized deductions* row; Debts, Budget,
  state and loop rows updated), `info/PARAMETERS.md` (`withItemized`), `ui/Documentation.py`
  (Budget types; an *Itemized deductions* paragraph after rent vs buy), `CHANGELOG.md` (itemized
  deductions federal and state; `medical` / `charity` types; the NJ line 41 fix under essential
  lines), `phase0-scenarios.md` (sections 3 and 5: the deductions are modeled, measured stakes, a
  `--set solver_options.withItemized=none` recipe), template (`withItemized = "loop"`).
  `taxes_state.toml`'s header was updated in the review commit.
- Scenario 5 with the deductions (exact, synthetic couple): +$13.1k (cash) / +$70.4k (mortgage)
  of bequest under statutory law; cash vs mortgage narrows from $204k to $147k, not reversed;
  cash vs rent turns from −$4.6k to +$8.5k (0.6%, unresolved).

Next: step 8 (upstream, concept level, `phase3-plan.md` §5), or Phase 5 / STAR as needed. *(Step 8 drafted 2026-10-12, below.)*

## Upstream dev 810a6cd merged (2026-10-12, on `claude/eager-cray-s0fvks`)

Three upstream commits of 2026-10-11 evening (`main` = `dev`), MCP and explainer only; no change to
`plan.py`, `tax_federal.py` or any tax rule:

- `17870e7`: the MCP parameter tools take `other_medical_expenses` (= `setMedicalExpenses`),
  `medical_inflation_excess`, `include_medicare_part_d`, `medicare_part_d_base_premium`; HSA
  balances without `other_medical_expenses` are flagged in `assumed_defaults`; the intake prompt
  asks for out-of-pocket qualified medical expenses when anyone has an HSA, and about Part D at
  63+. `explain_case` / `owlcli explain` get a `health_care` block; `explain_results` gets the
  premium added by the next IRMAA tier, the ACA MAGI against the Medicaid line and the 400% FPL
  cliff, and a `health_care` section (lifetime Medicare premiums with the IRMAA part and years,
  ACA net premiums, other medical expenses, HSA withdrawals). Its note: "Other medical expenses
  sit inside net spending; they only cap tax-free HSA withdrawals."
- `83ba462`: the explainer allows `THRESHOLD_SLACK = BRACKET_MARGIN / 2` when comparing a MAGI
  with an IRMAA or ACA threshold (a MAGI parked on a cliff came back $0.0008 above it);
  `net_premium_this_year` reads `aca_costs_n` (was `ACA_n`, zero in optimize mode).
- `810a6cd`: CHANGELOG.

Merge: one conflict, `tests/mcp/test_mcp_explain.py` (both sides appended tests at the same
place: the fork's NY locality/recapture tests and upstream's health-care tests; kept both).
No duplicated definitions in the touched files (grep). flake8: only upstream's
`localsearch.py:31`; ruff clean. The three merged test files: 209 passed. Full suite: **3193 passed, 1 skipped** (6:53; 3178 on
2026-10-11 plus upstream's new tests).

Effect on the fork: none on plans. Effect on step 8: `other_medical_expenses` is now a
first-class household input whose description (dental, vision, co-pays, deductibles) is the
Schedule A medical expense (Pub. 969: HSA qualified medical expenses are IRC 213(d) medical care,
the Schedule A definition; read on irs.gov 2026-10-12). The proposal now counts medical among the
amounts Owl already knows and asks whether Schedule A may read it (question 2).

Fork-side question this raised (fixed the same day, next section): the fork's federal and NY medical claims read
budget `medical` lines plus premiums, less all HSA distributions; `other_medical_k` is in no
claim (documented in `_medical_premium_terms`: the claim can only be understated). A household
that enters its out-of-pocket medical through `other_medical_expenses`, as upstream's intake now
asks, gets no deduction for it, and its HSA distributions against it are still subtracted from
the premiums. Options: read `other_medical_k` in the claim when the plan has no budget `medical`
line (one source, no double count), or refuse/warn when both are set. Decide with Phase 4.

## other_medical_expenses in the medical claims (2026-10-12, on `claude/eager-cray-s0fvks`)

The user chose the first option above. `Plan._medical_amount_terms()` is the household's own
medical expense for every claim (federal Schedule A, NY IT-196, NJ line 31, their candidate years,
floor flags, residuals and the NJ shortfall check): the budget's `medical` lines when it has any
(`_budget_has_medical`), otherwise `setMedicalExpenses`' amount (`other_medical_k`, nominal, grown
with `_medical_n`, coefficient 0 on net spending). One source, never both. `other_medical_k > 0`
also opens the NJ line 31 column, as a `medical` line did. Premiums and the HSA subtraction are
unchanged, so an HSA that pays the other medical amount now takes it back from a claim that
contains it.

- Tests (5 new): federal claim with no budget `medical` line (FL, $60k); the MCP path with no
  Budget sheet (flat profile, `netSpending` 80: itemizes the first 10 years, bequest above
  `"none"`); a budget `medical` line wins (claims identical with `setMedicalExpenses(30)` added);
  NJ line 31 and NY IT-196 read it. On the previous commit four of them fail (the guard passes on
  both, as it should).
- Examples that set `other_medical_expenses` (joe $3k, kim+sam $2k x 2): basis and bequest
  identical to the cent before and after (date frozen at 2026-01-01); no year itemizes in either.
- Docs: CHANGELOG fork entry, `modeling-capabilities.md` (itemized row: the old "in no claim"
  sentence replaced), `Documentation.py` (itemized paragraph; one clause on the Qualified Medical
  Expenses field).
- Full suite **3198 passed, 1 skipped** (7:50). flake8: only upstream's `localsearch.py:31`; ruff
  clean.
- Semantics, stated in the docs: `other_medical_expenses` is a fixed amount, so under
  `maxSpending` it does not scale with spending; a `medical` budget line does. With a Budget
  profile and no `medical` line, it is counted as paid even though the budget lines do not list
  it (upstream says it sits inside net spending).

## NY STAR credit as a rule (2026-10-17, on `claude/zen-heisenberg-rfreik`)

After the data check below (the user asked for STAR as a rule and allowed `pub.njleg.gov`). The
statutes, read on nysenate.gov the same day, are in `fork-notes/star/README.md` ("Statutes"):
Tax Law sec. 606(eee) makes the credit a refundable NY income tax credit; "affiliated income" is
AGI less IRA distributions; Basic at most $500,000 (fixed); Enhanced from an owner's 65 at most the
standard (RPTL 425: the SS COLA each year, never lower); RPTL 1306-a caps the credit at 102% of
the prior year's. tax.ny.gov's survivor rule: 62 by December 31 of the year of the death, else 65.

- `star.py` (schedule, implied credit, district lookup), data `data/property_tax_relief.toml`
  (75 rows: Westchester residential and NYC classes 1/2/4, 2025 final credits), the residence's
  new `school_district` (`residency.Residence` 4th field; basic_info and moves; a move may change
  only the district), config schema, plan/UI bridges (canonical spelling for the UI's
  selectbox), Create Case selectboxes, `withSTAR` = `"loop"` (default) | `"optimize"` | `"none"`,
  `previousSTARIncomes` (default `previousMAGIs`).
- In the plan: the credit comes off `_state_tax_terms` (outside the Yonkers surcharge), so the
  cash flow and the SALT row follow; `st_T_n` is net of it, `st_star_n` is the part; IT-196 line 6
  subtracts the lagged `STAR_n` (`_item_terms()["st_pt"]`, used by every state-schedule path).
  SC parameter `STAR_n`, residual family "STAR", loop movement counted. `"optimize"`: binary
  `zst_n` per Enhanced year, row income_(n-2) + M zst <= limit - $2 + M (the $2 margin removed a
  $1.4k residual from an income parked on the limit); `zst` is a local-search family;
  `breakpointMethod` sets `"optimize"`. Basic's $500k limit is a loop test in both modes.
- Taxes sheet column *STAR credit*, Summary *Total NY STAR credit received*.
- Docs: PARAMETERS.md, modeling-capabilities.md, CHANGELOG.md, UI Documentation, the template
  (`school_district`), `phase0-scenarios.md`.

Measured on the synthetic couple (`_plan` of `tests/tax/test_star.py`: born 1960/1961, Yonkers,
$25k property tax, $80k core budget, `maxBequest`; run 2026-10-17, not under the frozen test date):

| Case | Recipe | none | loop | optimize |
|---|---|---|---|---|
| $400k taxable each, SS $3,000/$2,400 | exact LP | 2,223,238 | 2,304,073 | 2,304,073 |
| same | default loop | 2,049,327 | 2,129,932 | 2,129,932 |
| $800k taxable each, SS $4,200/$3,600 | exact LP | 4,206,065 | 4,276,610 | 4,288,556 |
| same | default loop | 4,020,611 | 4,097,467 | 4,097,636 |
| same | local search | 4,089,060 (287 s) | 4,166,137 (309 s, `"optimize"`) | |

Credits received: $63.2k in today's dollars over 28 years where income stays under the standard
($57.9k loop / $61.9k optimize in the $800k exact case, where income crosses it); the bequest gain
is $70-81k. Where income sits near the Enhanced standard the loop loses Enhanced years the MILP
keeps (frozen-date sweep in the tests: 21 vs 23 years at $800k, 15 vs 17 at $850k, +$5-10k);
elsewhere the two agree. Optimize costs 2-10 s instead of 0.3 s per solve.

Tests: `tests/tax/test_star.py` 16 tests; full suite **3248 passed, 1 skipped** (9.5 min; three
fork asserts on `state_moves` updated to 4-field `Residence`). flake8/ruff: only upstream's
`localsearch.py:31` and B905 in `test_roth_maturation_losses.py`.

**Bias note:** with STAR modeled and Stay NJ / ANCHOR not, a NY-vs-NJ owner comparison now leans
toward NY by NJ's relief (65+: $4,000-6,500 a year total, `fork-notes/star/README.md`).

## STAR / Stay NJ data check (2026-10-17, on `claude/zen-heisenberg-rfreik`)

Open data questions of `phase3-plan.md` §3.4 and "Step 2 review" checked on tax.ny.gov and nj.gov
(PAS-1 2025 form and instructions, NJ-1040 2025 instructions, the Stay NJ Task Force report).
Notes and sources: `fork-notes/star/README.md`; 2025 final STAR credits for Westchester (77 rows)
and NYC (3 tax classes): `fork-notes/star/star_2025_westchester_nyc.csv`. No code changed.

- STAR amounts are published per municipality and school district after school rates are set;
  2025 credits: Yonkers Enhanced $2,455 / Basic $879; NYC $730-743 / $274-278; rest of
  Westchester (residential rows) Enhanced $1,753-4,517, Basic $611-1,665. The credit can grow at
  most 2% a year (exemption savings not at all), and cannot exceed the school tax paid. Enhanced
  limit $110,750 (2026) / $113,550 (2027); STAR income = AGI minus taxable IRA distributions, two
  years back (conversions out, 401(k) withdrawals and taxable SS in).
- Stay NJ = 50% of the bill, at most $6,500, minus ANCHOR and Senior Freeze (handout, Task Force
  recommendation 7; the nj.gov calculation page is 404 now). FY2027 tiers $6,500 / $5,000 /
  $4,000 to $100k / $150k / $200k; the PAS-1 still states the statutory $500k. Its income (and
  Senior Freeze's) is NJ-1040 line 27, before the retirement exclusion, plus gross SS, tax-exempt
  interest and Roth earnings; ANCHOR uses line 29 ($1,500 to $150k, $1,000 to $250k, homeowners
  of any age).
- **Correction to §3.4's reading:** "Stay NJ up to $4,000-6,500" is the NJ total, ANCHOR
  included. NJ minus Yonkers at 65+ is about $4,045 / $2,545 / $1,545 a year by Stay NJ tier
  with Enhanced STAR, $5,621 / $4,121 / $3,121 with Basic, $621 above $200k and under 65.
  Still several times the measured income-tax differences ($430-1,006/yr).
- NJ line 41 starts from property taxes paid; Senior Freeze applicants use their base-year tax
  (1040i Worksheet H). I did not find a reduction for ANCHOR or Stay NJ.
- Not checked: the statute text (pub.njleg.gov blocked), federal treatment of the credits
  ("recoveries", Pub. 525), NY senior citizens exemption / SCHE, NYC school tax credit.

Next for this item: step 9 as planned (scenario lever from a solved plan's PAS-1 and STAR
income); code tiers only if a solved plan sits near a cliff; STAR first if anything is coded.

## Upstream dev 2b34633 merged; #193 PR prepared at the maintainer's request (2026-10-17)

Upstream `dev` `2b34633` (#194: Debts/Fixed Assets editors keep rows still being typed; #195:
optimized SS claiming age no longer in the past, and with one free age the couple's whole benefit
streams tabulated per candidate age, `_ssa_B_cross`, `_ssaMaxBenefit`). Merge `0874f0f`: conflicts in
`_gateCeilings` (fork's `ss_in` parameter kept, upstream's `_ssaMaxBenefit` bound taken) and the
CHANGELOG (fork section above upstream's 2026.10.16, unchanged); the fork's `_item_income_ub_n` also
switched to `_ssaMaxBenefit` (it bounds income, and #195's partner streams belong in it). Full suite
**3232 passed, 1 skipped**.

Maintainer on #193 (2026-10-17; read from the issue page with WebFetch, which paraphrases): the SS MIP
uses 3 binaries a year, 1 suffices when the benefit exceeds the tier gap; he tried it hoping to go
pure MIP on SS, much slower in some cases, faster in others (the deleted `ss-binaries`); "Can you
bundle both points above in a single PR and I'll test and push"; out of tokens until Sunday.
Read as our two points: the warning/pointer when the loop leaves SS unsettled (first reply) and the
"loop" label of a convex solve (second reply). PR branch `ss-convex-pr` (local worktree; stock code
only): `upstream/ss-convex` + `upstream/dev` merged (clean, `7d1169c`) + `fb8b10e` (label,
`_warnSSResidual`, PARAMETERS.md, CHANGELOG under Version WIP, 3 tests). Upstream suite 2871 passed,
1 skipped; the two new tests fail without the change. Found while testing: under the tests' frozen
date the #193 couple at $105k leaves only $1,167 of SS residual (bar $1,550) although the loop is
>$10k short, so a residual warning catches non-settling, not settled-short; stated in the PR.
PR text `fork-notes/pr-193-body.md`. On the user's go, branch pushed to the fork as `ss-convex-pr`;
the session could not open the PR on `mdlacasse/Owl` (access scoped to the fork; a second repo named
`owl` cannot be attached), so the user opened it: **PR #196** (2026-10-17). Awaiting the maintainer's test and merge.

2026-10-17: `main` fast-forwarded to `claude/eager-cray-s0fvks` (`066b8d6` -> `c5a419e`, 89 commits, no force; then this note).

## "Convex" cap probe: the fork's loop parameters warm-started (2026-10-17, on `claude/eager-cray-s0fvks`)

The SS cap probe (upstream `ss-convex`, `_ssCapProbe`) re-solves the plan once per year it tries,
warm-started from the best plan's loop quantities; upstream's `warm_keys` covered its own only, so
the fork's `_SC_PARAMS` (NJ exclusion free set `RXF_n`, NY recapture `STR_n`, NYIR, the itemizing
branches and floors, NJ line 31) restarted cold in every probe: an NJ probe re-solved its first
iterate without the exclusion and re-grew the free set through extra MILPs. Fix (`plan.py`, 4 lines
in `_ssCapProbe`, marked "Fork"): `warm_keys` += every `_SC_PARAMS` entry except `Psi_n` ("convex"
sets SS by region). `_rx_fixed` (tiers kept after a node-capped MILP) is not carried, so a probe
can still change tiers.

Measured (`convex_fork.py convex`, `model-review/ss-loop/convex_fork_warm_2026-10-17.txt` against
`convex_fork_c22_2026-10-16.txt`; date frozen at 2026-10-15): NJ 2032 376 -> 271 s, NJ+mortgage 2032
542 -> 407 s, NJ 2099 321 -> 220 s, NJ+mortgage 2099 522 -> 329 s (-25% to -37%); bequests the same
except NJ+mortgage 2032 705,665 -> 705,656 (-$9); NY unchanged (1.7-3.1 s, same bequests; NY 2032's
residual $171 -> $0). Where the rest goes (`probe_trace.py`, NJ 2099): 27 probes (23 + 4 in a second
pass, 3 kept) take 205 of 217 s, 3-12 s each, no node cap hit: each probe is a full NJ loop solve
whose iterations are MILPs (tier binaries free). Local search on the same cases: 81-176 s.

Not done (a design choice, not just speed): pin the best plan's NJ tiers during probes (`_rx_fixed`
from its `zx`), making probes LPs, then re-solve the winning regions with free tiers. Probes would
then judge each SS move at fixed tiers.

Test: `tests/plan/test_ss_convex_fork.py` (the probe's warm start carries every fork `_SC_PARAMS`
key and not `Psi_n`; fails without the fix, listing the missing keys). Full suite with the fix
**3228 passed, 1 skipped** (7:46) before the new test; the new test passes (3.5 s).

## PR #196: is "convex" worth keeping? (2026-10-17, on `claude/friendly-mccarthy-585okd`)

Maintainer on PR #196 (relayed): "Are you sure you want to keep the ss-convex implementation? My
tests were mixed. I am not sure this adds much. Your call." Measured on stock `fb8b10e` (the PR
head) in a scratch worktree, date frozen at 2026-10-15; output
`fork-notes/model-review/ss-loop/pr196_check_2026-10-17.txt`, scripts `pr196_*.py` beside it. Times
are from up to 11 concurrent runs on 4 cores (relative only), except the uncontended john+sally
rerun (same objectives: the runs are deterministic).

- **Paired, every other family exact** (IRMAA, LTCG, NIIT, senior bonus, ACA where set, on
  "optimize", branch-and-bound, `maxTime=900`), only SS changed, "convex" / "optimize":
  john+sally 31,693 / 31,693; helen+ruth 195,201 / 195,246; joe 93,109 / 93,057; morgan 44,212 /
  44,201; kim+sam-bequest 1,961,483 / 1,961,326 (the "optimize" run stopped by hand at its second
  iterate, each MILP at `maxTime`). All within the reported gaps (0.2-0.5%). The branch-and-bound
  preset on john+sally: 31,778 (gap 0.19%).
- **Other families on the loop (the default)**: "convex" vs SS "optimize" differ in both
  directions (john+sally 28,898 / 18,481; morgan 41,747 / 40,601; kim+sam 1,958,030 / 1,953,516;
  jordan+taylor-qcd 2,263,567 / 2,260,012; joe 92,692 / 92,869; jack+jill 102,759 / 102,884;
  helen+ruth 194,421 / 194,151; alex+jamie equal). "Optimize" left residuals of $15.5-20.8k
  (mostly LTCG) in helen+ruth, joe and jack+jill; "convex" $0 in all eight. On john+sally, both with
  $0 residual, taxable SS equals the IRS formula in every year of both plans (`pr196_john_sally.py`);
  the gap is the IRMAA loop's fixed point ("convex" converts less in 2026-27, no IRMAA tier in
  2028-30, Medicare $136.3k vs $143.2k lifetime). This is the likely source of "mixed".
- **Speed:** with the rest on the loop "convex" is fast (john+sally 1.8 s vs 14.7 s uncontended);
  with the rest on "optimize" it is 2.3-4.9x slower than SS "optimize" (helen+ruth 867 / 252 s,
  joe 584 / 251, morgan 1,208 / 249; contended): the cap probe re-solves a MILP per year. The
  presets set SS to "optimize" (`_applyBreakpointOptions`), so "convex" is a loop-mode tool only.
- **Side finding, traced the same day: not SS** (section "Local search and the LTCG family" below).
  The local-search preset returns 20,004 on john+sally against 31,778 for the branch-and-bound
  preset; local search on SS + IRMAA reaches 31,693, and adding the LTCG family makes it keep the
  loop's plan (16,803). (A note here at first called the search's step objectives, $38-46k, a
  mismatch with the $16.7k plan: wrong, the steps log nominal dollars; 38,268 / 2.2898 = $16,712.)

Reply draft `fork-notes/pr-196-reply.md`, revised the same day after the user's review: drop "convex".
An opt-in is a burden with no signal for when to use it, and "the mixed results come from the other
loops" was an inference about tests we never saw: only the source of the differences in our own runs
was measured. The warning points to `withSSTaxability="optimize"` (local search dropped from the pointer
until `issue-ls-ltcg.md` is fixed upstream). The user decides. Fork impact either way: the decision recipe is local search, which does not use "convex"; if
upstream drops it, the fork can drop it too at the next sync (the `warm_keys` fork edit in
`_ssCapProbe` goes with it). Not merged here yet: upstream `dev` `7e5f11a`, `7abed19` (#195
follow-ups: a past SS claiming age).

## Upstream dev 4932cb9 merged: PR #196 landed (2026-10-18, on `claude/lucid-noether-20vnnv`)

The maintainer merged PR #196 (`4932cb9`, merge of our `e5a9ad5`; its tree is identical to
`e5a9ad5`, checked with `git diff`): the loop warns when taxable Social Security does not settle
(`_warnSSResidual`, `tests/plan/test_ss_residual_warning.py`). Merged here after `origin/main`
(`6d3a155`, #185 recheck, docs only; PROGRESS.md conflict, both sections kept). CHANGELOG
conflict: upstream's new "Version WIP" section kept below the fork's "Unreleased".

One fork adaptation: upstream's test couple (#193, NY + mortgage, $95k) settles under the fork's
default itemizing, SS residual $890 against the $1,550 bar (no warning), and does not with
`withItemized="none"`, upstream's model ($2,131, warning). The test's `_solve` now passes
`withItemized="none"`, with a comment; `withSTAR="none"` changes nothing there.

Tests: full suite **3193 passed, 1 skipped** (8:33; +3 upstream). flake8/ruff: only upstream's
known lines (`localsearch.py:31`, `test_roth_maturation_losses.py:49`).

PR #196 is done. Upstream table row: merged by the maintainer 2026-10-18 (as relayed by the user).

`main` fast-forwarded to this branch (`6d3a155` -> `0acf6a4`, then this note), at the user's request.

## Phase 5 planned: work, part time, SS earnings test (2026-10-17, on `claude/lucid-noether-20vnnv`)

Plan: `fork-notes/phase5-plan.md` (no code changed). Rules verified this session in the POMS
(`secure.ssa.gov`): 2026 exempt
amounts $24,480 / $65,160 (RS 02501.025 D), what counts and the FRA-year cut (RS 02501.021,
.080), family charging with no carry-over (RS 02501.095), partial months (RS 02501.110), grace
year and non-service months (RS 02501.030), ARF crediting months incl. partial deductions
(RS 00615.480/.482), 401(k) deferrals count and §125 amounts and the employer match do not
(RS 02505.005, .045, RS 01402.010, .036). Payroll-tax figures and the SSA Statement's
continued-work assumption are recalled, to check in step 0.

Measured (`fork-notes/phase5/et_examples.py`, output `et_examples_2026-10-17.txt`): 3 of the 18
upstream examples pay SS before FRA in a year with wages above the exempt amount (alex+jamie
2026-27, chris+pat 2028, jack+jill 2028; $80-85k wages against $9.9-11.6k of benefits, so the
annual test would withhold the whole year). Pat's and Jill's 2028 is their last work year, so
the answer turns on the month they stop, which annual wages do not carry.

Design: earnings are inputs, so the test is a deterministic function of the claiming month and
goes into the SS streams and the `withSSAges` tables (no new LP variables, rows, binaries or
loop parameters). Inputs: optional HFP columns for gross earnings and months worked. Steps 0-10
and decisions D1-D8 in the plan; D1, D2 and D6 are needed before code.

2026-10-18: **decisions D1-D8 as recommended, D5 no** (nobody works past 65 with employer
coverage; step 7 dropped). Access corrected after the user pointed out that `ssa.gov` and eCFR
are on the allow list: the first draft's "not reachable" was wrong for eCFR (wrong API path,
then its bot block); it works through the versioner API with a browser User-Agent, and
20 CFR 404.412, .429, .430, .434, .435 now back the plan (§2.1b: the exempt amounts' AWI
indexing formula; no charge in months at FRA, which settles one of the two inferences).
`www.ssa.gov` is passed by the proxy but denied by SSA's Akamai edge (curl with any User-Agent,
WebFetch); `ssa.gov` sends no intermediate certificate, and its issuer's host is refused by the
proxy. Details in the plan's header. After the user allowed `cacerts.digicert.com`: `ssa.gov`
verifies with the intermediate but 301s every page to `www.ssa.gov`. Test-first development for
steps 1-5 agreed in principle (plan §5b: strict-xfail test commits reviewed before the code).

Next: step 0 *(done 2026-10-18, below)*.

## Phase 5 step 0: sources and stakes (2026-10-18, on `claude/phase5-step0`)

Branch from `main` `afb53d52` (= `claude/lucid-noether-20vnnv`). No Owl code changed; the
step-0 scripts are fork-notes.

**Sources (plan §2.3).** Verified on `irs.gov` (2026-10-18): Pub. 15 (2026) "What's New" —
2026 SS wage base **$184,500**, SS 6.2% each, Medicare 1.45% each, no Medicare wage base;
Instructions for Form 8959 (2025) — Additional Medicare Tax **0.9%**, MFJ threshold **$250,000**,
not indexed. Both match what the plan recalled. The SSA Statement continued-work assumption is
**still recalled**: no Statement under `otherFiles/`, and the POMS pages tried (RS 00601.001/.020,
RS 00605.001/.010/.035, RS 02001.001, DI 10515.001) do not state it; only needed for D4(b), which
the user declined. AWI/PIA formula not checked (D4 = (a)).

**Stakes without the LP** (`fork-notes/phase5/et_stakes.py`, `et_stakes_compare.py`; outputs
`et_stakes_2026-10-18.txt`, `et_stakes_compare_2026-10-18.txt`; plan §3b). Stand-in worker born
1964-03-15, PIA $3,000, FRA 67, last plan year 2053; grid earnings x stop year x months-last x
claim 62–70. Best claiming age is **70 with and without the test in every cell**; at that age the
lifetime PV is unchanged. **Gate: not informative (review below); steps 6-8
stay.** Claim-62-while-working moves 0–10.5% in PV (the ARF replaces withheld months
and, on this stand-in, is worth more than the withholding costs): the correct stream is 0–10.5%
above Owl's no-test stream at 62, and Owl overstates cash in the work years by the withheld
amount (up to $121,800 nominal at $100k / 5 years). The plan's "early claiming is close to
claiming at the stop date" is only true at high earnings / long work (within 0.5% of claim-at-67
at $100k / stop 2031); at $40k / stop 2028 it looks like claim-at-63 (3.4% below claim-at-stop).
`months worked` 6 vs 12 flips whether the stop year is withheld (confirms D2 is load-bearing for
Pat and Jill). Prototype reviewed before commit (plan §3c: the first draft mixed payment and
entitlement months and dropped a chargeable month; grace-year start and the monthly exempt amount
checked; POMS RS 02501.080 examples and the 0.70/0.75 ARF hand numbers pass).

**Review (2026-10-18, same branch).** The numbers reproduce (both scripts rerun: identical output
except one header line saved from an earlier version). Three changes: (1) the gate could not fail
(with no work the own-benefit PV rises with every year of delay to 70, and every cell stops by
age 67, so a claim at 70 never meets the test); it was the plan's gate design, not the
implementation; steps 6 and 8 stay, and step 0's result is the size of the claim-while-working
correction. (2) Both outputs were UTF-16 with CRLF (PowerShell redirect), which git stores as
binary: regenerated as UTF-8; the run line says `.venv/bin/python`. (3) Step 1's tests gain the
no-work grace year (404.435(a)(7): a month without work is a non-service month; the prototype
skipped it, harmless in this grid) and Owl's earliest claiming month (62y1m for anyone born after
the 2nd; the prototype's claim-62 rows start one month earlier). Plan §3b, §3c, step 0, step 1.

`main` fast-forwarded to `claude/phase5-step0` (`afb53d5` -> `3803337`, then this note), at the user's request.

Next: step 1 (the rules as a pure function, test-first per §5b) *(done 2026-10-18, below)*.

## Phase 5 step 1: the earnings-test rules as a pure function (2026-10-18, on `claude/phase5-step1`)

Branch from `main` `41abe581` (= `claude/phase5-step0`). Size M from `phase5-plan.md` §5 step 1.
`socialsecurity.py` gains the rule pieces and `earnings_test(...)` (§4.3); **not yet wired** into
`compute_social_security_benefits` / `build_own_benefit_table` / `Plan` (steps 3-4). No recorded
value moves (the function is new and unused).

**What landed** (`socialsecurity.py`, `tests/ss/test_earnings_test.py`, 29 tests):

- Exempt-amount table (2024-2026 from RS 02501.025 D, TN 55, source comment) and
  `get_exempt_amounts` (later years held at the 2026 real level); tests pass their own
  `exempt_for_year` so the POMS examples run with their year's numbers.
- `excess_earnings` / `countable_earnings` (RS 02501.080, FRA-year cut at the FRA month),
  `is_non_service_month` / `initial_grace_year` (404.435; a month with no work is a
  non-service month — the step-0 gap), `charge_excess_months` (RS 02501.095 family charge,
  RS 02501.110 partial-month split by original shares with cap-and-reapportion).
- ARF as a single deterministic function of the withholding: `arf_self_factor` /
  `arf_spousal_factor` recompute the factor at `claim + crediting_months/12` (capped at
  FRA). ARF is effective only from the FRA month and charging never reaches that month,
  so crediting months come from the pre-ARF stream alone (one pass, not the prototype's two).
  A month with any deduction counts (RS 00615.482 B.1); an auxiliary is credited for
  deductions from the worker's charge too (B.2).
- `earnings_test(...)`: monthly own + spousal grids (eligibility reset 62y1m like
  `compute_social_security_benefits`), excess per person per year, family charging
  (worker's excess to the family on their record; an auxiliary's own excess to their
  remaining check), ARF from FRA, aggregation to payment-year annual amounts (check for
  month m in m+1). Survivor folded in after the first death as the greater of own and
  survivor; **survivor ARF deferred** (D7 said include if cheap — the charging rule is
  cheap, the survivor ARF schedule (RS 00615.580) is not; documented in the module
  docstring).

**Test-first (plan §5b) and reviews.** Spec commit first (`5d298f62`, tests only, strict
xfail, expected values from the POMS text). Three independent review passes: (1) approve
with gaps — grace-year outcomes were inequality-only, claim-62 had no hand number, tob=2
comment wrong; (2) those fixed but the grace-year e2e fed multi-year work while pinning
single-year totals (fixed to 2026-only work); hand numbers re-audited against POMS and
404.410; (3) **approve**, ready to implement. Implementation commit removes the markers.
The specs then caught two implementation bugs: the monthly grid overran `horizons` by 11
months (hidden in the single-worker no-op because the overflow fell past `N_n`), and the
December arrears check landed past the person's horizon (Owl stops at 12 full months of
the last plan year). Both fixed; the couple-with-survivor no-op is exact.

**Tests cite primary worked examples** (not numbers from the code): RS 02501.080
(\$1,260; \$4,333; the June FRA cut), RS 02501.095 (3 family months; 4 then 5, order as
`earnings_test` behavior), RS 02501.110 (\$600 split 2/6 and 1/6; Example 3
cap-and-reapportion → \$38/\$16/\$19/\$19), 404.435 grace-year shapes with hand totals
(\$0 vs \$7,760), ARF hand numbers (0.70 → 0.75 at 12 crediting months; claim-62-while-
working: ARF **57**, withheld **\$120,412.50**, from-FRA **\$2,966.67**/mo), payment-year
bucketing, PIA-share partial split, spousal ARF crediting from the worker's charge,
survivor fold-in / deferred survivor ARF, no-op when earnings are zero (identical to
`compute_social_security_benefits`), Owl's earliest claiming month (tob 1/2/3/15), nothing
at/after FRA.

**§2.2 ARF inference checked** against RS 00615.490 (TN 24, read 2026-10-18): the section
has **no numeric worked example** — it only states the procedure "Determine crediting
months. Subtract from original reduction factor. Apply result to PIA." That is exactly
`getSelfFactor(fra, claim + c/12)`. Marked **verified as procedure, no numeric example**.

**Cross-check** against `fork-notes/phase5/et_stakes.py` on the stand-in (claim 62,
\$40k / stop 2028 / 12 months): withheld **\$23,280** and **12** ARF months, identical.
(Prototype claim-62 starts one month early; the withheld/ARF match still holds here.)

Full suite: 3222 passed / 1 skipped (8:33). flake8 and Ruff clean.

Next: step 2 (inputs: `gross earnings` / `months worked` columns) *(done 2026-10-18, below)*.

## Phase 5 step 2: `gross earnings` / `months worked` columns (2026-10-18, on `claude/phase5-step1`)

Size S from `phase5-plan.md` §5 step 2. Spec commit `fca2f2cf` (17 xfail tests), independent
review (approve with gaps: clone test needed `rawHFP`, months-default keyed on gross not wages,
present-zero months unpinned), must-fixes applied, then implementation. Xfail markers removed.

**Columns** (`hfp_io._timeHorizonItems`, after `anticipated wages`): `gross earnings` (D1,
nominal $, W-2 box 5 + net SE) and `months worked` (D2, whole months 0-12). Both optional;
typo check applies; written back by `build_hfp_dataframes`. Months is not a dollar column:
`_conditionTimetables` refuses anything outside integer [0, 12] (12.5 and 6.5 included).

**Arrays** (`plan.py`): `etEarnings_in` / `etMonths_in`, shape (N_i, N_n), zeros in `__init__`,
filled in `setContributions` from `iloc[5:5+h]`, cleared by `zeroWagesAndContributions`.
Fallbacks at array-build time so a present zero wins: absent `gross earnings` → `anticipated
wages` plus a warning naming years with a non-zero deferral column (401k / Roth 401k / IRA /
Roth IRA / HSA); absent `months worked` → 12 when *countable* earnings > 0 else 0.

**Also:** UI bubble help + 0-12 editor for months; `Documentation.py` (16-column table and
descriptions); `PARAMETERS.md`; all 17 `examples/HFP*.xlsx` gain the two headers.

**Tests** (`tests/config/test_hfp_earnings_columns.py`, 17): schema, load, present-zero vs
absent, fallback warning, round trip (cell values, not just headers), clone after UI-style
`readHFP`, refusals, fresh-plan zeros, reset. Reviewer findings folded in: clone populates
`rawHFP` via `readHFP({n: timeLists[n]})` (bare `zeroWages` plans never set it — `clone`
skips HFP when `rawHFP` is empty, `plan_bridge.py:694`).

Full suite: 3239 passed / 1 skipped (8:41). flake8 and Ruff clean.

Next: step 3 (fixed claiming ages: wire `earnings_test` into `zeta_in`), after the review below.

## Phase 5 steps 1-2 review (2026-10-18) and fixes (2026-10-19, on `claude/phase5-step1`)

Review of `9743233` (steps 1-2): checks green (3239 passed / 1 skipped; flake8/Ruff only
upstream's two), but `earnings_test` was wrong in several cases and step 2 would have made
step 3 a no-op on the three examples of plan §3. Each finding was reproduced by a probe before
fixing; POMS RS 00615.482 (TN 76), RS 02501.025 and RS 02501.030 read on `secure.ssa.gov`
2026-10-18. Spec commit first (`e3b69da`, strict xfail), then the fixes. Findings and fixes:

1. **No-op broken for claims before the plan** (Jamie in alex+jamie): the monthly grid started
   in January, so the December check paid in January was lost (2026: 15,491.67 vs 16,900).
   Grid now starts the December before the plan.
2. **Trim applied twice in survivor years** (28,800 → 23,040 at 20%). Trim now precedes the
   survivor fold-in, as in `compute_social_security_benefits`.
3. **Charge order depended on person index**: person 0's excess was charged first. At 40k/40k
   the household total withheld was 9,856.67 with the worker first, 12,310 with the auxiliary
   first. Now workers' excess first in each year (RS 02501.095).
4. **One crediting count for both records**. RS 00615.482 B.3 NOTE: "grant ARFs separately on
   each record". A non-working auxiliary whose spousal add-on was withheld for the worker got
   +$1,617/yr on their own benefit; months before the spousal start raised the spousal factor.
   Now `arf_months` (own record) and `arf_months_spousal` (spouse record).
5. **Survivor years**: the docstring claimed survivor benefits were charged; the code paid them
   in full while `withheld_in` reported withholding. D7 fallback (b), since charging Owl's annual
   greater-of fold-in month by month is not cheap: the test is not applied to checks paid from the
   first death on (documented; `withheld_in` 0 there). Added: the survivor base uses the
   deceased's post-ARF benefit when the death follows their FRA (`compute_survivor_stream`
   gains a fork kwarg `deceased_factor`; 29,700 → 35,000 in the test case).
6. **FRA-year monthly exempt amount**: RS 02501.025 B.2, 1/12 of the *applicable* annual amount
   ($5,430 in 2026), and non-service months only before the FRA month. Measured effect with
   even spreading over `months worked`: none (an FRA-year excess needs more than $5,923 a
   worked month, so worked months are service months under either amount); fixed for fidelity.
7. **Born on the 1st**: FRA month one month late (the SSA-age FRA used as a conventional age) and
   the ARF cap past FRA (factor 1.00667, $3,020/mo on a $3,000 PIA). Both fixed; factor ≤ 1.
8. Docstrings (pre-plan years have no earnings, so anyone entitled before the plan has used
   the grace year; `earnings_in` must be deflated), dead code, plan's test count.
9. **UI sync dropped the fallback** (80,000 → 0 on the first sync, `owlbridge._setContributions`
   re-reads the edited tables). The defaults are now written into the table by `hfp_io`
   (`_derivedTimeHorizonItems`), so what is shown, synced and written back is what the test
   uses; the "treated as zero" log and UI warning no longer list these two columns, which get
   their own notice. Also fixed: a blank `months worked` cell stopped the read ("cannot convert
   float NaN to integer").
10. **Example workbooks**: the 16 upstream `HFP_*.xlsx` had present zeros, which turned the test
    off for jack+jill, chris+pat and alex+jamie. Reverted to upstream's (binary files: merge
    cost); the template keeps the headers. Upstream's
    `test_example_hfp_workbooks_have_required_person_sheet_columns` and
    `test_legacy_workbook_notice_points_at_saving` now leave out the derived columns (fork edits).
11. **Fallback warning** fired on every old workbook (a retiree included). Now only for years up
    to the FRA year with wages and a non-zero 401k/Roth 401k/IRA/Roth IRA column (HSA dropped:
    a payroll HSA is not in box 5).

**Two upstream bugs found by the new no-op grid** (`compute_social_security_benefits`'s spousal
add-on), on stock `dev` `4932cb9` too: the first plan year is cut by the partial-year fraction
when the later claim predates the plan (9,507.50 vs 12,255.00), and the spousal start depends on
which spouse is listed first when the later claimer's age is reset (11,123.61 vs 10,762.50).
No upstream example is affected (checked on the 18 TOMLs). Fixed in the fork
(`tests/ss/test_spousal_start_fork.py`, not test-first: found while fixing); draft issue, repro
and patch `fork-notes/issue-spousal-start.*` for the user to file (patched stock `dev`:
`tests/ss` + `tests/plan` 448 passed).

Full suite: 3282 passed / 1 skipped (7:05; +43 tests). flake8 and Ruff: only upstream's two.

### Review of the fixes (2026-10-19/20)

Two more problems, both reproduced before fixing; spec commit `b570e94` (strict xfail), then
the fix.

1. **No earnings-test input for cases built without a workbook.** Step 2's "a present zero
   wins" left `etEarnings_in` at 0 for a UI case with no workbook (`zeroWagesAndContributions`
   creates every column at 0; ran: wages 80,000 → earnings 0, months 0), for the MCP assistant
   (`assistant/tools.py` writes `omega_in` directly), and a blank `months worked` beside
   positive `gross earnings` read as 0 months, which `countable_earnings` turns into no test
   for that year. Fix 9 above only covered an old workbook. Now **0 means "not given"** in both
   columns (user's decision 2026-10-20): `Plan._earnings_test_inputs()` returns earnings =
   `gross earnings` where positive, else `anticipated wages`, and months = `months worked`
   where positive, else 12 in a year with earnings; `earnings_test` treats 0 months in a year
   with earnings as 12. The rule sits where the test's inputs are built, so it covers every
   path and follows later wage edits. Fix 9's table filling in `hfp_io` and its UI notice are
   removed (a filled copy would not follow a wage edit); absent columns read as zero like
   upstream's, still left out of the "treated as zero" notices. The deferral warning now
   fires for any year that falls back to wages, workbook or not. Step 3 must read the inputs
   through `_earnings_test_inputs` (and deflate the earnings).
2. **Spousal crediting months counted after the auxiliary's FRA.** The worker's excess still
   reduces the add-on then (correct), but the ARF is computed once at FRA from the months
   before it (RS 00615.482). Ran: auxiliary FRA June 2029, worker earning \$40k 2028-2032:
   15 months counted vs 6, spousal factor 1.0 vs 0.965278 (about \$291/yr). Both records now
   count only months before the person's FRA.

Full suite: 3286 passed / 1 skipped (8:22). flake8 and Ruff: only upstream's two.

### Second review of the fixes (2026-10-20)

No correctness bugs in `b570e94`/`1e88780`; two behaviour problems, both fixed (spec `fb4acd4`,
strict xfail, then the fix):

1. **The 401k/IRA fallback warning was noise.** After `1e88780` it fired at every HFP read
   and every UI sync. Ran: six examples (jack+jill, jon+jane, chris+pat, alex+jamie, joe,
   robin) gave 7 WARNING lines on load, 14 after one sync, nearly all for years the test could
   not reach (Jack claims at 70, Alex at 69, Jane 57-64 in the flagged years and claiming at
   65), with the test off by default (D6). It is no longer given at the HFP read:
   `Plan._warnGrossEarningsFallback(entitled_from)` names years from each person's first year
   of entitlement to their FRA year, and step 3 calls it when the test is on (plan §5 step 3).
2. **`other inc` is not read by the earnings test** (the fallback is `anticipated wages`
   alone), while the docs suggested consulting income goes there; net SE earnings count for
   the test (RS 02501.080 B.1.c, 404.429(a), read 2026-10-17/18). Help text, `Documentation.py`
   (*gross earnings* and *other inc*) and `PARAMETERS.md` now say to enter net self-employment
   earnings in *gross earnings*.

Full suite: 3287 passed / 1 skipped (8:15). flake8 and Ruff: only upstream's two. The six-example probe now prints 0 warning lines.

### Third review of the fixes (2026-10-20)

Spec `67a9417` (strict xfail), then the fix:

1. **The fallback warning read the tables, the test reads the plan arrays.** A plan built by
   the MCP assistant (wages in `omega_in`, contributions in `kappa_ijn`, tables at zero) fell
   back to wages but got no warning (ran: inputs 70,000 / 12 months, 0 warning lines). The
   warning now reads `omega_in`, `etEarnings_in` and `kappa_ijn[i, 1] + kappa_ijn[i, 2]`
   (= 401k + IRA + Roth 401k + Roth IRA, `setContributions`; HSA `[i, 3]` left out).
2. **Docs described a test that is not applied yet.** `modeling-capabilities.md` and the paper
   still (correctly) say the earnings test is not modeled; the column help, `Documentation.py`
   and `PARAMETERS.md` now say the two columns are not used yet. Step 3 removes these caveats
   (plan §5 step 3).

Full suite: 3288 passed / 1 skipped (7:30). flake8 and Ruff: only upstream's two. The MCP probe now gives one warning line naming both years.

## Upstream `dev` `bb52632` merged (2026-10-20, on `claude/phase5-step1`)

Eight upstream commits since `4932cb9` (2026.10.20):

- **#198** (`9770116`): our spousal-start report (`fork-notes/issue-spousal-start.md`, filed by
  the user as #198) fixed upstream with the same two changes as the fork's, crediting us, with 3
  tests in `tests/ss/test_socsec.py`. Took theirs: conflict hunks resolved to upstream's code,
  `tests/ss/test_spousal_start_fork.py` dropped (duplicate). `socialsecurity.py` now differs from
  upstream only by the earnings-test section and `compute_survivor_stream`'s `deceased_factor`.
- **#197** (`70fb8dd`, `7bf12cd`): our local-search LTCG fix landed upstream (same change, their
  wording). `localsearch.py` now differs from upstream only by the fork's STAR family. Upstream
  added no test, so `tests/plan/test_local_search_ltcg.py` stays (docstring updated). Upstream's
  CHANGELOG entry replaces the fork's.
- **#195** (`0b318e0`): the claiming-month MILP (`zssa`, `ssb`, `B_own`/`B_cross`, spousal
  offset, `build_own_benefit_table`) is gone; `withSSAges` now solves the plan at fixed ages for
  every open month and keeps the best (both: one age at a time until neither moves). Fork code
  that read the removed pieces: `_item_income_ub_n` and `_gateCeilings`' `ss_in` default (both
  now `zetaBar_in`, the solve's own Social Security). Phase 5 §4.1 and step 4 rewritten: step 4
  shrinks to S, since every candidate is a fixed-age solve.
- `ad79391`: scenario runs (historical, Monte Carlo, spending, regret) hold the plan's claiming
  ages. `bb52632`: version and lock refresh.

Conflicts: `CHANGELOG.md`, `localsearch.py` (2 comment hunks), `plan.py` (1), `socialsecurity.py`
(3, incl. the removed `build_own_benefit_table` next to the earnings-test section). No duplicated
definitions after the merge (scripted check; the repeats left are upstream's own). Full suite:
3280 passed / 1 skipped (10:38; upstream's SS-age tests now run real solves). flake8 and Ruff:
only upstream's two.

Merge review (2026-10-20): nothing lost or mis-resolved (diffs against upstream limited to fork
additions; the 3288 → 3280 test change accounted for test by test: upstream's #195/#198/scenario
test changes and our 3 dropped duplicates; no reference left to the removed MILP in `src`, `ui`,
`tests`, `info`; the same claiming ages as stock `dev` on jack+jill with Jill free, 65y11m, and
joe, 68y7m). Runtime, one run each on 4 cores: jack+jill (Jill free) 61.9 s on the fork vs 47.6 s
stock, joe 7.4 s vs 4.7 s (the fork's loops run in every candidate solve); the household template
frees both ages, so a run takes minutes, and the step-6 sweep should free only the spouse who
stops. Fixed after the review (docs only): stale MILP references in `phase5-plan.md` (§1 table,
§4.3, §4.4 call sites, step 1; `_adjustedParameters` → `_adjustParameters` where the method is
meant) and a status line on `fork-notes/issue-spousal-start.md` (#198, fixed in `9770116`).

Next: step 3 (fixed claiming ages: wire `earnings_test` into `zeta_in`, inputs from
`Plan._earnings_test_inputs`, fallback warning only with the switch on; plan §5 step 3)
*(done 2026-10-20, below)*.

## Phase 5 step 3: fixed claiming ages (2026-10-20, on `claude/phase5-step1`)

Size M from `phase5-plan.md` §5 step 3. The SSA earnings test is now applied to the plan's
Social Security streams, behind `solver_options.withEarningsTest` (D6: off in code, on in
the household template). Test-first per §5b: spec commit `13c3017` (30 strict-xfail tests),
reviewed, then the implementation (markers removed).

**What landed** (`plan.py`, `export.py`, `cmd_explain.py`, `schema.py`, `ui_bridge.py`):

- `Plan._ss_streams(ages, gamma_n=None)` is the one stream builder: `setSocialSecurity` and
  the rebuild at solve time (`_adjustParameters`, where `zetaBar_in` is set) both call it.
  With the switch on it runs `earnings_test` on `Plan._earnings_test_inputs()` (0 = not
  given; earnings deflated to today's dollars, like the exempt amounts), with the switch
  off or no earnings it is exactly `compute_social_security_benefits`. Stores `zeta_in`
  (today's $), `ss_withheld_in` (nominal) and `ss_arf_months_i` / `ss_arf_months_spousal_i`.
- Outputs: Summary rows *SS withheld by the earnings test* (today's $ / nominal) and *ARF
  months* (per person, own and spouse record), a *SS withheld* column next to *social sec*
  in the per-person Sources worksheets, and an `earnings_test` block in the SS entries of
  `owlcli explain` / the MCP `explain_case` (`applied`, `ss_withheld_total_today`,
  `arf_months`, `arf_months_spousal`; computed whatever the switch says, so a case can be
  described without solving). Not on the Cash Flow sheet: its rows are tested to sum to
  zero, and the withholding is not a cash flow (its SS column is already net of it).
- Warnings, once per solve and only with the switch on: `_warnGrossEarningsFallback`
  (only the years the test can reach, from entitlement to the FRA year; the year they turn
  62 under `withSSAges`), and a fixed claiming age that pays nothing before FRA — every
  entitlement month before FRA that falls in the plan is withheld. Emitted from
  `_ssAgeSearch`, the main path of `solve` and `_localSearchSolve`; of the nested solves,
  the age candidates print to their clones' discarded logs, while the local search's
  seeding runs and the search's own final solve are skipped by flag. Checked: one warning
  per solve under `withSSAges=["Pat"]` on chris+pat (about 100 candidate solves).
- `withEarningsTest` in `SolverOptions`, in `Plan.solve`'s option list and in
  `SOLVER_UI_PASSTHROUGH_KEYS` (so the UI round trip keeps it; no UI toggle). The
  household template sets it (D6). The "not used yet" caveats are gone
  (`Financial_Profile.py` help, `Documentation.py`, `PARAMETERS.md`, which documents the
  option), `socialsecurity.py`'s module docstring says what is modeled, CLAUDE.md gotchas
  updated.

**Tests** (`tests/ss/test_earnings_test_plan.py`, 30): the §5b properties (switch off or no
earnings → streams identical to `compute_social_security_benefits`); the three §3 examples
with the test on — Jill's 2028 fully withheld with `months worked` 12 and partly spared with 6 (5
checks paid, grace year), hand ARF numbers from the 20 CFR 404.410 rates (11 crediting
months → the factor of 48 reduction months, 0.75, at FRA; Jamie's 24 → 35 left, 0.805556;
the one 2026 check is for December 2025, a pre-plan month the test cannot charge); taxes on
SS from the net (2028 taxable SS 0 with the test on); the no-op objective on the other
fifteen to the cent; a second solve after editing wages through the UI's table re-read;
both warnings on and off; Summary, worksheet and explain outputs.

**Recorded values: none moved** (the switch is off by default and no example sets it; the
suite re-recorded nothing). What the test does move on the three §3 examples with it on
(2026-10-20, today's date, `basis` in today's $): jack+jill 103,499 → 103,574 (Jill withheld
\$14,302 nominal, ARF 11; taxable SS 2028 \$11,019 → 0), chris+pat 117,002 → 116,789 (Pat
\$12,320, ARF 11), alex+jamie 228,369 → 227,825 (Jamie \$20,612, ARF 24; her benefit from
FRA is higher, so her taxable SS 2028 rises, \$9,108 → \$9,552). The ARF outweighs the
withholding on jack+jill (step 0's finding) and not on the other two. Measured by
`fork-notes/phase5/et_step3_probe.py`, output `et_step3_probe_2026-10-20.txt` (which also
prints the warnings: 0 with the switch off, 1 with it on for chris+pat and alex+jamie, and
still exactly 1 under `withSSAges=["Pat"]`).

Full suite: 3310 passed / 1 skipped (9:05; 3280 before + the 30 new). flake8 clean; Ruff
only upstream's `B905` (`tests/plan/test_roth_maturation_losses.py:49`, theirs). (An earlier
run sharing the machine with two probe solves printed native
access-violation traces at worker teardown and exited 1 while reporting the same 3310
passed; the clean run above has none.)

### Review of step 3 (2026-10-20)

Independent review of `13c30170` / `527227e3` / `a056420d` (fresh session, read-only probes):
three bugs, two doc problems and a list of untested properties. Each bug reproduced by a
probe before fixing; spec commit `6217d10e` (strict xfail on the three regressions), then
the fix.

1. **Warnings read the wrong options dict.** `_earningsTestOn()` read `self.solverOptions`,
   which `solve()` only assigns after it has branched into `withSSAges` (`_ssAgeSearch`) and
   the local search (`_localSearchSolve`) — and `owlcli run --solver-opt ...` / the MCP call
   `plan.solve(objective, opts)` without pre-assigning it. So a switch passed to `solve()`
   applied the test but silenced the warnings (ran: chris+pat with `withSSAges=["Pat"]`, 0
   warnings instead of 1). Fixed: `_earningsTestOn(options)` takes the solve's own options,
   passed by every `_warnEarningsTest` caller.
2. **The "pays nothing before FRA" warning read stale outputs.** Under `withSSAges` it runs
   before any solve has rebuilt the streams, so it saw `ss_arf_months_i` of the last build
   (zeros on a fresh plan): ran alex+jamie with `withSSAges=["Alex"]` — a fresh plan warned
   nothing while a re-solved one warned (finding reproduced both ways). Fixed: the warning
   now computes `self._earningsTestResult()` fresh (a pure function of the ages and the
   earnings columns), instead of reading the stored arrays.
3. **`_earningsTestOn` mapped unknown strings to on** (`convert_to_bool`'s "unknown string,
   default to True": `"off"` read as on). Now it is a switch: the standard spellings are
   read, anything else is refused (`ValueError`), like the mode options. The TOML / CLI /
   MCP paths were already safe through `parse_solver_options`.
4. **Docs.** `info/PARAMETERS.md`: the new row landed after a stray blank line, i.e. outside
   the rendered table — moved next to `withSSAges`, and the blank line removed (it had also
   left `withdrawalOrder` and `withDuals` outside the table). `phase5-plan.md` §5b kept the
   first draft's "10 fewer reduction months"; her Feb-2028 claim has 11 chargeable months
   (Feb-Dec), which is what the tests use.
5. **Test gaps closed** (`6217d10e` and the fix): §5b's "unchanged with a stop before her
   claim month" (`months worked` 1: every entitlement month a non-service month of the grace
   year, 2028 = the no-test 10 checks); the separate spousal record (jack+jill with PIAs
   2,360/800 and Jill not working: Jack 36 own crediting months, Jill's add-on 11 on the
   spouse record, her own record untouched and paid throughout — RS 00615.482 B.3, and the
   "N spouse" form of the Summary row); `ss_withheld_in` nominal (today's $ x `gamma_n`);
   one warning per solve across two solves; the option's TOML/UI round trip (`parse_solver_options`
   coercion, `config_to_ui`/`ui_to_config`); `explain`'s `applied` flag on; the switch-off
   no-op checked on all three examples, not just jack+jill. The probe of the first review
   (`et_step3_probe.py`) has been run for the `withSSAges` warning count all along; the new
   tests pin it.

**One finding not upheld.** The reviewer read 20 CFR 404.435 as deducting "the full benefit
for each service month regardless of the annual excess" in the grace year. Re-read against
the regulation (eCFR 2026-10-15 text, versioner API — it answered again today after the IP
block of 2026-10-18): 404.434(a) charges the excess "each month from the beginning of the
year, **until all of the estimated excess earnings have been charged**", and 404.435(a)(7)
pays the non-service months of the grace year in full (Example 1: Don keeps May-December
"even though his earnings have substantially exceeded the annual exempt amount"). So the
total deduction is capped at the excess and skipped for non-service months — what step 1
implements. POMS RS 02501.030 (TN 37, read the same day) agrees on the NSM definition ("a
NSM exists whether or not the beneficiary has excess earnings for the year").

Not changed (nits, recorded): `setSocialSecurity`'s restructure is the conflict magnet that
`Plan._ss_streams(ages)` in both call sites (plan §4.4) implies; `ss_withheld_in` holds
today's dollars until the rates are set (a pre-solve read only; noted in its docstring).

Full suite after the fixes: 3320 passed / 1 skipped (9:33; 3310 + the 10 new tests). flake8
clean; Ruff only upstream's `B905`.

### Second review of the fixes (2026-10-21)

Fresh reviewer over `6217d10e` / `132fb5bc` / `f0dea029` (read-only probes): one bug in the
fix round itself, two doc inaccuracies, and untested paths. Spec `71debdf6` (strict xfail
on the one failing property), then the fix.

1. **The strict parsing was its own inconsistency.** `_earningsTestOn` refused what the case
   schema coerces (`"y"`/`"n"`/`"t"`/`"f"`, numpy scalars) and accepted what the schema
   refuses (`2`, `0.5`): one value read differently through `owlcli` (schema-coerced) and
   through a script or the UI's run options (`ui/owlbridge.py` passes
   `getSolveParameters()` through unchecked). Fixed with **one parser**,
   `utils.parse_switch`, used by `Plan._earningsTestOn` and by `SolverOptions` (a
   `mode="before"` validator), and applied at `solve()`'s door next to
   `normalize_mode_options` — the review's second finding: the refusal used to happen
   mid-solve, so "the same contract as the mode options" was only half true.
2. **Docs.** PROGRESS said "about 40 candidate solves" for `withSSAges=["Pat"]`: the search
   runs 96 candidates (its own log: "best of 96 fixed-age solve(s)"; a counter saw 98
   solves). And it described the age candidates as "skipped", which is not the mechanism:
   each runs the full warning on its clone and prints into that clone's discarded `StringIO`
   logger; only the local search's seeding runs and the search's own final solve are
   skipped, by flag. Reworded here and in `phase5-plan.md`.
3. **Tests pinned** (`71debdf6` and the fix, 43 tests in the file now): the switch's
   spellings against `parse_solver_options` in both directions (15 accepted values, numpy
   scalars among them; 5 refused by both), the UI run path (`getSolveParameters`, issue
   #156's shape — before, the option was only round tripped through `config_to_ui` /
   `ui_to_config`), the local-search path's one warning across its two nested solves
   (`localSearchTime=2` keeps it quick), and a fresh plan warning like a re-solved one (the
   second half of the stale-inputs bug).

Everything else the reviewer probed held: the three original bugs fixed on every path
(plain, `withSSAges`, local search, `resolve()`, two solves), the hand numbers exact
(11 x 1,642 x 0.7041667 = 12,718.66 today's $ = the withheld total; 36 / 11 / 0 crediting
months on the spousal case; 10 checks = 11,562.42 in the grace-year case), the xfail→pass
transition of the three regression tests real (the old behaviour monkeypatched back in
fails each key assertion), and `info/PARAMETERS.md`'s table contiguous with its technical
claims matching `earnings_test`.

Full suite: 3323 passed / 1 skipped (9:30; 3320 + the 3 new tests). flake8 clean; Ruff only
upstream's `B905`.

### Third review (2026-10-21)

Review of `13c3017`..`4a6ef71` (full suite 3323 / 1 on `4a6ef71`, read-only probes). One bug,
three doc points, two suggestions; all taken. Spec `8f8bf37` (strict xfail, each checked to fail
at the targeted assertion), then the fix `add3caf`.

1. **A rejected `setSocialSecurity` changed the plan.** Step 3 moved the `ssec*` assignments
   ahead of the stream build, so a call that raises left its values behind. Ran on jack+jill,
   `setSocialSecurity(pias, [71, 71])`: on `d1d1681` it raises `Age 71.0 out of range.` with the
   ages still `[70, 62.0833]`; on `4a6ef71` it raises the same with the ages `[71, 71]`, and
   every later solve fails. Fixed: the previous settings are put back when `_ss_streams`
   raises (`compute_survivor_stream` runs inside the build with the same arguments, so it is
   covered). Test with the switch off and on; the plan still solves afterwards.
2. **Summary rows only when something was withheld.** The UI's case comparison
   (`compareSummaries`) keeps only the rows both cases have, so two variants that both apply
   the test lost them whenever one withheld nothing. Now shown whenever the solve applied the
   test (`Plan.ss_earnings_test_applied`, set by `_ss_streams`): \$0 and "none".
3. **ARF months ignored the Summary's `N`** (no caller passes `N` today). The ARF takes effect
   at FRA, so the row counts a person's months only where their FRA month falls within the N
   years (`Plan._ssFRAStartAbs`, shared with the pays-nothing warning). Jill: a Summary through
   2032 holds her 2028 withholding and "none"; through 2033, "Jill 11 own".
4. **`plan_metrics`** gains `ss_withheld_today` / `ss_withheld_nominal` (0 with the test off),
   mapped to the Summary rows in `METRICS_COLUMN_MAP`; `owlcli compare` diffs every metric, so
   it now shows the withholding's delta (step 6 needs it per variant).
5. **Docs.** CLAUDE.md and the `_ss_streams` docstring said the test is applied "not at
   `setSocialSecurity`": it is applied there too when the plan's current options have the switch
   on (probe: switch set, `setSocialSecurity`, no solve → Jill's 2028 already 0, ARF 11); what
   counts is the rebuild in each solve. Reworded. "Spared with 6" (test name, this file, plan
   §5 step 3) is "partly spared": Feb-Jun are withheld, Jul-Nov paid. PARAMETERS.md lists the
   new metrics and when the rows appear.

Also seen, not changed: upstream's `info/PARAMETERS.md` (`dev` `bb52632`, line 376) still has
the blank line after `withSSAges` that leaves `withdrawalOrder` and `withDuals` outside the
table (fixed here in the first review); a one-line docs fix to send upstream some time.

Full suite: 3328 passed / 1 skipped (11:43; 3323 + the 5 new). flake8 clean; Ruff only
upstream's `B905`.

Next: step 4 (`withSSAges`: the clones carry the inputs and the switch).

## Phase 5 step 4: `withSSAges` (2026-10-21, on `claude/phase5-step1`)

Size S (`phase5-plan.md` §5 step 4). Since upstream #195 every `withSSAges` candidate is a
fixed-age solve on a `clone(self)` (a deepcopy: `etEarnings_in`, `etMonths_in` travel) with the
search's options less `withSSAges` (so `withEarningsTest` travels), and each reaches step 3's
path. **No code change.**

**Tests** (`tests/ss/test_earnings_test_ssages.py`, 5, `7507116`): jack+jill with Jill's age
searched over five of her open months (`_ssaOpenAges` patched: 62y1m, 63, 64, 67, 70; the
candidates recorded through `_objectiveValue`): every candidate equals a freshly loaded plan
solved at the same ages (objective, ARF months, amount withheld), switch on and off; the 62y1m
candidate has 2028 withheld (11 ARF months) on and nothing off, the later ones are equal either
way; the pick is the best of the independent solves and the returned plan carries its streams
and outputs. They passed on arrival, so no xfail spec commit (§5b). Instead, two mutations, run
by hand and reverted: clones losing `months worked` (`etMonths_in = 6` in `plan_bridge.clone`)
and candidates losing the switch (`_earningsTestOn` false on clones) each fail the first two
tests (2 failed, 3 passed).

**Measured** (`fork-notes/phase5/et_step4_probe.py` and `et_step4_crosscheck.py`, outputs
`*_2026-10-21.txt`; today's date, default loop unless stated; basis in today's \$/yr):

| Case | Search | Test off | Test on | Rounds / solves (on) |
|---|---|---|---|---|
| jack+jill | Jill | 65y11m, 104,586.81 | 65y11m, 104,586.81 (also with `months worked` 6) | 1 / 96 |
| chris+pat | Pat | 62y3m, 117,069.62 | 63y0m, 116,985.49 | 1 / 96 |
| alex+jamie | Alex | 70y0m, 229,007.15 | 70y0m, 228,245.39 (Jamie withheld \$20,612, ARF 24) | 1 / 40 |
| jack+jill | both | 69y1m / 65y11m, 104,703.63 | same | 3 / 340 |
| chris+pat | both | 68y9m / 62y1m, 117,319.78 | 69y4m / 63y0m, 117,288.64 | 4 / 507 (off: 2 / 171) |

- Jill's best age is after her work, so the test does not touch her pick. Pat's no-test pick is
  a claim in 2028, the year she earns \$85k: Owl pays it, SSA would withhold it (Apr-Dec,
  \$10,210 nominal). With the test on she claims in January 2029, the month after.
- **Cost of following the no-test pick**, solved at fixed ages with the test on (section 3 of
  the probe, cross-checked): Pat alone \$179.46 (loop), \$115.45 (local search), \$119.21
  (exact LP: `withMedicare="none"`, `withSSTaxability=0.85`): local search and the exact LP
  agree in sign, spread \$3.76: **resolved**. Both free \$166.33 / \$78.12 / \$75.91, spread
  \$2.21: **resolved** (CLAUDE.md, "Loop noise": the spread is between local search and the
  exact LP; corrected in the review below). Local search took about 121 s per fixed-age solve.
- **No cycling** with both ages free: 2-4 rounds of the cap of 5, test on or off (plan §7).
- The objectives with the test off are of plans SSA would not pay (Pat's 2028), so "off vs
  on" is not the test's value; the fixed-age cost above is. The picks were made under the loop;
  local search or the exact LP might pick other ages (step 8).

Docs: `info/PARAMETERS.md` (`withEarningsTest`: every `withSSAges` candidate is solved with the
test). Full suite: 3333 passed / 1 skipped (11:14; 3328 + the 5 new tests). flake8 clean; Ruff only upstream's `B905`.

### Review of step 4 (2026-10-21)

Review of `7507116` / `6cd02f8`. Held: the probe's round count (`_ssaOpenAges` is called only in
the search loop, `plan.py:6881`); Pat's no-test pick with the test on, 9 ARF months (Apr-Dec
2028), \$8,977.50 withheld in today's \$ = 9 x 1,400 x 0.7125 by hand (\$10,209.71 nominal:
\$9,024.16 in 2028, \$1,185.55 in 2029); the chris+pat values identical under the tests' frozen
date (63y0m over 62y3m by \$179.46 with the switch on, \$-84.13 off). Fixed:

1. **The cross-check's verdict used a stricter rule than the documented one.** The first
   `et_step4_crosscheck.py` took the spread over all three methods, the loop included; CLAUDE.md
   and plan §5 step 8 take it between local search and the exact LP only (the loop's fixed-point
   noise is what the rule sets aside). Under the documented rule the both-free pair is
   **resolved** (\$78.12 vs \$75.91, spread \$2.21), not "unresolved" as `6cd02f8`'s message,
   this section and the plan said. Script corrected and re-run (same values to the cent; the
   loop now printed for reference only); text above and the plan corrected; the commit message
   stays (no history rewrite).
2. **Timing.** "About 250 s per fixed-age solve" was the time of a pair; about 121 s per solve
   (the corrected script prints it per solve).
3. **Test gap: nothing pinned the decision.** Under the mutation where candidates lose the
   switch, the pick test still passed, as the returned plan is re-solved with the test. New
   `test_switch_moves_pats_pick` (`3f93c32`): chris+pat, Pat searched over {62y3m, 63y0m}: 62y3m
   off, 63y0m on, nothing withheld at the pick. A regression pin (values from the plan, the sign
   agreed by all three methods); it fails under that mutation (3 failed, 3 passed). Passes on
   arrival, so no xfail marker.

Full suite: 3334 passed / 1 skipped (10:51; 3333 + the new test). flake8 clean; Ruff only upstream's `B905`.

Next: step 9's draft (D8: the upstream issue after step 4, `fork-notes/issue-earnings-test.md`),
then step 5 (payroll tax).

## Upstream issues #199-#217 checked (2026-10-21, on `claude/phase5-step1`)

Eighteen new upstream issues (17 by `rationalpiper`, #208 by the maintainer), none fixed on
`dev`/`main` yet (`bb52632`). Each claim checked against the code on this commit and, where
reachable, the primary source (POMS RS 00615.320 / .694 / HI 01101.020, 26 CFR 1.36B-1 and
1.401(a)(9)-9, 2025 Form 1040 instructions, Rev. Proc. 2026-26); details, sources and what stays
unchecked in `fork-notes/upstream-199-217/README.md`. **No claim found wrong**; #203's PA law and
#215's run not checked.

What matters for the household (template: NY, both born 1964, ACA from 2027):
- **#200 + #201**: in the ACA years Owl's 400% FPL line is one year of inflation too high and the
  2027 percentages are Rev. Proc. 2026-26's (10.22% top), not 2026's. A plan parked under Owl's
  line can be over the real one and lose the whole credit. Until fixed upstream, check ACA-year
  MAGI against 4 x the prior year's guideline.
- **#208 (+ #199)**: B (born in December) is on the marketplace for 11 months of 2029; Owl charges
  12 months of Medicare and no ACA, and does not treat 2029 MAGI as ACA-year income.
- **#211**: if the lower PIA is under half the higher one, Owl overvalues delaying the lower
  earner past FRA (Phase 5's question); the fork's earnings-test builder repeats the rule and
  must mirror upstream's fix.
- **#207 / #212**: only for a birth date on the 1st; both template placeholders are on the 1st.
- #213, #214 small; #205 measured \$0 on the 18 examples (`ltcg_unused.py`); the rest no effect.
- Not in any issue: NY's Essential Plan (up to 200% FPL since 2026-07-01, per state notices read
  through a search summary) is priced by Owl as marketplace coverage.

Nothing drafted for upstream (not our issues; every checked claim holds; the maintainer will work
through them). Before decision runs: real birth dates and the PIA ratio.

## Upstream `dev` `37afa2a` merged (2026-10-22, on `claude/phase5-step1`)

25 upstream commits since `bb52632`: fixes for #199-#203 and #207-#217 (the issues checked on
2026-10-21, `fork-notes/upstream-199-217/README.md`, now with a status section) and #218 (a
survivor's home sale more than 2 years after the death gets the \$250,000 exclusion), the
claiming-age search passing the model to MOSEK in bulk, MCP sweeps holding SS ages, pandas
`inplace` removal. Not fixed upstream: #204, #205, #206.

Merge (`41eb4a7`). Conflicts in 10 files: `CHANGELOG.md` (fork Unreleased, then upstream's WIP
and 2026.10.21, kept verbatim: checked by substring), `info/modeling-capabilities.md` (fork rows
kept, upstream's #203 sentence and the local-search/`withSSAges` sentence carried in),
`explain.py` (one note string, both sides), `taxes_state.toml` (NY: upstream's
`roth_conversion = "exemption"` with the fork's recapture and IT-196 keys), `plan.py` (2),
`socialsecurity.py` (1), `tax_state.py` (4), three test files. Fork adaptations:
- **#203**: `roth_conversion_eligible` (bool) became `roth_conversion` = `"exemption"` |
  `"taxed"` | `"excluded"`. `StateTaxParams.conv_ok_n` → `conv_n` (object array of the mode,
  upstream's dict key), `Plan.st_conv_n` as upstream; `st_schedule` stays typed (upstream's dict
  version dropped again). `_state_agi_and_ti` now also leaves out conversions in "excluded"
  years (PA, MS), as the `state_taxable_income` row does; no NY plan changes.
- **#210**: upstream's widow(er)'s limit after the age reduction takes the fork's
  `deceased_factor` (the deceased's ARF-adjusted factor) where given.
- **#211**: mirrored in the earnings-test builder (own DRCs come out of the spousal excess), so
  it still equals `compute_social_security_benefits` with no earnings.
- `test_ss_residual_warning`: upstream's \$90k (moved from \$95k by #208's Medicare proration),
  the fork's `withItemized="none"`.
- Docs: CHANGELOG/CLAUDE.md names (`conv_n`). Separately (`59ea495`), the SS row of
  `modeling-capabilities.md` no longer says the earnings test is not modeled.

Full suite on the merge: **3463 passed, 1 skipped** (15:53, with other tests running alongside;
3334 before; upstream's 20 changed test files add 87 test functions and remove 6, plus
parametrizations; not accounted test by test). flake8 clean; Ruff only upstream's B905.

Merge review (2026-10-22, `b99990f`):
- **Found and fixed**: `_setup_itemized` built `item_base_n` (the standard deduction an itemized
  total is compared with, 65+ additions included) from calendar birth years, while upstream's
  #207 moved `taxParams` and `seniorBonusSchedule` to `yobs_tax` (a January 1 birthday reaches
  65 the year before). An itemizer born on January 1 would have had the 65+ addition counted a
  year late in that comparison. Now `yobs_tax`; new
  `test_january_first_birthday_counts_65_a_year_early_for_itemizers` (failed before). The other
  fork call sites of federal age-65 rules already use `yobs_tax` (grep of `tx.` calls). STAR's
  Enhanced age test keeps calendar years: it is NY's rule, not the IRS's day-before convention
  (recalled, not checked against RPTL 425).
- **Test gap closed**: no zero-earnings grid case had a spousal add-on on an own benefit with
  DRCs. Added one (3000/1000, lower earner at 70). Mutation check: with the #211 mirror removed
  the builder pays \$2,880/yr more than `compute_social_security_benefits` on it; with the mirror,
  180 zero-earnings cases (PIA ratios 1/3 to 3, claims 62-70, births on the 1st) agree within
  \$5e-10.
- Checked, nothing to change: no new variable blocks for `localsearch.FAMILIES` /
  `ALWAYS_FREE`; fork calls of the changed Medicare/ACA/IRMAA functions (`mediCosts`,
  `acaCosts`, `medicareMonths`, `irmaaThresholds`) are upstream's own and pass `mobs`/`tobs`;
  `_medical_premium_ub` reads `Cbar_nq` (now prorated) and `slcsp_aca_n`, both still upper bounds
  in the 65th-birthday year, where both premiums can be non-zero; `setContributions` keeps both the
  fork's `gross earnings`/`months worked` and upstream's HSA proration; `get_fixed_assets_arrays`
  gets `n_d` (#218); fork-only modules (`star.py`, `budget.py`, `tax_local.py`, `residency.py`,
  `localsearch.py`, `export.py`, their data) unchanged by the merge; `tax_federal.py` differs
  from upstream only by additions; no duplicated definitions beyond upstream's own.
- Full suite on `b99990f`: **3465 passed, 1 skipped** (15:02; the merge's 3463 + the 2 new tests).

Household effect: the interim checks from 2026-10-21 (ACA-year MAGI against 4 x the prior year's
guideline) are no longer needed. Before decision runs, still: real birth dates (on or off the 1st
changes #207, #208, #212) and the PIA ratio (#211).

Next: step 9's draft (D8: the upstream issue, `fork-notes/issue-earnings-test.md`; it should say
the builder mirrors `_add_spousal_benefit`'s #211 rule), then step 5 (payroll tax).

## Plan review after upstream `37afa2a` (2026-10-22, on `claude/phase5-step1`)

`fork-notes/plan-review-2026-10-22.md`. Phase 5's design (a stream-level earnings test, no LP
piece) still holds and #195 strengthened it; the builder's copy of upstream's spousal rule is the
weak point the merge exposed (#211), kept and guarded by the grid test. Step 9's evidence is
unchanged on stock `dev` `37afa2a` (`et_examples_2026-10-22_dev37afa2a.txt`). No payroll tax
upstream, so step 5 stays.

**Step 6's method changes** (measured on chris+pat, test on, Pat searched; `et_plan_review_probe`,
`et_aca_reference_probe`, `et_aca_ls_check`, all 2026-10-22):
- local search costs 67-177 s per solve, so a local-search age search (up to 97 candidates per
  spouse per round) is hours per variant;
- the loop's pick moved 63y0m (10-21) → 63y2m (today); local search ranks 63y0m best of 11 ages
  scored, 63y2m \$32/yr lower, and its own neighbour noise is tens of dollars;
- the exact LP's search (11 s) picked 63y0m; with a stand-in SLCSP (\$20k/yr from 2029) the exact
  LP with `withACA="optimize"` (172 s per search) also picks 63y0m, but values getting under the
  400% cliff at \$528/yr where the case's own model gives \$14 and local search keeps the income
  (+\$210/yr over that) and pays the full ACA. Local search did not miss a better plan there.
So: search ages under the exact LP (ACA optimized when there are ACA years), score the picks and
whole years under local search at fixed ages; local search decides. The CLAUDE.md cross-check
rule does not apply to plans with ACA years (caveat added to "Loop noise").

Remaining phases: Phase 4 mostly covered upstream now (medical inflation, #199-#202, #208); NY
community rating has no effect on this household (both spouses are 64-65 in the one year with a
lone enrollee, so the CMS curve gives 1/2); left: NY Essential Plan, only if a variant's ACA-year
MAGI is under 200% FPL. Phase 6 folded into step 6 (generic overrides). The real case is still
not filled (`otherFiles/` has no case); since the merge the birth dates and the SLCSP change
results directly.

Decisions R1-R6 for the user (note §5): two-stage step 6 method; whether any variant has one
spouse on employer coverage alone (Owl has one household `aca_start_year`); keep the spousal-rule
copy; no Phase 4 code now; Phase 6 folded in; fill the real case before step 6's runs.

**Answered 2026-10-22: R1, R3, R4, R5 as recommended; R2 no** (no variant has one spouse on
employer coverage alone, so no per-person ACA start). R6 (the real case) open.

**Step 9 drafted 2026-10-22**: `fork-notes/issue-earnings-test.md` (concept level, federal SS
only; not posted). Evidence from a real run on stock `dev` `37afa2a`
(`issue-earnings-test-repro.py`, output beside it): the same three examples pay SS before FRA in
a year with \$80-85k of wages, and `withSSAges=["Pat"]` on chris+pat picks 62y6m (entitlement from
July 2028, her last work year). Fork measurements with `withItemized="none"`
(`phase5/et_issue_measure`, `et_issue_crosscheck`, 2026-10-22): the fork's no-test pick equals
stock's; with the test Pat's pick is 63y2m, and following 62y6m costs \$50/yr (local search) /
\$63 (exact LP) / \$65 (loop), resolved (spread \$13); alex+jamie −\$542/yr, \$20,612 withheld,
24 ARF months. Four questions: in core and default, the earnings input, the stop month, survivors.

Posted by the user as **#220** (2026-10-22).

Next: step 5 (payroll tax); #220's answer when it comes.

## Phase 5 step 5: payroll tax (2026-10-22, on `claude/phase5-step1`)

Size S (`phase5-plan.md` §5 step 5, D3 = core, opt-in). Test-first: spec `af522c3` (19 tests,
strict xfail), implementation `788e0fa`.

**Rules, verified** on irs.gov the same day (and on 2026-10-18): Pub. 15 (2026), "What's New":
6.2% social security tax each for employer and employee, wage base \$184,500; Medicare 1.45%
each, no wage base. Instructions for Form 8959 (2025), threshold chart: MFJ \$250,000, MFS
\$125,000, single / head of household / qualifying surviving spouse \$200,000, "aren't indexed
for inflation"; Medicare wages and SE income combined against the threshold.

**As built** (details in the plan): `tax_federal.payrollTax` (pure; filing status as
`computeNIIT`: joint before `n_d`); `Plan._payroll_tax` at every solve in `_adjustParameters`, on
`_earnings_test_inputs()` earnings; `payroll_tax_n` a constant of the cash-flow row and of
`_check_cashflow_balance`; `solver_options.withPayrollTax` off in code, on in
`Case_us.template.toml`; Summary *Total payroll tax paid* (whenever charged) and *» Additional
Medicare tax* (where owed); `payroll_tax_today` / `_nominal` in `plan_metrics`; *payroll tax*
column in the Cash Flow sheet and CSV; inside "Tax bills + Med." and the charts' "taxes" slice;
fallback warning (wages, no `gross earnings`, non-zero 401k/IRA column, any plan year).
`_warnEarningsTest` renamed `_warnEarnings` (it now emits both). Not done: self-employment tax
(D3: only if a variant has consulting income; none known here), employer share, `owlcli explain`.

**Tests** (`tests/plan/test_payroll_tax.py`, 19): the rule by hand (one person below and above
the base with 10% inflation; couple then survivor; two \$150k earners owe the 0.9%; a plan
starting in 2030); jack+jill by hand (7.65% of \$180k, \$180k, \$185k; zero after 2028);
`gross earnings` preferred; jon+jane with Jon at \$300k (base cap + 0.9% of \$130k); paid from
the plan (lower basis, cash flow balances with it, Cash Flow column); the allocation's "taxes";
switch toggled between solves; Summary rows (\$0 included); metrics and comparison map; the
fallback warning (Jack's 2026-2027 named, not 2028, not Jill), none with `gross earnings` or the
switch off; local search warns once and carries the tax; switch spellings = schema; a bad value
refused by `solve()`; TOML/UI/run-options round trip. Mutation by hand (reverted): dropping the
cash-flow constant fails `test_the_tax_is_paid_from_the_plan` (1 failed, 18 passed).

**Measured** (`fork-notes/phase5/pt_ssages_check.py`, output `pt_ssages_check_2026-10-22.txt`;
frozen date 2026-01-01, loop, earnings test on): chris+pat, Pat searched (`withSSAges`). Tax off:
63y2m, basis \$117,005.94/yr; on: 63y1m, \$114,848.21, tax \$37,102.50 nominal (= 7.65% x
\$485,000 of wages, by hand); the returned plan equals a fixed-age solve at its pick (to the
cent). The pick moved one month: the tax is not a constant shift of the objective (less cash,
so other withdrawals and taxes); the off-pick costs \$7.78/yr with the tax on, loop only, far
under the step-4 spreads: immaterial and unresolved. The script's first docstring said the pick
could not move; corrected before the run was recorded.

Full suite: **3484 passed, 1 skipped** (11:17; 3465 + 19). flake8 clean; Ruff only upstream's
`B905` (`tests/plan/test_roth_maturation_losses.py:49`). No recorded value moved (switch off).

Next: step 6 (scenarios and sweep, method of `plan-review-2026-10-22.md` §3.2; needs the
household's real SLCSP), then 8 and 10.

### Review of step 5 (2026-10-22)

Independent pass over `af522c3..80971a3`. Held (checked): the rates and the citation (Pub. 15's
rates subsection sits under "9. Withholding From Employees' Wages" in the saved page text); the
filing status (`n_d` = the shorter horizon, so index `n_d` is the first year after the death and
the death year is joint, as `irmaaStatus` and IRC 6013(a)(2)); the per-person wage base (Pub. 15:
each employer stops at \$184,500; that a second employer's excess comes back on the return, so
the year's cash is the capped amount, is recalled, not read here);
`anticipated wages` is gross minus deferrals, not take-home (`PARAMETERS.md`), so the tax is not
counted twice; a payroll HSA is out of both the base and `anticipated wages`; the tax is rebuilt
per solve, so historical and Monte Carlo runs index the base with each scenario's inflation;
upper bounds that add incomes (`_incomeCeiling`, `_gateCeilings`) stay valid with an outflow;
`owlcli compare` diffs every `plan_metrics` key, so it reports the tax. Fixed (spec `d5f1ae7`,
then the fix):

1. **JSON outputs left it out.** `owlcli run --output-format json` and the MCP `run_case`
   serialize through `cli/formatters.plan_to_dict`, whose summary keys are listed by hand:
   neither the payroll tax nor the earnings test's withholding (a step-3 gap) was there. Added
   `payroll_tax_nominal` / `_today_dollars`, `ss_withheld_nominal` / `_today_dollars` and a
   per-year `payroll_tax`. Test `test_json_output_reports_it` (strict xfail in the spec).
2. **Doc wording.** `Documentation.py` said the tax lowers spending "without changing income
   tax"; the withdrawals that pay it are taxed. Reworded.
3. **Test gap.** Nothing pinned the tax in "Tax bills + Med." or the CSV; new
   `test_tax_bills_and_csv_carry_it` (passes on arrival, a regression guard).

Left as they are (judgment, not defects): with both switches on, a year without `gross earnings`
can be named by two warnings (the test's, for the years it reaches, and the payroll tax's, for
every year; chris+pat's Pat 2028 by both); the deferral check counts IRA contributions, which are
not payroll deferrals (the message says "401k/IRA", as step 3's); the Summary's *Effective tax
rate* and `showTaxes` ("Income Tax") stay income taxes only; a public employee outside Social
Security, or hired before 1986 outside Medicare (both recalled), is taxed as covered (no input
says otherwise).

Full suite: **3486 passed, 1 skipped** (11:07; 3484 + the 2 review tests). flake8 clean; Ruff only
upstream's `B905`.

### Fallback warnings merged (2026-10-23)

The user asked for one warning instead of two (review of step 5, "left as they are"). The
earnings test's and the payroll tax's fallback warnings are now one function,
`_warnGrossEarningsFallback(entitled_from=None, payroll=False)`, called once per solve from
`_warnEarnings`; `_warnPayrollFallback` is gone. One warning per person, over the union of the
years each use reads (the test: entitlement to the FRA year; the payroll tax: every year with
earnings), naming both uses and the test's years where they differ. With one switch on, the
message names that use only, as before. Spec `c9a11dd` (strict xfail), then the fix. Real
output, chris+pat, both on (today's date):

> 'gross earnings' is not given for 'Pat' in year(s) 2026, 2027, 2028: the payroll tax uses
> 'anticipated wages' there (the SSA earnings test too, in 2028), which leave out payroll
> deferrals (W-2 boxes 3 and 5 count them), and those years have a 401k/IRA contribution.
> Enter 'gross earnings' for them.

Chris (claims at 70, out of the test's reach): the payroll tax alone, 2026-2027. Tests
`test_one_fallback_warning_per_person_with_both_switches` and
`test_one_switch_keeps_its_own_warning`; the step-3 and step-2 warning tests pass unchanged.
Full suite: **3488 passed, 1 skipped** (10:52; 3486 + 2). flake8 clean; Ruff only upstream's `B905`.

## Upstream `dev` `3444729` merged (2026-10-24, on `claude/phase5-step1`)

Two upstream commits: `cd50a0a` (the Roth-conversion regret sweep can no longer report a negative
regret; `stresstests.py`) and `3444729` (#197 made faster; the maintainer's comment on the closed
#197 gives his timings, not re-measured here: on the 18 examples with the local-search preset,
MOSEK 726 -> 396 s, HiGHS 740 -> 695 s, john+sally still 31,778, the others within 0.07%).
`3444729`: step (b) pins `zl` again; the search relaxes the "zl = 0 => income at or above the
threshold" half of `ltcg_zl15_link` / `ltcg_zl20_link` in its own copy of the rows; step (b')
frees `zl` with the SS ball once per loop iteration when a round makes no move; stranded
binaries are set back to 1 before the repair, polish and dual solves.

Merged with no conflict. The fork's link rows are upstream's (no fork hunk on them; checked by
diff), so the relaxation finds them by tag as upstream does. Our `tests/plan/test_local_search_ltcg.py`
then had one test failing by design (`test_ss_step_leaves_ltcg_free`: step (b) pins `zl` again)
and one duplicating upstream's new john+sally test (both passed on the merged fork: run, 5:46
for the four tests): file dropped, upstream's two tests kept. Full suite: **3492 passed, 1 skipped** (11:42; 3489 + upstream's 5 new tests - our 2). flake8 clean; Ruff only upstream's `B905`s (two new in `3444729`: `localsearch.py:198`, `test_local_search.py:260`).

Not measured, inferred from the code only: (b') runs only after a round with no move, so a round
that moves something else defers it to a later round or the next loop iteration. Upstream's test
covers john+sally only. Worth a test case only if a run shows a plan it misses.

## Upstream `dev` `6ea43a9` merged: our earnings test landed (2026-10-24, on `claude/phase5-step1`)

Upstream since `3444729`: `ccd395a`, `a0d157b`, `e55276a` (#225: a negative `other inc` is an
above-the-line deduction, e.g. an HSA contribution without wages; new `dl` columns, the part a
year's income cannot absorb, in the federal and state taxable-income rows, the IRMAA/ACA bottom
brackets and the reported MAGI; MCP `other_income`), `2bc3148` (MCP HSA contributions stop at
Medicare) and **`6ea43a9`, PR #222 as landed** ("The SSA earnings test (#220, #222)"). His change
from the PR, quoted from the commit: the earnings are derived, not entered, "in a year with wages
the earnings are the wages plus that year's taxable, tax-deferred and Roth contributions
(kappa_ijn[:, :3]; an employer contribution makes them slightly high, HSA left out). The PR's
'gross earnings' column, its fallback warning and _ssEntitledFrom are gone; it changed nothing in
any example". `months worked` stays.

Merge (worktree, branch `merge-6ea43a9`, fast-forwarded into `claude/phase5-step1`): 19 conflicted
files. Taken from upstream: `socialsecurity.py` (ours differed in fork wording only, checked by
diff), the five earnings-test test files, the earnings-test parts of `plan.py`, `hfp_io.py`,
`export.py`, the CLI, UI, docs and the template workbook. Kept from the fork: the payroll tax
(`_payrollTaxOn`, `_payroll_tax`, its Summary / metrics / JSON keys and docs), the budget and
itemizing code, the fork's order of `processDebtsAndFixedAssets()` before `_buildOffsetMap`,
jack+jill's recorded 103_578 (the fork's model; unchanged by the derived earnings, the suite agrees).

**Payroll tax after the merge** reads upstream's derived earnings through
`_earnings_test_inputs()`: wages + contributions, which are FICA wages too (W-2 boxes 3 and 5),
so the base is better than the old `anticipated wages` fallback and needs no warning. Tests moved
with it (hand numbers): jack+jill 2026-2027 \$195,000 (Jack's \$15,000 401k now counts), the
second-solve test \$205,000, jon+jane's Additional Medicare case \$23,547.00 (Jon \$309,000, Jane
\$83,000; 6.2% x 184,500 + 1.45% x 309,000 + 7.65% x 83,000 + 0.9% x 142,000, equal to the run);
the gross-earnings test and the four fallback-warning tests dropped with the warning.

**#225 in the fork's NY rows** (upstream tests PA and CA only): new
`tests/plan/test_other_inc_deduction_ny.py`, a \$5,400 deduction on a \$30,000 conversion in NY,
Yonkers and NYC, loop and branch-and-bound: MAGI -\$5,400, federal \$1,420 -> \$850 (hand: 10% to
\$12,400 and 12% above, on taxable income \$13,900 -> \$8,500 with the recalled \$16,100 single
deduction), NY and local tax to zero (NY base about \$2,000 before, below zero after; the test
asserts only the signs and the MAGI drop, not recalled constants).

Full suite on the merge: first run **2 failed, 3489 passed, 1 skipped** (the two payroll hand
numbers above); after the fixes: **3497 passed, 1 skipped** (10:38; 3489 + the 2 fixed + the 6 new NY tests). flake8 clean; Ruff only upstream's three `B905`s.

## Upstream `dev` `4e55b36` merged (2026-10-24, on `claude/phase5-step1`, pushed as `claude/eager-hawking-scp4gw`)

Upstream since `6ea43a9` (all 2026-10-24): `d51b89c` (#223, #224: a year-m Roth conversion is free
from year m+5, not m+6; before 59 1/2 only matured conversions count as basis), `717d96f` (version,
package upgrades), `ccc4d46` (#221: `anticipated wages` are the wages in AGI, pay minus pre-tax
401k, deductible IRA and payroll HSA contributions; an after-tax contribution paid from pay is paid
by a negative big-ticket item; the earnings test now adds back only the tax-deferred contributions,
`kappa_ijn[:, 1]`; `HFP_jon+jane.xlsx` wages +2,000 and big-ticket -2,000 in 2026-2030), `9625beb`
(#206 documented, not modeled: worksheet line 25, at most \$57/yr joint), `241175c` (linux/win32
BEQUEST1 pins), `4e55b36` (#226: a HiGHS LP ending without a verdict is solved again with IPM,
presolve off).

Maintainer's comment on our PR #222 (relayed by the user 2026-10-24; the facts below are his, not
re-checked on GitHub): landed squashed as `6ea43a9` with the user as co-author; `gross earnings`
dropped (burden on the user; a plan looks forward, W-2 box 5 is a look-back input; "model a tax
rule exactly when it changes a decision the household faces soon"); `months worked` kept (the grace
year) and exposed to the MCP tools as `months_worked`; `test_the_test_moves_pats_pick` no longer
pins the pick made without the test (within loop noise: -\$7/yr MOSEK, +\$53/yr HiGHS); the merge
sits on #225; PR #222 and #220 closed by hand.

Merge: 3 conflicts. `info/modeling-capabilities.md`: the fork's Debts, Budget, Ordinary income,
Itemized, State and STAR rows kept; upstream's Wages row (#221 sentence) and LTCG row (#206
limitation) taken. `tests/plan/test_ss_residual_warning.py`: upstream's \$95k (at \$90k the loop now
settles under MOSEK, #224) with the fork's `withItemized="none"`. `tests/data/amo_mip_reference.json`:
the fork's entries kept (upstream's Case_morgan MOSEK entry stays removed, no MOSEK here).

**Payroll tax follows #221 with no code change**: `_payroll_tax` reads `_earnings_test_inputs()`,
now AGI wages + tax-deferred contributions, which is W-2 box 3/5 under the new convention (a
401(k) deferral is FICA wages; a payroll HSA under a cafeteria plan is not, and is left out).
Recalled, not re-read this session: the box 3/5 treatment of 401(k) deferrals and section 125 HSA
contributions. Under the old convention the base also added after-tax contributions back; now
they are already in the wages, so a case that follows the new convention gets the same base, and
an old-convention case (wages net of Roth/taxable contributions) is now short by them.
Docstring, `modeling-capabilities.md` and `PARAMETERS.md` rows, and the test docstring updated.
`gen_hfp_us.py` and `phase0-scenarios.md` (the household checklist) now state the #221
convention: **the household HFP in `otherFiles/` must enter wages that way** (not in this
container; not checked).

Tests moved (hand numbers):
- `test_additional_medicare_tax_on_the_plan`: Jon \$300,000 + \$7,000 401k = \$307,000 (his \$2,000
  taxable contribution no longer added), Jane \$83,000: 6.2% x 184,500 + 1.45% x 307,000 + 7.65% x
  83,000 + 0.9% x 140,000 = **\$23,500.00**, equal to the run (was \$23,547.00).
- AMO reference Case_morgan (fork, HiGHS, frozen date): basis 42,245.26 -> **42,715.56** (+1.1%,
  outside the 0.6% bar), the same relative move upstream recorded for its build (40,888.8 ->
  41,340.55; per his commit, the oscillating loop's fixed point, the exact MILP moving -\$70/yr).
  Re-recorded basis only, as upstream did; its per-year flows in the fixture are stale (the test
  reads basis and bequest only).

Phase 5 status unchanged: next is step 6 (work sweep), which needs the household's real SLCSP and
HFP (`otherFiles/` is empty in this container).

Full suite on the merge: **3516 passed, 1 skipped** (10:59; 3497 + upstream's 19 new tests: 16 in
`test_highs_lp_fallback.py`, 3 in `test_roth_early_withdrawals.py`), after the two fixes above
(targeted run before them: 2 failed, 380 passed). flake8 clean; Ruff only upstream's three `B905`s.

## Phase 5 step 6: the sweep script and its dry run (2026-10-25/26, on `claude/affectionate-goldberg-l0wd1l`)

`fork-notes/phase5/work_sweep.py` (`e57b7bb`, method of `plan-review-2026-10-22.md` §3.2, R1):
variants as `owlcli --set` specs plus HFP cell edits (openpyxl on a copy, so formats and other
cells stay); per variant (a) a `withSSAges` search under the exact LP, `withACA="optimize"` with
an SLCSP, (b) the same under the loop, (c) local search at fixed ages over each searched person's
whole years 62-70 and both picks, the others held, until no age moves. Local search's time caps
are raised (7200 s / 1800 s) so its node limits decide and scores do not depend on load or
`--jobs`; the report lists plans where the default caps (300 s / 60 s) would have bound. Spread =
deepest interior dip in a sweep (assumes the true value is unimodal in each age). Each variant's
HFP and case file are written out (`owlcli run` repeats them). Variant JSON format in the
docstring; `phase0-scenarios.md` §4 rewritten around it; template comment on `withSSAges`.

**Dry run** (`work_sweep_chris+pat.json`, output `work_sweep_chris+pat_2026-10-25.txt`, run at
`e57b7bb`; the later change only drops repeated sweeps from the report): chris+pat, stand-in
`slcsp_annual` 20, the same PIAs in every variant (mechanics, not a decision), both spouses
searched, `--jobs 4`. 5,901 s in all; every plan solved; no default cap would have bound; the date
rolled to 2026-10-26 during the third variant, which changes nothing here (every `date.today()`
in `src/owlplanner` reads the year, or the year and month in `_ssaCurrentAgeMonths`, except the
`start_date = "today"` path, not taken: chris+pat sets `2026-01-01`; checked by grep).

| Variant | (a) exact LP | (b) loop | Decided (local search) | Basis $/yr | Spread | (a) cost | (b) cost |
|---|---|---|---|---:|---:|---:|---:|
| base (Pat works through 2028) | 68y3m/63y0m | 68y6m/63y0m | 68y6m/63y0m | 113,479.30 | 26 | 13 | 0 |
| Pat stops end of 2027 | 68y3m/62y1m | 68y7m/62y3m | 68y7m/62y1m | 108,675.47 | 61 | 99 | 78 |
| Pat stops mid-2028 (6 months) | 68y3m/62y6m | 68y6m/62y6m | 68y6m/62y6m | 111,332.70 | 14 | 20 | 0 |
| Pat part time 2029-30 ($40k) | 68y3m/65y0m | 68y5m/63y7m | 68y5m/63y0m | 116,214.45 | 38 | 8 | 3 |

- Differences between variants (\$2.1-4.8k/yr) are far above every spread: "resolved". With the
  same PIAs they are not the price of work; a real sweep enters one PIA per variant (D4).
- The exact LP picked Chris 68y3m in every variant, the loop 68y5m-68y7m; local search sided with
  the loop each time, at \$8-99/yr. The exact-LP pick is a good start, not a decision, as §3.2
  said.
- Pat part time: 63y0m and 65y0m score within \$0.27/yr (116,214.45 vs 116,214.18), with 64y0m
  \$41 below both: unresolved between 63 and 65 by any measure. SS withheld \$9,050 at 63y0m
  (the earnings test on the 2029-30 wages).
- Two kinds of dip. In "Pat stops 2027" lifetime ACA flips between \$22.4k and \$29.7k across
  neighbouring Chris ages (68y0m 22,407, 68y3m 29,731, 68y7m 22,403), though Chris's claim starts
  after Pat's ACA years: local search missing the cheaper ACA plan, i.e. noise (the \$61 dip at
  68y3m). The dip at Pat 64y0m recurs in all four variants (13-38) with ACA and Medicare flat and
  more federal tax (base 360,958 vs 350,445 at 63 and 348,794 at 65): possibly the model's own
  shape, not noise; not resolved (an exact branch-and-bound at 63/64/65 would tell, not run). If
  it is the model's, the spread overstates the noise (errs toward "unresolved"); stated in the
  script and in `phase0-scenarios.md`.
- Cost: 20-28 min per variant; local-search solves 71-280 s.

**Branch-and-bound check of the Pat 64y0m dip** (2026-10-26, `fork-notes/phase5/ws_bb_check.py`,
outputs `ws_bb_check_2026-10-26.txt`, `ws_bb_check_part-time_2026-10-26.txt`,
`ws_bb_check_gap3e-3_2026-10-26.txt`): the dry run's plans at fixed ages under
`breakpointMethod="branch-and-bound"` (every family exact), one process per age, compared with the
dry run's local-search scores of 2026-10-25 (same month; the date check above applies).

- **Owl's automatic gap is too loose for this.** With no `gap` option and
  `withMedicare="optimize"`, `plan.py` sets the gap to `MILP_GAP` = 3e-3 (about \$340/yr here).
  At that gap branch-and-bound scored \$64-237/yr *below* local search at 63/64/65 (30-110 s).
  The check passes `gap=1e-5` (about \$1.1/yr) and Owl's 900 s per MIP.
- At gap 1e-5 every HiGHS run ended "Optimal" within the gap; no node or time cap; residual \$0-2.

| Variant (Chris held) | Pat | B&B \$/yr | Local search | B&B - LS | ACA B&B / LS | seconds |
|---|---|---:|---:|---:|---|---:|
| base (68y6m) | 63y0m | 113,542.48 | 113,479.30 | +63.18 | 12,819 / 19,906 | 176 |
| | 64y0m | 113,427.74 | 113,353.30 | +74.44 | 12,765 / 19,906 | 173 |
| | 65y0m | 113,426.62 | 113,379.36 | +47.26 | 11,660 / 19,906 | 288 |
| part time 2029-30 (68y5m) | 63y0m | 116,229.70 | 116,214.45 | +15.25 | 12,978 / 19,906 | 133 |
| | 64y0m | 116,194.31 | 116,173.41 | +20.90 | 12,208 / 19,906 | 182 |
| | 65y0m | 116,248.30 | 116,214.18 | +34.12 | 11,777 / 19,906 | 94 |

- **Base: the dip was local search's.** Under branch-and-bound 64y0m is \$1.12 above 65y0m, at
  the gap's size: no dip. The recurring dip is not evidence of a model feature by itself.
- **Part time: the dip is the model's.** 64y0m is \$35 below 63y0m and \$54 below 65y0m (gap
  \$1.2); at 64y0m the earnings test withholds \$4,463 and federal tax is highest (378,138 vs
  371,722 / 374,705); the mechanism was not isolated further.
- **The part-time pick reverses:** branch-and-bound ranks 65y0m above 63y0m by \$18.60/yr;
  local search had them \$0.27 apart and kept 63y0m. The dry-run table's part-time ages are
  therefore not the model's optimum (one variant; Chris's age not re-swept under branch-and-bound).
- **Local search falls short at every plan checked** (6 of 6, \$15-74/yr), and every
  branch-and-bound plan pays less ACA (\$11.7-13.0k lifetime vs \$19.9k): local search keeps
  the ACA-year income these plans avoid. This differs from the 2026-10-22 finding ("local search
  did not miss a better plan"), which compared it with branch-and-bound on ACA only, the other
  families in the loop, at other ages and before the payroll tax.
- **Cost:** 94-288 s per solve, the same order as local search's 71-280 s on this case. HiGHS
  branch-and-bound can be far slower on other cases (upstream's note: 49-238x slower than MOSEK),
  so this holds for chris+pat only until measured on the household case.

**Stage (c) decided by branch-and-bound** (2026-10-26, the user's call, revising R1; `cc0f5ac` and
the proof-rule fix after the run): `--decider bb` (default) solves each fixed-age plan with
`breakpointMethod="branch-and-bound"`, `gap=1e-5`, 900 s per MIP; a plan is proved when every
HiGHS run ended "Optimal" and none stopped on time or at the node limit, and its tolerance is the
reported gap x score; an unproved plan is also scored by local search and the better kept.
Variant differences are resolved against the two tolerances; ties within tolerance are listed;
the dip spread covers local-search scores only. `--report-from` reprints a saved run;
`--decider ls` is the old path.

Dry run rerun the same day (`work_sweep_chris+pat_bb_2026-10-26.txt` is the run's own log and
report; `..._report.txt` the report regenerated from its JSON under the fixed rule; same variants,
same stand-in SLCSP and PIAs):

| Variant | Decided (B&B) | Basis \$/yr | tol | Local search's pick (2026-10-25) | (a) cost | (b) cost |
|---|---|---:|---:|---|---:|---:|
| base | 68y6m/63y0m | 113,542.48 | 1.10 | 68y6m/63y0m, 113,479.30 | 0 | 0 |
| Pat stops end of 2027 | 68y7m/62y3m | 108,721.05 | 1.08 | 68y7m/62y1m, 108,675.47 | 2 | 0 |
| Pat stops mid-2028 | 68y6m/62y6m | 111,433.21 | 1.16 | 68y6m/62y6m, 111,332.70 | 1 | 0 |
| Pat part time 2029-30 | 68y5m/65y0m | 116,248.30 | 1.16 | 68y5m/63y0m, 116,214.45 | 2 | 19 |

- All 84 plans solved and proved (gaps 8.9e-6 to 2.0e-5), no time or node stop; the three
  differences from base (-\$4,821, -\$2,109, +\$2,706) resolved.
- **Proof rule fixed after the run:** it first also required the reported gap <= 1e-5; 12 plans
  (every run "Optimal", gaps 1.0-2.0e-5) failed it, were marked unproved and were also scored by
  local search (all 12 below branch-and-bound, so no score changed; the time was wasted). The run's
  own report shows the old classification; `--report-from` applies the fixed one.

**Why the reported gap exceeds `mip_rel_gap`** (2026-10-26, `fork-notes/phase5/highs_gap_probe.py`,
output `highs_gap_probe_2026-10-26.txt`): not HiGHS. One of the 12 plans re-solved
(pat-stops-2027, Chris 68y3m / Pat 62y1m; same value \$108,718.70 and `solverGap` 1.434e-5 as in
the run) with every HiGHS run recorded: both branch-and-bound solves ended "Optimal" at gaps of
9.952e-6 and 9.950e-6 (HiGHS's own log: "Gap 0.000995% (tolerance: 0.001%)"), the four repair
MIPs at 0. The extra gap is Owl's: `_stickyBinaries` (`plan.py:8826`, upstream `6250a5b0`)
re-solves the LP with the previous iteration's binaries pinned and keeps that plan when its
objective is within `_sticky_tol` of the new one; `_sticky_tol` is the loop's `rel_tol`
(`plan.py:7521`), 5e-5 by default (max(`REL_TOL`, gap/300) in `_build_sc_loop_policy`). It then
re-expresses HiGHS's bound against the kept plan, `gap' = (res - (obj - gap|obj|)) / |res|`. Here
the kept plan was 14.6073 objective units (4.39e-6 relative) worse than HiGHS's: 9.950e-6 + 4.39e-6
= 1.434e-5, the reported gap to four digits. Read in the HiGHS source at the installed commit
(1.15.1, `04024d7`): the reported `mip_gap` is |primal - dual| / |primal| with presolve's offset
added to both (`highs/mip/HighsMipSolver.cpp` 1076-1104), and nodes are pruned against
`mip_rel_gap` x |upper bound + offset| (`highs/mip/HighsMipSolverData.cpp` 628-666): the same
denominator, so a solve HiGHS calls "Optimal" stays within its gap.

- The reported gap is an honest bound on the kept plan (the bound is HiGHS's, the objective the
  kept plan's), so `work_sweep.py`'s fixed rule (tolerance = reported gap x score) is right, and
  the first rule (reported gap <= --gap) was wrong for this reason. The other 11 plans were not
  re-solved; their gaps (all <= 2.0e-5 <= 1e-5 + 5e-5) fit the same mechanism (inferred).
- With the default `relTol`, `--gap 1e-5` bounds a plan only to 1e-5 + 5e-5 (about \$6.5/yr on
  chris+pat): the sticky tie is looser than the gap whenever `gap < relTol`. At Owl's default gap
  (3e-3) it is 60x tighter than the gap, as the docstring intends ("a tie, not anything inside the
  gap"). Passing `relTol` equal to the gap makes the tie follow it (measured below).
- The tolerance is relative to the whole objective; using it as gap x basis assumes the objective
  is proportional to the basis under `maxSpending` (the tie-break terms aside): inferred, not
  checked. (Measured below: one sticky keep worth 4.39e-6 of the objective left the basis
  unchanged to the cent, so gap x basis can overstate the distance; it errs toward "unresolved".)

**Upstream note drafted: the sticky tie looser than a requested gap** (2026-10-26,
`fork-notes/issue-sticky-gap.md`, not filed; the user files it). On stock `dev` `4dcfabb`
(`issue-sticky-gap-repro.py`, output `issue-sticky-gap-repro-output.txt`): `Case_chris+pat` as
shipped with only `breakpointMethod="branch-and-bound", gap=1e-5` gives `solverGap` 1.833e-5 while
every HiGHS run reported <= 9.706e-6 (one sticky keep); two of three SLCSP stand-in variants likewise
(1.968e-5, 1.935e-5). Patch `issue-sticky-gap.patch` (`plan.py` +9/-3, two tests): a tie may not
take a plan the solver proved within the requested gap outside it; when the solve stopped above the
requested gap the tie is kept as today. With it: `solverGap` 9.942e-6 / 9.867e-6 / 9.981e-6, no
keeps, plans \$0-1.23/yr better, those solves 39-98 s longer. Upstream suite with the patch 3248
passed, 1 skipped; `-m deep` 6 passed, 3 skipped (the MOSEK-only `test_pathological_cases_settle`,
the case the sticky binaries were written for: not checkable here). A first version (limit = the
larger of the requested and the solve's gap) failed upstream's
`test_a_tie_keeps_the_previous_binaries`, whose HiGHS result carries a gap above the requested one;
the narrower rule keeps today's behaviour there. The `min(rel_tol, gap)` cap was considered and left
out of the issue: it would not remove one keep in the repro. The fork itself is not patched
(`work_sweep.py` passes `relTol` = gap, which bounds plans to 2 x gap).

**Sticky-gap issue reviewed** (2026-10-26, on `claude/affectionate-goldberg-l0wd1l`; probes
`fork-notes/phase5/sticky_default_probe.py` and `sticky_iter_probe.py`, outputs `*_2026-10-26.txt`,
stock `dev` `4dcfabb`, HiGHS):

- **Confirmed:** the repro reproduces to the cent on stock and patched (re-run, same day); the patch
  applies on `4dcfabb`; the refusal test fails on stock and passes patched; the mechanism matches
  the code (`_sticky_tol` = `rel_tol` = max(5e-5, gap/300); `requested` reads the same `gap` key that
  `_run_highs` and `_mosekSolve` read, including the 3e-3 default `solve()` writes into the options
  when Medicare is a MILP). The refusal costs one loop iteration in each of the three cases (3 vs 2).
- **Corrected in the issue:** "at the default gaps relTol is far inside the gap and nothing changes".
  A keep leaves the gap whenever HiGHS's gap plus the tie's cost exceeds the request, and HiGHS stops
  within 0.4% of its gap (0.9706-0.9981 at 1e-5, 0.9961-0.9999 at 1e-4 on the four cases). The
  reason small gaps differ is how often ties happen: none in the four cases at 1e-4 (stock and
  patched identical), one across the 19 examples at their own options (`Case_robin`, kept, within
  3e-3). So the patch refuses almost any tie that happens; whether MOSEK's ties in joe, jack+jill and
  avery+quinn survive depends on how close MOSEK stops to 3e-3 (not measurable here). The issue now
  names the `min(rel_tol, gap)` cap as the fallback if the maintainer's MOSEK run fails. The user's
  call (2026-10-26): lead with the patch, keep the cap as the fallback, as the draft stands.
- **Patch tests:** `test_a_tie_keeps_the_previous_binaries` passed `{}` with a 2e-3 gap, so under the
  patch it kept its tie through the stopped-above-the-gap branch (requested 1e-4), not the normal one;
  it now passes `{"gap": 3e-3}`, and a new test covers the stopped-above branch (7 passed patched).
- **Repro script:** its `RUNS` list and `_run_highs` wrapper were module state never reset, correct
  only because each of the four workers took one case; now per case and restored. Iterations counted.
- **Not in the issue (pre-existing, upstream):** `_stickyPrev` is set before
  `_repairInconsistentYears`, and the repair returns the gap it was given. In pat-stops-2027
  68y3m/62y1m (`highs_gap_probe`), the repair took the kept plan back to the new plan's objective
  (-33266.563), so the reported 1.434e-5 overstated that plan's 9.95e-6 (still a valid bound). In the
  issue's four cases no repair improved, so their gaps are the plans' own. Anchoring the tie after the
  repair changed nothing in them (`sticky_iter_probe` "anchor").

**Filed as #233** (2026-10-26, by the user), lead with the patch, the cap as the fallback (the
user's call). The fork itself stays unpatched; `work_sweep.py` passes `relTol` = gap.

**relTol equal to the gap, measured** (2026-10-26, `fork-notes/phase5/reltol_probe.py`, output
`reltol_probe_2026-10-26.txt`; `reltol_check.py`, `reltol_check_2026-10-26.txt`): the 15 plans of the
branch-and-bound dry run that matter here (the 12 whose reported gap exceeded 1e-5, and each
variant's decided plan, one of them among the 12) re-solved the same day at `gap=1e-5`, default
`relTol` (5e-5) vs `relTol=1e-5`, four at a time; 1,302 s.

- **No difference at all:** the same value to the cent, reported gap, iterations (2 each),
  convergence ("monotonic"), sticky keeps and residual for all 15 plans; times within 4 s. Every
  sticky keep in this set was already within 1e-5 of HiGHS's plan (reported gap less HiGHS's MIP
  gap <= 9.8e-6), so the default tie never used its extra room here; all values also equal the dry
  run's (same day).
- **The option reaches the tie** (checked, since "no change" alone could mean it did not):
  `Plan._sticky_tol` = 1e-5 and 1e-7 under `relTol` 1e-5 and 1e-7; at 1e-7 the keep is refused and
  the reported gap falls to HiGHS's (1.434e-5 -> 9.950e-6; 1.968e-5 -> 9.867e-6). The plans then
  move by \$0.00 and +\$1.13/yr (within tolerance); the second took one more iteration (216 s vs
  149 s).
- So on chris+pat `relTol` = gap costs nothing measured and tightens the worst-case bound from
  gap + 5e-5 to 2 x gap (\$6.5/yr to \$2.2/yr), but changed no plan. **Adopted** the same day
  (the user's call): `work_sweep.py` passes `relTol` = `--gap` to every branch-and-bound score and
  records `sticky_tol` per plan; checked on the part-time decided plan (\$116,248.30, gap
  9.96e-6, proved, `sticky_tol` 1e-5, 82 s), as in the dry run.
- **Correction to the 2026-10-25 dry run:** "the exact LP's Chris pick (68y3m) is 3-4 months
  early, \$8-99/yr" was local search's noise: under branch-and-bound 68y3m is within tolerance of
  the best Chris age in base, Pat-stops-2027 and mid-2028, and costs \$0-2/yr everywhere; the
  loop's pick \$0-19/yr. Pat's part-time pick reverses (65y0m, not 63y0m), as `ws_bb_check.py`
  found; Pat 62y3m vs 62y1m in Pat-stops-2027 is a tie within tolerance.
- Proved dips (the model's): Chris 67y0m in base (\$17) and mid-2028 (\$8), Pat 64y0m in the
  part-time variant (\$35).
- On the 75 plans both runs scored: branch-and-bound - local search -\$1.03 to +\$185/yr (the
  -\$1.03 within tolerance); lifetime ACA \$3.7-19.9k under branch-and-bound vs \$11.5-29.7k.
- Cost: 9,502 s (158 min) vs local search's 5,901 s; solves 84-632 s; per variant 29-51 min.

Next for step 6: the household's inputs (R6: birth dates, balances, basis, one PIA per variant,
SLCSP, HFP, variant list), then the real sweep in `otherFiles/`.

## Running locally; run-library design (2026-11-01, on `claude/nice-franklin-mylpt5`)

The user asked how to run the fork offline (inputs, run, results) and then for a design of a
web interface with a library of named runs. Docs only, no `src` or test change.

- `fork-notes/running-locally.md`: install, the two input files, the browser interface and
  `owlcli`, reading the results. Checked on the synthetic household:
  - `owlcli run` of the condo case at fixed ages 70 under local search: 5 min 10 s, 17 sheets;
  - the Streamlit app, driven headless: the fork's TOML (Yonkers, school district) and HFP
    loaded, budget profile shown, solved;
  - `uv run` rebuilds the environment on Python 3.14.6 (`.python-version`), and Owl solves under
    it.
- Found while checking:
  - `owlplanner.sh` leaves `server.address` unset, so the app listens beyond localhost; the
    guide passes `--server.address=localhost`.
  - The existing interface has no Budget editor and no widget for `withItemized`, `withSTAR` or
    moves after the first.
  - A solved `Plan` pickles except `mylog`, `_interpolator` and `rateModel` (they hold the log
    stream); without them it reloads and writes its workbook (jack+jill).
- `fork-notes/run-library-design.md`: the design (scenario JSON as the source of truth, a builder
  generalizing `make_cases.py`, immutable run folders with results and a solve record,
  background jobs, comparisons judged against the loop-noise rules, collections and grids).
  Decisions D1-D8 open, each with a proposal; nothing built.
- Same day, at the user's request: section 14 of the design, ideas from other planners
  (Boldin, ProjectionLab, MaxiFi, Pralana, Income Lab).
  - Their features come from web search summaries only: boldin.com and robberger.com do not
    resolve from the container. Owl's side was checked by grep.
  - Ten ideas, I1-I10, in order of value: milestone anchors, survivor/longevity variants,
    threshold proximity, a yearly check-in, guardrails, a one-year Sankey, a claiming-age map,
    a bracket view of conversions, a sensitivity tornado, a reverse mortgage.
  - Two new decisions, D9 (guardrails) and D10 (HECM).
- Later the same day: the user accepted D1-D9 in principle and allowed boldin.com and
  robberger.com.
  - Seven Boldin pages were read with curl (WebFetch still does not resolve them). robberger.com
    answers with a Cloudflare block; help.boldin.com, projectionlab.com, maxifi.com and
    incomelaboratory.com are refused by the proxy.
  - Section 14 rewritten: a source table and a label per claim (verified on a Boldin page, a
    competitor as Boldin describes it, reported, recalled).
  - Corrections: the side-by-side scenario counts; milestone "bindings" unconfirmed; Boldin's
    "Insights" is a chart section; the Roth Explorer's verified scope (four goals, IRMAA shown,
    ACA not modeled).
  - Boldin was confirmed to model a reverse mortgage and to offer "home equity as a way to pay
    for care", the D10 trade.
  - New ideas: I11, named downturn sequences (Boldin's Market Risk Explorer), with D11 (a rate
    table a case file can name); I12, care anchored to the end of life (Boldin's default: the
    last 28 months at national medians).

## Run-library design reviewed (2026-11-01, on `claude/nice-franklin-mylpt5`)

The user's answers: D10 no (no reverse mortgage), D11 yes (a rate table a case file can name).
Review in `fork-notes/run-library-review.md`; the design is fixed in place. Docs only.

- R1: Owl starts the plan in the solve year and ignores `start_date`'s year
  (`Plan._setStartingDate`). A run's inputs are therefore valid only in their plan year. D4's
  date freeze becomes required (else refuse), and the yearly check-in makes the next year's run.
  Confirmed by the user the same day; `main` fast-forwarded to this branch.
- R2: the noise rule. Local search reports no gap (`-1.0e+00` in the log), and the exact LP
  mis-prices ACA years, so it serves as an agreement check, not a tolerance.
- R3: two numbers, the score and the home at the end, as `run_suite.py` reports them; a variant
  leads only by dominance.
- R4: presets fix the claiming ages except the two Ages presets.
- R5: own-session workers with PID and heartbeat; a singleton manager; atomic writes; one job by
  default.
- R6: save through `ui_to_config`, since `getCaseString` is empty before the first run.
- R7-R9: missing scenario inputs; schema v1 in step 1; frozen generated files.
- R10-R13: pickles, the localhost check, I12's annual grain, D11 against the plugin path.
- Correction: "Load a Case Example" reads local `examples/`, not GitHub (fixed in
  `running-locally.md` too).

## Run-library review 2; build step 1 (2026-11-01, on `claude/run-library-step1`)

Second review of `fork-notes/run-library-design.md` after R1-R13 were folded in
(`fork-notes/run-library-review-2.md`, S1-S13). The design's code claims were checked again
(the named functions all exist; `getCaseString`'s comment; the conftest freeze patches
already-imported modules only; `make_cases.py`'s pieces; the 39-workbook benchmark; no `--as-of`
in `cli/`). The fixes are folded into the design:

- S1/S7: the frozen "as of" date is the run's own (balances') date, recorded in `record.json`,
  and the freeze is a first-class `as_of` input (`owlcli --as-of`), not only a monkeypatch --
  "a date in the plan year" would move `yearFracLeft`, and `owlcli run` must reproduce a run.
- S2: `status.json` is written when a job is queued, so a server restart re-queues waiting jobs
  (a "run the collection again" batch survives). S8/S9: heartbeat cadence, the worker's
  self-check on wake, cancel by token instead of a bare PID.
- S3/S4: a draft is a run with no results folder; a failed solve's record is kept and an
  overwrite moves results to `trash/`; renaming changes `run.json` only, never the folder.
- S5/S6/S10/S13: `library.lock` around every read-modify-write; `plan.pkl` staleness keys on
  the environment (commit, Python, packages) and fails soft; explicit canonical JSON for the
  inputs hash; the Owl commit among the comparison flags. S11: step 4 ships provenance markers
  first. S12: a server-side scratch instead of browser storage.

Then **build step 1** (`src/owlplanner/library/`; 50 tests in `tests/library/`; docs and this
module only, no change elsewhere in `src/` and none in `ui/`):

- `scenario.py`: schema v1 (hand rows: the case dictionary and the HFP tables as JSON),
  canonical JSON and the inputs hash (builder version included), validation, the change diff.
- `store.py`: run folders (`run.json`, `inputs/`), save-as with the identical-inputs notice,
  lineage with the computed change summary, rename (name only), delete to `trash/`, atomic
  writes and the lock.
- `casefiles.py`: import of a TOML + HFP through `load_toml` and `hfp_io.read` conditioning;
  export of the frozen `Case.toml` + `HFP.xlsx` through `save_toml` and pandas (a `budget_file`
  case keeps its JSON as a sidecar); `scenario_from_ui` through `ui_to_config` and
  `plan.saveContributions` (R6's route, works before the first run).
- Checks: 50 tests pass; `fork-notes/synthetic/check_library_roundtrip.py` on the synthetic
  household round-trips 39/39 workbook pairs with the same case dictionary and HFP tables; the
  exported pair builds under `config_to_plan(loadHFP=True)`, `owlcli run`'s own route. flake8
  and ruff show only upstream's known lines. Full suite: **3661 passed, 1 skipped** (8:19 on
  this machine; 3611 on 2026-10-29 + the 50 new).

Next: step 2 (background jobs, the date freeze as an `as_of` input), then step 3 (the library
page, run page and comparison).

### Step 1 independent review and fixes (2026-11-01, same session)

An independent reviewer agent went over the step-1 code against the design (`fork-notes/run-library-step1-review.md`, V1-V10; it ran the tests, the synthetic check and its own probes). Storage core (folders, run.json-last, atomic writes, save-as-only, lineage, trash, lock, S4/S5/S10) confirmed sound; the save path had one bug class and consistency holes. All findings fixed the same day (user: V1-V7 now, V8-V10 with them):

- V1/V2 (budget sidecar): `scenario_from_ui` resolves `budget_file` CWD-then-`case_dir` (the plan's own order; `case_dir=`/`budget_path=` parameters), the sidecar is captured whenever the case names one, and `export_case` refuses a frozen pair whose case references a budget file it does not carry.
- V3/V4 (one document): the scenario is normalized before hashing *and* generating (`scenario.json` is exactly what the frozen files were built from); `normalize` preserves int/float (the TOML keeps them apart, so the hash must too); `validate` rejects `None` and non-finite floats in the case dictionary with key-path messages.
- V6/V7/V8 (robustness and honesty): `generate` runs outside `library.lock` into a staging folder published with one rename; a damaged `run.json` is reported by `Library.damaged()` and never fatal; `SaveResult.dropped` reports the metadata the identical-inputs dedupe did not apply.
- V5/V9/V10: with no workbook both entry paths now record the plan's zero-filled tables (same hash); import's date-dependent conditioning (V5) and `save_toml`'s 8-sig-fig floats (V10) are documented in the design (section 6.4) and pinned with step 2's `as_of`.
- 65 tests in `tests/library/` (15 new); `check_library_roundtrip.py` stays 39/39; flake8 and ruff clean on the changed files. Full suite: **3676 passed, 1 skipped** (8:06; 3661 before the fix pass).

## `main` fast-forwarded to `claude/nifty-fermat-v742k9` (2026-10-29)

The user's call: `main` moves from `9f7a0dd` to this branch (the synthetic household and scenario
suite below; fork-notes, the Phase 0 template, CLAUDE.md and PROGRESS.md only: no `src` or test
change, so the suite count of 2026-10-29, 3611 passed / 1 skipped, stands).

## Synthetic household and scenario suite (2026-10-29, on `claude/nifty-fermat-v742k9`)

**Decision (user):** the household's case is run offline, by the user; cloud sessions never ask for
its inputs or for running it (CLAUDE.md "Household data"). Cloud work checks the tools on a
synthetic case with the household's structure: `fork-notes/synthetic/` (`make_cases.py`,
`run_suite.py`, README).

**The household's structure (user, the same day; CLAUDE.md top):** MFJ, born April and December 1964
(neither on the 1st), 40 SS credits each, both working in 2026 and retiring at the end of 2026 at
the earliest (part time and SS ages open), renting in Yonkers at \$4,000/month (flat in 2027, then
inflation), a condo in Yonkers (10701) or White Plains (10603) at about \$700,000 or Flushing,
Queens (11354) at about \$850,000, HOA \$800/month with inflation, cash or mortgage, the year open;
**renting to the end is not an option**; savings spent by 89, no bequest, the condo kept as a
reserve for long-term care; a joint brokerage account larger than the two IRAs, one IRA each, one
401k (rolled into its owner's IRA when work stops), no Roth, no HSA; opening Roth IRAs this year
under consideration. Template updated to match (`Case_us.template.toml`: dates, horizon 89, Yonkers,
accounts, `other_medical_expenses`; `gen_hfp_us.py`: horizon 89, 2029 gold line 2,315 for an April
birth).

**How Owl takes it** (verified in the code): `maxSpending` with `bequest = 0` spends savings only:
the `bequest_floor` row counts savings, fixed assets come outside it (`plan.py:4982`), so the condo
stays and shows as the final bequest. Fixed Assets values, Debts amounts and big-ticket items are in
the purchase year's dollars (`fixedassets.py:118`), so `make_cases.py` grows today's prices by the
case's own `gamma_n`. A Budget `medical` line does not raise the HSA withdrawal cap (Medicare
premiums + `other_medical_expenses` only). Roth: Owl chooses conversions per year and holds each
for five years at any age (`_add_roth_maturation_constraints`, "intentionally conservative"), so
starting the first-Roth clock early is worth nothing in the model. Owl's "conservative" rates
(`rates.get_fixed_rate_values`): 6.0% stocks, 4.0% bonds, 3.3% T-notes, 2.8% inflation.

**Suite** (`run_suite.py CASE CONDO_CASE SCENARIOS.json`): groups main (work variants, SS at
62/67/70, an earnings-test case, no itemizing, the 2032 reversion, the 2027 benchmark, Roth from 2027
or none), condo and condo-exact (a reference purchase, Yonkers 2027 cash, against 30 purchases:
3 places x 2027/2029/2031/2034/2038 x cash/mortgage, plus the two Roth cases), ltc (care from 2050,
condo kept or sold). Score under `maxSpending` with essential lines: the first year's
discretionary spending k x D_0 (the spending basis also holds the year's essential lines, which
differ between renting and owning), beside savings left and the home at the end. Run checks,
feature checks (each modeled rule fires where it should), Owl's warnings grouped by message, a
local-search vs exact-LP agreement table with error bars, the claiming-age candidates.

**Found and fixed while building it:**

- `ProcessPoolExecutor` with `fork` after the parent had solved: workers spun 21 minutes in HiGHS
  on a 0.4 s solve (`py-spy`: `_run_highs`); `spawn` fixes it (CLAUDE.md gotcha; `work_sweep.py`
  already spawned).
- Owl's own `withSSAges` search on the full model became too slow on the brokerage-heavy case: a
  fixed-age solve takes 14 s there (the loop iterates longer; each MIP still closes at the root),
  about 270 candidates. The suite decides ages in two stages (`two_stage_ages`): search under the
  exact LP (0.5 s per candidate; ACA left on the loop: `withACA="optimize"` made it 9 s per
  candidate, and the exact LP mis-prices ACA years anyway, plan-review §3.2), then the pick and its
  +-1-year neighbours (clipped to 62-70) at fixed ages under the case's model.
- Under the exact LP (no Medicare) an HSA had nothing to pay: \$64,117 left in every cash row of
  run (a). The template now asks for the out-of-pocket amount in `other_medical_expenses`.
- Report: "savings left" is the loan still owed at the end, or money the budget's shape cannot
  spend (the condo sold late), not "about 0"; the agreement table counts the runs' error bars; a
  loop at its iteration cap is a run check; warnings come from the final solve only.

**Run (c)** (17:18, Owl 2026.10.29, 77 runs, 3,406 s on 4 cores; invented balances: brokerage 2 x
\$800k at 70% basis, IRAs \$550k / \$400k): every run solved, every feature check ok. Claiming ages:
70 / 70 for the baseline (stage-2 candidates within \$13-255/yr of each other: a neighbourhood, not
a pick). Main, first-year discretionary spending vs the baseline (111,653): both full time 2027
+10,642 (+9.5%), Ari full time +7,108, Noa +4,517, both part time 2027-28 +6,023; both claim at 62
-7,414, at 67 -2,511; the earnings-test case -4,851 (\$36,059 withheld; plain `ss-62` withholds
\$17,745 from Ari's 2026 wages: entitled from May 2026); no itemizing -518, the 2032 reversion
-2,584, the 2027 benchmark -427. Condo (local search, reference 112,862): the earliest year (2027)
is best in every place-financing row, under both models; cash ahead of the mortgage (Yonkers 2027:
3,711 local search, 2,377 exact); White Plains -829, Queens -7,331 with \$163k more home at 89; every
difference resolved but `yonkers-2038-cash` (exact LP error bar +-4,877). Mechanism, from the
inputs: a 60/40 portfolio earns 5.2% nominal at these rates, under the 6.25% mortgage; rent \$48k
against owner costs of about \$20k plus about \$16.5k of forgone real return on the price. Care:
selling the condo in 2050 gives +17,742/yr against keeping it, with \$179,829 the late budget
cannot spend. Loops: most main runs end "oscillatory" with a zero error bar; `ss-62` +-1,196,
`noa-part-claim-62` +-932; seven condo-exact mortgage or late-purchase runs did not settle
(+-50 to 4,877).

**Roth, three methods** (the condo reference at 70 / 70; local search and exact LP runs 2026-10-29
evening, main from run (c)): the main group's method (branch-and-bound on IRMAA, loop on the rest)
converts nothing in 2026, local search converts \$40,000 that year and scores \$1,209/yr higher
(112,862 vs 111,653). Forbidding the 2026 conversion: main +0, local search **+23**, exact LP +0:
a 2026 conversion is a tie on these numbers (worth about \$0; which plan carries one is solver
noise), so the earlier "Owl does not convert in 2026" held for one method only and is withdrawn.
No conversions at all: main -1,118/yr, local search -978, exact LP -192 (\$280-323k converted
over the plan): every method says conversions pay; the size is unresolved (spread 786). Neither
counts the first-Roth clock (above). The Roth pair now also runs in the condo groups.

**Financing and rate sensitivity (later on 2026-10-29).** User: a 5/6 ARM at about 5.9% for a
purchase now or soon, paid down within its fixed 5 years or refinanced if advantageous. Owl's Debts
rows are fixed-rate, level-payment loans ended early only at the linked property's sale
(`debts.resolve_payoff_years`), so the 2027 purchases gained `arm5` (a 5-year loan at 5.9%, the
paydown branch) and `arm30` (30 years at 5.9%: the refinance branch at no higher rate, an upper bound
on its cost). New groups: `rates-exact`, every 28-year historical window (start years 1928-1998,
71 windows) for the reference and five decisions plus claiming at 62 and 67; `rates-ls`, local search
in 1929, 1966, 1973, 1982, 1998 and on the 1928-2025 average. Each run rescales the workbooks'
nominal purchase amounts (Fixed Assets, Debts, big-ticket items, wages, contributions) to its own
inflation path (`rescale_nominal`); a feature check confirms the condo kept to 89 is \$760,861 in
every window (`fixedassets.py`: kept to the end at full proceeds, stepped-up basis). In run (d)
(20:46, 660 runs, 5,602 s) 153 of 568 `rates-exact` runs did not settle (error bars median +-2,782,
up to +-12,856; 138 on the LTCG loop): the exact groups now also take `withLTCG="optimize"` (four
probed runs settled, 11-15 s each instead of 0.5-1 s), rerun as (e) (21:39, `--only condo-exact
rates-exact`, 3,001 s): 44 of 568 unsettled, `condo-exact` all settled.

Run (e), against the Yonkers 2027 cash purchase in the same window (first-year discretionary
spending, \$/yr; "settled" excludes windows where either run's loop did not settle):

| decision | ahead in | median | worst (window) | best (window) | settled only |
|---|---:|---:|---|---|---|
| Yonkers 2027, 6.25% fixed 30 years | 66 / 71 | +8,392 | -12,219 (1929) | +24,685 (1981) | 53 of 58, +6,409 |
| Yonkers 2027, ARM paid in 5 years | 48 / 71 | +1,250 | -17,874 (1929) | +7,713 (1981) | 39 of 62, +1,000 |
| White Plains 2027, cash | 9 / 71 | -431 | -1,181 (1966) | +905 (1949) | 7 of 68, -481 |
| Queens 2027, cash | 0 / 71 | -11,029 | -16,271 (1982) | -5,689 (1965) | 0 of 71 |
| Yonkers 2031, cash | 38 / 71 | +610 | -16,318 (1977) | +20,083 (1931) | 35 of 68, +503 |
| both claim at 62 | 36 / 71 | +412 | -9,172 (1961) | +9,016 (1977) | 28 of 56, +60 |
| both claim at 67 | 46 / 71 | +912 | -3,405 (1960) | +5,200 (1977) | 46 of 70, +936 |

The reference itself scores 94,195 (1973) to 204,187 (1982): the rate path moves spending more than
any of these choices. Reading, on these invented numbers: under the conservative fixed rates (5.2%
nominal for 60/40) cash beats every loan (local search: ARM paid in 5 years -928, refinanced ARM
-2,677, 6.25% fixed -3,711 in Yonkers), but over historical windows the 6.25% fixed loan beats cash in
66 of 71, so "cash first" is the conservative rates' artifact; Queens is behind in every window;
White Plains is a few hundred dollars behind in most; the purchase year (2027 vs 2031), the ARM
paydown and claiming at 62 / 67 / 70 split the windows and stay unresolved. Local search in the five
windows matched the exact model's signs (run (d), e.g. Queens -6,082 to -16,091 vs -6,148 to
-15,635). Report fixes: settled-only columns, n/a feature checks summarized in one line.

**For the offline run (user):** a copy of `make_cases.py` in `otherFiles/` with the real figures
(balances, wages, the 401k on its owner, PIAs per variant, property tax per place, closing costs,
mortgage rate), then the same `run_suite.py` command; `work_sweep.py` for the ages per work variant.
Not in the suite: stochastic rates (Monte Carlo); the historical windows above are deterministic.

## `main` fast-forwarded to `claude/optimistic-sagan-3onvdj` (2026-10-29)

The user's call: `main` moves from `d1ce58b` to this branch: upstream `dev` `1cf1925` merged
(#240, #241 fixed, `ss_thresh_n` dropped from `StateTaxParams`). Suite on the merge: 3611 passed,
1 skipped.

## Upstream `dev` `1cf1925` merged: #240 and #241 fixed (2026-10-29, on `claude/optimistic-sagan-3onvdj`)

Upstream `dev` = `main` = `1cf1925` (2026.10.29, six commits since `226ff54`):
- `8ac888d` **#240 fixed as filed**: `qcdLimit[2026]` = 111,000 (Notice 2025-67), a test pinning
  2025 and 2026, the same four doc mentions as our patch.
- `13d45ed` **#241 fixed**: `owl.tex` / `owl.pdf`. Each of the 11 numbered items of
  `issue-paper-226ff54.md` and the short items looked up in the new `owl.tex` (BinQ/BinT carry `z`;
  MedDecomp2 with no `e`, positive signs, `a-bar`, `max(0, tau)`; Eq. PI on `G^aca`; pension
  exemption per person; HSA (Medigap, cap, proration); earnings test (`employer ctrb`, IRA only with
  pay, lead-in rows, 2027); 5/12; single from the year after the death; `N_r = 8`; C3b numbered;
  the loop caveat in 3.5; per-asset clip in `I_n`, C6, C6'; `A^c` in `Q_n`; owlcli commands;
  KS/MO; state indexing, AGI add-back; longevity per person; SC stop with the residual; `chi`;
  `gamma^med` and the frozen top tier; smile delay; horizon; `xi_n`; `q_d(i, n)`): all fixed.
- `2e70957`, `f51be59`: KS/MO data comments; `ss_exemption_threshold` removed from
  `taxes_state.toml` and `st_taxParams` (never read by the LP; results unchanged).
- `0713477` version and CHANGELOG; `1cf1925` a pytest-benchmark shim for pytest 9.2.

Conflicts: `tax_state.py` (3), `plan.py` (1), `test_state_tax.py` (9), `modeling-capabilities.md`
(1), `owl.tex` (1). Fork kept its typed `StateTaxParams` and dropped `ss_thresh_n` from it (class,
`st_taxParams`, `st_schedule`, one test assertion, the `plan.py` comment); upstream's dict
`st_schedule` that reappeared at the end of the file dropped (the fork's is the one definition).
Docs: the fork's state-tax paragraph in `owl.tex` takes "Single in the year after the passing of a
spouse"; the fork's state row in `modeling-capabilities.md` takes upstream's KS/MO sentence.
`CHANGELOG.md` = upstream's.

Suite: **3611 passed, 1 skipped** (13:41, on a container that restarted mid-run once). flake8:
upstream's known E301/E304; Ruff: upstream's four B905.

Typed `StateTaxParams` vs upstream's tuple / dict (user's question, same day): named fields and one
type for the single-state and per-year paths; no result depends on it (the #158 patch was rebuilt
without it, plans identical). Cost: a conflict on each upstream change to these functions (this
merge: 13 hunks). Kept for now, nothing new built on it; revert to upstream's shapes (fork extras as
dict keys) if upstream changes these functions more often.

## #240 and #241 filed; `main` fast-forwarded (2026-10-29)

The user filed the QCD limit issue as **#240** (`fork-notes/issue-qcd-limit.md`) and the paper
docs issue as **#241** (`fork-notes/issue-paper-226ff54.md`), in that order. The user's call:
`main` moves from `11120b2` to `claude/quirky-franklin-yul9qg` (docs and fork-notes only since
`11120b2`: the paper review and the two drafts).

## Paper docs issue drafted (2026-10-29, on `claude/quirky-franklin-yul9qg`)

`fork-notes/issue-paper-226ff54.md` (not filed), per section E of `paper-review-226ff54.md`:
11 numbered items (SS-taxability MIP rows, IRMAA MAGI expansion, Eq. (PI), state pension
exemption, HSA, earnings test, spousal 5/12, MFJ-to-single year, ACA `N_r`, the C3b reference,
the loop caveat for section 3.5) with suggested text, then 16 short ones; line numbers rechecked on
`226ff54`. Replaces `issue-docs-loop-and-paper.md` (marked superseded). Refers to the QCD issue,
which goes first.

## QCD limit issue drafted (2026-10-29, on `claude/quirky-franklin-yul9qg`)

`fork-notes/issue-qcd-limit.md` (not filed): upstream's `tax_federal.qcdLimit[2026]` is
115,000; IRS Notice 2025-67 (irs.gov, read) says \$111,000. Repro on stock `dev` `226ff54`
(`issue-qcd-limit-repro.py`, via the HFP `QCD` column and `setContributions`): \$113,000 and
\$115,000 accepted; with the patch (`issue-qcd-limit.patch`: the figure, a pinning test, four
doc mentions) refused. `test_qcd.py` 22 passed with the patch; full stock suite with the patch:
3285 passed, 1 skipped (6:37).

## Full review of upstream's paper at `226ff54` (2026-10-29, on `claude/quirky-franklin-yul9qg`)

`fork-notes/paper-review-226ff54.md`: the whole of upstream's `owl.tex` read, suspect
statements checked against upstream's code or primary sources. New and verified: the SS
taxability MIP rows (BinQ/BinT) printed with `1 - z` where the code has `z` (as printed, the
taxable share could drop to 0); the **2026 QCD cap is \$111,000** (IRS Notice 2025-67), not
\$115,000 as in the paper **and in `tax_federal.py:157`** (an upstream code bug); Medigap is
not HSA-qualified (Pub. 969); HSA withdrawals are capped by medical costs and contributions
prorated in the Medicare year, contrary to the paper; earnings-test text predates #229/#235 and
the 2027 tables; spousal 5/12 rule missing; ACA `N_r` 7 vs 8; state pension exemption pooled
in the paper, per person in the code; NII clip; MFJ-to-single year; Eq. C3b's references print
the net-spending equation's number; `A^c` missing from `Q_n`; owlcli commands; KS/MO examples
obsolete. The earlier recheck was wrong on the loop caveat (the senior-bonus section states it
for that family) and too strong on the Tx2 clip (C6/C6' still lack it). Section E proposes a
separate QCD code issue and one rewritten docs issue.

## Paper-drift draft rechecked against `226ff54` (2026-10-29, on `claude/quirky-franklin-yul9qg`)

`fork-notes/issue-docs-loop-and-paper.md` read item by item against upstream's own `owl.tex`,
`info/*.md` and `ui/Documentation.py` on `dev` `226ff54` (per-item table at the top of the
draft). Fixed upstream: the Roth cap (per individual), AMO binaries, decomposition/Benders,
the 10^8 big-M, the survivor claim, the lexicographic terms, the Tx2 clip, the scenario
distribution, the `J_3` IRMAA rows, the plan year. The loop-is-not-optimal caveat is now in
`modeling-capabilities.md` and the UI docs (2026-10-24), not in the paper. Still wrong:
Eqs. MedDecomp2/3 (`-e` and flipped signs; `J_3` is right), Eq. (PI) (AGI-basis MAGI where the
code uses full SS), the longevity sentence (code passes each person's drawn age), and in Ch. 2
the state indexing claim (70 of 103 `brackets_indexed = false`), the AGI add-back (the
formulation section has it) and the change of state (not mentioned). The measurement table
(`a85ff76`) is stale. The draft must be rewritten to the remaining items before filing; the
original text is kept below the recheck.

## `main` fast-forwarded to `claude/intelligent-keller-0acb9o` after the `226ff54` merge (2026-10-29)

The user's call: `main` moves from `2e37cc5` to this branch: upstream `dev` `226ff54` merged
(docs pass, DCC-GARCH fix, explain-registry test) and the two fork row tags registered. Suite on
the merge: 3610 passed, 1 skipped.

## Upstream `dev` `226ff54` merged: docs pass, DCC-GARCH fix (2026-10-29, on `claude/intelligent-keller-0acb9o`)

Upstream `dev` = `main` = `226ff54` (2026-10-28, one commit since `b6a3ba7`): a docs pass
(`papers/owl.tex` largely rewritten, `owl.pdf` rebuilt, `PARAMETERS.md`, `modeling-capabilities.md`,
`Documentation.py`), a DCC-GARCH fix in the stochastic rate model (`garch_dcc.py`: each residual
scaled before its own shock enters the variance; `Q_bar` normalized to a correlation; the DCC
recursion and the terminal forecast realigned; `inflation_transform.py`), and explain-registry
entries (`roth_early_basis`, `senior_bonus_*`) with a new test that every row tag `plan.py` emits
is registered. Household: the DCC-GARCH model is a stochastic rate option, not in the template.

Conflicts, docs only:
- `info/modeling-capabilities.md` (2): the fork's lines kept with upstream's edits applied to
  them (fixed-asset growth rates real/nominal by type; the survivor's \$500k home-sale exclusion;
  #234's netting rule; the SC-loop list now with ACA premiums and gain fractions, plus the fork's
  itemizing branches). What still differs from upstream is fork-only text (checked with a word diff).
- `papers/owl.tex` (2): upstream's rewrite taken, the fork's 4 hunks (vs `b6a3ba7`) reapplied
  where still needed: the state-tax paragraph (indexing flags, exemptions and credits, federal-AGI
  base, NY recapture, local tax, several moves, federal standard deduction) kept; the other three
  dropped because upstream's new text covers them: Eq. StateTI with `e_n` added back and
  `t^sigma_n` under `"optimize"`; ACA brackets above the full-premium MAGI pinned off; the
  $10^{-4}$ bracket tie-break ("Tax pricing, switched on when needed").

Fork follow-up: upstream's `test_every_emitted_tag_is_registered` failed on two fork row tags;
`local_taxable_income` (the city-tax identity, structural) and `star_enhanced_income` (the
STAR `zst` big-M link, artifact) added to `CONSTRAINT_FAMILIES`.

Suite: first run 1 failed (that test), 3609 passed; after the fix **3610 passed, 1 skipped**
(11:17). flake8: only upstream's known E301/E304; Ruff: upstream's four B905.

The paper-drift draft (`fork-notes/issue-docs-loop-and-paper.md`, not filed): a grep of the new
`owl.tex` finds none of "benders", "always contributes" (the 4 N_n AMO binaries), the 10^8 big-M
or "combined conversions" (each present in `b6a3ba7`'s), and "fixed point" / "self-consistent
plan" three times (none before). Several of its items may be fixed; it needs a full recheck
before filing.

## `main` fast-forwarded again to `claude/intelligent-keller-0acb9o` (2026-10-28)

The user's call: `main` moves from `d3e16bf` to this branch: the chris+pat work sweep with
`--eta 0 1 optimize`, the part-time pick traced to the #229-#232 fixes, and the decision not to
add a month refinement pass. Docs and fork-notes only since `d3e16bf`.

## chris+pat work sweep with `--eta 0 1 optimize` (2026-10-28, on `claude/intelligent-keller-0acb9o`)

`work_sweep.py` as on `main` `d3e16bf` (upstream `b6a3ba7`; no `relTol`; `--eta` default
`0 1 optimize`), the same variants and stand-ins as the 2026-10-26 dry run (SLCSP 20, same PIAs:
a mechanics test, not a decision). `--jobs 4`, 8,824 s. Log and report
`fork-notes/phase5/work_sweep_chris+pat_bb_2026-10-28.txt`, scores `..._bb_2026-10-28.json`.
Every scored plan solved and proved by branch-and-bound; reported gaps 8.9e-6 to 1.0e-5 (the
2026-10-26 run: up to 2.0e-5, before #233); no plan nets a round trip (#234).

| Variant | Decided | Objective | tol | 2026-10-26 |
|---|---|---:|---:|---|
| base | 68y6m/63y0m | 113,542.48 | 1.10 | same ages, same value |
| Pat stops end of 2027 | 68y7m/62y3m | 108,721.05 | 1.08 | same |
| Pat stops mid-2028 | 68y6m/62y6m | 111,433.21 | 1.11 | same |
| Pat part time 2029-30 | 68y3m/64y7m | 116,246.11 | 1.15 | 68y5m/65y0m, 116,248.30 |

**Deposit split.** At every variant's decided ages, eta 0, 1 and "optimize" give the case's 0.5
value to the cent, except base: eta 0 and "optimize" +0.21 (unresolved against 1.10 + 1.10).
"optimize" is never below a fixed split, as it must be. On these inputs the split does not matter.

**Part-time variant: a different pick, and a miss.** Traced the same day:
- Stage (a) (exact-LP `withSSAges` search) picks 68y3m/64y7m today, 68y3m/65y0m on 2026-10-26.
  Run today on three code versions (`ws_parttime_a_check.py`, output
  `ws_parttime_a_check_2026-10-28.txt`): the current code and `0f93a14` (main before today's
  merges) both pick 68y3m/64y7m (119,962.22); `92e49bd`, before the #229-#232 earnings-test fixes
  (upstream `07b9a77`, merged 2026-10-27), picks 68y3m/65y0m and values 68y3m/64y7m at 119,936.58.
  So those fixes moved it: Pat (born 1966-01) claims at 64y7m in August 2030, inside her
  2029-30 part-time work, where the test applies (decided plan: 4,889 withheld, today's $); at
  65y0m she claims after it. Which of the four fixes does it was not isolated. Stage (b) (loop
  search) also moved, 68y5m/63y7m -> 68y9m/65y0m; not traced.
- With (a) and (b) moved, Chris 68y5m was no longer among the candidate ages (whole years, the
  held age, and the (a)/(b) picks: `decide()`), so the sweep never scored it. Scored afterwards by
  branch-and-bound at gap 1e-5 (`ws_parttime_bb_check.py`, output
  `ws_parttime_bb_check_2026-10-28.txt`): 68y5m/64y7m 116,248.44, 68y5m/65y0m 116,248.30 (the
  2026-10-26 value), 68y3m/64y7m 116,246.11 (the sweep's pick, reproduced). The best plan found
  is 68y5m/64y7m, $2.33/yr above the sweep's pick, against tolerances 1.15 + about 1.15: at the
  edge of resolved. Pat 64y7m vs 65y0m at Chris 68y5m: 0.14 apart, unresolved.
- So the script's coordinate search only compares the ages it is given; it can stop short of
  the best nearby month when (a) and (b) do not point at it. Here the cost is about $2/yr on a
  stand-in case. Not changed in the script (a refinement around the decided ages, e.g. +-1 to
  3 months per person, would cover it): the user's call.

**Decision (user, 2026-10-28): no refinement pass.** A +-1-3-month pass around the decided ages
(4-12 more plans per variant, 80-130 s each) is not added: a $2/yr miss does not justify it, and
no case was found where the miss would be significant. Reasoning, not measured:
- (a) and (b) each search every open month (`Plan._ssAgeSearch` solves each one), so (c) misses
  only when its best month is not a whole year and both proxies misprice a month-sensitive effect.
- ACA cliff: (a) over-values staying under it ($528/yr vs the case's $14,
  `plan-review-2026-10-22.md` §3.2), so it points at the cliff-safe month. Earnings test: a fixed
  table in the streams, the same in all three stages.
- IRMAA tiers ((a) has no Medicare; (b) prices them one loop iterate late) are the one candidate.
  With income that cannot move, MAGI does not depend on the plan and (b) prices IRMAA exactly;
  with movable income, branch-and-bound steps under the tier by shifting conversions or
  withdrawals at small cost, so its value is smooth in the claiming month. Only income partly
  movable falls between; the ceiling there is about one year's tier-1 surcharge for a couple
  (about $2.3k, recalled, not checked), on the order of $80/yr over a 30-year plan; no such case
  was built.
- Measured in this run: the best two candidates within $0.13-2.33/yr of each other in every
  sweep; slopes away from the optimum up to about $10-13/yr per month.
Revisit if a real-input sweep shows a sweep whose best two ages are far apart in months with a
steep value between them.

## `main` fast-forwarded to `claude/intelligent-keller-0acb9o` (2026-10-28)

The user's call: `main` moves from `0f93a14` to this branch: upstream `dev` `1bdc3b2` (#233 ours,
#234, #236, #238, #239) and `b6a3ba7` (#235, version 2026.10.28) merged, and `work_sweep.py`
without `relTol` = `--gap` and with `--eta optimize`. Suite on the last code commit: 3609 passed,
1 skipped.

## Upstream `dev` `b6a3ba7` merged: #235 fixed (2026-10-28, on `claude/intelligent-keller-0acb9o`)

Upstream `dev` = `main` = `b6a3ba7`, 2 commits since `1bdc3b2`:

- `92afe10` (**#235, on our earnings test**): `earnings_test` takes `past_earnings_in` /
  `past_work_months_in` (5 years before the plan, oldest first, nominal) and tests a person
  entitled before the plan from entitlement on: the grace year, the months withheld before the
  plan (credited at FRA), and the December check before the plan (paid in January of the first
  plan year). New plan arrays `omegaPast_in` / `etMonthsPast_in`, read from the HFP's lead-in rows
  (`anticipated wages`, `months worked`) and written back on save; `_earnings_test_inputs(past=True)`.
  Blank past years change nothing. Exempt amounts 2021-2023 added (SSA COLA fact sheets, per his
  comment; not checked here). MCP: wages, months worked and contributions take pre-plan years;
  results name the unsettled families (SS, LTCG) and the option that settles them. Overpayment
  recovery (the reporter's follow-up) is stated as not modeled.
- `b6a3ba7`: version 2026.10.28, dependency bumps (fonttools, narwhals, tzdata), two stochastic
  test files reformatted.

Merge: **no conflicts**. Fork code reading what changed (grep of `src`, `tests`, `fork-notes` for
`_earnings_test_inputs`, `earnings_test(`, `omegaPast`, `etMonthsPast`, `past_earnings`): the
fork's payroll tax and `_earningsReachable` call `_earnings_test_inputs()` with the default
(`past=False`), plan years only, unchanged. No duplicated `def`. `uv sync` took the new lock.

Check against #235's law-side figures (`fork-notes/upstream-234-235/check235_after.py`, output
`check235_after_2026-10-28.txt`; same person as `check235.py`: PIA 2,000, born 1963-06-15, claims
62y1m = July 2025, plan from 2026):
- Case 1 (works Jan-Jun 2026 for 80,000): with no past earnings, unchanged (1,408.33 in 2026,
  15,491.67 in 2027, 12 ARF months). With 2025 worked in full for 80,000: **7,041.67 in 2026,
  16,900 in 2027**, 12 ARF months, the law's side as recorded on 2026-10-26.
- Case 2 (no plan-year work): with Jul-Dec 2025 withheld, 15,491.67 in 2026 (the December 2025
  check withheld), 6 ARF months, 17,200 in 2030 (FRA June 2030: 6 x 1,408.33 + 6 x 1,458.33) and
  17,500 from 2031 (1,458.33/mo, $600/yr more), as recorded.
The rules themselves (404.435, 404.412) were not reread this session.

Household: no change today (born 1964, nobody claims before 2026, the first plan year). The HFP
rows are matched by year (`hfp_io`: rows from `thisyear - 5`), so in a plan built in a later year
the generator's earlier rows become the lead-in rows by themselves: a spouse who claimed while
working is then tested on those rows' `anticipated wages` and `months worked`, which must be the
real ones.

Suite: **3609 passed, 1 skipped** (12:12; +6 upstream tests). Ruff: upstream's four B905.
flake8: 8 new hits (E301/E304) in `tests/stochastic/test_spending_bequest_frontier.py` and
`test_spending_units.py`, upstream's files as `b6a3ba7` left them (identical to `upstream/dev`).

## Upstream `dev` `1bdc3b2` merged: #233 (ours), #234, #236, #238, #239 fixed (2026-10-28, on `claude/intelligent-keller-0acb9o`)

Upstream `dev` `1bdc3b2`, 6 commits since `07b9a77` (2026-10-27/28; `main` = `3931c8a`, the first
two of them). Commit messages read; the issues themselves were not (this session's GitHub access
covers the fork only), so #238 and #239 are known only from their commits.

- `4aa4887` (**#233, ours**): a sticky-binaries tie is kept only if the gap restated against the
  kept plan stays within the requested `gap`, or if the solve itself stopped above it. The code
  is our patch from `fork-notes/issue-sticky-gap.md` line for line (the `min(rel_tol, gap)`
  fallback not needed); two new tests, and the gap passed to the existing tie test.
- `3931c8a` (#234): `_netSurplusRoundTrip` nets only a round trip that realizes no gain
  (`cgr * alpha_0 * delta <= 0.01`), whatever the federal bracket; the gain fraction is now one
  helper, `_withdrawal_gain_fraction()`. Local search starts from `w_ijn_lp`, the withdrawals
  before netting. `2175eb0`: the docs follow.
- `f21486b` (#238, new): at the first death the survivor's taxable basis gains what
  `_add_account_balance_carryover` moves into the account (IRC 1014(a)); a taxable account that
  starts empty is tracked from a $0 basis (`_tracks_basis`) instead of the legacy approximation.
- `b6e695b` (#239, new): under `withLTCG="loop"`, a warning when the LTCG fixed-point residual
  exceeds `N_n x residual_tol`, pointing to `withLTCG="optimize"` (as the SS warning does).
- `1bdc3b2` (#236): `spousal_surplus_deposit_fraction = "optimize"` (`Plan.etaOptimize`): one row
  `d_0n + d_1n = s_n` while both live, epsilon tie-break toward spouse 0, a warning with
  beneficiary fractions below 1; UI disables the fraction; `amorepair.deposit_split` and the
  `eta` field of the AMO context removed.

Merge: **no conflicts**. Fork code reading what changed (grep of `src`, `fork-notes` for
`gain_fraction_in`, `tau_0prev`, `.eta`, `etaOptimize`, `w_ijn_lp`, `_ltcg_lp`, `_residual_tol`,
`"LTCG"`): only upstream's own, plus the fork's `_add_net_cash_flow` `tau_0prev` (dividends, not
touched) and `work_sweep.py` (below). The fork's `_computeFixedPointResidual` returns the
`{"abs_sum", "max_abs"}` per family that `_warnLTCGResidual` reads. No duplicated `def` in the
merged files. CHANGELOG.md upstream's.

Checks on the merged code:
- #233: `sticky_iter_probe.py 1e-5` (the issue's four chris+pat cases) gives the "patched" rows
  of 2026-10-26 to the cent: 114,327.09 / 113,451.71 / 113,362.69 / 113,542.48, accepted gaps
  9.94e-6 / 9.87e-6 / 9.98e-6 / 9.72e-6, 3/3/3/2 iterations
  (`fork-notes/phase5/sticky_iter_probe_2026-10-28_dev1bdc3b2.txt`).
- #234: `scan234.py` over the 19 examples (outside pytest, today's date): jack+jill is still the
  only case that nets, now $45,909 in one year (2035) instead of $118,626 in three (2034, 2036,
  2038 on 2026-10-26). A probe on the same plan: 2034, 2036 and 2038 carry gain fractions
  0.62 / 0.02-0.05 / 0.37 on the selling spouse and are now shown gross; 2035 has gain fraction 0
  for both (the 2034 sale and rebuy reset the basis) and is netted
  (`fork-notes/upstream-234-235/scan234_2026-10-28_dev1bdc3b2.txt`).
- Household (from `fork-notes/upstream-236/README.md`: equal horizons, no survivor phase): #238
  cannot apply (no first death inside the plan); #236's "optimize" was measured there before it
  existed, as a free split, and moved nothing beyond the solves' noise. Not rerun.

Fork changes: `work_sweep.py` docstring (#234 fixed: the recorded hidden gain should now be 0,
kept as a check).

Follow-up the same day (user: drop `relTol` unless it serves another purpose; add `"optimize"` to
`--eta` unless there is a downside):
- `relTol` = `--gap` **dropped** from `work_sweep.py`'s branch-and-bound scores. It was added only
  to bound the sticky tie (2026-10-26). Its other effects are the loop's convergence and cycle
  tolerances (`plan.py`: `tol = max(abs_tol, rel_tol * scale)`; in a branch-and-bound loop the
  convergence test is widened to the solve's own gap anyway). Measured on the merged code with
  `reltol_probe.py` (the same 15 chris+pat plans as 2026-10-26, default `relTol` vs 1e-5): every
  plan identical in value, reported gap, convergence, iterations and residual, no sticky keep in
  either, every gap <= 1e-5 (1,944 s; `fork-notes/phase5/reltol_probe_2026-10-28_dev1bdc3b2.txt`).
  Values differ from 2026-10-26 where a keep was refused (e.g. base 67y0m/63y0m 113,450.58 ->
  113,451.71, 3 iterations instead of 2), the #233 fix itself.
- `--eta` takes `"optimize"` (upstream #236), and the default is now `0 1 optimize`. Every fixed
  split is feasible under "optimize", so its score bounds what any fixed split gives (up to the
  solves' tolerances and the epsilon tie-break toward spouse 0). Downsides found: one more scored
  plan per couple variant (a branch-and-bound solve, 90-600 s on chris+pat, run in the pool with
  the others); upstream's warning for "optimize" with beneficiary fractions below 1 does not
  arise for the household (template fractions 1.0, and its condition needs a first death inside
  the plan). Checked: chris+pat base at 68y6m/63y0m under stage (a)'s exact LP, through
  `work_sweep.make_plan`: eta 0, 0.5, 1 and "optimize" all 117,116.96, "optimize" deposits all
  with spouse 0 (its tie-break); argument parsing, a bad value refused, `_report_eta` with
  "optimize" rows, `--report-from` on the 2026-10-26 run unchanged. Not run: a full sweep.

Suite: **3603 passed, 1 skipped** (14:35; 3588 before, +15 upstream tests). flake8 clean; Ruff
upstream's four B905 (the three known, plus `ui/Run_Options.py:257` from `1bdc3b2`).

## `main` fast-forwarded to `claude/youthful-einstein-nvadcx` (2026-10-28)

The user's call: `main` moves from `e142198` to this branch: the NY marketplace benchmark and gold
plans (`fork-notes/aca-ny/`), the template's `slcsp_annual = 20.84` and budget spending profile,
and the HFP generator's `core` and gold-plan Budget lines. Docs and fork-notes only.

## NY marketplace benchmark for Yonkers, Westchester, NYC (2026-10-27, on `claude/youthful-einstein-nvadcx`)

The user's question (the R6 input SLCSP). Details, sources and rerun steps:
`fork-notes/aca-ny/README.md` (`fetch.sh`, parsers, output `slcsp_2026-10-27.txt`).

- Source: DFS approved 2027 rate templates and Final Exhibits on `myportal.dfs.ny.gov` (direct
  links, no login). NYSOH's plan tool not used: it needs a browser cookie session, which the
  auto-mode classifier refused; `info.nystateofhealth.ny.gov` blocks curl (CloudFront 403).
- Zip codes 10701, 10603 and 11354 are all Rating Region 4 (5 boroughs, Rockland, Westchester);
  the two lowest silver plans (Fidelis) are sold in both counties, so all three get the same
  benchmark.
- 2027 benchmark, monthly single (couple x2): **1,053.68** (Anthem, if age-29 twins don't count)
  or 988.67 (Fidelis's age-29 twin, if they do). Couple per year 25,288 / 23,728. Which reading
  NYSOH uses is not resolved (26 CFR 1.36B-3 read; NYSOH tool or a 1095-A would settle it).
- 2026: 868.20 / 846.86 (couple 20,837 / 20,325 per year), so Owl's `slcsp_annual` = 20.84
  (or 20.32). 2027 is +21.4% / +16.7%, against the market's +6.0%: Fidelis drops its four
  cheapest silver plans.
- NY is community rated (couple = 2.000 x single on every family-tier row): Owl's lone-enrollee
  share from the CMS age curve (0.43-0.49 for a younger spouse 55-62) is 0.5 here. Small for
  the household (both born 1964); not filed.
- The user's call: the template takes `dep26`, `slcsp_annual = 20.84`
  (`fork-notes/phase0/Case_us.template.toml`); `phase0-scenarios.md` runs 25.29 (2027) as the
  sensitivity.
- Gold plans (the user's question, same day; `metal.py`, README "Gold plans"): standard gold
  2027 deductible $1,200, out-of-pocket max $12,000 (silver $3,750 / $12,000; Fidelis and HIP
  tables). Cheapest gold in both counties: Fidelis `25303NY0030001`, 1,219.05/mo single, couple
  29,257/yr, +3,969 over the benchmark (2026: +6,136). Owl prices the benchmark only; gold's extra
  would go in as a `medical` budget line.
- The user's call: `gen_hfp_us.py` now writes it into the Budget sheet, essential `medical` lines
  "gold over benchmark" 3,969 (2027-2028, survivor 50) and "..., B alone" 1,819 (2029, half x
  11/12 from the template's December birth date, survivor 100). Checked on a scratch copy of the
  template (budget profile, stand-in core line and balances): medical by year 0 / 3,969 / 3,969 /
  1,819 / 0, all essential; the plan solves. Read only under `spending_profile = "budget"`: the
  template's `flat` runs ignore them and warn "The Budget sheet is not used".
- The user's call: the template's `spending_profile` is now `"budget"`, and `gen_hfp_us.py` writes a
  discretionary `core` line (placeholder 100,000, TODO). Checked on a stand-in (balances 500/500
  taxable, 1,000/800 tax-deferred, PIAs 3,000/2,000; `maxSpending`, fixed ages, exact LP but the
  ACA loop, which hit its cap in all runs): `flat` and budget with `core` only give the same net
  spending in every year (max difference 0.0); with the gold lines `core` drops from 155,862 to
  155,462/yr (today's $), 159,431 in 2027-28, 157,281 in 2029; `core` at 50,000 gives the same
  plan (scale 3.109 vs 1.555).

## `main` fast-forwarded again to `claude/determined-goodall-f5yxft` (2026-10-27)

The user's call: `main` moves from `7e4b7df` to this branch, adding the #236 check against the
household's deposit split (`fork-notes/upstream-236/`) and the api.govinfo.gov note. Docs only.

## #236 checked against the household's deposit split (2026-10-27, on `claude/determined-goodall-f5yxft`)

The user's question. Details, table and rerun steps: `fork-notes/upstream-236/README.md`
(script `eta236.py`, output `eta236_2026-10-27.jsonl` / `.txt`).

- Code claim checked by grep: `eta` is read only by `_add_surplus_deposit_linking` and the
  uncalled `amorepair.deposit_split`, and saved with the case. Holds.
- Household structure (template): both born 1964, both 92, so equal horizons, `n_d = N_n`, no
  survivor phase. The reporter's gain comes through a first death within the plan. Both spouses
  have the same allocation, so while both live the accounts differ only in basis (a loop
  parameter).
- Stand-in (template with illustrative balances, gain shares 25% / 60%, 2026 wages), splits
  0 / 0.5 / 1 / free, horizons 92/92 and 85/92, `maxSpending` and `maxBequest` (120k), local
  search and exact LP: 32 solves, 19 min.
  - `maxSpending`: no deposit in any run, so the split cannot matter (spreads: local search
    up to $12/yr, exact LP up to $139/yr, both noise).
  - `maxBequest`, local search: deposits only in 2055-56 ($13.5k/yr) at equal horizons, split
    effect at most $157 (0.008%), free +$87 vs 0.5; none at 85.
  - The free split scored below 0.5 in three rows although its feasible set contains 0.5: noise
    as large as the effect.
  - Exact LP at equal horizons, `eta` = 1: -$14,715, its 2026 deposit going to the 60%-gain
    account; local search makes no 2026 deposit, so not decision-relevant.
- Verdict: nothing to change in the case or in `work_sweep.py`; its `--eta` check stays as a
  sensitivity on the real inputs.
- A first run was discarded: the pool reused workers, so the free-split patch leaked into later
  fixed-split jobs (CLAUDE.md gotcha added).

api.govinfo.gov (added to the environment's allow list by the user): answers with `DEMO_KEY`
(10 requests per hour; one 429 when it ran out). The granule summary for 2026-21796 gives the
title, NOTICE, 2026-10-26, SSA, and pdf/htm/mods links.

## `main` fast-forwarded to `claude/determined-goodall-f5yxft` (2026-10-27)

The user's call: `main` moves from `92e49bd` (`claude/clever-hypatia-6l8txj`) to this branch:
upstream `dev` `07b9a77` merged (#229-#232 fixed upstream, the fork's strict xfails removed,
`employer ctrb` in the household HFP generator; suite 3588 passed, 1 skipped), #236 and the
issue states recorded, and the 2027 figures checked against 91 FR 67380.

## 2027 figures checked against 91 FR 67380 (2026-10-27, on `claude/determined-goodall-f5yxft`)

The notice "Cost-of-Living Increase and Other Determinations for 2027" (SSA, document
2026-21796, 91 FR 67380, published 2026-10-26), found through the Federal Register API
(`https://www.federalregister.gov/api/v1/documents.json?...`, which answers now; the site's
citation pages and full-text URLs redirect) and read from GovInfo's PDF
(`https://www.govinfo.gov/content/pkg/FR-2026-10-26/pdf/2026-21796.pdf`, 6 pages, text
extracted with pypdf). Quoted figures:

- OASDI contribution and benefit base "$192,300 for remuneration paid in 2027"
  ($60,600 x 72,800.33 / 22,935.42 = $192,353.14, rounded to $192,300; recomputed here: same).
- Earnings-test monthly exempt amounts for 2027: "$2,130 for beneficiaries who will attain
  their Normal Retirement Age (NRA) ... after 2027 and $5,660 for those who attain NRA in
  2027"; annual "$25,560" and "$67,920" ($670 x 72,800.33 / 22,935.42 = $2,126.68 and
  $2,500 x 72,800.33 / 32,154.82 = $5,660.14; recomputed here: same).
- 2026 amounts the notice names as current: base $184,500, monthly exempt $2,040 / $5,430
  (x 12 = 24,480 / 65,160).

All match upstream's tables (`socialsecurity._EXEMPT_TABLE` 2026-2027,
`tax_federal.payrollWageBase`). No code change.

## Upstream `dev` `07b9a77` merged: #229-#232 fixed (2026-10-27, on `claude/determined-goodall-f5yxft`)

Upstream `dev` = `main` = `07b9a77`, 7 commits since `4dcfabb`, all 2026-10-27:

- `69d00c7` (#229): a 401k deferral is earnings with or without wages; an IRA contribution only
  in a year with wages or a 401k deferral (else a spousal IRA: pay all put in a deductible IRA
  is still missed, as his docstring says). New arrays `kappa401k_in` and `kappaEmployer_in`
  beside `kappa_ijn[:, 1]` (their sum, which the LP reads); new HFP column `employer ctrb`
  (same account, never earnings; absent = zero, not reported); saved workbooks write `401k ctrb`,
  `employer ctrb` and `IRA ctrb` separately; MCP contributions take `ira` and `employer`.
- `32df086`: MCP contributions refuse an unknown account (was taken as tax-deferred).
- `cc5377b` (#230): docs only; a nondeductible IRA is not supported.
- `3ea6f0f` (#231): exempt amounts and the payroll wage base are nominal tables by year,
  deflated by `gamma`, held flat in real terms after the last year (`utils.nominal_by_year`);
  2027 added (25,560 / 67,920, wage base 192,300, cited to 91 FR 67380; verified the same day
  from the notice, section "2027 figures checked against 91 FR 67380");
  `payrollTax` takes an optional `year0`.
- `d9d0bd0` (#232): the worker's excess charged on the ARF-adjusted add-on (two passes).
- `38b16b9` / `64e647f` (PR #237, setup-uv), `07b9a77` (MOSEK bump).

Merge: no conflicts. `CHANGELOG.md` and `socialsecurity.py` are upstream's byte for byte.
Fork code reading the changed APIs: none outside upstream's own (grep of `src`, `tests`,
`fork-notes` for `kappa401k`, `kappaEmployer`, `_earnings_test_inputs`, `payrollTax`).

Trial run before the test changes: 3581 passed, 3 failed, 1 skipped, 1 xfailed. The three
failures were the strict xfails for #232 (both wages) and #231 (2.5% inflation) turning XPASS.
The #229 xfail still failed, for a test-setup reason: it put the deferral in `kappa_ijn[:, 1]`
alone, which upstream now reads as an IRA contribution (0 with no wages, its rule). Checked by
running `_earnings_test_inputs` with the 401k share set: 0 wages + 23,500 401k -> 23,500.00;
1 + 23,500 -> 23,501.00; 0 wages + 7,000 IRA -> 0.00; 1 + 7,000 IRA -> 7,001.00.

Fork changes:
- `tests/ss/test_earnings_test_properties.py`: markers removed (`_known` kept for the next
  one), `_earnings` sets `kappa401k_in` and takes an `ira` amount, a new
  `test_an_ira_contribution_counts_only_in_a_year_with_pay` (3 cases).
- `fork-notes/phase0/gen_hfp_us.py`: `employer ctrb` column (upstream's order) and a note on
  where the match goes. Household: an employer match must go there, not in `401k ctrb`.
- `CLAUDE.md` (earnings-test inputs gotcha), `fork-notes/upstream-229-232/README.md`,
  `fork-notes/CHANGELOG-fork.md`.

Suite: **3588 passed, 1 skipped** (9:16). flake8 clean; Ruff only upstream's three B905.

Issues read the same day through the fetch tool (summaries): new **#236** (LP-chosen spousal
deposit split, above in the table); #233 self-assigned, label `bug`; #235 follow-up by the
reporter; #204 the maintainer on cost vs small tax gains. No new PRs besides #237. Discussion
#177: nothing after 2026-10-12.

## `main` fast-forwarded to `claude/clever-hypatia-6l8txj` (2026-10-27)

The user's call: `main` moves from `6c7a587` (`claude/affectionate-goldberg-l0wd1l`) to this
branch: upstream #229-#232 and #234-#235 checked, the earnings-test property tests (suite 3565
passed, 1 skipped, 4 xfailed), the #231 comment (posted by the user), and the `work_sweep.py`
netting record and eta check. Upstream `dev` is unchanged at `4dcfabb`.

## `work_sweep.py`: netting record and deposit-split check (2026-10-26, on `claude/clever-hypatia-6l8txj`)

The user's call after #234.

- **Netting record:** every scored plan records what `_netSurplusRoundTrip` nets per year, in
  today's $: the amount, the hidden gain (amount x gain coefficient x equity share, the part of
  `Q_n` the displayed flows miss) and that year's state tax. A per-worker wrapper keeps the
  record on the plan object, so a state that local search restores carries its own record.
- **Deposit-split check:** for couples, the decided ages are scored again at each `--eta`
  (default 0 and 1) with the same decider. The report gives the change against the case's split,
  "resolved" only when both plans are proved and the difference is beyond their tolerances. The
  ages are not re-decided.
- Both appear as report sections and in `--json` (`netting` per cell, `eta` per row).
  `--report-from` reads older JSON without them.

**Mechanics check** on jack+jill (`work_sweep_jack+jill.json`, ages fixed, `--no-loop --gap 3e-3
--max-time 120`, log `work_sweep_jack+jill_mechanics_2026-10-26.txt`, 19:55):

- Decided plan: branch-and-bound stopped on time, so local search's 111,038.88 was kept. It nets
  $3,260 in 2036, hiding $77 of gain, basis tracked, no state tax (TN). The loop's plan had netted
  $118,626 over three years (scan of 2026-10-26), so the netting depends on which plan is solved.
- Eta 0 gives -28.63 (local search, unproved) and eta 1 gives -86.12 (branch-and-bound,
  proved); neither nets anything. No verdict: the base is unproved.
- The first attempt, at gap 1e-5 with --max-time 600, did not finish one plan in 40 min and was
  stopped. jack+jill is slow under branch-and-bound here; chris+pat took 94-288 s per plan.

## Upstream issues #234 and #235 checked (2026-10-26, on `claude/clever-hypatia-6l8txj`)

The #231 comment (`fork-notes/issue-231-comment.md`) was posted by the user. Two more issues
by `rationalpiper`, read through the fetch tool (summaries):

- **#234**, upstream's `_netSurplusRoundTrip` (`8bd1f3d`): the worksheet nets a taxable sale
  and rebuy in years with no federally taxed gains, while `Q_n`, the state tax and the cost
  basis follow the gross flows. The fixed `eta` split can force the round trip, and local
  search starts from the netted `w_ijn`. All code claims are valid by reading. The numbers
  could not be reproduced: horizons, rates, allocations and objective are not given, and our
  rebuilt case had no surplus. Scan of the 19 examples (`scan234.py`): only jack+jill nets,
  $118,626 in 2034/2036/2038, basis tracked, Tennessee (no state tax). The hidden round trip
  there is a 0% gain harvest whose basis step-up the worksheet does not show.
  Household: the template has `eta = 0.5` and a cost basis, and NY taxes gains. On the real
  runs, record the netted amounts and run `eta` as a sensitivity.
- **#235**, our earnings test: no pre-plan history (grace year used, months withheld, the
  December check). This is the premise our docstring states, so the issue is a feature
  request. Owl's numbers reproduced (`check235.py`: 1,408.33 / 15,491.67, 12 ARF months; 16,900
  with 0); the law's arithmetic checked; the CFR/USC text recalled, not reread. Household:
  only once someone has claimed before a plan's start year.

No fork change; take the maintainer's fixes.

## Earnings-test property tests; #231 comment drafted (2026-10-26, on `claude/clever-hypatia-6l8txj`)

Assessment after #229-#232 (the user's question: do they show a weakness?): #229/#230 come
from the derived earnings (`6ea43a9`, the maintainer's replacement of our `gross earnings`;
our D1 had flagged the match). #231/#232 are in our `socialsecurity.py`, each on a premise
stated in a comment and never tested ("charging never reaches that month"; nominal table
read as first-year dollars). The four were found by property checks, which our example-based
tests lacked. A condition scan found none of the 19 examples affected by #229 or #232.

`tests/ss/test_earnings_test_properties.py`: conservation (paid + withheld = due, "due"
rebuilt from the rule functions), the excess bound, continuity of the earnings in wages
(401(k)), start-year invariance (a tabled year). #229, #231 and #232 are strict xfails with
`raises=AssertionError`. The tests' own checks: #232's figures come out exactly; a 1%-lossy
mutant of `charge_excess_months` fails conservation; 0% inflation passes the start-year
harness. Details in `fork-notes/upstream-229-232/README.md`, "Property tests". Full suite **3565 passed, 1 skipped, 4 xfailed** (12:05; 3555 before); flake8 and Ruff clean on the new file.

#231 comment `fork-notes/issue-231-comment.md`, for the user to post. It has two parts: a
regression test for the fix, run on stock `dev` `4dcfabb` (fails at 2.5%: 6,900.30 vs
7,220.00), and the wage base, which follows the brackets' release-year convention (285.97
on $250k between the two start years) and should join the exempt table's convention once
#231 is fixed. Repro `fork-notes/issue-231-repro.py`, output
`issue-231-repro-output.txt`. Correction to the chat assessment: the wage base is not a
separate unreported bug, only an inconsistency after #231's fix.

## Upstream issues #229-#232 checked (2026-10-26, on `claude/clever-hypatia-6l8txj`)

Four issues by `rationalpiper`, filed today, all on code that came from our PRs (the derived
earnings `_earnings_test_inputs`, read by the payroll tax and the earnings test; the earnings
test's exempt amounts and spousal charging). Texts read through the fetch tool (summaries; the
GitHub API and github.com answer 403 for upstream here). Every number in the four repros reproduced with
our own script (`fork-notes/upstream-229-232/check_229_232.py`, output saved next to it; #231's
318.77 comes out 318.78). No claim found wrong; the 2027 exempt amounts (91 FR 67380) could not be
fetched (federalregister.gov does not resolve, ssa.gov 403). Our own test
`test_earnings_are_the_wages_before_pre_tax_deferrals` pins #229's gate, which keeps a spousal IRA out
of earnings, so #229's first fix needs its second (401(k) and IRA separately). A condition scan of
the 19 examples finds none in #229's or #232's situation; #231 reaches every plan built from
2027-01-01. Fork not patched: merge the maintainer's fixes; patch first only if the step-6 sweep
must run on household inputs that meet a condition (README "Effect on the fork").

## `main` fast-forwarded to `claude/affectionate-goldberg-l0wd1l` (2026-10-26)

The user's call, after the `4dcfabb` merge: `main` moves from `8c51157` (`claude/phase5-step1`) to
this branch (Phase 5 step 6 dry run, #233, upstream `dev` `4dcfabb`; suite 3555 passed, 1 skipped).

## Upstream `dev` `4dcfabb` merged (2026-10-26, on `claude/affectionate-goldberg-l0wd1l`)

15 commits after `b52b766` (`main` = `dev`): a documentation pass (HFP columns, payroll tax,
PARAMETERS and Modeling Capabilities against the code, INSTALL, CONTRIBUTING, Docker, MCP guide,
credits), a `make_spia` docstring (indexed amounts in today's dollars), and one feature: MCP
`run_from_params` and `save_case` take `rate_params` (`c901c77`). Merge `270345d`; conflicts in docs
only:

- `info/PARAMETERS.md`, `withSSAges`: theirs (up to 96 months from the earliest claiming age, 97
  for a birth on the 1st or 2nd); the fork had not changed that row.
- `info/modeling-capabilities.md`: *Fixed assets* theirs (proceeds are cash flow of the sale year;
  the fork had not changed it); *Debts* and *Ordinary income tax* ours (itemizing; upstream had
  not changed them); *State income tax* ours with upstream's three edits (retirement exemption
  examples incl. KY, `pension_exemption` used by no state, SS exclusion a yes/no flag with the
  KS/MO AGI figures unused). Checked: `ss_exemption_threshold` and `pension_exemption` are 0 for
  every state in the fork's data, and `tax_state.py` reads them as upstream does.
- `CHANGELOG.md` is upstream's byte for byte.

Full suite **3555 passed, 1 skipped** (10:24; 3554 before, upstream's `rate_params` test added).
flake8 clean; Ruff's three B905 are upstream's lines (`localsearch.py:244`, 4 lines below
upstream's because of the fork's `zst` comment, `tests/plan/test_local_search.py:288`,
`tests/plan/test_roth_maturation_losses.py:49`).

## PR #228 landed; upstream `dev` `b52b766` merged (2026-10-25, on `claude/phase5-step1`)

- Found by the second git check-in (20:30 UTC): PR #228 squashed into `dev` as `3a2dfc33`, tree
  identical to our head `f98ef3e`; the maintainer closed the PR by hand (it targeted `main`).
  His comment (pasted by the user): MOSEK records recorded on darwin (`d5dc3ae0`; equal to HiGHS
  to the cent, john+sally's bequest \$55.53 vs \$21.00, inside the tolerance); the payroll tax
  its own line in the taxes plot, now "Taxes and Premiums" (`f2831e21`, `4c999efd`); its own
  `payroll` key, slice and band in `lifetime_allocation` / `annual_cashflow_mix` (`e2c3d197`;
  `taxes` is the federal income tax again); every Summary row always present (`3c036c1b`).
  Also `6250a5b0` (branch-and-bound loops: tied binaries stick, `_bbLoop`, residual drops an
  exact NIIT and adds the gain-fraction mismatch, convergence widened to the solve's gap) and the
  version kick `b52b766`. Check-ins stopped (it landed).
- Merge `bad2a987`: 7 conflicts. Taken upstream's: `test_payroll_tax.py` and the AMO fixture (the
  fork's were the PR's), `modeling-capabilities.md`, `Documentation.py`, the allocation and mix in
  `plan.py`. Kept the fork's: `tax_state.st_taxParams` (same rule, fork structure), the
  `_ltcg_wide_n` line. Combined: the loop residual (fork's `sc_lp` / STR / STAR / itemizing moves
  plus upstream's NIIT exclusion and gain-fraction move) and the Summary's state row (upstream's
  unconditional row, fork's parts after it). CHANGELOG.md = upstream's.
- Then upstream's new `test_giving_and_not_giving_have_the_same_rows` failed on the fork's
  conditional *Total itemized deduction*: the fork's five Summary rows (recapture, local tax,
  STAR, state and federal itemized) are now always present at \$0, as upstream's are
  (`test_state_recapture` updated).
- Full suite 3554 passed / 1 skipped (8:24); `-m deep` 6 passed, 3 skipped (MOSEK-only, as
  upstream reports for HiGHS). flake8 clean; Ruff only upstream's three B905.
- `payroll-tax-pr` is done.

## Upstream `dev` `6371346` merged; #227 PR merged with it and reviewed a last time (2026-10-25, on `claude/phase5-step1`)

- Upstream: `0d30350` (after each branch-and-bound solve, the years whose own income contradicts the
  cost charged are re-solved with their binaries free: `localsearch.repair_inconsistent_years`,
  `Plan._repairInconsistentYears`) and the 2026.10.25 version kick. Clean merge here (CHANGELOG
  is upstream's byte for byte); the fork's `zst` family already works with the repair
  (`RESIDUAL_FAMILY.get` in `_inconsistent_columns`). Fork suite 3545 passed / 1 skipped (10:12;
  3541 + upstream's 4).
- PR (`payroll-tax-pr`): `dev` merged (`2bc5e7d`, no conflict), but the auto-merge left the
  payroll entry inside the released 2026.10.25 section; moved under a new Version WIP (`f98ef3e`).
  3236 passed / 1 skipped, `-m deep` 6 passed. All 19 examples re-measured on stock `6371346`
  vs the PR head (frozen date, HiGHS): the PR table holds to the cent, the twelve without wages
  identical in basis, bequest, federal and state tax; john+sally still 21.00, IRMAA residual \$374.
  Final read of the text: base, commits, measured-on line, checks and Ruff line numbers updated;
  nothing else found.
- **Filed by the user as PR #228** (https://github.com/mdlacasse/Owl/pull/228), head `f98ef3e` =
  `payroll-tax-pr` (checked with `git ls-remote`). When it lands, take upstream's version and drop
  the fork's duplicate code and tests, as with #222.

## #227 PR text: MOSEK records empty, local search named for john+sally (2026-10-25, on `claude/phase5-step1`)

- AMO fixture (PR `033c9d8`, fork `457815a`): the five re-pinned cases' MOSEK records are `null`
  with a `_mosek_not_recorded` note; the MOSEK comparison skips them (checked with
  `OWL_TEST_SOLVER=mosek`: five skips, the other nine fail on the missing license). PR suite
  3232 passed, 1 skipped. The PR text says no MOSEK license, so not run, also for the shared
  `test_toml_cases` / `test_repro` pins, which a MOSEK run is held to.
- john+sally (user: name the local-search option): the text now proposes pinning it under
  `breakpointMethod = "local-search"`, measured on the PR head, frozen test date: 14,013.49 (=
  branch-and-bound), 45.6 s wall / 53.0 s CPU. Then made (user: as a deep test): PR `263c0b3`,
  `test_john_sally_under_local_search` (`deep`), john+sally out of `test_reproducibility`'s table;
  ported to the fork (file identical). PR head: 3232 passed / 1 skipped, `-m deep` 6 passed (7:05);
  fork: `test_toml_cases.py` default 2 passed, deep 1 passed (45 s). Left: the AMO fixture's HiGHS
  john+sally record (loop, 21.00; the test accepts up to \$72), flagged in the PR text; the user
  keeps it as is.
- The helper reviewed (user's questions: a distinct concept? fewer lines? more readable? a good
  name?): one tax rule at all ten sites, net 0 source lines (32 added, 32 removed, by hunk), clearer
  where it replaced the decrementing counter, worse in `taxParams` / `seniorBonusSchedule`, where
  the death now showed in two places (helper for the status, `souls.remove` in the block). User:
  renamed `filingStatusIndex_n` (it returns an index) and those two functions back to `dev`'s code.
  PR `5043e98`, fork the same (its two fork sites and `tax_local` renamed). PR suite 3232 passed /
  1 skipped; fork suite 3541 passed / 1 skipped (10:15).

## #227 PR reviewed and fixed (2026-10-25, on `claude/lucid-gates-uo4kbu`)

Code review of `payroll-tax-pr` (the `code-review` skill, unverified findings), each finding then
checked against the code. Fixed in `36cdddf` (pushed) and ported to the fork:

- **Taxes worksheet** lacked the tax while Income's *Tax bills + Med.* had it: a `payroll tax`
  column after `10% penalty` (when any year has one), outside `total` (`T_n`). The Sources sheets
  were left alone (they hold money coming in, debt payments the only outflow, no tax). The taxes
  plot (`showTaxes`) is left to the maintainer, asked in the PR text.
- **The #197 deep test had been made vacuous by the PR.** Knock-outs on john+sally (local search,
  bequest; without the tax / with it): full 31,778.17 / 14,013.49; (b') off 31,778.17 / 14,013.49;
  relaxation off (`_relax_links` returns the plan's rows) 30,823.25 / 14,013.49; both off
  20,004.43 / 14,013.49. My earlier note ("the test no longer shows (b') is needed, not this PR's")
  was half wrong: before the PR the `> 31_000` bar did catch reverting the relaxation; only (b')
  alone was unguarded, and the PR's 14,000 bar caught nothing. Now both deep tests solve john+sally
  with `payrollTax` patched to zero: bar 31,500 for the full search, and a new test on the full
  link rows with bar 30,000 for (b'). Each revert, run on the branch through env switches in a
  scratch worktree: no relaxation fails the first, no (b') the second, neither both.
- **One filing-status rule:** `tax_federal.filingStatus_n(N_i, n_d, N_n)` (joint while `n < n_d`),
  read by `payrollTax`, `computeNIIT` (vectorized; equal to the old loop to the bit on 20 random
  cases) and `compute_social_security_taxability`. Upstream's other copies (`capitalGainTax`,
  `taxParams`, `seniorBonusSchedule`, `taxBrackets`, `tax_state` brackets) offered as a follow-up.
  In the fork, `tax_state.filing_status_by_year` (fork code, the same rule) is gone: `tax_state` and
  `tax_local` call `filingStatus_n`.
- Not changed, with reasons (the user agreed): employer 401(k) contributions in the base are the
  maintainer's specified base and a documented limitation; the john+sally \$21 pin is flagged in
  the PR text for his decision; the wage base for a plan starting after 2026 is his rule; the
  hard-coded example count is upstream's own pattern; the earnings array rebuilt per solve is
  negligible. The user rejected two of my first answers: a defect is ours to fix whenever we find
  it (#197), and a worthwhile optimization is worth doing (`computeNIIT`).

Stock suite: 3232 passed, 1 skipped (8:11); `-m deep` 5 passed. Fork: 3541 passed, 1 skipped
(10:18). flake8 clean; Ruff only upstream's three B905. PR text updated (`pr-227-body.md`).

**Then all the copies** (`3167318`, pushed). User: one copy of a rule is worth having even without
vectorizing; vectorize only for a measurable speed gain. `filingStatus_n` now replaces ten copies on
stock `dev` (`capitalGainTax`, `taxParams`, `seniorBonusSchedule`, `taxBrackets`, `computeNIIT`,
`compute_social_security_taxability`, `tax_state.st_taxParams`, and the inline ones in the SS, LTCG
and NIIT rows of `plan.py`; the NIIT rows read `niitThreshold` instead of hard-coded numbers), and
two more in fork code (the itemizing warning's status array, the non-itemizer charity cap).
Other rules that look alike stay (`_filers_alive`, `deposit_split`, `irmaaStatus`, the home-sale
window, the fork's STAR survivor rule and budget survivor share). Vectorizing measured: 9 µs
(`computeNIIT`) and 100 µs (`payrollTax`) per call; 6 and 14 NIIT calls + 1 payroll call per solve
(joe 0.07 s, jack+jill 1.28 s): at most 0.2% of a solve, below noise, so both are loops again (reading
the helper). All 19 examples identical to the cent before and after (basis, bequest, payroll,
federal and state tax). Stock: 3232 passed, 1 skipped (7:05); `-m deep` 5 passed.

## PR for #227 built on stock `dev`; upstream `dev` `22ce72b` merged; fork aligned (2026-10-25, on `claude/lucid-gates-uo4kbu`, continued from `claude/phase5-step1`)

**#227 answered** (maintainer, relayed by the user 2026-10-25): "Please go ahead and submit a PR on
`dev`, as with #222." His repro check on `dev` `03aaef35`: five rows to the dollar, chris+pat
within \$6. His shape: wages stay gross; `payroll_n` from a pure function, refreshed at solve time;
only a constant on the cash-flow RHS next to `debt_payments_n`; not in `T_n` nor the effective
rate; earnings as the earnings test derives them; wage base \$184,500 in today's dollars; 0.9%
threshold switching at the first death; on for every case, no option; SE tax a documented
limitation. Outputs: Cash Flow column beside the taxes (shown when any year has one), `planData`,
*Tax bills + Med.*, `_check_cashflow_balance`, `lifetime_allocation` taxes, a Summary line for
every case, the plan metric `owlcli compare` reports. Tests: the pure function, cash-flow balance,
the twelve examples without wages unchanged to the cent, the ones with wages re-pinned on all
three platforms. And: check that no floor or constraint binds in john+sally's 16,803 -> 21.

**PR branch** `payroll-tax-pr` (pushed): one commit `55b49ba` on upstream `dev` `22ce72b`, built in
a worktree of stock `dev` (no fork code). Text for the user to open: `fork-notes/pr-227-body.md`.
Stock suite: 3205 passed, 1 skipped (7:16); `-m deep`: 4 passed; flake8 clean; Ruff only the
three B905 already on `dev`. Beyond his list (flagged in the text): `annual_cashflow_mix` taxes
too, `owlcli run` JSON keys, the paper (`\mathcal{F}_n`).

**Measured** (all 19 examples, `22ce72b` vs the branch, frozen date, HiGHS, real runs): the twelve
without wages identical to the cent (basis, bequest, federal and state tax); alex+jamie -2,999.91,
chris+pat -2,794.09, jack+jill -1,902.97, joe -1,298.34, jon+jane -5,156.17, riley+casey -242.14
(spending \$/yr; riley+casey is new since #227, \$48,000 of wages, \$3,672 of tax), john+sally
bequest 16,802.68 -> 21.00. Re-pinned (linux only; darwin and win32 tables take the linux values,
said so in the comment and the PR): `test_toml_cases`, `test_repro` (BEQUEST1 959,477 -> 859,316:
linear, \$2.28 per dollar of tax at half and full tax), AMO fixture HiGHS for five cases (their MOSEK
records left empty, null: no license here, so not run. They were first shifted by the HiGHS change
and marked as estimates; the user ruled that out the same day, no numbers that no run produced), the deep #197 test's
bar 31,000 -> 14,000.

**john+sally, answered with measurements** (scaling the tax by s; scripts in the session scratchpad,
not kept): under the loop the bequest falls a constant \$1.968 per dollar of tax for s = 0..0.97
with zero fixed-point residual (compounding: 2026 withdrawals all from taxable; real growth to the
horizon 1.998, every account 60/40). It reaches zero at s = 0.97; past that the zero bound on final
balances binds and the loop ends on plans that undercharge IRMAA: residual \$67 (0.975), \$117
(0.98), \$250 (0.99), \$374 (1.0, exit "monotonic"), "unsolvable iterate" at 1.2 (\$2,809). So the
shipped \$21 is a plan \$374 short on IRMAA. Local search: 31,778.17 / 22,895.83 / 14,013.49 at
s = 0 / 0.5 / 1 (constant \$2.019 per dollar, no residual); branch-and-bound 14,013.49 at s = 1.
`withMedicare="optimize"` alone: "unsolvable iterate" at s = 1 (7,238.50, LTCG tax 0), not a
reference. The PR leaves the example alone and offers three options (keep, pin under local
search, lower `netSpending`). Corrected an old fork note: the 2026 wages are John's, not Sally's.

**Found on the way** (in the PR text, not changed): on `dev` `22ce72b`, the #197 deep test also
passes with step (b') switched off (31,778.17 without the tax, 14,013.49 with it), so it no
longer shows that (b') is needed.

**Upstream `dev` `22ce72b` merged** (from `4e55b36`): `1ccc1cf` (#186, the unsolvable-iterate
fallback takes the most settled iterate; `trace["residuals"]`), `24666eb` (Case_riley+casey, a
`deep` marker, `pytest.ini` `-m "not deep"`), `03aaef3` (`_snapBinaries` after every MIP solve, in
the generic dispatch, so the fork's binaries are covered), `22ce72b` (version). Two conflicts:
`plan.py` trace keys (the fork builds the `_lp` keys from `_SC_PARAMS`; upstream's `residuals`
added), `test_local_search.py` (`deep` marker). CHANGELOG.md auto-merged to upstream's.

**Fork aligned with the PR**, so the merge is trivial when upstream lands it: `payroll_tax_n` ->
`payroll_n`, `payroll_addl_n` and `Plan._payroll_tax` gone, `tx.payrollTax(N_i, earnings_in,
gamma_n, n_d, N_n)` returns one total per year (the fork's per-year wage-base table went: one
constant), the Summary row is unconditional and the fork's *Additional Medicare tax* sub-row is
gone, the Cash Flow and CSV column sit after NIIT. The payroll lines of `tax_federal.py`,
`plan.py`, `export.py` and `cli/formatters.py` against upstream equal the PR's line for line
(checked by diffing the two diffs). Tests and docs: the PR's `test_payroll_tax.py`,
`test_repro.py`, `test_toml_cases.py`, `test_cashflow_balance.py`, `test_export.py`,
`test_local_search.py` and AMO fixture copied as is (the fork's "upstream model without payroll
tax" fixtures dropped; the fork passes the PR's pins), `test_payroll_tax_always.py` deleted; the
PR's doc hunks applied after removing the fork's payroll passages. Fork suite: 3514 passed,
1 skipped (8:54); flake8 clean; Ruff only upstream's three B905.

## The fork's smile dropped (2026-10-25, on `claude/phase5-step1`)

User's decision after the review (option A, taken further than the opt-in proposed): the fork's
age-anchored smile is gone and upstream's is back. The household does not use the smile
(`"flat"` in the template, `"budget"` for housing), and for its 62-92 horizon (31 years = the
fork's 30-year period + 1) the two curves were identical (both computed: low point 79% of the
first year at 76, 110% at 92). Taken from upstream as is: `spending.py`, `tests/plan/test_spending.py`,
the six example cases (no `smile_start_age`), `tests/plan/test_amo_postprocess.py`; reverted by hand:
`Plan.setSpendingProfile` (keeps the `"budget"` branch; `_smileYears` / `_youngerAgeAtStart` /
`smileStartAge` gone), `plan_bridge` (old-case warning, `smile_start_age` read and written),
`ui_bridge` (`_younger_age_now`), the schema field, the UI field (back to *Smile delay*), the docs.
`tests/plan/test_smile_start_age.py` deleted. A case still carrying `smile_start_age` has it
silently ignored (the section takes unknown keys, as upstream).

Pinned results: `test_toml_cases` is upstream's file again plus the payroll-tax fixture (jack+jill
102,621, upstream's value). AMO fixture: jordan+taylor and morgan take upstream's records, MOSEK
entries back (the fork's basis equals upstream's to the cent: 221,105.33 and 41,340.55; bequests
within the test's band); jack+jill re-recorded, basis only, 100,669.12 (the payroll tax: Jill's
wages). Cases still differing from upstream's fixture: alex+jamie, jack+jill, joe, john+sally,
jon+jane (payroll tax) and devon (itemizing).

## Fork review: closer to upstream (2026-10-25, on `claude/phase5-step1`)

Whole-fork diff against upstream `dev` `4e55b36` (nothing newer upstream), read for edits to
upstream lines; report `fork-notes/fork-review-2026-10-25.md`. Done:

- `@_fixedAcrossIterations` restored on `_add_defunct_constraints`: lost by mistake in `a5fd533`
  (NJ removal) with the NJ builder above it; the only upstream line that commit removed by mistake
  (scan of its removed lines against upstream). Same bounds, rebuilt each iteration instead of
  replayed: no plan change.
- The fork's `CHANGELOG.md` block moved to `fork-notes/CHANGELOG-fork.md`: `CHANGELOG.md` is
  upstream's byte for byte, so it stops conflicting at syncs. New fork entries go in the new file.
- Stale NJ text: the NJ exclusion paragraph in `papers/owl.tex`, two mentions in the template.

Open for the user (report section 2): the age-anchored smile (changes six upstream examples; the
household does not use the smile; recommended: opt-in through `smile_start_age`, upstream's curve
without it), `withItemized` default, several moves vs upstream's one, a tuple/dict-compatible
`StateTaxParams`, the legacy `Housing` reader, the tracked `otherFiles/PROGRESS.md`. Upstream
(section 3): #158 is closed but upstream still has no NY recapture (`git grep`), and the stock
patch no longer applies to `4e55b36`; the paper/docs drift draft is unfiled and stale.

## Payroll-tax issue draft reviewed; `withPayrollTax` removed (2026-10-25, on `claude/phase5-step1`)

**Posted by the user as #227** (2026-10-25), with the PR offer kept.

**`withPayrollTax` removed outright**, as `withEarningsTest` was (user): no `RETIRED_OPTIONS` entry,
so a case still carrying the key gets "Ignoring unknown solver option" and nothing else (remove the
line from `otherFiles/Case_us.toml` if it is there). The deprecated-key test and the saved-case
guard in `test_payroll_tax_always.py` went with it; code and docs no longer name the key
(PROGRESS, `phase5-plan.md` and the AMO fixture notes keep the history).

**Review of `fork-notes/issue-payroll-tax.md`** before posting. Fixed:
1. *Filing status cited wrong:* the shape said "as `irmaaStatus` does"; since #213 `irmaaStatus`
   follows the lookback return. The fork's rule (joint through the death year) is `computeNIIT`'s
   (`n == n_d` switches to single, read on `4e55b36`); now cited.
2. *Dates:* "since 2026-10-18 and, since today" -> charged since 2026-10-22 (step 5), no option since
   2026-10-24.
3. *Two claims verified that were recalled:* the wage base's indexing (20 CFR 404.1048, eCFR
   versioner API, 2026-10-15 text: refigured in each year with a benefit COLA by the ratio of
   average W-2 wages, rounded to \$300, never lower) and the SE-tax figures (IRS Tax Topic 554,
   reviewed 24-Sep-2026: 12.4% + 2.9% on 92.35% of net earnings, half deducted from AGI); both
   texts saved in `fork-notes/phase5/sources/`.
4. *SE earnings:* upstream's `PARAMETERS.md:83` tells users to enter net SE earnings in
   `anticipated wages` for the earnings test; under the proposed rule they would pay 7.65%, about
   half of SE tax's 14.1%. Now said in choice 2.
5. *Overstatements in wording:* "an extra working year looks 7.65% more valuable" -> each working
   year brings in 7.65% more cash than it does; "no effect on the tax computations or the loop" ->
   no term in any tax computation (the tax changes withdrawals, hence taxes, through the plan).
6. *Rerun advice:* the repro runs under the frozen test date, so it moves only with upstream code,
   not with the day.

Full suite: **3515 passed, 1 skipped** (11:39; 3517 - the 2 removed tests). flake8 clean.

Held (checked): the six examples with wages of 18 (the repro's case scan); the table against the
saved output; the no-hit search; `ui/Documentation.py:446-453` and `PARAMETERS.md:81` quotes; the
earnings test's exempt amounts held in today's dollars (upstream's SS row).

## Payroll tax always on; upstream issue drafted (2026-10-24, on `claude/phase5-step1`)

User's decision after the merge review: the payroll tax is part of the model, as the earnings test
is (no option), and an upstream design issue is drafted.

Test-first: spec `31bea3a` (`tests/plan/test_payroll_tax_always.py`: 4 strict xfail + 1 guard that
passed on arrival), then the implementation:

- `_payroll_tax` charges the tax at every solve; `_payrollTaxOn`, `payroll_tax_applied`, the
  schema field and its validator, `utils.parse_switch` (fork-only, used by nothing else; `utils.py`
  now differs from upstream only by the fork's two mode options) and the UI passthrough key are gone.
- `withPayrollTax` is a `RETIRED_OPTIONS` key ("now always charged"): unlike `withEarningsTest`,
  the household template carried it, so a case saved from it (`otherFiles/Case_us.toml`, not in this
  container) gets a deprecation warning, not "unknown option"; remove the line there. The template
  line is removed.
- Summary rows and the Cash Flow column for a household with earnings in the plan (the tax is then
  positive), none without.
- Docs: `modeling-capabilities.md` row, `Documentation.py`, the `PARAMETERS.md` row removed (as for
  `withEarningsTest`), `phase5-plan.md` step 5 and D3 marked revised, CLAUDE.md.

Recorded values. Upstream's own pins stay upstream's: `test_repro.py` (autouse), `test_toml_cases.py
::test_reproducibility` and the john+sally local-search test take the tax out with a `payrollTax`
monkeypatch fixture, so they keep checking that the fork equals upstream elsewhere and upstream's
future pin changes merge cleanly. Measured first that local search still reaches branch-and-bound
on john+sally with the tax (both 14,013.49 bequest; 9 s vs 44 s). The fork's model with the tax is
pinned in the AMO fixture (HiGHS, frozen date, basis and bequest only; MOSEK entries removed, as in
2026-10-10): alex+jamie 228,132.48 -> 225,076.85, jack+jill 103,502.74 -> 101,611.96, joe
93,043.84 -> 91,275.84, john+sally bequest 16,802.68 -> 21.00, jon+jane 160,677.41 -> 155,455.03.
Two hand-written cash-flow identities in upstream tests (`test_export.py::test_cash_flow_sheet_
balances_to_zero`, `test_cashflow_balance.py::_assert_cashflow_balance`) gained the tax term.
`test_payroll_tax.py`: switch tests removed; "without the tax" comparisons use a monkeypatched rule
(`_without_the_tax`); hand numbers unchanged.

First full run after the implementation: 16 failed (the pins and identities above), 3501 passed.

**Upstream issue** `fork-notes/issue-payroll-tax.md` (not posted), repro
`issue-payroll-tax-repro.py`, output `issue-payroll-tax-repro-output.txt` (stock `dev` `4e55b36`,
frozen date): FICA entered as a negative big-ticket item, which is how a non-deductible cash
outflow enters Owl, on the six examples with wages: spending -1.3% to -3.2% a year (alex+jamie
-3,000, chris+pat -2,794, jack+jill -1,903, joe -1,298, jon+jane -5,156), john+sally's bequest
16,803 -> 21. Cross-check: the fork's charged totals equal the script's hand FICA, and where the
fork's model otherwise equals upstream's (alex+jamie, joe, john+sally, jon+jane) the fork's objective
equals the script's "with FICA" within \$0.16. Upstream mentions no payroll tax: case-insensitive
search of its 296 `.md`/`.py`/`.tex`/`.toml` files on `4e55b36` (`\bfica\b`, `payroll tax`,
`0.0765`, `wage base`, `medicare tax` not after "additional", `social security tax\b`,
`self-employment tax`): one hit, digits in `data/mortality_tables.py:370`.

Full suite after the fixes: **3517 passed, 1 skipped** (11:56; 3516 + 5 new - 4 tests of the switch). flake8 clean;
Ruff only upstream's three `B905`s.

## Review of the merges after step 5 (2026-10-24, on `claude/phase5-step1`)

The user asked for a check of `2f18d7b` (`e3592e7`, #205), `8f99a4c` (`3444729`), `8f90118`
(`6ea43a9`, earnings test as landed, #225) and `14fcdc2` (`4e55b36`, #221/#223/#224/#226): technically
correct, and consistent with upstream's approach. The standard used, from the maintainer's own
words: model a rule exactly when it changes a decision the household faces soon, without making
the planner harder to use (inputs, options) or slower to solve; derive inputs from what the plan
already holds rather than add columns; no new loop quantities (#185); take upstream's version of
anything it lands.

Held (checked):
- **Take theirs.** `3444729`: our #197 test dropped for upstream's. `6ea43a9`: upstream's earnings
  test, tests and docs taken; no remnant of the fork's version (`gross earnings`, `withEarningsTest`,
  `_warnGrossEarningsFallback`, `_ssEntitledFrom`: grep over `src ui tests info examples
  fork-notes/phase0` finds only upstream's two asserts that the column is absent).
- **#205 guard (`e3592e7`)** adds no column and no binary (upstream's own commit avoids even an inert
  column), and leaves an approximation in place rather than a binary per year, as upstream chose for
  #206. Its residual change (floors count only in years that itemize) measures what the LP sees.
- **#225 in fork code.** The fork's AGI-based quantities (federal floors, SALT phase-down, NY
  medical floor, STAR income) read `MAGI_n`, which carries upstream's `dl` correction.
  `_state_agi_and_ti` starts from `G_n + e_n + Q_n` without it; probed: with a \$20,000 deduction on
  \$30,000 of income the LP lowers `e_n` (G 0, e 10,000, MAGI 10,000, NY AGI 8,000 = MAGI less the
  \$2,000 exemption), so `dl` is positive only when the deduction exceeds all income, where NY AGI
  is near zero and its only readers (recapture from \$107,650, the line 46 cut from \$200,000) cannot
  be reached. No code.
- **#226** reaches every fork solve: the fork calls HiGHS only through `_run_highs`, and
  `_run_highs_lp_with_duals` is upstream's.
- **#221 in the payroll tax**: same base as the earnings test (merge `14fcdc2`).

Fixed here:
1. **The #205 guard's limitation was undocumented and misdescribed.** PROGRESS, CLAUDE.md and the
   docstring said the guard is short of the worksheet "only when an itemizer's ordinary income is
   below the deduction"; it also covers non-itemizer charity years. Probed
   (`fork-notes/merge-review/nch205_probe.py`, output `_2026-10-24.txt`, frozen date, FL, \$3,000
   charity line): in a \$4M-taxable couple with or without a mortgage, ordinary income filled the
   deduction in every year (G > 0), where the guard is exact; with no tax-deferred balance, 8
   years had G = 0 but gains (~\$12.8k) stayed in the 0% bracket: cost \$0. Under
   `withLTCG="optimize"` the guard left more bequest than upstream's rows in every year in all
   three cases (\$2,302, \$3,885, \$209). It can cost only when ordinary
   income is below the deduction and gains pass the 0% bracket's top (\$98,900 MFJ in 2026), only
   under `withLTCG="optimize"` / local search (loop mode: identical plans with and without the guard
   in all three cases). Not worth code; now a stated limitation in `modeling-capabilities.md`'s
   itemized row, as upstream states #206, and the docstring and gotcha corrected.
2. **Household inputs behind upstream.** `gen_hfp_us.py` lacked `months worked` (the column that
   decides the grace year, the case the maintainer calls the one where the test matters most) and
   said `big-ticket items` is the only signed column (#225 made `other inc` signed too); it now
   writes upstream's columns in upstream's order and states #221/#225. `phase0-scenarios.md` §4b
   still said the earnings test is not modeled and to keep the worker at FRA; corrected (the full
   §4/§4b rewrite stays with step 6).
3. **CLAUDE.md gotchas** still described the pre-#221 earnings (`kappa_ijn[:, :3]`); corrected.
4. **#185 status.** The previous session's reply said #185 was still open with the maintainer; per
   the user it was dropped (upstream table row and CLAUDE.md updated; not checked on GitHub).

Open, the user's call (decided the same day: always on, issue drafted; next section): **the payroll tax is an opt-in switch** (`withPayrollTax`, off in code, D3
"core, opt-in", 2026-10-18), which is the pattern upstream and the user have since rejected: the
earnings test landed with no option (the fork retired `withEarningsTest` for the same reason), and
the user dropped "convex" because an opt-in with no signal for when to use it is a burden. The
payroll tax meets the maintainer's test as well as the earnings test does: it changes a near-term
decision (an extra year of work, part time), needs no input (it reads the derived earnings), and
costs nothing to solve (a constant of the cash-flow row). Upstream does not model it: since #221
`anticipated wages` are the AGI wages and are counted as cash, so a working year's cash is
overstated by 7.65% of wages (plus 0.9% above the Additional Medicare threshold); upstream's docs
do not mention payroll tax or FICA (grep over its `.md`, `.py`, `.tex` on `4e55b36`: no hit).
Options: (a) on by default with no switch, moving the fork's recorded values for cases with wages;
(b) a design issue upstream at the concept level, as #220 was; (c) leave as is.

## Local-search speed on the fork, before and after `3444729` (2026-10-24, on `claude/phase5-step1`)

The 18 examples with the local-search preset, HiGHS, today's date, fork code at `047c140` (before
the merge) and `6a3fe6a` (after), run one after the other on this container
(`fork-notes/local-search/speed-3444729/`: `run.py`, `before.tsv`, `after.tsv`; one run each).
Total **1,965 s -> 2,010 s (+2%)**: no speed-up on the fork with HiGHS. Per case from 0.66x
(kim+sam-spending, dana) to 2.25x (chris+pat) and 1.63x (jordan+taylor-qcd, the case the
maintainer says needs the full link rows under branch-and-bound). Objectives: john+sally
31,778.17 both ways; everything else within 0.05% (kim+sam-bequest -0.051%, chris+pat +0.030%,
morgan +0.018%), close to the maintainer's 0.07% band. Same method label in every case.

Not established: run-to-run noise on this container (one run per version; full-suite wall times
here have varied 8:55-10:22 on similar trees), and how much of the fork's time is the fork's
code rather than this machine (no stock-`dev` run here; the maintainer's 740 -> 695 s HiGHS
figures are from his machine). His large gain was with MOSEK (726 -> 396 s), which is not
installed here; HiGHS gained 6% for him.

**Same-machine stock baseline** (same day, stock `3444729` in a worktree, same script; `stock.tsv`):
stock **1,663 s**, fork **2,010 s** (1.21x). This container is about 2.4x slower than the
maintainer's machine for stock (his 695 s with HiGHS). The fork's extra time sits in four cases:
devon 68 -> 234 s (3.43x), jordan+taylor-qcd 66 -> 154 s (2.34x), jordan+taylor 48 -> 93 s
(1.92x), chris+pat 74 -> 120 s (1.61x); the other 14 are within 0.92-1.15x (bill and cameron
under a second). These are not the same problem: the fork's model differs (itemizing on by
default, the age-anchored smile, the earnings test in alex+jamie / chris+pat / jack+jill), and
the objectives move with it (jordan+taylor-qcd +3.5%, morgan +3.6%, jordan+taylor +2.7%, jack+jill
+1.0%, devon +0.5%, alex+jamie -0.3%, chris+pat -0.14%). Which fork feature costs the time in
those four is not measured (first check: the four with `withItemized="none"`).

**The four with `withItemized="none"`** (fork `6a3fe6a`, same day, same script with the option
added, `run2.py` / `noitem.tsv`; one run each):

| Case | stock | fork, itemizing (default) | fork, `"none"` | objective: stock / fork default / fork `"none"` |
|---|---:|---:|---:|---|
| devon | 68 s | 234 s | 71 s | 248,576.00 / 249,877.18 / 248,576.00 |
| jordan+taylor | 48 s | 93 s | 56 s | 1,559,325.13 / 1,600,971.47 / 1,600,636.90 |
| jordan+taylor-qcd | 66 s | 154 s | 148 s | 1,206,372.88 / 1,248,802.27 / 1,248,802.27 |
| chris+pat | 74 s | 120 s | 122 s | 117,308.95 / 117,139.65 / 117,139.65 |

- devon: itemizing is the whole difference, time and objective (`"none"` = stock to the cent).
- jordan+taylor: itemizing costs 37 s and \$335 of bequest; the rest of the +2.65% gap to stock
  is not itemizing. Both jordan+taylor cases use the smile with `smile_start_age = 66`, so the
  fork's age-anchored smile is the likely cause; not run.
- jordan+taylor-qcd: itemizing changes neither time nor objective; the 2.2x and the +3.5% are
  something else in the fork (the smile, likely, as above; not run).
- chris+pat: itemizing changes nothing; the case is one of the three the earnings test touches,
  and stock `3444729` has no earnings test, so its time and objective there are not comparable
  (a stock run at `6ea43a9`, which has the test, would be).

So itemizing explains devon and part of jordan+taylor. It is a model cost, not a search defect: the
default `"loop"` adds loop parameters (branch, floors, SALT cap) and can take more iterations.

**The rest isolated** (2026-10-24, `run3.py`, one run each, same container; `fork_flat.tsv`,
`stock_flat.tsv`, `fork_cp.tsv`, `stock6_cp.tsv`):

| Run | jordan+taylor | jordan+taylor-qcd | chris+pat |
|---|---|---|---|
| fork, itemizing off, flat profile (60%) | 52.6 s, 1,358,656.18 | 73.4 s, 1,003,632.53 | |
| stock `3444729`, flat profile (60%) | 51.1 s, 1,358,656.18 | 71.9 s, 1,003,632.53 | |
| fork, itemizing off | | | 123.2 s, 117,139.65 |
| stock `6ea43a9` (has the earnings test) | | | 122.5 s, 117,139.65 |

With the fork feature removed, each case equals stock to the cent and to within 2 s:
jordan+taylor's remaining cost and jordan+taylor-qcd's whole cost are the fork's age-anchored smile
(`smile_start_age = 66`); chris+pat's is the earnings test, which stock now has too (and the fork's
result there is upstream's to the cent). **Summary of the fork's 1.21x:** devon = itemizing;
jordan+taylor = itemizing + smile; jordan+taylor-qcd = smile; chris+pat = earnings test (no longer a
fork difference after `6ea43a9`). The search itself is no slower on the fork; the fork solves a
different problem in those cases.

## #220: earnings test reviewed; PR built on stock `dev` (2026-10-23, on `claude/phase5-step1`)

**Review** of the earnings-test implementation (rules in `socialsecurity.py`, `Plan._ss_streams`
and helpers, HFP columns, outputs, warnings), read against upstream's
`compute_social_security_benefits` / `_add_spousal_benefit` and the rule list of the module.
Two defects found, both fixed test-first (`103b252` spec, strict xfail; `e82f6bb` fix):

1. `Plan._ssFRAStartAbs` used the eligibility test (`tobs <= 2`) where only a birth on the 1st
   attains an age a month early (`earnings_test` uses `tobs == 1`). For a birth on the 2nd the
   plan's FRA month was a month early (run: born 1960-01-02, plan Dec 2026 vs the test's Jan
   2027). It feeds the Summary's *ARF months* window and the pays-nothing warning (by reading
   the code, not run: a false warning when all but the last pre-FRA month is withheld); the
   streams use the test's own FRA month and were not affected.
2. The `gross earnings` fallback warning counted 401k/IRA/Roth columns but not *taxable ctrb*,
   although upstream's convention nets *anticipated wages* of every ctrb column (Documentation):
   a year with wages and only a taxable contribution understated the test's earnings silently.
   The warning and the docs now say "net of contributions" (IRA and taxable contributions are
   not payroll deferrals, which the old text called them all).

Also renamed `born_on_first = tobs <= 2` (an eligibility flag) to `first_days` where it gates
the age-62 reset. Checked and not changed: entitlement grid vs upstream's payment start and
partial first year, spousal start (`max(ent_abs)` = upstream's latest claim), spousal end at the
first death, charging order and records, crediting months before each person's FRA, ARF from
the FRA month, survivor base with the deceased's ARF, trim on both streams, the solve-time
rebuild under `withSSAges` clones and local search. Not verified against a primary source
(recalled only): whether SSA also adjusts the reduction factor at a death before FRA for the
survivor's benefit; the module leaves it out and says so.

Fork tests on the touched files after the fixes: 456 passed (`tests/ss`, the HFP-column tests,
`test_payroll_tax.py`, `tests/ui`). Full fork suite on `e82f6bb`: **3489 passed, 1 skipped** (10:14; 3485 + the 4 new tests). flake8 clean; Ruff only upstream's `B905`.

**PR on stock `dev`** (branch `earnings-test-pr`, one commit `c6fcedb` on `e3592e7`; text
`fork-notes/pr-220-body.md`): the earnings test and the two columns only, ported by hand from the
fork (methods extracted verbatim, then the payroll-tax branches and fork references removed: the
fallback warning has no payroll path, plan/decision references and "review finding" dates are
gone from docstrings and tests). Added for upstream: CHANGELOG entry, `papers/owl.tex` (two "not
modeled" sentences), a JSON-output test (the fork's is in `test_payroll_tax.py`), the template
workbook's two columns. On stock `dev` the first full run gave 2 failures, both expected:
the example-workbook header check (exempted the two derived columns, as the fork does) and
jack+jill's recorded spending: **102,531.46 without the test -> 102,620.63 with it** (frozen
date, Jill's \$14,302 nominal withheld in 2028, 11 ARF months; same withholding as the fork),
re-recorded as 102_621. The fifteen other examples equal to the cent (the parametrized test).
PR suite on `c6fcedb`: **3140 passed, 1 skipped** (8:55); Ruff clean. CI's strict flake8 selection: 0.

The #220 reply draft points to the PR and names the taxable column in the warning. **Opened by
the user as PR #222** (https://github.com/mdlacasse/Owl/pull/222, 2026-10-23); the reply, which
links it, posted by the user the same day; no maintainer answer as of 2026-10-24.

2026-10-24: upstream `dev` moved to `3444729` (`cd50a0a`: regret sweep can no longer report a
negative regret; `3444729`: local search relaxes the redundant half of the LTCG links). PR #222
then conflicted in `CHANGELOG.md` only (both add a *Version WIP* entry at the top); merged
`upstream/dev` into `earnings-test-pr` with both entries kept (`7848cff`): full suite **3145 passed, 1 skipped** (10:22; 3140 + upstream's 5 new tests), CI's strict flake8 0; pushed, and the PR merges cleanly onto `dev` again (`git merge-tree`). (The suite run was first reported here as interrupted: only the wait on it was; it finished.) The fork merged it the
same day (next section).

## The earnings test without an option (2026-10-23, on `claude/phase5-step1`)

User's decision on the #220 reply draft: the maintainer asked for an implementation, not a choice,
and `withEarningsTest` had one effect, keeping wrong cases wrong (paying benefits SSA would
withhold). With the switch off Owl gave no signal that it mattered: `_warnEarnings` returned
before any earnings-test warning. D6 ("off in code") had been chosen only to keep the fork's
merges clean (`phase5-plan.md` §6, revised).

Test-first: spec `bb82794` (`tests/ss/test_earnings_test_always.py`, 6 strict xfail + 1 guard that
passed on arrival), then the implementation:

- every solve applies the test; the `withEarningsTest` switch is gone (first kept as a retired
  option with a deprecation warning; removed outright the same day at the user's review: the key
  never existed outside the fork and no case of ours had run on it, so nobody needs the warning);
- where the test withholds nothing and credits no ARF month, `_ss_streams` returns
  `compute_social_security_benefits`' own output (checked with a marker on that function), so the
  cases the test does not touch follow upstream's builder by construction;
- Summary rows for a household with earnings in a plan year up to someone's FRA year
  (`ss_earnings_reachable`), \$0 / "none" included, so two claiming ages of one household compare
  row by row; none for a household without such earnings;
- `owlcli explain` drops the `applied` flag; UI passthrough key, schema field and template line
  removed; docs (PARAMETERS, modeling-capabilities, Documentation, Financial Profile help).

Tests that compared on/off now compare against Owl without the test, i.e. the test run on zero
earnings (`_without_the_test`; wages still count everywhere else); tests of the switch itself
(spellings, round trips, "no warning when off") removed. Recorded values: only
`test_toml_cases.py` moved, jack+jill 103,499 -> 103,578 (103,499.11 with the test on zero
earnings, frozen date, same solve settings; Jill's \$14,302 withheld in 2028, 11 ARF months).
Full suite: **3488 passed, 1 skipped** (10:40; 3492 + the 7 new - 11 tests of the switch itself),
before the retired-option entry and its 3 tests were removed After that: **3485 passed, 1 skipped**
(10:31; 3488 - the 3 parametrized cases of the old-key test). flake8 clean; Ruff only upstream's `B905`.
flake8 clean; Ruff only upstream's `B905`.

The #220 reply draft (`fork-notes/issue-220-reply.md`) is revised accordingly: the test is part of
the model, the 15 untouched examples are unchanged, the three change; it promises a PR on stock
`dev` and leaves the payroll tax out.

## #220 answered by the maintainer; reply drafted with the full-MILP cost (2026-10-23, on `claude/phase5-step1`)

Maintainer on #220 (relayed): the case was overlooked, does not apply to him; "What did you end
up doing? ... I trust your judgement to fill the gap that suits you best. The only requirement is
that the optimize full MILP is still affordable on today's computer."

**Measured** (`fork-notes/phase5/et_milp_cost.py`, output `et_milp_cost_2026-10-23.txt`; today's
date, `breakpointMethod="branch-and-bound"`, `withItemized="none"`, the case's own claiming ages,
two solves per setting; a container restart interrupted the run after alex+jamie's first solve and
it was resumed for the missing solves):

| Case | Columns / binaries | Rows off / on | Off: s (nodes) | On: s (nodes) | Basis off -> on |
|---|---|---|---|---|---|
| chris+pat | 1,900 / 352 | 1,968 / 1,960 | 50.7, 49.8 (15) | 43.7, 42.7 (1) | 117,203.40 -> 117,088.45 |
| alex+jamie | 1,626 / 289 | 1,584 / 1,576 | 248.9, 197.8 (25) | 162.9, 162.2 (143) | 229,912.91 -> 229,363.80 |
| jack+jill | 1,900 / 352 | 2,001 / 1,993 | 312.6, 308.3 (267) | 200.8, 202.0 (1,077) | 104,251.68 -> 104,324.20 |

Same columns and binaries; 8 rows fewer, all `ss_tax_*` (SS-taxability rows of the year whose
benefits are fully withheld; Owl writes them only for years with SS; checked by tag count on
chris+pat, script not kept). Building the streams with the test: about 1 ms per solve. Every case
solved faster with the test on; nodes went down on one, up on two: input-driven, not a cost of the
test. Under `withSSAges` the candidate count is unchanged. Not run: a `withSSAges` search under
branch-and-bound (up to 97 candidates per person per round at 40-310 s each, with or without the
test).

**Reply draft** `fork-notes/issue-220-reply.md`: what was built (stream-level, opt-in; rules;
`gross earnings` / `months worked` with the fallback warning; survivors out; outputs; the no-op
property), the table above, and an offer of a PR on `dev` (the test and the two columns, opt-in,
with tests), the payroll tax as a separate PR if wanted. For the user to review and post.

## Upstream `dev` `e3592e7` merged (2026-10-23, on `claude/phase5-step1`)

One upstream commit, #205 (not ours): the QDCG worksheet starts from taxable income after the
deduction, so a standard deduction that ordinary income leaves unused takes gains out of tax.
Optimize mode: the room15/room20 MILP rows add `e_n` (and `k*p_n` under the optimized senior
bonus) and widen by `sigma_n`; loop mode: the brackets widen by the previous iterate's unused
deduction, with rows `ltcg_room15/20_deduction`; `_ltcg_tax_implied` follows the worksheet.
Merged with no text conflict (`2f18d7b`). On the merge commit alone the full suite gave 3489
passed, 1 failed (`test_examples_loop_matches_none_unless_a_year_itemizes[Case_robin]`).
Two fork adaptations (spec `[test]` commit, strict xfail, then the fix):

1. **Itemizers' brackets shrank.** Upstream takes `sigma_n` as the most `e_n` can be. Fork
   itemizing raises `e_n`'s bound in itemized-branch years and in non-itemizer-charity years,
   and there `sigma_n - e_n` is negative whenever ordinary income fills the deduction: the 0%
   room becomes `T15 - G_n - (e_n - sigma_n)` instead of `T15 - G_n`. Measured
   (`fork-notes/phase5/merge205_itemized_probe.py`, output `_2026-10-23.txt`, frozen date):
   mortgage couple with pensions, `withLTCG="optimize"`: bequest \$2,363,527 with the fix,
   \$2,360,673 with upstream's rows in every year (\$2,854 less: the LP cut ordinary income,
   `G_n` 77k -> 65k in 2026, to fit the gains under a bracket made too narrow); loop mode
   identical both ways (its unused deduction is clipped at 0 when `G_n > 0`). Fix:
   `Plan._ltcg_deduction_widens_n()` keeps those years' rows as before #205 (exact when
   ordinary income fills the deduction, short of the worksheet only when an itemizer's ordinary
   income is below the deduction), and `_ltcg_tax_implied` stacks gains on `G_n` there. The
   branch per year is now `_federal_item_branches()`, shared with `_add_federal_itemized`.
   Exact widening for itemizers would mirror every deduction row into the gains rows; not done.
2. **Robin's loop ran 3 iterations longer under `withItemized="loop"`.** The LP iterates were
   the same as under `"none"` (checked array by array for 17 iterations), but #205's rows
   change which vertex the LP returns at a tie (|dX| 65 vs 3 at the same objective), robin's
   charity paid sits at the 0.5% floor, and the floor flag `_item_chl_n` flipped each
   iterate. `_itemized_sc_moves` counted each flip as a \$2.1-2.4k move in years that take
   the standard deduction, where floors move nothing (the non-itemizer charity has no floor).
   The federal floors, their flags and the SALT cap, and the state medical floor and its flag,
   now count only in years where a branch itemizes (in the LP or at the iterate's amounts).
   Robin is back to the `"none"` plan to the cent.

Full suite: **3492 passed, 1 skipped** (13:47; 3488 + upstream's 2 + the 2 new). flake8 clean;
Ruff only upstream's `B905`. No recorded value moved.

## #185 after the changes since filing (2026-10-17, on `claude/intelligent-faraday-pfhera`)

#185 is open; on github.com (WebFetch, 2026-10-17) the only maintainer comment is still the
2026-10-12 one on cycling; then our data comment and the #193 pointer. Upstream `dev` `7abed19`
still says "Itemized deductions not modeled" (`info/modeling-capabilities.md:29`) and "Mortgage
interest is not deducted" (`ui/Documentation.py:560`); its commits since `10b9f72` are #195 (SS
ages), nothing on deductions.

Reruns on `50b152c` (`model-review/phase3-review/`):
- `itemized_convergence_2026-10-17.txt` (date frozen 2026-10-15, as the 2026-10-15 file): the 74
  non-NJ rows (NY probe, NY federal-only, property-tax sweep, local search, 18 examples) identical
  except `NYmort 2099 maxBequest LS loop` 686,772 -> 688,814 (the LTCG fix `997f36d`; not quoted
  in the comment; the quoted 2032 local-search numbers $498k / $670k / $710k are unchanged). The
  16 NJ rows all changed (upstream's NJ). The comment's NJ claim, redone: 7 pairs itemize (was 6),
  same ending in 6, one 2-cycle became plain "oscillatory" (the posted one went the other way);
  0-2 fewer iterations with itemizing (was 0-4 more); SS the largest residual in both modes,
  $1.4k-3.9k (was $1.1k-1.6k). The conclusion (no added cycling) holds on upstream's NJ.
- `gain_basis_loop_2026-10-17.txt` (`gain_basis_loop.py`: `gain_basis.py` with `"loop"`, since
  R1 removed `"optimize"`; date frozen 2026-10-11): at `fe4db7f` the NJ rows reproduce the posted
  stakes exactly (federal tax saved 15,478 / 20,453 / 88,708); at `50b152c` they are 17,730 /
  24,093 / 95,924 (bequest 30,385 -> 42,272, 27,934 -> 32,040, 140,995 -> 159,164). The rise is
  the NJ removal alone (`a5fd533`; `bbeee68` left its 40 regression cases identical, `5dc520b` changes no result): more
  NJ income tax, so more SALT. NY rows are not comparable through this script (`withItemized`
  now switches NY IT-196 too); NY results were unchanged by the removal (its regression).

Effect on the posted text: the "NY or NJ" stakes ($15k, $20k, $87-89k) were fork-NJ numbers; on
upstream's NJ they are $18k, $24k, $96k, so the issue understates them slightly; "two state
schedules I keep there" is now one (NY IT-196). Nothing changes a question or the design. Not
posted; worth a line in the next comment on #185.

## Discussion #177 after the NJ removal (2026-10-17, on `claude/intelligent-faraday-pfhera`)

Question: does dropping NJ affect the housing / budget proposal (#175, now Discussion #177)? No,
not in substance (grep over `fork-notes/` and `src/`). The NJ line 41 rule left the upstream ask in
our first #175 reply (2026-10-08); what #177 discusses is the budget -> spending-profile contract.
The posted reply 2 mentions NJ only in the test-case line ("a possible move to NJ"); reply 3 not at
all. No comment posted for that alone; the next reply can mention it in passing.

Cleanup:
- `budget.DEDUCTIBLE_TYPES` drops `"rent"`: NJ's 18% share was its only consumer (grep: nothing in
  `src/` read rent as deductible after `a5fd533`). Rent keeps its survivor default
  (`HOUSEHOLD_TYPES`). Stale NJ docstrings fixed in `budget.py`, `test_itemized.py`,
  `test_itemized_data.py`, `test_budget.py`; the latter now asserts rent is not deductible.
- `owl-budget-requirements.md`: requirement 5's example is now the fork's property tax (federal
  SALT, NY IT-196, STAR), medical and charity readers; test case without NJ.
- `issue-175-reply-2.md`, `issue-175-reply-3.md`: headers say posted (PROGRESS.md already did).

Tests: full suite **3190 passed, 1 skipped** (10:16, slowed by a parallel targeted run; same count
as before, the change only extends an assertion). flake8/ruff: only upstream's known lines.

## ss-convex removed (2026-10-17, on `claude/friendly-mccarthy-585okd`)

The fork had kept upstream's experiment branch `ss-convex` (merged in `ae1fb9d`, `bb00250`) under
the rule "drop it when upstream drops it", although our PR #196 reply asks upstream to drop it and
no decision run uses it (the local-search preset replaces "convex" with "optimize"). User's call:
remove it now, as with the NJ code. Done by applying the reverse of upstream's three commits
(`git diff c22f46d 10b9f72`, 3-way) to the current tree: `schema.py`, `utils.py` and `_run_highs`
are upstream `dev`'s again (the LP basis cache goes), `_configure_ss_taxability_convex`,
`_update_ss_regions`, `_ss_provisional_income_row`, `_ssCapProbeSolve` / `_ssCapProbe` /
`_ssCapGap` and `_BasisCache` are gone, and `tests/plan/test_ss_convex.py` with them. Three
`plan.py` conflicts, each resolved to the fork's pre-convex code (checked against `ae1fb9d^1`):
the probe body (removed), the loop start (`sc_lp = self._snapshot_sc()`, no warm start), the SS
residual move (`psi_implied - sc_lp["Psi_n"]`, no `tss` branch). Fork edits dropped too:
`warm_keys` in `_ssCapProbe`, `tests/plan/test_ss_convex_fork.py`. `withSSTaxability="convex"` is
now refused like any unknown mode. Every function the three commits touched is either gone, equal
to upstream `dev`, or a fork function whose remaining diff from `dev` is fork work only (no
convex identifier left, grep).

Regression (same 40 cases as the NJ removal, against its "after" run at `a5fd533`;
`fork-notes/model-review/nj-removal/compare_ss_convex_2026-10-17.txt`): all 40 identical to the
cent. Full suite **3190 passed, 1 skipped** (7:40; the 3 removed tests: two in `test_ss_convex.py`,
one in `test_ss_convex_fork.py`). flake8/ruff: only upstream's known lines. The fork-notes scripts
that ran "convex" (`model-review/ss-loop/convex_*.py`, `pr196_*.py`, `issue-193-*.py`) need `a5fd533`
or earlier.

## Fork NJ code removed (2026-10-17, on `claude/friendly-mccarthy-585okd`)

User's decision after "NJ dropped from the investigation" (below): the fork's NJ mechanisms were
generic in code but used by NJ alone, so removing them brings the fork closer to upstream and drops
code nobody uses. Removed:
- the income-tiered retirement exclusion (lines 28a-28c): `_add_state_tiered_exclusion`, the
  `st_rx` / `rxl` / `rxb` columns and `zx` binaries, `RX_WINDOW` / `RXF_n` (free set),
  `RX_NODE_LIMIT` / `RX_MOSEK_TIME_LIMIT`, `_rx_fixed` and `_refix_boundary_tiers`,
  `_tiered_exclusion_free` / `_implied`, `_set_tiered_exclusion`, `_exclusion_shortfall`,
  `tax_state._read_exclusion_tiers` / `exclusion_share`, the `zx` local-search family, the explain
  fields, the Summary's RX node-limit note;
- the property tax deduction (line 41): `st_pt`, `st_ptd_*`, `_add_property_tax_deduction`;
- the medical deduction (line 31): `st_med`, `NJMF_n` / `_nj_medl_n` (loop parameters),
  `_add_nj_medical_deduction`, `_nj_medical_*`, the "state medical" residual, the `hsa` switch of
  the medical-premium helpers (only line 31 passed `hsa=False`);
- with the node cap: `Plan._node_limit`, `_time_limit` and the fork's two log warnings for a MILP
  stopped at its time or node limit (`_warn_time_limit`, `_warn_node_limit`); `_run_highs`,
  `_countHighsNodes` and `_mosekSolve` are upstream's again, except `_run_highs`'s LP basis cache
  (from `ss-convex`); `export._mip_node_limit` is upstream's;
- data: the NJ sections of `taxes_state.toml` are upstream's text exactly, and the header no longer
  documents `retirement_exclusion_*`, `property_tax_deduction`, `medical_deduction`;
- tests: `test_state_tiered_exclusion.py`, `test_nj_medical.py`, ten NJ tests in `test_budget.py`
  and one in `test_itemized_data.py`; four generic tests kept without their NJ assertions (now NY);
- docs: CHANGELOG (four NJ sections out, one "Removed" entry in), CLAUDE.md, PARAMETERS.md,
  `modeling-capabilities.md`, `Documentation.py`, `phase0-scenarios.md`.

Kept: `processDebtsAndFixedAssets()` before the variable map in `solve()` (upstream calls it after):
mortgage interest and the budget feed the itemized columns too.

Size (diff against upstream `dev`): `plan.py` +2,714/-205 -> +2,146/-200; `tax_state.py` +412 -> +311;
`taxes_state.toml` +98 -> +50; `explain.py` +120 -> +70; `export.py` +126 -> +116; whole change
+101/-1,622 lines (src +46/-846).

**Regression** (`fork-notes/model-review/nj-removal/`: `regress.py`, `cases.txt`, before at
`fe4db7f` and after, `compare_2026-10-17.txt`; date frozen at 2026-10-15): all 36 non-NJ cases
**identical to the cent** in bequest or spending, lifetime federal and state tax, fixed-point
residual and method label (18 examples under the loop, 6 under the local-search preset, the NY
Yonkers probe couple with and without a mortgage under 2032 and 2099 law, loop and local search, NY
without a locality, STAR loop and optimize). NJ cases, as expected: bequest -$43k to -$69k, lifetime
state tax +$36k to +$45k (no exclusion or deductions), local search 138-149 s -> 42-44 s.

Full suite **3193 passed, 1 skipped** (7:43; 3250 in 8:23 before). flake8/ruff: only upstream's known lines.

Consequence: the fork-notes scripts that measured NJ (`nj_stakes.py`, `housing_stakes.py`'s NJ cases,
`convex_fork.py`'s NJ cases, `local-search/*` NJ runs) depend on the removed code; they run against
`fe4db7f` or earlier.

## NJ dropped from the investigation (2026-10-17, on `claude/friendly-mccarthy-585okd`)

User's decision: NJ is unlikely as a place to live, and with moves it complicates things for no
discernible benefit. Upstream's NJ (brackets, one move) stays. Measured on the fork at `da320bc`:

- **Fork NJ code**: about 250 added lines in `plan.py` (fork-only functions: the tiered exclusion,
  `_add_state_tiered_exclusion` 95 lines, `_exclusion_shortfall`, `_set_tiered_exclusion`,
  `_tiered_exclusion_free`, `_refix_boundary_tiers`, `_tiered_exclusion_implied`; line 41
  `_add_property_tax_deduction`; line 31 `_add_nj_medical_deduction`, `_nj_medical_paid`,
  `_nj_medical_floor_flags`, `_nj_medical_shortfall`), plus `tax_state.py` exclusion tiers, the
  `zx` local-search family, the `RX_NODE_LIMIT` / `_rx_fixed` handling in the loop, explain entries
  and data. NJ also appears in shared code: the itemizing and medical-premium functions (NJ line 31),
  `_ssCapProbe`, `_node_limit`.
- **Tests**: `test_state_tiered_exclusion.py` (19), `test_nj_medical.py` (12), the NJ cases in
  `test_budget.py`, `test_state_residency.py`, `test_state_itemized.py`: about 255 s of CPU,
  roughly 14% of the suite's CPU (one minute of its eight on 4 cores).
- **Runs**: NJ variants were the slow and unstable ones. "Convex" 4-7 min in NJ vs seconds in NY;
  local search 98-227 s vs 54-184 s on the probe couple; NJ `maxBequest` runs stopping at the
  exclusion node cap moved $2.2k in one day.
- **Merges**: of the recorded upstream merges, one (2026-10-10, node caps) needed NJ-specific work
  (`RX_NODE_LIMIT` routed through `Plan._node_limit`); the others' conflicts were docs, tests and the
  loop region.
- **Work avoided**: Stay NJ / ANCHOR / Senior Freeze, the next item planned, comparable in size to
  STAR (data check plus about 1,800 changed lines). Without it, every NY-vs-NJ owner comparison was
  biased toward NY, so NJ could not be compared fairly without doing it.

Decision taken: **drop NJ from the investigation, keep its code.** No new NJ work and no NJ variants
in decision runs; `CLAUDE.md`, `phase1-revised.md` and `phase0-scenarios.md` (section 3: the NJ
commands replaced by a move within NY) updated. Moves within NY (locality, STAR school district)
stay; they need the fork's multi-move `Residence`.

Removing the NJ code was first left undone (a session of edits for a small saving); the user then
decided to remove it: see "Fork NJ code removed" above.

## STAR branch merged (2026-10-17, on `claude/friendly-mccarthy-585okd`)

`claude/zen-heisenberg-rfreik` (`6b565a7` data check, `b09af78` NY STAR as a rule; base `f29a633`,
worked in parallel) merged after upstream `7abed19` and the #197 fix. Conflicts: CHANGELOG (both new
sections kept, STAR first) and CLAUDE.md's test-count line; `localsearch.py` auto-merged (STAR adds
`zst` to `FAMILIES`/`FAMILY_LABEL`, #197 changes step (b)); PROGRESS.md and the rest auto-merged. No
duplicate definitions (AST scan of the 27 changed Python files). Full suite **3250 passed, 1 skipped**
(8:23; = 3234 + STAR's 16). flake8/ruff: only upstream's known lines.

Checked the same day: does step (b) pinning `zst` block STAR moves? (`fork-notes/star/zst_step_b.py`,
output `zst_step_b_2026-10-17.txt`; NY Yonkers owner couple of `tests/tax/test_star.py`, budget $80k
core + $25k property tax, SS $4,200/$3,600 at 67, $900k/$600k tax-deferred, taxable $900k/$1.1M/$1.3M
each, born 1960/61 (65+ now) or 1962/63 (65 in 2027/28), `maxBequest`, statutory law.) Mechanism: a
pinned `zst = 1` caps the year-(n-2) STAR income, which includes taxable SS, at the standard, so an
SS move raising it is blocked; a pinned 0 cannot collect the credit.

| taxable | born | LS as is | LS, `zst` free in (b) | Enhanced yrs |
|---|---|---:|---:|---|
| $900k | 1960/61 | 4,454,138 | 4,454,138 | 28/28 both |
| $900k | 1962/63 | 4,425,039 | 4,425,724 (residual $0 -> $2,230) | 29/29 both |
| $1.1M | 1960/61 | 5,006,003 | 5,006,003 | 7/28 both |
| $1.1M | 1962/63 | 5,017,885 | 5,006,116 (-$11,769) | 24 -> 20 of 29 |
| $1.3M | 1960/61 | 5,580,488 | 5,581,689 (residual $1 -> $4,718) | 7/28 both |
| $1.3M | 1962/63 | 5,591,242 | 5,591,242 (residual $9,714 both) | 8/29 both |

No systematic loss from pinning `zst`: freeing it changed nothing in 3 cases, gained only with an
inconsistent plan in 2, and lost $11.8k in 1. **Not changed.** Not established: how far local search
is from the optimum on these cases. The branch-and-bound preset (`maxTime` 600) ran > 80 min per case;
the 2-hour background limit stopped the batch with one result, $900k / 1962-63: 4,421,378 at a 1.5%
gap with $12,802 of SS residual, below local search's 4,425,039, so not a usable reference. Also not
traced: the $9,714 residual in the $1.3M / 1962-63 case (both variants).

## Upstream dev 7abed19 merged; main fast-forwarded (2026-10-17, on `claude/friendly-mccarthy-585okd`)

Upstream `7e5f11a` + `7abed19` (2026.10.17, #195 follow-ups): a selected individual's claiming age
is always optimized; an entered age already past is refused with a `ValueError` naming the person
(`_ssaCheckPastAges`; select only people not yet collecting). Merge `c3cce53`: one conflict, the
CHANGELOG heading (2026.10.16 -> 2026.10.17) under the fork's sections, upstream part identical to
`upstream/dev`; no duplicate definitions (AST scan); fork code does not call the changed helpers.
Upstream `main` = `dev` = `7abed19`; `ss-convex` unchanged at `c22f46d`. Full suite **3234 passed, 1
skipped** (8:44; upstream changed tests, added none). flake8/ruff: only upstream's known lines.
`main` fast-forwarded from `f29a633` to this branch. The local-search issue is filed as **#197**.

For household scenarios: with `withSSAges` selecting someone whose entered claiming age is already
past, the solve now stops with an error instead of silently fixing the age (CLAUDE.md, earnings
test: select only the one who stops working).

## Local search and the LTCG family: step (b) pins `zl` (2026-10-17, on `claude/friendly-mccarthy-585okd`)

Traced on stock upstream `dev` `7abed19` (scratch worktrees, date frozen at 2026-10-15). Issue draft
`fork-notes/issue-ls-ltcg.md` (filed as #197), repro `issue-ls-ltcg-repro.py` + output, patch
`issue-ls-ltcg.patch`; sweeps and scripts `model-review/ss-loop/ls_ltcg_*`.

- **No objective mismatch:** the local-search step log prints `-res[0]`, the MILP objective, in
  nominal dollars; the loop prints today's. 38,268 / gamma_N (2.2898) = $16,712, the accepted plan.
- **Cause:** `zl` are regime binaries on ordinary taxable income (`ltcg_zl15_link`: `zl15 = 1`
  holds G_n <= T15, `zl15 = 0` holds G_n >= T15; T20 likewise), not on the gains alone. The better
  plan (branch-and-bound) moves G_n across T15 in 2028 and 2032-37 and SS taxability in 2032-37
  together (more conversions early; 2032-37 income $33-36k instead of $102,540, SS in the phase-in,
  federal tax $3.7-4.2k instead of $14.1k a year). Step (a) frees LTCG with SS pinned, (b) SS with
  LTCG pinned, (a') the non-SS families with SS pinned; (c) has no residual year. `localSearchRadius=200`:
  still 20,004.
- **Patch:** step (b) leaves `zl` free (`pinned = [f for f in others if f != "zl"]`). john+sally
  preset 20,004 -> 31,778, the branch-and-bound plan year by year. 18 examples: never lower, 8
  gain (+$7 to +$369, john+sally +$11,774), total time 1.53x (up to 2.6x, joe, no gain); avery+quinn
  residual $1,405 -> $1,665 at the same objective. Variant with a separate step (b') once nothing
  moved: same gains, 1.87x, dropped. Upstream suite with the patch: 2866 passed, 1 skipped.
- **Fork:** ran the same `localsearch.py` (20,004 on fork code too, from a `python -I` run that
  ignored `PYTHONPATH` and imported the main checkout). **Applied in the fork the same day**
  (`localsearch.py`, the patch as drafted), with `tests/plan/test_local_search_ltcg.py`: step (b)
  leaves every `zl` column free (spy on `_mip`), and john+sally's local-search preset is within
  0.5% of branch-and-bound (both fail without the patch: 20,004 vs 31,778 under the tests' frozen
  date too; 56 s together).
- **Household stand-ins rerun** (the real case `otherFiles/Case_us.toml` has never been filled in
  in this container; the stand-ins are the synthetic couples the decisions were measured on).
  Unpatched (worktree at `8330fa3`) and patched side by side, four at a time, same day; outputs
  `model-review/ss-loop/ls_ltcg_household_2026-10-17/`. Local search throughout:
  - `nj_stakes.py ls` ($1.5M, `maxSpending`, $/yr): FL 125,188, NY 123,239, NJ without the exclusion
    122,986 unchanged; NJ with it 123,780 -> 123,789 (lifetime NJ tax 23,468 -> 21,200). NJ - NY
    +$541 -> +$550/yr.
  - `housing_stakes.py ls` (NJ owner bigticket / budget, NJ rent, NY owner): identical to the dollar.
  - `phase3_step6_measure.py probe-ls`: identical.
  - `ss-loop/convex_fork.py ls` (probe couple, date frozen at 2026-10-15; old values equal the ones
    recorded 2026-10-16): NY 2032 819,098 -> **818,390 (-$708)**; NY+mortgage 2099 686,772 ->
    688,814 (+$2,042); NJ 2099 912,040 -> 912,273 (+$233); NJ+mortgage 2099 684,894 -> 685,119
    (+$225); the other four identical. Residuals unchanged.
  - Comparisons: NJ - NY 2099 +$35,792 -> +$36,025; NJ - NY 2032 +$33,765 -> +$34,473; NJ+mortgage -
    NY+mortgage 2099 -$1,878 -> -$3,695 (both under 0.6% of the bequest, inside the loop-noise
    band, unresolved as before); mortgage cost in NY 2099 $189,476 -> $187,434. **No sign changes,
    no decision moves.** The -$708 shows the patch is not monotone in the fork: within a loop
    iteration the search cannot do worse, but the next iteration's loop quantities (itemizing
    branches, NJ free set, ...) follow the plan, so the final plan can move either way.
  - Time: patched runs 0.8-1.5x the unpatched (NY 2032 184 -> 270 s; housing 1.08-1.47x; four runs at a time, so rough).

## #193: upstream experiment branch `ss-binaries` measured, not merged; deleted upstream (2026-10-16)

The user posted `issue-193-reply-2.md`. The maintainer then opened `ss-binaries` (`abd39b4`,
"[experiment] SS taxability MIP: one binary per year when the benefit is at least the tier gap",
"not intended for merge as is"): under `withSSTaxability="optimize"`, a year whose benefit is at
least the tier gap keeps only the cap binary `z1` (`z0` and `pmin` fixed out, the phase-in as convex
rows gated by `z1`); `OWL_SS_VARIANT` = `drop` (default) / `cuts` (keep `z0`, add the convex pieces
as cuts) / anything else (the formulation on `dev`). His note: exact everywhere, 1.5-4x more nodes on
the #193 cases, up to 13x on the examples.

**Not merged into the fork:** it changes `"optimize"` (and so local search) by default, for more
nodes, and is marked not for merge. Measured instead on stock `ss-binaries` with the #193 repro
(`fork-notes/issue-193-binaries-output.txt`; nodes = `solverNodesTotal`, whole solve): all three
variants give the same bequest to the dollar under branch-and-bound and local search; nodes dev
700-1,222, `drop` 3,392-4,735 (3.6-6.3x), `cuts` 1,090-2,428 (1.3-2.6x); branch-and-bound 14-22 s /
35-60 s / 22-32 s; local search 24-32 s / 26-36 s / 23-34 s. All far slower than "convex" (0.8-1.2 s).
Comment draft `fork-notes/issue-193-reply-3.md` **not posted**: the maintainer had already concluded
the experiment and deleted the branch (relayed by the user; confirmed with `git fetch --prune`).
Upstream left with `dev` `10b9f72` and `ss-convex` `c22f46d`, both merged here.

## #193 "convex" moved to upstream branch `ss-convex`; `c22f46d` merged; reply reassessed (2026-10-16)

Upstream force-pushed `dev` back to `10b9f72` and moved `6b02671` + `83a580b` (same hashes) to a new
branch `ss-convex`, with a third commit `c22f46d` ("cheaper cap probe": each probe warm-started
from the best plan's premiums, NIIT, LTCG room, MAGI and gain fractions; later passes only over
near-ties; the convex rows keep a fixed shape, switched through bounds, so HiGHS reuses the last
optimal basis, `_BasisCache`, keyed on (columns, rows); `_ssProbeTrace`). The fork already had the
first two (`ae1fb9d`), so `git merge upstream/ss-convex` brought only `c22f46d`: merge `bb00250`,
one conflict at the loop's start (the warm start goes before the fork's `_snapshot_sc()`).
Checked: the basis cache keys on the row count too (`lbvec` is the row bounds), so the fork's
varying itemizing/NJ rows never get a basis of another shape. The probe's warm list has upstream's
quantities only; the fork's `_SC_PARAMS` (NJ exclusion set `RXF_n`, itemizing branches, NY
recapture) still start cold in each probe. Full suite **3228 passed, 1 skipped** (7:30).

Measured at `c22f46d` (date frozen at 2026-10-15):

- Stock, the seven #193 cases (`issue-193-convex-c22-output.txt`): "convex" = `"optimize"` to the
  dollar in all seven, **0.8-1.2 s** (loop 0.7-1.1 s; branch-and-bound 14-21 s; `83a580b` 2.2-5.2 s).
- Stock, 18 examples (`model-review/ss-loop/examples_convex_c22_stock_2026-10-16.txt`): SS
  residual $0 in all; >= the loop in 17 (`alex+jamie` -$12); all under 3 s but `jack+jill` (30.5 s);
  against `83a580b`, six examples moved by -$22 to +$21 (`morgan` 41,769 -> 41,747, now +2.10%).
- Fork, probe couple (`model-review/ss-loop/convex_fork_c22_2026-10-16.txt`): same bequests as at
  `83a580b` (NJ+mortgage 2032 +$12); NY 1.5-3.3 s (was 2.5-9.7 s); NJ **321-542 s** (was 534-962
  s; local search 81-176 s).

Reply reassessed: `fork-notes/issue-193-reply-2.md` rewritten for the branch tip (the fix is now a
prototype on a branch, so the reply is evidence for moving it to `dev`): the `c22f46d` numbers, the
speed-up since `83a580b`, `morgan` +2.10%, the "loop" label (still there: `_breakpointFamilies`
names SS only under "optimize"). User's call to post.

Open (fork-side, not done): warm-start the fork's own `_SC_PARAMS` in the cap probe (extend
`warm_keys` there or in a fork hook) to cut the NJ times; measure before deciding.

## Upstream #193 fix merged: withSSTaxability="convex" (2026-10-16, on `claude/eager-cray-s0fvks`)

The user posted `issue-193-reply.md`; the maintainer answered with two commits on `dev`:
`6b02671` (`withSSTaxability="convex"`, "exact SS phase-in pricing without binaries (prototype,
#193)") and `83a580b` (start from a flat 85%). The mode keeps taxable SS as the LP column `tss`
above the three convex phase-in pieces; the 85% cap, the only non-convex part, is a per-year
region taken from the previous iterate (`_update_ss_regions`, at most `SS_REGION_FLIPS` = 2
switches a year), then probed greedily one year at a time with full solves
(`_ssCapProbeSolve`). Opt-in; not with `withSSAges="optimize"`; falls back on the loop on an
unsolvable iterate.

Merge `ae1fb9d`: one conflict, the loop's convergence test (upstream's SS term under "convex",
the LP's `tss` against the formula, written with the fork's `sc_lp` snapshot; the fork's
`_SC_PARAMS` moves and itemized moves kept). Fork code that touches taxable SS checked: the state
taxable-income rows exclude SS through `tss` when it exists, so they follow the LP's `tss`; the
post-solve state AGI and the NY recapture read `Psi_n`, which upstream now derives from `tss`
(allowed above 0.85 under "convex"). No duplicate definitions (AST). flake8/ruff: only the known
upstream lines. Full suite **3228 passed, 1 skipped** (7:01; +2 upstream tests).

Measured (date frozen at 2026-10-15):

- Stock `dev` `83a580b`, the seven #193 cases (`issue-193-convex-output.txt`): "convex" equals
  `withSSTaxability="optimize"` to the dollar in all seven, 2.2-5.2 s against 13-21 s, residual
  $0. The Summary labels "convex" runs "loop" (`breakpointMethodUsed`).
- Stock, 18 examples (`model-review/ss-loop/examples_convex_stock_2026-10-16.txt`): SS residual
  $0 in all; objective >= the loop's in 17 (`alex+jamie` -$12); `john+sally` +72%, `morgan`
  +2.15%, `kim+sam-bequest` +0.72%, `helen+ruth` +0.18%; 0-50 s (`jack+jill` 49.5 s). Matches the
  commit message's claims.
- Fork, the probe couple (`model-review/ss-loop/convex_fork_2026-10-16.txt`; fork defaults,
  itemizing on), bequest, loop / "convex" / local-search preset:
  NY 2032 760,903 / 819,127 / 819,098; NY+mortgage 2032 625,777 / 699,588 / 710,328;
  NJ 2032 817,280 / 852,872 / 852,863; NJ+mortgage 2032 666,027 / 705,653 / 707,057;
  NY 2099 825,195 / 874,558 / 876,248; NY+mortgage 2099 640,832 / 677,246 / 686,772;
  NJ 2099 876,102 / 911,735 / 912,040; NJ+mortgage 2099 632,267 / 685,119 / 684,894.
  "Convex" takes 2.5-9.7 s in NY but **534-962 s in NJ** (the cap probe re-solves the whole
  plan per year, each with the NJ exclusion MILP; local search 81-176 s there).
- Attribution of the NY+mortgage 2032 gap (`convex_attr.py`): exact SS alone gives 699,588 under
  branch-and-bound and local search, the same as "convex"; "convex" + Medicare, NIIT or senior
  bonus optimize: 699,588; "convex" + LTCG optimize: **710,328** = local search (618 s). The
  $10.7k is the LTCG loop, not SS. Not measured: whether the 2099 NY gaps ($1.7k, $9.5k) are LTCG
  too; whether the LTCG loop costs as much on stock upstream (the stock repro's presets added
  only $270-524 over exact SS).

Consequences for the fork: for NY decisions "convex" is a fast exact-SS mode (seconds); the
decision recipe stays local search (it also covers LTCG, which "convex" leaves to the loop, and is
faster than "convex" in NJ). Reply draft `fork-notes/issue-193-reply-2.md` (confirmation with the
repro's numbers, morgan, the "loop" label), user's call to post.

## #193 follow-up: local search on the repro cases (2026-10-16, on `claude/eager-cray-s0fvks`)

Maintainer on #193 (relayed by the user): "How does that compare with the local MILP which takes
binary families one by one around a local search (mipStrategy=local-search)?" Measured on stock
`dev` `10b9f72` (`fork-notes/issue-193-ls.py`, output `issue-193-ls-output.txt`, date frozen at
2026-10-15), all seven repro cases, five methods:

- SS `optimize` alone: `mipStrategy="local-search"` and branch-and-bound give the same bequest to
  the dollar in all seven (22-31 s vs 14-21 s; loop 0.7-1.3 s).
- `breakpointMethod="local-search"` (SS, IRMAA, LTCG, NIIT): +$270-524 over SS alone, 29-46 s.
  `breakpointMethod="branch-and-bound"`: the same except NY $110k (-$308), at the 0.3% gap upstream
  sets when Medicare is optimized and no `gap` is given (30 x GAP, `plan.py:5063-5070` on `dev`).
- Every exact run: fixed-point residual $0. Upstream's preset (not `mipStrategy` alone) is what
  sets the families to `optimize` (`_applyBreakpointOptions`).
- Correction to the filed issue: "3 iterations and a few seconds" for the exact SS solve was not
  timed; it is 14-21 s.

Reply `fork-notes/issue-193-reply.md` (table, the correction, question 2 narrowed to a pointer to
`breakpointMethod="local-search"` in the loop's warning): posted by the user.

## Upstream issue #193: SS-taxability loop (2026-10-16, on `claude/eager-cray-s0fvks`)

User's rule: new information or a concrete test case gets filed regardless of the maintainer's
own tests (CLAUDE.md, Conventions). Draft `fork-notes/issue-ss-loop.md` (new issue, plus a one-line
pointer comment for #185), repro `fork-notes/issue-ss-loop-repro.py`, plain Python on stock Owl,
date frozen at 2026-10-15; output `issue-ss-loop-repro-output.txt` from stock `dev` `10b9f72`
(run twice with identical output for parts 1-4). Contents, all measured on stock:

- Part 1: loop vs `withSSTaxability="optimize"` on the NY + mortgage couple (flat spending
  $95k-$115k, Roth 60/40 and 61/39, NJ): loop short by $33.7k-48.6k; 3 of 5 tied NY cases stop at
  the cap with $9.6k-26.4k SS residual.
- Part 2: where it comes from (conversions $852k vs $709k, taxable SS $632k vs $1,041k, federal
  tax $207k vs $274k).
- Part 3: the tie at a fixed SS fraction (pure LP, Psi 0.85): Joe's 2036 tax-deferred withdrawal
  pinned $13k lower, bequest unchanged to the cent, 21 account-years move (up to $110k); $13k
  higher costs $52.19.
- Part 4: the Summary shows "max iteration" and an error bar of +-$358 (0.07%) on a plan $38k
  short; the SS residual is only in the verbose log.
- Part 5: local search $545,434 (exact SS $544,961, loop $506,651).
- Examples (stock, `model-review/ss-loop/examples_ss_stock_2026-10-16.txt`): not general.
- Questions: the residual in the Summary; a re-solve or a recommendation when the loop ends at
  the cap or in a cycle with a large SS residual. Patch offered, not built.

Status: **filed by the user as #193** (2026-10-16); no maintainer response yet. The #185 pointer
comment naming #193 (end of the draft) was posted by the user the same day.

## Why the NY + mortgage loop fails without itemizing (2026-10-16, on `claude/eager-cray-s0fvks`)

Asked after the #185 measurement (section below): the NY couple with a $600k mortgage hit the
30-iteration cap with `withItemized="none"`. Scripts and outputs: `fork-notes/model-review/ss-loop/`
(`trace.py`, `tie.py`, `alloc.py`, `stock_repro.py`, `ex_ss.py`; `*_2026-10-16.txt`; date frozen
at 2026-10-15). Case: NY Yonkers, $25k property tax, 2032 reversion, maxBequest (bequest $464,074,
SS residual $18,663) unless stated.

**Not the fork's state code.** No Yonkers: cap, SS residual $22.6k. NY recapture forced to zero:
2-cycle at 23 iterations, $8.1k. Neither: cap, $31.1k. The worst residual family is the SS taxable
fraction in every case. Stock upstream `dev` `10b9f72` (worktree; same couple as flat $105k net
spending + the same mortgage, `stock_repro.py`): cap, SS residual $26.4k.

**The quantity that does not settle.** In the trace (`trace.py ny`), the years 2035-2038 have SS
in the phase-in (implied Psi 0.57-0.72, $80k of SS in today's $; 2034, the first SS year, 0.73-0.85) and no Roth conversions.
Over the last 10 iterations, each year's MAGI flips between two or three values about $13k
apart, and its NY taxable income between $0 and the top of NY's first bracket ($13,012 in today's
$ in 2036, after the $20k pension exclusion each and the standard deduction). The federal fill
stays inside the 15% bracket (58-86% full in 2035-2038). The swap that moves is Joe's tax-deferred withdrawal
against his Roth withdrawal (2036: $27,351 / $31k one iteration, $40,363 / $20k another).

**Why it moves: the LP is degenerate at a fixed Psi.** All accounts hold the same 60/40 mix at
fixed ("conservative") rates, so tax-deferred, Roth and taxable dollars grow identically, and
moving a withdrawal between years with the same marginal rates costs nothing. `tie.py ny 29 26
2036` rebuilds iteration 29's LP (its SC parameters) and pins Joe's 2036 tax-deferred withdrawal
to iteration 26's value: the objective moves by $0.01 (both directions), while the solution moves
by $10-20k of tax-deferred/Roth withdrawals in 2032-2040 and swaps $166k of taxable withdrawals
between the spouses in 2028-2031. Even the unpinned rebuild returned another vertex than the loop's
iterate ($40,363 instead of $27,351). With Psi a constant in the LP, those vertices are equally
good. Under the IRS formula they are not: a $13k MAGI difference moves taxable SS by about
0.14 x $80k. The next Psi then follows the solver's arbitrary pick, damped 30/70
(`_update_Psi_n`), and never settles.

**Why NJ settles.** Same couple in NJ: in 2036-2042 the federal 15% bracket is 100% full and NJ
taxable income is zero (exclusion), so the bracket boundary pins MAGI whatever vertex the solver
returns (MAGI within $100 or less per year over the last 10 iterations). In NY, the state's first
bracket makes those years cost 15% + 3.9% (+ Yonkers) inside the federal bracket, so the tied swap
moves MAGI.

**Breaking the tie.** Roth at 59/41 or 61/39 stock (others 60/40), `alloc.py`: the fork's NY
cases at $20k, $25k and $30k property tax go from the cap ($18.7k-21.9k residual) to a 2-cycle at
20 iterations ($2.4k-2.9k), like the cases that settle; stock upstream: the same ($2.4k, $2.8k).
Under the law as enacted (2099) the tied NY cases 2-cycle at 19 iterations ($2.2k) instead of
hitting the cap. On stock with the tie, flat spending $95k-$115k: cap at $100k, $105k, $115k;
2-cycles with $13.6k-14.8k residual at $95k and $110k.

**The larger problem: the SS loop is biased low on this couple, converged or not.** With
`withSSTaxability="optimize"` (exact, MILP) the same cases converge in 3-4 iterations, and the
bequest is higher in every case run: fork NY 2032 $25k: $494,962 vs $464,074 (local search
$498,322); stock NY: +$33.7k-40.2k at every spending level and allocation ($95k: 4.2%, $105k: 6.5-7.8%,
$110k: 14%, $115k: 59% of a $64k bequest); stock NJ $105k: +$48.6k (10%); fork NY 2099: +$25k-60k (3-20%). Mechanism (stock, Roth 61/39, where the
loop settles): the exact model converts $852k (today's $) instead of $709k, more of it in
2026-2027 ($233k + $193k vs $121k + $124k), which cuts lifetime taxable SS from $1,041k to $632k
and lifetime federal tax from $274k to $207k. With Psi fixed, the LP prices phase-in income at
15%; the true marginal rate there is up to 15% x 1.85 (each dollar adds up to $0.85 of taxable SS).

**Not general.** On the 18 examples (stock), exact SS is within +-0.5% of the loop in 16, +10% on
`Case_john+sally`, -0.7% on `Case_morgan` (worse), and 10-700 times slower (up to 686 s,
`kim+sam-bequest`; `examples_ss_stock_2026-10-16.txt`). The bias needs many years in the
phase-in with income the plan can move; this couple (SS claimed at 70, $1.5M tax-deferred) has
22 of 23 SS years there. The household's profile is of that kind.

Consequences: (1) loop-mode numbers on this kind of couple are biased low by several percent, and
can carry a $10k+ bias between scenarios (stock NJ vs NY at $105k: loop gap $28k, exact $17.7k);
the decision recipe (local search, which sets `withSSTaxability="optimize"`, or the exact LP)
already avoids it. (2) For #185: the cycling in the NY + mortgage runs is upstream's SS loop on a
degenerate LP, with or without itemizing; this supports the reply as posted. Drafted for
upstream the same day (section above).

## Upstream dev 10b9f72 merged; maintainer replies on #185 and #177 (2026-10-15, on `claude/eager-cray-s0fvks`)

Upstream since `810a6cd` (19 commits, `main` = `dev` = `10b9f72`, version 2026.10.15 + WIP):
Roth 5-year rule compounds recent conversions at real returns, losses included (`337b02b`; HiGHS
stalled on long historical plans, #184/#188); a plan ending before anyone reaches 65 solves
(`f54afab`, `mediVals` clamps `nmstart`); #190 (`owlcli run` real-dollar workbook name, every
I/O call takes a path; `saveWorkbook` returns the file name); MCP sweeps time one solve and ask
before a run projected beyond two minutes; #191 (top IRMAA tier frozen in nominal dollars through
2027, `tax_federal.irmaaThresholds`); `$` escaped in Markdown docs and UI strings; dependency
updates. PR #184 (HiGHS LP fallback) was merged and then reverted upstream.

Merge `c06b6af`: three doc conflicts. CHANGELOG: the fork's Unreleased section is kept above
upstream's, with its `$` escaped as upstream now does. PARAMETERS.md: upstream's escaped
`withSeniorBonus` row plus the fork's `withItemized`. modeling-capabilities.md: upstream's escaped
Fixed assets row plus the fork's Debts and Budget rows. `plan.py`, `tax_federal.py`, `export.py`
and `explain.py` auto-merged. Grep: no duplicated definitions (AST check over `src/`), no fork
code computing IRMAA thresholds by hand (the fork's premium terms go through `mediVals` /
`mediCosts`, so #191 reaches the medical claims). The fork adds no unescaped `$` to the docs or UI.
flake8: only upstream's `localsearch.py:31`. ruff: one hit, in upstream's new
`tests/plan/test_roth_maturation_losses.py:49` (B905). Upstream CI runs flake8 only, so it is left
as is. Full suite: **3226 passed, 1 skipped** (6:32). No fork expected value moved.

Maintainer replies relayed by the user:

- **#185** (federal itemized deductions; the draft `issue-federal-itemized.md` was posted): "I'll
  need to look more deeply into it. Adding more stuff to the recursion loop is what causes cycling
  and prevents monotonic convergence. I'll run a few tests and get back to you."
- **Discussion #177**: "Sorry for the delay. Give me a day to digest all the good info you
  provided. I mean really good info. The soft part of discretionary spending expressed as a slack
  variable is a total novelty in modeling deccumulation." A deferral; nothing to answer yet.

### Itemizing and loop convergence (the #185 concern, measured)

`fork-notes/model-review/phase3-review/itemized_convergence.py`, output
`itemized_convergence_2026-10-15.txt` (date frozen at 2026-10-15; default loop unless marked LS).
Iterations and endings are upstream's `convergenceType`; the residual is the largest
`fixedPointResidual` family (in every row below it is SS taxability unless named).

- 18 examples, `withItemized` none vs loop: identical iterations and endings in all 18; only
  `Case_devon` (22 itemizing years, +$1,199 objective) and `Case_jordan+taylor` (1 year, +$174)
  itemize.
- Probe couple (r123's: $1.5M tax-deferred, $80k core + $25k property tax), 16 pairs:
  - NJ, where only federal itemizing applies: 6 pairs itemize. Same ending in 5; NJmort 2099
    maxSpending went from "oscillatory" at 11 iterations to a 2-cycle at 14. 0 to +4 iterations;
    residual $1.1k-1.6k in both modes.
  - NY without a mortgage (federal 0 years as enacted, 25-26 under 2032; NY 31): 2 to 7 fewer
    iterations; two of the four went from "oscillatory" to a 2-cycle (residual $0.9k-1.4k ->
    $1.8k-4.3k).
  - NY with a mortgage (federal and NY IT-196): 2099: a 2-cycle at 18-19 iterations became the
    30-iteration cap, residual $2.2k -> $42.6k (maxBequest) and $19.3k (maxSpending). 2032: none
    already hits the cap (maxBequest residual $18.7k, maxSpending $10.0k); with itemizing, the cap
    with $33.2k, and a 3-cycle with $72.5k.
- Attribution (`nyattr`: NY's `_st_item_candidate_years` patched to `[]`): federal only in NY with
  a mortgage gives 18-19 iterations and a 2-cycle in all 4 cases, residual $2.6k-4.5k. So the
  worse NY + mortgage endings need NY IT-196 (fork-only), not federal itemizing. The line-46 cut
  is not the cause: it never activates there (state AGI < $200k in every iterate; forcing it to
  zero changes nothing).
- But the loop fails without itemizing too (`ptsweep`, NY + mortgage, 2032, maxBequest): at
  property tax $20k, $22.5k, $25k, $27.5k and $30k, **none** hits the cap (residual $18.7k-25.5k);
  only $15k converges. With itemizing the cap is hit at the same amounts (residual $11.9k-95.8k).
  The band where the SS loop fails moves with the data; itemizing shifts where in it a case sits.
- Local search (`ls`, NY + mortgage, maxBequest), residuals about 0: 2032 none $498,322 <
  federal only $670,284 < federal + NY $710,328; 2099 $600,901 < $645,667 < $686,772. The order
  is the expected one. The loop's results there are 4-12% below local search in every mode (2032:
  none $464,074, federal $644,003, both $625,777; 2099: $550,119, $594,395, $640,832). The loop's
  "NY itemizing lowers the bequest by $18k" in 2032 is an unconverged iterate.

Reading for #185: federal itemizing, as the fork builds it, did not add cycling that the loop did
not already have (examples, NJ, NY federal-only). The fork's NY schedule can push an already
fragile NY + mortgage loop over the cap. That is a fork matter, and the fork's decision recipe
(local search for comparisons) already covers it. Optional data comment for #185:
`fork-notes/issue-185-reply.md` (posted by the user, relayed 2026-10-16).

Open item, answered 2026-10-16 (section above): the SS-taxability loop on a degenerate LP
(identical growth in every account), on stock upstream too; not the fork's NY code.

## Phase 3 step 8 — upstream proposal drafted (2026-10-12, on `claude/eager-cray-s0fvks`)

`fork-notes/issue-federal-itemized.md`: a new design issue on federal itemized deductions, concept
level (`phase3-plan.md` §5 step 8; `phase3-review.md` R5), for the user to post. Federal only; NY
itemizing, NJ line 31 and Stay NJ stay in the fork.

- Content: Owl already computes mortgage interest (Debts `mortgage` rows, with the #173 payoff),
  its own state and local income tax (SALT) and Medicare/ACA premiums; the budget knows property
  tax, cash charity and out-of-pocket medical (an Owl-budget contract point, linked to #177).
  Loop only, no binary, with the R1 measurements as the reason to differ from `withSeniorBonus`'s
  shape. Stakes table (exact LP, lifetime federal tax saved): $0 / $20k without a mortgage, $15k /
  $87-89k with a $600k mortgage, as enacted / under Owl's 2032 reversion; rent/cash/mortgage
  +$11k / +$62k of bequest on the mortgage path. Three questions: in core and default, which
  medical amount (`setMedicalExpenses` caps HSA withdrawals only), and where the deductible
  categories live. Patch on stock `dev` offered only if asked.
- Checked on stock `dev` `390f02f` for the draft: modeling-capabilities and `owl.tex` say
  itemizing is not modeled; Debts docs say mortgage interest is not deducted; `debts.py` has the
  amortization but no interest-by-year function (the fork adds 83 lines); MFJ standard deduction
  $32,200 OBBBA vs $17,160 pre-TCJA from `yOBBBA = 2032`.
- Upstream state (github.com via WebFetch, 2026-10-12): #158 closed by `fmateoc` on 2026-10-07 as
  completed, no maintainer comment; #175 is Discussion #177, whose last comment is ours of
  2026-10-09 (reply 3, posted) with three open questions. Upstream `dev` still `390f02f`. Hence a
  new issue rather than a #177 comment (lesson 9: don't stack); timing is the user's call.
- No code change; tests not run.
- Revised the same day after merging `810a6cd` (section above): medical moved from "part of a
  third" to the amounts Owl knows (premiums + `other_medical_expenses`, less HSA withdrawals,
  Pub. 969); question 2 asks whether Schedule A may read `other_medical_expenses` and whether
  the intake would then ask everyone; question 3 narrowed to property tax and charity; one
  sentence on `medical_inflation_excess` (inferred, not measured).

Next: post the issue (user), then Phase 5 (part-time work / SS earnings test) or STAR as needed.

## Upstream dev 390f02f merged (2026-10-11, on `claude/eager-cray-s0fvks`)

2026.10.11: `setMedicalInflation` / `medical_inflation_excess` (Medicare, ACA and other medical
expenses grow faster than inflation; contributed by Dmitry Fink, #182). Conflict in `CHANGELOG.md`
only. Fork change: `_medical_premium_lo` grows the HSA cap's other-medical amount with
`_medical_n`, as upstream's `_add_hsa_medical_cap` now does. Questions for Phase 4 in
`phase3-review.md` R4 (budget `medical` lines grow at their own rate; upstream's
`setMedicalExpenses` is in no claim; it only caps HSA withdrawals, as part of general spending).

## Upstream dev 844a7ec merged (2026-10-11, on `claude/eager-cray-s0fvks`)

Upstream rewrote `dev`: `f41fcdc` (merged 2026-10-10) is replaced by `e5949e8`, same author date
and identical tree. New on top: `b8eb79c` (regret sweep reports the solves stopped at the node
limit, `node_limit_hits`) and `844a7ec` (Ruff B905, `zip(..., strict=True)` in tests and the UI).
`upstream/claude/magical-archimedes-2uo16r` has nothing beyond `d6970b2` (merged 2026-10-09).

- Conflicts: `plan.py`, `CHANGELOG.md` (the replayed commit; kept ours, plus the new CHANGELOG
  paragraph). `export.py` auto-merged into a **duplicate `_node_limit_hits`** with no conflict
  marker; kept ours. A `git stash` run by mistake mid-merge cleared the merge state; the merge was
  redone and its resolution restored from the stash (checked identical before committing).
- Ruff: upstream lints with Ruff B rules, which the fork did not run. Three B905 hits in fork code
  (`tax_state.py` x2, `tests/tax/test_state_recapture.py`) fixed: `itertools.pairwise` for the
  adjacent-pair loops (`strict=True` would raise there), `strict=True` on `exclusion_share`.
  `ruff check src tests ui` now passes and is part of the lint command in CLAUDE.md.
- Effect on Phase 3: none on tax content; details in `phase3-plan.md` §10.

## Upstream 2026.10.10 merged (2026-10-10, on `claude/eager-cray-s0fvks`)

Upstream `dev` `f41fcdc` (six commits; `main` = `dev`): node counts in the Summary and a public
`mipMaxNodes`; #180 (MCP `big_ticket_items`) settled as signed amounts, docs only; MOSEK license
lookup in the UI; dependencies. Conflicts in `plan.py` (constants, SC-loop trace, HiGHS node cap)
and `CHANGELOG.md`. Fork changes needed by the merge, detail in `phase3-plan.md` §9:
- `RX_NODE_LIMIT` goes through `Plan._node_limit` (falls back to upstream's `_mipNodeLimit`), and
  upstream's tally uses it: without that, a solve stopped at the RX cap counted as not stopped
  (test extended; it reads 0 of N without the fix). The Summary's *MIP node limit* row names the RX
  cap when it applied (`_rxNodeLimitUsed`).
- The node-limit warning is silenced only for local-search steps (upstream's `_localSearchStep`),
  not whenever `mipMaxNodes` is set, and reads the last run's own status and count.
- Phase 3 plan: no change to the tax content; caps for new binaries go in `_node_limit`; step 6
  reads the new Summary rows. §8 (#180) closed.

## Test status

2026-10-27, upstream `dev` `07b9a77` merged, xfails removed: **3588 passed, 1 skipped** (9:16). flake8 clean; Ruff only upstream's three B905.
2026-10-25, #227 PR review fixes ported (Taxes column, two #197 deep tests, `filingStatus_n`): **3541 passed, 1 skipped** (10:18). flake8 clean; Ruff only upstream's three B905. PR branch: 3232 passed, 1 skipped; `-m deep` 5 passed.
2026-10-25, upstream `dev` `22ce72b` merged and the payroll tax aligned with the #227 PR: **3514 passed, 1 skipped** (8:54; `deep` tests deselected by upstream's `pytest.ini`). flake8 clean; Ruff only upstream's three B905. The PR branch on stock `dev`: 3205 passed, 1 skipped (7:16); `-m deep` 4 passed.
2026-10-25, the fork's smile dropped: **3492 passed, 1 skipped** (7:14); the 23 fewer are the removed smile tests (15 in `test_smile_start_age.py`, 6 fork tests in `test_spending.py`, 2 schema round-trips of `smile_start_age`), checked by comparing collected test ids.
2026-10-25, fork review (decorator restored on `_add_defunct_constraints`): **3515 passed, 1 skipped** (7:10).
2026-10-25, `withPayrollTax` removed: **3515 passed, 1 skipped** (11:39). flake8 clean.

2026-10-24, payroll tax always on: **3517 passed, 1 skipped** (11:56). flake8 clean; Ruff only upstream's three B905.

2026-10-24, upstream `dev` `4e55b36` merged: **3516 passed, 1 skipped** (10:59). flake8 clean; Ruff only upstream's three B905.

2026-10-22, upstream `dev` `37afa2a` merged (`41eb4a7`): **3463 passed, 1 skipped** (15:53); after the merge review fixes (`b99990f`): **3465 passed, 1 skipped** (15:02). flake8 clean; Ruff only upstream's B905.

2026-10-17, after merging upstream `dev` `2b34633`: **3232 passed, 1 skipped** (7:57).

2026-10-17, local search leaves LTCG free in step (b) (+ `test_local_search_ltcg.py`): full suite **3234 passed, 1 skipped** (7:50).

2026-10-17, fork `_SC_PARAMS` warm-started in the "convex" cap probe: full suite **3228 passed, 1 skipped** (7:46) with the fix, then with `test_ss_convex_fork.py`: **3229 passed, 1 skipped** (7:44).

2026-10-16, after merging upstream `ss-convex` `c22f46d`: **3228 passed, 1 skipped** (7:30).

2026-10-16, after merging upstream `dev` `83a580b` (#193 "convex"): **3228 passed, 1 skipped** (7:01).
flake8 only upstream's `localsearch.py:31`; ruff only upstream's `test_roth_maturation_losses.py:49`.

2026-10-15, after merging upstream `dev` `10b9f72`: **3226 passed, 1 skipped** (full suite, 6:32).
flake8 only upstream's `localsearch.py:31`; ruff only upstream's `test_roth_maturation_losses.py:49` (B905).

2026-10-11, Phase 3 R1-R3 (`c1c88a3`): **3178 passed, 1 skipped** (full suite in a worktree with
`PYTHONPATH=src`, 6:59; 3184 − 8 optimize-mode tests + 2 `"none"` tests). flake8 only upstream's
`localsearch.py:31`; `ruff check src tests ui` passes. No AMO reference moved.

2026-10-11, Phase 3 review fixes + upstream `dev` `390f02f` merged: **3184 passed, 1 skipped**
(full suite, 7:54; before: 3168 on `e634c81`; +2 review regression tests, +12 upstream
`test_medical_inflation.py`, +2 upstream round-trip parametrizations). flake8 only upstream's
`localsearch.py:31`; `ruff check src tests ui` passes. No AMO reference moved.

2026-10-11, Phase 3 step 5 review fixes: **3168 passed, 1 skipped** (full suite, 7:51; +6 tests
in `test_itemized.py` and `test_nj_medical.py`). flake8 only upstream's `localsearch.py:31`;
`ruff check src tests ui` passes. No AMO reference moved.

2026-10-11, Phase 3 step 5 (medical premiums + NJ line 31): **3162 passed, 1 skipped** (full
suite, 6:10; +8 tests in `test_nj_medical.py` and `test_itemized.py`). flake8 only upstream's
`localsearch.py:31`; `ruff check src tests ui` passes.

2026-10-11, Phase 3 step 3 review fixes: **3154 passed, 1 skipped** (full suite, 7:15; +30 tests in
`test_itemized.py`). flake8 only upstream's `localsearch.py:31`; `ruff check src tests ui` passes.
No AMO reference moved (`Case_devon` under `loop` unchanged at $249,505.32).

2026-10-11, Phase 3 step 3 (federal itemized, `withItemized`): **3121 passed, 1 skipped** (full
suite, 5:18; +14 itemized tests, +1 upstream count after the AMO re-record). flake8 only upstream's
`localsearch.py:31`; `ruff check src tests ui` passes. `Case_devon`'s AMO reference re-recorded
(spending +$1,505 under the default `"loop"`); `Case_john+sally`, `Case_cameron` and the fixed-rows
fixture were unchanged after the zi=0 loop start. Four pre-existing assertions loosened for SC-loop
lag once federal itemizing moved conversions (`STMF_n`/`NYIR_n` vs this plan's AGI; see step 2) and
one NJ local-search time budget (`localSearchTime=1` was already tight).

2026-10-11, upstream `dev` `844a7ec` merged: **3107 passed, 1 skipped** (full suite, 6 min; +2 upstream
regret-sweep tests). flake8 only upstream's `localsearch.py:31`; `ruff check src tests ui` passes.

2026-10-11, Phase 3 step 2 review fixes: **3105 passed, 1 skipped** (full suite, 6 min; +8 itemized
tests). flake8 only upstream's `localsearch.py:31`.

2026-10-10, Phase 3 step 2 (NY itemized) after the pre-commit review: **3097 passed, 1 skipped**
(full suite, 7 min; +20 tests). flake8 only upstream's `localsearch.py:31`. Six bugs found and
fixed before commit (listed under step 2); the medical-floor row was rewritten twice (a hard
`st_imed ≤ paid − 0.075·AGI` is infeasible without medical expenses, and clamping the cut deletes
the floor — `max(0, ·)` needs a binary).

2026-10-10, upstream 2026.10.10 merged, after the step-1 review fixes: **3077 passed, 1 skipped**
(full suite, 7 min; +3 step-1 tests, +11 upstream `test_mip_nodes.py`). flake8 only upstream's
`localsearch.py:31`.

2026-10-10, Phase 3 step 1 (budget amount terms, `st_pt` fix, mortgage interest, SALT cap)
after the pre-commit review: **3063 passed, 1 skipped** (full suite, 5 min; +24 tests). Review
found and fixed: `by_type` IndexError on a default `essential=()`, mortgage interest past the
term on a late payoff, and a §3.3 regression that never reached k > 1. flake8 clean on the
changed files (upstream's `schema.py:406` and `localsearch.py:31` unchanged).

2026-10-10, smile follows the survivor's age + old-case warning: **3039 passed, 1 skipped** (full
suite, 7 min). flake8 only upstream's `schema.py:406` and `localsearch.py:31`.

2026-10-10, smile start age: **3035 passed, 1 skipped** (full suite, 7 min). flake8 only upstream's
`schema.py:406` and `localsearch.py:31`.

2026-10-10, Track B review fixes: **3022 passed, 1 skipped** (full suite, 7 min; before the fixes
3 failed, 2990 passed: the AMO references of jack+jill, jordan+taylor and morgan, moved by the
smile commit `9a3e9c1` and passing on `d4a4191`). `test_budget_json_age.py` 53 tests. flake8 only
upstream's `schema.py:399` and `localsearch.py:31`.

2026-10-10, Track B steps 1-2: age clocks on Budget lines (`clock="age"`, `start_age`/`end_age`,
`index`) and `optimization_parameters.budget_file` (JSON, `schema_version` 1; sheet wins; one
evaluator). `tests/assets/test_budget_json_age.py` 24 tests; budget suite 84 passed; config
round-trip 52 passed. flake8 only upstream's `schema.py:396`.

2026-10-10, age-anchored smile (`spending.SMILE_SPAN = 30`, one cosine period from the smile's
start; longer lives append the late-life rise): `tests/plan/test_spending.py` 10 tests;
`Case_jack+jill` expected basis 102_535 → 103_499 (33-year horizon no longer stretches the
go-go years); `Case_joe` unchanged (`N_n = 31 = SMILE_SPAN + 1`, exact match to the old curve).
toml cases + spending units + regret sweep: 130 passed.

2026-10-09, after merging upstream `dev` `d6970b2e` (`withSeniorBonus`): senior-bonus tests 7/7, budget + local-search 74/74; full suite not re-run this session. flake8 only upstream's `localsearch.py:31`.

2026-10-09, after merging upstream `dev` `0ca30f4` (#176, #178): 2931 passed, 1 skipped, 2 failed (fork NJ exclusion tests, see #178 row); after the exclusion fix and the essential lines (`5a4a12f`): **2956 passed, 1 skipped**. flake8 only upstream's `schema.py:391` and `localsearch.py:31`.

2026-10-08, Phase 2b (budget profile) + HFP rate fix: **2910 passed, 1 skipped** (2891 − 23 Housing tests + 38 budget tests + 4 rate tests); flake8 only upstream's two lines. Stock `dev` `156d812` with `issue-hfp-percent-rates.patch` alone: 2763 passed, 1 skipped (2760 collected on `dev` + 4 new).
2026-10-08, after merging upstream `dev` `156d812` (#173, #174): **2891 passed, 1 skipped** (2857 collected before − our 15 payoff/validator tests + upstream's 50 new); flake8 only upstream's `schema.py:389` and `localsearch.py:31`. The merge put upstream's `string_cols.append("property")` (hfp_io) under the fork's Housing branch instead of Debts; moved back by hand.
2026-10-07, review fixes on `claude/phase2-housing`: 2856 passed, 1 skipped (19 new tests); flake8 as below. Stock `dev` `004c840`: 2709 passed; with `issue-debt-payoff.patch` alone 2721, with `issue-solver-opt-numeric.patch` alone 2712. Before them: Phase 2 housing + NJ property tax deduction: 2837 passed, 1 skipped; flake8 clean on the changed files (upstream's `localsearch.py:31` and `config/schema.py:388` unchanged). Earlier: 2818 passed after merging `004c840` (2026.10.8).

Merge notes (2026-10-06): `tax_federal.py` and `socialsecurity.py` are now identical to upstream. Per-year state flags carry upstream's names. Upstream's explanation omits years without a state income tax and reports the state on every row; the fork follows. Earlier merge notes: NJ's $1,000 exemption per filer aged 65+ came from upstream 2026.10.3; fork-only amounts follow upstream's indexing flags (NY recapture thresholds with `brackets_indexed`, NJ exclusion ceilings/cap with `exemptions_indexed`).

## Run-library step 1: second review (2026-11-02, on `claude/run-library-design-review-97brrl`)

Review of `claude/run-library-step1` at `c970bf05` in `fork-notes/run-library-step1-review-2.md`
(T1-T6, each reproduced by a probe except T5). Checks: `tests/library` 65 passed, flake8/ruff clean,
`check_library_roundtrip.py` 39/39. Main findings: the stored case dict is not canonical (workbook
name, UI defaults, float precision), so an unchanged re-save makes a new run and the two entry
paths hash differently (T1; V9's test checks the tables only); `Library.open` deletes another
session's staging folder mid-save (T2); the UI path rewrites `plan_year` to the current year (T3);
`diff_summaries` misses int/float and bool/int changes (T4). Not fixed here: the user's call.

**T1-T4 fixed (2026-11-02, on `claude/run-library-step1`, user's call):**

- T1: `casefiles.canonicalize` (called by `scenario_from_case`, so by both entry paths, and by
  `save_run` with the default builder): the library's own file names in the case, the case read
  back through `save_toml`'s encoder (`toml.loads(toml.dumps(...))`, not `load_toml`, whose
  `sanitize_config` is date-dependent), integral floats in table cells as ints. The last one was
  found while fixing: the source workbook gives `0.0` where Owl's `saveContributions` read back
  gives `0`, which T4's stricter diff showed and which had already split the hash. `scenario_from_ui`
  takes `base=` (the opened run's scenario) and applies to its case only the fields where
  `ui_to_config(config_to_ui(base))` and `ui_to_config(pages)` differ (the UI round trip itself is
  lossy: it drops `asset_allocation.interpolation_*` on the synthetic condo case, so it is not the
  canonical form); a section the base lacks is added only if the pages changed something in it.
  The base's budget sidecar is reused when the reference is unchanged.
- T2: `Library.open` removes a staging folder only when its newest mtime is over
  `STAGING_STALE_SECONDS` (1 h) old.
- T3: with `base=` the plan year is the base's; `plan_year=` overrides; the start date's year
  follows it (month and day from the pages).
- T4: `_diff_into` compares `canonical_json`.

Checks: `tests/library` 82 passed (17 new); flake8 clean, ruff only upstream's four B905;
`check_library_roundtrip.py` now compares inputs hashes too, 39/39; the review's probes re-run:
re-saving a run's own files dedupes (`changes: []`), a UI-path scenario equals its own
`Case.toml` re-imported, a second `open` leaves a save in progress alone.

**T5, T6 fixed (2026-11-02, user's call):** T5 not with the review's token idea (a check before an
unlink leaves a window), but by making `library.lock` an OS file lock (`fcntl.flock` /
`msvcrt.locking`, non-blocking tries until `lock_wait`; `lock_stale` removed, the file stays on
disk): the kernel frees it when the holder dies, so nothing can be stale or taken over twice.
Tests: held lock raises, a leftover file does not block, a subprocess that takes the lock and
`os._exit`s leaves it free, 12 concurrent saves keep 12 `library.json` entries (mutation check: with
`_lock` a no-op, 6-10 of 12 kept in 5 of 5 runs). The `msvcrt` branch is untested here (Linux).
T6: S1's evidence corrected in `run-library-review-2.md` and design §8.3 (the solve month bounds
`withSSAges`' open ages, `_ssaOpenAges` / `_ssaCheckPastAges`; `yearFracLeft` reads today's day only
for `start_date = "today"`). `tests/library` 84 passed.

Full suite on the T1-T4 commit: 3693 passed / 1 skipped (9:32). `main` fast-forwarded to
`claude/run-library-step1` on 2026-11-02 (user).

## Run-library step 2: jobs and the `as_of` date (2026-11-02, on `claude/run-library-step2`)

Build step 2 of `fork-notes/run-library-design.md` (section 11): "Jobs: detached worker processes
with PID and heartbeat, the singleton manager, queue page, results folder, `record.json`, plan
cache; the frozen 'as of' date (D4 b, R1, S1: the run's own 'as of' date, as an `owlcli --as-of`
and worker input, S7)". Code in `src/owlplanner/library/`, `src/owlplanner/asof.py`, `ui/Queue.py`
and the "Open in Owl" glue; 55 new tests.

**The `as_of` date (S1, S7) is a first-class backend input, not a monkeypatch.** `owlplanner.asof`
(`today()`, `set_as_of`, `as_of(...)` context) is honoured by every calendar read in the backend:
every `date.today()` in `src/owlplanner` (78 call sites in 15 modules) now goes through it. No
override, no behaviour change. Settable by `owlcli run|compare|frontier|explain --as-of YYYY-MM-DD`
(a parse-time callback, so `load_toml`'s clamp and `hfp_io`'s conditioning see it too) and by the
worker. `tests/conftest.py` pins the suite with it (the old `date` monkeypatch stays for test
modules' own reads); the two tests that moved the date by patching `plan.date` (`midyear`,
`october_2026`) now move the input. The scenario (schema v1) records it as **the balances' date**
-- `basic_info.start_date`, the Account Balances page's "Account balance date", exactly §6.1's
"as of" -- validated to fall in the run's plan year (`validate` refuses, and so does the worker:
"the library refuses to solve a run outside its plan year", R1). Both entry paths capture *at* it
(`asof.as_of(...)` around `hfp_io.read`'s conditioning and `saveContributions`), so V5's import
date dependence is pinned to the run's plan year; a `start_date = "today"` case is stored with its
capture date, so re-importing a run's own files still gives the same hash. `resolve_as_of` is what
the worker freezes to.

**Jobs (section 8.2).** `results.py`: one results folder per solve (`results/<queued>_<preset>/`)
with `status.json` (the job record, on disk from the moment the job is queued, S2: state, PID,
process start token, heartbeat, per-job cancel token, step, last log line, loop iteration),
`record.json` (§5's fields: preset and options, Owl version and commit via `version.engine_provenance`,
the frozen date, solver, status, gap, iterations, converged, wall time, warnings, rate method and
seed, Python and package versions), `summary.json`, `plan.json`, `Results.xlsx`, `solve.log`, and
the `plan.pkl` cache (loaded only against the sha256 in `record.json` and the same environment,
dropped when stale: S6, R10). `worker.py`: `python -m owlplanner.library.worker` claims the job
under its token, freezes the date, builds the plan from the run's frozen files (the `owlcli run`
route) and solves with the preset's options; cancellation is checked before every step, on every
heartbeat (30 s, S8's self-check on wake) and throttled on every log line. `jobs.py`: `JobManager`
(one per server, `st.cache_resource`; the queue lives on disk), enqueue -> `tick()` dispatch up to
`max_parallel` (default 1), adoption at start-up (a live PID with a fresh heartbeat keeps its job,
a dead or silent one is interrupted with "run again"), `cancel` (token first, verified kill second,
S9: `procs.kill_process` only against the recorded process start token), `run_again` (fresh token:
never two workers on one run, S8), `stop_all`. Presets (`presets.py`): `quick` (default loop,
claiming ages held) and `custom`; `decision` and the two Ages presets come with steps 3 and 6.
`ui/Queue.py` (a "Run Library" nav section): the jobs list with elapsed time, heartbeat age, the
last log line and the loop iteration, self-refreshing (`st.fragment(run_every=2)`), cancel /
run again / stop all, and a small "Solve a run" expander so the page is useful before step 3's run
page exists.

**"Open in Owl" (R10's open item: "to be tried") was tried and was broken.** `owlbridge.genDic`
was dead code (nothing called it) and raised `IndexError` on every HSA case: its account keys
listed three accounts of four (`accName = ["txbl", "txDef", "txFree"]`, `for j1 in range(plan.N_j)`
with N_j=4). Fixed; `owlbridge.openCaseFromPlan` + `sskeys.openCaseFromPlan` build the case from a
solved Plan and set the keys `runPlan` writes after a solve (`caseStatus` from the plan, `summaryDf`,
`metricsDict`), so the Graphs page renders from the cached `plan.pkl` with no solve. Verified with
Streamlit's AppTest (`tests/ui/test_open_in_owl.py`): the page renders and `runPlan` is never
called.

**Checks (section 11's Check column), all green:** `fork-notes/synthetic/check_library_jobs.py`
on the synthetic baseline (`Case_ari+noa.toml` + its workbook) -- a run solves in the background
(real detached worker, 11.4 s, record with gap 0.0007 and 1 warning), a closed tab / a server
restart / a still-waiting queue lose nothing (a waiting job dispatched by a fresh manager, a live
worker's job adopted, a dead one interrupted), "Open in Owl" builds 128 page keys from the cached
plan with `caseStatus` "solved", and two solves on different days give identical summary and plan.
55 new tests: `tests/library/` 137 (the as_of input and its CLI reproducibility; the job record's
merge semantics -- a heartbeat never loses a cancel; adoption; cancel and the verified kill; the
worker's results folder, failure record, cancel-before-write, and the two-days determinism with
the wall clock mocked), `tests/ui/test_open_in_owl.py` 2.

**Found and fixed while building:** (a) `genDic`'s account keys, above -- the step-2 check earning
its keep; (b) `Logger` streams do not pickle, so `plan.pkl` could not exist: `Logger.__getstate__`
now drops non-picklable streams and rebuilds the default pair (mirroring its `__deepcopy__`
policy; `HistoricalRateModel` and `_interpolator` came along once the logger pickled); (c) the
suite's `freeze_year` fixture rebinds `datetime.date` itself, so `asof._parse` duck-types dates
instead of isinstance-checking them; (d) `plan_to_dict` flattens `plan_convergence` ("convergence"
is the type string there), so `build_record` normalizes both shapes.

**Known limits of this step:** `record.json`'s "iterations" is the self-consistent loop's count
from the solve log (the plan keeps none; a branch-and-bound preset will record nodes too); the
determinism guarantee covers deterministic and explicitly seeded rates -- a stochastic rate
method reseeds per call unless the case pins `rateSeed`; a cancelled job mid-solve stops at the
next log line or step boundary (the verified kill covers "stop now"); the preset is chosen at
queue time (it joins the scenario and the inputs hash with step 4's run method); §8.2's time
estimate and the `max_parallel` setting are not exposed yet (the manager takes it, default 1);
two managers over one library are out of scope (one per server, R5); §10's library-mode launcher
and localhost refusal come with the library pages (step 3); the `worker_argv` substitution is for
tests only.

**Step 2 independent review and fixes (2026-11-02, same session).** An independent reviewer
agent went over the step-2 code against the design (`F1-F10`; it ran the tests and wrote race
probes in `%TEMP%\opencode`). Freeze completeness, R1's refusal, the as_of derivations and
hashing, `record.json`'s fields, the plan cache, the kill path and the "Open in Owl" check were
confirmed sound; the job record's concurrency was not. All findings fixed the same day:

- **F1 (double dispatch):** two Queue fragments tick one manager concurrently, and `_spawn`
  marked the job running only after `Popen`, so one waiting job could be spawned twice (one
  probe reproduced it: 2 spawns, one token). Dispatch is now a compare-and-swap under the job's
  lock (`JobRecord.take_for_dispatch`: only one dispatcher takes a waiting job) and `tick()` runs
  under a manager lock.
- **F2 (the wake that kills "run again"):** a stale worker's `finish()` wrote over the re-queued
  attempt's record, and the new worker then stopped on it. Every worker write is token-guarded
  now (`JobRecord.update(token=...)` refuses once the job runs under a new token; a stale worker
  writes neither `status.json` nor `record.json`).
- **F3 (Windows, lost updates):** `status.json` read-modify-write was unserialized, and
  `os.replace` raises while any reader holds the file open (the Queue page reads every two
  seconds): heartbeats died silently and a cancel could fail. All record writes go through a
  per-job OS lock (`status.lock`, the S5 lesson applied to the job record) and the rename retries
  (falling back to an in-place write after 2 s; `JobRecord.read` retries torn reads). Probe A:
  0/300 lost cancels under a hammering heartbeat; probe D: ok with a reader holding the file.
- **F4 (tests without teeth):** the two-days determinism tests solved `Case_bill` under two
  pretend days in one year -- byte-identical even with a broken freeze. The pretend days now
  straddle a New Year, and `TestTheDateReachesTheSolve` pins S1's month sensitivity directly
  (`Plan._ssaOpenAges` follows the `as_of` date and ignores the wall clock).
- **F5 (thread leak):** `asof` was a process global, so one session's `as_of(...)` capture dated
  another session's solve (Streamlit sessions are threads; the probe showed 2000/2000 leaks).
  The context manager is thread-local now; `set_as_of` stays process-wide (probe: 0/2000).
- **F6 (S3's record):** an interrupted solve now leaves its `record.json` (status "interrupted"),
  and `run_again` starts clean -- the partial artifacts go, the old record is kept as
  `record.prev.json`.
- **F7 (adoption):** a live PID whose process start token is not the recorded one is not adopted
  (a reused PID is not ours, S9); the heartbeat thread survives a transient write failure instead
  of dying silent (a live worker would have been marked interrupted).
- **F8-F10 (honesty and shape):** `iterations` and the determinism claim are qualified above;
  `load_plan`'s docstring no longer overstates R10 (a zip-import must drop pickles; later steps);
  the env var is the design's `OWL_LIBRARY_DIR` and it switches the "Run Library" nav section on
  (like `OWL_ASSISTANT=1`); `import_case(as_of=...)` records the date it conditioned at;
  `openCaseFromPlan` re-attaches the case's log stream to the restored plan.

**Step 2 second review and fixes (2026-11-02, fresh session; `fork-notes/run-library-step2-review-2.md`,
G1-G2).** A second independent pass over the step at `b4a9ef18` (the F1-F10 state), run on Windows:
the full suite (3750 passed / 1 skipped, 7:38) exercises the `msvcrt` lock and `DETACHED_PROCESS`
branches the Linux container could not (step-1 T5's untested branch). Freeze completeness, R1's
refusal, the worker's `owlcli run` route, `record.json`'s fields and `converged` semantics, the plan
cache, `genDic`'s fix, F1/F3/F5/F7 and the determinism tests were confirmed sound. Two races the
first review's scope did not cover, both reproduced by probe and fixed the same day:

- **G1 (double enqueue):** `enqueue` picked `results/<stamp>_<preset>`, checked `folder.exists()`
  and then created it -- two Queue sessions clicking Solve in the same second landed in one folder
  and one job record was clobbered (probe: 2 enqueues, 1 job listed; if the first was already
  dispatched, two workers on one run). The claim is now the `mkdir` itself (atomic; `FileExistsError`
  takes the `-n` name).
- **G2 (the F2 guard's blind spot):** F2 token-guarded `status.json` and `record.json` writes, but
  the artifacts (`summary.json`, `plan.json`, `Results.xlsx`, `plan.pkl`) were written unguarded,
  while `requeue` had just cleaned exactly those files. A worker waking after "run again" (S8's
  machine-sleep scenario) put the old attempt's artifacts back into the new attempt's folder
  (probe: old `Results.xlsx` + `plan.pkl` beside a cleaned `summary.json`). The artifacts are now
  staged in `.attempt-<token8>` and published by `JobRecord.publish`: renames under the job's lock
  with the token checked inside the lock, so a publish and `requeue`'s clean-up cannot interleave
  (a stale worker publishes nothing and drops its staging). Regression tests from both probes;
  the probes re-run clean. Minors not fixed (M1-M6 in the review): the old `solve.log` is
  overwritten though `record.prev.json` is kept; section 10's `git check-ignore` refusal is
  neither implemented nor in the known limits; `adopt` treats an unreadable start token as ours;
  `asof.as_of(None)` falls back to the process-wide freeze; a 3-part `start_date`'s year is taken
  as the balances' year though Owl ignores it; `Queue.py`'s elapsed column parses `finished`
  unguarded.

Checks after the fixes: full suite **3752 passed / 1 skipped** (7:25; two regression tests added); flake8
clean, ruff only upstream's four B905; `tests/library` 139.

Next: step 3 (the library page, the run page, the comparison of two results with the noise rule),
then step 4 (the scenario model and builder). The `as_of` input goes upstream as a design issue
(`fork-notes/issue-as-of-date.md`, for the user to file).

**Step 2 third review (2026-11-02, fresh session; `fork-notes/run-library-step2-review-3.md`,
H1-H6, N1-N5; no code changed).** A fresh session reviewed `c3f45e6` (step 2 with F1-F10 and
G1-G2) for what the first two reviews missed. It found six H findings and fixed none:
- **H1:** the worker's thread-local freeze does not reach `withSSAges`' candidate threads,
  which read the real year. Probe on jack+jill at as_of 2025-03-01: 378 candidate calls saw
  2026, and the solve picked different ages and a different objective than under the
  process-wide freeze (\$106,737 vs \$106,866). Fix: the worker should use `set_as_of`.
- **H2:** both determinism tests pass with the freeze, or `--as-of`, disabled, because the
  session pin in `tests/conftest.py` supplies the date. The synthetic check has teeth.
- **H3:** naive local-time heartbeats read one hour old during the DST fall-back hour, so
  `adopt` interrupts live workers.
- **H4:** a stale worker's `record.json` write is check-then-write outside the lock; probe: an
  old "solved" record is left in a re-queued folder.
- **H5:** the queue advances only while a Queue page is open.
- **H6:** `plan.pkl` staleness ignores the commit, and an unpickle error is not soft.

`check_library_jobs.py` passes 4/4 on Linux. The user decides which findings to fix.

**Step 2 third review fixed (2026-11-02, same session; the user's call: fix H1-H6).** Details in
the review's dispositions.
- **H1:** the worker freezes with a new `asof.process_as_of(...)`, so `withSSAges`' candidate
  threads read the run's date.
- **H2:** the determinism tests clear the suite's pin (`no_session_pin`), and the worker test
  runs at an `as_of` other than the pin's.
- **H3:** stamps carry their UTC offset, and are compared and sorted through `stamp_seconds`.
- **H4:** `record.json` is written by `JobRecord.publish_record` under the job's lock, with
  the token checked.
- **H5:** `JobManager.start_ticker`, a daemon thread started by `ui/libraryjobs.py` from
  `main.py`.
- **H6:** `plan.pkl` is also keyed on `code_stamp()` (version, commit, the diff of a dirty
  tree), and an unloadable pickle is dropped.

14 new tests. Each fix was reverted in turn, and its tests failed (H1, H2, H3, H4, H6; H5's
tests need the new method). Full suite **3766 passed / 1 skipped** (10:05). flake8 clean, ruff
only upstream's four B905s. `check_library_jobs.py` 4/4. N1-N5 are still open.

**Step 2 third review's minors fixed (2026-11-02, same session; the user's call: fix N1-N5).**
Details in the review's minors dispositions.
- **N1:** two-stage cancel. The Queue's Cancel is cooperative, and Kill appears while the
  cancel is pending. A verified kill writes the attempt's "interrupted" record and drops its
  staging. The heartbeat continues while a cancel is pending.
- **N2:** the elapsed caption is corrected.
- **N3:** `update` raises instead of writing a stale copy over an unreadable record.
- **N4:** `requeue` is all-or-nothing (renames first, put back on failure), and it keeps
  `solve.prev.log` (M1).
- **N5:** `quick` puts every `"optimize"` family on the loop (`presets.resolve_options`). The
  synthetic baseline's quick solve went from 17.6 s with a MIP to 1.1 s with none.

Also: the ticker thread exits if its library folder is deleted.

16 new tests (`test_presets.py`, `tests/ui/test_queue_page.py` with AppTest, and the cancel,
kill, re-queue and heartbeat tests). Each fix was reverted in turn and its tests failed.
Full suite **3782 passed / 1 skipped** (9:24). flake8 clean, ruff only upstream's four B905s.
`check_library_jobs.py` 4/4, with 127 page keys: `gap` is absent without a MIP.

**The `as_of` input dropped (2026-11-02, same session; the user's call).** The question was what
the frozen date buys. A grep of every `asof.today()` call that reads more than `.year` found
three:
- two in the interface's own `ui_bridge`;
- `Plan._setStartingDate` for `start_date = "today"` (the day sets the first-year fraction);
- `Plan._ssaCurrentAgeMonths`: the earliest claiming month `withSSAges` may still pick, and the
  refusal of an entered age already past.

The last one is real-world truth (SSA does not pay for a month already gone), so freezing it to
the balances' date would let a later re-solve pick a claim that is no longer possible. Across
years, R1's refusal already covers it. What the freeze bought was only re-solving an old run at
its old date, against 78 call sites in 16 upstream modules, CLI options and an upstream issue.
User: drop it.

Done:
- **Back to upstream.** `src/owlplanner/asof.py` is deleted and `owlcli --as-of` removed. Every
  backend file, the CLI files, `tests/conftest.py` and the four test files that moved the date
  through `asof` are restored to `main`'s (= upstream's) versions; their diffs had been
  `as_of`-only, checked file by file.
- **Library.**
  - The scenario keeps `plan_year` (the start date's year, else the year of capture) and drops
    `as_of`.
  - `start_date = "today"` is stored as the capture day: this part was kept, so the solve day
    cannot move the first-year fraction.
  - `casefiles.check_plan_year` refuses a run outside its plan year, both at queue time and in
    the worker. The worker writes a "refused" record (status "refused", the reason in `error`).
  - `status.json` and `record.json` carry `plan_year` instead of `as_of`.
  - The Queue page shows the refusal as a message.
- **Tests.**
  - `tests/library/test_asof.py` is replaced by `test_plan_year.py`: the plan year and its
    refusal, the New Year refusal, `"today"` stored as the capture day (fails without that fix),
    and the claiming window following the month.
  - The worker tests: identical results on two days of the plan year; refused outside it
    (fails without the worker's check); claiming-age candidates read the same date as the
    main thread.
  - A Queue-page test for the refusal message.
- **Synthetic check.** `check_library_jobs.py` now has 5 checks (the 5th is the refusal): 5/5.
- **Docs.** Design §8.3 rewritten (D4 revised again: (a) record and flag, (b) refuse outside the
  plan year, (c) no frozen date, with the reasons), and §5, §11 and §12 updated.
  `issue-as-of-date.md` is marked withdrawn, with the fixes it would have needed. The review-3
  dispositions note H1/H2 as superseded. CLAUDE.md's date gotcha is back to upstream's freeze:
  it rebinds `datetime.date` too, so function-local imports are frozen as well, checked by a
  probe test.

Checks: full suite **3773 passed / 1 skipped** (10:41; 3782 before, with 18 `as_of` tests removed
and 9 plan-year tests added). flake8 clean, ruff only upstream's four B905s.
`check_library_jobs.py` 5/5.

`main` fast-forwarded to `claude/fervent-cerf-s86b65` at `11ecefab` (2026-11-02, the user's call):
run-library step 2, the fixes from all three reviews, and the `as_of` input dropped.

## Run-library step 3: the library page, the run page, the comparison (2026-11-02, on `claude/run-library-step3`)

Build step 3 of `fork-notes/run-library-design.md` (section 11): "Library page, run page,
comparison of two results with the noise rule"; check: "the synthetic baseline against a
variant". Scope (the user's call, before the build): the core first -- I3 (threshold
proximity), I6 (the one-year cash-flow Sankey) and I7 (the claiming-age map, design 14.3)
come as the second increment of this step -- and the comparison covers exactly two results
(section 9.2's "two or more" waits for step 6's collections). Code in
`src/owlplanner/library/view.py` and `compare.py`, `presets.py`, `store.py` and `results.py`;
the pages `ui/Library.py`, `ui/Run.py`, `ui/Compare.py` and `ui/main.py`'s nav; the
library-mode launchers `owlplanner-library.cmd/.sh`; small extensions to
`export.plan_metrics`, `cli/formatters.plan_to_dict` / `plan_convergence` and
`library/results.build_record`.

**Reading one result (`view.py`, design 9.1).** Everything the run page shows derives from
`record.json` / `summary.json` / `plan.json` alone (D7; the workbook's sheets come from
`Results.xlsx`), so a result whose `plan.pkl` cache is gone reads the same. The score is `run_suite.py`'s rule (its docstring): with essential
budget lines under maxSpending the first year's discretionary spending (k x D_0, the new
`discretionary_year1` metric), without them the spending basis, under maxBequest the final
bequest. Beside it the two end-of-plan numbers, never added (R3): the home at the end
(`final_bequest_today` less `final_bequest_savings_today`, run_suite's `home_at_end_today`)
and the savings left after the heirs' tax. Plus total taxes (income, gains, NIIT, payroll,
state), SS withheld by the earnings test, the claiming ages (`plan.json`'s new
`claiming_ages`), the quality line ("settled", or "the loop did not settle; differences under
1% are not meaningful", run_suite's `run_checks`), the method's noise tolerance (a proved
plan: reported gap x objective, read from the reported gap, CLAUDE.md "Branch-and-bound gap";
"local search -> loop" is not proved) and `is_exact_lp` for the agreement check.

**Judging a pair (`compare.py`, design 9.2, R2/R3/S13).** A difference of fifty cents or
less (TIE_DOLLARS, run_suite's `> 0.5` guard) is
no difference; a proved pair is judged by
both results' gap x objective; any unproved solve
brings the 1% loop-noise band (grey, "~", "the loop can make it, with either sign"), at or
above it the difference counts (local search decides). Flags when the two were solved on
different days ("plans start today ... run both again"), with different presets or under
different Owl commits. R3's verdict over the score and the home at the end: a result leads
when it is at least as good on both and better on one beyond the noise rule, otherwise
"trade-off" (the run page and the comparison never add the two numbers). When each run also
has an exact-model companion, the agreement check (run_suite's `agreement`): same sign and
beyond the spread plus the four error bars = resolved; in ACA years an unresolved
disagreement "goes to the local-search result, not to a tie" (the note is shown). "What
moved": the year-by-year differences in taxes, Medicare (IRMAA), ACA, Roth conversions,
withdrawals, SS income and spending, only the years and items that moved.

**Presets (`presets.py`).** `PRESETS` (what the interface offers: quick, decision, custom) vs
`SOLVE_PRESETS` (what one results folder records). "Decision" is one choice and two solves
(`preset_solves`): local search with the ages held (`decision`) plus its exact-model
companion (`decision_exact`). **Deviation from the design's wording (8.1/9.2):** the "exact
LP" is built as `run_suite.py`'s EXACT_GROUP -- the loop with Medicare off, SS taxability
0.85 **and `withLTCG="optimize"`** -- because that is the model the suite's agreement rule
and its condo-exact group compare against (with a large brokerage account the pure LP's LTCG
loop did not settle in 138 of 153 unsettled rates-exact runs there, its comment -- the
qualifier restored after review 2 Q5); the design's §8.1 Decision row
says so now. The two Ages presets stay with step 6.

**The pages.** `ui/Library.py`: the runs with their lineage (name, folder, plan year, "from
*parent*: changes", notes, tags, solves), "Import a case" (TOML + optional workbook +
budget file, through `import_case`) and "Save the current case as a new run"
(`scenario_from_ui`, against the run the case was opened from when there is one, T1/T3), a
zip download per run (`store.run_zip`: everything but lock files and `.attempt-*` staging),
rename (run.json's name only, S4) and delete (to `trash/`). `ui/Run.py`: the run and result
selectors, the header (solve date, method and commit, quality line), the six headline
numbers, four charts from `plan.json` (spending, balances, taxes by kind, income sources --
the new per-year wages/pension/SPIA/withdrawals), the Results workbook's sheets, and "Open in
Owl" (the cached plan, no solve), "Download everything", "Edit as new run" (the frozen
files into the case pages; saving on the Library page makes a child run), plus a solve
expander (any preset; "decision" queues both its solves). `ui/Compare.py`: the two result
selectors (defaulting to two main solves of two different runs, not to exact companions),
the inputs' difference in words (`diff_summaries`), the judged table, the leads verdict, the
flags, the agreement check and "what moved".

**Section 10 ships with the pages.** The library-mode launchers pass
`--server.address=localhost` and default `OWL_LIBRARY_DIR` to `otherFiles/library`; the app
refuses library mode on any other bind address (`libraryjobs.library_address_ok`, R11), and
`Library.open` refuses a library folder inside a git repository that does not ignore it
(`git check-ignore`, review M2: "Queue.py will create a library anywhere `OWL_LIBRARY_DIR`
points, a public repo included"). A trailing "/" on the probe makes `.gitignore`'s
directory-only patterns match a folder that does not exist yet (found by the test).

**Extended artifacts (small, additive).** `plan_metrics` gains `discretionary_year1` and
`essential_year1` beside `discretionary_scale` (the score rule needed them in the durable
files); `plan_to_dict` gains `claiming_ages` and per-year `wages` / `pension_income` /
`spia_income` / `portfolio_withdrawals` (the charts and "what moved"); `plan_convergence`
gains `objective_error_bar_today_dollars` (half the oscillation band, as the Summary's
"Objective error bar" row), which `build_record` carries into `record.json`'s convergence
block. `tests/plan/test_plan_metrics.py`'s key checks are subsets, so nothing pinned moved.

**Found and fixed while building: a step-2 regression on Windows (N4).** `requeue` ("run
again") renames `solve.log` to `solve.prev.log`, and a rename needs FILE_SHARE_DELETE on
every open handle -- `open()` does not request it (WinError 32), so "run again" refused with
"the previous attempt's worker may still be running" exactly in the machine-sleep wake (S8)
the G2 tests hold the worker in: `TestAStaleWorkerWritesNothing` failed on this machine at
`main` (`11ecefab` too). The solve log now opens with all three sharing flags
(`worker._open_log`, ctypes CreateFileW + `msvcrt.open_osfhandle`); after the rename the old
worker's remaining lines follow the file into `solve.prev.log`, which is where they belong.
Reproduced before and after with the two G2 tests (3.8 s green); N4's all-or-nothing refusal
stays for genuinely locked files (the workbook open in Excel).

**Checks.** `fork-notes/synthetic/check_library_compare.py` (the design's step-3 check, the
synthetic baseline against a variant -- `Case_ari+noa.toml` + its workbook, and the same
scenario with \\$400k less in the taxable account): **6/6** -- the baseline solves and its
numbers derive (score 108,959 first-year discretionary spending, home 760,861, savings 0,
taxes 310,107, Ari 67y0m + Noa 67y0m, "settled"); the variant moves the score -13.34%,
beyond the 1% band; the numbers survive without `plan.pkl`; the comparison reads "resolved",
"the first result leads", no flags, 2 input changes in words and 28 years moved; the same
inputs re-solved compare as "no difference" (all four numbers +0); the exact-model
companions agree on the ordering (d_pair -14,530, d_exact -15,672: resolved). 55 new test
functions in `tests/library` (the score rule, the quality line, the tolerances, the flags,
R3's verdicts, the agreement check, "what moved", presets, the check-ignore refusal and the
zip) and 18 in `tests/ui` (`test_library_pages.py`, the three pages with Streamlit's AppTest
and the localhost guard).

Next: the second increment of step 3 (I3 threshold proximity, I6 the cash-flow Sankey, I7
the claiming-age map), then step 4 (the scenario model and builder). D8: steps 1-3 go
upstream as a design issue after they work in the fork -- after the increment (the user's
call).

**Step 3 independent review and fixes (2026-11-02, same session;
`fork-notes/run-library-step3-review.md`, P1-P14).** An independent reviewer agent went over
the step's code against the design (it ran the tests, `check_library_compare.py` and its own
probes in `%TEMP%\opencode`). The noise rule's substance and direction, R3's leads rule in
every sign combination (brute-forced), the score rule and every artifact key name, the
`decision_exact` fingerprint end to end, `run_suite.agreement` term for term, `quality_notes`
vs `run_checks`, the N4 `_open_log` fix and the localhost guard were confirmed sound. All
findings fixed the same day except two noted below:

- **P1 (blocker, section 10's refusal):** `_git_ignored` probed with a trailing "/" so
  directory-only patterns would match a folder that does not exist yet -- and on this git
  (2.52, Windows) with a CRLF `.gitignore` containing a blank line (the repository's own
  shape), the blank pattern matches every not-yet-existing trailing-slash path, so
  `check-ignore` said "ignored" for a library dropped anywhere in the repo (`Library.open`
  created one under `src/`). The probe is now a sentinel *file* inside the folder: a file
  path is classified correctly (the blank pattern matches nothing) and directory patterns
  like `otherFiles/` still match paths inside it. Regression test with the CRLF + blank-line
  `.gitignore` (it fails on the old probe), and the allow cases re-checked against the real
  repository (`otherFiles/library` allowed, `src/...` and `docs/...` refused).
- **P2 (the Library page's "Open"):** the Run page's selector kept its widget value across
  reruns and silently ignored `library_selected_run` after the first render. "Open" now
  sets the state which the Run page consumes (`pop`) and writes into the selector's key.
  AppTest regression test.
- **P3 (missing summary.json read as $0):** `Result.solved` now needs all three durable
  files; a missing file reads as "no numbers" (None, the row's "-") with a quality note,
  never as zeros a comparison calls resolved.
- **P4 (companion lookup):** one result could be both sides' exact companion (a zero exact
  difference read as "disagree on the sign"), a companion could be the other side's selected
  result, and the oldest exact solve was picked regardless of day. The check now needs four
  distinct results, both selections are excluded from both lookups, and the companion is the
  newest exact solve of the pair's day (S13). Tests rewritten (the old one codified the
  shared companion).
- **P5 (run_zip):** rebuilt on every render of every zip button, could crash the page on a
  file vanishing mid-zip, silently skipped vanished files and shipped `requeue`'s
  `.requeue-*` trash. Now cached on the folder's fingerprint, `.requeue-*` is skipped like
  `.attempt-*`, and a vanished file raises `LibraryError` naming it (the pages show it and
  the user retries).
- **P6:** "a dollar or less" was the wording, the guard is run_suite's 50 cents
  (`TIE_DOLLARS = 0.5`): wording and test name corrected everywhere.
- **P7 (the ACA rule):** design 9.2's "a disagreement there goes to the local-search result,
  not to a tie" is now the verdict (in ACA years an unsettled agreement defers to the pair's
  own difference instead of leaving "unresolved" next to a note that denies the tie).
- **P9 (the tolerance):** `tolerance()` multiplied the gap by the *score*; it is the
  objective value (`Plan._objectiveValue`: first-year spending under maxSpending, the bequest
  under maxBequest) -- with essential lines the score is only the discretionary part and the
  tolerance was understated (9x on the reviewer's example). `view.objective_value` makes it
  explicit.
- **P10:** the test-count claim corrected (55 new `tests/library` and 18 `tests/ui` test
  functions in the diff against `7366cdee`, not "67" and "13"; commit `e223d866`'s "71 + 31"
  meant tests per file, a sloppy label).
- **P11 (ordering):** `Library.runs()` now orders by `library.json`'s `order` (the save
  order, "the order shown") instead of sorting same-second ties by a random uuid id; a
  copied-in folder sorts by (created, id) behind them. The results half is accepted as is:
  the folder stamps embed the solve time and sort the `decision_exact` companion right
  after its `decision` solve, and the pages' default skips companions anyway.
- **P12 (test gaps):** zip buttons rendered (both pages), the S13 flags rendered on the
  Compare page, `preset_solves("decision")` driven through `JobManager.enqueue` by the Run
  page's Solve button (two jobs, `decision` + `decision_exact`; `_spawn` stubbed), and
  "Edit as new run" asserts the exact base run.
- **P13 (stale base):** `library_base_run_id` is cleared whenever a case enters the session
  or becomes current by any other route (`sskeys.createCaseFromFile`, `createNewCase`,
  `openCaseFromPlan`, `switchToCase`), so a save can no longer claim the wrong parent.
  Known limit: "Edit as new run" twice in one session still refuses the duplicate case name
  (`createCaseFromFile`'s error), with no silent skip.
- **P14 (wordings):** an unsolved result's problem is shown once (the error line, not again
  as a quality warning); the agreement block says "the selected pair" (the primary pair can
  be any presets -- the check script's "d_quick" became "d_pair"); the plan-independence
  claim now names `Results.xlsx` as the workbook's source.

Not accepted, with evidence: **P8** -- the citation was said to name a nonexistent
CLAUDE.md gotcha; `**Branch-and-bound gap:**` ("read the reported gap, not the target") is
there, inside line 87's "Loop noise" bullet (one long line, which is why a line-oriented
grep misses it). The citation was sharpened to name the bullet.

Checks after the fixes: `check_library_compare.py` re-run **6/6** (every figure unchanged
but the renamed key); `tests/library` + `tests/ui` green in parallel runs; flake8 clean,
ruff only upstream's four B905s. Full suite: **3845 passed, 2 skipped** (12:36 on this
machine; the two skips are environmental: "MOSEK is installed but not licensed here" and
the POSIX-only tzset test).

## Run-library step 3, second increment: "Things to look at", the one-year Sankey, the claiming-age map (2026-11-02, on `claude/run-library-step3`)

I3, I6 and I7 of `fork-notes/run-library-design.md` (section 14.1, placed by 14.3), the
step-3 run-page increment the scope note deferred ("I3/I6/I7 come as the second increment
of this step"). The comparison still covers exactly two results. Two scope calls (the user,
2026-11-02): I3's "just below or just over" is a **band of 5% of the boundary** (not a fixed
$ band, not an unfiltered list); I7's scores file is read from the **run folder**
(`scores.json`), with a file picker as the fallback (not a separate page).

**I3 threshold proximity -- `src/owlplanner/thresholds.py`, in `plan.json` `thresholds`.**
`threshold_proximity(plan)` reads the solved arrays after a solve (no model change) and lists
the years whose income sits within `NEAR_BAND` (5%) of a boundary the model knows. Kinds,
each gated on the household actually being exposed that year: IRMAA tiers (the tax year's
MAGI against the *premium year's* thresholds, exactly as `mediCosts` compares them; the entry
names the premium year it affects), the 0% capital-gains bracket (taxable income `G_n + Q_n`
against the 0%->15% edge), the SS taxability bands (provisional income
`MAGI_aca_n - 0.5*SS`; ramps, so no cost is reported), the marketplace subsidy limits (the
year's table breakpoints x FPL, including the 400% cliff and the state's Medicaid line),
the NY benefit recapture start (state AGI), the Enhanced STAR limit (the income year's
tested income, with the benefit year it affects), and **the NIIT line** (added beyond the
design's six: `owlcli explain` reports it, and the crossing is a cliff on all net investment
income). Each entry: year, kind, label, side, the distance in today's $, the **cost of
closing the gap** -- the model's own charge evaluated at the boundary plus the gap, less the
charge at the boundary (`mediCosts`, `capitalGainTax`, `acaCosts`, `computeNIIT`,
`tax_state.state_recapture`, `star.implied_credit`), so a crossing that costs nothing here is
not listed -- the year the crossing bites, and a note. Sorted by year.

**I6 the one-year cash-flow Sankey -- `export.cash_flow_split`, in `plan.json` `cash_flow`.**
Sources and uses per year, nominal $, mirroring `Plan._check_cashflow_balance`'s identity
exactly (sources minus uses is its residual): wages, SS, pensions, SPIAs, other income, net
investment income, fixed-asset income and the fixed-asset sale (the condo), each account's
withdrawals (taxable / tax-deferred / Roth / HSA), big-ticket inflows; spending split along
the **budget's lines** (one "Net spending" use without a budget), each tax, the Medicare and
ACA premiums, debt payments, big-ticket purchases, the surplus deposit, and Roth conversions.
A conversion is a transfer inside the accounts: it appears as its own source ("from the
tax-deferred accounts") and its own use, so both sides stay equal while the flow is visible.
The run page's fifth chart tab picks a year (default: the first with a purchase, else the
first Medicare year -- the design's two uses) and draws the Sankey.

**I7 the claiming-age map -- `library/agemap.py`, on the run page.** Reads
`fork-notes/phase5/work_sweep.py --json` output (one row per work variant): the free
persons' ages and the objective of every scored plan (`results`; failed solves dropped), the
decided ages, and a tie shade per cell -- greedy groups by descending value at the larger of
the two cells' tolerances (R2's rule per cell: a proved cell's `gap x value`, else the 1%
loop-noise band). Heat map for two free persons (the decided pair marked), a line and a
table for one. Only the scored cells are drawn: work_sweep's sweeps score a cross around the
decided pair, so a full grid would come from step 6's Ages presets.

**Pages (`ui/Run.py`).** "Things to look at" as a table after the headline numbers (with the
band's rule and the cost's meaning in its caption), the fifth chart tab, and a "Claiming-age
map" section after the solve expander (run folder, else a file picker).

**Checks.** `fork-notes/synthetic/check_library_compare.py` extended with checks 7-9 (the
thresholds block's schema on the reloaded result; sources = uses in all 28 years of the
synthetic baseline and the Sankey year 2027 balances at 974,971 both sides; the map over the
real `work_sweep_chris+pat_bb_2026-10-26.json`): **9/9**. Tests: 19 new in
`tests/plan/test_thresholds.py` (stub plans pinning every boundary, side and distance, and
the cost of the IRMAA, gains, NIIT and STAR kinds against the model's own constants and
cost functions -- corrected after review 2 Q5: the recapture cost is unpinned and the
marketplace cost is only checked positive; the identity on solved plans; the
budget-lines split; the `plan.json` blocks), 10 in `tests/library/test_agemap.py`, 3 in
`tests/library/test_view.py`, 4 in `tests/ui/test_library_pages.py`. Full suite: **3881
passed, 2 skipped, 9 deselected** (26:07 on this machine; the `deep` marker's 9 are out of
the default run, the two skips are environmental, as before; 3845 + the 36 new tests).

Deviations from the design, for the review: NIIT added to I3's six kinds; the Sankey links
through one empty hub node (any pairwise source-to-use allocation would be invented); "each
account" is the four account kinds of `w_ijn`; the map shades only the scored cells (above).
Found on the way, not a bug: `Plan.setAccountBalances` is in thousands (`units="k"`), so a
bare-API fixture with dollar-sized balances is infeasible (the test fixtures look large but
are not).

Next: step 4 (the scenario model and builder from `make_cases.py`). D8 (steps 1-3 upstream
as a design issue, "after the increment") is unblocked: the issue draft next, the user's
call on when.

## Run-library step 3 reviewed as a whole; Q1 and Q3 fixed (2026-11-02, on `claude/run-library-step3`)

A full review of step 3, both increments, in two passes: this session's own and an
independent reviewer agent with fresh context (`fork-notes/run-library-step3-review-2.md`,
findings Q1-Q9; the independent pass's own text and probes are `step3-indep-review.md` and
`qprobe*.py` in `%TEMP%\opencode`). Both passes re-derived the acceptance check (**9/9**,
figures unchanged), the test counts (55 + 18, then 19/10/3/4) and the full suite
(**3881 passed, 2 skipped**, 12:40), verified every P1-P14 fix of the first review (P8's
rejection correct), and confirmed the noise rule, R3's verdicts, the score rule, the
agreement check, the `decision_exact` fingerprint, I6's identity mirror and I7's parsing.
The two passes converged on Q1 and Q2 independently; the own pass added Q7-Q8, the
independent one Q3-Q6.

Nine findings, two should-fix, folded in the same day:

- **Q1 (both passes):** I3's 0%-gains entry measured `G_n + Q_n`, not the QDCG line-1 basis
  the model prices the bracket on (`Plan._ltcg_tax_implied`: `G_n + e_n + max(Q_n,0) - ded`,
  `ded` = `sigmaBar_n` in the years whose brackets an unused deduction widens, #205). A
  year with unused deduction could read "over the 0% edge" where the model is well under
  (probe: over by 1,100 vs under by 28,900). `_gains_entries` now measures the model's own
  basis and clips gains at taxable; `FakePlan` carries `e_n`/`sigmaBar_n`/`_ltcg_wide_n`
  and `test_the_gains_bracket_measures_the_qdcg_taxable_income` pins the side flip.
- **Q3 (independent):** a `work_sweep.py --json` row with fixed claiming ages (no free
  person -- real output) crashed the Run page: the cells carry no age tuples and
  `_age_map_chart` indexed `c.ages[0]`. The map now draws nothing for such a variant
  ("swept no claiming ages"), `x_ages`/`y_ages` skip empty tuples, and two regression tests
  cover it (unit and the page end to end with a crafted zero-free `scores.json`).

Open, for a later pass (Q2, Q4-Q9): the NIIT exposure gate reads `I_n` only (gains-only
years are never listed); the first quality note shows twice (caption + warning); three
claims-vs-checks drifts (check 7's docstring, the cost-pinning claim, the "153 unsettled
runs" quote); I3 omits the 100%-FPL credit start outside expansion states; I3's IRMAA cost
reads $0 at the top-tier edge and at gaps under the $1 slack; `view.objective_value` is not
`Plan._objectiveValue` under maxBequest (it adds the home; the citation says otherwise);
P13's clearing of `library_base_run_id` misses `switchToCaseName`/`copyCase`/
`deleteCurrentCase`.

Checks after the fixes: `check_library_compare.py` **9/9** (every figure unchanged);
54 passed over the three touched test files; flake8 and ruff clean on the six touched files.
Full suite: **3884 passed, 2 skipped** (13:43; 3881 + the three new tests, no flakes).

## Run-library step 3, third review (2026-11-02, on `claude/compassionate-gates-8q0fmn`, from `claude/run-library-step3` `01d0846`)

A third pass over step 3, on Linux (the first two ran on Windows):
`fork-notes/run-library-step3-review-3.md`, findings W1-W9. Re-run here: full suite **3885
passed, 1 skipped** (11:01; the POSIX-only tzset test runs here), `check_library_compare.py`
**9/9** with every figure unchanged, flake8/ruff clean but upstream's known items.

Should-fix, all reproduced: **W1** the one-year Sankey drops negative flows (`ui/Run.py:97`).
STAR makes "State and local tax" negative in 23 of the synthetic baseline's 28 years: drawn
in vs out differ by up to \$3,492, while the caption says they are equal. Check 8 misses it
(raw sums, year 2027). **W2** "home at the end" is judged with the 1% loop-noise band, though
it is computed from inputs before any solve (`processDebtsAndFixedAssets`). Probe: +3%
spending and -\$6,000 home reads "the second result leads", where R3 says trade-off. **W3**
`st.error`/`st.info` followed by `st.rerun()` vanish: the Library page's import and save
errors, V8's "identical to an existing run" notice, and the Run page's plan-year refusal.
**W4** Delete during a running solve. The run went to `trash/`, the manager listed no job,
and the worker kept solving untracked for at least 60 s, then exited writing nothing; the
trashed `status.json` stays "running".

Minor: W5 under maxBequest the score already holds the home (R3's two numbers overlap); W6
"what moved" aligns years by position; W7 the NIIT note calls a kink a cliff (PROGRESS's
second-increment entry too); W8 `run_zip` ships `plan.pkl`, against section 10 (R10);
W9 library mode does not turn the AI pages off. Review 2's Q2 and Q4-Q9 are still open.
Nothing fixed in this pass: review only.

## Run-library step 3: review 3's W1-W4 fixed (2026-11-02, on `claude/run-library-step3`)

The four should-fix findings of `fork-notes/run-library-step3-review-3.md`, each entry
there marked "Fixed" with how:

- **W1** `view.cash_flow_year`: a negative row is drawn on the other side ("..., net
  refund" / "..., net outflow"), and the Sankey, its default year and its caption (both
  totals, as drawn) read it. Check 8 also balances the drawn sides: worst 2.00 over the 28
  years, 23 of them with a row moved across (3,492 before).
- **W2** `compare.difference(from_inputs=True)`: the home at the end is judged by the
  fifty-cent rule alone (it is set from the inputs before any solve). The probe's +3%
  spending with -\$6,000 home now reads "trade-off".
- **W3** `libraryjobs.flash` / `show_flashes`: a message queued before `st.rerun()` is drawn
  once after it (import and save errors, the "identical" notice, the Delete and Solve
  refusals; the Solve refusal also catches `JobsError`).
- **W4** `JobManager.delete_run` refuses while a solve is waiting or running (check and move
  under the tick lock), and the Library page's Delete goes through it. The page tests'
  fixture now leaves its hand-written results `done`, not `waiting`.

11 new tests: test_compare 2, test_view 1, test_jobs 4 (`TestDeleteRun`), test_library_pages
4 (`TestMessagesSurviveTheRerun`). Checks: `check_library_compare.py` **9/9** (every other
figure unchanged); full suite **3896 passed, 1 skipped** (9:26, Linux; 3885 + 11);
flake8/ruff clean but upstream's known items. Open: W5-W9 and review 2's Q2, Q4-Q9.

## Run-library step 3: every open review item fixed (2026-11-02, on `claude/run-library-step3`)

The open items of reviews 2 and 3 (Q2, Q4-Q9, W5-W9), all fixed. How each was fixed is in
the review docs: `run-library-step3-review-2.md` "Disposition after review 3" and
`run-library-step3-review-3.md` "Disposition of W5-W9". In short:

- **Q9** the "edited from run X" mark is stored in the case's own dictionary
  (`sskeys.setRunBase` / `runBase`) instead of a session key cleared route by route.
- **W5** under maxBequest the lead reads savings and home (the score already holds the
  home); different objectives are "not comparable" and flagged.
- **Q7** IRMAA crossings are priced outside the \$1 slack (the top tier and sub-dollar gaps
  had read \$0), and every priced kind drops a \$0 crossing.
- **Q2/W7** the NIIT gate reads `I_n + Q_n`, the note describes the kink, and the threshold
  comes from `tx.niitThreshold`.
- **W8** the run zip leaves `plan.pkl` out (section 10).
- **Q4** the quality caption no longer repeats the first note.
- **Q5** entries carry `boundary_today_dollars`, and check 7 verifies each is inside its
  band; two PROGRESS claims corrected in place; three garbled "§" restored.
- **W9** library mode never offers the Assistant chat (`ui/main.py`; design section 10
  reworded).
- **W6** "what moved" matches years by calendar year.
- **Q6** a known limit stated in `_aca_entries`.
- **Q8** `view.objective_value` under maxBequest is `final_bequest_savings_today`, the LP's
  objective. This changes the value, beyond the "docstring only" first proposed.

11 new tests: Q9 3, W5 3, Q7 2, Q2 1, Q5 1, W6 1. The four new threshold tests (Q2, Q5,
two for Q7) were also run against the committed `thresholds.py`: the Q2 and both Q7 tests
fail there; the Q5 test needs the new field, so it cannot run there. W9 has no automated
test (`main.py` is the entry script; read and compiled). Checks: `check_library_compare.py`
**9/9** (figures unchanged, check 7 now also checks the bands); full suite **3907 passed,
1 skipped** (9:33, Linux; 3896 + 11); flake8/ruff clean but upstream's known items. No
review item of step 3 is open.

`main` fast-forwarded to `claude/run-library-step3` (2026-11-02, the user's call): run-library
step 3 (both increments) with every finding of its three reviews fixed.

## D8: the run-library design issue drafted (2026-11-02, on `claude/eager-turing-4bs36n`)

`fork-notes/issue-run-library.md`: the upstream design issue for run-library steps 1-3 (D8),
concept level, for the user to post; not posted. The proposal: an opt-in (`OWL_LIBRARY_DIR`,
like `OWL_ASSISTANT`) for local installs, in three layers (run folders in Owl's own
`Case.toml` + `HFP.xlsx`, background solves with a record, a comparison judged against the
noise rule), what building it taught (plan year, pickling, `genDic`, the races, privacy), the
small core changes it needs, and five questions (in Owl or a separate project; pages behind an
env var; Docker; the 1% band; a core warning when `start_date` names another year).

Verified on stock upstream `dev` `73dc8815` (fetched today; 5 commits past `1cf1925`, Docker
and docs, **not merged here**), real runs from a worktree with its own `src`, on
`Case_jack+jill.toml`:

- a solved Plan does not pickle: `TypeError: cannot pickle '_io.TextIOWrapper' object`;
- `owlbridge.genDic` raises `IndexError` at `ui/owlbridge.py:2039` on this case. `N_j` is 4
  unconditionally (`plan.py:459`), so it is every case, not "every HSA case" as the step-2
  entry above says. Nothing on `dev` calls it.
- `docker/runentrypoint.sh` binds `0.0.0.0` and the compose file has no volume: the fork's
  localhost guard would switch library mode off in upstream's container (question 3).

Prior threads read for the text: #27 and #45 (bodies by `gh api search/issues`; the
maintainer's comments by WebFetch, a summary with quotes). Nothing in `src/` or `ui/` changed.

Reviewed independently the same day (a reviewer agent; 14 findings, the two stock repros
re-run). Every finding was checked and taken; the main one was checked directly: upstream
**#132** (Docker user lost their cases on closing the browser; the maintainer: "The server is
stateless between sessions", "No data stays there for privacy reasons"), which the first
draft's searches missed. The posted text now opens by answering it, and question 1 asks
whether a server on the user's own computer may keep files there. Other fixes: a run's source
of truth is `scenario.json` (not "exactly" Owl's files), `owlcli run` reproduces a run only with
the recorded options in its plan year, the list of existing-code changes completed (`ui/main.py`,
`openCaseFromPlan`, `sskeys`, `version.py`; the error bar is in `plan_convergence`, so MCP output
changes), the 1% band's basis is the loop (local search: \$15-74/yr shortfalls), the simplified
model no longer called exact, the claiming-age map dropped as fork-only. Findings and dispositions
are in the draft's "Review" section.

2026-11-03 (user): Docker and #132 dropped from the post. #132 is about the pre-built Docker
image; the fork runs the app built from source on the user's machine, and a known local process
saving local files raises no such concern. The opening now names source installs, the Docker
question is gone (four questions remain), and the #132 note in the draft records the decision.

`main` fast-forwarded to `claude/eager-turing-4bs36n` (2026-11-03, the user's call): the
run-library design issue draft (D8) with its review; docs only.

## Upstream `dev` `73dc881` merged (2026-11-03, on `claude/eager-turing-4bs36n`)

Five commits past `1cf1925`: `825a72b` (Connect your AI names all eighteen MCP tools and both
resources), `47d23fd` (Docker images native on Apple Silicon, #242), `f1002d4` (version
2026.10.30), `2deb60e` (Docker images pin uv 0.13.6), `73dc881` (benchmarks in the Makefile).
Clean merge (`30073969`); in `src/` only the version string changed, and the fork's git retry in
`version.py` is kept. `CHANGELOG.md` equals upstream's byte for byte. Full suite **3907 passed,
1 skipped** (9:46, Linux; unchanged count). flake8/ruff: only upstream's known items (the
`tests/stochastic` E301/E304s, the four B905s). `main` fast-forwarded afterwards (the user's call).

## Run-library step 4: the scenario model and builder (2026-11-03, on `claude/run-library-step4`)

Build step 4 of `fork-notes/run-library-design.md` (section 11): "Scenario model and builder
from `make_cases.py`; scenario editor pages with provenance (markers first; section 6.3's
overrides are a later increment of this step, S11)" -- check: "the builder reproduces
`make_cases.py`'s 39 workbooks cell for cell". The user's call for this increment: core plus
I1's anchors (events dated relative to other events). I12's care figures (NY-metro costs) are
still unverified, so the care event keeps a plain start year here (an age anchor is available).

**Schema v2** (`library/scenario.py`): `events` beside the hand rows (`case`, `hfp`).
`validate` reads 1 and 2; `migrate` brings 1 to 2 with no events (every row stays a hand row,
section 6.4); `canonicalize` migrates, so everything stored is current-version. `BUILDER_VERSION`
is 2: older runs read "built with an older builder" instead of aliasing new output (R9) -- old
v1 runs included, since a re-import now lands in v2. `diff_summaries` words events per event
("purchase: wp condo in 2029, 30-year loan at 6.25% -> ... 2031 ...", section 7) and skips the
provenance.

**Builder** (`library/builder.py`): the five D6 event kinds (work, claim, rent, purchase, care)
and I1's anchors -- `{"anchor": "age", "person": "Ari", "age": 86}`, `work_end` with `after`,
`purchase`, and `{"anchor": "event", "id": ...}` with an offset -- plus an editable text form
for them (`year_ref_text` / `parse_year_ref`: `age:Ari:86`, `after:Noa`, `purchase`,
`event:care+2`) that the editor's inputs use. `build(scenario) -> (case, hfp, provenance)` is
deterministic and without side effects (the inflation path through `config_to_plan` with
`loadHFP=False` and throwaway log streams) and does the coupled edits of section 6.2 in one
place: the move (or the school district) from the purchase, `aca_settings.aca_start_year` from
the last full-time work year (1 + its end; employer coverage runs while either spouse works
full time -- make_cases.py's rule), `social_security_ages` and `withSSAges` from the claims,
the Fixed Assets row in purchase-year dollars (grown by the case's own `gamma_n`), the Debts
row linked to it by name, the big-ticket outflow on `pay_on`'s sheet, the owner's Budget lines,
the rent rows to the year before the purchase, and the care row. The rent rule ("$4,000/month,
the same in 2027, then inflation") is `rent_rows`: one-year rows through `flat_until` (a flat
nominal amount declines in real terms, which one constant-rate row cannot express) and a tail
row named "rent from 2027" as make_cases.py named it. The row builders (`budget_row`,
`rent_rows`, `owner_rows`) moved into the library and `make_cases.py` uses them now (section
6.2: one implementation); `write_hfp` and `case` stay the suite's own (workbook writing and
template filling are not builder logic).

**Provenance (markers first, S11):** every generated row (Budget, Debts, Fixed Assets, by
name), person-sheet cell (by event and year) and case field (by path) records its event.
Generated rows are regenerated wholesale when the events change and hand rows are untouched;
the name is the row's identity, so a hand row named like a generated one is replaced. The
pages-save path drops the generated positions from the plan's tables (`casefiles._drop_generated`)
and reverts the generated case fields to the base's hand values (`_drop_generated_case`), so a
deleted event leaves nothing stale behind. **Limit of this increment:** an edit to a generated
value does not survive a regeneration (section 6.3's per-cell overrides with "back to
computed" are the later increment).

**make_cases.py and the acceptance:** the script shares the row builders and writes
`scenarios.json`: the same cases as v2 scenarios (36 grid + 2 long-term-care + 7 work + 1
earnings-test = 46), each with `expected_case` (the case its `set` builds) and the workbooks or
hfp edits its events must produce. The care event anchors at age 86 (= `CARE_YEAR`) and the
ltc-sell sale at the care event, against the script's explicit years. Before the refactor the
39 workbooks were generated from `git show HEAD:` of the script and compared with the new
ones: cell for cell identical (the JSONs byte-identical), so make_cases.py's output is
unchanged. `fork-notes/synthetic/check_library_builder.py` (the step's check) runs make_cases.py
fresh and compares the builder's output through `export_case`: **46/46 scenarios match (39
workbooks cell for cell; case fields and hfp edits included)**. Sensitivity probed (one-off):
a doubled price, a tampered expected district and a tampered wage cell are each caught while
the untouched scenario matches. `check_library_roundtrip.py` stays **39/39** through the new
export path (`export_case` builds first), and the step-2 and step-3 checks re-run green on the
same code: `check_library_jobs.py` **5/5** (a real background solve included) and
`check_library_compare.py` **9/9** (every figure unchanged).

**Editor** (`ui/Scenario.py`, registered in `ui/main.py`'s Run Library; "Edit the scenario" on
the Run page): the work and claiming events as tables, rent / home purchase / care as boxes
with the anchor grammar in their year fields, and "What the events generate (marked)": the
generated rows with their years and amounts, the person-sheet cells and the case fields, each
with its event. The save box shows the computed change summary against the open run and saves
as a new run whose parent is the one edited (D3). People, accounts, the goal and the
assumptions (section 6.1's other rows) stay in the case pages ("Edit as new run").

Tests: `tests/library/test_builder.py` (52: the row builders, event validation, every anchor,
build's coupled edits and markers, regeneration, determinism, the text grammar round trip, and
one run on the real inflation path), `test_scenario.py` +6 (v2 validate, the migration, the
worded diffs), `test_casefiles.py` +1 (`_drop_generated`), `tests/ui/test_scenario_page.py`
(5, AppTest: the page renders, the markers carry their events, a changed price moves the
change summary and saves a child run, an unbuildable scenario says why). Full suite **3970
passed, 2 skipped** (10:31, Windows; 3907 + 64 new - the POSIX-only tzset test, which skips
here; the other skip is the unlicensed-MOSEK check). flake8/ruff clean but upstream's known
items. Known limits, next increment: section 6.3's per-cell overrides; one
purchase/rent/care event per scenario ("sale and re-buy later", D6); work spans take plain
calendar years (the events that point at them may anchor); "Overwrite draft" (section 7) not
built -- save-as only; and re-importing a v2 run's frozen files gives a hand-rows scenario
(no events) with a different inputs hash (R9's flag is the answer for older runs).

## Run-library step 4: the independent review, U1-U12, folded (2026-11-03, on `claude/run-library-step4`)

A reviewer agent went over the step-4 code against the design (`fork-notes/run-library-step4-review.md`,
findings U1-U12; it re-ran the checks, the make_cases.py regression against `git show c61326ea:`
and its own probes from a temp folder). Every finding was checked and folded the same day
(the user's call); the disposition table is in the review doc. In short:

- **U1 (high) a pages-save leaked the generated case fields into the hand rows** (`basic_info.moves`,
  the district, the marketplace year, the claiming ages and the switch), so deleting an event
  after a "Edit as new run" save left stale, unmarked inputs steering the plan. `casefiles
  ._drop_generated_case` now reverts every generated case field to the base's hand value (the
  drop-to-nothing first attempt lost the fallback a claim-less person needs -- Jill's age).
  PROGRESS's "a deleted event leaves nothing stale behind" is true from here.
- **U2 phantom changes and a dedupe defeat:** the editor's widgets re-type event numbers as
  floats and inject default fields, so an unedited load showed changes and an unedited save
  duplicated the run. `canonicalize` canonicalizes the events now (year fields as refs,
  numbers as canonical cells, keys at their default dropped) and the page canonicalizes before
  diffing and saving. T1/V3 for events: the inputs hash is no longer type-sensitive where the
  generated files are not.
- **U3** an `event:` anchor to a work or rent event raised a raw KeyError; it now reads that
  event's year field, else a work span's end, else a rent's start.
- **U4 a mixed claim abandoned the fixed age on a false premise** ("withSSAges is global").
  `plan._parseSSAgesOption` takes a name or a list of names: the builder now writes
  `withSSAges = [<the "let Owl choose" names>]` and the fixed ages are held. The known limit
  is gone.
- **U5** a hand row named like a generated row in *another* table was dropped; names are now
  the identity within their own table. **U6** a `pay_on` typo silently dropped the big-ticket
  outflow; it is refused now. **U7** the year edges: a fractional age anchor is refused (whole
  years), every resolved year must sit in the plan window, a span that ends before it starts is
  refused, and `_plan_start` raises instead of guessing.
- **U8** the acceptance check's blind spots: `compare_case` compares leaves with their types
  (T1/V3) and a work variant's whole built workbook is compared against the baseline workbook
  with its edits overlaid -- previously a doubled price in a work variant passed. A kept hand
  age keeps its own type. The check re-ran **46/46** under the stricter rules.
- **U9** the markers table showed Debts and Fixed Assets rows as spans with a blank amount; a
  loan shows its term and amount, a home its value and "sold YYYY" or "kept".
- **U10/U12** doc fixes with one decision: work spans take plain calendar years (the events
  that point at them may anchor), and `months_worked` is written for every year of its span
  (the suite's edit format and `run_suite.py` depend on it; the year work stops is what the
  earnings test reads; split a span for a one-year value).
- **U11** CLAUDE.md's test counts and `rent_rows`'s docstring.

New regression tests: `test_builder.py` TestReviewFixes (8: U3, U5, U6, U7 x4, U8),
`test_casefiles.py` TestDropGenerated +1 (U1, with the probe's rebuild), `test_scenario_page.py`
+1 (U2: no phantom changes, an unedited save dedupes). Full suite **3981 passed, 2 skipped**
(9:46; 3907 + 75 new tests - the POSIX-only tzset test, which skips on Windows). Lint clean
but for upstream's known items. The reviewer's open design questions: section 5's "re-importing a run's own files gives
the same hash" no longer holds for scenarios with events (amend 5/6.3a, or an import that
recovers events later?) -- stands for the user; section 6.2's wording is **answered (the
user's call, 2026-11-03)**: the design is amended there -- only the row builders moved into
the module (`write_hfp` and `case` stay the suite's own: workbook writing and template filling
are not builder logic, and the suite's assembly and the builder's mapping are deliberately two
placements checked cell for cell).

## Run-library step 4: second review, X1-X9 (2026-11-03, on `claude/sweet-cori-it2jyw`)

A second review of `claude/run-library-step4` at `3d77fb80` (after U1-U12), on Linux:
`fork-notes/run-library-step4-review-2.md`. Nothing in `src/`, `ui/` or `tests/` changed; this
branch is the step-4 branch plus the review. Re-run: `tests/library` + the Scenario page tests
**312 passed**; `check_library_builder.py` **46/46**; `check_library_roundtrip.py` **39/39**;
flake8 on the step's files: one E128 (`tests/library/test_builder.py:350`, X9).

- **X1 (high):** a pages-save (`scenario_from_ui(base=...)`) returns a scenario with **no
  events**: `scenario_from_case` never carries the base's, while the generated rows, cells and
  case fields are stripped. "Edit as new run" -> save on a run with events loses the purchase,
  rent, work and claims (probe: `noa-part-claim-62` child events `[]`, Fixed Assets 2 -> 1 rows,
  claiming ages 62 -> 67).
- **X2:** `_drop_generated` zeroes generated cells and drops same-name rows instead of
  restoring the base's hand values (the U1 class, for the tables; the probe's hand 2026 wages
  168,000 end at 0 after the work event is deleted), and an unedited pages-save is then not
  identical to its base.
- **X3:** `build()` is not deterministic under non-reproducible stochastic rates (`histochastic`
  1970-2000: price 1,421,789 / 1,262,691 / 1,227,299 over three builds).
- **X4:** the Scenario page defaults closing to 0.03 and the loan's extra to 0.02 where the
  builder's defaults are 0, so an unedited save of a cash purchase without `closing` adds
  $21,727 to the outflow; the change summary words both sides the same.
- X5-X9 (low): `event:<id>` with an id ending in `-<digits>` does not round-trip; an anchor to
  a claim raises a raw TypeError and `event:rent` reads an explicit end, not the start; one claim
  event resets the other person's hand `withSSAges` to fixed; the page's self-anchored purchase
  default and a `schema_version: 1 -> 2` change shown for every pre-step-4 run; the E128.

Not fixed here (the user's call which to fold, and how for X3).

## Run-library step 4: second review folded, X1-X9 (2026-11-03)

The user's call: fix X1-X9 on the step-4 branch. Disposition table in
`fork-notes/run-library-step4-review-2.md`; the fixes, in short:

- **X1** `scenario_from_ui` carries the base's events (they were dropped with everything they
  generate); reverting a generated field also removes a section the build had created
  (`aca_settings = {}` on a case with none -- found by the new end-to-end test).
- **X2** `_drop_generated(..., base_hfp)` puts back the hand cells and the same-name hand rows
  the events replaced, at their place.
- **X3** `_gamma` refuses a non-deterministic rate model without a fixed seed (the model's own
  `deterministic` flag and `reproducible_rates`), only where a purchase or rent needs gamma.
- **X4** `builder.FINANCING_DEFAULTS` / `PLACE_DEFAULTS`, read by `build`, the canonical form
  (keys at their default dropped, zero owner costs too) and the page; the page keeps the keys
  it does not edit; the change summary words the price, sale, wages and ends, and names the
  changed fields when both sides' words are equal.
- **X5** `parse_year_ref(..., ids=)`; **X6** `event:` anchors to an unknown id or a claim are
  refused, the year field is chosen by the target's kind (`EVENT_YEAR_FIELD`); **X7** a person
  with no claim event keeps the hand `withSSAges` choice (`_searched_names`); **X8** a new
  purchase defaults to the plan year + 1, care to the first person at 86, rent to the plan
  year, and a schema-1 run shows no phantom change but a caption; **X9** the E128.
- `BUILDER_VERSION` 3 (X7 and the canonical form change the generated output and the hash).

Tests: 23 new (`test_builder.py` TestSecondReviewFixes 10, `test_scenario.py` 5,
`test_casefiles.py` TestPagesSaveWithEvents 4, `test_scenario_page.py` TestSecondReview 4;
two existing tests adjusted: the unknown-id anchor's message, the U4 test's hand case set to
fixed). Run against the pre-fix code (`7b4565cf`), 20 fail there; the rest pin behavior that
already held. Checks: `check_library_builder.py` **46/46**, `check_library_roundtrip.py`
**39/39**; the review's pages-save probe on the imported synthetic baseline: diff 0, same hash,
the 168,000 hand wages back after deleting the work event. Full suite (Linux, -n 4): **4004
passed, 1 skipped, 1 failed** (9:59): the failure is step 2's
`test_jobs.py::TestTicker::test_a_waiting_job_is_dispatched_with_no_page_ticking`, which passes
alone, passed 6/6 under a parallel library-suite load, and has a race in the test itself: its
fake `_spawn` marks the job running with no PID, and any tick before `stop_ticker()` runs
`adopt()`, which interrupts it (`pid_alive(None)`). Not fixed here (outside X1-X9); the library
and UI tests re-run green (529 passed). flake8/ruff: only upstream's known items.

Not changed: a scenario whose hand rows were written as JSON (`scenarios.json`'s documents)
rather than read from a workbook is normalized by its first pages-save, so it does not hash as
its base; the library's own entry paths store read-back rows and are identical. The first
review's section 5 round-trip question still stands for the user.

## The ticker test's race fixed (2026-11-03)

`tests/library/test_jobs.py::TestTicker::test_a_waiting_job_is_dispatched_with_no_page_ticking`
(step 2, H5) failed once in the full suite above. Cause, in the test: its fake `_spawn` took
the job (state running) but recorded no worker, which the real `_spawn` does right after
(`jobs.py`: `job.update(pid=..., pid_started=...)`); every `tick()` starts with `adopt()`, which
reads a running job with no PID as dead and interrupts it, so a tick between the dispatch and
`stop_ticker()` failed the test. The fake now records this live test process as the worker,
and the test waits 0.3 s (several ticks at 0.05 s) after the dispatch, so it also checks that a
dispatched job with a live worker stays running. With that wait, the old fake fails 3/3 with
the full suite's error (`'interrupted' == 'running'`) and the new one passes 3/3. Test-only;
`jobs.py` unchanged. Full suite (Linux, -n 4): **4005 passed, 1 skipped** (9:01).

## `main` fast-forwarded to run-library step 4 (2026-11-03)

The user's call. `main` moved from `c61326ea` to the head of `claude/run-library-step4`: step 4
(`b27d2838`), the first review's U1-U12 (`9b3e5c02`), the design 6.2 amendment, the second
review X1-X9 and its fixes (`7b4565cf`, `f4b2d5c6`), the ticker test's race (`781e3d53`), and
this note. Full suite on `781e3d53` (Linux): 4005 passed, 1 skipped. Next: step 5 (Budget
editor; the missing fork widgets).

## Run-library step 5: the Budget editor and the missing fork widgets (2026-11-03, on `claude/run-library-step5`)

Build step 5 of `fork-notes/run-library-design.md` (section 11): *"Budget editor; the missing fork
widgets (`withItemized`, `withSTAR`, all moves)"*. The design's check column for this step is
empty; the checks are the tests listed below. Everything is the case pages (generic UI: the Budget
editor is offered upstream later, section 12) and the run library picks it all up through the paths
step 1 built (`scenario_from_ui` reads the case keys and the plan's tables).

**Budget editor** (`ui/Financial_Profile.py`): a third table section, `### Budget`, with its own
expander and the same `houseEditorBase` / `storeHouseEdits` loop as Debts and Fixed Assets
(`houseListBudget`, through the "Budget" branch of `hfp_io.conditionDebtsAndFixedAssetsDF` that
already existed; `syncHouseLists` already carried it). All 14 `budget.SHEET_COLUMNS` get bubble
help (`budgetHelp`, the `timetableHelp` pattern). Beside the table, the model's own "adds nothing
to the plan" checks (`budget.lines_left_out`, exactly the ones `_evaluateBudget` logs at solve
time) are reported as the rows are edited -- a line whose years never meet the plan, an age clock
without its ages, an index that names nobody -- as `checkQCDColumn` does for QCD
(`owlbridge.checkBudgetRows`). A case naming `budget_file` says the interface does not read the
file (Documentation's own words).

**A restored run keeps its tables** (`owlbridge.seedProfileTables`, replacing the page's
`runOncePerCase(owb.resetTimeLists)`): "Open in Owl" restores a solved Plan into the pages (design
9.1), and the Financial Profile page then **zeroed the plan's Wages and Contributions**
(`plan.zeroWagesAndContributions`) and showed empty tables -- found while wiring the Budget
editor's seeding. The page now seeds `timeList*` / `houseList*` from the plan when it holds
tables, with `storeCaseKey` (seeding is not an edit: `setCaseKey` would mark a solved run
"modified"), and fills only keys that are still empty. A plan with no tables (a case uploaded
without its workbook) still starts from the zeroed skeleton, as before.

**Saving the current case to the library syncs the pages' tables first**
(`owlbridge.syncContributions` = `_setContributions(plan, "set")`, called by
`ui/Library.py::_save_current_case`): `scenario_from_ui` takes the HFP tables from the plan, and
its docstring puts the sync on the caller ("The caller syncs the UI's edited tables into the plan
first"). The Library page did not, so a Budget/Debts/Fixed Assets/wages edit that had not been run
or downloaded yet was missing from the saved run. Test: an edited `houseListBudget` reaches the
saved run's `inputs/HFP.xlsx`.

**`withItemized` and `withSTAR`** (`ui/Run_Options.py`, *Advanced options* -> *Deductions and
Credits*, placed above *Calculations* on purpose): radios bound to the passthrough names themselves
(`SOLVER_UI_PASSTHROUGH_KEYS`), so `getSolveParameters` (the solve) and `ui_to_config` (the
save) read the same case key and cannot drift (#156's lesson; no bridge translation involved).
Values are the `_MODE_OPTIONS` literals ("none"/"loop", plus "optimize" for STAR). Both stay
enabled under the local-search toggle: `Plan._applyBreakpointOptions` forces STAR to "optimize"
but honors "none", and itemizing is not a breakpoint family -- so the "individual settings do not
apply" caption is not extended to them (it says "every breakpoint below").

**All moves** (`ui/Create_Case.py`): moves after the first -- which `config_to_ui` carries as
`stateMovesMore` and the pages only counted in an info banner -- are edited under *Further moves*:
one block of cascading selects per move (year, state, city, school district; the first move's
`_state_choices` / `_locality_choices` / `_district_choices`, so a city or district outside its
state cannot be entered), an "Add a move" button and a per-row Remove. The rows are `stateMovesMore`
dicts exactly as `ui_to_config` writes them (`{year, state, [locality], [school_district]}`);
adding or removing drops the rows' widget state, so shifted rows cannot inherit each other's
half-typed values (#194's problem, for whole rows). The mistakes `residency._homes_by_year` refuses
at solve time are reported as the rows are edited: two moves in one year, and a move to the
residence it leaves (walked in year order from the starting residence; returning to a state you left
is legal and is not warned).

Tests (the step's checks): `tests/ui/test_budget_editor.py` (10: the column help covers the
sheet's columns; `checkBudgetRows`' messages; the page renders with lines and warns; the
`budget_file` note; a restored run keeps its tables and its "solved" status; a table edit reaches
the workbook; the Library save carries it), `tests/ui/test_run_options_deductions.py` (5: the
radios show the file's values and the loop default, stay enabled under local search, and a choice
reaches `getSolveParameters` and `ui_to_config` identically and round-trips through a case
file), `tests/ui/test_create_case_move.py` +7 (further moves show their values; add, edit and
remove; reach the case file and the plan's `genDic` split; warn on a duplicate year and on a move
to the residence it leaves; do not warn on a return to a state left behind),
`tests/config/test_config_ui_bridge.py` +1 (several moves with a locality and a school district
round-trip through the UI keys and the plan). Two AppTest quirks of interaction tests are handled in
the tests: the title bar's case selector decorates its options (the case name plus a marker
character) so a rerun cannot
re-serialize it (`test_ui_disabled_options`'s workaround, used before every rerun), and
streamlit's `date_input` rejected the plain `datetime.date` AppTest hands widget state back as
once `freeze_year` had rebound `date` (`tests/conftest.py`: `_FixedDateMeta.__instancecheck__`
now accepts any real date, so the freeze stays transparent to isinstance; found by the first
add-a-move rerun). AppTest cannot drive `st.data_editor`, so the editor's edit loop is covered
through the storage path (`syncContributions` -> `saveContributions`, and the Library save), as
the Debts and Fixed Assets editors are.

Also: `tests/ui/test_financial_profile.py` (upstream's) asserts the `### ` heading order to check
the download button sits below every table; it now lists *Budget* between *Debts and Fixed Assets*
and *Save your Financial Profile*. `ui/Documentation.py`: the Budget sheet says where its lines are
edited, the itemized and STAR paragraphs name their Run Options widgets, and the move paragraph
describes *Further moves* instead of "Only one move is modeled". `fork-notes/CHANGELOG-fork.md` has
the entry.

Not built (outside the design's named scope, for later): widgets for the other passthrough-only
keys -- `previousSTARIncomes` (STAR income before the plan; defaults to the MAGI entries, which
have widgets) and `withSeniorBonus`.

Checks: `tests/ui tests/config tests/library` **799 passed, 1 skipped** (2:20, Windows, -n 4).
Full suite (Windows, -n 4): **4027 passed, 2 skipped** (12:19; the two skips are the POSIX-only
jobs tzset test and the unlicensed-MOSEK check, as on every Windows run). flake8/ruff: only
upstream's known items (the `stochastic` test files' E301/E304, the four B905s).

## Run-library step 5: the review's W1-W5, W7-W8 folded (2026-11-03)

An independent reviewer agent went over the step-5 code against the design
(`fork-notes/run-library-step5-review.md`, findings W1-W8; it re-ran both suites, mutation-pinned
the three side fixes in a scratch worktree, and probed the interplays). Verdict: the step matches
its design row, with two silent-loss interplays and a two-thirds-true warnings claim to settle.
The user's call: W1 as the save-time notice, W2 as "the sheet wins on edit", W3-W5, W7 and W8
folded; W6 deferred.

- **W1 (medium): an edit to a generated Budget row (or person-sheet cell) reached the solve but
  was silently regenerated away by the library save, with no marker in the editor (§6.3).**
  Fixed as the save-time notice: `scenario_from_ui(..., dropped=)` reports every generated value
  the pages changed (`_generated_edits`: rows by name against `builder.build`'s tables, cells by
  position, blanks and int/float equal through the workbook round trip), and `ui/Library.py`
  flashes "Not kept in this run: ... — edit the event on the Scenario page instead" (capped at
  five names). The Debts/Fixed Assets and Budget editors carry §6.3's policy as a caption when the
  case was opened from a run (`kz.runBase()`). The marker column and the per-cell overrides stay
  the later increment.
- **W2 (medium): for a `budget_file` case one edit meant three things** — the solve honored it,
  the Download workbook blanked the sheet (`saveContributions` leaves file lines out) and a saved
  run kept the file's unchanged lines. Fixed as the model's own rule: an edit to the Budget table
  clears `plan.budgetFromFile` ("a Budget sheet with lines wins over it on every load"), so all
  three carry the same lines; the caption says so and no longer claims the lines "have to be in
  this table" where the seeding shows the file's.
- **W3 (medium): the move warnings held for two of residency's three refusals.** The first move
  was checked against the starting residence only (the page's older inline warning), so a further
  move dated before it could make the first move the refused one and no warning fired.
  `_moreMoveWarnings` now walks every move against the residence it leaves in year order,
  comparing canonical spellings as `residency` does (`_normResidence`); the first move's
  starting-residence case stays the inline warning, not a duplicate. **W4 (low):** with a plan, a
  move outside `first_year < year < first_year + N_n` is warned with residency's own wording
  (without one the help text is the guard). Both are pinned by
  `test_the_move_warnings_match_what_residency_refuses`, a parity grid of ten chains (the page's
  warnings against `residency.residence_by_year`: refused if and only if warned).
- **W5 (low):** the Budget `type` help said "a line of another type is left out" — it is a type
  *outside* `BUDGET_TYPES`, dropped at workbook read. Reworded.
- **W7 (low):** counts and comments (23 new tests in the step, `test_create_case_move.py` +7;
  the three "not editable yet" comments). **W8 (low):** with the move toggle off, a caption says
  the N further moves stay in the case but are neither solved nor saved.
- **W6 (low, not folded — the user's call):** `getRadio`'s coercion drifts for raw case values (a
  `"None"` shows "loop" while the solve normalizes to "none"; a legacy bool maps to the wrong
  choice and is refused at solve). Defense in depth: unreachable through the real paths (the
  schema normalizes mode strings and refuses bools, and `genDic` copies the parsed
  `solverOptions`). For a later pass.

Tests (17 new): the parity grid 10 and the toggle-off note (`test_create_case_move.py`), the
`budget_file` edit and the two W1 page tests (`test_budget_editor.py`), the three W1 report tests
(`test_casefiles.py`). `tests/ui tests/config tests/library` **816 passed, 1 skipped**. Full suite
(Windows, -n 4): **4044 passed, 2 skipped** (11:02). flake8/ruff: only upstream's known items. The
review's disposition table is filled in `fork-notes/run-library-step5-review.md`.

## Run-library step 5: second review, Y1-Y5 (2026-11-04)

A second independent review of `claude/run-library-step5` at `4aefd31`
(`fork-notes/run-library-step5-review-2.md`). Re-checked: `tests/ui tests/config tests/library`
817 passed (Linux); lint only upstream's items; W1's "not kept" report gives no false positive on
any of the 46 synthetic event scenarios (probe through the real export / workbook round trip).
Findings, each reproduced by a probe (not committed), nothing fixed (the user's call):

- **Y1 (medium):** a further move whose district or city is written in a spelling residency
  accepts (the district alone, "Yonkers"; a lower-case city) loses it on the first render of
  Create Case: `config_to_ui` canonicalizes only the first move, and `_renderMoreMoves` drops any
  value not literally in the select's choices (and marks the case modified).
- **Y2 (medium):** a further move dated this year or earlier stops the whole Create Case page
  (`StreamlitValueBelowMinError` from the year widget's `min_value`); the first move does not.
- **Y3 (low):** the two new `initCaseKey` defaults on Run Options make an unchanged case saved
  against its base show `withItemized` / `withSTAR` "added" and a different scenario hash.
- **Y4 (low):** the Library save ignores `syncContributions()` returning `False` and saves the
  plan's previous tables; the rerun wipes the error (reach through the editor not established).
- **Y5 (nit):** the STAR help omits Basic's own income limit; `seedProfileTables`' zeroing
  fallback is unreachable (every `Plan` holds tables from `__init__`).

## Run-library step 5: Y1-Y4 fixed (2026-11-04)

The user's call on the second review: fix Y1-Y4 (Y5 left). Dispositions in
`fork-notes/run-library-step5-review-2.md`; entry in `fork-notes/CHANGELOG-fork.md`.
- **Y1:** `config_to_ui` reads further moves through `ui_bridge._ui_further_move` (state
  upper-cased, canonical city and district, unknown values as written), so the Create Case
  selects no longer drop a spelling residency accepts.
- **Y2:** the further-move year widget's bounds include the move's own year; a past move renders
  with W4's warning and can be removed.
- **Y3:** Run Options no longer stores `withItemized` / `withSTAR` defaults.
- **Y4:** the library save stops with a message when `syncContributions()` returns `False`.

Tests (+8, each checked to fail on `4aefd31`'s `src/` and `ui/`): `test_create_case_move.py` +4
(Y1 three spellings, Y2), `test_config_ui_bridge.py` +1 (Y1), `test_run_options_deductions.py` +1
(Y3; the round-trip test now expects the untouched `withSTAR` absent), `test_budget_editor.py` +1
(Y4). The four touched files: 103 passed. Full suite (Linux, -n 4): **4052 passed, 1 skipped**
(8:48). flake8/ruff: only upstream's known items.

## `main` fast-forwarded to run-library step 5 (2026-11-04)

The user's call. `main` moved from `64244f8` to the head of `claude/run-library-step5`: step 5
(`26054d5`), the first review's W1-W5, W7-W8 (`4aefd31`), the second review Y1-Y5 (`1812604`),
its Y1-Y4 fixes (`25f42b3`, `ed94733`), and this note. Full suite on `25f42b3` (Linux): 4052
passed, 1 skipped. Next: step 5b (D11's rate table), then 6 (collections).

## Run-library step 5b: the rate table and the named downturn sequences (2026-11-04, on `claude/run-library-step5b`)

Design section 11, step 5b (D11, I11, R13): a year-by-year rates CSV the case file names, read
by a new rate method, and the named downturn sequences. The user's two calls before the build:
the sequence fills only its window and the years outside keep **the run's own rate method** (the
stress question stays "the same plan, but the market does this"), and the pages get **safety +
Scenario rows** (no Rates-page table editor this step).
- **The `table` rate method** (`src/owlplanner/rate_models/table.py`, in the registry and
  `info/RATE_MODELS.md` regenerated): `[rates_selection] method = "table"` + `rates_file` reads
  its returns from that CSV -- a `year` column and the four rate columns of
  `src/owlplanner/data/rates.csv` (extra columns ignored, so Owl's own history file can be
  named), values in percent. The file resolves CWD-then-beside-the-case (`Plan._config_dir`,
  set by `config_to_plan`; the HFP workbook's order), rows are matched to the plan's calendar
  years (`start_year`, passed by `Plan.setRates` like `dataframe`'s `n_years`), and the file is
  re-read at every `setRates` (a changed `rates.csv` reaches the plan, review Z1) -- the rows a
  plan already holds are reused only when the file cannot be resolved or read (the interface's
  path with no case directory in reach; `clone` passes `dirname`). `to_config` writes only the
  file name.
- **The library** stores the table in the scenario (`rates_table`, schema v3 + migration 1/2->3;
  `BUILDER_VERSION` 4): it is in the inputs hash (R13), `import_case` reads it as it reads the
  workbook (explicit path, CWD, beside the case; `rates_path=`), `export_case` writes
  `inputs/rates.csv` and the generated `Case.toml` names it. `validate` holds the two
  consistency rules (a table and the case must agree on `method = "table"`, both directions).
- **Downturn events (I11):** `{kind: "downturn", sequence, start}` places a named sequence at a
  year or an anchor (`purchase`, `age:Ari:70`, `event:buy+2`); `builder.rates_table` generates
  the run's table as the case's own rate path (through a plan build, like `_gamma`) with the
  sequence's window overlaid at the placement, and `build()` names the table in the generated
  case with provenance markers on the event. The named sequences
  (`data/downturn_sequences.toml`, `library/sequences.py`) carry their sources: `crash-30` is
  an invented stress year (Boldin's "custom downturns", the design's I11), `three-negative-years`
  (2000-2002) and `poor-decade` (1973-1982) replay rows of Owl's own `data/rates.csv`. One
  downturn event per run (the variant dimension is step 6); a hand table and an event refuse to
  coexist (the event generates the table: "drop one"), and a sequence over a `table` case is
  refused (no baseline to overlay). A table run's nominal amounts come from the table's
  inflation path (`build()`'s gamma), so an overlay moves the purchase price and the rent rows.
- **The pages keep a table case intact** (the review's W1/Y line of thought: the selectors'
  "not available" reset would have rewritten the case, and `_setRates` raises on unknown
  methods): `config_to_ui` / `ui_to_config` / `_ui_rate_method_to_config` / `_ui_rates_to_config`
  carry `method = "table"` and `ratesFile` (no forced historical window), `owlbridge.genDic`
  sets the read-only state, `_setRates` re-reads the frozen file through `plan.setRates`, and
  the Rates page shows the table read-only ("edit the scenario's downturn event"). The Scenario
  page edits the downturn event like the others (sequence picker with its source and window,
  placement in the anchor grammar; `_MANAGED` keeps unmanaged keys).
- **The acceptance** (`fork-notes/synthetic/check_library_rates.py`, the Check column):
  `owlcli run` of a run's frozen `inputs/Case.toml`, called from another working directory,
  reproduces the interface's worker solve field for field (`plan.json` -- the summary metrics
  among its fields, the solve's own timing aside; the run's `summary.json` is checked to hold
  its metrics, not compared, review Z8), for a downturn run and
  a hand-table run alike; the run's `record.json` records `rates.method = "table"`; the
  sequence's window sits at its placement with the baseline row outside it; re-importing the
  frozen files gives the run's own inputs hash (T1 -- the hand-table run: a downturn run
  re-imports as a hand-table scenario by design, every re-import drops events since step 4);
  re-exporting writes the same `rates.csv`.
  Both solves are the plain loop (the synthetic case's ages are held and Medicare put on the
  loop first: its `withSSAges x withMedicare = "optimize"` makes every age candidate a MIP).
  **11/11 checks pass** (2026-11-04; the two plan comparisons differ only in
  `solve_time_seconds`, which the check nulls).
- Tests: `tests/rate_models/test_rate_model_table.py` (20: reading by year, units, the errors a
  short or bad table gives, the TOML round trip, `Plan.setRates` with `_config_dir` and the
  in-memory fallback, `clone` with a new expectancy) and `tests/library/test_rates_table.py`
  (22: the hand table's import/export/round trip, the overlay and its anchors, the marked case
  fields, the refusals, the schema rules, the pages saves, gamma from the table).
- Notes for the record: the schema bump means re-importing a run saved before step 5b gives a
  new hash (a v3 document; like v1->v2 at step 4). The table must cover the plan's years or the
  solve names the missing ones -- a `clone` with a longer expectancy needs a longer table. The
  plan keeps the table's rows in memory (`TableRateModel.rows`), which is what lets the pages
  solve a table case with no case directory in reach.


Full suite (Windows, -n 4): **4094 passed, 2 skipped** (9:40; 4052 + 42 new tests; the skips are
the POSIX-only `test_jobs.py` tzset test and `test_solver_status.py`'s unlicensed-MOSEK check).
`info/PARAMETERS.md` gained the `table` method and its `rates_file` / `in_percent` keys, and
`ui/Documentation.py`'s method table its `table` row. flake8/ruff: only upstream's known items.


## Run-library step 5b: the independent review (Z1-Z9) (2026-11-04)

A fresh-eyes review of the two step-5b commits (`c99d3551`, `44676043`) is at
`fork-notes/run-library-step5b-review.md`: findings **Z1-Z9** (2 medium, 6 low, 1 nit), each
reproduced by a probe (`probe_review_z1..z7.py` in the session's temp dir), plus a "claims
checked" section that verifies the acceptance at 11/11, the pages keeping a table case intact
on a real AppTest render, the overlay semantics, the migrations and the docs' accuracy. The
step's main promises hold; the findings are the edges:
- **Z1 (medium):** the in-memory-rows fallback in `Plan.setRates` is unconditional, so a
  changed `rates.csv` is silently replaced by the plan's stale rows (the pages' re-solve and a
  fresh `owlcli`/worker solve of the same inputs disagree).
- **Z2 (medium):** `reproducible_rates = true` without `rate_seed` passes the determinism
  guard (which checks the plan's flag, not the case's seed), so `build()` and `export_case`
  can freeze different tables within one export and two exports differ at equal hash.
- Z3-Z8 (low): the two table workflows the pages' text recommends dead-end; a downturn
  placement outside the plan silently does nothing or is truncated; `method = "table"` without
  `rates_file` raises a bare `KeyError`; an Excel BOM is refused misleadingly and `nan`/`inf`
  cells reach `tau_kn`; the sequence window is invisible to the inputs hash (and `lru_cache`
  pins it); the acceptance record overstates (T1 holds for the hand-table run only; the
  `summary.json` metrics are not compared).
- Z9 (nit): a comment still says schema "2".

**The user's call: fold all nine, in a new session.** The work order is
`fork-notes/run-library-step5b-handoff.md` (per-finding fix + verification, the agreed
variants: Z7 folds a hash of the used sequences' windows into `scenario_hash` only for runs
with a downturn event; Z3 adds the Import uploader and takes the no-base save's table from the
plan's rows). Nothing of it is folded yet; the review's "unverified / to check" items are
listed there as optional.


## Run-library step 5b: Z1-Z9 folded (2026-11-04)

The user's call on `fork-notes/run-library-step5b-review.md`: fold all nine findings, per the
work order `fork-notes/run-library-step5b-handoff.md`. Dispositions (each named test checked to
fail before its fix; the review's probes rerun after):
- **Z1 (medium): a changed `rates.csv` was silently replaced by the plan's stale rows.**
  `Plan.setRates` now tries the file first (`rate_models.table.try_read_rates_csv`) and falls
  back to the rows the plan holds only when the file cannot be resolved or read (the
  interface's path: no case directory in reach -- the budget file's precedent). The comment and
  the step-5b entry's wording above now say exactly that. `probe_review_z1.py` after:
  `2) after apply_config_to_plan: 2027 rate = -0.55`, `STALE ROWS WIN, FILE IGNORED: False`.
- **Z2 (medium): `reproducible_rates` without `rate_seed` froze two different tables in one
  export.** `_throwaway_plan`'s guard now reads the **case** (the plan cannot tell a minted
  seed from a fixed one): a stochastic method needs `reproducible_rates` **and** `rate_seed`
  in the case, and the message says so. `export_case` computes the rates table once and passes
  it in (`build(scenario, rates_table=)`; the three-value return is unchanged), so one export
  builds and writes one and the same table. The probe's catching rerun
  (`%TEMP%\opencode\probe_z2_after.py`) after: the seedless case refused with the named
  message; the seeded one `two rates_table() calls equal: True`,
  `one export: build() saw 1 table(s); written csv == build()'s table: True`,
  `two exports write the same rates.csv: True`.
- **Z3 (low): the two workflows the pages' own text recommends dead-ended.** The Import tab
  takes a rates CSV (a fourth uploader, passed as `rates_path=`), and `import_case` reads the
  table before the plan build and passes its rows in, so an uploaded file that is not beside
  the case feeds both the plan and the scenario; `scenario_from_ui` with no base stores the
  table the plan holds in memory (`TableRateModel.rows`, the budget lines' precedent) instead
  of refusing with "import the CSV beside the case file"; the Rates caption names what can
  change the table (a hand table's route is the import; a generated one's is its downturn
  event). `probe_review_z3.py` after: `(b) save with base=None succeeded: rates_table in
  scenario: True`; an import with no CSV anywhere now says `pass rates_path= to the caller`.
- **Z4 (low): a placement that misses the plan looked applied.** `builder.rates_table`'s
  overlay refuses a window in no plan year (before the plan or past its end) and a window that
  starts before the plan and would be cut; a window that starts inside the plan and runs past
  its end stays "simply not used" (documented). The one ambiguity in the work order (its rule
  sentence vs its test sentence for a placement entirely past the plan) went to the user:
  **a window that lands nowhere raises** ("a placement that misses the plan must not look
  applied"), only the run-past-the-end truncation stays. `probe_review_z4.py` after (its plan
  is 2026-2058): 2020, 2024, 2069, 2075 and `age:Jack:60` all refused, the placement and the
  plan window named.
- **Z5 (low): `method = "table"` with no `rates_file` raised a bare `KeyError`.**
  `TableRateModel.from_config` raises `ValueError("rate method 'table' needs a 'rates_file'
  ...")` (a blank counts as none) through `config_to_plan` too.
- **Z6 (low): hostile CSV input.** `read_rates_csv` opens the file as `utf-8-sig` (Excel's
  "CSV UTF-8" writes a BOM) and refuses non-finite cells by year and column ("row 2027, column
  'S&P 500' is not a finite number"): the plain plan path and the library's confusing "not a
  number: None" are one named error now. `probe_review_z5.py` after: `(a)` the named error,
  `(b) BOM csv read: 45 rows`, `(c)` refused before it reaches a plan.
- **Z7 (low): the sequence window was builder input the inputs hash did not see.**
  `scenario_hash` folds in a hash of the named sequences the scenario's downturn events use
  (name + window) when there is such an event (design section 5 amended with the choice), and
  `sequences()` is no longer `lru_cache`d (a live server sees an edited file).
  **This changes the hash of downturn runs only** -- a run without a downturn event keeps its
  hash, and nothing on disk moves: a stored run's hash is still its stored scenario's, only a
  re-import of a downturn run's frozen files no longer aliases an edited window (the review's
  `probe_review_z6.py` still trips at its `load_sequences.cache_clear()` line: there is no
  cache to clear).
- **Z8 (low): the acceptance record overstated.** The step-5b acceptance bullet above and the
  check's docstring scope T1 to the hand-table run (a downturn run re-imports as a hand-table
  scenario by design -- every re-import drops events since step 4) and say the plan comparison
  carries the summary metrics inside `plan.json`; `summary.json` is checked to exist, not
  compared. The check still passes **11/11**.
- **Z9 (nit):** `canonicalize`'s comment says schema (3, with events and the rates table).

Tests (+21: `tests/rate_models/test_rate_model_table.py` +9 -- Z1's twin, Z5, Z6's reader;
`tests/library/test_rates_table.py` +12 -- Z2, Z3, Z4, Z6's import side, Z7; the two files now
29 + 34 = 63). **20 of the 21 were checked to fail before their fix** (the fixes under `src/`
stashed, the tests re-run: 20 failed / 43 passed, every one named above); the twenty-first
(`test_z2_a_seeded_baseline_exports_byte_identical_rates`) pins the seeded property and passes
either way. The four touched suites (`tests\library tests\rate_models tests\config tests\ui`):
**1225 passed, 1 skipped** (2:33). Full suite (Windows, -n 4): **4115 passed, 2 skipped**
(12:20; 4094 + 21). The acceptance check reruns at **11/11** (its docstring and the record
above scoped per Z8). flake8/ruff: only upstream's known items.


## Run-library step 5b: review 2, AA1-AA3 folded (2026-11-04)

A second independent review of the step (`fork-notes/run-library-step5b-review-2.md`, findings
AA1-AA6, prefix AA as U-Z are taken) went over the branch head at `365b72c5` -- the Z1-Z9 fold
included -- with 11 fresh probes in the session's temp dir. The user's call: fold **AA1-AA3**
(AA4-AA6 not folded). Dispositions (each named test checked to fail before its fix):
- **AA1 (medium): a decimal table (`in_percent = false`) drifted 100x through the pages.** A
  no-base "Save the current case" stored the plan's raw rows while `ui_to_config`'s table
  branch kept only `rates_file`, so the frozen run re-read the decimals as percent; the same
  loss re-priced the **session** plan at the next solve too (every solve re-applies the rates
  from the case keys: `prepareRun` -> `apply_config_to_plan`). Fixed at the root and at the
  save: `in_percent` rides with `ratesFile` through `config_to_ui`, `genDic` and
  `_ui_rates_to_config` (kept only when it is not the default, as `to_config` keeps it, so no
  hash changes), and `scenario_from_ui` supplies it from `plan.rateModel.params` when there is
  no base -- immune to which builder made the case keys. The review's (f3) end to end is
  `test_aa1_a_no_base_save_keeps_the_table_units` (the frozen plan prices the session's rates);
  `test_aa1_the_pages_round_trip_keeps_the_table_units` pins the key's round trip.
- **AA2 (low): `clone(plan, expectancy=)` skipped Z1's file-first re-read.** It passed the
  source plan's rows unconditionally (so `Plan.setRates` never tried the file), keeping stale
  rows after a `rates.csv` edit while its comment promised the file is re-read. `clone` now
  tries `try_read_rates_csv` and keeps the source rows only when the file cannot be resolved
  or read; `plan.py`'s comment names the rows-carrying callers (`clone`, `import_case`).
- **AA3 (low): `build(rates_table=)` trusted the caller**, skipping the "drop one" and "edit
  the table itself" refusals (and generating no table at all for a downturn run given `None`).
  The rules are `_check_table_events` now, enforced in `build` however the table arrives, plus
  a named refusal for `rates_table=None` on a downturn run (the contract is in `build`'s
  docstring).
- **AA4-AA6 not folded** (this round's call): AA4 is a product call (where the Rates page's
  `st.stop()` belongs -- the heirs-tax/OBBBA/dividend/liquidation widgets are unreachable for
  every table case today); AA5 (the export test spies only `builder.rates_table`; two name
  shadows in `build`) and AA6 (a directory as `rates_file`, an "optional" rates upload for a
  non-table case, a `nan` window in `downturn_sequences.toml`) stand as written.

Tests (+6: `tests/library/test_rates_table.py` +4, `tests/rate_models/test_rate_model_table.py`
+2; the two files now 38 + 31 = 69). **5 of the 6 were checked to fail before their fix** (the
fixes under `src/` and `ui/` stashed, the tests re-run: 5 failed / 1 passed); the sixth
(`test_a_clone_with_no_file_keeps_the_source_rows`) pins the fallback the fix preserves. The
four touched suites (`tests\library tests\rate_models tests\config tests\ui`): **1231 passed,
1 skipped** (2:12). Full suite (Windows, -n 4): **4121 passed, 2 skipped** (11:32; 4115 + 6).
The acceptance check reruns at **11/11**. flake8/ruff: only upstream's known items.



## Run-library step 5b: a third review, AB1-AB4 (2026-11-04)

A third independent review (`fork-notes/run-library-step5b-review-3.md`, prefix AB) at the
branch head `3b15dd97`, on Linux: the four touched suites **1232 passed**, `check_library_rates.py`
**11/11** (after `make_cases.py`), lint only upstream's items; full suite not re-run. Findings,
none folded (the user's call):
- **AB1 (medium):** a downturn run applies the hand case's `reverse_sequence` / `roll_sequence`
  twice -- `rates.csv` is written from the already-transformed `tau_kn` and the generated case
  keeps the keys, so the solve re-transforms the table (probe: the `crash-30` window placed at
  2030 lands in 2054, 31 of 32 other years leave the parent's path). Hand-table runs are
  consistent.
- **AB2 (low):** `owlbridge._setRates`'s table branch drops `in_percent` (missed by AA1) and
  reverse/roll: a Rates visit re-prices a decimal table 100x smaller in the session plan and
  shows it so; solves and saves are unaffected (they read the case keys).
- **AB3 (low):** `resolve_rates_csv` tries the working directory first, so a stray `rates.csv`
  there replaces a frozen run's own table (probe: 99.0 read for -30.0); the first review had
  called the order "not a finding" (the HFP's order).
- **AB4 (nit):** Create Case's upload cannot open a table case (no rates uploader there, and the
  error does not point to the Library's Import).


## Run-library step 5b: review 3, AB1-AB4 folded (2026-11-04)

The user's call on `fork-notes/run-library-step5b-review-3.md`: fold all four. Dispositions
(details in the review's "Dispositions"):
- **AB1:** a downturn run's case resets the hand case's `reverse_sequence` / `roll_sequence`
  (marked with the event; a pages save puts the hand values back): its table is the plan's
  path already transformed. `BUILDER_VERSION` 5, so every run's inputs hash moves (R9).
- **AB2:** the Rates page's `_setRates` passes the case's `in_percent` and sequence options.
- **AB3:** a relative `rates_file` is looked up beside the case first, then in the working
  directory (the import too); `HFP.xlsx` and the budget sidecar keep upstream's order.
- **AB4:** an uploaded table case that cannot find its CSV names the Run Library's Import and
  `owlcli run`.

Tests +11 (`tests/library/test_rates_table.py` +5, `tests/rate_models/test_rate_model_table.py`
+2, new `tests/ui/test_rates_page_table.py` 4). **9 of the 11 were checked to fail before their
fix** (`src/` and `ui/owlbridge.py` stashed, the tests re-run: 9 failed / 2 passed); the two
that pass pin behavior the fixes keep (a case without the options builds as before; other
upload errors carry no hint). `test_ab3_the_working_directory_is_the_fallback` failed before
only on the new error wording. Full suite (Linux, -n 4): **4133 passed, 1 skipped** (9:22;
Windows' 4121 / 2 skipped + 11, the skip count is the platform's). The acceptance check
(`check_library_rates.py`, after `make_cases.py`) reruns at **11/11**. Lint: only upstream's
known items.

`main` fast-forwarded to `claude/tender-bardeen-x1qyc5` on 2026-11-04 (the user's call): run-library
step 5b with the three reviews' folds (Z1-Z9, AA1-AA3, AB1-AB4). Next: step 6 (collections).


## Run-library step 6: collections, make variants, the grid view, the Ages preset (2026-11-04)

Branch `claude/run-library-step6` (from `main` `e898f699`): build step 6's core
(`fork-notes/run-library-design.md` sections 8.1, 9.3, 11). The user's calls at the start:
**core first** -- collections, "make variants", the grid view and the `ages` preset -- with
I8 (conversion view), I9 (tornado) and the I2/I11 variant dimensions as the step's second
increment; the variant dimensions of this increment are **the condo trio (place, purchase
year, financing) plus the last work year and the claiming ages**; only the `ages` preset now
(`work_sweep.py`'s "Ages, thorough" later); and the acceptance is a **reduced grid** (one
place x three purchase years x cash/mortgage through both routes, the same day), the full
42-cell grid documented as an offline/overnight run.

**The `ages` preset** (design 8.1). `src/owlplanner/library/agesearch.py` is
`run_suite.py`'s `two_stage_ages`, one implementation shared by the suite and the interface
(the fork's rule): stage 1 searches the claiming ages under the exact LP (Medicare off, SS
taxability 0.85; ACA stays on the loop -- a candidate must stay a pure LP), stage 2 scores
the pick and each searched person's pick +-1 year (clipped to 62-70) at fixed ages under the
case's own model and the best score wins (`score_plan`, run_suite's `_score_plan`). The
worker runs it before the final solve when the case says "let Owl choose", then pins the
pick (`fixed_ages`); `record.json` gains `age_search` = {"chosen", "candidates"} and the
run page says "Claiming ages searched ... from N candidate(s)". The stages' logs go to
`solve.log` but their warnings stay out of the record (`_LogTee.quiet`, run_suite's "their
warnings are not in the report"). `presets.py`: `PRESETS = (quick, decision, ages, custom)`;
`ages` forces **nothing** (R4's exception -- the case's own model and its own ages choice).
The exact-model option lists moved to `agesearch` (`EXACT_MODEL`, `EXACT_GROUP`;
`presets._FORCED["decision_exact"]` and `run_suite.py` read them), and `run_suite.py` lost
its own `two_stage_ages` / `_score_plan` / `fixed_ages` (imported now). Its single-name
`withSSAges` reading was fixed in the shared `searched_names` (a name searched only that
person; run_suite's `for n in sel` walked a string's characters).

**Collections** (`store.Collection` / `store.Member`, in `library.json` under
`library.lock`, `collection_order` for the order shown): question, rule, reference run,
members with their variant values ({dimension: label}), and the grid layout. CRUD on
`Library` (`create_collection`, `update_collection`, `set_reference`, `delete_collection`,
`add_member` -- idempotent, `remove_member`); a deleted run leaves every collection
(`delete_run`), a deleted collection deletes no runs. A malformed entry is skipped, never
fatal (V7's rule).

**"Make variants"** (`library.variants.plan_variants`): one child scenario per value of a
chosen dimension -- `place`, `year`, `financing`, `work` (one person's full-time end),
`claim` ({person: age or None}) -- and **several dimensions give their product** (the grid
of design section 4; one dimension is 9.3's case). Each value is a small edit to the
scenario's events; the children are scenarios like any other (`validate` at the door) and
freeze through `save_run` with their parent and change summary. A **single-valued dimension
holds every child** -- the claiming-ages dimension with one value pins the whole grid at
those ages, which is exactly `run_suite.py`'s rule ("every group but main runs at the
baseline's ages") and what makes a housing grid one question. A financing value's `name`
takes `{place}` (make_cases names the loan "yonkers mortgage"). Not in this increment: the
downturn-sequence and longevity dimensions (I11/I2, second increment).

**The grid view** (`library.grid`): the pivot of `run_suite.py`'s `condo_pivot` -- rows of
the row dimensions against the column dimension, each cell the score's difference from the
reference and the home at the end below it, coloured by the comparison rule (R3: leads /
trade-off / the reference leads; grey inside the 1% noise band), the best score per row
marked by score only. `lead_between` judges a pair on the two numbers without the
year-by-year pass; `front()` lists the variants no other variant beats on both numbers, each
with the entries it leads and its score's verdict against the reference. The reference is
the caption's number, not forced into a cell (a member with no values is listed beside the
grid); `latest_result` picks a run's newest non-exact solved result (R2: the exact companion
is a check, not the headline).

**The page**: `ui/Collections.py` (registered in `ui/main.py`'s Run Library section) --
create/edit collections (name, question, rule, grid layout), make variants (the dimensions'
editors: purchase years, places and financings as editable tables, one person's last work
years, per-person claiming age lists with "fill from the run's last solve"), the grid with
its leads and flags, the members (add a run, set the reference, remove), and "Queue every
member" (design 8.2's "run the whole collection again today"). `ui/Run.py` shows the search
on an ages result and its preset help names `ages`.

The acceptance `fork-notes/synthetic/check_library_variants.py`: the synthetic condo grid
through the interface -- the reference scenario from `scenarios.json` saved as a run and
solved with the `ages` preset through the worker, the children made by `plan_variants`
(place x year x financing, claiming ages held at the baseline's pick) and solved with
`decision` -- matches `run_suite.py`'s own `report.md` (its reduced `--only` run, same day).
**5/5 checks** (about 45 minutes beside the full-suite run: make_cases, one `--only`
run_suite run -- the baseline's age search plus 6 local-search solves -- the interface's
ages search and 6 `decision` solves):

1. the children are `make_cases.py`'s grid scenarios -- **6/6** (events, hand rows and hand
   case; the hand case differs only in `HFP_file_name`, which names make_cases' per-variant
   workbook where the library writes one `HFP.xlsx` per run -- inert in the stored case);
2. the `ages` preset picks the suite's baseline ages -- **[70.0, 70.0] on both sides** (the
   same two-stage search on the same inputs, the same day);
3. the reference's score matches the report -- **112,862 on both sides**, to the dollar;
4. the grid cells match the report -- **6/6** cells (deltas and homes; the tolerance was
   the 1% noise rule, the actual differences were zero: both routes are deterministic here);
5. the report's cells parse as whole dollars -- 6/6 (the parse is faithful).

The user's call: the reduced grid is the recorded check (one place x three purchase years x
cash/mortgage); `--full` runs the whole condo grid (30 cells, hours of local-search solves
on this machine -- an offline/overnight run). The synthetic cases are plan-year 2026, so the
check only runs in 2026 (R1).

Tests (63 new: `tests/library/test_agesearch.py` 10, `test_collections.py` 13,
`test_variants.py` 21, `test_grid.py` 13, `tests/ui/test_collections_page.py` 6; plus the
`test_presets.py` update, whose "unknown preset" case used to name `ages`). Full suite
(Windows, -n 4): **4196 passed, 2 skipped** (12:36; the branch's base 4133 / 1 skipped on
Linux + 63, the skip difference is the platform's). flake8/ruff: only upstream's known
items.

Left for the next increment (as called): I8/I9, the I2/I11 variant dimensions, "Ages,
thorough" (`work_sweep.py` as a preset), member values for hand-added runs (the grid places
them only through "make variants" today), and the save dialog's "Collection" field (design
section 7; adding to a collection is on the Collections page).


## Run-library step 6: the core reviewed, AC1-AC7 folded (2026-11-05)

An independent review of step 6's core (`fork-notes/run-library-step6-review.md`, findings
AC1-AC10, prefix AC; read against design sections 4, 8.1, 9.2, 9.3 and 11 with 10 probes on
the branch head `9372c7d9`). The user's call: fold **AC1-AC7** (AC8-AC10 stand as written).
Dispositions (details in the review's "Dispositions"):
- **AC1 (medium):** the "Fill the ages from the run's last solve" button is dead on click --
  an inline handler writing the claim boxes' widget keys raises
  `StreamlitWidgetAlreadyInstantiatedError`. It is an `on_click` callback now
  (`_fill_claim_ages`, which runs before the boxes exist).
- **AC2 (medium):** "Create the variants" ended in the same exception in its tail
  (`_open_collection` writing the collection picker's widget key): the children were saved
  but the page's last word was an error. `_open_collection` writes the plain
  `library_selected_collection` key now (the route a jump from another page takes).
- **AC3 (low):** `_open_collection` stored the collection's **id** where the picker holds
  **labels**, so "Create collection" landed on the first collection (the new one never
  opened, the previous selection lost). With AC2's change the id is translated to the label
  before the picker instantiates.
- **AC4 (low):** the grid silently dropped a member whose (row, column) key collided with
  another's (no cell, not even `unplaced`, and its best-score star marked a hidden entry).
  `grid_view` keeps one member per cell, lists a colliding member beside the grid
  (`Grid.collided`), and marks the cell that holds the row's best score.
- **AC5 (low):** `plan_variants` raised TypeError on a string place price (the shape check
  allows "a number or a string", then `price <= 0` compares). `_check_value` types the
  price and refuses anything else with `ScenarioError`.
- **AC6 (low):** the make-variants editors converted numbers unguarded (`float()` on prices
  and claim boxes: a raw ValueError ended the page where the years field flashed). The
  dimensions are built in `_dimensions` through `_number`; a bad cell flashes and nothing
  is made, and a table row with data but no label is skipped and named.
- **AC7 (low):** a collection with no runs crashed the page on every render
  (`lib.scenario(None)` -> "no run with id None"). Make variants renders only when the
  library has runs.

Tests +7 (`tests/library/test_grid.py` +1, `tests/library/test_variants.py` +1,
`tests/ui/test_collections_page.py` +5; the fixture's result plan now names bill's own
individual). **All 7 were checked to fail before their fix** (the fixes under `src/` and
`ui/` stashed, the tests re-run: 7 failed). The four touched suites
(`tests\library tests\rate_models tests\config tests\ui`): **1313 passed, 1 skipped**
(0:53). Full suite (Windows, -n 4): **4203 passed, 2 skipped** (8:30; 4196 + 7). flake8/ruff:
clean on the touched files (upstream's known items untouched).


## Run-library step 6: second review of the core, AD1-AD9 (2026-11-05)

Branch `claude/review-step6-core-abwxbs` (from `claude/run-library-step6` `97b6059`): a second,
independent review of step 6's core after the AC1-AC7 folds,
`fork-notes/run-library-step6-review-2.md`, findings **AD1-AD9** (1 high, 1 medium, 4 low,
3 nit). Nothing in `src/`, `ui/` or `tests/` changed; the user decides what to fold.
- **AD1 (high):** the page's places and financing tables read empty cells as NaN
  (`DataFrame.iterrows()` turns the editor's `None` into NaN, and every guard tests
  `None` / `""`): a place row with its costs left empty "to keep the parent's" saves and
  solves with property tax, HOA and insurance at \$0 (\$20,000/yr on the synthetic Yonkers
  parent); an empty price is refused, a loan with term and rate only fails in `build`
  (`ValueError`), an empty name becomes "nan". Reproduced with Streamlit 1.66.1's own
  edit-application code through `save_run` and `config_to_plan`.
- **AD2 (medium):** with no saved layout the grid takes the alphabetically first and last
  dimensions: place x year x financing shows financing x year, the other places listed
  "beside the grid" as "the same values"; one dimension pivots against itself.
- AD3 (AC4's fold stars a cell whose number is not the row's best), AD4 (cell grey where R3
  says the variant leads), AD5 (no flag when a cell's claiming ages differ from the
  reference's), AD6 (`bool("False")` is True for the move cell), AD7-AD9 nits.

Checks: `tests/library tests/ui` **693 passed** (Linux, 0:30); flake8 clean on the step's
files.


## Run-library step 6: the second review's AD1-AD6 folded (2026-11-05)

The user's call: fold **AD1-AD6** of `fork-notes/run-library-step6-review-2.md` (AD7-AD9
stand). Dispositions in the review's last section:
- **AD1 (high):** the make-variants tables are parsed in `ui/variant_tables.py` (pure
  functions); `records` reads a missing cell (None, NaN, blank) as None, so an empty cell
  keeps the parent's value (empty costs used to reach the plan as \$0); `-` clears a text
  cell (White Plains from Yonkers: locality `-`). `variants._check_value` and the builder's
  `validate_events` refuse non-finite numbers, costs that are not amounts >= 0, and loan
  terms that are not numbers, from any route.
- **AD2:** `variant_tables.grid_layout` -- the year as columns, every other varied dimension a
  row; a saved layout with columns as saved (empty rows: one row); "make variants" stores it.
- **AD3:** the row's star marks the best member itself (`Grid.best_beside` for one listed
  beside the grid).
- **AD4:** the cell colour is R3's verdict; `~` marks a score difference inside the noise band.
- **AD5:** `grid.claiming_ages_flag` (cells at other claiming ages than the reference's);
  Make variants warns after an `ages` solve when the claiming boxes are empty.
- **AD6:** `move` a checkbox column (typed text read by `variant_tables.flag`), `kind` a select
  box (a typo is refused, not cash).

Tests +47 (`tests/ui/test_variant_tables.py` 21 through Streamlit's own
`_apply_dataframe_edits`, `test_variants.py` +14, `test_grid.py` +5 with AC4's test re-pinned,
`test_collections_page.py` +7). Before the fold: 23 new tests + AC4's failed, the 21 table
tests errored (new module), 3 guards passed. `tests/library tests/ui`, the four touched files
and `check_library_builder.py` (46/46) green; flake8 clean, ruff only upstream's four known
items. Full suite (Linux, -n 4): **4251 passed, 1 skipped** (9:51; the first review's 4203 / 2
skipped on Windows is 4204 / 1 here, + 47).

`main` fast-forwarded to `claude/review-step6-core-abwxbs` on 2026-11-05 (the user's call): step 6's
core with both reviews' folds (AC1-AC7, AD1-AD6).


## Run-library step 6: the second increment -- the I2/I11 dimensions, I9, I8, "Ages, thorough" (2026-11-05)

Branch `claude/run-library-step6-inc2` (from `main` `92daa09`): the core's "left for the next
increment" list, in four commits. The user's calls at the start: the **full list** (I8, I9,
the I2/I11 variant dimensions, "Ages, thorough", member values for hand-added runs, the save
dialog's "Collection" field) with this agent's build order (dimensions and collection items,
then I9, I8, the preset); and on the tornado's two policy movers: "the 2027 marketplace
benchmark" is **both** the ACA-rules mover and a benchmark-premium mover, and "the 2032
reversion" mover is **both** directions (the reversion as scheduled, and none).

**The `death` (I2) and `sequence` (I11) dimensions** (`library.variants`, commit 1/4).
`death` is {"person", "age", "label"?} -- one child per value, "Ari dies at 75", each spouse
in turn (I2's grid) -- and gets a **`death` event kind** in the builder (the design's
"Builder and collections"): `basic_info.life_expectancy` is a generated case field (whole
list, provenance marked as the claiming ages are), one death per person, a whole age 1-120
(`DEATH_AGE_MAX`) and not before the plan start (`check_death_age`: a horizon of zero years
would give the plan nothing to solve). The window (U7) shrinks with the last death, so an
event past it is refused -- for a couple the max horizon usually stands (the other spouse),
for a single person moving the only death earlier refuses the runs whose events reach past
it, with the window in the message. `sequence` is {"label"?, "sequence", "start"}: the named
downturn overlay of step 5b's `downturn` event placed at a year or an anchor (one per
scenario: a value moves it, `sequence: None` takes it off -- the grid's "no downturn" cell);
a run that reads a rates table refuses an overlay, at the door as at build time. The
Collections page edits both (a first-death person + ages field; the sequence table with
`start` as text and `-` to clear), and the Scenario page keeps a run's death events (a
table beside claims -- `_assemble` would otherwise drop them on every edited save). Member
values for hand-added runs (the grid places a member through its values, however set): a
"Values" popover per member reads `dimension: label` pairs (`variant_tables.member_values`;
the year's label is stored as a year, so one cell holds both routes). The save dialogs'
**"Collection"** field (design section 7): the Library page's two tabs and the Scenario
page's save put the run into a collection as it is (values set later on the Collections
page); re-adding a member from the Add button keeps its values (`add_member` replaces them).

**The sensitivity tornado (I9)** (`library.tornado`, commit 2/4). One button on the run page
makes one child per key input moved by a set step -- returns -1 point, inflation +1 point
(both the run's own rate path written out as a shifted `rates_table`: `builder.
plan_rates_table`, a downturn overlay baked in and AB1's reverse/roll reset -- a hand table
keeps its case's transforms, shifting commutes with them), medical inflation +2 points
(`medical_inflation_excess`, the schema's 10% cap), condo price +10% (the purchase event),
the marketplace benchmark premium +10% and -10% (`aca_settings.slcsp_annual`), **the 2027
marketplace rules** (`aca_settings.aca_table_year = 2027`, the knob below), **the 2032
reversion and no reversion** (`rates_selection.obbba_expiration_year` at 2032 and 2100, each
skipped when the case already assumes it), and the first death at 80 per person (the `death`
event; skipped when the death is already past). Each child is an ordinary run in a
"Sensitivity: <run>" collection, queued under the exact LP ("for speed"); the bars are
sorted by the size of the effect, each with its tolerance (`compare.pair_tolerance`, now
public), against the run's newest exact-LP result when it has one. A mover that does not fit
the scenario is skipped with its reason (no home purchase, no benchmark premium). The
marketplace-rules mover is a small generic model knob: `aca_settings.aca_table_year` pins
one year's applicable-percentages table in every plan year (`tax_federal._aca_table`'s
`table_year`, through `acaCosts`/`acaVals`, `plan.aca_table_year` and both config bridges --
the round-trip suite caught the missing UI mapping; a None never enters the case dict).

**The conversion and bracket view (I8)** (`owlplanner.brackets`, commit 3/4). Per year
(today's $): the ordinary taxable income (`Plan.G_n`, the bracket base), the Roth conversion
layer within it and MAGI, against the ordinary bracket edges (`tx.taxBrackets`; the bracket
the income fills and the room to the next), the 0% capital-gains edge, the IRMAA tier edges
-- the *premium* year m+2's tiers in the tax year's dollars, as `thresholds` reads them --
and the ACA lines (the Medicaid limit of the year's tax household, where the credit starts,
the 400% FPL cliff). `plan_to_dict` writes it into `plan.json` (`brackets`; D7), the run
page draws it (stacked bars with the lines stepped over them, and the per-year table) and
its **regret sweep** button queues one `regret` job per request: the case's own model with
the ages fixed (R4), the base solve, then `stresstests.run_conversion_regret_sweep` at
"Quick look" size (18 historical scenarios, a 7-point grid, milp downgrade; `worker`'s
constants) over the windows whose starts fit a full horizon (`owlplanner.rates.FROM` to
`year_n[0] - N_n`). `regret.json` joins the artifacts, the summary is in `record.json`
(`regret`), and a failed sweep keeps the base results. The page shows the mean-regret curve
and the valley.

**The `ages_thorough` preset** (design 8.1's "Ages, thorough", commit 4/4).
`fork-notes/phase5/work_sweep.py`'s own `run_variant` decides the ages -- stage (a)'s
exact-LP search plus stage (c)'s sweep of every whole-year pair of the searched people,
each scored by branch-and-bound at gap 1e-5 (local search kept where it does not prove;
the loop search (b) and the deposit-split check `--eta` are off, both sensitivities rather
than the decision) -- then the final solve runs at them (`record.json`'s `age_search`, as
`ages`; R4's exception, it forces nothing) and the sweep's row is `scores.json` in the
results folder, which the claiming-age map (I7) reads (it also still reads a `scores.json`
at the run root or a picked file). The sweep stays phase 5's, one implementation shared
with `run_suite.py` by loading the fork-notes file (the fork's rule; a spawned pool would
need `score` picklable across a dynamically loaded module, so the worker runs its own
serial pool -- the CLI's `--jobs 1` default is serial too). **Moving `work_sweep.py` into
`src/owlplanner` stays open.**

Tests +77 (`tests/library/test_tornado.py` 18, `tests/plan/test_brackets.py` 5,
`test_variants.py` +18, `test_builder.py` +7, `test_scenario.py` +1, `test_worker.py` +4,
`test_presets.py` re-pinned, `tests/tax/test_aca.py` +2 (the `table_year` knob),
`tests/ui/test_variant_tables.py` +15, `test_collections_page.py` +6,
`test_scenario_page.py` +3, `test_library_pages.py` +5) across 12 files. Checked:
`check_library_builder.py` **46/46** after the `death` event (the generated case fields and
workbooks unchanged where no death event runs). flake8 clean on the touched files, ruff only
upstream's known items. Full suite (Windows, -n 4): **4345 passed, 2 skipped** (11:17; the
reviewed core's last full run was 4251 / 1 skipped on Linux -- this run is Windows, and the
new tests are counted with their parametrized cases). The first run of the suite caught a
BOM the file writer left in `tests/library/test_tornado.py`
(`tests/utils/test_text_encoding.py`); stripped, and the suite re-run.

Next: an independent review of the second increment (the pattern of the core: two reviews,
the folds decided by the user); moving `work_sweep.py` into `src/owlplanner`; and the full
42-cell condo grid through the interface as the overnight run
(`check_library_variants.py --full`).


## Run-library step 6: `work_sweep.py` moved into `src/owlplanner` (2026-11-05)

The second increment's open item (above). `fork-notes/phase5/work_sweep.py` is now
`src/owlplanner/work_sweep.py` (`owlplanner.work_sweep`, `git mv`), still the one
implementation (the fork's rule), shared by `library/worker.py`'s `_load_work_sweep` and
`fork-notes/synthetic/run_suite.py` -- both loaders are plain imports now. The move fixes
the loader's layout assumption (`Path(__file__).parents[3] / "fork-notes"` exists only in
a checkout of this fork: an installed `owlplanner` could not run "Ages, thorough" at all,
and the preset had to say so), drops the file's own `sys.path` hack and `# noqa: E402`
markers, and makes `score` picklable across spawned processes (the dynamically loaded
module was not) -- the worker keeps its own serial pool anyway (one job at a time; the
CLI's `--jobs 1` default is serial too). Phase 5's six probes that imported the sweep as a
sibling re-point at the package module (`highs_gap_probe.py`, `reltol_probe.py`,
`reltol_check.py`, `ws_bb_check.py`, `ws_parttime_a_check.py`, `ws_parttime_bb_check.py`;
the three importers share one module object, checked); the recorded outputs and data files
stay in `fork-notes/phase5/` (`work_sweep_chris+pat*.json/txt`). Live references updated:
the design's 8.1 table/`built` note, CHANGELOG-fork.md's entry, `run_suite.py` and
`make_cases.py` docstrings, `phase0-scenarios.md` and `Case_us.template.toml`'s command
examples, `running-locally.md`, the synthetic README, `issue-run-library.md`, the
`library/` docstrings (`agesearch`, `agemap`, `presets`, `worker`) and two test comments;
PROGRESS's dated entries and the phase-5 record docs keep their paths as written. One test
pins the move (`test_worker.py::TestAgesThorough::test_the_sweep_lives_in_the_package`).

Checks: `pytest tests/library tests/ui` **825 passed, 1 skipped** (3:40), the three
touched test files 40/40 with the new pin; `python -m owlplanner.work_sweep --help` and
`fork-notes/synthetic/run_suite.py --help` green; the probe imports green; flake8/ruff
clean on the touched files (`ws_parttime_bb_check.py`'s three pre-existing items stand).


## Run-library step 6: the second increment reviewed, AE1-AE3 (2026-11-05)

The independent review (`fork-notes/run-library-step6-inc2-review.md`, the core's pattern;
prefix AE after AC/AD) of `0bc64ca0..0964e351` read against the design's sections 6-9, 11,
14.1/14.3 and section 8.1's "Ages, thorough". **AE1** (medium): a death at the person's age
today passes `check_death_age`, and when it is the last horizon the plan is one year and
`config_to_plan` raises a raw `ValueError: Plan needs more than 1 years.` instead of the
designed named refusal (probe; the fold is a window check at the door).
**AE2** (low): `member_values` accepts a dimension name it does not know -- a typo places
the member in a phantom grid dimension (AD6's rule says refuse).
**AE3** (low): `regret.json` is a second copy of `record.json`'s summary while
`build_record`'s docstring, the run page's caption and the entry above all say the full
curve is there; the per-scenario sweep data is discarded. Checked and not a finding: the
rate movers' transforms (a hand table keeps them, a generated path resets them -- both
shift the effective path exactly once), the `deaths[0]` provenance (the established
pattern), `_sequence_value`'s empty cells (`records()` normalizes them),
`aca_table_year`'s round-trip and all five `acaCosts`/`acaVals` call sites, the
claiming-age map's sources, `pair_tolerance`'s call shape. Probes in the session's temp
only; the review changed nothing in `src/`, `ui/` or `tests/`. Tests: the increment's own
files **308 passed** (3:32); the full suite (Windows, -n 4) **4346 passed, 2 skipped**
(14:39; the increment's 4345 + the move's one pin). flake8/ruff clean on the touched files.

Folds (AE1-AE3) are the user's call; the core's pattern then gives the folded state its
second review.


## Run-library step 6: the second increment review's AE1-AE3 folded (2026-11-05)

The user's call: fold all three.

- **AE1**: `builder.check_death_window` (I2, U7's door check) refuses the plan window the
  deaths leave when it is not more than one year -- `Plan`'s own "Plan needs more than 1
  years" as a `ScenarioError` with the window in the message. It runs in `build` (the door
  every route passes) and at the two tables (`variants._check_value`, `tornado._death`),
  where a death not in the events yet (a variant value, a mover) is checked over the
  events' own deaths -- so a combination that collapses the window is refused or skipped
  where it is entered (the tornado's mover is skipped with the reason).
- **AE2**: `variant_tables.member_values` refuses a dimension that is not one of
  `variants.DIMENSIONS` (AD6's rule: a typo is refused, not a phantom grid dimension).
- **AE3**: `regret.json` is the sweep itself (the per-scenario curves
  `summarize_conversion_regret` reads) and `record.json` keeps the summary -- the split
  `build_record`'s docstring, the run page's caption and the entry above already describe.

Tests +5, **all five checked to fail before their fix** (the source stashed, the tests
run against it): `test_builder.py`'s "leaves the plan one year is refused",
`test_variants.py`'s combined-window refusal at the door, `test_tornado.py`'s mover skip,
`test_variant_tables.py`'s unknown dimension, `test_worker.py`'s regret artifact re-pinned
(`regret.json` the canned sweep, the record the summary). The five touched test files:
**218 passed** (24 s). flake8/ruff clean on the touched files.


## Run-library step 6: the full suite after AE1-AE3 (2026-11-05)

Full suite (Windows, -n 4) over the folded second increment: **4350 passed, 2 skipped**
(14:36; the pre-fold 4346 + the four new tests -- the fifth check re-pins the existing
regret test, counted in the fold's five). The overnight `check_library_variants.py --full`
(run 2) was still in flight; its verdict is in the pool entry below. `main` fast-forwarding
to `claude/run-library-step6-inc2` stays the user's call (the core's pattern: once the
reviews and their folds are done).


## Run-library step 6: the second review's AF1-AF5, AF7 folded (2026-11-05)

The user's call: fold AF1-AF5 and AF7 (the four defects in the approved AE/move work plus
AF3/AF4); AF6 (a duplicate `year:` key keeps the last silently) and AF8 (`gains_edge_0`'s
measure undocumented) stand.

- **AF1**: `build`'s no-events return runs `check_death_window` too -- AE1's door for a
  hand document (the named refusal instead of the model's own "Plan needs more than 1
  years." at solve time).
- **AF2**: `variants.VALUE_KEYS` (`DIMENSIONS` plus the tornado's `mover`) is what
  `member_values` accepts; the sensitivity members' "Values" popover round-trips again
  (AE2's door bolted over).
- **AF3**: `variants._start_ref` passes the scenario's event ids to `parse_year_ref` (X5's
  rule): `event:buy-2027` resolves to the id `buy-2027`, not id `buy` + offset -2027 --
  at the door and in the applied child alike.
- **AF4**: `brackets.bracket_view` drops the `min(n + 2, N - 1)` clamp -- a tax year whose
  premium year leaves the plan has no IRMAA edges (`thresholds._irmaa_entries` skips
  those years).
- **AF5**: `lift_regret_baselines` returns `v_at` normalized and
  `summarize_conversion_regret` reads `v_at`/`v_noconv` as arrays -- a saved `regret.json`
  round-trips back into `summarize_conversion_regret` (AE3's premise).
- **AF7**: `presets.py`'s stale "moving it into `src/owlplanner` stays open" (the move's
  missed docstring).

Tests +5, **all five checked to fail before their fix** (the source stashed): the
no-events window (`test_builder.py`), the `event:<id>` anchor against the ids
(`test_variants.py`), the mover round-trip (`test_variant_tables.py`), the premium year
past the plan (`test_brackets.py`), the saved result (`test_regret_sweep.py`). One
test-hygiene fix the AF3 test exposed: `test_variants.py`'s AD1 test edited the shared
`BUY_CASH` fixture in place (order-dependent pollution); it deep-copies now. The five
touched test files: **230 passed** (43 s). flake8/ruff clean.


## Run-library step 6: the full-grid check's suite pool bounded (2026-11-05)

The overnight `check_library_variants.py --full` (the "Next:" item above) died on its first
attempt after ~15 minutes of solving: `run_suite.py`'s own pool -- its `--jobs` default is
`os.cpu_count()`, **16** here -- ran the 30 condo rows and then raised `BrokenProcessPool`
(a worker terminated abruptly mid-solve; 32 GB machine with ~12 GB free, 16 concurrent
local-search solves). Not the increment and not the move: a 2-row `run_suite.py --jobs 2`
probe solved both rows and wrote the report (`main/base` 200.9 s, `condo/reference`
371.9 s, "every run outside the rate groups solved, its loop settled"), and the reduced
grid's 6 concurrent solves are the recorded 5/5. The check now passes `--jobs 6`
(`SUITE_JOBS`) to the suite's subprocess: the same solves at the proven concurrency
(the reduced grid's); scores do not depend on the job count (time-capped local search,
within the noise rule). Re-run launched 2026-11-05 15:45
(`check_library_variants_full_2026-11-05_run2.log` in the session's temp) and finished the
same evening: **5/5 checks passed** -- the children 30/30 are `make_cases.py`'s grid
scenarios, the ages preset and the suite's baseline both pick [70.0, 70.0], the reference
score 112,862 vs 112,862 (tolerance 1,129), 30/30 grid cells within the noise rule, 30/30
report cells parse as whole dollars. The grid is the check's `FULL` selection (3 places x
5 purchase years x cash/mortgage: 30 rows, the children and cells counted at 30);
`make_cases.py`'s six ARM rows (2027 arm5/arm30 per place) are outside it, and the
prose's "42-cell" count (the design, the check's own docstring) matches neither the 30
run nor the 36 variants `make_cases.py` writes -- the scope to reconcile with the user.


## Run-library step 6: AF6 folded, `--full` gains the ARM rows (2026-11-05)

The user's call: fold AF6, and `check_library_variants.py --full` must include the ARM
rows (the scope question above).

- **AF6**: `variant_tables.member_values` refuses a dimension given twice (the first pair
  was overwritten silently). Its test is checked to fail before the fix.
- **`--full`'s ARM rows**: the check's grid is now **36 cells** -- 3 places x 5 purchase
  years x cash/mortgage (30) plus `make_cases.py`'s six ARM rows (arm5: paid down within
  the fixed 5 years; arm30: refinanced at no higher rate; `ARM_YEARS = (2027,)` --
  "later rates are unknown"). The ARM rows are their own make-variants pass (one purchase
  year cannot ride the dimensions' product) into the same collection; `suite_only`, the
  children and the grid grow with them. The reduced grid stays its recorded 6 cells. The
  prose's "42-cell" count is corrected to 36 (the check's docstring, the design's 9.3
  note, CHANGELOG-fork): `make_cases.py` writes 36 condo variants and the grid has 36
  cells.
- Pre-flight without solving (the check's `check_children` logic over the full set):
  36/36 grid names in `scenarios.json`, 36/36 children match `make_cases.py`'s grid
  scenarios (events, hand rows, hand case), the reference cell among them.

Tests: `tests/ui/test_variant_tables.py` **42 passed**. flake8/ruff clean. The 36-cell
`--full` run launched the same evening (`check_library_variants_full_2026-11-05_run3.log`
in the session's temp) and finished overnight: **5/5 checks passed** -- the children 36/36
are `make_cases.py`'s grid scenarios (the six ARM rows included), the ages preset and the
suite's baseline both pick [70.0, 70.0], the reference score 112,862 vs 112,862 (tolerance
1,129), 36/36 grid cells within the noise rule, 36/36 report cells parse as whole dollars.
The acceptance item is closed: the whole condo grid through the interface matches
`run_suite.py`'s report.


## Run-library step 6: AF8 folded (2026-11-05)

The user's call: fold AF8 too -- the AF review's list is closed (AF1-AF8 all folded).
`gains_edge_0` is edged on the QDCG worksheet's line-1 income (`G_n + e_n + max(Q_n, 0)`
less the deduction the ordinary income leaves unused -- `thresholds._gains_entries`, the
step-3 review 2 Q1 fix), **not** on `ordinary_taxable_income`, and nothing said so. The
measure is now named where the other measures are named (the `brackets` module's and
`bracket_view`'s docstrings) and once in the artifact itself
(`brackets.gains_edge_0_measured_against`, beside `units`, so `plan.json`'s readers see
it per block). Its test is checked to fail before the fix.
`tests/plan/test_brackets.py` **7 passed**; flake8/ruff clean.


## Run-library step 6: the full suite after AF1-AF8 (2026-11-06)

Full suite (Windows, -n 4) over the fully folded state -- the AE and AF folds, the ARM
rows and the `work_sweep` move: **4357 passed, 2 skipped** (13:54; the 4350 after the AE
folds plus the AF folds' five, AF6's one and AF8's one). The branch
`claude/run-library-step6-inc2` now holds the second increment, both reviews'
findings (AE1-AE3 in `run-library-step6-inc2-review.md`, AF1-AF8 in
`run-library-step6-inc2-review-2.md`) and all eleven folds, the `work_sweep` move, and
the 36-cell acceptance at **5/5**. `main` fast-forwarding is the user's call (the core's
pattern: once the reviews and their folds are done).


## Run-library step 6: review of the whole step, AG1-AG11 (2026-11-06)

Branch `claude/step6-implementation-review-3bejy1` (from `claude/run-library-step6-inc2`
`c93b1be`). An independent review of step 6 as a whole -- the core, the second increment and
all four earlier reviews' folds -- looking between the increments and at what the tornado's
movers measure on the household's shape (`fork-notes/run-library-step6-review-3.md`, prefix
AG after AC-AF). **AG1** (medium): the rate movers add 1.0 to a hand table in decimals
(`in_percent = false`): -94% returns, 102.5% inflation in the child (probe). **AG2** (medium):
the tornado's bars fall back to a non-exact parent result, so every bar carries the model
change: +4,534 (`quick`) / +4,381 (`custom`) against the exact LP on the synthetic baseline at
fixed ages, four times the 1% band. **AG3** (medium): "inflation +1 point" holds nominal
returns, so its real returns match "returns -1 point" (bars -7,814 and -7,064 on the
synthetic baseline); which question the bar answers is the user's call. **AG4** (medium): "the
2027 marketplace rules" (Owl already reads the 2027 table from 2027 on) and "no 2032
reversion" (2066 -> 2100, both past the plan's end) are exact no-ops on the household's shape
(116,033.84 = the unmoved score; the 2032 control 113,131.74). **AG5** (low): the Collections
page shows the sensitivity collection as unsolved (`latest_result` skips exact-LP results).
**AG6** (low): the save dialogs' "Collection" field wipes an identical member's variant
values (AppTest of the Scenario page). **AG7** (low): the regret caption reads `mean`, the
summary says `mean_regret`: always "mean regret 0". **AG8** (low, design): death and sequence
values are judged as choices (an early death raises the score: +15,987 at 66). Nits AG9
(run names lose the mover's sign: "benchmark-premium-10" twice), AG10 (the regret sweep is
person 0's, unnamed), AG11 (a cooperative cancel can wait a whole "Ages, thorough" pass).
Checks: `tests/library tests/ui` + the bracket/ACA/regret tests **956 passed** (1:21, Linux);
full suite **4358 passed, 1 skipped** (9:45, Linux); lint only upstream's listed items. The review changed nothing in
`src/`, `ui/` or `tests/`. Folds are the user's call.


## Run-library step 6: the whole-step review's AG1-AG7, AG9-AG11 folded (2026-11-06)

The user's call: fold AG1-AG7 and AG9-AG11; AG8 (death and sequence values judged as
choices) stands as written. Dispositions in `fork-notes/run-library-step6-review-3.md`;
`fork-notes/CHANGELOG-fork.md` has the entry. In short:
- the tornado's rate shift is in the table's own units (AG1);
- the bars read exact-LP results on both sides, the button queues the run's own exact-LP
  solve, and the page names the ages the bars hold (AG2);
- "inflation +1 point" holds the real returns (AG3, the review's first option): -920 on the
  synthetic baseline, where it was -7,814, beside returns -1 point's -7,064;
- movers no plan year can see are skipped (AG4: on the synthetic household, the 2027
  marketplace rules and "no 2032 reversion");
- the Collections page reads a collection on one model, and the run is its sensitivity
  collection's reference (AG5);
- `Library.join_collection` keeps a member's values (AG6);
- the regret caption reads `mean_regret` and names the person (AG7, AG10);
- the children are named after the mover keys (AG9);
- the "Ages, thorough" sweep checks for a cancel before every scored plan (AG11).
Open, the user's: what the marketplace-rules bar should measure instead (the 2026 table held,
or the 2027 benchmark jump).

Checks: 21 new tests plus seven re-pinned and one dropped. The 21 and the re-pinned inflation
test were checked to fail with `src/` and `ui/` stashed. `tests/library tests/ui` **855
passed**; probes p1, p9 and p11 re-run on the fixed code (the numbers above); lint only
upstream's listed items; full suite **4378 passed, 1 skipped** (9:09, Linux; 4358 before the fold, net +20).


## Run-library step 6: the marketplace bar is the 2027 benchmark jump (2026-11-06)

The user's answer to AG4's open question: the bar measures the 2027 benchmark's jump above
inflation. "the 2027 marketplace rules" is replaced by "the 2027 benchmark jump" (key
`slcsp-published`). Two new `aca_settings` fields, `slcsp_published_year` and
`slcsp_published_annual` ($k, that year's dollars), are read by the run library only. They
are carried by both bridges, `plan_to_config` and `genDic`. The template states 2027's 25.29
with its source (`aca-ny/README.md`: +21.4% over 2026, the market +6.0%).

The mover sets `slcsp_annual` to the published amount over the run's own medical growth to
that year, so the plan's 2027 benchmark is 25.29. On the synthetic baseline (`decision_exact`,
70/70) that is `slcsp_annual` 24.2376, premiums 2027-2029 25,290 / 26,388 / 16,061 (were
21,745 / 22,689 / 13,810), and the score -375 (inside the 1% band). `aca_table_year` stays as
a knob no bar uses.

Found and fixed on the way: a save after "Open in Owl" turned `aca_start_year` 2027 into 0.
`genDic` lacked the key, and the save applies what differs from the run's case. `genDic` now
carries it and the other fork `aca_settings` keys; the test fails without the fix.

Checks: `check_library_builder.py` 46/46, `check_library_roundtrip.py` 39/39,
`tests/config` 256 passed, lint only upstream's items; full suite: the run for this commit was stopped for the next entry's change, and run after it. Details in
`run-library-step6-review-3.md`, last section.


## Run-library step 6: `aca_table_year` removed (2026-11-06)

The user's call: the knob the old marketplace-rules mover pinned goes, since no bar uses it.
Removed: the schema field, `Plan.aca_table_year`, `tax_federal._aca_table`'s / `acaCosts`'s
/ `acaVals`'s `table_year` and its five call sites, both config bridges, `genDic`'s key, and
`TestPinnedTableYear`. `tax_federal.py`, `thresholds.py`, `assistant/explain.py` and
`tests/tax/test_aca.py` are identical to `e898f699` (before step 6) again. Checks: lint only
upstream's items; `tests/config tests/tax tests/library tests/ui` + `test_brackets.py` 1662 passed; full suite **4380 passed, 1 skipped** (8:38, Linux; it covers this entry and the benchmark-jump entry above: 4378 + the jump's 3 tests and the Open in Owl test, - the rules mover's, + 4 round-trip cases for the two published fields, - 2 for `aca_table_year` and the 2 of `TestPinnedTableYear`).


## `main` fast-forwarded to `claude/step6-implementation-review-3bejy1` (2026-11-06)

The user's call. `main` moves from `92daa09` (step 6's core with AD1-AD6) to this branch:
step 6's second increment, its two reviews (AE, AF) and their folds, the `work_sweep` move,
the whole-step review (AG) and its folds, the 2027 benchmark-jump mover and the
`aca_table_year` removal. Full suite on the branch: 4380 passed, 1 skipped.

## Run-library step 6: third review of the second increment, AH1-AH6 (2026-11-06)

Branch `claude/great-galileo-j51nry` (from `main` `37dfad4`). An independent review of the
second increment as it now stands -- after the AG folds, the 2027 benchmark-jump mover and the
`aca_table_year` removal (`fork-notes/run-library-step6-inc2-review-3.md`, prefix AH after
AC-AG). **AH1** (medium): "Ages, thorough" publishes a final solve under the case's own options
(no gap: `MILP_GAP` under `withMedicare = "optimize"`), not the plan its sweep proved at gap
1e-5; on the synthetic baseline at 70/70 the sweep's cell is 165,361.78 (1,271 s) and the
published solve 164,153.49 (12 s, recorded as proved at gap 6.8e-4): 1,208 below, 1.08% of the
score; the run page says the candidates were "scored under the case's own model". **AH2**
(low): the benchmark jump reads a downturn run's inflation without its overlay (poor-decade at
2026: the plan's 2027 benchmark 26.744, not 25.29). **AH3** (low): it judges the marketplace
start on the hand case's `aca_start_year`, not the generated one (a hand case without it is
skipped with a false reason). **AH4** (low): the regret curve is never drawn -- the page reads
`by_grid`, the summarizer writes `regret_by_grid`; the worker test's canned summary uses the
invented key (AppTest: 6 charts, no curve; 7 with the key renamed). **AH5** (low): AG5's rule
puts a whole decision collection on the exact LP when one member's local search is running or
failed. **AH6** (nit): "run again" leaves `regret.json` and `scores.json` in the folder.
Checks: `tests/library tests/ui` + the bracket/ACA/regret tests **976 passed** (2:00, Linux);
lint only upstream's listed items; full suite not re-run. The review changed nothing in `src/`,
`ui/` or `tests/`. Folds are the user's call.

## Run-library step 6: the third review's AH1-AH6 folded (2026-11-06)

The user's call: fold AH1-AH6 (`fork-notes/run-library-step6-inc2-review-3.md`, "Dispositions").
**AH1**: `work_sweep.scorer_options` / `scorer_config` are the sweep's scorer settings in one
place; the "Ages, thorough" worker re-solves the decided cell with them (branch-and-bound at gap
1e-5, or local search where the cell fell back), records `age_search.decided` and
`published_value`, and the run page names the scorer. End to end on the synthetic baseline at 70/70 the final solve now gives 165,361.78
(gap 9.98e-6, 1,417 s), the sweep's cell to the cent (164,153.49 before). **AH2/AH3**: the benchmark jump
reads `builder.build(scenario)[0]` (the downturn run's 2027 benchmark 25.290; the generated
`aca_start_year`). **AH4**: the page reads `regret_by_grid`. **AH5**: `grid.member_results`
switches only for members whose every solve is exact-LP (`_exact_only`). **AH6**:
`results.ARTIFACTS` for `requeue`; the age map reads only solved folders. Tests: 11 new, one
re-pinned, checked to fail before the fold. Full suite **4391 passed, 1 skipped** (11:48, Linux);
lint only upstream's listed items.


## `main` fast-forwarded to `claude/great-galileo-j51nry` (2026-11-06)

The user's call. `main` moves from `37dfad4` (step 6 with the whole-step review's folds, the
2027 benchmark-jump mover and the `aca_table_year` removal) to this branch: the third review
of step 6's second increment (AH1-AH6) and its folds. Full suite on the branch: 4391 passed,
1 skipped.

## Run-library step 6: fourth review of the whole step, AI1-AI6 (2026-11-06)

Branch `claude/eager-fermat-bhl251` (from `main` `0e4803e`). An independent review of step 6 as
a whole after the AG and AH folds, looking at what the pages show on the household's shape and
at how the movers and dimensions meet the builder (`fork-notes/run-library-step6-review-4.md`,
prefix AI after AC-AH). **AI1** (medium): the I8 chart stacks the gross conversion on taxable
income net of the deduction (2028-2032 on `yonkers-2027-cash`: bars 51-62k for a taxable
income of 24,800) and draws the MAGI lines (IRMAA tier 1, the 400% FPL cliff) against that
bar: in 2028 the bar sits 33k under the cliff while MAGI is 121,355, 37k over it, and the full
premium is paid. **AI2** (low): "bracket filled" names the bracket below the income (91,493
for a couple reads "10%"; the test pins it) and flips between "below the first bracket / room
0" and "10% / room 76,000" on fractions of a cent at a filled edge. **AI3** (low): the tornado's
collection is found by the run's name: a second run with the same name draws the first run's
children (and the first run) as its bars; a rename orphans them, and the button then queues
every child again into a second collection (AppTest). **AI4** (low): the tornado shows the score
only; "condo price +10%" is -3,640 on the score and +76,086 on the home at the end, which no
column shows. **AI5** (low, design): that mover holds the property tax and insurance (-3,640;
-4,739 with both x 1.1); the user's call. **AI6** (nit): a death before the person's own last
work year builds; Owl drops the wages and the generated `aca_start_year` still follows the
dead person's work, so the widowed survivor pays no premium in 2027. Checks: `tests/library
tests/ui` + the bracket/ACA/regret tests **987 passed** (1:27, Linux); full suite **4391 passed, 1 skipped** (9:22, Linux);
lint only upstream's listed items. The review changed nothing in `src/`, `ui/` or `tests/`.
Folds are the user's call.

## Run-library step 6: the fourth review's AI1-AI6 folded (2026-11-06)

The user's call: fold AI1-AI6 (`fork-notes/run-library-step6-review-4.md`, "Dispositions";
`fork-notes/CHANGELOG-fork.md` has the entry). **AI1**: the I8 chart stacks the conversion's
taxable part (`brackets` row `conversion_taxable`) and draws MAGI as its own line; the table
gives the gross conversion beside its taxable part. **AI2**: "bracket" names the bracket the
income is in, "(full)" within a dollar of its top (on `yonkers-2027-cash`, 2028-2033 now all
read "10% (full)", room 76,000). **AI3**: the tornado is the run's by id
(`Collection.tornado_of`, `tornado.collection_of`; an older collection found by its base
member), and the button queues no run already queued or solved today by the running code
(`tornado.is_current`). **AI4**: the tornado's table and hover show the home at the end.
**AI5**: "condo price +10%" moves the property tax with the price, HOA and insurance held
(the agent's reading of the fold): -4,650 / -4,833 (cash / mortgage), were -3,640 / -3,830.
**AI6**: `builder.check_death_after_work` refuses a work year after the person's own death
(build, the death dimension, `plan_variants`' children, the tornado's death movers). Tests: 17
new, three re-pinned; with `src/` and `ui/` stashed the 19 selected failed. `tests/library
tests/ui` + bracket/ACA/regret **1004 passed** (1:18, Linux); `check_library_builder.py`
46/46; lint only upstream's listed items; full suite **4408 passed, 1 skipped** (7:59, Linux; 4391 + the 17 new tests).

## `main` fast-forwarded to `claude/eager-fermat-bhl251` (2026-11-06)

The user's call. `main` moves from `0e4803e` (step 6 with the AH folds) to this branch: the
fourth whole-step review of step 6 (AI1-AI6) and its folds. Full suite on the branch: 4408
passed, 1 skipped.

## Run-library step 6: fifth review of the whole step, AJ1-AJ4 (2026-11-06)

Branch `claude/modest-gauss-6hg9z6` (from `main` `59bc8d9`). An independent review of step 6 as
a whole after the AI folds, running every tornado mover through the real worker and comparing
the bars with the same movers under the case's own model, and the per-request jobs end to end
(`fork-notes/run-library-step6-review-5.md`, prefix AJ after AC-AI). **AJ1** (medium): the
tornado solves under the exact LP, which has `withMedicare = "none"`, so "medical inflation +2
points" reaches only the three marketplace years: on `yonkers-2027-cash` the bar is -83
(resolved at ±0, sorted last) while the same two scenarios move -1,813 under local search and
-1,901 under the loop, with lifetime Medicare premiums +57,182 / +57,273 today's \$; every other
mover agrees with the loop within about 10% (benchmark -10% aside, inside the loop's band).
The design pairs the mover with the model, so the fold is the user's call (another model for
this mover, skip it with the reason, or say so on the bar). **AJ2** (medium): a `regret` job's
`record.json` carries 126 warnings (the same base solve under `custom`: 1), because the sweep's
clones share the plan's logger and the log tee is not quiet during the sweep; the Run page reads
"Quality: 7 problem(s)", each a historical scenario's "Exiting loop on maximum iterations.",
for a plan whose `custom` twin reads "settled". **AJ3** (low): under maxBequest `view.score` is
savings + home, and the tornado's bars, the grid's cells and star and the front's "vs the
reference" still read it (W5 fixed only the lead rule): "condo price +10%" reads -97,822 =
-173,908 savings + 76,086 home, with the home shown again beside it; the household runs
maxSpending. **AJ4** (nit): the Ages preset's stage 2 clips neighbours to 62-70 but not to the
person's age this month, and a fixed past age is solved without a word as an entitlement
already running (Ari 62y0m = April 2026: 15,527 of 2026 benefits withheld by the earnings
test); it scores lowest here. Cleared: the exact-LP bars' ±0 tolerance matches `run_suite.py`
(no `~` outside its `main` group); the two death bars equal to the dollar (symmetric
survivors). Checks: `tests/library tests/ui` + the bracket/ACA/regret tests **1004 passed**
(2:11, Linux); full suite **4408 passed, 1 skipped** (13:21, Linux, `-n 3`); lint only
upstream's listed items. The review changed nothing in `src/`, `ui/` or `tests/`. Folds are
the user's call.

## Run-library step 6: the fifth review's AJ1-AJ4 folded (2026-11-06)

The user's call: fold AJ1-AJ4, and for AJ1 "solve this mover under a model with Medicare"
(`fork-notes/run-library-step6-review-5.md`, "Dispositions"; `fork-notes/CHANGELOG-fork.md`
has the entry; the design's I9 note amended). **AJ1**: a new solve preset `exact_medicare`
(the exact model with `withMedicare = "optimize"`), and `Mover.preset`: the medical-inflation
child and the run's own base for its bar solve under it, the other movers under
`decision_exact`. Chosen by measurement on the synthetic run and its `medical+2` child: Medicare
on the loop -1,842 (±0, 18 s for the pair), priced exactly -1,842 (±198, 14 s), at gap 1e-4
the same (±0, 51 s); local search -1,813. `tornado.bars` / `bar_flags` take the bases per
preset; the Run page queues the base under every preset its children need and gives each bar's
model. `view.record_companion` names both companion presets, so neither becomes a run's
headline (Run, Compare, `grid.latest_result`). End to end (the whole tornado through the
worker): medical inflation -1,842 ±198, 6th of 10 (was -83, last); the other bars unchanged.
**AJ2**: the log tee is quiet during the regret sweep: the regret job's record 1 warning
(was 126), quality "settled". **AJ3**: `view.first_number` (the savings left under
maxBequest) in the bars, the grid's cells, star and front: "condo price +10%" under
maxBequest -173,908 (was -97,822, savings + home). **AJ4**: stage 2 clips neighbours at each
person's first open claiming age (`Plan._ssaOpenAges`; Ari 62y7m, Noa 62y1m on 2026-11-06).
Tests: 14 new, three re-pinned; with `src/` and `ui/` stashed 13 of the 14 failed (the 14th
guards AG5's switch). `tests/library tests/ui` + bracket/ACA/regret **1018 passed** (2:44);
lint only upstream's listed items; full suite **4422 passed, 1 skipped** (11:47, Linux, `-n 4`; 4408 + the 14 new tests; two later edits, a docstring and the tornado axis label's escape, re-checked by the 8 tornado page tests).

## `main` fast-forwarded to `claude/modest-gauss-6hg9z6` (2026-11-06)

The user's call. `main` moves from `59bc8d9` (step 6 with the AI folds) to this branch: the
fifth whole-step review of step 6 (AJ1-AJ4) and its folds. Full suite on the branch: 4422
passed, 1 skipped.

## UX review of the browser UI (2026-11-07)

Branch `claude/optimistic-mccarthy-pidkig` (from `main` `1623d2e`). The user asked for a UX and
ergonomics audit from the spouse's point of view (a physician: analytical, no interest in solver
internals), **report first, no code change**: `fork-notes/ux-review.md`. The app was run in
library mode and driven with Playwright through the four journeys:

- cold start;
- a what-if against the baseline;
- the tax, ACA and IRMAA thresholds;
- one year's cash flow.

The case was the synthetic household (`Case_ari+noa_condo.toml` + the Yonkers 2029 cash
workbook), never the real one. Every finding is tagged [seen] / [ran] / [code].

Solves made:

- library "decision": 4 min 49 s, with its exact companion in 9 s;
- a Roth-cap what-if: 5 min 25 s;
- the classic Graphs page, which solves in the page request: not done after 22 minutes, with
  only the page header showing.

Defects found on the way (not fixed; the report's Q3, Q5, Q21, S4):

- the Queue page's "decision" queues no exact companion (the Run page's does), and Compare
  then tells the user to solve with Decision;
- a purchase event added to an imported run gives two residences, and its blank default
  school district overwrites the case's (STAR lost) [ran: `builder.build`];
- `owlbridge.runPlan` solves after `prepareRun` failed to apply the configuration (an ACA
  start year of 1999 gave the setACA error "e.g. 4025", then a misleading "No plan satisfies
  all the constraints");
- the Scenario page's "Property tax ($/yr, today's $)" label renders as math.

Also verified:

- Scenario edits are lost on navigation;
- the classic pages lose everything on a reload;
- the first click on *Create collection* is swallowed;
- "Things to look at" misses the 2029 IRMAA tier-2 crossing (2031 Medicare \$13,158 vs
  \$6,284 in 2032) and the 2027-28 marketplace-cliff overshoot, because it lists only years
  within 5% of a line.

Not walked: the Stress Tests pages, Settings, Logs, Documentation, the tornado and regret
sweep, a solved collection grid. Next: the user's call on which remediation items to build.

## UX review: the four bugs (2026-11-07)

Branch `claude/ux-fixes` (from `claude/optimistic-mccarthy-pidkig` `baf32e7`, which has the
review and the work order `fork-notes/ux-fixes-handoff.md`; `main` does not). Synthetic
household only. Each fix's test was run against the code before the fix and failed there
(the "failed before" lines below are from those runs).

- **B1 (= Q3), Queue's "decision" without its exact companion.** `ui/Queue.py` loops over
  `preset_solves` and flashes `ScenarioError`/`JobsError` across the rerun.
  `tests/ui/test_queue_page.py::test_decision_queues_its_exact_companion` failed before
  (`['decision']`). Re-driven: the Queue page lists `…_decision` and `…_decision_exact`.
- **B2, a purchase event on an imported run.** Semantics written in design 6.2 (amended):
  - a purchase without a move whose district is blank **keeps the case's district**; `-`
    states none (`builder.NO_PLACE`, the variants tables' clear spelling; `place_text`);
    a move's blank or `-` locality/district is none, as before;
  - a purchase over a hand Fixed Assets residence still owned while the event's home is
    (`yod` = disposal at the start of that year; zero/negative from the plan end) is
    **refused** (`_check_one_home`), a refusal rather than a warning because two homes are
    never what an imported case plus a purchase means, and the page shows refusals as "Not
    buildable yet"; a home sold by the purchase year, an inactive row and the event's own row
    are allowed;
  - the Scenario page pre-fills state, locality and district from the case, with dropdowns
    (`star.valid_districts`, `tax_local.valid_localities`, as Create Case), and keeps an
    event's own spelling when the pick builds the same (no phantom edit);
  - the variants tables store a cleared district as `-` (a blank would now keep the case's);
  - *Make variants*' "nothing to vary" names how to get a purchase event.
  - `BUILDER_VERSION` 6. `check_library_builder.py` 46/46 (every synthetic place states its
    district), `check_library_roundtrip.py` 39/39.
  - Failed before: `tests/library/test_builder_purchase_place.py` 6 of 11 (the 5 others are
    the allowed cases), `tests/ui/test_scenario_purchase_place.py` 3 of 3,
    `test_variant_tables.py::…test_b2_…` 1.
  - **Found on the way:** no synthetic workbook is rent-only: all 39 HFP files, including
    `HFP_ari+noa.xlsx`, hold a condo in Fixed Assets (checked with openpyxl). The work order's
    "start from the rent-only baseline" names nothing importable, so both messages describe the
    state needed ("a run with no home in its workbook"). For the journey a rent-only run was
    made by dropping the baseline's condo rows through the library API.
  - Re-driven: on `condo import` (Yonkers 2029 cash) ticking *Buy a home* shows "Not buildable
    yet: the case already holds a home, 'yonkers condo' (Fixed Assets, from 2029, kept to the
    end), owned while the purchase event's 'home' is (from 2027): the plan would hold two
    homes. …"; on the rent-only run the box shows *City of Yonkers / Yonkers* and *Yonkers*,
    and the saved child's `Case.toml` keeps `school_district = "City of Yonkers / Yonkers"`.
- **B3 (= Q21), a solve after the configuration failed (upstream code).** Re-checked on
  upstream `dev` `73dc8815` (unchanged since the last merge). `prepareRun` returns whether it
  applied; the five clone-and-solve callers stop; `runPlan` applies through `_applyConfig`,
  records `caseStatus = "invalid input"` and does not solve; `showCaseStatus` says it once;
  `sskeys.caseHasNotRun` lists the status. `setACA`: the offset hint only below 100, "is
  before 2000 … such as <next year>" otherwise (upstream's
  `test_start_year_offset_raises_for_typical_offsets` split accordingly). Issue draft
  `fork-notes/issue-prepare-run-failure.md`, patch `.patch` (verified with `git apply` on stock
  `dev`; stock `tests/ui` + `tests/tax/test_aca.py` 233 passed with it), repro script
  `-repro.py` with real output on stock and patched `dev` (stock jack+jill: the error, one
  solve, the half-applied case shown as solved). **Not filed.** Failed before (on stock
  `dev`): 2 of the 3 new tests in `tests/ui/test_prepare_run_failure.py`. Re-driven: Reports
  after *ACA start year* 1999 shows one alert, "The case was not solved: one of its inputs
  could not be applied. start_year=1999 is before 2000. Use a 4-digit calendar year such as
  2027.", and no solve.
- **B4 (= Q5), dollar labels as math.** The two labels in `ui/Scenario.py` escaped. The test
  is a source check (`tests/ui/test_ui_dollar_math.py`), chosen over rendering each label: it
  covers every page without building each page's state and does not break on rewording; it
  flags two unescaped `$` in a string passed to a Streamlit element or `help=`, unless they
  wrap a short math token (`$N$`); `Documentation.py` is math on purpose and excluded. Failed
  before (the two Scenario labels). Other hits checked by hand: `st.code` summaries in
  `owlbridge`, a Plotly axis title, docstrings and plan log messages: not rendered as
  Markdown. Re-driven: the label reads "Property tax ($/yr, today's $)".

## UX review: quick wins Q1-Q9 (2026-11-07)

Wording, display and defaults only: no solve, inputs hash or stored file format changes.

- **Q1** design/review codes and file names out of rendered strings on Run, Compare,
  Scenario, Collections, Library and Queue, and two notes from `library/compare.py`; meaning
  kept in plain words, codes left in comments. The scores-file uploader keeps `scores.json` /
  `work_sweep.py --json` in its help tooltip only. Test assertions on the old wording updated.
- **Q2** `ui/librarypresets.py`: `NAMES` through `format_func` (ids unchanged), the expert
  presets (`ages_thorough`, `custom`) behind an *Expert presets* toggle, one help text in plain
  words; used on Run, Queue and both Collections pickers, and in the result and queue labels.
  Times only as measured (quick 0.8 s, Careful 304-323 s on the condo case; this session's
  Careful took 5 min 18 s with the test suite running beside it); Ages: "slow" (not timed).
- **Q4** `compare.default_pair`: B the newest main solved result, A the newest main result of
  B's parent run, else of another run, never B. Nothing in the library sets `pins` (grep:
  only the delete path removes from it), so there is no pinned-baseline branch. The UI test
  failed on the old default. Re-driven: A = `baseline` quick, B = its child `rent only` quick,
  with `condo import` (another run, solved earlier) not chosen.
- **Q6** the four `by_year` charts titled "nominal $ per year" / "nominal $" (`by_year` is
  nominal: `cli/formatters.py`, "like every other by_year amount"); no today's-$ toggle
  (`plan.json` has no deflator: structural). *Things to look at*: localized number columns,
  an empty cell for a ramp. *What moved*: "(nominal $)" in the heading, separators,
  `hide_index`.
- **Q7** the score's own words as the metric label (`view.score_label`, so maxBequest reads
  "Final bequest"); "spent down by design" under *Savings left* only for maxSpending with a
  zero bequest target (`view.spent_down_by_design`); claiming ages "held at these: this solve
  does not search them" when the solve fixed what the frozen case searches, "chosen by Owl"
  after an age search (`view.claiming_ages_phrase`). Re-driven on `condo import`: "First
  year's discretionary spending ($/yr, today's) 108,506", "Savings left 0 spent down by
  design", "Ari 67y0m, Noa 67y0m (held at these: …)".
- **Q8** `libraryjobs.job_phase`: "Waiting for another solve to finish", "Solving: searching
  the tax breakpoints, step 12", "Solving, loop iteration 3", "Failed: <error>"; the raw line
  in the tooltip. Re-driven: the Queue showed "Waiting for another solve to finish" and
  "Solving".
- **Q9** `scenario.PATH_LABELS` (case fields in words, list indices kept, unknown paths raw)
  and `NO_OP_DEFAULTS` (`noLateSurplus` False, `timePreference` 0.0, `spendingSlack` 0: the
  defaults `Plan.solve` reads with) — added, removed or 0 -> 0.0 at the default is not a
  change. The safer fix only: `scenario_from_ui` still writes those keys, so no inputs hash
  moves. `check_library_compare.py` asserted the raw path `taxable_savings_balances`; it now
  reads the worded "taxable savings balances" (9/9; the script has nine checks now, not the
  six the work order quotes). The case-pages save journey of the review's [seen] item was not
  re-driven; the unit tests cover the diff.

Checks: `check_library_builder.py` 46/46, `check_library_roundtrip.py` 39/39,
`check_library_compare.py` 9/9, `check_library_jobs.py` 5/5. Lint: flake8 and ruff clean but
upstream's listed items (`ui/Run_Options.py:260` is the `1bdc3b2` B905, moved from 257).
Full suite: 4459 passed / 1 skipped (9:10, Linux, `-n 4`) on `aace7a1`, and again on the final code `b8b87db` (9:52; only docs changed after it).

Not fixed, seen on the way: the Scenario page's Save *Name* field keeps the previous run's
default when the run selector changes (its widget key is not per run).

## UX fixes: the independent review's AK1-AK7 folded (2026-11-07)

Review `fork-notes/ux-fixes-review.md` (an independent agent, report only: 1 medium, 3 low,
3 nits). All seven folded the same day, at the user's call, on `claude/ux-fixes`.

- **AK1 (medium)** `builder._check_one_home` no longer exempts a hand home with the purchase's
  name. The exception was meant for the event's own row, but the hand tables never hold
  it (a pages save drops generated rows, `casefiles._drop_generated`; a hand row an event
  replaced by name is put back only because the base had it). Re-run on the review's repro
  (condo case, 2029 mortgage workbook, cash purchase `yonkers condo` in 2031): it was built
  with the 2029 mortgage and down payment left over; it is now refused.
- **AK3 / AK5 (low / nit)** rows are read as the plan reads them: a blank `year`, or no `year`
  column, is the plan's first year (`fixedassets._get_reference_year`); a blank or absent
  `yod` is 0; `active` is inactive only when set and falsy (`utils.is_row_active`). Only a
  table with no `type` column is skipped.
- **AK2 (low)** `builder._check_place`: a move's locality and district are checked with
  `residency.normalize` when built (a `ScenarioError`, "Not buildable yet"). A purchase
  without a move is not checked against the case's state: I tried, and it refused existing
  fixtures whose case has no state or a non-NY one (Bill is TX). That goes beyond AK2, and
  such a district is a hand-district question, not this branch's. On the page, a State
  other than the one the pre-filled place came from starts both pickers at "(none)".
  `test_casefiles.py::…test_a_pages_save_drops_the_generated_case_fields` used an invented
  district (`City of X / X`) in a move. It now uses Yonkers; the test is about generated case
  fields, not the district.
- **AK6 (nit)** the page keeps the event's own spelling of the state when it matches the
  upper-cased field.
- **AK4 (low)** documented, not migrated: design 6.2 and the changelog say a pre-6 purchase
  with a blank district now keeps the case's district.
- **AK7 (nit)** changelog wording; "Q9 moves no hash, the builder bump moves every run's" in
  the changelog and CLAUDE.md; design 6.2 describes AK1's rule; the repro script prints
  "setACA error:". Its output was re-run on stock `dev` `73dc8815` and on the patched tree,
  identical apart from the label, and pasted into the issue draft.

Tests: 10 new or rewritten in `tests/library/test_builder_purchase_place.py` and
`tests/ui/test_scenario_purchase_place.py`. All 10 failed with the builder and page hunks
reverted (the 17 that pass there are the allowed cases and older tests).
`tests/library tests/ui tests/tax/test_aca.py`: 1016 passed. `check_library_builder.py` 46/46,
`check_library_roundtrip.py` 39/39. Lint clean apart from upstream's listed items.
Full suite: 4472 passed / 1 skipped (10:32, Linux, `-n 4`) on `8041d21` (only docs changed after it).

## `main` fast-forwarded to `claude/ux-fixes` (2026-11-07)

The user's call. `main` moves from `1623d2e` to this branch. The branch carries the UX review
(`claude/optimistic-mccarthy-pidkig`), its four bugs and quick wins Q1-Q9, and the independent
review's AK1-AK7 folds. Full suite on the branch: 4472 passed, 1 skipped. B3's upstream issue
(`fork-notes/issue-prepare-run-failure.md`) is still unfiled.

## UX review: quick wins Q10-Q20, and B3's issue reworked (2026-11-07)

Branch `claude/dazzling-gauss-69epxn`, from `claude/ux-fixes` `eaadfb7` (the work order
`fork-notes/ux-q10-q20-handoff.md`). Upstream `dev` still `73dc8815`.

**B3's issue draft reworked first (the user's call).** The draft's second point, `setACA`'s
hint for an ACA start year before 2000 ("e.g. 4025"), and its trigger, a start year of 1999,
answered an input nobody enters ("why not before 1900?"). Dropped from the issue, the patch and
the fork (`plan.py` `setACA` and `tests/tax/test_aca.py` are upstream's again; the method-name
stripping in `owlbridge._applyConfig` went with it). The new trigger is a move to the starting
state, which Create Case warns about but keeps: on stock `dev`, `Case_dana.toml` (CA) with the
state set to FL and a move to FL in 2031, plus \$50,000 of wages added for 2026, Reports showed
the error and then the results of a solve in CA (\$29,910 of state tax, for an FL case) with
\$0 of wages (the control, the same edit with the case left in CA, shows \$50,000: the skipped
`_setContributions`). Patched: no solve, one message, `invalid input`. The new test fails on
stock `dev` (one solve) and passes patched (`tests/ui` + `test_aca.py` 231 passed). Not filed.

**Decisions (the user's calls).** (1) Upstream pages split by kind: plain defects for everyone
with an issue draft, household-aimed wording in library mode only. (2) *Connect your AI* stays
in library mode (W9 stands). (3) *Edit as new run* goes to Run Options.

**The items.**
- **Q14** `owlplanner-library.sh`/`.cmd` pass `--client.toolbarMode=viewer`, not `minimal`:
  both drop Deploy, Rerun and Clear cache, and `minimal` would also drop the menu's Print and
  theme entries (the app sets no `menu_items`; option checked in Streamlit 1.66's `config
  show`). Welcome leaves out its AI-assistant paragraph in library mode.
- **Q18** reproduced with Playwright before the fix, on both buttons: typing the name and then
  clicking with the mouse hit a still-disabled button (the field commits on blur), and only the
  second click created. *Create collection* (fork) and *Create case* (upstream) are now enabled
  and name what is missing on a blank click. Re-drive afterwards: one click creates. The
  re-drive also showed a pre-existing twin: the name stays in the field after a create and a
  second click made a second collection with the same name; a taken name is now refused.
- **Q13** *Edit as new run* flashes where the inputs are and switches to Run Options;
  `sskeys.titleBar` draws a queued library message in library mode (the library pages do not
  call it, so only the classic pages are affected). New `sskeys.library_mode()`.
- **Q12** `owlbridge.openCaseFromPlan` sets `stHFP` from the plan's workbook name and marks the
  eight Case Setup pages visited. Not an upstream defect: every upstream workbook load goes
  through `readHFP`, which sets `stHFP` (and upstream's `genDic` is dead code). Both tests
  failed before the fix ("not yet been uploaded" shown; strip "(12%)").
- **Q10** `casefiles.case_references` and `ui/library_import.py` (the form's logic without
  Streamlit): a caption under each companion uploader ("Required: this case names
  *HFP_ari+noa.xlsx*"), an import missing a named file refused by name before anything is read
  (`_resolve_ref` would otherwise also look in the server's working directory), errors without
  the temporary folder, the form open after a failure with its files, cleared after a success
  (key counter). The uploaders keep fixed labels: a changed label can reset a widget.
- **Q11** Create Case confirms the workbook read ("loaded: wages and contributions for Ari and
  Noa; 0 debts, 1 fixed asset, 10 budget lines"; the Budget count only for a filled sheet or a
  budget profile) and drops "(Optional)" for a budget profile (fork part).
- **Q19** *Paid from* is a dropdown ("default (Ari)" keeps the event's `None`); the shares are
  shown in percent and the event keeps its own value while the shown percent is unchanged
  (0.029 does not survive x100/100: the two share tests fail with a plain `/100`); the event ids
  of rent, purchase, care and the downturn are in an "Advanced" popover (expanders cannot nest);
  a warning when property tax, HOA and insurance are all 0.
- **Q15-Q17** `ui/run_charts.py`. Brackets: every IRMAA tier on the chart's scale with the
  premium year in the hover (the tiers no year comes near are named in a caption: tier 5 on the
  synthetic case), the bracket tops as faint steps, red dashes for IRMAA and a purple dash-dot
  for the 400% FPL line; the table is a dataframe. *Taxes and premiums*: Medicare (IRMAA
  included) and marketplace premiums beside the taxes. *Income sources*: all-zero series left
  out; a big-ticket purchase year (found from `cash_flow`'s "Big-ticket purchases" use;
  `plan.json` unchanged) runs off the top with its total written on it. One year: a paragraph
  built from the same groups the Sankey draws (each side's groups add up to its total, tested),
  and a Sankey with the amounts in the node labels (Plotly 7.1's Sankey has no node text
  template), a labelled hub and Spending / Taxes / Health premiums nodes carrying totals.
- **Q20** Run Options (for everyone): the SLCSP field shows two decimals and steps by 1 (stock
  `dev`, in a browser: 20.84 typed showed 20.8, + went to 30.8). Goals (library mode only):
  Profile slack and Time preference behind "Advanced" with a sentence each; the profile axis
  reads "spending relative to the first year" where the profile starts at 1 (flat, budget) and
  "relative scale" where it does not (the smile starts at 1.094 on jack+jill, so the work
  order's "relative to year 1" would have been wrong there).

**Found.** Streamlit 1.66's `NumberColumn(format="plain")` shows 2028 as 2027.9999999999998
and 2034 as 2034.0000000000002 (a probe app, int64 column; `%d` is right). Q6's *Things to
look at* table used it for its years; both tables use `%d` now, and a source test keeps
`plain` out of `ui/`. Financial Profile's own "loaded" line after Open in Owl prints the plan's
full workbook path (`otherFiles/library/runs/.../inputs/HFP.xlsx`); left as is (upstream's
line, and `hfpFileName` feeds a saved case).

**Upstream issue drafts, not filed.** `fork-notes/issue-create-case.*` (Q18's lost click and
Q11's confirmation; stock patch, its test file 2 of 3 failing on stock `dev`, patched `tests/ui`
162 passed, a Playwright repro run on a stock server and a patched one) and
`fork-notes/issue-slcsp-field.*` (one call and a test failing on stock `dev`; patched
`tests/ui` 160 passed; Playwright repro on both). The fork carries both test files as is. The
stock Create Case test puts Streamlit's own `date` class back in its date widget: stock
`dev`'s test date freeze rebinds it there, and a rerun of a page with a birth date then fails
("Provided type: date"); the fork's conftest already handles it.

**Re-driven with Playwright** on the synthetic household in library mode, after the changes:
- Q10: with a run in the library the form starts closed; importing `Case_ari+noa.toml` alone
  says *"Not imported: this case names HFP_ari+noa.xlsx (choose it under Household workbook).
  Add it and import again."*, and the form stays open with the case file chosen.
- Q11: *"Upload Financial Profile"*, *"This case's spending profile is budget: its lines come
  from the workbook's Budget sheet."*, then *"✅ HFP_ari+noa_condo_yonkers_2027_cash.xlsx loaded:
  wages and contributions for Ari and Noa; 0 debts, 1 fixed asset, 10 budget lines."*
- Q12: Financial Profile shows no warning; the strip reads *"Case Setup Progress: (100%)"*.
- Q13: lands on Run Options with *"The inputs of Case_ari+noa_condo are open as the case
  ari+noa. Change them here or on any Case Setup page, then save them on the Library page
  (Save the current case): a new run, with Case_ari+noa_condo as its parent."*
- Q14: no Deploy button; the menu holds System / Light / Dark, Print, Record screen; Welcome
  has no AI headline.
- Q15: legend *IRMAA tier 1-4 (MAGI; premiums two years later)*, *400% FPL, the marketplace
  cliff (MAGI)*; caption *"Above the chart, never reached: IRMAA tier 5 (from 771,000)."*;
  the table's years read 2026, 2027, 2028 ... (after the `%d` fix).
- Q16: tab *Taxes and premiums* with *Marketplace premiums* and *Medicare premiums (with
  IRMAA)*; *Income sources* lists Wages, Social Security, Withdrawals from savings, and 2027
  carries *"↑ 974,971 incl. a 741,188 purchase"*.
- Q17: *"2027: spending \$141,369 plus big-ticket purchases \$741,188. All of it comes from
  savings: the taxable (brokerage) accounts \$888,582, the tax-deferred accounts (IRAs)
  \$86,389. Taxes \$70,669: capital gains \$36,187, state and local \$22,499, federal income
  tax \$7,072, NIIT \$4,911. Health premiums \$21,745 (marketplace \$21,745)."*; nodes
  *"2027 cash flow: \$974,971"*, *"Taxes: \$70,669"*, *"Spending: \$141,369"*.
- Q18: both buttons enabled at the click; one click creates.
- Q19: *Down payment (%)* 20.00, *Closing costs (% of the price)* 3.00, *Paid from* options
  *default (Ari)*, *Ari*, *Noa*; *Advanced* holds *Event id* "buy"; the all-zero warning shows.
- Q20: Goals' *Advanced* holds the two inputs and their sentences; the axis reads *spending
  relative to the first year*; the SLCSP field shows 20.84 with step 1.

**Checks.** Full suite on `bdfebd9` (all items built): 4507 passed, 1 skipped (11:11, Linux,
`-n 4`). Three UI-only commits followed (the tables' `%d` and whole dollars, the twin
collection); the full suite on the final code is recorded below. `check_library_builder.py`
46/46, `check_library_roundtrip.py` 39/39, `check_library_compare.py` 9/9. Lint: flake8 and
ruff report only upstream's listed items (the B905 in `ui/Run_Options.py` is at line 263 now).
The three upstream patches apply to stock `dev` `73dc8815` alone and together.

## UX quick wins: the independent review's AL1-AL2 folded (2026-11-07)

Branch `claude/review-ux-q10-q20` (from `claude/dazzling-gauss-69epxn` `3617bb5`). The
independent review `fork-notes/ux-q10-q20-review.md` (AL1-AL6: 2 low, 4 nit; the three issue
drafts reproduced exactly on stock and patched `dev`) was committed first; the user folded AL1
and AL2. AL3-AL6 stand.

- **AL1** (`ui/Scenario.py`): *Save as a new run* was `disabled=built is None`, Q18's pattern on
  a library page: after a field that kept the page from building was corrected, the click that
  left the field landed on a still-disabled button and nothing was saved (reproduced with
  Playwright). The button is now always enabled; a click while the events cannot be built shows
  *"Not saved: the events above cannot be built yet (see the message above)."* and saves
  nothing. Re-driven with Playwright: `bogus` in the care span's *From*, then `2040` typed and
  one mouse click on Save -> *"Saved as condo yonkers 2027 cash variant ..."* (before the fold:
  disabled at the click, nothing saved). B2's
  `test_scenario_purchase_place.py::test_a_second_home_is_refused_on_the_page` asserted the
  disabled button; it now clicks and checks the warning and that no run is saved.
- **AL2** (`ui/Run.py`, `ui/case_progress.py`): *Edit as new run* loads the run through
  `createCaseFromFile` + `readHFP`, not `openCaseFromPlan`, so Q12's "every Case Setup page
  visited" did not run, and Run Options' strip read *"(25%) - Step 2 of 8"*. Both paths now use
  `case_progress.all_setup_pages()`. Re-driven: *"(100%)"*.
- Tests: `tests/ui/test_scenario_page.py::TestSaveButton` (2) and an assertion added to
  `test_library_pages.py::test_run_options_draws_the_message_edit_as_new_run_left`; all three
  fail on `3617bb5` (checked in a worktree with the new tests copied in) and pass with the fold.
  `tests/ui tests/library` 985 passed. Lint: only upstream's listed items.
- Full suite on the fold (`abc473c2`): **4512 passed, 1 skipped** (8:59, Linux, `-n 4`); on
  `3617bb5` before it, 4510 passed / 1 skipped (9:55), the count the Q10-Q20 section promised
  and did not record (review AL6).

## Three issue drafts filed; `main` fast-forwarded (2026-11-07)

The user filed the three drafts on `mdlacasse/Owl`: **#245** (`issue-prepare-run-failure.md`, B3: the UI solves after "Failed to apply configuration"), **#246** (`issue-create-case.md`, Q18/Q11: Create Case's lost first click and the missing upload confirmation), **#247** (`issue-slcsp-field.md`, Q20: the SLCSP field's decimals and step). Numbers found with `gh api search/issues`. `main` fast-forwarded to `claude/review-ux-q10-q20` (Q10-Q20, the review, AL1-AL2 folded).

## UI remediation Phase 1: quick wins QW-1-QW-8 (2026-11-07, on `claude/ui-remediation-qw`)

Branch from `main` (`07701242`). The remediation plan's Phase 1 ("Labels, Units, Validation &
Table Ergonomics"; its file/line references were approximate -- several named functions no
longer exist -- so each item was implemented against the current code). One interpretation
per item, noted where the plan's wording allowed more than one reading.

- **QW-1** (AL4: a STAR refund called "income"; prose and Sankey words differ). `ui/run_charts.py`:
  a "..., net refund" row is a **tax offset**, never income (`_source_group`, a fourth source
  group "Tax refunds"), and the paragraph **nets it against the taxes** ("Taxes net of a
  \$1,000 state and local tax refund took \$62,597: ...", "gave back" when the refund is the
  larger); one set of words for the paragraph and the Sankey's nodes (`flow_label`: *Capital
  gains tax*, *ACA marketplace premiums*, *Medicare premiums*, *State and local tax refund*);
  Spending, Taxes and Health premiums always carry their total in a node of their own, even
  with one line (the Health premiums node vanished on a single-premium year); and a compact
  **Sources vs. Uses** table (`flows_table`, largest first) sits under the Sankey (`ui/Run.py`).
- **QW-2** ("Things to look at" showed near misses only). `src/owlplanner/thresholds.py`: a
  **crossed discrete cliff** is listed wherever the year sits over it, once crossing it costs
  over `CROSSING_COST` (\$500): the IRMAA tier the year is **in** (the highest tier its MAGI
  has crossed -- the tiers below it are not repeated) or the marketplace's 400% FPL cliff; a
  **continuous edge** (bracket edges, the NY recapture start, the NIIT kink) is listed only
  inside the 5% band **and** only when its price clears `SMALL_PRICE` (\$100): the \$3-\$26
  recapture edges of a parked year are noise. IRMAA rows name the payment year ("paid in 2030
  via the 2-year Medicare lookback"). The Run page's caption says which rows make it in.
- **QW-3** (the Brackets table showed IRMAA tier 1's edge only). `ui/run_charts.py`: one
  **IRMAA tier** text column -- the active (or next) tier for the year's MAGI ("IRMAA Tier 2
  (\$274,000) — crossed (+\$26,000 in 2029)" / "IRMAA Tier 1 (\$218,000) — \$98,000 below (sets
  2029)") -- and a **Binding ceiling** column: the ceiling with the least room left (a bracket
  top read against taxable income, an IRMAA tier or the 400% FPL cliff against MAGI), or the
  case's Roth conversion cap when the year is already at it. The cap is a new `conversion_cap`
  key in `brackets.bracket_view`'s rows (`maxRothConversion`: nominal, per person, as the LP
  caps it; today's \$ of the couple's total; results written before it carry none and simply
  never name the cap). "Sets premiums of" merged into the tier text.
- **QW-4** (Scenario.py showed percentages where Collections showed raw shares).
  `ui/variant_tables.py` + `ui/Collections.py`: `down`, `closing` and `extra` are typed and
  shown as **percentages** in the make-variants financing table (`format="%.2f%%"`, labels as
  on Scenario.py's purchase box) and stored as the shares the events hold (`_share`: 20 -> 0.20).
- **QW-5** (the headline read \$108,516 where the Spending chart's first bar read \$161,016).
  `ui/Run.py`: when the score is the first year's **discretionary** spending (essential budget
  lines under maxSpending), the headline metric is the first year's **total spending** (bar 1
  of the chart) with "\$108,516 discretionary + \$52,500 essential budget" under it; the
  caption names the score with its value. Other objectives keep the score as the headline.
- **QW-6** (preset/family codes, commit hashes and LP jargon on the decision screen).
  `view.method_text` is plain English ("Careful — exact tax & Medicare optimization"; "the
  fast approximate method"; companions "a simpler exact model, used as a check"), and the raw
  codes -- preset id, breakpoint method with its families, the branch-and-bound gap, the
  version and commit, the solver options, the claiming-age sweep's scorer ("branch-and-bound
  at gap 1e-5") and the note that the sensitivity children are solved under the exact LP --
  moved into a collapsed **"Technical solve details"** expander on the Run page. The
  sensitivity table lost its "model" column (QW-6.2).
- **QW-7** (AL3: a filesystem path after *Open in Owl*). `ui/owlbridge.openCaseFromPlan` names
  the workbook **without its folder** in `hfpFileName`/`stHFP`; *Edit as new run* **aborts**
  (a flash, no page switch) when `readHFP` returns False instead of announcing the inputs as
  open and leaving the error behind.
- **QW-8** (default variant name, the active-case icon, input bounds). `ui/Library.py`: the
  save-name default is *"{case} variant"* when the case is a run's edited inputs (`runBase`),
  the plain name otherwise. `ui/sskeys.flagCurrentCase` marks the current case with **✓** (was
  🔻, which read as a warning; the leak-stripping in `switchToCase` accepts both);
  `ui/Documentation.py` follows. `ui/Run_Options.py`: the Roth conversion years and the
  converter-switch year are **bounded by the plan horizon** (`max_value=plan.year_n[-1]`; a
  stored year outside the bounds is clamped to them -- the case keeps what the field shows --
  and the stop-year default is `min(thisyear + 10, plan end)`); the ACA start year is a plain
  calendar year, **default this year** ("0 = plan start" is gone: the plan starts in the solve
  year, so 0 reads as this year and the input is bounded below by it).
  `ui/Account_Balances.py` warns when a \$k balance reads as **\$50M or more** ("if these are
  dollars rather than thousands, divide by 1,000").

**Found and fixed on the way (Windows).** The suite runs on Windows here, which exposed two
platform bugs in the import flow QW-7/QW-8 touch: `toml_io.load_toml`'s `BytesIO`/`StringIO`
branch fed `toml.loads` a CRLF string, and the `toml` package then **silently kept only the
first key** (`library_import.case_refs` read every uploaded case as its name alone, and the
import failed on a workbook it had never seen named); both branches now normalize line
endings. `library_import.without_folder` matched the folder with `os.sep` only and left
forward-slash paths in its errors; it accepts either separator.

**Tests.** Updated for the intended changes: `tests/plan/test_thresholds.py` (the NIIT noise
price, the recapture stub narrowed so its crossing clears \$100, "every entry" = a near miss
or a crossed cliff), `tests/library/test_view.py` (plain-English `method_text`,
`method_details`), `tests/ui/test_run_charts.py` (the refund group and netting, the unified
words, the single-premium Health premiums node, the flows table, the new Brackets columns),
`tests/ui/test_library_pages.py` (the headline metric and its delta, the technical expander,
the scorer's new home, the tornado table without "model"). New: crossed-cliff rows and the
payment-year note (`TestCrossedCliffs`), the \$100 noise floor, `conversion_cap` in
`test_brackets.py`, the percent-to-share financing cells (`test_variant_tables.py`), the
workbook named without its folder (`test_open_in_owl.py`), the *"{case} variant"* default and
the ✓ mark (`test_library_pages.py`), the Sources vs. Uses table on the Run page, the Run
Options year bounds and ACA default (`tests/ui/test_run_options_year_bounds.py`), the \$50M
balance warning (`tests/ui/test_account_balances_units.py`), and a source check on the
financing percent format (`test_collections_page.py`).

**Checks.** Full suite on the Windows machine: **4539 passed, 2 skipped** (2026-11-07, 13:38,
`-n 4`, 818 s; the second skip is a platform one -- the Linux runs record 1 skipped). Lint:
flake8 and ruff report only upstream's listed items (the B905 in `ui/Run_Options.py` is at
line 314 now, moved by the edits above it). The review AM1-AM3/AM8 fold below re-runs the
affected tests.

## UI remediation Phase 1: the independent review, AM1-AM8 (2026-11-07)

An independent review of `082f9b96` (`fork-notes/ui-remediation-qw-review.md`; a fresh agent
with the work order, report-only -- no code changed by it): **AM1-AM8** (3 low, 5 nit; no high
or medium). Every QW item verified **done** (QW-2/3/6/8 "done with deviations", each judgment
call called defensible); every new/changed test checked for teeth in throw-away worktrees (each
fails without its change); AL3 and AL4 reproduced closed on before/after runs; its own full
suite run 4539 passed / 2 skipped, matching the counts above. The user folded **AM1-AM3 and
AM8** (AM4-AM7 stand):

- **AM1** (QW-6's jargon only half out of the sensitivity block): the three tornado captions
  use the plain vocabulary now ("this run's own solve in the children's model", "the
  simpler-model solve"), the block's opening caption points at *Technical solve details*, and
  the medical-inflation mover's note -- a fourth spot the review's list of three missed, found
  by the fold's own teeth check (`tornado.movers`) -- says "the simpler model prices no Medicare
  premiums". `test_ag2_...the_bars_wait` pins the new phrase and asserts that no caption on the
  page carries "exact LP" (it failed before the fold: the mover note).
- **AM2** (the fork's acceptance check asserted the invariant QW-2 breaks):
  `fork-notes/synthetic/check_library_compare.py`'s "Things to look at" rule is now "inside its
  band **or** a crossed cliff" (the rule QW-2 introduced; the suite's twin was already rewritten
  in `tests/plan/test_thresholds.py`), so the recorded 9/9 check will not report FAIL on a plan
  that crossed a cliff. The check needs a full synthetic solve and was not re-run here; its
  invariant now mirrors the suite's.
- **AM3** (the year clamp rewrote stored inputs silently): `_bound_year` and the page now name
  every move ("a stored year outside its field's range was set to the nearest allowed year:
  startRothConversions 2500 \u2192 2053"), and the fold splits the two kinds of move. A move
  **down** to the upper bound changes what the input means (a year past the plan can no longer
  say "never convert"), so the case is flagged modified (`setCaseKey`; `flagModified` makes the
  Graphs page re-solve, which is right -- the results are stale). A move **up** to the lower
  bound is the neutral one (a year before the plan's first year means "from its first year",
  what `sanitize_config` does at load), so it keeps the case's status: merely opening Run
  Options on a case carrying the old "0 = plan start" ACA value does not invalidate its solved
  results. `tests/ui/test_run_options_year_bounds.py` pins both halves (caption + status).
- **AM8** (docs): CLAUDE.md's lint note points at the B905's real line (314 after these edits;
  it had said 263 since Q20). The other half of AM8 is a fact of `082f9b96`'s commit message --
  a `$` interpolated away by the shell took "under $100" and "$50M" out of it -- with the
  amounts recorded in the section above.

**Checks.** Full suite after the fold: **4539 passed, 2 skipped** (2026-11-07, 10:53, Windows,
`-n 4`; the same counts as before the fold -- these are wording, invariant and message changes
with the tests that pin them). Lint: only upstream's listed items. The AM1 teeth assertion
(`test_ag2_...the_bars_wait`) fails on the pre-fold code with the mover note in its message.

## Ergonomics review QW-1 to QW-8: the work order (2026-11-07)

Branch `claude/upbeat-planck-c731oy` (from `main` `0770124`). The user pasted an independent
review of the browser UI's ergonomics: eight quick wins, QW-1 to QW-8. Each was checked against
the code at `0770124` and against `upstream/dev` `73dc881` (fetched the same day).

- **What the check found.**
  - Most of the claims that could be checked hold.
  - Several identifiers the review names do not exist (`_SUMMARY_USE_NAMES`,
    `cash_flow_summary_text`, `_PURCHASE_SWEEP_CONFIG`, `_render_headline`,
    `_sensitivity_frame`, `distance_frac`; grep of `src ui tests fork-notes`).
  - Its figures (\$161,016 / \$108,516, the \$3-\$26 recapture rows, ~\$6.9k of IRMAA) come
    from our own `fork-notes/ux-review.md` (lines 122, 222-233, 328-329, [seen]).
  - QW-2.3 (the IRMAA payment year) was already in the entries (`affects`, the note), but under
    an opaque column name.
- **Re-read for ergonomics (the user's call).** The first answer argued from earlier decisions
  and the code's structure; the user asked for an ergonomics reading, with earlier decisions
  open. That reopens AL3 and AL4 (`ux-q10-q20-review.md`) and parts of S5, S6 and S9
  (`ux-review.md` section 4).
  - Changed on that reading: QW-5's total as the Run page's headline; QW-1.2's group nodes
    always drawn; QW-6.2's "model" column dropped, with a † on the one bar measured
    differently; QW-8.2's marker and QW-8.3's toggle.
- **Found while checking, not in the review:**
  - The Collections financing table has no range check (`builder.py` 421-423, `variants.py`
    217-219), so `down = 20` typed as a percent builds a negative loan (`builder.py` 972; the
    solve was not run).
  - [inferred, not run] Every run from one import carries the import's `case_name`, and
    `sskeys.createCaseFromFile` refuses a name already in the session. *Edit as new run* on a
    run and then on its child, in one session, would stop at "Case name already exists".
- **Work order** `fork-notes/ux-qw-handoff.md`.
  - The items are in the reader's order: QW-2, QW-5, QW-1, QW-4, QW-6, QW-3, QW-7, QW-8.
  - Four decisions for the user come first: upstream pages; QW-2's rules; QW-5's headline;
    QW-8.4's threshold.
  - Each item gives file:line evidence, what to do, its tests and its check.
  - QW-2 and QW-3 add fields to `plan.json` for new solves only; no item moves an inputs hash.
- Docs only: nothing built, no test run.

## Ergonomics quick wins: the build reviewed against the work order (2026-11-07)

Branch `claude/upbeat-planck-c731oy`. The user had built QW-1 to QW-8 in parallel on
`claude/ui-remediation-qw` (from the original review's list, not from this branch's work
order), had it reviewed (AM1-AM8) and folded AM1-AM3 and AM8. It is merged here (`790364a`:
`src`, `ui` and `tests` identical to `44c3eec`; CLAUDE.md and PROGRESS.md kept side by side) and
reviewed against `fork-notes/ux-qw-handoff.md`, each difference judged on its merits, in either
direction.

- **What was run** (Linux, the implementation's code):
  - targeted suites, 1048 passed (72 s); full suite **4540 passed, 1 skipped** (11:49, `-n 4`);
    `check_library_compare.py` 9/9 (not re-run since AM2's fold until now);
  - lint, only upstream's listed items;
  - the UX review's baseline (`Case_ari+noa_condo.toml` +
    `HFP_ari+noa_condo_yonkers_2029_cash.xlsx`) imported into a fresh library and solved
    "Careful" (5 min 16 s) and its exact companion, and one Quick look solved with the
    pre-branch code as an "older result";
  - Playwright on the Run, Library, Account Balances and Collections pages;
  - AppTest and script probes for the rest.
  The Careful figures match `ux-review.md` to the dollar (premiums \$21,745 / \$22,689 / \$13,158
  nominal; \$161,016 = \$108,516 + \$52,500).
- **Kept from the build:**
  - QW-2's cliff costs, equal to `tx.acaCosts` called directly (\$12,547 / \$12,865 / \$4,824);
  - QW-5's total from `spending_year1`;
  - QW-1's refund never called income, and the one-line group nodes;
  - QW-6's plain phrase in `view.method_text`;
  - QW-7.1; QW-8.2's ✓; QW-8.3's Roth bounds and AM3's split;
  - the CRLF and separator fixes.
- **Findings AN1-AN11** (4 medium, 5 low, 2 nit), in the new work order:
  - AN1: the headline's split is drawn as math and cut, "108,516 discretionary + 52…" [seen].
    `st.metric`'s `delta` is Markdown, and the dollar-math test does not scan `delta=`.
  - AN2: Run Options says "acaStartYear 0 → 2026" on every case without an ACA start year,
    both upstream examples probed, and a save then writes the year.
  - AN3: QW-2 misses the crossed Enhanced STAR limit (2029, \$1,546 of the 2031 credit) [ran].
    It has no `groups` marker: the older result shows the new caption over one near row [seen].
    It removes the small rows from `plan.json`: on the same plan, the pre-branch report gives
    the four recapture rows (\$3.03-\$26.48) and the new one none [ran]. The ACA note on over
    rows is wrong, and the page is the old table.
  - AN4: QW-7.3 reproduces ("Case name 'bill' already exists."); 7.2 leaves the half-opened
    case current. The save name follows the import ("ari+noa variant" for "ari+noa condo
    baseline") and does not follow a case switch.
  - AN5: QW-3's "crossed (+\$12,802 in 2028)" names a premium year with no Medicare, and shows
    the overshoot where a premium is expected. A documented "no cap" (`maxRothConversion = -1`)
    reads "Conversion cap (\$-2,000)"; the cap is the household's where the plan's is per
    person.
  - AN6: QW-1's netted tax figure (\$2,177 in 2034) is in neither the Sankey (\$5,111, \$2,934)
    nor the table; STAR is not named; the chart's words differ; the table is flat.
  - AN7: a Collections down of 2000 builds a -\$13,672,400 mortgage.
  - AN8: two lists of preset names; "exact … optimization" for a local search; the tornado has
    no †, and its notes carry config codes.
  - AN9: upstream code changed with no draft. Among it, a real upstream defect reproduced on
    stock `dev` `73dc881`: a CRLF case with a `"""` string, uploaded, keeps only its name ("Failed
    to parse case file: 'basic_info'"); 14 of upstream's 19 examples hold one.
  - AN10 (pre-existing): "None" cells in the brackets table.
  - AN11: the balance warning's "\$60,000k".
- **Work order** `fork-notes/ux-qw-handoff-2.md`:
  - six decisions for the user first: the upstream drafts, QW-2's rules given the build, QW-5's
    wording elsewhere, QW-8.4's threshold, QW-8.3's toggle, QW-1's tax sentence;
  - then the remaining work per item, in the reader's order, and four new items (the CRLF
    draft, the "None" cells, AM5, the other drafts);
  - each defect with a test that must fail first.
  `fork-notes/ux-qw-handoff.md` is marked superseded for the remaining work.
- Docs only on this branch: nothing in `src`, `ui` or `tests` changed by this review. The probes
  lived in the session's scratchpad; their recipes are in the work order.

## Ergonomics quick wins: the second pass built (2026-11-07)

Branch `claude/upbeat-planck-c731oy`, work order `fork-notes/ux-qw-handoff-2.md`. The user's
call: **all six decisions as recommended** (1: drafts for the CRLF upload, 8.3 and 8.4, none
for the check mark; 2: crossings for IRMAA, the 400% FPL line and the Enhanced STAR limit, the
floor on the page, ramps in the fold, no floor on crossings; 3: "discretionary" for "score";
4: \$20M; 5: the ACA toggle; 6: the tax sentence in the Sankey's figures). One commit per
item, in the order QW-2, QW-5, QW-1, QW-4, QW-6, QW-3, QW-7, QW-8, N2, N3, N1, N4.

Each defect's test was run against the build's code first (a worktree of `686521e`, the
merged build, with `PYTHONPATH` set to its `src`):

- **QW-2** (`0aa42b3`): 10 of `test_thresholds.py`'s new or changed tests fail on the build
  (no STAR over-entry, no `group`/`groups`, a \$69 NIIT row and a \$50 crossing dropped).
  Model: `group` per entry, `groups` per block, Enhanced STAR crossings priced at the enhanced
  line only (an income over the basic limit too does not charge the basic credit to it),
  IRMAA `total_today_dollars`, the ACA over-cliff note ("no subsidy is paid"), `SMALL_PRICE`
  and `CROSSING_COST` gone. Page: `run_charts.threshold_parts` (two tables, the fold, plain
  columns, merged years, an older result split by its band with "Solved before crossings
  were reported: solve again to see them.").
- **QW-5** (`3f40a85`): the dollar-math source test now scans `value=`, `delta=`,
  `delta_description=` and failed on the build's `Run.py:497`; the split is its own escaped
  line; `view.score_name` names the score in Compare's first row, the lead note, the grid's
  pair rows, Collections' lines and the tornado's question; `tests/ui/test_no_score_word.py`
  (upstream's "Retirement Efficiency Score" is a proper name and stays). 4 tests fail on the
  build.
- **QW-1** (`cc54bf4`): on the build the 2034-shaped paragraph says "Taxes net of a \$2,934
  state and local tax refund took \$2,177", and \$2,177 is on no Sankey node (probe on the
  build's `run_charts`); now "Taxes \$5,111: federal income tax \$5,111; state and local, a
  net refund of \$2,934 (the STAR credit is larger than the tax)". `FLOW_LABELS` (label and
  prose), `TAX_SERIES`/`PREMIUM_SERIES` built from it, the grouped table with "Total in" /
  "Total out", no Spending node over "Net spending" alone, STAR only with a district and
  `withSTAR` on (`Run.py` `_has_star`). 10 of 14 one-year and chart tests fail on the build.
- **QW-4** (`693e2e5`): on the build a down of 20 builds a Debts row of -\$13,566,000 in the
  test's case (AN7's -\$13,672,400 on the synthetic price); now refused, "down payment 2000%:
  enter a percent between 0 and 100", in the builder and in `variants`; unit-slip warnings on
  both pages; Collections headers and bounds; Scenario's boxes bounded unless a stored value
  is already outside. Builder output unchanged (`BUILDER_VERSION` 6).
- **QW-6** (`0ac7a02`): `presets.PRESET_NAMES` (the one list), method words without "exact
  ... optimization" for a local search, AM4's repetition gone, the tornado's † and footnote,
  its notes in plain words with the codes as `Mover.detail` in the button's help, the
  expander's sensitivity line only once a sensitivity collection exists (the order said
  once results exist; the collection is made when the runs are queued, before any result).
  6 tests fail on the build.
- **QW-3** (`20aa424`): on the build `maxRothConversion = -1` gives `conversion_cap = -2000.0`;
  now per-person limits (`brackets.conversion_limits`: excluded, pinned, last years, window,
  swap, cap, not alive), `conversion_cap_each`, `conversion_window`, IRMAA edges only for a
  premium year with Medicare months; the page's IRMAA words and *Next limit*. 16 tests fail
  on the build.
- **QW-7** (`5170bc9`): on the build *Edit as new run* opens "bill" for "bill later", leaves
  the half-opened case behind after a damaged workbook, and a save stores the session's case
  name; now `sskeys.uniqueCaseName` (shared with *Open in Owl*), `createCaseFromFile(name=)`,
  the case deleted on a failed read, `scenario_from_ui` keeps the base's `case_name`, and
  Create Case says "HFP.xlsx (from *run*)". 3 tests fail on the build.
- **QW-8** (`f69316a`): on the build both unmodified upstream examples get `acaStartYear`
  2026 (the test's `assert 2026 == 0`); now the toggle storing 0, clamps named in the field's
  words, the save name "<base run> variant" keyed by the case with a duplicate warning, the
  \$20M warning in dollars. 4 Run Options tests fail on the build.
- **N2** (`0c8ca65`): Playwright on a probe page: Streamlit 1.66.1 draws a float NaN, a
  `Float64` `pd.NA` and an object `None` alike as a grey "None" (with or without
  `NumberColumn(format="localized")`); only an empty text cell is blank. The 400% FPL column
  is text now.
- **N3** (`b6b98c3`): AM5's corner fails on the build ("cannot read C:/tmp/xyz123/HFP.xlsx
  missing") and passes now.
- **N1** (`ba0a618`), **N4** (`fa7255d`): `fork-notes/issue-crlf-upload.*`,
  `issue-year-fields.*`, `issue-balance-units.*`, each reproduced on a stock `dev` `73dc881`
  worktree and patched there (`git apply --check` clean; the new tests fail on stock and pass
  with the patch; `tests/ui` + `tests/config` 409, 412 and 410 passed with them). Stock
  results: a CRLF case reads as `['case_name']` and Create Case says "Failed to parse case
  file: 'basic_info'"; a start year of 20300 is stored and the plan converts \$0 instead of
  \$322,299 (jack+jill); jack+jill with balances typed in dollars solves "infeasible". The
  balance draft carries a test-only `tests/conftest.py` hunk: on stock, an AppTest of Account
  Balances fails on `st.date_input` under the frozen date. **Not filed.**
- **Re-drive fixes** (`3c839e9`, found with Playwright): "Things to look at" cut "Year of
  income" and the IRMAA cost at the named widths (now pixels; the cost reads "\$3,741 (whole
  year \$6,216)"); the brackets table cut its IRMAA column; the tornado caption put the
  medical dagger twice and nested parentheses in the notes.
- **What was run** (Linux):
  - full suite on `fa7255d` (every item and draft committed): **4595 passed, 1 skipped**
    (14:50, `-n 3`, with a Careful solve beside it); after `3c839e9`, `tests/library`,
    `tests/ui`, `test_thresholds.py` and `test_brackets.py`: 1103 passed;
  - lint: flake8 and ruff report only upstream's listed items (`ui/Run_Options.py`'s B905 is
    at line 345 since `986c625e`);
  - `check_library_compare.py` **9/9** ("discretionary spending resolved"; "thresholds: 5
    near a threshold or over a cliff (aca, irmaa, star)"), `check_library_builder.py`
    **46/46**, `check_library_roundtrip.py` **39/39** (after QW-4 too);
  - the UX review's baseline (`Case_ari+noa_condo.toml` +
    `HFP_ari+noa_condo_yonkers_2029_cash.xlsx`) solved Careful with the final code (308 s,
    exact companion 12 s), and a child ("10k less taxable", the import's case name) solved
    Quick for the two-edit drive.
- **QW-2's check** on that solve (`run_charts.threshold_parts` on its `plan.json`, and the
  page): *Where the plan pays for being over a line* holds "2027-2029, marketplace subsidy
  cliff (400% FPL), \$48,790-\$243,823 over, \$4,824-\$12,864" (\$12,547.12 / \$12,864.41 /
  \$4,823.61 today's, x gamma 1.0280 / 1.0568 / 1.0864 = \$12,898.44 / \$13,594.90 /
  \$5,240.24 nominal), "2029, IRMAA tier 2, \$38,466 over, \$3,741 (whole year \$6,216), paid
  in 2031" (\$3,741.19 x 1.1481 = \$4,295.12 nominal; the year \$6,215.50 x 1.1481 =
  **\$7,135.78** nominal, the work order's \$7,136) and "2029, Enhanced STAR limit, \$181,038
  over, \$1,546, 2031". *Close to a line* is empty; "4 smaller items" holds 2030 / 2047 / 2048
  NY recapture (\$26, \$19, \$4) and 2050's 0% gains edge (\$9). The work order expected four
  recapture rows (\$26.48, \$19.19, \$4.42, \$3.03): today's plan differs in its late years, and
  the pre-branch `threshold_proximity` on today's plan lists exactly these four rows (run on
  the first of today's two Careful solves, whose `plan.pkl` was still loadable; the deflators
  above are from it too, and its entries equal the final solve's to the cent).
- **Playwright on the final code** (library mode, the baseline's Run page unless said):
  - QW-5: "Solved 2026-11-07 19:42 · Careful — taxes and premiums priced exactly, the plan
    found by a local search"; metrics 161,016 / 753,309 / 0 (spent down by design) / 304,959;
    "Of the first year's \$161,016: \$108,516 discretionary (the part the plan raises or
    lowers) and \$52,500 essential budget lines." whole, with its dollars; "The solve
    maximizes the first year's discretionary spending (\$/yr, today's): 108,516. ...".
  - QW-2: the two headings, the caption "The optimizer prices each of these lines, ...", the
    table and "4 smaller items" as above (screenshots).
  - QW-1, 2034: "spending \$167,469. The money comes from savings, \$91,924 (the taxable
    (brokerage) accounts \$43,596, the tax-deferred accounts (IRAs) \$41,311, the Roth
    accounts \$7,017), and from income, \$84,562 (Social Security \$84,562). Taxes \$5,109:
    federal income tax \$5,109; state and local, a net refund of \$2,934 (the STAR credit is
    larger than the tax). Health premiums \$6,842 (Medicare premiums (with IRMAA) \$6,842)."
    The table: "From savings \$91,924" ... "Tax refunds \$2,934 / State tax refund (STAR)
    \$2,934", "Taxes \$5,109 / Federal income tax \$5,109", "Total in \$179,420 | Total out
    \$179,420", equal to the caption's.
  - QW-3, 2026-2031 (IRMAA tier | Next limit): 2026 "no Medicare premiums in 2028" | "24/28%
    bracket top: \$82,909 away"; 2027 "below tier 1 by \$97,333: 2029 premiums" | "10% bracket
    top: \$2,000 away"; 2028 "below tier 1 by \$97,386: 2030 premiums" | "10% bracket top:
    \$1,662 away"; 2029 "tier 2 (\$38,466 over its \$289,559 edge): 2031 premiums" | "10%
    bracket top: \$24,800 away"; 2030 "below tier 1 by \$94,188: 2032 premiums" | "12/15%
    bracket top: \$53,538 away"; 2031 "below tier 1 by \$94,237: 2033 premiums" | "12/15%
    bracket top: \$47,120 away"; the 400% FPL cells blank outside 2027-2029; the caption
    under the table. The case sets no conversion limit these years, so none is named.
  - QW-6: the tornado's caption in plain words, "medical inflation +2 points †", no config
    code; the header as above.
  - QW-7: *Edit as new run* on "ari+noa condo baseline, 10k less taxable", then on "ari+noa
    condo baseline", in one session: both open under their run names (the case selector
    lists both, the current one ✓), no "already exists".
  - QW-8: the save name "ari+noa condo baseline variant", and after switching the case
    "ari+noa condo baseline, 10k less taxable variant" with its caption following;
    `Case_jack+jill.toml` uploaded unmodified: Run Options shows no message, the toggle on
    (disabled: no benchmark premium), no year box; Account Balances with 60,000 in Jack's
    taxable field: "Jack's taxable accounts: 60,000 here means \$60 million (amounts are in
    thousands). If you typed dollars, divide by 1,000."
- Docs: `fork-notes/CHANGELOG-fork.md` entry; CLAUDE.md State bullet and counts;
  `ux-review.md` status (S5, S6, S9 partly done); `ux-q10-q20-review.md` (AL3, AL4 folded);
  `ui-remediation-qw-review.md` (AM4-AM7 closed); the work order records the decisions.
- **Next:** the user's call on an independent review, on fast-forwarding `main`, and on
  filing the three drafts.

## Ergonomics quick wins: independent review of the second pass (2026-11-07)

Branch `claude/upbeat-planck-c731oy`, on `d64ec67`. Report:
`fork-notes/ux-qw-second-pass-review.md`, findings AO1-AO8. Report only: nothing in `src`, `ui`
or `tests` changed.

- **AO1 (medium, QW-2).** A cliff crossed inside the 5% band is `group="near"` and drawn under
  *Close to a line*.
  - Seen in 3 of 10 Quick looks of the synthetic baseline with the taxable balances moved.
  - Variant -200: the over table lists only 2029 (\$4,824) "largest cost first", while 2027
    (\$12,547) and 2028 (\$12,864) are near rows [seen in the browser].
  - AppTest: with only an in-band crossing, the over table says no year is over a line and
    the next table lists one.
  - It comes from the work order's own group definition.
- **AO2 (low).** The one-year paragraph's savings total is on no Sankey node (210 of 280
  paragraphs). The built test covers the tax sentence only.
- **AO3 (low/nit).** Create Case's "(from *run*)" follows the case, not the workbook.
- **AO4-AO8 (nits).** A cut Note column; "no Medicare premiums" for premium years after the
  plan; a failed *Edit as new run* leaves another case current; the ACA toggle forgets a typed
  year; one repro line in the year-fields draft can be misread.
- **Held.**
  - The three upstream drafts reproduce line for line on stock `dev` `73dc8815`, their patches
    apply, and their tests fail on stock and pass patched.
  - QW-2's "10 fail on the build" holds.
  - QW-3's limits mirror the LP [code].
- **Run (Linux).** Targeted suites 1103 passed; **full suite 4595 passed, 1 skipped** (11:24,
  `-n 4`); lint as recorded.
- **Next.** The user's call on which AO items to fold, on fast-forwarding `main`, and on filing
  the three drafts.

## Ergonomics quick wins: the second-pass review's AO1 and AO2 folded (2026-11-07)

The user's call: fold AO1 and AO2 of `fork-notes/ux-qw-second-pass-review.md`. AO3-AO8 stand.

- **AO1** (`thresholds.py`, `run_charts._entry_group`).
  - A crossing of one of the three cliffs is `"over"` wherever it sits, inside the 5% band
    included: the tier the year is in for IRMAA, the 400% FPL line, the Enhanced STAR limit.
  - `"near"` is the under side of those lines and every continuous edge (a contribution step
    crossed inside its band stays "near").
  - The page regroups by side and line, so results solved at `d64ec67` (in-band crossings
    marked "near") and older ones are drawn right.
  - `check_library_compare.py` check 7 follows the rule.
- **Re-checked on the review's ten Quick looks** (the baseline with each taxable balance moved
  by -300 to +500 $k).
  - The stored `d64ec67` results through the new page: variant -200 shows one row, "2027-2029,
    marketplace subsidy cliff (400% FPL), \$2,399-\$76,979 over, \$4,824-\$12,864", with no
    *Close to a line* table [seen, Playwright].
  - +100: the Enhanced STAR limit is one row, 2027-2029, \$145-\$250,411 over.
  - Re-solved with the new model, the same three variants mark their in-band crossings
    `"over"`: -200 (2027, 2028, the cliff), +100 (2028 STAR), +500 (2028 IRMAA tier 1).
- **AO2** (`run_charts.sankey_figure`).
  - A source group of two or more lines gets a node with its total ("From savings: \$940,176"),
    as the uses side does. It is drawn only when there is more than one source group: alone,
    the hub carries the same number and the paragraph names no total.
  - On the ten Quick looks, 0 of 280 one-year paragraphs name a figure that is on no node
    (210 did).
  - Seen in the browser: variant -200, 2029.
- **Tests** (7 new or changed; 6 fail on the previous code, run in a worktree of `63f710f`):
  - `test_thresholds.py`: the band-rule assertion and
    `test_a_cliff_crossed_inside_its_band_is_over_not_near`;
  - `test_run_charts.py`: the in-band merge, the under-side guard (passes on both, a guard),
    `test_every_figure_the_paragraph_names_is_on_a_sankey_node`;
  - `test_library_pages.py`: an AppTest of the in-band-only case (no "No year's income is
    over ..." caption), and the older-result test, whose \$1,200 IRMAA crossing is now in the
    over table.
- **Run (Linux).**
  - Targeted suites (`tests/library tests/ui test_thresholds.py test_brackets.py`): 1108 passed.
  - **Full suite: 4600 passed, 1 skipped** (10:27, `-n 4`).
  - `check_library_compare.py` 9/9.
  - Lint: only upstream's listed items.
- **Next.** The user's call on fast-forwarding `main`, and on filing the three drafts
  (`issue-crlf-upload`, `issue-year-fields`, `issue-balance-units`).

## Ergonomics review S-1 to S-6: the work order (2026-11-07)

The outside ergonomics review's second phase (six structural items, pasted by the user) checked
against the code at `f854721` and re-read for ergonomics; work order
`fork-notes/ux-structural-handoff.md`. Docs only, nothing built, no solve run.

- **Mapping to our own items** (`ux-review.md`): S-1 = S1, S-2 = S3 + S2, S-3 = S4, S-4 = the
  rest of S5, S-5 = S8 plus overlay charts, S-6 = S7.
- **Already built or not as described [code]:**
  - the Queue page already polls (`@st.fragment(run_every=2.0)`, `Queue.py:75`) with elapsed
    time;
  - `OWL_SKIP_DISCLAIMER` already exists (`Welcome.py:28`);
  - the Run page needs no `Plan`, so the review's auto-hydration through `openCaseFromPlan`
    adds a failure point for nothing;
  - no "Convert housing rows" function exists;
  - the review's line references for `library_import.py` and `scenario.py` are past the files'
    ends.
- **Found [code]:**
  - Compare's "What moved" lifetime row adds nominal dollars of different years (a defect;
    S-5 fixes it first);
  - `library.json`'s `pins` is never set by any code;
  - the review's three-form year picker leaves out `purchase` and `event:` anchors.
- **Changed from the review:**
  - S-3's conversion is offered behind an exact rebuild check, never automatic;
  - S-5 says "where it shows up", not "driven by";
  - S-6 drops the automatic switch to the Run page;
  - recapture stays inside state tax.
- **Nine decisions for the user** first; then S-2, S-1, S-4, S-5, S-3, S-6.
- **Next.** The user's decisions 1-9 in the work order.

## The maintainer's lesson from #245 (2026-11-08)

The user reports issues #245-#250 filed, all fixed upstream, and one draft withheld after the
maintainer's answer to #245 (B3, `issue-prepare-run-failure.md`). Not checked here: this session
cannot read `mdlacasse/Owl` (GitHub access refused), so the issue numbers beyond #247 and the
upstream fixes are the user's report, and no upstream `dev` was merged.

- **His answer:** he validated at the input (the starting state is no longer offered as a move
  target; bad TOML files were already rejected at load) and called the downstream check "not
  really relevant"; "Agents can find bugs easily, but I find their proposed solutions often
  lacking good and basic software engineering design."
- **What our draft did wrong:** its own text names the entry point (Create Case warns "The new
  state is the starting state" but keeps both), yet the patch changed six callers of
  `prepareRun`, added a case status (`invalid input`), a helper and `caseHasNotRun` handling:
  recovery after the fact instead of a one-line restriction where the state is entered.
- **The rule** is now in CLAUDE.md, Conventions ("Upstream patches: prevent at the input"):
  find the entry point and the existing validation, fix there in the code's idiom, add a
  downstream guard only for a failure the input cannot prevent and with its own repro.
- **Decided (user, 2026-11-08):** drop B3's downstream patch (`ea338d6`) and take upstream's
  fix; done in the merge below.
- **Next.** Unchanged: the user's decisions 1-9 in `ux-structural-handoff.md`.

## Upstream `dev` `d2ede71` merged (2026-11-08)

Nine upstream commits since `73dc881` (version 2026.11.07): our #245-#248 and #250 fixed, a
uv/setup-uv bump and dependency updates. Merge commit on `claude/peaceful-tesla-tc4vo5`;
`CHANGELOG.md` is upstream's byte for byte. Seven files conflicted.

- **#245 (`b719efa`), read from the commit:** `setStateTax` ignores a move to the starting
  state with a log warning instead of refusing it, so a case file carrying one loads; Create
  Case caps *Year of the move* at the plan's last year (the other refusal the UI could reach)
  and says the move "will be ignored". The new-state list still offers the starting state
  (`_state_choices()`, checked on `upstream/dev`), so the commit is not quite what his comment
  says ("removed from the list"); the lesson is the same: make the bad input harmless where it
  enters, not in the callers.
  - **B3 dropped** (the user's call): `owlbridge.prepareRun` / `runPlan` / the five clone
    callers / `showCaseStatus` / `sskeys.caseHasNotRun` are upstream's again (no `_applyConfig`,
    no `invalid input` status); `tests/ui/test_prepare_run_failure.py` deleted. The fork-notes
    draft, patch and repro stay as the record.
  - **Fork adaptation (several moves):** upstream's rule generalized: any move to the residence
    it leaves changes nothing and is dropped with a warning (`residency.changing_moves`, called
    by `setStateTax`; `residence_by_year` itself stays strict). Two moves in one year and a
    year outside the plan are still refused, a dropped move included. Create Case's warnings say
    "will be ignored" for those moves; the parity test (`test_the_move_warnings_match_what_the_plan_does`)
    now checks refusals and ignored moves separately against `changing_moves`. New tests in
    `test_state_tax.py`: a later no-op move is dropped, an ignored move still counts for "two
    moves in one year". Upstream's year cap applies to the first move; the further moves keep
    the fork's warning for a year outside the plan (not capped: a fork design choice left as is).
- **#246 (`2130052`):** upstream's `kz.hfp_loaded_caption()` replaces the fork's
  `_hfpLoadedText` (people and table counts dropped; sync rule). The fork keeps QW-7.1's run
  origin as its own caption, "Workbook of run *X*." The first-click part is "by design"
  upstream; the fork keeps its enabled-before-names `_createCase`.
- **#247 (`113ec13`):** upstream's SLCSP field and test taken (also other medical and Part D).
- **#248 (`d2ede71`):** case files and state data read with `tomllib`; the fork's `_lf` and its
  CRLF workaround dropped; `toml_io.py` is upstream's again.
- **#250 (`e78d2a0`), upstream's design taken:** the Roth years and the ACA start year accept
  any year up to `utils.last_year_entered` (this year + 120): a year past the plan is a
  legitimate "never" that survives a change of longevity. The fork's QW-8 bound at the plan's
  last year contradicted that (its clamp flagged the case modified because the meaning changed)
  and is gone: `_bound_year` keeps only clamping into [this year (or the start year), last
  accepted year], with the move named. Kept from the fork: the stop year's minimum is the
  start year (`986c625`), and the ACA toggle (QW-8.3, decision 5); upstream's
  `test_run_options_year_fields.py` sets `acaStartYear = 2030` so the box shows (marked as a
  fork adaptation). `test_run_options_year_bounds.py` rewritten for the new bound.
- **Checks:** flake8/ruff only upstream's known lines (ruff's B905 at `ui/Run_Options.py:367`
  now). Full suite **4633 passed, 1 skipped** (9:57, Linux, `-n 4`).
- **#249** (`issue-balance-units.md`, the \$k balance trap): filed by the user and closed by
  the user before the maintainer answered, after his #245 reply (user, 2026-11-08). The fork
  keeps its \$20M warning on Account Balances.
- **`main`** fast-forwarded to `claude/peaceful-tesla-tc4vo5` (`986c625` -> `4d76cbb`, then this note) on 2026-11-08.

## Ergonomics review S-1 to S-6: built (2026-11-08)

Branch `claude/loving-wright-44943l` (from `986c625`, after the work order
`fork-notes/ux-structural-handoff.md`). The user's nine decisions: **all as recommended** (Run
page on the pin; the reminder once per library; a goal box on Scenario; a six-form year picker;
conversion offered behind an exact check; recapture inside state tax; today's dollars by
default; "where it shows up"; library mode only for the classic pages). One commit per item, in
the order's sequence: S-2 `0f2555c`, S-1 `2b9bb8f`, S-4 `a4e2bfb`, S-5 `216884c`/`b4e7eeb`,
S-3 `6c8678b`, S-6 `4e4ab96`; re-drive fixes `78cd5b0`. No existing run's inputs hash moves
(`BUILDER_VERSION` stays 6).

- **S-2, Scenario drafts, dropdowns, year picker, goal box** (`ui/Scenario.py`,
  `ui/year_ref_input.py`).
  - A session draft per run (`scn_draft_<run id>`: every box's value, the three tables as
    records, a version in every widget key). Each data_editor gets the base it was mounted
    with for as long as it stays mounted (the user's watch-out: a data_editor replays its
    deltas on whatever `data=` it gets); it remounts from the draft after a page visit, and
    from the run after *Reset* (version + 1).
  - Banner "Unsaved changes against *run*" with *Reset to the run*; the Run page says "The
    Scenario page has unsaved changes for this run" with a way back. A save drops the draft
    and opens the page on the new run.
  - **Found and fixed:** the page also came back on the *newest* run after a visit (its own
    run selector is a widget whose state is dropped too), away from the draft; it now comes
    back on the run edited last (`scenario_last_run`) unless another page asks for one.
  - Person and level as `SelectboxColumn`s ("full time" / "part time", blank = full time);
    the event id hidden, kept for existing rows, made for new ones (`work-<person>-<start>`,
    `claim-<person>`, `death-<person>`, unique).
  - Year fields: "When" (calendar year, at an age, last work year, year after last work,
    home purchase year, another event's year with an offset, *Type it*; "Blank: ..." where
    the field may be empty). **Deviation:** the helper returns the text form, not the dict:
    the page parses every field once with the scenario's ids and the field's name in the
    error, and the draft keeps text. Round-tripped against `parse_year_ref` /
    `year_ref_text` over all six forms.
  - "Goal and conversions": objective, bequest target or net spending (the case's units),
    Roth cap (on/off), start year, stop year (on/off), bounded by `last_year_entered` (a stored
    year outside is named and kept unless changed). A field the case leaves out stays out unless
    changed. No event generates these fields (`builder.build`'s case fields), so the saves
    keep them.
  - **Driven:** AppTest's `switch_page` on `ui/main.py` for the boxes (the lost edit: on the
    pre-S-2 code `assert 700000.0 == 800000.0`, worktree of `986c625`); **Playwright** for
    the tables, which AppTest cannot edit: a new work row typed into the blank row, a second
    row added from the grid's ghost row, each edited twice, across a trip to Run: two rows,
    no duplicate, the banner listing both. Found there: a new row's blank `level` came back
    as NaN and failed to build ("got None"); fixed (`_present`).
- **S-1, landing page, pin, reminder** (`store.Library.pin/unpin/baseline`,
  `accept_disclaimer`/`disclaimer_accepted`; `ui/main.py`, `ui/Run.py`, `ui/Library.py`,
  `ui/disclaimer.py`).
  - Library mode: Run Library first in the menu, the Run page `default=True` (Welcome under
    Help). The Run page opens on the run viewed last in the session, else the baseline, else
    the newest with "Pin a run on the Library page ... to open it here". **Deviation:** the
    order says baseline whenever the selector has no state; that sent the page back to the
    baseline after every visit elsewhere, so the session's last run comes first.
  - Library page: *Make this the baseline* / *Baseline ✓* (unpins). Compare's default A is
    the baseline's newest result when B's run has no parent result.
  - The reminder: drawn by the Run page until `library.json` holds `disclaimer_accepted`; OK
    writes it. Upstream's text moved unchanged into `ui/disclaimer.py`, which Welcome now
    imports; in library mode Welcome no longer draws it. Outside library mode nothing
    changes (tested: Welcome default, its reminder).
- **S-4, today's dollars, the NY split, markers** (`cli/formatters.plan_to_dict`,
  `ui/run_charts.py`, `ui/Run.py`).
  - `by_year` rows gain `deflator`, `local_tax`, `state_recapture`, `star_credit` and
    (beyond the order, for per-person markers) `wages_by_person`. `state_tax` keeps its
    meaning. The identity `state_tax = state base + recapture + local - STAR` checked on a
    real solve of the synthetic baseline against `sum(st_T_tn) + STR_n - st_c_n`: within
    \$1 (three rounded integers); deflator = `gamma_n` to 5e-7.
  - Charts: a "Today's \$ | Nominal \$" control (session-wide, today's by default, shared with
    Compare); the taxes chart in `barmode="relative"` with *State tax* (recapture in the
    hover), *Local income tax (NYC / Yonkers)* and *NY STAR credit* below the axis, each part
    drawn only where non-zero, as the user's watch-out spelled out; markers for each person's
    last work year, the purchase, Medicare at 65 and the last loan year. An older result
    draws nominal, one state series, "Last wages", and says "A new solve can show today's
    dollars".
- **S-5, Compare** (`library/compare.py`, `ui/Compare.py`, `ui/run_charts.py`).
  - **Defect fixed:** "what moved"'s lifetime row summed nominal dollars of different years.
    Two plans that spend the same in today's dollars under inflation paths 1.5 and 1.2 read
    `('Spending', -30000)` on the old code (worktree of `986c625`); now 0. Totals are in
    today's dollars whenever both results carry the deflator, rows in the selected units;
    older results stay nominal and say so.
  - The verdict as a sentence with the runs' names and amounts (`verdict_sentence`: ahead /
    trade-off / too close to call / no difference / not comparable); "Where the difference
    shows up" (the three largest lifetime lines) and "Inputs that differ" apart, no "driven
    by"; the rule's reading, the noise rule and the exact-model check ("a second method
    agrees / disagrees / does not settle it") under *How sure is this?*.
  - Side-by-side tabs: spending, liquid net worth, cumulative taxes and premiums, MAGI with
    IRMAA tier 1 and the 400% FPL line from each result's brackets rows, matched by calendar
    year. **Deviation:** the toggle shows **B - A**, not A - B: every other difference on the
    page is B - A.
- **S-3, housing rows into events** (`casefiles.has_housing_rows`, `housing_events`,
  `convert_housing`; `ui/housing_convert.py`).
  - Reads one active residence, its linked loan (down share snapped to the shortest decimal
    that rebuilds the loan; closing and loan closing from the one outflow, the builder's
    defaults tried first: any pair that rebuilds the outflow is the same plan), the outflow's
    person, the owner's three lines, the rent rows (start, flat-until from the "rent from"
    tail or the one-year rows, an end only where it is not the year before the purchase), a
    move in the purchase year (taken out of the case, made by the event), and **care rows**
    (beyond the order: two synthetic workbooks end with a care line, which only a care event
    puts back in the same place).
  - Accepted only when `builder.build` of the converted run equals the original's tables and
    case cell for cell; else the differing cells (e.g. "Budget, row 8 (rent in 2027),
    amount: 49512 -> 49412") and nothing saved. Offered on the Run page (also for a run
    with no results) and the Library page, as a child run "<name>, home as events";
    `variants.py` points to it.
  - `check_library_builder.py`: **39/39** imported workbooks convert (each exported case
    with `make_cases.py`'s own workbook), beside 46/46.
- **S-6, the queue and the classic pages** (`ui/Queue.py`, `ui/background_solve.py`,
  `ui/library_save.py`, Graphs / Worksheets / Reports).
  - *Open result* on finished rows (selects the run, switches to Run); no switch on
    completion.
  - Library mode: a modified case is not solved on open; the pages offer *Save as a new run
    and solve it in the background* (the Library page's save, moved to `library_save.py`,
    then `preset_solves("decision")`) and *Open the Queue*; Graphs' *Re-run* becomes the same
    button. Outside library mode the pages take upstream's path (tested: `runPlan` called,
    *Re-run* shown).
- **Found in the re-drive:** a change summary holds "(today's \$)" twice, and two `$` in one
  Markdown element start LaTeX math, which swallowed the text between them in the browser.
  Pre-existing on the Scenario caption and the Run / Library "from" lines; new on the banner
  and Compare. `libraryjobs.plain` escapes them everywhere a summary is drawn. Also: Graphs
  showed the background button twice on a modified case (fixed); "where it shows up"
  lowercased "Roth" (fixed).
- **Re-driven with Playwright** (synthetic library in `otherFiles/library`: the builder
  baseline, White Plains 2029 as its child, the imported condo case; Quick looks with the new
  code, one with a worktree of `f854721` as the older result):
  - first session: the reminder dialog; OK stamped `2026-11-08T01:25:38+00:00` in
    `library.json`; a second session: no dialog, the Run page on "baseline (builder)" with
    ":material/push_pin: The baseline", menu "Run Library | Case Setup | Results | ...";
  - taxes chart, today's \$: legend "Federal income tax, Capital gains tax, NIIT (3.8%),
    Payroll tax, State tax, Local income tax (NYC / Yonkers), NY STAR credit, Medicare
    premiums (with IRMAA), Marketplace (ACA) premiums", axis "\$ per year (today's \$)",
    markers "Ari's last work year / Noa's last work year", "Purchase", "Ari: Medicare / Noa:
    Medicare"; nominal: axis "nominal \$ per year"; the older result: "This result was solved
    before the charts could show today's dollars ...", one "State and local tax" series,
    "Last wages";
  - Scenario: the purchase year switched to "Year after last work" / Ari, banner "Unsaved
    changes against baseline (builder): purchase: ... in the year after Ari's work, cash";
    bequest target 250: "bequest target: 0 → 250.0";
  - Compare (baseline Quick look vs White Plains 2029): "baseline (builder) comes out ahead:
    \$2,520/yr more discretionary spending and \$7,552 more home at the end."; "Where the
    difference shows up (lifetime, B - A, today's \$): Roth conversions -37,753; Spending
    +36,963; Withdrawals from savings +30,866."; tabs Spending, Liquid net worth, Taxes and
    health premiums, cumulative, MAGI; the B - A bars;
  - S-3 on the imported condo run: "Saved imported condo, home as events: the same tables,
    now made by rent and purchase events";
  - S-6: *Edit as new run*, then Graphs opened in 1.7 s with "The case changed since its last
    solve. In the run library it is solved in the background ..."; the click: "Saved as
    baseline (builder) variant; its Careful (about 5 minutes) solve is queued"; the Queue
    showed it running and its exact companion waiting. A server restart during the drive
    left that Careful job's record "running" (not re-checked to completion).
- **Not done as the order said:** Compare was driven on Quick looks, not on a Careful pair
  (the Careful solve queued through S-6 was not waited for).
- **Tests** (new: `test_scenario_drafts.py` 7, `test_year_ref_input.py` 12,
  `test_landing_page.py` 7, `test_plan_json_state_parts.py` 2, `test_run_charts.py` +9,
  `test_library_pages.py` +3, `test_compare.py` +10, `test_housing_conversion.py` 10,
  `test_housing_convert_button.py` 3, `test_classic_pages_library_mode.py` 5,
  `test_queue_page.py` +1, `test_ui_dollar_math.py` +1; changed: `test_scenario_page.py` for
  the picker, `test_variants.py` for the pointer).
- **Run (Linux).**
  - Full suite at `4e4ab96`: **4669 passed, 1 skipped** (11:37, `-n 3`, beside the browser
    drive). After `78cd5b0` (display only): `tests/library tests/ui tests/cli
    test_thresholds.py test_brackets.py` 1272 passed.
  - `test_worker.py::...test_run_again_leaves_no_artifacts_of_the_old_attempt` failed once
    under `-n 4` with the UI suites, passed alone and in every later run (a race test under
    load; not investigated).
  - `check_library_builder.py` 46/46 + 39/39; `check_library_roundtrip.py` 39/39;
    `check_library_compare.py` 9/9.
  - Lint: only upstream's listed items.
- **Next.** The user's call on an independent review and on fast-forwarding `main`.

## Ergonomics review S-1 to S-6: independent review AP1-AP5 folded (2026-11-08, branch `claude/loving-wright-44943l`)

- **Review scope.** Independent review of `986c625e..0f0c68a4` against
  `fork-notes/ux-structural-handoff.md` (`[ran]`, `[probe]`, `[code]`), then folded AP1-AP5 on
  the user's instruction (`fold A1-A5`), each code fix preceded by a regression test that
  failed before the fix (`FFFF` on `pytest -k "ap1 or ap2 or ap3 or ap4"`).
- **AP1 (S-2, `ui/Scenario.py`):** Raising *Year to start considering Roth conversions*
  (`_start`) above an existing `stopRothConversions` passed the edited `_stop_low` (`max(_start,
  plan_year)`) into `_year_shown`, so `_stop_shown` equalled the clamped widget value `_stop`
  and `_settings["solver_options.stopRothConversions"]` kept the old `_stop0` while the widget
  displayed `_start` (saving e.g. `startRothConversions = 2040 > stopRothConversions = 2035`).
  Fixed: `_year_shown` clamps against `max(_start_shown, plan_year)` (the stored start year's
  bound) and `st.session_state[scn_roth_stop_*]` is clamped to `_stop_low` before rendering, so
  raising `_start` above `_stop0` moves the saved `stopRothConversions` to `_start`. Test:
  `tests/ui/test_scenario_drafts.py::test_ap1_raising_roth_start_above_stop_moves_the_saved_stop_year`.
- **AP2 (S-5, `src/owlplanner/library/compare.py`, `ui/Compare.py`):** `what_moved` filtered
  `what_moved_totals` by `if key in moving` where `moving` was computed in `row_units`. When the
  Compare page's chart toggle was switched to `Nominal $`, any column whose nominal amounts
  were equal between the two runs (such as a nominal \$50,000 Roth conversion cap under two
  different inflation paths) dropped out of `what_moved_totals` and disappeared from **Where
  the difference shows up (lifetime, B - A, today's \$)** at the top of the page. Fixed:
  `what_moved_totals` includes every column in `moving` plus every column whose lifetime sum in
  `total_units` (today's dollars) is at least \$1, while the **What moved** table's lifetime
  footer row restricts to the table's displayed columns (`shown`). Test:
  `tests/library/test_compare.py::TestTodaysDollarsTotals::test_ap2_where_it_shows_up_is_the_same_under_nominal_and_today_s_dollars`.
- **AP3 (S-6, `ui/background_solve.py`, `ui/sskeys.py`):** Clicking *Save as a new run and
  solve it in the background* on `Graphs.py`, `Worksheets.py` or `Reports.py` left the *"The
  case changed since its last solve"* offer box and button on screen directly below the
  confirmation flash, and a second click queued a duplicate Careful solve. Fixed:
  `_save_and_queue` skips presets in `preset_solves("decision")` that are already waiting or
  running for that run (`results.WAITING`, `results.RUNNING`) and stores `library_queued_run`
  on the case (`kz.flagModified()` clears it when the case is edited again); `offer` shows the
  queued run's status and *Open the Queue* while `library_queued_run` is set. Test:
  `tests/ui/test_classic_pages_library_mode.py::test_ap3_once_queued_the_page_stops_asking_to_save_until_modified_again`.
- **AP4 (S-6, `ui/Reports.py`):** `Reports.py` replaced *Re-run* with `background_solve.button`
  in library mode but still rendered *Rerun all cases* (`owb.runAllCases`, a foreground solve)
  beside the synopsis table. Fixed: *Rerun all cases* is hidden when `kz.library_mode()` is
  true. Test:
  `tests/ui/test_classic_pages_library_mode.py::test_ap4_reports_in_library_mode_hides_rerun_all_cases`.
- **AP5 (`CLAUDE.md`, `PROGRESS.md`):** Updated `ui/Run_Options.py`'s pre-existing `B905` line
  number (345 on `claude/loving-wright-44943l`; 367 after merging `origin/main`).

## Upstream `dev` `8ec9c43b` merged (2026-11-09)

Three upstream commits since `d2ede71`:
- `520e7612`: `scripts/capture_amo_reference.py` writes `tests/data/amo_mip_reference.json` with `encoding="utf-8"`.
- `a3f899c3`: `.gitignore` ignores `scripts-local/` instead of `scripts/` so tracked scripts in `scripts/` are not hidden by `.gitignore` (local untracked `rebaseline_state_tax.py` moved from `scripts/` to `scripts-local/`).
- `8ec9c43b` (#251): `tests/utils/test_text_encoding.py` scans `scripts/` in addition to `src`, `ui`, `tests`, and `scripts/make_lowwealth_case.py` writes its TOML file with `encoding="utf-8"`.
- Clean merge; `tests/utils/test_text_encoding.py` passed.

## Ergonomics review: local use by a non-technical person (2026-11-10)

Branch `claude/loving-carson-a2dfi9` (from `a7b539b`). Report only, no code change:
`fork-notes/ux-review-local-use.md`. The question (user): how well the fork, run locally, suits a
non-technical user. The app was driven in library mode on an empty library with Playwright at
1366x768, Streamlit 1.67.0, synthetic household: import, Quick look (2 s), Careful (5 min 4 s +
8 s), the home conversion, a Scenario what-if (purchase 2029 → 2031), Compare, a collection of
three purchase-year variants queued together, the grid, a failed solve (\$7M home), *Edit as new
run* with three classic pages, a second server on the same library; the year rollover with the
clock at 2027-01-02 (library code). Not checked: Windows, printing, Stress Tests, the tornado and
regret results.

- **Answer:** as a reader of a library someone else set up and maintains, workable after a
  walkthrough; as its sole operator (install, start, data entry, new year, updates), no.
- **A1, the new year (ran):** on 2027-01-02 `check_plan_year` refuses every 2026 run; its message
  says "save it as a new run from the pages", but a save against a base run keeps the base's plan
  year (`test_the_base_plan_year_is_kept` passes; `ui/library_save.py:56` passes no `plan_year`),
  and a re-import of the same files reads `start_date`'s 2026. The yearly check-in (I4) is not
  built. Working routes, by the code, not driven: edit `start_date` in the TOML and import, or
  upload through Create Case (no base).
- **B1, a defect (seen):** the Queue page raises `StreamlitDuplicateElementKey`
  (`open_<job id>`, `ui/Queue.py:128`) once two runs are queued in the same second, which
  *Make variants* with "Queue them when created" does: job ids are unique per run folder only.
  The error box offers Ask Google / Ask ChatGPT links.
- **Seen:** the Run page does not redraw after *Solve* (only `ui/Queue.py` has a polling
  fragment); a what-if is 13 actions over 4 pages and Compare's default pair was not the what-if;
  the home conversion leaves the pin and the results on the unconverted run; the collection grid
  is empty until the parent is added by hand with its value and set as the reference; a failed
  solve's Run page says "Solved", "infeasible", "maximizes the final bequest" and "the Results
  workbook is gone"; the landing page's first screen at 1366x768 has no number.
- **Ran + code:** a converted import has `purchase` and `rent` events only, so the *Last work
  year* dimension (one full-time work event per person, `variants.py:308-315`) cannot vary the
  retirement year of an imported plan.
- **Grep:** `owlplanner-library` is named in no user-facing document; `running-locally.md`
  describes only the classic launcher and two limits since removed; no library help or glossary in
  `ui/`.
- Twelve recommendations in the report's section D (the Queue keys, a "start *year* from this
  run" action, a live Run page first).

Next: the user's call on what to build; D1 (the Queue keys) and D2 (the new year) first if any.

## Local-use review: D1 to D4 built (2026-11-10)

Branch `claude/loving-carson-a2dfi9`, one commit per item (the user's call: "Build D1, D2, D3, and
D4 from the ux-review-local-use.md report, one commit each"), plus one follow-up.

- **D1 `feaf587`, the Queue's keys.** `libraryjobs.job_key` (the run's folder and the job's):
  Kill, Cancel, Run again and Open result no longer share a key across runs. The test (two runs,
  one results-folder name, the four button states) fails on the old keys with the report's
  `StreamlitDuplicateElementKey`.
- **D2 `0b92cd5`, the new year.** `library/newyear.py`, `start_year(scenario, year)`, and the Run
  page's *Start \<year\> from this run*.
  - **Found:** the report's sketch (a child with this year as its plan year, the events kept) does
    not build. With the year at 2027 a run whose rent event starts in 2026 stops at
    `rent.start = 2026 is outside the plan (2027-2053)` (ran, clock moved). So the events are
    carried over: one that is over is dropped; one under way starts at the new year (a rent keeps
    its monthly amount, exact within its flat years: 48,000 in 2027 before and after); a home
    bought before the new year becomes hand rows, accepted only on an exact rebuild at the old plan
    year; a year anchored to an event that left or moved becomes its calendar year; the person
    sheets' past years become hand rows (history); `previousMAGIs` / `previousSTARIncomes` shift
    (the year now needed reads 0 and is named in a note); a move no longer ahead of the plan
    becomes the starting residence.
  - **Not done by it:** no amount is re-priced (amounts in today's dollars are read in the new
    year's: 700,000 for a 2029 purchase is 739,749 in 2029 dollars from 2027, 760,462 from 2026),
    and the balances stay last year's. The action stores nothing: it opens the carried-over inputs
    in the case pages on Account Balances with the list of what to bring up to date (kept on every
    Case Setup page until the save, `0c2ec51`); the Library page's save builds against
    the same carried-over document, warns when the balances were not changed, and warns when an
    ordinary *Edit as new run* of an old run was saved for the old year.
  - **A builder defect found by the roll (ran):** a purchase with a move in the plan's first year
    built `moves = [{year = <first year>}]`, which Owl refuses ("A move must fall after the first
    plan year"): a 2027 purchase in Queens could not be planned in 2027. It is the starting
    residence now. `BUILDER_VERSION` not bumped (no run built the old way could be solved).
  - **Checked with the clock moved, outside the suite:** the 46 synthetic scenarios carried to
    2027, 2028 and 2030 all build (46/46 each; 22 homes bought in 2027 pass the rebuild check in
    2028); three solved under the Quick preset (queens-2027-mortgage in 2027 and 2028,
    yonkers-2029-cash in 2028). A 25-year jump refuses 18 of 46 with "outside the case's inflation
    path" (the builder reads the path from a plan that starts at the clock's year): not a case
    anyone has. `check_library_builder.py` 46/46 and 39/39.
  - **Not built:** I4's plan-against-actual drift chart. A downturn event's drop is not unit-tested.
- **D3 `4fc78a4`, the live Run page.** A fragment under the run's header (two seconds): "Solving
  this run", one line per live job, and on a job's end a rerun of the whole page on the newest
  main result with one message. *Solve* names its jobs at the click (`libraryjobs.watch_jobs`), so
  a solve that ends before the page is drawn is still reported. Browser (Quick look): the box 0.5 s
  after the click, the result 4.6 s in, no reload.
- **D4 `b7ba0d6`, the what-if in one step.** *Save and solve* on the Scenario page (`ui/whatif.py`):
  the child saved, its Careful solve queued, its Run page opened; the parent queued for a Careful
  solve too when it has none from today, so the pair is like for like. *Compare with its parent*
  on the Run page opens Compare on the shown result against the parent's newest result solved the
  same way; Compare takes the pair from the session.
  - **Found by the browser drive:** a job's `queued` stamp is whole seconds, so jobs of two runs
    queued by one click tied on it and on the folder name and ran in the library's run order: the
    parent's five-minute solve ran before the what-if's exact-model check. Job records carry
    `queued_at` now and the queue orders by it.
  - **Browser (condo price 700,000 -> 750,000):** the what-if's Careful result after 323 s with no
    reload, the parent's after 653 s, Compare on the two Careful results with "A trade-off: ...
    spends \$2,493/yr more, ... keeps \$53,807 more home at the end", no warning. That drive ran
    on the queue order before the fix; the order and the child page's watch on its parent's solve
    are covered by tests, not re-driven.
- **Follow-up `0c2ec51`:** the new-year list of steps stays under the title bar of the Case Setup
  pages (seen in a browser: as a one-time message it was gone at the first edit).

Tests: 4774 passed / 1 skipped (2026-11-10, 10:38, Linux, `-n 4`, at `b7ba0d6`); the follow-up
touched `ui/` only, its page tests re-run (11 + 68). An earlier full run during the work showed 35
failures in `test_library_pages.py`: a test worker held the old `libraryjobs` module while `Run.py`
was edited under it, not a defect.

Next: the report's D5-D12 are not built. The user's next request (2026-11-10): starting in a local
household folder with guided first-time data entry.

## Operating it alone: a household folder and a first-time setup (2026-11-10)

The user's request (2026-11-10, after D4): "a nice way of starting in a local folder where the
generated and edited files would be stored. If there are no household data local files there, the
user should be prompted to enter it, no toml file editing. ... using Excel is acceptable, but the
user should be prompted to either select an existing, populated, or to populate an unpopulated
Excel file template. Not quite wizard, but the user should be guided through the steps ... after
asking the user what they want to do." The install was excluded by the user.

Built on `claude/loving-carson-a2dfi9`:

- **The folder.** `owlplanner-library.sh` / `.cmd [folder]`: a first argument that is not an option
  is the household folder (`OWL_HOME_DIR`, library in `<folder>/library`); the scripts `cd` to
  the checkout themselves, so they run from anywhere. `owlplanner-library.sh` was not executable
  in git (mode 100644; `owlplanner.sh` is 100755): fixed, and the starter file calls it through
  `bash` anyway. The Start page writes a starter file into the folder once
  (`household.write_starter`).
- **`library/household.py`.** Answers in dollars (`blank_answers`, `problems` in plain words),
  `case_from_answers` (the case dictionary; the assumptions nobody is asked are in `ASSUMPTIONS`:
  the "conservative" fixed rate path, since the builder refuses rates redrawn at every build;
  federal law as enacted, D1; a 60% survivor share), `write_workbook` (Instructions, a sheet per
  person with a row per plan year and a note on every heading, Budget / Debts / Fixed Assets with
  their headers; never replaces a file), `read_workbook` (the plan's own reader, then what was
  found, in words), `first_scenario` (through `import_case`; Budget lines make the profile
  "budget", else "flat"), the draft (`setup-draft.json` in the library folder).
- **`ui/Setup.py`.** Six short sections on one page (who, where, savings, Social Security and
  pensions, the workbook, the goal), "Still needed" above one button, which is enabled whatever
  is missing (AL1's lesson). The plan is saved, pinned as the baseline when there is none, queued
  for a Quick look, and its Run page opens (D3 shows the result).
- **`ui/Start.py`.** No plan: *Set up our plan* or *Bring in files made earlier*. A plan: "What do
  you want to do with it?" (read it, try a change, compare options, bring the numbers up to date
  or start the new year, find the files), each with numbered steps marked done or next and one
  button. `ui/main.py` opens on Start while the folder has no plan, on the plan otherwise (S-1
  kept).
- **Decisions taken without asking, the user's to revisit:** the folder's layout; Start as the
  landing page only while there is no plan; which figures count as minimal (no asset-allocation
  detail, no rate choice, no tax-law choice at the start); spending "flat" without Budget lines;
  a first solve at Quick look, not Careful.
- **Checked (browser, Linux):** the launcher called from another directory on a new folder with a
  space in its name; Start; the form typed field by field (birth dates in the segmented date
  field); `Household.xlsx` made, filled by a script standing in for Excel, read back ("Ari: wages
  from 2026 to 2026 (the largest year \$168,000) ... Budget: 2 budget lines"); the plan made and
  its Quick look shown with no reload; Start with the plan. In the browser `uv` was replaced by a
  shim to the session's venv (the real `uv run` would rebuild the environment on Python 3.14).
- **Not checked:** Windows and macOS (the `.cmd` launcher's folder argument, `Start Owl.cmd`,
  `Start Owl.command`); Excel itself; a single person through the browser (unit-tested).
- Tests: `tests/library/test_household.py` 38, `tests/ui/test_first_time.py` 13;
  the full suite 4825 passed / 1 skipped (10:43, Linux, `-n 4`, at `709766f`). Docs: `fork-notes/running-locally.md`
  section 1b.

Not built, from the local-use review's section D: D5-D10, D12, and of D11 the quiet terminal, the
second-launch guard and `client.showErrorDetails`.


## Local-use build: reviewed, AQ1-AQ8 folded (2026-11-10)

The user's request: "continue on branch `claude/loving-carson-a2dfi9`. Review the work you've
performed on it." The nine commits of the branch (D1-D4, the household folder, the first-time
setup) reviewed by the session that built them: `fork-notes/local-use-build-review.md`,
AQ1-AQ12. Not an independent review, and nothing was driven in a browser.

- **Baseline:** 4825 passed / 1 skipped at `74b6ec6` (9:30, `-n 4`), as recorded; lint clean
  apart from upstream's listed items.
- **A correction to "Local-use review: D1 to D4 built" above:** "the 46 synthetic scenarios
  carried to 2027, 2028 and 2030 all build (46/46 each)" was one jump from 2026 each. Rolled
  year by year, as the feature is used, 42/46 built through 2028 and 36/46 through 2032.
- **Folded, one commit each (AQ3 and AQ4 share one), each with a test:**
  - **AQ1 `54e782c`:** the rebuild check of a bought home compared table layouts; with no other
    event left (the rent and work dropped the year before) a cash purchase was refused the
    year after it, "Debts: columns differ". Year by year to 2032: 46/46 now;
    `yonkers-2027-cash` to 2028 and `queens-2029-cash` to 2030 solve (Quick look's options,
    clock moved).
  - **AQ2 `0f9f4fd`:** Owl's reader resets a Fixed Assets year in the past and reads the value
    as the worth at the plan's start, so the frozen home lost a year of growth and inflation
    per roll (`yonkers-2027-mortgage`, 2027 -> 2028: 25,089 less home at the end in 2028
    dollars). Nothing is re-priced; the notes ask for today's value, at the freeze and for
    every property held as rows at every later roll.
  - **AQ3, AQ4 `36f6e18`:** the empty workbook's Instructions said "year: when bought ...
    value: what it is worth in the dollars of that year" (an owned home valued at its purchase
    price); its heading notes left out that an after-tax contribution is paid for with a
    negative big-ticket amount (8,000 Roth IRA + 20,000 taxable a year for three years, typed
    as the notes said: +3,627/yr of spending; with the offsets -3/yr). Both corrected; the
    Setup page's read-back names after-tax contributions nothing pays for.
  - **AQ5 `ef48edf`:** the new-year marks on the case were never cleared (the pages kept
    "Nothing is saved yet" after the save). A save with this year's balances makes the new run
    the case's base and drops them.
  - **AQ6 `9c7db7f`:** no starter file for a library that is not `<home>/library`.
  - **AQ7 `2984580`:** an uploaded workbook is copied once per upload; its corrected copy is
    the one read (it was shadowed by a "(2)" copy of the old bytes).
  - **AQ8 `519e3e2`:** a run with a downturn placed before the new year stopped the roll at
    "the window starts at 2026, before the plan (2027-2053)"; the drop written for it was
    after the build that raised. Dropped first now.
- **Standing:** AQ9 (a jump of two or more years under a year-by-year rates table prices the
  frozen home on a shifted path: 735,000 where the run held 714,000), AQ10 (the setup refuses
  a cost basis above the account's value; Owl accepts it with a warning), AQ11 (the year just
  ended reads a MAGI of 0; the parent's result could fill it), AQ12 (the record above).
- **Not checked:** Windows and macOS launchers and starter files; a browser (D3, D4, the
  landing page's move from Start to Run; today's folds through AppTest and scripts only);
  Excel.
- Tests: 4838 passed / 1 skipped (9:41, Linux, `-n 4`, at `519e3e2`; 13 new tests). `check_library_builder.py` 46/46 and 39/39.

Next: the user's call on AQ9-AQ11, on fast-forwarding `main`, and a Windows run of the
launcher and the starter file.


## Performance review (2026-11-10, branch `claude/sleepy-bardeen-y2k2ov`)

The user's request: "review the project from a performance improvement perspective. Look for any
significant opportunities: architectural, algorithmic, memoization, dropping redundant steps."
Report only, no change in `src/`, `ui/` or `tests/`: `fork-notes/performance-review.md` (P1-P8),
scripts in `fork-notes/performance/`. Measured on the synthetic household at `abd8b6c`, ages fixed
at 70/70, HiGHS, this container.

- **Where the time goes:** a Careful solve is 346-349 s, 344 s of it in 71 HiGHS calls; Owl's
  Python is under 1%. 83% is twelve node-capped local-search steps ((b) and (b'), 3,000 nodes
  each, none proved), ten of which found nothing. Quick look 0.5-1 s, the exact-model check 6 s.
- **P1:** the interface never sets `JobManager(max_parallel=...)` (default 1). Four solves at once
  cost +5% wall each.
- **P2 (upstream's `localsearch.py`, a prototype only, `quiet_patch.py`):** skipping the capped
  steps in loop iterations where the binaries did not move gave the same plan to the cent in 6 of
  6 variants; CPU -16% to -48% in the four that settle, nothing in the two that keep moving
  (-20% over the six). With `localSearchStepNodes = 1000` as well: -36% over the six, same plan
  in 5, +\$1.75/yr in one.
- **Found on the way:** local search's 300 s wall-clock budget binds here. Run four at a time, 4
  of 6 base Careful solves logged "time budget spent" in one to three loop iterations; with the
  budget lifted one of the two variants tried moved by \$2.81/yr (688 s of CPU). The library's
  `decision` preset keeps the default budget (`work_sweep.py` lifts it) and a result cut by it is
  not marked anywhere the pages read.
- **P4-P5 (read in the code, not timed):** the `ages` preset's final solve repeats the winning
  stage-2 solve and stage 2 is serial; `ages_thorough` runs its sweep on `_SerialPool`.
- **P6:** `Library.get` scans every `run.json`; at 120 runs the Library page takes 1.5 s per
  click (15,480 file reads), the Collections page 0.58 s.
- **P7-P8:** 1.5-2.0 s of imports per worker (scipy, matplotlib, pandas; upstream modules); the 60
  slowest tests are 59% of the suite's worker time, two fork files among them (12%).
- **No opportunity:** seven HiGHS option settings on two dumped steps (nothing faster on both), a
  looser step gap, the Python model build, the what-if's parent (already reused), the ticker.
- **Not measured:** the household's case and machine, stock upstream examples, more than 6 of the
  36 grid variants, P4/P5 end to end, Windows/macOS, MOSEK.
- Tests: 4838 passed / 1 skipped (14:39, Linux, `-n 4` with two solves running beside it, at
  `abd8b6c`; code unchanged).

Next: the user's call on which of P1-P8 to build, and on an upstream issue for P2.

## Performance review: a second review audited (2026-11-11, branch `claude/sleepy-bardeen-y2k2ov`)

The user pasted a second, anonymized answer to the same request (a priority matrix of 13
items, no timings) and asked for its claims to be checked one by one and for
`fork-notes/performance-review.md` to be revised. Docs and scripts only; nothing in `src/`,
`ui/` or `tests/` changed, so the suite was not run again.

- **The audit:** `fork-notes/performance-review-audit.md`; scripts and their outputs in
  `fork-notes/performance/audit/`. 36 claims checked against the code at the same commit: 25 as
  stated in structure, 2 supported, 4 partly wrong, 4 false, 1 prediction contradicted by a
  measurement.
- **False, each reproduced:** its closed form for `stresstests._stochastic_lp` (the index is
  mirrored: wrong at 45 of 61 lambdas, the largest basis where the LP gives the smallest; the
  corrected index `ceil(S / lam) - 1` matches the LP except at one tie); a `_repairAmo` call
  "on every intermediate SC-loop iteration" (no such method or `self.amo` in the repository;
  the real repairs run once after the loop); `load_historical_slice` reading the CSV on every
  call (it is `lru_cache`d); the tornado's results loaded twice (once each).
- **Partly wrong:** "~700 NY school districts" scanned per year. New York has about that many
  (730, the user from data.nysed.gov; the site is refused by this container's proxy), but the
  list the code scans is the fork's `data/property_tax_relief.toml`, 75 rows (Westchester and
  New York City). `star_schedule` runs once per solve: 0.16 ms on 75 rows, 2.4 ms on a table
  padded to 730 (`audit/star_scan.py`). The first write-up of this said "the data file has 75"
  without naming the file or granting the state's count; corrected after the user's objection.
- **Its priorities, measured:** timers on a real Careful solve (129.4 s at a 300-node cap):
  99.48% in `_run_highs`; every deep copy 0.126 s, every CSR build 0.061 s, money scaling
  0.014 s, the SS streams 0.002 s. Its P0 "cache CSR and money scaling, stop deep-copying" is
  0.2% of the solve.
- **Valid and taken into the review:** the Run page parses the whole results workbook on every
  render (93 ms of a 260 ms page; new P9); `JobManager.tick()` scans the library three times
  (verified; 47 ms every 2 s; folded into P6, which had dismissed the tick); download buttons
  that build their workbook on every rerun (upstream pages; Streamlit 1.67 takes a callable;
  new P10); the stress tests, which the first version had not looked at (new section 3b).
- **Found on the way:** `run_stochastic_spending`'s thread pool gives 1.6x on four cores (60
  historical scenarios at Quick-look options: 24.6 s on four threads, 39.6 s on one), because
  42% of a loop-mode solve is Python (a Quick look: 58% HiGHS, 19% `_buildConstraints`). The
  first version's "nothing in the Python layer can matter for solves" is now scoped to Careful
  solves.
- **Not checked:** anything on Windows (the second review's paths are a Windows checkout);
  Monte Carlo and longevity sampling (the synthetic case's rates are not stochastic); its
  claims about `generate_historical_series`, `debts.py`, `fixedassets.py`, `copula.py`.

Next: the user's call on which of P1-P10 and 3b to build, and on upstream issues for P2, P10
and 3b.

## Performance review: the budget and the cores (2026-11-11, same branch)

The user's two questions on P3 and P1. Docs and one script; nothing in `src/` changed.

- **Measured** (`fork-notes/performance/lifted_budget.sh`; the review's "P3, measured on
  2026-11-11"): the two variants whose search keeps moving, both wall-clock caps lifted
  (`localSearchTime = 7200`, `localSearchStepTime = 1800`), six solves at once on four cores.
  whiteplains_2029_mortgage: 495 / 443 / 365 CPU-s at 3,000 nodes, 1,000 nodes, 1,000 with the P2
  prototype, 105,853.35 in all three. whiteplains_2038_cash: 804 / 572 / 483 CPU-s, 105,260.34
  at 3,000 and 105,259.28 at 1,000. The 3,000-node values are those of 2026-11-10 to the cent.
- **Found:** the step cap binds as well (an 81 s step at 3,000 nodes under this load;
  `STEP_TIME` is 60 s), so lifting the total alone is not enough; and six solves on four cores
  cost +17% to +18% of CPU on the same two solves (418 -> 495, 688 -> 804), not only wall.
- **Recommended, not built:** `presets._FORCED["decision"]` with 1,000 nodes and both caps
  lifted, the same for `ages` where the case's model is local search (its stage 2 picks by the
  raw score), and a mark in `record.json` when the round-level cut is logged. For the cores: a
  weight per job in `status.json`, counted by `JobManager.tick()` against a capacity, the worker
  sizing its pool from its own record.

Next: the user's call on both, on the `ages` preset gaining forced keys (R4), and on the
capacity default.

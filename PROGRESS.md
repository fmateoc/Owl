# Owl fork — progress (as of 2026-10-23)

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
| #185 Federal itemized deductions (design; `fork-notes/issue-federal-itemized.md`) | Posted by the user. Maintainer's reply (relayed 2026-10-15): "I'll need to look more deeply into it. Adding more stuff to the recursion loop is what causes cycling and prevents monotonic convergence. I'll run a few tests and get back to you." Measured the same day against that concern (section "Itemizing and loop convergence"); data comment `fork-notes/issue-185-reply.md` posted by the user (relayed 2026-10-16). The NY + mortgage failure it mentioned was traced to upstream's SS loop and filed as #193 (2026-10-16); pointer comment linking #193 posted by the user (2026-10-16). Rechecked 2026-10-17 after the NJ removal: conclusions hold; the NJ stakes rise on upstream's NJ (section "#185 after the changes since filing") |
| #199-#217 (not ours; filed 2026-10-20/21, 17 by `rationalpiper`, #208 by the maintainer) | **Fixed upstream** (`dev` `37afa2a`, 2026-10-22) except #204 (proposal), #205, #206; #218 (survivor's home-sale exclusion) too. Merged 2026-10-22, theirs; fork adaptations and a review fix in "Upstream `dev` `37afa2a` merged". Checked before the fixes 2026-10-21: no claim found wrong (`fork-notes/upstream-199-217/README.md`) |
| #220 SSA earnings test (design issue, ours) | **Posted by the user 2026-10-22** (`fork-notes/issue-earnings-test.md`, Phase 5 step 9): stock-`dev` `37afa2a` evidence (three examples pay SS before FRA in a work year; `withSSAges` picks Pat 62y6m inside her last work year), fork stakes, four questions (core and default, the earnings input, the stop month, survivors). **Maintainer (relayed 2026-10-23):** overlooked; "What did you end up doing?"; he trusts our judgement to fill the gap; only requirement: "the optimize full MILP is still affordable". Reply draft `fork-notes/issue-220-reply.md` (what the fork built, full-MILP cost measured, a PR on `dev` promised); revised the same day after the user's review: no option, the test is part of the model (fork: `withEarningsTest` retired); not posted |
| PR #196 (#193: `"convex"` + Summary label + SS-residual warning) | Opened by the user 2026-10-17 at the maintainer's request ("bundle both points above in a single PR and I'll test and push"). Head `fmateoc:ss-convex-pr` (`fb8b10e`: upstream `ss-convex` + `dev` `2b34633` merged + our commit), base `dev`. Upstream suite 2871 passed, 1 skipped. Text `fork-notes/pr-193-body.md`. If he pushes to the branch or merges it under new hashes, compare trees before the next sync. **Maintainer on the PR (2026-10-17, relayed):** "Are you sure you want to keep the ss-convex implementation? My tests were mixed. I am not sure this adds much. Your call." Measured the same day (section "PR #196: is 'convex' worth keeping?"); reply draft `fork-notes/pr-196-reply.md`, **revised after the user's review: drop "convex"** (as an opt-in it is a choice with no signal for when to make it; the warning misses a loop that settles short; dominated by "optimize" when the rest is exact); **PR reworked the same day**: branch `ss-convex-pr` force-pushed (lease on `fb8b10e`) to `e5a9ad5`, one commit on `dev` `7abed19` (the warning only, pointing to `withSSTaxability="optimize"`; `tests/plan/test_ss_residual_warning.py`; upstream suite 2869 passed, 1 skipped); new PR title/text (`pr-193-body.md`) **pasted and reply (`pr-196-reply.md`) posted by the user** (2026-10-17); awaiting the maintainer. The reply promises the local-search LTCG issue (`issue-ls-ltcg.md`) as a separate issue |
| #197 Local search pins the LTCG regime binaries in step (b) (`fork-notes/issue-ls-ltcg.md`) | **Filed by the user as #197** (2026-10-17). **Patch applied in the fork** the same day; household stand-ins rerun, no decision moves. Stock repro on `dev` `7abed19`: john+sally local-search preset 20,004 vs branch-and-bound 31,778; patch (step (b) leaves `zl` free) gives 31,778, never lower on the 18 examples, 1.53x the time. Section "Local search and the LTCG family" |
| #193 SS-taxability loop short of the exact model, stuck at the cap on LP ties (`fork-notes/issue-ss-loop.md`) | **Filed by the user 2026-10-16.** Stock repro `issue-ss-loop-repro.py` (output from `dev` `10b9f72`): loop $33.7k-48.6k below `withSSTaxability="optimize"` on the NY + mortgage couple, cap on ties, Summary error bar +-$358 on a plan $38k short, local search right. Questions: residual in the Summary; re-solve or recommend exact SS on a large SS residual. Maintainer (2026-10-16): how does it compare with `mipStrategy="local-search"`? Measured: local search on SS = branch-and-bound to the dollar; presets +$270-524; reply `issue-193-reply.md` **posted by the user**, with a correction (exact SS takes 14-21 s, not "a few seconds"). **Fixed upstream the same day** (`6b02671`, `83a580b`: `withSSTaxability="convex"`, opt-in), merged in `ae1fb9d`; then moved by the maintainer to branch `ss-convex` with `c22f46d` (cheaper cap probe), merged in `bb00250`; checked with the repro at `c22f46d` (equals `"optimize"` to the dollar, 0.8-1.2 s); confirmation `issue-193-reply-2.md` (at the branch tip) **posted by the user**; experiment branch `ss-binaries` (`abd39b4`, fewer SS binaries) measured, not merged: exact, 3.6-6.3x the nodes on the repro; the maintainer concluded it and deleted the branch, our comment draft not posted |
| #178 MIP money scaling (not ours) | Upstream `419a5ee`/`00d9bad`/`0ca30f4`: MILPs solved in hundreds of dollars (`mipScaleOrder`, default 2), tighter withdrawal-ordering big-M. Merged 2026-10-09. Effects on the fork: the NJ exclusion MILP closes its gap at the root (the 200-node cap test now runs at `mipScaleOrder=0`); local search on the NJ test couple 4x faster (43 -> 11 s) and +$154/yr; it also returned a plan that claimed the exclusion short of the statute (fixed in the fork, `b2ef9b2`, below). Not an upstream bug: their LP has no such exclusion |
| #173 Mortgage outlives the sale of its home | **Implemented upstream with another design** (`431aee0`): optional Debts `property` naming a residence/real estate in Fixed Assets; the loan is paid off in the year it is sold; a bad link is a configuration error. Maintainer: a typed year drifts from a `yod` counted from the plan end. Our payoff mechanics kept. Merged 2026-10-08, ours dropped |
| #174 `--solver-opt withSSTaxability=0.85` ignored | **Fixed upstream** (`fcf1b0b`), broader than our patch: all six mode options normalized or refused (`utils.normalize_mode_option`). Merged 2026-10-08, ours dropped; rechecked: jack+jill pins to 101,448 on both runs |
| Upstream workflow | Branch from and target `dev` (CONTRIBUTING) |

## Phase 0 — baseline case and scenarios

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
- [ ] Paper vs code drift, loop mode as a fixed point, taxable bond returns, plan year: one docs issue drafted, `fork-notes/issue-docs-loop-and-paper.md`. Upstream rewrote parts of `papers/owl.tex` in 2026.10.6-7: recheck before filing.

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

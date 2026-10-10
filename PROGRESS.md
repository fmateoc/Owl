# Owl fork — progress (as of 2026-10-10)

Fork-only file, like `CLAUDE.md`; not for upstream. Keep it current at the end of each work session.

Fork `fmateoc/Owl`, branch `claude/phase2-housing` (2026-10-07, from `main`): Phase 2 housing ledger and NJ property tax deduction, then the review fixes (same day): Debts `payoff` year, a crash before the first solve, Scenario 5 commands, stakes recorded on the objective, `--solver-opt` numeric text. 2026-10-08: merged upstream `dev` `156d812` (#173 loan linked to the property it finances, #174 mode options normalized, MCP partial bequest); our `payoff` column and `--solver-opt` validator dropped for theirs. Phase 2b the same day (after #175's answer): the Housing ledger replaced by a `"budget"` spending profile built from an HFP Budget sheet; HFP rate fix (a rate below 1 read as 100x). 2026-10-09: merged upstream `dev` `0ca30f4` (#176 our HFP rate report, fixed upstream with their design, ours dropped; #178 MIP money scaling); a fork fix the scaling exposed (NJ exclusion claimed short of the statute); essential budget lines (#175's cost-function point). Later the same day: merged upstream `dev` `d6970b2e` (`withSeniorBonus = "optimize"`; keep fork `zx` in `localsearch.FAMILIES` and their `zsb` in `ALWAYS_FREE`); Track B remainder plan rewritten against the shipped budget code. 2026-10-10: Track B steps 0-2 (smile anchored to its start with a fixed 30-year span; age clocks on Budget lines; JSON `budget_file`), then review fixes (below, and `fork-notes/track-b-spending-profile.md`, "Review fixes").
Plan details: `fork-notes/phase1-revised.md`. Scenario commands: `fork-notes/phase0/phase0-scenarios.md`.

## Upstream

Maintainer's responses as relayed by the user on 2026-10-06; issue states not re-checked on GitHub (this session's GitHub access covers the fork only).

| Item | State |
|---|---|
| #147, #149, #155 | Fixed upstream earlier; our copies dropped |
| #157 NY/NJ not indexed (+ NJ addendum) | Fixed upstream (`3c88ce1`, 2026.10.3); merged, theirs |
| #158 NY benefit recapture missing | Filed; no response (the issue said our code would not apply as is). **2026-10-06: rebuilt on stock `dev` `b4f1605`** without our loop registry or typed params, on upstream's `st_schedule`: `fork-notes/issue-ny-recapture.patch` (4 files, +369/−6, 23 tests; full upstream suite 2720 passed, 1 skipped; plans identical to the fork's to the dollar, also under local search and after the fork merged `b4f1605`). Follow-up comment **posted** by the user (`fork-notes/issue-ny-recapture-update.md`); no reply on #158 yet (the 2026-10-07 reply relayed answered the #171 points). 2026-10-07: patch refreshed on `5dd1623` (applies without offsets; upstream suite with it 2732 passed, 1 skipped; fork and patched stock still identical, by the same numbers moved $3-14/yr by upstream's own changes). Fork keeps its own version (locality surcharge on it, credits, Summary line) |
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
| #175 Housing ledger + NJ property tax deduction (design) | **Answered 2026-10-08**: no more state-tax plumbing upstream (NJ deduction stays in the fork); budgeting belongs outside the optimizer, as a module that builds the spending profile ("envelope") the optimizer consumes. Checked: rent inside a custom profile gives the same plan as our ledger under `maxBequest` to the dollar (`envelope_vs_ledger.py`). Plan `phase2b-budget-plan.md`; the user agreed to its 3 decisions and **posted** `issue-175-reply.md` (2026-10-08). **Implemented as Phase 2b** (below). Second answer (2026-10-08): budgeting as a **separate project, "Owl-budget"** (JSON, past five years for extrapolation, rent vs buy, health costs from the literature, HFP filling, Owl's look, files exchanged between two tabs); requirements first. Our input drafted: `owl-budget-requirements.md`, condensed reply `issue-175-reply-2.md`, **posted** by the user (#175 is now a GitHub Discussion). Third answer (2026-10-09): he owns Owl-budget for now; Owl's side of the contract goes in core ("hooks almost all there"); shape-only vs fixed lines open ("how the profile interacts with longevity"); JSON and Excel both, MCP on both sides for ladders of budgets; sources from a web search (BLS CE, HRS, EBRI, Vanguard, Fidelity); the budget must cover ~10 years before retirement; **cost function**: split core from discretionary spending. Answered first with the essential-lines prototype and measurements (`issue-175-reply-3-measured.md`, superseded: the maintainer keeps the discussion at the brainstorming level); restarted by the user as a conceptual reply, `issue-175-reply-3.md` (lines tied to the clock that causes them, calendar / age / household event, instead of Owl's plan-length-stretched smile; one series per household state as the time-series contract; priority tiers instead of utility weights, bequest as a possible tier; one risk tolerance per tier in stochastic spending; own history for the level, literature for change with age), **user to post** |
| #176 HFP rates below 1 read as 100x (0.5% real growth -> 50%) | Found 2026-10-08 while building the Budget sheet; repro on `dev` `156d812`: a home's end value $2.07M -> $509 billion, loan payment $15k -> $360k after save and reload. **Fixed upstream** (`ec6a5e0`, credited): only percent-formatted cells converted, each matched to its row by value and position. Merged 2026-10-09, ours dropped (their 6 tests cover our 4); the fork's Budget sheet keeps its rates as typed |
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

When upstream lands #158, merge `dev` and drop our duplicate, as with #149, #155, #157 and the 2026.10.5-7 fixes.

## Later phases (from requirements.md)

2 housing ledger (rent vs buy, property tax) · 3 itemized deductions · 4 healthcare cost model · 5 part-time work and SS earnings test · 6 scenario sweep and report · 7 NJ specifics (exclusion done; 65+ exemption done upstream in 2026.10.3; property tax deduction done with Phase 2; left: the $50 credit is out by decision)

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
- `debts.py` `get_mortgage_interest_array`: interest and average balance by calendar year for
  `type == "mortgage"` rows (payments minus the fall in balance; the payoff year pays principal
  only). `Plan.mortgage_interest_n` / `mortgage_balance_n`, zeros in `__init__`.
- `tax_federal.py`: `salt_cap(year, magi, yOBBBA)` (P.L. 119-21 sec. 70120 schedule, `inf` under a
  pre-TCJA reversion), `mortgage_limit`, `deductible_interest_share`, `itemize_terms` (the standard
  amount without the senior bonus), constants `MORTGAGE_LIMIT` / `MORTGAGE_LIMIT_LEGACY` /
  `MEDICAL_FLOOR` / `CHARITY_FLOOR` / `NONITEMIZER_CHARITY`.
- Tests: `tests/tax/test_itemized_data.py` (19: cap schedule and phase-down floor, hand
  amortization, payoff year, $750k proration and the $1M grandfather, amount terms with and
  without essentials, JSON/HFP round trip of the new types); §3.3 cases in `tests/assets/test_budget.py`.

Phase 5 now has a concrete case to serve: scenario 4b. The earnings test would let `withSSAges` optimize the working spouse too; a per-scenario PIA (or recomputing it from extra work years) would remove the manual PIA step. Medicare past 65 with employer coverage (delayed Part B) only matters if the worker goes past 65.

## Test status

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

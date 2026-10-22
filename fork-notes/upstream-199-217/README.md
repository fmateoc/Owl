# Upstream issues #199-#217 (filed 2026-10-20/21): validity and effect on the fork

Checked 2026-10-21 on `claude/phase5-step1` (upstream `dev` `bb52632` already merged; none of
these issues is fixed on `dev` or `main` yet: `git ls-remote upstream` shows `bb52632` on both,
and `1ab61bcb`, which #208 names as the #207 fix, is not on any upstream branch).
Seventeen are by `rationalpiper`, #208 by the maintainer. Maintainer on #199 (2026-10-21): he will
work through them, Pennsylvania rules first, then the other jurisdictions.

Issue texts were read through GitHub's web page (summarized by the fetch tool, not verbatim;
this session's GitHub API access covers the fork only).

**How each verdict was reached** (per the fork's evidence convention):
- *Code*: the cited code read on this commit (fork and `dev` are identical in every function
  named below unless the table says otherwise).
- *Repro*: the reporter's numbers reproduced here on the fork.
- *Source*: primary source fetched and read this session: POMS RS 00615.320, RS 00615.694,
  HI 01101.020 (secure.ssa.gov, saved copies not committed); 26 CFR 1.36B-1 and
  1.401(a)(9)-9 (eCFR versioner API, 2026-10-01); 2025 Form 1040 instructions (irs.gov
  `i1040gi.pdf`, pp. 33, 38, 110); Rev. Proc. 2026-26 (irs.gov `rp-26-26.pdf`).
- *Recalled*: not checked against a source this session.

## Verdicts

| # | Claim | Verdict | Checked |
|---|---|---|---|
| 199 | ACA family size drops to 1 when one spouse is on Medicare; should be the tax household (2 on a joint return) | **Valid** | Code (`acaCosts`/`acaVals`: `hh_size = min(nelig, 2)`); Source: 26 CFR 1.36B-1(d)(1)-(2) ("both spouses in the case of a joint return") |
| 200 | Coverage year Y uses the guideline of Y, should use Y-1; unpublished years grown from the plan start, not the guideline's year | **Valid** | Code (`fpl_year = calendar_year`, then `* gamma_n[n]`); Source: 1.36B-1(h) (guideline in effect on the first day of open enrollment *preceding* the year) |
| 201 | (a) 2027 table (Rev. Proc. 2026-26) missing; (b) exactly 400% FPL should qualify | **Valid**, both | Code (`ratio >= _ACA_BREAKPOINTS_2026[-1]`); Source: Rev. Proc. 2026-26 §3.01: 2.15 / 3.23-4.3 / 4.3-6.78 / 6.78-8.66 / 8.66-10.22 / 10.22%, top band "at least 300% but not more than 400%" |
| 202 | Non-expansion states priced as Medicaid up to 138% FPL | **Valid** (Owl's own comment says it is not modeled) | Code (`_ACA_MEDICAID_RATIO` comment); law recalled |
| 203 | PA: conversions exempt at any age; IRA distributions from 59½, not 60 | Code part valid (`[PA_*] exemption_age = 60`, one flag for both) | PA-40 instructions **not read** (PA is outside the investigation) |
| 204 | Proposal: per-year, data-driven ACA bands (non-expansion layout, CSR) | Design proposal, no defect claim of its own beyond #202 | Code (fixed 7 bands, `maca` in `[0, slcsp]`) |
| 205 | Standard deduction unused by ordinary income does not reduce taxable gains | **Valid** | Code (`_ltcg_tax_implied` stacks on `G_n + Q_n`; room rows on `G_n`); Repro: 21,632 vs 18,909 (diff 2,722) via `capitalGainTax`; Source: worksheet lines 1, 4, 5, 10 (line 1 = Form 1040 line 15, after the deduction) |
| 206 | Worksheet line 25 = min(stacked, regular tax) | **Valid**, ≤ $28.50 single / $57 joint per year (reporter's bound; not re-derived) | Source: worksheet line 25 "Enter the smaller of line 23 or line 24" |
| 207 | Born on January 1: 65 for the year before the 65th birthday | **Valid** | Code (`thisyear + n - yobs[i] >= 65` in `taxParams`, `seniorBonusSchedule`); Source: 1040 instructions p. 33 and p. 110 ("considered to reach age 65 on the day before the person's 65th birthday"; "born before January 2, 1961") |
| 208 | (maintainer) Medicare charged for the full 65th-birthday year; ACA not charged for the months before | **Valid** (filed by the maintainer) | Code (`mediVals`/`mediCosts` from `yobs + 65`, `n_aca_i` ends the year before); CMS/IRC citations recalled as consistent |
| 209 | Roth earnings withdrawn before 59½ neither taxed nor penalized | **Valid** as to code | Code (docstring of `_add_roth_maturation_constraints` states condition (b), no row enforces it); 408A ordering rules recalled |
| 210 | Widow(er)'s limit applied before the survivor's age reduction; law applies it after | **Valid** | Code (`max(deceased_monthly, 0.825 PIA) * _survivor_factor(...)`); Source: RS 00615.320 A.3 ("after adjustment for the family maximum and reduction for age") |
| 211 | Lower earner's own DRCs added on top of the spousal excess; should come out of it | **Valid** | Code (`_add_spousal_benefit` adds `spousal_amount * spousal_factor` whatever the own factor); Source: RS 00615.694 A-C (combined amount computed without DRCs; example $700 total, spouse payment $290) |
| 212 | Born on the 1st: claim at 70 gets a 37th credit; survivor reduction misses the one-month shift | **Valid** | Repro: `getSelfFactor(67, 70, True)` = 1.24667 (36 credits = 1.24); `_survivor_factor(67, 60)` = 0.715, `(67, 66y11m)` = 0.99661 (law 0.71839 / 1.0 for a survivor born on the 1st, 83 and 0 months early); statutory/CFR citations recalled |
| 213 | IRMAA in the survivor's first two years uses single thresholds on joint lookback MAGI | **Valid** | Repro: `mediCosts` = [4869.6, 4869.6, 4869.6, 7027.2, 7027.2, 3583.2], as filed; CFR citations recalled |
| 214 | 2026 Part D IRMAA tiers 2-4 are $37.50 / $60.40 / $83.30, not $36.30 / $58.10 / $79.90 | **Valid** | Code (`partD_irmaa_monthly` increments 14.50, 21.80 x3, 11.10); Source: HI 01101.020 B (2026 tables) |
| 215 | `withMedicare="optimize"` infeasible when a previous MAGI exceeds the year's income ceiling | Plausible (mechanism read in the issue; not reproduced here) | Not run |
| 216 | MAGI of exactly $500k / $750k is the top tier ("greater than or equal to") | **Valid** | Repro: 649.20/mo vs 689.90; Source: HI 01101.020 ("Greater than or equal to $500,000"; lower tiers "More than … less than or equal to"). The issue's "$48.40/month" is Part B 40.70 + Part D 7.70 (CMS values); its repro excludes Part D, hence 40.70 — consistent, not an error |
| 217 | Four RMD joint-table cells copy Pub. 590-B misprints | **Valid**: exactly those four cells differ from 26 CFR 1.401(a)(9)-9(d) | Source: the whole regulation table parsed (`cfr_joint_table.py`) and compared with Owl's 5,611 cells; the only other mismatches are the CFR's "120+" row/column, which the parser skips |

No claim was found wrong. Not checked: #203's PA law, #215's run, the recalled citations noted above.

## Status after upstream `dev` `37afa2a` (merged 2026-10-22)

Fixed upstream and merged into the fork (commit subjects name the issue): #199, #200, #201,
#202, #203, #207, #208, #209, #210, #211, #212, #213, #214, #215, #216, #217, and #218 (a
survivor's home sale more than 2 years after the death gets the \$250,000 exclusion; filed
after this note). **Not fixed**: #204 (proposal), #205 and #206 (LTCG worksheet). The
"until upstream fixes it" checks in item 1 above (ACA-year MAGI against 4 x the prior year's
guideline) are no longer needed. What the merge changed in fork code: PROGRESS.md, "Upstream
`dev` `37afa2a` merged".

## Effect on the household plan

Household facts used (template `fork-notes/phase0/Case_us.template.toml`): NY couple, both born
1964 (A "early 1964", B "Dec 1964"), ACA from 2027 (`aca_start_year`), Medicare in Owl from 2029
for both, claiming ages are the Phase 5 question. **Both placeholder birth dates are on the 1st**
(1964-01-01, 1964-12-01), which is exactly the case #207, #208 and #212 are about; with the real
dates some of the effects below vanish or change. Real PIAs are not in the repo, so #211 is
conditional.

Ranked by what they can do to a decision:

1. **#200 + #201 — the 400% FPL cliff in the ACA years (2027-2028).** Owl's line is one year of
   the plan's inflation too high (2027: law 4 x \$21,640 = \$86,560; Owl \$86,560 x `gamma_n[1]`),
   and 2027 contributions are 10.22% at the top, not 9.96% (Rev. Proc. 2026-26). Rev. Proc. 2026-26
   also confirms the cliff exists in 2027. An optimizer that parks MAGI just under Owl's line
   lands up to ~2-3% above the real one, where the whole credit is lost (cost = SLCSP instead of
   10.22% of MAGI). Until upstream fixes it: in any ACA-year plan, check MAGI against
   4 x the prior year's guideline, unindexed, and treat a margin under ~3% as over the cliff.
2. **#208 (+ #199) — 2029, the year both turn 65.** With B born in December, B is on the
   marketplace for 11 months of 2029 (10 if born on the 1st); Owl charges B 12 months of
   Medicare and no ACA, and does not see 2029 MAGI as an ACA-year MAGI at all (it lets 2029 carry
   income it would hold under the cliff in 2027-28). Once #208 is fixed, #199 matters too: in
   that year B is a 1-person enrollee in a 2-person tax household. Size not measured (needs a
   real SLCSP and the real birth months). Side note for the fork, recalled and not checked: NY
   uses pure community rating, so `couple_to_individual_fraction` (CMS age curve) should be
   exactly 1/2 in NY; it only matters in a year with one enrollee, which #208 creates.
3. **#211 — spousal benefit with own DRCs.** If the lower earner's PIA is below half the
   other's, Owl pays own-with-DRCs plus the full excess, so it overvalues delaying the lower
   earner past FRA: wrong direction for the claiming-age advice Phase 5 is about. No effect if
   the PIA ratio is 0.5 or more. **Fork code**: the earnings-test monthly builder
   (`socialsecurity.py`, own/spousal arrays before "Excess per person") duplicates the same rule,
   so an upstream fix in `_add_spousal_benefit` must be mirrored there.
4. **#207 / #212 — born on the 1st.** Only if a real birth date is on the 1st: A born
   January 1 gets the 65+ deductions in 2028, not 2029 (+\$1,650 additional standard deduction
   per person, Owl's 2026 MFJ amount `extra65Deduction`, + up to \$6,000 senior deduction); a claim at
   exactly 70 is overstated by one credit (0.67% of PIA for life). The fork's ARF helpers call
   `getSelfFactor`, so they inherit the #212 fix automatically.
5. **#213 — IRMAA after the first death.** Overcharge for two years after the first death,
   only when the couple's MAGI sits between the single and joint thresholds. Late, discounted;
   the optimizer may shift income around the death year to avoid a phantom charge.
6. **#214 — Part D tiers 2-4.** Certain but small: \$14.40 / \$27.60 / \$40.80 per enrollee per
   year in those tiers. Take upstream's fix.
7. **#205 / #206.** Measured: \$0 on all 18 examples for #205 (`ltcg_unused.py`, output
   `ltcg_unused_2026-10-21.txt`; cameron has 25 years with unused deduction and gains, all inside
   the 0% band). With a tax-deferred balance, conversions fill the deduction. This measures Owl's
   own plans, not plans optimized under the corrected rule. #206 ≤ \$57/yr.
8. **No effect**: #202/#204 (NY is an expansion state), #203 (PA), #209 (both past 59½ since
   2023-24), #210 (only deaths before the survivor's FRA, 2031; life expectancy 92), #215
   (previous MAGI would have to exceed twice the portfolio plus fixed income), #216 (\$500k MAGI),
   #217 (only spouses more than 10 years apart).

**Not raised in any issue, found while checking #204:** NY's Essential Plan. Since 2026-07-01 it
covers incomes up to 200% FPL (\$43,280 for two in 2026) again under the Basic Health Program,
down from 250% under the 1332 waiver (NY State of Health notice and NY DOH press release
2026-03-23, read through a web search summary, not the pages themselves; premium not checked).
Owl prices 138-200% FPL in NY as marketplace coverage (about 3.5-6.6% of MAGI in 2026, Owl's table). Relevant only
if a plan holds ACA-year MAGI under 200% FPL; #204's per-year bands would be the place to carry it.

## Effect on the fork's code (merge surfaces when upstream fixes land)

- `socialsecurity.py`: #210 lands in `compute_survivor_stream`, where the fork has its
  `deceased_factor` parameter (conflict expected); #211 needs mirroring in the earnings-test
  builder (above); #212 changes `getSelfFactor` / `_survivor_factor`, used by the fork's ARF code
  (no conflict expected; the earnings-test tests that pin factors for born-on-the-1st people
  may move).
- `tax_federal.py`: the fork's hunks are the itemizing constants and the functions after
  `seniorBonusSchedule`; #199-#201, #208, #213, #214, #216 touch functions the fork has not
  changed. The fork's itemized medical claims read Medicare and ACA through
  `_medical_premium_terms` / `_values` / `_lo` (CLAUDE.md), so #208's proration flows into them;
  recheck `_medical_premium_lp_n` if #208 changes the optimize-mode columns rather than only
  `Cbar`.
- `plan.py`: #205 (new `eq_n` column, LTCG partition rows), #209 (Roth basis rows), #215, #216
  touch upstream rows the fork has not changed; #205's column must also enter the fork's
  MAGI-based rows (NY IT-196, STAR income, SALT phase-down) if upstream adds it to MAGI.
- Data: #217 (RMD table) and #214 are data-only.

## Nothing filed

No comments drafted: the issues are not ours, every claim checked holds, and the maintainer has
said he will work through them. The fork waits for upstream's fixes and takes theirs on the next
sync. Before decision runs: enter the real birth dates (on or off the 1st changes #207, #208,
#212) and check the PIA ratio (#211).

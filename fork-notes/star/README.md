# STAR / Stay NJ data check (2026-10-17)

Purpose: settle the open data questions left by `phase3-plan.md` §3.4 and PROGRESS.md "Step 2
review" before deciding whether to model senior property-tax relief (NY STAR; NJ Stay NJ, ANCHOR,
Senior Freeze) as rules. No code changed.

Marking: **[V]** = read today on the primary source named (fetched 2026-10-17); **[R]** = recalled
or inferred, not checked; **[C]** = computed here from [V] figures.

## Sources read

| Source | URL | Page date |
|---|---|---|
| STAR eligibility | `https://www.tax.ny.gov/pit/property/star/eligibility.htm` | updated 2026-06-03 |
| Types of STAR | `https://www.tax.ny.gov/pit/property/star/types.htm` | 2026-06-02 |
| STAR FAQ | `https://www.tax.ny.gov/star/faqs.htm` | 2026-08-28 |
| STAR credit vs exemption amounts (index) | `https://www.tax.ny.gov/pit/property/star/comparison/` | 2024-12-31 |
| 2025 final STAR amounts, Westchester | `.../star/comparison/55-westchester.htm` | (not shown) |
| 2025 final STAR amounts, NYC | `.../star/comparison/65-newyork.htm` | 2026-07-08 |
| Reporting the STAR credit | `https://www.tax.ny.gov/pit/property/report_property_tax_credits.htm` | 2026-06-30 |
| Stay NJ | `https://www.nj.gov/treasury/taxation/staynj/index.shtml` | 2026-08-20 |
| ANCHOR | `https://www.nj.gov/treasury/taxation/anchor/index.shtml` | 2026-09-16 |
| ANCHOR amounts | `https://www.nj.gov/treasury/taxation/anchor/calculated.shtml` | 2026-07-16 |
| Senior Freeze amounts | `https://www.nj.gov/treasury/taxation/ptr/hoamount.shtml` | 2026-07-16 |
| Property tax relief FAQ | `https://www.nj.gov/treasury/taxation/propertytaxrelieffaq.shtml` | 2026-09-16 |
| PAS-1 2025 form and instructions | `https://www.nj.gov/treasury/taxation/pdf/25-pas1.pdf`, `25-pas1in.pdf` | issued Feb 2026 |
| Property tax relief handout | `https://www.nj.gov/treasury/taxation/pdf/help/resources-property-relief-info-handout.pdf` | PDF 2026-02-13 |
| Stay NJ Task Force report (c. 75) | `https://www.nj.gov/treasury/staynj/documents/StayNJFinalTaskForceReport-c75.pdf` | 2024-05-30 |
| Income tax treatment of NJ benefits | `https://www.nj.gov/treasury/taxation/treatment03.shtml` | 2025-06-02 |
| NJ-1040 instructions 2025 | `https://www.nj.gov/treasury/taxation/pdf/current/1040i.pdf` | PDF 2025-10-21 |

Not reachable: `staynj/calculation.shtml` (404 today; the Senior Freeze page still links to it as
"Stay NJ Calculation", and its card on the Stay NJ page is commented out in the HTML).
`pub.njleg.gov` was blocked at first (proxy 403); allowed later the same day, see "Statutes" below.

## Statutes (read 2026-10-17, second pass)

| Source | URL |
|---|---|
| NY Tax Law sec. 606(eee) (STAR credit) | `https://www.nysenate.gov/legislation/laws/TAX/606` |
| NY RPTL sec. 425 (STAR exemption; income standard) | `https://www.nysenate.gov/legislation/laws/RPT/425` |
| NY RPTL sec. 1306-a (tax savings; 2% cap) | `https://www.nysenate.gov/legislation/laws/RPT/1306-A` |
| NJ P.L.2023, c.75 (Stay NJ) | `https://pub.njleg.gov/Bills/2022/PL23/75_.HTM` |
| IRS Pub. 530 (2025) | `https://www.irs.gov/publications/p530` |

- **STAR credit** [V, 606(eee)]: "qualified taxpayer" = NY resident who owned and lived in the
  primary residence on July 1 of the taxable year, not on a STAR exemption. "Affiliated income" =
  federal AGI of the resident owners and spouses "reduced by distributions, to the extent included
  in federal adjusted gross income, received from an individual retirement account and an
  individual retirement annuity" (so 401(k)/403(b) distributions stay in). Basic: income at most
  $500,000, a fixed amount. Enhanced: an owner 65+ on December 31; a surviving spouse 62+ keeps a
  credit "once allowed". Each credit is "the lesser of" the district portion's tax savings and the
  qualifying taxes (school taxes; in the five big-city school districts, city and school taxes
  combined). It is a credit against the NY personal income tax, the excess refunded: **a
  refundable state income tax credit**, paid in advance.
- **Survivor** [V, tax.ny.gov eligibility page]: the survivor keeps Enhanced if 62 "by December 31
  in the year that their age-eligible spouse passed away"; otherwise Enhanced from their own 65.
- **Growth** [V, RPTL 1306-a(2)(a)(i)]: from 2019-20 the credit's tax savings for a portion "shall
  not exceed" 102% of the prior year's, rounded to the dollar; the exemption's shall not exceed
  the prior year's.
- **Income standard** [V, RPTL 425(4)(b)(i)(C)-(E)]: each year the previous standard increased by
  the Social Security cost-of-living adjustment; never decreased; rounded to a multiple of $50
  (direction not read). Income year advanced one per year (two years before the benefit year).
- **Federal** [V, Pub. 530]: "If you receive a refund or rebate of real estate taxes this year
  for amounts you paid this year, you must reduce your real estate tax deduction by the amount
  refunded." Whether the IRS reads the STAR credit as such a rebate was not found; as a refundable
  state income tax credit it reduces state income tax paid instead. Either reading lowers the
  SALT total by the credit in the year received, which is what the model does [C].
- **Stay NJ** [V, c.75 sec. 3-4]: credit = 50% of the property tax paid on the principal residence
  in the prior tax year; maximum $6,500 in 2026, then increased by the annual percentage increase
  in the average residential property tax bill (DCA); an applicant gets "the greater of" the Stay
  NJ credit or ANCHOR plus Senior Freeze; "Income" as defined in P.L.1975, c.194 (the PAAD
  definition; not read). A surviving spouse who stays in the home keeps it.

## STAR as modeled (2026-10-17)

`src/owlplanner/star.py`, data `src/owlplanner/data/property_tax_relief.toml`, tests
`tests/tax/test_star.py`.

- Input: `basic_info.school_district` (and a move's `school_district`), canonical
  "Municipality / School district" or the district alone where unique. The credit applies where
  the year's residence has a district and the budget a `property tax` line (an owner).
- Amounts: 2025 final credits per row, x 1.02 per year after 2025, at most the property tax paid.
- Income: AGI less tax-deferred withdrawals and conversions (Owl's tax-deferred account is taken
  to be an IRA), two years back; `previousSTARIncomes` (default `previousMAGIs`) for the two years
  before the plan.
- The credit is subtracted in `Plan._state_tax_terms` (outside the Yonkers surcharge), so the
  cash flow and the SALT row follow; IT-196 line 6 subtracts the lagged credit `STAR_n` from the
  real estate taxes (`_item_terms()["st_pt"]`).
- `withSTAR = "loop"` (default; SC parameter `STAR_n`, residual family "STAR"), `"optimize"`
  (binary `zst_n` per Enhanced year: income_(n-2) + M zst_n <= limit_n - $2 + M; a local-search
  family), `"none"`. The Basic limit is a loop test in both modes.


## NY STAR

- **Two forms** [V]: the STAR exemption (lower school bill) only for homes that had it in 2015;
  everyone else gets the STAR credit, a check or direct deposit. So for any purchase in the plan
  the bill shown is the bill paid and the credit is a separate inflow.
- **Basic STAR** [V]: no age limit; income limit $500,000 for the credit ($250,000 for the
  exemption); "based on the first $30,000 of the full value of a home".
- **Enhanced STAR** [V]: one resident owner 65+ by Dec 31 of the benefit year; income limit
  $110,750 for 2026 benefits, $113,550 for 2027 (+2.5%); "based on the first $88,500 of the full
  value" (2026-27). A surviving spouse keeps it if 62+ in the year the age-eligible spouse died,
  otherwise Basic until 65.
- **Income** [V]: federal AGI minus the taxable amount of IRA distributions (1040 line 11 minus
  line 4b), from the tax year two years before the benefit year (2026 benefit: 2024 return);
  owners and owners' spouses living there. Consequences [R/C]: IRA withdrawals and IRA-to-Roth
  conversions (line 4b, recalled) do not count; 401(k)/403(b) distributions (line 5b, pensions)
  and the taxable part of SS do. Rolling a 401(k) into an IRA before drawing it keeps those
  distributions out of STAR income.
- **Five big cities** [V]: in New York, Buffalo, Rochester, Yonkers and Syracuse the exemption is
  applied partly to city taxes and partly to school taxes.
- **Amounts** [V]: published per municipality and school district, after school tax rates are
  set (NYC in August, most counties in October), on the comparison pages above. 2025 final
  credits, saved in `star_2025_westchester_nyc.csv` (80 rows):

  | Place | Enhanced credit | Basic credit |
  |---|---|---|
  | Yonkers (City of Yonkers, Yonkers SD) | $2,455.00 | $879.00 |
  | NYC, tax class 1 (1-3 family homes) [class meaning R] | $730.00 | $275.00 |
  | NYC, class 2 / 4 | $743.00 / $738.00 | $274.00 / $278.00 |
  | Rest of Westchester, 72 residential rows [C] | $1,753-4,517, median $3,699 | $611-1,665, median $1,330 |

  The figures can exceed what a household got: a credit cannot exceed the school taxes paid, and
  a rate above the district's expected rate is paid the next year [V].
- **Growth** [V]: "by law, the STAR credit can increase by as much as 2% each year, but the
  value of the STAR exemption savings cannot increase". Either can fall. So in today's dollars
  the credit shrinks unless inflation is under 2% [C].
- **Taxes** [V]: on the NY return, itemizers reduce real estate taxes paid by the STAR credit
  received (IT-196); otherwise nothing to report. Federal treatment: not on the pages read [R:
  a reduction of the property tax deduction].

Not checked: the senior citizens exemption (RPTL 467; local option, low income limits [R]),
NYC's SCHE, and NYC's school tax credit on IT-201 (income-tax side; `taxes_local.toml` says
"not modeled").

## NJ: Stay NJ, ANCHOR, Senior Freeze (one application, PAS-1)

- **Stay NJ eligibility** [V]: 65+ during the tax year; owned and lived in an NJ home the full
  12 months; home subject to property tax or PILOT; renters and mobile homes excluded. The PAS-1
  instructions and the handout still state the statutory limit, income under $500,000; the FY2027
  Appropriations Act (signed 2026-06-30) pays only incomes up to $200,000.
- **Stay NJ amount** [V, handout and Task Force recommendation 7; the 404'd page not read]:
  50% of the property tax bill, at most $6,500, minus ANCHOR and Senior Freeze paid. The FY2027
  tiers for tax year 2025 (paid Feb/May 2027) cap the maximum: **$6,500 to $100,000, $5,000 to
  $150,000, $4,000 to $200,000, $0 above**, "assuming no changes ... in the FY2028 budget". The
  2026 payments (tax year 2024) were cut mid-year. Total relief from all programs is capped at the
  property tax paid [V].
- **ANCHOR (homeowners, tax year 2025)** [V]: income = **NJ-1040 line 29** (after the retirement
  exclusion); $1,500 up to $150,000, $1,000 to $250,000, nothing above. Renters: $450, $700 at
  65+, income up to $150,000. The homeowner table shows no senior add-on this year. Age does not
  matter for homeowners.
- **Senior Freeze** [V]: reimbursement = this year's tax minus the "base year" tax; 65+ (or SSDI);
  owned and lived there since Dec 31 three years before (2022 for tax year 2025); income limits
  $168,268 (2024) and $172,475 (2025), both years.
- **Stay NJ / Senior Freeze income** [V]: PAS-1 line 18f = NJ-1040 **line 27** (total income,
  before the line 28a-28c exclusion; it includes IRA withdrawals, pensions and IRA-to-Roth
  conversions, line 20a) + tax-exempt interest (line 16b) + earnings in qualified Roth
  distributions + disability pension + **gross Social Security** (SSA-1099 box 5, Part B
  premiums included); same tax year as the benefit (paid the year after next). The Task Force
  recommended exactly this definition ("excluded pension and retirement income ... gross Social
  Security"); ANCHOR keeps line 29.
- **Taxes** [V]: the three benefits are not NJ income; federally they are "recoveries" (IRS Pub.
  525, not read).

## What this means for the model

All [C] from the figures above, at 2025 amounts.

1. **The §3.4 reading overstated the NY-vs-NJ gap.** "Stay NJ up to $4,000-6,500 a year" is the
   NJ total, ANCHOR included. NJ homeowner 65+ with a bill of at least twice the tier maximum
   ($13,000 / $10,000 / $8,000): total relief $6,500 / $5,000 / $4,000 by PAS-1 income tier,
   versus a Yonkers owner's Enhanced STAR $2,455 (if STAR income <= $110,750) or Basic $879.
   So NJ minus Yonkers at 65+: about $4,045 / $2,545 / $1,545 a year with Enhanced STAR,
   $5,621 / $4,121 / $3,121 with Basic; above $200,000 of PAS-1 income, ANCHOR only:
   $1,500 - $879 = $621 (or $1,000 - $879 = $121). Under 65: ANCHOR $1,500 vs Basic $879, $621.
   Against the rest of Westchester (Enhanced median $3,699) the 65+ gaps shrink by about $1,250.
   Still larger than the measured NY-vs-NJ income-tax differences ($430-1,006/yr), and still the
   least certain number (annual appropriations; the statute's $500k / $6,500 vs the budget's
   $200k tiers).
2. **The income tests are three different quantities**, none of them Owl's state AGI:
   - STAR: federal AGI minus taxable IRA distributions, two years back. Conversions and IRA
     withdrawals are free with respect to it; 401(k) withdrawals and taxable SS are not.
   - Stay NJ (and Senior Freeze): NJ income before the exclusion plus gross SS (+ tax-exempt
     interest, Roth earnings). Conversions count in full, and so does all of SS. Owl's
     `st_agi_n` (state income before the exclusion, conversions included) plus gross SS is close;
     Roth qualified-distribution earnings are not tracked by Owl [R].
   - ANCHOR: NJ line 29, i.e. after the exclusion: `st_agi_n - st_rx_n`.
3. **Cliffs.** Stay NJ drops $1,500 at $100,000, $1,000 at $150,000, $4,000 at $200,000 (when the
   bill reaches the tier caps); Enhanced STAR drops to Basic above $110,750 (Yonkers: -$1,576).
   They are cliffs like the NJ exclusion's tiers, so per §3.4 they belong in the MILP (tier
   binaries in the `zx` form), not in the loop. With gross SS in Stay NJ income, a couple with
   two SS benefits starts well into the tiers before any withdrawal; whether the household sits
   near $100k/$150k/$200k needs its real numbers (`otherFiles/`).
4. **Data shape.** STAR: per school district, Basic and Enhanced credit, growth at most 2%/yr
   nominal (credit, not the bill), income limit indexed (2.5% this year; the index itself not
   checked), benefit year Y uses income Y-2. NJ: tier table and $6,500 cap from the budget,
   50% of the bill, ANCHOR by line 29, benefit for tax year Y paid in Y+2 (keep it in year Y,
   as §3.4 step 9 already says). Effect on the property tax claimed: NY IT-196 is reduced by the
   STAR credit [V]; federal [R]. NJ line 41 (Worksheet H, 2025 NJ-1040 instructions) starts from
   property taxes paid (line 40a), and "most Senior Freeze applicants must use their base year
   amount" there [V]; I did not find a reduction of line 40a for ANCHOR or Stay NJ (searched the
   1040i text for "reduc", "ANCHOR", "Stay NJ"). For the fork's `st_pt` this means: no change for
   ANCHOR / Stay NJ, and a Senior Freeze recipient's deduction is capped at the base-year tax.
5. **Recommendation** (before STAR was modeled the same day; STAR is now a rule, above). Keep step 9's order: first a scenario lever (the household's PAS-1 and
   STAR income from a solved plan, then the benefit as an inflow in the budget), and code tiers
   only if a solved plan sits near a cliff. STAR as a rule is simpler than Stay NJ (two
   amounts per district, one cliff, income two years back that conversions do not touch) and is
   the one needed for every NY owner scenario, so it comes first if anything is coded.

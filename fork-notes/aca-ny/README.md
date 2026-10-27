# NY marketplace benchmark (SLCSP) for Yonkers, Westchester and NYC (2026-10-27)

The user's question: the benchmark silver premium (Owl's `slcsp_annual`) for zip codes 10701
(Yonkers), 10603 (White Plains area, Westchester) and 11354 (Flushing, Queens), standing for the
household's three places.

## Sources and access

- NY State of Health (`nystateofhealth.ny.gov`): its anonymous plan search redirects to a cookie
  check (`/individual/checkCookie`); scripted access with a cookie jar was refused by this
  session's auto-mode classifier, so nothing was taken from the shopping tool.
  `info.nystateofhealth.ny.gov` answers curl with a CloudFront "403 Request blocked".
- NY DFS: press release `pr20260904` (2027 rates, 2026-09-04) and the prior-approval pages on
  `myportal.dfs.ny.gov`. The portal's login page is for submitting; direct document links work
  without an account:
  - summary: `/fr/web/prior-approval/ind-and-sg-medical/summary-of-2027-requested-rate-actions`
  - per filing: `/fr/web/prior-approval/ind-and-sg-medical/additional-information-2027`
    (Notice, Narrative, Exhibit 14, Rate Application, Proposed and **Approved Rates** templates)
  - `/fr/web/prior-approval/2027-final-exhibits` (zip of Exhibits 13c, 14, 16, 18, 23 per filing)
- 26 CFR 1.36B-3 from the eCFR versioner API (`/api/versioner/v1/full/2026-10-01/title-26.xml?section=1.36B-3`,
  plain curl, no User-Agent needed this time).

`fetch.sh <new dir>` downloads every file used; `rates.py`, `attrs.py`, `slcsp.py`,
`rates2026.py` rebuild the tables (run them from that directory; they need pandas, xlrd,
openpyxl). Output of the run from a fresh download: `slcsp_2026-10-27.txt`;
`silver_region4_2027.csv` is the ranked list (gold: section "Gold plans"). Downloads are not committed (about 200 MB unpacked).

## What the filings say (verified in the files)

- **2027 average:** individual market requested +20.6%, approved +6.0% (DFS summary table,
  updated 09/04/2026; per insurer from -3.1% Anthem HP to +12.2% Excellus/Highmark).
- **Community rating:** every rate template is "Family-Tier Rates" for adults (the age-based
  sheets hold child-only plans). Couple / single = 2.000 on all 1,173 family-tier rows (min
  1.99998, max 2.00003). Oscar's application: "All rates are community rated with no age or
  lifestyle rating"; tier factors Single 1, Single & Spouse 2. Fidelis: "New York is a
  community-rated state. There is no age curve calibration."
- **Rating Region 4 ("New York City")** = Bronx, Kings, New York, Queens, Richmond, Rockland,
  Westchester (Anthem HP, HIP, MVP, UHC and Fidelis county tables agree). Yonkers, White Plains
  and Flushing are all in Region 4. Zip to county (10701 and 10603 Westchester, 11354 Queens)
  is recalled, not checked against a source.
- **Rates and service areas go by county**, so 10701 and 10603 get the same answer.
- **Who sells in Region 4** (approved rates filed for Rating Area 4, then service area from the
  rate application):

  | Carrier (filing) | Exchange | Westchester | Queens | Evidence |
  |---|---|---|---|---|
  | Fidelis (NYQHC) | on + off | yes | yes | region list only (statewide factors) |
  | Anthem HP | on + off | yes | yes | area-factor table, region list |
  | Healthfirst PHSP | on + off | yes | yes | "Region 4 ... service area includes Bronx, Kings, New York, Queens, Richmond, and Westchester" |
  | MetroPlus | on + off | **no** | yes | "Counties in Rating Area": the five boroughs |
  | MVP HP | on + off | yes | **no** | county table: Rockland, Westchester "Yes"; boroughs "No" |
  | Oscar | on + off | yes | yes | "Bronx, Kings, New York, Queens, Richmond, Westchester" |
  | HIP (Emblem) | on + off | yes | yes | area factors "All Plans" for all Region 4 counties |
  | UHC of NY | on + off | yes | yes | area factor 1.000 (not "n/a") |
  | Aetna Life, UHIC | **off only** | - | - | Exhibit 23: every plan "Off"; cannot be the benchmark |

  For Fidelis, Anthem and HIP the evidence is a rate table naming the counties, not an explicit
  service-area statement; a plan-level network limited to some counties would not show there.

## 2027 result (approved rates, monthly)

| Rank (both counties) | Plan | Single | Couple |
|---|---|---|---|
| 1 | Fidelis `25303NY0020001` (standard silver, dependents to 26) | 941.66 | 1,883.32 |
| 2 | Fidelis `25303NY0140001` (the same plan with dependents to 29: 941.66 x 1.050) | 988.67 | 1,977.34 |
| 3 | Anthem HP `41046NY0010004` (standard silver, to 26; "benefits in addition to EHB": Yes) | 1,053.68 | 2,107.36 |
| 4 (Queens only) | MetroPlus `11177NY0040001` | 1,064.37 | 2,128.74 |
| 4 (Westchester) / 5 (Queens) | Healthfirst `91237NY0020007` | 1,084.36 | 2,168.72 |

The same two plans are lowest in both counties, so **Westchester and Queens have the same
benchmark** whichever reading below holds; MetroPlus (Queens only) and MVP (Westchester only)
rank too low to matter.

### Which plans count

26 CFR 1.36B-3 (read from eCFR): (f)(2) the family benchmark is "the second lowest-cost silver
plan that would cover the members of the taxpayer's coverage family"; (f)(6) a plan "not open to
enrollment by a taxpayer" is disregarded; (j)(1) premium allocable to benefits beyond the EHB,
including benefits "a State requires", is excluded **before** the benchmark is determined.
None of these says whether an age-29 twin is a separate plan. Two readings:

| Reading | 2027 benchmark | Couple per year |
|---|---|---|
| `dep26`: age-29 twins are not separate plans for a couple (not offered to a household without young-adult dependents, or a state-required add-on under (j)) | Anthem `41046NY0010004`, 1,053.68 | **25,288** |
| `all`: every exchange plan ID counts | Fidelis twin `25303NY0140001`, 988.67 | 23,728 |

Not resolved from primary sources. The NYSOH shopping tool (does it show age-29 plans to a
couple?) or any NY 1095-A (column B) would settle it. Under `dep26`, Anthem's own (j) share
(it adds benefits beyond EHB) would lower its benchmark premium by an amount not found in the
files read; under `all`, (j) would take the 5% age-29 load off the twin, leaving it at about
941.66. So the defensible range is about 941.66-1,053.68 single per month.

### 2026 and the jump to 2027

Exhibit 23 reports each plan's in-force 2026 Region 4 rate. Fidelis then sold four more silver
plans (`063`, `064`, `046`, `050`) that have no 2027 rate (0 in Exhibit 23's 2027 column and
absent from the approved-rates template). 2026 benchmark: 868.20 (`dep26`: `25303NY0020001`) or
846.86 (`all`: `064`, an age-29 twin), couple 20,837 or 20,325 per year. The 2027 benchmark is
**+21.4%** (`dep26`) or +16.7% (`all`) over 2026, against the market's +6.0% average: the
2026 benchmark plan itself rose 8.46% (868.20 -> 941.66), the rest is Fidelis dropping its cheapest
silver plans.

## Gold plans (added 2026-10-27, the user's question)

`metal.py Gold` and `rates2026.py fx/unz Gold`; output `gold_2026-10-27.txt`, ranked list
`gold_region4_2027.csv` (on and off exchange; Aetna Life and UHIC included: their applications
list Queens and Westchester in Region 4).

**Standard design 2027** (NY standardizes it; same table in Fidelis's and HIP's applications,
HIP labels the amounts "(single)"):

| | Platinum | Gold | Silver | Bronze |
|---|---|---|---|---|
| Deductible | $0 | $1,200 | $3,750 | $5,025 |
| Out-of-pocket maximum | $4,000 | $12,000 | $12,000 | $12,000 |
| PCP / specialist | $15 / $35 | $25 / $40 | $30 / $65 | $50 / $75 |
| Inpatient, per admission | $500 | $1,000 | $1,500 | $1,500 |
| AV (HIP) | 91.88% | 81.99% | 71.76% | 64.98% |

Gold and silver share the $12,000 out-of-pocket maximum: gold buys a lower deductible and
copays, not a lower worst case. Non-standard plans (`std` = Non-Standard) have their own designs,
not read here.

**Lowest gold premiums, 2027, monthly, dependents to 26** (approved rates):

| Plan | Exchange | Single | Couple | Westchester | Queens |
|---|---|---|---|---|---|
| Fidelis `25303NY0030001` (standard) | on | 1,219.05 | 2,438.10 | 1 | 1 |
| MetroPlus `11177NY0080001` (standard) | on | 1,242.19 | 2,484.38 | - | 2 |
| Fidelis `25303NY0550001` (non-standard) | on | 1,246.01 | 2,492.02 | 2 | 3 |
| Healthfirst `91237NY0020011` (standard) | on | 1,309.89 | 2,619.78 | 3 | 5 |
| Anthem HP `41046NY0010006` (standard) | on | 1,316.96 | 2,633.92 | 4 | 6 |

The most expensive gold (dependents to 26) in Region 4 is UHIC's off-exchange `54297NY0060002` at
1,998.32 single; Oscar's standard gold is 1,610.76, HIP's 1,762.33, UHC's 1,910.72.

**Against silver (couple, per year):** the cheapest gold costs 29,257 in 2027, **+3,969** over
the `dep26` benchmark (25,288) and +6,657 over the cheapest silver (22,600). In 2026 (Exhibit 23
in-force rates: Fidelis `25303NY0030001` 1,123.85 single, the lowest exchange gold in the Region 4 filings) it was
26,972, +6,136 over that year's benchmark (20,837): the gap narrows in 2027 because the
benchmark jumps (silver discontinuations) while this gold plan rises 8.47%.

## For Owl

- `aca_settings.slcsp_annual` is today's dollars, household benchmark, in $k. With the plan starting
  in 2026: **20.84** (in the template since 2026-10-27, the user's call) (`dep26`, 2026 rates) or 20.32 (`all`). Owl grows it with `_medical_n(gamma_n)` (inflation, or
  `setMedicalInflation`'s rate; `plan.py`, the `acaVals` call), so the 2027 jump above inflation is not represented; entering the
  2027 benchmark deflated one year is the conservative alternative (25.29 nominal 2027).
- **Buying gold:** Owl prices the marketplace as the benchmark (net cost min(SLCSP, applicable
  percentage x MAGI), `tax_federal.acaCosts`), so a gold plan's extra premium over the benchmark
  is not in the model. The credit does not depend on the plan bought, so the extra is the same
  at every income while the credit is below the gold premium: 3.97k/yr for the couple at 2027
  rates, 6.14k at 2026 rates. To model gold, add it as a `medical` budget line (premiums are
  medical expenses for the itemized claims), ending when Medicare starts.
- **Lone enrollee (verified in the code, `data/aca_age_rating.py:110`, used at
  `tax_federal.py:722` and `:725`):** when one spouse is on Medicare, Owl prices the other's
  benchmark as `f(younger) / (3.000 + f(younger))` of the couple's (CMS age curve). Under NY's
  tiers it is exactly 0.5. The gap is 0.5 - 0.479 at 60, - 0.459 at 58, - 0.426 at 55. For the
  household (both born 1964 per the template) the one-enrollee period lasts only the months
  between the two 65th birthdays, so the effect is small there; it matters for a couple with an
  age gap in NY (and other community-rated states). Not filed upstream.
- **Essential Plan:** DFS's summary says the rate decisions "do not include the Essential Plan
  ... available at no premium to lower-income New Yorkers who qualify". Fidelis's filing
  prices "the anticipated end of the EP5 expansion effective 7/1/2026, causing members in the
  200-250% FPL range to transition back to the QHP market". Owl models Medicaid up to 138% FPL
  and the federal sliding scale above it, not a $0 Essential Plan; the income limit (200% FPL
  after 7/1/2026) is inferred from that sentence, not read in a rule.

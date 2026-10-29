# Synthetic household and scenario suite

The household's own case is run **offline, by the user, on their own machine** (decision
2026-10-29; CLAUDE.md, "Household data"). Cloud sessions never ask for the real inputs or for
running the household case. They work here instead: a fictional household with the real one's
structure, and a suite that runs every scenario of `fork-notes/phase0/phase0-scenarios.md` on it,
so that each scenario is known to solve and to report readably before the real numbers go in.

| File | What it is |
|---|---|
| `make_cases.py` | Writes the synthetic household to `cases/` (gitignored): two case files, the workbooks, `condo_grid.json` (the suite's scenarios) and `work_variants.json` (for `work_sweep.py`) |
| `run_suite.py` | Runs the scenario set on a case pair (synthetic here, the real one offline) and writes `report.md`, plus a workbook, a synopsis and a log per run |
| `runs/` | Suite outputs (gitignored) |

## The household's structure (user, 2026-10-29)

- A couple born in April and December 1964, neither on the 1st (FRA 67; Medicare from April and
  December 2029).
- Both working in 2026; retiring at the end of 2026 at the earliest; part-time work and the SS
  claiming ages are open.
- Renting in Yonkers (10701). **Renting to the end is not an option** (no landlord asking them to
  move at 85): the question is where, when and how to buy a condo, in Yonkers (10701, about
  $700,000), White Plains (10603, about $700,000) or Flushing, Queens (11354, about $850,000),
  with cash or a mortgage. The purchase year is one of the things to decide.
- No bequest goal: savings spent by 89; the condo kept to the end as a reserve for long-term care.
- Married filing jointly; each has 40 SS credits (insured on their own record).
- Accounts: a joint brokerage account, larger than their two IRAs together, and one IRA each. Owl
  keeps one taxable account per spouse, so the joint account is entered as two equal halves (at a
  first death only the deceased's half gets a new basis, which is what Owl does with the
  deceased's own account, upstream #238). Taken as all their accounts: no Roth, no HSA, no 401k;
  wages come with an IRA contribution, not a 401k deferral.
- Rent $4,000/month, the same in 2027, then growing with inflation; condo HOA $800/month in every
  place, growing with inflation.

How Owl takes these:

- `life_expectancy = 89` for both, `maxSpending` with `bequest = 0`. The bequest floor counts
  savings only (`plan.py`, the `bequest_floor` row: fixed assets are added outside it), so savings
  are spent down and the condo is kept and reported in the final bequest.
- A purchase is rent until the year before, then the owner's Budget lines (property tax, common
  charges as `maintenance`, insurance; all `essential`), the condo in Fixed Assets, the price
  (cash) or the down payment and closing costs (mortgage) as a big-ticket item, the loan in Debts
  linked to the condo. Fixed Assets values, Debts amounts and big-ticket items are in the purchase
  year's dollars (`fixedassets.py`: "Basis and value are in reference-year dollars"), so the
  generator grows today's prices by the case's own inflation path.
- A purchase outside Yonkers is a move within NY in that year (`basic_info.moves`): White Plains
  has no local income tax; Queens is NYC (city income tax; a condo is tax class 2 for STAR,
  recalled, not checked against DOF). 10603 is split among school districts (White Plains City,
  Greenburgh Central, Valhalla per statisticalatlas.com, a secondary source): the condo's address
  decides; the synthetic case uses White Plains. A grep of `data/property_tax_relief.toml` finds no
  Valhalla.
- Owl has no purchase-year decision variable, so the year is a grid: 2027, 2029, 2031, 2034,
  2038, for each place and financing (30 variants).
- Long-term care: a care line from 2050 (age 86) with the condo kept (care paid from savings) or
  sold that year to pay for it.

Invented in the synthetic case (all stand-ins; the real ones go in the offline files): balances
(brokerage 2 x $800k, basis 70%; IRAs $550k and $400k), wages, the 2026 IRA contribution, PIAs (a little higher per extra work year), property tax and insurance of each condo,
closing costs, the mortgage rate, the condo's growth and selling commission, the care cost.

Rent in the Budget sheet is two lines in today's dollars: $48,000 in 2026, then $48,000 deflated
by one year of the case's inflation from 2027 on, with no real growth: the same nominal rent in
2026 and 2027, inflation after. The HOA is a `maintenance` line of $9,600 with no real growth.

## Running it

```bash
.venv/bin/python fork-notes/synthetic/make_cases.py
.venv/bin/python fork-notes/synthetic/run_suite.py fork-notes/synthetic/cases/Case_ari+noa.toml \
    fork-notes/synthetic/cases/Case_ari+noa_condo.toml fork-notes/synthetic/cases/condo_grid.json \
    --out-dir fork-notes/synthetic/runs/$(date +%F)
```

About 76 runs: the claiming-age searches one at a time, the fixed-age solves in parallel
(`--jobs`, default the core count); `--only condo ltc` runs a subset after the baseline.

Offline, on the real case: a copy of `make_cases.py` in `otherFiles/` with the real figures writes
the real case files, workbooks and scenario file there; then the same command on those files,
with `--out-dir otherFiles/suite/$(date +%F)`.

The work sweep (claiming ages decided by branch-and-bound at fixed ages; hours per variant) is
separate:

```bash
.venv/bin/python fork-notes/phase5/work_sweep.py fork-notes/synthetic/cases/Case_ari+noa.toml \
    fork-notes/synthetic/cases/work_variants.json --out-dir fork-notes/synthetic/runs/sweep --jobs 4
```

## What the report holds

Every comparison is against a purchase: the baseline buys in Yonkers at the start of 2027 with
cash (a reference point, not a recommendation). Groups:

- **main**: the baseline with its claiming ages searched; the work variants (stop at the end of
  2026; one or both full time in 2027; one or both part time 2027-2028), each with its stand-in
  PIA; both claiming at 62, 67 or 70; Noa part time 2027-2028 with both claiming at 62, for the SSA
  earnings test (every searched variant claims at 70; `ss-62` withholds too, from Ari's 2026
  wages: Ari is entitled from May 2026, at 62 and one month); no itemizing; the 2032 reversion; the 2027 benchmark.
  Differences under 1% are marked `~` (loop noise can make them, either sign). `both-stop-2026`
  repeats the baseline: its difference is the noise of the age search itself.
- **condo** (local search) and **condo-exact** (exact LP): the 30 purchases against the reference,
  at the baseline's claiming ages, with a pivot (purchase year against place and financing) and a
  table that says whether local search and the exact LP agree.
- **ltc**: care late in life, the condo kept or sold.
- **Run checks** (a run that did not solve, a loop that did not settle, cash-flow or infeasibility
  warnings), **feature checks** (each modeled rule fires where it should: payroll tax, ACA,
  Medicare, the Yonkers surcharge and the NYC tax, STAR for the owner, itemizing of the property
  tax and of the mortgage interest, the move ending the surcharge, the condo kept or sold, ...; a
  check says the rule fired, not that its amount is right), and the deduplicated **warnings**.

**Score.** The budget's housing and medical lines are essential, so under `maxSpending` net
spending is those lines plus k x the discretionary lines (core, travel, charity). The comparable
score is the first year's discretionary spending, k x D_0. The spending basis would not do: it
also holds the first year's essential lines, which differ between renting and owning. Beside the
score: savings left (about 0) and the home at the end, net of commission and of any loan still
owed. A later or cheaper purchase can give more spending and less home at the end; the report
shows both and does not add them.

Each run also leaves `<group>_<scenario>.xlsx` (the workbook `owlcli run` writes), `.txt` (its
Summary sheet as text) and `.log`; `results.json` keeps every metric; `--report-from
results.json` reprints the report without solving.

## Results

PROGRESS.md, "Synthetic household and scenario suite": the runs made so far and what they found.

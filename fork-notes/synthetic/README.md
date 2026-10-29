# Synthetic household and scenario suite

The household's own case is run **offline, by the user, on their own machine** (decision
2026-10-29; CLAUDE.md, "Household data"). Cloud sessions never ask for the real inputs or for
running the household case. What they do instead is this directory: a fictional household shaped
like the real one, and a suite that runs every scenario of `fork-notes/phase0/phase0-scenarios.md`
on it, so that by the time the real numbers go in, each scenario is known to solve and to report
readably.

| File | What it is |
|---|---|
| `make_cases.py` | Writes the synthetic household (invented numbers) to `cases/` (gitignored): two case files and seven HFP workbooks, plus `work_variants.json` for the work sweep |
| `run_suite.py` | Runs the scenario set on any case pair (synthetic here, the real one offline) and writes `report.md`, one workbook and one synopsis per run |
| `runs/` | Suite outputs (gitignored) |

## The synthetic household

"Ari" and "Noa", both born in 1964 (January and December, the template's shape), married filing
jointly, both living to 92, renting in Westchester outside Yonkers, no pensions. Both have wages in
2026 (pre-tax 401k deferral and an employer match) and stop at the end of the year. Marketplace
coverage from 2027 at the template's NY Region 4 benchmark (20.84 $k), gold-plan lines, Medicare
from 65 with medical prices 1.5%/yr above inflation, HSA balances. The budget profile has a
discretionary `core` line, a travel line on an age clock (62 to 80), essential medical lines, charity
and rent. The case file is the Phase 0 template with its TODOs filled, so a template change is
tested the next time the suite runs. All balances, PIAs and wages are invented.

Workbooks per scenario: one more work year (`_2027`), one spouse working part time 2027-2028
(`_oneworks`), renting (`_rent`), buying a Yonkers home at the end of 2026 with cash (`_buy_cash`)
or a 30-year mortgage at 6.25% (`_buy_mortgage`), and renting until 2031 then buying in New
Rochelle (`_move`, used with a `basic_info.moves` entry naming the school district).

## Running it

```bash
.venv/bin/python fork-notes/synthetic/make_cases.py
.venv/bin/python fork-notes/synthetic/run_suite.py fork-notes/synthetic/cases/Case_ari+noa.toml \
    fork-notes/synthetic/cases/Case_ari+noa_housing.toml --out-dir fork-notes/synthetic/runs/$(date +%F)
```

Offline, on the real case (files in `otherFiles/`, named as in `phase0-scenarios.md`; the housing
case is `Case_us_housing.toml`, section 5):

```bash
.venv/bin/python fork-notes/synthetic/run_suite.py otherFiles/Case_us.toml otherFiles/Case_us_housing.toml \
    --out-dir otherFiles/suite/$(date +%F)
```

The work sweep (section 4) is separate, because it takes hours:

```bash
.venv/bin/python fork-notes/phase5/work_sweep.py fork-notes/synthetic/cases/Case_ari+noa.toml \
    fork-notes/synthetic/cases/work_variants.json --out-dir fork-notes/synthetic/runs/sweep --jobs 4
```

## What the report holds

`report.md` has one section per group, each against its own base:

- **main**: the baseline as the case says (claiming ages searched), and per scenario of
  `phase0-scenarios.md` sections 1-3, 4b and 6 (retire a year later, claiming at 62/67/70, Yonkers,
  NYC, no itemizing, one keeps working, the 2032 reversion, the 2027 benchmark). Differences under
  1% are marked `~`: loop noise can produce them, with either sign.
- **residency-ls / residency-exact**: Yonkers and NYC again at the baseline's claiming ages, under
  local search and under the exact LP; a table then says whether the two agree on the sign and
  exceed their spread (the decision rule of CLAUDE.md "Loop noise").
- **housing / housing-exact**: buy with cash, with a mortgage (with and without itemizing), STAR
  off, and the 2032 move, against renting, under `maxBequest`; the same agreement table.
- **Run checks**: any run that did not solve, a loop that did not settle, cash-flow or
  infeasibility warnings.
- **Feature checks**: each modeled rule appears in the scenario that should trigger it (payroll
  tax on wages, ACA before 65, Yonkers and NYC tax, STAR for an owner and not for a renter,
  itemizing of property tax and mortgage interest, the home in the bequest, the move ending the
  Yonkers surcharge, ...). A check says the rule fired, not that its amount is right.
- **Warnings in the logs**, deduplicated, with the runs that raised each.

Each run also leaves `<group>_<scenario>.xlsx` (the workbook `owlcli run` writes), `.txt` (its
Summary sheet as text) and `.log`; `results.json` keeps every metric, and `--report-from
results.json` reprints the report without solving.

## Results

See PROGRESS.md, "Synthetic household and scenario suite", for the runs made so far and what they
found.

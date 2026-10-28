# Upstream #236 (LP-chosen spousal deposit split) against the household's structure

**Update 2026-10-28:** implemented upstream (`1bdc3b2`) as an option, `spousal_surplus_deposit_fraction =
"optimize"` (one row `d_0n + d_1n = s_n` while both live, epsilon tie-break toward spouse 0); merged.

Checked 2026-10-27 on `claude/determined-goodall-f5yxft` (upstream `dev` `07b9a77` merged).
The issue was read through the fetch tool (a summary, not verbatim): `rationalpiper`, 2026-10-26,
label enhancement, self-assigned by the maintainer 2026-10-27, no comments.

## The proposal

While both spouses are alive, replace the two rows `d_0n = (1 - eta) s_n`, `d_1n = eta s_n`
(`Plan._add_surplus_deposit_linking`) by one row `d_0n + d_1n = s_n`, keeping `d >= 0` and
the survivor rows. Reporter's PA case: one spouse's plan ends in 2030, the other's in 2039;
`eta` = 1 or the free split gives +$5,038 over the plan vs 0.5 (FL: +$365/yr), through the
first death and the ACA years before it.

**Code claim checked by reading (grep of `src`):** `eta` is read only by
`_add_surplus_deposit_linking` (`plan.py:4993`) and by `amorepair.deposit_split`
(`amorepair.py:90`, passed in `AmoContext` at `plan.py:8083`), which has no caller; it is saved
to and read from the case file (`plan_bridge.py:130`, `:499`) and the UI (`ui_bridge.py`).
Holds.

## The household's structure (template, `fork-notes/phase0/Case_us.template.toml`)

- Both born 1964, both `life_expectancy` 92: **equal horizons**, so `n_d = N_n` and the
  `eta` rows hold in every year. There is no survivor phase, so the first-death mechanism behind
  the reporter's gain cannot arise.
- `spousal_surplus_deposit_fraction = 0.5`; both spouses have the same allocation
  (`type = "individual"`, 60/40 for both). While both live, the two taxable accounts differ only
  in their cost basis (`taxable_cost_basis`), which enters the LP as a per-person gain fraction
  updated by the loop (`_update_gain_fraction`), not as an LP quantity.
- Objective `maxSpending` with bequest 0; rent vs buy is compared under `maxBequest` with a
  fixed `netSpending` (CLAUDE.md, "Budget profile").

## Measurement (`eta236.py`, output `eta236_2026-10-27.jsonl` / `.txt`)

A stand-in for the household: the template with **illustrative** balances (not the household's;
`otherFiles/` holds no inputs in this container): taxable 600k / 300k with basis 450k / 120k (gain
shares 25% / 60%, so that the split can matter), tax-deferred 1.2M / 500k, Roth 100k / 50k,
PIAs 3,200 / 2,000 at 67 (ages fixed), SLCSP 24k, 2026 wages 150k / 90k with 401k and employer
contributions, retired from 2027. Splits 0, 0.5, 1 and free (the proposal, patched in);
horizons as in the template (92 / 92) and a sensitivity with SpouseA at 85; objectives
`maxSpending` (template) and `maxBequest` at `netSpending` = 120k. Deciders: local search
(`breakpointMethod="local-search"`) and the exact LP (Medicare none, SS 0.85; LTCG, ACA and the
gain fraction stay in the loop). Same day, same code. Deposits are the LP's own, read before
`_netSurplusRoundTrip` (#234); it netted nothing in any run.

Results (value: spending k$/yr in today's $ under `maxSpending`, bequest in today's $ under
`maxBequest`; "vs 0.5" against the case's split):

| Decider | Objective | A's age | 0 | 0.5 | 1 | free | Deposits |
|---|---|---|---|---|---|---|---|
| local search | maxSpending | 92 | -2.44 | 160,979.28 | -3.96 | +6.52 | none |
| local search | maxSpending | 85 | -5.76 | 167,718.18 | -10.25 | -11.92 | none |
| local search | maxBequest | 92 | +0.01 | 1,855,929.86 | -157.14 | +86.87 | 2055-56, 13.5k/yr |
| local search | maxBequest | 85 | -512.46 | 2,015,694.48 | -473.30 | -512.46 | none |
| exact LP | maxSpending | 92 | +139.30 | 164,108.58 | -44.34 | +22.63 | none |
| exact LP | maxSpending | 85 | 0.00 | 170,391.32 | 0.00 | -0.03 | none |
| exact LP | maxBequest | 92 | +415.80 | 1,970,823.22 | -14,714.98 | -296.90 | 2026, 42.6k |
| exact LP | maxBequest | 85 | +453.80 | 2,126,830.53 | -787.69 | +453.80 | 2026, 42.6k |

What the table shows:

- **Under `maxSpending` (the template's objective) no run deposits anything**: spending is flat,
  so the 2026 wage year lowers withdrawals instead of creating a surplus. The split cannot
  matter; the spreads (local search up to $12/yr, exact LP up to $139/yr) are the solves' own
  noise, since the LPs differ only in rows on deposits that stay zero.
- **Under `maxBequest`, local search** (the decider for ACA years, CLAUDE.md "Loop noise")
  deposits only in the last two years, $13.5k each, at equal horizons: the split moves the
  bequest by at most $157 (0.008%), the free split +$87 vs 0.5. With SpouseA at 85 it deposits
  nothing, and the $512 spread is noise.
- **The free split does not dominate:** its feasible set contains every fixed split, yet it
  scored below 0.5 in three rows (local search maxSpending 85, -11.92; local search maxBequest
  85, -512.46; exact LP maxBequest 92, -296.90). The loop and the search settle on different
  plans, and that noise is as large as the split's effect here.
- **One large number, not decision-relevant:** the exact LP at equal horizons loses $14,715 of
  bequest at `eta` = 1, where its 2026 deposit goes to the 60%-gain account. Local search,
  which decides, makes no 2026 deposit at all. The exact LP keeps LTCG and the gain fraction in
  the loop, so this is a property of its plan, not of the split.

## Verdict for the household

On the template's structure (equal horizons, equal allocations) the deposit split does not
matter: no deposits under the template's objective, and at most $157 of bequest (0.008%) under
`maxBequest`, inside the solves' noise. #236's gain needs what the household does not have:
a first death within the plan, or accounts that differ in what the LP sees. Nothing to change
in the case file or in `work_sweep.py` (its `--eta` check stays as a cheap sensitivity on the
real inputs, which may differ from this stand-in: a larger wage surplus, a budget profile with a
drop in spending, unequal life expectancies, or different allocations per spouse).

Not checked: the reporter's own PA/FL numbers (his case setup is not reproduced here); the
issue's tie, inheritance and heirs points (outside the household's structure).

## Rerun

```bash
D=/path/to/workdir; mkdir -p $D
.venv/bin/python fork-notes/phase0/gen_hfp_us.py $D/HFP_us.xlsx
# then write HFP_us_wages.xlsx: row 2026 of SpouseA / SpouseB with anticipated wages 150000 / 90000,
# 401k ctrb 24000 / 15000, employer ctrb 6000 / 3000 (openpyxl), saved next to it
.venv/bin/python fork-notes/upstream-236/eta236.py $D > $D/out.jsonl
.venv/bin/python fork-notes/upstream-236/table.py $D/out.jsonl
```

32 solves on 4 workers took 19 min (14:20-14:39; 4,334 s of solves), local search 143-371 s each. A first run was discarded: the pool reuses worker
processes, so the free-split patch left on `Plan` by one job leaked into later fixed-split
jobs in the same worker (checked by a direct solve: `eta` = 1 put the 2026 deposit in B, the
leaked run in A). The script now sets the method on every job and records which was used
(`linking`).

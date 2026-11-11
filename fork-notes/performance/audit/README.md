# Scripts of the second performance review's audit (2026-11-11)

Run from the repository root after `fork-notes/synthetic/make_cases.py`. They change nothing in
`src/`; each prints what `fork-notes/performance-review-audit.md` quotes.

- `quantile_check.py`: the closed form for `stresstests._stochastic_lp`, the audited formula and a
  corrected one, against the LP over the 61 lambdas, and the time of both.
- `overhead_probe.py <preset> <HFP file> [options JSON]`: one solve with cumulative timers on HiGHS
  and on the Python the audited review wants cached (`deepcopy`, `to_csr`, money scaling, ...).
- `micro_timings.py`: single-call times (plan build, `readHFP`, `clone`, SS streams, `plan.json`
  blocks, the code stamp, ...), and the number of school districts in the STAR data.
- `workbook_read.py`: the Run page's `pd.read_excel(sheet_name=None)` on a results workbook.
- `stress_probe.py <n>`: `run_stochastic_spending` over `n` historical start years at Quick-look
  options, four worker threads then one.

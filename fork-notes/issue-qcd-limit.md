# Draft upstream issue: the 2026 QCD limit is \$111,000, not \$115,000

Status: **filed by the user as #240** (2026-10-29); **fixed upstream as filed** (`8ac888d`, 2026-10-29: the figure, a pinning test, the same four doc mentions; merged into the fork the same day). Drafted 2026-10-29 from the paper review (`fork-notes/paper-review-226ff54.md`,
item A2). Every figure below comes from stock upstream `dev` `226ff54`, run 2026-10-29:
- `fork-notes/issue-qcd-limit-repro.py`, run on stock and then with the patch (outputs below);
- the patch `fork-notes/issue-qcd-limit.patch` (`tax_federal.py` +3/-2, one test in
  `tests/plan/test_qcd.py`, the figure in `info/PARAMETERS.md`, `info/modeling-capabilities.md`,
  `ui/Documentation.py`, `papers/owl.tex`; made on `226ff54`).
- Source: IRS Notice 2025-67, "2026 Amounts Relating to Retirement Plans and IRAs",
  `https://www.irs.gov/pub/irs-drop/n-25-67.pdf`, fetched and read 2026-10-29 (quote below).
  The same notice confirms the 2025 figure Owl has (\$108,000).

Upstream suite on `226ff54` with the patch: 3285 passed, 1 skipped (6:37). Changed files flake8-clean.

Not in the patch: `CHANGELOG.md` line 1920 (the entry that introduced the limit says
\$115,000); it is history, the maintainer's call.

---

**Title:** QCD limit for 2026 is \$111,000 (IRS Notice 2025-67), not \$115,000

`tax_federal.qcdLimit` has `{2025: 108_000, 2026: 115_000}`. IRS Notice 2025-67 (2026
cost-of-living adjustments for retirement plans and IRAs) says:

> The aggregate amount of qualified charitable distributions that are not includible in gross
> income under section 408(d)(8)(A) is increased from \$108,000 to \$111,000.

So 2025 is right and 2026 is \$4,000 too high. `validateQCD` therefore accepts a 2026 QCD
between \$111,000 and \$115,000 and the model excludes all of it from income, where the excess
over \$111,000 is includible. Later years are projected from the last published figure, so every
projected cap is about 3.6% too high as well (2027: \$118,450 instead of \$114,330 at the fixed
3%).

**Repro** (stock `dev` `226ff54`, a single retiree born 1950, the QCD entered in the HFP `QCD`
column and read by `setContributions`; script attached):

```
tx.qcdLimit: {2025: 108000, 2026: 115000}
tx.qcdLimitForYear(2026): 115,000
QCD of $111,000 in 2026: accepted (qcd_in[0, 0] = 111,000)
QCD of $113,000 in 2026: accepted (qcd_in[0, 0] = 113,000)
QCD of $115,000 in 2026: accepted (qcd_in[0, 0] = 115,000)
QCD of $115,001 in 2026: refused: QCD of $115,001 for Alice in 2026 exceeds the annual per-person exclusion limit of $115,000.
```

With the patch:

```
tx.qcdLimit: {2025: 108000, 2026: 111000}
tx.qcdLimitForYear(2026): 111,000
QCD of $111,000 in 2026: accepted (qcd_in[0, 0] = 111,000)
QCD of $113,000 in 2026: refused: QCD of $113,000 for Alice in 2026 exceeds the annual per-person exclusion limit of $111,000.
QCD of $115,000 in 2026: refused: QCD of $115,000 for Alice in 2026 exceeds the annual per-person exclusion limit of $111,000.
QCD of $115,001 in 2026: refused: QCD of $115,001 for Alice in 2026 exceeds the annual per-person exclusion limit of $111,000.
```

**Fix:** `qcdLimit = {2025: 108_000, 2026: 111_000}`, with the notice cited beside it; the
same figure in `info/PARAMETERS.md`, `info/modeling-capabilities.md`, `ui/Documentation.py` and
`papers/owl.tex` (l. 1866). The existing tests read the limit through `qcdLimitForYear`, so none
pins the number; the patch adds one that does (`test_published_limits`). Patch attached; upstream
suite with it: 3285 passed, 1 skipped (6:37).

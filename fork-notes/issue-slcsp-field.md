# Issue draft: Run Options shows the benchmark premium to one decimal and steps it by \$10k

Status: **filed as #247** by the user (2026-11-07); was a draft, (2026-11-07, UX review Q20, `fork-notes/ux-review.md`). For the
user to file on `mdlacasse/Owl`. Checked on upstream `dev` `73dc8815` (2026-11-07). Patch:
`fork-notes/issue-slcsp-field.patch` (one call in `ui/Run_Options.py` and a test; applies to
stock `dev` with `git apply`; verified there: `tests/ui` 160 passed, and the new test fails on
stock `dev` with `'%.1f' == '%.2f'`). Repro script: `fork-notes/issue-slcsp-field-repro.js`
(Node + Playwright against a running Owl). The output below is from real runs in this
container: stock `dev` on one server, `dev` with the patch on another.

---

**Title:** Run Options: the SLCSP field shows one decimal and its +/− step is \$10k a year

*Benchmark Silver plan premium (SLCSP) (\$k/year)* is `kz.getNum(...)` with `sskeys.getNum`'s
defaults (`ui/Run_Options.py` 178): `format="%.1f"` and `step=10.0`. A premium is often known
to the dollar (\$20,840 a year is 20.84): typed in, it is shown as 20.8, and one click on +
adds \$10,000 a year.

**Repro (stock `dev` `73dc8815`):** upload `Case_riley+casey.toml` on Create Case, open Run
Options, type 20.84 in the field and press Enter, then click +.

```text
$ OWL_URL=http://localhost:8501 node issue-slcsp-field-repro.js examples/Case_riley+casey.toml
shown on arrival: 22.0 | step: 10
after typing 20.84: 20.8
after one + click: 30.8
```

**With the patch** (`step=1.0, format="%.2f"`; new `tests/ui/test_run_options_slcsp_field.py`
reads the field's format and step through AppTest):

```text
shown on arrival: 22.00 | step: 1
after typing 20.84: 20.84
after one + click: 21.84
```

(What the case stores after typing 20.84 on stock `dev` was not checked; the point is what the
field shows and what + does.)

Found by a review of the interface in our fork (`fmateoc/Owl`); the fork carries the same line.

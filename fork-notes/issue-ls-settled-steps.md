# Draft upstream issue: local search re-runs its node-capped steps in loop iterations where nothing moved

Status: **filed by the user as #252** (2026-11-11) **without a patch**: the issue presents the two
options (skip the capped steps; skip them and confirm the converged plan with one full search)
with their measurements. The patches below stay here, unattached. **Fixed upstream** the same day
as `1d91494` ("Local search skips the capped steps once the binaries have settled", `Fixes #252`,
authored as the user's with the maintainer as co-author), the first option, with no confirming
search; **merged here on 2026-11-12** (`c8a7d2e`, branch `claude/nice-euler-qy6161`). Its code
against `issue-ls-settled-steps.patch`: the same three skips under the same condition; a
`moved` flag set wherever a step is better replaces the patch's comparison of the final objective
with the start's (the same except within the `_IMPROVE` band, 1e-7 relative); the log line comes
before the steps ("binaries settled; skipping (b), (b') and (a')"); the module docstring describes
the rule. Its test is on `Case_joe` at `localSearchStepNodes = 100` with no monkeypatch (ours
forced four iterations on `Case_bill`). Its CHANGELOG entry gives the measurements of the issue
(`Case_joe` half the CPU, `Case_jack+jill` about a fifth less, plans unchanged to the cent). Checked
on the fork's synthetic variants against the draft patch: `performance-review.md`, section 6f.
The issue thread itself was not read (this session cannot read upstream issues); the commit is the
source. From the fork's performance review, P2
(`fork-notes/performance-review.md`, section "P2 on stock upstream"). Every number below comes
from stock upstream `dev` `8ec9c43` and the same checkout with the patch, HiGHS 1.15.1, this
container (4 cores, Linux), on 2026-11-11 with the date frozen at 2026-01-01 as the test suite
does:

- `fork-notes/issue-ls-settled-steps-repro.py` (stock only: `owlplanner` and the shipped
  examples), its output in `issue-ls-settled-steps-repro-output.txt`;
- the patch `fork-notes/issue-ls-settled-steps.patch` (`localsearch.py` +14/-3, one test in
  `tests/plan/test_local_search.py`, 2.4 s; applies cleanly on `8ec9c43`; the test fails on stock
  and passes with the patch);
- the variant with a confirming search `fork-notes/issue-ls-settled-steps-confirm.patch`
  (`localsearch.py`, `plan.py` +4, two tests; also applies cleanly on `8ec9c43`; measured in
  `performance-review.md` section 6e, the user's question of 2026-11-11);
- every example measured with `fork-notes/performance/p2_stock_run.sh` (both checkouts
  interleaved, three solves at a time), table by `p2_stock_table.py`.

Upstream suite on `8ec9c43` with the patch: 3318 passed, 1 skipped (10:53, `-n 2`, beside other
solves). The patch's own test is the one more test than stock's. With the variant: 3319 passed,
1 skipped (6:54, `-n 4`), its two tests the two more.

Check before filing (CLAUDE.md, "prevent at the input"): this is a performance finding, not a
bad input; the root cause is named first and the patch is kept to it. The open point (no
confirming search once the loop has settled) is stated, not hidden.

---

**Title:** Local search re-runs its node-capped steps in loop iterations where nothing moved

Under `breakpointMethod = "local-search"`, every iteration of the self-consistent loop runs a full
search. When an iteration's search starts from the binaries the previous one returned
(`start: previous binaries (LP)`) and moves none of them, the next iteration's problem differs
from it only by the loop's fed-back parameters, and steps (b), (b') and (a') run again from the
same binaries. In every example below where this happens they find nothing again, and the (b')
step stops at its 3,000-node cap each time. Those steps are most of the search's time.

**Repro** (stock `dev` `8ec9c43`, HiGHS, both wall-clock caps lifted so that the result does not
depend on load, `withSSAges = "fixed"`, the date frozen at 2026-01-01):

```
python issue-ls-settled-steps-repro.py examples/Case_joe.toml
```

Stock `dev`:

```
maxSpending: 99,080.90   CPU 198.8 s   local search (SS, IRMAA, LTCG, NIIT)
  search 0: start: repair from the loop plan, withdrawals and conversions +-$1; moved; 54.6 s, of which (b), (b'), (a') 46.6 s
  search 1: start: previous binaries (LP); no move; 39.2 s, of which (b), (b'), (a') 34.5 s
  search 2: start: previous binaries (LP); no move; 35.5 s, of which (b), (b'), (a') 32.1 s
  search 3: start: previous binaries (LP); no move; 32.1 s, of which (b), (b'), (a') 28.5 s
  search 4: start: previous binaries (LP); no move; 30.0 s, of which (b), (b'), (a') 27.2 s
```

With the patch:

```
maxSpending: 99,080.90   CPU 102.1 s   local search (SS, IRMAA, LTCG, NIIT)
  search 0: start: repair from the loop plan, withdrawals and conversions +-$1; moved; 52.3 s, of which (b), (b'), (a') 44.7 s
  search 1: start: previous binaries (LP); no move; 39.4 s, of which (b), (b'), (a') 34.7 s
  search 2: start: previous binaries (LP); no move; 3.5 s, of which (b), (b'), (a') 0.0 s
  search 3: start: previous binaries (LP); no move; 4.9 s, of which (b), (b'), (a') 0.0 s
  search 4: start: previous binaries (LP); no move; 3.6 s, of which (b), (b'), (a') 0.0 s
```

Searches 2 to 4 each start from the binaries the search before returned, move nothing, and spend
89-91% of their time in (b), (b') and (a'), which found nothing on the same binaries in search 1.
The plan is the same to the cent; the CPU time halves.

**All 19 examples** (same settings; CPU seconds; "searches" counts the loop iterations that
called the search, a repeated problem included):

| Example | Objective | Value, stock | Patched | Searches | Skipped | CPU stock | CPU patched | |
|---|---|---|---|---|---|---|---|---|
| Case_alex+jamie | maxSpending | 226,712.00 | same | 3 | 0 | 100.8 | 101.2 | +0% |
| Case_avery+quinn | maxBequest | 2,407,939.88 | same | 3 | 0 | 143.5 | 143.8 | +0% |
| Case_bill | maxSpending | 36,665.93 | same | 2 | 0 | 0.4 | 0.3 | -25% |
| Case_cameron | maxSpending | 18,996.31 | same | 2 | 0 | 1.0 | 1.1 | +10% |
| Case_chris+pat | maxSpending | 114,326.15 | same | 2 | 0 | 109.3 | 108.4 | -1% |
| Case_dana | maxSpending | 81,273.00 | same | 2 | 0 | 43.5 | 43.7 | +0% |
| Case_devon | maxSpending | 248,576.00 | same | 2 | 0 | 77.5 | 77.6 | +0% |
| Case_helen+ruth | maxSpending | 195,598.42 | same | 2 | 0 | 99.2 | 100.2 | +1% |
| Case_jack+jill | maxSpending | 111,038.88 | same | 4 | 1 | 291.6 | 239.0 | -18% |
| Case_joe | maxSpending | 99,080.90 | same | 5 | 3 | 191.1 | 97.2 | -49% |
| Case_john+sally | maxBequest | 14,013.49 | same | 2 | 0 | 51.8 | 51.6 | -0% |
| Case_jon+jane | maxSpending | 155,605.94 | same | 2 | 0 | 34.4 | 34.4 | +0% |
| Case_jordan+taylor-qcd | maxBequest | 1,206,372.88 | same | 2 | 0 | 69.2 | 69.2 | +0% |
| Case_jordan+taylor | maxBequest | 1,559,336.31 | same | 2 | 0 | 58.5 | 59.0 | +1% |
| Case_kim+sam-bequest | maxBequest | 1,962,072.42 | same | 2 | 0 | 250.6 | 251.7 | +0% |
| Case_kim+sam-spending | maxSpending | 186,383.24 | same | 2 | 0 | 219.7 | 220.3 | +0% |
| Case_morgan | maxSpending | 47,656.11 | same | 2 | 0 | 306.3 | 307.0 | +0% |
| Case_riley+casey | maxSpending | 118,949.85 | same | 4 | 0 | 769.3 | 767.7 | -0% |
| Case_robin | maxSpending | 44,159.28 | same | 2 | 0 | 18.6 | 19.4 | +4% |
| All 19 | | | 19 same | | 4 | 2,836.3 | 2,692.8 | -5.1% |

The CPU seconds were measured three solves at a time on four cores, both checkouts interleaved;
changes of a few percent either way where nothing was skipped are that noise.

Every plan is the same to the cent. The patch changes nothing where the loop converges in two
iterations (the second rebuilds the first problem and reuses its plan, `785217c`): 14 of the 19.
In `Case_alex+jamie`, `Case_avery+quinn` and `Case_riley+casey` the search that moves nothing
is the last one, or is followed by that reuse. It matters where the fed-back parameters keep
moving after the binaries have stopped: `Case_joe` and `Case_jack+jill` here.

With upstream's default caps (300 s per search, 60 s per step), two solves at a time, the two
examples where it applies give the same plans, no budget cut on either side, and the same
saving: `Case_joe` 190 -> 99 CPU-seconds (167 -> 84 s of wall), `Case_jack+jill` 291 -> 240
(269 -> 220 s of wall). On a slower machine or under load, where the 300 s budget cuts the stock
search short, the patch spends the freed time on the searches that move, so there the plans could
differ (the budget being wall-clock, not measured here).

**Suggested patch** (`localsearch.py`, attached with a test): remember whether the iteration
started from the previous binaries and moved none of them, and in the next iteration skip (b),
(b') and (a'). The (a) steps and (c) still run; when one of them moves the plan, the iteration
after it runs the full search again.

**What it leaves open, and a variant that closes it:** with the patch alone, once the loop has
settled no full search confirms the plan, so a move that the parameters' last changes opened to
(b) would be missed. It changed no plan in the 19 examples. The variant (attached as a second
patch, `localsearch.py` and four lines of `plan.py`, two tests) confirms it: when the loop's
decision is "converged" and that iteration's search skipped its capped steps, the full search runs
once on the same problem from the accepted plan (the rows are still that iteration's); if it finds
a better plan the loop goes on, and searches its next problem in full. A loop that ends on a cycle,
stagnation or its cap accepts an earlier iterate and is not confirmed. The confirmation costs one
full search, about what one skipped iteration saved, and found nothing in any run below:

| Example (caps lifted, CPU s) | Stock | Patch | Patch + confirmation |
|---|---|---|---|
| `Case_joe` | 193.5 | 99.6 (-49%) | 133.3 (-31%) |
| `Case_jack+jill` | 298.7 | 247.7 (-17%) | 303.9 (+2%) |

(The same three checkouts interleaved, three solves at a time; the plans the same to the cent.
The other 17 examples skip nothing, so the confirmation never runs there.) Over the 19 that is
about -2% with the confirmation, against -5% without. On six larger cases from a fork, which carry
fork-only features and so are not a repro here, it was -26% without and -13% with.

# Draft upstream issue: local search re-runs its node-capped steps in loop iterations where nothing moved

Status: **draft, not filed** (2026-11-11). From the fork's performance review, P2
(`fork-notes/performance-review.md`, section "P2 on stock upstream"). Every number below comes
from stock upstream `dev` `8ec9c43` and the same checkout with the patch, HiGHS 1.15.1, this
container (4 cores, Linux), on 2026-11-11 with the date frozen at 2026-01-01 as the test suite
does:

- `fork-notes/issue-ls-settled-steps-repro.py` (stock only: `owlplanner` and the shipped
  examples), its output in `issue-ls-settled-steps-repro-output.txt`;
- the patch `fork-notes/issue-ls-settled-steps.patch` (`localsearch.py` +14/-3, one test in
  `tests/plan/test_local_search.py`, 2.4 s; applies cleanly on `8ec9c43`; the test fails on stock
  and passes with the patch);
- every example measured with `fork-notes/performance/p2_stock_run.sh` (both checkouts
  interleaved, three solves at a time), table by `p2_stock_table.py`.

Upstream suite on `8ec9c43` with the patch: 3318 passed, 1 skipped (10:53, `-n 2`, beside other
solves). The patch's own test is the one more test than stock's.

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
iterations (the second rebuilds the first problem and reuses its plan, `785217c`), which is most
examples; it matters where the fed-back parameters keep moving after the binaries have stopped.

DEFAULTS_PARAGRAPH

**Suggested patch** (`localsearch.py`, attached with a test): remember whether the iteration
started from the previous binaries and moved none of them, and in the next iteration skip (b),
(b') and (a'). The (a) steps and (c) still run, and the first iteration in which one of them
moves runs the full search again.

**What it leaves open:** once the loop has settled, no full search confirms the plan, so a move
that the parameters' last changes opened to (b) would be missed. It changed no plan in the 19
examples. A confirming search would need the loop to tell the search that it is the last
iteration (the loop decides convergence after the solve); it would cost one full search, about
the time of the iterations above.

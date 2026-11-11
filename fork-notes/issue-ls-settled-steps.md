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

REPRO_OUTPUT

Searches 2 to 4 each start from the binaries the search before returned, move nothing, and spend
over 85% of their time in (b), (b') and (a').

**All 19 examples** (same settings; CPU seconds; "searches" counts the loop iterations that
called the search, a repeated problem included):

EXAMPLES_TABLE

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

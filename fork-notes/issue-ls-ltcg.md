# Draft upstream issue: local search pins the LTCG regime binaries while it moves SS taxability

Status: **draft, not filed** (2026-10-17). Found while checking PR #196 (`pr-196-reply.md`, which
mentions it in one line). Every number comes from stock upstream `dev` `7abed19`, with the date frozen
at 2026-10-15:
- `fork-notes/issue-ls-ltcg-repro.py`, output `issue-ls-ltcg-repro-output.txt`, on stock and then
  with the patch;
- the 18 examples, `model-review/ss-loop/ls_ltcg_sweep_2026-10-17.txt` (script `ls_ltcg_ex.py`;
  four runs at a time on 4 cores, so the times are relative).

Patch `fork-notes/issue-ls-ltcg.patch` (3 code lines plus comments, `localsearch.py` only). Upstream
suite on `7abed19` with it: 2866 passed, 1 skipped; flake8 only upstream's own E501 at
`localsearch.py:31`.

**Applied in the fork on 2026-10-17** (PROGRESS.md "Local search and the LTCG family": household stand-ins rerun; one fork case moved down $708, which is why the issue no longer says "never lower" without qualification). The fork ran the same `localsearch.py` and gave the same 20,004 (seen on fork code by mistake, a
`python -I` run that ignored `PYTHONPATH`). Our decision runs use the local-search preset, so the fork
needs the fix whatever upstream does (PROGRESS.md).

Not in the issue: the alternative measured and dropped, a separate step (b') that frees SS and LTCG
together only once nothing else moved (`model-review/ss-loop/ls_ltcg_variant2.patch`). It found the
same gains (john+sally 31,778; elsewhere within $630 of the patch's) for 1.87x stock's total time,
against 1.53x, with more code.

---

**Title:** Local search: $11.8k short on Case_john+sally, because step (b) pins the LTCG regime binaries while it moves SS taxability

While testing PR #196, I found that on the shipped example `Case_john+sally.toml` the local-search
preset stops well short of branch-and-bound. It is not SS pricing; it is the order in which the
search frees the families. Repro attached (`issue-ls-ltcg-repro.py`, plain Python on stock `dev`
`7abed19`, date frozen at 2026-10-15).

**1. The gap** (bequest, today's $; residual $0 in every run):

| run | bequest |
|---|---:|
| `breakpointMethod="local-search"` | 20,004 |
| `breakpointMethod="branch-and-bound"` | 31,778 |
| local search on SS + IRMAA (the rest on the loop) | 31,693 |
| ... + NIIT | 31,693 |
| ... + senior bonus | 31,778 |
| ... + LTCG | 16,803 ("local search -> loop": the loop's own plan) |
| branch-and-bound on SS + IRMAA + LTCG | 31,693 |

The loss appears only once LTCG is a searched family. A larger SS ball does not help:
`localSearchRadius=200` still gives 20,004 (on `7abed19`, 18.6 s).

**2. Why.** The `zl` binaries are regime binaries on ordinary taxable income itself:
`ltcg_zl15_link` holds G_n at or below T15 when `zl15 = 1`, and at or above it when `zl15 = 0`
(T20 likewise). They are not only about where the gains fall. Pinned, they hold each year's ordinary
income on its current side of each threshold, even in a year with no gains. The better plan moves
income across T15 in seven years and SS taxability in six of them, in the same move (today's $,
T15 = $98,900 MFJ):

| year | local search: G_n, taxable SS | branch-and-bound: G_n, taxable SS |
|---|---|---|
| 2028 | 95,550 (below), 0 | 183,829 (above), 0 |
| 2032 | 102,540 (above), 48,960 | 32,915 (below), 23,375 |
| 2033-2037 | 102,540 (above), 48,960 | 33,639-36,346 (below), 24,099-26,806 |

Branch-and-bound converts more early, so from 2032 to 2037 the couple's income drops under T15 and
SS is taxed in the phase-in rather than at 85%. Federal tax in those years is $3,677-4,192 instead of
$14,121. No step of the search can take that path:
- (a) frees LTCG with SS pinned;
- (b) frees SS with LTCG pinned;
- (a') frees the non-SS families jointly, SS still pinned.

Every move that needs both is blocked. (c) frees only years with a residual, and there is none.

**3. Patch** (`issue-ls-ltcg.patch`): in step (b), leave the LTCG binaries free along with the SS
ball:

```python
pinned = [f for f in others if f != "zl"]
res, dt = self._mip(options, overrides=self._pin(best[1], pinned), A=A, warm=best[1])
```

With it, john+sally under the local-search preset gives 31,778 (= branch-and-bound), and the plan is
the same as branch-and-bound's year by year (repro output, part 3). On the 18 examples (local-search
preset; objective = net spending for `maxSpending`, bequest for `maxBequest`; four runs at a time
on 4 cores):

| example | objective | `dev` | patched | change | time `dev` / patched |
|---|---|---:|---:|---:|---|
| alex+jamie | maxSpending | 229,688 | 229,697 | +9 | 61 / 118 s |
| avery+quinn | maxBequest | 3,253,440 | 3,253,440 | 0 | 159 / 220 s |
| bill | maxSpending | 36,666 | 36,666 | 0 | 0.5 / 0.6 s |
| cameron | maxSpending | 18,996 | 18,996 | 0 | 0.9 / 0.8 s |
| chris+pat | maxSpending | 117,197 | 117,295 | +98 | 56 / 117 s |
| dana | maxSpending | 81,273 | 81,273 | 0 | 39 / 76 s |
| devon | maxSpending | 248,613 | 248,613 | 0 | 59 / 64 s |
| helen+ruth | maxSpending | 195,210 | 195,332 | +122 | 57 / 66 s |
| jack+jill | maxSpending | 103,304 | 103,333 | +29 | 113 / 265 s |
| joe | maxSpending | 93,108 | 93,108 | 0 | 68 / 180 s |
| john+sally | maxBequest | 20,004 | 31,778 | +11,774 | 23 / 41 s |
| jon+jane | maxSpending | 160,905 | 160,905 | 0 | 18 / 30 s |
| jordan+taylor | maxBequest | 2,631,000 | 2,631,000 | 0 | 77 / 86 s |
| jordan+taylor-qcd | maxBequest | 2,278,835 | 2,278,835 | 0 | 70 / 72 s |
| kim+sam-bequest | maxBequest | 1,958,801 | 1,959,170 | +369 | 139 / 182 s |
| kim+sam-spending | maxSpending | 186,269 | 186,327 | +58 | 149 / 217 s |
| morgan | maxSpending | 44,209 | 44,216 | +7 | 151 / 168 s |
| robin | maxSpending | 44,159 | 44,159 | 0 | 17 / 15 s |

The patch is never lower here, and it gains in 8 of 18. That is not guaranteed in general: each restricted solve contains the current plan, so within one loop iteration the search cannot do worse, but a different plan feeds the next iteration's loop quantities, so the final plan can move either way. The cost is time: 1,257 s to 1,919 s in total
(1.53x), up to 2.6x on one example (joe, for no gain), because step (b) now branches on the LTCG
binaries too. One side effect: avery+quinn's residual moves from $1,405 to $1,665 at the same
objective. Upstream's suite on `7abed19` with the patch: 2866 passed, 1 skipped.

I also tried a cheaper-looking variant: a separate step that frees SS and LTCG together only once
nothing else moved. It found the same gains but took longer in total (1.87x), so I'd go with the
simpler change. If the time matters more than the gains on the examples, a step capped at fewer
nodes may do. I have not measured that.

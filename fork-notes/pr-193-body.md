# PR for #193: "convex" + the two points from the thread, for the user to open

Status: **opened by the user as PR #196** against `mdlacasse/Owl` `dev` (2026-10-17), from the fork's branch `ss-convex-pr` (`fb8b10e`). The PR could not be opened from the session (its GitHub access covers `fmateoc/owl` only, and `mdlacasse/owl` cannot be attached alongside a repo of the same name), so the user opens it: https://github.com/mdlacasse/Owl/compare/dev...fmateoc:Owl:ss-convex-pr?expand=1 with the title and text below. The maintainer on #193 (2026-10-17, read from the issue
page): "Can you bundle both points above in a single PR and I'll test and push." Read as the two
points in our two comments above his: (1) when the loop ends at the cap or in a cycle with a large SS
residual, point to an exact method (first reply); (2) the Summary labels a "convex" solve "loop"
(second reply). Point 2 needs "convex", which is only on `ss-convex`, so the branch is
`upstream/ss-convex` + `upstream/dev` merged in (clean) + one commit, and the PR targets `dev`.

Local branch `ss-convex-pr` (worktree in the scratchpad): `7d1169c` merge of `dev` `2b34633` into
`ss-convex` `c22f46d`, then `fb8b10e`. Stock code only, no fork code. Upstream suite on it: 2871
passed, 1 skipped; flake8 (CI's strict select) 0; ruff only the B905 already on `dev`. The two new
tests fail without the change; the pinned-fraction test passes either way (it guards against a false
warning).

Limit stated in the PR: the warning reports a loop that did not settle (residual above
residualTol x N_n), not a loop that settled short with a small residual. Under the tests' frozen
date the #193 couple at $105k ends with $1,167 of SS residual (bar $1,550) while upstream's own test
shows the loop >$10k short of "convex"; at $95k it 2-cycles with $3,073 and warns.

---

**Title:** #193: withSSTaxability="convex", with the Summary naming it and a warning when the loop leaves SS unsettled

As asked in #193, this bundles the two points from the thread on top of your `ss-convex` branch.
The branch is `ss-convex` (`c22f46d`) with `dev` (`2b34633`) merged in (no conflicts), plus one
commit, so the diff against `dev` includes your three `"convex"` commits.

**1. The Summary names "convex".** `_breakpointMethodLabel` listed only the families carried as
binaries, so a `"convex"` solve read "loop". It now ends in "; SS: convex" when SS was priced by
`"convex"`, and stays "loop" when it fell back on the loop (`withSSAges="optimize"`, or an
unsolvable iterate).

**2. A pointer when the loop leaves SS unsettled.** `_warnSSResidual` runs after the fixed-point
residual is computed. When the SS residual exceeds the loop's own tolerance summed over the plan
(`residualTol` x `N_n`, $50 x years by default), the log says so and points to
`withSSTaxability="convex"` or `breakpointMethod="local-search"`. It is skipped for a pinned
fraction (a choice, not a loop result), inside local search's seeding loop, and inside a `"convex"`
probe.

One limit: this catches a loop that did not settle, not one that settled short with a small
residual. Under the tests' frozen date (2026-01-01), the #193 couple at $105k ends with $1,167 of SS
residual (the bar is $1,550), while `test_convex_beats_the_loop_and_is_consistent` shows the loop
more than $10k short of `"convex"` there. At $95k the loop 2-cycles with $3,073 and the warning
fires; the test uses that case. I don't see a cheap signal for the second kind short of solving
exactly.

**Also:** `info/PARAMETERS.md` documents `"convex"`; CHANGELOG entries under *Version WIP*.

**Tests** (`tests/plan/test_ss_convex.py`):
- the label under `"convex"` and under the loop;
- the warning at $95k under the loop, and none under `"convex"`;
- no warning for a pinned fraction (0.85).

The first two fail without the change. Full suite: 2871 passed, 1 skipped; flake8 with CI's strict
selection: 0. Ruff reports only the B905 already on `dev` (`tests/plan/test_roth_maturation_losses.py:49`).

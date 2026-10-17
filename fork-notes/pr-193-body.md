# PR for #193 (PR #196): the SS-residual warning only, for the user to paste

Status: **reworked 2026-10-17** after the maintainer's question ("Are you sure you want to keep the
ss-convex implementation? ... Your call") and the user's decision to drop "convex"
(`pr-196-reply.md`). Branch `fmateoc:ss-convex-pr` force-pushed (with a lease on the old head)
from `fb8b10e` (upstream `ss-convex` + `dev` + label/warning) to `e5a9ad5`: one commit on upstream
`dev` `7abed19`, stock code only. Upstream suite on it: 2869 passed, 1 skipped; flake8 (CI's strict
select) 0, ruff clean on the changed files. The warning test fails without the change; the other
two pass either way (they guard against a false warning). The session cannot edit the PR on
`mdlacasse/Owl` (GitHub access covers the fork only): the user replaces its title and description
with the text below.

The previous version of this file (the "convex" PR text, as opened) is in git history at `c5a419e`.

---

**Title:** #193: the loop warns when Social Security does not settle

As discussed in #193 and on this PR: `ss-convex` is left out, and this is now one commit on `dev`
(`7abed19`).

**The warning.** `_warnSSResidual` runs after the fixed-point residual is computed. When the SS
residual exceeds the loop's own tolerance summed over the plan (`residualTol` x `N_n`, $50 x years
by default), the log says so and points to `withSSTaxability="optimize"`. It is skipped for a pinned
fraction (a choice, not a loop result), under `"optimize"`, and inside local search's seeding loop.

One limit: this catches a loop that did not settle, not one that settled short with a small
residual. Under the tests' frozen date (2026-01-01), the #193 couple at $105k ends with $1,167 of SS
residual (the bar is $1,550) although its plan is well short of the exact one; at $95k the loop
2-cycles with $3,073 and the warning fires. The test uses that case. I don't see a cheap signal for
the second kind short of solving exactly.

**Tests** (`tests/plan/test_ss_residual_warning.py`, the #193 couple):
- the warning at $95k under the loop;
- none under `withSSTaxability="optimize"`;
- none for a pinned fraction (0.85).

The first fails without the change. Full suite: 2869 passed, 1 skipped; flake8 with CI's strict
selection: 0. CHANGELOG entry under *Version WIP*.

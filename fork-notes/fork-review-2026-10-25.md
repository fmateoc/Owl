# Fork review: where the fork can move closer to upstream (2026-10-25)

Fork-only note. Branch `claude/phase5-step1` at `5109380` (upstream `dev` `4e55b36` merged; `dev`
has nothing newer, `git log HEAD..upstream/dev` empty). Method: `git diff upstream/dev HEAD`, file
by file. Edits to upstream lines (the `-` side of each hunk) were read in full for `plan.py`,
`tax_state.py`, `export.py`, `hfp_io.py`, the config bridges, `explain*`, the UI, `info/`, the
paper and the changed upstream tests; added fork code was read only where it replaces upstream
code. Each claim below says how it was checked.

## 1. Done in this session

| Change | Why | Checked |
|---|---|---|
| `@_fixedAcrossIterations` restored on `Plan._add_defunct_constraints` | Deleted by mistake in `a5fd533` (NJ removal) along with the NJ builder above it: the decorator line went with the deleted block. Upstream has it. Without it the bounds were rebuilt on every loop iteration instead of replayed: same bounds, so no plan changes, only the extra rebuild. | `git show a5fd533` (the `-    @_fixedAcrossIterations` line sits right above `def _add_defunct_constraints`); a scan of every line `a5fd533` removed that upstream still has: this was the only one. Full suite (section 5). |
| Fork block of `CHANGELOG.md` (203 lines at the top) moved to `fork-notes/CHANGELOG-fork.md` | `CHANGELOG.md` conflicted at most syncs (upstream: 84 commits to it since 2026-10-01; PROGRESS.md records a `CHANGELOG.md` conflict in the merges of upstream `f41fcdc`, `844a7ec`, `390f02f` (its only conflict), `bb52632` and `37afa2a`, among others). It is now upstream's byte for byte (`git diff upstream/dev -- CHANGELOG.md` empty). The block had already stopped being complete (no Phase 5 entry). Trade-off: the UI's About page (`ui/About_Owl.py`) shows upstream's notes only. | diff empty |
| `papers/owl.tex`: the NJ exclusion paragraph removed | It described code removed on 2026-10-17 (tier binaries `z^x`), with a 60 s cap replaced on 2026-10-06. | read |
| `fork-notes/phase0/Case_us.template.toml`: two NJ mentions | Description listed NJ as a residence option; the `withItemized` comment named NJ line 31. | template still loads (`toml.load`) |
| `fork-notes/CHANGELOG-fork.md`: "recapture and exclusion arrays" -> "recapture and itemized-deduction arrays" | `StateTaxParams` has no exclusion field since `a5fd533`. | read `tax_state.py` |

## 2. Decisions for the user, largest divergence first

### A. The age-anchored smile changes upstream's own examples

**Done 2026-10-25 (user): the fork's smile dropped, upstream's taken** (not the opt-in below). See
PROGRESS.md, "The fork's smile dropped".

The fork's smile (fixed 30-year cosine period, start at an age, survivor's age after the first
death) replaces upstream's curve for every smile case, including the six example cases, which
carry a fork-only `smile_start_age` line. Measured on 2026-10-24 (PROGRESS.md, "The rest
isolated"; recorded, not rerun today): with itemizing off and a flat profile, jordan+taylor and
jordan+taylor-qcd equal stock to the cent; so the smile is all of jordan+taylor-qcd's +3.5% and
2.3x solve time (66 -> 154 s) and part of jordan+taylor's +2.7%. jack+jill's pinned value is 103,578 in the
fork vs upstream's 102,621 (`tests/plan/test_toml_cases.py`; the 102,535 -> 103,499 step is the
smile, per the comment there). morgan's +3.6% was not isolated. The AMO fixture rows of jack+jill,
jordan+taylor and morgan were re-recorded for it, and their MOSEK entries dropped.

The household does not use the smile: the template sets `spending_profile = "flat"`
(`Case_us.template.toml:76`) and the housing scenarios use `"budget"` (`phase0-scenarios.md`
section 5); the budget's age clocks are separate code (`budget.py` does not call the smile).

Options:
1. **Opt-in** (recommended): without `smile_start_age`, `gen_spending_profile` draws upstream's
   plan-stretched curve from `smile_delay`; with it, the fork's anchored curve. Drop the line from
   the six examples. Upstream's examples, pinned values and AMO rows (as far as the smile goes) are
   upstream's again; `smile_start_age` stays available. The old-case warning goes away.
2. File it upstream as its own issue (the track-B note already called it "a self-contained
   upstream issue"; not filed, `grep` of `fork-notes/issue-*.md` finds no smile issue). Compatible
   with 1.
3. Keep as is. This was the user's choice on 2026-10-10 (track-B finding 6), made for a plan that
   used the smile.

### B. `withItemized = "loop"` by default

Itemizing is fork-only for good (#185 dropped upstream, user 2026-10-24). As the default it runs on
every upstream case: devon's whole difference from stock (3.4x time, +0.5%) and part of
jordan+taylor (PROGRESS.md, "The four with `withItemized="none"`"), and it is why the fork's copy
of upstream's `test_ss_residual_warning.py` passes `withItemized="none"`. The household's template
sets `withItemized = "loop"` itself (`Case_us.template.toml:85`), so a default of `"none"` would
not change the household's runs; it would make upstream's cases run upstream's model. Cost: a case
file without the key loses itemizing silently (the docs would have to say so); every fork test that
relies on the default needs the option.

### C. The payroll tax, always on

Decided on 2026-10-24 (user); upstream design issue #227 is open. Cost on the upstream side: the
`payrollTax` monkeypatch fixtures in three upstream test files and the AMO rows of the cases with
wages. Nothing to change unless #227 is declined; then option A's opt-in pattern applies here too.

### D. Several moves where upstream takes one

No scenario uses more than one move (`phase0-scenarios.md`: the only move command, line 62, has one
entry; NJ and moves between states are dropped). Going back to upstream's limit of one, keeping the
locality and school district on it, would drop the UI's `stateMovesMore` plumbing, the `moves` list
in `explain`, and the fork's edits to upstream's move tests (`"At most one"`); `Residence` stays a
4-tuple, so the two `state_moves == [(year, "FL", "", "")]` test edits stay. Moderate gain, low
risk.

### E. `StateTaxParams` where upstream returns a tuple and a dict

The fork rewrote every upstream test that unpacks `st_taxParams` or indexes `st_schedule` (about
40 lines of `tests/tax/test_state_tax.py`). Giving `StateTaxParams` an `__iter__` that yields
upstream's 9-tuple and a `__getitem__` for upstream's dict keys would let those tests go back to
upstream's text and let new upstream tests on these functions merge unedited. Low priority:
upstream touched `tax_state.py` / `test_state_tax.py` in 3 commits since 2026-10-01.

### F. Fork features the scenarios do not use

`grep` of `fork-notes/phase0/` finds no use of `budget_file` (JSON), essential budget lines, age
clocks on budget lines, `withSTAR = "optimize"`, or a `Housing` sheet. Most of this lives in
fork-only files (`budget.py`), so it costs little at a sync. The exception is the legacy `Housing`
sheet reader in upstream's `hfp_io.py` (`_conditionHouseTables`), for a sheet format the fork used
for one day (2026-10-07) before Phase 2b: removable. The rest were also the fork's input to
Discussion #177 (Owl-budget); keep unless a smaller fork is wanted.

### G. `otherFiles/PROGRESS.md` is tracked

The only tracked file under the gitignored `otherFiles/`: stale Phase-1 notes (Windows-1252 bytes,
references to `myfiles/requirements.md` and `scripts/`). No balances or PIAs in it (read). Removing
it with `git rm` would also delete it from the user's own checkouts at the next pull, so it is left
for the user.

## 3. Upstream opportunities

1. **NY benefit recapture (#158).** Closed by `fmateoc` on 2026-10-07 as completed, with no
   maintainer comment (PROGRESS.md, read on GitHub 2026-10-12; not rechecked: this session cannot
   read upstream issues). Upstream still has no recapture: `git grep -i recapture upstream/dev --
   src` finds nothing. So upstream under-taxes every NY plan above \$107,650 of NY AGI. The stock
   patch `fork-notes/issue-ny-recapture.patch` (refreshed on `5dd1623`) no longer applies to
   `4e55b36` (`git apply --check`: fails in `tax_state.py` and `plan.py`). Recommended: check
   whether the closing was intended; if not, refresh the patch on current `dev` and reopen or
   refile.
2. **Paper and docs drift.** `fork-notes/issue-docs-loop-and-paper.md` (not filed; measured on
   `a85ff76`, before local search). The fork's own `owl.tex` edits also describe upstream code that
   upstream's paper does not: per-state indexing flags (#157), the state base as federal AGI (the
   `-e_n` term in Eq. StateTI; upstream's `_add_state_taxable_income` adds the federal deduction
   back, read), the state SS exclusion through `tss` under `withSSTaxability="optimize"` (read),
   the ACA threshold clipping (#161), the bracket-order tie-break (#162; `TAX_TIEBREAK` in
   upstream's objective, read) and the change of state (#159). Refreshing the draft and filing it
   would let most of the fork's paper diff go.
3. **The anchored smile** (option A.2).

## 4. Checked, nothing found

- No upstream test was dropped: every `def test*` in every upstream test file exists in the fork's
  copy (script over `git ls-tree upstream/dev tests`).
- `examples/`: the only fork edit is the `smile_start_age` line (A).
- The other edits to upstream lines in `export.py`, `hfp_io.py`, `config/`, `assistant/`, `cli/`,
  `ui/` and `info/` serve fork features (locality, STAR, moves, budget, payroll tax, itemizing);
  none is cosmetic. `localsearch.py`: `zst` as a family, needed (CLAUDE.md, "Upstream's local
  search and fork binaries").
- `plan.py`'s rewrite of upstream's loop bookkeeping (`M_n_lp` / `ACA_n_lp` / `J_n_lp` /
  `Psi_n_lp` replaced by the `_SC_PARAMS` registry) is the largest edit of upstream lines left
  (about 60 lines in `solve`). Upstream touched `plan.py` in 42 commits since 2026-10-01, so it is
  a conflict risk, but it carries the fork's own loop parameters (`STR_n`, `STAR_n`, itemizing);
  no change proposed.

## 5. Tests

Full suite with the restored decorator: **3515 passed, 1 skipped** (7:10), the count of the
previous run (2026-10-25, `withPayrollTax` removed). flake8 and Ruff clean on `plan.py`.

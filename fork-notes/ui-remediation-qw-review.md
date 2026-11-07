# UI remediation Phase 1 (QW-1-QW-8): independent review of `claude/ui-remediation-qw` (2026-11-07)

Independent review of branch `claude/ui-remediation-qw` at `082f9b96` (one commit on top of
`main` `07701242`, 28 files, +1,026/−137), against the work order quoted in the review brief
(the remediation plan's Phase 1 "Labels, Units, Validation & Table Ergonomics"), the AL1-AL6
review `fork-notes/ux-q10-q20-review.md` (AL3/AL4 are what QW-7/QW-1 close), and PROGRESS.md's
"UI remediation Phase 1: quick wins QW-1-QW-8". Findings **AM1-AM8** (3 low, 5 nit; no high or
medium); prefix AM after AL.

**Status (2026-11-07, the user's call):** AM1-AM3 and AM8 **folded** on the branch (PROGRESS.md
"UI remediation Phase 1: the independent review, AM1-AM8"; AM1's fold also covers the
medical-inflation mover's note, a fourth jargon spot its own teeth check found); AM4-AM7 stand.

Environment: Windows, Python from `.venv`, HiGHS only, tests with
`.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` (the suite freezes the date at
2026-01-01; the real date is 2026-11-07). **Nothing in `src/`, `ui/`, `tests/` or the existing
docs was changed by this review** (only this file). Probes live in the session's temp dir
(`…\Temp\opencode\qw-review\probe_qw1.py`); before/after runs and teeth-checks were made in
throw-away `git worktree`s of `082f9b96` and `07701242` (removed afterwards), with
`PYTHONPATH` set to the worktree's `src`. `git status` is clean apart from this file.

## What was run

| Command | Result |
|---|---|
| Full suite, `pytest -n 4 -q -p no:cacheprovider` on `082f9b96` | **4539 passed, 2 skipped** (700 s) — matches PROGRESS/CLAUDE's claim; the skips are `tests/library/test_jobs.py:184` (tzset, POSIX-only) and `tests/solver/test_solver_status.py:85` (MOSEK unlicensed), so "the second skip is a platform one" holds (`-rs` on both files: 33 passed, 2 skipped) |
| `flake8 src tests ui --max-line-length=120` | only upstream's E301/E304 in `tests/stochastic/test_spending_{bequest_frontier,units}.py` |
| `ruff check src tests ui` | 4 B905, all upstream's listed items; `ui/Run_Options.py` is at **line 295**, as PROGRESS claims (CLAUDE.md still says 263, see AM8) |
| Targeted: `test_thresholds.py`, `test_brackets.py`, `test_view.py` | 72 passed |
| Targeted: `test_run_charts.py`, `test_variant_tables.py`, `test_open_in_owl.py`, `test_run_options_year_bounds.py`, `test_account_balances_units.py` | 78 passed |
| AL4/QW-1 before/after probe (`probe_qw1.py`) on `07701242` and `082f9b96` | see AM6/AL4 evidence below |
| AL3/QW-7: new `test_the_workbook_is_named_without_its_folder` run against the parent's code | **failed** there (`'runs\\2026-11-07_x\\inputs\\HFP.xlsx' == 'HFP.xlsx'`), passes at `082f9b96` — before/after shown |
| Teeth checks (throw-away worktree at `082f9b96`, one hunk reverted at a time, then `git checkout --`): see the table under "Tests have teeth" | every listed test fails without its change |
| New `tests/ui/test_run_charts.py` copied onto `07701242` | **13 failed, 7 passed** (every new/changed test binds to QW-1/QW-3) |
| `toml` CRLF claim, `without_folder`, `method_text` wording (probes) | see AM4/AM5 and the changelog check below |

## What holds (each claim checked; how)

- **QW-1** [probe + tests]: a "`…, net refund`" row is grouped as a tax offset
  (`_source_group`), never appears under *income*, and the taxes sentence nets it. The
  before/after paragraph and Sankey nodes (probe, a STAR-refund year):
  - before (`07701242`): *"…and from income, \$29,645 (Social Security \$28,931, State and
    local tax, net refund \$714). Taxes \$2,847: state and local \$2,847…"*, node
    `State and local tax, net refund: $714`, and a single-premium year has **no** Health
    premiums node;
  - after (`082f9b96`): *"…and from income, \$28,931 (Social Security \$28,931). Taxes net of
    a \$714 state and local tax refund took \$2,133: State and local tax \$2,847, Federal
    income tax \$0. Health premiums \$21,745 (ACA marketplace premiums \$21,745)…"*, node
    `State and local tax refund: $714`, `Health premiums: $21,745` kept with one line, and the
    Sources vs. Uses table renders under the Sankey (`ui/Run.py:143`).
  AL4's three labels (Capital gains tax / ACA marketplace premiums / Medicare premiums) are
  indeed one word set for prose and nodes (`FLOW_WORDS`).
- **QW-2** [tests + code]: crossed discrete cliffs are listed wherever the year sits
  (`TestCrossedCliffs`, both fail without the builder change), the \$100 noise floor drops the
  \$3–\$26 recapture/NIIT noise (`test_a_pricing_under_a_hundred_dollars_is_noise_and_is_not_listed`),
  and IRMAA rows read "paid in 2030 via the 2-year Medicare lookback: the MAGI of 2028 sets
  those premiums" (`ui/Run.py`'s table shows the note and the `Affects` year).
- **QW-3** [tests]: "IRMAA tier" names the active/next tier ("IRMAA Tier 2 ($274,000) —
  crossed (+$26,000 in 2029)" / "IRMAA Tier 1 ($218,000) — $98,000 below (sets 2029)") and
  "Binding ceiling" names the closest ceiling; `conversion_cap` is a new per-row key in
  `brackets.bracket_view` (`maxRothConversion` scaled by `utils.get_monetary_option` exactly as
  `plan.py:4624-4633` caps each individual's conversions; test: 50 ($k) × 2 converters =
  100,000 today's $). Older plan.json rows degrade gracefully (`row.get("conversion_cap")`,
  "-" where no IRMAA edges; `tests/ui/test_run_charts.py:75`).
- **QW-4** [tests]: `down`/`closing`/`extra` are typed as percentages (20 → 0.20 stored),
  matching Scenario.py's purchase box (`_share_from_percent`, `ui/Scenario.py:267-275`); the
  event shape is unchanged, so stored collections need no migration (the editor starts empty).
  `rate`/`term` keep their Scenario.py semantics (percent / years) — checked, no second
  mismatch hiding beside this one (`builder.FINANCING_DEFAULTS`, `library/scenario.py:370`).
- **QW-5** [tests]: the headline is "First year's total spending" with the split as delta only
  when the objective is `maxSpending` **and** the summary carries both split keys — which
  `export.plan_metrics` writes only with essential budget lines
  (`src/owlplanner/export.py:1051-1059`), so no "$0 essential budget" headline can appear.
  Other objectives keep the score; the caption names the score with its value.
- **QW-6** [tests]: `method_text` is plain English ("Careful — exact tax & Medicare
  optimization"; companions "a simpler exact model, used as a check"), the codes/families/gap/
  commit/options and the claiming-age scorer sit in the collapsed "Technical solve details"
  expander, and the sensitivity table lost its "model" column. `ui/Collections.py:445`, the
  other `method_text` consumer, renders the plain words fine (full suite green).
- **QW-7** [tests + parent run]: `openCaseFromPlan` names the workbook without its folder in
  both `hfpFileName` and `stHFP` (the parent run above shows the path that AL3 reported;
  `plan.hfpFileName` itself is left alone, so nothing that treats it as a path breaks — its
  consumers are display/save-name code, `casefiles` normalizes at save). The *Edit as new run*
  handler aborts on a falsy `readHFP`; `readHFP` returns True/False exactly (`ui/owlbridge.py:
  1381-1421`, verified), so "any falsy" and "returns False" are the same test here.
- **QW-8** [tests]: "*{case}* variant" default when `kz.runBase()` is set (`ui/Library.py:189-200`);
  ✓ instead of 🔻 with both marks stripped in `switchToCase`; Roth/swap years clamped into
  `[thisyear, plan_end]` with the stop default `min(thisyear+10, plan_end)`; ACA start year a
  plain year defaulting to this one (a stored 0 is equivalent — the plan starts in the solve
  year and `aca_start_year` is consumed as an offset, `brackets.py:112-113`); the \$50M balance
  warning fires at > 50,000 ($k).
- **The two platform fixes are real**: `toml.loads` of a CRLF **Case.toml** really keeps only
  the first key on `toml` 0.10.2 here (probe: `LF keys: 12 / CRLF keys: 1 ['case_name']` —
  literally "read as its name alone"), and `load_toml` now returns all 12 keys from both the
  `StringIO` and `BytesIO` branches (probe). `without_folder`'s fix is incomplete in one
  corner, see AM5.
- **Docs' claims**: suite count 4539/2 [verified]; B905 at `ui/Run_Options.py:295` [verified
  with ruff]; the changelog's toml claim [verified with the probe above]; the changelog's
  QW-1/QW-5 example strings [verified in tests]. Two doc blemishes in AM8.

## Tests have teeth (revert checks, each in the throw-away worktree, restored afterwards)

| Reverted hunk | Tests that fail |
|---|---|
| `run_charts._source_group`'s ", net refund" clause (QW-1) | `TestOneYear` 3 failed |
| `thresholds._irmaa_entries`/`_aca_entries` far-cliff generation (QW-2) | `TestCrossedCliffs` 2 failed |
| `thresholds._keep` back to `cost > 0.005` (QW-2) | `test_a_pricing_under_a_hundred_dollars_is_noise_and_is_not_listed` failed |
| `variant_tables._share` without `/100` (QW-4) | `TestFinancingPercentages` 2 failed |
| `Run.py` `_split` forced False (QW-5) | `test_the_headline_numbers_come_from_the_result` failed |
| `view.method_text` without `PRESET_PHRASES` (QW-6) | `test_view` 2 failed |
| `owlbridge.openCaseFromPlan` without the basename strip (QW-7) | `test_the_workbook_is_named_without_its_folder` failed (also the AL3 before/after run) |
| `sskeys.flagCurrentCase` back to "🔻" (QW-8) | `TestTheCurrentCaseMark::test_the_current_case_is_marked_with_a_check` failed |
| whole new `test_run_charts.py` on `07701242` (QW-1/QW-3) | 13 failed, 7 passed |

## Findings

### AM1 (low): QW-6's jargon is only half out of the sensitivity block

The sensitivity expander's header was rewritten to plain words ("Each child is re-solved in a
simpler, faster model", `ui/Run.py:689-700`), but three captions **inside the same expander**
still say "exact LP": *"The bars wait for this run's own exact-LP solve"*
(`ui/Run.py:758-760`), *"'s {'exact-LP' …} solve"* (`ui/Run.py:764-766`) and *"(each is one
solve under the exact LP, the medical-inflation pair with Medicare priced exactly)"*
(`ui/Run.py:815-817`). The header expander also keeps the line "The sensitivity children are
solved under the exact LP (for speed)" (`ui/Run.py:452-453`) — that one is where QW-6 meant
the jargon to live. The net effect is that one block uses two vocabularies, and a reader of
the tornado cannot tell that "the simpler, faster model" and "the exact LP" are the same
thing. Mitigations that make this low, not medium: these captions are inside the collapsed
Sensitivity expander (Streamlit forbids nesting it in the header expander), and the tests pin
one of the strings (`tests/ui/test_library_pages.py:714`). Fix: reword the three captions to
the plain phrase ("this run's own solve in that model", "the medical-inflation bar's
Medicare-priced solve") and add "see Technical solve details" once.

### AM2 (low): the fork's own acceptance check now asserts the invariant QW-2 breaks

`fork-notes/synthetic/check_library_compare.py:183-187` (the design's step-3 check, recorded
**9/9** in PROGRESS) still requires *every* thresholds entry to sit inside its 5% band
(`e["amount_today_dollars"] <= band * e["boundary_today_dollars"] + 0.01`). QW-2 deliberately
lists crossed cliffs far outside the band (the suite's twin of this invariant was rewritten as
"near or a crossed cliff", `tests/plan/test_thresholds.py:348-357`). The next run of the check
on any plan with a crossed IRMAA tier or ACA cliff will print `FAIL thresholds` even though
the report is behaving as designed. Verified by code reading (the check itself needs a full
synthetic solve and was not re-run here). Fix: mirror the suite's rule in the check — each
entry is either inside its band or a crossed cliff (`side == "over"` and
`kind == "irmaa" or "cliff" in label`).

### AM3 (low): the QW-8 year clamp rewrites stored case inputs at render, silently

`ui/Run_Options.py:44-58` (`_bound_year`) stores the clamped year back into the case on every
render, and `ui/sskeys.py:488-492` (`storeCaseKey`) deliberately does **not** call
`flagModified()` (verified). So opening Run Options in a later calendar year silently moves an
explicit `startRothConversions`/`swapRothConvertersYear`/`acaStartYear` up to the new
"thisyear", rewrites the old "0 = plan start" ACA value to a concrete year, and a subsequent
save bakes the new values into the case and the run's inputs hash (inferred from the save
path's read of these case keys; not exercised in a probe) — with no "modified" mark
and no message. The clamp itself is right (a stored year outside the horizon cannot mean
anything, and Streamlit would otherwise show the bound while the case kept the old value);
the judgment worth the user's eye is the *silent persistence*. Fix: clamp only what the widget
shows and keep the stored value, or call `flagModified()`/flash once when a value is moved
("startRothConversions 2500 is outside this plan: showing 2052").

### AM4 (nit): `method_text` repeats itself for the Medicare-priced companion

For a record with preset `exact_medicare`, `PRESET_PHRASES`' head ("Exact model with Medicare
priced", `src/owlplanner/library/view.py:347`) and the tail ("the exact model with Medicare
premiums priced", `view.py:368-369`) concatenate to *"Exact model with Medicare priced — the
exact model with Medicare premiums priced"* (probe output, verified):

```text
exact_medicare companion: Exact model with Medicare priced — the exact model with Medicare premiums priced
```

Fix: return `head` alone for that companion, or drop the "Exact model with Medicare priced"
phrase from `PRESET_PHRASES` and keep the sentence.

### AM5 (nit): `without_folder` still leaves a folder spelled with the "other" separator

`ui/library_import.py:61-68` tries `form + os.sep` and `form + "/"`, so it cleans a message
that spells the folder as `str(folder)` and continues with either separator (the shape the new
test covers). But when the message spells the *folder itself* with `/` while `folder` holds
`\` (or vice versa) nothing matches (probe, verified):

```text
cannot read HFP.xlsx missing                      <- folder + "\" or "/" : cleaned
cannot read C:/tmp/xyz123/HFP.xlsx missing        <- folder spelled with the other separator: left in
```

The docstring/changelog's "it accepts either separator" overclaims in that corner. In practice
`tempfile.TemporaryDirectory()` and most exception text use the OS spelling, so this is a
corner, not the original bug. Fix: normalize separators in both `message` and `form` before
replacing (e.g. compare on `message.replace("\\", "/")`).

### AM6 (nit): "one set of words" covers the tax/health rows only

AL4's three named labels are unified, but the sources side still speaks two dialects: the
paragraph says *"the taxable (brokerage) accounts \$105,000"* (`SAVINGS_SOURCES`) while the
Sankey node and the new Sources-vs-Uses table say *"Taxable-account withdrawals  \$105,000"*
(`flow_label` falls through to the raw row name) — probe output above, verified. The same
applies to income rows in prose (`INCOME_WORDS`, lowercase) vs nodes (raw names). The work
order only named the three labels, so this is a nit against the "one label map feeds both"
claim, not against the order itself. Fix: render `flows_table` cells (and optionally the
Sankey source nodes) through `SAVINGS_SOURCES`/`INCOME_WORDS`, or add those rows to
`FLOW_WORDS`.

### AM7 (nit): QW-2's noise floor is broader than its wording, and the Run-page caption omits two rules

`thresholds._keep` (`src/owlplanner/thresholds.py:417-429`) applies the \$100 floor to **every**
near row, including near rows of the discrete cliffs and the Enhanced STAR limit; the work
order scoped the filter to "continuous bracket edges whose tax price is < \$100". (Arguably
fine — noise is noise at any kind — but it can hide, say, a just-below IRMAA tier priced under
\$100.) Separately, the caption (`ui/Run.py:84-91`) explains only the \$100 floor: it does not
say that far-crossed cliffs under \$500 (`CROSSING_COST`) are dropped, nor that only the IRMAA
tier the year is *in* is listed (the tiers below it collapse), so a reader comparing the table
to the plan's wording ("IRMAA Tier 1-5") sees fewer rows than expected with no explanation.
Fix: scope the floor to `not _is_cliff(entry)` kinds (or say so), and add the two rules to the
caption.

### AM8 (nit, docs): two stale/broken doc strings

CLAUDE.md's lint note still points at `ui/Run_Options.py:263` ("line 263 since the fork's Q20
edit above it") while the B905 is at line 295 now — the commit updated CLAUDE.md's suite line
but not this one (verified with ruff; PROGRESS has it right). And the commit message itself
lost two dollar amounts where a `$` was interpolated away: "drops continuous edges priced
under **,**" and "a ** ** balance warning" (verified in `git log -1`). Fix: touch up CLAUDE.md
and, if the message matters, note the amounts in PROGRESS (already there).

## Per-QW verdicts

| ID | Verdict | Notes |
|---|---|---|
| QW-1 | **done** | The judgment call (refund both reclassified *and* netted) satisfies "never called income" and keeps the Sankey balanced; defensible. AM6 is the only residue. |
| QW-2 | **done with deviations** | "IRMAA Tier 1-5 crossed" reads as the tier the year is in only (lower crossed tiers collapse) and the \$100 floor also touches non-continuous kinds (AM7); both defensible, the caption should say so. The `affects`/note carries the payment year as ordered. |
| QW-3 | **done with deviations** | "Closest above MAGI" implemented as least-room-left with bracket tops read against taxable income and IRMAA/ACA against MAGI — defensible (it answers "what stops the next dollar of conversion"), and better than the literal wording; "Conversion cap" named only when the year is at the cap (defensible); `conversion_cap` is a plan.json schema addition that old results tolerate (verified). |
| QW-4 | **done** | Percent cells → stored shares, matching Scenario.py exactly (verified both directions). The "type 20 for 20%" warning is in the page text; the Collections source-check test is weak but the conversion is unit-tested. |
| QW-5 | **done** | Gating on `maxSpending` + both split keys is exactly right (the keys exist only with essential lines, verified in `export.py`). |
| QW-6 | **done with deviations** | Plain-English header, codes in the collapsed expander, "model" column dropped — but the tornado's captions keep "exact-LP" (AM1) and AM4's duplication. |
| QW-7 | **done** | AL3 genuinely resolved (before/after run above); the readHFP abort is correct (`readHFP` really returns True/False); the manual separator strip is equivalent to `os.path.basename` for both separators. |
| QW-8 | **done with deviations** | All four sub-items land; the render-time clamp's silent persistence (AM3) is the one judgment call I would let the user overrule. |

## Summary

| Finding | Severity | Description | Evidence |
|---|---|---|---|
| AM1 | Low | QW-6 jargon half-moved: three tornado captions still say "exact LP" beside the plain-English header | code read (`ui/Run.py:758, 764-766, 815-817` vs `:689-700`); verified |
| AM2 | Low | `check_library_compare.py`'s "every entry inside its band" invariant now contradicts QW-2; the 9/9 check will report FAIL | code read + suite's twin invariant rewritten; verified (check not re-run) |
| AM3 | Low | QW-8 clamp silently rewrites stored case years at render, without the modified flag | code read (`Run_Options.py:44-58`, `sskeys.py:488-492`); verified |
| AM4 | Nit | `method_text` says "Exact model with Medicare priced — the exact model with Medicare premiums priced" | probe output; verified |
| AM5 | Nit | `without_folder` misses a folder spelled with the other separator; "accepts either separator" overclaims | probe output; verified |
| AM6 | Nit | Prose vs Sankey/flows-table wording still differs for savings/income rows | probe output; verified |
| AM7 | Nit | \$100 floor broader than the wording; caption omits the \$500 cliff floor and the tier collapse | code read; verified |
| AM8 | Nit (docs) | CLAUDE.md lint line stale (263 vs 295); commit message lost two dollar amounts | ruff output, `git log -1`; verified |

Everything else checked holds: the suite is exactly as claimed (4539/2), lint shows only the
listed upstream items, every new/changed test fails without its change (table above), AL3 and
AL4 are genuinely closed, the untouched consumers (`Collections`' `method_text`, old plan.json
results, `cash_flow_year`) are unaffected, and the two platform fixes are real (the `toml` CRLF
bug reproduced exactly as documented). The user decides what gets folded; the one change I
would insist on first is AM2 (a fork acceptance check that now contradicts the feature).

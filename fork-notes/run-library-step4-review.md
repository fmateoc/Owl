# Run-library build step 4: independent review (2026-11-03)

Reviewed: commit `b27d2838` ("[feat] Run-library step 4: the scenario model and builder") on
branch `claude/run-library-step4`, against `fork-notes/run-library-design.md` sections 2, 6.1-6.4,
7, 11 (the step-4 row and its check), 14.3 (I1), `fork-notes/run-library-review-2.md` (S11),
the top "Unreleased" entry of `fork-notes/CHANGELOG-fork.md`, the last entry of `PROGRESS.md`
("Run-library step 4: the scenario model and builder") and `CLAUDE.md`. Nothing was changed in
the repository; every probe ran from `C:\Users\fmate\AppData\Local\Temp\opencode\`.

## What was run

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest tests\library tests\ui -q -p no:cacheprovider` | **494 passed, 1 skipped** (99.7 s) |
| `.venv\Scripts\python.exe -m pytest -n 4 -q -p no:cacheprovider` (full suite, for the "3970 passed, 2 skipped" claim) | **3970 passed, 2 skipped** (508 s) — the claim holds |
| `.venv\Scripts\python.exe fork-notes\synthetic\check_library_builder.py` | **46/46 scenarios match (39 workbooks cell for cell; case fields and hfp edits included)** |
| `.venv\Scripts\python.exe fork-notes\synthetic\check_library_roundtrip.py` | **39/39 pairs round-trip unchanged** |
| `.venv\Scripts\python.exe -m flake8 src tests ui --max-line-length=120` | only upstream's known E301/E304 in `tests/stochastic/test_spending_bequest_frontier.py` and `test_spending_units.py` (8 lines) |
| `.venv\Scripts\python.exe -m ruff check src tests ui` | exactly upstream's 4 known B905s (`localsearch.py:244`, `tests/plan/test_local_search.py:288`, `tests/plan/test_roth_maturation_losses.py:49`, `ui/Run_Options.py:257`) |

Probes (all under `C:\Users\fmate\AppData\Local\Temp\opencode\`, none in the repo):

- `probe_step4.py` — 22 probes of build/anchors/rent_rows/typing/canonicalize (P2-P24).
- `probe_makecases_regression.py` — the pre-refactor `make_cases.py` (`git show c61326ea:...`)
  and the new one, each run into its own folder and compared.
- `probe_scenario_page.py` — `ui/Scenario.py` under Streamlit's AppTest with a loan purchase
  and anchors (an unusual scenario).
- `probe_pages_save_leak.py` — the `scenario_from_ui` pages-save diff with a base that has events.
- `probe_check_teeth.py` — tampering with `scenarios.json` to prove the acceptance check fails
  on purpose.

Full-suite result: 3970 passed, 2 skipped (matches the commit message and CLAUDE.md exactly).

## Findings

| # | Severity | Finding | Evidence | Design / doc at issue |
|---|---|---|---|---|
| U1 | **high** | **A pages-save leaks the builder's generated case fields into the hand rows, so a deleted event leaves stale, unmarked inputs steering the plan.** `_drop_generated` cleans only the HFP tables; `basic_info.moves`, `school_district`, `aca_settings.aca_start_year`, `fixed_income.social_security_ages` and `solver_options.withSSAges` survive in the saved hand case, and `build()` only writes those paths *when the event exists* — it never removes them. Delete the purchase after any "Edit as new run" save and the new run still moves to White Plains in 2027 with no condo. PROGRESS's "so a deleted event leaves nothing stale behind" is false for case fields. | `casefiles.py:344-388` (`_drop_generated`: tables only); `builder.py:540-549, 565-592` (set-only, never cleared); `probe_pages_save_leak.py`: all four field families leaked and "after deleting the purchase, the rebuilt case still moves: [{'year': 2027, ...}] ... marks it: False"; `probe_step4.py` P9 | §6.3 ("a generated row is regenerated wholesale... hand rows untouched"); PROGRESS.md:5606 |
| U2 | **medium** | **The Scenario page shows phantom changes on a no-edit load and its save defeats the identical-inputs dedupe.** Widget round-trips re-type event numbers (`st.number_input` and DataFrame cells give floats), so `diff_summaries` reports "rent: 4000/mo ... -> 4000.0/mo ..." and "work: ... -> ..." when nothing changed, and a no-edit "Save as a new run" creates a duplicate run instead of "Identical to *bill*". Events are not canonicalized: `_canonical_cell` normalizes integral floats in the HFP tables but nothing does it for event fields, so the inputs hash is type-sensitive where the generated files are not. | AppTest `probe_scenario_page.py` PROBE 1 ("Changes against this run: purchase: condo ... -> condo ...; care: 110000/yr -> 110000.0/yr; ..."; PROBE 5 "Saved as *bill no-edit*" not "Identical to"); `probe_step4.py` P18/P20 (hash differs, generated output equal); `ui/Scenario.py:120,138,217`; `casefiles.py:203-209` | §7 (the computed change summary) and §5 (identical-inputs dedupe, V8); S10/T4 canonical form |
| U3 | **medium** | **An `event:` anchor to a work or rent event raises a raw `KeyError: 'year'`.** `resolve_years` reads `other["year"]`, but work events resolve to `start`/`end` and rent to `start`/`flat_until`. `validate_events` and `parse_year_ref` accept any id, and the page's caption advertises the grammar, so `event:w-bill` is reachable; the page then shows "Cannot build this scenario yet: 'year'". | `builder.py:398-400` vs `builder.py:208-219`; `probe_step4.py` P4/P4b ("RAW KeyError: 'year'" for both) | §6.3a (validation), I1 (anchors), `ui/Scenario.py:73-79` caption |
| U4 | **medium** | **A mixed claim silently abandons the fixed age, on a false premise.** With one claim fixed and one "let Owl choose" the builder sets `withSSAges="optimize"`, which searches *both* ages (the fixed spouse's age becomes only a starting point), while the code and PROGRESS say "Owl's withSSAges is global". Owl's `_parseSSAgesOption` accepts one name **or a list of names**; `withSSAges = ["Noa"]` searches only Noa and holds Ari's age — exactly the mixed case. | `builder.py:586-590`; `plan.py:5391-5409` ("an individual's name or a list of names -> those individuals", and 5432 "An age is held when the individual ... was not selected"); `probe_step4.py` P21; PROGRESS.md:5644 | §6.1 ("claiming ages fixed or 'let Owl choose'" per person), §8.1 R4; PROGRESS "known limits" |
| U5 | **medium** | **A generated row's name identity is cross-table: a hand row named like a generated row in *another* table is silently dropped.** `generated_names` unions all three tables' generated names and then filters every table with it, so buying a home named "home" (the UI's default) drops a hand Budget line named "home"; "hand rows are untouched" is violated. `_drop_generated` in `casefiles.py` does this per table; `builder._merge_tables` does not. | `builder.py:610, 644-647`; `probe_step4.py` P10 (a hand Budget row "condo" vanished once a purchase named "condo" generated a Fixed Assets row); contrast `casefiles.py:355-358` | §6.3 ("hand rows are untouched") |
| U6 | **medium** | **`pay_on` is not validated against the person sheets: a typo silently drops the purchase's big-ticket outflow.** The cell is recorded in provenance and in `by_sheet` under the bad name, but no such sheet is emitted, so the workbook shows the condo bought with no payment — and the markers page still lists the cell. | `builder.py:532-533`; `builder.py:617, 631-638` (sheets come from `names` + hand sheets); `probe_step4.py` P8 ("Zoe sheet present: False" while the marker exists) | §6.2 (the big-ticket outflow) |
| U7 | low | **Year/anchor edge cases are unhandled.** (a) A fractional age anchor silently truncates (`age:Ari:86.5` resolves to the year they turn 86). (b) A purchase year before the plan start indexes `gamma[negative]`, which wraps to a *silently wrong* price (700,000 x 1.02^24). (c) A year past the gamma window, or a case with no `start_date` and no `plan_year`, raises a raw `IndexError`, not a `ScenarioError`. (d) `rent_rows` with `flat_until <= start` and `end < start` emits a backwards row (year 2027, end 2026). | `builder.py:393` (`int(ref["age"])`), `builder.py:493-494`, `builder.py:677-682`, `builder.py:133-134`; `probe_step4.py` P5/P7/P13/P14/P15 | I1; §6.2 (deterministic builder that refuses what it cannot build) |
| U8 | low | **Number typing: the build coerces int ages to floats and the acceptance check cannot see it.** `float(claim["age"])` / `float(current[i])` turn a hand case's `social_security_ages = [67, 70]` into `[67.0, 66.0]`; per T1/V3 the generated TOML keeps those apart (`[67.0, 66.0,]` written). `check_library_builder.compare_case` compares with `!=` and a bool check only, so int-vs-float case differences pass; and a work-variant scenario compares only the cells its `hfp` edits list, so a doubled purchase price in those scenarios passes (grid scenarios catch it via the workbook). | `builder.py:579-581`; `check_library_builder.py:96`; `probe_step4.py` P11/P12; `probe_check_teeth.py` ("doubled price in the events: []" for the work variant, caught only by the workbook path) | §5 (T1/V3), §11 (the step-4 check) |
| U9 | low | **The markers table misreports Debts and Fixed Assets rows.** It looks for `end` and `amount` columns, which those tables do not have: the loan shows "2027-end" (the term is invisible), the Fixed Assets row shows "2027-end" with a blank amount even when `yod` holds a sale year (the ltc-sell case) and `value` holds the price. | `ui/Scenario.py:307-312`; AppTest `probe_scenario_page.py` PROBE 2 (`{'sheet': 'Fixed Assets', ... 'years': '2027-end', "amount ($/yr, today's $)": nan}`) | §6.3 (markers shown to the user) |
| U10 | low | **Work events take no anchors at all**, so "part time the year after Noa's last work year" cannot be said of the work event itself (only of the events that point at it), while CHANGELOG-fork.md, PROGRESS.md and the page's caption say "a year field may name a calendar year or anchor to ..." without that restriction. | `builder.py:352` ("work takes plain calendar years"); `probe_scenario_page.py` (the work table exposes int columns only); `CHANGELOG-fork.md:16-17` | I1 ("builder events take anchors"); §6.1 (work) |
| U11 | low | **Doc drift.** CLAUDE.md's step-4 bullet says "test_scenario +4"; six tests were added (PROGRESS's "+6" is right: `git diff` shows 7 new `def test_` lines, one a rename). `builder.rent_rows`'s docstring promises a `"<name> from <year>"` name parameter the function does not take (the tail is hardcoded "rent from ..."). | `CLAUDE.md:31`; `git diff b27d2838^ b27d2838 -- tests/library/test_scenario.py`; `builder.py:123-145` | CHANGELOG/PROGRESS/CLAUDE consistency |
| U12 | low | **`months_worked` is written into every year of the work span**, not just the last: a span 2026-2028 with "6 months in the last year" writes 6 in 2026 and 2027 too, so a mid-year stop cannot be expressed (the synthetic cases use 12 everywhere and never exercise it). | `builder.py:505-508` + `probe_step4.py` P22 (`{2026: 6, 2027: 6, 2028: 6}`) | §6.1 ("months worked in the last year") |

## Claims checked (verified, worth recording)

- **The step's check passes as claimed:** `check_library_builder.py` reports 46/46 scenarios,
  the 39 workbooks cell for cell, case fields and hfp edits included (ran).
- **`make_cases.py`'s outputs are unchanged by the refactor** — checked independently of the
  new shared row builders: the pre-refactor script (`git show c61326ea:...`, run from a temp
  copy with `ROOT` patched) and the new one produce **39 workbooks cell for cell and
  byte-identical `Case_*.toml`, `condo_grid.json` and `work_variants.json`**; the only new
  file is `scenarios.json` (`probe_makecases_regression.py`).
- **`check_library_roundtrip.py` stays 39/39** through the new `export_case` path (ran).
- **The acceptance check has teeth:** a tampered expected district and a tampered expected wage
  cell are each flagged, and a doubled price is caught by the workbook comparison, while the
  untouched scenarios match (`probe_check_teeth.py`) — with U8's blind spots noted above.
- **`build()` is deterministic and does not mutate its argument** (two builds equal, input deep-
  equal afterwards; `probe_step4.py` P2; `config_to_plan(loadHFP=False)` writes nothing —
  `plan_bridge.py`'s `dirname` only resolves paths).
- **`canonicalize` is idempotent on a v2 document with events, and a v1 document migrates to v2
  and hashes stably** (`probe_step4.py` P17).
- **`gamma[0] == 1` is an Owl invariant** (`rates.gen_gamma_n` starts from `np.ones`), so the
  builder's guard can never fire on a real case — it is harmless belt-and-braces.
- **The T1 save-path claim holds:** `store.save_run` canonicalizes before hashing *and* before
  `export_case` (`store.py:426-431`).
- **Validation is solid where it exists:** unknown kinds, missing/duplicate ids, unknown
  persons, bad months, one purchase/rent/care per scenario, cycles and missing anchor targets
  are refused with `ScenarioError`s (tests plus P6); `_drop_generated` handles DataFrames as
  well as dicts (P19) — `_tables_from_plan` returns DataFrames and both shapes work.
- **Lint is clean but for upstream's known items** exactly as `CLAUDE.md` lists them (ran).
- **Provenance markers** cover generated rows, person cells and case fields as claimed, and the
  workbooks' row order matches the generators' event order (the acceptance check compares row
  order too).

## Open questions for the user

- **Section 5's round-trip guarantee ("re-importing a run's own files gives the same hash") no
  longer holds for v2 scenarios with events** (a re-import is a hand-rows scenario with a
  different hash). PROGRESS lists it under "known limits" and R9's builder badge is the answer
  for old runs, but the design text is now unconditional. Amend §5/§6.3a, or plan an import
  that recovers events (e.g. from provenance markers written beside the run) later?
- **Section 6.2 says `write_hfp` and `case` move into the module** ("moved into a module with
  tests"); only `budget_row`/`rent_rows`/`owner_rows`/`care_row`/`asset_row`/`debt_row` did,
  with a rationale in PROGRESS ("workbook writing and template filling are not builder logic").
  Worth amending the design so the step-4 row reads as built?
- **U1 is the one fix I would require before calling step 4 done.** Generated *case fields*
  need the same treatment as generated rows (drop-then-regenerate in `scenario_from_ui`, or
  provenance-stamped fields kept out of the hand case), otherwise every "delete the purchase"
  edit after a pages-save silently produces a wrong run — and the pages-save is the only place
  to edit balances (the Scenario page itself points there).
- **U4's fix looks small** (`withSSAges = [<the names to search>]`, which Owl already accepts);
  folding it into this step would remove a "known limit" and honor the scenario's fixed ages.
- Not re-run here (claimed green in PROGRESS on this code): `check_library_jobs.py` (5/5) and
  `check_library_compare.py` (9/9).

## Disposition of U1-U12 (2026-11-03, same day; folded on `claude/run-library-step4`)

Every finding checked against the code and the probes above and fixed the same day (the user's
call: fold the review into the step).

| # | Disposition |
|---|---|
| U1 | **Fixed.** `casefiles._drop_generated_case` reverts every generated case field to the base's hand value in `scenario_from_ui`, beside `_drop_generated`'s tables. (The first attempt dropped the fields outright and lost the fallback a claim-less person needs -- Jill's age -- so it reverts rather than removes.) Test: `test_a_pages_save_drops_the_generated_case_fields`, including the U1 probe's rebuild after deleting the purchase. PROGRESS's "a deleted event leaves nothing stale behind" is true now. |
| U2 | **Fixed.** `canonicalize` canonicalizes the events (`_canonical_events`): year fields normalized to refs, every number a canonical cell, keys at their default dropped (`level: "full"`, care's `name`/`essential`, `pay_on: None`, zero growth/commission) -- so a widget's floats and a hand-written JSON are one document, for the change summary and the inputs hash. The page canonicalizes before diffing and saving. Test: the page's no-edit case (no phantom changes; a no-edit save reports "Identical to"). |
| U3 | **Fixed.** An `event:` anchor reads the other event's year field, else a work span's `end`, else a rent's `start` (documented in the grammar). |
| U4 | **Fixed.** A mixed claim generates `withSSAges = [<the free names>]`: `plan._parseSSAgesOption` (checked at plan.py:5391-5409) takes a list of names to search and holds the others' ages. The "known limit" is gone. Tests: `test_one_free_claiming_age_searches_only_that_person`, `test_everyone_free_searches_both`. |
| U5 | **Fixed.** `_merge_tables` filters hand rows by the names generated in their own table only. |
| U6 | **Fixed.** `validate_events` refuses a `pay_on` who is not one of the case's people. |
| U7 | **Fixed.** (a) an age anchor takes whole years; (b) and (c) every resolved year must sit in the plan window (the plan start to the year the last person reaches their life horizon) and `nominal` refuses years outside the inflation path; `_plan_start` raises instead of returning 0; (d) a rent end before its start (and the care and sale equivalents) is refused and `rent_rows` returns no rows for a backwards span. |
| U8 | **Fixed.** `check_library_builder.compare_case` compares leaves with their types (T1/V3), a work variant's whole built workbook is compared against the baseline workbook with its edits overlaid (every generated cell is checked now), and a kept hand age keeps its own type. |
| U9 | **Fixed.** The markers table shows a loan as "2027, 30-year loan" with its amount, and a Fixed Assets row as "2027, sold 2050" or "2027, kept" with its value. |
| U10 | **Doc fix.** The anchors are documented as the rent, purchase and care events' year fields (work spans take plain calendar years): builder's docstring, the Scenario page's caption, CHANGELOG-fork.md. |
| U11 | **Fixed.** CLAUDE.md's test counts; `rent_rows`'s docstring names the tail row as it is built. |
| U12 | **Doc fix (a decision).** `months_worked` is written for every year of its span: the synthetic suite's edit format (`condo_grid.json`, consumed by `run_suite.py` and `work_sweep.py`) writes it that way and the earnings test reads only the year work stops (0 means 12 in a year with wages). Split the span to give one year its own value; the Scenario page's caption says so. Section 6.1's "months worked in the last year" holds at input level. |

Re-run after the fixes: `check_library_builder.py` **46/46** with U8's stricter comparison
(the work variants against the baseline plus their edits), `tests/library` +
`tests/ui/test_scenario_page.py` **303 passed, 1 skipped**, lint clean but for upstream's
known items. Of the open questions below, U1 and U4 are resolved; the two design-text
questions stand for the user.

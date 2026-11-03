# Run-library build step 4: second review (2026-11-03)

Reviewed: branch `claude/run-library-step4` at `3d77fb80` (step 4 `b27d2838`, the U1-U12 fixes
`9b3e5c02`, the design 6.2 amendment), against `fork-notes/run-library-design.md` sections 5,
6.1-6.3 and 7, the first review (`run-library-step4-review.md`, U1-U12 and their disposition)
and the two PROGRESS.md entries. Linux container, Python 3.11, HiGHS. Nothing in `src/`, `ui/`
or `tests/` was changed; the probes are scratch scripts outside the repository, their output is
quoted below.

## What was run

| Command | Result |
|---|---|
| `pytest tests/library tests/ui/test_scenario_page.py -n 4` | **312 passed** (13.6 s) |
| `fork-notes/synthetic/check_library_builder.py` | **46/46** scenarios match |
| `fork-notes/synthetic/check_library_roundtrip.py` (after `make_cases.py`) | **39/39** |
| `flake8` on the step's files (`src/owlplanner/library`, `ui/Scenario.py`, `tests/library`, `tests/ui/test_scenario_page.py`, the two synthetic scripts), repo `.flake8`, flake8 7.4.1 / pycodestyle 2.15.0 | **1 error**: `tests/library/test_builder.py:350:61: E128` (added in `9b3e5c02`) |

Not run: the full suite, `check_library_jobs.py`, `check_library_compare.py`, ruff (not
installed in this container).

## Findings

| # | Severity | Finding | Evidence |
|---|---|---|---|
| X1 | **high** | **Saving from the case pages drops every event of the base run.** `scenario_from_ui(base=...)` strips the generated rows, cells and case fields (`_drop_generated`, `_drop_generated_case`) and then returns `scenario_from_case(...)`, which builds a scenario with no `events` (`casefiles.py:375`; `migrate` adds `events: []`). So "Edit as new run" -> Library page "Save the current case" on any run with events makes a child run with no purchase, no rent, no work, no claims, and their generated output removed too. The first review's pages-save probe (U1) did not show this: it checked the case fields only. No test covers `scenario_from_ui` with a base that has events end to end (`test_a_pages_save_drops_the_generated_case_fields` calls `_drop_generated_case` directly). | Probe: export a `scenarios.json` scenario, load its `Case.toml` + `HFP.xlsx` as the pages do (`config_to_plan`, `config_to_ui`), call `scenario_from_ui(uidic, plan, base=base)`. `noa-part-claim-62`: base events `[work-ari-2026, work-noa-2026, work-noa-part, rent, buy, claim-ari, claim-noa]`, **child events `[]`**; the child's frozen files: Fixed Assets 2 -> 1 rows, Budget 11 -> 7, `social_security_ages [62.0, 62.0] -> [67.0, 67.0]`, `withSSAges 'fixed' -> 'optimize'`. `whiteplains-2029-mortgage`: Debts 2 -> 1, Fixed Assets 2 -> 1, Budget 12 -> 7, `basic_info.moves [{2029, White Plains}] -> None`. |
| X2 | medium | **`_drop_generated` zeroes generated cells and drops generated-name rows instead of restoring the base's hand values** -- U1's class, fixed for case fields only. A work event over a year whose hand cell held wages, or a purchase whose fixed owner-row names (`property tax`, `HOA`, `condo insurance`) match hand Budget rows, loses those hand values at the first pages-save; deleting the event afterwards leaves 0 / no row. It also breaks T1 for such runs: an unedited pages-save is not identical to its base. | Probe (with X1 patched by hand, `child["events"] = base["events"]`): import `Case_ari+noa.toml` + `HFP_ari+noa.xlsx` (hand Ari 2026 wages 168,000; hand Budget has `property tax`, `HOA`, `condo insurance`), add a work event Ari 2026-2027 at 50,000 and a cash purchase. Unedited pages-save: `diff 2 ['hfp.Ari.rows[5][1]: 168000 -> 0', 'hfp.Budget.rows: 10 -> 7 rows']`, hash differs. Delete the work event and build: Ari 2026 wages **0** (hand value was 168,000). `casefiles.py:418` (`= 0`), `:429` (rows dropped). |
| X3 | medium | **`build()` is not deterministic for a case with non-reproducible stochastic rates.** `_gamma` reads `gamma_n` from a fresh `config_to_plan` (`builder.py:468`), which draws new rates each time, so the purchase price in purchase-year dollars (and the rent's flat rows) is a random draw, frozen into the run, unrelated to the inflation path the solve will draw. Section 6.2 and the module docstring say deterministic. | Probe, `queens-2034-cash` with `rates_selection` set to `histochastic` 1970-2000: three builds give Fixed Assets value **1,421,789 / 1,262,691 / 1,227,299**. With `reproducible_rates = true, rate_seed = 1234`: 1,225,802 three times. `historical` 1970-2000: 1,400,279 three times. Options: refuse, use the deterministic mean inflation, or require reproducible rates when events need `gamma`. |
| X4 | medium | **The Scenario page writes closing costs the run did not have, and the change summary hides it.** The widgets default `closing` to 0.03 and `extra` to 0.02 (`ui/Scenario.py:164,166`) where the builder's defaults are 0 (`builder.py:555-556,563`), so an event without those keys (hand-written JSON, a future import) gains them on any save from the page, even with nothing edited. The purchase's words (`scenario.py:208`) omit price, closing, down payment and rate, so the summary reads "condo in 2027, cash -> condo in 2027, cash". The page also does not carry a purchase's `type` or `basis` (no widget), so a save drops them. | AppTest probe: a run whose purchase is `{"kind": "cash"}`, page loaded, nothing edited. Change summary: `purchase: condo in 2027, cash -> condo in 2027, cash`. "Save as a new run" makes a second run (`['bill', 'bill variant']`, not "Identical to"); the 2027 big-ticket item goes from **-724,220 to -745,947**. `type`/`basis` were checked by reading `_assemble` only. |
| X5 | low | **The `event:` text form does not round-trip ids that end in `-<digits>`.** `parse_year_ref` takes the last `+`/`-` followed by digits as the offset (`builder.py:276`), and the suite's own work ids end in a year. A stored anchor to `work-ari-2026` is shown as `event:work-ari-2026` and parsed back as id `work-ari`, offset -2026, so the page says "not buildable" on an unedited load. | `parse_year_ref("event:work-ari-2026")` -> `{'anchor': 'event', 'id': 'work-ari', 'offset': -2026}`. Only the rent, purchase and care year fields go through text. |
| X6 | low | **U3's fix leaves two holes.** (a) An `event:` anchor to a claim event raises a raw `TypeError` (a claim has no year fields, so `main` is None, `builder.py:411`). (b) For a rent with an explicit `end`, `event:rent` resolves to the **end**, not the start that the docstring and the page's caption promise (`other.get("end", ...)` is checked before `start`). | (a) `care.year = event:c-ari+2` -> `RAW TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`. (b) rent 2026-2030 with explicit end, `care.year = event:rent` -> **2030**. |
| X7 | low | **A claim event for one person resets the other person's hand `withSSAges` to fixed.** With no free claim, the builder writes `"fixed"` (`builder.py:624`). It keeps the hand age of a person who has no claim event but not that person's hand "let Owl choose". | Hand case `withSSAges = "optimize"`, one claim event (Ari 67) -> `withSSAges = 'fixed'`, ages `[67.0, 67.0]`: Noa's search is silently dropped. |
| X8 | low | **The page's defaults and its run migration.** (a) Ticking "Buy a home" on a run with no purchase pre-fills the year as `purchase`, which anchors to itself, so the page shows "event years that cannot be resolved ... buy.year" until it is typed over (`ui/Scenario.py:144`). (b) Every run saved before step 4 (schema v1) shows `schema_version: 1 -> 2` as its change on an unedited load (the page diffs the stored document against the migrated one). The rent defaults (2026, flat through 2027, $4,000) and the price ($700,000) are the household's figures hard-coded as defaults. | (a) `builder.build` of a purchase with `year = {"anchor": "purchase"}` -> `ScenarioError: ... buy.year`. (b) `diff_summaries(v1, canonicalize(v1))` -> `['schema_version: 1 -> 2']`. |
| X9 | low | **Lint is not clean as claimed.** | `tests/library/test_builder.py:350:61: E128 continuation line under-indented for visual indent`. |

## Claims checked (verified)

- The step's acceptance check passes as claimed: `check_library_builder.py` 46/46 on Linux;
  `check_library_roundtrip.py` 39/39.
- The library and Scenario-page tests pass on Linux (312; the PROGRESS figure of 303 + 1
  skipped is from Windows and covers a different selection, so the counts are not comparable).
- The builder's owner lines end the year before the sale, which matches Owl: a Fixed Assets row
  is disposed of "at beginning of yod" (`fixedassets.py`, `get_fixed_assets_arrays`), and a
  `yod` of 0 means "kept past the plan".
- U4's list form of `withSSAges` survives the case pages: `ui_bridge._with_ss_ages_to_ui_mode`
  and `owlbridge.genDic` map a list of names to `ssAgesMode`, and back to a name.

## Suggested fixes

- X1: in `scenario_from_ui`, carry the base's events into the result
  (`scenario["events"] = base["events"]` before the final canonicalize), and add an end-to-end
  test: an unedited pages-save of a run with events is identical to its base (T1). With that
  patch alone, X2 still makes the test fail where generated positions overlap hand values.
- X2: restore the base's hand cells and rows (from `base["hfp"]`) instead of zeroing and
  dropping, as `_drop_generated_case` does for case fields.
- X3: see the options in the table; the user's call.
- X4: give the widgets the builder's defaults (or read the defaults from one place), add price,
  closing and financing terms to `_event_words`, and either expose `type`/`basis` or carry
  unknown keys through `_assemble`.
- X5: escape the offset (e.g. `event:<id>@+2`), or match the id against the scenario's ids first.
- X6, X7: small code fixes; X7 needs a rule (keep the hand mode for a person with no claim event).

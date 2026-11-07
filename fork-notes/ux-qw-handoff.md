# Handoff: the ergonomics review's QW-1 to QW-8 (2026-11-07)

**Superseded for the remaining work by `fork-notes/ux-qw-handoff-2.md`** (same day): the user
built QW-1 to QW-8 in parallel on `claude/ui-remediation-qw`, merged into this branch; the
second note reviews that build against this order and orders what remains. This file stays as
the record of the first order.

For the **next session**. The work order for eight "quick wins" from an independent
ergonomics review of the browser UI. The user pasted it into the chat on 2026-11-07, and it is
not committed elsewhere: each item below opens with what the review asked for. The review's
emphasis is ergonomics, what the reader of a page meets, and the work should keep that
emphasis.

The items run in order of what the spouse meets first: QW-2, QW-5, QW-1, QW-4, QW-6, QW-3,
QW-7, QW-8. Earlier decisions are open to revision (user, 2026-11-07). This reopens AL3 and AL4
(`fork-notes/ux-q10-q20-review.md`, left standing when AL1-AL2 were folded) and pulls parts of
the structural items S5, S6 and S9 (`fork-notes/ux-review.md` section 4, "not planned") into
scope, where the items below say so.

Tags, as in `fork-notes/ux-review.md`:

- **[seen]**: observed in the running app by that review (synthetic household, 2026-11-07);
- **[code]**: read in the source at `0770124` for this note and not exercised;
- **[inferred]**: follows from the code, not reproduced. Reproduce it before fixing it.

## Where things stand

- **Branches.** This note is on `claude/upbeat-planck-c731oy` (from `0770124`, which is `main`
  after the three issue drafts were filed). Start the work on a new session branch from
  `origin/main`, or from this branch if `main` does not hold this note yet. Do **not**
  fast-forward `main`: the user decides.
- **Upstream.** `dev` `73dc881` (fetched 2026-11-07), the same as the last merge.
- **Full suite.** Last green run: **4512 passed, 1 skipped** (2026-11-07, Linux, `-n 4`,
  8:59, on `abc473c2`).
- **Models for new strings:** Q1's plain wording and Q2's preset names (`ui/librarypresets.py`).
  Use `\$` for dollars on the pages; `tests/ui/test_ui_dollar_math.py` checks them. Use
  `NumberColumn(format="%d")` for years, never `"plain"`
  (`tests/ui/test_run_charts.py::test_no_page_uses_the_plain_number_format`).

## Decisions for the user, before or during the work

Ask these at the start, one question each with the recommendation; do not settle them alone.

1. **Upstream's own pages and modules.** QW-8.2 (`ui/sskeys.py` `flagCurrentCase`), QW-8.3
   (`ui/Run_Options.py`) and QW-8.4 (`ui/Account_Balances.py`) change upstream code, checked
   against `upstream/dev` `73dc881`. So may QW-7.1's display on Financial Profile.
   - The user's rule from Q10-Q20: a plain defect is changed for everyone, with an issue draft
     and a patch verified on stock `dev`; wording aimed at this household goes in library mode
     only.
   - Recommendation: for everyone, with **one issue draft per item** (the fork's convention:
     one finding per issue), for 8.2, 8.3 and 8.4. The three hold for every user: a marker
     that reads as a warning, a sentinel in a number field, a unit trap. Leave Financial
     Profile's line to upstream: it shows the bare name once QW-7.1 stores one.
2. **QW-2's rules.**
   - (a) Which lines report crossings beyond the 5% band. Recommendation: the IRMAA tiers, the
     marketplace's 400% FPL cliff and the Enhanced STAR limit (the three cliffs). The other
     kinds are ramps or kinks, priced smoothly.
   - (b) The floor below which a near item is folded away. Recommendation: \$100 (today's \$)
     per entry.
   - (c) Ramps with no price (the SS taxability bands). Recommendation: folded with the small
     items.
   - (d) A floor on crossings. Recommendation: none. A crossing is listed with its cost
     whatever the cost is, and consecutive years over the same line are merged into one row.
3. **QW-5's headline.** Recommendation: the Run page leads with the first year's **total**
   spending and its split. Compare, the grid and the tornado keep ranking on the discretionary
   part and say "discretionary" wherever they now say "score".
4. **QW-8.4's threshold.** Recommendation: \$20M per balance (S9's figure; the review said
   \$50M). A balance typed in dollars is caught from \$20,000 up rather than from \$50,000 up,
   and a real balance above \$20M only gets a warning it can ignore.

## The items

These are display, wording, validation and navigation changes. None may change a solve or an
existing run's inputs hash (`BUILDER_VERSION` stays 6), unless the item says so. Two items add
fields to `plan.json` (QW-2, QW-3): the additions are for new solves only, and an older result
must still render, as it does today, with a caption saying a new solve shows more.

### QW-2: *Things to look at* lists the plan's real costs

**Review:** always include years where a cliff (ACA 400% FPL, IRMAA tiers 1-5) is crossed;
filter or de-emphasize edges priced under \$100 (the \$3-\$26 NY recapture rows); label the
IRMAA payment year.

- [seen] (`ux-review.md` 222-233) On the synthetic baseline the list showed four NY-recapture
  rows priced \$3-\$26. It showed neither of the plan's two largest threshold effects:
  - 2027-2028 MAGI of about \$133,000 against the 400% FPL cliff at \$84,202 (today's \$), with
    the full marketplace premium paid (\$21,745 and \$22,689 nominal);
  - about \$6.9k of IRMAA in the 2031 premiums.
- [code] Every kind is gated by `_near` (`src/owlplanner/thresholds.py` 63-64, `NEAR_BAND` =
  5%, the user's call of 2026-11-02, which stays for "near"). The page is `ui/Run.py`
  `_things_to_look_at` (77-105). The block reaches `plan.json` through `cli/formatters.py`
  279.
- **Do, the model side** (`thresholds.py`, at solve time: the cost needs the model's own
  premium and credit functions):
  - A second group of entries, `"group": "over"`, for the kinds of decision 2a, wherever the
    income is above the line beyond the band. Near entries keep `"group": "near"`, and a near
    entry on the over side stays near.
  - **IRMAA:** one entry per tax year, for the **highest** tier the MAGI is above. Its
    `cost_today_dollars` keeps today's meaning, the price of closing the gap: what getting
    back under that tier saves. It is the existing computation of `_irmaa_entries` (107-111)
    with the band dropped. Add `total_today_dollars`: the year's whole surcharge, priced
    with the MAGI just below tier 1. Both are in the premium year's dollars, deflated as
    today's code does.
  - **ACA cliff:** the existing `_aca_entries` computation for ratio 4.0 with the band dropped.
    Its cost is the subsidy lost by being over. Check it against `tx.acaCosts` called directly
    at both MAGIs.
  - **Enhanced STAR:** the same, from `_star_entries`.
  - At the top of the block, `"groups": ["near", "over"]`, so the page can tell a result
    solved before this build (no key) from one with no crossings.
- **Do, the page side** (helpers in `ui/run_charts.py`, pure and tested; `Run.py` only draws):
  - **First table, "Where the plan pays for being over a line":** sorted by cost, with
    consecutive years over the same line merged into one row ("2027-2028: \$49,000 over the
    400% FPL line; the marketplace premium is \$12,xxx more each year", with the figures from
    the entries).
  - **Second table, "Close to a line":** today's entries, with the plain columns below.
  - **Folded:** the entries under decision 2b's floor and the ramps (2c) go into an expander,
    "N smaller items", which keeps the old table.
  - **Columns (review item 3):**
    - Year of income;
    - Line;
    - Where ("\$1,200 under", "\$49,000 over");
    - Costs;
    - Paid in: the `affects` year (IRMAA's premium year, STAR's benefit year), else the
      income year. This replaces "Affects", which reads as a code;
    - Note.
  - **Caption, rewritten in plain words:** the optimizer priced these lines, so being over
    one can be the cheaper choice; the list shows where the money goes, not mistakes.
  - **An older result** (no `groups` key): today's table, plus "Solved before crossings were
    reported: solve again to see them."
- **Tests:**
  - `tests/plan/test_thresholds.py`:
    - a plan far over tier 1 gives exactly one IRMAA over-entry, for its highest tier, with
      the step cost and the total;
    - a plan far over the cliff gives one ACA over-entry, whose cost equals `acaCosts`'
      difference;
    - every existing near test passes unchanged.
  - `tests/ui/test_run_charts.py`: the merge of consecutive years, the floor, the fold, the
    column words, and an older result drawn as before.
- **Check:** solve the synthetic baseline ("Careful") and quote the first table. The
  2027-2028 cliff rows and the 2029→2031 IRMAA row must appear. Their premiums must agree with
  `ux-review.md` 222-228 to the dollar, nominal, with the year's deflator shown.

### QW-5: one spending number the household recognizes

**Review:** show the first year's total spending (\$161,016, the Spending chart's first point)
as the main number, with "\$108,516 discretionary + \$52,500 essential budget" under it.

- [seen] (`ux-review.md` 122, 328-329) The Run page headlined the score, \$108,516 (since Q7
  labelled "First year's discretionary spending"). For the same result, Reports headlines
  *"Yearly spending (today's \$) \$161,016"* (`ui/owlbridge.py` 1589, `plan.g_n[0]`). Nothing
  ties the two together.
- [code] `ui/Run.py` 446-471. The summary carries `discretionary_year1` and
  `essential_year1` when the case has essential budget lines (`src/owlplanner/export.py`
  1052-1059). Net spending is essential plus k × discretionary, so their sum is the year-1
  total (52,500 + 108,516 = 161,016 on the figures above).
- **Do (decision 3):**
  - **`maxSpending` with essential lines:** the first metric is "First year's spending", the
    total. Under it goes "of which \$108,516 discretionary (the part the plan raises or
    lowers) and \$52,500 essential budget lines". The help text says the comparisons rank on
    the discretionary part.
  - **`maxSpending` without essential lines:** the total, labelled the same, with no split.
  - **`maxBequest`:** unchanged (the final bequest leads; the spending is the case's target).
  - **Fallback:** where the two summary keys are missing, read `by_year[0]["spending"]`.
    Check that year 1 is the same in nominal and today's dollars (`rates.gen_gamma_n` starts
    at 1) before relying on it.
  - **Compare, Collections, tornado:** every rendered "score" becomes the score's own words
    (`view.score_label` / `first_number_label`, the Q7 pattern). Grep the pages for the word,
    starting with `ui/Collections.py` 438 (`"score {entry.score:,.0f}"`) and the Compare
    rows' names from `library/compare.py`.
- **Tests:** AppTest on the Run page for a result with essential lines (the total and the
  split shown) and one without; a source test that no page names a number "score" (the
  claiming-age map's *scores file* uploader keeps its word).

### QW-1: one year's money story (reopens AL4)

**Review:** never call the STAR refund "income"; one vocabulary in the paragraph and the
Sankey; the *Health premiums* node kept with one line; a two-column sources / uses table
under the Sankey.

- [seen] (AL4, probe on the synthetic run) *"2031: … and from income, \$29,645 (Social
  Security \$28,931, State and local tax, net refund \$714). Taxes \$2,847: federal income tax
  \$2,847."* This happens in 23 of its 28 years.
- [code] `view.cash_flow_year` moves a negative use to the sources as "…, net refund"
  (`src/owlplanner/library/view.py` 285-290). `ui/run_charts.py` `_source_group` (257-262)
  calls every other source income, and `INCOME_WORDS` (228-230) has no entry for it.
  - The words differ: the paragraph's `TAX_USES` / `PREMIUM_USES` (222-224) against the
    Sankey's node names (the row names: "Gains tax", "ACA premiums") and the *Taxes and
    premiums* chart (`TAX_SERIES` / `PREMIUM_SERIES`, 159-162: "State + local", "Marketplace
    premiums").
  - `sankey_figure` gives a group its own node only with two or more lines (349-354), so in
    the synthetic case *Health premiums* appears only in the year with both marketplace and
    Medicare premiums. *Taxes* likewise disappears in a year with one tax.
- **Do:**
  - **The refund.** A "refunds" source group for the "…, net refund" rows. The paragraph puts
    it in the tax sentence: "Taxes \$2,847: federal income tax \$2,847; state and local, a
    net refund of \$714 (the STAR credit is larger than the tax)".
    - Name STAR only when the run has it: the frozen case has a `school_district` and
      `withSTAR` is not "none" (`_frozen_solver_options` and the Case.toml's `basic_info`).
      Otherwise say "a refundable credit".
    - First confirm by grep that STAR is the only way `st_T_n` goes negative in the fork
      (CLAUDE.md, STAR).
    - In the Sankey the refund stays a source node (a flow cannot be negative), labelled
      "State tax refund (STAR)".
  - **The vocabulary.** One label map used by all three: the paragraph, the Sankey's nodes and
    the *Taxes and premiums* chart: "Federal income tax", "Capital gains tax", "NIIT (3.8%)",
    "Payroll tax", "State and local tax", "Medicare premiums (with IRMAA)", "Marketplace (ACA)
    premiums". `plan.json`'s row names stay as they are (old results, Compare).
  - **The group nodes.** *Taxes* and *Health premiums* always get their node, with one line
    too, so the diagram keeps its shape when the year changes. *Spending* keeps today's rule
    (a group node only for a budget's lines; "Net spending" alone needs none).
  - **The table (S6's table only, not the year card).** Under the Sankey, two columns, Sources
    and Uses, from `run_charts.year_breakdown`: group subtotals (from savings, income,
    refunds; taxes, premiums), lines under them, thousands separators, and the same words as
    above.
- **Tests:** `tests/ui/test_run_charts.py`.
  - A year with a "…, net refund" row: it is never in the income sentence, it is in the tax
    sentence, and the sides still balance. This must fail on today's code; record that.
  - A one-line premium group has its node.
  - The labels match between the paragraph and the Sankey.
  - The table's totals equal the caption's in and out.
- **Check:** `check_library_compare.py` 9/9.

### QW-4: financing in percent, everywhere

**Review:** the Collections financing table takes shares (0.2), Scenario shows percent
(Q19); use percent in both.

- [code] `ui/variant_tables.py` 37 (`FINANCING_COLUMNS`) and `_financing_value` (186-200)
  pass `down`, `closing` and `extra` through as typed, under bare headers
  (`ui/Collections.py` 181-184 configures only `kind`). In the same row, `rate` is in percent
  (Scenario's "Rate (%)", default 6.25, stored as typed: `ui/Scenario.py` 263, 489).
- [code] No range check. `builder` validates only that the numbers are finite (`builder.py`
  421-423), as does `variants.py` 217-219. So `down = 20`, typed as a percent, builds
  `loan = round(price * (1 - 20))` (`builder.py` 972), a negative loan. [inferred] What the
  solve does with it was not run.
- **Do:**
  - The Collections table's headers say their unit: "rate (%)", "term (years)", "down (%)",
    "closing (% of price)", "loan closing (% of loan)". Each is a `NumberColumn` with
    `min_value` / `max_value` (0-100 for the shares). `_financing_value` divides the three
    shares by 100. The scenario keeps shares, so a 20% loan typed on either page stores the
    same value and gives the same inputs hash.
  - One shared range check (in `builder`, called by `variants`'s validation too):
    - down between 0 and 1, closing and extra 0 or more, a positive term and a rate of 0 or
      more;
    - the refusal says it in words: "down payment 2000%: enter a percent between 0 and 100".
    - Builder output does not change, so no `BUILDER_VERSION` bump.
  - A warning, not a refusal, for a rate between 0 and 1 on either page ("0.0625% a year:
    did you mean 6.25%?").
  - Scenario's three percent boxes (`ui/Scenario.py` 267-275) get `min_value=0.0` and
    `max_value=100.0`.
- **Tests:**
  - `tests/ui/test_variant_tables.py`: the existing tests feed shares; they now feed percent.
    The same loan through both pages gives the same scenario.
  - `tests/library/test_builder.py`: a down of 20 is refused with the sentence. This fails on
    today's code; record that.
- **Check:** `check_library_builder.py` 46/46 and `check_library_roundtrip.py` 39/39
  (nothing stored moves).

### QW-6: plain words up top, the technical record one click away

**Review:** replace the raw preset and family codes with plain English; put commit hashes,
"branch-and-bound at gap 1e-5" and "solved under the exact LP" in a collapsed "Technical solve
details" expander; drop the tornado table's "model" column.

- [code] The header (`ui/Run.py` 406-407) prints `view.method_text`
  (`src/owlplanner/library/view.py` 342-352): the raw preset id ("decision",
  "exact_medicare"), the breakpoint method and "Owl <version> (<commit>)". The Result picker
  above it already uses `librarypresets.name` (376). The age-search captions (408-429) speak
  of "branch-and-bound at gap 1e-5". The tornado caption (638-650) and its table (750-762,
  a "model" column on every row) speak of "the exact LP".
- **Do:**
  - **The header:** "Solved 2026-11-07 14:02 with *Careful (~5 min)*" (`librarypresets.name`).
  - **A collapsed `st.expander("Technical details of this solve")`** holding:
    - the preset id;
    - the breakpoint method as recorded;
    - Owl's version and commit;
    - the age-search captions;
    - the solver gap where the record has one.
  - Keep `view.method_text`, which `ui/Collections.py` 438 and tests use. Do the new header in
    `ui/` (`library/` must not import `librarypresets`), and give Collections' member line
    the same plain name.
  - **The tornado:** drop the "model" column.
    - Mark the one bar measured differently (medical inflation, `tornado.MEDICARE_PRESET`)
      with "†" in its label, on the chart's axis and in the table. One footnote under the
      table: "† measured against this run's solve with Medicare premiums priced; the other
      bars use the faster model without them".
    - Rewrite the caption in plain words: one sentence on what a bar is, one on the
      tolerance. The rest goes to the expander or the help text.
- **Tests:** AppTest that the header shows no preset id and holds the expander; the tornado
  table has no "model" column, and the † note appears when a medical bar is present
  (`tests/ui/test_library_pages.py` has the tornado's AppTest).

### QW-3: the brackets table says what stops the conversion

**Review:** instead of tier 1 alone, show the year's active or next IRMAA tier ("IRMAA Tier 2
(\$266,000), crossed (+\$6,884 in 2031)"), and add a "Binding ceiling" column: the threshold
(22% bracket, IRMAA tier 1, ACA 400% FPL, conversion cap) closest above MAGI.

- [code] `ui/run_charts.py` `brackets_table` (128-154) reads only
  `(row.get("irmaa_edges") or [{}])[0]`. The chart has drawn every tier since Q15.
  - The bracket tops are measured on **taxable income**, while IRMAA and the cliff are
    measured on **MAGI** (`brackets.bracket_view`, `src/owlplanner/brackets.py` 81-160).
  - `plan.json` holds the household's conversion only (`cli/formatters.py` 171, 198), not
    each person's.
  - `maxRothConversion` caps each person's conversion in **nominal** dollars every year
    (`plan.py` 4624-4633: `setRange(x, 0, cap)`), and `plan.json` carries no deflator
    (`Run.py` 55-56).
- **Do:**
  - **The IRMAA columns:** replace them with "IRMAA now" (the tier the MAGI is in, "below tier
    1" included), "Next IRMAA tier at" (the amount) and its premium year.
  - **A "Next limit" column, as a sentence:** "IRMAA tier 2: \$38,000 away (2031 premiums)",
    "22% bracket top: \$4,100 away", "conversion cap reached (Ari)", "no conversions before
    2028 (the case's window)". Each line's room is computed on its own measure, and the
    smallest one is named.
    - Call it "Next limit", not "binding": the table cannot know which constraint holds the
      plan.
    - The caption says so: the plan may stop short of the nearest line for another reason
      (state tax, the taxation of SS).
  - **The conversion cap and window,** computed at solve time in `brackets.bracket_view`,
    where the plan knows the cap, the window (`solverOptions`, through
    `u.get_monetary_option`) and the deflator. A row gains `conversion_by_person` (today's \$)
    and `conversion_limit` (`"cap"` with the names, `"window"`, or none). On an older result
    the cap and the window are left out of "Next limit".
  - The amount columns stay numbers. The sentence is its own text column.
- **Tests:** `tests/ui/test_run_charts.py` (the tier now and next, the smallest room on mixed
  measures, an older row) and `tests/plan/test_brackets.py` (the cap reached in a capped
  plan, the window before `startRothConversions`).

### QW-7: after *Open in Owl* and *Edit as new run* (reopens AL3)

**Review:** keep the bare workbook name after Open in Owl ("HFP.xlsx (from White Plains
2029)"); stop *Edit as new run* from switching pages when `readHFP` fails.

- **7.1, the path.** [seen, AL3] After *Open in Owl*, Create Case's confirmation prints the
  run's absolute `inputs/HFP.xlsx` path; Financial Profile's (upstream) line does too.
  - [code] `owlbridge.openCaseFromPlan` (fork, `ui/owlbridge.py` 2386-2389) takes it from
    upstream's `genDic` (2183, `plan.hfpFileName`).
  - [code] `ui_to_config` writes the same key into a downloaded Case.toml's `HFP_file_name`
    (`src/owlplanner/config/ui_bridge.py` 553). Library saves write `HFP.xlsx` themselves
    (`library/casefiles.py` 300, 863).
  - Do: store `Path(hfp).name` in `hfpFileName` and `stHFP` in `openCaseFromPlan`. The plan's
    own `hfpFileName` keeps the path, for its logs.
  - Do: every run's workbook is called `HFP.xlsx`, so the bare name alone tells nothing. The
    fork's `_hfpLoadedText` (`ui/Create_Case.py` 283) shows "HFP.xlsx (from *run name*)" when
    the case came from a run. That is display only: the stored value must stay loadable.
  - Test (`tests/ui/test_open_in_owl.py`): the stored name is bare, and a Case.toml written
    from the pages names `HFP.xlsx`.
- **7.2, a failed read.** [code] `ui/Run.py` 557 ignores `readHFP`'s return.
  - `readHFP` returns False after an `st.error` on a parse failure (`ui/owlbridge.py`
    1395-1399). The branch then sets the run base, flashes "open", marks the pages visited
    and switches page, and the error is lost.
  - Do: on False, delete the case just created (`kz.deleteCurrentCase`, `ui/sskeys.py` 417,
    so a retry does not hit "already exists"), flash the error, and stay on the Run page.
  - Test: a run folder with a damaged `inputs/HFP.xlsx`. This fails on today's code; record
    that.
- **7.3, two runs from one import. [inferred]** Reproduce first.
  - No library code sets `case_name` (a grep of `src/owlplanner/library/` finds none), so
    every run descended from one import carries that import's case name in its frozen
    Case.toml.
  - `sskeys.createCaseFromFile` refuses a case name already in the session (`ui/sskeys.py`
    333-336).
  - So *Edit as new run* on a run, then on its child, in one session, would stop at "Case
    name '…' already exists" and open nothing.
  - If it reproduces: open the case under the run's own name, made unique in the session
    ("<run name> (2)").
  - This also makes QW-8.1's default meaningful.

### QW-8: the smaller traps

**Review:** default the Library save name to "<case> variant"; replace the 🔻 current-case
marker with ● or ✓; bound the Roth conversion years by the plan and replace "ACA start year =
0" with a toggle or this year; warn when a \$k balance exceeds 50,000 (\$50M).

- **8.1, the save name.** [code] `ui/Library.py` 195 defaults *Run name* to the case's name,
  and the store refuses only an empty name.
  - Do: when the case came from a run (`kz.runBase()`), default to "<base run's name>
    variant". Warn, without refusing, when the name equals an existing run's.
  - Streamlit keeps `lib_save_name`'s value once drawn, so the default must follow the case:
    key the widget by the case, or reset it when the case changes.
  - Test: AppTest after *Edit as new run*.
- **8.2, the marker. Decision 1.** [code] `ui/sskeys.py` 1039-1043 appends "🔻" (red, pointing
  down: it reads as a decline or a warning); 188-190 strip it from stored values. Both are
  upstream's (`upstream/dev` 994 and 159-160).
  - Do: " ●" (or "(open)"), and change the strip with it.
  - Test: the strip on the new marker.
- **8.3, sentinels and bounds. Decision 1.** [code] `ui/Run_Options.py` 186-202: "ACA start
  year (0 = plan start, else 4-digit year)", and its help has to warn against typing an
  offset. Roth start and stop (83-103) have `min_value=thisyear` and no upper bound.
  - Do: a toggle, "Marketplace coverage from the plan start". On, it stores 0, the code's
    sentinel (`thresholds.py` 224, `brackets.py` 108, the builder). Off, it shows a year box
    bounded by the plan's first and last years. Roth start and stop get the plan's last year
    as `max_value`.
  - Keep upstream's rule (comment at 89-91): bound the years, never derive a default from the
    horizon.
  - [code] `sskeys.getIntNum` (875-891) passes a stored value to the widget unclamped.
    Check with AppTest what Streamlit 1.66 does with a stored year outside the new bounds (a
    case whose life expectancy was shortened). Clamp before the widget and show a note rather
    than raise.
- **8.4, the unit trap. Decisions 1 and 4.** [code] `ui/Account_Balances.py` 48 and 79:
  the balances are in \$k with no plausibility check.
  - CLAUDE.md's gotcha: balances typed in dollars came back "infeasible" with no other hint.
  - Do: under the inputs, one warning per balance above the threshold: "Ari's taxable accounts:
    60,000 here means \$60 million (amounts are in thousands). If you typed dollars, divide by
    1,000."
  - Test: AppTest with one balance above the threshold and one below.

## Order

1. Decisions 1-4 first.
2. Then the items as listed: QW-2, QW-5, QW-1, QW-4, QW-6, QW-3, QW-7, QW-8 (the reader's
   order, the user's call). One commit per item, in that order, and PROGRESS.md's section
   follows it.

## Setup and driving

As in `fork-notes/ux-q10-q20-handoff.md`, "Setup and driving":

- the synthetic household only, never the real one;
- library mode on localhost;
- Playwright from Node, with that note's helpers;
- no rent-only synthetic workbook;
- Careful takes about 5 minutes per solve in this container;
- never solve the condo case on the classic pages with its own options.

QW-2's check needs a "Careful" solve of the baseline: queue it early.

## Done means

- **Tests.** A test per item. For a defect (QW-1's refund called income, QW-4's negative loan,
  QW-7.2, QW-7.3 if it reproduces), the test fails before the fix: record that in PROGRESS.md.
- **Suites.** `tests/library tests/ui tests/plan/test_thresholds.py tests/plan/test_brackets.py`,
  plus anything touched; then the **full suite** green, with the count and time recorded.
- **Lint.** flake8 and ruff, with only upstream's listed items left.
- **Checks.** `check_library_builder.py` 46/46 and `check_library_roundtrip.py` 39/39 (QW-4);
  `check_library_compare.py` 9/9 (QW-1, QW-5).
- **Re-drive with Playwright** on the synthetic case and quote what the pages now say for each
  item: QW-2's first table, QW-5's headline, QW-1's 2031 paragraph and table, QW-6's header,
  QW-3's "Next limit" column for 2026-2031, QW-7's confirmation line, and QW-8's pages.
- **Issue drafts.** For decision 1's items, in `fork-notes/issue-*.md`, each with a stock
  repro and a patch verified on stock `dev`. **Not filed**: the user files them.
- **Docs:**
  - PROGRESS.md, one section;
  - `fork-notes/CHANGELOG-fork.md`, an entry;
  - CLAUDE.md's "State", a bullet for the branch;
  - `fork-notes/ux-review.md`'s status table: S5, S6 and S9 marked partly done, naming what;
  - `fork-notes/ux-q10-q20-review.md`: AL3 and AL4 marked folded.
- **Commit and stop.** Commit with CONTRIBUTING tags, push the session's branch, **stop and
  report**. The user decides on an independent review and on fast-forwarding `main`.

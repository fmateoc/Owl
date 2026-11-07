# Handoff: the ergonomics quick wins, second pass (2026-11-07)

For the **next session**. Two things were written in parallel on 2026-11-07:

- the first work order for QW-1 to QW-8, `fork-notes/ux-qw-handoff.md` (this branch, `88957ff`);
- an implementation of the same eight items by the user, branch `claude/ui-remediation-qw`
  (`082f9b9`), built from the original review's QW list rather than from that work order. It
  was reviewed independently (`fork-notes/ui-remediation-qw-review.md`, AM1-AM8), and AM1-AM3
  and AM8 were folded (`44c3eec`).

This note reviews the implementation **against the first work order**. Where the two differ,
each difference is judged on its merits, in either direction. It then orders what remains. It
replaces `ux-qw-handoff.md` for the remaining work; that file stays as the record of the first
order.

Tags:

- **[seen]**: in the running app, driven with Playwright on the synthetic household;
- **[ran]**: a script on a real solve of the synthetic household;
- **[probe]**: a script or AppTest on small inputs;
- **[code]**: read, not exercised;
- **[inferred]**: follows from the code, not reproduced.

## Where things stand

- **Branch.** `claude/upbeat-planck-c731oy` holds the first order, the implementation and this
  note. The implementation came in as merge `790364a`: `src`, `ui` and `tests` are identical to
  `claude/ui-remediation-qw` `44c3eec`, and both doc conflicts were kept side by side.
  - Start the next session's branch from this branch: `main` (`0770124`) holds none of it.
  - Do not fast-forward `main`: the user decides.
- **Upstream.** `dev` `73dc881`, unchanged.
- **Suites on the implementation's code (Linux, this session).**
  - Targeted (`tests/library tests/ui tests/plan/test_thresholds.py tests/plan/test_brackets.py`):
    **1048 passed** (72 s).
  - Full suite: **4540 passed, 1 skipped** (11:49, `-n 4`).
  - `check_library_compare.py`: **9/9**, re-run here after AM2's fold (its thresholds
    check reads "4 near a threshold or over a cliff (aca, irmaa)").
  - The implementation recorded 4539 passed / 2 skipped on Windows.
- **Lint.** flake8 and ruff report only upstream's listed items; the B905 in
  `ui/Run_Options.py` is at line 314.
- **The solves used here.**
  - The UX review's baseline (`Case_ari+noa_condo.toml` +
    `HFP_ari+noa_condo_yonkers_2029_cash.xlsx`) was imported into a fresh library and solved
    "Careful" with the implementation's code: 5 min 16 s, then its exact companion.
  - One Quick look was solved with the pre-branch code (`src` as at `0770124`): an "older
    result" for the new pages.
  - The Careful figures match `ux-review.md` 222-228 and 328 to the dollar [ran]:
    - 2027-2028 marketplace premiums \$21,745 and \$22,689 (nominal);
    - 2031 Medicare premiums \$13,158 (nominal);
    - the headline \$161,016 = \$108,516 discretionary + \$52,500 essential.

## The review

### What the implementation did that this order keeps

Judged on its merits and kept, whether or not the first order asked for it:

- **QW-2:**
  - One IRMAA entry per year, for the highest tier the MAGI is above. Its cost is the price of
    getting back under that tier, as the first order asked.
  - The costs are right [ran]. On the Careful solve, `tx.acaCosts` called directly at the MAGI
    and at \$1 under 400% FPL gives \$12,547, \$12,865 and \$4,824 (today's \$, 2027-2029),
    the entries' figures to the dollar. IRMAA tier 2's step for the 2031 premiums is \$3,741
    (today's \$).
  - The IRMAA note names the payment year ("paid in 2031 via the 2-year Medicare lookback").
- **QW-5:**
  - The total comes from `summary["spending_year1"]` (`export.py` 985, `g_n[0]`). That is
    sounder than the first order's `by_year[0]` fallback.
  - The split is shown only under `maxSpending` with both split keys present, so a
    "\$0 essential" split cannot appear.
- **QW-1:**
  - A refund is never called income [ran: 2034 and 2037 of the Careful solve].
  - The Taxes and Health premiums nodes are drawn even with one line.
- **QW-6:** the plain phrase lives in `view.method_text`, so the Collections member line gets
  the same words. The first order put it in `ui/` only. AN8 covers the second list of names
  this created.
- **QW-7.1**, and QW-7.2's "no page switch".
- **QW-8.2:** the ✓ mark [seen: "ari+noa ✓"].
- **QW-8.3:**
  - The Roth years are bounded by the plan.
  - AM3's split: a move up to the lower bound is neutral; a move down to the upper bound flags
    the case.
- **Two fixes beyond either order:**
  - `toml_io.load_toml` normalizes CRLF. It is upstream code with an upstream defect: AN9.
  - `library_import.without_folder` takes either separator (AM5's corner stands).

### Findings AN1-AN11

Prefix AN, after AM. Each finding is set against the first work order, unless it says otherwise.

**AN1 (medium, QW-5): the split under the headline renders as math and is cut off.**

- [seen] On both results, the chip under *First year's total spending* reads
  "108,516 discretionary + 52…", in a green monospace chip.
- The f-string `delta=f"${…} discretionary + ${…} essential budget"` (`ui/Run.py` 485-486)
  holds a `$…$` pair.
  - Streamlit 1.66.1's `delta` "can optionally contain GitHub-flavored Markdown, subject to the
    same limitations described in the `label` parameter" (`streamlit/elements/metric.py`
    169-170), so the pair is drawn as math.
  - The chip then truncates the text.
- `tests/ui/test_ui_dollar_math.py` scans positional arguments and the `help=`, `label=` and
  `placeholder=` keywords, but not `delta=`. So the test passed.

**AN2 (medium, QW-8.3): Run Options announces a change nobody made, in code words, on every
case without an ACA start year.**

- [probe] An AppTest of Run Options on upstream's `Case_jack+jill.toml` (no SLCSP, so the field
  is disabled) and on `Case_riley+casey.toml`, both unmodified, shows: *"A stored year outside
  its field's range was set to the nearest allowed year: acaStartYear 0 → 2026."*
- Why:
  - The module-level `kz.initCaseKey("acaStartYear", 0)` (`ui/Run_Options.py` 75) runs before
    the new `initCaseKey("acaStartYear", thisyear)` (244). So every case without the key stores
    0.
  - The clamp then moves that 0 up to this year.
- Effects:
  - The case now holds 2026, and the next save writes `aca_start_year = 2026` where the file had
    none (`config/ui_bridge.py` 715) [code].
  - The message names a session key, not the field. Q1's rule is no codes in rendered text.

**AN3 (medium, QW-2): one cliff of three missing, an older result not told apart, small rows
dropped from the record.**

- **Enhanced STAR is crossed and not listed** [ran].
  - The 2029 STAR income, \$323,486, is over the \$126,812 limit (nominal). It costs \$1,546
    (today's \$) of the 2031 credit.
  - `_star_entries` still gates on `_near` (`thresholds.py` 331-368), and `_is_cliff` knows
    only IRMAA and the 400% line.
- **No `groups` marker** [seen].
  - The Quick look solved before the branch is drawn under the new caption ("…and every year
    that has crossed one of the big cliffs…").
  - It lists one near row, while that plan is over the cliff in 2027-2029.
- **Small rows removed from `plan.json`, not folded** [ran].
  - The pre-branch `threshold_proximity` on the same solved plan gives the four NY recapture
    rows (\$26.48, \$19.19, \$4.42, \$3.03), which are the UX review's "\$3-\$26", and no
    crossings.
  - The new one gives the four crossings and nothing else.
  - A floor applied at solve time cannot be changed without a re-solve. It also drops near
    cliff rows priced under \$100 (AM7).
  - A crossing costing under \$500 (`CROSSING_COST`) is dropped too. The first order
    recommended no floor on crossings (decision 2d).
- **The ACA note is wrong on an over-the-cliff row** [seen]. It says "the premium is a share of
  MAGI (or the SLCSP, whichever is less)". Over 400% FPL no credit is paid (`tx.acaCosts`
  docstring: from 2026, no subsidy above 400%).
- **The page is the old table plus rows** [seen].
  - Rows are sorted by year; 2027 and 2028 are separate rows.
  - The columns are still "Side", "Amount (\$)" and "Affects" ("-" on the ACA rows).
  - The label is cut to "marketplace subsidy cliff (4…".
- **No year total for IRMAA.** The 2031 surcharge is \$7,136 nominal (\$6,215 today's \$), but
  the row says \$3,741, the step back under tier 2 [ran].

**AN4 (medium, QW-7.2, QW-7.3, QW-8.1): *Edit as new run* and the save name.**

- **7.3 reproduces** [probe].
  - The fixture's child was saved under the import's case name, as a save from the pages does.
  - *Edit as new run* on "bill later" opens the case **bill**.
  - *Edit as new run* on "bill" then stops at *"Case name 'bill' already exists."*, and "bill
    later"'s inputs stay current.
- **7.2 leaves a half-opened case** [probe]. After a damaged `inputs/HFP.xlsx`, the case
  without its workbook stays in the session as the current case. A retry says *"Case name 'bill
  later' already exists."*
- **8.1's default follows the import's name** [seen]. The run "ari+noa condo baseline" opens as
  the case **ari+noa**, and the Library offers **"ari+noa variant"**.
- **8.1's default does not follow the case** [probe].
  - Draw the Library with case "draft" (a run's inputs), then switch to "other".
  - The field still reads "draft variant" while the caption says *"The case **other** will be
    saved as a new run."*

**AN5 (low, QW-3): the brackets table says things it cannot know.**

- **2026's IRMAA cell** [seen] reads *"IRMAA Tier 3 (\$361,420) — crossed (+\$12,802 in
  2028)"*, but nobody is on Medicare in 2028 (both turn 65 in 2029).
  - `brackets.bracket_view` gives IRMAA edges for every premium year inside the plan (143-150).
  - `thresholds._irmaa_entries` skips years with no Medicare months.
- **The "+\$X in YYYY" is the MAGI's overshoot, and reads as a premium.** 2029 says "+\$38,466
  in 2031", where the tier's step is \$3,741 and the year's surcharge \$7,136.
- **A documented "no cap" reads as a cap** [probe]. With `maxRothConversion = -1` ("omit, or
  give a negative value, for no cap", `info/PARAMETERS.md` 359), `conversion_cap` is -2000 and
  every row's *Binding ceiling* reads "Conversion cap (\$-2,000)".
- **The cap is the household's, the plan's is per person** [probe].
  - Under a swap of converters, one person at their own \$50k cap is read against a \$100k
    household cap, so the cap is never named.
  - A year before `startRothConversions` names a bracket.
  - The last-two-years zeroing and the `Roth conv fixed` pins are not read either (`plan.py`
    4674-4704) [code].
- **"Binding" claims more than the table knows** [seen]. 2029, a year with no conversion and a
  MAGI of \$328,025, says "10% bracket (\$24,800)". This is the first order's reason for "Next
  limit".

**AN6 (low, QW-1): the paragraph's tax figure is in neither the Sankey nor the table; three word
sets remain.**

- **The netted figure appears nowhere else** [ran: the page's helpers on the stored
  `plan.json`].
  - 2034 of the Careful solve reads: *"Taxes net of a \$2,934 state and local tax refund took
    \$2,177: Federal income tax \$5,111."*
  - The Sankey under it says "Taxes: \$5,111" and "State and local tax refund: \$2,934".
  - Q17's rule was the paragraph from the very rows the Sankey draws.
- **STAR is not named.** The first order's precondition holds [code]: `plan._finalize_state_tax`
  (8005-8016) subtracts only `st_star_n` as a refundable amount, and personal credits stop at
  zero. So a negative state-and-local row is STAR in the fork.
- **Three word sets.**
  - The *Taxes and premiums* chart keeps "Gains tax", "State + local" and "Marketplace
    premiums" (`TAX_SERIES` / `PREMIUM_SERIES`).
  - The savings and income rows still differ between prose and nodes (AM6).
  - Prose capitalizes mid-sentence: "Taxes \$10,116: Federal income tax \$6,826, State and
    local tax \$3,290".
- **The table is a flat list by size** [seen]. In 2031, "Roth conversions \$76,395" sits
  between "core" and "travel while able", with no group subtotals and no totals.
- **A redundant Spending node.** "Net spending" alone now gets a Spending node over it carrying
  the same number (`_NAMED_USE_GROUPS`). The first order kept today's rule there.

**AN7 (low, QW-4): no range check; a negative mortgage builds.**

- [probe] A Collections cell of 2000 becomes `down = 20.0`. `builder.build` then writes a Debts
  row of **-\$13,672,400**, with no refusal.
- [seen] `term` and `rate` keep bare headers. The help line shows the field codes (`name`,
  `{place}`, `down`, `closing`, `extra`).
- No rate warning; Scenario's boxes are unbounded (`ui/Scenario.py` 267-275) [code].
- With percent input, the likely slip is now 0.2 for 20%.

**AN8 (low, QW-6): two lists of names, an "exact" claim, the tornado's codes.**

- **Two lists of preset names, kept in step by hand:** `view.PRESET_PHRASES` (new) and
  `ui/librarypresets.NAMES`.
- **"Careful — exact tax & Medicare optimization" for a local search.** Compare judges local
  search by the 1% band, so "exact optimization" promises more than the comparison grants.
- **AM4 stands:** "Exact model with Medicare priced — the exact model with Medicare premiums
  priced".
- **The tornado** [seen].
  - It lost its "model" column, but the medical bar has no †.
  - The mover notes in its caption (`ui/Run.py` 691) carry codes: "medical_inflation_excess",
    "(withMedicare = optimize)", "aca_settings.slcsp_annual" and
    "rates_selection.obbba_expiration_year = 2032".

**AN9 (low, the first order's decision 1): upstream code changed with no issue draft.**

- The files are `ui/sskeys.py` (the marker), `ui/Run_Options.py` (bounds, ACA),
  `ui/Account_Balances.py` (the warning), `ui/Documentation.py` and
  `src/owlplanner/config/toml_io.py`.
- **The last is a real upstream defect, reproduced on stock `dev` `73dc881`** [probe].
  - `load_toml` of `examples/Case_jack+jill.toml` with CRLF line endings, from a `StringIO` or a
    `BytesIO`, returns `['case_name']`. From a path it returns 11 keys.
  - The upload path is `ui/Create_Case.py` 106 (`StringIO(file.read().decode("utf-8"))`). Stock
    Create Case then says *"Failed to parse case file: 'basic_info'"*.
- **The trigger is a `"""` string.** Under CRLF, `toml` 0.10.2 drops it and every key after it.
  A file without one loads whole, as the synthetic case does.
- **Why it reaches users.** Upstream's `.gitattributes` covers `*.sh` only, so a Git-for-Windows
  checkout (`core.autocrlf` on by default) gets CRLF examples; 14 of the 19 hold a `"""`
  string. The implementation's note ("silently kept only the first key") holds for such files,
  not for every CRLF file.

**AN10 (nit, pre-existing): "None" in the brackets table.** [seen] The table's "400% FPL" shows
"None" in the years with no marketplace line. The same conversion is on `0770124`
(`brackets_table`), so ff22f88's "empty cells empty" does not hold for a float NaN in
Streamlit 1.66.

**AN11 (nit, QW-8.4): the warning's wording and threshold.**

- [seen] *"Read as \$50M or more (the fields are \$k): Ari's taxable \$60,000k. If these are
  dollars rather than thousands, divide by 1,000."*
- "\$60,000k" leaves the reader to do the conversion the warning is about.
- The threshold is \$50M; the first order recommended \$20M (its decision 4, never asked).

AM5 stands. AM7 is settled by QW-2's page-side fold below.

### Per item

| Item | First order | Built | Verdict |
|---|---|---|---|
| QW-2 | crossings of three cliffs with `group`/`groups` and totals; two tables, merged years, a fold, plain columns | IRMAA and the 400% line, wherever they sit; floors at solve time; old table | model half done (STAR, markers, totals missing); page half not done (AN3) |
| QW-5 | total + split; "score" worded elsewhere | total + split as a delta chip | split unreadable (AN1); wording elsewhere not done |
| QW-1 | refund in the tax sentence, STAR named, one map for three views, grouped table | refund netted, two views share words, flat table | half done (AN6) |
| QW-4 | percent cells, shared range check, warnings, bounds | percent cells | range check missing (AN7) |
| QW-6 | plain header, expander, † on the tornado | plain header, expander, column dropped | † and notes missing; naming (AN8) |
| QW-3 | "Next limit", per-person cap and window | one tier text column, "Binding ceiling", household cap | wording and cap defects (AN5) |
| QW-7 | bare name, abort and delete, unique case names | bare name, abort | 7.2 half, 7.3 not done (AN4) |
| QW-8 | run-name default, marker, toggle, \$20M | case-name default, ✓, year default, \$50M | 8.1 and 8.3 defects (AN2, AN4); drafts missing (AN9) |

## Decisions for the user, before the work

Ask each with its recommendation; do not settle them alone.

1. **Upstream drafts** (the user's rule from Q10-Q20: a plain defect is changed for everyone,
   with an issue draft and a patch verified on stock `dev`).
   - Recommendation: one draft each for
     - the CRLF upload (AN9: a defect with a stock repro, the strongest of the four);
     - QW-8.3 (year fields without an upper bound, the "0 = plan start" sentinel);
     - QW-8.4 (the \$k unit trap).
   - QW-8.2's marker is cosmetic: a draft only if the user wants it.
   - The code is already changed in the fork for all four; the drafts carry stock-`dev` patches.
2. **QW-2's rules, given what was built.**
   - (a) The cliffs that report crossings. Recommendation: IRMAA, the 400% FPL line **and the
     Enhanced STAR limit** (AN3: \$1,546 on the baseline).
   - (b) Where the floor lives. Recommendation: on the page. Every entry stays in `plan.json`,
     and entries under \$100 (today's \$, crossings and near rows alike) fold into "N smaller
     items" rather than being dropped at solve time.
   - (c) Ramps (the SS taxability bands). Recommendation: in the fold.
   - (d) A floor on crossings. Recommendation: none; `CROSSING_COST` goes. A cheap crossing
     folds with the small items.
3. **QW-5's wording elsewhere** (the first order's decision 3, second half, not done).
   Recommendation: Compare, the grid and the tornado say "discretionary" (the score's own
   words) wherever they now say "score".
4. **QW-8.4's threshold.** \$50M as built, or \$20M. Recommendation: \$20M. Dollars typed for a
   \$20,000-\$49,999 balance are caught, and a real balance above \$20M only gets a warning it
   can ignore.
5. **QW-8.3's ACA start year.** Built: a year field defaulting to this year, storing this year.
   First order: a toggle, "Marketplace coverage from the plan start", storing 0.
   - Recommendation: the toggle.
   - Evidence: AN2's message on every case without the key, and saved files changing value with
     no change in meaning.
6. **QW-1's tax sentence.** Built: "Taxes net of a \$2,934 … refund took \$2,177: …". First
   order: "Taxes \$5,111: federal income tax \$5,111; state and local, a net refund of
   \$2,934 (the STAR credit is larger than the tax)".
   - Recommendation: the first order's form.
   - Reason: its figures are the Sankey's (AN6).

## The work

The reader's order as before: QW-2, QW-5, QW-1, QW-4, QW-6, QW-3, QW-7, QW-8, then the new
items. None may change a solve or an existing run's inputs hash (`BUILDER_VERSION` stays 6).
`plan.json` additions are for new solves; an older result must still render, with a caption
saying a new solve shows more.

### QW-2: finish the model side, build the page side

- **Model** (`src/owlplanner/thresholds.py`):
  - Each entry carries `"group": "near"` or `"over"`; the block carries
    `"groups": ["near", "over"]`.
  - `_keep` (decision 2b-d):
    - near rows return to the pre-branch rule: priced above \$0.005, or a ramp;
    - every crossing of the three cliffs is kept;
    - `SMALL_PRICE` and `CROSSING_COST` leave the module; the floor is the page's.
  - Enhanced STAR over-entries wherever the year sits (`_star_entries`; `_is_cliff` takes the
    kind). The cost is `implied_credit`'s difference, as today.
  - `total_today_dollars` on IRMAA entries: the year's whole surcharge, against the MAGI just
    under tier 1, deflated as `cost_today_dollars` is.
  - The ACA note on an over row says that above 400% FPL no credit is paid. Use the model's own
    words.
- **Page** (helpers in `ui/run_charts.py`, pure and tested; `ui/Run.py` draws). As the first
  order, unchanged:
  - two tables, "Where the plan pays for being over a line" (sorted by cost, consecutive years
    over the same line merged, the cost shown as a range when it differs) and "Close to a line";
  - the fold "N smaller items";
  - the columns Year of income, Line, Where, Costs, Paid in, Note;
  - the caption in plain words;
  - the older-result caption, keyed on `groups`.
  - Widen or wrap the Line column, so "marketplace subsidy cliff (400% FPL)" is not cut.
- **Tests:**
  - the first order's list;
  - one STAR over-entry for a plan far over the limit, its cost `implied_credit`'s difference;
  - `group`/`groups` present;
  - an older result (no `groups`) drawn with the old caption, plus the "solve again" line;
  - the fold holds what the floor removes;
  - `TestCrossedCliffs` and the \$100 test move to the page helpers.
- **Check:** the Careful baseline. The first table holds:
  - the 2027-2029 cliff rows;
  - "2029 → 2031 premiums, IRMAA tier 2" with the \$3,741 step and the \$7,136 nominal year
    total;
  - the 2029 → 2031 Enhanced STAR row (\$1,546).

  The fold holds the four recapture rows. Quote it, nominal with the deflator shown.

### QW-5: make the split readable, then the words

- **AN1.** Take the split out of `delta`. Put it on its own line under the metrics row, with
  `\$` escaped; or in `delta_description`, but only if Playwright shows it whole and with its
  dollars.
- Extend `tests/ui/test_ui_dollar_math.py` to the `delta=`, `delta_description=` and `value=`
  keywords. It must fail on today's code: record that.
- The caption under the row: "first year's discretionary spending (\$/yr, today's) (108,516) is
  the score" starts lower-case and doubles its parentheses; reword it.
- Decision 3: the pages' "score" words, as in the first order (rendered strings found by a grep
  for "score" on this branch:
  - `ui/Collections.py` 70, 117, 367, 380-381, 398, 403, 445;
  - `library/compare.py` 143, 179, 184, 316, 326;
  - `library/grid.py` 317;
  - `library/tornado.py` 463;
  - `ui/Run.py` 512, 657;
  - the claiming-age map's *scores file* keeps its word).
- **Tests:**
  - AppTest that the split's text is on the page with its dollars;
  - the source test above;
  - the first order's "no page names a number score".

### QW-1: the tax sentence, STAR, one word map, the grouped table

- **Decision 6.** The tax sentence uses the Sankey's figures. The refund is its own clause:
  "state and local, a net refund of \$2,934 (the STAR credit is larger than the tax)".
  - Name STAR when the frozen case has a `school_district` and `withSTAR` is not "none";
    otherwise "a refundable credit".
  - The Sankey's source node reads "State tax refund (STAR)" on the same rule.
- **One label map** for the paragraph, the Sankey and the *Taxes and premiums* chart. Build
  `TAX_SERIES` and `PREMIUM_SERIES` from it, and cover the savings and income rows too (AM6).
  Prose takes the same words in lower case.
- **The table** under the Sankey, as the first order asked (S6's table):
  - group subtotals with their lines under them;
  - a totals line equal to the caption's in and out;
  - the same words as the paragraph.
- **The Spending node:** a group node only for a budget's lines; "Net spending" alone needs none.
  Taxes and Health premiums keep the built rule.
- **Tests** (`tests/ui/test_run_charts.py`):
  - every amount the paragraph names for a group is a node value of the Sankey. This must fail
    on today's code for a refund year: record that;
  - STAR named only with a district;
  - the chart's series names come from the map;
  - the table's totals equal the caption's.
- **Check:** `check_library_compare.py` 9/9 (9/9 on the build, this session).

### QW-4: the range check, the warnings, the headers

- **One range check in `builder`, called by `variants`'s validation too:**
  - down between 0 and 1, closing and extra 0 or more, a positive term, a rate of 0 or more;
  - the refusal in words: "down payment 2000%: enter a percent between 0 and 100".
  - Builder output does not change.
- **Warnings, not refusals, on both pages:**
  - a rate between 0 and 1 ("0.0625% a year: did you mean 6.25%?");
  - a down payment between 0 and 1 percent ("0.2% down: did you mean 20%?").
- **Headers and bounds:**
  - "term (years)", "rate (%)";
  - `min_value`/`max_value` on the Collections number columns and on Scenario's three percent
    boxes;
  - the help line in words, without the field codes.
- **Tests:**
  - `tests/library/test_builder.py`: a down of 20 (a share) is refused with the sentence. It
    must fail on today's code: record that (AN7's -\$13,672,400);
  - the warnings;
  - the same loan through both pages gives the same scenario.
- **Checks:** `check_library_builder.py` 46/46, `check_library_roundtrip.py` 39/39.

### QW-6: one list of names, honest words, the tornado

- **One list of plain preset names** in `library/` (for example `library/presets.py`).
  - `ui/librarypresets.NAMES` builds on it, adding the time hints; `view.method_text` reads it.
  - A test that every preset in `PRESETS` and `SOLVE_PRESETS` has a name.
- **The method words.** No "exact … optimization" for a local search. For example:
  - loop: "the fast approximate method";
  - local search: "taxes and premiums priced exactly, the plan found by a local search";
  - proved: "…, proved optimal within its gap".

  Fix AM4's repetition.
- **The tornado:**
  - "†" on the medical-inflation bar's label, on the chart's axis and in the table, with one
    footnote under the table (the first order's wording);
  - the mover notes in plain words, with their codes moved into the *Technical solve details*
    expander or the help.
- **Nit:** the expander's sensitivity line only when sensitivity results exist.
- **Tests:**
  - the header holds no preset id;
  - the † and its note when a medical bar is present;
  - no caption carries a dotted config path or `withX =`.

### QW-3: correct the cells, then "Next limit"

- **Model** (`brackets.bracket_view`, new solves):
  - IRMAA edges only for a premium year in which someone has Medicare months (as
    `_irmaa_entries`); otherwise `"medicare_in_premium_year": false`.
  - `conversion_by_person` (today's \$).
  - `conversion_limit` per person: `"cap"`, `"window"` (before `startRothConversions` or from
    `stopRothConversions`), `"last years"`, `"excluded"`, `"pinned"`, or none.
  - The cap is per person, and `None` when `maxRothConversion` is absent **or negative**.
- **Page:**
  - Keep the built single IRMAA text column (compact, readable). Correct its words:
    - "tier 2 (\$38,466 over its \$289,559 edge): 2031 premiums";
    - "below tier 1 by \$97,333: 2029 premiums";
    - "no Medicare premiums in 2028".
  - For an older row without the flag, judge Medicare from the row's `ages` (+2 years, 65 or
    more), or say nothing.
  - Never put the overshoot where a premium is expected.
  - Rename *Binding ceiling* to *Next limit*, as a sentence: "IRMAA tier 2: \$38,000 away (2031
    premiums)", "conversion cap reached (Ari)", "no conversions before 2028 (the case's
    window)". Add the first order's caption (the plan may stop short for another reason).
- **Tests:**
  - a negative cap is no cap (it must fail on today's code: record that);
  - a swap with one person at their cap;
  - a year before the window;
  - a premium year with no Medicare;
  - an older row.

### QW-7: finish *Edit as new run*

- **7.2:** on a failed `readHFP`, also delete the case just created (`kz.deleteCurrentCase`,
  `ui/sskeys.py` 421).
  - Test: a retry after a damaged workbook opens nothing and says why, without "already
    exists". It must fail on today's code: record that.
- **7.3:** open the case under the run's own name, made unique in the session ("<run name>
  (2)").
  - One helper, shared with *Open in Owl*'s naming (`ui/Run.py` 577).
  - Test: *Edit as new run* on a run and then on its child, in one session, opens both. It must
    fail on today's code: record that (AN4's probe is the recipe).
- **7.1 (low):** Create Case's `_hfpLoadedText` (`ui/Create_Case.py` 283) shows "HFP.xlsx (from
  *run name*)" for a run's case. Display only.

### QW-8: the save name, the year fields, the warning

- **8.1:**
  - Default to "<base run's name> variant". After 7.3 that is also the case's name; read the
    run's name through `kz.runBase()`.
  - The default must follow the case: key the widget by the case, or reset it on a change.
  - Warn, without refusing, when the name equals an existing run's.
  - Test: AN4's switch probe, which must fail on today's code: record that.
- **8.3** (decision 5): the toggle storing 0.
  - The clamp's message names the field, not the key: "Year to stop considering Roth
    conversions: 2500 is past the plan's last year, 2053; shown as 2053".
  - The sentinel 0 never produces a message.
  - The ACA year box (toggle off) is bounded by the plan's first and last years.
  - Test: an unmodified upstream example shows no message and keeps `acaStartYear == 0`. It
    must fail on today's code: record that.
- **8.4** (decision 4): the threshold, and the first order's wording ("Ari's taxable accounts:
  60,000 here means \$60 million (amounts are in thousands). If you typed dollars, divide by
  1,000.").
- **8.2:** keep the ✓.

### New items

- **N1, the CRLF upload draft** (decision 1, AN9): `fork-notes/issue-crlf-upload.md`.
  - A stock repro: `load_toml(StringIO(crlf_text))` on `examples/Case_jack+jill.toml`, and
    Create Case's message.
  - A patch: the fork's `_lf` in `load_toml`'s two branches, verified on stock `dev`.
  - Mention `.gitattributes` as a second option for upstream. **Not filed.**
- **N2, AN10's "None" cells.** Find what Streamlit 1.66 draws empty (a nullable `Float64` with
  `pd.NA`, or a text column with ""), check it with Playwright, and test it.
- **N3 (nit), AM5:** compare separators normalized in `without_folder`.
- **N4, the three upstream drafts** of decision 1 (8.3, 8.4, and 8.2 if wanted). Each needs a
  stock repro and a patch verified on stock `dev`. **Not filed.**

## Order

1. Decisions 1-6 first.
2. Then QW-2, QW-5, QW-1, QW-4, QW-6, QW-3, QW-7, QW-8, N1-N4: one commit per item, and
   PROGRESS.md's section follows the same order.

## Setup and driving

As in `fork-notes/ux-q10-q20-handoff.md`, "Setup and driving", plus what this session used:

- The synthetic household only; library mode on localhost (`OWL_LIBRARY_DIR`,
  `--server.address=localhost`).
- Queue the Careful solve early: about 5 min 16 s here. Import the baseline and enqueue it
  through `Library.save_run` + `JobManager.enqueue` before the server starts; the server's
  ticker then runs it.
- An older result: solve one Quick look with `PYTHONPATH` pointing at a worktree of `0770124`
  (`JobRecord.create` + `worker.run_job`, as `check_library_compare.py` `_solve` does).
- Tables drawn by `st.dataframe` are canvas: read their content through the helpers
  (`run_charts.*` on the stored `plan.json`) and check the drawing on a screenshot.
- AppTest recipes for AN2 and AN4 are in this note's findings: render Run Options with an
  example case's `config_to_ui`; use the `library` fixture of `tests/ui/test_library_pages.py`
  with the child saved under the import's case name.

## Done means

- **Tests.** A test per item. For each defect (AN1-AN5, AN7, the QW-1 figure test), the test
  fails before the fix: record that in PROGRESS.md.
- **Suites.** `tests/library tests/ui tests/plan/test_thresholds.py tests/plan/test_brackets.py`,
  plus anything touched; then the **full suite** green, with the count and time recorded.
- **Lint.** flake8 and ruff, with only upstream's listed items left.
- **Checks.** `check_library_builder.py` 46/46, `check_library_roundtrip.py` 39/39,
  `check_library_compare.py` 9/9.
- **Re-drive with Playwright** on the synthetic case, and quote what the pages now say:
  - QW-2's two tables and the fold;
  - QW-5's headline and split;
  - QW-1's 2034 paragraph and table;
  - QW-6's header and the tornado caption;
  - QW-3's IRMAA and *Next limit* cells for 2026-2031;
  - QW-7's two edits in one session;
  - QW-8's Run Options on an unmodified example, the save name after a case switch, and the
    balance warning.
- **Issue drafts** N1 and N4, in `fork-notes/issue-*.md`. **Not filed**: the user files them.
- **Docs:**
  - PROGRESS.md, one section;
  - `fork-notes/CHANGELOG-fork.md`, an entry;
  - CLAUDE.md's "State", a bullet for the branch;
  - `fork-notes/ux-review.md`'s status table (S5, S6 and S9 partly done, naming what);
  - `fork-notes/ux-q10-q20-review.md` (AL3 and AL4 folded);
  - `fork-notes/ui-remediation-qw-review.md` (AM4-AM7: which item closed each).
- **Commit and stop.** Commit with CONTRIBUTING tags, push the session's branch, **stop and
  report**. The user decides on an independent review and on fast-forwarding `main`.

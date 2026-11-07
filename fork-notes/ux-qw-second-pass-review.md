# Ergonomics quick wins, second pass: independent review (2026-11-07)

Branch `claude/upbeat-planck-c731oy` at `d64ec67`: the second pass of QW-1-QW-8 and N1-N4
(`0aa42b3..d64ec67`), built against `fork-notes/ux-qw-handoff-2.md`. Findings are prefixed
AO (after AN). Report only: nothing in `src`, `ui` or `tests` changed.

Tags, as in the work order: **[seen]** Playwright on the running app; **[ran]** a script on a
real solve of the synthetic household; **[probe]** a script or AppTest on small inputs;
**[code]** read, not exercised; **[inferred]** follows from the code, not reproduced.

## Summary

- One **medium** finding (AO1): QW-2's page puts a cliff crossed by less than 5% of its line in
  *Close to a line*, so *Where the plan pays for being over a line* can omit the costliest
  crossings, split one run of years across both tables, or say no year is over a line while
  the next table lists one. It follows the work order's own definition of the groups, so it is
  a defect of the order, faithfully built. It occurs on real solves: 3 of 10 Quick looks of the
  baseline with the taxable balances moved.
- One **low** finding (AO2) and one **low/nit** (AO3); five nits (AO4-AO8).
- Everything else checked holds (below), including the three issue drafts, which reproduce
  exactly on stock `dev` `73dc8815`.

## What was run

| What | Result |
|---|---|
| Targeted suites (`tests/library tests/ui tests/plan/test_thresholds.py tests/plan/test_brackets.py`) on `d64ec67` | **1103 passed** (78 s), as PROGRESS.md says |
| Full suite on `d64ec67` (`-n 4`) | see "Full suite" at the end |
| `flake8 src tests ui --max-line-length=120`, `ruff check src tests ui` | only upstream's listed items; ruff's B905 in `ui/Run_Options.py` at line 340, as CLAUDE.md says |
| QW-2's `test_thresholds.py` at `0aa42b3` on the build's code (`686521e`, worktree, `PYTHONPATH` set; the new `GROUPS` import stubbed, since the build lacks it) | **10 failed, 21 passed**: the "10 fail on the build" claim holds |
| N1, N4: the three repro scripts on a stock `dev` `73dc8815` worktree, then each patch applied | output identical to the drafts' (below) |
| `make_cases.py`, then Quick looks of the UX review's baseline (`Case_ari+noa_condo.toml` + `HFP_ari+noa_condo_yonkers_2029_cash.xlsx`) and of 10 variants with each taxable balance moved by -300 to +500 ($k), through `JobRecord.create` + `worker.run_job` in a scratch library | about 3 s each; the threshold entries, `run_charts.threshold_parts`, `brackets_table`, `year_summary` and `sankey_figure` read from their `plan.json` |
| Playwright (Node `playwright`, the pre-installed Chromium) on the scratch library, Run page of variant "v-200" | screenshot quoted in AO1 |

## Findings

### AO1 (medium, QW-2): a cliff crossed inside the 5% band is filed under "Close to a line"

**What happens.** `thresholds._irmaa_entries`, `_aca_entries` and `_star_entries` mark an entry
`group="near"` whenever `_near(distance, edge)` holds, on either side of the line, and `"over"`
only beyond the band. `run_charts.threshold_parts` then draws "over" entries under *Where the
plan pays for being over a line* and "near" ones under *Close to a line*. So a year that is
**over** the 400% FPL cliff, an IRMAA tier or the Enhanced STAR limit by less than 5% of the
line goes to the second table, although it pays the full step.

**On real solves [ran].** 10 Quick looks of the baseline with each taxable balance moved:

| Variant (taxable, $k each) | *Where the plan pays...* | *Close to a line* |
|---|---|---|
| -200 | 2029, 400% FPL cliff, \$76,979 over, **\$4,824** | 2027, 400% FPL cliff, \$2,399 over, **\$12,547**; 2028, 400% FPL cliff, \$3,852 over, **\$12,864** |
| +100 | 2027 Enhanced STAR, \$7,359 over, \$1,570; 2029 Enhanced STAR, \$250,411 over, \$1,546 (two rows) | 2028 Enhanced STAR, \$145 over, \$1,558 |
| +500 | 2027 IRMAA tier 2, \$25,805 over, \$1,513; 2029 IRMAA tier 4, \$217,760 over, \$3,739 (and the cliff and STAR rows) | 2028 IRMAA tier 1, \$10,402 over, \$2,438 (whole year \$2,438) |

The other seven variants have no such entry.

**On the page [seen]** (variant -200, 1500 px wide): under *Where the plan pays for being over a
line* and its caption "... consecutive years over the same line are one row, the largest cost
first", the table holds one row, 2029 at \$4,824. The 2027 row (\$12,547) is the first row of
*Close to a line*.

**The empty case [probe]** (AppTest of `Run.py` on the `library` fixture of
`tests/ui/test_library_pages.py`, `plan.json`'s thresholds replaced by a single 400% FPL entry
\$2,000 over, cost \$11,800, `group: "near"`). The page reads, in order:

- *Where the plan pays for being over a line*: "No year's income is over an IRMAA tier, the
  marketplace's 400% FPL line or the Enhanced STAR limit."
- *Close to a line*: "marketplace subsidy cliff (400% FPL) | \$2,000 over | \$11,800".

**Three effects.**

- The costliest crossings can sit outside the table whose caption says it lists them, largest
  first.
- One run of consecutive years over the same line is split across the two tables (-200's
  2027-2029). It can also be split into three rows (+100's STAR 2027 / 2028 / 2029), where
  QW-2 asked for one merged row.
- With no crossing beyond the band, the first table states that no year is over a line, and
  the next table contradicts it.

**Where it comes from.** The work order defines the groups this way ("near: inside the band, on
either side"; "over: above one of the three discrete cliffs beyond the band"). The build
follows it, and its tests encode it (`tests/plan/test_thresholds.py` asserts
`e["group"] == ("near" if near else "over")`). `check_library_compare.py`'s check 7 accepts it
as well. The order's own check (the Careful baseline) has no crossing inside a band, so it did
not show.

**Suggested fix (for the user's call).**

- A crossing of one of the three cliffs (`side == "over"`: the highest IRMAA tier crossed, the
  400% line, the Enhanced STAR limit) is `"over"` wherever it sits.
- `"near"` keeps the under side of those lines and every continuous edge (brackets, recapture,
  NIIT, the ramps).
- Results already solved can be regrouped on the page: `side` and `kind`/`label` are in every
  entry.
- A test with a crossing inside the band, at the model and on the page.

### AO2 (low, QW-1): the paragraph's "from savings" total is on no Sankey node

- [ran] The 10 Quick looks give 280 one-year paragraphs. In **210** of them, the paragraph names
  a figure that no node of the Sankey under it carries.
  - In every one of those, the figure is the savings group's total: "The money comes from
    savings, \$158,708 (the taxable (brokerage) accounts \$127,435, the tax-deferred accounts
    (IRAs) \$31,273)" (variant -300, 2028).
  - The Sankey draws one source node per account and no group node on the sources side.
  - The table under it has the total ("From savings").
- The order's test for QW-1 was "every amount the paragraph names for a group is a node value
  of the Sankey". The built test
  (`test_every_tax_figure_the_paragraph_names_is_on_a_sankey_node`) covers the tax sentence only.
- On these runs, every other group amount in the paragraph (income, taxes, premiums, spending,
  conversions, surplus) is on a node.
- The income total would miss a node too in a year with two or more income rows. None occurs
  here [inferred].
- Fix: either a source-side group node for savings (and income), or the paragraph's total
  dropped and its lines kept.

### AO3 (low/nit, QW-7.1): "(from *run*)" follows the case, not the workbook

- [code] `Create_Case._hfpLoadedText` adds " (from *<run>*)" whenever `kz.runBaseName()` is set,
  that is, for the whole life of a case opened with *Edit as new run*.
- Financial Profile has its own HFP uploader (`ui/Financial_Profile.py` 336). After it reads
  another workbook, Create Case says "*other.xlsx* (from *bill later*) loaded".
- The " \*" of an edited workbook is stripped before the origin is added. So a workbook edited
  on the pages also reads as the run's own.
- Fix: clear the run's name from the case when a workbook is read by hand, or keep the origin
  beside the workbook's own name key.

### AO4 (nit, QW-2): the Note column is cut

- [seen] At 1500 px, the ACA over row's note reads "above 400% FPL no subsidy is paid: the full
  benchmark premium (SL…".
- The re-drive fixed the cut "Year of income" and IRMAA cost columns. The Note column
  (`width="large"`) is still cut.
- The full text is reachable on hover only.

### AO5 (nit, QW-3): premium years after the plan read "no Medicare premiums"

- [ran] On the baseline's Quick look, the last two rows of the brackets table read "no Medicare
  premiums in 2054" and "… in 2055". The plan ends in 2053.
- In the model nobody is alive then, so the sentence is not false. But it is the same
  construction that AN5 corrected for 2028 (a year with no one on Medicare yet), applied to
  years the plan does not have.
- Suggested words: "2054 is after the plan".

### AO6 (nit, QW-7.2): a failed *Edit as new run* leaves another case current

- [code] On a workbook that cannot be read, `kz.deleteCurrentCase()` removes the half-opened
  case. It then makes `list(ss.cases)[0]` current, not the case that was current before the
  click.
- The flash message is right. But the case pages then show the first case in the session.

### AO7 (nit, QW-8.3): the ACA toggle forgets a typed year

- [code] `_onAcaFromStart` stores 0 when switched on. When switched back off, it stores next
  year.
- So a case with `aca_start_year = 2029` that is toggled on and off comes back as 2027 with no
  message.
- Keeping the last real year in the case dict while the toggle is on would avoid it.

### AO8 (nit, N4): the year-fields draft's patched repro line can be misread

- [ran] With the patch, the repro prints "after typing 20300 in 'Year to start ...': the case
  holds 2026".
- [inferred] 2026 is the value already stored. The bounded widget does not take 20300 (its
  maximum is 2058), so nothing is clamped to 2026.
- A reader can take it for the patch mapping 20300 to 2026. A parenthesis would prevent it,
  e.g. "(the field refuses a year past 2058 and keeps the stored 2026)".

## What holds (each claim checked; how)

- **The three issue drafts** [ran, stock `dev` `73dc8815` worktree, `PYTHONPATH` set,
  `owlplanner.__file__` printed]:
  - **CRLF upload.** The repro output matches the draft line for line ("from StringIO, CRLF
    text: ['case_name']" … "Failed to parse case file: 'basic_info'"). 14 of 19
    `examples/Case_*.toml` hold a `"""` string.
  - **Year fields.**
    - Stock: "min 2026.0, max None"; "the case holds 20300"; conversions \$322,299 with 2030
      and \$0 with 20300.
    - Patched: "max 2058.0".
    - The patch's tests: 4 failed / 1 passed on stock, 5 passed with the patch.
  - **Balance units.**
    - Stock: "'solved'" then "'infeasible'".
    - The patch's tests: 2 failed / 1 passed on stock, 3 passed with the patch.
  - All three patches pass `git apply --check` on stock `dev`.
- **QW-3's `brackets.conversion_limits` mirrors the LP** [code, against
  `plan.py::_add_roth_conversion_constraints` 4600-4704 and `solve` 6831-6833]:
  - the cap is per person, nominal, and applies only when non-negative;
  - start and stop are `n < yearn` and `n >= yearn`;
  - the swap's two ranges are as in the LP;
  - `noRothConversions` is dropped beside a swap, as `solve` drops it;
  - "Roth conv fixed" pins override every policy except the exclusion;
  - the last two years of a life allow no conversion.
- **QW-2's Enhanced STAR price** [code]: pricing an over entry at `min(across, basic_limit)`
  keeps the basic credit, since `StarSchedule.implied_credit` tests `inc <= basic_limit`.
- **QW-6's loop wording** [code]:
  - `"local search -> loop"` (`plan.py` 6996) is written when the seeding loop found no plan,
    when the search found no feasible start (`NoIncumbent`), or when it found nothing better
    than the loop.
  - The first case is not "solved", so `method_kind` gives "no solve".
  - "the local search found nothing better" is exact for the third case and fair for the
    second.
- **QW-5's renaming has no stale consumer** [code, grep]:
  - nothing in `src/owlplanner/library` or `ui` looks a comparison row up by the label "score";
  - `lead_verdict`'s only two callers (`compare.compare`, `grid.lead_between`) put the score row
    first;
  - no library string a page renders says "score".
- **Real-solve figures** [ran]: the baseline's Quick look lists the 2027-2029 cliff rows at
  \$12,547.12 / \$12,864.41 / \$4,823.61. These are the Careful solve's figures in PROGRESS.md,
  to the cent.
  - 2029 IRMAA tier 2: \$3,741.19, whole year \$6,215.50.
  - 2029 Enhanced STAR: \$1,545.94.
  - The brackets table gives "tier 2 (\$70,650 over its \$289,559 edge): 2031 premiums" and
    "no Medicare premiums in 2028" for 2026.
- **The re-drive's layout fixes** [seen]: the *Year of income* and *Costs* columns are whole at
  1500 px.

## Not checked

- The Careful solve and its exact companion (Quick looks only).
- Windows.
- The per-item "N tests fail on the build" counts other than QW-2's: the later items' test
  files mix several items' tests.
- QW-7 and QW-8 in the browser: AppTest and code only.

## Full suite

Running on `d64ec67` (`-n 4`, Linux) when this note was first committed; the result follows in
the next commit.

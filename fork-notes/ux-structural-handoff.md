# Handoff: the ergonomics review's structural items S-1 to S-6 (2026-11-07)

**Status (2026-11-08): built** on `claude/loving-wright-44943l`, the nine decisions all as
recommended; what was built, the deviations and the checks are in PROGRESS.md "Ergonomics
review S-1 to S-6: built".

This is for the **next session**. The outside ergonomics review that suggested QW-1 to QW-8 also
suggested a second phase: six structural items, S-1 to S-6, "Workflows, State Persistence &
NY/ACA/IRMAA Storytelling". The user pasted them on 2026-11-07, asked for a review without
changes, then asked for that review as a work order.

Each item below was checked against the code at `f854721` (branch
`claude/upbeat-planck-c731oy`) and judged from the reader's side, the way the quick wins were.
Where this order keeps, changes or drops part of an item, it says why.

**Our own items.** Every one of S-1 to S-6 overlaps an item of our own review,
`fork-notes/ux-review.md` S1-S10. That review's status table marks S1-S4, S7, S8 and S10 "not
started (the user's call)", and S5, S6 and S9 "partly done":

| Outside item | Ours | Verdict |
|---|---|---|
| S-1 home screen | S1 | Keep the landing page. Drop the auto-hydration and the cookie |
| S-2 drafts, dropdowns, year text, plan settings | S3 + S2 | Keep the drafts and dropdowns. Structured years with the text kept as a fallback |
| S-3 converting housing rows on import | S4 | Offer the conversion behind an exact check. Never convert automatically |
| S-4 deflator, today's \$, NY split, markers | S5 (rest) | Keep. Fold recapture into state |
| S-5 Compare verdicts and overlays | S8 + new | Keep sentences and overlays. "Where it shows up", not "driven by" |
| S-6 queue polling, classic pages in the background | S7 | Polling is already built. No automatic page switch. Background solves in library mode only |

**Line references.** The review's line references are approximate:

- `ui/library_import.py` has 92 lines; the review cites 120-157.
- `src/owlplanner/library/scenario.py` has 428 lines; the review cites 465-530.
- The formatter is `src/owlplanner/cli/formatters.py`.

Tags:

- **[seen]**: in the running app (from `ux-review.md`, driven with Playwright on the synthetic
  household);
- **[code]**: read at `f854721`, not exercised;
- **[inferred]**: follows from the code, not reproduced;
- **[recalled]**: from memory, not checked here.

## Where things stand

- **Branch.** `claude/upbeat-planck-c731oy` (`f854721`) holds QW-1 to QW-8, both passes, and
  AO1-AO2.
  - Start the next session's branch from this one: `main` (`0770124`) holds none of it.
  - The user decides when to fast-forward `main`.
- **Upstream.** `dev` `73dc881`, unchanged.
- **Last full suite.** 4600 passed, 1 skipped (Linux, PROGRESS.md "Ergonomics quick wins: the
  second-pass review's AO1 and AO2 folded").
- **No solve has been run for this order.** The checks in "Done means" are for the build.

## Findings by item

### S-1: household home screen

The outside review asks for:

- library sections first in the menu;
- a landing page with the pinned baseline already selected, and that run opened in the case
  pages through `openCaseFromPlan()`;
- the disclaimer's dismissal kept in a cookie or in the library's metadata.

What the code does:

- **Menu and landing page [code].** `ui/main.py` builds Case Setup, Results, Stress Tests,
  Tools, Help, then Run Library last. The default page is `Welcome.py` (`default=True`).
- **Pins [code].** `library.json` has a `"pins"` list (`store.py:294`, `306`). The only code
  that touches it removes a deleted run's id (`store.py:567`). No `Library` method and no page
  sets a pin (grep over `ui/` and `store.py`).
- **Selecting a run [code].** The Run page reads `st.session_state["library_selected_run"]`
  (`Run.py:409`, popped once) into its selector `run_page_run`. The key `library_run_id` named
  in the review does not exist.
- **The Run page needs no `Plan` [code].** It draws from `plan.json` and `record.json` (the
  comment at `Run.py:55`).
- **Opening the run in the case pages has side effects [code].** `sskeys.openCaseFromPlan` adds
  a case to the session and refuses with `st.error` when the name is taken (`sskeys.py:387-401`).
  Calling it on every visit would add a step that can fail, for no gain on the page she sees.
- **The disclaimer [code].**
  - `Welcome.py:28` already honors `OWL_SKIP_DISCLAIMER` (also in `owlplanner.sh`/`.cmd` and
    the Docker README).
  - The dialog is drawn by `Welcome.py` only. If Welcome is no longer the landing page, the
    dialog never shows unless the new landing page draws it.
  - [recalled] Streamlit's `st.context.cookies` is read-only, so a cookie would need a custom
    component.

Verdict:

- Keep: library sections first, a landing page showing the baseline, a pin action.
- Drop: auto-hydration.
- Replace the cookie: see decision 2.

### S-2: Scenario drafts, dropdowns, structured years, plan settings

What the code does:

- **Edits are lost on page switch [seen, code].**
  - The editors and boxes are widgets keyed per run (`scn_work_{key}`, `scn_rent_on_{key}`, …;
    `Scenario.py:197-400`).
  - Streamlit drops a widget's state when its page is not drawn, so a purchase typed on the
    page is gone after a visit to Run (`ux-review.md` F3, "Scenario edits vanish on
    navigation").
  - No draft is kept anywhere.
- **The change summary already exists [code].** `diff_summaries(current, edited)` is drawn as
  "Changes against this run: …" above Save (`Scenario.py`, the Save section).
- **Free-text columns [code].**
  - The work table's `id`, `person` and `level`, and the claim and death tables' `id` and
    `person`, are plain text columns. Only the number columns have a `column_config`.
  - `level` must be `"full"` or `"part"` (`builder.py:415-417`).
  - `names` (the case's people) is already on the page (`Scenario.py:91`).
- **Year anchors as text [code].**
  - The rent, purchase, care and downturn years are `text_input`s parsed by
    `builder.parse_year_ref`.
  - The grammar has six forms (`builder.py:316-372`):
    - a calendar year;
    - `age:<person>:<age>`;
    - `work:<person>` (that person's last work year);
    - `after:<person>` (the year after it);
    - `purchase` (the home purchase's year);
    - `event:<id>` with an optional `+n`/`-n` offset.
  - The review's picker ("Calendar Year | Age | After Retirement") covers three of the six. It
    leaves out `purchase` and `event:…`, which the care event and the grids' rent end use.
- **No plan settings on the page [code].** The page says "Balances, PIAs, the goal and the
  assumptions are edited in the case pages ('Edit as new run' on the Run page)". Case Setup is
  eight pages (`main.py`). `maxRothConversion`, the conversion window, the objective and its
  spending or bequest target are case fields (`solver_options`), not events.

Verdict:

- Keep: drafts, dropdowns, structured years.
- Keep the text form as a fallback.
- Plan settings: see decision 3.

### S-3: housing rows on import

What the code does:

- **No conversion exists [code].** There is no "Convert housing rows" button or function; grep
  finds neither the label nor "Treat this as a purchase".
- **Refusals and guidance [code].**
  - The builder refuses a purchase event over a hand-built home that is still owned
    (`builder.py:1142`, B2).
  - `variants.py:100-105` says how to proceed: start from a run with no home in its workbook,
    then add the purchase on the Scenario page.
  - So the review's "without hand-editing JSON" overstates the present path. The real friction:
    she has to strip the hand-built rows out of the workbook (classic pages) before the grid can
    vary the purchase.
- **Why not automatically [code, inferred].** The builder writes the housing rows in different
  units and shapes:
  - the Fixed Assets row in purchase-year dollars;
  - the Budget lines in today's dollars;
  - the rent as one-year rows plus a "rent from 2027" tail (`builder.rent_rows`);
  - a Debts row linked by name;
  - a big-ticket outflow.

  Reading a hand-made workbook back into events is a guess about which rows form the pattern. A
  wrong guess would silently change the imported plan, and with it the inputs hash.
- **The household's workbook is hand-made [inferred].** The synthetic workbooks were made with
  the builder's own functions (`make_cases.py`), so they will convert. The household's own
  workbook is the likeliest not to. That argues for the check, not against the feature.

Verdict: offer the conversion as a new child run, only when the converted events rebuild the
imported tables cell for cell. Otherwise show the cells that differ and change nothing.

### S-4: today's dollars, the NY tax split, event markers

What the code does:

- **No yearly deflator in `plan.json` [code].** Only an end-of-plan
  `cumulative_inflation_factor` (`formatters.py:99`). `by_year` is nominal
  (`formatters.py:5`, `183-212`).
- **The Run page mixes units [code].**
  - The headline, "Things to look at" and the brackets text are in today's dollars.
  - The four by-year charts are nominal (`Run.py:55`, axes `run_charts.NOMINAL_PER_YEAR`).
  - Q6 labelled the axes and deferred the switch as structural (`ux-review.md` status, Q6).
  - Upstream's Graphs page already has a nominal/today radio (`Graphs.py:46-53`), which is a
    model for the wording.
- **The NY parts exist on the `Plan` [code].**
  - `lt_T_n` is the local tax, part of `st_T_n` (`plan.py:602`, `8011-8013`).
  - `st_recap_n` is the recapture, part of `st_T_n` (`plan.py:604`, `8010`).
  - `st_star_n` is the STAR credit received; `st_T_n` is net of it (`plan.py:611`, `8015`).
  - `by_year.state_tax` is `st_T_n`, all of them together.
- **Recapture is small [recalled from CLAUDE.md "Dropped by decision"].** \$81 to \$6.4k over a
  lifetime: as its own bar series it would be empty most years.
- **One marker exists [code].** The income chart already marks a purchase year that sets the
  scale (`run_charts.income_sources_figure`, Q16).

Verdict:

- Keep: the deflator, the switch, the local-tax and STAR split, the markers.
- Recapture stays inside state tax, shown in the tooltip and the year table (decision 6).

### S-5: Compare

What the code does:

- **Raw verdict as a heading [code].**
  - `compare.lead_verdict` returns "the second result leads", "the first result leads",
    "trade-off", "no difference beyond the noise rule" or "not comparable"
    (`compare.py:171-202`).
  - `Compare.py:148-151` draws it as `### {verdict}`.
  - The readings column says "~ unresolved"; the notes name "the 1% loop-noise band"
    (`compare.py:93`).
- **No charts on Compare [code].**
- **"What moved" mixes years' dollars [code].**
  - It is computed in nominal dollars (`compare._by_year_sums`, `what_moved`).
  - Its "lifetime" row adds nominal dollars of different years (`Compare.py:178-192`).
  - **This is a defect, not taste.** The review's example ("−\$58k lifetime") would inherit it.
- **The example verdict.** "White Plains 2029 (5-yr ARM) supports … driven by avoiding NYC's
  3.88% local income tax (−\$58k lifetime) and lower purchase price (−\$150k)" goes wrong in two
  ways:
  - It skips the noise rule's "too close to call" outcome.
  - It mixes an input difference (the price) with an attributed cause [inferred]. In an
    optimized plan, taxes, conversions and spending move together; "what moved" says where a
    difference shows up, not what caused it.

Verdict:

- Keep: verdict sentences, overlay and difference charts.
- Fix: the lifetime totals in today's dollars.
- Change: "where it shows up" plus "inputs that differ", not "driven by".

### S-6: Queue and the classic pages

What the code does:

- **The Queue page already polls [code].** `@st.fragment(run_every=2.0)` (`Queue.py:75`), with
  state, heartbeat age, elapsed time, the phase in words and Cancel / Kill / Run again. The
  review's first bullet is built.
- **Finished rows have no action [code].** Only waiting, running, interrupted and failed jobs
  get a button (`Queue.py:101-123`).
- **The classic pages solve in the foreground [code].** `Graphs.py:34-35`, `Worksheets.py:33-34`
  and `Reports.py:53-54` call `owb.runPlan()` on open whenever `caseIsRunReady()` (status
  "modified" or "new").
  - A claiming-age search can take 30 minutes or more [recalled from `ux-review.md` S7].
  - A plain Careful solve took about 5 minutes on the synthetic baseline (`ux-qw-handoff-2.md`).
  - The review's "20 minutes" was not timed here.
  - "Open in Owl" restores from `plan.pkl` without a solve (Q12); the foreground solve happens
    after an edit in the case pages.
- **Switching pages when a job finishes [inferred].** Several jobs can be queued, and pulling
  her off the page she is reading on every completion is worse than one click.

Verdict:

- Drop: the automatic page switch.
- Add: "Open result" on finished rows.
- Background solve for the classic pages: library mode only (decision 9).

## Decisions for the user, before the work

Ask each with its recommendation; do not settle them alone.

1. **S-1, the landing page.**
   - (a) The Run page, opened on the pinned baseline.
   - (b) A new Home page (our S1: headline, spending chart, *Things to look at*, the
     collections' open questions with their current answer, *What if…* and *Compare*
     buttons).

   Recommendation: (a) now. The Run page already carries the headline, the charts and *Things
   to look at*. A Home page would repeat them, and the collections' "current answer" needs a
   rule for picking it that does not exist yet.
2. **S-1, the disclaimer.**
   - (a) Set `OWL_SKIP_DISCLAIMER=1` in `owlplanner-library.sh`/`.cmd`.
   - (b) Show it once per library: the landing page draws upstream's dialog, and OK writes
     `disclaimer_accepted` (a timestamp) to `library.json`.
   - (c) As now: once per browser session, drawn by the landing page.

   Recommendation: (b). The reminder stays, she sees it once, and it costs one key in a file
   the library already writes under its lock. No cookie.
3. **S-2, plan settings.**
   - (a) A "Goal and conversions" box on the Scenario page: objective, spending or bequest
     target, Roth conversion cap and window. These are hand case fields edited in the scenario's
     `case`, not events, so they appear in `diff_summaries` and save as a child run like
     everything else on the page.
   - (b) A what-if panel on the Run page (our S2).
   - (c) Neither: keep *Edit as new run*.

   Recommendation: (a). One what-if page with one save path; a Run-page panel would be a second
   way to make a child run. This revises our S2's placement. The levers stay the same.
4. **S-2, year fields.**
   - (a) A structured picker covering all six forms, with "type it" as a fallback for the text
     form.
   - (b) The review's three forms only.
   - (c) Keep the text.

   Recommendation: (a). Three forms would strand the care and rent anchors the grids use.
5. **S-3, conversion.**
   - (a) Offered, behind the exact rebuild check.
   - (b) Automatic on import.
   - (c) Not built; better guidance only.

   Recommendation: (a).
6. **S-4, recapture.**
   - (a) Folded into state tax (tooltip and year table only).
   - (b) Its own series.

   Recommendation: (a), because of its size.
7. **S-4, the default unit.** Today's dollars (the review) or nominal. Recommendation: today's
   dollars on the library pages, matching the headline. The switch keeps nominal one click
   away. Upstream's pages are untouched.
8. **S-5, attribution.**
   - (a) "Where it shows up": the largest lifetime lines of "what moved", in today's dollars,
     plus a separate "inputs that differ" line from the two scenarios' diff.
   - (b) The review's "driven by".

   Recommendation: (a).
9. **S-6, the classic pages.**
   - (a) In library mode only: Graphs, Worksheets and Reports do not solve on open. They offer
     *Save as a new run and solve it in the background*, the Library page's save plus a Careful
     enqueue. Outside library mode, upstream's behavior.
   - (b) Also offer upstream a spinner with elapsed time, as an issue draft.

   Recommendation: (a) only. There is no defect to report upstream, only taste, and the user's
   rule is that upstream gets plain defects.

## The work

The order: S-2, S-1, S-4, S-5, S-3, S-6, one commit per item. Rules for all of them:

- **No solve and no existing run's inputs hash may change.** `BUILDER_VERSION` stays 6.
  - S-2's plan settings and S-3's conversion make new child runs, with their own inputs.
  - `plan.json` additions (S-4) are for new solves. An older result must still render, with a
    caption saying a new solve shows more.
- **Upstream pages** (Graphs, Worksheets, Reports, Welcome) change in library mode only
  (`sskeys.library_mode()`).

### S-2: drafts, dropdowns, structured years, plan settings

- **Drafts.**
  - Keep one non-widget dict per run, `st.session_state[f"scn_draft_{run.id}"]`. It holds:
    - the three tables as records;
    - every box's values (rent, purchase, care, downturn);
    - a version counter.
  - **Writing it.** After each render, write the editors' returned frames and the boxes'
    values into it, from the values the page already assembles (`_assemble`'s inputs).
  - **Seeding from it.**
    - On render, take the editors' `data` and the boxes' `value=` from the draft when it
      exists, else from the run.
    - Key the editors with the version (`scn_work_{run.id}_{version}`), so a returning page
      does not re-apply `data_editor` deltas recorded against other data.
    - [inferred] Re-applying them would duplicate added rows. The test must show it does not.
  - **Banner.** When `diff_summaries(current, edited)` is non-empty, draw "Unsaved changes
    against *{run}*: …" with **Reset** (drop the draft, bump the version).
  - **Elsewhere.** The Run page shows one line when its run has a non-empty draft: "The
    Scenario page has unsaved changes for this run", with a button to go there.
  - **Lifetime.** A successful *Save as a new run* drops the draft. Drafts last for the browser
    session only; design section 4's drafts on disk stay a later step.
- **Dropdowns.**
  - `person` as `SelectboxColumn(options=names)` in all three tables.
  - `level` as `SelectboxColumn(options=["full", "part"])`, shown as "full time" / "part
    time".
  - `id` hidden from the tables. It stays in the records: generate one for a new row the way
    `_event_id` does, and keep an existing row's.
- **Structured years.**
  - **The helper.** One widget helper, `ui/year_ref_input.py`, returns the dict form
    `parse_year_ref` returns. Its parts:
    - "When" (Calendar year · At an age · Last work year · Year after last work · Home purchase
      year · Another event's year);
    - then a year, or a person and an age, or a person, or an event and an offset, as the
      choice needs;
    - and "Type it" for the text form.
  - **Where.** It replaces each `text_input` year field in the rent, purchase, care and
    downturn boxes. The work spans keep plain years.
  - **The test.** A round trip over every form against `year_ref_text` / `parse_year_ref`.
- **Plan settings (decision 3 (a)).**
  - A "Goal and conversions" expander with:
    - the objective;
    - `netSpending` or `bequest`, in today's dollars, as the case stores them;
    - `maxRothConversion`;
    - the conversion window fields the case uses (the start and stop years; read their keys
      from `ui/Run_Options.py`, do not invent new ones).
  - The values are read from and written to the scenario's `case`, as hand values. Check that
    `casefiles._drop_generated_case` leaves them alone: no event generates them.
  - Bounds as on Run Options (QW-8's year clamps). Labels through `scenario.PATH_LABELS`, so the
    diff reads in words.
- **Tests.**
  - An AppTest that edits the purchase, switches to Run and back, and finds the edit, with
    nothing duplicated. It fails before the change.
  - The dropdowns' options.
  - The year helper's round trip.
  - A plan-settings edit appears in the diff and in the saved child's case.

### S-1: the landing page, the pin, the disclaimer

- **`store.Library`.**
  - `pin(run)`, `unpin(run)` and `baseline()` (the first pin that still exists, else `None`),
    under `library.lock`.
  - The `"pins"` list already exists; nothing in it changes meaning.
- **Library page.** "Make this the baseline" / "Baseline ✓" per run.
- **`ui/main.py`, in library mode.**
  - Put Run Library first.
  - Make the Run page `default=True`, and Welcome not the default.
  - Outside library mode, nothing changes.
- **Run page.** With no `library_selected_run` and no selector state, select `baseline()`.
  Without a pin, keep today's behavior (the newest run) with one line: "Pin a run on the Library
  page to open it here".
- **Disclaimer (decision 2 (b)).**
  - The landing page draws upstream's reminder unless `library.json` holds
    `disclaimer_accepted` or `OWL_SKIP_DISCLAIMER` is set. OK writes the stamp.
  - Reuse `Welcome._welcome_session_reminder`'s text; do not fork it.
- **Tests.**
  - The pin API.
  - The default page in library mode and outside it.
  - The Run page's pick with and without a pin.
  - The disclaimer once per library.

### S-4: deflator, today's dollars, the NY split, markers

- **`cli/formatters.plan_to_dict`.** Each `by_year` row gains:
  - `deflator` (`gamma_n[n]`, 6 places);
  - `local_tax` (`lt_T_n`);
  - `state_recapture` (`st_recap_n`);
  - `star_credit` (`st_star_n`, positive = received).

  Then:
  - `state_tax` keeps its meaning: `st_T_n`, net, with all of these inside it.
  - Document the identity in the module docstring:
    `state_tax = state base + state_recapture + local_tax - star_credit`. Check it holds on a
    real solve before writing it.
- **`ui/run_charts.py`.**
  - A `units` argument ("today" | "nominal") on the by-year figures, dividing by `deflator`.
  - The axis title follows the units (`TODAY_PER_YEAR` / `NOMINAL_PER_YEAR` already exist).
  - On the taxes chart, "State and local tax" splits into:
    - *State tax* (base + recapture; recapture in the hover);
    - *Local tax* (Yonkers/NYC, drawn only when non-zero);
    - *STAR credit* as a negative bar (the Sankey's W1 rule).
  - The words go through `FLOW_LABELS`, so the Sankey and the table agree.
- **Markers.** Vertical lines with a short label for:
  - each person's last work year;
  - the purchase year;
  - each person's Medicare start (the year they turn 65);
  - a debt's last year (`by_year.debt` falls to 0).

  All are read from `plan.json`. The Q16 annotation stays.
- **Pages.**
  - A segmented control "Today's \$ | Nominal \$" at the top of the Run page's charts and on
    Compare, default per decision 7, kept in the session (`st.session_state`, not per run).
  - An older result without `deflator` draws nominal with the caption "A new solve can show
    today's dollars".
- **Tests.**
  - The new keys on a solved plan, with the identity above.
  - The figures in both units.
  - The split drawn only where the parts are non-zero.
  - An older `plan.json` renders.

### S-5: Compare's verdicts and charts

- **The lifetime totals, first (defect).**
  - `compare.what_moved` gives its totals in today's dollars, each year divided by that result's
    own `deflator`. Rows stay per year, in the units the page selects.
  - Older results without `deflator`: totals labelled nominal, as now.
  - A test with two results of different inflation shows the old sum was wrong.
- **Sentences.** A wording map over `lead_verdict` and the score row, naming the runs and the
  amounts:
  - "*{B}* comes out ahead: \$X/yr more {score words}, and as much home at the end or more";
  - "Too close to call: \$X/yr, within this method's noise (1% of the plan)";
  - "A trade-off: *{B}* spends \$X/yr more, *{A}* keeps \$Y more home at the end";
  - "No difference";
  - "Not comparable: one result has no numbers".

  Score words come from `view.score_name`. The noise rule's explanation goes in a "How sure is
  this?" expander, with the agreement check as "a second method agrees / disagrees".
- **Where it shows up (decision 8 (a)).**
  - Under the sentence: the two or three largest lifetime lines of "what moved" (today's
    dollars), as "Where the difference shows up: taxes −\$…, Medicare premiums …".
  - A separate line "Inputs that differ", from `diff_summaries` between the two runs'
    scenarios.
  - No "driven by".
- **Charts.** A *Side by side* tab with A and B overlaid, and an *A − B* toggle:
  - spending per year;
  - liquid net worth;
  - cumulative taxes plus health premiums;
  - MAGI per year with the threshold lines from each result's `brackets` rows.

  All in the selected units.
- **Tests.**
  - Every verdict's sentence.
  - The lifetime totals in today's dollars.
  - The charts with results of different plan years (matched by calendar year, as
    `what_moved` is: W6).

### S-3: housing rows into events, on request

- **`library/casefiles.py`: `housing_events(scenario)`.**
  - It finds the pattern in a run's hand tables:
    - a Fixed Assets residence row;
    - the big-ticket outflow in its year;
    - the owner's Budget lines (property tax, HOA, insurance);
    - an optional Debts row linked to it by name;
    - rent Budget rows ending the year before.
  - It proposes `rent` and `purchase` events, with the hand rows they replace.
- **The check.**
  - Apply the proposal to a copy (hand rows removed, events added) and `builder.build` it.
  - Accept only if the built tables equal the imported ones **cell for cell**, the
    `check_library_builder.py` comparison.
  - Otherwise return the cells that differ.
- **Run page and Library page.**
  - "Turn the home rows into a purchase event" when `housing_events` finds a pattern.
  - On success: a child run with the events, saved through `Library.save_run`, and its inputs
    produce the same tables as the parent's.
  - On failure: the differing cells in a table, and nothing saved.
- **Make variants.** When a purchase dimension meets hand-built rows, point to this button
  instead of the "start from a run with no home" text (`variants.py:100-105`).
- **Tests.**
  - All 39 synthetic workbooks: each proposal rebuilds exactly. Add it to
    `check_library_builder.py` or a new check.
  - A tampered workbook (rent row edited) is refused with its cells.
  - The child's tables equal the parent's.

### S-6: the queue and the classic pages

- **Queue.**
  - "Open result" on finished rows: sets `library_selected_run` and switches to Run.
  - No switch on completion.
  - The fragment's 2-second poll stays.
- **Classic pages (decision 9 (a)), in library mode only.**
  - `Graphs.py`, `Worksheets.py` and `Reports.py` skip the solve on open when
    `caseIsRunReady()`.
  - In its place, a notice: "The case changed since its last solve", with *Save as a new run
    and solve it in the background*, doing the Library page's save (against `runBase`) plus a
    Careful enqueue through `preset_solves`. Then a link to the Queue.
  - *Re-run* is replaced the same way.
  - Outside library mode, upstream's code path, byte for byte.
- **Tests.**
  - AppTest in library mode: Graphs on a modified case does not call `runPlan` and offers the
    save. Outside library mode it still solves (the existing tests).
  - "Open result" selects the run.

## Setup and driving

As in `fork-notes/ux-qw-handoff-2.md`, "Setup and driving": the synthetic household only;
library mode on localhost (`OWL_LIBRARY_DIR`, `--server.address=localhost`); queue the Careful
solve early (about 5 min 16 s). Also needed here:

- **An older result** (a pre-S-4 `plan.json`) for the fallback captions: one Quick look solved
  with `PYTHONPATH` pointing at a worktree of `f854721`.
- **S-2's draft test** needs a page switch inside AppTest. If AppTest cannot switch pages,
  drive it with Playwright, and record which was used.

## Done means

- **Tests.** A test per item. For the two defects, the test fails before the fix; record that in
  PROGRESS.md:
  - S-2's lost edit;
  - S-5's nominal lifetime totals.
- **Suites.** `tests/library tests/ui tests/plan/test_thresholds.py tests/plan/test_brackets.py`,
  plus anything touched; then the **full suite** green, with the count and time recorded.
- **Lint.** flake8 and ruff, with only upstream's listed items left.
- **Checks.**
  - `check_library_builder.py` 46/46, with S-3's 39/39 conversions;
  - `check_library_roundtrip.py` 39/39;
  - `check_library_compare.py` 9/9.
- **Re-drive with Playwright** on the synthetic case, and quote what the pages now say:
  - the landing page with a pin, and the disclaimer once;
  - a purchase edit surviving a trip to Run;
  - the year picker;
  - the plan-settings diff;
  - the taxes chart in both units with the split and the markers;
  - Compare's sentence, "where it shows up" and the overlay tab;
  - a conversion on a synthetic import;
  - Graphs on a modified case in library mode.
- **Docs.**
  - PROGRESS.md, one section;
  - `fork-notes/CHANGELOG-fork.md`, an entry;
  - CLAUDE.md's "State", a bullet;
  - `fork-notes/ux-review.md`'s status table (S1, S3, S4, S7, S8 and the rest of S5, naming
    what was built).
- **Commit and stop.** Commit with CONTRIBUTING tags, push the session's branch, then **stop and
  report**. The user decides on an independent review and on fast-forwarding `main`.

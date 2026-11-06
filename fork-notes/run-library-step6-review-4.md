# Run-library step 6: fourth review of the whole step (2026-11-06)

Independent review of run-library build step 6 **as a whole** on `claude/eager-fermat-bhl251`
at `0e4803e` (= `main`: `e898f699..0e4803e`, the core, the second increment, the six earlier
reviews' folds AC-AH, the 2027 benchmark-jump mover and the `aca_table_year` removal). It reads
against `run-library-design.md` sections 4, 8.1, 9.3, 14 (I2, I8, I9, I11) and R2/R3. The
earlier reviews (`run-library-step6-review.md` AC, `-review-2.md` AD, `-review-3.md` AG,
`run-library-step6-inc2-review.md` AE, `-inc2-review-2.md` AF, `-inc2-review-3.md` AH) are not
repeated; the items they left standing (AC8-AC10, AD7-AD9, AG8) are not re-raised. This one
looks at what the pages **show** on the household's shape (the I8 chart and table, the tornado
seen from a second run), and at how the movers and dimensions meet the builder's coupled edits.
Findings **AI1-AI6** (1 medium, 4 low, 1 nit); prefix AI after AC-AH.

Environment: Linux, Python 3.11 (`uv sync`), HiGHS only, Streamlit 1.66.1 from the lock file.
**Nothing in `src/`, `ui/` or `tests/` was changed by this review.** The probes are scripts in
the session's scratchpad (`solvehelp.py`, `p2_condo_price.py` ... `test_q1_tornado_by_name.py`);
their outputs are pasted below. The synthetic cases are `make_cases.py`'s (39 workbooks, 46
scenarios, regenerated this session), solved on 2026-11-06 in plan year 2026 under
`decision_exact` with the claiming ages pinned at 70/70 unless said otherwise.

## What was run

| Command | Result |
|---|---|
| `pytest -n 4 tests/library tests/ui tests/plan/test_brackets.py tests/tax/test_aca.py tests/stochastic/test_regret_sweep.py` | **987 passed** (1:27) |
| full suite (`pytest -n 4 -q`) | **4391 passed, 1 skipped** (9:22, Linux; the same count PROGRESS records after the AH folds) |
| `flake8 src tests ui --max-line-length=120`, `ruff check src tests ui` | only the upstream items CLAUDE.md lists (`test_spending_bequest_frontier.py` / `test_spending_units.py` E301/E304; B905 in `localsearch.py:244`, `test_local_search.py:288`, `test_roth_maturation_losses.py:49`, `Run_Options.py:260`) |
| probes p2-p5, q1 (below) | AI1-AI6 reproduced; four suspects cleared |
| `check_library_variants.py` (reduced or `--full`) | not run (PROGRESS records 5/5 for both) |

## Findings

### AI1 (medium): the conversion chart draws a bar its lines cannot be read against

`ui/Run.py` `_conversions_and_brackets` stacks two bars per year -- "taxable income, ex
conversions" = `max(0, ordinary_taxable_income - conversion)` and "Roth conversions" =
`conversion` -- and draws three dotted lines over them: the next ordinary bracket edge, IRMAA
tier 1 and the 400% FPL cliff. Two things go wrong on the household's shape:

1. **The conversion layer is gross, the income is net of the deduction.** `conversion` is
   `sum(x_in[:, n])` (the gross conversion), `ordinary_taxable_income` is `G_n` (after the
   deduction). When the deduction absorbs part of the conversion -- the usual "fill the
   deduction and the 10% bracket" pattern -- the conversion exceeds the taxable income, the
   first bar is clipped to 0 and the stack shows the gross conversion as the year's taxable
   income: about twice the real figure. The table says the same thing in words ("taxable income
   24,800 | of which conversions 51,455").
2. **The IRMAA and cliff lines are MAGI lines; the bar is not MAGI.** The caption says so, but
   the chart puts the two side by side with nothing at MAGI: in the marketplace years the bar
   sits far below the 400% FPL line while MAGI is above it and the full premium is paid.

Probe (`p5_brackets.py`, `p5b.py`, `p5c.py`: `yonkers-2027-cash`, `brackets.bracket_view` of
the solved plan; "bar top" is what the chart stacks):

```
2027 bar top         0  MAGI   323,193  400% FPL 84,202  IRMAA t1 230,379  ACA paid 21,153
2028 bar top    51,455  MAGI   121,355  400% FPL 84,202  IRMAA t1 230,379  ACA paid 21,470
2029 bar top    55,078  MAGI   119,016  400% FPL 84,202  IRMAA t1 230,379  ACA paid 12,712
2028 G_n/gamma = 24799.996971945075 x = 51454.94 e_n/gamma = 36076.77 MAGI = 121355.45
     chart bar height (ex-conv + conv): 51454.94  table taxable income: 24800.0
2032 G_n/gamma = 24800.00218869349 x = 61555.04 e_n/gamma = 37194.62 MAGI = 111762.85
     chart bar height (ex-conv + conv): 61555.04  table taxable income: 24800.0
```

In 2028 the chart reads "51k of income, 33k under the cliff" while MAGI is 121k, 37k over it,
and the household pays the whole benchmark (21,470 today's \$, no credit); in 2027 the bar is
empty (the year's income is gains, which `G_n` leaves out) while MAGI is 323k. In 2028-2032
every conversion bar is 2.1-2.5 times the taxable income it is labelled as. The design's I8
asks for "taxable income, the Roth conversion layer that fills the bracket, the IRMAA and ACA
lines" (14.1); the page tests use a canned year whose conversion (15,000) is below its income
(90,000), so neither case is exercised.

Location: `ui/Run.py` `_conversions_and_brackets` (the stack and the table's column), and
`brackets.bracket_view` (`conversion` is the gross amount with no "of taxable income" share).
Suggested fold: stack the conversion's share of taxable income (`min(conversion,
ordinary_taxable_income)`, the conversion taken as the last layer) and say the rest is absorbed
by the deduction (or draw gross ordinary income with the deduction as a line); draw MAGI as its
own line or markers so the IRMAA and cliff lines have something to be read against; a page or
`bracket_view` test with a conversion larger than the taxable income and a MAGI over the cliff.

### AI2 (low): "bracket filled" names the bracket below the income, and flips on cents at an edge

`brackets._fill` returns the label of the last edge at or below the income. The labels are the
brackets whose **top** the edges are (`tax_federal.taxBrackets`: `"10%"` is 24,800 for a couple
in 2026, `"12/15%"` is 100,800; `taxParams` builds bracket t as (edge[t-1], edge[t]]), so an
income inside the 12% bracket is labelled `"10%"` and one inside the 10% bracket `"below the
first bracket"`. `test_brackets.py::test_the_bracket_the_income_fills_and_the_room_to_the_next`
pins it: an income 5,000 under the 12/15% edge asserts `fills_bracket == "10%"`. Read as "the
last bracket filled to the top" the label is defensible, but the docstring says "the bracket
the income fills" and the column header "bracket filled", while the room shown beside it is the
room to the top of the bracket the income is in (the two columns describe different brackets).

The edge itself is the worse case: a plan that fills a bracket exactly -- the conversion pattern
the view exists to explain -- sits on the edge to within solver noise, and the label and the
room flip on fractions of a cent (`p5_brackets.py`, `p5b.py`, the same plan):

```
2028 income  24,800 (24799.99697) conv 51,455 fills_bracket='below the first bracket' room=0.0
2031 income  24,800               conv 59,339 fills_bracket='below the first bracket' room=0.0
2032 income  24,800 (24800.00219) conv 61,555 fills_bracket='10%'                     room=76000.0
2035 income  91,493               conv      0 fills_bracket='10%'                     room=9306.97
```

Five conversion years at the same edge read two different ways (room 0 or room 76,000), and
2035 (91,493, marginal rate 12%) reads "10%". Location: `src/owlplanner/brackets.py` `_fill`.
Suggested fold: name the bracket the income is in (the first edge above it), treat an income
within a dollar of an edge as at that edge ("10% bracket full, 0 to the next edge"), re-pin
the test; the view's label and the "room" then agree.

### AI3 (low): the tornado's collection is found by the run's name

`ui/Run.py` finds the sensitivity collection by `c.name == f"Sensitivity: {run.name}"` (the
bars, line 667) and `_tornado_collection` reuses a collection of that name. Run names are not
unique (`Library.save_run` checks only that a name is not empty; an import is named from the
file, a pages save from the case name) and can be changed (`Library.rename_run`, the Library
page's rename box), so:

- **two runs with the same name share one tornado.** The second run's page draws the first run's
  children as its own bars, measured against the second run's base -- and the first run itself
  as a bar ("none (this run)"), since the page skips only `member.run == run.id`;
- **a rename orphans the tornado.** The bars disappear; the only way back is the button, which
  makes a second collection and queues every child again although each already has its
  exact-LP result (identical children join the old runs, and `enqueue` runs regardless).

Probe (`test_q1_tornado_by_name.py`, AppTest of the real Run page; `examples/Case_bill.toml`,
records written by hand as the page tests do: base 70,000, children 69,000 ... 65,000):

```
run B's page (never pressed its tornado button):     # a second run named "bill", base 90,000
| Bill dies at 80 | -25,000 | ±900 | resolved (the 1% loop-noise band) |
| no 2032 reversion | -24,000 | ±900 | resolved (the 1% loop-noise band) |
...
| none (this run) | -20,000 | ±900 | resolved (the 1% loop-noise band) |
collections: [('Sensitivity: bill', 6, True)]        # the reference is run A

before rename, bars table present: True
after rename, bars table present: False
queued per run: [('bill baseline', 1), ('bill death-bill', 3), ('bill inflation+1', 3), ...]
collections: [('Sensitivity: bill', 6), ('Sensitivity: bill baseline', 6)]
```

(Per child: the first click's solve, the hand-written result, and the second click's solve.)
Suggested fold: key the tornado's collection on the run (a `tornado_of: <run id>` field on
the collection, or the collection whose reference is the run and whose members carry
`mover` values), keep the name for display; skip a child that already has a same-day exact-LP
result of the same code, or say the button re-solves them all.

### AI4 (low): the tornado shows one of R3's two numbers, and the condo mover moves the other

The bars and the table are the score's difference only (`tornado.bars`: `view.score`). For
most movers the home at the end does not move, but "condo price +10%" moves it by about the
price change, and it is a gain the bar does not show (`p2_condo_price.py`):

```
yonkers-2027-cash
  unmoved                          solved score 116,034 (+0)  home 760,861 (+0)  savings 0
  condo+10 (mover)                 solved score 112,394 (-3,640)  home 836,947 (+76,086)  savings 0
yonkers-2027-mortgage
  unmoved                          solved score 113,418 (+0)  home 707,287 (+0)  savings 53,574
  condo+10 (mover)                 solved score 109,587 (-3,830)  home 778,016 (+70,729)  savings 58,931
```

R3 keeps the two numbers apart and never adds them, so the bar is not wrong, but "condo price
+10%: -3,640" read alone says only what the dearer condo costs, not that the household leaves
76,086 more in the home (the condo kept as the care reserve, per the household's own goal).
The Collections page's grid of the same children does show the home (it is a collection like
any other), the Run page's tornado does not. Suggested fold: a "home at the end" column in the
tornado's table (and the bar's hover), judged with `from_inputs=True` as the grid judges it.

### AI5 (low, design): "condo price +10%" holds the property tax and the insurance

`tornado._condo_plus_10` scales the purchase event's `price` and nothing else; the place's
`costs` (property tax, HOA, insurance in today's \$) stay as entered. A dearer condo in the same
place usually carries a proportionally larger assessment (the property tax in the scenario is a
fixed amount, not a rate), so the bar measures "the same condo with a 10% higher price tag".
Measured (`p2_condo_price.py`, the child again with property tax and insurance x 1.1, HOA held):

```
yonkers-2027-cash      condo+10 (mover) -3,640    condo+10, tax+insurance x1.1 -4,739
yonkers-2027-mortgage  condo+10 (mover) -3,830    condo+10, tax+insurance x1.1 -4,923
```

The held costs make the bar about a quarter smaller (1,099-1,093 of 4,739-4,923; outside the
1% band either way). What "+10%" should carry is the user's call; the mover's note ("the home
purchase's price, 10% higher") is accurate. Suggested fold, if wanted: scale the property tax
(and, if the user says so, the insurance) with the price, and say so in the note; or keep it
and add "(costs held)" to the label.

### AI6 (nit): a death before the person's own last work year builds, and the survivor loses the marketplace year

`builder.build` checks every event year against the last life horizon, not the person's own,
so a death dimension value (or a Scenario-page death) before that person's last work year is
accepted. Owl then drops the dead person's wages after the horizon (silently), while the
builder's marketplace start still comes from that work event ("employer coverage runs while
either spouse works full time"), so the survivor has no coverage cost in the gap
(`p3_work_after_death.py`, `p3b_aca.py`: `ari-full-2027`, Ari works full time to 2027, Noa
stops in 2026; the `death` dimension at Ari 62):

```
ari-dies-at-62 life [62, 89] aca_start 2028
  status solved horizons n_i [1, 28] year_n[0] 2026
  Ari wages by year (nominal $): [(2026, 168000), (2027, 0), (2028, 0), (2029, 0)]
ACA_n [0, 0, 11345, 10851]
wages Noa 2026-2028: [121000, 0, 0]
```

Noa, retired and widowed in 2027, pays no premium that year. The dimension's intended values
(75-85, I2) never meet a work event, so this is a nit; it is the death dimension's door that
lets the combination through. Suggested fold: `check_death_window`'s neighbour -- refuse (or
flag) a death year before that person's last work year, or let a death end the person's work
and coverage in the builder (the marketplace start the earlier of the last work year + 1 and
the year after the death).

## Checked and not a finding

- **The regret sweep's end year** (`worker._regret_sweep`): `int(plan.year_n[0]) - plan.N_n` is
  upstream's own `owlbridge.histYendMax`.
- **The tornado on other rate methods** (`p4_stochastic.py`): a seeded `gaussian` and a
  `historical_average` case make every mover; an unseeded `gaussian` case skips the two rate
  movers and the benchmark jump with the builder's reason (X3). (An invalid rate method makes
  `tornado_variants` raise a bare ValueError, but such a case cannot be saved with events.)
- **Job overrides under "Ages, thorough"** (`worker._solve`): the final solve's options are
  rebuilt from the case through `work_sweep.scorer_options`, which would drop a job's own
  overrides; no page passes any (`enqueue` call sites in `ui/` all pass a preset only).
- **Collections read across presets** (`grid.member_results` takes each member's newest
  non-exact result, a `regret` job's base solve included): the grid's flags name the different
  presets (`compare.flags`, S13).
- **`_shift_rates`, the jump's growth, AG1/AH2's folds**: re-read; nothing new.

## Not checked

- `check_library_variants.py` (reduced and `--full`): PROGRESS records 5/5 for both.
- An "Ages, thorough" or "regret" job end to end through the worker.
- A browser session of the pages (AppTest only); Windows.

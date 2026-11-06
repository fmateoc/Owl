# Run-library step 6: review of the whole step (2026-11-06)

Independent review of run-library build step 6 **as a whole** on `claude/run-library-step6-inc2`
at `c93b1be` (`e898f699..c93b1be`: the core, its two reviews' folds AC1-AC7 and AD1-AD6, the
second increment, its two reviews' folds AE1-AE3 and AF1-AF8, the `work_sweep` move). It reads
against `run-library-design.md` sections 4, 6.2-6.3, 8.1, 9.1-9.3, 11 and 14 (I2, I8, I9, I11)
and the R2/R3/R4 rules. The four earlier reviews each read one increment
(`run-library-step6-review.md` AC, `-review-2.md` AD, `run-library-step6-inc2-review.md` AE,
`-inc2-review-2.md` AF); this one looks for what sits **between** the increments (the tornado
seen from the Collections page, the save dialogs against make-variants' member values, the
new dimensions under R3's lead rule) and for what the movers measure on the household's own
shape. Findings **AG1-AG11** (4 medium, 4 low, 3 nit); prefix AG because AC-AF are taken.
None repeats an earlier item; the items those reviews left standing (AC8-AC10, AD7-AD9) are
not re-raised.

Environment: Linux, Python 3.11 (`uv sync`), HiGHS only, Streamlit from the lock file.
**Nothing in `src/`, `ui/` or `tests/` was changed by this review.** The probes are scripts in
the session's scratchpad (`p1_decimal_shift.py` ... `test_p12_regret_caption.py`); their
outputs are pasted below where a finding rests on them. The synthetic cases are
`make_cases.py`'s (39 workbooks, 46 scenarios), solved on 2026-11-06 in plan year 2026.

## What was run

| Command | Result |
|---|---|
| `pytest -n 4 tests/library tests/ui tests/plan/test_brackets.py tests/tax/test_aca.py tests/stochastic/test_regret_sweep.py` | **956 passed** (1:21) |
| full suite (`pytest -n 4 -q`) | running at the first commit; result in the follow-up commit |
| `flake8 src tests ui --max-line-length=120`, `ruff check src tests ui` | only the upstream items CLAUDE.md lists (`test_spending_bequest_frontier.py` / `test_spending_units.py` E301/E304; B905 in `localsearch.py:244`, `test_local_search.py:288`, `test_roth_maturation_losses.py:49`, `Run_Options.py:260`) |
| probes p1-p12 (below) | AG1-AG7, AG9 reproduced; three suspects cleared |
| `check_library_variants.py` (reduced or `--full`) | not run (PROGRESS records 5/5 for both) |

## Findings

### AG1 (medium): the tornado's rate movers shift a decimal-unit hand table by 100 points

`tornado._shift_rates` adds `RETURNS_STEP = -1.0` / `INFLATION_STEP = 1.0` to the table's cells
as percentage points. A hand table is stored "as the file holds them and `in_percent` says what
they mean" (`casefiles.py:498`, review AA1), so on a table in decimals
(`rates_selection.in_percent = false`, supported since AA1) the step is 1.0 = **100 points**:
"returns -1 point" writes -94% returns into every year and "inflation +1 point" 102.5%
inflation. The child keeps `in_percent = false`, exports and builds without complaint.

Probe (`p1_decimal_shift.py`: a couple on a hand table of 0.06/0.045/0.03/0.025, `in_percent`
false; each child through `export_case` and `config_to_plan`):

```
returns -1 point row 2026: [2026, -0.94, -0.955, -0.97, 0.025] in_percent: False
   the child's plan tau (first year, S&P, Bonds, T-notes, infl): [-0.94, -0.955, -0.97, 0.025]
inflation +1 point row 2026: [2026, 0.06, 0.045, 0.03, 1.025] in_percent: False
   the child's plan tau (first year, S&P, Bonds, T-notes, infl): [0.06, 0.045, 0.03, 1.025]
```

`test_tornado.py::test_a_hand_table_is_shifted_and_keeps_its_case_s_transforms` covers a percent
table only. Location: `src/owlplanner/library/tornado.py` `_shift_rates`. Suggested fold: scale
the step by the table's units (`0.01` when the case's `rates_selection.in_percent` is false),
or write the shifted child in percent and drop `in_percent`; a test on a decimal table.

### AG2 (medium): the tornado's bars measure the model change when the run has no exact-LP result

The button queues each child under `decision_exact` (the exact LP: Medicare off, SS taxability
0.85, LTCG exact) and nothing for the parent. `tornado.result_of(run.path)` then takes the
parent's newest exact-LP result "when it has one, else its newest" -- so for a run solved
with `quick`, `custom`, `ages`, `ages_thorough` or `regret` (anything but `decision`), every
bar is (mover + exact LP - the parent's model). The tolerance is the 1% band either way
(`pair_tolerance`: neither is "proved"), so the offset reads as a resolved effect, the same
on every bar.

Measured (`p2_base_offset.py`, the synthetic baseline `Case_ari+noa.toml`, ages pinned at
70/70, the same inputs under three presets; no mover applied):

```
decision_exact  solved   score      116,034  (4 s)  medicare=none bp=loop
quick           solved   score      111,500  (1 s)  medicare=loop bp=loop
custom          solved   score      111,653  (12 s)  medicare=optimize bp=None
```

A child that moves nothing would show a bar of **+4,534** against a `quick` parent and
**+4,381** against a `custom` one (3.9-4.1%, four times the band), beside real effects of the
same size (AG3: about -7,000 for the rate movers). The fallback is documented in
`tornado.py`'s docstring ("else its newest result"); the run page says nothing about which
result the bars are measured from.

A related mismatch: a run whose case searches the claiming ages (the synthetic case does,
`withSSAges = "optimize"`) shows its `ages` pick on the page, while `decision_exact` forces
`withSSAges = "fixed"`, so the children (and the parent's exact companion) solve at the case's
hand `social_security_ages`, not at the pick (AD5's mechanism, here with no flag).

Location: `ui/Run.py` ("Make the sensitivity runs"), `tornado.result_of`. Suggested fold: the
button also queues the parent under `decision_exact` when it has no exact result of the same
code (`code_stamp`), and `bars` refuses a base that is not exact-LP ("waiting for this run's
exact-LP solve") instead of falling back; for an `ages` parent, pin its pick in the parent's
and the children's exact solves (`fixed_ages`) or say on the page which ages the bars hold.

### AG3 (medium): "inflation +1 point" is mostly "returns -1 point" again

The inflation mover raises the table's `Inflation` column and leaves the nominal returns
where they are, so the real returns of stocks and bonds fall by about one point -- the same
cut the returns mover makes (Owl's fourth class, cash, follows inflation, so neither mover
changes its real return). The two bars therefore measure nearly the same thing, and the
tornado's ranking (its purpose) puts "inflation" first on what is mostly the real-return cut.

Measured end to end (`p11_rate_movers.py`: the synthetic baseline from `scenarios.json`
through `tornado_variants`, `export_case` and a `decision_exact` solve, ages pinned 70/70):

```
unmoved              score 116,034  first-year nominal [6.0, 4.0, 3.3, 2.8]  real (S&P, Baa, T-notes) [3.11, 1.17, 0.49]
returns -1 point     score 108,970  first-year nominal [5.0, 3.0, 2.3, 2.8]  real (S&P, Baa, T-notes) [2.14, 0.19, -0.49]
inflation +1 point   score 108,220  first-year nominal [6.0, 4.0, 3.3, 3.8]  real (S&P, Baa, T-notes) [2.12, 0.19, -0.48]
```

Bars -7,064 (returns) and -7,814 (inflation); the inflation bar exceeds the returns bar by
-750 (if the effects add, that is what one point of inflation costs at the same real
returns). Whether the bar should answer "inflation at the same nominal returns" or "at the
same real returns" is the user's call -- the design says only "inflation +1 point", and the
mover's note says "(prices and the deflator)". Suggested fold: move the three return
columns by +1 too (inflation at constant real returns: the indexing, basis and fixed-nominal
effects alone), or keep the edit and relabel it ("inflation +1 point, nominal returns held").

### AG4 (medium): two of the eleven movers cannot move the household's plan

On the household's shape (coverage from 2027, D1's statutory base) two movers are
inputs-only changes the model never reads, and both are made, queued and drawn:

- **"the 2027 marketplace rules"** pins `aca_table_year = 2027`, but `tax_federal._aca_table`
  already reads the 2027 table for every year from 2027 on ("a year past the last one
  published uses the last one"; `_ACA_TABLES` holds 2026 and 2027). The pin can change only
  ACA years before 2027 -- for a run whose plan year is 2027 or later, never anything.
- **"no 2032 reversion"** moves `obbba_expiration_year` from the template's 2066 to 2100, both
  past the plan's last year (2053 for the 1964-born couple at 89); the skip test compares
  only with the exact target year.

Probe (`p9_synthetic_movers.py`, `p5_aca_pin.py`, `p10_noop_movers.py`; the synthetic
baseline, `decision_exact`, ages 70/70):

```
made: ['returns -1 point', 'inflation +1 point', 'medical inflation +2 points', 'condo price +10%',
       'benchmark premium +10%', 'benchmark premium -10%', 'the 2027 marketplace rules',
       'the 2032 reversion', 'no 2032 reversion', 'Ari dies at 80', 'Noa dies at 80']   skipped: []
coverage from plan year 1 (2027): years whose cost moves: []
unmoved                        solved score 116,033.84  yOBBBA=2066 aca_table_year=0 last plan year 2053
no 2032 reversion (2100)       solved score 116,033.84  yOBBBA=2100 aca_table_year=0 last plan year 2053
the 2027 marketplace rules     solved score 116,033.84  yOBBBA=2066 aca_table_year=2027 last plan year 2053
the 2032 reversion (control)   solved score 113,131.74  yOBBBA=2032 aca_table_year=0 last plan year 2053
```

Each draws a "no difference" bar under a label that reads as "this policy does not matter",
and costs a solve. The marketplace one is the user's own call ("the 2027 marketplace benchmark
is both the ACA-rules mover and a benchmark-premium mover"), so what it should measure is
theirs to say: the design's I9 text names "the 2027 marketplace benchmark", and
`fork-notes/aca-ny/README.md` (147-148) records the one 2027 change the model does not
represent -- the benchmark's jump above inflation (25.29 nominal in 2027, entered deflated one
year as the conservative alternative). Suggested fold: skip a mover whose edit cannot reach a
plan year, with the reason (no ACA year before 2027; an expiration year already past the
plan's end), as the other skips do; and ask the user whether the rules half should become
"the 2026 table held" or the 2027 benchmark jump.

### AG5 (low): the Collections page shows a sensitivity collection as unsolved

`ui/Collections.py` reads each member through `grid.latest_result(run.path)`, which with
`prefer_exact=False` **skips** exact-LP results (`bool(is_exact_lp(result)) != prefer_exact`).
The tornado's children have nothing else, so the "Sensitivity: <run>" collection -- created by
the run page and listed on this page like any other -- shows every member as "no solved result
yet", the grid as "No member of this collection has a solved result yet", however many have
solved. The collection also has no reference and cannot get a meaningful one: the parent is
not a member.

Probe (`test_p3_sensitivity_page.py`: three tornado children, each with one solved
`decision_exact` result; AppTest of the real page):

```
{'mover': 'returns -1 point'} latest_result: None | tornado.result_of solved: True
...
info: ['No member of this collection has a solved result yet: queue them below (or on the Run page) and come back.']
members: ['**bill returns-1-point**  \nmover: returns -1 point  \nno solved result yet', ...]
```

Suggested fold: `_entry` falls back to the exact-LP result when a run has no other (marked
"exact LP" in the member line), and the tornado adds the parent as the collection's member and
reference (`mover: none`) -- which also gives AG2's exact-LP base a place on this page.

### AG6 (low): the save dialogs' "Collection" field wipes a member's variant values

`ui/Library.py` `_add_to_collection` and `ui/Scenario.py`'s save call
`lib.add_member(collection.id, run)` with no values. `add_member` replaces the member's values
(`members.append({"run": ..., "values": dict(values or {})})`), and a save identical to an
existing run joins that run (`result.identical_to`). So saving a grid cell's run again
unchanged -- the natural "open it, look, save" -- with the same collection chosen turns its
values into `{}`, and it leaves the grid ("Beside the grid (no variant values)"). The
Collections page's Add button guards against exactly this (`existing.values`; AF's "checked"
list covers that path, not the dialogs).

Probe (`test_p6_identical_save.py`: a member with `{year: 2027, place: yonkers}`; AppTest of
the real Scenario page, the Collection chosen, "Save as a new run" with no edit):

```
before: [('7a7578ab...', {'place': 'yonkers', 'year': 2027})]
after:  [('7a7578ab...', {})]
```

Suggested fold: the dialogs pass the existing member's values when the run is already a
member (`coll.member(run.id)`), as the Collections page does; one test per dialog.

### AG7 (low): the regret caption always says "mean regret 0"

`ui/Run.py` prints `valley.get('mean', 0)`, but `summarize_conversion_regret` names it
`mean_regret` (`stresstests.py:1132`: `"valley": {"x": ..., "mean_regret": ...}`). The page's
tests check the button only; no test renders a finished sweep.

Probe (`test_p12_regret_caption.py`: the real summarizer on a two-scenario sweep, its summary
in a result's `record.json`; AppTest of the Run page):

```
valley: {'x': 25000.0, 'mean_regret': 150.0}
LEAST: ['Least regret: commit 25,000 (mean regret 0); the curves and ...']
```

Suggested fold: read `mean_regret`; a page test with a summarized sweep in the record.

### AG8 (low): the death and sequence dimensions are judged as if they were choices

R3's lead rule and "What nothing beats" compare every member with one reference. A `death` or
`sequence` value is a state of the world, not an option the household picks, but the page
colours its cells by "leads the reference" and lets it into the front. An early death raises
the score (the survivor's spending share), so death cells read as resolved leads:

```
p7_death_before_claim.py (synthetic baseline, decision_exact, ages 70/70):
[89, 89] solved score 116,034
[66, 89] solved score 132,021        # "Ari dies at 66": +15,987
```

On the page that cell would be green and in the front: the score is up beyond the 1% band
and the home at the end is the same input (inferred from `lead_between`'s rule; the page was
not rendered with these two results).

With `grid_layout` putting `death`/`sequence` in the rows, the per-row star is right (it
compares choices within one outcome); the colours, the cells' differences and the front are
not. Design question, so the user's call. Suggested fold: when a collection varies `death` or
`sequence`, judge each cell against the reference's choice in its own row (the row's cell at
the reference's other values) and keep those dimensions out of the front, or at least say on
the page that those rows are outcomes, not options. The tornado's death bars have the same
shape (an early death "helps"), but they make no lead claim.

### AG9 (nit): the tornado's run names lose the mover's sign

`_slug` drops `+`, `-` and `%`, so "benchmark premium +10%" and "-10%" are both run
**"<run> benchmark-premium-10"** (folders `...-10` and `...-10-2`), "inflation +1 point" is
"inflation-1-point" (reads as minus), and "returns -1 point" is "returns-1-point" (probe
`p4_names.py`). The Library, Run and Queue pages list runs by name. Suggested fold: name the
children from the mover's `key` (`slcsp+10`, `slcsp-10`, `inflation+1`), which is already
unique, or let `_slug` keep a sign.

### AG10 (nit): the regret sweep is person 0's conversion, and nothing says so

`worker._regret_sweep` passes `person=0`; upstream's interface offers the choice
(`ui/owlbridge.runConversionRegret`, `regret_person`). For the household (one IRA each) the
run page's "what a different conversion would have cost" is the first-named spouse's first-year
conversion only, and neither the caption nor `record.json` names whose. Suggested fold: name
the person in the record and the caption; a person choice on the button if the user wants it.

### AG11 (nit): "Cancel" during "Ages, thorough" can wait a whole sweep pass

`_ages_thorough`'s cancel check rides on `run_variant`'s log messages, which come once per
person pass (`work_sweep.decide`: after `pool.map(score, ...)` over every age of the pass), and
each scored plan may run to `TIME_LIMIT` (900 s) -- up to about two hours for nine ages before a
cooperative cancel registers. The heartbeat thread keeps the job alive and N1's "Kill" is
offered while the cancel is pending, so nothing is stuck; the docstring ("the cancel checks
run at every sweep message") is accurate. Suggested fold, if wanted: call `check` inside
`_SerialPool.map` between items.

## Checked and not a finding

- **Death before the claiming age** (`p7`): Ari dying at 66 with a fixed claim at 70 builds and
  solves; Noa's benefit then starts in 2034 instead of 2035 (Owl's survivor mechanics). No
  refusal is needed.
- **The 2100 expiration year in the case pages**: the Rates page's field caps at this year + 40;
  an AppTest of `getIntNum`'s pattern with a seeded 2100 raises nothing (`test_p8_cap.py`).
- **The bracket view's units**: `tx.taxBrackets` returns base-year (today's-dollar) edges, the
  income is `G_n / gamma_n`, and the IRMAA edges are the premium year's nominal thresholds over
  the tax year's `gamma_n` -- the same comparison as nominal MAGI(m) against the m+2 thresholds.
- **`aca_table_year`'s plumbing**: every `acaCosts` / `acaVals` / `_aca_table` caller passes it
  (`plan.py` x3, `explain.py`, `thresholds.py`), both bridges round-trip it, and a 0 never
  enters the case dict (as AE/AF found; re-read).
- **The `ages` preset's consistency**: stage 2 and the final solve both run under the case's
  own model (`resolve_options("ages")` forces nothing; `fixed_ages` pins the pick).
- **Rate movers on a generated path** (`p11`): the child's table is the run's own path shifted
  by exactly one point in the columns named, and solves (the AG3 numbers).
- **The `regret` artifacts**: the second `publish` into the same results folder adds
  `regret.json` under the token check; a failed sweep keeps the base results (AF's reading,
  re-read).

## Not checked

- `check_library_variants.py` (reduced and `--full`): PROGRESS records 5/5 for both; not re-run.
- An "Ages, thorough" or "regret" job end to end through the worker (the pieces were read; the
  presets' tests pass).
- A browser session of the pages (AppTest only).

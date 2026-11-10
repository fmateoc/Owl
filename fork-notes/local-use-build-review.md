# Local-use build: review of D1-D4, the household folder and the first-time setup (2026-11-10)

Branch `claude/loving-carson-a2dfi9` at `74b6ec6` (nine commits on `main` `a7b539b`): the
local-use review's D1-D4 (`feaf587`, `0b92cd5`, `4fc78a4`, `b7ba0d6`, `0c2ec51`) and the
household folder with the first-time setup (`709766f`). A review by the session that built
them, on the user's request ("review the work you've performed on it"), so not an independent
one. Findings are prefixed AQ (after AP).

**Status: AQ1-AQ8 folded** on the same branch, one commit each (AQ3 and AQ4 share one), each
with a test; AQ9-AQ12 stand. The folds were made without asking: each is a defect with a
measured effect or a dead end, and each is one commit to revert.

Tags: **[ran]** a script on the real code, clock moved where a year is named; **[probe]**
AppTest or a small script; **[code]** read, not exercised; **[inferred]** follows from the
code, not reproduced. Nothing here was driven in a browser.

## Summary

- **Four medium findings.** Two in the new-year roll: rolled year by year, as it will be used,
  a home bought with cash was refused the year after the purchase (AQ1); a bought home carried
  over as rows lost a year of growth and inflation at every roll, and the note said to check
  it against what was paid (AQ2). Two in the first-time workbook: its instructions valued a
  home owned for years at its purchase price (AQ3), and its heading notes left out Owl's rule
  for after-tax contributions, which then add money (AQ4).
- **Four low findings**, folded: the new-year banner and marks outlived the save (AQ5); the
  starter file for a library the launcher would not open (AQ6); an uploaded workbook's
  corrected copy never read (AQ7); a run with a downturn placed before the new year could not
  be rolled (AQ8).
- **Standing:** a jump of two or more years under a year-by-year rates table (AQ9, low), the
  cost basis above the account's value (AQ10, low), two nits (AQ11, AQ12).
- PROGRESS.md's "the 46 synthetic scenarios carried to 2027, 2028 and 2030 all build" was true
  of one jump from 2026 each; the yearly chain was not run, and that is where AQ1 was.

## What was run

| What | Result |
|---|---|
| Full suite at `74b6ec6` (`-n 4`) | **4825 passed, 1 skipped** (9:30), as PROGRESS.md says |
| `flake8 src tests ui --max-line-length=120`, `ruff check src tests ui` | only upstream's listed items (ruff: 4) |
| `make_cases.py`, then the 46 scenarios through `newyear.start_year` with the clock moved to 2 January of each year: one jump to 2028 and to 2032, and year by year 2027..2028 and 2027..2032 | one jump 46/46 both; year by year **42/46** and **36/46** before AQ1, 46/46 after |
| `yonkers-2027-mortgage` year by year to 2029; the exported workbook read by the plan; `fixedassets.get_fixed_assets_bequest_value` | AQ2's figures |
| Setup's answers -> `write_workbook` -> filled with openpyxl -> `read_workbook` -> `export_case` -> a loop solve, three fillings | AQ4's figures |
| AppTest: *Start 2026 from this run*, a save, then Account Balances and Library | AQ5 |
| `home_dir` / `write_starter` / `keep_upload` on a scratch folder | AQ6, AQ7 |
| A downturn placed at 2026 on `yonkers-2029-mortgage`, rolled on 2 January 2027 | AQ8 |
| `yonkers-2027-mortgage` under a rates table with 2%, 10%, 5% inflation in 2026-2028, jump to 2028 | AQ9 |
| After the folds: `yonkers-2027-cash` to 2028 and `queens-2029-cash` to 2030, year by year, solved with the Quick look's options under the moved clock | both solved |
| After the folds: `check_library_builder.py` | 46/46 and 39/39 |
| After the folds: full suite at `519e3e2` (`-n 4`) | **4838 passed, 1 skipped** (9:41); 13 new tests |

## Findings

### AQ1 (medium, D2, folded `54e782c`): year by year, a cash purchase is refused the year after it [ran]

`_freeze_home` accepts a bought home as rows only if the scenario without the purchase event
builds the same tables. It compared layouts: a build with events lays out every house table
(an empty Debts table for a cash purchase) and a zero row per plan year; a build with no
events is the hand document as it is (`builder.build`'s early return). One jump from 2026
keeps the rent and work events in the check, so the layouts match. Year by year, 2027 drops
those as over, and in 2028 the check builds with no events:

```
chained 2027..2032: 36/46 build
  refused at 2028 (4): the bought home cannot be carried over as rows: the plan would not be the same (Debts: columns differ)
     ['both-stop-2026', 'yonkers-2027-cash', 'whiteplains-2027-cash', 'queens-2027-cash']
  refused at 2030 (3): ... ['yonkers-2029-cash', 'whiteplains-2029-cash', 'queens-2029-cash']
  refused at 2032 (3): ... ['yonkers-2031-cash', 'whiteplains-2031-cash', 'queens-2031-cash']
one jump 2026->2032: 46/46 build
```

The user had no way on from the refusal. A couple that retires at the end of 2026 and buys
with cash in 2027, with no other event, is that shape. A run with a mortgage or any other
event left passed. Fix: the check compares what the plan reads (`_sorted_tables`
leaves out a table without rows and a person-sheet row that is zero apart from its year).
Tests: the chain 2026 -> 2027 -> 2028 -> 2029, and that a row with a value still differs.

### AQ2 (medium, D2, folded `0f9f4fd`): the bought home loses a year of appreciation at every roll [ran]

Owl's reader resets a Fixed Assets year in the past to the plan's first year
(`hfp_io.py:663-673`) and reads the value as the worth at its start. The frozen row keeps the
purchase year and the price:

```
2027 plan (purchase event, first year): rows [{'year': 2027, 'basis': 700000.0, 'value': 700000.0, 'rate': 0.5}]
    home at the end: nominal 1,603,686; in 2027 dollars 760,861
2028 plan (frozen rows): rows [{'year': 2028, 'basis': 700000.0, 'value': 700000.0, ...}]
    home at the end: nominal 1,552,245; in 2028 dollars 757,076
2029 plan (hand rows):  ... in 2029 dollars 753,309
2028 vs 2027 restated to 2028 dollars (782,165): -25,089
```

The home at the end is one of the household's two headline numbers (the long-term-care
reserve). The docstring said the row "stay[s] in the dollars of the year it was bought in",
and the note said "Check its price and loan against what was paid", which keeps the drift.
The loan is exact (Owl amortizes from its start year). Fix, within "no amount is re-priced":
the freeze's note and one note per property already held as rows (`_owned_assets`, every
year) ask for today's value; the docstring says what Owl does with the row.

### AQ3 (medium, setup, folded `36f6e18`): the workbook's instructions value an owned home at its purchase price [code, and AQ2's run]

The Instructions sheet said "Fixed Assets: a home or other property you own. year: when
bought. basis: what was paid. value: what it is worth in the dollars of that year." With the
reset of AQ2, a home bought in 2005 for 300,000 and entered so is worth 300,000 today in the
plan. Owl's Documentation (`ui/Documentation.py:727-739`): *year* is the reference year, this
year or after; one you already own carries the current year. The sheet now says so, and that
the rate is above inflation for a home.

### AQ4 (medium, setup, folded `36f6e18`): contributions typed as the heading notes say add money [ran]

Owl deposits a contribution without taking it out of the year's cash: a pre-tax one is
already out of the wages, an after-tax one is paid for with a negative *big-ticket items*
amount (`ui/Documentation.py:540-543`). The notes on the headings said "Money added to the
taxable (brokerage) account.", "Roth IRA contribution." and no more. Ari with wages of
150,000 in 2026-2028, a loop solve of the plan the setup makes:

```
+ the same with the -28,000 big-ticket offset (Owl's documentation): status solved, yearly net spending (today's $) 146,096
notes-only vs none: +3,627/yr; with offset vs none: -3/yr
```

(8,000 of Roth IRA and 20,000 of taxable contributions a year.) The notes on the three
after-tax columns and on *big-ticket items*, and the Instructions sheet, now state the rule;
the three pre-tax columns say the wages are already net of them; the read-back on the Setup
page names after-tax contributions that no big-ticket amount of the year pays for
("**Check Ari's contributions**: ...").

### AQ5 (low, D2, folded `ef48edf`): after the save, the pages still say "Nothing is saved yet" [probe]

`RUN_NEW_YEAR_KEY` and its steps were set by *Start \<year\> from this run* and cleared
nowhere. After a save with new balances (abridged):

```
AFTER SAVE keys: {'library_base_run_id': <the 2025 run>, 'library_new_year': 2026, 'library_new_year_steps': ...}
INFO BOXES: ['**2026, started from *our plan - 2025*.** ... Nothing is saved yet: b...']
CAPTIONS: ['The case **our plan - 2026** will be saved as a new run for plan year 2026, with *our plan - 2025* as its parent.']
```

so every later save made another "our plan - 2026" from last year's run. Now a save whose
balances changed makes the new run the case's base and drops the marks; a save with last
year's balances keeps them (its warning says to enter them and save again).

### AQ6 (low, setup, folded `9c7db7f`): a starter file that starts another library [ran]

`home_dir` falls back on the library folder's parent, and the starter calls the launcher with
that folder, which opens `<folder>/library`. With `OWL_LIBRARY_DIR=docs/owl-lib` set by hand:

```
library: docs/owl-lib | home: docs | starter: docs/start-owl.sh
  -> the launcher sets OWL_LIBRARY_DIR=<home>/library = docs/library exists: False
```

a file written into a folder nobody named, starting an empty library. `write_starter` now
writes none unless the library in use is `<home>/library`.

### AQ7 (low, setup, folded `2984580`): an uploaded workbook's corrected copy is never read [ran, and a failing test]

The Setup page copied the upload into the folder at every rerun. The uploader keeps its bytes;
once the copy was corrected in Excel (the page: "Correct it in Excel, save, and this page
reads it again") it no longer matched them, so `keep_upload` wrote the old bytes as
`theirs (2).xlsx` and the page read that. Now copied once per upload (`file_id`), and the
copy is the workbook.

### AQ8 (low, D2, folded `519e3e2`): a run with a downturn placed before the new year cannot be rolled [ran]

The roll dropped a past downturn after its first build of the run; the builder reads the
rate path from a plan that starts in the clock's year and refuses the window first:

```
ScenarioError: down: the 'poor-decade' window starts at 2026, before the plan (2027-2053), and would be cut: place it inside the plan
```

PROGRESS.md had "A downturn event's drop is not unit-tested": it was unreachable in the new
year (the suite's clock is 2026, where the build passes). It is dropped before the build now,
with a note that no longer says "behind the plan" of a window that may still run. Tests with
a plan stub that starts in 2027.

### AQ9 (low, D2, stands): a jump of two or more years under a year-by-year rates table [ran]

The builder reads the inflation path from a plan that starts in the clock's year and indexes
it from the scenario's plan year. For the usual one-year roll nothing depends on it (history
and a frozen home are in the old plan's first year, where the price level is 1). After a
skipped year, under a table whose inflation differs by year (2%, 10%, 5% in 2026-2028):

```
built in 2026 (the run as solved): Fixed Assets (year, value) [(2027, 714000)]
jump to 2028: frozen Fixed Assets (year, value) [(2027, 735000)]
```

The rebuild check cannot see it: both of its builds read the same shifted path. Fixed and
historical-window rate methods are unaffected. Options: refuse a jump of more than one year
for a table or downturn run, or say so in a note. With AQ2's note the value is to be replaced
by today's anyway.

### AQ10 (low, setup, stands): a cost basis above the account's value is refused [ran, code]

```
['Ari: what was paid for the taxable investments cannot be more than they are worth today (leave it empty when it is not known).']
```

for 560,000 paid and 500,000 today. An account under water is a real state, and Owl accepts
it with a warning (`plan.py:1108-1113`, "Is this intentional?"). The refusal also guards a
mistyped zero; which matters more is the user's call.

### AQ11 (nit, D2, stands): the year just ended reads a MAGI of 0 [inferred]

`_roll_case` shifts `previousMAGIs` and leaves the new year at 0, with a note. Medicare's
premium two years on is read from it, so until the user enters it the plan prices that year
at the base premium. The parent's own result holds the plan's MAGI for that year and could be
the starting value.

### AQ12 (nit, records): what "46/46 each" covered

PROGRESS.md's "the 46 synthetic scenarios carried to 2027, 2028 and 2030 all build (46/46
each; 22 homes bought in 2027 pass the rebuild check in 2028)" was each a single jump from
the 2026 scenario. Corrected in today's entry.

## Checked and found right

- The setup's case keys sit where the schema reads them (`rates_selection.obbba_expiration_year`,
  `heirs_rate_on_tax_deferred_estate`, `dividend_rate`; `config/schema.py:177-190`), so
  "federal law as enacted" is applied, not ignored by `extra="allow"`. [code]
- "Let Owl choose ... the other solves hold 67 meanwhile": `quick`, `decision` and their
  companions force `withSSAges = "fixed"` (`presets.py:117-123`). [code]
- The *anticipated wages* note (net of pre-tax 401k, deductible IRA and payroll HSA) is
  Owl's own rule (`ui/Documentation.py:454-457`). [code]
- A rent under way keeps its nominal amount within its flat years (`rent_rows` with
  `flat_until <= start` is one row from the new year). [code, and the suite's test]
- The loan of a frozen home: `debts.py` amortizes from the row's start year, before the plan
  or not. [code]
- D1's keys, D4's `queued_at` order: read, and covered by tests that fail on the old code
  (PROGRESS.md); not re-run against the old code here. [code]

## Not checked

- Windows and macOS: `owlplanner-library.cmd`'s folder argument, `Start Owl.cmd`,
  `Start Owl.command`.
- A browser: D3's fragment, D4's flow, the default page moving from Start to Run when the
  first plan is made. PROGRESS.md records browser drives of them from the build; none was
  repeated, and today's folds were checked with AppTest and scripts only.
- Excel itself (the workbook was filled with openpyxl).
- The household's real case (offline, by rule).

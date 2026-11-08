# Issue draft: Run Options' year fields take any year, and "ACA start year (0 = plan start)"

Status: **filed as #250** by the user; fixed upstream another way (`e78d2a0`, merged here 2026-11-08): the fields accept any year up to `last_year_entered` (this year + 120), since a year past the plan is a legitimate "never"; the plan-end bound proposed here is dropped from the fork too. Was a draft (2026-11-07; `ux-qw-handoff-2.md` N4, QW-8.3, decision 5). For the
user to file on `mdlacasse/Owl`. Checked on upstream `dev` `73dc8815` (2026-11-07). Patch:
`fork-notes/issue-year-fields.patch` (`ui/Run_Options.py` and a new
`tests/ui/test_run_options_year_bounds.py`; applies to stock `dev` with `git apply`; verified
there: 4 of the 5 new tests fail on stock `dev` and all pass with the patch; `tests/ui` and
`tests/config` 412 passed with it). Repro script: `fork-notes/issue-year-fields-repro.py` (run
from a stock `dev` checkout with `PYTHONPATH=src`; AppTest for the page, two solves for the
plan). The output below is from real runs in this container.

The fork carries the same change since the QW-1-QW-8 build's second pass (2026-11-07).

---

**Title:** Run Options: the Roth conversion years have no upper bound, and the ACA start year is "0 = plan start"

Two small input traps on Run Options:

1. *Year to start considering Roth conversions*, *Year to stop considering Roth conversions*
   and *Year to switch converters* have `min_value=thisyear` and no `max_value`. A typo past
   the plan (20300 for 2030) is stored as typed, and the plan then converts nothing, with the
   case still "solved".
2. *ACA start year (0 = plan start, else 4-digit year)* is a number field whose 0 is a
   sentinel; its help has to warn against typing an offset ("Do not enter an offset (e.g. 3)").

**Repro (stock `dev` `73dc8815`):** `Case_jack+jill.toml`, the fields as the page draws them,
20300 typed into the start year, and the plan solved with 2030 and with 20300:

```text
$ PYTHONPATH=src python issue-year-fields-repro.py examples/Case_jack+jill.toml
field 'Year to start considering Roth conversions': min 2026.0, max None
field 'ACA start year (0 = plan start, else 4-digit year)': min 0.0, max 2076.0
after typing 20300 in 'Year to start ...': the case holds 20300 | exceptions: []
startRothConversions = 2030: solved, Roth conversions over the plan $322,299 (nominal)
startRothConversions = 20300: solved, Roth conversions over the plan $0 (nominal)
```

**With the patch:**

```text
field 'Year to start considering Roth conversions': min 2026.0, max 2058.0
after typing 20300 in 'Year to start ...': the case holds 2026 | exceptions: []
```

(The two solve lines are the model's, unchanged by a page patch; the ACA field is now a
toggle, so the repro lists no number field for it.)

**The patch:**

- The three Roth year fields get `max_value` = the plan's last year (`plan.year_n[-1]`), and
  `stopRothConversions`' default is held inside it. The page keeps upstream's rule (the
  comment above the stop toggle): it bounds the years and derives no default from the
  horizon.
- A stored year outside its field's bounds (a case whose life expectancy was shortened) is
  set to the nearest allowed year before the widget draws it, and the page says so in the
  field's words: *"Year to stop considering Roth conversions: 2500 is past the plan's last
  year, 2053; shown as 2053."* A move down to the last year changes the input's meaning, so
  the case is flagged modified; a move up to the first year (a year before the plan means
  "from its start") keeps its status.
- The ACA start year becomes a toggle, *Marketplace coverage from the plan start*, which
  stores 0 (the code's own sentinel, so saved files do not change); off, a year box bounded by
  the plan's first and last years appears, defaulting to next year. An unmodified example
  keeps its 0 and shows no message.

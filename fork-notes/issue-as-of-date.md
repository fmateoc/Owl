# Issue draft: an "as of" date input (`--as-of`), so a case reproduces on any day

**Withdrawn 2026-11-02 (user): not to be filed.** The fork dropped the `as_of` input itself. A
run is refused outside its plan year instead (`run-library-design.md` §8.3), and within the plan
year the only month-dependent read, the `withSSAges` claiming window, should follow the real
date. The draft is kept as a record. If it is ever revived, it needs the fixes listed in the
conversation of 2026-11-02:
- a process-wide freeze, because `withSSAges` and the stress tests run thread pools;
- a repro on stock `dev`;
- correct dates in the evidence (the mocked days were 2026-01-10 and 2027-02-01);
- the lazy-import claim marked as inferred;
- upstream's own `tests/conftest.py` freeze given as the main motivation.

Status: **draft for the user to file** (fork-only; 2026-11-02, run-library step 2). Design issue
rather than a bug report: the change is generic backend, like the rate table (D11). The fork
ships the mechanism for its run library (`run-library-design.md` §8.3 b) and would port the patch
to stock `dev` on request. Not yet rebuilt against stock `dev` -- the code references below are
the fork's at `dev` + the fork's merges; every named line was read there, but the patch itself is
verified on the fork only (stated as such when filing).

## Title

An `as_of` date input (`owlcli --as-of`): freeze the day a case's inputs are valid at, so a case
reproduces on any day

## Problem

Owl reads "today" all over the backend, so the same case file gives different plans on different
days, and after a New Year it silently reads its inputs as the new year's:

- the plan starts in the calendar year of the *solve*: `Plan._setStartingDate` ignores the year
  of `basic_info.start_date` ("Year is ignored"; `refdate = date(thisyear, ...)`) and every
  `thisyear = date.today().year` in `plan.py` follows;
- the claiming ages `withSSAges` may choose are bounded by the current *month*
  (`Plan._ssaOpenAges` / `_ssaCheckPastAges` read `_ssaCurrentAgeMonths`), so two solves of
  identical inputs a week apart can pick different claiming ages;
- `hfp_io._conditionTimetables` conditions the workbook to `today-5 .. today+horizon` and clamps
  a past Fixed Assets year to today; `toml_io.sanitize_config` clamps a past
  `startRothConversions` to this year -- an import is not reproducible either.

Our run library keeps one folder per run and promises "run the whole collection again today"
gives the same numbers (it compares runs solved on different days). That is impossible while
"today" is the wall clock: balancing two solves against each other across a weekend already moves
loop-noise-sized numbers, and a case balanced in January 2026, solved in January 2027, is read
with its balances as January 2027 balances -- nothing warns.

## Proposal

A tiny generic input, honoured wherever the backend reads today:

- one leaf module (ours is `owlplanner/asof.py`, ~70 lines): `today()` returns the frozen date
  when one is set, else `datetime.date.today()`; `set_as_of("YYYY-MM-DD")` / `clear_as_of()` /
  an `as_of(...)` context manager;
- every `date.today()` in `src/owlplanner` replaced by that `today()` (mechanical: 78 call sites
  in 15 modules on our tree -- `plan.py`, `hfp_io.py`, `tax_federal.py`, `tax_state.py`,
  `socialsecurity.py`, `fixedassets.py`, `debts.py`, `pension.py`, `config/*`, `utils.py`);
- `owlcli --as-of YYYY-MM-DD` on the solving commands (`run`, `compare`, `frontier`, and
  `explain`, which describes a config without solving), set at parse time before any date is
  read;
- no behaviour change without the flag: `today()` is `date.today()`.

With it, `owlcli run --as-of <the date the balances were taken at> case.toml` reproduces a run
on any machine on any day, and the date becomes part of a run's record.

## Why not the test suite's monkeypatch

`tests/conftest.py` freezes the date by rebinding `date` in every loaded module (and
`datetime.date` itself). That is fine inside pytest but not a product input: it reaches only
modules imported before it runs (a lazy import during a solve sees the real date), and rebinding
`date` breaks `isinstance(x, date)` checks against the real class (we hit both).

## Evidence (real runs, fork tree)

- Two solves of `examples/Case_bill.toml` at a fixed `--as-of 2026-06-15`, under two mocked
  wall-clock days (2026-01-10 and 2026-11-20): identical JSON results apart from the reported
  wall/CPU time (`tests/library/test_asof.py::TestCli::test_two_solves_on_different_days_give_identical_results`).
- Without the freeze, the same mock changes the plan whenever the solve year or month matters
  (`tests/plan/test_regressions.py`'s `midyear` fixture exists because a silent reset to "today"
  moved the start date; `tests/ss/test_ss_ages.py` runs issue #195's October date).

Happy to shape the patch as the maintainer prefers (a module like ours, or `Plan`-level state);
the mechanical call-site change is the bulk of it.

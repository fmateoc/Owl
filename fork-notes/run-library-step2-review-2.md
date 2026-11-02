# Second review of run-library build step 2 (2026-11-02)

Review of branch `claude/run-library-step2` at `b4a9ef18` (step 2 plus the F1-F10 fixes) against
`fork-notes/run-library-design.md` (sections 5, 8.1-8.3, 10, 11 step 2), `run-library-review-2.md`
(S1-S13) and the step's own review in PROGRESS.md (F1-F10). A fresh session's pass over the
implementation; findings are numbered **G1-G2** (fixes folded in the same day, user's call) and
**M1-M6** (minors). Every G finding was reproduced by a probe run here (scripts in the session
scratchpad, Windows, Python 3.11, real date 2026-11-01/02, not pytest's frozen 2026-01-01);
M findings say "inferred" where no probe was run.

## Checks run

- Full suite `.venv/Scripts/python -m pytest -n 4 -q -p no:cacheprovider` -> **3750 passed,
  1 skipped** (7:38), on Windows: this run exercises the `msvcrt` lock and `DETACHED_PROCESS`
  branches the Linux container could not (step-1 T5 noted the Windows branch as untested there).
  Re-run after the G1/G2 fixes: **3752 passed, 1 skipped** (7:25; two regression tests added).
- `flake8 src tests ui --max-line-length=120` and `ruff check src tests ui` -> only the known
  upstream-owned findings (their `test_spending_*` E301/E304 and four B905).
- `fork-notes/synthetic/check_library_jobs.py` not re-run (needs `make_cases.py` output); its
  four checks are covered by `tests/library` and `tests/ui/test_open_in_owl.py`, all green.

## Findings

| # | Severity | Finding | Evidence |
|---|---|---|---|
| G1 | medium | **Two concurrent enqueues share one results folder and one job record is lost.** `enqueue` picked the folder name `results/<stamp>_<preset>`, checked `folder.exists()` and then created it (`jobs.py`, the `while folder.exists()` loop into `JobRecord.create`, which does `mkdir(parents=True, exist_ok=True)`) -- a check-then-create with no lock around it. Two Queue sessions clicking Solve in the same second (the stamp has second resolution) pass the check together and land in **one** folder: the second `create` clobbers the first's `status.json`, so one queued solve vanishes (`manager.jobs()` lists 1 job for 2 enqueues), and if the first was already dispatched its worker's token is dead while the second's worker runs the same folder -- two workers on one run, S8's "never" case. Sequential enqueues are fine (the `-n` suffix loop); the design already plans batch queueing ("run the whole collection again", step 6), where two tabs make this likely. Fix: the claim is the `mkdir` itself (`folder.mkdir()`, `FileExistsError` -> the `-n` name): the OS makes one winner. | probe `probe_enqueue_race.py` (2 threads, frozen clock, held record write: one folder, job a's token gone; after the fix: `..._quick` + `..._quick-2`, 2 records) |
| G2 | medium | **The F2 token guard covers the record but not the artifacts: a stale worker re-fills the folder "run again" had just cleaned.** `requeue` deletes `summary.json`, `plan.json`, `Results.xlsx`, `plan.pkl` and keeps the old `record.json` as `record.prev.json` (F6), but `Worker._solve` wrote those four files with no token check (`worker.py`: `_write_json`, `saveWorkbook`, `save_plan`), and the `touch(token)` before them silently no-ops on a token change. The window is exactly S8's own scenario: the machine sleeps during "writing the results", adoption marks the job interrupted, "run again" cleans and re-queues under a fresh token, the old worker wakes and finishes its writes -- the **old attempt's artifacts land in the new attempt's folder** (probe: `Results.xlsx` + `plan.pkl` back, `summary.json` already cleaned -- a mix of two attempts), and if the new attempt fails the folder shows the old results beside the new record. Fix (folded in): the artifacts are staged in a private `.attempt-<token>` folder and renamed into place by `JobRecord.publish`, which runs **under the job's lock** and only while the job still runs under the worker's token. `requeue` cleans under the same lock, so a publish and a clean-up cannot interleave: a stale worker publishes nothing (and drops its staging), a publish that comes first is deleted by the clean-up. | probe `probe_stale_artifacts.py` (worker held inside `saveWorkbook`, job re-queued mid-write; before: old `Results.xlsx` + `plan.pkl` reappeared; after: the folder stays `solve.log` + `status.json` + `status.lock`, the worker returns "interrupted") |

## Minors (not fixed; the user's call)

| # | Finding |
|---|---|
| M1 | `requeue` keeps the old attempt's `record.json` as `record.prev.json` but not its `solve.log`: `_LogTee` opens the log with `"w"`, so the new attempt overwrites it and the kept record points to a log that is gone. A `solve.prev.log` beside `record.prev.json` would match F6's intent. |
| M2 | Design section 10's "the interface refuses a library folder inside the repository that git does not ignore (checked with `git check-ignore`)" is not implemented and is not in the step's known-limits list (the library-mode launcher and the localhost refusal are). `Queue.py` will create a library anywhere `OWL_LIBRARY_DIR` points, a public repo included. One check in `default_library_root` / `Queue.py`, or one line in PROGRESS.md's known limits until step 3. |
| M3 | `adopt` treats a record whose `pid_started` is None as ours (`ours = stamped is None or ...`), the opposite of S9's kill rule ("an unknown token refuses"). A reused PID whose start token could not be read at spawn is adopted and cannot be killed; only its token stops it. Harmless at this scale (adoption keeps the job, it never kills), but worth aligning or documenting. |
| M4 | `asof.as_of(None)` does not clear the freeze for the block when a process-wide `set_as_of` is set: `get_as_of`/`today` fall back to `_AS_OF` whenever the thread-local is None. A caller wanting "the real today" inside a frozen process has no context for it. Trivial; document or give the context an explicit sentinel. |
| M5 | `as_of_from_case` takes a 3-part `start_date`'s **year** as the balances' year, while Owl itself ignores it (`Plan._setStartingDate`: "Year is ignored") and the UI shows the current year for it (`ui_bridge._start_date_to_ui`). A file whose `start_date` year differs from its plan year (valid upstream) is therefore refused by the library (`resolve_as_of`, R1) instead of being read as upstream reads it. The refusal is defensible under R1 and the message is clear; the docstring should say the year is taken as the balances' year, unlike `_setStartingDate`. |
| M6 | `Queue.py`'s elapsed column calls `datetime.fromisoformat(finished)` on the record's `finished` string without a guard: one hand-edited or truncated `status.json` breaks the whole fragment every two seconds. Trivial (`try`/`except`, or `_since(finished)`). |

## Checked and fine

- The `as_of` conversion is complete: no `date.today()` left in `src/owlplanner` (the 78 sites
  are all `asof.today()`; `ui/` keeping the real today is the design's scope boundary), and no
  `datetime.now()` feeds a calendar decision. `import_case` freezes before `load_toml`, so the
  clamp and the conditioning see the run's date; both entry paths capture at it.
- The worker's solve route is `owlcli run`'s exactly (`config_to_plan` -> `parse_solver_options`
  -> `plan.solve(plan.objective, opts)`; `with_config="first"` is the CLI default; `plan.objective`
  is what `cmd_run` passes).
- `record.json`'s `converged` matches the plan's own semantics: only `"monotonic"`/`"oscillatory"`
  are `_check_obj_convergence`'s converged; `"oscillatory (cycle length n)"`, `"(stagnation)"` and
  `"max iteration"` are loop endings and correctly recorded as not converged.
- `owlbridge.genDic`'s account-key fix is right (`Plan.N_j = 4`); `openCaseFromPlan` re-attaches
  the log stream and sets the keys `runPlan` writes; `tests/ui/test_open_in_owl.py` renders the
  Graphs page with no solve.
- The plan cache fails soft everywhere: hash mismatch and environment mismatch drop the pickle
  (`load_plan`), `record.json` keeps the durable results; `Logger.__getstate__` mirrors
  `__deepcopy__`'s stream policy.
- F1's compare-and-swap dispatch, F3's per-job OS lock and rename retry, F5's thread-local
  freeze, F7's start-token adoption, the two-days determinism tests (New-Year-straddling, plus
  the month-sensitivity pin) and the `tests/conftest.py` `as_of` pin: as described, and tested.
- `procs.py`'s Windows branch (`OpenProcess`/`GetProcessTimes`/`TerminateProcess`) and the POSIX
  `/proc` field 22 parse are correct; the kill path refuses without a start token.

## Dispositions (2026-11-02, the user's call: fix G1 and G2)

| # | Disposition |
|---|---|
| G1 | Fixed. `enqueue` claims the results folder with `folder.mkdir()` (atomic; `FileExistsError` -> the `-n` name), then `JobRecord.create` fills it. Regression test `test_two_enqueues_at_once_get_their_own_folder` (two threads, the clock frozen to one stamp, both held inside the record write): two folders, two records, each token on disk. |
| G2 | Fixed. The four artifacts are staged in `.attempt-<token8>` and published by `JobRecord.publish(token, staging, names)`: a rename under the job's `_status_lock` with a token check inside the lock, so it serializes with `requeue`'s clean-up (same lock). A stale worker raises `JobCancelled` from the publish, writes no record (F2) and drops its staging folder (a hard kill can leave a `.attempt-<token>` folder behind -- cosmetic, nothing reads it). Regression test `test_run_again_leaves_no_artifacts_of_the_old_attempt` (the probe as a test: worker held in `saveWorkbook`, `run_again` mid-write): the folder stays `solve.log` + `status.json` + `status.lock`, the stale worker returns "interrupted". Probes re-run clean: "no collision this run", "no stale artifacts". |

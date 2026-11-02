# Draft upstream design issue: an opt-in run library for local installs (run-library steps 1-3, D8), for the user to post

Status: draft, 2026-11-02, on `claude/eager-turing-4bs36n` (from `main` `970eb3d5`). Not posted.
Decision D8 (`run-library-design.md` §15: "propose steps 1-3 as a design issue after they work in
the fork"): steps 1-3 and step 3's second increment are built and reviewed (CLAUDE.md "State",
PROGRESS.md). Concept level, as #185 and #227 were: the gap, the shape, what the fork learned
building it, and questions; not a request to merge the fork's code.

## Where to post (user's call)

Recommendation: a **new issue**. The maintainer turned #175 (housing ledger) into Discussion #177
and a separate project; this proposal may get the same answer, and the first question below asks
that directly, so either venue works. An issue keeps it beside the earlier design issues.

Prior upstream threads, read 2026-11-02 (bodies through `gh api search/issues`; the maintainer's
comments through WebFetch, which returns a summary with quotes, so the quotes below are as the
tool returned them, not checked against the page):

- **#27** ("Towards a CLI and scenario analysis", jleonard99, 2025-12-18): the maintainer
  (2025-12-21): a CLI "can change the paradigm of the user interface, which would then be used for
  manipulating input files and validate input"; "The output files can then be made consumable to
  the UI"; "Families of files should be handled at a higher loop level, possibly in Pl.an, or ever
  higher." `owlcli` exists since.
- **#45** ("Reproducibility and the TOML file", jleonard99, 2025-12-29): proposed folding the HFP
  and year-by-year rates into the TOML. The maintainer: the separate HFP lets "many users ... use
  the power of a spreadsheet"; "I don't want to rewrite Excel, and the friendlier Owl is to Excel,
  the better is its usefulness"; "it is generally much simpler to build basic capabilities from the
  bottom up". The proposal below keeps `Case.toml` + `HFP.xlsx` as they are, which fits this.

Searched with no relevant hit (`gh api search/issues`, `repo:mdlacasse/Owl is:issue`): "persist"
(0 issues), "session lost" (0); "save", "storage", "background", "compare", "history runs" gave
only unrelated issues in the titles listed.

## What the text rests on

**Verified on stock upstream `dev` `73dc8815`** (fetched 2026-11-02; 5 commits past the fork's last
merge `1cf1925`, Docker and docs only, not merged here):

- `ui/main.py`: the Assistant page is added only when `assistant_enabled()`; its comment: "The AI
  assistant chat is opt-in (OWL_ASSISTANT=1) and intended for self-hosted or Docker deployments;
  the hosted app never sets the variable." The precedent for an environment-variable opt-in.
- `owlplanner.sh` passes `--browser.serverAddress=localhost` but no `--server.address`.
  `docker/runentrypoint.sh` starts streamlit with `--server.address=0.0.0.0`;
  `docker/docker-compose.yml` publishes `8501:8501` and declares no volume.
- `Plan._setStartingDate` docstring (`plan.py:771`): "Year is ignored."
- **A solved Plan does not pickle.** Real run from a worktree of `upstream/dev` (its own `src` on
  the path, `owlplanner.__file__` printed from the worktree), `examples/Case_jack+jill.toml`,
  `maxSpending`: `caseStatus` solved, `pickle.dumps(plan)` raises
  `TypeError: cannot pickle '_io.TextIOWrapper' object` (the logger's streams).
- **`owlbridge.genDic` raises on every case.** Same worktree and example:
  `IndexError: list index out of range` at `ui/owlbridge.py:2039`,
  `dic[accName[j1] + str(i)]`: `accName` lists three accounts, the loop runs over `plan.N_j`,
  which is 4 unconditionally (`plan.py:459`). Nothing on `dev` calls `genDic` (grep: only
  docstrings in `config/ui_bridge.py` and a comment in `sskeys.py` name it), so no user meets it
  today. (PROGRESS.md said "every HSA case"; with `N_j` fixed at 4 it is every case.)
- `src/owlplanner/version.py` has `engine_commit` and `engine_provenance` (the fork's change
  there is a retry only).

**Built and measured in the fork** (PROGRESS.md, "Run library step 1/2/3" and their reviews;
`run-library-design.md` §5, §8, §9, §10):

- Size: `src/owlplanner/library/` 3,690 lines, the four pages and `ui/libraryjobs.py` 1,090,
  `thresholds.py` 403 (`wc -l`, 2026-11-02). Tests: 234 test functions in `tests/library/`, 32 in
  `tests/ui/test_library_pages.py` and `test_open_in_owl.py` (`grep -c "def test_"`).
- Checks on the synthetic household: `check_library_roundtrip.py` 39/39 workbook pairs round-trip
  unchanged; `check_library_jobs.py` 5/5 (a background solve in a detached worker, 11.4 s;
  restart survival; page keys from the cached plan; two solves on different days of the plan year
  identical); `check_library_compare.py` 9/9 (a \$400k-less variant: score -13.34%, "resolved", "the
  first result leads"; the same inputs re-solved: "no difference").
- The 1% band (question 4): CLAUDE.md "Loop noise", e.g. NJ vs NY at \$1.5M, loop -\$191/yr, local
  search +\$430, exact LP +\$1,006 (PROGRESS.md; measured with the fork's since-removed NJ code, so
  the example is not cited in the text). Owl's "Objective error bar" is `oscillationAbs / 2`
  (`export.py:706`), and `oscillationAbs` is 0 when the loop converged (`plan.py:727-728`).
- Why background jobs: one synthetic condo run took 5 min 10 s under local search (design §2,
  2026-11-01).
- Races and platform bugs found by the reviews, each fixed with a test (CLAUDE.md "State"): two
  same-second enqueues shared one results folder; a worker waking after "run again" overwrote the
  new attempt's files; job stamps without a UTC offset marked live workers dead in the DST
  fall-back hour; on Windows the old worker's open log blocked "run again" (WinError 32); a CRLF
  `.gitignore` with a blank line made `git check-ignore` call any new folder ignored.

**Fork-only, kept out of the proposal:** the score rule's first branch (first-year discretionary
spending, which needs the fork's essential budget lines); the NY recapture and Enhanced STAR
entries of `thresholds.py`; the budget sidecar handling in `casefiles.py`. The generic score is
the objective (spending basis under `maxSpending`, the bequest under `maxBequest`), which is what
the fork falls back to.

**Recalled, not checked here:** that Docker's `ports: 8501:8501` binds every host interface
(`127.0.0.1:8501:8501` limits it to the host's loopback). Stated in the text as a question, not as
a fact.

---

**Title:** Opt-in run library for local installs: saved runs, background solves, and comparisons that say whether a difference is real

For anyone who runs Owl on their own machine to choose between options (retire this year or next,
buy or rent, claim at 67 or 70), the web app has three gaps:

- **Nothing is kept.** Cases live in the browser session; they come in by upload and leave by
  download. Closing the tab loses the work, and there is no record of which inputs gave which
  result.
- **Solves block the page.** A solve runs inside the page request. Plans with local search or
  `"optimize"` families take minutes (5 min on one of my test cases), a claiming-age sweep much
  longer.
- **A comparison does not say whether a difference is meaningful.** Two runs a few hundred dollars
  apart may differ only by where the loop settled (#193, #239), and runs solved on different days
  or with different methods are compared as if alike.

I built an answer in my fork as an opt-in for local installs, the way `OWL_ASSISTANT=1` turns on
the Assistant. I am posting it as a design question first: it is large, and whether it belongs in
Owl at all is your call.

**The shape.** `OWL_LIBRARY_DIR=<folder>` adds a "Run Library" section (four pages: Library, Run,
Compare, Queue) to the existing app. Three layers:

1. **Storage: one folder per run, in Owl's own files.** A run is `Case.toml` + `HFP.xlsx` exactly
   as Owl reads them today, plus a small `run.json` (name, parent run, notes, a hash of the inputs,
   the plan year). No new input format: Excel stays the editor, and
   `owlcli run runs/<run>/inputs/Case.toml` reproduces a run outside the interface. A solved run
   is never edited in place: saving changes makes a new run whose parent is the old one, so the
   runs build up into a history. Saving inputs identical to an existing run says so instead of
   making a copy.
2. **Jobs: solves in separate processes.** Each solve runs in a fresh Python process (a detached
   `python -m owlplanner.library.worker`), queued on disk, so it survives a closed tab and a server
   restart, and can be cancelled. Each solve gets its own results folder: the Results workbook,
   `plan_metrics` and `plan_to_dict` as JSON, the solve log, and a `record.json` with the solve
   date, the method and options, the reported gap, iterations and convergence, the warnings, and
   the Owl version and commit (`engine_provenance`). A pickled copy of the solved Plan is kept as
   a cache, so "Open in Owl" restores the existing Graphs and Worksheets pages without solving
   again; the JSON files are the durable record, and a stale pickle only costs a re-solve.
3. **Reading: a run page and a two-result comparison.** The run page draws headline numbers and
   charts from the JSON files. The comparison shows the input changes in words, the outputs side
   by side, and judges each difference: for a plan proved by branch-and-bound, resolved when it
   exceeds the reported gap times the objective; for the loop and local search, which report no
   gap, unresolved under 1%; flagged when the two were solved on different days, with different
   methods or on different commits. Optionally the comparison also solves each run under a second,
   exact model (the loop with Medicare off, SS taxability pinned at 0.85, LTCG optimized) and
   reports whether it orders the two the same way.

The hosted app has no disk to keep runs on, so it would never set the variable.

**What building it taught me** (each found by a test or a review, and fixed):

- **A run belongs to one calendar year.** The plan starts in the year of the solve whatever
  `start_date` says (`_setStartingDate`: "Year is ignored"). Balances entered in January 2026 and
  solved in 2027 are read as January 2027 balances, and the 2026 rows of the HFP fall before the
  plan, with no warning. The library therefore records each run's plan year and refuses to solve
  it in another year. Within the year, a run with fixed claiming ages gave identical results on
  two different days.
- **A solved Plan does not pickle on `dev`**: `pickle.dumps` on a solved jack+jill raises
  `TypeError: cannot pickle '_io.TextIOWrapper' object`, from the logger's streams. A
  `__getstate__`/`__setstate__` pair on `Logger` that drops unpicklable streams and restores the
  default pair (the policy its `__deepcopy__` already follows) is enough.
- **`owlbridge.genDic` raises `IndexError` on every case** on `dev` (`ui/owlbridge.py:2039`:
  `accName` lists three accounts, `N_j` is 4). Nothing calls it today, so no one meets it; it is
  the natural way to rebuild the pages from a Plan, and "Open in Owl" needed it fixed. One line;
  happy to file it on its own if you prefer.
- **Concurrency is where the work is.** The reviews found, among others: two queue requests in the
  same second sharing a results folder; a worker waking after "run again" overwriting the new
  attempt; timestamps without a UTC offset marking live workers dead in the DST fall-back hour; on
  Windows, an open log file blocking "run again". The fork now claims folders with an atomic
  `mkdir`, guards every worker write with a per-attempt token under an OS file lock, and opens
  logs with Windows' share-delete flag.
- **Household data on disk raises the stakes on privacy.** The fork switches the library pages
  off unless streamlit binds to localhost (its launcher passes `--server.address=localhost`),
  refuses a library folder inside a git checkout that git does not ignore, and does not offer the
  Assistant chat, which sends the case to an outside model.

The run page also carries three extras that could come later or not at all: the years whose
income sits within 5% of a threshold the model knows (IRMAA tiers, the 0% gains bracket, the SS
bands, the marketplace limits, NIIT) with the price of crossing it, a one-year cash-flow Sankey,
and a claiming-age map over a sweep's scores.

**What core would need.** Almost all of it is new files (`src/owlplanner/library/`, four pages, a
launcher). The changes to existing code are small: the `Logger` pickling above, the `genDic` fix,
and a few more keys in `plan_to_dict` (the claiming ages used, per-year wages, pension and
withdrawals, the objective's error bar on an unsettled loop) so that a result can be read without
the pickle.

**Questions.**

1. Is this something you would want in Owl, as an opt-in for local and Docker installs, or would
   you rather it lived as a separate project (as Owl-budget does) that imports `owlplanner` and
   adds pages?
2. If in Owl: are Streamlit pages behind an environment variable, like the Assistant, the right
   form?
3. Docker: the entrypoint binds `0.0.0.0` inside the container, which the fork's localhost check
   refuses, and the compose file has no volume to keep runs on. Would a compose service with a
   mounted library folder and the port published on `127.0.0.1` only, plus a flag telling the app
   it is in a container, be acceptable? Or should library mode simply not be offered in Docker?
4. The comparison's 1% band for loop and local-search results comes from my measurements in the
   fork, where differences between variants under about 1% sometimes had the wrong sign under the
   loop against local search and the exact model. Owl's own "Objective error bar" covers a loop
   that oscillates, but is 0 for a loop that settled on one of several fixed points. Is a fixed
   band acceptable to you, or do you have a better measure in mind?
5. The plan year: the library refuses a run outside its year. Would you rather Owl itself warn
   when `start_date` names a year other than the current one? That is a small core change that
   would help every user who reloads last year's case file, library or not.

The fork's code is public (`src/owlplanner/library/`, `ui/Library.py`, `ui/Run.py`,
`ui/Compare.py`, `ui/Queue.py` on `fmateoc/Owl` `main`), with its design notes in
`fork-notes/run-library-design.md`. If you want any of it, I would build a PR on stock `dev` in your
shape; the pickling and `genDic` fixes could come first on their own.

# Draft upstream design issue: an opt-in run library for local installs (run-library steps 1-3, D8), for the user to post

Status: draft, 2026-11-02, on `claude/eager-turing-4bs36n` (from `main` `970eb3d5`). Not posted.
Decision D8 (`run-library-design.md` §15: "propose steps 1-3 as a design issue after they work in
the fork"): steps 1-3 and step 3's second increment are built and reviewed (CLAUDE.md "State",
PROGRESS.md). Concept level, as #185 and #227 were: the gap, the shape, what the fork learned
building it, and questions; not a request to merge the fork's code. Reviewed independently the same
day (findings 1-14 below, "Review"); the text below the `---` line is the revised version.

## Where to post (user's call)

Recommendation: a **new issue**. The maintainer turned #175 (housing ledger) into Discussion #177
and a separate project; this proposal may get the same answer, and the first question below asks
that directly, so either venue works. An issue keeps it beside the earlier design issues.

Prior upstream threads, read 2026-11-02 (bodies through `gh api search/issues`; the maintainer's
comments through WebFetch, which returns a summary with quotes, so the quotes below are as the
tool returned them, not checked against the page):

- **#132** ("Question: access from differen browser", faspina, 2026-07-18; closed as completed by
  the maintainer 2026-07-22). The body (`gh`, verbatim): "I am running using the docker compose. How
  do I map volumes so that I can access the web from different browers. I want to VPN to home server
  and access the web over local IP and port. ... Running in docker does not seem to save my cases
  when I close the browser and go back in". The maintainer (2026-07-20, WebFetch): "the docker image
  starts a service on port 8501 accessible from localhost only. This was done by design to enhance
  the security of the Streamlit service"; "Your data live on your computer, not on the image, the
  same way as if you were using the Streamlit Cloud Community server. No data stays there for
  privacy reasons."; "The server is stateless between sessions. You must save the HFP file and the
  case file as instructed in the documentation." Review finding 1 put this at the head of the post;
  **dropped on 2026-11-03 (user):** #132 is about running the pre-built Docker image, where caution
  is right; the fork runs the app built from source on the user's machine, a supported way to run
  Owl, and a known local process saving local files raises no such concern. The post says once that
  the library is for source installs and does not mention #132 or Docker otherwise.
- **#27** ("Towards a CLI and scenario analysis", jleonard99, 2025-12-18): the maintainer
  (2025-12-21): a CLI "can change the paradigm of the user interface, which would then be used for
  manipulating input files and validate input"; "The output files can then be made consumable to
  the UI". `owlcli` exists since.
- **#45** ("Reproducibility and the TOML file", jleonard99, 2025-12-29): proposed folding the HFP
  and year-by-year rates into the TOML. The maintainer: the separate HFP lets "many users ... use
  the power of a spreadsheet"; "I don't want to rewrite Excel, and the friendlier Owl is to Excel,
  the better is its usefulness"; "it is generally much simpler to build basic capabilities from the
  bottom up". Cases enter and leave the library as `Case.toml` + `HFP.xlsx`, which fits this; inside
  a run the source of truth is a JSON copy of both (finding 2), which the text says.
- **#54** ("HFP file with old year causes loading issue", sengsational, 2026-01-02): title only,
  not read; related to question 4.

Searched with no relevant hit (`gh api search/issues`, `repo:mdlacasse/Owl is:issue`): "persist"
(0 issues), "session lost" (0); "save", "storage", "background", "compare", "history runs" gave
only unrelated issues in the titles listed.

## What the text rests on

**Verified on stock upstream `dev` `73dc8815`** (fetched 2026-11-02; 5 commits past the fork's last
merge `1cf1925`: Docker builds, the version kick, `ui/Connect_your_AI.py` text and the `Makefile`;
not merged here):

- `ui/main.py`: the Assistant page is added only when `assistant_enabled()`; its comment: "The AI
  assistant chat is opt-in (OWL_ASSISTANT=1) and intended for self-hosted or Docker deployments;
  the hosted app never sets the variable." The precedent for an environment-variable opt-in.
- `owlplanner.sh` passes `--browser.serverAddress=localhost` but no `--server.address`.
  `docker/runentrypoint.sh` starts streamlit with `--server.address=0.0.0.0` and prints "Other
  network addresses are turned off for security reasons."; `docker/docker-compose.yml` publishes
  `8501:8501` and declares no volume.
- `Plan._setStartingDate` docstring (`plan.py:771`): "Year is ignored." Stock run by the reviewer:
  a case with `start_date` 2025-01-15 logs "Setting 1st-year starting date to 2025-01-15." and
  solves with `year_n[0]` 2026, no warning. The HFP keeps the five years before the plan as
  history (`hfp_io.py:336`, "Go back 5 years for Roth maturation"; read by the earnings test since
  #235), so last year's rows become history rather than disappearing.
- **A solved Plan does not pickle.** Real run from a worktree of `upstream/dev` (its own `src` on
  the path, `owlplanner.__file__` printed from the worktree), `examples/Case_jack+jill.toml`,
  `maxSpending`: `caseStatus` solved, `pickle.dumps(plan)` raises
  `TypeError: cannot pickle '_io.TextIOWrapper' object` (the logger's streams). Reproduced by the
  reviewer; with only the fork's `mylogging.py` change applied the plan pickles (406,088 bytes) and
  reloads with the same basis.
- **`owlbridge.genDic` raises on every case.** Same worktree and example:
  `IndexError: list index out of range` at `ui/owlbridge.py:2039`,
  `dic[accName[j1] + str(i)]`: `accName` lists three accounts, the loop runs over `plan.N_j`,
  which is 4 unconditionally (`plan.py:459`). Nothing on `dev` calls `genDic` (grep: only
  docstrings in `config/ui_bridge.py` and a comment in `sskeys.py` name it), so no user meets it
  today. (PROGRESS.md said "every HSA case"; with `N_j` fixed at 4 it is every case.) Reviewer:
  adding `"hsa"` to `accName` makes it succeed on the solved and on the unpickled plan.
- `src/owlplanner/version.py` has `engine_commit` and `engine_provenance`. The fork's change there
  is a retry of the git calls with the timeout raised from 5 to 15 s (commit `7be985ca`: the cache's
  code stamp depends on it).
- Owl's "Objective error bar" is `oscillationAbs / 2` (upstream `export.py:706`), and
  `oscillationAbs` is 0 when the loop converged (upstream `plan.py:727-728`).

**Built and measured in the fork** (PROGRESS.md, "Run library step 1/2/3" and their reviews;
`run-library-design.md` §5, §8, §9, §10):

- Source of truth of a run: `inputs/scenario.json` (`library/store.py:7-10`, `library/scenario.py:1-7`);
  `Case.toml` and `HFP.xlsx` are generated from it and frozen (design §5, R9).
- A preset solve forces options that are not in `Case.toml` (`library/presets.py` `_FORCED`;
  `worker.py:224`), and `record.json` stores the options the solve used (`results.py:577`, filled
  from `worker.py:306`). So `owlcli run` reproduces a run with those options, in its plan year.
- Size: `src/owlplanner/library/` 3,690 lines, the four pages and `ui/libraryjobs.py` 1,090,
  `thresholds.py` 403 (`wc -l`, 2026-11-02). Tests: 234 test functions in `tests/library/`, 32 in
  `tests/ui/test_library_pages.py` and `test_open_in_owl.py` (`grep -c "def test_"`).
- Checks on the synthetic household: `check_library_roundtrip.py` 39/39 workbook pairs round-trip
  unchanged; `check_library_jobs.py` 5/5 (a background solve in a detached worker, 11.4 s;
  restart survival; page keys from the cached plan; two solves on different days of the plan year
  identical, on one synthetic case, with `start_date = "today"` stored as the capture day);
  `check_library_compare.py` 9/9 (a \$400k-less variant: score -13.34%, "resolved", "the first
  result leads"; the same inputs re-solved: "no difference").
- The 1% band (question 3) is `run_suite.py`'s "~" convention (design §9.2, R2). For the loop:
  CLAUDE.md "Loop noise", e.g. NJ vs NY at \$1.5M, loop -\$191/yr, local search +\$430, exact LP
  +\$1,006 (measured with the fork's since-removed NJ code, so not cited in the text). For local
  search, the measured shortfalls are far smaller: \$8-99/yr against the exact LP's picks
  (PROGRESS.md:2405, later found to be local search's own noise, :2587) and \$15-74/yr against
  branch-and-bound at gap 1e-5 on 6 of 6 plans (PROGRESS.md:2449); chris+pat, a fork synthetic case.
- Why background jobs: one synthetic condo run took 5 min 10 s under local search (PROGRESS.md:2607,
  fork features on, HiGHS, this container about 2.4x slower than the maintainer's machine).
- Races and platform bugs found by the reviews, each fixed with a test (CLAUDE.md "State"): two
  same-second enqueues shared one results folder; a worker waking after "run again" overwrote the
  new attempt's files; job stamps without a UTC offset marked live workers dead in the DST
  fall-back hour; on Windows the old worker's open log blocked "run again" (WinError 32); a CRLF
  `.gitignore` with a blank line made `git check-ignore` call any new folder ignored.
- Existing code the library changes (`git diff 1cf1925f HEAD`): `mylogging.py` (`Logger`
  pickling), `version.py` (the retry), `ui/owlbridge.py` (`genDic` fix, `openCaseFromPlan`),
  `ui/sskeys.py` (`openCaseFromPlan`, `setRunBase`, `runBase`), `ui/main.py` (the section, the
  localhost check, the Assistant off), `cli/formatters.py` (`plan_to_dict`: `claiming_ages`,
  per-year `wages` / `pension_income` / `spia_income` / `portfolio_withdrawals`, and `cash_flow`,
  `thresholds` for the extras; `plan_convergence`: `objective_error_bar_today_dollars`, which also
  reaches the MCP compare tools, `assistant/tools.py:997`, `:2648`), `export.py`
  (`cash_flow_split`). New dependencies: none (the library imports the standard library, numpy,
  pandas, plotly, streamlit, toml).

**Fork-only, kept out of the proposal:** the score rule's first branch (first-year discretionary
spending, which needs the fork's essential budget lines); the NY recapture and Enhanced STAR
entries of `thresholds.py`; the budget sidecar handling in `casefiles.py`; the claiming-age map
(`library/agemap.py` reads `fork-notes/phase5/work_sweep.py --json`, which upstream has no
producer for); `housing_costs_nominal`, `locality` and the `state_moves` shape in `plan_to_dict`.
The generic score is the objective (spending basis under `maxSpending`, the bequest under
`maxBequest`), which is what the fork falls back to.

**Recalled, not checked here:** that Docker's `ports: 8501:8501` binds every host interface
(`127.0.0.1:8501:8501` limits it to the host's loopback); docs.docker.com is not reachable from this
container. Not in the text, and not our concern (we do not run the image).

## Review (2026-11-02, independent reviewer agent; all findings checked and taken)

1. #132 missed: cited in the opening, question 1 answered it, question 3 split. **Reverted
   2026-11-03 (user):** Docker and #132 are not how the fork runs Owl; the opening and the Docker
   question are gone (see the #132 note above).
2. "exactly as Owl reads them ... No new input format" was wrong (the source of truth is
   `scenario.json`): reworded.
3. `owlcli run` reproduces a run only with the recorded options and in its plan year: said so.
4. "What core would need" incomplete (`ui/main.py`, `openCaseFromPlan`, `sskeys`, `version.py`;
   the error bar is in `plan_convergence`, so MCP output changes too): completed; "no new
   dependency" added.
5. The 1% band justified for the loop only: question 3 (4 before the Docker question was dropped) gives local search's measured shortfalls
   and asks about a per-method band.
6. The "second, exact model" is fork methodology and "exact" misleads: now "a simplified model ...
   as an ordering check", with its ACA limit.
7. The claiming-age map is fork-only: dropped from the text.
8. Two-days identity depends on the library storing `today` as the capture day, one case: said so.
9. Last year's HFP rows become history, not "before the plan": reworded.
10. The hosted app's reason: now "shared by all visitors, disk not persistent" (plausible, not
    checked).
11. "the policy its `__deepcopy__` already follows" overstated: now "close to".
12. "5 min": now qualified.
13. Evidence-note errors (the five commits, the version.py timeout, upstream line numbers, the #27
    quote): fixed; the uncheckable #27 quote dropped.
14. Question 3 bundled two questions: split, then removed with the Docker question (finding 1).

---

**Title:** Opt-in run library for local installs: saved runs, background solves, and comparisons that say whether a difference is real

For anyone who runs Owl from source on their own computer to choose between options (retire this
year or next, buy or rent, claim at 67 or 70), the web app has three gaps:

- **Nothing is kept.** Cases come in by upload and leave by download; closing the tab loses the
  work, and there is no record of which inputs gave which result.
- **Solves block the page.** A solve runs inside the page request. Plans with local search or
  `"optimize"` families take minutes (5 min for one of my test cases, on a slow machine), a
  claiming-age sweep much longer.
- **A comparison does not say whether a difference is meaningful.** Two runs a few hundred dollars
  apart may differ only by where the loop settled (#193, #239), and runs solved on different days
  or with different methods are compared as if alike.

I built an answer in my fork as an opt-in for local installs, the way `OWL_ASSISTANT=1` turns on
the Assistant. I am posting it as a design question first: it is large, and whether it belongs in
Owl at all is your call.

**The shape.** `OWL_LIBRARY_DIR=<folder>` adds a "Run Library" section (four pages: Library, Run,
Compare, Queue) to the existing app. Three layers:

1. **Storage: one folder per run, on the user's disk.** A run holds its inputs as one JSON
   document (the case dictionary and the HFP tables, hashed, so identical inputs are recognized),
   and, generated from it and then frozen, the `Case.toml` and `HFP.xlsx` Owl reads today, plus a
   small `run.json` (name, parent run, notes, plan year). Cases come in and go out as Owl's own two
   files, so Excel stays the editor: export, edit, import as a new run. A solved run is never
   edited in place: saving changes makes a new run whose parent is the old one, so the runs build
   up into a history. `owlcli run` on a run's `Case.toml`, with the solver options its record
   lists, reproduces it in its plan year.
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
   methods or on different commits. Optionally, each run is also solved under a simplified model
   (Medicare off, SS taxability pinned at 0.85, LTCG optimized) as an ordering check: does it rank
   the two the same way? It mis-prices marketplace years, so there it does not overrule.

It is meant for installs run from source (`owlplanner.sh`); the hosted app would never set the
variable. Nothing leaves the user's machine: the library is a folder they chose, holding the same
files they would otherwise download.

**What building it taught me** (each found by a test or a review, and fixed):

- **A run belongs to one calendar year.** The plan starts in the year of the solve whatever
  `start_date` says (`_setStartingDate`: "Year is ignored"; the log even echoes the stale year).
  Balances entered in January 2026 and solved in 2027 are read as January 2027 balances, and the
  2026 rows of the HFP are read as history before the plan, with no warning. The library therefore
  records each run's plan year and refuses to solve it in another year. Within the year, a run with
  fixed claiming ages gave identical results on two different days (the library stores a `today`
  start date as the day it was captured; checked on one case).
- **A solved Plan does not pickle on `dev`**: `pickle.dumps` on a solved jack+jill raises
  `TypeError: cannot pickle '_io.TextIOWrapper' object`, from the logger's streams. A
  `__getstate__`/`__setstate__` pair on `Logger` that drops unpicklable streams and restores the
  default pair (close to the policy its `__deepcopy__` follows) is enough.
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

The run page also carries two extras that could come later or not at all: the years whose income
sits within 5% of a threshold the model knows (IRMAA tiers, the 0% gains bracket, the SS bands, the
marketplace limits, NIIT), with the price of crossing it, and a one-year cash-flow Sankey.

**What it would change in existing code.** Most of it is new files (`src/owlplanner/library/`, four
pages, a launcher), with no new dependency. In existing code:

- `mylogging.py`: the `Logger` pickling above; `version.py`: a retry of the git calls behind
  `engine_commit` (several processes stamp the code at once);
- `ui/owlbridge.py`: the `genDic` fix and an `openCaseFromPlan` that sets the keys a solve would
  (`caseStatus`, `summaryDf`, `metricsDict`, the log streams); `ui/sskeys.py`: opening a case from
  a Plan, and a mark of the run a case was opened from; `ui/main.py`: the section, the localhost
  check, the Assistant off in library mode;
- `cli/formatters.py`: more `plan_to_dict` keys (the claiming ages used; per-year wages, pension,
  SPIA income and withdrawals; the extras' data), and the objective's error bar in
  `plan_convergence`, so `owlcli --json` and the MCP compare tools gain keys too.

**Questions.**

1. Is this something you would want in Owl, as an opt-in for source installs, or would you rather
   it lived as a separate project (as Owl-budget does) that imports `owlplanner` and adds pages?
2. If in Owl: are Streamlit pages behind an environment variable, like the Assistant, the right
   form?
3. The comparison's 1% band for the loop comes from my measurements in the fork, where differences
   between variants under about 1% sometimes had the wrong sign under the loop against local search
   and the exact model. Owl's "Objective error bar" covers a loop that oscillates but is 0 for a loop
   that settled on one of several fixed points. For local search the band is a conservative
   placeholder: its measured shortfalls against branch-and-bound were \$15-74 a year. Would you
   rather have a band per method, or a measure Owl reports itself?
4. The plan year: the library refuses a run outside its year. Would you rather Owl itself warn
   when `start_date` names a year other than the current one? A small core change that would help
   anyone who reloads last year's case file, library or not; I can file it on its own.

The fork's code is public (`src/owlplanner/library/`, `ui/Library.py`, `ui/Run.py`,
`ui/Compare.py`, `ui/Queue.py` on `fmateoc/Owl` `main`), with its design notes in
`fork-notes/run-library-design.md`. If you want any of it, I would build a PR on stock `dev` in your
shape; the pickling and `genDic` fixes could come first on their own.

# Running the fork locally

How to install the fork on your own computer, enter the household's data, run Owl, and read the
results. Everything here runs on your machine; nothing needs a network connection after the
install (2026-11-01).

**Checked in a cloud session on the synthetic household only** (`fork-notes/synthetic/`), not on
Windows and not on a case built from the real template: see "What was checked" at the end.

## Not the MCP server

`owlcli serve` (the "MCP server" in Owl's documentation) also runs locally, but its purpose is to
let an AI app (Claude Desktop and the like) drive Owl, so the case's figures would go to the AI
provider. That defeats keeping the household data offline: do not use it, nor the
**Tools → Connect your AI** page, nor the Assistant page (shown only when `OWL_ASSISTANT=1` is set).

## 1. Install (once)

Install `uv`: on macOS or Linux `curl -LsSf https://astral.sh/uv/install.sh | sh`; on Windows see
`INSTALL.md`. Then clone **the fork** (upstream lacks the budget profile, the Yonkers and NYC
taxes, STAR and itemizing); its `main` branch carries all the fork's work:

```bash
git clone https://github.com/fmateoc/Owl.git
```

```bash
cd Owl
```

The first `uv run` installs everything. The repository pins Python 3.14 (`.python-version`);
`uv run` builds its environment on it, and Owl solved under Python 3.14.6 (2026-11-01). The
`--python 3.11` in CLAUDE.md's setup was about a 3.14 pre-release.

To update later: `git pull`, then `uv sync`.

## 2. Enter the data

Two files, kept in `otherFiles/` (gitignored by upstream itself, so they never reach GitHub):

| File | What it holds |
|---|---|
| Case file (`.toml`, plain text) | names, birth dates, balances (in \$k), SS PIAs, state, locality, school district, objective, solver options |
| Household Financial Profile (`.xlsx`) | one sheet per person, year by year (wages, IRA contributions, `months worked`, big-ticket items); `Budget` (core spending, rent, property tax, HOA, care, ...); `Debts` (the mortgage); `Fixed Assets` (the condo) |

Two ways to start:

- **The baseline only:** copy the template and generate an empty workbook, then fill in the
  `TODO`s with a text editor and Excel:
  ```bash
  mkdir -p otherFiles && cp fork-notes/phase0/Case_us.template.toml otherFiles/Case_us.toml
  ```
  ```bash
  uv run python fork-notes/phase0/gen_hfp_us.py
  ```
- **The whole condo grid:** copy `fork-notes/synthetic/make_cases.py` to `otherFiles/` and replace
  its invented figures (balances, wages, PIAs, prices, property taxes, closing costs, care cost)
  with the real ones. It writes the case files, one workbook per purchase variant (place x year x
  cash or mortgage) and the scenario list for `run_suite.py`, which is much less work than 30
  workbooks by hand (`fork-notes/synthetic/README.md`, "Running it").

Rules that bite:

- `basic_info.names` must match the workbook's person-sheet names exactly.
- Save the TOML as UTF-8: an em dash pasted from Word stops `owlcli` with a `UnicodeDecodeError`.
- Balances are as of `start_date`.
- `anticipated wages` are the wages in AGI (pay less pre-tax 401k, deductible IRA and payroll HSA
  contributions).
- Big-ticket items are signed: negative = an expense.

`fork-notes/phase0/phase0-scenarios.md` (its checklist is at the end) and the docstring of
`fork-notes/phase0/gen_hfp_us.py` explain every column.

## 3a. Run it in the browser (to look around)

```bash
./owlplanner.sh --server.address=localhost
```

(`owlplanner.cmd` on Windows.) It opens `http://localhost:8501` in your browser; Ctrl-C in the
terminal stops it. `--server.address=localhost` keeps the page reachable from this computer only:
`owlplanner.sh` does not set it, and a server started without it printed a "Network URL" and an
"External URL", that is, it listened beyond this computer.

1. **Case Setup → Create Case**, tab **Upload Your Own Case File**: choose the TOML. The locality
   and school district show on that page.
2. Upload the HFP workbook in the box that then appears below it. The browser interface does not
   read the workbook named in the TOML; you upload it.
3. Check or edit the other Case Setup pages (Goals shows the "budget" spending profile; Account
   Balances, Fixed Income, Rates, Run Options).
4. **Results → Graphs** solves the plan when opened ("Re-run" after an edit); **Worksheets** has
   the year-by-year tables; **Reports** has the summary and the downloads (plan workbook, case
   file, HFP workbook).

Limits with the fork:

- Edits live in the browser session only: download the case file (and the HFP) from Reports to
  keep them.
- `withItemized` and `withSTAR` have no control on Run Options; they are taken from the TOML.
- Only the first move can be edited; the others are kept from the file.
- The Budget lines have no editor: they come from the uploaded workbook.
- "Load a Case Example" reads the example cases in `examples/` from your checkout
  (`ui/tomlexamples.loadCaseExample`), although its caption says GitHub.

## 3b. Run it from the command line (for the decisions)

```bash
uv run owlcli run otherFiles/Case_us.toml
```

This writes `otherFiles/Case_us_results.xlsx` next to the case.

- `uv run owlcli compare otherFiles/Case_us.toml --set ...` runs one variant against the base;
  `phase0-scenarios.md` has the command for each question (retirement year, SS ages, locality,
  rent against buy, the 2032 reversion, the 2027 ACA benchmark).
- `fork-notes/synthetic/run_suite.py` runs the whole scenario set at once and writes a `report.md`
  (`fork-notes/synthetic/README.md`).
- `fork-notes/phase5/work_sweep.py` decides the work and claiming-age variants
  (`phase0-scenarios.md`, section 4).

Expect minutes per solve. The template's `withSSAges = "optimize"` with
`withMedicare = "optimize"` makes every claiming-age candidate a full MIP: fix the ages in a run
(`--set solver_options.withSSAges=fixed --set "fixed_income.social_security_ages=[70.0, 70.0]"`),
or decide them with `work_sweep.py`.

## 4. Read the results

The results workbook has these sheets: Config (the TOML), Income, Cash Flow, Sources and Accounts
per person, Household Sources, HSA, Balance Sheet, Liquid Balance Sheet, Taxes, Budget,
Allocations, Rates, and **Summary**.

Start with **Summary**: net spending per year in today's dollars, the tax breakdown, SS withheld by
the earnings test, the final bequest with the condo. The browser's Graphs and Reports pages show
the same data.

Before calling a difference between two runs:

- Compare runs made the same day: plans start "today", so results move from one day to the next.
- Differences under about 1% between runs on the default loop can be loop noise, of either sign.
  For decisions use `breakpointMethod = "local-search"` and the exact-LP cross-check
  (`phase0-scenarios.md`, section 3; CLAUDE.md, "Loop noise").
- Check the log for a "Cash flow balance" warning.

## What was checked (2026-11-01, cloud container, synthetic household)

- `owlcli run` on `Case_ari+noa_condo.toml` with the ages fixed at 70 under local search: status
  solved, 5 min 10 s, a 17-sheet workbook; Summary net spending \$165,362/yr.
- The browser interface, driven by a headless browser:
  - the fork's TOML loaded with locality Yonkers and its school district, and the HFP uploaded;
  - Goals showed the budget profile;
  - Graphs solved the case (on the loop, so not the same run as above): \$164,153/yr and a
    \$760,861 condo in the bequest;
  - Reports showed the synopsis and the downloads.
- `uv run` replaced a Python 3.11 environment with 3.14.6, and `owlcli run` solved
  `examples/Case_jack+jill.toml` under it.

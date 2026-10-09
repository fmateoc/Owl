# Owl-budget: requirements brainstorm (draft, 2026-10-08)

Fork-only working note, our input to the brainstorm the maintainer proposed on #175. The condensed
version for the issue is `issue-175-reply-2.md`. What is checked against Owl's code is marked
**(checked)**; rules and data recalled rather than read from a source are marked **(recalled)**.

## The maintainer's frame (#175, relayed 2026-10-08)

- Budgeting is critical, and a different problem from decumulation. People start from the past
  ("what was the number last year?").
- Categories differ by person: flexible and extensible, structure likely saved as JSON.
- A separate project: analyze past trends, compare rent vs buy, suggest medical expenses by
  health status and urban vs rural, drawing on the literature.
- UX parallel to Owl; two browser tabs that exchange files. Owl compares the impact on retirement;
  "Owl-budget" builds and provides the profiles and the HFP.
- It can simplify filling the HFP: wages from current wages and expected raises, 401(k)
  contributions; the last 5 years as data for extrapolation.

## 1. Boundary

Owl-budget estimates what the household will **spend** and **earn and save before retirement**.
Owl decides how to **fund** it (withdrawals, conversions, claiming ages, taxes). Nothing that Owl
optimizes or computes should be entered in Owl-budget, and nothing Owl-budget produces should need
an optimizer.

Non-goals: tax computation, portfolio advice, bank-account aggregation, any optimization.

## 2. The interface with Owl (decide this first)

Everything else can evolve; this contract is what both projects maintain.

1. **Two outputs.** (a) A spending profile file (JSON) that an Owl case points to, as it points
   to an HFP workbook today. (b) An HFP workbook in Owl's existing format (person sheets, Debts,
   Fixed Assets), so that Owl needs nothing new to read it.
2. **The profile is a specification Owl evaluates, not a year-by-year array.** The survivor step
   sits at the first death, and Owl rebuilds plans with other lifespans
   (`clone(expectancy=...)`, lifespan sampling) **(checked)**. A frozen array would be wrong for
   every lifespan but the one it was built with. So the file carries lines with their rules
   (years, growth, what a survivor keeps), and Owl turns them into its spending shape for each
   horizon. Owl's side is small: the fork's `budget.evaluate()` + `profile()` does it in about
   100 lines, with no LP change **(checked)**.
3. **Units and time.** Amounts in today's dollars; calendar years; real growth per line. Owl
   applies its single inflation path **(checked: the profile is real, and Owl multiplies it by
   `gamma_n`)**. Category-specific inflation (medical, education) is expressed as real growth.
4. **Scale semantics.** Owl's spending is the profile times one basis. Under `maxBequest` the
   basis is the first year's spending; under `maxSpending` the optimizer scales the whole profile,
   so a rent line scales with travel **(checked: fork, `test_max_spending_scales_the_whole_budget`;
   measured: same plan as a fixed rent at fixed spending, up to $2,821/yr apart under
   `maxSpending`)**. Decide whether v1 is "shape only" (no Owl LP change) or also marks
   **non-scalable lines** (rent, insurance, a car loan), which needs a fixed outflow next to
   spending in Owl's LP: the "constraint" option the maintainer mentioned. Our recommendation:
   shape only in v1; it answers rent vs buy, which is read at fixed spending.
5. **Categories survive the trip.** Owl reports net spending by line, and the fork's NJ property
   tax deduction reads the property-tax and rent lines **(checked: fork)**. Totals alone would
   lose both.
6. **No double counting.** The budget excludes what Owl already charges **(checked)**: federal and
   state income tax, Medicare Part B/D premiums and IRMAA, ACA premiums, loan payments in
   `Debts`, `big-ticket items`, contributions. It must include what Owl does not charge:
   out-of-pocket medical costs (Owl's `other_medical_expenses` only caps HSA withdrawals; it is
   not spent **(checked)**), property tax, insurance, maintenance, long-term care.
7. **Versioning and validation.** A schema version in the file; Owl refuses a version it does not
   know, and refuses lines it cannot honor (as #173 does for bad property links), instead of
   reading them as something else.
8. **Round trip.** Owl can hand the file back unchanged (a case saved from Owl keeps the profile),
   and Owl-budget can reopen an HFP it wrote.

## 3. Data model (JSON)

- **Categories:** a tree with user-defined names (Housing > Rent; Health > Dental). A starter
  taxonomy, mappable to the BLS Consumer Expenditure Survey categories so that comparisons with
  published averages are possible **(recalled: the CE survey publishes spending by category,
  age and region; not checked)**.
- **Line:** category, name, amount (today's $), start and end year (or an age of a person),
  recurrence (yearly, every N years, once), real growth, survivor share, tags (household vs
  personal; deductible types such as property tax), notes, source (history, estimate, rule).
- **Uncertainty:** an optional low / base / high per line, or named scenarios (lean, base,
  comfortable). Owl compares scenarios; it does not need distributions. This answers the
  maintainer's caution about false certainty with ranges instead of point estimates.
- **History:** per category and year, actual spending (nominal), with the year's CPI factor.
- **People:** names and birth dates matching the Owl case (needed for ages, survivor rules,
  wages); the file should refuse a case whose names differ, as Owl's HFP does.

## 4. From the past to a projection

- **Input:** the last five years by category, typed in or imported from CSV (bank or card
  exports, categorized by the user once and remembered by rule). No credentials, nothing stored on
  a server.
- **Normalization:** to today's dollars with CPI-U **(recalled; the series is from BLS)**, so trends
  are real.
- **Projection:** per category, a method the user picks and sees: last year, average, median,
  real trend; one-off spikes flagged and excludable. Every projected number can be overridden.
- **Retirement transitions:** categories that change at retirement (commuting, work clothes,
  payroll-deducted items fall; travel, hobbies, health rise), offered as editable defaults, not
  imposed. The smile shape becomes explicit lines (travel ending at 75, care starting at 80)
  instead of a formula.

## 5. Modules

1. **Housing (rent / buy with cash / buy with a mortgage, moves).** Output: budget lines (rent,
   or property tax, insurance, maintenance, HOA), and the HFP entries Owl already reads: price or
   down payment as a big-ticket item, the home in Fixed Assets, the mortgage in Debts linked to it
   (#173). Moves and a later sale split the lines at the move year. Rules of thumb (maintenance as
   a share of value, insurance by region) as editable suggestions with sources. Not modeled in Owl
   upstream and outside this module: the mortgage interest deduction (itemizing).
2. **Health.** Out-of-pocket estimates by age, health status and region from published surveys
   (MEPS is the usual US source **(recalled)**), clearly separated from the premiums Owl computes.
   Long-term care as a scenario line (duration, cost, start age) rather than a probability inside
   the budget.
3. **HFP builder.** Per person: current wages, expected raises (real), retirement or part-time
   dates; contributions (401(k), IRA, Roth, HSA) and employer match, checked against IRS limits by
   year and age (catch-up from 50, the higher catch-up at 60-63 **(recalled, SECURE 2.0; verify)**).
   It must follow Owl's conventions **(checked in Owl's docs)**: *anticipated wages* net of all
   contributions; employer contributions inside the *ctrb* columns; HSA contributions stop at
   Medicare age; nominal dollars. Roth conversions stay with Owl.
4. **Comparison.** Several budgets side by side (variants of housing, location, lifestyle),
   written as several profile files for `owlcli compare` or Owl's case comparison.

## 6. UX

- Streamlit with Owl's theme and page structure, so the two feel like one tool. Two tabs, files
  exchanged by download and upload; later, if both run locally, a shared folder.
- Every number shows where it came from (history, rule, override).
- Charts: history vs projection by category; the resulting profile in today's dollars; the
  survivor step; the split housing / health / other.

## 7. Data the project would maintain

CPI-U, IRS contribution limits, survey averages by category and region, medical cost tables.
Each dated and sourced in the file that holds it, as Owl's tax tables are. This is where the
maintainer's "diminishing returns" applies: keep the tables few and national unless a user
supplies local numbers.

## 8. Questions for the maintainer

1. Repository and ownership: a new repo under his account, with us contributing?
2. Is the Owl side of the contract (section 2, items 1-3, 7) acceptable in Owl's core? It is
   the part both projects depend on, and it does not change the LP.
3. Shape only, or also non-scalable lines (section 2, item 4)?
4. JSON for the profile only, or also for what the HFP holds today (wages and contributions)?
5. Uncertainty: scenarios only, or ranges per line?
6. Which literature sources he has in mind for health and region (to check them before relying
   on them).

## The maintainer's answers (relayed 2026-10-09) and where they leave the design

1. **Ownership:** a new project under his account for now; a managed structure later (Owl has
   2,000+ Streamlit users, 10-20 new per day).
2. **Owl's side of the contract in core:** yes ("options and hooks almost all there"). Checked:
   upstream's `gen_spending_profile` builds `flat` and `smile` only; an evaluated external
   profile is new code (the fork's `budget.py`).
3. **Shape only or non-scalable lines:** open, pending "how the profile interacts with
   longevity". Our answer: evaluation per horizon handles the horizon; non-scalable (essential)
   lines turn a long life or a bad sequence into a cut in discretionary spending, then into
   infeasibility, which lifespan sampling already counts as a full shortfall. Prototype in the
   fork (2026-10-09): the `essential` column, `Plan._add_essential_profile`.
4. **Formats:** JSON for AI, Excel for retirees, possibly both; MCP on both sides so that
   ladders (parameter sweeps) of budgets can run against Owl. Our position: one schema, JSON
   canonical, Excel as the editable view, round trip tested.
5. **Sources:** his web search (BLS CE, HRS, EBRI, Vanguard, Fidelity). Checked as far as the
   proxy allows (bls.gov, FRED, ebri.org, fidelity.com blocked; search results and reprints
   only): BLS CE 2024 65+ figures match FRED's copies; Fidelity 2026 $185,500, 45% of it Medicare
   B/D premiums that Owl charges already; EBRI 2024 31% spend more than they can afford. The
   budget must also cover the ~10 years before retirement: Owl's plan already starts today, but
   Owl charges no payroll tax (no FICA/OASDI in its source, by grep), so a working-years budget
   needs a payroll-tax line.
6. **Cost function (his new point):** budget fixed -> bequest is the objective; bequest fixed ->
   spending is; spending needs are elastic, so split core from discretionary. Our reading:
   g_n = E_n + k D_n, `maxSpending` maximizes k, `maxBequest` at k = 0 gives the reserve above the
   core, and upstream's spending-bequest frontier traces k against the bequest. Draft reply:
   `issue-175-reply-3.md`.

## Our household's use, as a test case

NY metro couple: rent vs buy with cash vs buy with a mortgage, Yonkers / NYC / Westchester / NJ,
a possible later move, part-time work, healthcare costs as the main worry. The fork's Phase 2b
(Budget sheet, `budget.py`, the `"budget"` profile) already covers section 2 items 2-6 for one
format; it can serve as the reference consumer on Owl's side.

# Draft reply on #175 (Owl-budget requirements), for the user to post

Status: draft, 2026-10-08. Not posted. Longer working version: `owl-budget-requirements.md`.

---

Agreed on a separate project, and on starting with requirements. Here is our first pass, ordered by
what both sides would have to live with.

**1. The contract with Owl (worth settling first)**

- Owl-budget writes two things: a spending-profile file (JSON) that a case points to, like
  `HFP_file_name` today, and an HFP workbook in Owl's current format (wages, contributions, Debts,
  Fixed Assets), so Owl needs nothing new to read that part.
- The profile should be a specification that Owl evaluates, not a year-by-year array: lines with
  their years, real growth and what a survivor keeps. The survivor step sits at the first death,
  and `clone(expectancy=...)` and lifespan sampling rebuild the plan with another horizon, so a
  frozen array would be right for one lifespan only. Evaluating it is small (about 100 lines in
  our fork) and doesn't touch the LP: the lines' sum, divided by its first year, becomes `xi_n`.
- Amounts in today's dollars, real growth per line; Owl keeps applying its single inflation path.
- Scale: under `maxBequest` the first year is the spending level; under `maxSpending` the whole
  profile scales, rent included. We measured that the two readings give the same plan at fixed
  spending and differ by up to $2,821/yr under `maxSpending` on our test couple. Shape only for a
  first version? Non-scalable lines (your "constraint" option) would need a fixed outflow next to
  spending in the LP.
- Categories survive the trip, so Owl can report spending by line.
- No double counting: the budget leaves out what Owl charges (income taxes, Medicare premiums and
  IRMAA, ACA premiums, Debts payments, big-ticket items, contributions) and includes what it
  doesn't. Out-of-pocket medical costs, for instance: `other_medical_expenses` only caps HSA
  withdrawals and is not spent.
- A schema version, and Owl refusing a file or a line it can't honor, as #173 does for property
  links.

**2. Owl-budget itself**

- Categories as a user-editable tree, with a starter set that maps to published survey categories
  so that comparisons with averages are possible.
- Past years by category, typed or imported from CSV exports (no credentials, nothing on a
  server), put in today's dollars with CPI, projected per category by a method the user sees and
  can override (last year, average, trend), with one-off spikes flagged.
- Retirement transitions as explicit, editable lines (commuting ends; travel until 75; care from
  80), which also makes the smile shape explicit.
- Ranges or named scenarios (lean / base / comfortable) instead of single numbers, compared in Owl.
- Modules: housing (rent / buy with cash / buy with a mortgage, moves; the purchase and loan go to
  big-ticket items, Fixed Assets and Debts with the #173 link), health (out-of-pocket by age,
  health status and region; long-term care as a scenario line), and an HFP builder (wages with
  raises and retirement or part-time dates, contributions and employer match within the year's
  limits, following Owl's conventions: wages net of contributions, employer money in the `ctrb`
  columns, HSA contributions stopping at Medicare).
- Same look as Owl (Streamlit), two tabs exchanging files.
- Data tables kept few, dated and sourced, as Owl's tax tables are.

**3. Questions for you**

1. A new repository under your account, with us contributing?
2. Would the Owl side of the contract (the profile file, its evaluation, versioning) go into Owl's
   core? It's the part both projects depend on.
3. Shape only at first, or non-scalable lines too?
4. JSON for the profile only, or eventually for what the HFP holds as well?
5. Which literature sources do you have in mind for health and regional costs?

Our own case (NY metro couple: rent vs buy, a possible move to NJ, part-time work, healthcare costs
as the main worry) can serve as a test case, and our fork's budget profile can serve as a reference
for Owl's side of the contract.

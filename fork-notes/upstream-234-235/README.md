# Upstream issues #234 and #235 (filed 2026-10-26): validity and effect on the fork

**Update 2026-10-28:** #234 fixed upstream (`3931c8a`) and merged: only a round trip that realizes no gain is
netted. Rerun: `scan234_2026-10-28_dev1bdc3b2.txt` (jack+jill nets one year, gain fraction 0).

Checked 2026-10-26 on `claude/clever-hypatia-6l8txj` (upstream `dev` = `main` = `4dcfabb`, so
neither is fixed). Both were filed by `rationalpiper` and have no comments yet. Their texts were
read through the fetch tool, which returns summaries, not verbatim text. The reporter's scripts
(`docs/upstream/repro-v58.py`, `repro-v56-earnings-test-preplan.py`) are not available here.
Our #231 comment, posted by the user, is on #231, with no reply yet.

## #234: `_netSurplusRoundTrip` hides a taxable sale and rebuy

**Origin:** upstream's code, not ours. `def _netSurplusRoundTrip` first appears on `dev` in
`8bd1f3d` (2026-10-22). The fork has it unchanged.

| Claim | Verdict | Checked |
|---|---|---|
| The netting runs after the solve and nets only in years with no federally taxed gains (`q_pn[1] + q_pn[2] <= 1`), taking `min(d, w_txbl, s)` off the withdrawal, the deposit and the surplus | **Valid** | Code (`plan.py` `_netSurplusRoundTrip`, called at the end of `_aggregateResults`) |
| `Q_n` and the state tax are computed from the gross flows, so a netted year shows gains and state tax its displayed flows do not explain | **Valid** | Code (netting runs after `Q_n`, `st_T_n` are set); the state test is absent: no state term in the netting condition |
| The cost basis follows the gross flows (the rebuy enters basis at full value) | **Valid** | Code (`_update_gain_fraction`: `c_n = kappa_n + d_n`, basis reduced by `w_n / b_n`; it runs inside the loop, before the final aggregation nets) |
| The surplus split is fixed (`d_0 = (1-eta) s`, `d_1 = eta s`), so the LP can be forced to deposit into one spouse's account to fund the other's | **Valid** as to the constraint | Code (`_add_surplus_deposit_linking`); the docstring's "a round-trip that costs anything is never chosen" ignores it |
| Local search starts from the netted `w_ijn` | **Valid** | Code (`localsearch.LocalSearch(self, self.w_ijn.copy(), ...)` after the loop's aggregation; used as "loop plan" in `_incumbent`). It is a starting band for repairs, so the effect is on search quality, not on the validity of the result |
| Repro numbers (PA couple: $25,022 Q gap, +$484/yr at `eta = 1.0`, basis replay +$2,299-3,792) | **Not reproduced** | The issue omits horizons, rates, allocations and objective. Our rebuilt case (maxSpending, guessed inputs) had no surplus at all, so it nets nothing in PA or NY (scratch probe, not kept) |

**Fork examples** (`scan234.py`, output `scan234_2026-10-26.txt`, fork code, default options):
only jack+jill nets, $118,626 over 2034, 2036 and 2038, all with a tracked basis. Tennessee
has no income tax, so #234's state-tax point does not arise there, but the basis one does.
In those years the hidden round trip is a gain harvest at 0% federal. Its basis step-up
lowers every later year's gains, and the worksheet does not show it.

**Household:**
- The template (`fork-notes/phase0/Case_us.template.toml`) uses `eta = 0.5` and has a cost-basis
  field. NY taxes gains in the state row, so a netted year would hide NY (and Yonkers) tax on
  a sale the worksheet does not show.
- Whether the household's plans net at all is unknown here. Work years produce surplus, but a
  round trip needs a taxable withdrawal in the same year.
- To check on the real runs, two cheap steps: record the netted amount per year (the spy in
  `scan234.py`), and compare `eta` 0.5 against 0 and 1 as a sensitivity. `eta` is a modelling
  constraint, not a household fact.

## #235: earnings test with history before the plan

**Origin:** ours (`socialsecurity.earnings_test`, PR #222). The behaviour is the premise our
docstring states: "Years before the plan carry no earnings here, so a person entitled before
the plan has their initial grace year in their (pre-plan) entitlement year and only the annual
test in plan years". `initial_grace_year` says the same for a year missing from its map. So
this is a documented limitation, and #235 is a feature request with the law behind it.

| Claim | Verdict | Checked |
|---|---|---|
| Owl's numbers: case 1 pays 1,408.33 in 2026 and 15,491.67 in 2027, with 12 ARF months; cases 2-3 pay 16,900 in 2026, 2030 and 2031, with 0 ARF months | **Reproduced** | `check235.py`, output saved (PIA 2,000, born 1963-06-15, claim 62y1m) |
| The law's side: 2026 is the grace year in case 1 (7,041.67 paid in 2026, 16,900 in 2027); 6 pre-plan crediting months give 1,458.33/mo from FRA ($600/yr); 12 give $1,200/yr and 24 give $2,433.33/yr | **Arithmetic checked** (5 × 1,408.33; `arf_self_factor` gives 1,458.33 / 1,508.33 / 1,611.11) | The rules (404.435(b)(1), (a)(7); 402(q)(7)(A); 404.412(b)) are recalled as stated, not reread this session; our step-1 code cites the same 404.435 rules |
| The proposed inputs reproduce today's results at their defaults | Not checked (the reporter's patch is not available) | |

**Household:** none today if neither spouse has claimed before the plan starts. It is not
checkable here: the claiming status is in `otherFiles/`. It becomes relevant later: plans start
"today", so a spouse who claims at 62 while still working is in #235's situation in every plan
built after that year. A later run would then need the three facts the issue proposes.

## Action

None in code. #234 is upstream's own display and seeding logic. #235 extends our code in a
direction the maintainer decides. When either lands, take his version. For #234, re-run
`scan234.py` then. Nothing new seems worth commenting on either issue: the jack+jill netting is
consistent with #234's bullet 3 and adds no new mechanism.

# Third review of run-library step 3 (2026-11-02)

Scope: branch `claude/run-library-step3` at `01d0846` (both increments, the P1-P14 fixes and
Q1/Q3), reviewed in a Linux cloud container. The two earlier passes ran on Windows. This
pass read the code fresh, re-ran the checks on Linux and probed what the earlier reviews did
not cover. Findings **W1-W9**. Q2 and Q4-Q9 of review 2 are still open and are not repeated
here. Each claim below says whether it was executed or read. **W1-W4 were fixed on
2026-11-02 on `claude/run-library-step3`** (their entries say how); W5-W9 are open.

## Checks run here

| What | Result |
|---|---|
| Full suite, `pytest -n 4 -q -p no:cacheprovider` | **3885 passed, 1 skipped** (11:01). Windows had 3884 + 2 skips; the POSIX-only tzset test runs here |
| `fork-notes/synthetic/check_library_compare.py` (after `make_cases.py`) | **9/9**, every figure as in PROGRESS (108,959 / 760,861 / 0 / 310,107; -13.34%; d_pair -14,530, d_exact -15,672; 2027 at 974,971 both sides) |
| flake8 / ruff over `src tests ui` | clean except upstream's own known items (the `tests/stochastic` E301/E304 and four B905s) |
| Probes | `p1_solve.py` (the baseline through the worker, its `cash_flow` read the way the page reads it), `p2_compare.py` (stub results through `compare.compare` / `what_moved`), `p3_app.py` (the Streamlit message-then-rerun pattern under AppTest, Streamlit 1.66.1), `p4_delete.py` (Delete during a real detached solve). They were kept in the session's scratchpad, not committed |

## Should-fix

**W1. The one-year Sankey drops negative flows, and on the household's own shape that
happens in most years (executed).** `ui/Run.py:97` keeps only values `> 0.5`. On a NY plan
with STAR, `st_T_n` (state + recapture + local - STAR) goes negative once the refundable
credit exceeds the tax (CLAUDE.md, "STAR"). On the synthetic baseline (Yonkers, STAR),
"State and local tax" is negative in **23 of its 28 years** (2031 -714, 2032 -1,708, ...).
In each of those years the drawn uses exceed the sources, by up to **\$3,492**, while the
caption says "\$X in, the same \$X out". The same applies to a negative `other inc` (#225)
or any other signed row. Check 8 passes because it sums the raw arrays and its Sankey year
(2027) comes before the first STAR year (2031). Fix: show a negative use as a source (for
example "State tax refund (STAR credit)") and a negative source as a use, then filter. Make
check 8 apply the page's own filter in every year.

**Fixed.** `view.cash_flow_year(result, n)` returns the year's drawn sides: a negative use
becomes a source named "..., net refund", and a negative source becomes a use named
"..., net outflow". Flows of fifty cents or less are left out of both sides. The Sankey,
its default year and its caption read it; the caption now gives both totals, as drawn, and
says a negative tax is drawn as a source. Check 8 also balances the drawn sides in every
year: worst 2.00, with 23 years that have a row moved across (the old filter gave 3,492).
Test: `test_a_negative_flow_is_drawn_on_the_other_side` (test_view.py).

**W2. "Home at the end" is judged against the 1% loop-noise band, but no solve can move it,
so R3's verdict can be wrong (executed on stubs; the source read).** `home_at_end` =
`final_bequest_today - final_bequest_savings_today` =
`(fixed_assets_bequest_value - remaining_debt_balance) / gamma_N` (`export._compute_estate`).
Both terms are set in `Plan.processDebtsAndFixedAssets` (plan.py:2678-2740) from the Debts and
Fixed Assets tables and `gamma_n`, before any solve. `compare.py:281` still judges it with
`_pair_tolerance` (1% of A's home, about \$7.6k on the baseline). The probe gives B 3% more
spending and \$6,000 less home. The home row reads "~ the loop can make it, with either sign",
which is false, and the verdict is **"the second result leads"**, though R3 calls it a
trade-off (more spending, less home). A small remaining loan balance or a price or commission
difference is that size. Fix: judge the home only against `TIE_DOLLARS` (no loop band and no
gap: it is not a solve output).

**Fixed.** `compare.difference(..., from_inputs=True)` judges the home only against
`TIE_DOLLARS`, with the note "set by the inputs (no solve moves it): no noise band
applies". The probe's pair now reads "trade-off". Tests:
`test_the_home_is_an_input_so_no_noise_band_hides_a_home_difference` and
`test_a_proved_pair_judges_the_home_without_its_gap`. `test_within_noise_everywhere...`
had a +300 home difference that the band used to swallow; it now uses +0.4.

**W3. Messages shown just before `st.rerun()` never reach the user (the mechanism executed;
the pages read).** `st.rerun()` ends the script run, and the next run clears every element it
does not draw again. Only toasts survive (probe: after the click `at.error == []` and
`at.info == []`, the toast is present). Affected:
- `ui/Library.py:82` "Cannot import this case: ...", then the rerun at :128;
- `ui/Library.py:103` "Cannot save this case yet: ...", then :148;
- `_report_saved`'s `st.info` "Identical to *X*: not saved again" and its "Not applied"
  caption (V8's point, step 1), lost the same way;
- `ui/Run.py:425`, the plan-year refusal of Solve (R1's ScenarioError), then :428.

The user clicks and nothing appears to happen. The pages themselves were not driven here
(AppTest has no file_uploader). Fix: keep the message in `st.session_state` and show it on
the next run, or skip `st.rerun()` on failure.

**Fixed.** `libraryjobs.flash(kind, text)` queues a message in the session, and
`libraryjobs.show_flashes()` draws it once, under the title of the Library and Run pages.
The import and save errors, the "identical" notice and its "Not applied" caption, the
Delete refusal (W4) and the Solve refusal (now also catching `JobsError`) all go through
it; toasts stay toasts. AppTest tests (`TestMessagesSurviveTheRerun`): a failed save of the
current case is shown after the rerun and not on the render after that, and a refused
Solve says why.

**W4. Delete is allowed while the run has a waiting or running solve (executed on Linux).**
`ui/Library.py:199` calls `lib.delete_run`, and `store.delete_run` moves the folder with no
check on jobs. The probe queued "decision" on the synthetic baseline, waited for `running`,
then deleted. The folder went to `trash/`, and `manager.jobs()` returned `[]`, so the Queue
page has nothing left to cancel or kill. The worker (PID 1810) was still solving 60 s later,
uncounted by `max_parallel`. It later exited without writing a log or record, and the trashed
`status.json` stays `"running"`. On Windows the rename of a folder with open handles probably
raises instead and shows a page exception (not tested). Fix: refuse Delete, or disable the
button, while any job of the run is waiting or running, and say "cancel it on the Queue page
first".

**Fixed.** `JobManager.delete_run(run)` refuses with `JobsError` ("... has a solve still
waiting/running ... Cancel it on the Queue page first") and checks and moves under the
manager's tick lock, so the ticker cannot dispatch in between. The page's Delete goes
through it and shows the refusal (W3). Tests: `TestDeleteRun` (test_jobs.py: waiting,
running, cancelled-then-deleted, no solve) and two AppTest tests (refused with a waiting
job, deleted without one). The page tests' fixture left its hand-written solved results
at `waiting`, which a real worker never does; they are now `done`.

## Minor

**W5. Under maxBequest the score already contains the home, so R3's two numbers overlap
(executed on stubs).** `view.score` is `final_bequest_today` (savings + home) under
maxBequest, and the leads rule reads score and home. Probe: B has +\$150k home and -\$100k
savings, and the result reads "the second result leads" on both numbers. R3 calls this a
trade-off. `run_suite.score` does the same, and the household runs maxSpending. Under
maxBequest the two numbers should be savings and home.

**W6. "What moved" aligns years by position (executed on stubs).** `compare.py:248` takes B's
years as labels and indexes both plans by position. Two results with different first years
(runs of different plan years, which S13 already flags) compare A's 2027 with B's 2028 under
the label 2027. Fix: align by `year`. Separately, the "lifetime" row adds 28 years of nominal
dollars next to headline numbers in today's dollars. The caption says nominal, but a sum in
today's dollars would read better.

**W7. The NIIT entry is described as a cliff; it is not (source read).** `computeNIIT`
charges `3.8% x min(MAGI - threshold, I_n + Q_n)` (tax_federal.py:1289), a kink. The page's
note at `thresholds.py:352` ("3.8% of all net investment income, once MAGI crosses the
line") and PROGRESS ("the crossing is a cliff on all net investment income") overstate it.
The listed cost is computed correctly, by `computeNIIT` itself. Also, `thresholds.py:337`
hard-codes 200k/250k instead of reading `tx.niitThreshold`.

**W8. `run_zip` ships `plan.pkl`; design section 10 says a run from a zip "comes without its
pickles" (read).** The docstring (store.py:523) says the pickle is loaded only against the
hash and code stamp in its own `record.json`. But `record.json` travels in the same zip, and
`Library.runs()` accepts a folder copied in by hand. So for an unzipped folder the check
compares the pickle with a hash it brought along. That is an undeclared deviation from R10.
Fix: leave `plan.pkl` out of the zip (it is a cache; "Open in Owl" says "solve again"), or
declare the deviation.

**W9. Library mode does not keep the AI pages off (read).** Section 10 says "The AI pages
stay off", but `ui/main.py` adds the Assistant page whenever `OWL_ASSISTANT=1`, library
mode included, and the launchers do not clear the variable. It is opt-in, so this is
low-risk; either enforce it or reword section 10.

## Verified as sound here (re-derived, not taken from the earlier reviews)

- `decision_exact` = `run_suite.EXACT_GROUP` (loop, Medicare none, SS 0.85, LTCG optimize),
  read from both files.
- `discretionary_year1` = `k x budget.discretionary_n[0]`, as in `run_suite.solve_one`.
- `cash_flow_split`: its terms are `_check_cashflow_balance`'s (plan.py:7482-7506), with
  `Lambda` netted before the in/out split.
- The I7 tie rule: `max(ta, tb)` is a valid sufficient condition. Ordering two optima needs
  only the trailing plan's tolerance (v_a > v_b + t_b gives opt_a > opt_b). `work_sweep.py`'s
  report uses `ta + tb`, which is stricter, so the map can shade apart two cells that
  work_sweep calls unresolved. That is a difference between the two views, not an error.
- The localhost guard and the launchers' defaults.

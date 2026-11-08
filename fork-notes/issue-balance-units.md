# Issue draft: balances typed in dollars into the \$k fields solve "infeasible" with no hint

Status: **filed as #249 and closed by the user before the maintainer answered** (2026-11-08, after his #245 reply: the fork's \$20M warning is a heuristic after the fact, not validation at the input; CLAUDE.md, Conventions, "prevent at the input"). The fork keeps its warning. Was a draft (2026-11-07; `ux-qw-handoff-2.md` N4, QW-8.4, decision 4). For the
user to file on `mdlacasse/Owl`. Checked on upstream `dev` `73dc8815` (2026-11-07). Patch:
`fork-notes/issue-balance-units.patch` (`ui/Account_Balances.py`, a new
`tests/ui/test_account_balances_units.py`, and `tests/conftest.py`; applies to stock `dev` with
`git apply`; verified there: the two warning tests fail on stock `dev`, all three pass with the
patch; `tests/ui` and `tests/config` 410 passed with it). Repro script:
`fork-notes/issue-balance-units-repro.py` (run from a stock `dev` checkout with
`PYTHONPATH=src`). The output below is from real runs in this container.

The fork carries the same warning since the QW-1-QW-8 build (at \$50M), at \$20M since
2026-11-07.

---

**Title:** Account Balances: a balance typed in dollars into a \$k field solves "infeasible" with no hint

The balance fields on Account Balances are in thousands of dollars ("Taxable accounts (\$k)").
A balance typed in dollars there (90,500 for \$90,500) is read as \$90.5 million, and the
case then solves **infeasible**, with nothing pointing at the units.

**Repro (stock `dev` `73dc8815`):** `Case_jack+jill.toml` solved as it is, and with its
balances (and cost basis) multiplied by 1,000, as if typed in dollars:

```text
$ PYTHONPATH=src python issue-balance-units-repro.py examples/Case_jack+jill.toml
as entered ($k): taxable [90.5, 60.2] -> caseStatus 'solved'
typed in dollars (x1000): taxable [90500.0, 60200.0] -> caseStatus 'infeasible'
```

(Why the larger balances are infeasible was not traced; the point is that the page gives no
hint about the units.)

**The patch:** under the balance fields, one warning naming each balance of 20,000 or more
(\$20M), in dollars: *"Riley's taxable accounts: 60,000 here means \$60 million (amounts are
in thousands). If you typed dollars, divide by 1,000."* A warning, never a refusal: a real
balance above \$20M only gets a message it can ignore. \$20M catches dollars typed for any
balance from \$20,000 up.

The patch's test is an AppTest of Account Balances. On stock `dev` that page cannot run under
the test suite's frozen date: `tests/conftest.py` replaces `datetime.date` with a subclass,
and `st.date_input` then rejects the page's own date value (*"Invalid `value` type. Expected
one of: date, datetime, ISO string, "today". Provided type: date."*). The patch's conftest hunk
gives the frozen class a metaclass whose instance check accepts any real date, so the freeze
stays transparent to `isinstance` while `today()` stays frozen. That is a test-only change and
can be taken or left with the warning.

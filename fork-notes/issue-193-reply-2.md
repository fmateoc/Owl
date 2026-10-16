# Second reply on #193: the "convex" fix checked with the repro, for the user to post

Status: draft 2026-10-16, after upstream `6b02671` + `83a580b` (`withSSTaxability="convex"`).
Numbers: `issue-193-convex-output.txt` (`issue-193-ls.py 600 loop,convex,ss-bb,preset-ls` on stock
`dev` `83a580b`) and `model-review/ss-loop/examples_convex_stock_2026-10-16.txt` (`ex_ss.py ...
convex`). Both from stock `dev`, date frozen at 2026-10-15. The fork-side results (NJ exclusion
slow under "convex", LTCG loop $10.7k on the fork's couple) stay out: fork code, not upstream's.

---

Thanks, I ran the repro against `83a580b`. `withSSTaxability="convex"` gives the same bequest as
`"optimize"` to the dollar in all seven cases, in 2.2-5.2 s against 13-21 s, with a fixed-point
residual of $0. On the 18 examples I get what your commit message says: SS residual $0 everywhere,
at or above the loop on 17 (`Case_alex+jamie` -$12), `Case_john+sally` +72%, `Case_helen+ruth`
+0.18%, 0-50 s per solve. One more you did not list: `Case_morgan` +2.15%, where `"optimize"` had
been -0.7%.

One small thing: the Summary's breakpoint method reads "loop" for a `"convex"` solve
(`breakpointMethodUsed`), so a saved workbook does not show that SS was priced exactly.

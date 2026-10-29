# Review of upstream's paper at `dev` `226ff54` (2026-10-29)

Fork-only notes, not for upstream as is. Read the whole of upstream's `papers/owl.tex`
(`git show upstream/dev:papers/owl.tex`, 6,987 lines, "October 28, 2026") in order, then
checked each suspect statement against upstream's code at the same commit, or a primary
source where it is a statement of law. Line numbers are that file's. Each item says how it
was checked:

- **[code]**: read in upstream's source at `226ff54` (file and line given);
- **[source]**: read in a primary document fetched this session;
- **[paper]**: an inconsistency between two places in the paper, no outside check;
- **[recalled]**: from memory, not checked this session.

The fork's own `owl.tex` (its state-tax paragraph, ch. 2) is not reviewed here.

## A. Wrong against the code or the law (verified)

1. **Eqs. (BinQ), (BinT), SS taxability MIP (l. 2709-2733).** The first row of each pair is
   printed as `p^min >= p̄ (1 - z0)` and `t >= 0.85 Σζ (1 - z1)`. With the second rows
   (`... + M z >= 0`), both rows of a pair relax at `z = 1`, so `p^min` and `t^σ` could
   fall to 0 and the taxable share of SS to nothing. The code has `p^min >= p̄ z0` and
   `t >= 0.85 Σζ z1` (`plan.py` 4039-4057: `pmin - M z0 >= p_ub - M`, M = p_ub), so that
   exactly one row of each pair binds. [code]
2. **QCD cap for 2026 (l. 1866): \$115,000.** IRS Notice 2025-67 (irs.gov,
   `n-25-67.pdf`): the 408(d)(8)(A) limit "is increased from \$108,000 to \$111,000".
   **The code has the same wrong figure**: `tax_federal.py:157`
   `qcdLimit = {2025: 108_000, 2026: 115_000}`, so input between \$111,000 and \$115,000
   is accepted. The paper's bibliography lists Notice 2025-67 but never cites it. [source, code]
3. **Medigap premiums as HSA-qualified (l. 251-253, 842-845).** Pub. 969 (irs.gov,
   current): Medicare and other coverage at 65+ qualify "other than premiums for a Medicare
   supplemental policy, such as Medigap". [source]
4. **HSA withdrawals "not tracked" (l. 839-848, 874-878).** The paper says the optimizer
   treats HSA withdrawals as generic tax-free cash. The code caps them each year at
   Medicare costs plus `other_medical_expenses` (`plan.py` 3470-3482,
   `_add_hsa_medical_cap`, tag `hsa_medical_cap`, which the paper's own Table of policy tags
   lists, l. 6203). Before Medicare the cap is `other_medical_expenses` alone (0 without it). [code]
5. **HSA contributions in the Medicare year (l. 896-902).** "Owl zeroes the entire year,
   which is conservative." The code keeps the months before enrollment (`plan.py` 1842-1858,
   `_setHSAStop`, `hsaFrac_in = 1 - months/12`), as the paper itself says at l. 302-304,
   836-837 and 5117-5119. [code, paper]
6. **Earnings test inputs are stale (l. 274-322, 574-578, 591-592, 601-606, 5152-5157).**
   - The HFP column list has no `employer ctrb` (`hfp_io.py:42`), and the limitation
     "employer contributions included in 401k ctrb ... make the earnings slightly high"
     (l. 604-606) predates that column (#229).
   - "anticipated wages plus 401k ctrb and IRA ctrb" (l. 575-576): the code adds the IRA
     contribution only in a year with pay (`plan.py` 2296-2323), and reads the five years
     before the plan for someone already claiming (#235); neither is in the paper.
   - "Exempt amounts ... 2024-2026 ... held at the 2026 level" (l. 591-592, 601-603) and
     the wage base "held at that level" (l. 5153): the code has 2027 for both
     (`socialsecurity.py:852` 25,560 / 67,920; `tax_federal.py:255` 192,300). [code]
7. **Spousal reduction (l. 471-474, 4503-4505).** Only 25/36 of 1% per month is given; the
   code applies 5/12 of 1% per month beyond 36 months (`socialsecurity.py` 103-123,
   `_reduction_factor(diff, 0, 25/36%·12, 0.75)`), which is the rule (32.5% of PIA at 62
   with FRA 67, as the code's docstring says). [code]
8. **ACA bracket count in the appendix (l. 4691-4693, 5169-5176).** `N_r = 7`, "r = 0..5",
   "bracket 6 (above 400%)". Ch. 2 (l. 986) and ch. 4 (l. 2892) say 8, as the code does
   (`tax_federal.py:225`, `N_ACA_R = 8`; a docstring at l. 939 there still says 7). [code, paper]
9. **State pension exemption (l. 2591).** `E^π = min(Σ_i π_i, N_i c^π)` pools the caps, and
   gives a survivor two. The code takes each person's pension up to their own cap,
   `Σ_i min(π_in, c_in)` (`plan.py` 3168-3169, "each person's pension up to their own cap"). [code]
10. **NII clip (l. 5364-5369).** `𝕀_n` clips the sum of the bond and cash returns; the code
    clips each asset's return (`plan.py` 4439, `fak_in = Σ_k max(0, τ_k) α_k`), as Eq. Tx2
    does. [code]
11. **Filing-status year (l. 1221-1222, 1643-1646).** "Transitions from MFJ to single in the
    calendar year of the first spouse's death" / "Beginning in that year". The paper's own
    convention is death at the end of year `n_d - 1` and single from `n_d` (l. 4672,
    4923-4929, 5992), the couple files jointly in the year of death (l. 1037-1039), and the
    code sets `n_d = min(horizons)` with `horizons = yob + expectancy - thisyear + 1`
    (`plan.py` 504-520). [code, paper]
12. **Broken cross-reference.** Eq. (C3b) (l. 2306-2315), "the current approach used in
    Owl", is in an eqnarray whose only row is `\nonumber`, so its label takes the next
    number: in `owl.pdf` its four references in the text ("balance carryover Eq. (4.28)",
    l. 1839, 2318, 5828, 5993) and the tag table (l. 6221, "(4.26)-(4.28)") print 4.28, which
    is the net-spending equation. (Eq. MedDecomp2 has
    the same construction; its one reference lands on MedDecomp3, which is harmless.) [PDF]
13. **Fixed-asset capital gains missing from `Q_n` (Eq. Qx2, l. 5254-5265).** The code adds
    them to the LTCG partition and to `Q_n` (`plan.py` 4284, 7595); the paper's IRMAA
    expansion includes `A^c` but its `Q_n` does not. [code]
14. **owlcli (l. 6695-6699).** "Supports list and run": the CLI has compare, explain,
    frontier, list, list-rates, run, serve (`cli/_main.py` 57-63); the paper mentions
    `owlcli frontier` itself at l. 4397. [code]
15. **State examples (l. 1285-1287).** Kansas and Missouri as states exempting SS only
    below an AGI threshold: both exempt all of it since tax year 2024 (Kansas SB 1, 2024
    special session, kslegislature.gov bill page; Missouri DOR FAQ, dor.mo.gov, for filers
    62+). Upstream's data comment for KS says the same ("modeled here as fully exempt",
    `taxes_state.toml:913`). [source]

## B. Already in the drift draft, confirmed by the full read

16. **Eqs. MedDecomp2/3 (l. 2833-2863):** `-e_(n-2)` and flipped signs on `w_i1 + x` and on
    the taxable-account term; also no `ā_i` and no `max(0, τ)`, both in the `J_3` rows.
    The ACA MAGI is defined by reference to MedDecomp2 (l. 2913), so the error carries over. [code, paper]
17. **Eq. (PI) (l. 2619):** `Π = 𝔾_n - ½Σζ` with the AGI-basis `𝔾_n`; l. 5344 and
    l. 2753-2756 and the code use the full-SS MAGI. [code, paper]
18. **Ch. 2 state section (l. 1268-1274):** "bracket widths and deductions are indexed",
    while 70 of 103 `brackets_indexed` entries are false; no AGI add-back (the formulation,
    Eq. StateTI, has it); no change of state. [code, paper]
19. **Longevity (l. 4170-4172):** "life expectancy set to the drawn last-survivor horizon";
    the code passes each person's draw (`stresstests.py`, `clone(plan, expectancy=drawn_list[i])`). [code]
20. **Commitment LP framing (l. 4060-4143):** unchanged ("equivalent to minimizing CVaR",
    Markowitz analogy). Its solution is the empirical quantile of the bases at level `1/Λ`
    (so every `Λ < 1` gives `max g_s`); a framing point, not an error. [paper]

## C. Internal inconsistencies and smaller points [paper unless marked]

21. Loop termination: l. 2680-2681 says the loop ends when the objective settles; §3.5
    (l. 1587-1594) requires the residual too.
22. Eqs. (C6) and (C6′) (l. 2533-2544, 2746) use `τ_kn` without the clip that Eq. Tx2 and
    the `J_7` rows (l. 5965-5978) have.
23. "The OBBBA 65+ bonus deduction phaseout is computed outside the LP" (l. 1245-1246,
    1236-1237): not under `withSeniorBonus = "optimize"` (l. 1907).
24. "Five families" of binaries (l. 4835-4852): omits `z^sb` and `z^o`, which ch. B lists
    (l. 5682-5688).
25. QCD: two paragraphs say the same thing (l. 1853-1860 and 1862-1867).
26. The survivor spending fraction is `φ` in ch. 3 (l. 1478-1482), which also names the
    beneficiary fractions `φ_j` (l. 5182) and the year fraction in Eq. BackProject; it is
    `χ` in ch. 4 and the appendix (l. 2371, 4911, 4919).
27. Medicare costs scale with `γ_n` (l. 2784, 5145) though §"Medical price inflation"
    (l. 1089-1091) says `γ^med`; thresholds `L̄ = γ L` for every tier (l. 2786) though
    the top tier is frozen until 2028 (l. 1070-1072).
28. The appendix smile (l. 4906-4908: no delay, normalized to `N_n`) differs from Eq.
    SmileProfile (l. 1472-1482), which matches `spending.py` 59-70. [code]
29. Horizon: "through the year following the last individual's projected death"
    (l. 1319-1320) vs "through the assumed year of death" (l. 1324-1325) and the code.
30. Previous MAGIs needed when "the oldest individual is currently either 64 or 65"
    (l. 2772-2773); l. 1052-1057 states the general rule (Medicare in either of the first
    two years).
31. "Surplus deposits land in the taxable account at year end" (l. 1996-1997): in Eq. C3b,
    Eq. B1 and the code (`plan.py` 3785) a deposit grows with `1 + T`, i.e. it is made at
    the start of the year. The conclusion (no surplus with the exhausted gate) still holds.
32. SPIA premium: removed from the tax-deferred balance without the growth factor (Eq. B1's
    `v`, l. 5845; `plan.py` 3777), i.e. at year end, while a full year's income is paid from
    the purchase year (l. 683-684, 715-716). The premium earns a year's return and the
    annuity pays a year in the same year; not listed as a limitation. [code]
33. `spending.py` described as "the spending profile `Λ_n`" (l. 6614); the profile is `ξ_n`.
    `q_d(i, j, n)` (l. 6049): `d` has no `j`.
34. Bibliography: seven entries never cited (`cfr401a9`, `irc121`, `irc1014`, `irs15`,
    `irsnotice2025_67`, `revproc2025_32`, `revproc2026_26`), though several are named in
    the text. All `\ref`s resolve. [grep]
35. "Frozen since 1983 and 1994 respectively" (l. 545-546) pairs the dates with single and
    MFJ; they belong to the first and second tiers. [recalled]
36. Roth earnings (l. 733-735): five years and 59½ are given as both needed "for a
    penalty-free withdrawal"; after 59½ unqualified earnings are taxed but not penalized. [recalled]
37. MOSEK and Gurobi listed as "algebraic modeling languages" (l. 5450).

Checked and found consistent: the constraint-tag tables against `CONSTRAINT_FAMILIES` and the
tags `plan.py` emits (every emitted tag is in a table) [code]; the variable count
`C_* = 34 N_n + 8` (l. 5658-5662) [arithmetic]; the SS damping and update threshold
(l. 2675-2679; `plan.py` 116, 7464-7465) [code]; the default mortality table SSA 2025 [code];
the 2025/2026 FPL figures match the code [code; HHS not checked]; the RiskMetrics,
lognormal and tanh glide-path algebra [arithmetic]. 2026 Part B, IRMAA, LTCG thresholds,
standard deductions and HSA limits match what I recall; not checked this session [recalled].

## D. Comparison with the recheck of the drift draft (same day)

The recheck (top of `issue-docs-loop-and-paper.md`) was a grep for the draft's own items.
Against the full read:

- **Confirmed as stated:** MedDecomp2/3 (16), Eq. (PI) (17), the ch. 2 state items (18),
  longevity (19), the CVaR framing (20); and the items marked fixed (Roth cap, AMO, Benders,
  big-M 10^8, survivor claim, lexicographic terms, scenario wording).
- **Recheck was wrong or too strong:**
  - Item 1 (loop not optimal): the recheck said a grep found no statement in the paper. The
    senior-bonus section says it for that family: "A solve under that constant cannot trade
    income against the bonus, and will accept income the bonus would have sheltered"
    (l. 1904-1905). What is missing is the general statement in §3.5; and §4's
    termination sentence contradicts §3.5 (21).
  - Item 2 / Tx2 clip "fixed": true of Eq. Tx2 only; Eqs. C6 and C6′ still omit the clip
    (22), and `𝕀_n` clips differently from the code (10).
  - AMO "fixed": the 4N_n text is gone, but the binary-family list is stale in another way (24).
- **Missed by the recheck (not in the draft):** everything in A except 16-19, i.e. the
  BinQ/BinT signs, the QCD cap (also a code bug), Medigap, the HSA medical cap and
  proration, the earnings-test staleness, the spousal 5/12, ACA `N_r`, the pension
  exemption pooling, the NII clip, the filing-status year, the C3b reference, `A^c` in
  `Q_n`, owlcli, KS/MO; and the internal points of C.

## E. What to file (proposal)

- **Separate code issue:** the 2026 QCD cap (`tax_federal.py:157`, \$111,000 per Notice
  2025-67). Small, verifiable, independent of the docs.
- **One docs issue**, replacing the draft's text, ordered by consequence: BinQ/BinT (1),
  MedDecomp2/3 (16), Eq. (PI) (17), pension exemption (9), HSA: Medigap, medical cap,
  proration (3-5), earnings test (6), spousal 5/12 (7), filing-status year (11), ACA
  `N_r` (8), the C3b reference (12), then the shorter items (10, 13-15, 18-24, 26-29, 31-33)
  as a list. The loop caveat as one sentence for §3.5, pointing to l. 1904-1905. Leave
  out 20, 32 and the [recalled] items unless checked first.

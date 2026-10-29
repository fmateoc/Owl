# Draft upstream issue: paper (`owl.tex`) errors and drift at `dev` `226ff54`

Status: **filed by the user as #241** (2026-10-29). Drafted 2026-10-29 from `fork-notes/paper-review-226ff54.md` (section E),
replacing `fork-notes/issue-docs-loop-and-paper.md` (2026-10-04, written against `a85ff76`; most
of it was fixed by upstream's 2026-10-28 rewrite). Documentation only; no code change proposed.
The 2026 QCD limit, which is wrong in the code as well, is a separate issue
(`fork-notes/issue-qcd-limit.md`); file that one first, and this one refers to it.

How each item was checked (the review says per item): against upstream's code at `226ff54`
(file and line given in the review), against the paper itself, against `papers/owl.pdf` (item 10),
or against a primary source fetched 2026-10-29 (Pub. 969 for item 5; Kansas Legislature and
Missouri DOR pages for the KS/MO line). Left out on purpose: the commitment-LP / CVaR framing and
the SPIA premium timing (judgment calls, not errors), and three points I only recalled (the
1983/1994 threshold dates, the Roth-earnings penalty wording, MOSEK and Gurobi called modeling languages) — review items 20, 32,
35-37. Line numbers are `papers/owl.tex` at `226ff54`; spot-checked again before drafting.

Beyond section E: items 25 (duplicate QCD paragraph) and 30 (previous MAGIs) are in the short
list too (E left them out without a reason; kept by the user, 2026-10-29).

---

**Title:** Paper (owl.tex): equations and statements that disagree with the code at 226ff54

Reading the 2026-10-28 `owl.tex` against the code at `226ff54`, these places disagree. Line numbers
are `papers/owl.tex` at `226ff54`. In each case the code is right as far as I can tell, so this is
a docs-only issue. Ordered by how much a reader relying on the paper would be misled.

**1. SS-taxability MIP rows, Eqs. (BinQ) and (BinT) (l. 2709-2733).** The first row of each pair
is printed with `(1 - z)`:

```latex
p^{\sigma,\min}_n \ge \bar p_n (1 - z^\sigma_{0n}), \qquad
t^\sigma_n \ge 0.85 \textstyle\sum_i \bar\zeta_{in}\,(1 - z^\sigma_{1n}).
```

The second row of each pair is relaxed by `+M z`, so as printed both rows of a pair are switched
off when `z = 1`, and `p^min` and `t^sigma` (the taxable SS) could drop to 0. The code
(`plan.py` 4039-4057, `ss_tax_pmin_lb_cap`, `ss_tax_tss_lb_cap`) has `p^min >= p̄ z0` and
`t >= 0.85 Σζ z1`, so exactly one row of each pair holds. Suggested:

```latex
p^{\sigma,\min}_n \ge \bar p_n\, z^\sigma_{0n}, \qquad
t^\sigma_n \ge 0.85 \textstyle\sum_i \bar\zeta_{in}\, z^\sigma_{1n}.
```

**2. IRMAA MAGI expansion, Eqs. (MedDecomp2) and (MedDecomp3) (l. 2833-2863).** They carry
`- e_(n-2)` and negative signs on `Σ[w_i1 + x]` and on `Σ(b - w + d)(…)`, so MAGI would fall with
tax-deferred withdrawals and conversions. The `J_3` rows of the appendix (l. 5868-5900) are right
and say why there is no `e` term (l. 5895). MedDecomp2 also lacks `ā_i` and the `max(0, τ)` that
`J_3` has. Suggested MedDecomp2, all indices at `n-2`:

```latex
\sum_q h_{qn} = \mathcal{A}^x + \mathcal{A}^c
  + \sum_i [\omega_i + \upsilon_i + \nu_i + R\bar\zeta_i + \bar\pi_i + \bar a_i]
  + \sum_i [w_{i1} + x_i]
  + \sum_i (b_{i0} - w_{i0} + d_i)\Big(\sum_{k\ne0}\alpha_{i0k}\max(0,\tau_k) + \mu\alpha_{i00}\Big)
  + \sum_i w_{i0}\,\alpha_{i00}\max(0, \tau_{0,(n-3)} - \mu)
  + 0.5\sum_i \kappa_{i0}\Big(\sum_{k\ne0}\alpha_{i0k}\max(0,\tau_k) + \mu\alpha_{i00}\Big),
```

and MedDecomp3 the same with the variables moved left (or both replaced by a pointer to the
`J_3` rows). The ACA MAGI is defined "with the same structure as in Eq. (MedDecomp2)"
(l. 2913), so it inherits the error.

**3. Provisional income, Eq. (PI) (l. 2619).** `Π_n = 𝔾_n − ½Σζ` uses the AGI-basis MAGI, which
holds only the taxable part of SS. The intermediate-variables entry (l. 5344:
`Π_n = 𝔾^aca_n − ½Σζ`), the text at l. 2753-2756 and the code ("PI = MAGI_aca - 0.5*SS") use the
full benefit. Suggested: `Π_n = 𝔾^{aca}_n − ½ Σ_i ζ̄_in`.

**4. State pension exemption (l. 2591).** `E^π_n = min(Σ_i π̄_in, N_i c̄^π_n)` pools the two caps
(and leaves a survivor two). The code takes each person's pension up to that person's cap
(`plan.py` 3168-3169: `Σ_i min(π̄_in, c_in)`), as the next sentences say for the retirement
exemption. Suggested: `E^π_n = Σ_i min(π̄_in, c̄^π_in)`.

**5. HSA (l. 251-253, 839-848, 874-878, 896-902).**
- Medigap premiums are listed as qualified HSA expenses (l. 251-253, 842-845). Pub. 969 excludes
  them: Medicare and other coverage at 65+ qualify "other than premiums for a Medicare
  supplemental policy, such as Medigap".
- "The optimizer does not track medical expenses explicitly; it treats HSA withdrawals as
  generic tax-free cash flow" (l. 846-848). The code caps HSA withdrawals each year at the
  Medicare cost plus `other_medical_expenses` (`plan.py` 3470-3482, `_add_hsa_medical_cap`; the
  policy-tag table lists `hsa_medical_cap`, l. 6203). Before Medicare only
  `other_medical_expenses` counts, so without it HSA withdrawals before 65 are zero
  (`setMedicalExpenses` docstring).
- "Owl zeroes the entire year [of Medicare enrollment], which is conservative" (l. 896-902). The
  code keeps the months before enrollment (`plan.py` 1842-1858, `_setHSAStop`), as l. 302-304,
  836-837 and 5117-5119 say.

**6. Earnings test text predates #229 and #235 (l. 274-322, 574-578, 591-592, 601-606, 5153).**
- The HFP column list has no `employer ctrb` (`hfp_io.py:42`); the limitation "Employer
  contributions included in 401k ctrb … make the earnings slightly high" (l. 604-606) is the
  case that column now handles.
- "anticipated wages plus that year's 401k ctrb and IRA ctrb" (l. 575-576): the IRA contribution
  counts only in a year with pay (`plan.py` 2296-2323), and for someone entitled before the plan
  the five rows before it are read (#235). Neither is in the paper; l. 306-307 still says the
  lead-in rows serve the Roth rule only.
- Exempt amounts "for 2024-2026 … held at the 2026 level" (l. 591-592, 601-603) and the wage base
  "held at that level" (l. 5153): the code has 2027 for both (`socialsecurity.py:852`,
  `tax_federal.py:255`).

**7. Spousal reduction (l. 471-474, 4503-4505).** Only 25/36 of 1% per month is given. The code
(`socialsecurity.py` 103-123, 334-379) applies 5/12 of 1% per month beyond 36 months, which is the
rule: 32.5% of the worker's PIA at 62 with an FRA of 67. Suggested: "25/36 of 1% per month for the
first 36 months and 5/12 of 1% for each further month".

**8. MFJ to single (l. 1221-1222, 1643-1646).** "Filing status transitions from MFJ to single in the
calendar year of the first spouse's death"; "Beginning in that year". The paper's own convention is
death at the end of year `n_d − 1` with single status from `n_d` (l. 4672, 4923-4929, 5992), and
l. 1037-1039 says the couple files jointly in the year of death. The code has
`n_d = min(horizons)` (`plan.py` 504-520). Suggested: "from the year after the first death".

**9. ACA bracket count in the appendix (l. 4691-4693, 5169-5176).** `N_r = 7`, `r = 0..5`,
"bracket 6 (above 400% FPL)". Ch. 2 (l. 986), ch. 4 (l. 2892) and the code (`tax_federal.py:225`,
`N_ACA_R = 8`) have 8. (The docstring at `tax_federal.py:939` still says 7.)

**10. A broken reference.** Eq. (C3b) (l. 2306-2315), the carryover the paper calls "the current
approach used in Owl", is an eqnarray whose only row is `\nonumber`, so its label takes the next
equation's number. In `owl.pdf` its four references (l. 1839, 2318, 5828, 5993: "Eq. (4.28)") and
the tag table (l. 6221: "(4.26)-(4.28)") point to (4.28), the net-spending equation. Dropping the
`\nonumber` (or using `equation`) fixes it.

**11. The loop caveat.** `modeling-capabilities.md` and the UI docs now say that the loop can settle
on a plan that is self-consistent but not optimal, and the senior-bonus section says it for that
family (l. 1904-1905: "A solve under that constant cannot trade income against the bonus, and will
accept income the bonus would have sheltered"). §3.5 (l. 1555-1640) does not. Suggested sentence
after l. 1594: "Within each solve the fed-back quantities are constants, so the optimizer cannot
trade income against them (an IRMAA tier, the Social Security phase-in, the senior-bonus
phase-out): the loop can settle on a plan that is self-consistent and still not the best one. The
"optimize" modes below, and local search, remove this for the families they cover."

**Shorter items**
- `𝕀_n` (l. 5364-5369) clips the sum of the bond and cash returns at zero; the code clips each
  asset (`plan.py` 4439), as Eq. (Tx2) and the `J_7` rows do. Eqs. (C6) and (C6′) (l. 2533-2544,
  2746) use `τ_kn` without the clip at all.
- `Q_n`, Eq. (Qx2) (l. 5254-5265), has no fixed-asset capital gains; the code adds them to `Q_n`
  and the LTCG partition (`plan.py` 4284, 7595), and MedDecomp2 has `𝒜^c`.
- `owlcli` "supports list and run" (l. 6695-6699); it has compare, explain, frontier, list,
  list-rates, run and serve (`cli/_main.py` 57-63); l. 4397 mentions `owlcli frontier`.
- Kansas and Missouri as states that exempt SS only below an AGI threshold (l. 1285-1287): both
  exempt all of it from tax year 2024 (Kansas SB 1, 2024 special session; Missouri DOR, for
  filers 62+). The data comment for KS (`taxes_state.toml:913`) already models it as exempt.
- Ch. 2 state section (l. 1267-1274): "bracket widths and deductions are indexed to inflation",
  while 70 of the 103 `brackets_indexed` entries in `taxes_state.toml` are `false` (#157);
  state income from "federal ordinary taxable income" without the deduction add-back that
  Eq. (StateTI) explains (l. 2579-2582); no mention of the change of state (#159).
- Longevity (l. 4170-4172): "life expectancy set to the drawn last-survivor horizon"; the code
  passes each person's drawn age (`stresstests.py`, `clone(plan, expectancy=drawn_list[i])`).
- l. 2680-2681: "The SC loop terminates when the change in the objective function … falls below a
  prescribed tolerance"; §3.5 (l. 1587-1594) requires the fixed-point residual too.
- "The OBBBA 65+ bonus deduction phaseout is computed outside the LP" (l. 1236-1237, 1245-1246):
  not under `withSeniorBonus = "optimize"` (l. 1907).
- "Five families" of binaries (l. 4835-4852): `z^sb` and `z^o` are missing (listed at
  l. 5682-5688).
- QCD: l. 1853-1860 and l. 1862-1867 say the same thing twice (and l. 1866 has the 2026 figure of
  the separate QCD issue).
- The survivor spending fraction is `φ` in ch. 3 (l. 1478-1482), a symbol also used for the
  beneficiary fractions `φ_j` (l. 5182) and in Eq. (BackProject); it is `χ` at l. 2371, 4911, 4919.
- Medicare costs `C̄_qn = γ_n C_q` (l. 2784, 5145), though §"Medical price inflation"
  (l. 1089-1091) scales them with `γ^med_n`; thresholds `L̄_qn = γ_n L_q` for every tier
  (l. 2786), though the top tier is frozen to 2028 (l. 1070-1072).
- The appendix smile (l. 4906-4908: no delay, normalized to `N_n`) differs from Eq.
  (SmileProfile) (l. 1472-1482), which matches `spending.py`.
- "Through the year following the last individual's projected death" (l. 1319-1320) vs "through
  the assumed year of death" (l. 1324-1325), which matches `horizons` in the code.
- Previous MAGIs needed when "the oldest individual is currently either 64 or 65" (l. 2772-2773):
  needed whenever Medicare starts in either of the first two years, as l. 1052-1057 says.
- "Surplus deposits land in the taxable account at year end" (l. 1996-1997): in Eq. (C3b),
  Eq. (B1) and the code a deposit grows by `1 + T` that year, i.e. it lands at the start. The
  argument there holds either way.
- `spending.py` is "the spending profile `Λ_n`" (l. 6614); the profile is `ξ_n`. `q_d(i, j, n)`
  (l. 6049): `d` has no `j` index.

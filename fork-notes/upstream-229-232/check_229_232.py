"""Independent checks of upstream #229-#232 on the fork's code (= upstream 4dcfabb for these paths)."""
import io
import numpy as np
import owlplanner as owl
from owlplanner import socialsecurity as ss
from owlplanner import tax_federal as tx

print("owlplanner from", owl.__file__)

# ---- #229 / #230: derived earnings and payroll tax, year 0 (gamma = 1) ----
def payroll(wages, k401=0.0, ira=0.0):
    p = owl.Plan(["A"], ["1976-07-01"], [90], "x", verbose=False, logstreams=[io.StringIO()])
    p.omega_in[0, 0] = wages
    p.kappa_ijn[0, 1, 0] = k401 + ira
    e = p._earnings_test_inputs()[0]
    pay = tx.payrollTax(p.N_i, e, np.ones(p.N_n), p.n_d, p.N_n)
    return e[0, 0], pay[0]

def law(pay):  # employee FICA, single, 2026 wage base 184,500
    return 0.062 * min(pay, 184_500) + 0.0145 * pay + 0.009 * max(0, pay - 200_000)

print("\n#229")
for label, w, k, ira, gross in [
    ("23,500 all to 401k", 0, 23_500, 0, 23_500),
    ("23,501, 23,500 to 401k", 1, 23_500, 0, 23_501),
    ("7,000 all to deductible IRA", 0, 0, 7_000, 7_000),
    ("7,001, 7,000 to IRA", 1, 0, 7_000, 7_001),
]:
    e, pay = payroll(w, k, ira)
    print(f"  {label:32s} earnings {e:10,.2f}  payroll {pay:9,.2f}  law {law(gross):9,.2f}")

print("\n#230")
for label, w, k, ira, gross in [
    ("103,500, 23,500 deferred", 80_000, 23_500, 0, 103_500),
    ("same + 6,000 employer match", 80_000, 29_500, 0, 103_500),
    ("80,000 + 7,000 nondeductible IRA", 80_000, 0, 7_000, 80_000),
]:
    e, pay = payroll(w, k, ira)
    print(f"  {label:32s} earnings {e:10,.2f}  payroll {pay:9,.2f}  law {law(gross):9,.2f}  diff {pay - law(gross):7,.2f}")

# ---- #231: exempt amounts in a plan starting 2027, and 2027 in a 2026 plan ----
PUB = {2024: (22_320.0, 59_520.0), 2025: (23_400.0, 62_160.0), 2026: (24_480.0, 65_160.0),
       2027: (25_560.0, 67_920.0)}  # 2027 as stated in #231 (not verified here)

def et_one(birth, earn_n, thisyear, exempt=None, N=10):
    y, m, d = birth
    e = np.zeros((1, N)); e[0, : len(earn_n)] = earn_n
    return ss.earnings_test([2000], [62 + 1 / 12], [y], [m], [d], [N], 1, N, e,
                            thisyear=thisyear, exempt_for_year=exempt)

print("\n#231")
print("  get_exempt_amounts 2026/2027/2030:", [tuple(ss.get_exempt_amounts(y)) for y in (2026, 2027, 2030)])
pub_nom = lambda y: ss.get_exempt_amounts(y, PUB)
for label, birth, earn in [("plan 2027, under FRA, $40,000", (1963, 8, 15), [40_000]),
                           ("plan 2027, FRA Sep 2027, $110,000", (1960, 9, 15), [110_000])]:
    a = et_one(birth, earn, 2027).withheld_in.sum()
    b = et_one(birth, earn, 2027, exempt=pub_nom).withheld_in.sum()
    print(f"  {label:36s} withheld Owl {a:9,.2f}  published {b:9,.2f}  diff {a - b:7,.2f}")
g = 1.025
real_pub = lambda y: (ss.ExemptAmounts(*[v / g ** (y - 2026) for v in PUB[y]]) if y in PUB and y >= 2026
                      else ss.get_exempt_amounts(y))
naive = lambda y: ss.get_exempt_amounts(y, PUB)  # 2027 added as is, read as 2026 dollars
earn = [0, 40_000 / g]
a = et_one((1963, 8, 15), earn, 2026).withheld_in.sum()
b = et_one((1963, 8, 15), earn, 2026, exempt=real_pub).withheld_in.sum()
c = et_one((1963, 8, 15), earn, 2026, exempt=naive).withheld_in.sum()
print(f"  plan 2026, $40,000 in 2027 @2.5%: Owl - right = {(a - b) * g:7,.2f} (2027 $); "
      f"'2027 added as is' - right = {(c - b) * g:7,.2f}")

# ---- #232: worker's excess on the spouse's add-on after the spouse's FRA ----
print("\n#232")
flat = lambda y: ss.get_exempt_amounts(2026)
for wage in (60_000, 70_000):
    N = 30
    e = np.zeros((2, N)); e[0, :5] = wage
    r = ss.earnings_test([2400, 400], [62 + 1 / 12, 63 + 10 / 12], [1963, 1962], [8, 3], [15, 15],
                         [N, N], 2, N, e, thisyear=2026, exempt_for_year=flat)
    n = 3  # payment year 2029: checks for Dec 2028 .. Nov 2029
    w_own = 2400 * ss.getSelfFactor(67, 62 + 1 / 12, False)
    s_own = 400 * ss.getSelfFactor(67, 63 + 10 / 12, False)
    sp_pre = (1200 - 400) * ss.getSpousalFactor(67, 63 + 10 / 12, False)
    sp_arf = (1200 - 400) * ss.arf_spousal_factor(67, 63 + 10 / 12, int(r.arf_months_spousal[1]), False)
    due = 12 * (w_own + s_own) + 3 * sp_pre + 9 * sp_arf
    paid, wh = r.zeta_in[:, n].sum(), r.withheld_in[:, n].sum()
    print(f"  W ${wage:,}: due {due:10,.2f}  paid {paid:10,.2f} + withheld {wh:10,.2f} = {paid + wh:10,.2f}"
          f"  missing {due - paid - wh:8,.2f}  (spousal {sp_pre:.2f} -> {sp_arf:.2f}, "
          f"{int(r.arf_months_spousal[1])} crediting months)")

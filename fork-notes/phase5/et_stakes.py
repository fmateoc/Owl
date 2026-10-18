"""Phase 5 step 0 stakes: lifetime SS with and without the earnings test, no LP.

Stand-in couple from ``nj_stakes.py``: born 1964-03-15 / 1964-09-15, PIAs $3,000 / $2,400,
life expectancies 89 / 92 (Owl's convention: last plan year = birth year + expectancy).
The grid is on the worker (Joe, PIA $3,000, FRA 67): earnings x last work year x ``months
worked`` in the last year x claiming age.

For each cell the script prints lifetime own benefits in today's dollars, undiscounted and
at 2% real, with and without the test, plus the lifetime amount withheld and the ARF
crediting months. Prototype of the step-1 ``earnings_test`` function (``phase5-plan.md``
§4.3); not wired into Owl. One worker's own benefit only (this couple has no spousal
add-on). Exempt amounts are the 2026 statutory ones held constant in today's dollars
(POMS RS 02501.025 D; 20 CFR 404.430(a)(2) indexes them to wages, which Owl has no
series for).

Month indexing (the bug in the first draft): entitlement months, not payment months.
Benefits are paid in arrears, so the check for entitlement month ``m`` arrives in ``m+1``
and is bucketed to that payment year — the same convention as
``socialsecurity._payment_start`` / ``compute_social_security_benefits``. The test charges
entitlement months before the FRA month (RS 02501.021, 404.434); the FRA month itself is
never charged (404.435(a)(3)).

Run from the repo root:

    .venv/bin/python fork-notes/phase5/et_stakes.py > fork-notes/phase5/et_stakes_<date>.txt

(On Windows, `.venv\\Scripts\\python`; write the output as UTF-8, e.g. `$env:PYTHONIOENCODING="utf-8"`
and `| Out-File -Encoding utf8`, not PowerShell's default `>`, which writes UTF-16.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from owlplanner import socialsecurity as socsec

# --- stand-in worker (nj_stakes.py) -------------------------------------------------
YOB, MOB, TOB = 1964, 3, 15
PIA = 3000.0
DEATH_AGE = 89
THISYEAR = 2026  # frozen test date; the plan starts in 2026
LAST_YEAR = YOB + DEATH_AGE  # 2053, Owl's last plan year (full year, like zeta_in)
FRA = float(socsec.getFRAs([YOB], [MOB], [TOB])[0])  # 67
BORN_ON_FIRST = TOB == 1

# POMS RS 02501.025 D (TN 55, 11/21/2025), annual / monthly amounts for 2026.
EXEMPT_2026 = 24480.0
EXEMPT_FRA_YEAR_2026 = 65160.0
EXEMPT_MONTHLY_2026 = EXEMPT_2026 / 12.0  # $2,040

REAL_DISCOUNT = 0.02


@dataclass
class YearResult:
    year: int
    earnings: float
    excess: float
    withheld: float
    benefit_paid: float
    benefit_gross: float
    chargeable_months: int
    non_service_months: int
    is_grace: bool
    is_fra_year: bool


@dataclass
class LifetimeResult:
    claim_age: float
    lifetime_no_test: float
    lifetime_no_test_pv: float
    lifetime_test: float
    lifetime_test_pv: float
    lifetime_withheld: float
    arf_months: int
    years: list[YearResult]


def _self_factor(fra: float, claim_age: float) -> float:
    return socsec.getSelfFactor(fra, claim_age, BORN_ON_FIRST)


def _ent_start_month(claim_age: float) -> int:
    """Absolute month index (year * 12 + month - 1) when entitlement begins (age attained)."""
    return YOB * 12 + (MOB - 1) + int(round(claim_age * 12))


def _month_in_year(abs_month: int) -> int:
    return abs_month % 12 + 1


def _year_of(abs_month: int) -> int:
    return abs_month // 12


def _fra_abs_month() -> int:
    """Absolute month of FRA attainment (born 1964-03-15 → March 2031 = age 67)."""
    return YOB * 12 + (MOB - 1) + int(round(FRA * 12))


def _earnings_by_year(earnings: float, last_work_year: int, months_last: int) -> dict[int, tuple[float, int]]:
    """Map calendar year -> (countable wages for the test, months worked at the start of the year)."""
    out: dict[int, tuple[float, int]] = {}
    if earnings <= 0:
        return out
    for year in range(THISYEAR, last_work_year + 1):
        if year == last_work_year:
            out[year] = (earnings * months_last / 12.0, months_last)
        else:
            out[year] = (earnings, 12)
    return out


def _is_non_service(month_num: int, y_earn: float, y_months: int, in_earned: bool) -> bool:
    """A month of entitlement with wages not above the monthly exempt amount (404.435(a)(7)).

    ``months worked`` are at the start of the year (D2); even spread over those months.
    A month with no work, or with monthly wages at or below the monthly exempt amount,
    is a non-service month. Substantial services in self-employment are out of scope.
    """
    if not in_earned:
        return False  # no work that year: excess is 0, nothing to skip
    if month_num > y_months:
        return True  # after the months-worked period: no wages
    if y_months <= 0:
        return True
    monthly = y_earn / y_months
    return monthly <= EXEMPT_MONTHLY_2026


def _grace_year(earned: dict[int, tuple[float, int]], ent_start: int) -> int | None:
    """First taxable year with a non-service month in or after the month of entitlement (404.435(b))."""
    start_year = _year_of(ent_start)
    start_month = _month_in_year(ent_start)
    for year in sorted(earned):
        if year < start_year:
            continue
        y_earn, n_work = earned[year]
        ent_month_in_year = start_month if year == start_year else 1
        for month_num in range(ent_month_in_year, 13):
            if _is_non_service(month_num, y_earn, n_work, True):
                return year
    return None


def lifetime_pair(claim_age: float, earnings: float, last_work_year: int, months_last: int) -> LifetimeResult:
    """
    Prototype of ``socialsecurity.earnings_test`` for one worker's own benefit.

    Monthly grid on entitlement months. Even-spread earnings over ``months worked``.
    Excess charged month by month from the first entitlement month of the year; never
    carried to the next year (RS 02501.095); a partial last month keeps the remainder
    (RS 02501.110 — with one beneficiary that is the whole split). Grace year: non-service
    months are not charged (404.435). FRA year: only wages of the months before the FRA
    month count (RS 02501.021 B); $1 per $3 above the FRA-year exempt amount. Nothing is
    charged in the FRA month or later (404.435(a)(3)). From the month of FRA the benefit
    is raised by the ARF (claim age + crediting months, capped at FRA; 404.412).
    """
    ent_start = _ent_start_month(claim_age)
    # Owl's horizon: full last year, like ``zeta_in``'s ``nd = horizons[i]``.
    ent_end = LAST_YEAR * 12 + 11  # December of LAST_YEAR
    fra_m = _fra_abs_month()
    base_factor = _self_factor(FRA, claim_age)
    earned = _earnings_by_year(earnings, last_work_year, months_last)
    grace = _grace_year(earned, ent_start)

    def monthly_gross(crediting: int) -> list[float]:
        if crediting > 0 and claim_age < FRA:
            effective = min(FRA, claim_age + crediting / 12.0)
            factor = _self_factor(FRA, effective)
        else:
            factor = base_factor
        # ARF is effective with the month of FRA (404.412).
        return [PIA * (base_factor if m < fra_m else factor) for m in range(ent_start, ent_end + 1)]

    def charge(gross: list[float]) -> tuple[list[float], list[float], int, list[YearResult]]:
        paid = list(gross)
        withheld = [0.0] * len(gross)
        crediting = 0
        years: list[YearResult] = []

        for year in range(THISYEAR, LAST_YEAR + 1):
            y_earn, y_months = earned.get(year, (0.0, 0))
            in_earned = year in earned
            is_fra_year = _year_of(fra_m) == year

            countable = y_earn
            if is_fra_year and y_earn > 0 and y_months > 0:
                fra_month_in_year = _month_in_year(fra_m)
                months_before = min(y_months, max(0, fra_month_in_year - 1))
                countable = y_earn * months_before / y_months

            exempt = EXEMPT_FRA_YEAR_2026 if is_fra_year else EXEMPT_2026
            divisor = 3.0 if is_fra_year else 2.0
            raw_excess = max(0.0, (countable - exempt) / divisor)
            excess = math.floor(raw_excess)

            year_withheld = 0.0
            year_paid = 0.0
            year_gross = 0.0
            chargeable = 0
            non_service = 0
            is_grace = year == grace

            for mi, m in enumerate(range(ent_start, ent_end + 1)):
                if _year_of(m) != year:
                    continue
                year_gross += gross[mi]
                if m >= fra_m:
                    year_paid += paid[mi]
                    continue
                chargeable += 1
                if _is_non_service(_month_in_year(m), y_earn, y_months, in_earned):
                    non_service += 1
                    if is_grace:
                        # Grace-year monthly test: full benefit, skip the annual test (RS 02501.030 B).
                        year_paid += paid[mi]
                        continue
                if excess > 0:
                    month_benefit = gross[mi]
                    take = min(excess, month_benefit)
                    if take > 0:
                        crediting += 1
                    paid[mi] = month_benefit - take
                    withheld[mi] = take
                    excess -= take
                    year_withheld += take
                year_paid += paid[mi]

            years.append(
                YearResult(
                    year=year,
                    earnings=y_earn,
                    excess=raw_excess,
                    withheld=year_withheld,
                    benefit_paid=year_paid,
                    benefit_gross=year_gross,
                    chargeable_months=chargeable,
                    non_service_months=non_service,
                    is_grace=is_grace,
                    is_fra_year=is_fra_year,
                )
            )
        return paid, withheld, crediting, years

    gross1 = monthly_gross(0)
    _, _, c1, _ = charge(gross1)
    gross2 = monthly_gross(c1)
    paid, withheld, c2, years = charge(gross2)
    if c2 != c1:
        gross3 = monthly_gross(c2)
        paid, withheld, c_final, years = charge(gross3)
    else:
        c_final = c2

    def by_pay_year(monthly: list[float]) -> dict[int, float]:
        """Check for entitlement month m arrives in m+1 (arrears); bucket to that year."""
        out: dict[int, float] = {}
        for mi, m in enumerate(range(ent_start, ent_end + 1)):
            py = _year_of(m + 1)
            out[py] = out.get(py, 0.0) + monthly[mi]
        return out

    def total_pv(by_year: dict[int, float]) -> tuple[float, float]:
        total = pv = 0.0
        for y, amt in sorted(by_year.items()):
            if y < THISYEAR:
                continue
            total += amt
            pv += amt / ((1.0 + REAL_DISCOUNT) ** (y - THISYEAR))
        return total, pv

    nt_total, nt_pv = total_pv(by_pay_year(gross1))
    t_total, t_pv = total_pv(by_pay_year(paid))
    wh_total = sum(v for y, v in by_pay_year(withheld).items() if y >= THISYEAR)

    return LifetimeResult(
        claim_age=claim_age,
        lifetime_no_test=nt_total,
        lifetime_no_test_pv=nt_pv,
        lifetime_test=t_total,
        lifetime_test_pv=t_pv,
        lifetime_withheld=wh_total,
        arf_months=c_final,
        years=years,
    )


def main() -> None:
    earnings_grid = [0, 20_000, 30_000, 40_000, 60_000, 100_000]
    last_years = list(range(2026, 2032))
    months_grid = [6, 12]
    ages = [62 + i for i in range(9)]  # 62..70

    print(
        f"Stand-in worker: born {YOB}-{MOB:02d}-{TOB:02d}, PIA ${PIA:,.0f}/mo, "
        f"FRA {FRA:g}, last plan year {LAST_YEAR} (death age {DEATH_AGE})"
    )
    print(
        f"Exempt ${EXEMPT_2026:,.0f} / FRA-year ${EXEMPT_FRA_YEAR_2026:,.0f} "
        f"(2026, held flat in today's $; monthly ${EXEMPT_MONTHLY_2026:,.0f})"
    )
    print(
        f"Grid: earnings {earnings_grid} x last work year {last_years[0]}-{last_years[-1]} "
        f"x months last {{6,12}} x claim 62-70"
    )
    print()

    best_rows = []
    for earn in earnings_grid:
        for stop in last_years:
            for months in months_grid:
                if earn == 0 and months == 6:
                    continue  # redundant with months=12 when there are no earnings
                results = [lifetime_pair(a, earn, stop, months) for a in ages]
                best_nt = max(results, key=lambda r: r.lifetime_no_test_pv)
                best_t = max(results, key=lambda r: r.lifetime_test_pv)
                for r in results:
                    mark = "best" if r.claim_age == best_t.claim_age else ""
                    print(
                        f"{earn:7,.0f} {stop:5d} {months:3d} {r.claim_age:5.0f} "
                        f"{r.lifetime_no_test:12,.0f} {r.lifetime_no_test_pv:12,.0f} "
                        f"{r.lifetime_test:12,.0f} {r.lifetime_test_pv:12,.0f} "
                        f"{r.lifetime_withheld:10,.0f} {r.arf_months:5d} {mark:>5}"
                    )
                best_rows.append((earn, stop, months, best_nt, best_t))
                print()

    print()
    print("=" * 110)
    print("GATE SUMMARY (best claiming age by 2% real PV)")
    print(
        f"{'earn':>7} {'stop':>5} {'mo':>3} "
        f"{'bestNT':>7} {'PV_NT':>12} {'bestT':>7} {'PV_T':>12} {'dPV%':>7} {'same?':>5}"
    )
    print("-" * 70)
    household_cells = 0
    household_age_moves = 0
    household_dpv_over_1 = 0
    for earn, stop, months, best_nt, best_t in best_rows:
        d = (
            (best_t.lifetime_test_pv - best_nt.lifetime_no_test_pv) / best_nt.lifetime_no_test_pv * 100
            if best_nt.lifetime_no_test_pv
            else 0.0
        )
        same = "yes" if best_nt.claim_age == best_t.claim_age else "NO"
        print(
            f"{earn:7,.0f} {stop:5d} {months:3d} "
            f"{best_nt.claim_age:7.0f} {best_nt.lifetime_no_test_pv:12,.0f} "
            f"{best_t.claim_age:7.0f} {best_t.lifetime_test_pv:12,.0f} "
            f"{d:7.2f} {same:>5}"
        )
        if 20_000 <= earn <= 60_000 and 2026 <= stop <= 2029:
            household_cells += 1
            if best_nt.claim_age != best_t.claim_age:
                household_age_moves += 1
            if abs(d) > 1.0:
                household_dpv_over_1 += 1
    print()
    print(f"Household cells (earn 20-60k, stop 2026-2029): {household_cells}")
    print(f"  best age moves with the test: {household_age_moves}")
    print(f"  |dPV| > 1% at the two best ages: {household_dpv_over_1}")
    print(
        "  gate: stop after step 4 as a correctness fix if best age never moves and "
        "|dPV| at that best age is < 1%"
    )


if __name__ == "__main__":
    main()

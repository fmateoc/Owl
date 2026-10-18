"""Claim-62 comparison table appended to the step-0 stakes output."""

import sys

sys.path.insert(0, "fork-notes/phase5")
from et_stakes import EXEMPT_2026, lifetime_pair  # noqa: E402


def main() -> None:
    print()
    print("Claim-62 stakes vs alternatives (2% real PV, today's $)")
    print(
        f"{'earn':>7} {'stop':>5} {'mo':>3} | {'c62 NT':>10} {'c62 T':>10} {'dT%':>7} | "
        f"{'c=stop':>10} {'c67':>10} {'c70':>10} | {'ARF':>4} {'wh':>9}"
    )
    print("-" * 110)
    for earn in [20000, 30000, 40000, 60000, 100000]:
        for stop in range(2026, 2032):
            for months in (6, 12):
                r62 = lifetime_pair(62, earn, stop, months)
                stop_age = max(62, min(70, stop - 1964))
                r_stop = lifetime_pair(float(stop_age), earn, stop, months)
                r67 = lifetime_pair(67, earn, stop, months)
                r70 = lifetime_pair(70, earn, stop, months)
                d = (r62.lifetime_test_pv - r62.lifetime_no_test_pv) / r62.lifetime_no_test_pv * 100
                print(
                    f"{earn:7,} {stop:5d} {months:3d} | "
                    f"{r62.lifetime_no_test_pv:10,.0f} {r62.lifetime_test_pv:10,.0f} {d:7.1f} | "
                    f"{r_stop.lifetime_test_pv:10,.0f} {r67.lifetime_test_pv:10,.0f} {r70.lifetime_test_pv:10,.0f} | "
                    f"{r62.arf_months:4d} {r62.lifetime_withheld:9,.0f}"
                )
    print()
    print(f"Note: exempt ${EXEMPT_2026:,.0f}; c=stop is claim at age (stop-1964) with the test.")


if __name__ == "__main__":
    main()

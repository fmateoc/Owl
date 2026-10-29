"""
Write the synthetic household: a fictional NY-metro couple built from the Phase 0 template.

Every number here is invented. The cases exist to exercise, on inputs shaped like the household's,
every feature the household's own runs use, so that the scenario suite (run_suite.py) can show that
each run completes and that its report reads correctly. The real case is run offline, by the user,
never in the cloud (decision 2026-10-29, CLAUDE.md "Household data").

The couple, "Ari" and "Noa": both born in 1964 (Ari in January, Noa in December, the template's
shape), married filing jointly, equal horizons (92), renting in Westchester outside Yonkers, no
pensions. Both stop working at the end of 2026 in the base case; marketplace coverage from 2027
until each reaches 65.

Files written to --out-dir (default fork-notes/synthetic/cases, gitignored):

    Case_ari+noa.toml           the template with every TODO filled (maxSpending, budget profile)
    Case_ari+noa_housing.toml   the same household renting in Yonkers, under maxBequest with local search
                                and fixed claiming ages (phase0-scenarios.md section 5)
    HFP_ari+noa.xlsx            base: both stop at the end of 2026, renting
    HFP_ari+noa_2027.xlsx       both work through 2027
    HFP_ari+noa_oneworks.xlsx   Ari stops in 2026; Noa works part time 2027-2028
    HFP_ari+noa_rent.xlsx       housing base: renting (same lines as the base workbook)
    HFP_ari+noa_buy_cash.xlsx   buy a home in Yonkers at the end of 2026, paid in cash
    HFP_ari+noa_buy_mortgage.xlsx  the same home with a 30-year mortgage
    HFP_ari+noa_move.xlsx       rent until 2031, then buy in New Rochelle (a move within NY)
    work_variants.json          variants for fork-notes/phase5/work_sweep.py

Run from the repository root:

    .venv/bin/python fork-notes/synthetic/make_cases.py [--out-dir DIR]

It overwrites what it wrote before (the files are generated, not edited by hand).
"""

import argparse
import copy
import importlib.util
import json
import sys
import tomllib
from pathlib import Path

import toml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "fork-notes" / "phase0" / "Case_us.template.toml"
sys.path.insert(0, str(ROOT / "src"))
from owlplanner.budget import SHEET_COLUMNS  # noqa: E402

_spec = importlib.util.spec_from_file_location("gen_hfp_us", ROOT / "fork-notes" / "phase0" / "gen_hfp_us.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

NAMES = ["Ari", "Noa"]
SLUG = "ari+noa"

# Invented figures ($k for balances, monthly $ for PIAs).
BALANCES = {
    "taxable_savings_balances": [450.0, 300.0],
    "taxable_cost_basis": [330.0, 240.0],
    "tax_deferred_savings_balances": [1150.0, 700.0],
    "tax_free_savings_balances": [120.0, 60.0],
    "hsa_savings_balances": [30.0, 18.0],
}
PIAS = [3150, 2500]
PIAS_NOA_WORKS = [3150, 2560]   # stand-in: two more part-time years raise Noa's PIA a little

# Wages in AGI (upstream #221: pay less the pre-tax 401k deferral), deferral, employer match.
WORK = {
    "Ari": {"anticipated wages": 168000, "401k ctrb": 32500, "employer ctrb": 9000},
    "Noa": {"anticipated wages": 121000, "401k ctrb": 32500, "employer ctrb": 6000},
}
NOA_PART_TIME = {"anticipated wages": 46000, "401k ctrb": 0, "employer ctrb": 0}

HOME = 725000.0            # Yonkers home bought at the end of 2026 (price, nominal 2026 $)
CLOSING = 0.03
DOWN = 0.20
MORTGAGE_RATE = 6.25
HOME_2 = 780000.0          # New Rochelle home bought at the start of 2032 in the move workbook


def line(name, typ, year, end, amount, rate=0.0, survivor=None, essential=False, **age):
    row = {"active": True, "name": name, "type": typ, "year": year, "end": end, "amount": amount,
           "rate": rate, "survivor": survivor, "essential": essential,
           "clock": None, "start_age": None, "end_age": None, "index": None, "kind": None}
    row.update(age)
    return [row[c] for c in SHEET_COLUMNS]


# Lines shared by every workbook: discretionary core, an age-clock travel line (Track B), the
# template's gold-plan lines (its dates match ours: A in January, B in December), a medical line
# for out-of-pocket costs, and charity (both deductible when itemizing wins).
COMMON = [
    line("core", "core", 2026, 0, 78000),
    line("travel while able", "travel", None, None, 12000, clock="age", start_age=62, end_age=80, index="younger"),
    line("out of pocket medical", "medical", 2026, 0, 4500, rate=2.0, survivor=60, essential=True),
    line("gold over benchmark", "medical", 2027, 2028, 3969, survivor=50, essential=True),
    line("gold over benchmark, B alone", "medical", 2029, 2029, 1819, survivor=100, essential=True),
    line("charity", "charity", 2026, 0, 3000),
]
RENT = [line("rent", "rent", 2026, 0, 48000, rate=0.5, essential=True)]
RENT_UNTIL_BUY = [line("rent", "rent", 2026, 2026, 48000, rate=0.5, essential=True)]
OWNER_YONKERS = [
    line("property tax", "property tax", 2027, 0, 17500, rate=1.0, essential=True),
    line("home insurance", "insurance", 2027, 0, 2600, essential=True),
    line("maintenance", "maintenance", 2027, 0, 7000, essential=True),
]
MOVE = [
    line("rent", "rent", 2026, 2031, 48000, rate=0.5, essential=True),
    line("property tax", "property tax", 2032, 0, 21000, rate=1.0, essential=True),
    line("home insurance", "insurance", 2032, 0, 2800, essential=True),
    line("maintenance", "maintenance", 2032, 0, 7500, essential=True),
]


def residence(name, year, value):
    return [True, name, "residence", year, value, value, 0.5, 0, 6.0]


def mortgage(name, year, amount, home):
    return [True, name, "mortgage", year, 30, amount, MORTGAGE_RATE, home]


def write_hfp(path, budget, work_years=(2026,), noa_part_time=(), debts=(), assets=(), big_ticket=()):
    """One workbook: wages in work_years, Noa part time in noa_part_time, household sheets as given."""
    wb = gen.write_hfp(path, names=NAMES, budget_lines=[], overwrite=True)
    for name in NAMES:
        ws = wb[name]
        cols = {c.value: c.column for c in ws[1]}
        for r in range(2, ws.max_row + 1):
            year = ws.cell(r, cols["year"]).value
            if year in work_years:
                for k, v in WORK[name].items():
                    ws.cell(r, cols[k]).value = v
            if name == "Noa" and year in noa_part_time:
                for k, v in NOA_PART_TIME.items():
                    ws.cell(r, cols[k]).value = v
            for who, y, amount in big_ticket:
                if who == name and y == year:
                    ws.cell(r, cols["big-ticket items"]).value = amount
    del wb["Budget"]
    ws = wb.create_sheet("Budget")
    ws.append(list(SHEET_COLUMNS))
    for row in budget:
        ws.append(row)
    for row in debts:
        wb["Debts"].append(row)
    for row in assets:
        wb["Fixed Assets"].append(row)
    wb.save(path)


def case(template, hfp, **changes):
    c = copy.deepcopy(template)
    c["case_name"] = SLUG
    c["description"] = ("Synthetic NY-metro couple (fork-notes/synthetic/make_cases.py): invented numbers shaped "
                        "like the household's, to check that every scenario runs and reports. Not a real case.")
    bi = c["basic_info"]
    bi["names"] = NAMES
    bi["sexes"] = ["M", "F"]
    bi["date_of_birth"] = ["1964-01-20", "1964-12-05"]
    c["savings_assets"].update(BALANCES)
    c["household_financial_profile"]["HFP_file_name"] = hfp
    c["fixed_income"]["social_security_pia_amounts"] = PIAS
    c["optimization_parameters"]["medical_inflation_excess"] = 1.5
    for section, values in changes.items():
        c.setdefault(section, {}).update(values)
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(ROOT / "fork-notes" / "synthetic" / "cases"))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(TEMPLATE, "rb") as f:
        template = tomllib.load(f)

    buy_year_assets = [residence("Yonkers home", 2027, HOME)]
    write_hfp(out / f"HFP_{SLUG}.xlsx", COMMON + RENT)
    write_hfp(out / f"HFP_{SLUG}_rent.xlsx", COMMON + RENT)
    write_hfp(out / f"HFP_{SLUG}_2027.xlsx", COMMON + RENT, work_years=(2026, 2027))
    write_hfp(out / f"HFP_{SLUG}_oneworks.xlsx", COMMON + RENT, noa_part_time=(2027, 2028))
    write_hfp(out / f"HFP_{SLUG}_buy_cash.xlsx", COMMON + RENT_UNTIL_BUY + OWNER_YONKERS, assets=buy_year_assets,
              big_ticket=[("Ari", 2026, -round(HOME * (1 + CLOSING)))])
    write_hfp(out / f"HFP_{SLUG}_buy_mortgage.xlsx", COMMON + RENT_UNTIL_BUY + OWNER_YONKERS, assets=buy_year_assets,
              debts=[mortgage("Yonkers mortgage", 2027, HOME * (1 - DOWN), "Yonkers home")],
              big_ticket=[("Ari", 2026, -round(HOME * (DOWN + CLOSING)))])
    write_hfp(out / f"HFP_{SLUG}_move.xlsx", COMMON + MOVE, assets=[residence("New Rochelle home", 2032, HOME_2)],
              big_ticket=[("Ari", 2031, -round(HOME_2 * (1 + CLOSING)))])

    base = case(template, f"HFP_{SLUG}.xlsx")
    housing = case(template, f"HFP_{SLUG}_rent.xlsx",
                   basic_info={"locality": "Yonkers", "school_district": "City of Yonkers / Yonkers"},
                   optimization_parameters={"objective": "maxBequest"},
                   solver_options={"breakpointMethod": "local-search", "withSSAges": "fixed"},
                   fixed_income={"social_security_ages": [70.0, 67.0]})
    for name, conf in ((f"Case_{SLUG}.toml", base), (f"Case_{SLUG}_housing.toml", housing)):
        with open(out / name, "w", encoding="utf-8") as f:
            toml.dump(conf, f)

    variants = {
        "description": ("Synthetic work variants for work_sweep.py (fork-notes/synthetic/make_cases.py). Invented "
                        "numbers; Noa's PIA with two more part-time years is a stand-in, not an SSA estimate."),
        "set": ["solver_options.withSSAges=optimize"],
        "variants": [
            {"name": "both-stop-2026", "set": ["aca_settings.aca_start_year=2027"]},
            {"name": "noa-part-time-2027-28",
             "set": ["aca_settings.aca_start_year=2027",
                     f"fixed_income.social_security_pia_amounts={json.dumps(PIAS_NOA_WORKS)}"],
             "hfp": {"Noa": [{"years": [2027, 2028], **NOA_PART_TIME, "months worked": 12}]}},
        ],
    }
    with open(out / "work_variants.json", "w", encoding="utf-8") as f:
        json.dump(variants, f, indent=2)
        f.write("\n")
    print(f"Wrote the synthetic household to {out}:")
    for p in sorted(out.iterdir()):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()

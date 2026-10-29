"""
Write the synthetic household: a fictional couple with the household's structure, built from the
Phase 0 template.

Structure from the user (2026-10-29): a couple born in April and December 1964 (neither on the
1st), both working in 2026, retiring at the end of 2026 at the earliest (part-time work and the SS
claiming ages open), married filing jointly, each with 40 SS credits (insured on their own record),
a joint brokerage account larger than their two IRAs together, one 401k (rolled into its owner's
IRA when work stops), no Roth, no HSA, renting in Yonkers (10701),
considering a condo in Yonkers (10701, about $700,000), White Plains (10603, about $700,000) or
Flushing, Queens (11354, about $850,000), the purchase year open, no bequest goal: savings spent by
89, a condo kept as a reserve for long-term care. Also from the user: rent $4,000/month, the same
in 2027, then growing with inflation; condo HOA $800/month, growing with inflation. Every other
amount is invented (balances, wages, PIAs, property tax, insurance, closing costs, care): the cases
exercise the household's scenarios, they are not the household's case, which is run offline by the
user (CLAUDE.md "Household data").

Files written to --out-dir (default fork-notes/synthetic/cases, gitignored):

    Case_ari+noa.toml           the template with every TODO filled (maxSpending, bequest 0, budget profile)
    Case_ari+noa_condo.toml     the same household for the condo grid: local search (claiming ages
                                set by the suite from the baseline's pick)
    HFP_ari+noa.xlsx            base: both work in 2026 and stop; rent in Yonkers in 2026, buy a Yonkers
                                condo at the start of 2027 with cash (REFERENCE; renting to the end is
                                not an option)
    HFP_ari+noa_condo_<place>_<year>_<cash|mortgage>.xlsx   rent until <year>, then own (PLACES, BUY_YEARS)
    HFP_ari+noa_ltc_keep.xlsx   Yonkers condo bought in 2027 with cash, care from 2050 paid from savings
    HFP_ari+noa_ltc_sell.xlsx   the same, the condo sold in 2050 to pay for the care
    condo_grid.json             the scenarios run_suite.py reads: "work" ({name, what, set, hfp}: the
                                hfp edits as in work_sweep.py), "extra" (more main scenarios, same
                                format: the earnings-test case), "grid" (also place, year,
                                financing), "ltc", and "reference" (the grid entry equal to the baseline)
    work_variants.json          the same work variants for fork-notes/phase5/work_sweep.py

Amounts follow Owl's conventions: Budget lines in today's dollars; Fixed Assets value and basis in
the purchase year's dollars, Debts amounts and big-ticket items in that year's nominal dollars,
so a purchase price in today's dollars is grown by the case's own inflation path (gamma_n of the
case's rates). Run from the repository root:

    .venv/bin/python fork-notes/synthetic/make_cases.py [--out-dir DIR]

It overwrites what it wrote before (the files are generated, not edited by hand).
"""

import argparse
import copy
import importlib.util
import io
import json
import shutil
import sys
import tomllib
from pathlib import Path

import toml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "fork-notes" / "phase0" / "Case_us.template.toml"
sys.path.insert(0, str(ROOT / "src"))
from owlplanner.budget import SHEET_COLUMNS  # noqa: E402
from owlplanner.config import config_to_plan  # noqa: E402

_spec = importlib.util.spec_from_file_location("gen_hfp_us", ROOT / "fork-notes" / "phase0" / "gen_hfp_us.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

NAMES = ["Ari", "Noa"]
SLUG = "ari+noa"
DOB = ["1964-04-17", "1964-12-09"]      # the household's months, invented days (neither on the 1st)
HORIZON = 89
START = 2026
YEARS = list(range(START, 1964 + HORIZON + 1))

# Invented figures ($k for balances, monthly $ for PIAs).
# Accounts as the household's (user, 2026-10-29): a joint brokerage account, entered as two equal
# halves, larger than the two IRAs together; one IRA each; no Roth, no HSA. Amounts invented.
BALANCES = {
    "taxable_savings_balances": [800.0, 800.0],
    "taxable_cost_basis": [560.0, 560.0],
    "tax_deferred_savings_balances": [550.0, 400.0],
    "tax_free_savings_balances": [0.0, 0.0],
    "hsa_savings_balances": [0.0, 0.0],
}
PIAS = [3150, 2500]

# Wages in AGI (upstream #221: pay less the pre-tax 401k deferral). One of them has a 401k (user,
# 2026-10-29), rolled into that one's IRA at the end of work: in Owl both are the same tax-deferred
# account, so the rollover is no event. Here Ari has it (the real case puts it on whoever does):
# a deferral and an employer match while working full time. No IRA contribution for Noa: with Ari
# covered by a workplace plan, its deduction depends on the household's income (recalled, not
# checked), and Owl takes every IRA contribution as deductible. Amounts invented.
FULL = {
    "Ari": {"anticipated wages": 168000, "401k ctrb": 31000, "employer ctrb": 7000},
    "Noa": {"anticipated wages": 121000},
}
PART = {
    "Ari": {"anticipated wages": 60000, "401k ctrb": 0, "employer ctrb": 0},
    "Noa": {"anticipated wages": 45000},
}

# Work variants: (name, what, {person: (kind, years)}, aca_start_year, PIAs). 2026 is a full work
# year for both in every variant. Employer coverage is taken to cover both spouses while either
# works full time (Owl has one household aca_start_year; R2 = no, 2026-10-22); part-time work is
# taken to come without coverage. PIAs: stand-ins, a little higher with more work years (D4: the
# real ones come from SSA's calculator, one per variant).
WORK_VARIANTS = [
    ("both-stop-2026", "both stop at the end of 2026", {}, 2027, [3150, 2500]),
    ("ari-full-2027", "Ari works full time in 2027", {"Ari": ("full", [2027])}, 2028, [3190, 2500]),
    ("noa-full-2027", "Noa works full time in 2027", {"Noa": ("full", [2027])}, 2028, [3150, 2530]),
    ("both-full-2027", "both work full time in 2027", {"Ari": ("full", [2027]), "Noa": ("full", [2027])}, 2028,
     [3190, 2530]),
    ("ari-part-2027-28", "Ari works part time 2027-2028", {"Ari": ("part", [2027, 2028])}, 2027, [3170, 2500]),
    ("noa-part-2027-28", "Noa works part time 2027-2028", {"Noa": ("part", [2027, 2028])}, 2027, [3150, 2520]),
    ("both-part-2027-28", "both work part time 2027-2028",
     {"Ari": ("part", [2027, 2028]), "Noa": ("part", [2027, 2028])}, 2027, [3170, 2520]),
]

# Condo places. Price: the user's figure (today's $). Costs per year in today's $: invented
# stand-ins (property tax, HO-6 insurance), except the HOA (common charges, as 'maintenance'): the
# user's figure, $800/month in every place, growing with inflation (2026-10-29). NYC condos are tax
# class 2 (recalled, not checked against DOF). 10603 is split among school districts (White Plains
# City, Greenburgh Central, Valhalla; a secondary source, statisticalatlas.com): the condo's address
# decides; White Plains here. Valhalla is not in data/property_tax_relief.toml.
HOA = 800 * 12                 # condo HOA / common charges (user), today's $, real growth 0
PLACES = {
    "yonkers": {"what": "Yonkers (10701)", "price": 700000, "locality": "Yonkers",
                "district": "City of Yonkers / Yonkers", "move": False,
                "property tax": 9500, "maintenance": HOA, "insurance": 900},
    "whiteplains": {"what": "White Plains (10603)", "price": 700000, "locality": "",
                    "district": "City of White Plains / White Plains", "move": True,
                    "property tax": 11500, "maintenance": HOA, "insurance": 900},
    "queens": {"what": "Flushing, Queens (11354)", "price": 850000, "locality": "NYC",
               "district": "New York City / New York City (class 2)", "move": True,
               "property tax": 7000, "maintenance": HOA, "insurance": 900},
}
BUY_YEARS = [2027, 2029, 2031, 2034, 2038]
# The baseline's purchase: renting to the end is not an option (user, 2026-10-29: no landlord
# asking them to move at 85), so every comparison is against a purchase. Yonkers, where they rent
# now, at the start of 2027, with cash: a reference point, not a recommendation.
REFERENCE = ("yonkers", 2027, "cash")
CLOSING = 0.03                 # buyer's closing costs, share of the price (stand-in)
MORTGAGE_EXTRA = 0.02          # extra closing costs with a loan (recording tax, lender fees), share of the loan
DOWN = 0.20
MORTGAGE_RATE = 6.25           # nominal, 30-year fixed (stand-in)
HOME_RATE = 0.5                # real growth of the condo's value (stand-in)
COMMISSION = 5.0               # selling cost at the plan end or at a sale (stand-in)
RENT = 4000 * 12               # Yonkers rent (user, 2026-10-29): $4,000/month, the same in 2027, then
#                                growing with inflation (rent_lines)
CARE = 110000                  # care per year from 2050 (age 86), today's $ (stand-in)
CARE_YEAR = 2050
OUT_OF_POCKET = 4500             # out-of-pocket medical per year, today's $ (stand-in)


def line(name, typ, year, end, amount, rate=0.0, survivor=None, essential=False, **age):
    row = {"active": True, "name": name, "type": typ, "year": year, "end": end, "amount": amount,
           "rate": rate, "survivor": survivor, "essential": essential,
           "clock": None, "start_age": None, "end_age": None, "index": None, "kind": None}
    row.update(age)
    return [row[c] for c in SHEET_COLUMNS]


# Lines shared by every workbook: discretionary core, an age-clock travel line (Track B), essential
# out-of-pocket medical, the template's gold-plan lines (for these birth months), charity.
COMMON = [
    line("core", "core", START, 0, 72000),
    line("travel while able", "travel", None, None, 12000, clock="age", start_age=62, end_age=80, index="younger"),
    line("out of pocket medical", "medical", START, 0, OUT_OF_POCKET, rate=2.0, survivor=60, essential=True),
    *[line(gl[1], gl[2], gl[3], gl[4], gl[5], rate=gl[6], survivor=gl[7], essential=gl[8])
      for gl in gen.BUDGET_LINES[1:]],
    line("charity", "charity", START, 0, 3000),
]


def rent_lines(gamma, last_year=0):
    """Rent from START to last_year (0: the plan end): RENT in 2026, the same nominal amount in 2027
    (so RENT / gamma[1] in today's dollars), then that amount with inflation (real growth 0)."""
    lines = [line("rent", "rent", START, START, RENT, essential=True)]
    if last_year == 0 or last_year > START:
        lines.append(line("rent from 2027", "rent", START + 1, last_year, round(RENT / float(gamma[1])),
                          essential=True))
    return lines


def owner_lines(place, first_year, last_year=0):
    c = PLACES[place]
    return [line("property tax", "property tax", first_year, last_year, c["property tax"], rate=1.0, essential=True),
            line("HOA", "maintenance", first_year, last_year, c["maintenance"], essential=True),
            line("condo insurance", "insurance", first_year, last_year, c["insurance"], essential=True)]


def write_hfp(path, budget, work=None, debts=(), assets=(), big_ticket=()):
    """One workbook: full-time wages in 2026 for both, `work` = {person: (kind, years)} after that."""
    wb = gen.write_hfp(path, names=NAMES, years=YEARS, budget_lines=[], overwrite=True)
    work = work or {}
    for name in NAMES:
        ws = wb[name]
        cols = {c.value: c.column for c in ws[1]}
        kind, years = work.get(name, (None, []))
        for r in range(2, ws.max_row + 1):
            year = ws.cell(r, cols["year"]).value
            if year == START:
                values = FULL[name]
            elif year in years:
                values = (FULL if kind == "full" else PART)[name]
            else:
                values = {}
            for k, v in values.items():
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
    c["description"] = ("Synthetic couple with the household's structure (fork-notes/synthetic/make_cases.py): "
                        "invented balances, wages, PIAs and costs. Not the household's case.")
    bi = c["basic_info"]
    bi.update(names=NAMES, sexes=["M", "F"], date_of_birth=DOB, life_expectancy=[HORIZON, HORIZON],
              start_date=f"{START}-01-01", state="NY", locality="Yonkers", school_district="")
    c["savings_assets"].update(BALANCES)
    c["household_financial_profile"]["HFP_file_name"] = hfp
    c["fixed_income"]["social_security_pia_amounts"] = PIAS
    c["optimization_parameters"]["medical_inflation_excess"] = 1.5
    # The HSA cap: Medicare premiums plus other_medical_expenses; the budget's medical line does not
    # raise it, so the out-of-pocket line's amount goes here too (it is not claimed twice).
    c["optimization_parameters"]["other_medical_expenses"] = OUT_OF_POCKET / 1000
    for section, values in changes.items():
        c.setdefault(section, {}).update(values)
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(ROOT / "fork-notes" / "synthetic" / "cases"))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("HFP_*.xlsx"):
        old.unlink()
    with open(TEMPLATE, "rb") as f:
        template = tomllib.load(f)

    ref_district = PLACES[REFERENCE[0]]["district"]
    base = case(template, f"HFP_{SLUG}.xlsx", basic_info={"school_district": ref_district})
    condo = case(template, f"HFP_{SLUG}.xlsx", basic_info={"school_district": ref_district},
                 solver_options={"breakpointMethod": "local-search"})
    for name, conf in ((f"Case_{SLUG}.toml", base), (f"Case_{SLUG}_condo.toml", condo)):
        with open(out / name, "w", encoding="utf-8") as f:
            toml.dump(conf, f)
    # The case's own inflation path, to put purchase-year amounts in that year's dollars.
    gamma = config_to_plan(copy.deepcopy(base), str(out), logstreams=[io.StringIO()], loadHFP=False).gamma_n

    def nominal(amount, year):
        return round(amount * float(gamma[year - START]))

    # Work variants: edits of the baseline workbook (the format work_sweep.py reads), so each one
    # carries the baseline's purchase.
    work_json = []
    for name, what, work, aca, pias in WORK_VARIANTS:
        hfp_edits = {}
        for person, (kind, years) in work.items():
            vals = (FULL if kind == "full" else PART)[person]
            hfp_edits[person] = [{"years": [years[0], years[-1]], **vals, "months worked": 12}]
        work_json.append({"name": name, "what": what,
                          "set": [f"aca_settings.aca_start_year={aca}",
                                  f"fixed_income.social_security_pia_amounts={json.dumps(pias)}"],
                          **({"hfp": hfp_edits} if hfp_edits else {})})

    # The SSA earnings test: with these figures every variant claims at 70, so nobody is paid before
    # FRA while working. Force it: Noa (62 in December 2026) works part time in 2027-2028 above the
    # exempt amount, and both claim at 62.
    noa_part = next(w for w in work_json if w["name"] == "noa-part-2027-28")
    extra = [{"name": "noa-part-claim-62", "what": "Noa works part time 2027-2028, both claim at 62 (earnings test)",
              "set": [*noa_part["set"], "solver_options.withSSAges=fixed",
                      "fixed_income.social_security_ages=[62.0, 62.0]"],
              "hfp": noa_part["hfp"]}]

    grid = []
    for place, c in PLACES.items():
        for year in BUY_YEARS:
            price = nominal(c["price"], year)
            asset = [True, f"{place} condo", "residence", year, price, price, HOME_RATE, 0, COMMISSION]
            budget = COMMON + rent_lines(gamma, year - 1) + owner_lines(place, year)
            if c["move"]:
                sets = ["basic_info.moves=" + json.dumps(
                    [{"year": year, "state": "NY", "locality": c["locality"], "school_district": c["district"]}])]
            else:
                sets = [f"basic_info.school_district={c['district']}"]
            for fin in ("cash", "mortgage"):
                hfp = f"HFP_{SLUG}_condo_{place}_{year}_{fin}.xlsx"
                if fin == "cash":
                    write_hfp(out / hfp, budget, assets=[asset],
                              big_ticket=[("Ari", year, -round(price * (1 + CLOSING)))])
                else:
                    loan = round(price * (1 - DOWN))
                    write_hfp(out / hfp, budget, assets=[asset],
                              debts=[[True, f"{place} mortgage", "mortgage", year, 30, loan, MORTGAGE_RATE,
                                      f"{place} condo"]],
                              big_ticket=[("Ari", year, -round(price * (DOWN + CLOSING) + loan * MORTGAGE_EXTRA))])
                if (place, year, fin) == REFERENCE:
                    shutil.copyfile(out / hfp, out / f"HFP_{SLUG}.xlsx")
                grid.append({"name": f"{place}-{year}-{fin}", "place": place, "year": year, "financing": fin,
                             "what": f"buy in {c['what']} in {year}, {fin}",
                             "set": [f"household_financial_profile.HFP_file_name={hfp}", *sets]})

    # Long-term care: the Yonkers condo bought in 2027 with cash, care from CARE_YEAR to the end.
    price = nominal(PLACES["yonkers"]["price"], 2027)
    care = [line("care", "care", CARE_YEAR, 0, CARE, essential=True)]
    tix = [("Ari", 2027, -round(price * (1 + CLOSING)))]
    keep = [True, "yonkers condo", "residence", 2027, price, price, HOME_RATE, 0, COMMISSION]
    sell = [True, "yonkers condo", "residence", 2027, price, price, HOME_RATE, CARE_YEAR, COMMISSION]
    write_hfp(out / f"HFP_{SLUG}_ltc_keep.xlsx", COMMON + rent_lines(gamma, 2026) + owner_lines("yonkers", 2027) + care,
              assets=[keep], big_ticket=tix)
    write_hfp(out / f"HFP_{SLUG}_ltc_sell.xlsx",
              COMMON + rent_lines(gamma, 2026) + owner_lines("yonkers", 2027, CARE_YEAR - 1) + care,
              assets=[sell], big_ticket=tix)
    district = f"basic_info.school_district={PLACES['yonkers']['district']}"
    ltc = [{"name": "ltc-keep", "what": f"Yonkers condo (2027, cash) kept; care {CARE:,}/yr from {CARE_YEAR} "
                                        "paid from savings",
            "set": [f"household_financial_profile.HFP_file_name=HFP_{SLUG}_ltc_keep.xlsx", district]},
           {"name": "ltc-sell", "what": f"the same, the condo sold in {CARE_YEAR} to pay for the care",
            "set": [f"household_financial_profile.HFP_file_name=HFP_{SLUG}_ltc_sell.xlsx", district]}]

    with open(out / "condo_grid.json", "w", encoding="utf-8") as f:
        json.dump({"description": "Condo purchase grid and long-term-care pair (make_cases.py); invented costs.",
                   "reference": "-".join(map(str, REFERENCE)), "grid": grid, "ltc": ltc, "work": work_json,
                   "extra": extra},
                  f, indent=1)
        f.write("\n")
    with open(out / "work_variants.json", "w", encoding="utf-8") as f:
        json.dump({"description": ("Synthetic work variants for work_sweep.py (fork-notes/synthetic/make_cases.py). "
                                   "Invented wages; PIAs are stand-ins, not SSA estimates (D4)."),
                   "set": ["solver_options.withSSAges=optimize"],
                   "variants": [{k: w[k] for k in ("name", "set", "hfp") if k in w} for w in work_json]},
                  f, indent=1)
        f.write("\n")
    print(f"Wrote the synthetic household to {out}: {len(list(out.glob('HFP_*.xlsx')))} workbooks, "
          f"{len(grid)} condo variants, {len(work_json)} work variants.")


if __name__ == "__main__":
    main()

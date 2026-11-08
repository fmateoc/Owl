"""The Run page's "why" views (UX review Q15-Q17, 2026-11-07): `ui/run_charts.py`.

Q15: every IRMAA tier with its premium year, the bracket tops as faint steps, distinct hues
and dashes for IRMAA and the 400% FPL line, older results without some keys still drawn.
Q16: the premiums beside the taxes; all-zero income series left out; a purchase year that
would set the scale annotated instead. Q17: the one-year paragraph and the Sankey come from
the same groups, and each side's groups add up to its total.

Copyright (C) 2024-2026 Martin-D. Lacasse and The Owl Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from pathlib import Path

import pytest

UI_DIR = Path(__file__).resolve().parents[2] / "ui"


@pytest.fixture
def rc(monkeypatch):
    monkeypatch.syspath_prepend(str(UI_DIR))
    import run_charts

    return run_charts


def _bracket_row(year, magi, income=60_000.0, conversion=10_000.0):
    tiers = [218_000.0, 274_000.0, 342_000.0, 410_000.0, 750_000.0]
    return {"year": year, "ordinary_taxable_income": income, "conversion": conversion,
            "conversion_taxable": conversion, "magi": magi, "fills_bracket": "12/15%",
            "room_to_next_edge": 40_800.0,
            "ordinary_edges": [{"label": "10%", "amount": 24_800.0}, {"label": "12/15%", "amount": 100_800.0},
                               {"label": "22/25%", "amount": 211_400.0}, {"label": "24/28%", "amount": 403_550.0},
                               {"label": "32/33%", "amount": 512_450.0}],
            "irmaa_edges": [{"label": f"IRMAA tier {k}", "amount": a, "premium_year": year + 2}
                            for k, a in enumerate(tiers, start=1)],
            "aca_lines": [{"label": "400% FPL (the subsidy cliff)", "amount": 84_202.0}] if year < 2029 else []}


class TestBrackets:
    def test_every_reachable_irmaa_tier_is_drawn_with_its_premium_year(self, rc):
        years = [_bracket_row(2027, 300_000.0), _bracket_row(2028, 120_000.0), _bracket_row(2029, 110_000.0)]
        fig, note = rc.brackets_figure(years)
        traces = {t.name: t for t in fig.data}
        tiers = [name for name in traces if name.startswith("IRMAA tier")]
        # MAGI tops at 300k: the chart runs to 360k, so tiers 1-3 are on it and 4-5 are named.
        assert [t.split(" (")[0] for t in tiers] == ["IRMAA tier 1", "IRMAA tier 2", "IRMAA tier 3"]
        assert note == "Above the chart, never reached: IRMAA tier 4 (from 410,000); IRMAA tier 5 (from 750,000)."
        tier1 = traces[tiers[0]]
        assert list(tier1.customdata) == [2029, 2030, 2031]  # the premium year each income sets
        assert "Medicare" in tier1.hovertemplate and tier1.line.dash == "dash"
        cliff = next(t for name, t in traces.items() if name.startswith("400% FPL"))
        assert cliff.line.color != tier1.line.color and cliff.line.dash == "dashdot"
        assert list(cliff.y) == [84_202.0, 84_202.0, None]

    def test_the_bracket_tops_are_steps_not_a_zigzag(self, rc):
        years = [_bracket_row(2027, 120_000.0, income=30_000.0), _bracket_row(2028, 120_000.0, income=150_000.0)]
        fig, _note = rc.brackets_figure(years)
        tops = [t for t in fig.data if (t.name or "").startswith("top of the")]
        # One flat line per bracket top on the chart (the old line followed the year's bracket).
        assert [t.name for t in tops] == ["top of the 10% bracket", "top of the 12/15% bracket"]
        assert all(len(set(t.y)) == 1 and t.line.shape == "hv" for t in tops)

    def test_an_older_result_without_the_lines_still_draws(self, rc):
        years = [{"year": 2027, "ordinary_taxable_income": 50_000.0, "conversion": 5_000.0, "magi": 70_000.0},
                 {"year": 2028, "ordinary_taxable_income": 40_000.0, "conversion": 0.0, "magi": 60_000.0}]
        fig, note = rc.brackets_figure(years)
        assert note == ""
        assert [t.name for t in fig.data][:3] == ["taxable income, ex conversions",
                                                  "Roth conversions (their taxable part)",
                                                  "MAGI (what IRMAA and the cliff read)"]
        table = rc.brackets_table(years)
        assert (table["IRMAA tier"] == "-").all() and list(table["Of which taxable"]) == [5_000.0, 0.0]


class TestTaxesAndIncome:
    BY_YEAR = [
        {"year": 2027, "federal_income_tax": 7_000, "ltcg_tax": 36_000, "niit": 4_900, "payroll_tax": 0,
         "state_tax": 22_500, "medicare_premiums": 0, "aca_premiums": 21_700, "wages": 0,
         "ss_income": [0, 0], "pension_income": 0, "spia_income": 0, "portfolio_withdrawals": 975_000},
        {"year": 2028, "federal_income_tax": 2_000, "ltcg_tax": 1_000, "niit": 0, "payroll_tax": 0,
         "state_tax": 2_500, "medicare_premiums": 2_300, "aca_premiums": 13_800, "wages": 0,
         "ss_income": [0, 0], "pension_income": 0, "spia_income": 0, "portfolio_withdrawals": 180_000},
        {"year": 2029, "federal_income_tax": 2_000, "ltcg_tax": 1_000, "niit": 0, "payroll_tax": 0,
         "state_tax": 2_500, "medicare_premiums": 6_700, "aca_premiums": 0, "wages": 0,
         "ss_income": [30_000, 0], "pension_income": 0, "spia_income": 0, "portfolio_withdrawals": 150_000},
    ]

    def test_the_premiums_are_drawn_beside_the_taxes(self, rc):
        names = [t.name for t in rc.taxes_and_premiums_figure(self.BY_YEAR).data]
        assert "Medicare premiums (with IRMAA)" in names and "Marketplace (ACA) premiums" in names

    def test_the_chart_series_take_the_one_word_map(self, rc):
        """QW-1 (review AN6): the chart said "Gains tax", "State + local" and "Marketplace
        premiums" where the paragraph and the Sankey said otherwise."""
        names = [t.name for t in rc.taxes_and_premiums_figure(self.BY_YEAR).data]
        for row in ("Federal income tax", "Gains tax", "NIIT", "State and local tax",
                    "Medicare premiums", "ACA premiums"):
            assert rc.flow_label(row) in names
        assert "Capital gains tax" in names and "State and local tax" in names
        assert not {"Gains tax", "State + local", "Marketplace premiums"} & set(names)

    def test_zero_series_are_left_out_and_the_purchase_year_annotated(self, rc):
        fig = rc.income_sources_figure(self.BY_YEAR, purchases={0: 741_188.0})
        assert [t.name for t in fig.data] == ["Social Security", "Withdrawals from savings"]
        assert tuple(fig.layout.yaxis.range) == (0, pytest.approx(1.3 * 180_000))
        assert "741,188" in fig.layout.annotations[0].text and "975,000" in fig.layout.annotations[0].text

    def test_without_a_purchase_the_scale_is_left_alone(self, rc):
        fig = rc.income_sources_figure(self.BY_YEAR)
        assert fig.layout.yaxis.range is None and not fig.layout.annotations

    def test_the_big_ticket_years_come_from_the_cash_flow(self, rc):
        assert rc.big_ticket_years({"uses": {"Big-ticket purchases": [0, 741_188.0, 0]}}) == {1: 741_188.0}
        assert rc.big_ticket_years({}) == {}


class TestOneYear:
    SOURCES = {"Taxable-account withdrawals": 888_582.0, "Tax-deferred withdrawals": 86_389.0,
               "Roth conversions (from the tax-deferred accounts)": 20_000.0,
               "State and local tax, net refund": 1_000.0}
    USES = {"core": 90_000.0, "rent": 51_369.0, "Big-ticket purchases": 741_188.0, "Gains tax": 36_187.0,
            "State and local tax": 22_499.0, "NIIT": 4_911.0, "ACA premiums": 21_745.0,
            "Roth conversions": 20_000.0, "Savings (surplus)": 8_072.0}

    def test_the_groups_partition_each_side(self, rc):
        b = rc.year_breakdown(self.SOURCES, self.USES)
        assert sum(sum(g.values()) for g in b["uses"].values()) == sum(self.USES.values())
        assert sum(sum(g.values()) for g in b["sources"].values()) == sum(self.SOURCES.values())
        assert set(b["uses"]["taxes"]) == {"Gains tax", "State and local tax", "NIIT"}
        assert set(b["uses"]["spending"]) == {"core", "rent"}
        # QW-1: a refunded tax is a tax offset, never income.
        assert set(b["sources"]["tax_offsets"]) == {"State and local tax, net refund"}
        assert b["sources"]["income"] == {}

    def test_the_paragraph_reads_the_same_rows(self, rc):
        text = rc.year_summary(2027, self.SOURCES, self.USES)
        assert text.startswith("**2027**: spending \\$141,369 plus big-ticket purchases \\$741,188.")
        # Decision 6: the taxes the Sankey draws, and the refund its own clause.
        assert ("Taxes \\$63,597: capital gains tax \\$36,187, state and local tax \\$22,499, "
                "NIIT (3.8%) \\$4,911, federal income tax \\$0; state and local, a net refund of "
                "\\$1,000 (a refundable credit is larger than the tax).") in text
        assert "comes from income" not in text and "net of" not in text
        assert "Health premiums \\$21,745 (marketplace (ACA) premiums \\$21,745)." in text
        assert "\\$8,072 goes back into savings." in text
        assert "the taxable (brokerage) accounts \\$888,582" in text

    def test_star_is_named_only_when_the_run_has_it(self, rc):
        with_star = rc.year_summary(2027, self.SOURCES, self.USES, star=True)
        assert "a net refund of \\$1,000 (the STAR credit is larger than the tax)" in with_star
        labels = list(rc.sankey_figure(2027, self.SOURCES, self.USES, star=True).data[0].node.label)
        assert "State tax refund (STAR): $1,000" in labels
        labels = list(rc.sankey_figure(2027, self.SOURCES, self.USES).data[0].node.label)
        assert "State tax refund: $1,000" in labels and not any("STAR" in x for x in labels)

    def test_every_figure_the_paragraph_names_is_on_a_sankey_node(self, rc):
        """Review AO2: the paragraph's group totals are the Sankey's figures too. On d64ec67
        "The money comes from savings, $158,708 (...)" was on no node in 210 of 280 one-year
        paragraphs of ten Quick looks of the synthetic baseline: the sources had no group
        nodes. Several accounts, several incomes, a conversion, a refund, budget lines, a
        purchase, a loan, both premiums and a surplus."""
        import re

        sources = {"Taxable-account withdrawals": 127_435.0, "Tax-deferred withdrawals": 31_273.0,
                   "Roth withdrawals": 7_017.0, "Social Security": 52_000.0, "Pensions": 12_000.0,
                   "Roth conversions (from the tax-deferred accounts)": 16_953.0,
                   "State and local tax, net refund": 1_876.0}
        uses = {"core": 98_000.0, "travel while able": 23_340.0, "Big-ticket purchases": 30_000.0,
                "Debt payments": 12_000.0, "Federal income tax": 3_778.0, "Gains tax": 1_200.0,
                "ACA premiums": 7_261.0, "Medicare premiums": 2_305.0, "Roth conversions": 16_953.0}
        uses["Savings (surplus)"] = round(sum(sources.values()) - sum(uses.values()), 2)
        assert uses["Savings (surplus)"] > 0
        text = rc.year_summary(2029, sources, uses, star=True)
        figures = {float(x.replace(",", "")) for x in re.findall(r"\\\$([\d,]+)", text)}
        nodes = {float(lbl.rsplit("$", 1)[1].replace(",", ""))
                 for lbl in rc.sankey_figure(2029, sources, uses, star=True).data[0].node.label}
        assert {165_725.0, 64_000.0} <= figures  # the savings and income totals are named
        assert figures <= nodes, sorted(figures - nodes)
        labels = list(rc.sankey_figure(2029, sources, uses, star=True).data[0].node.label)
        assert "From savings: $165,725" in labels and "Income: $64,000" in labels
        # One line of its own needs no group node: it is its own total. Nor does the only source
        # group: the hub carries its total, and the paragraph names none ("All of it comes
        # from savings: ...").
        one = rc.sankey_figure(2029, {"Taxable-account withdrawals": 90_000.0}, {"Net spending": 90_000.0})
        assert not any(lbl.startswith("From savings") for lbl in one.data[0].node.label)
        only = {"Taxable-account withdrawals": 60_000.0, "Tax-deferred withdrawals": 30_000.0}
        assert "All of it comes from savings" in rc.year_summary(2029, only, {"Net spending": 90_000.0})
        labels = rc.sankey_figure(2029, only, {"Net spending": 90_000.0}).data[0].node.label
        assert not any(lbl.startswith("From savings") for lbl in labels)

    def test_every_tax_figure_the_paragraph_names_is_on_a_sankey_node(self, rc):
        """Review AN6: the build netted the refund into the taxes ("Taxes net of a \\$2,934
        ... refund took \\$2,177"), a figure on no node and in no table. The 2034 shape of the
        Careful baseline: \\$5,111 federal income tax, a \\$2,934 STAR refund."""
        import re

        sources = {"Taxable-account withdrawals": 60_000.0, "Social Security": 50_000.0,
                   "State and local tax, net refund": 2_934.0}
        uses = {"core": 107_823.0, "Federal income tax": 5_111.0}
        text = rc.year_summary(2034, sources, uses, star=True)
        taxes = text[text.index("Taxes"):]
        taxes = taxes[:taxes.index(").") + 2]
        figures = {float(x.replace(",", "")) for x in re.findall(r"\\\$([\d,]+)", taxes)}
        nodes = {float(lbl.rsplit("$", 1)[1].replace(",", ""))
                 for lbl in rc.sankey_figure(2034, sources, uses, star=True).data[0].node.label}
        assert figures == {5_111.0, 2_934.0}
        assert figures <= nodes

    def test_a_refund_bigger_than_the_taxes_is_its_own_clause(self, rc):
        sources = {"Wages": 10_000.0, "Social Security": 5_000.0, "State and local tax, net refund": 4_000.0}
        uses = {"core": 19_000.0}
        text = rc.year_summary(2028, sources, uses)
        assert "All of it comes from income" not in text
        assert "The money comes from income, \\$15,000 (wages \\$10,000, Social Security \\$5,000)." in text
        assert ("Taxes \\$0: federal income tax \\$0; state and local, a net refund of \\$4,000 "
                "(a refundable credit is larger than the tax).") in text
        labels = list(rc.sankey_figure(2028, sources, uses).data[0].node.label)
        assert "Income: $15,000" in labels

    def test_the_sankey_carries_the_amounts_and_the_taxes_total(self, rc):
        fig = rc.sankey_figure(2027, self.SOURCES, self.USES)
        sankey = fig.data[0]
        labels = list(sankey.node.label)
        hub = labels.index(f"2027 cash flow: ${sum(self.SOURCES.values()):,.0f}")
        assert "Taxes: $63,597" in labels and "Capital gains tax: $36,187" in labels
        assert "Marketplace (ACA) premiums: $21,745" in labels
        assert "Taxable (brokerage) accounts: $888,582" in labels  # AM6: the prose's words
        links = list(zip(sankey.link.source, sankey.link.target, sankey.link.value, strict=True))
        into_hub = sum(v for s, t, v in links if t == hub)
        out_of_hub = sum(v for s, t, v in links if s == hub)
        assert into_hub == pytest.approx(sum(self.SOURCES.values()))
        assert out_of_hub == pytest.approx(sum(self.USES.values()))

    def test_one_premium_line_still_gets_the_health_premiums_node(self, rc):
        """QW-1: the node vanished whenever a year had a single premium line."""
        uses = {"core": 90_000.0, "ACA premiums": 21_745.0}
        labels = list(rc.sankey_figure(2027, {"Wages": 111_745.0}, uses).data[0].node.label)
        assert "Health premiums: $21,745" in labels and "Marketplace (ACA) premiums: $21,745" in labels

    def test_net_spending_alone_needs_no_spending_node(self, rc):
        """Review AN6: "Net spending" alone got a Spending node over it with the same number."""
        labels = list(rc.sankey_figure(2027, {"Wages": 90_000.0}, {"Net spending": 90_000.0}).data[0].node.label)
        assert "Net spending: $90,000" in labels and "Spending: $90,000" not in labels
        labels = list(rc.sankey_figure(2027, {"Wages": 90_000.0}, {"core": 90_000.0}).data[0].node.label)
        assert "Spending: $90,000" in labels  # a budget's line keeps its group node

    def test_the_table_groups_each_side_and_its_totals_are_the_caption_s(self, rc):
        table = rc.flows_table(self.SOURCES, self.USES, star=True)
        assert list(table.columns) == ["Sources", "Uses"]
        left, right = list(table["Sources"]), list(table["Uses"])
        assert left[0] == "From savings  $974,971"
        assert left[1] == "\u2003Taxable (brokerage) accounts  $888,582"
        assert "Tax refunds  $1,000" in left and "\u2003State tax refund (STAR)  $1,000" in left
        assert "Taxes  $63,597" in right and "\u2003Capital gains tax  $36,187" in right
        assert "Big-ticket purchases  $741,188" in right
        assert "\u2003Big-ticket purchases  $741,188" not in right  # no line repeating its group
        # The totals line: the caption's in and out.
        assert left[-1] == f"Total in  ${sum(self.SOURCES.values()):,.0f}"
        assert right[-1] == f"Total out  ${sum(self.USES.values()):,.0f}"


def test_the_table_keeps_years_whole_and_empty_cells_empty(rc):
    years = [_bracket_row(2027, 120_000.0), {**_bracket_row(2052, 90_000.0), "irmaa_edges": [], "aca_lines": []}]
    table = rc.brackets_table(years)
    assert str(table["Year"].dtype) == "Int64"
    # N2 (review AN10): Streamlit 1.66 draws any missing number as "None" (a float NaN, a
    # Float64 pd.NA, an object None: checked with Playwright); only an empty text cell is blank.
    assert table["400% FPL"].tolist()[1] == "" and table["400% FPL"].tolist()[0] != ""
    assert table["400% FPL"].tolist()[0].replace(",", "").isdigit()
    assert table["IRMAA tier"][1] == "-" and table["Next limit"][1] != ""


class TestTheActiveTierAndNextLimit:
    """QW-3 (ux-qw-handoff-2.md, review AN5): the IRMAA column says the tier the MAGI is in,
    or its room below tier 1, with the premium year -- never the overshoot where a premium is
    expected, never a premium year with nobody on Medicare -- and *Next limit* names the
    case's own limits on the year's conversions, then the closest line above the income."""

    def test_the_tier_the_magi_is_in_with_its_overshoot_and_premium_year(self, rc):
        table = rc.brackets_table([_bracket_row(2027, 300_000.0)])
        assert table["IRMAA tier"][0] == "tier 2 ($26,000 over its $274,000 edge): 2029 premiums"

    def test_below_every_tier_the_room_under_tier_1(self, rc):
        table = rc.brackets_table([_bracket_row(2027, 120_000.0)])
        assert table["IRMAA tier"][0] == "below tier 1 by $98,000: 2029 premiums"

    def test_a_premium_year_with_no_medicare_says_so(self, rc):
        """Review AN5: 2026's cell read "crossed (+$12,802 in 2028)" with nobody on Medicare
        in 2028 (both turn 65 in 2029)."""
        row = {**_bracket_row(2026, 300_000.0), "irmaa_edges": [], "medicare_in_premium_year": False}
        assert rc.brackets_table([row])["IRMAA tier"][0] == "no Medicare premiums in 2028"
        # A row written before the flag: judged from its ages two years on.
        old = {**_bracket_row(2026, 300_000.0), "ages": [62, 62]}
        assert rc.brackets_table([old])["IRMAA tier"][0] == "no Medicare premiums in 2028"
        old = {**_bracket_row(2026, 300_000.0), "ages": [62, 64]}
        assert rc.brackets_table([old])["IRMAA tier"][0].startswith("tier 2")

    def test_the_next_limit_is_the_closest_line_above_on_its_own_measure(self, rc):
        # MAGI 300,000, taxable income 60,000: the 12/15% top ($40,800 of room on taxable
        # income) is closer than IRMAA tier 3 ($42,000 of room on MAGI).
        table = rc.brackets_table([_bracket_row(2027, 300_000.0)])
        assert table["Next limit"][0] == "12/15% bracket top: $40,800 away"
        row = {**_bracket_row(2027, 330_000.0)}
        assert rc.brackets_table([row])["Next limit"][0] == "IRMAA tier 3: $12,000 away (2029 premiums)"

    def test_the_case_s_cap_is_named_with_the_person(self, rc):
        row = {**_bracket_row(2027, 300_000.0), "conversion_limit": ["cap", "cap"]}
        assert rc.brackets_table([row], names=["Ari", "Noa"])["Next limit"][0] == "conversion cap reached (Ari, Noa)"
        # One person at the cap, the other free: the cap, then the line the other one meets.
        row = {**_bracket_row(2027, 300_000.0), "conversion_limit": ["cap", None]}
        assert rc.brackets_table([row], names=["Ari", "Noa"])["Next limit"][0] == (
            "conversion cap reached (Ari); 12/15% bracket top: $40,800 away")

    def test_a_year_before_the_window(self, rc):
        row = {**_bracket_row(2027, 120_000.0), "conversion_limit": ["window", "window"]}
        text = rc.brackets_table([row], {"start": 2028, "stop": None, "swap": None}, ["Ari", "Noa"])["Next limit"][0]
        assert text == "no conversions before 2028 (the case's window)"

    def test_the_last_years_and_the_pins(self, rc):
        row = {**_bracket_row(2027, 120_000.0), "conversion_limit": ["last years", "pinned"]}
        text = rc.brackets_table([row], names=["Ari", "Noa"])["Next limit"][0]
        assert text == ("no conversions in the last two years of life (Ari); conversion held at "
                        "the case's amount (Noa, Roth conv fixed)")

    def test_an_older_row_gets_the_lines_only(self, rc):
        """A build-era row carries the household's `conversion_cap`, which the page no longer
        reads (review AN5: a documented "no cap" read "Conversion cap ($-2,000)")."""
        row = {**_bracket_row(2027, 300_000.0), "conversion": 50_000.0, "conversion_cap": -2_000.0}
        assert rc.brackets_table([row])["Next limit"][0] == "12/15% bracket top: $40,800 away"

    def test_nothing_above_says_so(self, rc):
        row = {**_bracket_row(2027, 300_000.0), "ordinary_edges": [], "irmaa_edges": [],
               "aca_lines": []}
        assert rc.brackets_table([row])["Next limit"][0] == "-"


def test_no_page_uses_the_plain_number_format():
    """Streamlit 1.66 renders some integers wrongly with format="plain" (2028 as
    2027.9999999999998, 2034 as 2034.0000000000002; seen in a browser, 2026-11-07)."""
    offenders = [p.name for p in UI_DIR.glob("*.py") if 'format="plain"' in p.read_text(encoding="utf-8")]
    assert offenders == []


def _threshold(year, kind, label, side, amount, cost, *, boundary, group=None, affects=None,
               note="a note", total=None):
    e = {"year": year, "kind": kind, "label": label, "side": side, "amount_today_dollars": amount,
         "boundary_today_dollars": boundary, "cost_today_dollars": cost, "affects": affects, "note": note}
    if group is not None:
        e["group"] = group
    if total is not None:
        e["total_today_dollars"] = total
    return e


CLIFF = "marketplace subsidy cliff (400% FPL)"


def _baseline_like(groups=True):
    """The Careful baseline's shape (ux-qw-handoff-2.md): three years over the 400% line,
    2029 in IRMAA tier 2, over the Enhanced STAR limit, four small recapture rows, a ramp."""
    g = (lambda name: name) if groups else (lambda name: None)
    return [
        _threshold(2027, "aca", CLIFF, "over", 48_000.0, 12_547.0, boundary=84_202.0, group=g("over")),
        _threshold(2028, "aca", CLIFF, "over", 49_000.0, 12_865.0, boundary=84_202.0, group=g("over")),
        _threshold(2029, "aca", CLIFF, "over", 20_000.0, 4_824.0, boundary=84_202.0, group=g("over")),
        _threshold(2029, "irmaa", "IRMAA tier 2", "over", 38_466.0, 3_741.0, boundary=289_559.0,
                   group=g("over"), affects=2031, total=6_215.0, note="paid in 2031 via the lookback"),
        _threshold(2029, "star", "Enhanced STAR limit", "over", 180_000.0, 1_546.0, boundary=110_000.0,
                   group=g("over"), affects=2031),
        _threshold(2030, "irmaa", "IRMAA tier 1", "under", 9_000.0, 2_200.0, boundary=230_000.0,
                   group=g("near"), affects=2032),
        *[_threshold(2034 + k, "state_recapture", "NY benefit recapture starts", "over", 400.0, cost,
                     boundary=107_650.0, group=g("near"))
          for k, cost in enumerate((26.48, 19.19, 4.42, 3.03))],
        _threshold(2040, "ss_taxability", "SS 85% taxation starts", "over", 1_000.0, None,
                   boundary=44_000.0, group=g("near")),
    ]


class TestThingsToLookAt:
    """QW-2's page side (ux-qw-handoff-2.md, decisions 2b-2d): the floor, the fold, the merge,
    the plain columns, and an older result."""

    def test_the_columns_are_in_plain_words(self, rc):
        parts = rc.threshold_parts(_baseline_like(), 0.05)
        for name in ("over", "near", "small"):
            assert list(parts[name].columns) == ["Year of income", "Line", "Where", "Costs", "Paid in", "Note"]

    def test_consecutive_years_over_the_same_line_are_one_row_largest_cost_first(self, rc):
        over = rc.threshold_parts(_baseline_like(), 0.05)["over"]
        assert list(over["Line"]) == [CLIFF, "IRMAA tier 2", "Enhanced STAR limit"]
        cliff = over.iloc[0]
        assert cliff["Year of income"] == "2027-2029"
        assert cliff["Where"] == "$20,000-$49,000 over"
        assert cliff["Costs"] == "$4,824-$12,865"
        assert cliff["Paid in"] == "2027-2029"

    def test_the_irmaa_row_carries_its_step_its_year_total_and_its_payment_year(self, rc):
        over = rc.threshold_parts(_baseline_like(), 0.05)["over"]
        irmaa = over[over["Line"] == "IRMAA tier 2"].iloc[0]
        assert irmaa["Costs"] == "$3,741 (whole year $6,215)"
        assert irmaa["Paid in"] == "2031" and irmaa["Year of income"] == "2029"

    def test_the_floor_folds_small_items_and_ramps_instead_of_dropping_them(self, rc):
        parts = rc.threshold_parts(_baseline_like(), 0.05)
        small = parts["small"]
        assert len(small) == 5  # the four recapture rows and the ramp
        assert sorted(small["Costs"]) == sorted(["$26", "$19", "$4", "$3", "-"])
        assert list(parts["near"]["Line"]) == ["IRMAA tier 1"]
        # Everything is somewhere: nothing the report holds is lost on the page.
        assert len(parts["over"]) + len(parts["near"]) + len(small) == 3 + 1 + 5

    def test_a_cheap_crossing_folds_with_the_small_items(self, rc):
        cheap = [_threshold(2030, "star", "Enhanced STAR limit", "over", 50_000.0, 40.0, boundary=110_000.0,
                            group="over", affects=2032)]
        parts = rc.threshold_parts(cheap, 0.05)
        assert parts["over"].empty and len(parts["small"]) == 1

    def test_years_apart_are_not_merged(self, rc):
        entries = [_threshold(y, "aca", CLIFF, "over", 40_000.0, 10_000.0, boundary=84_202.0, group="over")
                   for y in (2027, 2029)]
        assert list(rc.threshold_parts(entries, 0.05)["over"]["Year of income"]) == ["2027", "2029"]

    def test_a_cliff_crossed_inside_its_band_is_over_and_merges_with_its_neighbours(self, rc):
        """Review AO1, the shape of a Quick look of the synthetic baseline with $200k less in
        each taxable account: 2027 and 2028 are $2,399 and $3,852 over the 400% FPL line
        (inside its 5% band), 2029 far over. d64ec67 marked the first two "near": *Where the
        plan pays...* held 2029's $4,824 alone, and the two costliest crossings sat under
        *Close to a line*. The page regroups by side and line, so a result solved then is drawn
        right too."""
        entries = [_threshold(y, "aca", CLIFF, "over", a, c, boundary=84_202.0, group=g)
                   for y, a, c, g in ((2027, 2_399.0, 12_547.0, "near"), (2028, 3_852.0, 12_864.0, "near"),
                                      (2029, 76_979.0, 4_824.0, "over"))]
        parts = rc.threshold_parts(entries, 0.05)
        assert parts["near"].empty
        (row,) = parts["over"].to_dict("records")
        assert row["Year of income"] == "2027-2029" and row["Costs"] == "$4,824-$12,864"
        # An IRMAA tier and the Enhanced STAR limit crossed inside the band, marked "near" then.
        inside = [_threshold(2028, "irmaa", "IRMAA tier 1", "over", 10_402.0, 2_438.0, boundary=218_000.0,
                             group="near", affects=2030, total=2_438.0),
                  _threshold(2028, "star", "Enhanced STAR limit", "over", 145.0, 1_558.0, boundary=110_000.0,
                             group="near", affects=2030)]
        parts = rc.threshold_parts(inside, 0.05)
        assert parts["near"].empty and sorted(parts["over"]["Line"]) == ["Enhanced STAR limit", "IRMAA tier 1"]

    def test_the_under_side_and_continuous_edges_stay_near(self, rc):
        entries = [_threshold(2030, "irmaa", "IRMAA tier 1", "under", 9_000.0, 2_200.0, boundary=230_000.0,
                              group="near", affects=2032),
                   _threshold(2031, "niit", "NIIT threshold", "over", 4_000.0, 160.0, boundary=250_000.0,
                              group="near"),
                   _threshold(2027, "aca", "marketplace contribution step (3x FPL)", "over", 500.0, 300.0,
                              boundary=63_000.0, group="near")]
        parts = rc.threshold_parts(entries, 0.05)
        assert parts["over"].empty and len(parts["near"]) == 3

    def test_a_new_result_is_not_older(self, rc):
        assert rc.threshold_parts(_baseline_like(), 0.05)["older"] is False

    def test_an_older_result_is_marked_and_split_by_its_band(self, rc):
        """A result solved before the groups were marked: the page says so (and asks for a new
        solve); its entries still land in the right table, read against their band."""
        parts = rc.threshold_parts(_baseline_like(groups=False), 0.05, has_groups=False)
        assert parts["older"] is True
        assert list(parts["over"]["Line"]) == [CLIFF, "IRMAA tier 2", "Enhanced STAR limit"]
        assert list(parts["near"]["Line"]) == ["IRMAA tier 1"]
        assert len(parts["small"]) == 5


class TestUnitsSplitAndMarkers:
    """Ergonomics review S-4: today's dollars from each row's deflator, the state tax's parts,
    and the event markers, all from plan.json."""

    ROWS = [
        {"year": 2026, "ages": [62, 64], "deflator": 1.0, "spending": 100_000, "federal_income_tax": 10_000,
         "ltcg_tax": 0, "niit": 0, "payroll_tax": 0, "state_tax": 5_000, "local_tax": 800, "state_recapture": 300,
         "star_credit": 0, "medicare_premiums": 0, "aca_premiums": 0, "wages": 90_000, "wages_by_person": [90_000, 0],
         "ss_income": [0, 0], "pension_income": 0, "spia_income": 0, "portfolio_withdrawals": 20_000, "debt": 300_000},
        {"year": 2027, "ages": [63, 65], "deflator": 1.25, "spending": 125_000, "federal_income_tax": 12_500,
         "ltcg_tax": 0, "niit": 0, "payroll_tax": 0, "state_tax": -500, "local_tax": 250, "state_recapture": 0,
         "star_credit": 2_000, "medicare_premiums": 2_500, "aca_premiums": 0, "wages": 0, "wages_by_person": [0, 0],
         "ss_income": [0, 25_000], "pension_income": 0, "spia_income": 0, "portfolio_withdrawals": 50_000,
         "debt": 0},
        {"year": 2028, "ages": [64, 66], "deflator": 1.5, "spending": 150_000, "federal_income_tax": 15_000,
         "ltcg_tax": 0, "niit": 0, "payroll_tax": 0, "state_tax": 3_000, "local_tax": 300, "state_recapture": 0,
         "star_credit": 1_500, "medicare_premiums": 3_000, "aca_premiums": 0, "wages": 0, "wages_by_person": [0, 0],
         "ss_income": [0, 30_000], "pension_income": 0, "spia_income": 0, "portfolio_withdrawals": 60_000,
         "debt": 0},
    ]

    def test_today_s_dollars_divide_by_the_deflator(self, rc):
        shown = rc.in_units(self.ROWS, "today")
        assert [r["spending"] for r in shown] == [100_000, 100_000, 100_000]
        assert shown[1]["ss_income"] == [0, 20_000] and shown[1]["ages"] == [63, 65]
        assert rc.in_units(self.ROWS, "nominal") == self.ROWS
        fig = rc.taxes_and_premiums_figure(self.ROWS, "today")
        fed = next(t for t in fig.data if t.name == rc.flow_label("Federal income tax"))
        assert list(fed.y) == [10_000, 10_000, 10_000]
        assert fig.layout.yaxis.title.text == rc.TODAY_PER_YEAR
        assert rc.taxes_and_premiums_figure(self.ROWS, "nominal").layout.yaxis.title.text == rc.NOMINAL_PER_YEAR

    def test_an_older_result_draws_nominal(self, rc):
        old = [{k: v for k, v in r.items() if k not in ("deflator", "local_tax", "state_recapture", "star_credit",
                                                        "wages_by_person")} for r in self.ROWS]
        assert rc.effective_units(old, "today") == "nominal"
        fig = rc.taxes_and_premiums_figure(old, "today")
        assert fig.layout.yaxis.title.text == rc.NOMINAL_PER_YEAR
        names = [t.name for t in fig.data]
        assert rc.flow_label("State and local tax") in names and rc.flow_label("STAR credit") not in names
        assert [m[1] for m in rc.event_markers(old, ["A", "B"])] == ["Last loan year", "Last wages", "B: Medicare"]

    def test_the_state_tax_parts_add_up_to_the_net_state_tax(self, rc):
        parts = rc.state_tax_parts(self.ROWS)
        for n, row in enumerate(self.ROWS):
            assert parts["state"][n] + parts["local"][n] + parts["star"][n] == pytest.approx(row["state_tax"])
        assert parts["state"][1] == 1_250 and parts["star"][1] == -2_000  # a net refund year
        fig = rc.taxes_and_premiums_figure(self.ROWS, "nominal")
        by_name = {t.name: t for t in fig.data}
        assert {"State tax", "Local income tax (NYC / Yonkers)", "NY STAR credit"} <= set(by_name)
        assert rc.flow_label("State and local tax") not in by_name
        assert list(by_name["NY STAR credit"].y) == [0, -2_000, -1_500]
        assert "recapture" in by_name["State tax"].hovertemplate
        assert fig.layout.barmode == "relative"

    def test_a_part_that_is_zero_everywhere_is_not_drawn(self, rc):
        rows = [dict(r, local_tax=0, star_credit=0, state_recapture=0) for r in self.ROWS]
        names = [t.name for t in rc.taxes_and_premiums_figure(rows, "nominal").data]
        assert "State tax" in names
        assert "Local income tax (NYC / Yonkers)" not in names and "NY STAR credit" not in names

    def test_the_markers(self, rc):
        marks = rc.event_markers(self.ROWS, ["Ari", "Noa"], purchases={1: 700_000.0})
        assert marks == [(2026, "Ari's last work year"), (2026, "Last loan year"), (2027, "Noa: Medicare"),
                         (2027, "Purchase")]
        fig = rc.taxes_and_premiums_figure(self.ROWS, "today", marks)
        texts = [a.text for a in fig.layout.annotations]
        assert "Ari's last work year<br>Last loan year" in texts and "Noa: Medicare<br>Purchase" in texts

    def test_the_purchase_annotation_follows_the_units(self, rc):
        rows = [dict(r, portfolio_withdrawals=1_000_000 if r["year"] == 2027 else 20_000) for r in self.ROWS]
        fig = rc.income_sources_figure(rows, {1: 750_000.0}, "today")
        note = next(a.text for a in fig.layout.annotations if "purchase" in a.text)
        assert "600,000" in note  # 750,000 nominal / 1.25


class TestCompareCharts:
    """S-5: Compare's side-by-side charts, matched by calendar year, in the selected units."""

    A = [{"year": y, "deflator": 1.0 + 0.5 * (y - 2026), "spending": 100_000 * (1.0 + 0.5 * (y - 2026)),
          "liquid_net_worth": 1e6, "federal_income_tax": 10_000, "state_tax": 2_000, "medicare_premiums": 1_000}
         for y in (2026, 2027, 2028)]
    B = [{"year": y, "deflator": 1.0 + 0.5 * (y - 2026), "spending": 90_000 * (1.0 + 0.5 * (y - 2026)),
          "liquid_net_worth": 9e5, "federal_income_tax": 10_000, "state_tax": 2_000, "medicare_premiums": 0}
         for y in (2027, 2028, 2029)]  # a later plan year

    def test_series_by_calendar_year_in_units(self, rc):
        a, b = rc.compare_series(self.A, "today"), rc.compare_series(self.B, "today")
        assert a["Spending"] == {2026: 100_000, 2027: 100_000, 2028: 100_000}
        assert b["Spending"][2027] == pytest.approx(90_000)
        assert rc.compare_series(self.A, "nominal")["Spending"][2028] == 200_000
        assert a["Taxes and health premiums, cumulative"][2026] == 13_000

    def test_the_difference_is_over_the_common_years(self, rc):
        a, b = rc.compare_series(self.A, "today"), rc.compare_series(self.B, "today")
        fig = rc.compare_figure("Spending", a["Spending"], b["Spending"], diff=True)
        assert list(fig.data[0].x) == [2027, 2028]
        assert list(fig.data[0].y) == pytest.approx([-10_000, -10_000])
        overlay = rc.compare_figure("Spending", a["Spending"], b["Spending"])
        assert list(overlay.data[0].x) == [2026, 2027, 2028, 2029]
        assert overlay.data[0].y[3] is None and overlay.data[1].y[0] is None

    def test_magi_and_its_lines_from_the_brackets_rows(self, rc):
        years = [{"year": 2027, "magi": 100_000, "irmaa_edges": [{"label": "IRMAA tier 1", "amount": 218_000},
                                                                  {"label": "IRMAA tier 2", "amount": 274_000}],
                  "aca_lines": [{"label": "400% FPL (the subsidy cliff)", "amount": 84_600}]}]
        magi, irmaa, fpl = rc.magi_series(years, self.A, "today")
        assert magi == {2027: 100_000} and irmaa == {2027: 218_000} and fpl == {2027: 84_600}
        magi, _irmaa, _fpl = rc.magi_series(years, self.A, "nominal")
        assert magi == {2027: 150_000}  # today's dollars x the year's deflator

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
        assert table["IRMAA tier 1"].isna().all() and list(table["Of which taxable"]) == [5_000.0, 0.0]


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
        assert "Medicare premiums (with IRMAA)" in names and "Marketplace premiums" in names

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

    def test_the_paragraph_reads_the_same_rows(self, rc):
        text = rc.year_summary(2027, self.SOURCES, self.USES)
        assert text.startswith("**2027**: spending \\$141,369 plus big-ticket purchases \\$741,188.")
        assert ("Taxes \\$63,597: capital gains \\$36,187, state and local \\$22,499, NIIT \\$4,911, "
                "federal income tax \\$0.") in text
        assert "Health premiums \\$21,745 (marketplace \\$21,745)." in text
        assert "\\$8,072 goes back into savings." in text
        assert "the taxable (brokerage) accounts \\$888,582" in text

    def test_the_sankey_carries_the_amounts_and_the_taxes_total(self, rc):
        fig = rc.sankey_figure(2027, self.SOURCES, self.USES)
        sankey = fig.data[0]
        labels = list(sankey.node.label)
        hub = labels.index(f"2027 cash flow: ${sum(self.SOURCES.values()):,.0f}")
        assert "Taxes: $63,597" in labels and "Gains tax: $36,187" in labels
        links = list(zip(sankey.link.source, sankey.link.target, sankey.link.value, strict=True))
        into_hub = sum(v for s, t, v in links if t == hub)
        out_of_hub = sum(v for s, t, v in links if s == hub)
        assert into_hub == pytest.approx(sum(self.SOURCES.values()))
        assert out_of_hub == pytest.approx(sum(self.USES.values()))


def test_the_table_keeps_years_whole_and_empty_cells_empty(rc):
    years = [_bracket_row(2027, 120_000.0), {**_bracket_row(2052, 90_000.0), "irmaa_edges": [], "aca_lines": []}]
    table = rc.brackets_table(years)
    assert str(table["Year"].dtype) == "Int64" and str(table["Sets premiums of"].dtype) == "Int64"
    assert table["Sets premiums of"].isna().tolist() == [False, True]
    assert table["400% FPL"].dtype == float and table["400% FPL"].isna().tolist() == [False, True]


def test_no_page_uses_the_plain_number_format():
    """Streamlit 1.66 renders some integers wrongly with format="plain" (2028 as
    2027.9999999999998, 2034 as 2034.0000000000002; seen in a browser, 2026-11-07)."""
    offenders = [p.name for p in UI_DIR.glob("*.py") if 'format="plain"' in p.read_text(encoding="utf-8")]
    assert offenders == []

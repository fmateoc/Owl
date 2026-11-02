"""The claiming-age map over work_sweep.py's scores output (design 14.1, I7): parsing one
variant into an AgeMap, and the rule that shades ties together (R2's tolerances per cell)."""

import json

import pytest

from owlplanner.library import agemap
from owlplanner.library.view import NOISE_FRACTION

# work_sweep.py's shape (fork-notes/phase5/work_sweep.py, summarize): one row per work
# variant; `results` keyed by the claiming ages, each cell with value/tolerance/proved/ages.
SCORES = [
    {
        "name": "base",
        "free": ["Chris", "Pat"],
        "best": [822, 756],
        "sweeps": [{"pass": 0, "person": "Chris", "index": 0}, {"pass": 0, "person": "Pat", "index": 1}],
        "results": {
            "68y6m/63y0m": {"status": "solved", "value": 113_542.11, "tolerance": 1.13,
                            "proved": True, "ages": [822, 756]},
            "63y9m/63y0m": {"status": "solved", "value": 113_541.50, "tolerance": 1.13,
                            "proved": True, "ages": [765, 756]},
            "68y6m/62y0m": {"status": "solved", "value": 112_000.00, "tolerance": 1.12,
                            "proved": True, "ages": [822, 744]},
            "66y0m/63y0m": {"status": "solved", "value": 108_718.70, "tolerance": None,
                            "proved": False, "ages": [792, 756]},
        },
    },
    {
        "name": "pat-stops-2027",
        "free": ["Pat"],
        "best": [822, 747],
        "sweeps": [{"pass": 0, "person": "Pat", "index": 1}],
        "results": {
            "68y6m/62y3m": {"status": "solved", "value": 108_718.70, "tolerance": None,
                            "proved": False, "ages": [822, 747]},
            "68y6m/66y0m": {"status": "solved", "value": 109_000.00, "tolerance": None,
                            "proved": False, "ages": [822, 792]},
            "68y6m/67y0m": {"status": "failed", "value": None, "ages": [822, 804]},
        },
    },
]


@pytest.fixture
def maps():
    return agemap.parse_scores(SCORES)


class TestParsing:
    def test_one_map_per_work_variant_with_its_free_people_and_decided_ages(self, maps):
        assert [m.name for m in maps] == ["base", "pat-stops-2027"]
        assert maps[0].free == ["Chris", "Pat"]
        assert maps[0].decided == (822, 756)
        assert maps[1].free == ["Pat"]
        assert maps[1].decided == (747,)

    def test_cells_carry_the_free_persons_ages_and_the_objective(self, maps):
        m = maps[0]
        assert len(m.cells) == 4
        cell = m.at(822, 756)
        assert cell is not None and cell.value == pytest.approx(113_542.11)
        assert cell.tolerance == pytest.approx(1.13)

    def test_a_failed_solve_is_not_a_cell(self, maps):
        assert len(maps[1].cells) == 2
        assert all(c.ages != (804,) for c in maps[1].cells)

    def test_an_unproved_cell_falls_back_to_the_loop_noise_band(self, maps):
        cell = maps[0].at(792, 756)
        assert cell.tolerance == pytest.approx(NOISE_FRACTION * 108_718.70)

    def test_a_file_loads_from_a_path_and_from_bytes(self, tmp_path):
        path = tmp_path / "scores.json"
        path.write_text(json.dumps(SCORES), encoding="utf-8")
        assert [m.name for m in agemap.load_scores(path)] == ["base", "pat-stops-2027"]
        assert len(agemap.load_scores(json.dumps(SCORES).encode("utf-8"))) == 2

    def test_an_older_file_without_the_ages_column_reads_its_keys(self):
        doc = [{"name": "base", "free": ["Chris", "Pat"], "best": [822, 756], "sweeps": [],
                "results": {"68y6m/63y0m": {"status": "solved", "value": 100.0}}}]
        (m,) = agemap.parse_scores(doc)
        assert m.at(822, 756) is not None
        assert m.at(822, 756).tolerance == pytest.approx(NOISE_FRACTION * 100.0)


class TestTieShading:
    def test_cells_within_tolerance_of_the_best_share_its_shade(self, maps):
        groups = maps[0].tie_groups()
        # 113,542 and 113,541.50 are within 1.13 of each other; 112,000 and 108,718 are not.
        assert [[c.ages for c in g] for g in groups] == [
            [(822, 756), (765, 756)], [(822, 744)], [(792, 756)],
        ]

    def test_the_group_of_shades_the_best_group_first(self, maps):
        shades = maps[0].group_of()
        assert shades[(822, 756)] == 0 and shades[(765, 756)] == 0
        assert shades[(822, 744)] == 1 and shades[(792, 756)] == 2

    def test_the_larger_of_the_two_tolerances_decides_a_tie(self):
        m = agemap.AgeMap(name="x", free=["A", "B"], cells=[
            agemap.AgeCell(ages=(700, 700), value=100.0, tolerance=0.5),
            agemap.AgeCell(ages=(712, 700), value=99.0, tolerance=1.5),
        ])
        assert len(m.tie_groups()) == 1  # 1.0 apart, within the second cell's 1.5

    def test_the_map_knows_its_dimensions(self, maps):
        assert maps[0].dimensions == 2
        assert maps[0].x_ages() == [765, 792, 822]
        assert maps[0].y_ages() == [744, 756]
        assert maps[1].dimensions == 1
        assert maps[1].y_ages() == []
        assert maps[1].best().ages == (792,)

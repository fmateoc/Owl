"""A numeric solver option given on the command line arrives as text and must be read as a number."""

from owlplanner.cli.cmd_run import _parse_solver_opts
from owlplanner.config.schema import parse_solver_options


def test_ss_taxability_text_is_read_as_a_number():
    opts = parse_solver_options(dict(_parse_solver_opts(["withSSTaxability=0.85"])))
    assert opts["withSSTaxability"] == 0.85 and isinstance(opts["withSSTaxability"], float)


def test_ss_taxability_modes_stay_text():
    for mode in ("loop", "optimize"):
        assert parse_solver_options({"withSSTaxability": mode})["withSSTaxability"] == mode


def test_ss_taxability_number_unchanged():
    assert parse_solver_options({"withSSTaxability": 0.5})["withSSTaxability"] == 0.5
